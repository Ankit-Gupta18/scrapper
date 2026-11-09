# companies/singlestore.py
from scrappers.greenhouse import BaseGreenhouseScraper


class SinglestoreScraper(BaseGreenhouseScraper):
    company_name = "SingleStore"
    greenhouse_board_token = "singlestore"

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