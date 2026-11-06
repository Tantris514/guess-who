#!/bin/bash
# Events agent: run editor scripts under the shared locks.
# Usage: ev_slot.sh "<note>" "<assets, /Game paths without the prefix /Game/GW/>" "<script args>" ["<script args>" ...]
# Waits until none of ITS assets (and no GAMETEST / BUILD / HOOKS) is locked, posts its locks, runs the scripts, unlocks.
ROOT="/j/Projets/Unreal_Projects/Guess Who"
T="$ROOT/Tools"
L="$T/agent_logs/locks.md"
note="$1"; ASSETS="$2"; shift 2
scripts=("$@")
rx="GAMETEST|BUILD|HOOKS"; for a in $ASSETS; do rx="$rx|/Game/GW/$a( |$)"; done
post() { for a in $ASSETS; do echo "$1 /Game/GW/$a events $(date +%H:%M)${2:+ ($2)}" >> "$L"; done; }
busy() { python -I -X utf8 "$T/qa/locks_open.py" | grep -v ' events ' | grep -Eq "$rx"; }
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
  python -I -X utf8 "$T/ui/ue_run.py" "$f" "$@" 2>&1 | grep -v "^LogPython: *$" | tail -40 | cut -c1-900
done
post UNLOCK
for a in $ASSETS; do ls -la --time-style=full-iso "$ROOT/GuessWho/Content/GW/$a.uasset" 2>/dev/null | cut -c28-; done
echo "TURN DONE events $(date +%H:%M) ($note)" >> "$L"
echo "=== slot done $(date +%H:%M:%S)"
