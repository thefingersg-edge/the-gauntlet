#!/bin/bash
# Installs the fastbot weekly job as a launchd agent, runs it once now, and
# shows the heartbeat. Safe to re-run: it unloads any old copy first.
set -eu
HERE="$(cd "$(dirname "$0")" && pwd)"
DST="$HOME/Library/LaunchAgents/com.fastbot.weeklyjob.plist"
mkdir -p "$HOME/Library/LaunchAgents"
launchctl bootout "gui/$(id -u)" "$DST" 2>/dev/null || true
cp "$HERE/com.fastbot.weeklyjob.plist" "$DST"
plutil -lint "$DST"
launchctl bootstrap "gui/$(id -u)" "$DST"
echo "loaded. first run now (RunAtLoad) -- waiting 90s..."
sleep 90
echo "--- heartbeat:";   cat "$HERE/../data/weekly_heartbeat.txt"
echo "--- last log lines:"; tail -8 "$HERE/../data/weekly_job.log"
echo "--- launchd:";     launchctl print "gui/$(id -u)/com.fastbot.weeklyjob" | grep -E 'state|last exit|runs' || true
