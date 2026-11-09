# scrappers/wordpress.py
import html
import requests
from typing import List, Dict, Any
from scrappers.base import BaseJobScraper

class BaseWordPressScraper(BaseJobScraper):
    site_url: str = ""  # e.g., "https://careers.housing.com"
    custom_post_type: str = "jobs"  # e.g., "jobs"

    @property
    def api_url(self) -> str:
        return f"{self.site_url.rstrip('/')}/wp-json/wp/v2/{self.custom_post_type}"

    def fetch_jobs(self) -> List[Dict[str, Any]]:
        headers = {
            "accept": "application/json",
            "user-agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
        }
        
        params = {"per_page": 100}
        response = requests.get(self.api_url, headers=headers, params=params, timeout=15)
        response.raise_for_status()
        return response.json()

    def parse_jobs(self, raw_jobs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        parsed_jobs = []

        for item in raw_jobs:
            job_id = str(item.get("id", ""))
            
            # Extract and unescape title
            title_obj = item.get("title", {})
            raw_title = title_obj.get("rendered", "") if isinstance(title_obj, dict) else str(title_obj)
            title = html.unescape(raw_title)

            job_url = item.get("link", "")
            posted_date = item.get("date", "")

            parsed_jobs.append({
                "id": job_id,
                "company": self.company_name,
                "title": title,
                "url": job_url,
                "location": "India",
                "posted_date": posted_date,
            })

        return parsed_jobs