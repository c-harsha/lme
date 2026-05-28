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

## Notes

- Prices are USD per metric tonne; LME stock is tonnes.
- Weekends and LME holidays are absent from the upstream tables and so from the CSVs.
- `fetcher.py` re-downloads every year for every metal on each run, so missed days self-heal.
- The cron runs at 18:00 UTC, after the LME official settlement.
