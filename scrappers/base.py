from abc import ABC, abstractmethod
from typing import List, Dict, Any

# Non-India geography markers found in location strings. When a "remote" posting
# names any of these it is NOT eligible even if "remote" is in target_locations —
# "Remote, Canada" and "Remote, Americas" are the common leaks.
NON_INDIA_LOCATION_HINTS = (
    "united states", "usa", " u.s.", " u.s ", "canada", "mexico", "brazil",
    "argentina", "chile", "colombia", "peru",
    "united kingdom", " u.k.", " uk,", " uk ", "britain", "england", "scotland",
    "wales", "ireland",
    "germany", "france", "spain", "portugal", "italy", "netherlands", "belgium",
    "switzerland", "austria", "poland", "czechia", "sweden", "norway", "denmark",
    "finland", "greece", "romania", "ukraine",
    "australia", "new zealand",
    "japan", "singapore", "philippines", "vietnam", "indonesia", "thailand",
    "malaysia", "china", "hong kong", "taiwan", "korea",
    "uae", "dubai", "israel", "saudi", "egypt", "south africa", "nigeria",
    "americas", "emea", "apac", "latam", "europe", "north america",
    "worldwide",
)

INDIA_SIGNAL_TOKENS = (
    "india", "bengaluru", "bangalore", "mumbai", "hyderabad",
    "pune", "delhi", "gurgaon", "gurugram", "noida", "chennai",
    "kolkata", "ahmedabad", "jaipur",
)


class BaseJobScraper(ABC):
    """Base scraper. Filter composition at runtime:

    Each concrete instance ends up with THREE sources of filter tokens unioned
    into target_keywords / exclude_keywords / target_locations:

      1. Scraper-level  — the base class's class attrs (e.g. BaseAshbyScraper
                          ships engineering defaults). Platform-wide floor.
      2. Catalog-level  — database/catalog.yaml `defaults.filters`.
      3. Row-level      — the individual catalog row's `filters` override.

    `companies/__init__.py:_build_from_catalog_row` performs the union
    (dedup, case-insensitive, order preserved). matches_filter then evaluates
    the composed instance attrs:
       - include_titles / include_locations: ANY match passes (OR)
       - exclude_titles: ANY match blocks (OR) — so a stricter floor from
         either the base class or the catalog cannot be weakened by a row.
    Legacy companies/<name>.py scrapers override class attrs directly and skip
    the catalog path; they already carry the combined effect in one place."""
    company_name: str = "Unknown"
    base_url: str = ""

    # Neutral defaults: Neutral empty lists so the child company defines its own rules
    target_keywords: List[str] = []
    exclude_keywords: List[str] = []
    target_locations: List[str] = []

    @abstractmethod
    def fetch_jobs(self) -> Any:
        pass

    @abstractmethod
    def parse_jobs(self, raw_data: Any) -> List[Dict[str, Any]]:
        pass

    def matches_filter(self, job: Dict[str, Any]) -> bool:
        """Standard filter evaluation against company-specific criteria."""
        title = job.get("title", "").lower()
        location = job.get("location", "").lower()

        # 1. Exclude unwanted roles
        if self.exclude_keywords and any(neg.lower() in title for neg in self.exclude_keywords):
            return False

        # 2. Check required title keywords (if any defined)
        if self.target_keywords and not any(kw.lower() in title for kw in self.target_keywords):
            return False

        # 3. Location check. India tokens are an outright pass; "remote" is
        #    gated — it only passes when the posting does NOT also name a
        #    non-India geography (which would make it an Americas/EMEA
        #    remote role, not an India one).
        if self.target_locations:
            targets_lower = [t.lower() for t in self.target_locations]
            india_targets = [t for t in targets_lower if t != "remote"]
            if any(t in location for t in india_targets):
                return True
            if "remote" in targets_lower and "remote" in location:
                if not any(hint in location for hint in NON_INDIA_LOCATION_HINTS):
                    return True
            return False

        return True

    def filter_jobs(self, jobs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Filters the parsed jobs list using the company's filter rules."""
        return [job for job in jobs if self.matches_filter(job)]

    def scrape(self) -> List[Dict[str, Any]]:
        """Orchestrates fetch -> parse -> filter."""
        raw_data = self.fetch_jobs()
        parsed_jobs = self.parse_jobs(raw_data)
        filtered_jobs = self.filter_jobs(parsed_jobs)
        print(f"[{self.company_name}] Scraped {len(parsed_jobs)} jobs, {len(filtered_jobs)} matched filters.")
        return filtered_jobs