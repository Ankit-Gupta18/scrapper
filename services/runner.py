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

    def run(self):
        print("--- Starting Job Scrape Cycle ---")

        # 1. Fetch scrapers list
        active_scrapers = get_active_scrapers()

        if not active_scrapers:
            print("No active scrapers enabled. Exiting cycle.")
            return

        # 2. Scrape companies concurrently (network-bound). Only the scraping runs in
        #    worker threads; DB writes and notifications stay on this thread.
        workers = max(1, Config.MAX_WORKERS)
        print(f"Scraping {len(active_scrapers)} companies with {workers} parallel workers")
        with ThreadPoolExecutor(max_workers=workers) as pool:
            futures = {pool.submit(scraper.scrape): scraper for scraper in active_scrapers}
            for future in as_completed(futures):
                self._handle_result(futures[future], future)

        # 3. One summary email with all new jobs from this run
        if Config.SEND_EMAIL:
            self.email.send_run_summary(self.new_jobs)
        else:
            print(f"[Email] SEND_EMAIL=false - baseline run, {len(self.new_jobs)} job(s) recorded without emailing.")

        # 4. Cleanup DB
        self.storage.cleanup_old_jobs(days=90)

        current_time_ist = datetime.now(ZoneInfo("Asia/Kolkata")).isoformat()
        self.storage.set_last_run(current_time_ist)

        print("--- Scrape Cycle Completed Successfully ---")

    def _handle_result(self, scraper, future):
        try:
            matched_jobs = future.result()
            # Only new jobs (not already in the DB) are printed/sent, in both local and Telegram mode.
            unseen_jobs = [j for j in matched_jobs if not self.storage.is_job_seen(j["id"], j["company"])]

            if unseen_jobs:
                for job in unseen_jobs:
                    self.storage.save_job(job)

                self.telegram.send_company_summary_notification(unseen_jobs)
                self.new_jobs.extend(unseen_jobs)

        except Exception as e:
            error_msg = str(e)
            print(f"[{scraper.company_name}] Failed: {error_msg}")
            self.telegram.send_error_notification(scraper.company_name, error_msg)

        finally:
            gc.collect()


def run_pipeline():
    try:
        runner = JobRunner()
        runner.run()
        sys.exit(0)
    except Exception as e:
        print(f"Critical Pipeline execution failure: {e}")
        sys.exit(1)
