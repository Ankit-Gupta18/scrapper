# scrappers/procore.py
from typing import List, Dict, Any
from scrappers.workday import BaseWorkdayScraper


class ProcoreScraper(BaseWorkdayScraper):
    company_name: str = "procore"
    exclude_keywords = ["hardware", "support"]
    tenant_host: str = "procore.wd12.myworkdayjobs.com"
    client_slug: str = "procore"
    site_slug: str = "Procore_External_Careers"

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

            locations_text = item.get("locationsText", "")
            location_desc = item.get("locationDescriptor", "")
            bullet_str = " ".join(item.get("bulletFields", []))

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
                        "location": locations_text or location_desc or "Bangalore, India",
                        "posted_date": item.get("postedOn", ""),
                    }
                )

        return parsed_jobs