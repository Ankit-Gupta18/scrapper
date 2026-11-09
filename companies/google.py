"""
Google custom scraper — careers.google.com's own results page.
The old JSON careers API is gone; the SPA now embeds the page's job payload
in an `AF_initDataCallback({key:'ds:1', ..., data:[...]})` script block.
Mirrors freehire's google.go regex extraction.

Each record in the ds:1 array has a known positional shape (decoded from live
pages 2026-10-27):
  [0]  = job id (string)
  [1]  = title
  [2]  = application URL
  [7]  = company name ("Google" / "YouTube" / "DeepMind")
  [9]  = location array; location string at `[9][0][0]`
"""
import json
import re
from typing import List, Dict, Any

import requests

from scrappers.base import BaseJobScraper

GOOGLE_LIST_URL = "https://www.google.com/about/careers/applications/jobs/results"
GOOGLE_JOB_URL_FMT = "https://www.google.com/about/careers/applications/jobs/results/{job_id}"
GOOGLE_MAX_PAGES = 15  # safety ceiling
GOOGLE_REQUEST_TIMEOUT = 20

# Capture the data array of the ds:1 AF_initDataCallback — see freehire's
# googleDS1Data regex. Lazy match stops at the ", sideChannel" marker.
DS1_RE = re.compile(
    r"AF_initDataCallback\(\{key: 'ds:1', hash: '[^']+', data:(?P<arr>\[.*?\]), sideChannel",
    re.DOTALL,
)


class GoogleScraper(BaseJobScraper):
    company_name = "Google"

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
            "accept": "text/html,application/xhtml+xml",
            "user-agent": (
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/124.0.0.0 Safari/537.36"
            ),
        }
        collected: List[list] = []
        for page in range(1, GOOGLE_MAX_PAGES + 1):
            params = {
                "location": "India",
                "target_level": "MID,EARLY",
                "page": page,
            }
            try:
                response = requests.get(
                    GOOGLE_LIST_URL,
                    headers=headers,
                    params=params,
                    timeout=GOOGLE_REQUEST_TIMEOUT,
                )
                response.raise_for_status()
            except Exception as e:
                print(f"[Google] page {page} failed: {e}")
                return collected

            match = DS1_RE.search(response.text)
            if not match:
                print(f"[Google] page {page}: ds:1 script not found")
                break
            try:
                outer = json.loads(match.group("arr"))
            except json.JSONDecodeError as e:
                print(f"[Google] page {page}: ds:1 JSON decode failed: {e}")
                break

            records = outer[0] if outer and isinstance(outer[0], list) else []
            if not records:
                break
            collected.extend(records)
            # outer[3] is the catalogue total hint; stop once we've seen it all
            total = outer[3] if len(outer) > 3 and isinstance(outer[3], int) else 0
            if total and len(collected) >= total:
                break
        return collected

    def parse_jobs(self, raw_jobs: List[Any]) -> List[Dict[str, Any]]:
        parsed: List[Dict[str, Any]] = []
        for rec in raw_jobs:
            if not isinstance(rec, list) or len(rec) < 10:
                continue
            jid = str(rec[0]) if rec[0] else ""
            title = rec[1] if isinstance(rec[1], str) else ""
            if not jid or not title:
                continue

            # location: rec[9] = [[["City, State, Country", "..."], ...], ...]
            location = ""
            loc_block = rec[9]
            if isinstance(loc_block, list) and loc_block:
                first = loc_block[0]
                if isinstance(first, list) and first:
                    location = first[0] if isinstance(first[0], str) else ""

            # Prefer the Google-careers canonical URL (slug-agnostic — id resolves)
            # over the login-wrapped apply URL at rec[2].
            parsed.append({
                "id": jid,
                "company": self.company_name,
                "title": title,
                "url": GOOGLE_JOB_URL_FMT.format(job_id=jid),
                "location": location,
                "posted_date": "",
            })
        return parsed
