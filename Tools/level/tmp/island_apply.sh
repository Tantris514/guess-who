#!/bin/bash
cd "J:/Projets/Unreal_Projects/Guess Who/Tools"
echo "== island level $(date +%H:%M)"
level/run.sh level/island_build.py level 2>&1 | grep -vi deprecat | grep -E "island|sublevel|saved|removed|cleared|!!|rror|FAILED|Traceback|line [0-9]|Exception|waiting"
echo "== arch $(date +%H:%M)"
level/run.sh build_manor.py arch 2>&1 | grep -E "wall decor|GW_Arch|saved|FAILED|ERROR|Error|rror:|waiting"
echo "== checks $(date +%H:%M)"
level/run.sh level/nav_check.py | tail -2
level/run.sh level/export_instances.py | tail -1
python -I -X utf8 level/validate_offline.py | grep -E "^(duplicate|coplanar|door checks)"
python -I -X utf8 level/validate_walls.py | sed -n 2,6p
python -I -X utf8 level/audit_furniture.py | head -6
"V:/ComfyUI/ComfyUI/ComfyUI/.venv/Scripts/python.exe" -I level/lanes_check.py | sed 's/\[.*\]//' | head -5
echo "== done $(date +%H:%M)"
