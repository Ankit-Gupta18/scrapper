# scrappers/kula.py
import json
import requests
from typing import List, Dict, Any
from scrappers.base import BaseJobScraper


class BaseKulaScraper(BaseJobScraper):
    """Kula ATS career pages (careers.kula.ai/<board>). The server-rendered page embeds the full
    job list as JSON in the Next.js payload, so one GET is enough."""
    board: str = ""

    @property
    def page_url(self) -> str:
        return f"https://careers.kula.ai/{self.board}"

    def fetch_jobs(self) -> List[Dict[str, Any]]:
        if not self.board:
            print(f"[{self.company_name}] Error: No Kula board provided.")
            return []
        headers = {
            "accept": "text/html",
            "user-agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
                          "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        }
        response = requests.get(self.page_url, headers=headers, timeout=30)
        response.raise_for_status()
        text = response.text.replace('\\"', '"').replace("\\\\", "\\")
        marker = '"jobs":['
        start = text.find(marker)
        if start < 0:
            raise RuntimeError(f"Kula page for '{self.board}' has no embedded job list (layout changed?)")
        jobs, _ = json.JSONDecoder().raw_decode(text[start + len(marker) - 1:])
        return [j for j in jobs if isinstance(j, dict) and j.get("listed", True) and j.get("on_career_page", True)]

    def parse_jobs(self, raw_jobs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        parsed = []
        for item in raw_jobs:
            job_id = str(item.get("id", ""))
            if not job_id:
                continue
            offices = (item.get("ats_job") or {}).get("offices") or []
            location = "; ".join(o.get("location") or o.get("name", "") for o in offices if isinstance(o, dict)) or "Unspecified"
            parsed.append({
                "id": job_id,
                "company": self.company_name,
                "title": (item.get("title") or "").strip(),
                "url": f"{self.page_url}/{job_id}",
                "location": location,
                "posted_date": item.get("launch_at", ""),
            })
        return parsed
