"""
Keka adapter — Indian HR/ATS SaaS. Board = Keka subdomain (e.g. `minfy` for
minfy.keka.com). A single GET to the platform's own /api/jobs/default/active
returns every open posting with description inline, no per-posting detail
fetch needed. Ported from freehire's internal/ingest/sources/keka.go.
"""
import requests
from typing import List, Dict, Any

from scrappers.base import BaseJobScraper


class BaseKekaScraper(BaseJobScraper):
    board: str = ""  # e.g. "minfy" for minfy.keka.com

    @property
    def base_url(self) -> str:
        return f"https://{self.board}.keka.com/careers"

    @property
    def api_url(self) -> str:
        return f"{self.base_url}/api/jobs/default/active"

    def fetch_jobs(self) -> List[Dict[str, Any]]:
        if not self.board:
            print(f"[{self.company_name}] Error: No Keka board (subdomain) provided.")
            return []

        headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                           "AppleWebKit/537.36 (KHTML, like Gecko) "
                           "Chrome/120.0.0.0 Safari/537.36",
            "Accept": "application/json",
        }

        try:
            response = requests.get(self.api_url, headers=headers, timeout=15)
            response.raise_for_status()
            data = response.json()
        except Exception as e:
            print(f"[{self.company_name}] Failed: {e} for url: {self.api_url}")
            raise

        if not isinstance(data, list):
            return []
        return data

    def parse_jobs(self, raw_jobs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        parsed = []
        for item in raw_jobs:
            job_id = str(item.get("id", ""))
            title = item.get("title", "")

            # First job location — city/state/country concatenated.
            locations = item.get("jobLocations") or []
            if locations:
                loc = locations[0]
                location_parts = [loc.get("city", ""), loc.get("state", ""), loc.get("countryName", "")]
                location = ", ".join(p for p in location_parts if p)
            else:
                location = ""

            parsed.append({
                "id": job_id,
                "company": self.company_name,
                "title": title,
                "url": f"{self.base_url}/jobdetails/{job_id}",
                "location": location,
                "posted_date": item.get("publishedOn", ""),
            })
        return parsed
