# scrappers/eightfold_pcsx.py
import time
import requests
from typing import List, Dict, Any
from scrappers.base import BaseJobScraper

PAGE_SIZE = 10        # the endpoint ignores larger `num` values
MAX_PAGES = 120       # safety ceiling (1200 postings)


class BaseEightfoldPcsxScraper(BaseJobScraper):
    """Eightfold 'PCSX' careers API (newer than /api/apply/v2). `host` is the Eightfold tenant host
    (e.g. qualcomm.eightfold.ai); `domain` is the company email domain (qualcomm.com).
    The search is done server-side for `search_location` so only India postings are paged."""
    host: str = ""
    domain: str = ""
    search_location: str = "India"

    @property
    def api_url(self) -> str:
        return f"https://{self.host}/api/pcsx/search"

    def fetch_jobs(self) -> List[Dict[str, Any]]:
        if not self.host or not self.domain:
            print(f"[{self.company_name}] Error: Eightfold host/domain not provided.")
            return []
        headers = {
            "accept": "application/json",
            "user-agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
                          "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        }
        positions: List[Dict[str, Any]] = []
        start, total = 0, None
        with requests.Session() as session:
            for _ in range(MAX_PAGES):
                params = {"domain": self.domain, "query": "", "location": self.search_location,
                          "start": start, "num": PAGE_SIZE, "sort_by": "relevance"}
                response = session.get(self.api_url, params=params, headers=headers, timeout=20)
                response.raise_for_status()
                data = (response.json() or {}).get("data") or {}
                page = data.get("positions") or []
                total = data.get("count", total)
                if not page:
                    break
                positions.extend(page)
                start += PAGE_SIZE
                if total is not None and start >= total:
                    break
                time.sleep(0.2)
        return positions

    def parse_jobs(self, raw_jobs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        parsed = []
        for item in raw_jobs:
            job_id = str(item.get("displayJobId") or item.get("id") or "")
            if not job_id:
                continue
            locations = item.get("locations") or item.get("standardizedLocations") or []
            path = item.get("positionUrl") or f"/careers/job/{item.get('id')}"
            parsed.append({
                "id": job_id,
                "company": self.company_name,
                "title": (item.get("name") or "").strip(),
                "url": f"https://{self.host}{path}",
                "location": "; ".join(locations) if isinstance(locations, list) else str(locations),
                "posted_date": str(item.get("postedTs", "")),
            })
        return parsed
