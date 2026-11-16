# scrappers/zerodha.py
import requests
from typing import List, Dict, Any
from scrappers.base import BaseJobScraper


class BaseZerodhaScraper(BaseJobScraper):
    """careers.zerodha.com serves its (small) job list from /api/jobs as {count, data: [...]}."""
    api_url: str = "https://careers.zerodha.com/api/jobs"

    def fetch_jobs(self) -> List[Dict[str, Any]]:
        headers = {"accept": "application/json", "user-agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)"}
        response = requests.get(self.api_url, headers=headers, timeout=30)
        response.raise_for_status()
        return [j for j in ((response.json() or {}).get("data") or []) if isinstance(j, dict)]

    def parse_jobs(self, raw_jobs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        parsed = []
        for item in raw_jobs:
            slug = item.get("name") or item.get("job_title", "")
            if not slug:
                continue
            location = item.get("location") or "Unspecified"
            if "india" not in str(location).lower():
                location = f"{location}, India"   # Zerodha hires only in India
            parsed.append({
                "id": str(slug),
                "company": self.company_name,
                "title": (item.get("job_title") or "").strip(),
                "url": "https://careers.zerodha.com/",
                "location": location,
                "posted_date": "",
            })
        return parsed
