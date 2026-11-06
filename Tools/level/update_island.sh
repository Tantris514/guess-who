#!/bin/bash
# Storm-island exterior (always-loaded sublevel /Game/GW/Maps/L_Manor_Island) - full refresh:
#   bash Tools/level/update_island.sh
# 1. offline sources: island_src/gen/build_all.py (meshes/textures/audio, only if missing) + island_layout.py
# 2. editor: textures + MPC + masters (island_materials.py), nightsky master (ue_materials.py nightsky),
#    meshes + audio + level (island_build.py), storm BP (island_storm_bp.py), then the arch part so the windows get
#    the rain glass (build_manor.py arch) and the usual checks.
# level/run.sh waits for LOCK BUILD / LOCK HOOKS in agent_logs/locks.md and for a busy editor.
cd "$(dirname "$0")/.."
VPY="V:/ComfyUI/ComfyUI/ComfyUI/.venv/Scripts/python.exe"
[ -f level/island_src/meshes/SM_GW_Island.obj ] || "$VPY" -I level/island_src/gen/build_all.py | tail -3
"$VPY" -I level/island_layout.py | tail -1
python -I -X utf8 level/hlsl_check.py level/island_materials.py | grep -v " OK$"
python -I -X utf8 level/hlsl_check.py | grep -v " OK$"
level/run.sh level/island_materials.py 2>&1 | grep -E "island|!!|rror|FAILED"
level/run.sh ue_materials.py nightsky 2>&1 | grep -E "built|rror|FAILED"
level/run.sh level/island_build.py mesh audio 2>&1 | grep -E "island|!!|rror|FAILED"
level/run.sh level/island_storm_bp.py 2>&1 | grep -E "BP_GW_Storm|COMPILE|ERR|DSL|rror"
level/run.sh level/island_build.py level 2>&1 | grep -E "island|sublevel|saved|removed|cleared|!!|rror|FAILED"
level/run.sh build_manor.py arch 2>&1 | grep -E "wall decor|GW_Arch|saved|FAILED|ERROR|Error|rror:"
level/run.sh level/nav_check.py | tail -2
level/run.sh level/export_instances.py | tail -1
python -I -X utf8 level/validate_offline.py | grep -E "^(duplicate|coplanar|door checks)"
python -I -X utf8 level/validate_walls.py | sed -n 2,6p
python -I -X utf8 level/audit_furniture.py | head -6
