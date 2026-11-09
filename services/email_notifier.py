import smtplib
from collections import defaultdict
from datetime import datetime
from email.message import EmailMessage
from html import escape
from typing import List, Dict, Any, Optional


class EmailService:
    """Sends one HTML summary email per run: every new job link grouped by company, plus a
    section listing scrapers that failed (with a warning when one keeps failing)."""

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

    @staticmethod
    def _short(text: Any, limit: int = 250) -> str:
        text = " ".join(str(text or "Unknown error").split())
        return text if len(text) <= limit else text[:limit] + "..."

    def _jobs_html(self, grouped: Dict[str, List[Dict[str, Any]]]) -> str:
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
        return "".join(sections)

    def _failures_html(self, failures: List[Dict[str, Any]]) -> str:
        if not failures:
            return ""
        rows = []
        for f in failures:
            streak = int(f.get("streak", 1))
            if f.get("flagged"):
                badge = (f"<span style='background:#dc2626;color:#fff;padding:2px 8px;border-radius:10px;"
                         f"font-size:11px;font-weight:600;'>&#9888; failing {streak} runs in a row</span>")
            else:
                badge = (f"<span style='background:#e5e7eb;color:#374151;padding:2px 8px;border-radius:10px;"
                         f"font-size:11px;'>{'1st failure' if streak <= 1 else f'{streak} in a row'}</span>")
            rows.append(
                "<tr><td style='padding:8px 12px;border-bottom:1px solid #fde8c8;'>"
                f"<b>{escape(str(f.get('company')))}</b> {badge}"
                f"<div style='color:#6b7280;font-size:12px;margin-top:3px;word-break:break-all;'>"
                f"{escape(self._short(f.get('error')))}</div></td></tr>"
            )
        return (
            f"<h3 style='margin:28px 0 8px;font-size:16px;color:#b45309;'>"
            f"Scrapers that failed this run ({len(failures)})</h3>"
            "<table width='100%' cellspacing='0' cellpadding='0' "
            "style='border:1px solid #fcd9a8;background:#fffbeb;border-radius:6px;border-collapse:separate;'>"
            f"{''.join(rows)}</table>"
        )

    def _build_html(self, grouped, total: int, failures, run_label: str) -> str:
        flagged = sum(1 for f in failures if f.get("flagged"))
        if total:
            title = "New job openings"
            sub = f"{total} new job(s) across {len(grouped)} company(ies)"
            color = "#1a56db"
        else:
            title = "Scraper alert"
            sub = f"{flagged} scraper(s) failing repeatedly"
            color = "#dc2626"
        if total and flagged:
            sub += f" &middot; &#9888; {flagged} scraper(s) failing repeatedly"
        return (
            "<html><body style='margin:0;padding:0;background:#f3f4f6;"
            "font-family:-apple-system,Segoe UI,Roboto,Arial,sans-serif;'>"
            "<div style='max-width:720px;margin:0 auto;padding:24px;'>"
            f"<div style='background:{color};color:#fff;padding:20px 24px;border-radius:8px 8px 0 0;'>"
            f"<div style='font-size:20px;font-weight:700;'>{title}</div>"
            f"<div style='font-size:13px;opacity:.9;margin-top:4px;'>{sub} &middot; {escape(run_label)}</div></div>"
            "<div style='background:#fff;padding:8px 24px 24px;border-radius:0 0 8px 8px;'>"
            f"{self._jobs_html(grouped)}{self._failures_html(failures)}</div>"
            "</div></body></html>"
        )

    def _build_text(self, grouped, total: int, failures, run_label: str) -> str:
        lines = [f"New job openings - {total} job(s) - {run_label}", ""]
        for company, jobs in grouped.items():
            lines.append(f"== {company} ({len(jobs)}) ==")
            for idx, job in enumerate(jobs, start=1):
                lines.append(f"{idx}. {job.get('title')} ({job.get('location')})")
                lines.append(f"   {job.get('url')}")
            lines.append("")
        if failures:
            lines.append(f"== Scrapers that failed this run ({len(failures)}) ==")
            for f in failures:
                flag = f"  [FAILING {f.get('streak')} RUNS IN A ROW]" if f.get("flagged") else ""
                lines.append(f"- {f.get('company')}{flag}: {self._short(f.get('error'))}")
            lines.append("")
        return "\n".join(lines)

    def send_run_summary(self, jobs: List[Dict[str, Any]],
                         failures: Optional[List[Dict[str, Any]]] = None) -> Optional[bool]:
        """Sends the email when there are new jobs, or when a scraper has just crossed its
        failure-alert threshold. Returns True if sent, False on failure, None if there was
        nothing to send or email isn't configured.

        `failures` items: {company, error, streak, flagged, alert}."""
        failures = failures or []
        alert_worthy = any(f.get("alert") for f in failures)
        if not jobs and not alert_worthy:
            return None
        if not self.is_configured:
            print("[Email] EMAIL_SENDER / EMAIL_APP_PASSWORD not set in .env. Skipping email.")
            return None

        grouped = self._group(jobs)
        run_label = datetime.now().strftime("%d %b %Y, %I:%M %p")
        text_body = self._build_text(grouped, len(jobs), failures, run_label)
        flagged = sum(1 for f in failures if f.get("flagged"))

        if jobs:
            subject = f"{len(jobs)} new job(s) from {len(grouped)} company(ies) - {run_label}"
            if flagged:
                subject += f" | {flagged} scraper(s) failing"
        else:
            subject = f"Scraper alert: {flagged} scraper(s) failing repeatedly - {run_label}"

        msg = EmailMessage()
        msg["Subject"] = subject
        msg["From"] = self.sender
        msg["To"] = self.recipient
        msg.set_content(text_body)
        msg.add_alternative(self._build_html(grouped, len(jobs), failures, run_label), subtype="html")
        # Full plain-text list as an attachment (Gmail clips very long HTML emails).
        msg.add_attachment(text_body.encode("utf-8"), maintype="text", subtype="plain",
                           filename="new_jobs.txt")

        try:
            with smtplib.SMTP(self.host, self.port, timeout=30) as server:
                server.starttls()
                server.login(self.sender, self.password)
                server.send_message(msg)
            print(f"[Email] Sent {len(jobs)} job(s) and {len(failures)} failure note(s) to {self.recipient}")
            return True
        except Exception as e:
            print(f"[Email] Failed to send email: {e}")
            return False
