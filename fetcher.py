"""
Fetch LME daily prices (cash settlement, 3-month, LME stock) from
westmetall.com for several metals and write one clean CSV per metal.

Source pages (one per metal per year, 2008 -> current):
    https://www.westmetall.com/en/markdaten.php
        ?action=table&field=LME_<code>_cash&year=YYYY

Prices are USD/tonne. LME stock is in tonnes. Weekends and LME holidays
are simply absent from the upstream tables.

Historical years never change, so refresh_all() only re-downloads from the
year of the last date already in each CSV onward. Any days missed while
this program wasn't running are still filled in automatically, but a normal
run only fetches the current (and possibly previous) year instead of every
year back to 2008. If a CSV is missing or unreadable it is rebuilt in full.
"""

import datetime as dt
import io
import logging
import random
import time
import traceback
from pathlib import Path

import pandas as pd
import requests

import healthcheck

FIRST_YEAR = 2008

# Retry transient network failures to westmetall.com before giving up.
MAX_RETRIES = 4
RETRY_BACKOFF = 5  # seconds; multiplied by attempt number

# If the whole refresh fails (e.g. westmetall.com is down for a while), wait
# a couple of hours and try the entire run again before giving up for good.
LONG_RETRIES = 1
LONG_RETRY_MIN = 2 * 3600  # seconds
LONG_RETRY_MAX = 3 * 3600  # seconds

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
    url = BASE_URL.format(code=code, year=year)
    # westmetall.com occasionally times out or returns a 5xx; retry with
    # backoff so one transient hiccup doesn't fail the whole refresh.
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            r = requests.get(url, headers={"User-Agent": USER_AGENT}, timeout=30)
            r.raise_for_status()
            break
        except requests.RequestException as exc:
            if attempt == MAX_RETRIES:
                raise
            wait = RETRY_BACKOFF * attempt
            logging.warning(
                "fetch %s %s failed (attempt %d/%d): %s — retrying in %ds",
                code, year, attempt, MAX_RETRIES, exc, wait,
            )
            time.sleep(wait)
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


def _load_existing(path):
    """Return the existing CSV as a DataFrame, or None if missing/unusable."""
    if not path.exists():
        return None
    try:
        df = pd.read_csv(path, dtype={"date": str})
    except Exception as exc:  # corrupt/empty file — rebuild from scratch
        logging.warning("could not read %s (%s) — rebuilding in full", path, exc)
        return None
    if df.empty or "date" not in df.columns:
        return None
    return df


def refresh_metal(code, name):
    this_year = dt.date.today().year
    path = DATA_DIR / f"{name}.csv"

    existing = _load_existing(path)
    if existing is not None:
        # Historical years are immutable, so only re-fetch from the year of
        # the last stored date onward (refilling any recently missed days).
        start_year = int(existing["date"].max()[:4])
    else:
        start_year = FIRST_YEAR

    frames = [existing] if existing is not None else []
    for year in range(start_year, this_year + 1):
        raw = _fetch_year(code, year)
        frames.append(_clean(raw))
        time.sleep(1)  # be polite to westmetall.com
    out = (
        # Freshly fetched rows come after the existing ones, so keep="last"
        # lets any upstream corrections for overlapping dates win.
        pd.concat(frames, ignore_index=True)
        .drop_duplicates(subset="date", keep="last")
        .sort_values("date")
        .reset_index(drop=True)
    )
    out.to_csv(path, index=False)
    return path, len(out), out["date"].iloc[-1]


def refresh_all():
    DATA_DIR.mkdir(exist_ok=True)
    return {name: refresh_metal(code, name) for code, name in METALS.items()}


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")

    healthcheck.ping_start()
    for attempt in range(1, LONG_RETRIES + 2):
        try:
            results = refresh_all()
            summary = "\n".join(
                f"{name}: wrote {n} rows to {path}, latest = {latest}"
                for name, (path, n, latest) in results.items()
            )
            print(summary)
            healthcheck.ping_success(summary)
            break
        except Exception:
            tb = traceback.format_exc()
            print(tb)
            if attempt > LONG_RETRIES:
                # Out of long retries — fail for good and go red.
                healthcheck.ping_fail(tb)
                raise  # preserve the non-zero exit code so the workflow goes red too
            wait = random.randint(LONG_RETRY_MIN, LONG_RETRY_MAX)
            logging.warning(
                "refresh failed (attempt %d/%d) — retrying in %d min",
                attempt, LONG_RETRIES + 1, wait // 60,
            )
            time.sleep(wait)
