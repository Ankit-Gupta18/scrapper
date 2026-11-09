# scrappers/darwinbox.py
from typing import List, Dict, Any
from curl_cffi import requests
from scrappers.base import BaseJobScraper


class BaseDarwinboxScraper(BaseJobScraper):
    darwinbox_slug: str = ""

    @property
    def api_url(self) -> str:
        return f"https://{self.darwinbox_slug}.darwinbox.in/ms/candidateapi/job/alljobs?companyId=main"

    @property
    def base_careers_url(self) -> str:
        return f"https://{self.darwinbox_slug}.darwinbox.in"

    def fetch_jobs(self) -> List[Dict[str, Any]]:
        session = requests.Session(impersonate="chrome120")

        headers = {
            "accept": "application/json, text/plain, */*",
            "accept-language": "en",
            "content-type": "application/json",
            "origin": self.base_careers_url,
            "referer": f"{self.base_careers_url}/ms/candidatev2/main/careers/allJobs",
            "sec-ch-ua": '"Not;A=Brand";v="8", "Chromium";v="150", "Google Chrome";v="150"',
            "sec-ch-ua-mobile": "?0",
            "sec-ch-ua-platform": '"macOS"',
            "sec-fetch-dest": "empty",
            "sec-fetch-mode": "cors",
            "sec-fetch-site": "same-origin",
            "user-agent": (
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/150.0.0.0 Safari/537.36"
            ),
        }

        payload = {
            "companyId": "main",
            "page": 1,
            "limit": 100,
            "sort_option": "new",
            "department": [],
            "location": [],
            "work_mode": [],
            "capabilities": [],
            "job_tags": [],
            "functional_area": [],
            "exp_from": "",
            "exp_to": "",
            "country": [],
            "legal_entities": [],
        }

        try:
            response = session.post(self.api_url, json=payload, headers=headers, timeout=15)
            response.raise_for_status()
            res_json = response.json()
        except Exception as e:
            print(f"[{self.company_name}] Failed to fetch jobs via Darwinbox API: {e}")
            return []

        # Robust extraction of the jobs array across different response formats
        job_list = []
        if isinstance(res_json, dict):
            raw_data = res_json.get("data")
            if isinstance(raw_data, list):
                job_list = raw_data
            elif isinstance(raw_data, dict):
                job_list = raw_data.get("jobs", [])
            else:
                job_list = res_json.get("jobs", [])
        elif isinstance(res_json, list):
            job_list = res_json

        raw_jobs = []

        for job in job_list:
            if not isinstance(job, dict):
                continue

            job_id = (
                job.get("id")
                or job.get("_id")
                or job.get("job_id")
                or job.get("jobId")
            )
            
            title = (
                job.get("title")
                or job.get("designation_display_name")
                or job.get("designation_name")
                or job.get("job_title", "")
            )

            # Location extraction prioritizing readable strings
            loc_list = (
                job.get("officelocation_show_arr_list")
                or job.get("officelocations_without_area")
                or job.get("location")
            )

            if isinstance(loc_list, list) and len(loc_list) > 0:
                location = ", ".join([str(x).strip() for x in loc_list if str(x).strip()])
            else:
                location = str(job.get("locations") or job.get("country") or "India")

            if not job_id or not title:
                continue

            job_url = f"{self.base_careers_url}/ms/candidatev2/main/careers/jobDetails?jobId={job_id}"

            raw_jobs.append({
                "id": str(job_id),
                "title": str(title).strip(),
                "url": job_url,
                "location": location.strip() or "India",
                "posted_date": str(job.get("created_on") or job.get("posted_on", "")),
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
                "posted_date": item.get("posted_date", ""),
            })
        return parsed_jobs