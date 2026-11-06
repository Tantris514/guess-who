#!/bin/bash
# Camera & combat agent: run a game test (headless or rendered) under LOCK GAMETEST, when no other GAMETEST, BUILD or
# HOOKS lock is open; CC_STRICT=1 also waits while any /Game asset is LOCKed (a -game process holding .uasset files
# makes compile saves fail with Error 32). After locking, re-reads locks.md: if another open LOCK GAMETEST line comes
# before ours (same-minute race), releases and waits again.  Usage: bash cc_gametest.sh <ps1 script> [ps1 args...]
T='J:/Projets/Unreal_Projects/Guess Who/Tools'
LOCKS="$T/agent_logs/locks.md"
check() {   # $1 = busy | first
  python -I -X utf8 - "$LOCKS" "$1" <<'PY'
import sys, os
STRICT = os.environ.get('CC_STRICT') == '1'
held, order = {}, []
for line in open(sys.argv[1], encoding='utf-8', errors='replace'):
    p = line.split()
    if len(p) < 3 or p[0] not in ('LOCK', 'UNLOCK'):
        continue
    if p[0] == 'LOCK':
        held[p[1]] = p[2]
        if p[1] == 'GAMETEST':
            order.append(p[2])
    else:
        held.pop(p[1], None)
        if p[1] == 'GAMETEST' and p[2] in order:
            order.remove(p[2])
if sys.argv[2] == 'first':                       # are we the earliest open GAMETEST holder?
    sys.exit(0 if order and order[0] == 'camera-combat' else 1)
b = {a: w for a, w in held.items() if (a in ('BUILD', 'HOOKS', 'GAMETEST') or (STRICT and a.startswith('/Game/'))) and w != 'camera-combat'}
sys.exit(1 if b else 0)
PY
}
while true; do
  until check busy; do sleep 15; done
  echo "LOCK GAMETEST camera-combat $(date +%H:%M)" >> "$LOCKS"
  sleep 3
  if check first; then break; fi
  echo "UNLOCK GAMETEST camera-combat $(date +%H:%M) (race: another GAMETEST came first, waiting)" >> "$LOCKS"
  sleep 20
done
powershell -NoProfile -ExecutionPolicy Bypass -File "$@"
echo "UNLOCK GAMETEST camera-combat $(date +%H:%M)" >> "$LOCKS"
