# scrappers/groww.py
import requests
from typing import List, Dict, Any
from scrappers.base import BaseJobScraper


class GrowwScraper(BaseJobScraper):
    company_name: str = "groww"
    exclude_keywords = ["hardware", "support"]
    embed_url: str = "https://job-boards.eu.greenhouse.io/embed/open_positions?for=groww"

    def fetch_jobs(self) -> List[Dict[str, Any]]:
        headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                          "AppleWebKit/537.36 (KHTML, like Gecko) "
                          "Chrome/120.0.0.0 Safari/537.36",
            "Accept": "application/json",
        }

        # EU boards can also be fetched using standard API with provider flag
        api_url = "https://boards-api.greenhouse.io/v1/boards/groww/jobs?provider=greenhouse"

        try:
            response = requests.get(api_url, headers=headers, timeout=15)
            response.raise_for_status()
            data = response.json()
            return data.get("jobs", [])
        except Exception:
            # Fallback to direct EU Embed JSON endpoint if API errors
            try:
                res = requests.get(self.embed_url, headers=headers, timeout=15)
                res.raise_for_status()
                return res.json().get("jobs", [])
            except Exception as e:
                print(f"[{self.company_name}] Fetch failed: {e}")
                raise

    def parse_jobs(self, raw_jobs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        parsed_jobs = []

        eng_keywords = [
            "engineer", "engineering", "developer", "software",
            "frontend", "backend", "fullstack", "full stack",
            "data", "qa", "devops", "platform", "infrastructure",
            "systems", "architect", "tech lead", "technical lead", "sde", "sdet"
        ]

        india_locations = ["india", "bangalore", "bengaluru", "mumbai", "gurgaon"]

        for item in raw_jobs:
            job_id = str(item.get("id", ""))
            title = item.get("title", "")
            title_lower = title.lower()

            # Handle location structures from API or Embed responses
            location_info = item.get("location", {})
            if isinstance(location_info, dict):
                location = location_info.get("name", "")
            else:
                location = str(location_info)
                
            location_lower = location.lower()

            is_india = any(loc in location_lower for loc in india_locations) or location == ""
            is_engineering = any(kw in title_lower for kw in eng_keywords)

            if is_india and is_engineering:
                # Build canonical link matching job-boards.eu.greenhouse.io/groww/jobs/<id>
                abs_url = item.get("absolute_url") or f"https://job-boards.eu.greenhouse.io/groww/jobs/{job_id}"

                parsed_jobs.append(
                    {
                        "id": job_id,
                        "company": self.company_name,
                        "title": title,
                        "url": abs_url,
                        "location": location or "Bengaluru, India",
                        "posted_date": item.get("updated_at", ""),
                    }
                )

        return parsed_jobs