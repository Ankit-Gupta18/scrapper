import re
from typing import List, Dict, Any
from bs4 import BeautifulSoup
from curl_cffi import requests
from scrappers.base import BaseJobScraper


class ToastScraper(BaseJobScraper):
    company_name = "Toast"

    # Base search URL captured from network traffic
    search_url = "https://careers.toasttab.com/jobs/search"

    # Keywords evaluated by BaseJobScraper
    target_keywords = ["software", "engineer", "developer", "backend", "full stack", "java", "frontend", "data", "director"]
    exclude_keywords = ["intern", "hardware", "support"
    ]
    target_locations = ["india", "bengaluru", "bangalore", "hyderabad"]

    def fetch_jobs(self) -> List[Dict[str, Any]]:
        session = requests.Session(impersonate="chrome120")

        headers = {
            "accept": "text/vnd.turbo-stream.html, text/html, application/xhtml+xml",
            "accept-language": "en-US,en;q=0.9",
            "referer": "https://careers.toasttab.com/jobs/search",
            "user-agent": (
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/124.0.0.0 Safari/537.36"
            ),
        }

        raw_jobs = []
        page = 1

        while True:
            params = {
                "country_codes[]": "IN",
                "page": page,
                "query": "",
            }

            try:
                response = session.get(self.search_url, params=params, headers=headers, timeout=15)
                response.raise_for_status()
                html_content = response.text
            except Exception as e:
                print(f"[{self.company_name}] Request error on page {page}: {e}")
                break

            soup = BeautifulSoup(html_content, "html.parser")
            
            # Find all job links pointing to /jobs/<job-slug>
            job_anchors = soup.find_all("a", href=re.compile(r"^/jobs/"))

            if not job_anchors:
                # No more jobs on this page
                break

            page_added = 0
            for a in job_anchors:
                href = a.get("href", "")
                
                # Filter out generic navigation search links
                if href in ["/jobs/search", "/jobs/"]:
                    continue

                full_url = f"https://careers.toasttab.com{href}"
                
                # Extract unique ID from the end of the URL slug
                slug = href.replace("/jobs/", "").strip("/")
                job_id = slug.split("-")[-1] if "-" in slug else slug
                
                # Clean up title text
                title = a.get_text(strip=True)
                if not title:
                    title = slug.replace("-", " ").title()

                # Extract location from parent card container if present
                card = a.find_parent(["div", "li", "article"])
                location = "India"
                if card:
                    loc_el = card.find(class_=re.compile(r"location", re.I))
                    if loc_el:
                        location = loc_el.get_text(strip=True)

                # Avoid duplicate entries on the same page
                if not any(j["url"] == full_url for j in raw_jobs):
                    raw_jobs.append({
                        "id": job_id,
                        "title": title,
                        "url": full_url,
                        "location": location,
                        "posted_date": "",
                    })
                    page_added += 1

            if page_added == 0:
                break

            page += 1

        return raw_jobs

    def parse_jobs(self, raw_jobs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        return [
            {
                "id": item["id"],
                "company": self.company_name,
                "title": item["title"],
                "url": item["url"],
                "location": item["location"],
                "posted_date": item.get("posted_date", ""),
            }
            for item in raw_jobs
        ]