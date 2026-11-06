#!/bin/bash
# Camera & combat slot 2026-11-03 (coordinator's queue): start on the next "TURN DONE shop" after line $1 of locks.md;
# cc_gunfit (Character) + s37 nogm (PC + Character) when it starts before 08:13, else cc_gunfit alone (voice 08:30);
# then the rendered check (gunshot_render.ps1 -Tag gun4, port 7791, LOCK GAMETEST) and "TURN DONE camera".
T='J:/Projets/Unreal_Projects/Guess Who/Tools'
G="$T/gameplay"
LOCKS="$T/agent_logs/locks.md"
N=$1
until tail -n +$((N+1)) "$LOCKS" | grep -q "^TURN DONE ${2:-shop}"; do sleep 15; done
echo "trigger at $(date +%H:%M:%S)"
if [ "$(date +%H%M)" -lt 0813 ]; then
  bash "$G/cc_run.sh" "BP_GW_PlayerController BP_GW_Character" "$G/cc_chain.py" cc_gunfit.py s37_view.py:nogm > /dev/null 2>&1
else
  bash "$G/cc_run.sh" "BP_GW_Character" "$G/cc_chain.py" cc_gunfit.py > /dev/null 2>&1
fi
grep -v "^LogBlueprint\|^\s*$" "$G/logs/cc_last_run.txt" | grep -i "=====\|revolver fit\|compiled\|FAILED\|ERROR\|DSL\|\[\]\|SAVE" | head -20
echo "compiled at $(date +%H:%M:%S)"
if [ "$(date +%H%M)" -lt 0826 ]; then
  CC_STRICT=1 bash "$G/cc_gametest.sh" "J:\Projets\Unreal_Projects\Guess Who\Tools\gameplay\gunshot_render.ps1" -Tag gun4 2>&1 | head -5
fi
echo "TURN DONE camera $(date +%H:%M) (revolver low-ready fit + guest-gun harness; render shots/gun4)" >> "$LOCKS"
echo "done at $(date +%H:%M:%S)"
