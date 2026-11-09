# scrappers/freshteam.py
import requests
from typing import List, Dict, Any
from scrappers.base import BaseJobScraper

class BaseFreshteamScraper(BaseJobScraper):
    freshteam_domain: str = ""  # e.g., "greythr", "housing"

    @property
    def api_url(self) -> str:
        return f"https://{self.freshteam_domain}.freshteam.com/api/job_postings"

    def fetch_jobs(self) -> List[Dict[str, Any]]:
        headers = {
            "accept": "application/json",
            "user-agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
        }
        
        response = requests.get(self.api_url, headers=headers, timeout=15)
        response.raise_for_status()
        return response.json()

    def parse_jobs(self, raw_jobs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        parsed_jobs = []

        for item in raw_jobs:
            job_id = str(item.get("id", ""))
            title = item.get("title", "")
            
            # Direct application page URL format for Freshteam
            job_url = f"https://{self.freshteam_domain}.freshteam.com/jobs/{job_id}"
            
            # Extract location city/string safely
            location_info = item.get("location", {})
            if isinstance(location_info, dict):
                location_name = location_info.get("city") or location_info.get("name") or "Unspecified"
            else:
                location_name = str(location_info) if location_info else "Unspecified"

            parsed_jobs.append({
                "id": job_id,
                "company": self.company_name,
                "title": title,
                "url": job_url,
                "location": location_name,
                "posted_date": item.get("created_at", ""),
            })

        return parsed_jobs