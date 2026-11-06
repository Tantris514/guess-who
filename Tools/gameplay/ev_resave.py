"""Saves the controllers again when a save failed silently (a -game process held the file). Prints the mtimes and the bank size."""
import os, time, unreal
R = r'J:\Projets\Unreal_Projects\Guess Who\GuessWho\Content\GW\Blueprints'
for n in UE_ARGS or ('BP_GW_KamikazeController', 'BP_GW_BanditController'):
    a = unreal.load_asset('/Game/GW/Blueprints/' + n)
    ok = unreal.EditorAssetLibrary.save_loaded_asset(a, False)
    print(n, 'saved', ok, time.ctime(os.path.getmtime(os.path.join(R, n + '.uasset'))), os.path.getsize(os.path.join(R, n + '.uasset')))
gs = unreal.get_default_object(unreal.load_object(None, '/Game/GW/Blueprints/BP_GW_GameState.BP_GW_GameState_C'))
gm = unreal.get_default_object(unreal.load_object(None, '/Game/GW/Blueprints/BP_GW_GameMode.BP_GW_GameMode_C'))
print('bank GS', len(gs.get_editor_property('BankSounds')), 'GM', len(gm.get_editor_property('VBDur')), 'once kamikaze/greet', gm.get_editor_property('VCatOnce')[12], gm.get_editor_property('VCatOnce')[16])
