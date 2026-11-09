# companies/sharechat.py
import requests
from typing import List, Dict, Any
from scrappers.base import BaseJobScraper


class SharechatScraper(BaseJobScraper):
    company_name = "ShareChat"
    api_url = "https://sharechat.com/api/careersList?limit=100"

    # Standardized target tech keywords
    target_keywords = [
        "software",
        "engineer",
        "developer",
        "backend",
        "python",
        "full stack",
        "java",
        "frontend",
        "data",
    ]

    # Standardized seniority/role exclusions
    exclude_keywords = [
        "intern",
        "manager",
        "director",
        "vp",
        "principal",
        "lead",
        "staff",
        "vulnerability",
        "reinforcement",
        "senior",
        "integration",
        "support",
        "sr",
        "customer", "hardware"
    ]

    # Standardized locations
    target_locations = [
        "india",
        "bengaluru",
        "bangalore",
        "hyderabad",
    ]

    def fetch_jobs(self) -> List[Dict[str, Any]]:
        headers = {
            "accept": "application/json",
            "client-type": "web",
            "content-type": "application/json",
            "referer": "https://sharechat.com/careers",
            "user-agent": (
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/150.0.0.0 Safari/537.36"
            ),
        }

        try:
            response = requests.get(self.api_url, headers=headers, timeout=15)
            response.raise_for_status()
            response_json = response.json()
        except Exception as e:
            print(f"[{self.company_name}] Failed to fetch jobs: {e}")
            raise

        # Extract categories array from data.careersList
        careers_list = response_json.get("data", {}).get("careersList", [])
        raw_jobs = []

        # Iterate through categories (e.g. "Content & Operations", "Enablement", "Engineering")
        for category in careers_list:
            category_jobs = category.get("data", [])
            for job in category_jobs:
                req_id = job.get("requisitionId")
                title = job.get("requisitionTitle") or job.get("designation", "")

                if not req_id or not title:
                    continue

                # Parse locations array (e.g., ["Bangalore"], ["India"])
                locations = job.get("officeLocationNames", [])
                location_str = ", ".join(locations) if locations else "India"

                # Link points back to MyNextHire job detail view
                job_url = f"https://sharechat.mynexthire.com/employer/jobs?reqId={req_id}"

                raw_jobs.append({
                    "id": str(req_id),
                    "title": str(title).strip(),
                    "url": job_url,
                    "location": location_str,
                    "posted_date": str(job.get("createdDate", "")),
                })
        return raw_jobs

    def parse_jobs(self, raw_jobs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        parsed_jobs = []
        for item in raw_jobs:
            parsed_jobs.append({
                "id": item["id"],
                "company": self.company_name,
                "title": item["title"],
                "url": item["url"],
                "location": item["location"],
                "posted_date": item.get("posted_date", ""),
            })
        return parsed_jobs