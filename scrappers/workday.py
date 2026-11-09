# scrappers/workday.py
import requests
from typing import List, Dict, Any
from scrappers.base import BaseJobScraper

class BaseWorkdayScraper(BaseJobScraper):
    # These must be set by subclasses
    tenant_host: str = ""      # e.g., "alteryx.wd108.myworkdayjobs.com"
    client_slug: str = ""      # e.g., "alteryx"
    site_slug: str = ""        # e.g., "AlteryxCareers"
    
    # Optional filtering facets override for server-side Workday filtering
    applied_facets: dict = {}

    @property
    def api_url(self) -> str:
        return f"https://{self.tenant_host}/wday/cxs/{self.client_slug}/{self.site_slug}/jobs"

    @property
    def site_base_url(self) -> str:
        return f"https://{self.tenant_host}/en-US/{self.site_slug}"

    def fetch_jobs(self) -> List[Dict[str, Any]]:
        all_jobs = []
        limit = 20
        offset = 0
        total = None

        headers = {
            "accept": "application/json",
            "content-type": "application/json",
            "user-agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/150.0.0.0 Safari/537.36",
        }

        while total is None or offset < total:
            payload = {
                "appliedFacets": self.applied_facets,
                "limit": limit,
                "offset": offset,
                "searchText": ""
            }

            response = requests.post(self.api_url, json=payload, headers=headers, timeout=15)
            response.raise_for_status()
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