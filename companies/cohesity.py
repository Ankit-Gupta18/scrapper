# scrappers/cohesity.py
from typing import List, Dict, Any
from scrappers.workday import BaseWorkdayScraper


class CohesityScraper(BaseWorkdayScraper):
    company_name: str = "cohesity"
    exclude_keywords = ["hardware", "support"]
    tenant_host: str = "cohesity.wd5.myworkdayjobs.com"
    client_slug: str = "cohesity"
    site_slug: str = "Cohesity_Careers"

    def parse_jobs(self, raw_jobs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        parsed_jobs = []

        # Target keywords for Engineering & Tech roles
        eng_keywords = [
            "engineer", "engineering", "developer", "software",
            "frontend", "backend", "fullstack", "full stack",
            "sde",
           "member of technical staff", "mts"
        ]

        # Target locations in India
        india_locations = ["india", "bangalore", "bengaluru", "pune", "mumbai", "elnath"]

        for item in raw_jobs:
            title = item.get("title", "")
            title_lower = title.lower()

            # Workday location fields
            locations_text = item.get("locationsText", "")
            location_desc = item.get("locationDescriptor", "")
            bullet_str = " ".join(item.get("bulletFields", []))

            # Combine all text fields to ensure no location data is missed
            combined_text = f"{title} {locations_text} {location_desc} {bullet_str}".lower()

            is_india = any(loc in combined_text for loc in india_locations)
            is_engineering = any(kw in title_lower for kw in eng_keywords)

            if is_india and is_engineering:
                external_path = item.get("externalPath", "")
                job_url = f"{self.site_base_url}{external_path}" if external_path else ""

                parsed_jobs.append(
                    {
                        "id": external_path or item.get("bulletFields", [title])[0],
                        "company": self.company_name,
                        "title": title,
                        "url": job_url,
                        "location": locations_text or location_desc or "India",
                        "posted_date": item.get("postedOn", ""),
                    }
                )

        return parsed_jobs