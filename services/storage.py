import sqlite3
import os
from typing import Dict, Any

class StorageService:
    def __init__(self, db_path: str = "database/jobs.db"):
        self.db_path = db_path
        self._ensure_db_exists()

    def _get_connection(self):
        return sqlite3.connect(self.db_path)

    def _ensure_db_exists(self):
        """Creates the database folder and jobs table if they don't exist."""
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS jobs (
                    id TEXT,
                    company TEXT,
                    title TEXT,
                    location TEXT,
                    url TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    PRIMARY KEY (id, company)
                )
            """)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS scraper_health (
                    company TEXT PRIMARY KEY,
                    consecutive_failures INTEGER DEFAULT 0,
                    last_error TEXT,
                    last_success TIMESTAMP,
                    last_failure TIMESTAMP
                )
            """)
            conn.commit()

    def record_scraper_result(self, company: str, error: str = None) -> int:
        """Records one scraper outcome. Returns how many runs in a row this scraper has
        failed (0 after a success)."""
        with self._get_connection() as conn:
            if error is None:
                conn.execute(
                    """
                    INSERT INTO scraper_health (company, consecutive_failures, last_success)
                    VALUES (?, 0, CURRENT_TIMESTAMP)
                    ON CONFLICT(company) DO UPDATE SET
                        consecutive_failures = 0, last_success = CURRENT_TIMESTAMP
                    """,
                    (company,),
                )
                conn.commit()
                return 0
            conn.execute(
                """
                INSERT INTO scraper_health (company, consecutive_failures, last_error, last_failure)
                VALUES (?, 1, ?, CURRENT_TIMESTAMP)
                ON CONFLICT(company) DO UPDATE SET
                    consecutive_failures = consecutive_failures + 1,
                    last_error = excluded.last_error,
                    last_failure = CURRENT_TIMESTAMP
                """,
                (company, error[:500]),
            )
            conn.commit()
            row = conn.execute(
                "SELECT consecutive_failures FROM scraper_health WHERE company = ?", (company,)
            ).fetchone()
            return row[0] if row else 1

    def is_job_seen(self, job_id: str, company: str) -> bool:
        """Checks if a job from a specific company already exists in SQLite."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT 1 FROM jobs WHERE id = ? AND company = ?", 
                (job_id, company)
            )
            return cursor.fetchone() is not None

    def save_job(self, job: Dict[str, Any]):
        """Inserts a new job record into SQLite."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT OR IGNORE INTO jobs (id, company, title, location, url)
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    job.get("id"),
                    job.get("company"),
                    job.get("title"),
                    job.get("location"),
                    job.get("url")
                )
            )
            conn.commit()

    def cleanup_old_jobs(self, days: int = 30):
        """Deletes job records older than X days to prevent database bloating."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "DELETE FROM jobs WHERE created_at < datetime('now', ?)",
                (f"-{days} days",)
            )
            conn.commit()

    def set_last_run(self, timestamp_str: str):
        """Saves the latest run timestamp to a metadata table."""
        with self._get_connection() as conn:
            conn.execute(
                "CREATE TABLE IF NOT EXISTS metadata (key TEXT PRIMARY KEY, value TEXT)"
            )
            conn.execute(
                "INSERT OR REPLACE INTO metadata (key, value) VALUES ('last_run', ?)",
                (timestamp_str,),
            )

            # delete command for db
            # sqlite3 database/jobs.db "DELETE FROM jobs;"