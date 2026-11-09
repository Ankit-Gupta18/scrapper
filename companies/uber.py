"""
Uber custom scraper — jobs.uber.com flat sitemap + per-posting HTML detail.
Uber has no lightweight JSON search; the only path is the sitemap (733 URLs
today). Each detail page carries a schema.org JobPosting ld+json block.

To bound CPU/RAM cost (user runs on Oracle free tier, 1 CPU / 1GB RAM), the
sitemap is filtered to postings with lastmod in the last UBER_RECENT_DAYS so
each cycle only hits new/updated roles — typically ~50 URLs. Older rows are
already in SQLite from previous cycles.
"""
import json
import re
from datetime import datetime, timedelta, timezone
from typing import List, Dict, Any

from curl_cffi import requests as cfr

from scrappers.base import BaseJobScraper

UBER_SITEMAP_URL = "https://jobs.uber.com/en/jobs/sitemap.xml"
UBER_RECENT_DAYS = 30         # only fetch detail for postings modified ≤ this
UBER_MAX_DETAIL_FETCHES = 100  # safety cap even within the window
UBER_REQUEST_TIMEOUT = 20

SITEMAP_URL_RE = re.compile(
    r"<url>\s*<loc>([^<]+)</loc>\s*<lastmod>([^<]+)</lastmod>",
    re.DOTALL,
)
LDJSON_RE = re.compile(
    r'<script type="application/ld\+json"[^>]*>(.*?)</script>',
    re.DOTALL,
)


class UberScraper(BaseJobScraper):
    company_name = "Uber"

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

    def _session(self):
        """Chrome fingerprint — Uber's edge Cloudflare-challenges plain Python."""
        return cfr.Session(impersonate="chrome120")

    def _recent_urls(self, session) -> List[tuple[str, str]]:
        """Pull sitemap, keep only entries whose lastmod is within the window."""
        try:
            response = session.get(UBER_SITEMAP_URL, timeout=UBER_REQUEST_TIMEOUT)
            response.raise_for_status()
        except Exception as e:
            print(f"[Uber] sitemap failed: {e}")
            return []

        cutoff = datetime.now(timezone.utc) - timedelta(days=UBER_RECENT_DAYS)
        recent: List[tuple[str, str]] = []
        for loc, lastmod in SITEMAP_URL_RE.findall(response.text):
            try:
                ts = datetime.fromisoformat(lastmod.replace("Z", "+00:00"))
            except ValueError:
                continue
            if ts >= cutoff:
                recent.append((loc, lastmod))
        recent.sort(key=lambda x: x[1], reverse=True)
        return recent[:UBER_MAX_DETAIL_FETCHES]

    def fetch_jobs(self) -> List[Dict[str, Any]]:
        session = self._session()
        urls = self._recent_urls(session)
        if not urls:
            return []

        collected: List[Dict[str, Any]] = []
        for url, lastmod in urls:
            try:
                r = session.get(url, timeout=UBER_REQUEST_TIMEOUT)
                if r.status_code != 200:
                    continue
                html = r.text
            except Exception:
                continue

            posting = None
            for match in LDJSON_RE.finditer(html):
                try:
                    doc = json.loads(match.group(1))
                except json.JSONDecodeError:
                    continue
                if isinstance(doc, dict) and doc.get("@type") == "JobPosting":
                    posting = doc
                    break
            if not posting:
                continue
            posting["_source_url"] = url
            posting["_lastmod"] = lastmod
            collected.append(posting)
        return collected

    def parse_jobs(self, raw_jobs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        parsed: List[Dict[str, Any]] = []
        for job in raw_jobs:
            identifier = job.get("identifier") or {}
            jid = str(identifier.get("value") if isinstance(identifier, dict) else "")
            title = job.get("title", "")
            if not jid or not title:
                continue

            location_strs = []
            jl = job.get("jobLocation")
            if isinstance(jl, dict):
                jl = [jl]
            for entry in jl or []:
                addr = (entry or {}).get("address") or {}
                parts = [addr.get("addressLocality"), addr.get("addressRegion"), addr.get("addressCountry")]
                location_strs.append(", ".join(p for p in parts if p))
            location = " / ".join(filter(None, location_strs))

            parsed.append({
                "id": jid,
                "company": self.company_name,
                "title": title,
                "url": job.get("_source_url", ""),
                "location": location,
                "posted_date": job.get("datePosted", "") or job.get("_lastmod", ""),
            })
        return parsed
