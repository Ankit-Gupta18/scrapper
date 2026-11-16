# scrappers/workday.py
import os
import random
import threading
import time
from datetime import datetime, timezone
from curl_cffi import requests  # Chrome TLS fingerprint: python-requests' is throttled harder
from typing import List, Dict, Any, Optional, Sequence
from scrappers.base import BaseJobScraper

# Rate-limit friendliness (Workday answers 429 when one IP sends too many requests).
WORKDAY_MAX_CONCURRENT = max(1, int(os.getenv("WORKDAY_MAX_CONCURRENT", "3")))  # tenants paged at once
PAGE_DELAY_SEC = float(os.getenv("WORKDAY_PAGE_DELAY", "0.4"))   # pause between pages of one tenant
MAX_ATTEMPTS = 4          # per page, on 429 / 5xx
BACKOFF_BASE_SEC = 10     # 10s, 20s, 40s (or Retry-After if the server sends it)
BACKOFF_MAX_SEC = 90
_WORKDAY_SLOTS = threading.BoundedSemaphore(WORKDAY_MAX_CONCURRENT)

# Shared state: when ANY tenant gets a 429 every Workday request pauses (the limit is per source IP,
# so hammering other tenants meanwhile only extends the block). If several tenants in a row stay
# blocked after all retries, the IP is blocked: skip the rest of the run quickly instead of burning
# time (they are retried on the next run, and the failure is reported as usual).
_state_lock = threading.Lock()
_cooldown_until = 0.0
_blocked_streak = 0
BLOCK_BREAKER_THRESHOLD = int(os.getenv("WORKDAY_BREAKER_THRESHOLD", "4"))


def _wait_for_cooldown():
    while True:
        with _state_lock:
            remaining = _cooldown_until - time.time()
        if remaining <= 0:
            return
        time.sleep(min(remaining, 5))


def _start_cooldown(seconds: float):
    global _cooldown_until
    with _state_lock:
        _cooldown_until = max(_cooldown_until, time.time() + seconds)


def _record_outcome(blocked: bool):
    global _blocked_streak
    with _state_lock:
        _blocked_streak = _blocked_streak + 1 if blocked else 0


def _breaker_open() -> bool:
    with _state_lock:
        return _blocked_streak >= BLOCK_BREAKER_THRESHOLD

# Server-side narrowing. Scrapers only keep India roles, so by default Workday is asked for jobs
# matching this text instead of every job worldwide (4-7x fewer requests). The search is not
# perfect (e.g. a location that names only a city), so one run a day (UTC hour below) does an
# unfiltered full scan as a safety net. WORKDAY_FULL_SCAN=true forces a full scan.
DEFAULT_SEARCH_TEXTS = ("India",)
FULL_SCAN_UTC_HOUR = int(os.getenv("WORKDAY_FULL_SCAN_UTC_HOUR", "4"))


def _full_scan_now() -> bool:
    if os.getenv("WORKDAY_FULL_SCAN", "").strip().lower() in ("1", "true", "yes"):
        return True
    return datetime.now(timezone.utc).hour == FULL_SCAN_UTC_HOUR

class BaseWorkdayScraper(BaseJobScraper):
    # These must be set by subclasses
    tenant_host: str = ""      # e.g., "alteryx.wd108.myworkdayjobs.com"
    client_slug: str = ""      # e.g., "alteryx"
    site_slug: str = ""        # e.g., "AlteryxCareers"
    
    # Optional filtering facets override for server-side Workday filtering
    applied_facets: dict = {}

    # Optional server-side search queries (results are merged). None = default: "India" when no
    # facets narrow the list already, otherwise no search. Use [""] to always fetch everything.
    search_texts: Optional[Sequence[str]] = None

    def _queries(self) -> Sequence[str]:
        if _full_scan_now():
            return [""]
        if self.search_texts is not None:
            return list(self.search_texts) or [""]
        return [""] if self.applied_facets else list(DEFAULT_SEARCH_TEXTS)

    @property
    def api_url(self) -> str:
        return f"https://{self.tenant_host}/wday/cxs/{self.client_slug}/{self.site_slug}/jobs"

    @property
    def site_base_url(self) -> str:
        return f"https://{self.tenant_host}/en-US/{self.site_slug}"

    def _post_with_retry(self, session, payload: dict, headers: dict):
        """POST one page; on 429 / 5xx back off (honouring Retry-After) and retry."""
        for attempt in range(MAX_ATTEMPTS):
            _wait_for_cooldown()
            response = session.post(self.api_url, json=payload, headers=headers, timeout=15)
            status = response.status_code
            if status != 429 and status < 500:
                response.raise_for_status()
                return response
            retry_after = str(response.headers.get("Retry-After", ""))
            wait = float(retry_after) if retry_after.isdigit() else BACKOFF_BASE_SEC * (2 ** attempt)
            wait = min(wait, BACKOFF_MAX_SEC) + random.uniform(0, 3)
            if attempt == MAX_ATTEMPTS - 1:
                raise RuntimeError(
                    f"HTTP {status} from {self.tenant_host} at offset {payload.get('offset')} "
                    f"after {MAX_ATTEMPTS} attempts (Retry-After={retry_after or 'none'})"
                )
            _start_cooldown(wait)
        raise RuntimeError("unreachable")

    def fetch_jobs(self) -> List[Dict[str, Any]]:
        # Workday throttles per source IP, and GitHub runners share IPs. Only a few tenants are
        # paged at a time (class-level semaphore shared by every Workday scraper in the process).
        with _WORKDAY_SLOTS:
            if _breaker_open():
                raise RuntimeError(
                    f"Skipped: Workday keeps answering 429 to this IP ({BLOCK_BREAKER_THRESHOLD}+ tenants "
                    "in a row blocked); will retry next run"
                )
            merged, seen = [], set()
            try:
                for query in self._queries():
                    for item in self._fetch_all_pages(query):
                        key = item.get("externalPath") or (item.get("bulletFields") or [None])[0] or id(item)
                        if key in seen:
                            continue
                        seen.add(key)
                        merged.append(item)
            except RuntimeError as e:
                _record_outcome(blocked=str(e).startswith("HTTP 429"))
                raise
            _record_outcome(blocked=False)
            return merged

    def _fetch_all_pages(self, search_text: str = "") -> List[Dict[str, Any]]:
        all_jobs = []
        limit = 20
        offset = 0
        total = None

        headers = {
            "accept": "application/json",
            "content-type": "application/json",
        }

        with requests.Session(impersonate="chrome120") as session:
            while total is None or offset < total:
                payload = {
                    "appliedFacets": self.applied_facets,
                    "limit": limit,
                    "offset": offset,
                    "searchText": search_text
                }

                response = self._post_with_retry(session, payload, headers)
                data = response.json()

                # Some tenants (Intel, Wells Fargo, Mastercard, Sony) only report
                # `total` on the first page and return 0 afterwards; keep the first
                # non-zero value so pagination doesn't stop after 2 pages.
                total = data.get("total") or total or 0
                job_postings = data.get("jobPostings", [])

                if not job_postings:
                    break

                all_jobs.extend(job_postings)
                offset += limit

                if offset < total:
                    time.sleep(PAGE_DELAY_SEC + random.uniform(0, PAGE_DELAY_SEC / 2))

        return all_jobs

    def parse_jobs(self, raw_jobs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        parsed_jobs = []

        for item in raw_jobs:
            job_id = item.get("bulletFields", [None])[0] or item.get("jobPostingId", "")
            title = item.get("title", "")
            external_path = item.get("externalPath", "")
            location = item.get("locationsText", "Remote/Unspecified")
            posted_date = item.get("postedOn", "")

            job_url = f"{self.site_base_url}{external_path}" if external_path else ""

            # Pure transformation step (no filtering here)
            parsed_jobs.append({
                "id": job_id,
                "company": self.company_name,
                "title": title,
                "url": job_url,
                "location": location,
                "posted_date": posted_date,
            })

        return parsed_jobs