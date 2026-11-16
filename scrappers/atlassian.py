# scrappers/atlassian.py
import requests
from typing import List, Dict, Any
from scrappers.base import BaseJobScraper


class BaseAtlassianScraper(BaseJobScraper):
    """Atlassian publishes every open role as one JSON list (no pagination)."""
    api_url: str = "https://www.atlassian.com/endpoint/careers/listings"

    def fetch_jobs(self) -> List[Dict[str, Any]]:
        headers = {
            "accept": "application/json",
            "user-agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
                          "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        }
        response = requests.get(self.api_url, headers=headers, timeout=30)
        response.raise_for_status()
        data = response.json()
        return data if isinstance(data, list) else []

    @staticmethod
    def _short_location(raw: str) -> str:
        # "Bengaluru - India -   Bengaluru,  560071 India" -> "Bengaluru, India"
        parts = [p.strip() for p in str(raw).split(" - ")]
        if len(parts) >= 2 and parts[0] and parts[1]:
            return f"{parts[0]}, {parts[1]}"
        return parts[0] if parts else ""

    def parse_jobs(self, raw_jobs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        parsed = []
        for item in raw_jobs:
            job_id = str(item.get("id", ""))
            if not job_id:
                continue
            locations = [self._short_location(l) for l in (item.get("locations") or [])]
            parsed.append({
                "id": job_id,
                "company": self.company_name,
                "title": (item.get("title") or "").strip(),
                "url": f"https://www.atlassian.com/company/careers/details/{job_id}",
                "location": "; ".join(l for l in locations if l) or "Unspecified",
                "posted_date": item.get("updatedDate", ""),
            })
        return parsed
