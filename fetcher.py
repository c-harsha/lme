"""
Fetch LME Copper daily prices (cash settlement, 3-month, LME stock) from
westmetall.com and write a clean CSV covering all available years.

Source pages (one per year, 2008 -> current):
    https://www.westmetall.com/en/markdaten.php
        ?action=table&field=LME_Cu_cash&year=YYYY

Prices are USD/tonne. LME stock is in tonnes. Weekends and LME holidays
are simply absent from the upstream table.

Every call to refresh() re-downloads every year, so any days missed while
this program wasn't running are filled in automatically.
"""

import datetime as dt
import io
import time
from pathlib import Path

import pandas as pd
import requests

FIRST_YEAR = 2008
BASE_URL = (
    "https://www.westmetall.com/en/markdaten.php"
    "?action=table&field=LME_Cu_cash&year={year}"
)
USER_AGENT = "lme-copper-fetcher/1.0 (+https://github.com/)"

DATA_DIR = Path(__file__).parent / "data"
OUTPUT = DATA_DIR / "copper.csv"


def _fetch_year(year):
    r = requests.get(
        BASE_URL.format(year=year),
        headers={"User-Agent": USER_AGENT},
        timeout=30,
    )
    r.raise_for_status()
    tables = pd.read_html(io.StringIO(r.text), thousands=",", decimal=".")
    # The price table is the one with the cash-settlement column.
    for t in tables:
        if any("Cash-Settlement" in str(c) for c in t.columns):
            return t
    raise RuntimeError(f"no copper table found for {year}")


def _clean(df):
    df = df.rename(
        columns={
            "date": "date",
            "LME Copper Cash-Settlement": "cash_settlement",
            "LME Copper 3-month": "three_month",
            "LME Copper stock": "lme_stock",
        }
    )
    df = df[["date", "cash_settlement", "three_month", "lme_stock"]].copy()
    # Repeated header rows show up as literal "date" — drop them.
    df = df[df["date"].astype(str).str.lower() != "date"]
    df["date"] = pd.to_datetime(df["date"], format="%d. %B %Y", errors="coerce")
    for col in ("cash_settlement", "three_month", "lme_stock"):
        df[col] = pd.to_numeric(df[col], errors="coerce")
    df = df.dropna(subset=["date", "cash_settlement"])
    df["date"] = df["date"].dt.strftime("%Y-%m-%d")
    return df


def refresh():
    DATA_DIR.mkdir(exist_ok=True)
    this_year = dt.date.today().year
    frames = []
    for year in range(FIRST_YEAR, this_year + 1):
        raw = _fetch_year(year)
        frames.append(_clean(raw))
        time.sleep(1)  # be polite to westmetall.com
    out = (
        pd.concat(frames, ignore_index=True)
        .drop_duplicates(subset="date")
        .sort_values("date")
        .reset_index(drop=True)
    )
    out.to_csv(OUTPUT, index=False)
    return OUTPUT, len(out), out["date"].iloc[-1]


if __name__ == "__main__":
    path, n, latest = refresh()
    print(f"wrote {n} rows to {path}, latest = {latest}")
