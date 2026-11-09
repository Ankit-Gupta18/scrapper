"""
Scraper discovery. Two sources are consulted, in this order:

1. Legacy registry.json + per-company Python files (companies/<name>.py). These
   carry CUSTOM parse/fetch logic for companies whose ATS can't be modelled
   generically — e.g. akamai (direct HTML), paylocity (custom pagination),
   airbnb (India-only filter embedded in parse_jobs). Preserved unchanged for
   back-compat.

2. database/catalog.yaml. Generic per-provider rows (greenhouse, lever, ashby,
   workable, workday) imported from freehire's upstream inventory and filtered
   by database/india_allowlist.yaml. Each row instantiates the matching base
   class from scrappers/ and injects (company_name, board, filters).

A catalog row is DROPPED when its company_name already appears in a legacy
scraper — the legacy custom logic wins.
"""
import importlib
import json
import os
from pathlib import Path

import yaml

PROJECT_ROOT = Path(__file__).resolve().parent.parent
REGISTRY_PATH = PROJECT_ROOT / "database" / "registry.json"
CATALOG_PATH = PROJECT_ROOT / "database" / "catalog.yaml"


def get_legacy_scraper(company_key: str):
    """companies.<key> -> <Key>Scraper(). Returns None on import/attr failure."""
    try:
        module = importlib.import_module(f"companies.{company_key}")
        class_name = f"{company_key.capitalize()}Scraper"
        scraper_cls = getattr(module, class_name)
        return scraper_cls()
    except (ImportError, AttributeError) as e:
        print(f"Failed to load scraper for '{company_key}': {e}")
        return None


def _load_legacy_scrapers() -> list:
    """Enabled scrapers from database/registry.json + companies/*.py."""
    if not REGISTRY_PATH.exists():
        REGISTRY_PATH.parent.mkdir(parents=True, exist_ok=True)
        REGISTRY_PATH.write_text(json.dumps({"akamai": True}, indent=2))

    with REGISTRY_PATH.open() as f:
        registry = json.load(f)

    out = []
    for key, enabled in registry.items():
        if not enabled:
            continue
        scraper = get_legacy_scraper(key)
        if scraper is not None:
            out.append(scraper)
    return out


def _union(*lists) -> list:
    """Case-insensitive union preserving first-seen order. Drops empty."""
    seen, out = set(), []
    for src in lists:
        for item in src or []:
            key = item.lower().strip()
            if not key or key in seen:
                continue
            seen.add(key)
            out.append(item)
    return out


def _build_from_catalog_row(row: dict, defaults: dict):
    """Instantiate the right scrappers.<provider>.Base<Provider>Scraper and
    inject (company_name, board, filters). Returns None for an unsupported
    provider, so a catalog that holds rows this process can't handle (e.g.
    keka when the adapter isn't ported yet) prints a warning and continues.

    Filter COMPOSITION (requested behavior): a job must survive filters from
    BOTH levels at once.
      - scraper-level  = base class class-attrs (Ashby ships engineering
                         defaults; Keka ships none because every tenant is
                         India-native).
      - company-level  = catalog `defaults.filters` ∪ per-row `filters`.
    All three contribute to the instance's effective target_* lists via UNION
    (dedup, case-insensitive). include_titles / include_locations win on ANY
    match (job stays); exclude_titles blocks on ANY match. This means a per-row
    override cannot WEAKEN the base-class exclude list — a stricter floor
    always wins, which is the safer default."""
    provider = row["provider"]
    row_filters = row.get("filters", {}) or {}
    default_filters = defaults.get("filters", {}) or {}

    if provider == "greenhouse":
        from scrappers.greenhouse import BaseGreenhouseScraper
        scraper = BaseGreenhouseScraper()
        scraper.board_token = row["board"]
    elif provider == "lever":
        from scrappers.lever import BaseLeverScraper
        scraper = BaseLeverScraper()
        scraper.lever_company_id = row["board"]
    elif provider == "ashby":
        from scrappers.ashby import BaseAshbyScraper
        scraper = BaseAshbyScraper()
        scraper.job_board_name = row["board"]
    elif provider == "ashby_graphql":
        from scrappers.ashby_graphql import BaseAshbyGraphQLScraper
        scraper = BaseAshbyGraphQLScraper()
        scraper.job_board_name = row["board"]
    elif provider == "workable":
        from scrappers.workable import BaseWorkableScraper
        scraper = BaseWorkableScraper()
        scraper.company_subdomain = row["board"]
    elif provider == "workday":
        from scrappers.workday import BaseWorkdayScraper
        scraper = BaseWorkdayScraper()
        scraper.tenant_host = row["tenant_host"]
        scraper.client_slug = row["client_slug"]
        scraper.site_slug = row["site_slug"]
        scraper.applied_facets = row.get("applied_facets", {})
    elif provider == "keka":
        from scrappers.keka import BaseKekaScraper
        scraper = BaseKekaScraper()
        scraper.board = row["board"]
    elif provider == "darwinbox":
        from scrappers.darwinbox import BaseDarwinboxScraper
        scraper = BaseDarwinboxScraper()
        scraper.darwinbox_slug = row["board"]
    elif provider == "freshteam":
        from scrappers.freshteam import BaseFreshteamScraper
        scraper = BaseFreshteamScraper()
        scraper.freshteam_domain = row["board"]
    elif provider == "phenom":
        from scrappers.phenom import BasePhenomScraper
        scraper = BasePhenomScraper()
        scraper.company_domain = row["board"]
    else:
        return None

    scraper.company_name = row["company"]
    cls = type(scraper)
    # Union: scraper-level (class attrs) ∪ catalog defaults ∪ row-level override.
    scraper.target_locations = _union(
        getattr(cls, "target_locations", []),
        default_filters.get("include_locations", []),
        row_filters.get("include_locations", []),
    )
    scraper.target_keywords = _union(
        getattr(cls, "target_keywords", []),
        default_filters.get("include_titles", []),
        row_filters.get("include_titles", []),
    )
    scraper.exclude_keywords = _union(
        getattr(cls, "exclude_keywords", []),
        default_filters.get("exclude_titles", []),
        row_filters.get("exclude_titles", []),
    )
    return scraper


def _load_catalog_scrapers(skip_names: set[str]) -> list:
    """Enabled scrapers from database/catalog.yaml, excluding any whose
    company name matches a legacy scraper already loaded."""
    if not CATALOG_PATH.exists():
        return []
    with CATALOG_PATH.open() as f:
        data = yaml.safe_load(f) or {}

    defaults = data.get("defaults", {})
    out = []
    for row in data.get("companies", []):
        if not row.get("enabled", False):
            continue
        if row["company"].lower().strip() in skip_names:
            continue
        scraper = _build_from_catalog_row(row, defaults)
        if scraper is None:
            print(f"[catalog] unsupported provider '{row['provider']}' for {row['company']}, skipped")
            continue
        out.append(scraper)
    return out


def get_active_scrapers():
    """All enabled scrapers from both sources. Legacy wins on name collision."""
    legacy = _load_legacy_scrapers()
    legacy_names = {s.company_name.lower().strip() for s in legacy}
    catalog = _load_catalog_scrapers(skip_names=legacy_names)
    return legacy + catalog
