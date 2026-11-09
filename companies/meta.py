"""
Meta custom scraper — metacareers.com flat sitemap + per-posting HTML detail.
Meta's edge requires a Chrome TLS fingerprint; a plain Python request is
refused. No lightweight JSON search endpoint exists.

Cost control (user on Oracle free tier): a HARD CAP of META_MAX_DETAIL_FETCHES
bounds the per-cycle work. We sort URLs by lastmod descending so each cycle
sees the newest postings first; older ones are already in SQLite from prior
cycles.
"""
import json
import re
from typing import List, Dict, Any

from curl_cffi import requests as cfr

from scrappers.base import BaseJobScraper

META_SITEMAP_URL = "https://www.metacareers.com/jobsearch/sitemap.xml"
META_JOB_ID_RE = re.compile(r"/job_details/(\d+)/?")
META_MAX_DETAIL_FETCHES = 120   # ~120 HTTP + HTML parses per cycle
META_REQUEST_TIMEOUT = 20

SITEMAP_URL_RE = re.compile(
    r"<url>\s*<loc>([^<]+)</loc>\s*<lastmod>([^<]+)</lastmod>",
    re.DOTALL,
)
LDJSON_RE = re.compile(
    r'<script type="application/ld\+json"[^>]*>(.*?)</script>',
    re.DOTALL,
)


class MetaScraper(BaseJobScraper):
    company_name = "Meta"

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
        return cfr.Session(impersonate="chrome120")

    def _sitemap_urls(self, session) -> List[tuple[str, str]]:
        try:
            response = session.get(META_SITEMAP_URL, timeout=META_REQUEST_TIMEOUT)
            response.raise_for_status()
        except Exception as e:
            print(f"[Meta] sitemap failed: {e}")
            return []
        pairs = SITEMAP_URL_RE.findall(response.text)
        pairs.sort(key=lambda x: x[1], reverse=True)
        return pairs[:META_MAX_DETAIL_FETCHES]

    def fetch_jobs(self) -> List[Dict[str, Any]]:
        session = self._session()
        urls = self._sitemap_urls(session)
        collected: List[Dict[str, Any]] = []
        for loc, lastmod in urls:
            try:
                r = session.get(loc, timeout=META_REQUEST_TIMEOUT)
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
            # Meta's ld+json address subobject is unreliable (freehire's note).
            # Use jobLocation[].name instead; derive id from the URL.
            m = META_JOB_ID_RE.search(loc)
            jid = m.group(1) if m else ""
            if not jid:
                continue
            posting["_id"] = jid
            posting["_url"] = loc
            posting["_lastmod"] = lastmod
            collected.append(posting)
        return collected

    def parse_jobs(self, raw_jobs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        parsed: List[Dict[str, Any]] = []
        for job in raw_jobs:
            jid = str(job.get("_id") or "")
            title = job.get("title", "")
            if not jid or not title:
                continue
            jl = job.get("jobLocation")
            if isinstance(jl, dict):
                jl = [jl]
            names = [(entry or {}).get("name") or "" for entry in (jl or [])]
            location = " / ".join(n for n in names if n)
            parsed.append({
                "id": jid,
                "company": self.company_name,
                "title": title,
                "url": job.get("_url", ""),
                "location": location,
                "posted_date": job.get("datePosted", "") or job.get("_lastmod", ""),
            })
        return parsed
