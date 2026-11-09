#!/bin/bash
# Full rollback: removes the LaunchAgent and cancels the wake events this project scheduled.
#   Usage: bash scheduler/uninstall.sh
DIR="$(cd "$(dirname "$0")/.." && pwd)"
LABEL="com.jobscraper.runner"
PLIST="$HOME/Library/LaunchAgents/$LABEL.plist"

launchctl bootout "gui/$UID/$LABEL" 2> /dev/null || true
rm -f "$PLIST"
echo "LaunchAgent removed."

if [ -f "$DIR/scheduler/.scheduled_wakes" ]; then
  sudo "$DIR/scheduler/wakes.sh" cancel
  rm -f "$DIR/scheduler/.scheduled_wakes"
  echo "Wake events cancelled. Verify with: pmset -g sched"
fi
echo "Rolled back. (Logs in scheduler/ were kept.)"
