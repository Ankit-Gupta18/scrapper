#!/bin/bash
# Must run as root (called through sudo by install.sh / uninstall.sh).
#   wakes.sh apply   -> schedule every wake time listed in scheduler/.scheduled_wakes
#   wakes.sh cancel  -> cancel exactly those wake times (other apps' events are left alone)
DIR="$(cd "$(dirname "$0")" && pwd)"
LIST="$DIR/.scheduled_wakes"
[ -f "$LIST" ] || { echo "No wake list found ($LIST)"; exit 0; }

case "$1" in
  apply)  CMD="schedule" ;;
  cancel) CMD="schedule cancel" ;;
  *) echo "usage: $0 apply|cancel"; exit 1 ;;
esac

COUNT=0
while IFS= read -r when; do
  [ -z "$when" ] && continue
  pmset $CMD wake "$when" "jobscraper" > /dev/null 2>&1 && COUNT=$((COUNT + 1))
done < "$LIST"
echo "wake events processed ($1): $COUNT"
