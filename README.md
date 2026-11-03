# lme

Daily LME base-metal prices (USD/tonne) as per-metal CSVs, refreshed by GitHub Actions.

Each CSV has columns `date, cash_settlement, three_month, lme_stock` with history from **2008-01-02** to present:

| Metal | File | Source |
|---|---|---|
| Copper | `data/copper.csv` | [LME_Cu_cash](https://www.westmetall.com/en/markdaten.php?action=table&field=LME_Cu_cash) |
| Tin | `data/tin.csv` | [LME_Sn_cash](https://www.westmetall.com/en/markdaten.php?action=table&field=LME_Sn_cash) |
| Lead | `data/lead.csv` | [LME_Pb_cash](https://www.westmetall.com/en/markdaten.php?action=table&field=LME_Pb_cash) |
| Zinc | `data/zinc.csv` | [LME_Zn_cash](https://www.westmetall.com/en/markdaten.php?action=table&field=LME_Zn_cash) |
| Aluminium | `data/aluminium.csv` | [LME_Al_cash](https://www.westmetall.com/en/markdaten.php?action=table&field=LME_Al_cash) |
| Nickel | `data/nickel.csv` | [LME_Ni_cash](https://www.westmetall.com/en/markdaten.php?action=table&field=LME_Ni_cash) |

## Raw URL for Sheets / Excel

```
https://raw.githubusercontent.com/c-harsha/lme/main/data/<metal>.csv
```

## Run locally

```bash
pip install -r requirements.txt   # CI uses Python 3.12
python fetcher.py
```

If the refresh fails (for example, westmetall.com is down), `fetcher.py` waits 2–3 hours
and tries once more before exiting with an error. Press Ctrl+C to stop it sooner.

Health pings are skipped locally unless you export `HC_PING_URL` (the base check URL);
see [Monitoring](#monitoring).

## How the refresh runs

- **When:** daily at 20:00 UTC (~3 hours after the LME official settlement), on pushes to
  `main` that change `fetcher.py`, `healthcheck.py`, `requirements.txt` or the workflow, and
  on demand from the Actions tab. Docs and data commits don't start a run. If a run is
  already going, the new one waits for it instead of cancelling it.
- **What it fetches:** for each metal, only the years from the CSV's last date onward, so
  missed days fill themselves in without re-downloading 2008+. A missing or unreadable CSV
  is rebuilt in full. Where dates overlap, the freshly fetched values win, so upstream
  corrections are picked up.
- **Retries:** each page download is retried up to 4 times (waiting 5, 10, then 15 seconds).
  If the whole refresh still fails, the job waits 2–3 hours and tries once more.
- **Layout check:** columns are renamed by position, so the job first checks that the upstream
  table is still date, cash, 3-month, stock in that order. If not, it fails rather than
  writing data under the wrong column names.
- **Output:** the workflow commits changed CSVs to `main` as `data: refresh YYYY-MM-DD`.
- **Dependencies:** `requirements.txt` is pinned so a new upstream release can't break the
  daily job. pandas allows patch releases only; the others allow minor releases.

## Monitoring

The refresh job pings [Healthchecks.io](https://healthchecks.io/docs/http_api/) so an
outside monitor knows whether the daily run started, succeeded, or failed:

- **start** — sent before each attempt (lets Healthchecks.io measure duration and detect hangs).
- **success** — sent after all CSVs are written, with a per-metal row-count summary in the body.
- **fail** — sent when the last attempt fails, with the traceback in the body (trimmed to
  its last 10,000 characters, which hold the error).

No ping is sent during the 2–3 hour wait before a retry. Healthchecks.io marks a check down
if no success arrives within its grace time after a start ping, so with a grace time under
~3 hours you'll get a down alert during the wait. The check comes back up if the retry succeeds.

The ping URL is supplied through the `HC_PING_URL` GitHub Actions secret, set to the
**base check URL** (e.g. `https://hc-ping.com/<ping-key>/lme-price-updates`); the code derives
the `/start` and `/fail` endpoints from it. Pings are best-effort — a monitoring outage never
changes the job's outcome — and are skipped entirely when `HC_PING_URL` is unset, so local runs
and forks need no configuration.

To rotate the ping key, rotate it in the Healthchecks.io project and update the `HC_PING_URL`
secret; no code change is needed.

## Notes

- Prices are USD per metric tonne; LME stock is tonnes.
- Weekends and LME holidays are absent from the upstream tables and so from the CSVs.
