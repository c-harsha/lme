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
pip install -r requirements.txt
python fetcher.py
```

Health pings are skipped locally unless you export `HC_PING_URL` (the base check URL);
see [Monitoring](#monitoring).

## Monitoring

The refresh job pings [Healthchecks.io](https://healthchecks.io/docs/http_api/) so an
outside monitor knows whether the daily run started, succeeded, or failed:

- **start** — sent before the fetch begins (lets Healthchecks.io measure duration and detect hangs).
- **success** — sent after all CSVs are written, with a per-metal row-count summary in the body.
- **fail** — sent on any unhandled exception, with the traceback in the body.

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
- `fetcher.py` re-downloads every year for every metal on each run, so missed days self-heal.
- The cron runs at 18:00 UTC, after the LME official settlement.
