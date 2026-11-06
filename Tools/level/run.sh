#!/bin/bash
# usage: level/run.sh <script.py relative to Tools> [args...]   (runs in the interactive shared editor only)
# Waits while Tools/agent_logs/locks.md holds a LOCK BUILD / HOOKS / GAMETEST (last line of each kind), then retries
# (up to ~40 min) while the editor is busy with another agent's command (no remote-exec answer).
T="J:/Projets/Unreal_Projects/Guess Who/Tools"
S="$1"; shift
locked() {
    for kind in BUILD HOOKS GAMETEST; do
        last=$(grep -E "^(LOCK|UNLOCK) $kind" "$T/agent_logs/locks.md" 2>/dev/null | tail -1)
        case "$last" in LOCK*) echo "$last"; return 0;; esac
    done
    return 1
}
for i in $(seq 1 720); do                      # up to 2 h; free = unlocked on two checks 5 s apart (UNLOCK/LOCK pairs)
    if ! l=$(locked); then
        sleep 5
        locked >/dev/null || break
        continue
    fi
    [ "$i" -eq 1 ] && echo "waiting: $l" >&2
    sleep 10
done
if locked >/dev/null; then echo "ERROR: still locked: $(locked)"; exit 4; fi
for i in $(seq 1 80); do
    out=$(python -I -X utf8 "$T/level/ue_main.py" "$T/$S" "$@" 2>&1); rc=$?
    if [ $rc -eq 3 ] && echo "$out" | grep -q "interactive editor not found"; then
        sleep 10
        continue
    fi
    # another client's command was running: the connection was reset before ours ran (scripts are idempotent)
    if echo "$out" | tail -3 | grep -q "ConnectionResetError\|ConnectionRefusedError\|ConnectionAbortedError"; then
        echo "retry after connection reset ($i)" >&2
        sleep 20
        continue
    fi
    echo "$out"
    exit $rc
done
echo "ERROR: interactive editor not found (gave up after retries)"
exit 3
