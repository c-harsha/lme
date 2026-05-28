# lme-copper

Daily LME Copper prices (USD/tonne) as a single CSV, refreshed by GitHub Actions.

- `data/copper.csv` — columns: `date, cash_settlement, three_month, lme_stock`. History from **2008-01-02** to present.
- Source: [westmetall.com](https://www.westmetall.com/en/markdaten.php?action=table&field=LME_Cu_cash) (one HTML page per year, scraped and concatenated).

## Raw URL for Sheets / Excel

```
https://raw.githubusercontent.com/<user>/lme-copper/main/data/copper.csv
```

## Run locally

```bash
pip install -r requirements.txt
python fetcher.py
```

## Notes

- Prices are USD per metric tonne; LME stock is tonnes.
- Weekends and LME holidays are absent from the upstream tables and so from the CSV.
- `fetcher.py` re-downloads every year on each run, so missed days self-heal.
- The cron runs at 18:00 UTC, after the LME official settlement.
