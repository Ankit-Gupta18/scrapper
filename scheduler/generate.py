"""Generates the launchd plist and the pmset wake list from RUN_INTERVAL_MINUTES in .env.

Usage:
    python scheduler/generate.py plist   -> prints the LaunchAgent plist (XML)
    python scheduler/generate.py wakes   -> prints upcoming wake times, one per line (MM/DD/YY HH:MM:SS)
"""
import sys
from datetime import datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LABEL = "com.jobscraper.runner"


def read_env(key: str, default: str) -> str:
    env_file = ROOT / ".env"
    value = default
    if env_file.exists():
        for line in env_file.read_text().splitlines():
            line = line.strip()
            if line.startswith(f"{key}="):
                value = line.split("=", 1)[1].strip().strip('"\'') or default
    return value


def get_interval() -> int:
    try:
        interval = int(read_env("RUN_INTERVAL_MINUTES", "60"))
    except ValueError:
        sys.exit("RUN_INTERVAL_MINUTES must be a number")
    if interval < 5 or 1440 % interval != 0:
        sys.exit("RUN_INTERVAL_MINUTES must be at least 5 and divide 1440 evenly "
                 "(e.g. 5, 10, 15, 20, 30, 60, 120, 180, 240, 360, 720, 1440)")
    return interval


def slots(interval: int):
    return [(m // 60, m % 60) for m in range(0, 1440, interval)]


def make_plist() -> str:
    entries = "".join(
        f"        <dict><key>Hour</key><integer>{h}</integer>"
        f"<key>Minute</key><integer>{m}</integer></dict>\n"
        for h, m in slots(get_interval())
    )
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key><string>{LABEL}</string>
    <key>ProgramArguments</key>
    <array>
        <string>/bin/bash</string>
        <string>{ROOT}/scheduler/run_job.sh</string>
    </array>
    <key>WorkingDirectory</key><string>{ROOT}</string>
    <key>StartCalendarInterval</key>
    <array>
{entries}    </array>
    <key>StandardOutPath</key><string>{ROOT}/scheduler/launchd.log</string>
    <key>StandardErrorPath</key><string>{ROOT}/scheduler/launchd.log</string>
</dict>
</plist>
"""


def make_wakes() -> str:
    days = int(read_env("WAKE_DAYS", "7"))
    now = datetime.now()
    earliest = now + timedelta(minutes=2)
    out = []
    for offset in range(days + 1):
        day = (now + timedelta(days=offset)).replace(hour=0, minute=0, second=0, microsecond=0)
        for h, m in slots(get_interval()):
            t = day.replace(hour=h, minute=m)
            if earliest < t <= now + timedelta(days=days):
                out.append(t.strftime("%m/%d/%y %H:%M:%S"))
    return "\n".join(out)


if __name__ == "__main__":
    mode = sys.argv[1] if len(sys.argv) > 1 else ""
    if mode == "plist":
        print(make_plist())
    elif mode == "wakes":
        print(make_wakes())
    else:
        sys.exit(__doc__)
