import os
import sys
import json
import sqlite3
import subprocess
from datetime import datetime
from zoneinfo import ZoneInfo

import yaml

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

# Standard library imports must come before python-telegram-bot
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

from config import Config

# --- Configuration & File Paths ---
TOKEN = Config.TELEGRAM_BOT_TOKEN
# Only allow your personal Telegram User ID to run bot commands
ALLOWED_USER_ID = int(Config.TELEGRAM_ADMIN_CHAT_ID)

MARKER = "JOB_SCRAPER_JOB"
DATABASE_PATH = Config.DATABASE_PATH
REGISTRY_FILE = os.path.join(PROJECT_ROOT, "database", "registry.json")
CATALOG_FILE = os.path.join(PROJECT_ROOT, "database", "catalog.yaml")


# --- Helper Functions ---

def is_authorized(update: Update) -> bool:
    """Restricts command execution exclusively to your personal Admin User ID."""
    return update.effective_user.id == ALLOWED_USER_ID


def get_crontab():
    result = subprocess.run(
        ["crontab", "-l"],
        capture_output=True,
        text=True
    )
    return result.stdout.splitlines()


def write_crontab(lines):
    with open("/tmp/mycron_scraper", "w") as f:
        f.write("\n".join(lines) + "\n")
    subprocess.run(["crontab", "/tmp/mycron_scraper"])


def toggle_job():
    lines = get_crontab()
    new_lines = []
    new_status = None

    for line in lines:
        if MARKER in line:
            if line.lstrip().startswith("#"):
                # ENABLE: remove leading '#'
                line = line.lstrip()[1:]
                new_status = "ENABLED"
            else:
                # DISABLE: prepend '#'
                line = "#" + line
                new_status = "DISABLED"
        new_lines.append(line)

    write_crontab(new_lines)

    if new_status == "ENABLED":
        return "✅ JOB SCRAPER cron job ENABLED"
    elif new_status == "DISABLED":
        return "⛔ JOB SCRAPER cron job DISABLED"
    else:
        return f"⚠️ Could not find cron line tagged with '{MARKER}'"


def is_cron_enabled() -> bool:
    lines = get_crontab()
    for line in lines:
        if MARKER in line and not line.lstrip().startswith("#"):
            return True
    return False


def get_last_run_time() -> str:
    """Reads last run time directly from SQLite DB."""
    if not os.path.exists(DATABASE_PATH):
        return "Database file not found."

    try:
        conn = sqlite3.connect(DATABASE_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT value FROM metadata WHERE key = 'last_run'")
        row = cursor.fetchone()
        conn.close()
        if not row or not row[0]:
            return "No execution recorded yet."

        raw_str = row[0]
        # Parse ISO string and convert to formatted IST string
        dt = datetime.fromisoformat(raw_str).astimezone(ZoneInfo("Asia/Kolkata"))
        return dt.strftime("%d %b %Y, %I:%M %p IST")
    except Exception as e:
        return f"Error reading DB: {e}"


def load_registry() -> dict:
    if os.path.exists(REGISTRY_FILE):
        with open(REGISTRY_FILE, "r") as f:
            return json.load(f)
    return {}


def save_registry(registry_data: dict):
    with open(REGISTRY_FILE, "w") as f:
        json.dump(registry_data, f, indent=2)


def load_catalog() -> dict:
    """Returns the catalog.yaml document, or an empty companies list if absent."""
    if os.path.exists(CATALOG_FILE):
        with open(CATALOG_FILE, "r") as f:
            return yaml.safe_load(f) or {"companies": []}
    return {"companies": []}


def save_catalog(catalog_data: dict):
    with open(CATALOG_FILE, "w") as f:
        yaml.safe_dump(catalog_data, f, sort_keys=False)


def toggle_catalog_entry(identifier: str) -> tuple[bool, str]:
    """Match a catalog row by (company name or board), case-insensitive, and flip
    its `enabled`. Returns (changed, message)."""
    catalog = load_catalog()
    needle = identifier.lower().strip()
    for row in catalog.get("companies", []):
        if row["company"].lower().strip() == needle or row["board"].lower().strip() == needle:
            row["enabled"] = not row.get("enabled", False)
            save_catalog(catalog)
            new_state = "✅ ENABLED" if row["enabled"] else "🔴 DISABLED"
            label = f"{row['company']} [{row['provider']}:{row['board']}]"
            return True, f"Catalog entry '<b>{label}</b>' is now {new_state}."
    return False, ""


# --- Command Handlers ---

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Command: /start - Welcome message."""
    if not is_authorized(update):
        await update.message.reply_text("⛔ You are not authorized to access control commands.")
        return

    msg = (
        "👋 <b>Welcome to Job Scraper Controller!</b>\n\n"
        "Available Admin Commands:\n"
        "• /status - Show cron state, last run & active company counts\n"
        "• /run - Manually trigger background scrape cycle\n"
        "• /toggle - Enable/Disable crontab schedule\n"
        "• /companies - List company scraper statuses\n"
        "• /toggle_company &lt;company_name&gt; - Toggle scraper for a specific company"
    )
    await update.message.reply_text(msg, parse_mode="HTML")


async def toggle_cron(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Command: /toggle - Toggles the crontab entry for job scraper."""
    if not is_authorized(update):
        await update.message.reply_text("❌ Not authorized.")
        return

    try:
        message = toggle_job()
        await update.message.reply_text(message)
    except Exception as e:
        await update.message.reply_text(f"⚠️ Error: {str(e)}")


async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Command: /status - Displays cron status, last run time, and active companies count."""
    if not is_authorized(update):
        await update.message.reply_text("❌ Not authorized.")
        return

    cron_state = "🟢 ENABLED" if is_cron_enabled() else "🔴 DISABLED"
    last_run = get_last_run_time()

    registry = load_registry()
    legacy_active = sum(1 for s in registry.values() if s is True)
    legacy_total = len(registry)

    catalog_rows = load_catalog().get("companies", [])
    catalog_active = sum(1 for r in catalog_rows if r.get("enabled", False))
    catalog_total = len(catalog_rows)

    text = (
        f"📊 <b>Job Scraper Status</b>\n"
        f"━━━━━━━━━━━━━━━━━━━\n"
        f"⏰ <b>Cron Schedule:</b> {cron_state}\n"
        f"🕒 <b>Last Run:</b> <code>{last_run}</code>\n"
        f"🏢 <b>Legacy:</b> {legacy_active}/{legacy_total} companies\n"
        f"📚 <b>Catalog:</b> {catalog_active}/{catalog_total} companies\n"
    )
    await update.message.reply_text(text, parse_mode="HTML")


async def toggle_company(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Command: /toggle_company <company_name>
    Example: /toggle_company zoom
    Toggles true/false state for a company in registry.json.
    """
    if not is_authorized(update):
        await update.message.reply_text("❌ Not authorized.")
        return

    if not context.args:
        await update.message.reply_text("⚠️ Please provide a company name.\nExample: <code>/toggle_company zoom</code>", parse_mode="HTML")
        return

    target_company = context.args[0].lower().strip()
    registry = load_registry()

    # Legacy registry match wins — matches historical behavior.
    if target_company in registry:
        new_state = not registry[target_company]
        registry[target_company] = new_state
        save_registry(registry)
        state_icon = "✅ ENABLED" if new_state else "🔴 DISABLED"
        await update.message.reply_text(
            f"Company '<b>{target_company}</b>' is now {state_icon} in registry.",
            parse_mode="HTML",
        )
        return

    # Fall back to the catalog (by company name or board, case-insensitive).
    changed, msg = toggle_catalog_entry(target_company)
    if changed:
        await update.message.reply_text(msg, parse_mode="HTML")
        return

    legacy_names = ", ".join(sorted(registry.keys()))
    await update.message.reply_text(
        f"❌ Company '<b>{target_company}</b>' not found in legacy registry or catalog.\n\n"
        f"<b>Legacy keys:</b>\n<code>{legacy_names}</code>",
        parse_mode="HTML",
    )


async def list_companies(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Command: /companies - Shows status of all scrapers in registry.json."""
    if not is_authorized(update):
        await update.message.reply_text("❌ Not authorized.")
        return

    registry = load_registry()
    catalog_rows = load_catalog().get("companies", [])
    if not registry and not catalog_rows:
        await update.message.reply_text("⚠️ Both legacy registry and catalog are empty.")
        return

    legacy_on = sorted(c for c, active in registry.items() if active)
    legacy_off = sorted(c for c, active in registry.items() if not active)
    catalog_on = sorted(f"{r['company']} ({r['provider']})" for r in catalog_rows if r.get("enabled"))
    catalog_off_n = sum(1 for r in catalog_rows if not r.get("enabled"))

    msg_lines = [f"📋 <b>Scrapers</b> ({len(registry) + len(catalog_rows)} total)\n"]
    msg_lines.append(f"🟢 <b>Legacy active ({len(legacy_on)}):</b>")
    msg_lines.append("\n".join(f"• <code>{c}</code>" for c in legacy_on) if legacy_on else "None")
    if legacy_off:
        msg_lines.append(f"\n🔴 <b>Legacy disabled ({len(legacy_off)}):</b>")
        msg_lines.append("\n".join(f"• <code>{c}</code>" for c in legacy_off))
    msg_lines.append(f"\n📚 <b>Catalog active ({len(catalog_on)}):</b>")
    # Telegram's 4096-char message limit — truncate long catalogs with a tail count.
    body = "\n".join(f"• <code>{c}</code>" for c in catalog_on) if catalog_on else "None"
    if len(body) > 2500:
        body = body[:2500] + f"\n… (+{body.count(chr(10)) - 60} more)"
    msg_lines.append(body)
    if catalog_off_n:
        msg_lines.append(f"\n🔴 <b>Catalog disabled:</b> {catalog_off_n}")

    await update.message.reply_text("\n".join(msg_lines), parse_mode="HTML")


async def trigger_manual_run(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Command: /run - Manually triggers main.py in a background process."""
    if not is_authorized(update):
        await update.message.reply_text("❌ Not authorized.")
        return

    main_script_path = os.path.join(PROJECT_ROOT, "main.py")
    python_executable = sys.executable  # Uses active venv Python interpreter

    try:
        # Launch main.py as a non-blocking background process
        subprocess.Popen([python_executable, main_script_path])
        
        await update.message.reply_text(
            "🚀 <b>Manual Scraper Run Started!</b>\n"
            "The scraper is running in the background. Job posts will go to your channel.",
            parse_mode="HTML"
        )
    except Exception as e:
        await update.message.reply_text(f"⚠️ Failed to start process: <code>{str(e)}</code>", parse_mode="HTML")


# --- Main Application Loop ---

def main():
    app = Application.builder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("toggle", toggle_cron))
    app.add_handler(CommandHandler("status", status))
    app.add_handler(CommandHandler("toggle_company", toggle_company))
    app.add_handler(CommandHandler("companies", list_companies))
    app.add_handler(CommandHandler("run", trigger_manual_run))

    print("Job Scraper Telegram Controller started...")
    app.run_polling()


if __name__ == "__main__":
    main()