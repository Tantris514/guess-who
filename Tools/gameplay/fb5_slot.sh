#!/bin/bash
# feedback5 agent: run editor scripts under the shared locks (same logic as ev_slot.sh).
# Usage: fb5_slot.sh "<note>" "<assets, /Game paths without the prefix /Game/GW/>" "<script args>" ["<script args>" ...]
ROOT="/j/Projets/Unreal_Projects/Guess Who"
T="$ROOT/Tools"
L="$T/agent_logs/locks.md"
note="$1"; ASSETS="$2"; shift 2
scripts=("$@")
rx="GAMETEST|BUILD|HOOKS"; for a in $ASSETS; do rx="$rx|/Game/GW/$a( |$)"; done
post() { for a in $ASSETS; do echo "$1 /Game/GW/$a feedback5 $(date +%H:%M)${2:+ ($2)}" >> "$L"; done; }
busy() { python -I -X utf8 "$T/qa/locks_open.py" | grep -v ' feedback5 ' | grep -Eq "$rx"; }
while true; do
  while busy; do sleep 5; done
  post LOCK "$note"
  sleep 3
  busy || break
  post UNLOCK "withdrawn: another lock came first"
  sleep 25
done
for s in "${scripts[@]}"; do
  echo "=== $(date +%H:%M:%S) $s"
  set -- $s; f="J:/Projets/Unreal_Projects/Guess Who/Tools/$1"; shift
  python -I -X utf8 "$T/ui/ue_run.py" "$f" "$@" 2>&1 | grep -v "^LogPython: *$" | grep -v "^ *$" | tail -30 | cut -c1-700
done
post UNLOCK
for a in $ASSETS; do ls -la --time-style=full-iso "$ROOT/GuessWho/Content/GW/$a.uasset" 2>/dev/null | cut -c28-; done
echo "=== slot done $(date +%H:%M:%S)"
