# scrappers/jibe.py
import time
import requests
from typing import List, Dict, Any
from scrappers.base import BaseJobScraper

PAGE_SIZE = 100
MAX_PAGES = 30


class BaseJibeScraper(BaseJobScraper):
    """iCIMS 'Jibe' career sites (www.github.careers, careers.docusign.com, ...). They expose
    /api/jobs with server-side country filtering. `host` is the careers site host."""
    host: str = ""
    country: str = "India"

    @property
    def api_url(self) -> str:
        return f"https://{self.host}/api/jobs"

    def fetch_jobs(self) -> List[Dict[str, Any]]:
        if not self.host:
            print(f"[{self.company_name}] Error: No Jibe host provided.")
            return []
        headers = {
            "accept": "application/json",
            "user-agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
                          "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        }
        jobs: List[Dict[str, Any]] = []
        with requests.Session() as session:
            for page in range(1, MAX_PAGES + 1):
                params = {"page": page, "limit": PAGE_SIZE, "sortBy": "relevance",
                          "descending": "false", "internal": "false"}
                if self.country:
                    params["country"] = self.country
                response = session.get(self.api_url, params=params, headers=headers, timeout=30)
                response.raise_for_status()
                data = response.json() or {}
                batch = data.get("jobs") or []
                if not batch:
                    break
                jobs.extend(batch)
                if len(jobs) >= int(data.get("totalCount") or 0):
                    break
                time.sleep(0.2)
        return jobs

    def parse_jobs(self, raw_jobs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        parsed = []
        for item in raw_jobs:
            d = item.get("data") or {}
            job_id = str(d.get("req_id") or d.get("slug") or "")
            if not job_id:
                continue
            place = d.get("full_location") or d.get("location_name") or ""
            country = d.get("country") or ""
            location = f"{place}, {country}".strip(", ") if country and country.lower() not in place.lower() else place
            parsed.append({
                "id": job_id,
                "company": self.company_name,
                "title": (d.get("title") or "").strip(),
                "url": f"https://{self.host}/careers-home/jobs/{d.get('slug') or job_id}",
                "location": location or "Unspecified",
                "posted_date": d.get("posted_date", ""),
            })
        return parsed
