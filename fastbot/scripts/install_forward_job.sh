#!/bin/bash
# Installs the v25 forward tick as a launchd agent, runs it once now, and
# shows the heartbeat. Safe to re-run: it unloads any old copy first.
set -eu
HERE="$(cd "$(dirname "$0")" && pwd)"
DST="$HOME/Library/LaunchAgents/com.fastbot.forwardtick.plist"
mkdir -p "$HOME/Library/LaunchAgents"
launchctl bootout "gui/$(id -u)" "$DST" 2>/dev/null || true
cp "$HERE/com.fastbot.forwardtick.plist" "$DST"
plutil -lint "$DST"
launchctl bootstrap "gui/$(id -u)" "$DST"
echo "loaded. first tick running now (RunAtLoad) -- waiting 90s..."
sleep 90
echo "--- heartbeat:";   cat "$HERE/../data/forward_heartbeat.txt"
echo "--- last log lines:"; tail -8 "$HERE/../data/forward_tick.log"
echo "--- launchd:";     launchctl print "gui/$(id -u)/com.fastbot.forwardtick" | grep -E 'state|last exit|runs' || true
