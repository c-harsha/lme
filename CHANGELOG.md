# Changelog

All notable changes to this project are documented here.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [Unreleased]

### Changed
- `refresh_metal()` now fetches incrementally: it reads each existing CSV and only
  re-downloads from the year of its last stored date onward, instead of every year
  back to 2008. Missing or unreadable CSVs are rebuilt in full, and overlapping
  dates keep the freshly fetched values so upstream corrections still apply.
- Bumped `actions/checkout` to `v5` and `actions/setup-python` to `v6` (Node 24
  native), resolving the Node 20 deprecation warning and dropping the
  `FORCE_JAVASCRIPT_ACTIONS_TO_NODE24` workaround.
- Moved the daily refresh schedule from 18:00 to 20:00 UTC (~3 hours after LME
  close) so official prices are reliably settled before the run.

### Added
- Health monitoring via [Healthchecks.io](https://healthchecks.io/docs/http_api/):
  the refresh job sends **start**, **success**, and **fail** pings around each run.
  - New `healthcheck.py` module — best-effort pings with bounded retries, a request
    timeout, and a body cap; a no-op when `HC_PING_URL` is unset.
  - `fetcher.py` wraps `refresh_all()` to ping start/success/fail (success carries a
    per-metal row-count summary, fail carries the traceback) and re-raises on error.
  - `refresh.yml` passes the `HC_PING_URL` secret to the fetch step.
  - README "Monitoring" section documenting setup and key rotation.
