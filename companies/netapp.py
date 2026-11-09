# companies/netapp.py
import re
import requests
from bs4 import BeautifulSoup
from typing import List, Dict, Any
from scrappers.base import BaseJobScraper


class NetappScraper(BaseJobScraper):
    company_name = "NetApp"

    search_url = "https://careers.netapp.com/search-jobs/results"

    target_keywords = [
        "software",
        "engineer",
        "developer",
        "backend",
        "python",
        "full stack",
        "c++",
        "cloud",
        "storage",
        "qa",
        "devops",
    ]

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
        "customer",
        "account",
        "sales", "hardware"
    ]

    target_locations = [
        "india",
        "bengaluru",
        "bangalore",
        "karnataka",
    ]

    def fetch_jobs(self) -> List[Dict[str, Any]]:
        headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                           "AppleWebKit/537.36 (KHTML, like Gecko) "
                           "Chrome/120.0.0.0 Safari/537.36",
            "Accept": "*/*",
            "Accept-Language": "en-US,en;q=0.9",
            "X-Requested-With": "XMLHttpRequest",
            "Referer": "https://careers.netapp.com/search-jobs/Karnataka?orgIds=27600&alp=1269750-1267701&alt=3",
        }

        # Parameters extracted from your browser curl snippet
        params = {
            "ActiveFacetID": "1269750-1267701",
            "CurrentPage": "1",
            "RecordsPerPage": "100",  # Fetch up to 100 Karnataka jobs in one call
            "TotalContentResults": "",
            "Distance": "50",
            "RadiusUnitType": "0",
            "Keywords": "",
            "Location": "Karnataka, India",
            "ShowRadius": "False",
            "IsPagination": "False",
            "CustomFacetName": "",
            "FacetTerm": "",
            "FacetType": "0",
            "FacetFilters[0].ID": "1269750-1267701",
            "FacetFilters[0].FacetType": "3",
            "FacetFilters[0].Display": "Karnataka, India",
            "FacetFilters[0].IsApplied": "true",
            "SearchResultsModuleName": "Search Results",
            "SearchFiltersModuleName": "Search Filters",
            "SortCriteria": "0",
            "SortDirection": "0",
            "SearchType": "6",
            "OrganizationIds": "27600",
            "PostalCode": "",
            "ResultsType": "0",
        }

        try:
            response = requests.get(self.search_url, params=params, headers=headers, timeout=15)
            response.raise_for_status()
            data = response.json()
        except Exception as e:
            print(f"[{self.company_name}] Failed to fetch jobs: {e}")
            return []

        html_results = data.get("results", "")
        if not html_results:
            print(f"[{self.company_name}] No results returned in response.")
            return []

        soup = BeautifulSoup(html_results, "html.parser")
        raw_jobs = []

        # Radancy job listing items
        for card in soup.select("ul li a"):
            href = card.get("href", "")
            if not href or "/job/" not in href:
                continue

            full_url = f"https://careers.netapp.com{href}" if href.startswith("/") else href

            job_id_match = re.search(r"/(\d+)(?:\?|$)", full_url)
            job_id = job_id_match.group(1) if job_id_match else card.get("data-job-id", href)

            title_elem = card.select_one("h2, h3, .job-title")
            title = title_elem.get_text(strip=True) if title_elem else card.get_text(strip=True)

            location_elem = card.select_one(".job-location, .location")
            location = location_elem.get_text(strip=True) if location_elem else "Karnataka, India"

            raw_jobs.append({
                "id": str(job_id),
                "title": title,
                "url": full_url,
                "location": location,
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
                "posted_date": "",
            })
        return parsed_jobs