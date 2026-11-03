# CLAUDE.md

Notes for Claude Code working in this repo. `README.md` is the user-facing doc; keep it in
sync when you change the schedule, triggers, retries, monitoring or CSV columns.

## What this is

- `fetcher.py` scrapes daily LME prices for six metals from westmetall.com and writes
  `data/<metal>.csv`.
- `healthcheck.py` sends best-effort Healthchecks.io pings (start / success / fail).
- `.github/workflows/refresh.yml` runs the fetch daily at 20:00 UTC and commits the CSVs.

## Commands

```bash
pip install -r requirements.txt            # CI uses Python 3.12
python3 -m py_compile fetcher.py healthcheck.py

# Check parsing against live data for every metal, without writing CSVs:
python3 -c '
import datetime, fetcher
year = datetime.date.today().year
for code in fetcher.METALS:
    print(code, len(fetcher._clean(fetcher._fetch_year(code, year))), "rows")
'

gh run list --limit 3                      # recent refresh runs
gh run watch <run-id> --exit-status
```

`python3 fetcher.py` does a full refresh and overwrites `data/*.csv`. If it fails, it sleeps
2–3 hours before retrying, so don't run it in the foreground while westmetall.com is failing.

## Testing

There is no test suite. After changing parsing, run the live check above for all metals.
After changing `healthcheck.py`, confirm the pings do nothing when `HC_PING_URL` is unset.

## Git and CI

- `main` has linear history with no merge commits. Rebase or cherry-pick branches onto
  `main` instead of `git merge`.
- The bot commits `data: refresh YYYY-MM-DD` to `main` most days. Run `git pull --ff-only`
  before starting work and before pushing.
- Pushing a change to `fetcher.py`, `healthcheck.py`, `requirements.txt` or the workflow starts
  a live refresh run, which commits data and pings Healthchecks.io. Docs-only pushes don't.
- Log user-visible changes in `CHANGELOG.md` under `[Unreleased]` (Keep a Changelog).
  Prefix docs-only commits with `docs:`.

## Rules

- Don't hand-edit `data/*.csv`; they're generated.
- Upstream columns are renamed by position, and `_check_layout()` guards their order. If
  westmetall changes its layout and the job fails, fix the parser; don't loosen the check.
- Monitoring must never break the job: `healthcheck.py` swallows its own errors and does
  nothing without `HC_PING_URL`. The real ping URL is a GitHub secret; never put it in code
  or logs.
- Be polite to westmetall.com: keep the 1-second sleep between pages and the `User-Agent`,
  and don't fetch in parallel.
- `requirements.txt` is pinned on purpose (pandas patch releases only). Bump versions
  deliberately and re-run the live check.
