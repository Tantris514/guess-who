"""Re-save only /Game/GW/Blueprints/Pickups (after a save failed while a -game test held the files)."""
import unreal
EAL = unreal.EditorAssetLibrary
for p in sorted(EAL.list_assets('/Game/GW/Blueprints/Pickups', recursive=False)):
    a = unreal.load_asset(p.split('.')[0])
    if isinstance(a, unreal.Blueprint) and 'DslTest' not in p:
        unreal.BlueprintEditorLibrary.compile_blueprint(a)
    print('saved' if EAL.save_loaded_asset(a, only_if_is_dirty=False) else '!!! SAVE FAILED', p)
