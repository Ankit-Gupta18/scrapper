"""
Ashby GraphQL adapter — for boards whose public Posting API (see ashby.py) is
disabled, so the only machine-readable source is the same embed GraphQL endpoint
Ashby's own hosted careers widget calls. Ported from freehire's
internal/ingest/sources/ashbygraphql.go.

job-scrapper only needs the list query (id/title/locationName) — detail query
is skipped since we don't render descriptions in Telegram.
"""
from typing import List, Dict, Any

import requests

from scrappers.base import BaseJobScraper

ASHBY_GQL_URL = "https://jobs.ashbyhq.com/api/non-user-graphql"
ASHBY_GQL_JOB_URL = "https://jobs.ashbyhq.com/"
ASHBY_GQL_LIST_OP = "ApiJobBoardWithTeams"
ASHBY_GQL_REQUEST_TIMEOUT = 20

ASHBY_GQL_LIST_QUERY = (
    "query ApiJobBoardWithTeams($organizationHostedJobsPageName: String!) { "
    "jobBoard: jobBoardWithTeams(organizationHostedJobsPageName: $organizationHostedJobsPageName) "
    "{ jobPostings { id title locationName employmentType } } }"
)


class BaseAshbyGraphQLScraper(BaseJobScraper):
    """Board = organization slug on jobs.ashbyhq.com (same as ashby.py's
    job_board_name). Use for tenants whose /posting-api/job-board/<slug> returns
    an empty jobs array — the GraphQL endpoint still serves their postings."""
    job_board_name: str = ""

    def fetch_jobs(self) -> List[Dict[str, Any]]:
        if not self.job_board_name:
            print(f"[{self.company_name}] Error: No job_board_name provided.")
            return []

        headers = {
            "content-type": "application/json",
            "accept": "application/json",
            "user-agent": (
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/124.0.0.0 Safari/537.36"
            ),
            "origin": "https://jobs.ashbyhq.com",
            "referer": f"https://jobs.ashbyhq.com/{self.job_board_name}",
        }
        body = {
            "operationName": ASHBY_GQL_LIST_OP,
            "variables": {"organizationHostedJobsPageName": self.job_board_name},
            "query": ASHBY_GQL_LIST_QUERY,
        }

        try:
            response = requests.post(
                f"{ASHBY_GQL_URL}?op={ASHBY_GQL_LIST_OP}",
                json=body,
                headers=headers,
                timeout=ASHBY_GQL_REQUEST_TIMEOUT,
            )
            response.raise_for_status()
            data = response.json()
        except Exception as e:
            print(f"[{self.company_name}] Ashby GraphQL fetch failed: {e}")
            return []

        return ((data.get("data") or {}).get("jobBoard") or {}).get("jobPostings") or []

    def parse_jobs(self, raw_jobs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        parsed: List[Dict[str, Any]] = []
        for p in raw_jobs:
            job_id = p.get("id")
            title = p.get("title")
            if not job_id or not title:
                continue
            parsed.append({
                "id": str(job_id),
                "company": self.company_name,
                "title": title,
                "url": f"{ASHBY_GQL_JOB_URL}{self.job_board_name}/{job_id}",
                "location": p.get("locationName", ""),
                "posted_date": "",
            })
        return parsed
