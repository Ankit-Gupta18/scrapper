import uuid
import requests
from typing import List, Dict, Any
from scrappers.base import BaseJobScraper
from config import Config

class AkamaiScraper(BaseJobScraper):
    company_name = "Akamai"
    
    # Company-Level Filtering Rules
    target_keywords = ["software engineer", "software developer"]
    exclude_keywords = ["intern", "contractor", "principal", "director", "manager", "reliability", "lead", "senior", "cloud", "staff", "hardware", "support"
    ]
    target_locations = ["india", "bengaluru", "bangalore"]

    # Oracle Cloud Endpoints
    BASE_API_URL = "https://fa-extu-saasfaprod1.fa.ocs.oraclecloud.com/hcmRestApi/resources/latest/recruitingCEJobRequisitions"
    JOB_BASE_URL = "https://jobs.akamai.com/en/sites/CX_1/job"

    def fetch_jobs(self) -> List[Dict[str, Any]]:
        """Queries Akamai's Oracle Cloud REST API for active job requisitions."""
        all_requisitions = []
        offset = 0
        limit = 25

        headers = {
            **getattr(Config, "DEFAULT_HEADERS", {}),
            "accept": "*/*",
            "accept-language": "en",
            "content-type": "application/vnd.oracle.adf.resourceitem+json;charset=utf-8",
            "ora-irc-cx-userid": str(uuid.uuid4()),
            "ora-irc-language": "en",
            "origin": "https://jobs.akamai.com",
            "referer": "https://jobs.akamai.com/",
        }

        while True:
            finder_param = (
                f"findReqs;"
                f"siteNumber=CX_1,"
                f"facetsList=LOCATIONS%3BWORK_LOCATIONS%3BWORKPLACE_TYPES%3BTITLES%3BCATEGORIES%3BORGANIZATIONS%3BPOSTING_DATES%3BFLEX_FIELDS,"
                f"limit={limit},"
                f"offset={offset},"
                f"sortBy=POSTING_DATES_DESC"
            )

            params = {
                "onlyData": "true",
                "expand": "requisitionList.workLocation,requisitionList.otherWorkLocations,requisitionList.secondaryLocations,flexFieldsFacet.values,requisitionList.requisitionFlexFields",
                "finder": finder_param
            }

            response = requests.get(
                self.BASE_API_URL, 
                params=params, 
                headers=headers, 
                timeout=getattr(Config, "DEFAULT_TIMEOUT", 30)
            )
            response.raise_for_status()
            data = response.json()

            items = data.get("items", [])
            if not items:
                break

            requisitions = items[0].get("requisitionList", [])
            if not requisitions:
                break

            all_requisitions.extend(requisitions)

            total_count = items[0].get("TotalJobsCount", 0)
            if len(all_requisitions) >= total_count:
                break

            offset += limit

        return all_requisitions

    def parse_jobs(self, raw_data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Transforms raw Oracle API response payloads into standardized job dictionaries."""
        jobs = []
        for req in raw_data:
            job_id = str(req.get("Id"))
            title = req.get("Title", "Untitled Role")
            
            # Safely handle workLocation list or fall back to PrimaryLocation
            location_str = req.get("PrimaryLocation", "Unspecified")
            work_locations = req.get("workLocation")
            
            if isinstance(work_locations, list) and len(work_locations) > 0:
                first_loc = work_locations[0]
                city = first_loc.get("TownOrCity")
                country = first_loc.get("Country")
                if city and country:
                    location_str = f"{city}, {country}"
                elif city or country:
                    location_str = city or country

            # Append WorkplaceType (e.g. Remote) if present
            workplace_type = req.get("WorkplaceType")
            if workplace_type and workplace_type.lower() not in location_str.lower():
                location_str = f"{location_str} ({workplace_type})"

            jobs.append({
                "id": job_id,
                "title": title,
                "location": location_str,
                "url": f"{self.JOB_BASE_URL}/{job_id}",
                "company": self.company_name
            })
            
        return jobs