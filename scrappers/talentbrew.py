# scrappers/talentbrew.py
import time
import requests
from bs4 import BeautifulSoup
from typing import List, Dict, Any
from scrappers.base import BaseJobScraper

PAGE_SIZE = 100
MAX_PAGES = 40


class BaseTalentBrewScraper(BaseJobScraper):
    """Radancy TalentBrew career sites (jobs.intuit.com, careers.arm.com, ...). The search page's
    AJAX endpoint /search-jobs/results returns {"results": "<html>"}; the location parameter is not
    reliable without coordinates, so everything is paged and the India filter runs locally."""
    host: str = ""

    @property
    def api_url(self) -> str:
        return f"https://{self.host}/search-jobs/results"

    def _page(self, session, page: int) -> str:
        params = {
            "ActiveFacetID": 0, "CurrentPage": page, "RecordsPerPage": PAGE_SIZE,
            "TotalContentResults": "", "Distance": 50, "RadiusUnitType": 0, "Keywords": "",
            "Location": "", "ShowRadius": "False", "IsPagination": "False", "CustomFacetName": "",
            "FacetTerm": "", "FacetType": 0, "SearchResultsModuleName": "Search Results",
            "SearchFiltersModuleName": "Search Filters", "SortCriteria": 0, "SortDirection": 0,
            "SearchType": 5, "PostalCode": "", "fc": "", "fl": "", "fcf": "", "afc": "", "afl": "",
            "afcf": "", "TotalContentPages": "NaN",
        }
        headers = {
            "accept": "application/json, text/javascript, */*; q=0.01",
            "x-requested-with": "XMLHttpRequest",
            "user-agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
                          "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        }
        response = session.get(self.api_url, params=params, headers=headers, timeout=30)
        response.raise_for_status()
        return (response.json() or {}).get("results", "")

    def fetch_jobs(self) -> List[Dict[str, Any]]:
        if not self.host:
            print(f"[{self.company_name}] Error: No TalentBrew host provided.")
            return []
        items: List[Dict[str, Any]] = []
        with requests.Session() as session:
            for page in range(1, MAX_PAGES + 1):
                soup = BeautifulSoup(self._page(session, page), "lxml")
                section = soup.find("section", id="search-results")
                total_pages = int(section.get("data-total-pages", 0) or 0) if section else 0
                cards = [li for li in soup.find_all("li") if li.find("a", href=lambda h: h and "/job/" in h)]
                if not cards:
                    break
                for li in cards:
                    a = li.find("a", href=lambda h: h and "/job/" in h)
                    title_el = li.find("h2") or li.find(class_="job-card__title") or a
                    loc_el = li.find(class_="job-location") or li.find(class_="location")
                    href = a["href"]
                    items.append({
                        "id": a.get("data-job-id") or href.rstrip("/").split("/")[-1],
                        "title": title_el.get_text(" ", strip=True),
                        "location": loc_el.get_text(" ", strip=True) if loc_el else "",
                        "href": href,
                    })
                if page >= total_pages:
                    break
                time.sleep(0.2)
        return items

    def parse_jobs(self, raw_jobs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        seen, parsed = set(), []
        for item in raw_jobs:
            job_id = str(item["id"])
            if job_id in seen:
                continue
            seen.add(job_id)
            parsed.append({
                "id": job_id,
                "company": self.company_name,
                "title": item["title"],
                "url": f"https://{self.host}{item['href']}",
                "location": item["location"] or "Unspecified",
                "posted_date": "",
            })
        return parsed
