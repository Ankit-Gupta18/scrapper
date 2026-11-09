# scrappers/phonepe.py
import requests
from typing import List, Dict, Any
from scrappers.base import BaseJobScraper


class PhonepeScraper(BaseJobScraper):
    company_name: str = "phonepe"
    exclude_keywords = ["hardware", "support"]
    api_url: str = "https://api.smartrecruiters.com/v1/companies/PHONEPELIMITED/postings"

    def fetch_jobs(self) -> List[Dict[str, Any]]:
        all_jobs = []
        limit = 100
        offset = 0
        total = None

        headers = {
            "accept": "application/json",
            "user-agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/150.0.0.0 Safari/537.36",
        }

        while total is None or offset < total:
            params = {
                "limit": limit,
                "offset": offset,
            }

            response = requests.get(self.api_url, headers=headers, params=params, timeout=15)
            response.raise_for_status()
            data = response.json()

            total = data.get("totalFound", 0)
            job_postings = data.get("content", [])

            if not job_postings:
                break

            all_jobs.extend(job_postings)
            offset += limit

        return all_jobs

    def parse_jobs(self, raw_jobs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        parsed_jobs = []

        eng_keywords = [
            "engineer", "engineering", "developer", "software",
            "backend", "fullstack", "full stack", "sde"
        ]

        india_locations = ["india", "bangalore", "bengaluru", "pune", "mumbai", "delhi", "gurugram", "noida"]

        for item in raw_jobs:
            title = item.get("name", "")
            title_lower = title.lower()

            # Location extraction from SmartRecruiters payload
            location_info = item.get("location", {})
            city = location_info.get("city", "")
            country = location_info.get("country", "")
            location = f"{city}, {country}".strip(", ") if city else "Bengaluru, India"
            location_lower = location.lower()

            is_india = any(loc in location_lower for loc in india_locations) or country.lower() == "in" or location == ""
            is_engineering = any(kw in title_lower for kw in eng_keywords)

            if is_india and is_engineering:
                job_id = str(item.get("id"))
                parsed_jobs.append(
                    {
                        "id": f"phonepe_{job_id}",
                        "company": self.company_name,
                        "title": title,
                        "url": f"https://jobs.smartrecruiters.com/PHONEPELIMITED/{job_id}",
                        "location": location,
                        "posted_date": item.get("releasedDate", ""),
                    }
                )

        return parsed_jobs