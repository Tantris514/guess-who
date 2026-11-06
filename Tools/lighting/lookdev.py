"""Look-dev entry (runs inside the editor): rebuild only the lighting/atmosphere, optionally save.

  python -I -X utf8 Tools/level/ue_main.py Tools/lighting/lookdev.py [lights] [env] [tune] [pp] [mats] [save]
  (no part = lights env)
"""
import importlib
import os
import sys

import unreal

ROOT = r"J:\Projets\Unreal_Projects\Guess Who"
sys.path.insert(0, os.path.join(ROOT, "Tools", "lighting"))
import rig  # noqa: E402

importlib.reload(rig)
ARGS = [a.lower() for a in globals().get("UE_ARGS", [])]
parts = [a for a in ARGS if a != "save"] or ["lights", "env"]
world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
assert world.get_path_name().split(".")[0] == "/Game/GW/Maps/L_Manor", world.get_path_name()
if "lights" in parts:
    print("  cleared", rig.clear("GW_Light"), "GW_Light")
    rig.build_lights(save_materials=True)
if "env" in parts:
    print("  cleared", rig.clear("GW_Env"), "GW_Env")
    rig.build_env()
if "pp" in parts and "env" not in parts:
    rig.clear("GW_Env", ["PP_"])
    rig.post_process()
if "fog" in parts and "env" not in parts:
    rig.clear("GW_Env", ["L_Moon", "SkyLight", "Fog_", "Haze_"])
    rig._moon_and_sky()
    rig._haze()
if "tune" in parts and "lights" not in parts:
    rig.tune_dress_lights()
if "mats" in parts and "lights" not in parts:
    rig.apply_fixture_materials()
if "save" in ARGS:
    unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).save_current_level()
    print("saved L_Manor")
