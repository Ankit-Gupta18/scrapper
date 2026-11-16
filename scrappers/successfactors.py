# scrappers/successfactors.py
import re
import time
import requests
from bs4 import BeautifulSoup
from typing import List, Dict, Any
from scrappers.base import BaseJobScraper

PAGE_SIZE = 25
MAX_PAGES = 40
COUNTRY_CODES = {"IN": "India"}


class BaseSuccessFactorsScraper(BaseJobScraper):
    """SAP SuccessFactors 'career site builder' pages (careers.payu.in, ...). The search page is
    server-rendered HTML: /search/?q=&locationsearch=<text>&startrow=<n>, 25 rows per page."""
    host: str = ""
    location_search: str = "India"

    def fetch_jobs(self) -> List[Dict[str, Any]]:
        if not self.host:
            print(f"[{self.company_name}] Error: No SuccessFactors host provided.")
            return []
        headers = {
            "accept": "text/html",
            "user-agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
                          "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        }
        items: List[Dict[str, Any]] = []
        with requests.Session() as session:
            for page in range(MAX_PAGES):
                params = {"q": "", "locationsearch": self.location_search, "startrow": page * PAGE_SIZE}
                response = session.get(f"https://{self.host}/search/", params=params, headers=headers, timeout=30)
                response.raise_for_status()
                soup = BeautifulSoup(response.text, "lxml")
                rows = soup.select("tr.data-row")
                if not rows:
                    break
                for row in rows:
                    link = row.select_one("a.jobTitle-link")
                    if not link:
                        continue
                    loc = row.select_one("td.colLocation span.jobLocation") or row.select_one("span.jobLocation")
                    date = row.select_one("span.jobDate")
                    items.append({
                        "href": link["href"],
                        "title": link.get_text(" ", strip=True),
                        "location": loc.get_text(" ", strip=True) if loc else "",
                        "date": date.get_text(" ", strip=True) if date else "",
                    })
                label = soup.select_one("span.paginationLabel")
                nums = re.findall(r"\d+", label.get_text(" ", strip=True).replace(",", "")) if label else []
                if len(nums) >= 3 and int(nums[1]) >= int(nums[2]):
                    break
                if len(rows) < PAGE_SIZE:
                    break
                time.sleep(0.2)
        return items

    def parse_jobs(self, raw_jobs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        seen, parsed = set(), []
        for item in raw_jobs:
            href = item["href"]
            m = re.search(r"/(\d+)/?$", href)
            job_id = m.group(1) if m else href
            if job_id in seen:
                continue
            seen.add(job_id)
            location = COUNTRY_CODES.get(item["location"].strip().upper(), item["location"])
            parsed.append({
                "id": job_id,
                "company": self.company_name,
                "title": item["title"],
                "url": f"https://{self.host}{href}",
                "location": location or "Unspecified",
                "posted_date": item["date"],
            })
        return parsed
