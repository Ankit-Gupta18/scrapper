"""
Netflix custom scraper — explore.jobs.netflix.net JSON search.
Server-side location filter works (passing `location=India` already narrows
response), so one or two paginated calls cover the full India catalogue.
"""
from typing import List, Dict, Any

import requests

from scrappers.base import BaseJobScraper

NETFLIX_API_URL = "https://explore.jobs.netflix.net/api/apply/v2/jobs"
NETFLIX_JOB_URL_FMT = "https://explore.jobs.netflix.net/careers/job/{job_id}"
NETFLIX_PAGE_SIZE = 50
NETFLIX_MAX_PAGES = 5  # 250 India jobs cap — Netflix's India catalogue is small
NETFLIX_REQUEST_TIMEOUT = 20


class NetflixScraper(BaseJobScraper):
    company_name = "Netflix"

    target_keywords = [
        "engineer", "developer", "software", "backend", "frontend",
        "fullstack", "full stack", "sde", "sdet",
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
        for page in range(NETFLIX_MAX_PAGES):
            params = {
                "domain": "netflix.com",
                "start": page * NETFLIX_PAGE_SIZE,
                "num": NETFLIX_PAGE_SIZE,
                "location": "India",
            }
            try:
                response = requests.get(
                    NETFLIX_API_URL,
                    headers=headers,
                    params=params,
                    timeout=NETFLIX_REQUEST_TIMEOUT,
                )
                response.raise_for_status()
                data = response.json()
            except Exception as e:
                print(f"[Netflix] page {page} failed: {e}")
                return collected

            batch = data.get("positions") or []
            if not batch:
                break
            collected.extend(batch)
            if len(batch) < NETFLIX_PAGE_SIZE:
                break
        return collected

    def parse_jobs(self, raw_jobs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        parsed: List[Dict[str, Any]] = []
        for job in raw_jobs:
            jid = str(job.get("id") or job.get("ats_job_id") or "")
            title = job.get("name", "")
            if not jid or not title:
                continue
            parsed.append({
                "id": jid,
                "company": self.company_name,
                "title": title,
                "url": NETFLIX_JOB_URL_FMT.format(job_id=jid),
                "location": job.get("location", ""),
                "posted_date": job.get("t_create", ""),
            })
        return parsed
