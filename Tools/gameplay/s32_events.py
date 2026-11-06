"""Game events: À l'attaque (bandits), Au feu, Panne de courant, Le kamikaze, Le robot.

Framework (BP_GW_GameMode): StartEvent(Id) / EndEvent / EventTick (called by RoundTick). The game state replicates
EventId / EventName / EventStart (HUD banner in big letters, alarm sting, blackout on every client) and RobotOn.
Automatic events (AutoEvents, every EventEvery s during the hunt, the first one 45 s after the hunt starts) are ON by
default (the user: "events must trigger in the game"); the dev menu (F2 -> Événements) turns them off/on, and sets the
frequency and an optional duration override (EventDurSet, 0 = each event's own).
Every event brings NPC reactions through s31_reactions.py: panic (screams, alarm lines, everybody runs), lines aimed
at the players, then calm-down lines, plus its own sounds.

Special characters are BP_GW_Character with Kind 1 bandit / 2 kamikaze / 3 robot (ApplySpecialLook: generated mesh
from SpecialMeshes, filled by s29_gen_chars.py from manifest "outfits": "bandit" | "kamikaze" | "robot"; the plain
mannequin until those exist) driven by their own AI controllers:
- BP_GW_BanditController: runs between random points, shouts, fires every 0.6-1.4 s at a random character within
  25 m with a wide spread (BanditShoot: 50 damage to players, an NPC dies).
- BP_GW_KamikazeController: sprints from room to room, explodes 15-25 s later wherever it is. He says nothing else than the alarm: BP_GW_KamiAlarm (s43_feedback6.py kami, run it before this script
  if the asset is gone), spawned by SpawnSpecial, follows him and loops SFX_Kamikaze_Alarm_Loop in 3D until he falls (the user, 2026-11-05: "juste ALAARM en boucle sans arret")
  (Explode: 6.5 m, kills everyone inside).
- BP_GW_RobotController: big (x1.3), slow, heavy steps, red eyes; scans for players (in front, 30 m, line of sight),
  says "Cible détectée", shows a thin charging beam for ROBOT_CHARGE s (it follows the target for ROBOT_LOCK s, then holds its line: step out of it),
  then fires along that line. The line stops at the first wall or prop (GM.RobotBeamEnd), the first character on it is hit (GM.RobotDmg: two hits kill a
  player). It has health (GM.RobotHP): bullets 100, sword 50, turret 25, explosions kill it (GM.RobotHurt / RobotDown). Stays until the round ends or it dies.
Fire: BP_GW_Fire actors in random rooms plus BP_GW_WallFire sheets of flame on a nearby wall, and the fire bell rings
on every client. Whoever touches a flame catches fire (Ignite): flames on the body (BurnFlame0-2), a scream, arms
flailing (the arm bodies go physical, FlailTick shakes the hands); a player loses 10 per 0.25 s in the flames, an
NPC runs off burning and dies 3.5 s later. The robot sees far (60 m) but narrow (cone ~23 deg, shown by a red
VisionLight), never through walls, and fires 0.6 s after it spots a player. Blackout: each client
hides every light and turns on its own flashlight (BP_GW_Character.Flashlight, seen only by its owner, so a beam never
gives a player away), with eye adaptation off so it stays dark.
Usage: ue_run.py s32_events.py  (then s26_costumes.py ApplyLook, s12_gamemode.py RoundTick, u14_hud.py graph RefreshWith)
"""
import sys, importlib
sys.path.insert(0, r'J:\Projets\Unreal_Projects\Guess Who\Tools\gameplay')
import gw_lib; importlib.reload(gw_lib)
from gw_lib import *

REP = unreal.BlueprintVariableReplication
V3 = unreal.Vector.static_struct()
CHAR = '"/Game/GW/Blueprints/BP_GW_Character.BP_GW_Character_C"'
ISVALID = 'GW|Call|/Script/Engine.KismetSystemLibrary|IsValid'
GSC = '(Utilities|Casting|CastToBP_GW_GameState (Game|GetGameState))'
GMC = '(Utilities|Casting|CastToBP_GW_GameMode (Game|GetGameMode))'
MEL = unreal.MaterialEditingLibrary
AT = unreal.AssetToolsHelpers.get_asset_tools()
CAT = {'scream': 1, 'shout': 2, 'calm': 3, 'attack_guest': 6, 'attack_bandit': 7, 'fire': 8, 'fire_after': 9,
       'blackout': 10, 'blackout_after': 11, 'kamikaze': 12, 'robot_voice': 13, 'explosion': 20, 'power_down': 22,
       'power_up': 23, 'robot_step': 24, 'servo': 25, 'laser': 26, 'fire_whoosh': 30}
FLAME = '/Game/GW/Materials/Master/M_GW_Flame'                     # ue_materials.py build_flame
EVENTS = {1: ("ÉVÉNEMENT : À L'ATTAQUE !", 12.0), 2: ('ÉVÉNEMENT : AU FEU !', 25.0), 3: ('ÉVÉNEMENT : PANNE DE COURANT !', 45.0),
          4: ('ÉVÉNEMENT : LE KAMIKAZE !', 40.0), 5: ('ÉVÉNEMENT : LE ROBOT !', 5.0), 6: ('ÉVÉNEMENT : LES ZOMBIES !', 70.0)}
CENTER = (3000.0, 2200.0, 160.0)
DOOR = (3000.0, 300.0, 100.0)


def mi(name, parent, color, strength):
    p = f'/Game/GW/Materials/{name}'
    m = unreal.load_asset(p) if EAL.does_asset_exist(p) else AT.create_asset(name, '/Game/GW/Materials', unreal.MaterialInstanceConstant, unreal.MaterialInstanceConstantFactoryNew())
    MEL.set_material_instance_parent(m, unreal.load_asset(parent))
    MEL.set_material_instance_vector_parameter_value(m, 'Color', unreal.LinearColor(*color))
    MEL.set_material_instance_scalar_parameter_value(m, 'Strength', strength)
    MEL.update_material_instance(m)
    EAL.save_loaded_asset(m)
    return m


MI_LASER = mi('MI_GW_Laser', '/Game/GW/Materials/Master/M_GW_Emissive', (1.0, 0.03, 0.02, 1), 60.0)
MI_BLAST = mi('MI_GW_Blast', '/Game/GW/Materials/Master/M_GW_Emissive', (1.0, 0.45, 0.08, 1), 40.0)
MI_FIRE = mi('MI_GW_EventFire', FLAME, (1.0, 0.16, 0.005, 1), 7.0)    # ue_materials.py flame (the user: more orange)


def flame_mi(name, height, width, strength):
    m = mi(name, FLAME, (1.0, 0.16, 0.005, 1), strength * 0.5)
    MEL.set_material_instance_scalar_parameter_value(m, 'Height', height)
    MEL.set_material_instance_scalar_parameter_value(m, 'Width', width)
    MEL.update_material_instance(m)
    EAL.save_loaded_asset(m)
    return m


MI_BODYFIRE = flame_mi('MI_GW_BodyFlame', 190.0, 30.0, 14.0)
MI_WALLFIRE = flame_mi('MI_GW_WallFlame', 280.0, 62.0, 14.0)


def actor_bp(name):
    bp = load_or_create_bp(name, unreal.Actor)
    compile_bp(bp, quiet=True)
    d = cdo(bp)
    d.set_editor_property('replicates', True)
    d.set_editor_property('always_relevant', True)
    return bp


def mesh(bp, name, asset, mat, loc=(0, 0, 0), rot=(0, 0, 0), scale=(1, 1, 1)):
    c = ensure_component(bp, name, unreal.StaticMeshComponent, 'DefaultSceneRoot')
    c.set_editor_property('static_mesh', unreal.load_asset(asset))
    c.set_editor_property('override_materials', [mat])
    c.set_editor_property('relative_location', unreal.Vector(*loc))
    c.set_editor_property('relative_rotation', unreal.Rotator(roll=rot[0], pitch=rot[1], yaw=rot[2]))
    c.set_editor_property('relative_scale3d', unreal.Vector(*scale))
    c.set_editor_property('cast_shadow', False)
    c.set_collision_enabled(unreal.CollisionEnabled.NO_COLLISION)
    return c


def light(bp, name, color, intensity, radius, parent='DefaultSceneRoot', loc=(0, 0, 0)):
    c = ensure_component(bp, name, unreal.PointLightComponent, parent)
    # keywords: unreal.Color's positional order is B, G, R, A (the fire's glow was blue for a long time)
    c.set_editor_property('light_color', unreal.Color(r=color[0], g=color[1], b=color[2], a=color[3]))
    c.set_editor_property('intensity', intensity)
    c.set_editor_property('attenuation_radius', radius)
    c.set_editor_property('relative_location', unreal.Vector(*loc))
    c.set_editor_property('cast_shadows', False)
    return c


# ---------------------------------------------------------------- effect actors
MI_EMBER = mi('MI_GW_Ember', '/Game/GW/Materials/Master/M_GW_Emissive', (1.0, 0.28, 0.03, 1), 8.0)
MI_FSMOKE = unreal.load_asset('/Game/GW/Materials/MI_GW_FireSmoke') if EAL.does_asset_exist('/Game/GW/Materials/MI_GW_FireSmoke') else \
    AT.create_asset('MI_GW_FireSmoke', '/Game/GW/Materials', unreal.MaterialInstanceConstant, unreal.MaterialInstanceConstantFactoryNew())
MEL.set_material_instance_parent(MI_FSMOKE, unreal.load_asset('/Game/GW/Materials/Master/M_GW_Smoke'))
MEL.set_material_instance_scalar_parameter_value(MI_FSMOKE, 'Density', 0.7)
MEL.update_material_instance(MI_FSMOKE)
EAL.save_loaded_asset(MI_FSMOKE)
fire = actor_bp('BP_GW_Fire')
for i, yaw in enumerate((0, 60, 120)):                      # the main blaze: 1.8 m wide, 2.6 m tall
    mesh(fire, f'Flame{i}', '/Engine/BasicShapes/Plane', MI_FIRE, loc=(0, 0, 130), rot=(90, 0, yaw), scale=(1.8, 2.6, 1))
for i, (x, y, yaw) in enumerate(((55, 20, 30), (-50, -25, 150))):   # two smaller tongues around it
    mesh(fire, f'Flame{3 + i}', '/Engine/BasicShapes/Plane', MI_FIRE, loc=(x, y, 70), rot=(90, 0, yaw), scale=(1.0, 1.4, 1))
light(fire, 'Glow', (255, 105, 22, 255), 16000.0, 1500.0, loc=(0, 0, 110))
er = ensure_component(fire, 'EmberRoot', unreal.SceneComponent, 'DefaultSceneRoot')
er.set_editor_property('relative_location', unreal.Vector(0, 0, 40))
for i in range(8):                                          # sparks swirling up (FireAnim moves and spins EmberRoot)
    import math as _m
    a = _m.radians(i * 47)
    e = ensure_component(fire, f'Ember{i}', unreal.StaticMeshComponent, 'EmberRoot')
    e.set_editor_property('static_mesh', unreal.load_asset('/Engine/BasicShapes/Sphere'))
    e.set_editor_property('override_materials', [MI_EMBER])
    e.set_editor_property('relative_location', unreal.Vector(_m.cos(a) * (25 + 6 * i), _m.sin(a) * (25 + 6 * i), i * 28))
    e.set_editor_property('relative_scale3d', unreal.Vector(0.035, 0.035, 0.035))
    e.set_editor_property('cast_shadow', False)
    e.set_collision_enabled(unreal.CollisionEnabled.NO_COLLISION)
for i, (z, sc) in enumerate(((330, 2.6), (470, 3.6))):    # dark smoke above it
    sm = ensure_component(fire, f'Smoke{i}', unreal.StaticMeshComponent, 'DefaultSceneRoot')
    sm.set_editor_property('static_mesh', unreal.load_asset('/Engine/BasicShapes/Sphere'))
    sm.set_editor_property('override_materials', [MI_FSMOKE])
    sm.set_editor_property('relative_location', unreal.Vector(0, 0, z))
    sm.set_editor_property('relative_scale3d', unreal.Vector(sc, sc, sc * 0.8))
    sm.set_editor_property('cast_shadow', False)
    sm.set_collision_enabled(unreal.CollisionEnabled.NO_COLLISION)
ensure_fn(fire, 'FireAnim')
ensure_var(fire, 'EmberZ', 'float', category='GW')
ensure_var(fire, 'EmberYaw', 'float', category='GW')
compile_bp(fire, quiet=True)
write(fire, 'FireAnim', '''
(fn FireAnim ()
  (Rendering|Components|Light|SetIntensity :self (Variables|Default|GetGlow) :NewIntensity (Math|Random|RandomFloatinRange 9000.0 26000.0))
  (Variables|GW|SetEmberYaw (+ (Variables|GW|GetEmberYaw) 17.0))
  (Transformation|SetRelativeRotation :self (Variables|Default|GetEmberRoot) :NewRotation (Math|Rotator|MakeRotator :Yaw (Variables|GW|GetEmberYaw)) :bSweep false :bTeleport true)
  (Variables|GW|SetEmberZ (select (> (Variables|GW|GetEmberZ) 140.0) 0.0 (+ (Variables|GW|GetEmberZ) 11.0)))
  (Transformation|SetRelativeLocation :self (Variables|Default|GetEmberRoot) :NewLocation (Math|Vector|MakeVector 0.0 0.0 (+ 40.0 (Variables|GW|GetEmberZ))) :bSweep false :bTeleport true))
''', compile_after=False)
write(fire, 'EventGraph', '''
(event EventBeginPlay
  (Utilities|Time|SetTimerbyFunctionName :Object self :FunctionName "FireAnim" :Time 0.06 :bLooping true))
''', compile_after=False)
au = ensure_component(fire, 'Crackle', unreal.AudioComponent, 'DefaultSceneRoot')
_loop = '/Game/GW/Audio/Gen/fire_loop/SFX_Fire_Crackle_Loop'
au.set_editor_property('sound', unreal.load_asset(_loop if unreal.EditorAssetLibrary.does_asset_exist(_loop) else '/Game/GW/Audio/AMB_Fire'))
au.set_editor_property('attenuation_settings', unreal.load_asset('/Game/GW/Audio/ATT_GW_Fire'))
au.set_editor_property('volume_multiplier', 1.6)
cdo(fire).set_editor_property('initial_life_span', 120.0)
compile_bp(fire); save(fire)

boom = actor_bp('BP_GW_Explosion')
mesh(boom, 'Ball', '/Engine/BasicShapes/Sphere', MI_BLAST, loc=(0, 0, 60), scale=(5, 5, 5))
light(boom, 'Flash', (255, 170, 80, 255), 150000.0, 1800.0, loc=(0, 0, 120))     # was 500000 / 3000: lighter on Lumen
cdo(boom).set_editor_property('initial_life_span', 0.35)
compile_bp(boom); save(boom)

wall = actor_bp('BP_GW_WallFire')                     # spawned facing out of a wall (StartFire)
for i, yaw in enumerate((0, 90)):
    mesh(wall, f'Sheet{i}', '/Engine/BasicShapes/Plane', MI_WALLFIRE, loc=(0, 0, 140), rot=(90, 0, yaw), scale=(1.2, 2.8, 1))
light(wall, 'Glow', (255, 105, 22, 255), 8000.0, 800.0, loc=(30, 0, 120))
cdo(wall).set_editor_property('initial_life_span', 120.0)
compile_bp(wall); save(wall)

beam = actor_bp('BP_GW_Beam')
mesh(beam, 'Ray', '/Engine/BasicShapes/Cube', MI_LASER, scale=(1, 0.04, 0.04))
light(beam, 'RayGlow', (255, 20, 10, 255), 20000.0, 500.0)
ensure_var(beam, 'BeamStart', struct=V3, rep=REP.REPLICATED, category='GW')
ensure_var(beam, 'Width', 'float', rep=REP.REPLICATED, category='GW')           # 2.5 the shot, under 1.3 the charging beam
ensure_var(beam, 'BeamEnd', struct=V3, rep=REP.REP_NOTIFY, category='GW')
ensure_var(beam, 'Charge', 'bool', rep=REP.REP_NOTIFY, category='GW')          # true once: the rising whine (Tools/audio/fb5_sounds.py)
ensure_fn(beam, 'OnRep_BeamEnd')
ensure_fn(beam, 'OnRep_Charge')
compile_bp(beam, quiet=True)
cdo(beam).set_editor_property('Width', 1.0)
cdo(beam).set_editor_property('initial_life_span', 0.45)
write(beam, 'OnRep_BeamEnd', '''
(fn OnRep_BeamEnd ()
  (bind a (Variables|GW|GetBeamStart))
  (bind b (Variables|GW|GetBeamEnd))
  (Transformation|SetActorLocationAndRotation :self self :NewLocation (* (+ a b) 0.5) :NewRotation (Math|Rotator|FindLookatRotation :Start a :Target b) :bSweep false :bTeleport true)
  (bind w (Variables|GW|GetWidth))
  (Rendering|Components|Light|SetIntensity :self (Variables|Default|GetRayGlow) :NewIntensity (select (>= w 2.0) 20000.0 (* w 2500.0)))
  (Transformation|SetActorScale3D :self self :NewScale3D (Math|Vector|MakeVector (/ (Math|Vector|Distance(Vector) a b) 100.0) w w)))
''', compile_after=False)
_charge = '/Game/GW/Audio/Gen/inv/SFX_Charge_Laser'    # not in laser/: the bank takes SFX_Laser* for the zap
write(beam, 'OnRep_Charge', f'''
(fn OnRep_Charge ()
  (if (Variables|GW|GetCharge)
    (Audio|PlaySoundatLocation :Sound "{_charge}.SFX_Charge_Laser" :Location (Variables|GW|GetBeamStart) :VolumeMultiplier 0.8 :AttenuationSettings "/Game/GW/Audio/ATT_GW_Voice.ATT_GW_Voice")))
''', compile_after=False)
compile_bp(beam); save(beam)

# ---------------------------------------------------------------- character: special looks, flashlight, robot eyes
ch = load_bp('BP_GW_Character')
fl = ensure_component(ch, 'Flashlight', unreal.SpotLightComponent, 'FollowCamera')
fl.set_editor_property('relative_location', unreal.Vector(340, 0, -15))       # just ahead of the character, looking where the camera looks
fl.set_editor_property('intensity', 12000.0)
fl.set_editor_property('attenuation_radius', 2200.0)
fl.set_editor_property('inner_cone_angle', 11.0)
fl.set_editor_property('outer_cone_angle', 21.0)
fl.set_editor_property('light_color', unreal.Color(r=255, g=236, b=205, a=255))
fl.set_editor_property('cast_shadows', True)
fl.set_editor_property('visible', False)
eye = light(ch, 'EyeGlow', (255, 10, 5, 255), 0.0, 260.0, parent='Mesh', loc=(0, 18, 168))
MI_SIGHT = mi('MI_GW_RobotSight', '/Game/GW/Materials/Master/M_GW_Beam', (1.0, 0.04, 0.02, 1), 1.5)
MI_SIGHTLINE = mi('MI_GW_RobotSightLine', '/Game/GW/Materials/Master/M_GW_Emissive', (1.0, 0.03, 0.02, 1), 90.0)
vroot = ensure_component(ch, 'VisionRoot', unreal.SceneComponent, 'Mesh')       # OnRep_SightLen scales it: cut at the first wall
vroot.set_editor_property('relative_location', unreal.Vector(0, 30, 165))
_objs = subobjects(ch)                                         # the first cone hung on the mesh directly
if 'VisionCone' in _objs:
    unreal.get_engine_subsystem(unreal.SubobjectDataSubsystem).delete_subobject(_objs['DefaultSceneRoot'][0] if 'DefaultSceneRoot' in _objs else _objs['Mesh'][0], _objs['VisionCone'][0], ch)
cone = ensure_component(ch, 'VisionConeB', unreal.StaticMeshComponent, 'VisionRoot')   # the robot's real sight: 30 m, 15 deg each side
cone_mesh = unreal.load_asset('/Engine/BasicShapes/Cone')
cone.set_editor_property('static_mesh', cone_mesh)
cone.set_editor_property('override_materials', [MI_SIGHT])
_L = 3000.0
_bb = cone_mesh.get_bounding_box()
_h = _bb.max.z - _bb.min.z                                   # cone height in its own units (apex at +Z)
_r = (_bb.max.x - _bb.min.x) / 2.0
_rot = next(r for r in (unreal.Rotator(roll=90, pitch=0, yaw=0), unreal.Rotator(roll=-90, pitch=0, yaw=0))
            if unreal.MathLibrary.greater_greater_vector_rotator(unreal.Vector(0, 0, 1), r).y < -0.9)   # apex (+Z) toward the robot
_tan = 0.268                                                 # tan(15 deg)
_mid = (_bb.max.z + _bb.min.z) / 2.0                          # pivot offset along the cone axis
cone.set_editor_property('relative_rotation', _rot)
cone.set_editor_property('relative_scale3d', unreal.Vector(_tan * _L / _r, _tan * _L / _r, _L / _h))
cone.set_editor_property('relative_location', unreal.Vector(0, _L / 2.0 + _mid * _L / _h, 0))
cone.set_editor_property('cast_shadow', False)
cone.set_editor_property('visible', False)
cone.set_collision_enabled(unreal.CollisionEnabled.NO_COLLISION)
_cyl = unreal.load_asset('/Engine/BasicShapes/Cylinder')       # 1 m tall along Z, 50 cm radius
import math as _mm
_s, _c = _mm.sin(_mm.radians(15.0)), _mm.cos(_mm.radians(15.0))
for _n, _d, _th in (('VisionCore', (0, 1, 0), 0.05), ('VisionEdgeL', (-_s, _c, 0), 0.035), ('VisionEdgeR', (_s, _c, 0), 0.035),
                    ('VisionEdgeU', (0, _c, _s), 0.035), ('VisionEdgeD', (0, _c, -_s), 0.035)):
    _v = unreal.Vector(*_d)
    _e = ensure_component(ch, _n, unreal.StaticMeshComponent, 'VisionRoot')
    _e.set_editor_property('static_mesh', _cyl)
    _e.set_editor_property('override_materials', [MI_SIGHTLINE])
    _e.set_editor_property('relative_location', _v * (_L / 2.0))
    _e.set_editor_property('relative_rotation', unreal.MathLibrary.make_rot_from_z(_v))
    _e.set_editor_property('relative_scale3d', unreal.Vector(_th, _th, _L / 100.0))
    _e.set_editor_property('cast_shadow', False)
    _e.set_editor_property('visible', False)
    _e.set_collision_enabled(unreal.CollisionEnabled.NO_COLLISION)
ensure_var(ch, 'SightLen', 'float', rep=REP.REP_NOTIFY, category='GW')          # 0-1 of the 30 m actually free ahead of the robot
ensure_fn(ch, 'OnRep_SightLen')
for _f in ('ZombieVisual', 'ZombieAnim', 'OnRep_ZombieGroan'):                 # bodies: s40_events2.py
    ensure_fn(ch, _f)
vis = ensure_component(ch, 'VisionLight', unreal.SpotLightComponent, 'Mesh')   # the robot's sight cone, red
vis.set_editor_property('relative_location', unreal.Vector(0, 30, 165))
vis.set_editor_property('relative_rotation', unreal.Rotator(roll=0, pitch=-9, yaw=90))   # mesh +Y = forward
vis.set_editor_property('intensity', 0.0)
vis.set_editor_property('attenuation_radius', 6000.0)
vis.set_editor_property('inner_cone_angle', 8.0)
vis.set_editor_property('outer_cone_angle', 15.0)
vis.set_editor_property('light_color', unreal.Color(r=255, g=25, b=12, a=255))
vis.set_editor_property('cast_shadows', False)
for i, yaw in enumerate((0, 60, 120)):                     # flames on a burning character, hidden until it burns
    bf = ensure_component(ch, f'BurnFlame{i}', unreal.StaticMeshComponent, 'Mesh')
    bf.set_editor_property('static_mesh', unreal.load_asset('/Engine/BasicShapes/Plane'))
    bf.set_editor_property('override_materials', [MI_BODYFIRE])
    bf.set_editor_property('relative_location', unreal.Vector(0, 0, 100))
    bf.set_editor_property('relative_rotation', unreal.Rotator(roll=90, pitch=0, yaw=yaw))
    bf.set_editor_property('relative_scale3d', unreal.Vector(0.6, 1.9, 1))
    bf.set_editor_property('cast_shadow', False)
    bf.set_editor_property('visible', False)
    bf.set_collision_enabled(unreal.CollisionEnabled.NO_COLLISION)
ensure_var(ch, 'Burning', 'bool', rep=REP.REP_NOTIFY, category='GW')
ensure_var(ch, 'BurnUntil', 'float', category='GW')
ensure_var(ch, 'BurnKillAt', 'float', category='GW')
ensure_fn(ch, 'OnRep_Burning')
ensure_fn(ch, 'FlailTick')
ensure_var(ch, 'SpecialMeshes', obj_class=unreal.SkeletalMesh, array=True, category='Costume')
ensure_var(ch, 'Variant', 'int', rep=REP.REPLICATED, category='GW')
ensure_fn(ch, 'ApplySpecialLook')
ensure_fn(ch, 'OnRep_Kind')
compile_bp(ch, quiet=True)
if cdo(ch).get_editor_property('Kind') is not None:
    BT.set_variable_replication(ch, 'Kind', REP.REP_NOTIFY)
compile_bp(ch, quiet=True)
manny = unreal.load_asset('/Game/Characters/Mannequins/Meshes/SKM_Manny_Simple')
if len(cdo(ch).get_editor_property('SpecialMeshes')) < 5:          # s29_gen_chars.py puts the generated ones in
    cdo(ch).set_editor_property('SpecialMeshes', (list(cdo(ch).get_editor_property('SpecialMeshes')) + [manny] * 5)[:5])
NULL = '(Variables|Costume|GetNoMesh)'
slots = ''.join(f'  (CallFunction|ApplySlot :Comp (Variables|Default|Get{c}) :M {NULL})\n' for c in ('ShellMesh', 'SkirtMesh', 'HairMesh', 'MaskMesh', 'HatMesh'))
write(ch, 'ApplySpecialLook', f'''
(fn ApplySpecialLook ()
  (bind k (Variables|GW|GetKind))
  ; a zombie keeps its own character: only its skin and gait change (s40_events2.py)
  (if (== k 4)
    (CallFunction|ZombieVisual)
    (return))
  (bind meshes (Variables|Costume|GetSpecialMeshes))
  (bind m (Variables|Character|GetMesh))
  ; bandits come in two looks: Variant 1 wears SpecialMeshes[4]
  (bind idx (select (and (== k 1) (and (== (Variables|GW|GetVariant) 1) (> (Utilities|Array|Length meshes) 4))) 4 k))
  (if (and (> k 0) (< idx (Utilities|Array|Length meshes)))
    (Components|SkeletalMesh|SetSkeletalMeshAsset :self m :NewMesh (Utilities|Array|Get(acopy) meshes idx)))
  (Rendering|Material|SetMaterial :self m :ElementIndex 0)
  (Rendering|Material|SetMaterial :self m :ElementIndex 1)
  (GW|Call|/Script/Engine.SkinnedMeshComponent|UnHideBoneByName :self m :BoneName "thigh_l")
  (GW|Call|/Script/Engine.SkinnedMeshComponent|UnHideBoneByName :self m :BoneName "thigh_r")
{slots}  (CallFunction|ApplySlot :Comp (Variables|Default|GetGunMesh) :M (select (== k 1) (Variables|GW|GetRevolverMesh) {NULL}))
  (Transformation|SetActorScale3D :self self :NewScale3D (select (== k 3) (Math|Vector|MakeVector 1.3 1.3 1.3) (Math|Vector|MakeVector 1.0 1.0 1.0)))
  (Rendering|Components|Light|SetIntensity :self (Variables|Default|GetEyeGlow) :NewIntensity (select (== k 3) 6000.0 0.0))
  (Rendering|Components|Light|SetIntensity :self (Variables|Default|GetVisionLight) :NewIntensity (select (== k 3) 40000.0 0.0))
  (Rendering|SetVisibility :self (Variables|Default|GetVisionRoot) :bNewVisibility (== k 3) :bPropagateToChildren true))
''', compile_after=False)
write(ch, 'OnRep_Burning', '''
(fn OnRep_Burning ()
  (bind on (Variables|GW|GetBurning))
  (Rendering|SetVisibility :self (Variables|Default|GetBurnFlame0) :bNewVisibility on :bPropagateToChildren false)
  (Rendering|SetVisibility :self (Variables|Default|GetBurnFlame1) :bNewVisibility on :bPropagateToChildren false)
  (Rendering|SetVisibility :self (Variables|Default|GetBurnFlame2) :bNewVisibility on :bPropagateToChildren false)
  ; a ragdoll keeps its physics: only the living flail their arms
  (if (Variables|GW|GetIsDead)
    (return))
  (bind m (Variables|Character|GetMesh))
  (Physics|SetAllBodiesBelowSimulatePhysics :self m :InBoneName (Utilities|Name|MakeLiteralName :Value "upperarm_l") :bNewSimulate on :bIncludeSelf true)
  (Physics|SetAllBodiesBelowSimulatePhysics :self m :InBoneName (Utilities|Name|MakeLiteralName :Value "upperarm_r") :bNewSimulate on :bIncludeSelf true)
  (Physics|SetAllBodiesBelowPhysicsBlendWeight :self m :InBoneName (Utilities|Name|MakeLiteralName :Value "upperarm_l") :PhysicsBlendWeight (select on 1.0 0.0) :bSkipCustomPhysicsType false :bIncludeSelf true)
  (Physics|SetAllBodiesBelowPhysicsBlendWeight :self m :InBoneName (Utilities|Name|MakeLiteralName :Value "upperarm_r") :PhysicsBlendWeight (select on 1.0 0.0) :bSkipCustomPhysicsType false :bIncludeSelf true)
  (if on
    (Utilities|Time|SetTimerbyFunctionName :Object self :FunctionName "FlailTick" :Time 0.12 :bLooping true)
    (else
      (Utilities|Time|ClearTimerbyFunctionName :Object self :FunctionName "FlailTick"))))
''', compile_after=False)
write(ch, 'FlailTick', '''
(fn FlailTick ()
  (if (or (not (Variables|GW|GetBurning)) (Variables|GW|GetIsDead))
    (Utilities|Time|ClearTimerbyFunctionName :Object self :FunctionName "FlailTick")
    (return))
  (bind m (Variables|Character|GetMesh))
  (Physics|AddImpulse :self m :Impulse (* (Math|Random|RandomUnitVector) 280.0) :BoneName "hand_l" :bVelChange true)
  (Physics|AddImpulse :self m :Impulse (* (Math|Random|RandomUnitVector) 280.0) :BoneName "hand_r" :bVelChange true))
''', compile_after=False)
write(ch, 'OnRep_Kind', '(fn OnRep_Kind () (if (!= (Variables|GW|GetKind) 0) (CallFunction|ApplySpecialLook) (else (CallFunction|ZombieVisual))))', compile_after=False)
write(ch, 'OnRep_SightLen', '(fn OnRep_SightLen () (bind s (Math|Float|Max(Float) (Variables|GW|GetSightLen) 0.02)) (Transformation|SetRelativeScale3D :self (Variables|Default|GetVisionRoot) :NewScale3D (Math|Vector|MakeVector s s s)))', compile_after=False)
compile_bp(ch)
print('BP_GW_Character', node_problems(ch))
save(ch)

# ---------------------------------------------------------------- game state
gsb = load_bp('BP_GW_GameState')
for v, t in (('EventId', 'int'), ('EventName', 'string'), ('EventStart', 'float'), ('RobotOn', 'bool')):
    ensure_var(gsb, v, t, rep=REP.REPLICATED, category='GW')
ensure_var(gsb, 'EventSting', obj_class=unreal.SoundBase, category='Audio')
ensure_var(gsb, 'FireAlarm', obj_class=unreal.SoundBase, category='Audio')
compile_bp(gsb, quiet=True)
_sting = '/Game/GW/Audio/Gen/sting/SFX_Event_Alarm_01'
cdo(gsb).set_editor_property('EventSting', unreal.load_asset(_sting if unreal.EditorAssetLibrary.does_asset_exist(_sting) else '/Game/GW/Audio/S_GW_Gong'))
_bell = '/Game/GW/Audio/Gen/fire_alarm/SFX_Fire_Bell_Loop'                 # Tools/audio/synth_fire_bell.py, s31 import
if unreal.EditorAssetLibrary.does_asset_exist(_bell):
    cdo(gsb).set_editor_property('FireAlarm', unreal.load_asset(_bell))
compile_bp(gsb, quiet=True)
save(gsb)

# ---------------------------------------------------------------- AI controllers for the special characters
chc = ch.generated_class()
# game mode signatures first: the controllers call them
gm = load_bp('BP_GW_GameMode')
for v, t in (('AutoEvents', 'bool'), ('EventEvery', 'float'), ('EventDurSet', 'float'), ('NextEventAt', 'float'),
             ('EventEnd', 'float'), ('NextFireDmg', 'float')):
    ensure_var(gm, v, t, category='GW')
ensure_var(gm, 'Fires', obj_class=unreal.Actor, array=True, category='GW')
ensure_var(gm, 'EndingId', 'int', category='GW')
ensure_var(gm, 'EventPick', 'int', category='GW')
ensure_fn(gm, 'StartEvent', inputs=[('Id', 'int')])
for f in ('EndEvent', 'EventTick', 'StartAttack', 'StartFire', 'StartBlackout', 'StartKamikaze', 'StartRobot', 'FireTick',
          'BanditsLeave', 'StartZombie', 'EndZombie', 'Events2Tick', 'FireAlarmOn', 'FireAlarmOff'):   # the last 5: s40_events2.py
    ensure_fn(gm, f)
ensure_fn(gm, 'HurtCharacter', inputs=[('Victim', chc), ('Amount', 'float'), ('Impulse', V3), ('Cause', 'string')])
ensure_fn(gm, 'BanditShoot', inputs=[('Shooter', chc), ('Start', V3), ('Dir', V3)])
ensure_fn(gm, 'Explode', inputs=[('Loc', V3), ('Radius', 'float'), ('Cause', 'string')])
ensure_fn(gm, 'RobotLaser', inputs=[('From', V3), ('Victim', chc)])
ensure_fn(gm, 'RobotBeamEnd', inputs=[('From', V3), ('Dir', V3), ('Who', chc)], outputs=[('End', V3)])
ensure_fn(gm, 'RobotShot', inputs=[('From', V3), ('End', V3), ('Who', chc)])
ensure_fn(gm, 'RobotHurt', inputs=[('Victim', chc), ('Amount', 'float'), ('Dir', V3)])
ensure_fn(gm, 'RobotDown', inputs=[('Victim', chc), ('Dir', V3)])
for v, d in (('RobotHP', 300.0), ('RobotDmg', 55.0), ('LaserD', 0.0)):
    ensure_var(gm, v, 'float', category='GW')
ensure_var(gm, 'LaserV', obj_class=chc, category='GW')
ensure_fn(gm, 'SpawnSpecial', inputs=[('Kind', 'int'), ('Loc', V3)], outputs=[('Ch', chc)])
ensure_fn(gm, 'EventFocus', outputs=[('Loc', V3), ('Ok', 'bool')])     # dev menu "Aller voir l'événement" + QA shots
ensure_fn(gm, 'Ignite', inputs=[('Ch', chc), ('From', V3)])
ensure_fn(gm, 'ZombieDown', inputs=[('Victim', chc), ('Impulse', V3)])
ensure_fn(gm, 'BurnTick')
ensure_fn(gm, 'DeathCry', inputs=[('Victim', chc)])                      # body: s31_reactions.py
ensure_var(gm, 'WallDir', struct=V3, category='GW')
ensure_var(gm, 'NextSpread', 'float', category='GW')
ensure_var(gm, 'SpreadFrom', obj_class=unreal.Actor, category='GW')
ensure_var(gm, 'GunContext', 'bool', category='GW')                    # s31: voice lines about guns allowed
compile_bp(gm, quiet=True)
cdo(gm).set_editor_property('EventEvery', 180.0)     # the user, 2026-11-05: one event every 3 minutes
cdo(gm).set_editor_property('RobotHP', 300.0)
cdo(gm).set_editor_property('RobotDmg', 55.0)
cdo(gm).set_editor_property('AutoEvents', True)


def controller(name, fns, locals_=()):
    bp = load_or_create_bp(name, unreal.AIController)
    for v, t in (('NextShot', 'float'), ('NextSay', 'float'), ('BoomAt', 'float'), ('FireAt', 'float'),
                 ('NextStep', 'float'), ('NextScan', 'float'), ('IsMoving', 'bool'), ('MoveStart', 'float'),
                 ('Leaving', 'bool'), ('LeaveAt', 'float'), ('WakeAt', 'float'), ('BestD', 'float')):
        ensure_var(bp, v, t, category='GW')
    ensure_var(bp, 'Target', obj_class=chc, category='GW')
    ensure_var(bp, 'ShotAt', obj_class=chc, category='GW')
    ensure_var(bp, 'Cand', obj_class=chc, category='GW')
    ensure_var(bp, 'NoTarget', obj_class=chc, category='GW')
    ensure_var(bp, 'Points', obj_class=unreal.Actor, array=True, category='GW')
    ensure_fn(bp, 'Brain', inputs=[('Ch', chc)])
    ensure_fn(bp, 'Think')
    ensure_fn(bp, 'Roam', inputs=[('Ch', chc), ('Rooms', 'bool')])
    for f in fns:
        ensure_fn(bp, f, inputs=[('Ch', chc)])
    compile_bp(bp, quiet=True)
    for fn, n, t in locals_:
        g = get_graph(bp, fn)
        if n not in BT.list_variables(bp, g):
            if t == 'char':
                BT.add_object_variable(bp, n, chc, graph=g)
            else:
                BT.add_variable(bp, n, t, graph=g)
    return bp


THINK = '''
(fn Think ()
  (bind ch (Utilities|Casting|CastToBP_GW_Character (Pawn|GetControlledPawn :self self))
    (:then
      (if (GW|Get|BP_GW_Character|IsDead :self ch)
        (Utilities|Time|ClearTimerbyFunctionName :Object self :FunctionName "Think")
        (return))
      (CallFunction|Brain :Ch ch))
    (:CastFailed
      (Utilities|Time|ClearTimerbyFunctionName :Object self :FunctionName "Think")
      (Actor|DestroyActor :self self))))
'''
ROAM = '''
(fn Roam (Ch Rooms)
  (bind now (Utilities|Time|GetGameTimeinSeconds))
  (bind speed (Math|Vector|VectorLength (Transformation|GetVelocity :self Ch)))
  (if (and (Variables|GW|GetIsMoving) (or (> (- now (Variables|GW|GetMoveStart)) 25.0) (and (> (- now (Variables|GW|GetMoveStart)) 1.0) (< speed 10.0))))
    (Variables|GW|SetIsMoving false))
  (if (Variables|GW|GetIsMoving)
    (return))
  (if (== (Utilities|Array|Length (Variables|GW|GetPoints)) 0)
    (Variables|GW|SetPoints (Actor|GetAllActorswithTag :Tag "GW_NPCSpawn")))
  (bind origin (select Rooms (Transformation|GetActorLocation :self (Utilities|Array|Get(acopy) (Variables|GW|GetPoints) (Math|Random|RandomIntegerinRange 0 (- (Utilities|Array|Length (Variables|GW|GetPoints)) 1)))) (Transformation|GetActorLocation :self Ch)))
  (bind (d ok) (AI|Navigation|GetRandomReachablePointinRadius :Origin origin :Radius (select Rooms 250.0 1500.0)))
  (if ok
    (AI|Navigation|MovetoLocation :self self :Dest d :AcceptanceRadius 80.0 :bStopOnOverlap true :bUsePathfinding true :bProjectDestinationToNavigation true :bCanStrafe false :bAllowPartialPath true)
    (Variables|GW|SetIsMoving true)
    (Variables|GW|SetMoveStart now)))
'''
EG = '''
(event EventOnPossess (PossessedPawn)
  (Utilities|Time|SetTimerbyFunctionName :Object self :FunctionName "Think" :Time {t} :bLooping true :InitialStartDelayVariance 0.1))
'''


def gm_call(body):
    return f'''  (bind gm {GMC}
    (:then
{body})
    (:CastFailed))'''


mv0 = lambda v: f'(Math|Vector|MakeVector {v[0]} {v[1]} {v[2]})'
bandit = controller('BP_GW_BanditController', ['Shoot'], [('Shoot', 'Pick', 'char'), ('Shoot', 'Tries', 'int')])
write(bandit, 'Think', THINK, compile_after=False)
write(bandit, 'Roam', ROAM, compile_after=False)
write(bandit, 'Brain', f'''
(fn Brain (Ch)
  ; the attack is over: they walk back out by the main entrance (the user: no pop-out)
  (if (Variables|GW|GetLeaving)
    (bind t0 (Utilities|Time|GetGameTimeinSeconds))
    (if (GW|Get|BP_GW_Character|IsSprinting :self Ch)
      (GW|Call|BP_GW_Character|SetSprint :self Ch :On false))
    (if (or (< (Math|Vector|Distance2D(Vector) (Transformation|GetActorLocation :self Ch) {mv0(DOOR)}) 150.0) (> (- t0 (Variables|GW|GetLeaveAt)) 45.0))
      (Development|PrintString :InString (cat "GW: EV bandit out after " (- t0 (Variables|GW|GetLeaveAt)) " s at " (Transformation|GetActorLocation :self Ch)) :bPrintToScreen false)
      ; no pawn left: the next Think destroys this controller
      (Actor|DestroyActor :self Ch)
      (return))
    (if (or (not (Variables|GW|GetIsMoving)) (and (> (- t0 (Variables|GW|GetMoveStart)) 1.5) (< (Math|Vector|VectorLength (Transformation|GetVelocity :self Ch)) 10.0)))
      (AI|Navigation|MovetoLocation :self self :Dest {mv0(DOOR)} :AcceptanceRadius 60.0 :bStopOnOverlap true :bUsePathfinding true :bProjectDestinationToNavigation true :bCanStrafe false :bAllowPartialPath true)
      (Variables|GW|SetIsMoving true)
      (Variables|GW|SetMoveStart t0))
    (return))
  (if (not (GW|Get|BP_GW_Character|IsSprinting :self Ch))
    (GW|Call|BP_GW_Character|SetSprint :self Ch :On true))
  (CallFunction|Roam :Ch Ch :Rooms false)
  (bind now (Utilities|Time|GetGameTimeinSeconds))
  (if (>= now (Variables|GW|GetNextShot))
    (Variables|GW|SetNextShot (+ now (Math|Random|RandomFloatinRange 0.6 1.4)))
    (CallFunction|Shoot :Ch Ch)))
''', compile_after=False)
write(bandit, 'Shoot', f'''
(fn Shoot (Ch)
  (bind here (Transformation|GetActorLocation :self Ch))
  (bind all (Actor|GetAllActorsOfClass :ActorClass {CHAR}))
  (Variables|Default|SetPick (Variables|GW|GetNoTarget))
  (Variables|Default|SetTries 0)
  (while (and (< (Variables|Default|GetTries) 6) (not ({ISVALID} :Object (Variables|Default|GetPick))))
    (Variables|Default|SetTries (+ (Variables|Default|GetTries) 1))
    (Variables|GW|SetCand (Utilities|Array|Get(acopy) all (Math|Random|RandomIntegerinRange 0 (- (Utilities|Array|Length all) 1))))
    (bind c (Variables|GW|GetCand))
    (if (and (and (== (GW|Get|BP_GW_Character|Kind :self c) 0) (not (GW|Get|BP_GW_Character|IsDead :self c))) (< (Math|Vector|Distance(Vector) (Transformation|GetActorLocation :self c) here) 2500.0))
      (Variables|Default|SetPick c)))
  (bind t (Variables|Default|GetPick))
  (if (not ({ISVALID} :Object t))
    (return))
  (bind start (+ here (Math|Vector|MakeVector 0.0 0.0 55.0)))
  (bind aim (Math|Vector|Normalize (- (+ (Transformation|GetActorLocation :self t) (Math|Vector|MakeVector 0.0 0.0 30.0)) start)))
  (bind dir (Math|Random|RandomUnitVectorinEllipticalConeinDegrees :ConeDir aim :MaxYawInDegrees 11.0 :MaxPitchInDegrees 5.0))
  (Transformation|SetActorRotation :self Ch :NewRotation (Math|Rotator|MakeRotator :Yaw (.yaw (Math|Rotator|FindLookatRotation :Start here :Target (Transformation|GetActorLocation :self t)))) :bTeleportPhysics false)
{gm_call("      (GW|Call|BP_GW_GameMode|BanditShoot :self gm :Shooter Ch :Start (+ start (* dir 60.0)) :Dir dir)")})
''', compile_after=False)
write(bandit, 'EventGraph', EG.format(t=0.3), compile_after=False)
compile_bp(bandit)
print('BP_GW_BanditController', node_problems(bandit))
save(bandit)

kami = controller('BP_GW_KamikazeController', [])
KAMI_BOOM = gm_call('      (GW|Call|BP_GW_GameMode|Explode :self gm :Loc (Transformation|GetActorLocation :self Ch) :Radius 650.0 :Cause "a été soufflé par le kamikaze")')
write(kami, 'Think', THINK, compile_after=False)
write(kami, 'Roam', ROAM, compile_after=False)
write(kami, 'Brain', f'''
(fn Brain (Ch)
  (bind now (Utilities|Time|GetGameTimeinSeconds))
  (if (<= (Variables|GW|GetBoomAt) 0.0)
    (Variables|GW|SetBoomAt (+ now (Math|Random|RandomFloatinRange 15.0 25.0))))
  (if (not (GW|Get|BP_GW_Character|IsSprinting :self Ch))
    (GW|Call|BP_GW_Character|SetSprint :self Ch :On true))
  (CallFunction|Roam :Ch Ch :Rooms true)
  (if (>= now (Variables|GW|GetBoomAt))
    (Utilities|Time|ClearTimerbyFunctionName :Object self :FunctionName "Think")
{KAMI_BOOM}))
''', compile_after=False)
write(kami, 'EventGraph', EG.format(t=0.3), compile_after=False)
compile_bp(kami)
print('BP_GW_KamikazeController', node_problems(kami))
save(kami)

ROBOT_CHARGE, ROBOT_LOCK = 1.5, 0.5
robot = controller('BP_GW_RobotController', ['Scan', 'Fire', 'AimTick'], [('Scan', 'Seen', 'char')])
ensure_fn(robot, 'AimStop')
ensure_var(robot, 'AimPoint', struct=V3, category='GW')
ensure_var(robot, 'AimLockAt', 'float', category='GW')
ensure_var(robot, 'AimTicks', 'int', category='GW')
ensure_var(robot, 'IgnoreMe', obj_class=unreal.Actor, array=True, category='GW')
ensure_var(robot, 'AimBeam', obj_class=load_bp('BP_GW_Beam').generated_class(), category='GW')
ensure_var(robot, 'NoBeam', obj_class=load_bp('BP_GW_Beam').generated_class(), category='GW')
ensure_var(robot, 'LastSeen', struct=V3, category='GW')
ensure_var(robot, 'LastSeenAt', 'float', category='GW')
ensure_var(robot, 'Dbg', 'bool', category='GW')
ensure_var(robot, 'NextDbg', 'float', category='GW')
ensure_var(robot, 'GMRef', obj_class=load_bp('BP_GW_GameMode').generated_class(), category='GW')   # IsSmokeBetween
compile_bp(robot, quiet=True)
cdo(robot).set_editor_property('LastSeenAt', -100.0)
write(robot, 'Think', THINK, compile_after=False)
write(robot, 'Roam', ROAM, compile_after=False)
write(robot, 'Brain', f'''
(fn Brain (Ch)
  (bind now (Utilities|Time|GetGameTimeinSeconds))
  (Class|CharacterMovementComponent|SetMaxWalkSpeed :self (GW|Get|/Script/Engine.Character|CharacterMovement :self Ch) :MaxWalkSpeed 115.0)
  (bind sf (+ (Transformation|GetActorLocation :self Ch) (Math|Vector|MakeVector 0.0 0.0 110.0)))
  (bind sd (Transformation|GetActorForwardVector :self Ch))
  (if (== (Utilities|Array|Length (Variables|GW|GetIgnoreMe)) 0)
    (Utilities|Array|Add :TargetArray (Variables|GW|GetIgnoreMe) :NewItem Ch))
  ; from the eye itself, the robot's own body left out (a head start of 90 cm went through a wall right in front of it)
  (bind (sh sok) (Collision|LineTraceByChannel :Start sf :End (+ sf (* sd 3000.0)) :TraceChannel "Visibility" :bTraceComplex false :ActorsToIgnore (Variables|GW|GetIgnoreMe) :bIgnoreSelf true))
  (bind (sb si st sdist sl si2 sn sn2 sp sa) (Collision|BreakHitResult sh))
  ; while it charges, the cone closes: the only line left is the charging beam
  (bind want (select ({ISVALID} :Object (Variables|GW|GetTarget)) 0.01 (select sok (/ sdist 3000.0) 1.0)))
  (if (> (Math|Float|Absolute(Float) (- want (GW|Get|BP_GW_Character|SightLen :self Ch))) 0.02)
    (GW|Set|BP_GW_Character|SightLen :self Ch :SightLen want))
  (if ({ISVALID} :Object (Variables|GW|GetTarget))
    (if (>= now (Variables|GW|GetFireAt))
      (CallFunction|Fire :Ch Ch)
      (else
        (CallFunction|AimTick :Ch Ch)))
    (return))
  ; hunting: for 10 s after it last saw a player it walks to where that player was, else it roams the rooms
  (if (< (- now (Variables|GW|GetLastSeenAt)) 10.0)
    (if (> (- now (Variables|GW|GetMoveStart)) 1.0)
      (AI|Navigation|MovetoLocation :self self :Dest (Variables|GW|GetLastSeen) :AcceptanceRadius 150.0 :bStopOnOverlap true :bUsePathfinding true :bProjectDestinationToNavigation true :bCanStrafe false :bAllowPartialPath true)
      (Variables|GW|SetIsMoving true)
      (Variables|GW|SetMoveStart now))
    (else
      (CallFunction|Roam :Ch Ch :Rooms true)))
  (if (and (>= now (Variables|GW|GetNextStep)) (> (Math|Vector|VectorLength (Transformation|GetVelocity :self Ch)) 30.0))
    (Variables|GW|SetNextStep (+ now 0.62))
{gm_call(f"      (GW|Call|BP_GW_GameMode|Say :self gm :Ch Ch :Cat {CAT['robot_step']})")})
  (if (>= now (Variables|GW|GetNextScan))
    (Variables|GW|SetNextScan (+ now 0.15))
    (CallFunction|Scan :Ch Ch)))
''', compile_after=False)
write(robot, 'Scan', f'''
(fn Scan (Ch)
  (bind head (+ (Transformation|GetActorLocation :self Ch) (Math|Vector|MakeVector 0.0 0.0 110.0)))
  (bind fwd (Transformation|GetActorForwardVector :self Ch))
  (Variables|Default|SetSeen (Variables|GW|GetNoTarget))
  (if (not ({ISVALID} :Object (Variables|GW|GetGMRef)))
    (bind gm0 {GMC}
      (:then (Variables|GW|SetGMRef gm0))
      (:CastFailed)))
  ; QA diagnostic (-GWDevTest / -GWRobotLog), once a second: where it stands and why each player is or isn't seen
  (Variables|GW|SetDbg (and (or (Utilities|HasLaunchOption :OptionToCheck "GWDevTest") (Utilities|HasLaunchOption :OptionToCheck "GWRobotLog")) (>= (Utilities|Time|GetGameTimeinSeconds) (Variables|GW|GetNextDbg))))
  (if (Variables|GW|GetDbg)
    (Variables|GW|SetNextDbg (+ (Utilities|Time|GetGameTimeinSeconds) 1.0))
    (Development|PrintString :InString (cat "GW: robot scan at " (Transformation|GetActorLocation :self Ch) " yaw=" (.yaw (Transformation|GetActorRotation :self Ch)) " speed=" (Math|Vector|VectorLength (Transformation|GetVelocity :self Ch))) :bPrintToScreen false))
  (for c (Actor|GetAllActorsOfClass :ActorClass {CHAR})
    (if (Pawn|IsPlayerControlled :self c)
      (bind to (Math|Vector|Normalize (- (Transformation|GetActorLocation :self c) head)))
      (bind dot (Math|Vector|DotProduct fwd to))
      (bind dist (Math|Vector|Distance(Vector) (Transformation|GetActorLocation :self c) head))
      ; from the eye itself, the robot's own body left out (bIgnoreSelf is this controller, not its pawn); a head start of 90 cm saw through a near wall
      (bind (hit ok) (Collision|LineTraceByChannel :Start head :End (+ (Transformation|GetActorLocation :self c) (Math|Vector|MakeVector 0.0 0.0 30.0)) :TraceChannel "Visibility" :bTraceComplex false :ActorsToIgnore (Variables|GW|GetIgnoreMe) :bIgnoreSelf true))
      (bind (bBlock bInit hTime hDist hLoc hImpact hNormal hImpNormal hPhys hActor) (Collision|BreakHitResult hit))
      (if (Variables|GW|GetDbg)
        (Development|PrintString :InString (cat "GW: robot looks at " (Utilities|GetDisplayName :Object c) " dead=" (GW|Get|BP_GW_Character|IsDead :self c) " dist=" dist " dot=" dot " sight hits " (Utilities|GetDisplayName :Object hActor) " blocked=" ok) :bPrintToScreen false))
      ; seen = nothing blocks the line before his chest (characters ignore Visibility) or the line hits him
      (if (and (and (not (GW|Get|BP_GW_Character|IsDead :self c)) (< dist 3000.0)) (and (and (> dot 0.966) (or (not ok) (== hActor c))) (not (GW|Call|BP_GW_GameMode|IsSmokeBetween :self (Variables|GW|GetGMRef) :A head :B (+ (Transformation|GetActorLocation :self c) (Math|Vector|MakeVector 0.0 0.0 30.0))))))
        (Variables|Default|SetSeen c))))
  (bind s (Variables|Default|GetSeen))
  (if ({ISVALID} :Object s)
    (Development|PrintString :InString (cat "GW: robot spotted " (Utilities|GetDisplayName :Object s)) :bPrintToScreen false)
    (Variables|GW|SetLastSeen (Transformation|GetActorLocation :self s))
    (Variables|GW|SetLastSeenAt (Utilities|Time|GetGameTimeinSeconds))
    (Variables|GW|SetTarget s)
    (Variables|GW|SetFireAt (+ (Utilities|Time|GetGameTimeinSeconds) {ROBOT_CHARGE}))
    (Variables|GW|SetAimLockAt (+ (Utilities|Time|GetGameTimeinSeconds) {ROBOT_LOCK}))
    (Variables|GW|SetAimTicks 0)
    (AI|Navigation|StopMovement :self self)
    (Variables|GW|SetIsMoving false)
    (Transformation|SetActorRotation :self Ch :NewRotation (Math|Rotator|MakeRotator :Yaw (.yaw (Math|Rotator|FindLookatRotation :Start head :Target (Transformation|GetActorLocation :self s)))) :bTeleportPhysics false)
{gm_call(f"      (GW|Call|BP_GW_GameMode|WorldSound :self gm :Cat {CAT['servo']} :Loc head)" + chr(10) + f"      (GW|Call|BP_GW_GameMode|QueueSay :self gm :Ch Ch :Cat {CAT['robot_voice']} :Delay 0.35)")}))
''', compile_after=False)
write(robot, 'AimStop', f'''
(fn AimStop ()
  (bind b (Variables|GW|GetAimBeam))
  (if ({ISVALID} :Object b)
    (Actor|DestroyActor :self b))
  (Variables|GW|SetAimBeam (Variables|GW|GetNoBeam)))
''', compile_after=False)
# the warning: a thin beam, thicker and blinking as the shot comes; it holds its line after ROBOT_LOCK seconds
write(robot, 'AimTick', f'''
(fn AimTick (Ch)
  (bind t (Variables|GW|GetTarget))
  (if (GW|Get|BP_GW_Character|IsDead :self t)
    (CallFunction|AimStop)
    (Variables|GW|SetTarget (Variables|GW|GetNoTarget))
    (Variables|GW|SetNextScan (+ (Utilities|Time|GetGameTimeinSeconds) 0.5))
    (return))
  (bind now (Utilities|Time|GetGameTimeinSeconds))
  (bind head (+ (Transformation|GetActorLocation :self Ch) (Math|Vector|MakeVector 0.0 0.0 110.0)))
  (if (< now (Variables|GW|GetAimLockAt))
    (Variables|GW|SetAimPoint (+ (Transformation|GetActorLocation :self t) (Math|Vector|MakeVector 0.0 0.0 30.0)))
    (Transformation|SetActorRotation :self Ch :NewRotation (Math|Rotator|MakeRotator :Yaw (.yaw (Math|Rotator|FindLookatRotation :Start head :Target (Variables|GW|GetAimPoint)))) :bTeleportPhysics false))
  (if (not ({ISVALID} :Object (Variables|GW|GetAimBeam)))
    (Variables|GW|SetAimBeam (Game|SpawnActorfromClass :Class "/Game/GW/Blueprints/BP_GW_Beam.BP_GW_Beam_C" :SpawnTransform (Math|Transform|MakeTransform :Location head) :CollisionHandlingOverride "AlwaysSpawn"))
    (Actor|SetLifeSpan :self (Variables|GW|GetAimBeam) :InLifespan {ROBOT_CHARGE + 1.0})
    (GW|Set|BP_GW_Beam|BeamStart :self (Variables|GW|GetAimBeam) :BeamStart head)
    (GW|Set|BP_GW_Beam|Charge :self (Variables|GW|GetAimBeam) :Charge true))
  (Variables|GW|SetAimTicks (+ (Variables|GW|GetAimTicks) 1))
  (bind frac (Math|Float|Clamp(Float) :Value (- 1.0 (/ (- (Variables|GW|GetFireAt) now) {ROBOT_CHARGE})) :Min 0.0 :Max 1.0))
  (bind b (Variables|GW|GetAimBeam))
  (GW|Set|BP_GW_Beam|BeamStart :self b :BeamStart head)
  (GW|Set|BP_GW_Beam|Width :self b :Width (* (+ 0.5 (* 0.8 frac)) (select (== (% (Variables|GW|GetAimTicks) 2) 0) 1.0 0.65)))
  (GW|Set|BP_GW_Beam|BeamEnd :self b :BeamEnd (GW|Call|BP_GW_GameMode|RobotBeamEnd :self (Variables|GW|GetGMRef) :From head :Dir (Math|Vector|Normalize (- (Variables|GW|GetAimPoint) head)) :Who Ch))
  (Networking|ForceNetUpdate :self b))
''', compile_after=False)
write(robot, 'Fire', f'''
(fn Fire (Ch)
  (Variables|GW|SetTarget (Variables|GW|GetNoTarget))
  (Variables|GW|SetNextScan (+ (Utilities|Time|GetGameTimeinSeconds) 2.0))
  (CallFunction|AimStop)
  (bind head (+ (Transformation|GetActorLocation :self Ch) (Math|Vector|MakeVector 0.0 0.0 110.0)))
  ; no laser through a smoke cloud (shop's smoke grenade)
  (if (GW|Call|BP_GW_GameMode|IsSmokeBetween :self (Variables|GW|GetGMRef) :A head :B (Variables|GW|GetAimPoint))
    (return))
  (Development|PrintString :InString (cat "GW: robot fires, aim " (Variables|GW|GetAimPoint)) :bPrintToScreen false)
  (GW|Call|BP_GW_GameMode|RobotShot :self (Variables|GW|GetGMRef) :From head :End (GW|Call|BP_GW_GameMode|RobotBeamEnd :self (Variables|GW|GetGMRef) :From head :Dir (Math|Vector|Normalize (- (Variables|GW|GetAimPoint) head)) :Who Ch) :Who Ch))
''', compile_after=False)
write(robot, 'EventGraph', EG.format(t=0.2), compile_after=False)
compile_bp(robot)
print('BP_GW_RobotController', node_problems(robot))
save(robot)

# ---------------------------------------------------------------- game mode: framework, damage, events
mv = lambda v: f'(Math|Vector|MakeVector {v[0]} {v[1]} {v[2]})'
CTRL = {1: 'BP_GW_BanditController', 2: 'BP_GW_KamikazeController', 3: 'BP_GW_RobotController'}
KAMI_ALARM = '/Game/GW/Blueprints/BP_GW_KamiAlarm.BP_GW_KamiAlarm_C'
spawn_ctrl = '\n'.join(f'''  (if (== Kind {k})
    (bind c{k} (Game|SpawnActorfromClass :Class "/Game/GW/Blueprints/{n}.{n}_C" :SpawnTransform (Math|Transform|MakeTransform :Location Loc) :CollisionHandlingOverride "AlwaysSpawn"))
    (Pawn|Possess :self c{k} :InPawn ch))''' for k, n in CTRL.items())
G = {
    'SpawnSpecial': f'''
(fn SpawnSpecial (Kind Loc)
  (bind ch (Game|SpawnActorfromClass :Class {CHAR} :SpawnTransform (Math|Transform|MakeTransform :Location Loc) :CollisionHandlingOverride "AdjustIfPossibleButAlwaysSpawn"))
  (bind old (Pawn|GetController :self ch))
  (if ({ISVALID} :Object old)
    (Actor|DestroyActor :self old))
  (GW|Set|BP_GW_Character|IsSeeker :self ch :IsSeeker false)
  (GW|Set|BP_GW_Character|Health :self ch :Health (select (== Kind 3) (Variables|GW|GetRobotHP) 100.0))
  (GW|Set|BP_GW_Character|Variant :self ch :Variant (Math|Random|RandomIntegerinRange 0 1))
  (GW|Set|BP_GW_Character|Kind :self ch :Kind Kind)
{spawn_ctrl}
  (if (== Kind 2)
    (bind al (Game|SpawnActorfromClass :Class "{KAMI_ALARM}" :SpawnTransform (Math|Transform|MakeTransform :Location Loc) :CollisionHandlingOverride "AlwaysSpawn"))
    (GW|Set|{KAMI_ALARM}|Ch :self al :Ch ch))
  (return ch))
''',
    # players lose health (and die at 0: ghost, counts, maybe the round); a guest NPC dies and respawns later
    'HurtCharacter': '''
(fn HurtCharacter (Victim Amount Impulse Cause)
  (if (and (== (GW|Get|BP_GW_Character|Kind :self Victim) 4) (not (GW|Get|BP_GW_Character|IsDead :self Victim)))
    (CallFunction|ZombieDown :Victim Victim :Impulse Impulse)
    (return))
  (if (== (GW|Get|BP_GW_Character|Kind :self Victim) 3)
    (CallFunction|RobotHurt :Victim Victim :Amount Amount :Dir (Math|Vector|Normalize Impulse))
    (return))
  (if (or (GW|Get|BP_GW_Character|IsDead :self Victim) (!= (GW|Get|BP_GW_Character|Kind :self Victim) 0))
    (return))
  (if (Pawn|IsPlayerControlled :self Victim)
    (GW|Set|BP_GW_Character|Health :self Victim :Health (- (GW|Get|BP_GW_Character|Health :self Victim) Amount))
    (if (<= (GW|Get|BP_GW_Character|Health :self Victim) 0.0)
      (CallFunction|Announce :Text (cat (CallFunction|NameOf :P Victim) " " Cause " !"))
      (CallFunction|DeathCry :Victim Victim)
      (CallFunction|KillPlayer :Victim Victim :Impulse Impulse)
      (CallFunction|UpdateCounts))
    (return))
  (CallFunction|DeathCry :Victim Victim)
  (GW|Call|BP_GW_Character|Die :self Victim :Impulse Impulse)
  (Utilities|Array|Add :TargetArray (Variables|GW|GetPendingNPCRespawns) :NewItem (+ (CallFunction|Now) (Variables|GW|GetNPCRespawnDelay))))
''',
    # catches fire: flames, a scream, flailing arms (OnRep_Burning); an NPC runs off and dies 3.5 s later (BurnTick)
    'Ignite': f'''
(fn Ignite (Ch From)
  (if (not (GW|Get|BP_GW_Character|Burning :self Ch))
    (GW|Set|BP_GW_Character|Burning :self Ch :Burning true)
    (CallFunction|Say :Ch Ch :Cat {CAT['scream']})
    (if (not (Pawn|IsPlayerControlled :self Ch))
      (GW|Set|BP_GW_Character|BurnKillAt :self Ch :BurnKillAt (+ (CallFunction|Now) 3.5))
      (GW|Set|BP_GW_Character|BurnUntil :self Ch :BurnUntil (+ (CallFunction|Now) 3.5))
      (bind c (Utilities|Casting|CastToBP_GW_NPCController (Pawn|GetController :self Ch))
        (:then
          (GW|Set|BP_GW_NPCController|PanicUntil :self c :PanicUntil (+ (CallFunction|Now) 3.5))
          (GW|Set|BP_GW_NPCController|PanicFrom :self c :PanicFrom From)
          (GW|Set|BP_GW_NPCController|IsMoving :self c :IsMoving false)
          (GW|Set|BP_GW_NPCController|NextMoveTime :self c :NextMoveTime (CallFunction|Now)))
        (:CastFailed))))
  (GW|Set|BP_GW_Character|BurnUntil :self Ch :BurnUntil (Math|Float|Max(Float) (GW|Get|BP_GW_Character|BurnUntil :self Ch) (+ (CallFunction|Now) 2.5))))
''',
    'BurnTick': f'''
(fn BurnTick ()
  (for c (Actor|GetAllActorsOfClass :ActorClass {CHAR})
    (if (GW|Get|BP_GW_Character|Burning :self c)
      (if (and (> (GW|Get|BP_GW_Character|BurnKillAt :self c) 0.0) (>= (CallFunction|Now) (GW|Get|BP_GW_Character|BurnKillAt :self c)))
        (GW|Set|BP_GW_Character|BurnKillAt :self c :BurnKillAt 0.0)
        (CallFunction|HurtCharacter :Victim c :Amount 1000.0 :Impulse (Math|Vector|MakeVector 0.0 0.0 200.0) :Cause "a péri dans les flammes"))
      (if (or (> (CallFunction|Now) (GW|Get|BP_GW_Character|BurnUntil :self c)) (GW|Get|BP_GW_Character|IsDead :self c))
        (GW|Set|BP_GW_Character|Burning :self c :Burning false)))))
''',
    'BanditShoot': '''
(fn BanditShoot (Shooter Start Dir)
  (Variables|GW|SetGunContext true)
  (bind traceEnd (+ Start (* Dir 5000.0)))
  (bind (hit ok) (Collision|LineTraceByProfile :Start Start :End traceEnd :ProfileName "BlockAll" :bIgnoreSelf true))
  (bind (bBlock bInit hTime hDist hLoc hImpact hNormal hImpNormal hPhys hActor) (Collision|BreakHitResult hit))
  (GW|Set|BP_GW_Character|ShotEnd :self Shooter :ShotEnd (select ok hImpact traceEnd))
  (GW|Set|BP_GW_Character|ShotTime :self Shooter :ShotTime (GameState|GetServerWorldTimeSeconds :self (Game|GetGameState)))
  (GW|Set|BP_GW_Character|ShotCounter :self Shooter :ShotCounter (+ (GW|Get|BP_GW_Character|ShotCounter :self Shooter) 1))
  (if ok
    (bind v (Utilities|Casting|CastToBP_GW_Character hActor)
      (:then
        (Development|PrintString :InString (cat "GW: bandit hit " (Utilities|GetDisplayName :Object v)) :bPrintToScreen false)
        (CallFunction|HurtCharacter :Victim v :Amount 50.0 :Impulse (* Dir 600.0) :Cause "a été touché par une balle perdue"))
      (:CastFailed))))
''',
    'Explode': f'''
(fn Explode (Loc Radius Cause)
  (CallFunction|WorldSound :Cat {CAT['explosion']} :Loc Loc)
  (Game|SpawnActorfromClass :Class "/Game/GW/Blueprints/BP_GW_Explosion.BP_GW_Explosion_C" :SpawnTransform (Math|Transform|MakeTransform :Location Loc) :CollisionHandlingOverride "AlwaysSpawn")
  (for c (Actor|GetAllActorsOfClass :ActorClass {CHAR})
    (bind d (Math|Vector|Distance(Vector) (Transformation|GetActorLocation :self c) Loc))
    (if (and (< d Radius) (not (GW|Get|BP_GW_Character|IsDead :self c)))
      (if (== (GW|Get|BP_GW_Character|Kind :self c) 2)
        (GW|Call|BP_GW_Character|Die :self c :Impulse (Math|Vector|MakeVector 0.0 0.0 900.0))
        (else
          (CallFunction|HurtCharacter :Victim c :Amount 500.0 :Impulse (* (Math|Vector|Normalize (+ (- (Transformation|GetActorLocation :self c) Loc) (Math|Vector|MakeVector 0.0 0.0 80.0))) 1500.0) :Cause Cause)))))
  (CallFunction|StartPanic :Loc Loc :Dur 12.0))
''',
    # the line of the laser: stops at the first wall or prop (characters don't block Visibility; the robot is left out)
    'RobotBeamEnd': f'''
(fn RobotBeamEnd (From Dir Who)
  (Utilities|Array|Clear (Variables|Shop|GetTraceIgnore))
  (Utilities|Array|Add :TargetArray (Variables|Shop|GetTraceIgnore) :NewItem Who)
  (bind far (+ From (* Dir 3200.0)))
  (bind (hit ok) (Collision|LineTraceByChannel :Start From :End far :TraceChannel "Visibility" :bTraceComplex false :ActorsToIgnore (Variables|Shop|GetTraceIgnore) :bIgnoreSelf true))
  (bind (bBlock bInit hTime hDist hLoc hImpact hNormal hImpNormal hPhys hActor) (Collision|BreakHitResult hit))
  (return (select ok hImpact far)))
''',
    # the shot: the beam, the zap, the first character on the line (not a tick: one hit per shot)
    'RobotShot': f'''
(fn RobotShot (From End Who)
  (Variables|GW|SetGunContext true)
  (GW|Set|BP_GW_GameState|TenseUntil :self (CallFunction|GetGS) :TenseUntil (+ (GameState|GetServerWorldTimeSeconds :self (CallFunction|GetGS)) 25.0))
  (bind b (Game|SpawnActorfromClass :Class "/Game/GW/Blueprints/BP_GW_Beam.BP_GW_Beam_C" :SpawnTransform (Math|Transform|MakeTransform :Location From) :CollisionHandlingOverride "AlwaysSpawn"))
  (GW|Set|BP_GW_Beam|BeamStart :self b :BeamStart From)
  (GW|Set|BP_GW_Beam|Width :self b :Width 2.5)
  (GW|Set|BP_GW_Beam|BeamEnd :self b :BeamEnd End)
  (CallFunction|WorldSound :Cat {CAT['laser']} :Loc From)
  (bind dir (Math|Vector|Normalize (- End From)))
  (bind len (Math|Vector|Distance(Vector) End From))
  (Variables|GW|SetLaserD (+ len 1.0))
  (Variables|GW|SetLaserV (Variables|GW|GetNoChar))
  (for c (Actor|GetAllActorsOfClass :ActorClass {CHAR})
    (if (and (!= c Who) (not (GW|Get|BP_GW_Character|IsDead :self c)))
      (bind cl (Transformation|GetActorLocation :self c))
      (bind along (Math|Vector|DotProduct (- cl From) dir))
      (if (and (> along 0.0) (< along (Variables|GW|GetLaserD)))
        (bind near (+ From (* dir along)))
        (if (and (< (Math|Vector|Distance2D(Vector) near cl) 50.0) (< (Math|Float|Absolute(Float) (- (.z near) (.z cl))) 105.0))
          (Variables|GW|SetLaserD along)
          (Variables|GW|SetLaserV c)))))
  (bind v (Variables|GW|GetLaserV))
  (Development|PrintString :InString (cat "GW: laser line " From " -> " End " len " len " hits " (select ({ISVALID} :Object v) (Utilities|GetDisplayName :Object v) "nobody")) :bPrintToScreen false)
  (if ({ISVALID} :Object v)
    (CallFunction|HurtCharacter :Victim v :Amount (Variables|GW|GetRobotDmg) :Impulse (* dir 300.0) :Cause "a été désintégré par le robot")
    (Development|PrintString :InString (cat "GW: laser victim health " (GW|Get|BP_GW_Character|Health :self v) " dead " (GW|Get|BP_GW_Character|IsDead :self v)) :bPrintToScreen false)))
''',
    # bullets 100, sword 50, turret 25; at zero it falls
    'RobotHurt': f'''
(fn RobotHurt (Victim Amount Dir)
  (if (or (GW|Get|BP_GW_Character|IsDead :self Victim) (!= (GW|Get|BP_GW_Character|Kind :self Victim) 3))
    (return))
  (GW|Set|BP_GW_Character|Health :self Victim :Health (- (GW|Get|BP_GW_Character|Health :self Victim) Amount))
  (Development|PrintString :InString (cat "GW: robot hit -" Amount ", health " (GW|Get|BP_GW_Character|Health :self Victim)) :bPrintToScreen false)
  (if (<= (GW|Get|BP_GW_Character|Health :self Victim) 0.0)
    (CallFunction|RobotDown :Victim Victim :Dir Dir)
    (else
      (CallFunction|WorldSound :Cat {CAT['robot_step']} :Loc (Transformation|GetActorLocation :self Victim)))))
''',
    'RobotDown': f'''
(fn RobotDown (Victim Dir)
  (bind here (Transformation|GetActorLocation :self Victim))
  (GW|Call|BP_GW_Character|Die :self Victim :Impulse (* Dir 900.0))
  (Game|SpawnActorfromClass :Class "/Game/GW/Blueprints/BP_GW_Explosion.BP_GW_Explosion_C" :SpawnTransform (Math|Transform|MakeTransform :Location here) :CollisionHandlingOverride "AlwaysSpawn")
  (CallFunction|WorldSound :Cat {CAT['explosion']} :Loc here)
  (for b (Actor|GetAllActorsOfClass :ActorClass "/Game/GW/Blueprints/BP_GW_Beam.BP_GW_Beam_C")
    (Actor|DestroyActor :self b))
  (GW|Set|BP_GW_GameState|RobotOn :self (CallFunction|GetGS) :RobotOn false)
  (CallFunction|SayNearPlayers :Cat {CAT['calm']} :PerPlayer 1 :Delay 1.2 :Spread 2.0)
  (Development|PrintString :InString "GW: robot down" :bPrintToScreen false))
''',
    'StartAttack': f'''
(fn StartAttack ()
  (for k (range (Math|Random|RandomIntegerinRange 3 4))
    (CallFunction|SpawnSpecial :Kind 1 :Loc (+ {mv(DOOR)} (Math|Vector|MakeVector (* (- k 1.5) 140.0) (Math|Random|RandomFloatinRange 0.0 120.0) 0.0))))
  (CallFunction|StartPanic :Loc {mv(DOOR)} :Dur (+ (Variables|GW|GetEventEnd) (- 0.0 (CallFunction|Now))))
  (CallFunction|SayNearPlayers :Cat {CAT['attack_guest']} :PerPlayer 2 :Delay 0.4 :Spread 1.3))
''',
    'StartFire': f'''
(fn StartFire ()
  (bind pts (Actor|GetAllActorswithTag :Tag "GW_NPCSpawn"))
  (Utilities|Array|Clear (Variables|GW|GetFires))
  (CallFunction|FireAlarmOn)
  (for k (range (+ 10 (Utilities|Array|Length (CallFunction|GetGWPlayers))))
    (bind p (Transformation|GetActorLocation :self (Utilities|Array|Get(acopy) pts (Math|Random|RandomIntegerinRange 0 (- (Utilities|Array|Length pts) 1)))))
    (bind (fp fpok) (AI|Navigation|GetRandomReachablePointinRadius :Origin p :Radius 200.0))
    (bind f (Game|SpawnActorfromClass :Class "/Game/GW/Blueprints/BP_GW_Fire.BP_GW_Fire_C" :SpawnTransform (Math|Transform|MakeTransform :Location (select fpok (- fp (Math|Vector|MakeVector 0.0 0.0 5.0)) (- p (Math|Vector|MakeVector 0.0 0.0 95.0)))) :CollisionHandlingOverride "AlwaysSpawn"))
    (Utilities|Array|Add :TargetArray (Variables|GW|GetFires) :NewItem f)
    (CallFunction|WorldSound :Cat {CAT['fire_whoosh']} :Loc (Transformation|GetActorLocation :self f))
    (bind r4 (Math|Random|RandomIntegerinRange 0 3))
    (Variables|GW|SetWallDir (select (== r4 0) (Math|Vector|MakeVector 1.0 0.0 0.0) (select (== r4 1) (Math|Vector|MakeVector -1.0 0.0 0.0) (select (== r4 2) (Math|Vector|MakeVector 0.0 1.0 0.0) (Math|Vector|MakeVector 0.0 -1.0 0.0)))))
    (bind fb (Transformation|GetActorLocation :self f))
    (bind (whit wok) (Collision|LineTraceByChannel :Start (+ fb (Math|Vector|MakeVector 0.0 0.0 100.0)) :End (+ fb (+ (Math|Vector|MakeVector 0.0 0.0 100.0) (* (Variables|GW|GetWallDir) 700.0))) :TraceChannel "Visibility" :bTraceComplex false :bIgnoreSelf true))
    (bind (wb wi wt wd wl wImpact wNormal wn2 wp wa) (Collision|BreakHitResult whit))
    (if wok
      (bind wf (Game|SpawnActorfromClass :Class "/Game/GW/Blueprints/BP_GW_WallFire.BP_GW_WallFire_C" :SpawnTransform (Math|Transform|MakeTransform :Location (+ (Math|Vector|MakeVector (.x wImpact) (.y wImpact) (.z fb)) (* wNormal 6.0)) :Rotation (Math|Rotator|FindLookatRotation :Start (Math|Vector|MakeVector 0.0 0.0 0.0) :Target wNormal)) :CollisionHandlingOverride "AlwaysSpawn"))
      (Utilities|Array|Add :TargetArray (Variables|GW|GetFires) :NewItem wf)))
  (if (> (Utilities|Array|Length (Variables|GW|GetFires)) 0)
    (CallFunction|StartPanic :Loc (Transformation|GetActorLocation :self (Utilities|Array|Get(acopy) (Variables|GW|GetFires) 0)) :Dur 10.0))
  (CallFunction|SayNearPlayers :Cat {CAT['fire']} :PerPlayer 2 :Delay 0.5 :Spread 1.4))
''',
    'FireTick': '''
(fn FireTick ()
  (if (< (CallFunction|Now) (Variables|GW|GetNextFireDmg))
    (return))
  (Variables|GW|SetNextFireDmg (+ (CallFunction|Now) 0.25))
  ; the fire spreads: every 1.5 s a new blaze next to an existing one, up to 32
  (if (and (>= (CallFunction|Now) (Variables|GW|GetNextSpread)) (and (> (Utilities|Array|Length (Variables|GW|GetFires)) 0) (< (Utilities|Array|Length (Variables|GW|GetFires)) 32)))
    (Variables|GW|SetNextSpread (+ (CallFunction|Now) 1.5))
    (Variables|GW|SetSpreadFrom (Utilities|Array|Get(acopy) (Variables|GW|GetFires) (Math|Random|RandomIntegerinRange 0 (- (Utilities|Array|Length (Variables|GW|GetFires)) 1))))
    (if (GW|Call|/Script/Engine.KismetSystemLibrary|IsValid :Object (Variables|GW|GetSpreadFrom))
      (bind (sp sok) (AI|Navigation|GetRandomReachablePointinRadius :Origin (Transformation|GetActorLocation :self (Variables|GW|GetSpreadFrom)) :Radius 320.0))
      (if sok
        (bind nf (Game|SpawnActorfromClass :Class "/Game/GW/Blueprints/BP_GW_Fire.BP_GW_Fire_C" :SpawnTransform (Math|Transform|MakeTransform :Location (- sp (Math|Vector|MakeVector 0.0 0.0 5.0))) :CollisionHandlingOverride "AlwaysSpawn"))
        (Utilities|Array|Add :TargetArray (Variables|GW|GetFires) :NewItem nf)
        (CallFunction|WorldSound :Cat 30 :Loc sp))))
  (for f (Variables|GW|GetFires)
    (if (GW|Call|/Script/Engine.KismetSystemLibrary|IsValid :Object f)
      (bind fl (Transformation|GetActorLocation :self f))
      (for c (Actor|GetAllActorsOfClass :ActorClass "/Game/GW/Blueprints/BP_GW_Character.BP_GW_Character_C")
        (bind cl (Transformation|GetActorLocation :self c))
        (bind dz (- (.z cl) (+ (.z fl) 95.0)))
        (if (and (and (< (Math|Vector|Distance2D(Vector) cl fl) 150.0) (< (* dz dz) 25600.0)) (and (not (GW|Get|BP_GW_Character|IsDead :self c)) (== (GW|Get|BP_GW_Character|Kind :self c) 0)))
          (CallFunction|Ignite :Ch c :From fl)
          (if (Pawn|IsPlayerControlled :self c)
            (CallFunction|HurtCharacter :Victim c :Amount 10.0 :Impulse (Math|Vector|MakeVector 0.0 0.0 300.0) :Cause "a péri dans les flammes")))))))
''',
    'StartBlackout': f'''
(fn StartBlackout ()
  (CallFunction|WorldSound :Cat {CAT['power_down']} :Loc {mv(CENTER)})
  (CallFunction|StartPanic :Loc {mv(CENTER)} :Dur 6.0)
  (CallFunction|SayNearPlayers :Cat {CAT['blackout']} :PerPlayer 2 :Delay 1.0 :Spread 1.8))
''',
    'StartKamikaze': f'''
(fn StartKamikaze ()
  (bind pts (Actor|GetAllActorswithTag :Tag "GW_NPCSpawn"))
  (CallFunction|SpawnSpecial :Kind 2 :Loc (Transformation|GetActorLocation :self (Utilities|Array|Get(acopy) pts (Math|Random|RandomIntegerinRange 0 (- (Utilities|Array|Length pts) 1)))))
  (CallFunction|SayNearPlayers :Cat {CAT['shout']} :PerPlayer 1 :Delay 2.5 :Spread 1.0))
''',
    'StartRobot': f'''
(fn StartRobot ()
  (CallFunction|SpawnSpecial :Kind 3 :Loc {mv(DOOR)})
  (bind s (CallFunction|GetGS))
  (GW|Set|BP_GW_GameState|RobotOn :self s :RobotOn true)
  (CallFunction|SayNearPlayers :Cat {CAT['shout']} :PerPlayer 1 :Delay 1.5 :Spread 1.0))
''',
    'StartEvent': '\n'.join([
        '(fn StartEvent (Id)',
        '  (if (!= (GW|Get|BP_GW_GameState|EventId :self (CallFunction|GetGS)) 0)',
        '    (CallFunction|EndEvent))',
        '  (bind s (CallFunction|GetGS))',
        '  (bind now (CallFunction|Now))',
        '  (GW|Set|BP_GW_GameState|EventId :self s :EventId Id)',
        '  (GW|Set|BP_GW_GameState|EventStart :self s :EventStart (GameState|GetServerWorldTimeSeconds :self s))',
    ] + [f'''  (if (== Id {k})
    (GW|Set|BP_GW_GameState|EventName :self s :EventName "{name}")
    (Variables|GW|SetEventEnd (+ now (select (and (> (Variables|GW|GetEventDurSet) 0.0) (!= Id 5)) (Variables|GW|GetEventDurSet) {dur}))))'''
         for k, (name, dur) in EVENTS.items()] + [
        '  (CallFunction|Announce :Text (GW|Get|BP_GW_GameState|EventName :self s))',
        '  (Development|PrintString :InString (cat "GW: event " Id " started, ends in " (- (Variables|GW|GetEventEnd) now) " s") :bPrintToScreen false)',
        '  (if (== Id 1) (CallFunction|StartAttack))',
        '  (if (== Id 2) (CallFunction|StartFire))',
        '  (if (== Id 3) (CallFunction|StartBlackout))',
        '  (if (== Id 4) (CallFunction|StartKamikaze))',
        '  (if (== Id 6) (CallFunction|StartZombie))',
        '  (if (== Id 5) (CallFunction|StartRobot)))']),
    # the attack is over: the bandits still alive walk back out by the main entrance (BanditController Brain)
    'BanditsLeave': f'''
(fn BanditsLeave ()
  (for c (Actor|GetAllActorsOfClass :ActorClass {CHAR})
    (if (and (== (GW|Get|BP_GW_Character|Kind :self c) 1) (not (GW|Get|BP_GW_Character|IsDead :self c)))
      (bind bc (Utilities|Casting|CastToBP_GW_BanditController (Pawn|GetController :self c))
        (:then
          (GW|Set|BP_GW_BanditController|Leaving :self bc :Leaving true)
          (GW|Set|BP_GW_BanditController|IsMoving :self bc :IsMoving false)
          (GW|Set|BP_GW_BanditController|LeaveAt :self bc :LeaveAt (CallFunction|Now)))
        (:CastFailed)))))
''',
    'EndEvent': f'''
(fn EndEvent ()
  (bind s (CallFunction|GetGS))
  ; a bind re-reads its source: keep the id in a variable before clearing it
  (Variables|GW|SetEndingId (GW|Get|BP_GW_GameState|EventId :self s))
  (bind id (Variables|GW|GetEndingId))
  (if (== id 0)
    (return))
  (GW|Set|BP_GW_GameState|EventId :self s :EventId 0)
  (Development|PrintString :InString (cat "GW: event " id " ended") :bPrintToScreen false)
  (if (== id 6)
    (CallFunction|EndZombie))
  (if (== id 1)
    (CallFunction|BanditsLeave)
    (CallFunction|SayNearPlayers :Cat {CAT['calm']} :PerPlayer 1 :Delay 1.0 :Spread 2.0))
  (if (== id 2)
    (for f (Variables|GW|GetFires)
      (if (GW|Call|/Script/Engine.KismetSystemLibrary|IsValid :Object f)
        (Actor|DestroyActor :self f)))
    (Utilities|Array|Clear (Variables|GW|GetFires))
    (CallFunction|FireAlarmOff)
    (CallFunction|SayNearPlayers :Cat {CAT['fire_after']} :PerPlayer 1 :Delay 0.8 :Spread 2.0))
  (if (== id 3)
    (CallFunction|WorldSound :Cat {CAT['power_up']} :Loc {mv(CENTER)})
    (CallFunction|SayNearPlayers :Cat {CAT['blackout_after']} :PerPlayer 1 :Delay 0.6 :Spread 1.5))
  (if (== id 4)
    (for c (Actor|GetAllActorsOfClass :ActorClass {CHAR})
      (if (and (== (GW|Get|BP_GW_Character|Kind :self c) 2) (not (GW|Get|BP_GW_Character|IsDead :self c)))
        (CallFunction|Explode :Loc (Transformation|GetActorLocation :self c) :Radius 650.0 :Cause "a été soufflé par le kamikaze")))))
''',
    # runs every RoundTick: ends events on time (or when the round is over), burns, starts automatic events
    'EventTick': '''
(fn EventTick ()
  (CallFunction|Events2Tick)
  (bind s (CallFunction|GetGS))
  (bind id (GW|Get|BP_GW_GameState|EventId :self s))
  (bind phase (GW|Get|BP_GW_GameState|Phase :self s))
  (bind now (CallFunction|Now))
  (if (and (!= id 0) (or (>= now (Variables|GW|GetEventEnd)) (or (== phase 0) (== phase 3))))
    (CallFunction|EndEvent))
  (if (== id 2)
    (CallFunction|FireTick))
  (CallFunction|BurnTick)
  (if (and (GW|Get|BP_GW_GameState|RobotOn :self s) (or (== phase 0) (== phase 3)))
    (GW|Set|BP_GW_GameState|RobotOn :self s :RobotOn false))
  ; outside the hunt the clock stays 45 s ahead, so the first event of a round comes 45 s into the hunt
  (if (!= phase 2)
    (Variables|GW|SetNextEventAt (+ now 45.0)))
  (if (and (and (Variables|GW|GetAutoEvents) (== phase 2)) (and (== id 0) (>= now (Variables|GW|GetNextEventAt))))
    (Variables|GW|SetNextEventAt (+ now (Variables|GW|GetEventEvery)))
    (Variables|GW|SetEventPick (Math|Random|RandomIntegerinRange 1 6))
    (CallFunction|StartEvent :Id (select (and (== (Variables|GW|GetEventPick) 5) (GW|Get|BP_GW_GameState|RobotOn :self s)) 6 (Variables|GW|GetEventPick)))))
''',
    # what an event is about: the first fire, else a living bandit / kamikaze / robot
    'EventFocus': f'''
(fn EventFocus ()
  (for f (Variables|GW|GetFires)
    (if ({ISVALID} :Object f)
      (return (Transformation|GetActorLocation :self f) true)))
  (for c (Actor|GetAllActorsOfClass :ActorClass {CHAR})
    (if (and (!= (GW|Get|BP_GW_Character|Kind :self c) 0) (not (GW|Get|BP_GW_Character|IsDead :self c)))
      (return (Transformation|GetActorLocation :self c) true)))
  (return (Math|Vector|MakeVector 0.0 0.0 0.0) false))
''',
}
for name, code in G.items():
    if name == 'HurtCharacter':      # s46_last_standing.py owns it
        continue
    write(gm, name, code, compile_after=False)
compile_bp(gm)
print('BP_GW_GameMode', node_problems(gm))
save(gm)

# ---------------------------------------------------------------- player controller: blackout, sting (local only)
pc = load_bp('BP_GW_PlayerController')
ensure_var(pc, 'LastEventStart', 'float', category='GW')
ensure_var(pc, 'DarkOn', 'bool', category='GW')
ensure_var(pc, 'AlarmComp', obj_class=unreal.AudioComponent, category='GW')
ensure_var(pc, 'NoAlarm', obj_class=unreal.AudioComponent, category='GW')
ensure_fn(pc, 'EventClientTick')
ensure_fn(pc, 'PianoClientTick')                    # body: s33_piano.py
for f in ('ShopClientTick', 'SocialClientTick', 'TurretClientTick', 'ViewClientTick', 'PickupClientTick', 'BreakerClientTick'):    # s34 / s36 / s35 / s37 / s38 / s40
    ensure_fn(pc, f)
ensure_fn(pc, 'DevEventShot')
ensure_fn(pc, 'DevEventShotNow')
compile_bp(pc, quiet=True)
write(pc, 'DevEventShot', '''
(fn DevEventShot ()
  (CallFunction|DevServer :Cmd "GWDevEventGo")
  (Utilities|Time|SetTimerbyFunctionName :Object self :FunctionName "DevEventShotNow" :Time 0.6 :bLooping false))
''', compile_after=False)
write(pc, 'DevEventShotNow', '(fn DevEventShotNow () (Development|ExecuteConsoleCommand :Command "Shot showui" :SpecificPlayer self))', compile_after=False)
ensure_fn(pc, 'SetDark', inputs=[('On', 'bool')])
compile_bp(pc, quiet=True)
write(pc, 'SetDark', '''
(fn SetDark (On)
  (Variables|GW|SetDarkOn On)
  (for a (Actor|GetAllActorsOfClass :ActorClass "/Script/Engine.Light")
    (Rendering|SetActorHiddenInGame :self a :bNewHidden On))
  (for a (Actor|GetAllActorsOfClass :ActorClass "/Script/Engine.SkyLight")
    (Rendering|SetActorHiddenInGame :self a :bNewHidden On))
  (Development|ExecuteConsoleCommand :Command (select On "ShowFlag.EyeAdaptation 0" "ShowFlag.EyeAdaptation 2") :SpecificPlayer self))
''', compile_after=False)
write(pc, 'EventClientTick', f'''
(fn EventClientTick ()
  (CallFunction|PianoClientTick)
  (CallFunction|ShopClientTick)
  (CallFunction|SocialClientTick)
  (CallFunction|TurretClientTick)
  (CallFunction|ViewClientTick)
  (CallFunction|PickupClientTick)
  (CallFunction|BreakerClientTick)
  (bind s {GSC}
    (:then
      (bind id (GW|Get|BP_GW_GameState|EventId :self s))
      (if (and (!= id 0) (!= (GW|Get|BP_GW_GameState|EventStart :self s) (Variables|GW|GetLastEventStart)))
        (Variables|GW|SetLastEventStart (GW|Get|BP_GW_GameState|EventStart :self s))
        (Audio|PlaySound2D :Sound (GW|Get|BP_GW_GameState|EventSting :self s) :VolumeMultiplier 1.0)
        ; -GWDevShot: a screenshot of every event 2.5 s in (QA)
        (if (Utilities|HasLaunchOption :OptionToCheck "GWDevShot")
          (Utilities|Time|SetTimerbyFunctionName :Object self :FunctionName "DevEventShot" :Time 2.5 :bLooping false)))
      (if (!= (== id 3) (Variables|GW|GetDarkOn))
        (CallFunction|SetDark :On (== id 3)))
      ; "Au feu !": the fire bell rings on every client until the fire is out
      (if (and (== id 2) (not ({ISVALID} :Object (Variables|GW|GetAlarmComp))))
        (Variables|GW|SetAlarmComp (Audio|SpawnSound2D :Sound (GW|Get|BP_GW_GameState|FireAlarm :self s) :VolumeMultiplier 0.32)))
      (if (and (!= id 2) ({ISVALID} :Object (Variables|GW|GetAlarmComp)))
        (GW|Call|/Script/Engine.AudioComponent|FadeOut :self (Variables|GW|GetAlarmComp) :FadeOutDuration 1.5 :FadeVolumeLevel 0.0)
        (Variables|GW|SetAlarmComp (Variables|GW|GetNoAlarm)))
      (bind me (Utilities|Casting|CastToBP_GW_Character (Pawn|GetControlledPawn :self self))
        (:then (Rendering|SetVisibility :self (GW|Get|BP_GW_Character|Flashlight :self me) :bNewVisibility (Variables|GW|GetDarkOn) :bPropagateToChildren false))
        (:CastFailed)))
    (:CastFailed)))
''', compile_after=False)
compile_bp(pc)
print('BP_GW_PlayerController', node_problems(pc))
save(pc)
