# companies/paylocity.py
import re
from urllib.parse import urljoin
import requests
from bs4 import BeautifulSoup
from typing import List, Dict, Any
from scrappers.base import BaseJobScraper


class PaylocityScraper(BaseJobScraper):
    company_name = "Paylocity"

    # Direct AEM component endpoint extracted from your curl
    search_url = (
        "https://www.paylocity.com/company/careers/product-technology/"
        "_jcr_content/root/container/container/careers/career-search/"
    )

    target_keywords = [
        "software",
        "engineer",
        "developer",
        "backend",
        "frontend",
        "full stack",
        "qa",
        "test engineer",
        "data engineer",
        "salesforce",
        "netsuite",
        "programmer",
        "architect",
        "product manager",
    ]

    exclude_keywords = [
        "intern",
        "director",
        "vp",
        "vice president",
        "manager"
        "product", "hardware", "support"
    ]

    target_locations = [
        "bengaluru",
        "bangalore",
        "india",
    ]

    def fetch_jobs(self) -> List[Dict[str, Any]]:
        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/150.0.0.0 Safari/537.36"
            ),
            "Accept": "*/*",
            "Referer": "https://www.paylocity.com/company/careers/product-technology/?l=Bengaluru%2C+India&r=10&p=1",
        }

        params = {
            "l": "Bengaluru, India",
            "r": "10",
            "p": "1",
        }

        try:
            response = requests.get(self.search_url, params=params, headers=headers, timeout=15)
            response.raise_for_status()
            html_content = response.text
        except Exception as e:
            print(f"[{self.company_name}] Failed to fetch jobs: {e}")
            raise

        soup = BeautifulSoup(html_content, "html.parser")
        raw_jobs = []
        seen_ids = set()

        # Target job links rendered by the career-search component
        job_cards = soup.select("a[href*='.job.'], a[href*='/careers/']")
        if not job_cards:
            job_cards = soup.find_all("a", href=re.compile(r"/job/|\.job\."))

        for card in job_cards:
            href = card.get("href", "")
            if not href:
                continue

            full_url = urljoin("https://www.paylocity.com/", href)

            # Extract job ID (e.g. .job.46500 or /job/46500)
            job_id_match = re.search(r"\.job\.(\d+)|/job/(\d+)", full_url)
            job_id = (
                job_id_match.group(1) or job_id_match.group(2)
                if job_id_match
                else card.get("data-job-id", href)
            )

            if job_id in seen_ids:
                continue

            # Title extraction
            title_elem = card.select_one("h2, h3, h4, .job-title, .title")
            title = title_elem.get_text(strip=True) if title_elem else card.get_text(strip=True)

            if not title or title.lower() in ["apply now", "learn more", "view job"]:
                parent = card.find_parent(["div", "li", "tr", "article"])
                if parent:
                    p_title = parent.select_one("h2, h3, h4, .job-title, .title")
                    if p_title:
                        title = p_title.get_text(strip=True)

            # Location extraction
            location = "Bengaluru, India"
            parent = card.find_parent(["div", "li", "tr", "article"])
            if parent:
                loc_elem = parent.select_one(".location, .job-location, span")
                if loc_elem:
                    location = loc_elem.get_text(strip=True)

            seen_ids.add(job_id)
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