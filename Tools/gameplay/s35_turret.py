"""The mezzanine machine gun: a mounted 1930s tripod gun on the hall's gallery, any player can use it.

- Where: on the gallery floor (z 500) 45 cm behind the balustrade, between the newel posts at x 3000 and 3355, facing
  south over the hall and the entrance (manor_layout.json "gallery"; build_manor.py stairs_and_gallery: balustrade
  y 1942-1960, newels at x 2645 / 3000 / 3355; dress.py keeps the chairs and benches at y >= 2300, so the gunner at
  y ~2090 leaves the walkway behind him free). BP_GW_GameMode.TurretTick (s31 ReactionsTick, 0.25 s) spawns it at
  runtime on L_Manor (no level edit). Placeholder geometry from basic shapes (dark metal, brass, dark wood): tripod,
  pedestal, Vickers-style water jacket, flash hider, spade grips, ammo box with a brass belt.
- E near it (TryTurret, from InteractOther) mounts it: the server teleports the player behind the gun and freezes his
  movement; E again dismounts. One gunner at a time (BP_GW_Turret.Gunner, replicated).
- Mounted: the camera glides from the eyes to the gun's sight (s37 BP_GW_ViewDriver through
  BP_GW_PlayerController.TurretFrame, every frame); the view is held within the gun's arc (yaw +-75, pitch -40..+12)
  and turns the gun at once on the gunner's machine; the aim goes to the server (ServerExec GWTurretAim, ~12 Hz);
  left click held = automatic fire (GWTurretTrigger 1/0), 9 rounds/s.
- Server (BP_GW_Turret.ServerTick / FireOne): each round converges on what the crosshair (the sight's ray) shows,
  with 1.1 deg of spread; a hit BP_GW_Character goes to BP_GW_GameMode.TurretHit:
    detective at the gun -> OnCharacterShot (the usual rules: guest players unmasked, innocents cost health,
                            bandits / kamikaze / robot);
    guest at the gun     -> NPC: DeathCry, death, respawn later, RewardNPCKill(Killer, Victim) (+100 $, shop agent);
                            detective: DeathCry, KillPlayer, anonymous announcement (+ the shop's reward when it exists);
                            other guests are never hurt; bandit falls, kamikaze explodes, robot: bullets bounce.
  Every burst panics the manor for 10 s (StartPanic(muzzle, 10) when GS.PanicUntil < now + 4).
- Ammo: guests use BP_GW_PlayerState.TurretAmmo (replicated int, bought in the shop; 1 per round). Detectives have
  unlimited rounds but 3 s of fire (usable in several taps, BurstLeft), then a 25 s recharge (CoolUntil).
  The gunner's hand gun is kept silent while mounted (s11 ServerFire cooldown via LastFireTime).
- Every machine plays the gun from the replicated Firing flag: one shot sound per round (bank category turret_fire,
  ATT_GW_Far: loud and positional; Tools/audio/synth_turret.py), muzzle flash + light, tracer streaks every second
  round; the empty / overheat click is turret_empty (WorldSound).
- HUD while mounted: WBP_GW_TurretHUD (own widget): crosshair (guests: the HUD shows one only to detectives),
  "MUNITIONS : 42" / "RAFALE : 2,4 s" / "RECHARGE : 18 s" + bar + key hints. A floating "E" prompt near the gun.
- Dev menu (u15, Joueur): "Aller à la tourelle" (GWDevTurretGo), "Donner 60 munitions de tourelle"
  (GWDevTurretAmmo). Headless test: -GWDev -GWTurretTest (TurretTestTick: guest mount/fire/kill/dismount, detective
  burst/cooldown, aim-down-sights rotation, view switch), log lines "GW: turret ..." / "GW turrettest ...".
Usage: ue_run.py s35_turret.py  (after s37_view.py; then u15_dev_menu.py for the menu lines)
"""
import sys, importlib
sys.path.insert(0, r'J:\Projets\Unreal_Projects\Guess Who\Tools\gameplay')
import gw_lib; importlib.reload(gw_lib)
from gw_lib import *

REP = unreal.BlueprintVariableReplication
V3 = unreal.Vector.static_struct()
RT = unreal.Rotator.static_struct()
ISVALID = 'GW|Call|/Script/Engine.KismetSystemLibrary|IsValid'
GSC = '(Utilities|Casting|CastToBP_GW_GameState (Game|GetGameState))'
GMC = '(Utilities|Casting|CastToBP_GW_GameMode (Game|GetGameMode))'
MYCH = '(Utilities|Casting|CastToBP_GW_Character (Pawn|GetControlledPawn :self self))'
CHAR = '"/Game/GW/Blueprints/BP_GW_Character.BP_GW_Character_C"'
FOLDER = '/Game/GW/Blueprints/Turret'
TUR = f'{FOLDER}/BP_GW_Turret.BP_GW_Turret_C'
HUDW = f'{FOLDER}/WBP_GW_TurretHUD.WBP_GW_TurretHUD_C'
EAL_ = unreal.EditorAssetLibrary
AT = unreal.AssetToolsHelpers.get_asset_tools()
# placement (world) and geometry (turret space: X forward, root on the gallery floor)
TX, TY, TZ, TYAW = 3177.0, 2005.0, 500.0, -90.0
PIVOT_Z = 155.0
MUZ = (110.0, 0.0, 1.0)
CAMP = (-84.0, 0.0, 33.0)                          # the sight: above and behind the receiver
SEAT_X = -85.0
RATE, BURST, COOL = 9.0, 3.0, 25.0
INTERVAL = round(1.0 / RATE, 4)
YAW_LIM, PMIN, PMAX, SPREAD, RANGE = 30.0, -40.0, 12.0, 1.1, 9000.0
NEAR, NEAR_Z = 170.0, 160.0
CAT_FIRE, CAT_EMPTY = 38, 39                       # s31_reactions.py CAT turret_fire / turret_empty
TRACERS = 4
TR_SPEED, TR_LEN = 17000.0, 480.0                  # visual tracer speed (cm/s) and streak length
TR_W = 0.055                                       # tracer thickness (basic cylinder scale)


def mv(v):
    return f'(Math|Vector|MakeVector {float(v[0])} {float(v[1])} {float(v[2])})'


ERRORS = []


def wr(bp, name, code):
    """Rewrite one of OUR graphs from scratch (stale nodes wired to the entry pins otherwise survive a rewrite)."""
    g = get_graph(bp, name)
    for node in list(BT.find_nodes(g)):
        if node.get_class().get_name() in ('K2Node_FunctionEntry', 'K2Node_FunctionResult'):
            for p in node.list_all_pins():
                for c in list(p.list_connected_pins()):
                    p.break_single_pin_link(c)
            continue
        BT.delete_node(node)
    try:
        write(bp, name, code, compile_after=False)
    except Exception as e:                            # keep going: every broken graph is reported in one run
        ERRORS.append(f'{bp.get_name()}.{name}: {str(e)[:300]}')


def lock(asset, on):
    import time
    with open(r'J:\Projets\Unreal_Projects\Guess Who\Tools\agent_logs\locks.md', 'a', encoding='utf-8') as fh:
        fh.write(f"{'LOCK' if on else 'UNLOCK'} {asset} camera-combat {time.strftime('%H:%M')}\n")


def local(bp, fn, name, typ=None, obj=None):
    g = get_graph(bp, fn)
    if name in BT.list_variables(bp, g):
        return
    if obj is not None:
        BT.add_object_variable(bp, name, obj, graph=g)
    else:
        BT.add_variable(bp, name, typ, graph=g)


# ---------------------------------------------------------------- materials
def find_mat(cands, fallback):
    for c in cands:
        p = f'/Game/GW/Materials/{c}'
        if EAL_.does_asset_exist(p):
            return unreal.load_asset(p)
    print('material fallback for', cands[0])
    return unreal.load_asset(fallback)


MEL = unreal.MaterialEditingLibrary


def emissive_mi(name, color, strength):
    p = f'{FOLDER}/{name}'
    m = unreal.load_asset(p) if EAL_.does_asset_exist(p) else AT.create_asset(name, FOLDER, unreal.MaterialInstanceConstant, unreal.MaterialInstanceConstantFactoryNew())
    MEL.set_material_instance_parent(m, unreal.load_asset('/Game/GW/Materials/Master/M_GW_Emissive'))
    MEL.set_material_instance_vector_parameter_value(m, 'Color', unreal.LinearColor(*color))
    MEL.set_material_instance_scalar_parameter_value(m, 'Strength', strength)
    MEL.update_material_instance(m)
    EAL_.save_loaded_asset(m)
    return m


M_METAL = find_mat(['MI_GW_Gunmetal', 'MI_GW_Iron_Dark', 'MI_GW_Metal_Dark', 'MI_GW_Iron', 'MI_GW_Steel', 'MI_GW_Metal_Black',
                    'MI_GW_BlackIron', 'MI_GW_Iron_Black'], '/Engine/EngineMaterials/DefaultMaterial')
M_BRASS = find_mat(['MI_GW_Brass', 'MI_GW_GoldLeaf'], '/Engine/EngineMaterials/DefaultMaterial')
M_WOOD = find_mat(['MI_GW_Wood_Dark', 'MI_GW_Wood_Walnut'], '/Engine/EngineMaterials/DefaultMaterial')
M_FLASH = unreal.load_asset('/Game/GW/Materials/MI_GW_Blast')
M_TRACER = emissive_mi('MI_GW_Tracer', (1.0, 0.62, 0.18, 1), 55.0)
print('materials', M_METAL.get_name(), M_BRASS.get_name(), M_WOOD.get_name())

# ---------------------------------------------------------------- the turret actor
ch = load_bp('BP_GW_Character')
chc = ch.generated_class()
cap = cdo(ch).get_editor_property('capsule_component')
HH = float(cap.get_unscaled_capsule_half_height()) + 2.0
tur = load_or_create_bp('BP_GW_Turret', unreal.Actor, FOLDER)
compile_bp(tur, quiet=True)
TURRET_ONLY = 'turret' in UE_ARGS   # only BP_GW_Turret + WBP_GW_TurretHUD: no shared Blueprint is touched (run via cc_chain)

# signatures other graphs call before their bodies exist (game mode, player state)
# ---------------------------------------------------------------- game mode: spawn, hits, view server tick
gm = load_bp('BP_GW_GameMode')
if not TURRET_ONLY:
    ensure_var(gm, 'Turret', obj_class=tur.generated_class(), category='GW')
    for f in ('TurretTick', 'ViewServerTick'):
        ensure_fn(gm, f)
    ensure_fn(gm, 'TurretHit', inputs=[('Gunner', chc), ('Victim', chc), ('Dir', V3)])
    ensure_fn(gm, 'IsOnTurret', inputs=[('P', unreal.Pawn)], outputs=[('On', 'bool')], pure=True)
    compile_bp(gm, quiet=True)
# the voice director's s39 adds StartPanicCause (Cause 1 = a gun: nearby guests shout "il tire !"); plain panic before
PANIC = ('(GW|Call|BP_GW_GameMode|StartPanicCause :self gm :Loc muzzle :Dur 10.0 :Cause 1)' if 'StartPanicCause' in graph_names(gm)
         else '(GW|Call|BP_GW_GameMode|StartPanic :self gm :Loc muzzle :Dur 10.0)')
print('turret panic call:', PANIC.split('|')[3].split()[0])

# ---------------------------------------------------------------- player state: the guest's turret ammo
ps = load_bp('BP_GW_PlayerState')
if not TURRET_ONLY and 'TurretAmmo' not in [str(v) for v in BT.list_variables(ps)]:
    lock('/Game/GW/Blueprints/BP_GW_PlayerState', True)
    ensure_var(ps, 'TurretAmmo', 'int', rep=REP.REPLICATED, category='Shop')
    compile_bp(ps)
    save(ps)
    lock('/Game/GW/Blueprints/BP_GW_PlayerState', False)
    print('created BP_GW_PlayerState.TurretAmmo')

td = cdo(tur)
td.set_editor_property('replicates', True)
td.set_editor_property('always_relevant', True)

SHAPES = '/Engine/BasicShapes/'


def part(name, shape, mat, parent, loc=(0, 0, 0), rot=(0, 0, 0), scale=(1, 1, 1), shadow=True, coll=False):
    c = ensure_component(tur, name, unreal.StaticMeshComponent, parent)
    c.set_editor_property('static_mesh', unreal.load_asset(SHAPES + shape))
    c.set_editor_property('override_materials', [mat])
    c.set_editor_property('relative_location', unreal.Vector(*loc))
    c.set_editor_property('relative_rotation', unreal.Rotator(roll=rot[0], pitch=rot[1], yaw=rot[2]))
    c.set_editor_property('relative_scale3d', unreal.Vector(*scale))
    c.set_editor_property('cast_shadow', shadow)
    if coll:
        c.set_collision_profile_name('BlockAllDynamic')
    else:
        c.set_collision_enabled(unreal.CollisionEnabled.NO_COLLISION)
        c.set_editor_property('generate_overlap_events', False)
    return c


def scene(name, parent, loc=(0, 0, 0)):
    c = ensure_component(tur, name, unreal.SceneComponent, parent)
    c.set_editor_property('relative_location', unreal.Vector(*loc))
    return c


R = 'DefaultSceneRoot'
X_AXIS = (0, -90, 0)                                   # a basic cylinder's axis (Z) turned onto X
part('Pedestal', 'Cylinder', M_METAL, R, (0, 0, 64), scale=(0.2, 0.2, 1.28), coll=True)
part('Collar', 'Cylinder', M_BRASS, R, (0, 0, 130), scale=(0.28, 0.28, 0.06))
part('Hub', 'Cylinder', M_METAL, R, (0, 0, 72), scale=(0.26, 0.26, 0.12))
for i, yaw in enumerate((180.0, 60.0, -60.0)):          # tripod legs: rear one straight back, front ones clear of the rail
    import math
    rad = math.radians(yaw)
    part(f'Leg{i}', 'Cube', M_METAL, R, (28 * math.cos(rad), 28 * math.sin(rad), 36), rot=(0, -39, yaw), scale=(0.05, 0.05, 0.92))
    part(f'Foot{i}', 'Cube', M_METAL, R, (57 * math.cos(rad), 57 * math.sin(rad), 2), rot=(0, 0, yaw), scale=(0.14, 0.08, 0.04))
scene('Swivel', R, (0, 0, PIVOT_Z))
part('Yoke', 'Cube', M_METAL, 'Swivel', (0, 0, -13), scale=(0.16, 0.22, 0.2))
scene('Cradle', 'Swivel')
part('Receiver', 'Cube', M_METAL, 'Cradle', (-6, 0, 0), scale=(0.52, 0.13, 0.17))
part('Jacket', 'Cylinder', M_METAL, 'Cradle', (51, 0, 1), rot=X_AXIS, scale=(0.13, 0.13, 0.62))
for i, x in enumerate((22.0, 51.0, 80.0)):
    part(f'Ring{i}', 'Cylinder', M_BRASS, 'Cradle', (x, 0, 1), rot=X_AXIS, scale=(0.145, 0.145, 0.03))
part('Barrel', 'Cylinder', M_METAL, 'Cradle', (92, 0, 1), rot=X_AXIS, scale=(0.04, 0.04, 0.2))
part('Hider', 'Cylinder', M_BRASS, 'Cradle', (104, 0, 1), rot=X_AXIS, scale=(0.075, 0.075, 0.08))
for i, y in enumerate((6.5, -6.5)):
    part(f'Grip{i}', 'Cylinder', M_WOOD, 'Cradle', (-37, y, -3), rot=(0, 12, 0), scale=(0.045, 0.045, 0.13))
part('Trigger', 'Cube', M_BRASS, 'Cradle', (-35, 0, 1), scale=(0.025, 0.06, 0.03))
part('AmmoBox', 'Cube', M_METAL, 'Cradle', (-4, -15, -7), scale=(0.2, 0.12, 0.16))
part('Belt', 'Cube', M_BRASS, 'Cradle', (-4, -8.5, 1.5), scale=(0.1, 0.05, 0.025))
part('SightF', 'Cube', M_METAL, 'Cradle', (78, 0, 9), scale=(0.012, 0.012, 0.07))
part('SightR', 'Cube', M_METAL, 'Cradle', (-20, 0, 11), scale=(0.025, 0.06, 0.05))
scene('MuzzlePoint', 'Cradle', MUZ)
scene('CamPoint', 'Cradle', CAMP)
part('MuzzleFlash', 'Sphere', M_FLASH, 'Cradle', (MUZ[0] + 9, 0, 1), scale=(0.34, 0.15, 0.15), shadow=False)
fl = ensure_component(tur, 'MuzzleLight', unreal.PointLightComponent, 'Cradle')
fl.set_editor_property('relative_location', unreal.Vector(MUZ[0] + 4, 0, 4))
fl.set_editor_property('intensity', 0.0)
fl.set_editor_property('attenuation_radius', 1100.0)
fl.set_editor_property('light_color', unreal.Color(r=255, g=175, b=90, a=255))   # warm muzzle flash (keywords: the
#                                                       positional order rendered it blue-white in gun2's shots)
fl.set_editor_property('cast_shadows', False)
for i in range(TRACERS):
    t_ = part(f'Tracer{i}', 'Cylinder', M_TRACER, R, (0, 0, 0), scale=(TR_W, TR_W, 1), shadow=False)
    t_.set_editor_property('absolute_location', True)
    t_.set_editor_property('absolute_rotation', True)
    t_.set_editor_property('absolute_scale', True)
    t_.set_editor_property('visible', False)
compile_bp(tur, quiet=True)

for v, t in (('AimYaw', 'float'), ('AimPitch', 'float'), ('Firing', 'bool'), ('CoolUntil', 'float'), ('BurstLeft', 'float'),
             ('ShotsFired', 'int')):
    ensure_var(tur, v, t, rep=REP.REPLICATED, category='Turret')
ensure_var(tur, 'Gunner', obj_class=chc, rep=REP.REPLICATED, category='Turret')
for v, t in (('TriggerDown', 'bool'), ('ShotAcc', 'float'), ('Clicked', 'bool'), ('VisYaw', 'float'), ('VisPitch', 'float'),
             ('LocalGun', 'bool'), ('LocalAcc', 'float'), ('FlashT', 'float'), ('ShotN', 'int'), ('TrN', 'int'),
             ('FireIdxDone', 'bool'), ('BurstShots', 'int')):
    ensure_var(tur, v, t, category='Turret')
for i in range(TRACERS):
    ensure_var(tur, f'TrA{i}', struct=V3, category='Turret')
    ensure_var(tur, f'TrB{i}', struct=V3, category='Turret')
    ensure_var(tur, f'TrAge{i}', 'float', category='Turret')
ensure_var(tur, 'ShotDir', struct=V3, category='Turret')
ensure_var(tur, 'TDir', struct=V3, category='Turret')
ensure_var(tur, 'FireIdx', 'int', array=True, category='Turret')
ensure_var(tur, 'NoChar', obj_class=chc, category='Turret')
ensure_var(tur, 'FallbackShot', obj_class=unreal.SoundBase, category='Turret')
ensure_fn(tur, 'Seat', outputs=[('Loc', V3)], pure=True)
ensure_fn(tur, 'PromptLoc', outputs=[('Loc', V3)], pure=True)
ensure_fn(tur, 'BaseYaw', outputs=[('Yaw', 'float')], pure=True)
ensure_fn(tur, 'CamWorld', outputs=[('Loc', V3)], pure=True)
ensure_fn(tur, 'AimRot', outputs=[('Rot', RT)], pure=True)
ensure_fn(tur, 'MuzzleWorld', outputs=[('Loc', V3)], pure=True)
ensure_fn(tur, 'SNow', outputs=[('T', 'float')])
ensure_fn(tur, 'SetVisualAim', inputs=[('P', 'float'), ('Y', 'float')])
ensure_fn(tur, 'ApplyVisual')
ensure_fn(tur, 'Mount', inputs=[('Ch', chc)])
ensure_fn(tur, 'Dismount')
ensure_fn(tur, 'ServerTick', inputs=[('Dt', 'float')])
ensure_fn(tur, 'TriggerTick', inputs=[('Dt', 'float'), ('G', chc), ('Now', 'float')])
ensure_fn(tur, 'FireOne', inputs=[('G', chc)])
ensure_fn(tur, 'BurstOver', inputs=[('Now', 'float')])
ensure_fn(tur, 'Click')
ensure_fn(tur, 'GunnerAmmo', inputs=[('G', chc)], outputs=[('N', 'int')], pure=True)
ensure_fn(tur, 'UseAmmo', inputs=[('G', chc)])
ensure_fn(tur, 'CosmeticTick', inputs=[('Dt', 'float')])
ensure_fn(tur, 'CosmeticShot')
ensure_fn(tur, 'StartTracer', inputs=[('A', V3), ('B', V3)])
ensure_fn(tur, 'TracerTick', inputs=[('Dt', 'float')])
ensure_fn(tur, 'ShotSound', outputs=[('S', unreal.SoundBase)])
compile_bp(tur, quiet=True)
td = cdo(tur)
td.set_editor_property('BurstLeft', BURST)
td.set_editor_property('AimPitch', -8.0)
td.set_editor_property('VisPitch', -8.0)
td.set_editor_property('FallbackShot', unreal.load_asset('/Game/GW/Audio/S_GW_Gunshot'))
for i in range(TRACERS):
    td.set_editor_property(f'TrAge{i}', -1.0)

TV = lambda n: f'(Variables|Turret|Get{n})'
TS = lambda n, v: f'(Variables|Turret|Set{n} {v})'
PIVOT = f'(Math|Transform|TransformLocation :T (Transformation|GetActorTransform) :Location {mv((0, 0, PIVOT_Z))})'
FI = 'Math|Interpolation|FInterpTo'
ATT_FAR = '"/Game/GW/Audio/ATT_GW_Far.ATT_GW_Far"'
NAME = '(Utilities|GetDisplayName :Object G)'


def tracer_start(k):
    return f'''  (if (== slot {k})
    {TS(f'TrA{k}', 'A')}
    {TS(f'TrB{k}', 'B')}
    {TS(f'TrAge{k}', '0.0')})'''


def tracer_tick(k):
    comp = f'(Variables|Default|GetTracer{k})'
    return f'''  (if (>= {TV(f'TrAge{k}')} 0.0)
    {TS(f'TrAge{k}', f"(+ {TV(f'TrAge{k}')} Dt)")}
    (bind a{k} {TV(f'TrA{k}')})
    (bind len{k} (Math|Vector|Distance(Vector) a{k} {TV(f'TrB{k}')}))
    (bind head{k} (* {TV(f'TrAge{k}')} {TR_SPEED}))
    (if (>= (- head{k} {TR_LEN}) len{k})
      {TS(f'TrAge{k}', '-1.0')}
      (Rendering|SetVisibility :self {comp} :bNewVisibility false :bPropagateToChildren false)
      (else
        (bind dir{k} (Math|Vector|Normalize (- {TV(f'TrB{k}')} a{k})))
        (bind s0{k} (Math|Float|Max(Float) 0.0 (- head{k} {TR_LEN})))
        (bind s1{k} (Math|Float|Min(Float) head{k} len{k}))
        (Transformation|SetWorldLocationAndRotation :self {comp} :NewLocation (+ a{k} (* dir{k} (* (+ s0{k} s1{k}) 0.5))) :NewRotation (Math|Rotator|MakeRotfromZ :Z dir{k}) :bSweep false :bTeleport true)
        (Transformation|SetWorldScale3D :self {comp} :NewScale (Math|Vector|MakeVector {TR_W} {TR_W} (/ (Math|Float|Max(Float) (- s1{k} s0{k}) 1.0) 100.0)))
        (Rendering|SetVisibility :self {comp} :bNewVisibility true :bPropagateToChildren false))))'''


T = {
    'Seat': f'(fn Seat () (return (Math|Transform|TransformLocation :T (Transformation|GetActorTransform) :Location {mv((SEAT_X, 0, HH))})))',
    'PromptLoc': f'(fn PromptLoc () (return (Math|Transform|TransformLocation :T (Transformation|GetActorTransform) :Location {mv((-30, 0, PIVOT_Z + 30))})))',
    'BaseYaw': '(fn BaseYaw () (return (.yaw (Transformation|GetActorRotation))))',
    'CamWorld': '(fn CamWorld () (return (Transformation|GetWorldLocation :self (Variables|Default|GetCamPoint))))',
    'AimRot': f'(fn AimRot () (return (Math|Rotator|MakeRotator :Pitch {TV("AimPitch")} :Yaw (+ (CallFunction|BaseYaw) {TV("AimYaw")}) :Roll 0.0)))',
    'MuzzleWorld': f'(fn MuzzleWorld () (return (+ {PIVOT} (Math|Vector|RotateVector :A {mv(MUZ)} :B (CallFunction|AimRot)))))',
    'SNow': f'''
(fn SNow ()
  (bind gs (Game|GetGameState))
  (if ({ISVALID} :Object gs)
    (return (GameState|GetServerWorldTimeSeconds :self gs)))
  (return (Utilities|Time|GetGameTimeinSeconds)))
''',
    'ApplyVisual': f'''
(fn ApplyVisual ()
  (Transformation|SetRelativeRotation :self (Variables|Default|GetSwivel) :NewRotation (Math|Rotator|MakeRotator :Pitch 0.0 :Yaw {TV("VisYaw")} :Roll 0.0) :bSweep false :bTeleport true)
  (Transformation|SetRelativeRotation :self (Variables|Default|GetCradle) :NewRotation (Math|Rotator|MakeRotator :Pitch {TV("VisPitch")} :Yaw 0.0 :Roll 0.0) :bSweep false :bTeleport true))
''',
    'SetVisualAim': f'''
(fn SetVisualAim (P Y)
  {TS('VisPitch', 'P')}
  {TS('VisYaw', 'Y')}
  (CallFunction|ApplyVisual))
''',
    'Mount': f'''
(fn Mount (Ch)
  {TS('Gunner', 'Ch')}
  {TS('TriggerDown', 'false')}
  {TS('Firing', 'false')}
  {TS('Clicked', 'false')}
  {TS('AimYaw', '0.0')}
  {TS('AimPitch', '-8.0')}
  (Transformation|SetActorLocation :self Ch :NewLocation (CallFunction|Seat) :bSweep false :bTeleport true)
  (Transformation|SetActorRotation :self Ch :NewRotation (Math|Rotator|MakeRotator :Pitch 0.0 :Yaw (CallFunction|BaseYaw) :Roll 0.0) :bTeleportPhysics true)
  (GW|Call|BP_GW_Character|SetFrozen :self Ch :Frozen true)
  (GW|Set|BP_GW_Character|Aiming :self Ch :Aiming false)
  (Development|PrintString :InString (cat "GW: turret mounted by " (Utilities|GetDisplayName :Object Ch) " seeker=" (GW|Get|BP_GW_Character|IsSeeker :self Ch)) :bPrintToScreen false))
''',
    'Dismount': f'''
(fn Dismount ()
  (bind g {TV('Gunner')})
  (if ({ISVALID} :Object g)
    (if (not (GW|Get|BP_GW_Character|IsDead :self g))
      (GW|Call|BP_GW_Character|SetFrozen :self g :Frozen false))
    (Development|PrintString :InString (cat "GW: turret dismounted by " (Utilities|GetDisplayName :Object g) " shots=" {TV('ShotsFired')}) :bPrintToScreen false))
  {TS('Gunner', TV('NoChar'))}
  {TS('TriggerDown', 'false')}
  {TS('Firing', 'false')})
''',
    'ServerTick': f'''
(fn ServerTick (Dt)
  (bind now (CallFunction|SNow))
  (if (and (> {TV('CoolUntil')} 0.0) (>= now {TV('CoolUntil')}))
    {TS('CoolUntil', '0.0')}
    {TS('BurstLeft', BURST)}
    (Development|PrintString :InString "GW: turret recharged (detective)" :bPrintToScreen false))
  (if (not ({ISVALID} :Object {TV('Gunner')}))
    {TS('Firing', 'false')}
    (return))
  (bind g {TV('Gunner')})
  (if (or (or (GW|Get|BP_GW_Character|IsDead :self g) (not (Pawn|IsPlayerControlled :self g))) (> (Math|Vector|Distance2D(Vector) (Transformation|GetActorLocation :self g) (CallFunction|Seat)) 150.0))
    (CallFunction|Dismount)
    (return))
  ; the gunner's hand gun stays silent: s11 ServerFire refuses shots within FireCooldown of LastFireTime
  (GW|Set|BP_GW_Character|LastFireTime :self g :LastFireTime (Utilities|Time|GetGameTimeinSeconds))
  (if (not {TV('TriggerDown')})
    {TS('Firing', 'false')}
    (return))
  (bind s {GSC}
    (:then
      (if (!= (GW|Get|BP_GW_GameState|Phase :self s) 2)
        {TS('Firing', 'false')}
        (return))
      (CallFunction|TriggerTick :Dt Dt :G g :Now now))
    (:CastFailed)))
''',
    # detective: 3 s of fire then a 25 s recharge; guest: one round of TurretAmmo per shot
    'TriggerTick': f'''
(fn TriggerTick (Dt G Now)
  (if (GW|Get|BP_GW_Character|IsSeeker :self G)
    (if (> {TV('CoolUntil')} 0.0)
      {TS('Firing', 'false')}
      (if (not {TV('Clicked')})
        {TS('Clicked', 'true')}
        (CallFunction|Click)
        (Development|PrintString :InString (cat "GW: turret refused (detective cooldown, " (Math|Float|Round (- {TV('CoolUntil')} Now)) " s left)") :bPrintToScreen false))
      (return))
    (else
      (if (<= (CallFunction|GunnerAmmo :G G) 0)
        {TS('Firing', 'false')}
        (if (not {TV('Clicked')})
          {TS('Clicked', 'true')}
          (CallFunction|Click)
          (Development|PrintString :InString (cat "GW: turret empty (guest without ammo) " {NAME}) :bPrintToScreen false))
        (return))))
  {TS('Firing', 'true')}
  {TS('ShotAcc', f"(Math|Float|Min(Float) (+ {TV('ShotAcc')} Dt) {2 * INTERVAL})")}
  (if (>= {TV('ShotAcc')} {INTERVAL})
    {TS('ShotAcc', f"(- {TV('ShotAcc')} {INTERVAL})")}
    (CallFunction|FireOne :G G))
  (if (GW|Get|BP_GW_Character|IsSeeker :self G)
    {TS('BurstLeft', f"(- {TV('BurstLeft')} Dt)")}
    (if (<= {TV('BurstLeft')} 0.0)
      (CallFunction|BurstOver :Now Now))))
''',
    'BurstOver': f'''
(fn BurstOver (Now)
  {TS('BurstLeft', '0.0')}
  {TS('CoolUntil', f'(+ Now {COOL})')}
  {TS('Firing', 'false')}
  {TS('TriggerDown', 'false')}
  {TS('Clicked', 'true')}
  (CallFunction|Click)
  (Development|PrintString :InString (cat "GW: turret burst over, detective cooldown {COOL:.0f} s, shots=" {TV('ShotsFired')}) :bPrintToScreen false))
''',
    'Click': f'''
(fn Click ()
  (bind gm {GMC}
    (:then (GW|Call|BP_GW_GameMode|WorldSound :self gm :Cat {CAT_EMPTY} :Loc (CallFunction|MuzzleWorld)))
    (:CastFailed)))
''',
    'GunnerAmmo': '''
(fn GunnerAmmo (G)
  (bind ps (Utilities|Casting|CastToBP_GW_PlayerState (GW|Get|/Script/Engine.Pawn|PlayerState :self G))
    (:then (return (GW|Get|BP_GW_PlayerState|TurretAmmo :self ps)))
    (:CastFailed (return 0))))
''',
    'UseAmmo': '''
(fn UseAmmo (G)
  (bind ps (Utilities|Casting|CastToBP_GW_PlayerState (GW|Get|/Script/Engine.Pawn|PlayerState :self G))
    (:then (GW|Set|BP_GW_PlayerState|TurretAmmo :self ps :TurretAmmo (Math|Integer|Max(Integer) 0 (- (GW|Get|BP_GW_PlayerState|TurretAmmo :self ps) 1))))
    (:CastFailed)))
''',
    # one round: converge on what the sight's ray shows, spread, hit, panic
    'FireOne': f'''
(fn FireOne (G)
  (bind rot (CallFunction|AimRot))
  (bind pivot {PIVOT})
  (bind muzzle (+ pivot (Math|Vector|RotateVector :A {mv(MUZ)} :B rot)))
  (bind cam (+ pivot (Math|Vector|RotateVector :A {mv(CAMP)} :B rot)))
  (bind fwd (Math|Vector|GetForwardVector rot))
  (bind (h1 ok1) (Collision|LineTraceByProfile :Start (+ cam (* fwd 40.0)) :End (+ cam (* fwd {RANGE})) :ProfileName "BlockAll" :bTraceComplex false :bIgnoreSelf true))
  (bind (b1 i1 t1 d1 l1 imp1 n1 in1 p1 a1) (Collision|BreakHitResult h1))
  {TS('ShotDir', f"(Math|Random|RandomUnitVectorinEllipticalConeinDegrees :ConeDir (Math|Vector|Normalize (- (select ok1 imp1 (+ cam (* fwd {RANGE}))) muzzle)) :MaxYawInDegrees {SPREAD} :MaxPitchInDegrees {SPREAD})")}
  (bind dir {TV('ShotDir')})
  (bind (h2 ok2) (Collision|LineTraceByProfile :Start muzzle :End (+ muzzle (* dir {RANGE})) :ProfileName "BlockAll" :bTraceComplex false :bIgnoreSelf true))
  (bind (b2 i2 t2 d2 l2 imp2 n2 in2 p2 a2) (Collision|BreakHitResult h2))
  {TS('ShotsFired', f"(+ {TV('ShotsFired')} 1)")}
  (if (not (GW|Get|BP_GW_Character|IsSeeker :self G))
    (CallFunction|UseAmmo :G G))
  (bind gm {GMC}
    (:then
      ; every burst panics the manor, not more often than the panic itself
      (if (< (GW|Get|BP_GW_GameState|PanicUntil :self (GW|Call|BP_GW_GameMode|GetGS :self gm)) (+ (GW|Call|BP_GW_GameMode|Now :self gm) 4.0))
        {PANIC}
        (Development|PrintString :InString "GW: turret burst panics the manor" :bPrintToScreen false))
      (if ok2
        (bind v (Utilities|Casting|CastToBP_GW_Character a2)
          (:then (GW|Call|BP_GW_GameMode|TurretHit :self gm :Gunner G :Victim v :Dir dir))
          (:CastFailed))))
    (:CastFailed)))
''',
    # every machine: the gun follows the replicated aim (the gunner's own machine drives it directly), shots
    'CosmeticTick': f'''
(fn CosmeticTick (Dt)
  {TS('LocalGun', 'false')}
  (if ({ISVALID} :Object {TV('Gunner')})
    {TS('LocalGun', f"(Pawn|IsLocallyControlled :self {TV('Gunner')})")})
  (if (not {TV('LocalGun')})
    {TS('VisYaw', f"({FI} :Current {TV('VisYaw')} :Target {TV('AimYaw')} :DeltaTime Dt :InterpSpeed 12.0)")}
    {TS('VisPitch', f"({FI} :Current {TV('VisPitch')} :Target {TV('AimPitch')} :DeltaTime Dt :InterpSpeed 12.0)")}
    (CallFunction|ApplyVisual))
  (if {TV('Firing')}
    {TS('LocalAcc', f"(+ {TV('LocalAcc')} Dt)")}
    (if (>= {TV('LocalAcc')} {INTERVAL})
      {TS('LocalAcc', f"(Math|Float|Min(Float) (- {TV('LocalAcc')} {INTERVAL}) {INTERVAL})")}
      (CallFunction|CosmeticShot))
    (else
      {TS('LocalAcc', INTERVAL)}))
  {TS('FlashT', f"(- {TV('FlashT')} Dt)")}
  (if (<= {TV('FlashT')} 0.0)
    (Rendering|SetVisibility :self (Variables|Default|GetMuzzleFlash) :bNewVisibility false :bPropagateToChildren false)
    (Rendering|Components|Light|SetIntensity :self (Variables|Default|GetMuzzleLight) :NewIntensity 0.0))
  (CallFunction|TracerTick :Dt Dt))
''',
    'CosmeticShot': f'''
(fn CosmeticShot ()
  (bind mp (Variables|Default|GetMuzzlePoint))
  (bind m (Transformation|GetWorldLocation :self mp))
  (bind f (Transformation|GetForwardVector :self mp))
  (bind snd (CallFunction|ShotSound))
  (Audio|PlaySoundatLocation :Sound snd :Location m :VolumeMultiplier 1.0 :PitchMultiplier (Math|Random|RandomFloatinRange 0.95 1.05) :AttenuationSettings {ATT_FAR})
  {TS('FlashT', '0.045')}
  (Rendering|SetVisibility :self (Variables|Default|GetMuzzleFlash) :bNewVisibility true :bPropagateToChildren false)
  (Transformation|SetRelativeRotation :self (Variables|Default|GetMuzzleFlash) :NewRotation (Math|Rotator|MakeRotator :Pitch 0.0 :Yaw 0.0 :Roll (Math|Random|RandomFloatinRange 0.0 360.0)) :bSweep false :bTeleport true)
  (Rendering|Components|Light|SetIntensity :self (Variables|Default|GetMuzzleLight) :NewIntensity (Math|Random|RandomFloatinRange 30000.0 60000.0))
  {TS('ShotN', f"(+ {TV('ShotN')} 1)")}
  (if (== (% {TV('ShotN')} 2) 0)
    ; tracers converge like the real rounds, on what the sight looks at
    (bind cp (Transformation|GetWorldLocation :self (Variables|Default|GetCamPoint)))
    (bind (hc okc) (Collision|LineTraceByProfile :Start (+ cp (* f 40.0)) :End (+ cp (* f {RANGE})) :ProfileName "BlockAll" :bTraceComplex false :bIgnoreSelf true))
    (bind (bc ic tc dc lc impc nc inc pc ac) (Collision|BreakHitResult hc))
    {TS('TDir', f"(Math|Random|RandomUnitVectorinEllipticalConeinDegrees :ConeDir (Math|Vector|Normalize (- (select okc impc (+ cp (* f {RANGE}))) m)) :MaxYawInDegrees {SPREAD} :MaxPitchInDegrees {SPREAD})")}
    (bind (ht okt) (Collision|LineTraceByProfile :Start m :End (+ m (* {TV('TDir')} {RANGE})) :ProfileName "BlockAll" :bTraceComplex false :bIgnoreSelf true))
    (bind (bt it tt dt lt impt nt int pt at) (Collision|BreakHitResult ht))
    (CallFunction|StartTracer :A m :B (select okt impt (+ m (* {TV('TDir')} {RANGE}))))))
''',
    'StartTracer': ('(fn StartTracer (A B)\n' + f"  (bind slot (% {TV('TrN')} {TRACERS}))\n"
                    + '\n'.join(tracer_start(k) for k in range(TRACERS))
                    + '\n  ' + TS('TrN', '(+ ' + TV('TrN') + ' 1)') + ')\n'),
    'TracerTick': '(fn TracerTick (Dt)\n' + '\n'.join(tracer_tick(k) for k in range(TRACERS)) + ')\n',
    'ShotSound': f'''
(fn ShotSound ()
  (bind s {GSC}
    (:then
      (bind cats (GW|Get|BP_GW_GameState|BankCat :self s))
      (if (not {TV('FireIdxDone')})
        {TS('FireIdxDone', 'true')}
        (Utilities|Array|Clear (Variables|Turret|GetFireIdx))
        (for i (range (Utilities|Array|Length cats))
          (if (== (Utilities|Array|Get(acopy) cats i) {CAT_FIRE})
            (Utilities|Array|Add :TargetArray (Variables|Turret|GetFireIdx) :NewItem i))))
      (bind n (Utilities|Array|Length (Variables|Turret|GetFireIdx)))
      (if (> n 0)
        (return (Utilities|Array|Get(acopy) (GW|Get|BP_GW_GameState|BankSounds :self s) (Utilities|Array|Get(acopy) (Variables|Turret|GetFireIdx) (Math|Random|RandomIntegerinRange 0 (- n 1))))))
      (return {TV('FallbackShot')}))
    (:CastFailed (return {TV('FallbackShot')}))))
''',
    'EventGraph': '''
(event EventBeginPlay
  (CallFunction|ApplyVisual))

(event EventTick (DeltaSeconds)
  (if (Networking|HasAuthority)
    (CallFunction|ServerTick :Dt DeltaSeconds))
  (CallFunction|CosmeticTick :Dt DeltaSeconds))
''',
}
for n, code in T.items():
    wr(tur, n, code)
    compile_bp(tur, quiet=True)
compile_bp(tur)
print('BP_GW_Turret', node_problems(tur))
save(tur)

# ---------------------------------------------------------------- the gunner's HUD (own widget)
sys.path.insert(0, r'J:\Projets\Unreal_Projects\Guess Who\Tools\ui')
import uilib; importlib.reload(uilib)
W = uilib.get_or_create('WBP_GW_TurretHUD', FOLDER)
uilib.clear_tree(W)
uilib.add(W, unreal.CanvasPanel, 'Root')
cr = uilib.add(W, unreal.Image, 'Cross', 'Root', var=True)
uilib.image(cr, 'T_UI_Crosshair', (84, 84))
uilib.canvas(cr, ((0.5, 0.5), (0.5, 0.5)), (0.5, 0.5), (0, 0), (84, 84), z=4)
pn = uilib.add(W, unreal.VerticalBox, 'Panel', 'Root', var=True)
uilib.canvas(pn, ((0.5, 0.5), (0.5, 0.5)), (0.5, 0.0), (0, 66), auto=True, z=5)
mt = uilib.add(W, unreal.TextBlock, 'Main', 'Panel', var=True)
uilib.text(mt, 'MUNITIONS : 0', 'Display', 'Regular', 26, uilib.GOLD_HI, spacing=260, just='center')
uilib.box_slot(mt, (0, 0, 0, 4), uilib.H.H_ALIGN_CENTER)
bb = uilib.add(W, unreal.SizeBox, 'BarBox', 'Panel')
uilib.size_box(bb, w=260, h=4)
uilib.box_slot(bb, (0, 0, 0, 6), uilib.H.H_ALIGN_CENTER)
bo = uilib.add(W, unreal.Overlay, 'BarO', 'BarBox')
bk = uilib.add(W, unreal.Image, 'BarBack', 'BarO')
bk.widget.set_editor_property('brush', uilib.brush(None, (8, 8), 'image', tint=(uilib.GOLD[0], uilib.GOLD[1], uilib.GOLD[2], 0.3)))
uilib.overlay_slot(bk)
bf = uilib.add(W, unreal.Image, 'BarFill', 'BarO', var=True)
bf.widget.set_editor_property('brush', uilib.brush(None, (8, 8), 'image', tint=uilib.GOLD_HI))
uilib.overlay_slot(bf)
uilib.pivot(bf, 0.0, 0.5)
ht = uilib.add(W, unreal.TextBlock, 'Hint', 'Panel', var=True)
uilib.text(ht, 'Clic gauche : tirer   ·   E : descendre', 'Sans', 'Regular', 15, uilib.IVORY, just='center')
uilib.box_slot(ht, (0, 0, 0, 0), uilib.H.H_ALIGN_CENTER)
uilib.compile_widget(W)
ensure_fn(W, 'SetInfo', inputs=[('Main', 'string'), ('Hint', 'string'), ('Frac', 'float'), ('Warn', 'bool'), ('Cross', 'bool')])
compile_bp(W, quiet=True)
OV = lambda n: f'(Variables|WBP_GW_TurretHUD|Get{n})'
uilib.write(W, 'SetInfo', f'''
(fn SetInfo (Main Hint Frac Warn Cross)
  (Widget|SetText(Text) :self {OV('Main')} :InText (Utilities|Text|ToText(String) Main))
  (Widget|SetText(Text) :self {OV('Hint')} :InText (Utilities|Text|ToText(String) Hint))
  (Widget|Transform|SetRenderScale :self {OV('BarFill')} :Scale (Math|Vector2D|MakeVector2D (Math|Float|Clamp(Float) :Value Frac :Min 0.0 :Max 1.0) 1.0))
  (Widget|SetRenderOpacity :self {OV('Main')} :InOpacity (select Warn (+ 0.55 (* 0.45 (Math|Float|Absolute(Float) (Math|Trig|Sin(Radians) (* (Utilities|Time|GetRealTimeSeconds) 6.0))))) 1.0))
  (if Cross
    (Widget|SetVisibility :self {OV('Cross')} :InVisibility "HitTestInvisible")
    (else
      (Widget|SetVisibility :self {OV('Cross')} :InVisibility "Hidden"))))
''', compile_after=False)
compile_bp(W)
print('WBP_GW_TurretHUD', node_problems(W))
uilib.compile_widget(W)

if TURRET_ONLY:
    print('turret-only run: game mode / player controller untouched')
    raise SystemExit
gm_graphs = graph_names(gm)
# a guest who kills a detective earns 100 $ (shop agent's s34: ShopPay(PS, Amount, Note))
REWARD = 'ShopPay' if 'ShopPay' in gm_graphs else None
print('detective-kill reward hook:', REWARD)
REWARD_CALL = ('(bind kps (CallFunction|PSOf :P Gunner))\n      (if (' + ISVALID + ' :Object kps)\n'
               '        (CallFunction|ShopPay :PS kps :Amount 100 :Note "+100 $ : un détective de moins !"))' if REWARD else
               '(Development|PrintString :InString "GW: turret detective kill (ShopPay missing: run s34 then s35 again)" :bPrintToScreen false)')
G = {
    'TurretTick': f'''
(fn TurretTick ()
  (CallFunction|ViewServerTick)
  (if ({ISVALID} :Object (Variables|GW|GetTurret))
    (return))
  (bind found (Actor|GetAllActorsOfClass :ActorClass "{TUR}"))
  (if (> (Utilities|Array|Length found) 0)
    (Variables|GW|SetTurret (Utilities|Array|Get(acopy) found 0))
    (return))
  (if (not (Utilities|String|Contains :SearchIn (Game|GetCurrentLevelName) :Substring "L_Manor"))
    (return))
  (Variables|GW|SetTurret (Game|SpawnActorfromClass :Class "{TUR}" :SpawnTransform (Math|Transform|MakeTransform :Location {mv((TX, TY, TZ))} :Rotation (Math|Rotator|MakeRotator :Pitch 0.0 :Yaw {TYAW} :Roll 0.0)) :CollisionHandlingOverride "AlwaysSpawn"))
  (Development|PrintString :InString (cat "GW: turret spawned at " (Transformation|GetActorLocation :self (Variables|GW|GetTurret))) :bPrintToScreen false))
''',
    'IsOnTurret': f'''
(fn IsOnTurret (P)
  (bind t (Variables|GW|GetTurret))
  (if (or (not ({ISVALID} :Object t)) (not ({ISVALID} :Object P)))
    (return false))
  (return (== (GW|Get|/Game/GW/Blueprints/Turret/BP_GW_Turret.BP_GW_Turret_C|Gunner :self t) P)))
''',
    'TurretHit': f'''
(fn TurretHit (Gunner Victim Dir)
  (if (GW|Get|BP_GW_Character|IsDead :self Victim)
    (return))
  (if (GW|Get|BP_GW_Character|IsSeeker :self Gunner)
    (Development|PrintString :InString (cat "GW: turret (detective) hit " (Utilities|GetDisplayName :Object Victim)) :bPrintToScreen false)
    (CallFunction|OnCharacterShot :Shooter Gunner :Victim Victim :Dir Dir)
    (return))
  ; a guest at the gun
  (bind kind (GW|Get|BP_GW_Character|Kind :self Victim))
  (if (== kind 3)
    (return))
  (if (== kind 2)
    (CallFunction|Announce :Text "Le kamikaze a sauté sous la mitrailleuse !")
    (CallFunction|Explode :Loc (Transformation|GetActorLocation :self Victim) :Radius 650.0 :Cause "a été soufflé par le kamikaze")
    (return))
  (if (== kind 1)
    (CallFunction|DeathCry :Victim Victim)
    (GW|Call|BP_GW_Character|Die :self Victim :Impulse (* Dir 900.0))
    (CallFunction|Announce :Text "Un bandit est tombé sous la mitrailleuse !")
    (return))
  (if (Pawn|IsPlayerControlled :self Victim)
    ; guests never hurt guests; a detective falls (the gunner stays anonymous)
    (if (GW|Get|BP_GW_Character|IsSeeker :self Victim)
      (Development|PrintString :InString (cat "GW: turret killed detective " (CallFunction|NameOf :P Victim)) :bPrintToScreen false)
      (CallFunction|Announce :Text (cat (CallFunction|NameOf :P Victim) " a été abattu par la mitrailleuse !"))
      (CallFunction|DeathCry :Victim Victim)
      (CallFunction|KillPlayer :Victim Victim :Impulse (* Dir 900.0))
      {REWARD_CALL}
      (CallFunction|UpdateCounts))
    (return))
  (Development|PrintString :InString (cat "GW: turret kill NPC " (Utilities|GetDisplayName :Object Victim) " by " (Utilities|GetDisplayName :Object Gunner)) :bPrintToScreen false)
  (CallFunction|DeathCry :Victim Victim)
  (GW|Call|BP_GW_Character|Die :self Victim :Impulse (* Dir 900.0))
  (Utilities|Array|Add :TargetArray (Variables|GW|GetPendingNPCRespawns) :NewItem (+ (CallFunction|Now) (Variables|GW|GetNPCRespawnDelay)))
  (CallFunction|RewardNPCKill :Killer Gunner :Victim Victim))
''',
}
import shop_items
for n, code in G.items():
    if n in shop_items.S40_OWNS:      # body in s40_inventory.py (run it after this script)
        continue
    wr(gm, n, code)
compile_bp(gm)
print('BP_GW_GameMode', node_problems(gm))
save(gm)

# ---------------------------------------------------------------- player controller
lock('/Game/GW/Blueprints/BP_GW_PlayerController', True)
pc = load_bp('BP_GW_PlayerController')
kp = unreal.load_asset('/Game/GW/Blueprints/BP_GW_KeyPrompt').generated_class()
ensure_var(pc, 'TurretRef', obj_class=tur.generated_class(), category='GW')
ensure_var(pc, 'TurretPrompt', obj_class=kp, category='GW')
ensure_var(pc, 'TurretHUD', obj_class=W.generated_class(), category='GW')
ensure_var(pc, 'NoTurretHUD', obj_class=W.generated_class(), category='GW')
for v, t in (('WasMounted', 'bool'), ('TFrame', 'bool'), ('TLmb', 'bool'), ('TTestFire', 'bool'), ('TTestAim', 'bool'),
             ('TSearchAt', 'float'), ('TAimAt', 'float'), ('TLastP', 'float'), ('TLastY', 'float'), ('TTestT0', 'float'),
             ('TTestStep', 'int')):
    ensure_var(pc, v, t, category='GW')
ensure_var(pc, 'TRot', struct=RT, category='GW')
ensure_fn(pc, 'TryTurret', outputs=[('Handled', 'bool')])
ensure_fn(pc, 'TurretClientTick')
ensure_fn(pc, 'TurretFrame', inputs=[('Dt', 'float')], outputs=[('Mounted', 'bool'), ('CamLoc', V3)])
ensure_fn(pc, 'MyTurret', outputs=[('T', tur.generated_class())])
ensure_fn(pc, 'NearTurret', inputs=[('T', tur.generated_class()), ('P', unreal.Pawn)], outputs=[('Ok', 'bool')], pure=True)
ensure_fn(pc, 'TurretToServer', inputs=[('Cmd', 'string')])
ensure_fn(pc, 'TurretClientChar', inputs=[('T', tur.generated_class()), ('Ch', chc)])
ensure_fn(pc, 'TurretHudUpdate', inputs=[('T', tur.generated_class()), ('Ch', chc)])
ensure_fn(pc, 'TurretTestTick')
ensure_fn(pc, 'GWTurret', exec_fn=True)
ensure_fn(pc, 'GWTurretAim', inputs=[('Pitch', 'float'), ('Yaw', 'float')], exec_fn=True)
ensure_fn(pc, 'GWTurretTrigger', inputs=[('On', 'int')], exec_fn=True)
for f in ('GWDevTurretGo', 'GWDevTurretAmmo', 'GWDevTurretTarget'):
    ensure_fn(pc, f, exec_fn=True)
compile_bp(pc, quiet=True)
local(pc, 'GWDevTurretTarget', 'BestD', 'float')
local(pc, 'GWDevTurretTarget', 'BestT', obj=chc)


def gate(name):
    return f'''  (if (not (CallFunction|DevOK))
    (Development|PrintString :InString (cat "GW: dev {name} refused for " (PlayerState|GetPlayerName :self (GW|Get|/Script/Engine.Controller|PlayerState)) " (server not started with -GWDev)") :bPrintToScreen false)
    (return))'''


def step(n, at, body):
    return f'''  (if (and (== (Variables|GW|GetTTestStep) {n}) (> el {at}))
    (Variables|GW|SetTTestStep {n + 1})
{body}
    (CallFunction|TTLog :What "{n + 1}"))'''


ensure_fn(pc, 'TTLog', inputs=[('What', 'string')])
compile_bp(pc, quiet=True)
TPAWN = '(Pawn|GetControlledPawn :self self)'
AIM_AT_TARGET = '''    (Variables|GW|SetTTestAim true)'''
P = {
    'MyTurret': f'''
(fn MyTurret ()
  (if ({ISVALID} :Object (Variables|GW|GetTurretRef))
    (return (Variables|GW|GetTurretRef)))
  (if (< (Utilities|Time|GetRealTimeSeconds) (Variables|GW|GetTSearchAt))
    (return (Variables|GW|GetTurretRef)))
  (Variables|GW|SetTSearchAt (+ (Utilities|Time|GetRealTimeSeconds) 1.0))
  (bind all (Actor|GetAllActorsOfClass :ActorClass "{TUR}"))
  (if (> (Utilities|Array|Length all) 0)
    (Variables|GW|SetTurretRef (Utilities|Array|Get(acopy) all 0)))
  (return (Variables|GW|GetTurretRef)))
''',
    'NearTurret': f'''
(fn NearTurret (T P)
  (bind ch (Utilities|Casting|CastToBP_GW_Character P)
    (:then
      (if (GW|Get|BP_GW_Character|IsDead :self ch)
        (return false))
      (bind seat (GW|Call|/Game/GW/Blueprints/Turret/BP_GW_Turret.BP_GW_Turret_C|Seat :self T))
      (bind loc (Transformation|GetActorLocation :self ch))
      (bind dz (- (.z loc) (.z seat)))
      (return (and (< (Math|Vector|Distance2D(Vector) loc seat) {NEAR}) (< (* dz dz) {NEAR_Z * NEAR_Z}))))
    (:CastFailed (return false))))
''',
    'TurretToServer': '''
(fn TurretToServer (Cmd)
  (if (Networking|HasAuthority)
    (Development|ExecuteConsoleCommand :Command Cmd :SpecificPlayer self)
    (else
      (Development|ExecuteConsoleCommand :Command (cat "ServerExec " Cmd) :SpecificPlayer self))))
''',
    # E near the gun mounts it, E again dismounts (the server decides)
    'TryTurret': f'''
(fn TryTurret ()
  (bind t (CallFunction|MyTurret))
  (if (not ({ISVALID} :Object t))
    (return false))
  (bind p {TPAWN})
  (if (not ({ISVALID} :Object p))
    (return false))
  (if (== (GW|Get|/Game/GW/Blueprints/Turret/BP_GW_Turret.BP_GW_Turret_C|Gunner :self t) p)
    (CallFunction|TurretToServer :Cmd "GWTurret")
    (return true))
  (if (not (CallFunction|NearTurret :T t :P p))
    (return false))
  (CallFunction|TurretToServer :Cmd "GWTurret")
  (return true))
''',
    'GWTurret': f'''
(fn GWTurret ()
  (bind t (CallFunction|MyTurret))
  (if (not ({ISVALID} :Object t))
    (Development|PrintString :InString "GW: turret refused (no turret)" :bPrintToScreen false)
    (return))
  (bind ch {MYCH}
    (:then
      (if (== (GW|Get|/Game/GW/Blueprints/Turret/BP_GW_Turret.BP_GW_Turret_C|Gunner :self t) ch)
        (GW|Call|/Game/GW/Blueprints/Turret/BP_GW_Turret.BP_GW_Turret_C|Dismount :self t)
        (return))
      (if (not (CallFunction|NearTurret :T t :P ch))
        (Development|PrintString :InString (cat "GW: turret refused for " (Utilities|GetDisplayName :Object ch) " (too far or dead)") :bPrintToScreen false)
        (return))
      (if ({ISVALID} :Object (GW|Get|/Game/GW/Blueprints/Turret/BP_GW_Turret.BP_GW_Turret_C|Gunner :self t))
        (Development|PrintString :InString (cat "GW: turret refused for " (Utilities|GetDisplayName :Object ch) " (occupied)") :bPrintToScreen false)
        (return))
      (GW|Call|/Game/GW/Blueprints/Turret/BP_GW_Turret.BP_GW_Turret_C|Mount :self t :Ch ch))
    (:CastFailed
      (Development|PrintString :InString "GW: turret refused (not a character)" :bPrintToScreen false))))
''',
    'GWTurretAim': f'''
(fn GWTurretAim (Pitch Yaw)
  (bind t (CallFunction|MyTurret))
  (if (not ({ISVALID} :Object t))
    (return))
  (if (or (not ({ISVALID} :Object {TPAWN})) (!= (GW|Get|/Game/GW/Blueprints/Turret/BP_GW_Turret.BP_GW_Turret_C|Gunner :self t) {TPAWN}))
    (return))
  (GW|Set|/Game/GW/Blueprints/Turret/BP_GW_Turret.BP_GW_Turret_C|AimPitch :self t :AimPitch (Math|Float|Clamp(Float) :Value Pitch :Min {PMIN} :Max {PMAX}))
  (GW|Set|/Game/GW/Blueprints/Turret/BP_GW_Turret.BP_GW_Turret_C|AimYaw :self t :AimYaw (Math|Float|Clamp(Float) :Value Yaw :Min {-YAW_LIM} :Max {YAW_LIM})))
''',
    'GWTurretTrigger': f'''
(fn GWTurretTrigger (On)
  (bind t (CallFunction|MyTurret))
  (if (not ({ISVALID} :Object t))
    (return))
  (if (or (not ({ISVALID} :Object {TPAWN})) (!= (GW|Get|/Game/GW/Blueprints/Turret/BP_GW_Turret.BP_GW_Turret_C|Gunner :self t) {TPAWN}))
    (return))
  (bind down (!= On 0))
  (if (and down (not (GW|Get|/Game/GW/Blueprints/Turret/BP_GW_Turret.BP_GW_Turret_C|TriggerDown :self t)))
    ; the first round leaves at once
    (GW|Set|/Game/GW/Blueprints/Turret/BP_GW_Turret.BP_GW_Turret_C|ShotAcc :self t :ShotAcc {INTERVAL}))
  (if (not down)
    (GW|Set|/Game/GW/Blueprints/Turret/BP_GW_Turret.BP_GW_Turret_C|Clicked :self t :Clicked false))
  (GW|Set|/Game/GW/Blueprints/Turret/BP_GW_Turret.BP_GW_Turret_C|TriggerDown :self t :TriggerDown down)
  (Development|PrintString :InString (cat "GW: turret trigger " On " shots=" (GW|Get|/Game/GW/Blueprints/Turret/BP_GW_Turret.BP_GW_Turret_C|ShotsFired :self t) " burst=" (GW|Get|/Game/GW/Blueprints/Turret/BP_GW_Turret.BP_GW_Turret_C|BurstLeft :self t)) :bPrintToScreen false))
''',
    # every frame from the view driver (s37): hold the view in the gun's arc, turn the gun, send aim and trigger
    'TurretFrame': f'''
(fn TurretFrame (Dt)
  (bind t (CallFunction|MyTurret))
  (if (not ({ISVALID} :Object t))
    (return false (Math|Vector|MakeVector 0.0 0.0 0.0)))
  (bind p {TPAWN})
  (if (or (not ({ISVALID} :Object p)) (!= (GW|Get|/Game/GW/Blueprints/Turret/BP_GW_Turret.BP_GW_Turret_C|Gunner :self t) p))
    (Variables|GW|SetTFrame false)
    (Variables|GW|SetTLmb false)
    (return false (Math|Vector|MakeVector 0.0 0.0 0.0)))
  (bind base (GW|Call|/Game/GW/Blueprints/Turret/BP_GW_Turret.BP_GW_Turret_C|BaseYaw :self t))
  (if (not (Variables|GW|GetTFrame))
    (Variables|GW|SetTFrame true)
    (Pawn|SetControlRotation :self self :NewRotation (Math|Rotator|MakeRotator :Pitch -8.0 :Yaw base :Roll 0.0)))
  (Variables|GW|SetTRot (Pawn|GetControlRotation :self self))
  (bind rp (Math|Float|Clamp(Float) :Value (Math|Rotator|NormalizeAxis :Angle (.pitch (Variables|GW|GetTRot))) :Min {PMIN} :Max {PMAX}))
  (bind ry (Math|Float|Clamp(Float) :Value (Math|Rotator|NormalizeAxis :Angle (- (.yaw (Variables|GW|GetTRot)) base)) :Min {-YAW_LIM} :Max {YAW_LIM}))
  (Pawn|SetControlRotation :self self :NewRotation (Math|Rotator|MakeRotator :Pitch rp :Yaw (+ base ry) :Roll 0.0))
  (GW|Call|/Game/GW/Blueprints/Turret/BP_GW_Turret.BP_GW_Turret_C|SetVisualAim :self t :P rp :Y ry)
  (bind now (Utilities|Time|GetRealTimeSeconds))
  (if (and (> (- now (Variables|GW|GetTAimAt)) 0.08) (or (> (Math|Float|Absolute(Float) (- rp (Variables|GW|GetTLastP))) 0.15) (> (Math|Float|Absolute(Float) (- ry (Variables|GW|GetTLastY))) 0.15)))
    (Variables|GW|SetTAimAt now)
    (Variables|GW|SetTLastP rp)
    (Variables|GW|SetTLastY ry)
    (CallFunction|TurretToServer :Cmd (cat "GWTurretAim " rp " " ry)))
  (bind lmb (or (Game|Player|IsInputKeyDown :self self :Key "LeftMouseButton") (Variables|GW|GetTTestFire)))
  (if (!= lmb (Variables|GW|GetTLmb))
    (Variables|GW|SetTLmb lmb)
    ; the latest aim first, so the first rounds fly where the gunner looks
    (CallFunction|TurretToServer :Cmd (cat "GWTurretAim " rp " " ry))
    (CallFunction|TurretToServer :Cmd (select lmb "GWTurretTrigger 1" "GWTurretTrigger 0")))
  (return true (GW|Call|/Game/GW/Blueprints/Turret/BP_GW_Turret.BP_GW_Turret_C|CamWorld :self t)))
''',
    'TurretClientTick': f'''
(fn TurretClientTick ()
  (if (not (Pawn|IsLocalPlayerController))
    (return))
  (if (Utilities|HasLaunchOption :OptionToCheck "GWTurretTest")
    (CallFunction|TurretTestTick))
  (bind t (CallFunction|MyTurret))
  (if (not ({ISVALID} :Object t))
    (return))
  (bind ch {MYCH}
    (:then (CallFunction|TurretClientChar :T t :Ch ch))
    (:CastFailed
      (if ({ISVALID} :Object (Variables|GW|GetTurretPrompt))
        (GW|Call|BP_GW_KeyPrompt|ShowPrompt :self (Variables|GW|GetTurretPrompt) :On false))
      (if ({ISVALID} :Object (Variables|GW|GetTurretHUD))
        (Widget|RemovefromParent :self (Variables|GW|GetTurretHUD))
        (Variables|GW|SetTurretHUD (Variables|GW|GetNoTurretHUD)))
      (Variables|GW|SetWasMounted false))))
''',
    'TurretClientChar': f'''
(fn TurretClientChar (T Ch)
  (bind m (== (GW|Get|/Game/GW/Blueprints/Turret/BP_GW_Turret.BP_GW_Turret_C|Gunner :self T) Ch))
  (if (!= m (Variables|GW|GetWasMounted))
    (Variables|GW|SetWasMounted m)
    ; the same freeze / seat as the server, here at once (no correction snap)
    (GW|Call|BP_GW_Character|SetFrozen :self Ch :Frozen m)
    (if m
      (Transformation|SetActorLocation :self Ch :NewLocation (GW|Call|/Game/GW/Blueprints/Turret/BP_GW_Turret.BP_GW_Turret_C|Seat :self T) :bSweep false :bTeleport true))
    (Development|PrintString :InString (cat "GW: turret client mounted=" m) :bPrintToScreen false))
  (bind showP (and (and (not ({ISVALID} :Object (GW|Get|/Game/GW/Blueprints/Turret/BP_GW_Turret.BP_GW_Turret_C|Gunner :self T))) (not m)) (CallFunction|NearTurret :T T :P Ch)))
  (if (and showP (not ({ISVALID} :Object (Variables|GW|GetTurretPrompt))))
    (Variables|GW|SetTurretPrompt (Game|SpawnActorfromClass :Class "/Game/GW/Blueprints/BP_GW_KeyPrompt.BP_GW_KeyPrompt_C" :SpawnTransform (Math|Transform|MakeTransform :Location (GW|Call|/Game/GW/Blueprints/Turret/BP_GW_Turret.BP_GW_Turret_C|PromptLoc :self T)) :CollisionHandlingOverride "AlwaysSpawn"))
    (GW|Call|BP_GW_KeyPrompt|SetPrompt :self (Variables|GW|GetTurretPrompt) :Key "E" :Label "Prendre la mitrailleuse"))
  (if ({ISVALID} :Object (Variables|GW|GetTurretPrompt))
    (GW|Call|BP_GW_KeyPrompt|ShowPrompt :self (Variables|GW|GetTurretPrompt) :On showP))
  (if m
    (if (not ({ISVALID} :Object (Variables|GW|GetTurretHUD)))
      (Variables|GW|SetTurretHUD (UserInterface|CreateWidget :Class "{HUDW}" :OwningPlayer self))
      (UserInterface|Viewport|AddtoViewport :self (Variables|GW|GetTurretHUD) :ZOrder 5))
    (CallFunction|TurretHudUpdate :T T :Ch Ch)
    (else
      (if ({ISVALID} :Object (Variables|GW|GetTurretHUD))
        (Widget|RemovefromParent :self (Variables|GW|GetTurretHUD))
        (Variables|GW|SetTurretHUD (Variables|GW|GetNoTurretHUD))))))
''',
    'TurretHudUpdate': f'''
(fn TurretHudUpdate (T Ch)
  (bind s {GSC}
    (:then
      (bind now (GameState|GetServerWorldTimeSeconds :self s))
      (bind hunt (== (GW|Get|BP_GW_GameState|Phase :self s) 2))
      (bind hint (select hunt "Clic gauche : tirer   ·   E : descendre" "La mitrailleuse ne tire que pendant la chasse   ·   E : descendre"))
      (if (GW|Get|BP_GW_Character|IsSeeker :self Ch)
        (bind cool (GW|Get|/Game/GW/Blueprints/Turret/BP_GW_Turret.BP_GW_Turret_C|CoolUntil :self T))
        (bind left (Math|Float|Max(Float) 0.0 (- cool now)))
        (bind b (Math|Float|Max(Float) 0.0 (GW|Get|/Game/GW/Blueprints/Turret/BP_GW_Turret.BP_GW_Turret_C|BurstLeft :self T)))
        (bind main (select (> cool 0.0) (cat "RECHARGE : " (Math|Float|Truncate (+ left 0.99)) " s") (cat "RAFALE : " (Math|Float|Truncate b) "," (% (Math|Float|Truncate (* b 10.0)) 10) " s")))
        (GW|Call|{HUDW}|SetInfo :self (Variables|GW|GetTurretHUD) :Main main :Hint hint :Frac (select (> cool 0.0) (- 1.0 (/ left {COOL})) (/ b {BURST})) :Warn (> cool 0.0) :Cross false)
        (return))
      (bind ps (Utilities|Casting|CastToBP_GW_PlayerState (GW|Get|/Script/Engine.Controller|PlayerState))
        (:then
          (bind ammo (GW|Get|BP_GW_PlayerState|TurretAmmo :self ps))
          (GW|Call|{HUDW}|SetInfo :self (Variables|GW|GetTurretHUD) :Main (select (> ammo 0) (cat "MUNITIONS : " ammo) "PLUS DE MUNITIONS (au bar)") :Hint hint :Frac (/ ammo 60.0) :Warn (<= ammo 0) :Cross true))
        (:CastFailed)))
    (:CastFailed)))
''',
    'GWDevTurretGo': f'''
(fn GWDevTurretGo ()
{gate('turretgo')}
  (bind t (CallFunction|MyTurret))
  (bind p {TPAWN})
  (if (and ({ISVALID} :Object t) ({ISVALID} :Object p))
    (bind base (GW|Call|/Game/GW/Blueprints/Turret/BP_GW_Turret.BP_GW_Turret_C|BaseYaw :self t))
    (Transformation|SetActorLocation :self p :NewLocation (- (GW|Call|/Game/GW/Blueprints/Turret/BP_GW_Turret.BP_GW_Turret_C|Seat :self t) (* (Math|Vector|GetForwardVector (Math|Rotator|MakeRotator :Pitch 0.0 :Yaw base :Roll 0.0)) 70.0)) :bSweep false :bTeleport true)
    (Pawn|SetControlRotation :self self :NewRotation (Math|Rotator|MakeRotator :Pitch -10.0 :Yaw base :Roll 0.0))
    (Development|PrintString :InString "GW: dev went to the turret" :bPrintToScreen false)))
''',
    'GWDevTurretAmmo': f'''
(fn GWDevTurretAmmo ()
{gate('turretammo')}
  (bind ps (Utilities|Casting|CastToBP_GW_PlayerState (GW|Get|/Script/Engine.Controller|PlayerState))
    (:then
      (GW|Set|BP_GW_PlayerState|TurretAmmo :self ps :TurretAmmo (+ (GW|Get|BP_GW_PlayerState|TurretAmmo :self ps) 60))
      (Development|PrintString :InString (cat "GW: dev turret ammo " (GW|Get|BP_GW_PlayerState|TurretAmmo :self ps)) :bPrintToScreen false))
    (:CastFailed)))
''',
    # test helper: the guest NPC nearest a spot in the hall in front of the gun goes there and stays still
    'GWDevTurretTarget': f'''
(fn GWDevTurretTarget ()
{gate('turrettarget')}
  (bind spot (Math|Vector|MakeVector 3400.0 1000.0 100.0))
  (Variables|Default|SetBestD 100000000.0)
  (for a (Actor|GetAllActorsOfClass :ActorClass {CHAR})
    (if (and (and (not (Pawn|IsPlayerControlled :self a)) (not (GW|Get|BP_GW_Character|IsDead :self a))) (== (GW|Get|BP_GW_Character|Kind :self a) 0))
      (bind d (Math|Vector|Distance(Vector) (Transformation|GetActorLocation :self a) spot))
      (if (< d (Variables|Default|GetBestD))
        (Variables|Default|SetBestD d)
        (Variables|Default|SetBestT a))))
  (bind tg (Variables|Default|GetBestT))
  (if ({ISVALID} :Object tg)
    (Transformation|SetActorLocation :self tg :NewLocation spot :bSweep false :bTeleport true)
    (GW|Call|BP_GW_Character|SetFrozen :self tg :Frozen true)
    (Development|PrintString :InString (cat "GW: dev turret target " (Utilities|GetDisplayName :Object tg) " at " spot) :bPrintToScreen false)))
''',
    'TTLog': f'''
(fn TTLog (What)
  (bind t (CallFunction|MyTurret))
  (bind ps (Utilities|Casting|CastToBP_GW_PlayerState (GW|Get|/Script/Engine.Controller|PlayerState))
    (:then
      (if ({ISVALID} :Object t)
        (Development|PrintString :InString (cat "GW turrettest step " What " mounted=" (== (GW|Get|/Game/GW/Blueprints/Turret/BP_GW_Turret.BP_GW_Turret_C|Gunner :self t) {TPAWN}) " firing=" (GW|Get|/Game/GW/Blueprints/Turret/BP_GW_Turret.BP_GW_Turret_C|Firing :self t) " shots=" (GW|Get|/Game/GW/Blueprints/Turret/BP_GW_Turret.BP_GW_Turret_C|ShotsFired :self t) " ammo=" (GW|Get|BP_GW_PlayerState|TurretAmmo :self ps) " burst=" (GW|Get|/Game/GW/Blueprints/Turret/BP_GW_Turret.BP_GW_Turret_C|BurstLeft :self t) " cool=" (GW|Get|/Game/GW/Blueprints/Turret/BP_GW_Turret.BP_GW_Turret_C|CoolUntil :self t) " aim=" (GW|Get|/Game/GW/Blueprints/Turret/BP_GW_Turret.BP_GW_Turret_C|AimPitch :self t) "/" (GW|Get|/Game/GW/Blueprints/Turret/BP_GW_Turret.BP_GW_Turret_C|AimYaw :self t) " role=" (GW|Get|BP_GW_PlayerState|GWRole :self ps) " pawn=" (Utilities|GetDisplayName :Object {TPAWN})) :bPrintToScreen false)
        (else
          (Development|PrintString :InString (cat "GW turrettest step " What " (no turret yet)") :bPrintToScreen false))))
    (:CastFailed)))
''',
    'TurretTestTick': f'''
(fn TurretTestTick ()
  (bind now (Utilities|Time|GetRealTimeSeconds))
  (if (<= (Variables|GW|GetTTestT0) 0.0)
    (Variables|GW|SetTTestT0 now))
  (bind el (- now (Variables|GW|GetTTestT0)))
  ; keep the gun on the test target
  (if (Variables|GW|GetTTestAim)
    (bind t0 (CallFunction|MyTurret))
    (if ({ISVALID} :Object t0)
      (CallFunction|TurretTestAim :T t0)))
{step(0, 6, '    (CallFunction|DevServer :Cmd "GWDevQuickTest 1")')}
{step(1, 9, '    (CallFunction|DevServer :Cmd "GWDevTurretAmmo")')}
{step(2, 10, '    (CallFunction|DevServer :Cmd "GWDevTurretGo")')}
{step(3, 11, '    (bind h3 (CallFunction|TryTurret))' + chr(10) + '    (Development|PrintString :InString (cat "GW turrettest TryTurret handled=" h3) :bPrintToScreen false)')}
{step(4, 12.5, '    (CallFunction|DevServer :Cmd "GWDevTurretTarget")')}
{step(5, 13.5, AIM_AT_TARGET)}
{step(6, 15.0, '    (Variables|GW|SetTTestFire true)')}
{step(7, 17.0, '    (Variables|GW|SetTTestFire false)')}
{step(8, 18.0, '    (Variables|GW|SetTTestAim false)')}
{step(9, 18.5, '    (bind h9 (CallFunction|TryTurret))' + chr(10) + '    (Development|PrintString :InString (cat "GW turrettest dismount handled=" h9) :bPrintToScreen false)')}
{step(10, 20.0, '    (CallFunction|DevServer :Cmd "GWDevRole 2")')}
{step(11, 23.0, '    (CallFunction|DevServer :Cmd "GWDevTurretGo")')}
{step(12, 24.0, '    (bind h12 (CallFunction|TryTurret))' + chr(10) + '    (Development|PrintString :InString (cat "GW turrettest detective TryTurret handled=" h12) :bPrintToScreen false)')}
{step(13, 25.0, '    (CallFunction|DevServer :Cmd "GWDevTurretTarget")')}
{step(14, 26.0, AIM_AT_TARGET)}
{step(15, 27.0, '    (Variables|GW|SetTTestFire true)')}
{step(16, 31.5, '    (Variables|GW|SetTTestFire false)')}
{step(17, 32.5, '    (Variables|GW|SetTTestFire true)')}
{step(18, 33.5, '    (Variables|GW|SetTTestFire false)' + chr(10) + '    (Variables|GW|SetTTestAim false)')}
{step(19, 34.5, '    (bind h19 (CallFunction|TryTurret))' + chr(10) + '    (Development|PrintString :InString (cat "GW turrettest detective dismount handled=" h19) :bPrintToScreen false)')}
{step(20, 36.0, '    (CallFunction|DevServer :Cmd "GWAim 1")')}
{step(21, 37.0, '    (CallFunction|DevServer :Cmd "GWAim 0")')}
{step(22, 38.0, '    (CallFunction|SetViewMode :FP false)')}
{step(23, 41.0, '    (CallFunction|SetViewMode :FP true)')}
{step(24, 44.0, '    (Development|PrintString :InString "GW turrettest done" :bPrintToScreen false)')})
''',
}
ensure_fn(pc, 'TurretTestAim', inputs=[('T', tur.generated_class())])
compile_bp(pc, quiet=True)
local(pc, 'TurretTestAim', 'BestD', 'float')
local(pc, 'TurretTestAim', 'BestT', obj=chc)
P['TurretTestAim'] = f'''
(fn TurretTestAim (T)
  (bind spot (Math|Vector|MakeVector 3400.0 1000.0 100.0))
  (Variables|Default|SetBestD 400.0)
  (for a (Actor|GetAllActorsOfClass :ActorClass {CHAR})
    (if (and (not (Pawn|IsPlayerControlled :self a)) (not (GW|Get|BP_GW_Character|IsDead :self a)))
      (bind d (Math|Vector|Distance(Vector) (Transformation|GetActorLocation :self a) spot))
      (if (< d (Variables|Default|GetBestD))
        (Variables|Default|SetBestD d)
        (Variables|Default|SetBestT a))))
  (bind tg (Variables|Default|GetBestT))
  (if ({ISVALID} :Object tg)
    (Pawn|SetControlRotation :self self :NewRotation (Math|Rotator|FindLookatRotation :Start (GW|Call|/Game/GW/Blueprints/Turret/BP_GW_Turret.BP_GW_Turret_C|CamWorld :self T) :Target (+ (Transformation|GetActorLocation :self tg) (Math|Vector|MakeVector 0.0 0.0 20.0))))))
'''
for n, code in P.items():
    wr(pc, n, code)
compile_bp(pc)
print('BP_GW_PlayerController', node_problems(pc))
save(pc)
lock('/Game/GW/Blueprints/BP_GW_PlayerController', False)
print('DSL ERRORS:', len(ERRORS))
for e_ in ERRORS:
    print('  ', e_)
