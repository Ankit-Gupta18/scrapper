# scrappers/airbnb.py
from typing import List, Dict, Any
from scrappers.greenhouse import BaseGreenhouseScraper


class AirbnbScraper(BaseGreenhouseScraper):
    company_name: str = "airbnb"
    exclude_keywords = ["hardware", "support"]
    board_token: str = "airbnb"  # Greenhouse board token for Airbnb

    def parse_jobs(self, raw_jobs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        parsed_jobs = []

        # Keywords to match Engineering roles
        eng_keywords = [
            "engineer", "engineering", "developer", "software",
            "frontend", "backend", "fullstack", "full stack",
             "sde"
        ]

        # Location markers for India
        india_locations = ["india", "bangalore", "bengaluru"]

        for item in raw_jobs:
            title = item.get("title", "")
            title_lower = title.lower()
            location = item.get("location", "")
            location_lower = location.lower()

            # 1. Location check
            is_india = any(loc in location_lower for loc in india_locations)

            # 2. Department / Role title check
            is_engineering = any(kw in title_lower for kw in eng_keywords)

            if is_india and is_engineering:
                parsed_jobs.append(
                    {
                        "id": item["id"],
                        "company": self.company_name,
                        "title": title,
                        "url": item["url"],
                        "location": location,
                        "posted_date": item.get("updated_at", ""),
                    }
                )

        return parsed_jobs