# scrappers/rippling.py
import requests
from typing import List, Dict, Any
from scrappers.base import BaseJobScraper


class BaseRipplingScraper(BaseJobScraper):
    """Rippling ATS public board API (ats.rippling.com/<board>/jobs). One JSON list."""
    board: str = ""

    @property
    def api_url(self) -> str:
        return f"https://api.rippling.com/platform/api/ats/v1/board/{self.board}/jobs"

    def fetch_jobs(self) -> List[Dict[str, Any]]:
        if not self.board:
            print(f"[{self.company_name}] Error: No Rippling board provided.")
            return []
        headers = {
            "accept": "application/json",
            "user-agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
                          "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        }
        response = requests.get(self.api_url, headers=headers, timeout=30)
        response.raise_for_status()
        data = response.json()
        return data if isinstance(data, list) else []

    def parse_jobs(self, raw_jobs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        parsed = []
        for item in raw_jobs:
            job_id = str(item.get("uuid", ""))
            if not job_id:
                continue
            loc = item.get("workLocation") or {}
            parsed.append({
                "id": job_id,
                "company": self.company_name,
                "title": (item.get("name") or "").strip(),
                "url": item.get("url") or f"https://ats.rippling.com/{self.board}/jobs/{job_id}",
                "location": loc.get("label") or "Unspecified",
                "posted_date": "",
            })
        return parsed
