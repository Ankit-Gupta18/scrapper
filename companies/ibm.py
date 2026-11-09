"""
IBM custom scraper — careers.ibm.com's underlying Elasticsearch endpoint
(www-api.ibm.com/search/api/v2). careers.ibm.com itself sits behind an AWS
WAF challenge, but this search backend is public and keyless.

Ported from freehire's ibm.go. One POST per page; `_source` must enumerate
each field (requesting ["*"] returns empty). Light on CPU — pure JSON.
"""
from typing import List, Dict, Any

import requests

from scrappers.base import BaseJobScraper

IBM_SEARCH_URL = "https://www-api.ibm.com/search/api/v2"
IBM_JOB_URL_FMT = "https://careers.ibm.com/careers/JobDetail?jobId={job_id}"
IBM_PAGE_SIZE = 50
IBM_MAX_PAGES = 50          # 2500 jobs cap (IBM has ~2200 total)
IBM_REQUEST_TIMEOUT = 20

IBM_SOURCE_FIELDS = [
    "field_text_01",     # job id (integer)
    "title",             # posting title
    "dcdate",            # YYYY-MM-DD
    "field_keyword_05",  # country name
    "field_keyword_17",  # work mode: "Hybrid" / "Remote" / ""
    "field_keyword_19",  # city, e.g. "Bangalore, IN"
]


class IbmScraper(BaseJobScraper):
    company_name = "IBM"

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

    def _search_body(self, from_: int) -> Dict[str, Any]:
        return {
            "appId": "careers",
            "scopes": ["careers2"],
            "query": {"bool": {"must": []}},
            "post_filter": {"bool": {"must": []}},
            "size": IBM_PAGE_SIZE,
            "from": from_,
            "sort": [{"id": "asc"}],   # Load-bearing — see freehire's comment
            "lang": "zz",
            "localeSelector": {},
            "sm": {"query": "", "lang": "zz"},
            "_source": IBM_SOURCE_FIELDS,
        }

    def fetch_jobs(self) -> List[Dict[str, Any]]:
        headers = {
            "accept": "application/json",
            "content-type": "application/json",
            "user-agent": (
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/124.0.0.0 Safari/537.36"
            ),
        }
        collected: List[Dict[str, Any]] = []
        for page in range(IBM_MAX_PAGES):
            try:
                response = requests.post(
                    IBM_SEARCH_URL,
                    headers=headers,
                    json=self._search_body(page * IBM_PAGE_SIZE),
                    timeout=IBM_REQUEST_TIMEOUT,
                )
                response.raise_for_status()
                data = response.json()
            except Exception as e:
                print(f"[IBM] page {page} failed: {e}")
                return collected

            hits = (data.get("hits") or {}).get("hits") or []
            if not hits:
                break
            # Early exit once we've covered India jobs — client-side filter
            # on country keyword catches these before they hit matches_filter.
            for hit in hits:
                src = hit.get("_source") or {}
                country = (src.get("field_keyword_05") or "").lower()
                city = (src.get("field_keyword_19") or "").lower()
                if "india" in country or " in" in f" {city}":
                    collected.append(src)
            total = (data.get("hits", {}).get("total") or {}).get("value", 0)
            if total and (page + 1) * IBM_PAGE_SIZE >= total:
                break
        return collected

    def parse_jobs(self, raw_jobs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        parsed: List[Dict[str, Any]] = []
        for src in raw_jobs:
            jid = str(src.get("field_text_01") or "")
            title = src.get("title", "")
            if not jid or not title:
                continue
            parsed.append({
                "id": jid,
                "company": self.company_name,
                "title": title,
                "url": IBM_JOB_URL_FMT.format(job_id=jid),
                "location": src.get("field_keyword_19", ""),
                "posted_date": src.get("dcdate", ""),
            })
        return parsed
