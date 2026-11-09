# scrappers/greenhouse.py
import requests
from typing import List, Dict, Any
from scrappers.base import BaseJobScraper


class BaseGreenhouseScraper(BaseJobScraper):
    board_token: str = ""
    company_slug: str = ""

    @property
    def target_token(self) -> str:
        if getattr(self, "board_token", None):
            return self.board_token.strip()
        if getattr(self, "company_slug", None):
            return self.company_slug.strip()
        return getattr(self, "company_name", "").lower().replace(" ", "")

    @property
    def api_url(self) -> str:
        # Greenhouse handles both US and EU boards at this single API endpoint:
        return f"https://boards-api.greenhouse.io/v1/boards/{self.target_token}/jobs"

    def fetch_jobs(self) -> List[Dict[str, Any]]:
        token = self.target_token
        if not token:
            print(f"[{self.company_name}] Error: No Greenhouse board_token provided.")
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

        raw_jobs = []
        jobs_list = data.get("jobs", [])

        for item in jobs_list:
            job_id = str(item.get("id", ""))
            title = item.get("title", "")
            absolute_url = item.get("absolute_url", "")

            location_info = item.get("location", {})
            location_name = (
                location_info.get("name", "India")
                if isinstance(location_info, dict)
                else str(location_info)
            )

            raw_jobs.append(
                {
                    "id": job_id,
                    "title": title,
                    "url": absolute_url,
                    "location": location_name,
                    "updated_at": item.get("updated_at", ""),
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
                    "posted_date": item.get("updated_at", ""),
                }
            )
        return parsed_jobs