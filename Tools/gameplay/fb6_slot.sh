#!/bin/bash
# One slot of feedback6's compiles: fb6_slot.sh "<script args>" ...  each argument = a Tools-relative script plus args. Takes the Blueprint locks for the whole slot. Do not run it under `timeout`: it would leave locks open.
TOOLS="/j/Projets/Unreal_Projects/Guess Who/Tools"
L="$TOOLS/agent_logs/locks.md"
BPS="/Game/GW/Blueprints/BP_GW_GameMode /Game/GW/Blueprints/BP_GW_PlayerController /Game/GW/Blueprints/BP_GW_PlayerState /Game/GW/Blueprints/BP_GW_KamikazeController /Game/GW/Blueprints/Shop/BP_GW_Barman /Game/GW/UI/WBP_HUD /Game/GW/UI/WBP_Inventory /Game/GW/UI/WBP_DevMenu /Game/GW/UI/WBP_Shop /Game/GW/Blueprints/BP_GW_Character /Game/GW/Blueprints/BP_GW_GameState /Game/GW/UI/BP_GW_Settings /Game/GW/UI/WBP_MainMenu /Game/GW/UI/WBP_GameSetup"
until [ "$(python -I -X utf8 "$TOOLS/qa/locks_open.py")" = "free" ]; do sleep 10; done
for b in $BPS; do echo "LOCK $b feedback6 $(date +%H:%M) (feedback6 slot)" >> "$L"; done
for job in "$@"; do
  set -- $job
  s="$1"; shift
  echo "=== $s $* $(date +%H:%M:%S)"
  python -I -X utf8 "$TOOLS/ui/ue_run.py" "J:/Projets/Unreal_Projects/Guess Who/Tools/$s" "$@" 2>&1 | grep -v "^LogPython\|^$" | cut -c1-400 | tail -n 40
done
for b in $BPS; do echo "UNLOCK $b feedback6 $(date +%H:%M)" >> "$L"; done
echo "=== slot done $(date +%H:%M:%S)"
