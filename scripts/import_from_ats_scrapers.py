#!/usr/bin/env python3
"""
Import ATS inventory CSVs from kalil0321/ats-scrapers (the same upstream freehire's
cmd/seed-from-inventory consumes) into database/catalog.yaml, filtered by the India
company allowlist.

Usage:
    python scripts/import_from_ats_scrapers.py [--csv-dir /tmp/ats-scrapers] [--dry-run]

CSVs are fetched on demand (greenhouse, lever, workday, ashby, workable, phenom)
unless --csv-dir points at an already-downloaded set.
"""
import argparse
import csv
import os
import sys
import urllib.parse
import urllib.request
from pathlib import Path

import yaml

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_CSV_DIR = Path("/tmp/ats-scrapers")
ALLOWLIST_PATH = PROJECT_ROOT / "database" / "india_allowlist.yaml"
CATALOG_PATH = PROJECT_ROOT / "database" / "catalog.yaml"

UPSTREAM_BASE = "https://raw.githubusercontent.com/kalil0321/ats-scrapers/main/ats-companies"
SUPPORTED_PROVIDERS = ["greenhouse", "lever", "workday", "ashby", "workable", "phenom"]


def fetch_csv(provider: str, dest: Path) -> Path:
    """Download the upstream CSV for a provider if it isn't already on disk."""
    out = dest / f"{provider}.csv"
    if out.exists() and out.stat().st_size > 0:
        return out
    dest.mkdir(parents=True, exist_ok=True)
    url = f"{UPSTREAM_BASE}/{provider}.csv"
    print(f"[fetch] {url}")
    with urllib.request.urlopen(url, timeout=30) as resp:
        out.write_bytes(resp.read())
    return out


def load_allowlist() -> set[str]:
    with ALLOWLIST_PATH.open() as f:
        data = yaml.safe_load(f) or {}
    return {s.lower().strip() for s in data.get("india_companies", []) if s.strip()}


def matches_allowlist(name: str, slug: str, allowlist: set[str]) -> bool:
    """EXACT match on either name or slug (case-folded). See india_allowlist.yaml
    for why substring matching was abandoned."""
    return name.lower().strip() in allowlist or slug.lower().strip() in allowlist


def parse_workday_url(url: str, slug: str) -> dict | None:
    """Workday: slug is `<client>/<site>`; URL carries the tenant host."""
    parsed = urllib.parse.urlparse(url)
    if "myworkdayjobs.com" not in parsed.netloc:
        return None
    parts = [p for p in slug.split("/") if p]
    if len(parts) < 2:
        return None
    return {
        "tenant_host": parsed.netloc,
        "client_slug": parts[0],
        "site_slug": parts[1],
    }


def rows_from_csv(provider: str, path: Path, allowlist: set[str]) -> list[dict]:
    """Yield catalog rows for allowlisted companies in the provider's CSV."""
    rows = []
    with path.open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for r in reader:
            name = (r.get("name") or "").strip()
            slug = (r.get("slug") or "").strip()
            url = (r.get("url") or "").strip()
            if not name or not slug:
                continue
            if not matches_allowlist(name, slug, allowlist):
                continue

            row = {
                "provider": provider,
                "company": name,
                "enabled": True,
            }
            if provider == "workday":
                wd = parse_workday_url(url, slug)
                if not wd:
                    continue
                row.update(wd)
                row["board"] = f"{wd['client_slug']}/{wd['site_slug']}"
            else:
                row["board"] = slug
            rows.append(row)
    return rows


def load_existing_catalog() -> dict:
    if not CATALOG_PATH.exists():
        return {"companies": []}
    with CATALOG_PATH.open() as f:
        return yaml.safe_load(f) or {"companies": []}


def merge(existing: dict, new_rows: list[dict]) -> dict:
    """Keep hand-set `enabled`, `filters`, and `defaults` on existing rows; add new rows."""
    index: dict[tuple[str, str], dict] = {}
    for row in existing.get("companies", []):
        key = (row["provider"], row["board"])
        index[key] = row

    added = 0
    for row in new_rows:
        key = (row["provider"], row["board"])
        if key in index:
            prior = index[key]
            prior["company"] = row["company"]
            for k in ("tenant_host", "client_slug", "site_slug"):
                if k in row:
                    prior[k] = row[k]
        else:
            index[key] = row
            added += 1

    merged_rows = sorted(index.values(), key=lambda r: (r["provider"], r["board"]))
    out: dict = {}
    if "defaults" in existing:
        out["defaults"] = existing["defaults"]
    out["companies"] = merged_rows
    out["_stats"] = {"total": len(merged_rows), "added": added}
    return out


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--csv-dir", type=Path, default=DEFAULT_CSV_DIR)
    parser.add_argument("--providers", nargs="+", default=SUPPORTED_PROVIDERS,
                        choices=SUPPORTED_PROVIDERS)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    allowlist = load_allowlist()
    print(f"[allowlist] {len(allowlist)} tokens")

    all_new_rows: list[dict] = []
    for provider in args.providers:
        csv_path = fetch_csv(provider, args.csv_dir)
        rows = rows_from_csv(provider, csv_path, allowlist)
        print(f"[{provider}] {len(rows):>4} matched (of {sum(1 for _ in csv_path.open()) - 1} total)")
        all_new_rows.extend(rows)

    existing = load_existing_catalog()
    merged = merge(existing, all_new_rows)
    stats = merged.pop("_stats")
    print(f"[catalog] {stats['total']} total rows ({stats['added']} new)")

    if args.dry_run:
        print("--- dry run, catalog not written ---")
        print(yaml.safe_dump(merged, sort_keys=False)[:1500])
        return 0

    CATALOG_PATH.write_text(yaml.safe_dump(merged, sort_keys=False))
    print(f"[write] {CATALOG_PATH}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
