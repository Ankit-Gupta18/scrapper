# companies/porch.py
from scrappers.workday import BaseWorkdayScraper


class PorchScraper(BaseWorkdayScraper):
    company_name = "Porch"
    
    # Required attributes for BaseWorkdayScraper
    tenant_host = "porch.wd1.myworkdayjobs.com"
    client_slug = "porch"
    site_slug = "careers"
    
    # Server-side Workday facet filtering for India
    applied_facets = {
        "locationCountry": ["c4f78be1a8f14da0ab49ce1162348a5e"]
    }

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
        "system",
        "crm", "hardware"
    ]

    # Standardized locations
    target_locations = [
        "india",
        "bengaluru",
        "bangalore",
        "hyderabad",
    ]