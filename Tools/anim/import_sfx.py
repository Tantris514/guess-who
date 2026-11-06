"""Imports the social SFX (Tools/anim/sfx/*.wav, made by social_sfx.py) into /Game/GW/Audio/Social with the SFX sound
class and the room attenuation (heard in the room and the next one). Editor: ue_run.py Tools/anim/import_sfx.py
Re-runnable (re-imports a file only when it changed)."""
import glob
import os

import unreal

SRC = r'J:\Projets\Unreal_Projects\Guess Who\Tools\anim\sfx'
DEST = '/Game/GW/Audio/Social'
EAL = unreal.EditorAssetLibrary
AT = unreal.AssetToolsHelpers.get_asset_tools()
sc = unreal.load_asset('/Game/GW/Audio/Classes/SC_GW_SFX')
att = unreal.load_asset('/Game/GW/Audio/ATT_GW_Room')
for path in sorted(glob.glob(os.path.join(SRC, '*.wav'))):
    name = os.path.splitext(os.path.basename(path))[0]
    dest = f'{DEST}/{name}'
    stamp = f'{os.path.getsize(path)}|{int(os.path.getmtime(path))}'
    if EAL.does_asset_exist(dest) and EAL.get_metadata_tag(unreal.load_asset(dest), 'GWSrcStamp') == stamp:
        print('up to date', dest)
        continue
    t = unreal.AssetImportTask()
    t.filename = path
    t.destination_path = DEST
    t.automated = True
    t.replace_existing = True
    t.save = False
    AT.import_asset_tasks([t])
    s = unreal.load_asset(dest)
    EAL.set_metadata_tag(s, 'GWSrcStamp', stamp)
    if sc:
        s.set_editor_property('sound_class_object', sc)
    if att:
        s.set_editor_property('attenuation_settings', att)
    EAL.save_loaded_asset(s, False)
    print('imported', dest, round(s.get_editor_property('duration'), 2), 's')
