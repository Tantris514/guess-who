#!/bin/bash
# Camera & combat agent: run an editor script with lock lines, retrying while the shared editor is busy.
# Usage: bash cc_run.sh "<asset names to lock, space-separated>" <script.py> [args...]
T='J:/Projets/Unreal_Projects/Guess Who/Tools'
LOCKS="$T/agent_logs/locks.md"
assets="$1"; shift
paths=""
for a in $assets; do paths="$paths /Game/GW/Blueprints/$a"; done
until python -I -X utf8 "$T/gameplay/locks_free.py" $assets >/dev/null; do sleep 10; done
for p in $paths; do echo "LOCK $p camera-combat $(date +%H:%M)" >> "$LOCKS"; done
for i in $(seq 1 30); do
  out=$(python -I -X utf8 "$T/ui/ue_run.py" "$@" 2>&1)
  if echo "$out" | grep -q "interactive editor not found\|ConnectionResetError"; then sleep 15; continue; fi
  break
done
echo "$out" > "$T/gameplay/logs/cc_last_run.txt"
echo "$out" | grep -v "^LogBlueprint\|^\s*$" | tail -60
for p in $paths; do echo "UNLOCK $p camera-combat $(date +%H:%M)" >> "$LOCKS"; done
