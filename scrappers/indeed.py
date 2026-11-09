# # scrappers/indeed.py
# import json
# import re
# from typing import List, Dict, Any
# from bs4 import BeautifulSoup
# from playwright.sync_api import sync_playwright
# from scrappers.base import BaseJobScraper


# class BaseIndeedScraper(BaseJobScraper):
#     company_slug: str = ""  # e.g., "Indeed"

#     @property
#     def api_url(self) -> str:
#         return f"https://in.indeed.com/cmp/{self.company_slug}/jobs"

#     def fetch_jobs(self) -> List[Dict[str, Any]]:
#         html_content = ""

#         with sync_playwright() as p:
#             # Launch Chromium with resource-saving flags
#             browser = p.chromium.launch(
#                 headless=True,
#                 args=[
#                     "--disable-gpu",
#                     "--disable-dev-shm-usage",  # Prevents shared memory buffer leaks
#                     "--no-sandbox",
#                     "--disable-setuid-sandbox",
#                     "--disable-extensions",
#                 ],
#             )
            
#             try:
#                 context = browser.new_context(
#                     user_agent=(
#                         "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
#                         "AppleWebKit/537.36 (KHTML, like Gecko) "
#                         "Chrome/120.0.0.0 Safari/537.36"
#                     ),
#                     viewport={"width": 1280, "height": 800},
#                     locale="en-US",
#                 )
#                 page = context.new_page()

#                 # Navigate to company jobs page
#                 response = page.goto(
#                     self.api_url, wait_until="domcontentloaded", timeout=20000
#                 )

#                 if response and response.status in [403, 503]:
#                     print(
#                         f"[{self.company_name}] Playwright hit Cloudflare block (HTTP {response.status})."
#                     )
#                     return []

#                 # Wait briefly for dynamic jobs list to mount
#                 page.wait_for_timeout(3000)
#                 html_content = page.content()

#             except Exception as e:
#                 print(f"[{self.company_name}] Playwright fetching failed: {e}")
#                 return []
            
#             finally:
#                 # GUARANTEED CLEANUP: Always closes the browser instance, even if exceptions occur
#                 browser.close()

#         if not html_content:
#             return []

#         soup = BeautifulSoup(html_content, "html.parser")

#         # Strategy 1: Embedded window._initialData JSON
#         embedded_jobs = self._extract_from_embedded_json(soup)
#         if embedded_jobs:
#             return embedded_jobs

#         # Strategy 2: Fallback DOM Extraction
#         return self._extract_from_html(soup)

#     def _extract_from_embedded_json(
#         self, soup: BeautifulSoup
#     ) -> List[Dict[str, Any]]:
#         raw_jobs = []
#         for script in soup.find_all("script"):
#             script_text = script.string or ""
#             if "window._initialData" in script_text or "jobData" in script_text:
#                 try:
#                     match = re.search(
#                         r"window\._initialData\s*=\s*(\{.*?\});",
#                         script_text,
#                         re.DOTALL,
#                     )
#                     if match:
#                         data = json.loads(match.group(1))
#                         job_keys = data.get("jobList", {}).get(
#                             "jobs", []
#                         ) or data.get("jobs", [])

#                         for item in job_keys:
#                             job_id = str(
#                                 item.get("jobKey") or item.get("id") or ""
#                             )
#                             title = item.get("title", "")
#                             location = item.get("location", "India")
#                             job_url = (
#                                 f"https://in.indeed.com/viewjob?jk={job_id}"
#                                 if job_id
#                                 else ""
#                             )

#                             if title and job_url:
#                                 raw_jobs.append(
#                                     {
#                                         "id": job_id,
#                                         "title": title,
#                                         "url": job_url,
#                                         "location": location,
#                                     }
#                                 )
#                 except Exception:
#                     continue

#         return raw_jobs

#     def _extract_from_html(self, soup: BeautifulSoup) -> List[Dict[str, Any]]:
#         raw_jobs = []
#         seen_urls = set()

#         job_links = soup.select(
#             "a[href*='/rc/clk'], a[href*='/viewjob'], a[data-mobtk], a[href*='/job/']"
#         )

#         for link in job_links:
#             title = link.get_text(strip=True)
#             href = link.get("href", "")

#             if not href or not title:
#                 continue

#             full_url = (
#                 f"https://in.indeed.com{href}"
#                 if href.startswith("/")
#                 else href
#             )

#             if "jk=" in full_url:
#                 job_id = full_url.split("jk=")[-1].split("&")[0]
#                 clean_url = f"https://in.indeed.com/viewjob?jk={job_id}"
#             else:
#                 job_id = full_url.rstrip("/").split("/")[-1]
#                 clean_url = full_url

#             if clean_url in seen_urls:
#                 continue

#             seen_urls.add(clean_url)

#             raw_jobs.append(
#                 {
#                     "id": job_id,
#                     "title": title,
#                     "url": clean_url,
#                     "location": "India",
#                 }
#             )

#         return raw_jobs

#     def parse_jobs(self, raw_jobs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
#         parsed_jobs = []
#         for item in raw_jobs:
#             parsed_jobs.append(
#                 {
#                     "id": item["id"],
#                     "company": self.company_name,
#                     "title": item["title"],
#                     "url": item["url"],
#                     "location": item["location"],
#                     "posted_date": "",
#                 }
#             )
#         return parsed_jobs





import json
import re
from typing import List, Dict, Any
from bs4 import BeautifulSoup
from curl_cffi import requests
from scrappers.base import BaseJobScraper


class BaseIndeedScraper(BaseJobScraper):
    company_slug: str = ""  # e.g., "Indeed"

    @property
    def api_url(self) -> str:
        return f"https://in.indeed.com/cmp/{self.company_slug}/jobs"

    def fetch_jobs(self) -> List[Dict[str, Any]]:
        html_content = ""

        # Initialize a curl_cffi session with Chrome TLS fingerprinting
        session = requests.Session(impersonate="chrome")
        session.headers.update({
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/124.0.0.0 Safari/537.36"
            ),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
            "Accept-Encoding": "gzip, deflate, br",
            "Sec-Ch-Ua": '"Chromium";v="124", "Google Chrome";v="124", "Not-A.Brand";v="99"',
            "Sec-Ch-Ua-Mobile": "?0",
            "Sec-Ch-Ua-Platform": '"Windows"',
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "none",
            "Sec-Fetch-User": "?1",
            "Upgrade-Insecure-Requests": "1",
        })

        try:
            # 1. Warm up session cookies by touching the root domain
            session.get("https://in.indeed.com", timeout=10)

            # 2. Fetch the company jobs page
            response = session.get(self.api_url, timeout=15)

            if response.status_code == 200:
                html_content = response.text
            elif response.status_code in [403, 503]:
                print(f"[{self.company_name}] HTML endpoint hit Cloudflare (HTTP {response.status_code}). Attempting RSS fallback...")
                
                # 3. Fallback: Query Indeed RSS endpoint (rarely blocked by Cloudflare)
                rss_url = f"https://in.indeed.com/rss?q={self.company_name}"
                rss_response = session.get(rss_url, timeout=15)
                
                if rss_response.status_code == 200:
                    html_content = rss_response.text
                else:
                    print(f"[{self.company_name}] RSS fallback failed (HTTP {rss_response.status_code}).")
                    return []
            else:
                print(f"[{self.company_name}] Failed with HTTP {response.status_code}")
                return []

        except Exception as e:
            print(f"[{self.company_name}] curl_cffi fetching failed: {e}")
            return []

        if not html_content:
            return []

        soup = BeautifulSoup(html_content, "html.parser")

        # Strategy 1: Embedded window._initialData JSON
        embedded_jobs = self._extract_from_embedded_json(soup)
        if embedded_jobs:
            return embedded_jobs

        # Strategy 2: Fallback DOM Extraction (Handles HTML & RSS XML items)
        return self._extract_from_html(soup)

    def _extract_from_embedded_json(
        self, soup: BeautifulSoup
    ) -> List[Dict[str, Any]]:
        raw_jobs = []
        for script in soup.find_all("script"):
            script_text = script.string or ""
            if "window._initialData" in script_text or "jobData" in script_text:
                try:
                    match = re.search(
                        r"window\._initialData\s*=\s*(\{.*?\});",
                        script_text,
                        re.DOTALL,
                    )
                    if match:
                        data = json.loads(match.group(1))
                        job_keys = data.get("jobList", {}).get(
                            "jobs", []
                        ) or data.get("jobs", [])

                        for item in job_keys:
                            job_id = str(
                                item.get("jobKey") or item.get("id") or ""
                            )
                            title = item.get("title", "")
                            location = item.get("location", "India")
                            job_url = (
                                f"https://in.indeed.com/viewjob?jk={job_id}"
                                if job_id
                                else ""
                            )

                            if title and job_url:
                                raw_jobs.append(
                                    {
                                        "id": job_id,
                                        "title": title,
                                        "url": job_url,
                                        "location": location,
                                    }
                                )
                except Exception:
                    continue

        return raw_jobs

    def _extract_from_html(self, soup: BeautifulSoup) -> List[Dict[str, Any]]:
        raw_jobs = []
        seen_urls = set()

        # Handles both standard HTML links and RSS <item> tags
        job_links = soup.select(
            "a[href*='/rc/clk'], a[href*='/viewjob'], a[data-mobtk], a[href*='/job/'], item"
        )

        for link in job_links:
            # RSS feed support
            if link.name == "item":
                title_elem = link.find("title")
                link_elem = link.find("link")
                guid_elem = link.find("guid")

                if title_elem and link_elem:
                    title = title_elem.get_text(strip=True)
                    clean_url = link_elem.get_text(strip=True)
                    job_id = guid_elem.get_text(strip=True) if guid_elem else clean_url
                    
                    if clean_url not in seen_urls:
                        seen_urls.add(clean_url)
                        raw_jobs.append({
                            "id": job_id,
                            "title": title,
                            "url": clean_url,
                            "location": "India",
                        })
                continue

            # Standard HTML link parsing
            title = link.get_text(strip=True)
            href = link.get("href", "")

            if not href or not title:
                continue

            full_url = (
                f"https://in.indeed.com{href}"
                if href.startswith("/")
                else href
            )

            if "jk=" in full_url:
                job_id = full_url.split("jk=")[-1].split("&")[0]
                clean_url = f"https://in.indeed.com/viewjob?jk={job_id}"
            else:
                job_id = full_url.rstrip("/").split("/")[-1]
                clean_url = full_url

            if clean_url in seen_urls:
                continue

            seen_urls.add(clean_url)

            raw_jobs.append(
                {
                    "id": job_id,
                    "title": title,
                    "url": clean_url,
                    "location": "India",
                }
            )

        return raw_jobs

    def parse_jobs(self, raw_jobs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        parsed_jobs = []
        for item in raw_jobs:
            parsed_jobs.append(
                {
                    "id": item["id"],
                    "company": self.company_name,
                    "title": item["title"],
                    "url": item["url"],
                    "location": item["location"],
                    "posted_date": "",
                }
            )
        return parsed_jobs









        {
  "akamai": true,
  "alteryx": true,
  "arcticwolf": true,
  "bloomreach": true,
  "bugcrowd": true,
  "celigo": true,
  "confluent": true,
  "crunchyroll": true,
  "digicert": true,
  "doordash": true,
  "gitlab": true,
  "h1": true,
  "harness": true,
  "harvey": true,
  "housing": true,
  "indeed": true,
  "lingaro": true,
  "mariadb": true,
  "mongodb": true,
  "netapp": true,
  "paylocity": true,
  "peoplegrove": true,
  "porch": true,
  "postman": true,
  "sharechat": true,
  "singlestore": true,
  "spotdraft": true,
  "texasinstruments": true,
  "toast": false,
  "weave": true,
  "writesonic": true,
  "yugabyte": true,
  "zoetis": true,
  "zoho": true,
  "zoom": true
}