import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    # Set USE_TELEGRAM=true in .env to post to Telegram; default is local console output only
    USE_TELEGRAM = os.getenv("USE_TELEGRAM", "false").strip().lower() in ("1", "true", "yes")

    # Number of companies scraped in parallel (set MAX_WORKERS=1 for sequential)
    MAX_WORKERS = int(os.getenv("MAX_WORKERS", "20"))

    # Email (Gmail SMTP). EMAIL_APP_PASSWORD must be a Google "App Password", not your login password.
    EMAIL_SENDER = os.getenv("EMAIL_SENDER")
    EMAIL_APP_PASSWORD = (os.getenv("EMAIL_APP_PASSWORD") or "").replace(" ", "")
    EMAIL_TO = os.getenv("EMAIL_TO", "ankitguptabhabha@gmail.com")
    SMTP_HOST = os.getenv("SMTP_HOST", "smtp.gmail.com")
    SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))

    # Set SEND_EMAIL=false to record jobs as seen without emailing (used for baseline runs)
    SEND_EMAIL = os.getenv("SEND_EMAIL", "true").strip().lower() in ("1", "true", "yes")

    # Telegram
    TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
    TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
    TELEGRAM_ADMIN_CHAT_ID=os.getenv("TELEGRAM_ADMIN_CHAT_ID")

    # Storage
    DATABASE_PATH = os.getenv("DB_PATH", "database/jobs.db")
    
    # HTTP / Scraping Configuration
    DEFAULT_TIMEOUT = 30
    DEFAULT_HEADERS = {
        "User-Agent": os.getenv(
            "USER_AGENT",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
        )
    }