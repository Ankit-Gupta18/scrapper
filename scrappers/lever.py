# scrappers/lever.py
import requests
from typing import List, Dict, Any
from scrappers.base import BaseJobScraper

# Lever's edge is slow to warm up — Mindtickle and Palantir timed out at 15s
# on cold hits during the India audit. Bumped to 30s to absorb the first
# request's TLS/pool setup without failing the whole board.
LEVER_REQUEST_TIMEOUT = 30


class BaseLeverScraper(BaseJobScraper):
    lever_company_id: str = ""
    company_slug: str = ""

    @property
    def target_slug(self) -> str:
        """Dynamically fallback to find the valid Lever slug."""
        if getattr(self, "lever_company_id", None):
            return self.lever_company_id.strip()
        if getattr(self, "company_slug", None):
            return self.company_slug.strip()
        # Fallback: convert company_name like "Lingaro Group" to "lingarogroup"
        return getattr(self, "company_name", "").lower().replace(" ", "")

    @property
    def api_url(self) -> str:
        return f"https://api.lever.co/v0/postings/{self.target_slug}?mode=json"

    def fetch_jobs(self) -> List[Dict[str, Any]]:
        slug = self.target_slug
        if not slug:
            print(f"[{self.company_name}] Error: No Lever slug provided.")
            return []

        headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                           "AppleWebKit/537.36 (KHTML, like Gecko) "
                           "Chrome/120.0.0.0 Safari/537.36",
            "Accept": "application/json",
        }

        try:
            response = requests.get(self.api_url, headers=headers, timeout=LEVER_REQUEST_TIMEOUT)
            response.raise_for_status()
            data = response.json()
        except Exception as e:
            print(f"[{self.company_name}] Failed: {e} for url: {self.api_url}")
            raise

        raw_jobs = []
        for item in data:
            job_id = item.get("id", "")
            title = item.get("text", "")
            hosted_url = item.get("hostedUrl", "")

            categories = item.get("categories", {})
            location = categories.get("location", "India")
            department = categories.get("department", "")

            raw_jobs.append(
                {
                    "id": job_id,
                    "title": title,
                    "url": hosted_url,
                    "location": location,
                    "department": department,
                    "createdAt": item.get("createdAt", ""),
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
                    "posted_date": item.get("createdAt", ""),
                }
            )
        return parsed_jobs