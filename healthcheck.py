"""
Best-effort health pings to Healthchecks.io (https://healthchecks.io/docs/http_api/).

We use the slug-based ping URLs:
    <base>          -> success
    <base>/start    -> run started
    <base>/fail     -> run failed
where <base> is supplied (without trailing slash) via the HC_PING_URL env var,
e.g. https://hc-ping.com/<ping-key>/lme-price-updates

Every function here is intentionally failure-proof: a monitoring problem must
never affect the outcome of the job it is monitoring.
"""

import logging
import os

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

log = logging.getLogger("healthcheck")

# Healthchecks.io accepts up to 100 KB of body; keep well under that.
_MAX_BODY = 10_000
_TIMEOUT = 10  # seconds

# A short, bounded retry policy so transient network errors don't lose a ping,
# without ever blocking the job for long.
_RETRY = Retry(
    total=3,
    backoff_factor=1,  # 0s, 1s, 2s between attempts
    status_forcelist=(500, 502, 503, 504),
    allowed_methods=frozenset({"GET", "POST"}),
)


def _session():
    s = requests.Session()
    adapter = HTTPAdapter(max_retries=_RETRY)
    s.mount("https://", adapter)
    s.headers["User-Agent"] = "lme-fetcher/1.0 (+https://github.com/c-harsha/lme)"
    return s


def _ping(suffix="", body=""):
    base = os.environ.get("HC_PING_URL")
    if not base:
        # No secret configured (local dev, forks, PRs): silently skip.
        log.debug("HC_PING_URL not set; skipping %r ping", suffix or "success")
        return

    url = base.rstrip("/") + suffix
    try:
        with _session() as s:
            s.post(url, data=body[:_MAX_BODY].encode("utf-8"), timeout=_TIMEOUT)
    except requests.RequestException as exc:
        # Never propagate: monitoring must not break the monitored job.
        log.warning("health ping %r failed: %s", suffix or "success", exc)


def ping_start():
    _ping("/start")


def ping_success(body=""):
    _ping("", body)


def ping_fail(body=""):
    _ping("/fail", body)
