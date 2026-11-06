"""Plug generated staff skins (and the waiter's tray) into the shop Blueprints. Runs INSIDE the interactive editor:

  python -I -X utf8 Tools\\ui\\ue_run.py Tools\\chars\\plug_shop_skins.py Barman=char_barman Junkie=char_junkie Waiter=char_waiter [Tray=/Game/.../SM_x] [--dry]

KEY=char_x -> /Game/GW/Blueprints/Shop/BP_GW_<KEY> gets its OWN class-default 'Skin' = /Game/GW/Characters/Gen/char_x/SK_char_x
(Junkie and Waiter are children of Barman, so each CDO is set separately). Tray=<StaticMesh path> sets BP_GW_Waiter's
'TrayMesh'. Each touched BP is compiled and saved. --dry only reports what is there. Post LOCK/UNLOCK lines in
Tools/agent_logs/locks.md around the run (shop BPs are not shared BPs, but other agents read the log).
Shop spec (shop agent): at BeginPlay a valid Skin replaces SKM_Manny_Simple, keeps ABP_Unarmed and hides the placeholder
apron / bow tie / cap; TrayMesh replaces the flat cylinder at mesh-space (-28, 24, 112).
"""
import unreal

EAL = unreal.EditorAssetLibrary
SHOP = "/Game/GW/Blueprints/Shop/BP_GW_"
GEN = "/Game/GW/Characters/Gen"
args = list(UE_ARGS)  # noqa: F821  (injected by ue_run.py)
dry = "--dry" in args
pairs = [a.split("=", 1) for a in args if "=" in a]
tray = next((v for k, v in pairs if k == "Tray"), None)
out = {}
for key, char in pairs:
    if key == "Tray":
        continue
    bp_path = SHOP + key
    sk_path = f"{GEN}/{char}/SK_{char}"
    bp = unreal.load_asset(bp_path) if EAL.does_asset_exist(bp_path) else None
    sk = unreal.load_asset(sk_path) if EAL.does_asset_exist(sk_path) else None
    if bp is None:
        out[key] = "MISSING BP " + bp_path
        continue
    cdo = unreal.get_default_object(bp.generated_class())
    before = cdo.get_editor_property("Skin")
    rep = {"skin_before": before.get_path_name() if before else None}
    if key == "Waiter":
        tm0 = cdo.get_editor_property("TrayMesh")
        rep["tray_before"] = tm0.get_path_name() if tm0 else None
    if sk is None:
        rep["skin"] = "MISSING " + sk_path
        out[key] = rep
        continue
    if not dry:
        cdo.set_editor_property("Skin", sk)
        if key == "Waiter" and tray:
            tm = unreal.load_asset(tray)
            if tm is None:
                rep["tray"] = "MISSING " + tray
            else:
                cdo.set_editor_property("TrayMesh", tm)
                rep["tray"] = tm.get_path_name()
        unreal.BlueprintEditorLibrary.compile_blueprint(bp)
        rep["saved"] = bool(EAL.save_loaded_asset(bp, False))
        cdo = unreal.get_default_object(bp.generated_class())      # re-read after the compile
        now = cdo.get_editor_property("Skin")
        rep["skin_after"] = now.get_path_name() if now else None
    out[key] = rep
print("PLUG", out)
