# scrappers/smartrecruiters.py
import requests
from typing import List, Dict, Any
from scrappers.base import BaseJobScraper


class BaseSmartRecruitersScraper(BaseJobScraper):
    """SmartRecruiters public postings API. `sr_company_id` is the identifier in
    https://jobs.smartrecruiters.com/<identifier> (case-insensitive for the API)."""
    sr_company_id: str = ""
    # Server-side country filter (ISO code). Cuts big boards (ServiceNow: 816 postings) to the
    # India subset, which is all the scrapers keep anyway.
    country: str = "in"
    page_size: int = 100

    @property
    def api_url(self) -> str:
        return f"https://api.smartrecruiters.com/v1/companies/{self.sr_company_id}/postings"

    def fetch_jobs(self) -> List[Dict[str, Any]]:
        if not self.sr_company_id:
            print(f"[{self.company_name}] Error: No SmartRecruiters company id provided.")
            return []

        headers = {
            "accept": "application/json",
            "user-agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
                          "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        }
        all_jobs: List[Dict[str, Any]] = []
        offset = 0
        total = None

        while total is None or offset < total:
            params = {"limit": self.page_size, "offset": offset}
            if self.country:
                params["country"] = self.country
            response = requests.get(self.api_url, headers=headers, params=params, timeout=15)
            response.raise_for_status()
            data = response.json()

            total = data.get("totalFound", 0)
            postings = data.get("content", [])
            if not postings:
                break
            all_jobs.extend(postings)
            offset += self.page_size

        return all_jobs

    def parse_jobs(self, raw_jobs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        parsed = []
        for item in raw_jobs:
            job_id = str(item.get("id", ""))
            loc = item.get("location") or {}
            location = loc.get("fullLocation") or ", ".join(
                p for p in (loc.get("city"), loc.get("region"), (loc.get("country") or "").upper()) if p
            )
            identifier = (item.get("company") or {}).get("identifier") or self.sr_company_id
            parsed.append({
                "id": job_id,
                "company": self.company_name,
                "title": item.get("name", ""),
                "url": f"https://jobs.smartrecruiters.com/{identifier}/{job_id}",
                "location": location,
                "posted_date": item.get("releasedDate", ""),
            })
        return parsed
