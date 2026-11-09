# main.py
import os
import sys
import time
import logging
from services.runner import run_pipeline

PROJECT_ROOT = os.path.abspath(os.path.dirname(__file__))
LOG_FILE = os.path.join(PROJECT_ROOT, "scraper.log")
MARKER_FILE = os.path.join(PROJECT_ROOT, ".log_last_cleared")
SEVEN_DAYS_SEC = 7 * 24 * 60 * 60


def clean_log_if_needed():
    """Truncates log file if more than 7 days have passed since the last reset."""
    now = time.time()

    # If marker file doesn't exist, create it with current time
    if not os.path.exists(MARKER_FILE):
        with open(MARKER_FILE, "w") as f:
            f.write(str(now))
        return

    # Read last cleared timestamp
    try:
        with open(MARKER_FILE, "r") as f:
            last_cleared = float(f.read().strip())
    except Exception:
        last_cleared = now

    # Reset log file if 7 days have passed
    if (now - last_cleared) >= SEVEN_DAYS_SEC:
        if os.path.exists(LOG_FILE):
            open(LOG_FILE, "w").close()  # Clears file content instantly
        
        # Reset the timestamp inside marker
        with open(MARKER_FILE, "w") as f:
            f.write(str(now))


class StreamToLogger:
    """Redirects stdout / stderr directly to Python logging."""
    def __init__(self, logger, level):
        self.logger = logger
        self.level = level

    def write(self, message):
        if message.strip():
            self.logger.log(self.level, message.strip())

    def flush(self):
        pass


def setup_logging():
    # 1. Clean log before attaching standard file handlers
    clean_log_if_needed()

    # 2. Setup standard logging
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)

    file_handler = logging.FileHandler(LOG_FILE, encoding="utf-8")
    formatter = logging.Formatter("[%(asctime)s] %(levelname)s: %(message)s", datefmt="%Y-%m-%d %H:%M:%S")
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    # Also echo logs to the real terminal so job links are visible locally
    console_handler = logging.StreamHandler(sys.__stdout__)
    console_handler.setFormatter(logging.Formatter("%(message)s"))
    logger.addHandler(console_handler)

    # 3. Redirect standard stdout / stderr to logs
    sys.stdout = StreamToLogger(logger, logging.INFO)
    sys.stderr = StreamToLogger(logger, logging.ERROR)


def main():
    setup_logging()
    run_pipeline()


if __name__ == "__main__":
    main()