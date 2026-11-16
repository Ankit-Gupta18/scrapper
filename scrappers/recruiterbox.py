# scrappers/recruiterbox.py
import requests
from typing import List, Dict, Any
from scrappers.base import BaseJobScraper


class BaseRecruiterboxScraper(BaseJobScraper):
    """Recruiterbox / Trakstar Hire public openings API. `client_name` is the subdomain of
    <client>.recruiterbox.com / <client>.hire.trakstar.com."""
    client_name: str = ""
    api_url: str = "https://jsapi.recruiterbox.com/v1/openings"

    def fetch_jobs(self) -> List[Dict[str, Any]]:
        if not self.client_name:
            print(f"[{self.company_name}] Error: No Recruiterbox client_name provided.")
            return []
        headers = {
            "accept": "application/json",
            "user-agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
                          "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        }
        response = requests.get(self.api_url, params={"client_name": self.client_name},
                                headers=headers, timeout=30)
        response.raise_for_status()
        return [j for j in ((response.json() or {}).get("objects") or []) if isinstance(j, dict)]

    def parse_jobs(self, raw_jobs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        parsed = []
        for item in raw_jobs:
            job_id = str(item.get("id", ""))
            if not job_id:
                continue
            loc = item.get("location") or {}
            if isinstance(loc, dict):
                location = ", ".join(str(loc[k]) for k in ("city", "state", "country") if loc.get(k))
            else:
                location = str(loc)
            parsed.append({
                "id": job_id,
                "company": self.company_name,
                "title": (item.get("title") or "").strip(),
                "url": item.get("hosted_url") or f"https://{self.client_name}.recruiterbox.com/jobs/{job_id}",
                "location": location or "Unspecified",
                "posted_date": "",
            })
        return parsed
