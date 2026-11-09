from typing import List, Dict, Any
import requests
from scrappers.base import BaseJobScraper


class BaseAshbyScraper(BaseJobScraper):
    job_board_name: str = ""  # e.g., "harvey" or "confluent"

    # Default filter lists (can be overridden in child company scrapers)
    target_keywords: List[str] = [
        "software", "engineer", "developer", "backend", "python", 
        "full stack", "java", "frontend", "data"
    ]
    exclude_keywords: List[str] = [
        "intern", "manager", "director", "vp", "principal", "lead", 
        "staff", "vulnerability", "reinforcement", "senior", "integration", 
        "support", "sr", "customer"
    ]
    target_locations: List[str] = [
        "india", "bengaluru", "bangalore", "hyderabad"
    ]

    @property
    def api_url(self) -> str:
        return f"https://api.ashbyhq.com/posting-api/job-board/{self.job_board_name}?includeCompensation=true"

    def fetch_jobs(self) -> List[Dict[str, Any]]:
        if not self.job_board_name:
            print(f"[{self.company_name}] Error: No job_board_name provided.")
            return []

        headers = {
            "accept": "application/json",
            "user-agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
        }
        
        try:
            # Ashby public posting API expects GET
            response = requests.get(self.api_url, headers=headers, timeout=15)
            response.raise_for_status()
            data = response.json()
            return data.get("jobs", [])
        except Exception as e:
            print(f"[{self.company_name}] Failed to fetch Ashby jobs: {e}")
            raise

    def parse_jobs(self, raw_jobs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        parsed_jobs = []

        for item in raw_jobs:
            # Skip unlisted or internal draft postings
            if not item.get("isListed", True):
                continue

            job_id = str(item.get("id", ""))
            title = item.get("title", "").strip()

            # Location formatting
            location = item.get("locationName") or item.get("location") or "Unspecified"
            if item.get("isRemote") and "remote" not in str(location).lower():
                location = f"{location} (Remote)"

            job_url = item.get("jobUrl") or f"https://jobs.ashbyhq.com/{self.job_board_name}/{job_id}"

            parsed_jobs.append({
                "id": job_id,
                "company": self.company_name,
                "title": title,
                "url": job_url,
                "location": str(location),
                "posted_date": item.get("publishedAt", ""),
            })

        return parsed_jobs