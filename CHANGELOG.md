# Changelog

All notable changes to this project are documented here.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [Unreleased]

### Added
- Health monitoring via [Healthchecks.io](https://healthchecks.io/docs/http_api/):
  the refresh job sends **start**, **success**, and **fail** pings around each run.
  - New `healthcheck.py` module — best-effort pings with bounded retries, a request
    timeout, and a body cap; a no-op when `HC_PING_URL` is unset.
  - `fetcher.py` wraps `refresh_all()` to ping start/success/fail (success carries a
    per-metal row-count summary, fail carries the traceback) and re-raises on error.
  - `refresh.yml` passes the `HC_PING_URL` secret to the fetch step.
  - README "Monitoring" section documenting setup and key rotation.
