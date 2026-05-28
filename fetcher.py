"""
Fetch LME daily prices (cash settlement, 3-month, LME stock) from
westmetall.com for several metals and write one clean CSV per metal.

Source pages (one per metal per year, 2008 -> current):
    https://www.westmetall.com/en/markdaten.php
        ?action=table&field=LME_<code>_cash&year=YYYY

Prices are USD/tonne. LME stock is in tonnes. Weekends and LME holidays
are simply absent from the upstream tables.

Every call to refresh_all() re-downloads every year for every metal, so
any days missed while this program wasn't running are filled in
automatically.
"""

import datetime as dt
import io
import time
from pathlib import Path

import pandas as pd
import requests

FIRST_YEAR = 2008

# westmetall slug -> output filename stem
METALS = {
    "Cu": "copper",
    "Sn": "tin",
    "Pb": "lead",
    "Zn": "zinc",
    "Al": "aluminium",
    "Ni": "nickel",
}

BASE_URL = (
    "https://www.westmetall.com/en/markdaten.php"
    "?action=table&field=LME_{code}_cash&year={year}"
)
USER_AGENT = "lme-fetcher/1.0 (+https://github.com/c-harsha/lme)"

DATA_DIR = Path(__file__).parent / "data"


def _fetch_year(code, year):
    r = requests.get(
        BASE_URL.format(code=code, year=year),
        headers={"User-Agent": USER_AGENT},
        timeout=30,
    )
    r.raise_for_status()
    tables = pd.read_html(io.StringIO(r.text), thousands=",", decimal=".")
    for t in tables:
        if any("Cash-Settlement" in str(c) for c in t.columns):
            return t
    raise RuntimeError(f"no {code} table found for {year}")


def _clean(df):
    # Columns vary per metal ("LME Tin Cash-Settlement" etc.) — normalise by position.
    df = df.iloc[:, :4].copy()
    df.columns = ["date", "cash_settlement", "three_month", "lme_stock"]
    # Repeated header rows show up as literal "date" — drop them.
    df = df[df["date"].astype(str).str.lower() != "date"]
    df["date"] = pd.to_datetime(df["date"], format="%d. %B %Y", errors="coerce")
    for col in ("cash_settlement", "three_month", "lme_stock"):
        df[col] = pd.to_numeric(df[col], errors="coerce")
    df = df.dropna(subset=["date", "cash_settlement"])
    df["date"] = df["date"].dt.strftime("%Y-%m-%d")
    return df


def refresh_metal(code, name):
    this_year = dt.date.today().year
    frames = []
    for year in range(FIRST_YEAR, this_year + 1):
        raw = _fetch_year(code, year)
        frames.append(_clean(raw))
        time.sleep(1)  # be polite to westmetall.com
    out = (
        pd.concat(frames, ignore_index=True)
        .drop_duplicates(subset="date")
        .sort_values("date")
        .reset_index(drop=True)
    )
    path = DATA_DIR / f"{name}.csv"
    out.to_csv(path, index=False)
    return path, len(out), out["date"].iloc[-1]


def refresh_all():
    DATA_DIR.mkdir(exist_ok=True)
    return {name: refresh_metal(code, name) for code, name in METALS.items()}


if __name__ == "__main__":
    for name, (path, n, latest) in refresh_all().items():
        print(f"{name}: wrote {n} rows to {path}, latest = {latest}")
