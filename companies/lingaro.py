# companies/lingaro.py
from scrappers.lever import BaseLeverScraper


class LingaroScraper(BaseLeverScraper):
    company_name = "Lingaro Group"
    lever_company_id = "lingarogroup"  # Matches https://jobs.lever.co/lingarogroup

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
        "hyderabad",
        "gurgaon",
        "mumbai",
        "noida",
    ]