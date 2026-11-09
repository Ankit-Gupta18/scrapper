# companies/spotdraft.py
from scrappers.darwinbox import BaseDarwinboxScraper


class SpotdraftScraper(BaseDarwinboxScraper):
    company_name = "SpotDraft"
    darwinbox_slug = "spotdraft"

    # Standardized target tech keywords
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

    # Standardized seniority/role exclusions
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

    # Standardized locations
    target_locations = [
        "india",
        "bengaluru",
        "bangalore",
        "hyderabad",
    ]