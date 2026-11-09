"""
Apple custom scraper — jobs.apple.com public search API (same POST endpoint
freehire's apple.go uses). Paginated via `page` field; filters pass as an
empty object (API rejects a body without a filters key).

Country filter is NOT applied server-side (Apple's postLocation-* enum maps
to large regions, not countries), so we fetch all pages and let the base
BaseJobScraper.matches_filter catch India via location strings.
"""
from typing import List, Dict, Any

import requests

from scrappers.base import BaseJobScraper

APPLE_SEARCH_URL = "https://jobs.apple.com/api/v1/search"
APPLE_JOB_URL_FMT = "https://jobs.apple.com/en-us/details/{position_id}/{slug}"
APPLE_PAGE_SIZE = 20  # Apple's fixed page size for this endpoint
APPLE_MAX_PAGES = 25  # 500 jobs cap — enough for an India slice; tune up if needed
APPLE_REQUEST_TIMEOUT = 20


class AppleScraper(BaseJobScraper):
    company_name = "Apple"

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

    def _search_body(self, page: int) -> Dict[str, Any]:
        """Request body mirrors what Apple's own site sends — the API 400s
        without `filters` (even empty) and without the `format` block."""
        return {
            "query": "",
            "filters": {},
            "page": page,
            "locale": "en-us",
            "sort": "newest",
            "format": {
                "longDate": "MMMM D, YYYY",
                "mediumDate": "MMM D, YYYY",
            },
        }

    def fetch_jobs(self) -> List[Dict[str, Any]]:
        headers = {
            "accept": "application/json",
            "content-type": "application/json",
            "origin": "https://jobs.apple.com",
            "referer": "https://jobs.apple.com/en-us/search?location=india",
            "user-agent": (
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/124.0.0.0 Safari/537.36"
            ),
        }

        collected: List[Dict[str, Any]] = []
        for page in range(1, APPLE_MAX_PAGES + 1):
            try:
                response = requests.post(
                    APPLE_SEARCH_URL,
                    headers=headers,
                    json=self._search_body(page),
                    timeout=APPLE_REQUEST_TIMEOUT,
                )
                response.raise_for_status()
                data = response.json()
            except Exception as e:
                print(f"[Apple] page {page} failed: {e}")
                return collected

            res = (data or {}).get("res", {})
            batch = res.get("searchResults") or []
            if not batch:
                break
            collected.extend(batch)
            total = res.get("totalRecords") or 0
            if total and len(collected) >= total:
                break

        return collected

    def parse_jobs(self, raw_jobs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        parsed: List[Dict[str, Any]] = []
        for job in raw_jobs:
            position_id = str(job.get("positionId") or job.get("id") or "")
            title = job.get("postingTitle", "")
            if not position_id or not title:
                continue

            locations = job.get("locations") or []
            loc_parts = []
            for loc in locations:
                if not isinstance(loc, dict):
                    continue
                parts = [loc.get("city"), loc.get("stateProvince"), loc.get("countryName")]
                loc_parts.append(", ".join(p for p in parts if p) or loc.get("name") or "")
            location = " / ".join(p for p in loc_parts if p)

            slug = job.get("transformedPostingTitle") or ""
            parsed.append({
                "id": position_id,
                "company": self.company_name,
                "title": title,
                "url": APPLE_JOB_URL_FMT.format(position_id=position_id, slug=slug),
                "location": location,
                "posted_date": job.get("postingDate", ""),
            })
        return parsed
