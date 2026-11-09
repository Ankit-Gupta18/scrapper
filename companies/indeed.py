# companies/indeed.py
from scrappers.indeed import BaseIndeedScraper


class IndeedScraper(BaseIndeedScraper):
    company_name = "Indeed"
    company_slug = "Indeed"  # Matches https://in.indeed.com/cmp/Indeed/jobs

    # Target tech-only keywords
    target_keywords = [
        "software",
        "engineer",
        "developer",
        "backend",
        "python",
        "full stack",
    ]

    # Exclude non-tech or management roles
    exclude_keywords = [
        "intern",
        "manager",
        "director",
        "vp",
        "principal",
        "lead",
        "staff",
        "vulnerablility",
        "reinforcement",
        "senior",
        "integration",
        "support",
        "sr",
        "customer",
        "Site Reliability", "hardware"
    ]

    target_locations = [
        "india",
        "bengaluru",
        "bangalore",
        "hyderabad",
        "gurgaon",
        "mumbai",
        "noida",
    ]