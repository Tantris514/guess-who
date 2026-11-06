"""Append ONE rigged character to the live cast without pulling every other "roster" entry of the manifest (s29_gen_chars.py rebuilds the
whole cast from the manifest; on 2026-11-05 that would also have added 13 rigged Creator characters nobody asked to integrate yet).
Usage: ue_run.py add_to_roster.py char_x   Idempotent. Same arrays and ghost material as s29; a later full s29 keeps the character (manifest "outfits": "roster")."""
import sys, importlib, json
sys.path.insert(0, r'J:/Projets/Unreal_Projects/Guess Who/Tools/gameplay')
import gw_lib; importlib.reload(gw_lib)
from gw_lib import *
sys.path.insert(0, r'J:/Projets/Unreal_Projects/Guess Who/Tools/chars')
import gen_material as GM; importlib.reload(GM)
MAN = json.load(open(r'J:/Projets/Unreal_Projects/Guess Who/AssetGen/manifest.json', encoding='utf-8'))
ch, gm = load_bp('BP_GW_Character'), load_bp('BP_GW_GameMode')
c = cdo(ch)
for name in UE_ARGS:
    e = next(x for x in MAN['assets'] if x['name'] == name)
    assert e.get('outfits') == 'roster' and e.get('rig'), name
    sk = unreal.load_asset(e['rig']['skeletal_mesh'])
    cast = list(c.get_editor_property('GenChars'))
    if sk in cast:
        print('already in cast', name)
        continue
    src = sk.materials[0].material_interface
    tex = unreal.MaterialEditingLibrary.get_material_instance_texture_parameter_value(src, 'BaseColor')
    ghost = GM.ghost_instance(name, sk.get_path_name().rsplit('/', 1)[0], tex)
    for prop, val in (('GenChars', sk), ('GenNames', e.get('display_name', name)), ('GenIds', name), ('GenGhostMats', ghost), ('GenFemale', e.get('body') == 'quinn')):
        a = list(c.get_editor_property(prop)); a.append(val); c.set_editor_property(prop, a)
compile_bp(ch, quiet=True); save(ch)
n = len(c.get_editor_property('GenChars'))
cdo(gm).set_editor_property('NumOutfits', n)
compile_bp(gm, quiet=True); save(gm)
print('ROSTERDONE', n, list(cdo(ch).get_editor_property('GenNames')), 'NumOutfits', cdo(gm).get_editor_property('NumOutfits'))
