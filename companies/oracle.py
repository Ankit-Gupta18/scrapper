"""
Oracle custom scraper — Oracle Cloud HCM recruiting API hosted on their own
tenant (eeho.fa.us2.oraclecloud.com). One keyless GET returns a page of
requisitions with id/title/location inline; paginate via offset.
Light on CPU/RAM — pure JSON, no HTML parsing.
"""
from typing import List, Dict, Any
from urllib.parse import urlencode

import requests

from scrappers.base import BaseJobScraper

ORACLE_HOST = "eeho.fa.us2.oraclecloud.com"
ORACLE_API_URL = f"https://{ORACLE_HOST}/hcmRestApi/resources/latest/recruitingCEJobRequisitions"
ORACLE_JOB_URL_FMT = f"https://{ORACLE_HOST}/hcmUI/CandidateExperience/en/sites/CX_1/job/{{job_id}}"
ORACLE_PAGE_SIZE = 25
ORACLE_MAX_PAGES = 20   # 500 jobs cap
ORACLE_REQUEST_TIMEOUT = 20


class OracleScraper(BaseJobScraper):
    company_name = "Oracle"

    target_keywords = [
        "engineer", "developer", "software", "backend", "frontend",
        "fullstack", "full stack", "sde", "sdet", "mts",
    ]
    exclude_keywords = [
        "intern", "manager", "director", "vp", "principal",
        "lead", "staff", "senior", "hardware", "support"
    ]
    target_locations = [
        "india", "bengaluru", "bangalore", "hyderabad", "pune",
        "mumbai", "delhi", "gurgaon", "noida", "chennai",
    ]

    def fetch_jobs(self) -> List[Dict[str, Any]]:
        headers = {
            "accept": "application/json",
            "user-agent": (
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/124.0.0.0 Safari/537.36"
            ),
        }
        collected: List[Dict[str, Any]] = []
        for page in range(ORACLE_MAX_PAGES):
            # finder uses semicolons for params, kept as a raw string
            finder = (
                "findReqs;siteNumber=CX_1,facetsList=LOCATIONS;TITLES,"
                f"limit={ORACLE_PAGE_SIZE},offset={page * ORACLE_PAGE_SIZE},"
                "sortBy=POSTING_DATES_DESC"
            )
            params = {
                "onlyData": "true",
                "expand": "requisitionList.secondaryLocations",
                "finder": finder,
            }
            url = f"{ORACLE_API_URL}?{urlencode(params, safe=';,=')}"
            try:
                response = requests.get(url, headers=headers, timeout=ORACLE_REQUEST_TIMEOUT)
                response.raise_for_status()
                data = response.json()
            except Exception as e:
                print(f"[Oracle] page {page} failed: {e}")
                return collected

            items = data.get("items") or []
            if not items:
                break
            batch = items[0].get("requisitionList") or []
            if not batch:
                break
            collected.extend(batch)
            if len(batch) < ORACLE_PAGE_SIZE:
                break
        return collected

    def parse_jobs(self, raw_jobs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        parsed: List[Dict[str, Any]] = []
        for job in raw_jobs:
            jid = str(job.get("Id") or "")
            title = job.get("Title", "")
            if not jid or not title:
                continue
            parsed.append({
                "id": jid,
                "company": self.company_name,
                "title": title,
                "url": ORACLE_JOB_URL_FMT.format(job_id=jid),
                "location": job.get("PrimaryLocation", ""),
                "posted_date": job.get("PostedDate", ""),
            })
        return parsed
