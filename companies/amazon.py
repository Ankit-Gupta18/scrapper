"""
Amazon custom scraper — amazon.jobs public JSON search API. The ATS is Amazon's
own portal, not any ATS our catalog base classes cover. One keyless GET per page.

Filter at the API layer by `normalized_country_code=IND` + a set of
engineering-adjacent job categories so we only fetch India tech roles. The
BaseJobScraper matches_filter then applies the usual title/location gate.
"""
from typing import List, Dict, Any
from urllib.parse import urlencode

import requests

from scrappers.base import BaseJobScraper

AMAZON_SEARCH_URL = "https://www.amazon.jobs/en/search.json"
AMAZON_JOB_BASE = "https://www.amazon.jobs"
AMAZON_PAGE_SIZE = 100
AMAZON_MAX_PAGES = 10          # safety ceiling — 1000 jobs max per cycle
AMAZON_REQUEST_TIMEOUT = 20

# Job categories to pull. Amazon's own taxonomy; names must match exactly.
# "Software Development" alone covers ~2k India roles; adding Data Science /
# Machine Learning / Solutions Architect brings MLE and SRE roles into net.
AMAZON_TECH_CATEGORIES = [
    "Software Development",
    "Data Science",
    "Machine Learning Science",
    "Solutions Architect",
    "Systems, Quality, & Security Engineering",
]


class AmazonScraper(BaseJobScraper):
    company_name = "Amazon"

    # Mid-junior India engineering filter — mirrors the Category C template.
    target_keywords = [
        "engineer", "developer", "software", "backend", "frontend",
        "fullstack", "full stack", "sde", "sdet", "data scientist",
        "machine learning", "mle",
    ]
    exclude_keywords = [
        "intern", "manager", "director", "vp", "principal",
        "lead", "staff", "senior", "sr.", "sr ", "hardware", "support"
    ]
    target_locations = [
        "india", "bengaluru", "bangalore", "hyderabad", "pune",
        "chennai", "mumbai", "delhi", "gurgaon", "noida",
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
        seen_ids = set()  # Amazon returns the same posting across categories

        for category in AMAZON_TECH_CATEGORIES:
            for page in range(AMAZON_MAX_PAGES):
                params = [
                    ("offset", page * AMAZON_PAGE_SIZE),
                    ("result_limit", AMAZON_PAGE_SIZE),
                    ("sort", "recent"),
                    ("normalized_country_code[]", "IND"),
                    ("job_category[]", category),
                ]
                url = f"{AMAZON_SEARCH_URL}?{urlencode(params)}"
                try:
                    response = requests.get(url, headers=headers, timeout=AMAZON_REQUEST_TIMEOUT)
                    response.raise_for_status()
                    data = response.json()
                except Exception as e:
                    print(f"[Amazon] category={category!r} page={page} failed: {e}")
                    break

                batch = data.get("jobs") or []
                if not batch:
                    break
                for job in batch:
                    jid = str(job.get("id") or job.get("id_icims") or "")
                    if not jid or jid in seen_ids:
                        continue
                    seen_ids.add(jid)
                    collected.append(job)
                if len(batch) < AMAZON_PAGE_SIZE:
                    break

        return collected

    def parse_jobs(self, raw_jobs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        parsed: List[Dict[str, Any]] = []
        for job in raw_jobs:
            jid = str(job.get("id") or job.get("id_icims") or "")
            title = job.get("title", "")
            if not jid or not title:
                continue
            location = job.get("location") or job.get("primary_search_label", "")
            job_path = job.get("job_path", "")
            url = f"{AMAZON_JOB_BASE}{job_path}" if job_path else ""
            parsed.append({
                "id": jid,
                "company": self.company_name,
                "title": title,
                "url": url,
                "location": location,
                "posted_date": job.get("posted_date", ""),
            })
        return parsed
