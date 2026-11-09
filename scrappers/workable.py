from typing import List, Dict, Any
import requests
from scrappers.base import BaseJobScraper


class BaseWorkableScraper(BaseJobScraper):
    company_subdomain: str = ""  # e.g., "writesonic"

    @property
    def api_url(self) -> str:
        return f"https://apply.workable.com/api/v1/widget/accounts/{self.company_subdomain}"

    def fetch_jobs(self) -> List[Dict[str, Any]]:
        if not self.company_subdomain:
            print(f"[{self.company_name}] Error: No company_subdomain provided.")
            return []

        headers = {
            "Accept": "application/json",
            "User-Agent": (
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/124.0.0.0 Safari/537.36"
            ),
        }

        try:
            response = requests.get(self.api_url, headers=headers, timeout=15)
            response.raise_for_status()
            data = response.json()
            return data.get("jobs", [])
        except Exception as e:
            print(f"[{self.company_name}] Failed to fetch Workable jobs: {e}")
            raise

    def parse_jobs(self, raw_jobs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        parsed_jobs = []

        for item in raw_jobs:
            if not isinstance(item, dict):
                continue

            shortcode = item.get("shortcode", "")
            title = item.get("title", "").strip()

            # Location extraction
            city = item.get("city", "")
            country = item.get("country", "")
            telecommute = item.get("telecommute", False)

            loc_parts = [p for p in [city, country] if p]
            if telecommute:
                loc_parts.append("Remote")
            
            location = ", ".join(loc_parts) if loc_parts else "Unspecified"

            # Construct job URL matching Workable's shortcode pattern
            job_url = f"https://apply.workable.com/{self.company_subdomain}/j/{shortcode}/"

            parsed_jobs.append({
                "id": shortcode,
                "company": self.company_name,
                "title": title,
                "url": job_url,
                "location": location,
                "posted_date": item.get("published_on", ""),
            })

        return parsed_jobs