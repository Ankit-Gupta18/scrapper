# companies/housing.py
import requests
from bs4 import BeautifulSoup
from typing import List, Dict, Any
from scrappers.base import BaseJobScraper

class HousingScraper(BaseJobScraper):
    company_name = "Housing.com"
    ajax_url = "https://careers.housing.com/jm-ajax/get_listings/"

    # Company-level filtering criteria
    target_keywords = ["software", "engineer", "developer", "backend", "python", "full stack"]
    exclude_keywords = [
        "intern", "manager", "director", "vp", "principal", 
        "lead", "staff", "vulnerability", "reinforcement",
        "senior", "integration", "support", "sr", "customer", "hardware"
    ]
    target_locations = ["india", "bengaluru", "bangalore", "hyderabad", "gurgaon", "mumbai", "noida"]

    def fetch_jobs(self) -> List[Dict[str, Any]]:
        headers = {
            "user-agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "accept": "application/json, text/javascript, */*; q=0.01",
            "x-requested-with": "XMLHttpRequest",
        }
        
        # Request all listings at once from the AJAX endpoint
        payload = {
            "per_page": 200,
            "show_pagination": "false",
        }

        response = requests.post(self.ajax_url, headers=headers, data=payload, timeout=15)
        response.raise_for_status()

        data = response.json()
        html_content = data.get("html", "")
        
        soup = BeautifulSoup(html_content, "html.parser")
        
        # Find all job listing container elements
        job_listings = soup.select("li.job_listing, div.job_listing, article.job_listing")
        
        # Fallback if container tags aren't wrapped strictly in li/div
        if not job_listings:
            job_listings = soup.find_all(True, class_=lambda c: c and "job_listing" in c)

        raw_jobs = []
        seen_urls = set()

        for listing in job_listings:
            # Extract main job link
            link_tag = listing.find("a", href=True)
            if not link_tag:
                continue

            job_url = link_tag["href"].split("#")[0].rstrip("/")  # Strip fragment & trailing slash
            
            if not job_url or job_url in seen_urls:
                continue
            
            seen_urls.add(job_url)

            # Title extraction: look for h3/h4 header or fallback to link text
            title_tag = listing.find(["h3", "h4", "h2"])
            if title_tag:
                title = title_tag.get_text(strip=True)
            else:
                title = link_tag.get_text(strip=True)

            # Location extraction: look for location element
            location_tag = listing.find(class_=lambda c: c and "location" in c.lower())
            location = location_tag.get_text(strip=True) if location_tag else "India"

            job_id = job_url.split("/")[-1]

            raw_jobs.append({
                "id": job_id,
                "title": title,
                "url": job_url,
                "location": location,
            })

        return raw_jobs

    def parse_jobs(self, raw_jobs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        parsed_jobs = []

        for item in raw_jobs:
            parsed_jobs.append({
                "id": item["id"],
                "company": self.company_name,
                "title": item["title"],
                "url": item["url"],
                "location": item["location"],
                "posted_date": "",
            })

        return parsed_jobs