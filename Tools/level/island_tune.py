"""(in editor) Look tuning of the storm-island instances without rebuilding the masters (fast).
  level/run.sh level/island_tune.py
"""
import unreal

mel = unreal.MaterialEditingLibrary
eal = unreal.EditorAssetLibrary
ENV = "/Game/GW/Environment"
TUNE = {
    # at night the panes mirrored the lit rooms and hid the storm: weaker, slightly blurred reflections, finer drops
    "MI_GW_WindowGlass": dict(s={"Opacity": 0.04, "DropOpacity": 0.12, "DropStrength": 0.35, "Specular": 0.12,
                                 "Roughness": 0.09}),
    "MI_GW_Island": dict(s={"RockTile": 820.0, "NormalStrength": 0.55},
                         v={"RockTint": (0.55, 0.55, 0.58), "GrassTint": (0.55, 0.6, 0.55), "GravelTint": (0.5, 0.48, 0.45)}),
    "MI_GW_RainCurtain": dict(s={"Base": 0.05, "FlashBoost": 3.0}),
    "MI_GW_Sea": dict(s={"FoamAmount": 1.8, "FoamGlow": 0.01}),
}
for name, t in TUNE.items():
    mi = unreal.load_asset(f"{ENV}/{name}")
    if mi is None:
        print("  missing", name)
        continue
    for k, v in t.get("s", {}).items():
        mel.set_material_instance_scalar_parameter_value(mi, k, v)
    for k, v in t.get("v", {}).items():
        mel.set_material_instance_vector_parameter_value(mi, k, unreal.LinearColor(v[0], v[1], v[2], 1.0))
    mel.update_material_instance(mi)
    eal.save_loaded_asset(mi)
bp = unreal.load_asset(f"{ENV}/BP_GW_Storm")
cdo = unreal.get_default_object(bp.generated_class())
cdo.set_editor_property("BoltLux", 120.0)
eal.save_loaded_asset(bp)
print("  island tuned")
# the placed storm actor (L_Manor_Island) keeps its own copy of BoltLux: update it and save the sublevel
eas = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
les = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
storms = [a for a in eas.get_all_level_actors() if a.get_class().get_name() == "BP_GW_Storm_C"]
for a in storms:
    a.set_editor_property("BoltLux", 120.0)
if storms and les.set_current_level_by_name("L_Manor_Island"):
    try:
        les.save_current_level()
        print("  storm actor updated, L_Manor_Island saved")
    finally:
        les.set_current_level_by_name("L_Manor")
