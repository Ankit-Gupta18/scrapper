import sys
import gc
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from zoneinfo import ZoneInfo
from config import Config
from companies import get_active_scrapers
from services.storage import StorageService
from services.telegram_notifier import TelegramService
from services.console_notifier import ConsoleService
from services.email_notifier import EmailService


class JobRunner:
    def __init__(self):
        self.storage = StorageService(Config.DATABASE_PATH)
        self.use_telegram = Config.USE_TELEGRAM
        if self.use_telegram:
            self.telegram = TelegramService(Config.TELEGRAM_BOT_TOKEN, Config.TELEGRAM_CHAT_ID)
        else:
            self.telegram = ConsoleService()
        self.email = EmailService(Config.EMAIL_SENDER, Config.EMAIL_APP_PASSWORD, Config.EMAIL_TO,
                                  Config.SMTP_HOST, Config.SMTP_PORT)
        self.new_jobs = []
        self._new_job_keys = set()
        self.failures = []
        self.email_failed = False
        # When an email will be sent, jobs are marked as seen only AFTER it goes out, so a failed
        # send never loses jobs (they simply show up again in the next run's email).
        # Baseline runs (SEND_EMAIL=false) and runs without email set up record jobs straight away.
        self.defer_save = Config.SEND_EMAIL and self.email.is_configured and not self.use_telegram

    def run(self) -> bool:
        """Returns False if the summary email could not be sent."""
        print("--- Starting Job Scrape Cycle ---")

        # 1. Fetch scrapers list
        active_scrapers = get_active_scrapers()

        if not active_scrapers:
            print("No active scrapers enabled. Exiting cycle.")
            return True

        # 2. Scrape companies concurrently (network-bound). Only the scraping runs in
        #    worker threads; DB writes and notifications stay on this thread.
        workers = max(1, Config.MAX_WORKERS)
        print(f"Scraping {len(active_scrapers)} companies with {workers} parallel workers")
        with ThreadPoolExecutor(max_workers=workers) as pool:
            futures = {pool.submit(scraper.scrape): scraper for scraper in active_scrapers}
            for future in as_completed(futures):
                self._handle_result(futures[future], future)

        # 3. One summary email: new jobs + scrapers that failed
        self._send_summary()

        # 4. Cleanup DB
        self.storage.cleanup_old_jobs(days=90)

        current_time_ist = datetime.now(ZoneInfo("Asia/Kolkata")).isoformat()
        self.storage.set_last_run(current_time_ist)

        print("--- Scrape Cycle Completed Successfully ---")
        return not self.email_failed

    def _handle_result(self, scraper, future):
        company = scraper.company_name
        try:
            matched_jobs = future.result()
            self.storage.record_scraper_result(company)

            # Only new jobs (not already in the DB, not already found this run) are reported.
            fresh = []
            for job in matched_jobs:
                key = (job["id"], job["company"])
                if key in self._new_job_keys or self.storage.is_job_seen(*key):
                    continue
                self._new_job_keys.add(key)
                fresh.append(job)

            if fresh:
                if not self.defer_save:
                    for job in fresh:
                        self.storage.save_job(job)

                self.telegram.send_company_summary_notification(fresh)
                self.new_jobs.extend(fresh)

        except Exception as e:
            error_msg = str(e)
            print(f"[{company}] Failed: {error_msg}")
            try:
                streak = self.storage.record_scraper_result(company, error_msg)
            except Exception as db_error:
                print(f"[{company}] Could not record failure: {db_error}")
                streak = 1
            self.failures.append({"company": company, "error": error_msg, "streak": streak})
            self.telegram.send_error_notification(company, error_msg)

        finally:
            gc.collect()

    def _failure_report(self):
        """Adds `flagged` (failing several runs in a row) and `alert` (worth an email on its own:
        crossed the threshold this run, or a periodic reminder) to each failure."""
        threshold = max(1, Config.FAIL_ALERT_THRESHOLD)
        reminder = Config.FAIL_REMINDER_EVERY
        report = []
        for f in self.failures:
            streak = f["streak"]
            over = streak - threshold
            report.append({
                **f,
                "flagged": streak >= threshold,
                "alert": streak == threshold or (over > 0 and reminder > 0 and over % reminder == 0),
            })
        # Repeat offenders first, then alphabetical
        report.sort(key=lambda f: (not f["flagged"], f["company"].lower()))
        return report

    def _send_summary(self):
        failures = self._failure_report()

        if not Config.SEND_EMAIL:
            print(f"[Email] SEND_EMAIL=false - baseline run, {len(self.new_jobs)} job(s) recorded without emailing.")
            return

        result = self.email.send_run_summary(self.new_jobs, failures)
        if result is False:
            self.email_failed = True
            print("[Email] Not sent - jobs were NOT marked as seen, so they will be included in the next run's email.")
        elif result and self.defer_save:
            for job in self.new_jobs:
                self.storage.save_job(job)
        elif result is None and self.defer_save and self.new_jobs:
            # Defensive: there were jobs but nothing was sent - keep them unseen.
            print("[Email] Nothing sent - jobs left unseen for the next run.")


def run_pipeline():
    try:
        runner = JobRunner()
        ok = runner.run()
        # Non-zero exit makes GitHub mark the run as failed (and email you about it)
        sys.exit(0 if ok else 1)
    except Exception as e:
        print(f"Critical Pipeline execution failure: {e}")
        sys.exit(1)
