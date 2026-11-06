"""Cast of generated characters (Tools/chars/rig_character.py): every guest and NPC is one of them.

Approved, rigged manifest characters with "outfits": "roster" form the cast, in manifest order; the one with
"outfits": "detective" is the seeker's look. OutfitIndex is now an index into the cast:
  BP_GW_Character.GenChars / GenNames (display_name, shown by the dev menu) / GenIds (character id = its voice id,
  read by the voice director s39_voice_director.py) / GenDetective,
  BP_GW_GameMode.NumOutfits = cast size (NPCs and players draw from it),
  GenGhostMats / GenDetectiveGhostMat: each one's blue see-through ghost material (M_GW_Ghost, gen_material.py).
Event characters: "outfits": "bandit" | "kamikaze" | "robot" | "bandit2" fill BP_GW_Character.SpecialMeshes
  [_, bandit, kamikaze, robot, bandit2] (s32_events.py ApplySpecialLook; bandit2 = second bandit look, Variant 1);
  a missing one stays the plain mannequin (bandit2 falls back to bandit).
`clear` restores the old mannequin + costume pool (32 outfits), kept only for A/B comparisons.
Usage: ue_run.py s29_gen_chars.py [clear]
"""
import sys, importlib, json
sys.path.insert(0, r'J:\Projets\Unreal_Projects\Guess Who\Tools\gameplay')
import gw_lib; importlib.reload(gw_lib)
from gw_lib import *
import voice_bank as VB; importlib.reload(VB)

sys.path.insert(0, r'J:\Projets\Unreal_Projects\Guess Who\Tools\chars')
import gen_material as GM; importlib.reload(GM)

MAN = json.load(open(r'J:\Projets\Unreal_Projects\Guess Who\AssetGen\manifest.json', encoding='utf-8'))
ch = load_bp('BP_GW_Character')
gm = load_bp('BP_GW_GameMode')
ensure_var(ch, 'GenNames', 'string', array=True, category='Costume')
ensure_var(ch, 'GenIds', 'string', array=True, category='Costume')      # voice = character (s39_voice_director.py)
ensure_var(ch, 'GenGhostMats', obj_class=unreal.MaterialInterface, array=True, category='Costume')
ensure_var(ch, 'GenDetectiveGhostMat', obj_class=unreal.MaterialInterface, category='Costume')
compile_bp(ch, quiet=True)
c = cdo(ch)
cast, names, det, ids = [], [], None, []
ghosts, det_ghost, female = [], None, []
SPECIAL = {'bandit': 1, 'kamikaze': 2, 'robot': 3, 'bandit2': 4}
manny = unreal.load_asset('/Game/Characters/Mannequins/Meshes/SKM_Manny_Simple')
special = [None] * 5


def ghost_mat(e, sk):
    """Blue see-through twin of the character's material (s30_ghost.py dresses the ghost with it)."""
    folder = sk.get_path_name().rsplit('/', 1)[0]
    src = sk.materials[0].material_interface if sk.materials else None
    tex = unreal.MaterialEditingLibrary.get_material_instance_texture_parameter_value(src, 'BaseColor') \
        if isinstance(src, unreal.MaterialInstance) else None
    return GM.ghost_instance(e['name'], folder, tex)
if not (UE_ARGS and UE_ARGS[0] == 'clear'):
    for e in MAN['assets']:
        if e.get('kind') != 'character' or e.get('status') != 'approved' or not e.get('rig'):
            continue
        sk = unreal.load_asset(e['rig']['skeletal_mesh'])
        if e.get('outfits') == 'detective':
            det = sk
            det_ghost = ghost_mat(e, sk)
        elif e.get('outfits') in SPECIAL:
            special[SPECIAL[e['outfits']]] = sk
        elif e.get('outfits') == 'roster':
            cast.append(sk)
            names.append(e.get('display_name', e['name']))
            ids.append(VB.voice_id(e))                          # its own char id, or the existing voice it borrows (manifest "voice")
            ghosts.append(ghost_mat(e, sk))
            female.append(e.get('body') == 'quinn')
# OutfitIndex 32 means "the detective's look on a guest" (s26 ApplyLook, s38, dev menu): with more than 32 guests that slot holds the detective, GM.NextOutfit never draws it
if len(cast) > 32 and det:
    cast.insert(32, det); names.insert(32, 'Le détective'); ids.insert(32, 'char_detective'); ghosts.insert(32, det_ghost); female.insert(32, False)
c.set_editor_property('GenChars', cast)
c.set_editor_property('GenNames', names)
c.set_editor_property('GenIds', ids)
c.set_editor_property('GenDetective', det)
c.set_editor_property('GenGhostMats', ghosts)
c.set_editor_property('GenDetectiveGhostMat', det_ghost)
c.set_editor_property('GenFemale', female)                       # voices (s31_reactions.py GenderOf)
special[4] = special[4] or special[1]
c.set_editor_property('SpecialMeshes', [m or manny for m in special])
compile_bp(ch, quiet=True)
save(ch)
cdo(gm).set_editor_property('NumOutfits', len(cast) if cast else 32)
compile_bp(gm, quiet=True)
save(gm)
print('special', [m.get_name() if m else '(mannequin)' for m in special])
print('cast', list(zip(names, [s.get_name() for s in cast])), 'detective', det.get_name() if det else None,
      'NumOutfits', cdo(gm).get_editor_property('NumOutfits'))
