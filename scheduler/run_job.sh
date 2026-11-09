#!/bin/bash
# Wrapper started by launchd. Waits for Wi-Fi, keeps the Mac awake while the scraper runs,
# and logs power/network state to scheduler/runs.log (useful for the lid-closed battery test).
DIR="$(cd "$(dirname "$0")/.." && pwd)"
LOG="$DIR/scheduler/runs.log"
PY="$DIR/.venv/bin/python"

power_state() { pmset -g batt | sed -n '1p;2p' | tr '\n' ' ' | tr -s ' \t' ' '; }

# Skip if a previous run is still going
if pgrep -f "$PY main.py" > /dev/null; then
  echo "$(date '+%F %T') SKIP  previous run still running" >> "$LOG"
  exit 0
fi

START=$(date +%s)
echo "$(date '+%F %T') START | $(power_state)" >> "$LOG"

# Wait up to ~90s for the network (Wi-Fi can take a few seconds after a wake)
NET="down"
for _ in $(seq 1 30); do
  if curl -s -m 3 -o /dev/null https://www.google.com; then NET="up"; break; fi
  sleep 3
done
echo "$(date '+%F %T') NET   | $NET (after $(( $(date +%s) - START ))s)" >> "$LOG"

cd "$DIR" || exit 1
# caffeinate: -i blocks idle sleep, -s blocks system sleep (the latter only works on AC power)
/usr/bin/caffeinate -i -s "$PY" main.py > "$DIR/scheduler/last_run.log" 2>&1
CODE=$?

echo "$(date '+%F %T') END   | exit=$CODE duration=$(( $(date +%s) - START ))s | $(power_state)" >> "$LOG"
exit $CODE
