"""
Phenom adapter. Board = careers host (e.g. `careers.phenom.com`,
`careers.gehealthcare.com`). Ported from freehire's internal/ingest/sources/
phenom.go — one JSON POST to `/widgets` with `ddoKey=refineSearch`,
paginated, no per-tenant ref_num / country params needed. The host IS the
only per-tenant input; `country` here filters only the first page and we
rely on the location-token filter in BaseJobScraper for India selection.
"""
from typing import List, Dict, Any

from curl_cffi import requests

from scrappers.base import BaseJobScraper

PHENOM_PAGE_SIZE = 50
PHENOM_REQUEST_TIMEOUT = 20
PHENOM_MAX_PAGES = 40  # ceiling — a board of 2000 postings is already huge


class BasePhenomScraper(BaseJobScraper):
    company_domain: str = ""  # e.g. "careers.phenom.com"

    @property
    def api_url(self) -> str:
        return f"https://{self.company_domain}/widgets"

    @property
    def base_job_url(self) -> str:
        return f"https://{self.company_domain}/jobs/"

    def fetch_jobs(self) -> List[Dict[str, Any]]:
        if not self.company_domain:
            print(f"[{self.company_name}] Error: No company_domain provided.")
            return []

        session = requests.Session(impersonate="chrome120")
        headers = {
            "accept": "application/json",
            "content-type": "application/json",
            "origin": f"https://{self.company_domain}",
            "referer": f"https://{self.company_domain}/jobs/search",
            "user-agent": (
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/124.0.0.0 Safari/537.36"
            ),
        }

        raw_jobs: List[Dict[str, Any]] = []
        for page in range(PHENOM_MAX_PAGES):
            payload = {
                "deviceType": "desktop",
                "ddoKey": "refineSearch",
                "jobs": True,
                "from": page * PHENOM_PAGE_SIZE,
                "size": PHENOM_PAGE_SIZE,
            }
            try:
                response = session.post(
                    self.api_url, json=payload, headers=headers, timeout=PHENOM_REQUEST_TIMEOUT,
                )
                response.raise_for_status()
                data = response.json()
            except Exception as e:
                print(f"[{self.company_name}] Phenom page {page} failed: {e}")
                return raw_jobs

            batch = (data.get("refineSearch", {}) or {}).get("data", {}).get("jobs", []) or []
            if not batch:
                break
            raw_jobs.extend(batch)
            if len(batch) < PHENOM_PAGE_SIZE:
                break

        return raw_jobs

    def parse_jobs(self, raw_jobs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        parsed: List[Dict[str, Any]] = []
        for job in raw_jobs:
            if not isinstance(job, dict):
                continue
            job_id = job.get("jobId") or job.get("id") or job.get("jobSeqNo") or job.get("reqId")
            title = job.get("title") or job.get("jobTitle", "")
            if not job_id or not title:
                continue

            location = (
                job.get("location")
                or job.get("cityStateCountry")
                or job.get("country")
                or ""
            )
            slug = job.get("slug") or str(job_id).lower()

            parsed.append({
                "id": str(job_id),
                "company": self.company_name,
                "title": str(title).strip(),
                "url": f"{self.base_job_url}{slug}",
                "location": str(location).strip(),
                "posted_date": str(job.get("postedDate") or job.get("posted_at") or ""),
            })
        return parsed
