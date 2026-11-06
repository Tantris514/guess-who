"""Second waiter look: BP_GW_Waiter2 is a child of BP_GW_Waiter that only changes the class default Skin (char_waiter2).
GameMode.SpawnVendors (s34_shop.py) spawns one BP_GW_Waiter and one BP_GW_Waiter2. Server-chosen class, so every client sees the same look.
Run with ue_run.py, inside the interactive editor. Idempotent."""
import unreal
EAL = unreal.EditorAssetLibrary
SHOP = '/Game/GW/Blueprints/Shop'
path = SHOP + '/BP_GW_Waiter2'
parent = unreal.load_asset(SHOP + '/BP_GW_Waiter')
if EAL.does_asset_exist(path):
    bp = unreal.load_asset(path)
else:
    f = unreal.BlueprintFactory()
    f.set_editor_property('parent_class', parent.generated_class())
    bp = unreal.AssetToolsHelpers.get_asset_tools().create_asset('BP_GW_Waiter2', SHOP, unreal.Blueprint, f)
sk = unreal.load_asset('/Game/GW/Characters/Gen/char_waiter2/SK_char_waiter2')
cdo = unreal.get_default_object(bp.generated_class())
cdo.set_editor_property('Skin', sk)
unreal.BlueprintEditorLibrary.compile_blueprint(bp)
saved = bool(EAL.save_loaded_asset(bp, False))
cdo = unreal.get_default_object(bp.generated_class())
print('WAITER2', {'saved': saved, 'skin': cdo.get_editor_property('Skin').get_path_name(),
                  'tray': (cdo.get_editor_property('TrayMesh').get_path_name() if cdo.get_editor_property('TrayMesh') else None),
                  'mobile': cdo.get_editor_property('Mobile'), 'kind': cdo.get_editor_property('VendorKind')})
