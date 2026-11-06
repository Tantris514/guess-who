"""Imports the approved props (dress.import_props) and places the ones with reserved slots in the frozen L_Manor, with
dress.slot's own scale and fit maths. Positions copy build_dress. Re-runnable: removes its own actors (tag GW_NewProp)
first. Args: "dry" = report overlaps, change nothing; "nonav" = skip BuildPaths.
Usage: python -I -X utf8 Tools\\ui\\ue_run.py Tools\\level\\place_new_props.py [dry] [nonav]
"""
import json
import os
import sys
import unreal

sys.path.insert(0, r'J:\Projets\Unreal_Projects\Guess Who\Tools\level')
import dress
import lvl_build

ARGS = [a.lower() for a in globals().get('UE_ARGS', [])]
DRY = 'dry' in ARGS
eas = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
EAL = unreal.EditorAssetLibrary
FIT = dict(statue_dancer=(75, 75, 165), fern_stand=(85, 85, 135), birdcage=(70, 70, 175), chaise_longue=(190, 80, 90),
           champagne_bucket=(45, 45, 90), fire_screen=(100, 40, 90), microphone_stand=(45, 45, 180),
           vase_floor=(50, 50, 105), dress_form=(60, 55, 170), drum_kit=(160, 120, 120), writing_bureau=(100, 60, 115),
           film_projector=(75, 100, 145), double_bass=(75, 55, 190), card_table=(90, 90, 80))
L, D, C, H, B, ST, CO, CL = ('Dress_library', 'Dress_dining', 'Dress_corridor_w', 'Dress_hall', 'Dress_ballroom',
                             'Dress_study', 'Dress_conservatory', 'Dress_cloakroom')
E, BI = 'Dress_corridor_e', 'Dress_billiard'
SLOTS = [
    (L, 'fire_screen', 142, 3400, 0), (L, 'card_table', 1650, 4100, 90), (L, 'writing_bureau', 600, 2460, 90, dict(back=True)),
    (L, 'film_projector', 380, 4120, -45), (L, 'chaise_longue', 1850, 3950, 180),
    (D, 'fire_screen', 142, 900, 0), (D, 'vase_floor', 60, 1740, -90), (D, 'vase_floor', 850, 1745, -90),
    (D, 'vase_floor', 1150, 1745, -90), (D, 'champagne_bucket', 1460, 780, 0),
    (C, 'vase_floor', 850, 1845, 90), (C, 'vase_floor', 850, 2355, -90), (C, 'vase_floor', 1150, 1845, 90),
    (C, 'vase_floor', 1150, 2355, -90), (C, 'fern_stand', 1835, 1865, 90), (C, 'fern_stand', 1835, 2335, 90),
    (E, 'vase_floor', 4850, 1845, 90), (E, 'vase_floor', 4850, 2355, -90), (E, 'vase_floor', 5150, 1845, 90),
    (E, 'vase_floor', 5150, 2355, -90), (E, 'fern_stand', 4165, 1865, 90), (E, 'fern_stand', 4165, 2335, 90),
    (H, 'statue_dancer', 3000, 850, -90), (H, 'fern_stand', 2850, 850, 90), (H, 'fern_stand', 3150, 850, 90),
    (H, 'vase_floor', 2735, 2335, -90, dict(fit=(50, 50, 96))), (H, 'vase_floor', 3265, 2335, -90, dict(fit=(50, 50, 96))),
    (B, 'double_bass', 3060, 4200, -90, dict(z=60)), (B, 'drum_kit', 3360, 4150, -90, dict(z=60)),
    (B, 'microphone_stand', 3440, 3960, -90, dict(z=60)), (B, 'dress_form', 2440, 4190, -90),
    (B, 'chaise_longue', 3755, 2419, 90, dict(back=True)), (B, 'statue_dancer', 3700, 3175, 180),
    (B, 'champagne_bucket', 2400, 2662, 90), (B, 'champagne_bucket', 3600, 2662, 90),
    (BI, 'card_table', 5450, 300, 90),
    (ST, 'writing_bureau', 5250, 2419, 90, dict(back=True)), (ST, 'film_projector', 5250, 3050, 0),
    (CO, 'fern_stand', 4380, 4300, 90), (CO, 'fern_stand', 5300, 3300, 90), (CO, 'fern_stand', 4130, 3560, 90),
    (CO, 'birdcage', 5350, 4200, -90), (CO, 'chaise_longue', 4500, 4100, -90),
    (CL, 'dress_form', 3000, 150, 90),
]
for (cx, cy) in ((1650, 4100), (5450, 300)):                 # the 4 chairs of each card table (dress.card_group)
    for a, (dx, dy) in ((90, (0, 80)), (180, (-80, 0)), (270, (0, -80)), (0, (80, 0))):
        SLOTS.append((L if cx < 3000 else BI, 'chair_dining', cx + dx, cy + dy, a + 180, dict(nofit=True)))


class Capture:
    def __init__(self):
        self.rows = []

    def add(self, g, mesh, mat, loc, yaw=0.0, pitch=0.0, roll=0.0, scale=(1, 1, 1), coll=False, shadow=True):
        self.rows.append(dict(g=g, mesh=mesh, loc=loc, yaw=yaw, scale=scale))


world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
if 'L_Manor' not in world.get_name():
    raise RuntimeError('open L_Manor first, current map is ' + world.get_name())
state = dress.import_props()
cap = Capture()
for s in SLOTS:
    g, name, x, y, face = s[:5]
    kw = dict(s[5]) if len(s) > 5 else {}
    if not kw.pop('nofit', False):
        kw.setdefault('fit', FIT[name])
    if name not in state:
        print('!! not imported:', name)
        continue
    dress.slot(cap, g, state, name, x, y, face, **kw)

# dress.slot passes world positions already; report any overlap with what's there now
old = [a for a in eas.get_all_level_actors() if 'GW_NewProp' in [str(t) for t in a.tags]]
others = []
for a in eas.get_all_level_actors():
    if 'GW_Manual' in [str(t) for t in a.tags] and a not in old:
        o, e = a.get_actor_bounds(False)
        others.append((a.get_actor_label(), o.x - e.x, o.y - e.y, o.x + e.x, o.y + e.y, o.z - e.z, o.z + e.z))
foot = dress.FOOT[-len(cap.rows):]
clash = 0
for f in foot:
    for (lab, x0, y0, x1, y1, z0, z1) in others:
        if f[0] < x1 - 5 and x0 + 5 < f[2] and f[1] < y1 - 5 and y0 + 5 < f[3] and z0 < f[5] and f[6] < z1:
            print(f'  overlap: {f[4]} ({f[0]:.0f},{f[1]:.0f})-({f[2]:.0f},{f[3]:.0f}) with {lab}')
            clash += 1
print(f'place_new_props: {len(cap.rows)} to place, {clash} overlaps')
if DRY:
    raise SystemExit

for a in old:
    eas.destroy_actor(a)
n = 0
for r in cap.rows:
    x, y, z = r['loc']
    a = eas.spawn_actor_from_class(unreal.StaticMeshActor, unreal.Vector(x, y, z), unreal.Rotator(roll=0, pitch=0, yaw=r['yaw']))
    smc = a.static_mesh_component
    smc.set_mobility(unreal.ComponentMobility.MOVABLE)
    smc.set_static_mesh(unreal.load_asset(r['mesh']))
    smc.set_collision_profile_name('BlockAll')
    smc.set_mobility(unreal.ComponentMobility.STATIC)
    a.set_actor_scale3d(unreal.Vector(*r['scale']))
    a.set_actor_label(f"{r['mesh'].split('/')[-1]}_new{n}")
    a.set_folder_path(f"Decor_Manuel/{r['g']}")
    a.tags = [unreal.Name('GW_Manual'), unreal.Name('GW_NewProp')]
    n += 1

dress.play_point('GW_Instrument_Bass', 3060, 4200, 60.0, -90, FIT['double_bass'][1] / 2.0, 'back')
dress.play_point('GW_Instrument_Drums', 3360, 4150, 60.0, -90, FIT['drum_kit'][1] / 2.0, 'back')
for (tag, ix, iy, iz, iyaw) in dress.INSTRUMENTS[-2:]:
    if not [a for a in eas.get_all_level_actors() if tag in [str(t) for t in a.tags]]:
        lvl_build.target_point((ix, iy, iz), tag, yaw=iyaw, label=tag)
        print('marker', tag, ix, iy, iz)

p = os.path.join(dress.ROOT, 'Tools', 'level', 'dress_state.json')
ds = json.load(open(p, encoding='utf-8'))
have = {i[0] for i in ds.get('instruments', [])}
ds['instruments'] = ds.get('instruments', []) + [i for i in dress.INSTRUMENTS[-2:] if i[0] not in have]
placed = {s[1] for s in SLOTS} | {'card_table+chairs'}
for r in ds.get('reserved', []):
    if r[4] in placed:
        r[7] = True
json.dump(ds, open(p, 'w', encoding='utf-8'), indent=0)

if 'nonav' not in ARGS:
    unreal.SystemLibrary.execute_console_command(world, 'BuildPaths')
unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).save_current_level()
print(f'place_new_props: placed {n} actors; level saved')
