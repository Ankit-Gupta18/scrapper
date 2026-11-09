from typing import List, Dict, Any
import requests
from scrappers.base import BaseJobScraper


class ZohoScraper(BaseJobScraper):
    company_name = "Zoho"

    # Zoho Corp recruitment endpoint
    api_url = (
        "https://careers.zohocorp.com/recruit/v2/public/Job_Openings"
        "?pagename=Careers&source=CareerSite&extra_fields=%5B%22Remote_Job%22%5D"
    )

    # Filter rules evaluated by BaseJobScraper
    target_keywords = [
        "software", "engineer", "developer", "backend", 
        "full stack", "java", "frontend", "data", "python", 
        "member technical staff", "mts", "c++"
    ]
    exclude_keywords = ["intern", "hardware", "support"
    ]
    target_locations = [
        "india", "chennai", "tenkasi", "bengaluru", 
        "bangalore", "salem", "coimbatore"]

    def fetch_jobs(self) -> List[Dict[str, Any]]:
        # Persist session across requests to automatically accept and reuse cookies set by Zoho
        session = requests.Session()

        headers = {
            "Accept": "*/*",
            "Accept-Language": "en-US,en;q=0.9",
            "Origin": "https://www.zoho.com",
            "Referer": "https://www.zoho.com/",
            "User-Agent": (
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/124.0.0.0 Safari/537.36"
            ),
        }

        raw_jobs = []

        try:
            response = session.get(self.api_url, headers=headers, timeout=15)
            response.raise_for_status()
            data = response.json()
            
            job_list = data.get("data", [])

            for item in job_list:
                if not isinstance(item, dict):
                    continue

                job_id = str(item.get("id") or item.get("Job_Opening_ID") or "")
                title = (
                    item.get("Posting_Title") 
                    or item.get("Job_Opening_Name") 
                    or ""
                ).strip()

                # Extract location details
                city = item.get("City", "")
                state = item.get("State", "")
                country = item.get("Country", "")
                is_remote = item.get("Remote_Job", False)

                loc_parts = [p for p in [city, state, country] if p]
                if is_remote:
                    loc_parts.append("Remote")
                location = ", ".join(loc_parts) if loc_parts else "India"

                if not job_id or not title:
                    continue

                # Construct direct job detail URL
                job_url = f"https://www.zoho.com/careers/jobdetail.html?job_id={job_id}"

                raw_jobs.append({
                    "id": job_id,
                    "title": title,
                    "url": job_url,
                    "location": location,
                    "posted_date": str(item.get("Created_Time", "")),
                })

        except Exception as e:
            print(f"[{self.company_name}] Failed to fetch jobs: {e}")
            return []

        return raw_jobs

    def parse_jobs(self, raw_jobs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        return [
            {
                "id": item["id"],
                "company": self.company_name,
                "title": item["title"],
                "url": item["url"],
                "location": item["location"],
                "posted_date": item.get("posted_date", ""),
            }
            for item in raw_jobs
        ]