# companies/mongodb.py
from scrappers.greenhouse import BaseGreenhouseScraper


class MongodbScraper(BaseGreenhouseScraper):
    company_name = "MongoDB"
    board_token = "mongodb"  
    
    target_keywords = [
        "software",
        "engineer",
        "developer",
        "backend",
        "python",
        "full stack",
        "go",
        "golang",
        "c++",
        "database",
        "systems",
        "distributed",
        "platform",
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
        "service",
        "customer",
        "account",
        "sales", "hardware"
    ]

    # Target Locations
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