# scrappers/ti.py
from typing import List, Dict, Any
from curl_cffi import requests
from scrappers.base import BaseJobScraper


class TexasinstrumentsScraper(BaseJobScraper):
    company_name = "Texas Instruments"

    def fetch_jobs(self) -> List[Dict[str, Any]]:
        session = requests.Session(impersonate="chrome120")

        headers = {
            "accept": "*/*",
            "accept-language": "en",
            "content-type": "application/vnd.oracle.adf.resourceitem+json;charset=utf-8",
            "ora-irc-language": "en",
            "origin": "https://careers.ti.com",
            "referer": "https://careers.ti.com/",
            "sec-ch-ua": '"Not;A=Brand";v="8", "Chromium";v="150", "Google Chrome";v="150"',
            "sec-ch-ua-mobile": "?0",
            "sec-ch-ua-platform": '"macOS"',
            "sec-fetch-dest": "empty",
            "sec-fetch-mode": "cors",
            "sec-fetch-site": "cross-site",
            "user-agent": (
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/150.0.0.0 Safari/537.36"
            ),
        }

        base_endpoint = "https://edbz.fa.us2.oraclecloud.com/hcmRestApi/resources/latest/recruitingCEJobRequisitions"
        query_string = (
            "?onlyData=true"
            "&expand=requisitionList.workLocation,requisitionList.otherWorkLocations,requisitionList.secondaryLocations,flexFieldsFacet.values,requisitionList.requisitionFlexFields"
            '&finder=findReqs;siteNumber=CX,facetsList=LOCATIONS%3BWORK_LOCATIONS%3BWORKPLACE_TYPES%3BTITLES%3BCATEGORIES%3BORGANIZATIONS%3BPOSTING_DATES%3BFLEX_FIELDS,limit=25,keyword="Software Engineer",locationId=100001734561645,radius=25,radiusUnit=MI,sortBy=POSTING_DATES_DESC'
        )

        full_url = base_endpoint + query_string

        try:
            response = session.get(full_url, headers=headers, timeout=15)
            response.raise_for_status()
            res_json = response.json()
        except Exception as e:
            print(f"[{self.company_name}] Failed to fetch jobs via TI Oracle API: {e}")
            raise

        items = res_json.get("items", [])
        if not items or not isinstance(items, list):
            print(f"[{self.company_name}] No valid items found in response.")
            return []

        requisitions = items[0].get("requisitionList", [])
        raw_jobs = []

        for req in requisitions:
            if not isinstance(req, dict):
                continue

            job_id = req.get("Id") or req.get("RequisitionId")
            title = req.get("Title") or req.get("JobTitle", "")

            primary_loc = req.get("PrimaryLocation", "")
            work_loc = req.get("workLocation", {})
            loc_name = ""
            
            if isinstance(work_loc, dict):
                loc_name = work_loc.get("Name") or work_loc.get("LocationName", "")

            location = loc_name or primary_loc or "Bengaluru, Karnataka, India"

            if not job_id or not title:
                continue

            job_url = f"https://careers.ti.com/en/sites/CX/job/{job_id}"

            raw_jobs.append({
                "id": str(job_id),
                "title": str(title).strip(),
                "url": job_url,
                "location": str(location).strip(),
                "posted_date": str(req.get("PostedDate") or req.get("PostedDateSortKey", "")),
            })
        return raw_jobs

    def parse_jobs(self, raw_jobs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
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
            "RTL",
            "Architect",
            "Test",
            "System-On-Chip",
            "Validation", "hardware"
    ]

        target_locations = [
            "india",
            "bengaluru",
            "bangalore",
            "hyderabad",
        ]

        parsed_jobs = []

        for item in raw_jobs:
            title_lower = item["title"].lower()
            location_lower = item["location"].lower()

            # 1. Match at least one target keyword in title
            matches_target = any(kw in title_lower for kw in target_keywords)
            
            # 2. Must NOT match any exclude keyword in title
            matches_exclude = any(ex in title_lower for ex in exclude_keywords)

            # 3. Match at least one target location
            matches_location = any(loc in location_lower for loc in target_locations)

            # Keep position only if all 3 criteria pass
            if matches_target and not matches_exclude and matches_location:
                parsed_jobs.append({
                    "id": item["id"],
                    "company": self.company_name,
                    "title": item["title"],
                    "url": item["url"],
                    "location": item["location"],
                    "posted_date": item.get("posted_date", ""),
                })

        return parsed_jobs