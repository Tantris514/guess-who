"""Ambient sound actors in L_Manor (tag GW_Audio only, never GW_Gen, so the level agent's rebuilds keep them).
Re-runnable: removes the previous GW_Audio actors first. Positions come from Tools/manor_layout.json + the level's fire lights
and the gramophone placement in Tools/level/dress.py (ballroom stage, 3330, 4250).
UE_ARGS: 'save' to save the map afterwards (only do it when nobody else has unsaved changes in L_Manor)."""
import json
import unreal

EAS = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
assert world.get_name() == 'L_Manor', f'open level is {world.get_name()}, expected L_Manor'
A = '/Game/GW/Audio'
layout = json.load(open(r'J:\Projets\Unreal_Projects\Guess Who\Tools\manor_layout.json', encoding='utf-8'))
rooms = {r['name']: r['rect'] for r in layout['rooms']}


def centre(name, z=180.0):
    x0, y0, x1, y1 = rooms[name]
    return unreal.Vector((x0 + x1) / 2, (y0 + y1) / 2, z)


removed = 0
for a in EAS.get_all_level_actors():
    if any(str(t) == 'GW_Audio' for t in a.tags):
        EAS.destroy_actor(a); removed += 1

fires = [a.get_actor_location() for a in EAS.get_all_level_actors() if a.get_actor_label() == 'L_Fire']
SPEC = [  # label, sound, attenuation, location, volume
    ('Gramophone_Ballroom', 'MUS_Gramophone', 'ATT_GW_Gramophone', unreal.Vector(3330, 4250, 140), 0.85),
    ('Crowd_Ballroom', 'AMB_Crowd', 'ATT_GW_Room', centre('ballroom'), 0.75),
    ('Crowd_Hall', 'AMB_Crowd', 'ATT_GW_Room', centre('hall'), 0.6),
    ('Glasses_Bar', 'AMB_Glasses', 'ATT_GW_Room', unreal.Vector(4420, 1650, 150), 0.8),
    ('Glasses_Dining', 'AMB_Glasses', 'ATT_GW_Room', centre('dining'), 0.55),
    ('Rain_Conservatory', 'AMB_Rain', 'ATT_GW_Room', centre('conservatory', 300.0), 0.7),
]
for i, f in enumerate(fires):
    SPEC.append((f'Fireplace_{i}', 'AMB_Fire', 'ATT_GW_Fire', unreal.Vector(f.x, f.y, 70.0), 1.6))

for label, sound, att, loc, vol in SPEC:
    act = EAS.spawn_actor_from_class(unreal.AmbientSound, loc)
    act.set_actor_label(f'GW_Audio_{label}')
    act.set_folder_path('GW_Audio')
    act.tags = [unreal.Name('GW_Audio')]
    ac = act.get_editor_property('audio_component')
    ac.set_editor_property('sound', unreal.load_asset(f'{A}/{sound}'))
    ac.set_editor_property('attenuation_settings', unreal.load_asset(f'{A}/{att}'))
    ac.set_editor_property('volume_multiplier', vol)
    ac.set_editor_property('auto_activate', True)
    print('placed', label, sound, [round(loc.x), round(loc.y), round(loc.z)])
print('removed', removed, 'placed', len(SPEC))
if 'save' in UE_ARGS:
    ok = unreal.EditorLoadingAndSavingUtils.save_current_level()
    print('map saved' if ok else '!!! MAP SAVE FAILED')
else:
    print('map NOT saved (pass "save")')
