import requests
from typing import List, Dict, Any
from collections import defaultdict


class TelegramService:
    def __init__(self, bot_token: str, channel_chat_id: str, admin_chat_id: str = None):
        self.bot_token = bot_token
        self.channel_chat_id = channel_chat_id
        # Fallback to channel ID if admin ID is omitted
        self.admin_chat_id = admin_chat_id or channel_chat_id
        self.api_url = f"https://api.telegram.org/bot{self.bot_token}/sendMessage"

    def send_message(self, message: str, target_chat_id: str = None):
        """Sends an HTML formatted message to a specific target chat or defaults to the channel."""
        chat_target = target_chat_id or self.channel_chat_id
        if not self.bot_token or not chat_target:
            print("[Telegram] Token or Target Chat ID not configured. Skipping alert.")
            return

        payload = {
            "chat_id": chat_target,
            "text": message,
            "parse_mode": "HTML",
            "disable_web_page_preview": True,
        }

        try:
            response = requests.post(self.api_url, json=payload, timeout=10)
            response.raise_for_status()
        except Exception as e:
            print(f"[Telegram] Failed to send message to {chat_target}: {e}")

    def send_company_summary_notification(self, jobs: List[Dict[str, Any]]):
        """Groups new jobs by company and posts summary directly to the public Channel."""
        if not jobs:
            return

        grouped_jobs = defaultdict(list)
        for job in jobs:
            grouped_jobs[job.get("company", "Unknown")].append(job)

        for company, company_jobs in grouped_jobs.items():
            lines = [f"🚨 <b>{company}</b> posted <b>{len(company_jobs)}</b> new job(s):\n"]

            for idx, job in enumerate(company_jobs, start=1):
                title = job.get("title")
                location = job.get("location")
                url = job.get("url")
                lines.append(f"{idx}. <a href='{url}'><b>{title}</b></a> ({location})")

            # Route job posts strictly to the public channel
            message = "\n".join(lines)
            self.send_message(message, target_chat_id=self.channel_chat_id)

    def send_error_notification(self, company_name: str, error_message: str):
        """Sends failure alerts ONLY to your personal Admin DM to keep the channel feed clean."""
        clean_error = str(error_message)[:1000] if error_message else "Unknown Error"

        text = (
            f"❌ <b>SCRAPER FAILURE ALERT</b> ❌\n\n"
            f"🏢 <b>Company:</b> <code>{company_name}</code>\n"
            f"⚠️ <b>Error Details:</b>\n"
            f"<code>{clean_error}</code>\n\n"
            f"🛠️ <i>Please check server logs for stack trace.</i>"
        )
        # Route errors strictly to your personal admin DM
        self.send_message(text, target_chat_id=self.admin_chat_id)