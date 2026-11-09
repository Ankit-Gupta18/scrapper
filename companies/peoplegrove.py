# companies/peoplegrove.py
from typing import List, Dict, Any
# Import your project's Base Lever Scraper class
from scrappers.lever import BaseLeverScraper 


class PeoplegroveScraper(BaseLeverScraper):
    company_name = "PeopleGrove"
    lever_company_slug = "peoplegrove"  # Target endpoint: api.lever.co/v0/postings/peoplegrove

    # Target tech-only keywords
    target_keywords = [
        "software",
        "engineer",
        "developer",
        "backend",
        "python",
        "full stack",
        "java",
        "frontend",
        "data",
    ]

    # Seniority/Role Exclusions
    exclude_keywords = [
        "intern",
        "manager",
        "director",
        "vp",
        "principal",
        "lead",
        "staff",
        "vulnerability",
        "reinforcement",
        "senior",
        "integration",
        "support",
        "sr",
        "customer", "hardware"
    ]

    target_locations = [
        "india",
        "bengaluru",
        "bangalore",
        "hyderabad"
    ]