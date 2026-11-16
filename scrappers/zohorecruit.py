# scrappers/zohorecruit.py
import requests
from typing import List, Dict, Any
from scrappers.base import BaseJobScraper


class BaseZohoRecruitScraper(BaseJobScraper):
    """Zoho Recruit public career-site API. `host` is the Recruit portal host,
    e.g. quadeye.zohorecruit.in (the .in data centre) or <org>.zohorecruit.com."""
    host: str = ""

    @property
    def api_url(self) -> str:
        return f"https://{self.host}/recruit/v2/public/Job_Openings"

    def fetch_jobs(self) -> List[Dict[str, Any]]:
        if not self.host:
            print(f"[{self.company_name}] Error: No Zoho Recruit host provided.")
            return []
        headers = {
            "accept": "application/json",
            "user-agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
                          "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        }
        params = {"pagename": "Careers", "source": "CareerSite"}
        response = requests.get(self.api_url, params=params, headers=headers, timeout=30)
        response.raise_for_status()
        data = response.json()
        return [j for j in (data.get("data") or []) if isinstance(j, dict)]

    def parse_jobs(self, raw_jobs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        parsed = []
        for item in raw_jobs:
            job_id = str(item.get("id") or "")
            title = (item.get("Posting_Title") or item.get("Job_Opening_Name") or "").strip()
            if not job_id or not title:
                continue
            parts = [item.get("City"), item.get("State"), item.get("Country")]
            location = ", ".join(str(p) for p in parts if p) or "Unspecified"
            parsed.append({
                "id": job_id,
                "company": self.company_name,
                "title": title,
                "url": item.get("$url") or f"https://{self.host}/jobs/Careers/{job_id}",
                "location": location,
                "posted_date": item.get("Date_Opened", ""),
            })
        return parsed
