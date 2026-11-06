"""Per-room sound environment in L_Manor (editor script, re-runnable). Supersedes Tools/ui/u30_ambient.py: it removes every
actor tagged GW_Audio and re-places all of them (tag GW_Audio only, never GW_Gen, so level rebuilds keep them).

  python -I -X utf8 Tools\\ui\\ue_run.py Tools\\audio\\room_ambience.py [import] [save]

  import  (re)import AssetGen/audio/final/ambience/AMB_Room_*.wav into /Game/GW/Audio (SC_GW_Ambience, looping) and set the
          music playback volume (MUS_Party 0.8 / MUS_Gramophone 0.7, the brass-free versions; same values as music_volumes.py)
  save    save L_Manor afterwards, only if it had no unsaved changes before this script ran (someone else's work)

Each room gets its beds as non-spatialised AmbientSounds with a BOX attenuation that matches the room (Tools/manor_layout.json)
shrunk by half the falloff, LINEAR falloff over 400 cm: at every wall/door the two rooms cross-fade (each at ~50 %, constant sum)
over +-2 m. Point sources stay spatialised: the gramophone on the ballroom stage, the fireplaces (L_Fire lights).
Levels: beds -27..-34 LUFS at volume <= 1, under the voices (-14..-21 LUFS) and the music."""
import glob
import json
import os

import unreal

EAS = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
EAL = unreal.EditorAssetLibrary
world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
assert world.get_name() == 'L_Manor', f'open level is {world.get_name()}, expected L_Manor'
A = '/Game/GW/Audio'
SRC = r'J:\Projets\Unreal_Projects\Guess Who\AssetGen\audio\final\ambience'
FALLOFF = 400.0
layout = json.load(open(r'J:\Projets\Unreal_Projects\Guess Who\Tools\manor_layout.json', encoding='utf-8'))
rooms = {r['name']: (r['rect'], r.get('height', 500)) for r in layout['rooms']}
args = set(globals().get('UE_ARGS', []))


def map_was_dirty():
    try:
        return any('L_Manor' in p.get_name() for p in unreal.EditorLoadingAndSavingUtils.get_dirty_map_packages())
    except Exception as e:
        print('dirty check unavailable:', e)
        return True


dirty_before = map_was_dirty()

# ------------------------------------------------------------------ assets
if 'import' in args:
    AT = unreal.AssetToolsHelpers.get_asset_tools()
    tasks = []
    for f in sorted(glob.glob(os.path.join(SRC, 'AMB_Room_*.wav'))):
        t = unreal.AssetImportTask()
        t.filename = f; t.destination_path = A; t.destination_name = os.path.splitext(os.path.basename(f))[0]
        t.automated = True; t.replace_existing = True; t.save = False
        tasks.append(t)
    AT.import_asset_tasks(tasks)
    sc = unreal.load_asset(f'{A}/Classes/SC_GW_Ambience.SC_GW_Ambience')
    for t in tasks:
        w = unreal.load_asset(f'{A}/{t.destination_name}')
        w.set_editor_property('sound_class_object', sc)
        w.set_editor_property('looping', True)
        EAL.save_loaded_asset(w, False)
    print('imported', [t.destination_name for t in tasks])
    for name, vol in (('MUS_Party', 0.8), ('MUS_Gramophone', 0.7)):   # brass-free versions since 2026-11-03 (= music_volumes.py)
        w = unreal.load_asset(f'{A}/{name}')
        w.set_editor_property('volume', vol)
        EAL.save_loaded_asset(w, False)
        print('volume', name, vol)

# ------------------------------------------------------------------ actors
removed = 0
for a in EAS.get_all_level_actors():
    if any(str(t) == 'GW_Audio' for t in a.tags):
        EAS.destroy_actor(a); removed += 1


def box(room):
    (x0, y0, x1, y1), h = rooms[room]
    s = unreal.SoundAttenuationSettings()
    s.set_editor_property('attenuate', True)
    s.set_editor_property('spatialize', False)
    s.set_editor_property('attenuation_shape', unreal.AttenuationShape.BOX)
    s.set_editor_property('attenuation_shape_extents',
                          unreal.Vector(max(50.0, (x1 - x0) / 2 - FALLOFF / 2), max(50.0, (y1 - y0) / 2 - FALLOFF / 2), h / 2))
    s.set_editor_property('falloff_distance', FALLOFF)
    s.set_editor_property('distance_algorithm', unreal.AttenuationDistanceModel.LINEAR)
    return s, unreal.Vector((x0 + x1) / 2, (y0 + y1) / 2, h / 2)


def spawn(label, sound, loc, vol, att_asset=None, att_override=None):
    act = EAS.spawn_actor_from_class(unreal.AmbientSound, loc)
    act.set_actor_label(f'GW_Audio_{label}')
    act.set_folder_path('GW_Audio')
    act.tags = [unreal.Name('GW_Audio')]
    ac = act.get_editor_property('audio_component')
    ac.set_editor_property('sound', unreal.load_asset(f'{A}/{sound}'))
    if att_override is not None:
        ac.set_editor_property('override_attenuation', True)
        ac.set_editor_property('attenuation_overrides', att_override)
    elif att_asset:
        ac.set_editor_property('attenuation_settings', unreal.load_asset(f'{A}/{att_asset}'))
    ac.set_editor_property('volume_multiplier', vol)
    ac.set_editor_property('auto_activate', True)
    return act


ROOM_BEDS = {  # room: [(sound, volume)]
    'ballroom': [('AMB_Crowd', 0.75), ('AMB_Glasses', 0.45)],
    'hall': [('AMB_Room_Hall', 0.9)],
    'billiard': [('AMB_Room_Billiard', 0.9), ('AMB_Glasses', 0.4)],
    'dining': [('AMB_Room_Dining', 0.9), ('AMB_Glasses', 0.5)],
    'library': [('AMB_Room_Library', 0.9)],
    'study': [('AMB_Room_Study', 0.9)],
    'conservatory': [('AMB_Room_Conservatory', 0.85), ('AMB_Rain', 0.7)],
    'corridor_w': [('AMB_Room_Corridor', 0.9)],
    'corridor_e': [('AMB_Room_Corridor', 0.9)],
}
placed = []
for room, beds in ROOM_BEDS.items():
    for sound, vol in beds:
        if not EAL.does_asset_exist(f'{A}/{sound}'):
            print('!!! missing', sound, '(run with "import")'); continue
        s, c = box(room)
        spawn(f'{room}_{sound}', sound, c, vol, att_override=s)
        placed.append((room, sound, vol))
# point sources (as before): the gramophone on the ballroom stage (big band, softer now), the fireplaces
spawn('Gramophone_Ballroom', 'MUS_Gramophone', unreal.Vector(3330, 4250, 140), 0.6, att_asset='ATT_GW_Gramophone')
placed.append(('ballroom', 'MUS_Gramophone (point)', 0.6))
fires = [a.get_actor_location() for a in EAS.get_all_level_actors() if a.get_actor_label() == 'L_Fire']
for i, f in enumerate(fires):
    spawn(f'Fireplace_{i}', 'AMB_Fire', unreal.Vector(f.x, f.y, 70.0), 1.4, att_asset='ATT_GW_Fire')
placed.append(('fireplaces', f'AMB_Fire x{len(fires)} (point)', 1.4))
for p in placed:
    print('placed', p)
print('removed', removed, 'GW_Audio actors; placed', len(placed) - 1 + len(fires))

if 'save' in args:
    if dirty_before:
        print('!!! L_Manor had unsaved changes before this script: NOT saved (someone else is editing it)')
    else:
        ok = unreal.EditorLoadingAndSavingUtils.save_current_level()
        print('map saved' if ok else '!!! MAP SAVE FAILED')
else:
    print('map NOT saved (pass "save")')
