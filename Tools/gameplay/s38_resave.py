"""Re-save the s38 assets after a failed save (Error Code 32: a -game test held the files)."""
import unreal
EAL = unreal.EditorAssetLibrary
for p in ['/Game/GW/Blueprints/BP_GW_GameMode', '/Game/GW/Blueprints/BP_GW_PlayerController', '/Game/GW/Blueprints/BP_GW_PlayerState',
          '/Game/GW/Blueprints/Pickups/BP_GW_HeldSword', '/Game/GW/Blueprints/Pickups/BP_GW_ThrownBall',
          '/Game/GW/Blueprints/Pickups/BP_GW_Pickup', '/Game/GW/Blueprints/Pickups/BP_GW_SwapGhost',
          '/Game/GW/Blueprints/Pickups/BP_GW_FPItems', '/Game/GW/UI/WBP_DevMenu']:
    a = unreal.load_asset(p)
    if isinstance(a, unreal.Blueprint):
        unreal.BlueprintEditorLibrary.compile_blueprint(a)
    ok = EAL.save_loaded_asset(a, only_if_is_dirty=False)
    print('saved' if ok else '!!! SAVE FAILED', p)
