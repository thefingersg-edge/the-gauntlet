#!/bin/bash
# Run a long job, stream its output, and RETURN THE PROMPT when it finishes.
#
# The problem this solves: every long run in this project has been launched as
#   nohup ... & tail -f log
# and `tail -f` never exits. The terminal looks busy for hours after the job is
# done, and twice a finished run was reported as "still going" -- once for two
# days. The job was never the thing that was stuck.
#
# This backgrounds the work, tails the log, and kills the tail the moment the
# job exits -- so an idle prompt means finished, not ambiguous. It also prints
# an unmistakable banner, writes a DONE/FAILED sentinel beside the log, and
# raises a macOS notification so you do not have to be watching.
#
#   bash runlog.sh mylog.log bash run_objectives.sh
#   bash runlog.sh spx.log .venv/bin/python train_staged.py --csv ... --tf M15
set -u
LOG="$1"; shift
: > "$LOG"
rm -f "$LOG.DONE" "$LOG.FAILED"

"$@" >> "$LOG" 2>&1 &
JOB=$!
tail -f "$LOG" & TAILER=$!
# Kill the tailer whatever happens -- including Ctrl-C -- so no stray tail
# survives to confuse the next run.
trap 'kill $TAILER 2>/dev/null' EXIT INT TERM

wait "$JOB"; RC=$?
sleep 1                      # let the tailer flush the last lines
kill "$TAILER" 2>/dev/null
wait "$TAILER" 2>/dev/null

echo
if [ "$RC" -eq 0 ]; then
  echo "=============================================================="
  echo "  FINISHED OK  ($(date +'%Y-%m-%d %H:%M'))   log: $LOG"
  echo "=============================================================="
  date > "$LOG.DONE"
  MSG="finished OK"
else
  echo "=============================================================="
  echo "  FAILED rc=$RC  ($(date +'%Y-%m-%d %H:%M'))   log: $LOG"
  echo "  last lines:"
  tail -5 "$LOG" | sed 's/^/    /'
  echo "=============================================================="
  echo "rc=$RC $(date)" > "$LOG.FAILED"
  MSG="FAILED rc=$RC"
fi

printf '\a'                                          # terminal bell
command -v osascript >/dev/null 2>&1 && osascript -e \
  "display notification \"$(basename "$LOG") $MSG\" with title \"pineport\"" \
  >/dev/null 2>&1
exit "$RC"
