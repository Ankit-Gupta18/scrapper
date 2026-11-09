import os
import re
from datetime import datetime
from typing import List, Dict, Any
from collections import defaultdict

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
DEFAULT_OUTPUT_DIR = os.path.join(PROJECT_ROOT, "job_links")
RUN_FILE_PATTERN = re.compile(r"^run_(\d+)\.txt$")


class ConsoleService:
    """Drop-in replacement for TelegramService.

    Prints jobs to the console and appends them to a numbered file
    (job_links/run_001.txt, run_002.txt, ...) - one file per run.
    """

    def __init__(self, output_dir: str = DEFAULT_OUTPUT_DIR):
        self.output_dir = output_dir
        os.makedirs(self.output_dir, exist_ok=True)

        self.run_number = self._next_run_number()
        self.output_file = os.path.join(self.output_dir, f"run_{self.run_number:03d}.txt")
        self._job_counter = 0

        with open(self.output_file, "w", encoding="utf-8") as f:
            f.write(f"Run #{self.run_number} - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write("=" * 60 + "\n")
        print(f"Job links for this run will be saved to: {self.output_file}")

    def _next_run_number(self) -> int:
        numbers = []
        for name in os.listdir(self.output_dir):
            match = RUN_FILE_PATTERN.match(name)
            if match:
                numbers.append(int(match.group(1)))
        return max(numbers, default=0) + 1

    def _append(self, text: str):
        with open(self.output_file, "a", encoding="utf-8") as f:
            f.write(text)

    def send_company_summary_notification(self, jobs: List[Dict[str, Any]]):
        if not jobs:
            return

        grouped_jobs = defaultdict(list)
        for job in jobs:
            grouped_jobs[job.get("company", "Unknown")].append(job)

        for company, company_jobs in grouped_jobs.items():
            header = f"\n=== {company}: {len(company_jobs)} job(s) ==="
            print(header)
            self._append(header + "\n")

            for job in company_jobs:
                self._job_counter += 1
                line = f"{self._job_counter}. {job.get('title')} ({job.get('location')})"
                url = f"   {job.get('url')}"
                print(line)
                print(url)
                self._append(f"{line}\n{url}\n")

    def send_error_notification(self, company_name: str, error_message: str):
        print(f"[{company_name}] ERROR: {error_message}")
