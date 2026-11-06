#!/bin/bash
# Full refresh after AssetGen/manifest.json changes (textures, paintings, rugs, props) or script edits.
#   bash Tools/level/update_level.sh
# NOTE: the 'lights' and 'env' parts belong to the lighting agent (Tools/lighting) - never run them from here.
# dress runs first so the arch wall decor sees the current furniture footprints (dress_state.json).
# Props still being generated have reserved slots in dress.py (slot(..., fit=...)): they appear on the next run
# after they are approved in the manifest; markers, audits and lanes already keep their floor free.
cd "$(dirname "$0")/.."
VPY="V:/ComfyUI/ComfyUI/ComfyUI/.venv/Scripts/python.exe"
level/run.sh level/setup_materials.py 2>&1 | grep -E "MIs ok|FAILED|ERROR|Error|rror:" | tail -3
level/run.sh build_manor.py dress 2>&1 | grep -E "dress:|saved|FAILED|ERROR|Error|rror:"
level/run.sh build_manor.py arch markers cams nav settings 2>&1 | grep -E "wall decor|GW_Arch|markers:|review cams|navmesh built|RecastNavMesh|GameMode|saved|FAILED|ERROR|Error|rror:"
level/run.sh level/nav_check.py | tail -2
level/run.sh level/export_instances.py | tail -1
python -I -X utf8 level/validate_offline.py | grep -E "^(duplicate|coplanar|door checks|stairs)"
python -I -X utf8 level/validate_walls.py | sed -n 2,20p
python -I -X utf8 level/audit_furniture.py | head -8
[ -x "$VPY" ] && "$VPY" -I level/lanes_check.py | head -4
