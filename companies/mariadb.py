# companies/mariadb.py
from scrappers.greenhouse import BaseGreenhouseScraper


class MariadbScraper(BaseGreenhouseScraper):
    company_name = "MariaDB"
    board_token = "mariadbplc"  # Correct token for MariaDB

    target_keywords = [
        "software",
        "engineer",
        "developer",
        "backend",
        "python",
        "full stack",
        "c++",
        "database",
        "qa",
        "devops",
    ]

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
        "account",
        "sales",
        "QA",
        "cloud", "hardware"
    ]

    target_locations = [
        "india",
        "bengaluru",
        "bangalore",
        "hyderabad",
        "gurgaon",
        "mumbai",
        "noida",
        "pune",
    ]