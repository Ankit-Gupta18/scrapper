import smtplib
from collections import defaultdict
from datetime import datetime
from email.message import EmailMessage
from html import escape
from typing import List, Dict, Any, Optional


class EmailService:
    """Sends one HTML summary email per run, with every new job link grouped by company."""

    def __init__(self, sender: str, password: str, recipient: str,
                 host: str = "smtp.gmail.com", port: int = 587):
        self.sender = sender
        self.password = password
        self.recipient = recipient
        self.host = host
        self.port = port

    @property
    def is_configured(self) -> bool:
        return bool(self.sender and self.password and self.recipient)

    @staticmethod
    def _group(jobs: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
        grouped = defaultdict(list)
        for job in jobs:
            grouped[job.get("company", "Unknown")].append(job)
        return dict(sorted(grouped.items(), key=lambda kv: kv[0].lower()))

    def _build_html(self, grouped: Dict[str, List[Dict[str, Any]]], total: int, run_label: str) -> str:
        sections = []
        for company, jobs in grouped.items():
            rows = []
            for job in jobs:
                url = escape(str(job.get("url") or "#"), quote=True)
                title = escape(str(job.get("title") or "Untitled"))
                location = escape(str(job.get("location") or "-"))
                rows.append(
                    "<tr>"
                    f"<td style='padding:8px 12px;border-bottom:1px solid #eee;'>"
                    f"<a href='{url}' style='color:#1a56db;text-decoration:none;font-weight:600;'>{title}</a>"
                    f"<div style='color:#6b7280;font-size:12px;margin-top:2px;'>{location}</div></td>"
                    f"<td style='padding:8px 12px;border-bottom:1px solid #eee;text-align:right;white-space:nowrap;'>"
                    f"<a href='{url}' style='background:#1a56db;color:#fff;padding:5px 12px;"
                    f"border-radius:4px;font-size:12px;text-decoration:none;'>Apply</a></td>"
                    "</tr>"
                )
            sections.append(
                f"<h3 style='margin:24px 0 8px;font-size:16px;color:#111827;'>"
                f"{escape(company)} <span style='color:#6b7280;font-weight:400;'>({len(jobs)})</span></h3>"
                "<table width='100%' cellspacing='0' cellpadding='0' "
                "style='border:1px solid #e5e7eb;border-radius:6px;border-collapse:separate;'>"
                f"{''.join(rows)}</table>"
            )

        return (
            "<html><body style='margin:0;padding:0;background:#f3f4f6;"
            "font-family:-apple-system,Segoe UI,Roboto,Arial,sans-serif;'>"
            "<div style='max-width:720px;margin:0 auto;padding:24px;'>"
            "<div style='background:#1a56db;color:#fff;padding:20px 24px;border-radius:8px 8px 0 0;'>"
            "<div style='font-size:20px;font-weight:700;'>New job openings</div>"
            f"<div style='font-size:13px;opacity:.9;margin-top:4px;'>{total} new job(s) across "
            f"{len(grouped)} company(ies) &middot; {escape(run_label)}</div></div>"
            "<div style='background:#fff;padding:8px 24px 24px;border-radius:0 0 8px 8px;'>"
            f"{''.join(sections)}</div>"
            "</div></body></html>"
        )

    @staticmethod
    def _build_text(grouped: Dict[str, List[Dict[str, Any]]], total: int, run_label: str) -> str:
        lines = [f"New job openings - {total} job(s) - {run_label}", ""]
        for company, jobs in grouped.items():
            lines.append(f"== {company} ({len(jobs)}) ==")
            for idx, job in enumerate(jobs, start=1):
                lines.append(f"{idx}. {job.get('title')} ({job.get('location')})")
                lines.append(f"   {job.get('url')}")
            lines.append("")
        return "\n".join(lines)

    def send_run_summary(self, jobs: List[Dict[str, Any]]) -> Optional[bool]:
        """Returns True if sent, False on failure, None if nothing to send / not configured."""
        if not jobs:
            return None
        if not self.is_configured:
            print("[Email] EMAIL_SENDER / EMAIL_APP_PASSWORD not set in .env. Skipping email.")
            return None

        grouped = self._group(jobs)
        run_label = datetime.now().strftime("%d %b %Y, %I:%M %p")
        text_body = self._build_text(grouped, len(jobs), run_label)

        msg = EmailMessage()
        msg["Subject"] = f"{len(jobs)} new job(s) from {len(grouped)} company(ies) - {run_label}"
        msg["From"] = self.sender
        msg["To"] = self.recipient
        msg.set_content(text_body)
        msg.add_alternative(self._build_html(grouped, len(jobs), run_label), subtype="html")
        # Full plain-text list as an attachment (Gmail clips very long HTML emails).
        msg.add_attachment(text_body.encode("utf-8"), maintype="text", subtype="plain",
                           filename="new_jobs.txt")

        try:
            with smtplib.SMTP(self.host, self.port, timeout=30) as server:
                server.starttls()
                server.login(self.sender, self.password)
                server.send_message(msg)
            print(f"[Email] Sent {len(jobs)} job(s) to {self.recipient}")
            return True
        except Exception as e:
            print(f"[Email] Failed to send email: {e}")
            return False
