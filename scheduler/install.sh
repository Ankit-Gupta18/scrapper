#!/bin/bash
# Installs the recurring schedule. Re-run it any time to apply a new RUN_INTERVAL_MINUTES
# or to extend the wake schedule.   Usage: bash scheduler/install.sh [--agent-only]
set -euo pipefail
DIR="$(cd "$(dirname "$0")/.." && pwd)"
PY="$DIR/.venv/bin/python"
LABEL="com.jobscraper.runner"
PLIST="$HOME/Library/LaunchAgents/$LABEL.plist"
AGENT_ONLY=0
[ "${1:-}" = "--agent-only" ] && AGENT_ONLY=1

[ -x "$PY" ] || { echo "Missing $PY - create the venv first"; exit 1; }
chmod +x "$DIR/scheduler/"*.sh

# 1. LaunchAgent (runs the job at each slot, and once on wake if a slot was missed)
mkdir -p "$HOME/Library/LaunchAgents"
"$PY" "$DIR/scheduler/generate.py" plist > "$PLIST.tmp"
plutil -lint "$PLIST.tmp" > /dev/null
mv "$PLIST.tmp" "$PLIST"
launchctl bootout "gui/$UID/$LABEL" 2> /dev/null || true
launchctl bootstrap "gui/$UID" "$PLIST"
echo "LaunchAgent installed: $PLIST"

# 2. Wake schedule (needs sudo). Drop old wakes first so changing the interval is clean.
if [ "$AGENT_ONLY" -eq 0 ]; then
  if [ -f "$DIR/scheduler/.scheduled_wakes" ]; then
    sudo "$DIR/scheduler/wakes.sh" cancel
  fi
  "$PY" "$DIR/scheduler/generate.py" wakes > "$DIR/scheduler/.scheduled_wakes"
  sudo "$DIR/scheduler/wakes.sh" apply
  echo "Wake schedule set. Verify with: pmset -g sched"
fi

echo "Done. Interval: $(grep -E '^RUN_INTERVAL_MINUTES=' "$DIR/.env" 2> /dev/null | tail -1 | cut -d= -f2 || true) (default 60 minutes if blank)."
echo "Logs: $DIR/scheduler/runs.log"
