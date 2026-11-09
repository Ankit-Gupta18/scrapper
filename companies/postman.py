# companies/postman.py
from scrappers.greenhouse import BaseGreenhouseScraper


class PostmanScraper(BaseGreenhouseScraper):
    company_name = "Postman"
    greenhouse_board_token = "postman"

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
        "customer",
        "Enterprise",
        "Strategic", "hardware"
    ]

    # Standardized locations
    target_locations = [
        "india",
        "bengaluru",
        "bangalore",
        "hyderabad",
    ]