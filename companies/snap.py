"""
Snap custom scraper — careers.snap.com/api/jobs. One keyless GET returns the
full open-roles catalogue as Elasticsearch-style hits in `body[]._source`.
No per-posting detail needed; each item already carries title, offices,
primary_location, absolute_url.

Yield today is tiny (~1 India role across all Snap) but the catalogue is
cheap to pull, so running it costs ~1 request per cycle.
"""
from typing import List, Dict, Any

import requests

from scrappers.base import BaseJobScraper

SNAP_API_URL = "https://careers.snap.com/api/jobs"
SNAP_REQUEST_TIMEOUT = 20


class SnapScraper(BaseJobScraper):
    company_name = "Snap"

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
        try:
            response = requests.get(
                SNAP_API_URL, headers=headers, timeout=SNAP_REQUEST_TIMEOUT,
            )
            response.raise_for_status()
            data = response.json()
        except Exception as e:
            print(f"[Snap] fetch failed: {e}")
            return []
        return data.get("body") or []

    def parse_jobs(self, raw_jobs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        parsed: List[Dict[str, Any]] = []
        for hit in raw_jobs:
            src = (hit or {}).get("_source", {})
            jid = str(src.get("id") or hit.get("_id") or "")
            title = src.get("title", "")
            if not jid or not title:
                continue

            # offices is a list of {location: "City - Country"} dicts; join into
            # one display string so matches_filter can regex-check it.
            offices = src.get("offices") or []
            loc_parts = []
            for office in offices:
                if isinstance(office, dict):
                    loc_parts.append(office.get("location") or "")
            location = ", ".join(p for p in loc_parts if p) or src.get("primary_location", "")

            parsed.append({
                "id": jid,
                "company": self.company_name,
                "title": title,
                "url": src.get("absolute_url", ""),
                "location": location,
                "posted_date": "",
            })
        return parsed
