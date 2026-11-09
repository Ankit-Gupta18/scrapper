# scrappers/eightfold.py
import requests
from typing import List, Dict, Any
from scrappers.base import BaseJobScraper


class BaseEightfoldScraper(BaseJobScraper):
    domain: str = ""  # e.g., "careers.netapp.com"

    @property
    def api_url(self) -> str:
        return f"https://{self.domain}/api/apply/v2/jobs"

    def fetch_jobs(self) -> List[Dict[str, Any]]:
        if not self.domain:
            print(f"[{self.company_name}] Error: No domain provided.")
            return []

        headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                           "AppleWebKit/537.36 (KHTML, like Gecko) "
                           "Chrome/120.0.0.0 Safari/537.36",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

        # Query payload targeting India locations
        payload = {
            "start": 0,
            "num": 100,
            "location": "Karnataka, India",
            "sort_by": "relevance",
        }

        try:
            response = requests.post(self.api_url, json=payload, headers=headers, timeout=15)
            response.raise_for_status()
            data = response.json()
        except Exception as e:
            print(f"[{self.company_name}] Failed: {e} for url: {self.api_url}")
            return []

        raw_jobs = []
        positions = data.get("positions", [])

        for item in positions:
            job_id = str(item.get("id", ""))
            title = item.get("name", "")
            
            # Construct standard candidate URL
            canonical_url = f"https://{self.domain}/careers/job/{job_id}"

            # Extract location string
            locations = item.get("location", [])
            location_name = ", ".join(locations) if isinstance(locations, list) else str(locations)

            raw_jobs.append(
                {
                    "id": job_id,
                    "title": title,
                    "url": canonical_url,
                    "location": location_name if location_name else "India",
                    "posted_date": item.get("t_create", ""),
                }
            )

        return raw_jobs

    def parse_jobs(self, raw_jobs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        parsed_jobs = []
        for item in raw_jobs:
            parsed_jobs.append(
                {
                    "id": item["id"],
                    "company": self.company_name,
                    "title": item["title"],
                    "url": item["url"],
                    "location": item["location"],
                    "posted_date": item.get("posted_date", ""),
                }
            )
        return parsed_jobs