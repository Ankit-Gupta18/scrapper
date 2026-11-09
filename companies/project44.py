# scrappers/project44.py
from typing import List, Dict, Any
from scrappers.greenhouse import BaseGreenhouseScraper


class Project44Scraper(BaseGreenhouseScraper):
    company_name: str = "project44"
    exclude_keywords = ["hardware", "support"]
    board_token: str = "project44"

    def parse_jobs(self, raw_jobs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        parsed_jobs = []

        eng_keywords = [
            "engineer", "engineering", "developer", "software",
           "backend", "fullstack", "full stack",
            "sde"
        ]

        india_locations = ["india", "bangalore", "bengaluru"]

        for item in raw_jobs:
            title = item.get("title", "")
            title_lower = title.lower()
            location = item.get("location", "")
            location_lower = location.lower()

            is_india = any(loc in location_lower for loc in india_locations) or location == ""
            is_engineering = any(kw in title_lower for kw in eng_keywords)

            if is_india and is_engineering:
                parsed_jobs.append(
                    {
                        "id": item["id"],
                        "company": self.company_name,
                        "title": title,
                        "url": item["url"],
                        "location": location or "Bengaluru, India",
                        "posted_date": item.get("updated_at", ""),
                    }
                )

        return parsed_jobs