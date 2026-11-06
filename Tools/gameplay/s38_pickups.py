"""Pickups & special weapons: billiard balls, the armours' swords, the body-swap gun (guests only).

Billiard balls (BP_GW_Pickup Kind 0, 6 on the billiard table): E near a ball (TryPickup, from InteractOther) takes it,
2 at most (BP_GW_PlayerState.Balls). Left click (GuestAttack, called by s34_shop.py when the guest has no gun ammo)
throws one: BP_GW_ThrownBall flies the same arc on every machine (StartLoc / Vel / Go), the server sweeps it and on
impact: clack (cat ball_clack); an NPC hit dies (HurtCharacter = DeathCry + Die + respawn, StartPanic, RewardNPCKill),
a detective loses 25 HP (HurtCharacter); other guest players are never hurt. A taken ball is back 45 s later.
Swords (BP_GW_Pickup Kind 1, leaning on each armor_suit in the hall): E steals it (HasSword, one at a time). The
server gives the holder a BP_GW_HeldSword (replicated, attached to the right hand on every machine: everybody sees
it). Left click with the sword: a slash (SlashCount -> a procedural chop of the blade + the MM_Attack montage when
the anim blueprint has a slot) in a 2 m cone in front: NPC dies / detective -25 HP. With both balls and a sword, the
sword is used when someone is in reach, else a ball is thrown. A stolen sword is back on its armour 60 s later.
Body-swap gun (s34 sells it: HasSwapGun / SwapReadyAt): R (IA_Swap -> RequestSwap) aims at the NPC guest in the
crosshair (camera trace, 25 m; never players, detectives or special characters). Server (GWSwap -> GM SwapStart):
the target loses its AI, the old body dies like any guest (DeathCry, ragdoll, short panic, an NPC respawn queued),
a blue see-through ghost (BP_GW_SwapGhost, the old body's GenGhostMats look) flies from the old body to the target
in 1 s for everyone (cat swap_whoosh), the swapper's camera follows the ghost (local view target), then SwapFinish
possesses the target (same PlayerState: role, alive, score unchanged; UpdateCounts). The gun recharges 90 s
(SwapReadyAt); notices on the HUD (LocalNotice) when it is used / ready again.
Every action is checked on the server (Exec functions: GWPickup, GWGuestAttack <pitch> <yaw>, GWSwap <pitch> <yaw>;
a client sends "ServerExec ..."). Inventories are emptied when a round starts and when the player dies.
Interactables (same BP_GW_Pickup, same E key): Kind 2 the post-it with this round's safe code (a yellow square on
the floor, a new random spot every round, never in the cloakroom or on the stage; E reads it: PC.KnownCode /
KnownRound replicate to the owning client only), Kind 3 the study safe (a door + dial over the fallback safe's
front: E with this round's code opens it once per round: 500 $ through the shop's ShopPay, the door swings open,
gold inside, cat safe_open), Kind 4 the fire-alarm pull stations (red boxes on walls in the corridors, the hall
and the dining room, spots found by wall traces when this script runs: once per game for the whole manor, any
living player: every client rings GameState.FireAlarm in 2D for 10 s, StartPanic 10 s), Kind 5 the toilets
(invisible, one per GW_Toilet marker: anyone farts, cat fart, far attenuation, 5 s cooldown per player).
Hooks (coordinator): GM.ReactionsTick -> PickupTick, PC.EventClientTick -> PickupClientTick,
PC.InteractOther -> TryPickup. Dev (u15 page Joueur): GWDevGiveBall, GWDevGiveSword, GWDevGiveSwap; tests:
GWDevAimAt <mode> <dist>, GWDevPickupSpawn, -GWPickupTest (PickupTestTick on host and client).
Usage: ue_run.py s38_pickups.py   (after s31 / s32 / s33; sounds: Tools/audio/synth_pickups.py + s31 import)
"""
import sys, importlib, math
sys.path.insert(0, r'J:\Projets\Unreal_Projects\Guess Who\Tools\gameplay')
import gw_lib; importlib.reload(gw_lib)
from gw_lib import *

REP = unreal.BlueprintVariableReplication
NOTIFY, REPL = REP.REP_NOTIFY, REP.REPLICATED
V3 = unreal.Vector.static_struct()
TRS = unreal.Transform.static_struct()
FOLDER = '/Game/GW/Blueprints/Pickups'
PK = f'{FOLDER}/BP_GW_Pickup.BP_GW_Pickup_C'
HS = f'{FOLDER}/BP_GW_HeldSword.BP_GW_HeldSword_C'
TB = f'{FOLDER}/BP_GW_ThrownBall.BP_GW_ThrownBall_C'
SG = f'{FOLDER}/BP_GW_SwapGhost.BP_GW_SwapGhost_C'
HUD = '/Game/GW/UI/WBP_HUD.WBP_HUD_C'
CHAR = '"/Game/GW/Blueprints/BP_GW_Character.BP_GW_Character_C"'
ISVALID = 'GW|Call|/Script/Engine.KismetSystemLibrary|IsValid'
VMUL = 'GW|Call|/Script/Engine.KismetMathLibrary|Multiply_VectorFloat'     # vector * float (the * operator wires lists badly)
GSC = '(Utilities|Casting|CastToBP_GW_GameState (Game|GetGameState))'
GMC = '(Utilities|Casting|CastToBP_GW_GameMode (Game|GetGameMode))'
MYCH = '(Utilities|Casting|CastToBP_GW_Character (Pawn|GetControlledPawn :self self))'
PSC = '(Utilities|Casting|CastToBP_GW_PlayerState (GW|Get|/Script/Engine.Controller|PlayerState))'
SNOW = '(GameState|GetServerWorldTimeSeconds :self (Game|GetGameState))'
CAT = {'ball_clack': 41, 'sword_swish': 42, 'sword_hit': 43, 'swap_whoosh': 44, 'fart': 48, 'safe_open': 49}     # s31_reactions.py CAT
# NPC reaction lines (voice director, s39: one line per character, P5, silent until the lines exist)
REACT = {'safe': 66, 'alarm': 67, 'ghost': 69, 'sword': 70, 'ball': 71}
# the guest nearest to where it happens says it (a fresh Stamp so NearestNPC may pick anyone)
NEAR_SAY = lambda loc, cat, delay, maxd=1200.0: (f'(Variables|GW|SetStamp (+ (Variables|GW|GetStamp) 1))\n'
                                                f'  (CallFunction|QueueSay :Ch (CallFunction|NearestNPC :Loc {loc} :MaxD {maxd}) :Cat {cat} :Delay {delay})')
BALL_BACK, SWORD_BACK, SWAP_RELOAD = 45.0, 60.0, 90.0
REACH, BALL_SPEED, BALL_G = 170.0, 2400.0, 300.0
SLASH_RANGE, SLASH_COS = 210.0, 0.5                     # 2 m (+ capsule), 60 degrees each side
SWAP_RANGE, SWAP_FLY = 2500.0, 1.0
EAL = unreal.EditorAssetLibrary
AT = unreal.AssetToolsHelpers.get_asset_tools()
MAT = '/Game/GW/Materials'

# ---------------------------------------------------------------- where: billiard table and armours (Tools/level/dress.py)
# billiard_table footprint x 4855..5145, y 820..980 (dress_state.json); felt measured in L_Manor (probe_s38.py)
FELT_Z = float(UE_ARGS[0]) if UE_ARGS and UE_ARGS[0].replace('.', '', 1).isdigit() else 80.67
SKIP_GM = 'nogm' in UE_ARGS          # ue_run.py s38_pickups.py nogm: pickup actors + player controller only
BALL_R = 2.85
BALLS = [(4945, 882), (4963, 913), (4931, 931), (5046, 876), (5071, 906), (5027, 933)]
# armor_suit (2620, 2381) and (3380, 2381), back on the hall's north wall, facing -Y; plinth front at y = 2325.
# The sword stands point-down in front of the plinth, its hilt leaning back against the armour's thighs.
# 2026-11-04 (user: the knights really hold the sword): the grip sits in the armour's right gauntlet (x + 28, height ~92),
# the point rests on the floor in front of it
SWORD_TIP_Y, SWORD_LEAN, SWORD_HAND_X = 2297.0, 29.0, 28.0
ARMOURS = [2620.0, 3380.0]
SWORD_LEN_DOWN = 103.0                                  # grip centre -> tip (half grip + guard + blade + point)


ALARM_Z = 135.0
ALARM_CANDIDATES = {     # room: (x, y, dir x, dir y) rays from inside the room towards a wall
    'corridor_w': [(600, 2100, 0, -1), (900, 2100, 0, 1), (1300, 2100, 0, -1), (1500, 2100, 0, 1), (400, 2100, 0, 1)],
    'corridor_e': [(5400, 2100, 0, -1), (5100, 2100, 0, 1), (4700, 2100, 0, -1), (4500, 2100, 0, 1), (5600, 2100, 0, 1)],
    'hall': [(2450, 700, 0, -1), (3550, 700, 0, -1), (2450, 300, -1, 0), (3550, 300, 1, 0), (2400, 2200, 0, 1)],
    'dining': [(1000, 900, 0, -1), (700, 900, 0, -1), (1000, 900, -1, 0), (300, 1300, 0, 1), (1400, 900, 0, -1)],
}


def wall_spot(room):
    """First candidate whose 5 rays (centre, +-12 cm sideways, +-15 cm up/down) hit one flat wall: a free patch of wall
    big enough for the box (no door, painting edge or furniture in the way)."""
    w = unreal.EditorLevelLibrary.get_editor_world()
    for (x, y, dx, dy) in ALARM_CANDIDATES[room]:
        ds = []
        for (o, oz) in ((0, 0), (12, 0), (-12, 0), (0, 15), (0, -15)):
            sx, sy = x - dy * o, y + dx * o
            h = unreal.SystemLibrary.line_trace_single(w, unreal.Vector(sx, sy, ALARM_Z + oz), unreal.Vector(sx + dx * 900, sy + dy * 900, ALARM_Z + oz),
                                                     unreal.TraceTypeQuery.TRACE_TYPE_QUERY1, True, [], unreal.DrawDebugTrace.NONE, True)
            if not h:
                break
            t = h.to_tuple()
            n = t[7]
            if n.x * -dx + n.y * -dy < 0.97:
                break
            ds.append(t[3])
        if len(ds) == 5 and max(ds) - min(ds) < 2.0:
            d = ds[0] - 0.3
            return (x + dx * d, y + dy * d, ALARM_Z), math.degrees(math.atan2(-dy, -dx))
    print('!! no free wall for the alarm box in', room)
    return None


SAFE_FRONT, SAFE_YAW = (5900.25, 2499.75, 0.0), 135.0    # study safe (level prop 70 x 65 x 95): its door face, facing NW
CLOAK = (2580, 3420, -100, 560)                          # never put the post-it in the cloakroom or on the stage
STAGE = (2500, 3500, 3820, 4380)
SAFE_MONEY = 500


def sword_spot(x):
    lean = math.radians(SWORD_LEAN)
    grip = unreal.Vector(x + SWORD_HAND_X, SWORD_TIP_Y + SWORD_LEN_DOWN * math.sin(lean), 2.0 + SWORD_LEN_DOWN * math.cos(lean))
    blade = unreal.Vector(0.0, -math.sin(lean), -math.cos(lean))          # local +Z (towards the tip)
    rot = unreal.MathLibrary.make_rot_from_zx(blade, unreal.Vector(1, 0, 0))
    return grip, rot


# ---------------------------------------------------------------- assets
def mat(name, fallback='/Engine/BasicShapes/BasicShapeMaterial'):
    p = f'{MAT}/{name}'
    return unreal.load_asset(p) if EAL.does_asset_exist(p) else unreal.load_asset(fallback)


STEEL, BRASS, GRIP = mat('MI_GW_Chrome'), mat('MI_GW_Brass'), mat('MI_GW_Leather_Oxblood')
IRON, GOLD, BLACK = mat('MI_GW_Iron'), mat('MI_GW_Gold', f'{MAT}/MI_GW_GoldLeaf'), mat('MI_GW_Lacquer_Black')
WHITE = mat('MI_GW_Porcelain')


def emissive_mi(name, color, strength):
    path = f'{FOLDER}/{name}'
    m = unreal.load_asset(path) if EAL.does_asset_exist(path) else AT.create_asset(name, FOLDER, unreal.MaterialInstanceConstant, unreal.MaterialInstanceConstantFactoryNew())
    MEL = unreal.MaterialEditingLibrary
    MEL.set_material_instance_parent(m, unreal.load_asset('/Game/GW/Materials/Master/M_GW_Emissive'))
    MEL.set_material_instance_vector_parameter_value(m, 'Color', unreal.LinearColor(*color))
    MEL.set_material_instance_scalar_parameter_value(m, 'Strength', strength)
    MEL.update_material_instance(m)
    EAL.save_loaded_asset(m)
    return m


POSTIT = emissive_mi('MI_GW_PostIt', (1.0, 0.82, 0.08, 1), 0.9)
RED = emissive_mi('MI_GW_AlarmRed', (0.9, 0.03, 0.02, 1), 0.35)
BALL_MATS = [mat(n) for n in ('MI_GW_Velvet_Gold', 'MI_GW_Book_Navy', 'MI_GW_Velvet_Red', 'MI_GW_Book_Black',
                              'MI_GW_Porcelain', 'MI_GW_Velvet_Green')]


def actor_bp(name, replicates=True, life=0.0):
    bp = load_or_create_bp(name, unreal.Actor, FOLDER)
    compile_bp(bp, quiet=True)
    d = cdo(bp)
    d.set_editor_property('replicates', replicates)
    d.set_editor_property('always_relevant', True)
    if life:
        d.set_editor_property('initial_life_span', life)
    return bp


def part(bp, name, shape, material, parent='DefaultSceneRoot', loc=(0, 0, 0), rot=(0, 0, 0), scale=(1, 1, 1)):
    c = ensure_component(bp, name, unreal.StaticMeshComponent, parent)
    c.set_editor_property('static_mesh', unreal.load_asset(f'/Engine/BasicShapes/{shape}'))
    c.set_editor_property('override_materials', [material])
    c.set_editor_property('relative_location', unreal.Vector(*loc))
    c.set_editor_property('relative_rotation', unreal.Rotator(roll=rot[0], pitch=rot[1], yaw=rot[2]))
    c.set_editor_property('relative_scale3d', unreal.Vector(*scale))
    c.set_editor_property('cast_shadow', True)
    c.set_collision_enabled(unreal.CollisionEnabled.NO_COLLISION)
    c.set_editor_property('generate_overlap_events', False)
    return c


def sword_parts(bp):
    """A placeholder longsword from basic shapes on a SwordRoot: grip centre at the origin, blade along +Z."""
    root = ensure_component(bp, 'SwordRoot', unreal.SceneComponent, 'DefaultSceneRoot')
    part(bp, 'Grip', 'Cylinder', GRIP, 'SwordRoot', scale=(0.03, 0.03, 0.18))
    part(bp, 'Pommel', 'Sphere', BRASS, 'SwordRoot', loc=(0, 0, -10.5), scale=(0.05, 0.05, 0.05))
    part(bp, 'Guard', 'Cube', BRASS, 'SwordRoot', loc=(0, 0, 10.5), scale=(0.22, 0.035, 0.03))
    part(bp, 'Blade', 'Cube', STEEL, 'SwordRoot', loc=(0, 0, 55.0), scale=(0.045, 0.008, 0.86))
    part(bp, 'Tip', 'Cone', STEEL, 'SwordRoot', loc=(0, 0, 102.0), scale=(0.045, 0.008, 0.08))
    return root


SWORD_CARRY_TILT = 50.0


def hand_rel():
    """BP_GW_HeldSword's transform relative to the hand_r bone: grip in the fist, blade out of the thumb side, edge
    along the knuckles (same bone frame as the revolver fit, s25_costume_import.py)."""
    mod = unreal.SkeletonModifier()
    mod.set_skeletal_mesh(unreal.load_asset('/Game/Characters/Mannequins/Meshes/SKM_Manny_Simple'))
    B = lambda n: mod.get_bone_transform(n, True)
    hand, mid = B('hand_r').translation, B('middle_01_r').translation
    idx, pinky = B('index_01_r').translation, B('pinky_01_r').translation
    fwd = (mid - hand).normal()
    up = idx - pinky
    up = (up - fwd * up.dot(fwd)).normal()
    grip = hand + (mid - hand) * 0.45
    # carried low: the blade leaves the fist on the thumb side, tilted 50 deg towards the fingers (down and forward
    # when the arm hangs; rendered QA: straight out of the thumb it stuck out sideways at hip height)
    th = math.radians(SWORD_CARRY_TILT)
    blade = (up * math.cos(th) + fwd * math.sin(th)).normal()
    xax = (fwd * math.cos(th) - up * math.sin(th)).normal()
    rot = unreal.MathLibrary.make_rotation_from_axes(xax, blade.cross(xax), blade)
    comp = unreal.Transform(grip, rot, unreal.Vector(1, 1, 1))
    return unreal.MathLibrary.make_relative_transform(comp, B('hand_r'))


AF = '/Game/GW/Blueprints/Pickups/AM_GW_Slash'
if not EAL.does_asset_exist(AF):
    try:
        f = unreal.AnimMontageFactory()
        src = unreal.load_asset('/Game/Characters/Mannequins/Anims/Unarmed/Attack/MM_Attack_02')
        f.set_editor_property('source_animation', src)
        f.set_editor_property('target_skeleton', src.get_editor_property('skeleton'))
        AT.create_asset('AM_GW_Slash', FOLDER, unreal.AnimMontage, f)
    except Exception as e:
        print('montage not created:', e)
SLASH_MONTAGE = unreal.load_asset(AF) if EAL.does_asset_exist(AF) else None
if SLASH_MONTAGE:
    EAL.save_loaded_asset(SLASH_MONTAGE, False)

chc = load_bp('BP_GW_Character').generated_class()

# ---------------------------------------------------------------- BP_GW_Pickup: a ball on the table or a sword on an armour
pk = actor_bp('BP_GW_Pickup')
ball = part(pk, 'Ball', 'Sphere', BALL_MATS[0], scale=(0.057, 0.057, 0.057))
sword_parts(pk)
part(pk, 'PostIt', 'Plane', POSTIT, loc=(0, 0, 0.3), scale=(0.1, 0.1, 1))
ensure_component(pk, 'SafeRoot', unreal.SceneComponent, 'DefaultSceneRoot')
# the prop's own (painted) door reads as closed: this door only appears when the safe opens, then swings out, and a
# dark opening with gold bars covers the painted door (rendered QA with the level's generated safe, 70 x 65 x 95)
SAFE_GREEN = mat('MI_GW_Book_Green', f'{MAT}/MI_GW_Iron')
ensure_component(pk, 'DoorHinge', unreal.SceneComponent, 'SafeRoot').set_editor_property('relative_location', unreal.Vector(0.2, -30, 50))
part(pk, 'SafeDoor', 'Cube', SAFE_GREEN, 'DoorHinge', loc=(2.0, 30, 0), scale=(0.04, 0.60, 0.80))
part(pk, 'SafeDial', 'Cylinder', BRASS, 'DoorHinge', loc=(4.6, 40, 6), rot=(0, 90, 0), scale=(0.11, 0.11, 0.02))
part(pk, 'SafeHandle', 'Cylinder', BRASS, 'DoorHinge', loc=(6.5, 44, -12), rot=(0, 90, 0), scale=(0.03, 0.03, 0.08))
part(pk, 'SafeInside', 'Cube', BLACK, 'SafeRoot', loc=(2.4, 0, 50), scale=(0.005, 0.56, 0.74))
for i, (gy, gz) in enumerate(((-14, 22), (6, 22), (-4, 28.2))):
    part(pk, f'Gold{i}', 'Cube', GOLD, 'SafeRoot', loc=(4.5, gy, gz), scale=(0.08, 0.17, 0.06))
ensure_component(pk, 'AlarmRoot', unreal.SceneComponent, 'DefaultSceneRoot')
part(pk, 'AlarmBox', 'Cube', RED, 'AlarmRoot', loc=(3, 0, 0), scale=(0.06, 0.13, 0.19))
part(pk, 'AlarmHandle', 'Cube', WHITE, 'AlarmRoot', loc=(7, 0, 3), scale=(0.025, 0.09, 0.03))
part(pk, 'AlarmPlate', 'Cube', WHITE, 'AlarmRoot', loc=(6.1, 0, 7.5), scale=(0.002, 0.1, 0.03))
for v, t, r in (('Kind', 'int', NOTIFY), ('Variant', 'int', NOTIFY), ('Slot', 'int', REPL), ('Taken', 'bool', NOTIFY),
                ('BackAt', 'float', None), ('RingUntil', 'float', REPL), ('OpenT0', 'float', None), ('DoorOpen', 'bool', None)):
    ensure_var(pk, v, t, rep=r, category='GW')
ensure_var(pk, 'BallMats', obj_class=unreal.MaterialInterface, array=True, category='GW')
for f in ('ApplyLook', 'OnRep_Kind', 'OnRep_Variant', 'OnRep_Taken', 'StartTest', 'DoorTick'):
    ensure_fn(pk, f)
compile_bp(pk, quiet=True)
cdo(pk).set_editor_property('BallMats', BALL_MATS)
try:
    cdo(pk).set_editor_property('net_update_frequency', 4.0)
except Exception as e:
    print('net_update_frequency:', e)

# ---------------------------------------------------------------- BP_GW_HeldSword: the stolen sword in a guest's hand
hs = actor_bp('BP_GW_HeldSword')
sword_parts(hs)
ensure_var(hs, 'Holder', obj_class=chc, rep=NOTIFY, category='GW')
ensure_var(hs, 'SlashCount', 'int', rep=NOTIFY, category='GW')
ensure_var(hs, 'SwingT0', 'float', category='GW')
ensure_var(hs, 'HandRel', struct=TRS, category='GW')
ensure_var(hs, 'Slash', obj_class=unreal.AnimMontage, category='GW')
for f in ('OnRep_Holder', 'OnRep_SlashCount', 'SwingTick'):
    ensure_fn(hs, f)
compile_bp(hs, quiet=True)
cdo(hs).set_editor_property('HandRel', hand_rel())
cdo(hs).set_editor_property('Slash', SLASH_MONTAGE)

# ---------------------------------------------------------------- BP_GW_ThrownBall: same arc on every machine, server hits
tb = actor_bp('BP_GW_ThrownBall', life=5.0)
part(tb, 'Ball', 'Sphere', BALL_MATS[0], scale=(0.057, 0.057, 0.057))
for v, t, r in (('Go', 'int', NOTIFY), ('Landed', 'int', NOTIFY), ('Variant', 'int', REPL), ('FloorZ', 'float', REPL),
                ('T0', 'float', None), ('DropT0', 'float', None), ('Bounces', 'int', None)):
    ensure_var(tb, v, t, rep=r, category='GW')
for v, r in (('StartLoc', REPL), ('Vel', REPL), ('HitLoc', REPL), ('LastPos', None)):
    ensure_var(tb, v, struct=V3, rep=r, category='GW')
ensure_var(tb, 'Thrower', obj_class=unreal.Pawn, category='GW')
ensure_var(tb, 'BallMats', obj_class=unreal.MaterialInterface, array=True, category='GW')
for f in ('OnRep_Go', 'OnRep_Landed', 'FlyTick'):
    ensure_fn(tb, f)
ensure_fn(tb, 'OnBallHit', inputs=[('Other', unreal.Actor), ('Where', V3)])
compile_bp(tb, quiet=True)
cdo(tb).set_editor_property('BallMats', BALL_MATS)

# ---------------------------------------------------------------- BP_GW_SwapGhost: the spirit flying to its new body
sg = actor_bp('BP_GW_SwapGhost', life=2.5)
body = ensure_component(sg, 'Body', unreal.SkeletalMeshComponent, 'DefaultSceneRoot')
body.set_editor_property('relative_location', unreal.Vector(0, 0, -90))
body.set_editor_property('relative_rotation', unreal.Rotator(roll=0, pitch=0, yaw=-90))
body.set_editor_property('cast_shadow', False)
body.set_collision_enabled(unreal.CollisionEnabled.NO_COLLISION)
body.set_editor_property('animation_mode', unreal.AnimationMode.ANIMATION_SINGLE_NODE)
ad = unreal.SingleAnimationPlayData()
ad.set_editor_property('anim_to_play', unreal.load_asset('/Game/Characters/Mannequins/Anims/Unarmed/Jump/MM_Fall_Loop'))
ad.set_editor_property('saved_looping', True)
ad.set_editor_property('saved_playing', True)
body.set_editor_property('animation_data', ad)
glow = ensure_component(sg, 'Glow', unreal.PointLightComponent, 'DefaultSceneRoot')
glow.set_editor_property('light_color', unreal.Color(r=110, g=170, b=255, a=255))    # (r, g, b, a): a cold blue, like the ghosts
glow.set_editor_property('intensity', 9000.0)          # rendered QA: the flying ghost read too faint
glow.set_editor_property('attenuation_radius', 650.0)
glow.set_editor_property('cast_shadows', False)
boom = ensure_component(sg, 'Boom', unreal.SpringArmComponent, 'DefaultSceneRoot')
boom.set_editor_property('target_arm_length', 300.0)
boom.set_editor_property('socket_offset', unreal.Vector(0, 0, 60))
boom.set_editor_property('relative_rotation', unreal.Rotator(roll=0, pitch=-12, yaw=0))
# rendered QA: without the probe the camera ended up inside bookcases and walls behind the ghost
boom.set_editor_property('do_collision_test', True)
boom.set_editor_property('probe_size', 14.0)
boom.set_editor_property('probe_channel', unreal.CollisionChannel.ECC_VISIBILITY)
ensure_component(sg, 'Cam', unreal.CameraComponent, 'Boom')
ensure_var(sg, 'GhostMesh', obj_class=unreal.SkeletalMesh, rep=NOTIFY, category='GW')
ensure_var(sg, 'GhostMat', obj_class=unreal.MaterialInterface, rep=NOTIFY, category='GW')
ensure_var(sg, 'FromLoc', struct=V3, rep=REPL, category='GW')
ensure_var(sg, 'ToLoc', struct=V3, rep=REPL, category='GW')
ensure_var(sg, 'Swapper', obj_class=unreal.Pawn, rep=REPL, category='GW')
ensure_var(sg, 'Go', 'int', rep=NOTIFY, category='GW')
ensure_var(sg, 'FlyT0', 'float', category='GW')
ensure_var(sg, 'Started', 'bool', category='GW')
for f in ('ApplyGhostLook', 'OnRep_GhostMesh', 'OnRep_GhostMat', 'OnRep_Go', 'StartFly', 'FlyTick'):
    ensure_fn(sg, f)
compile_bp(sg, quiet=True)
for b in (pk, hs, tb, sg):
    save(b)

# ---------------------------------------------------------------- BP_GW_FPItems: first-person sword / ball (local, never replicated)
fp = actor_bp('BP_GW_FPItems', replicates=False)
cdo(fp).set_editor_property('always_relevant', False)
sword_parts(fp)
part(fp, 'Ball', 'Sphere', BALL_MATS[2], scale=(0.057, 0.057, 0.057))
for c_ in ('Grip', 'Pommel', 'Guard', 'Blade', 'Tip', 'Ball'):
    lib_ = unreal.SubobjectDataBlueprintFunctionLibrary
    comp_ = lib_.get_object(subobjects(fp)[c_][1])
    comp_.set_editor_property('cast_shadow', False)
# pose in camera space (X forward, Y right, Z up): the hilt low right, the blade up and slightly inwards
_blade = unreal.Vector(0.35, -0.1, 0.93)
_blade = _blade.normal()
FP_SWORD_ROT = unreal.MathLibrary.make_rot_from_zx(_blade, unreal.Vector(1, 0, 0))
ensure_component(fp, 'SwordRoot', unreal.SceneComponent, 'DefaultSceneRoot').set_editor_property('relative_location', unreal.Vector(36, 27, -31))
subobj_root = unreal.SubobjectDataBlueprintFunctionLibrary.get_object(subobjects(fp)['SwordRoot'][1])
subobj_root.set_editor_property('relative_rotation', FP_SWORD_ROT)
subobj_root.set_editor_property('relative_scale3d', unreal.Vector(0.8, 0.8, 0.8))
subobj_ball = unreal.SubobjectDataBlueprintFunctionLibrary.get_object(subobjects(fp)['Ball'][1])
subobj_ball.set_editor_property('relative_location', unreal.Vector(34, 17, -19))
for v, t in (('SwingT0', 'float'), ('SeenSlash', 'int')):
    ensure_var(fp, v, t, category='GW')
ensure_var(fp, 'BaseRot', struct=unreal.Rotator.static_struct(), category='GW')
for f in ('FPSwingTick', 'StartSwing'):
    ensure_fn(fp, f)
compile_bp(fp, quiet=True)
cdo(fp).set_editor_property('BaseRot', FP_SWORD_ROT)
save(fp)

# ---------------------------------------------------------------- player state: the inventory
ps_bp = load_bp('BP_GW_PlayerState')
ensure_var(ps_bp, 'Balls', 'int', rep=REPL, category='GW')
ensure_var(ps_bp, 'HasSword', 'bool', rep=REPL, category='GW')
ensure_var(ps_bp, 'HasSwapGun', 'bool', rep=REPL, category='GW')       # sold by s34_shop.py (item 8)
ensure_var(ps_bp, 'SwapReadyAt', 'float', rep=REPL, category='GW')     # server time (GM.Now) when it can fire again
ensure_var(ps_bp, 'SwordActor', obj_class=hs.generated_class(), category='GW')   # server only
compile_bp(ps_bp)
save(ps_bp)

# ---------------------------------------------------------------- signatures: game mode, player controller
gm = load_bp('BP_GW_GameMode')
pkc, tbc = pk.generated_class(), tb.generated_class()
for v, t in (('PickupsOn', 'bool'), ('PickupRound', 'int')):
    ensure_var(gm, v, t, category='GW')
ensure_var(gm, 'SwapLoc', struct=V3, category='GW')
ensure_var(gm, 'SlashVictim', obj_class=chc, category='GW')
ensure_var(gm, 'NoChar', obj_class=chc, category='GW')
for v, t in (('SafeCode', 'int'), ('PostTries', 'int'), ('PostOK', 'bool')):
    ensure_var(gm, v, t, category='GW')
ensure_var(gm, 'PostSpot', struct=V3, category='GW')
GMF = {
    'PickupTick': ([], []), 'PickupSpawn': ([], []),
    'SpawnPickup': ([('Kind', 'int'), ('Slot', 'int'), ('Variant', 'int'), ('Loc', V3), ('Rot', unreal.Rotator.static_struct())], []),
    'TakePickup': ([('P', pkc), ('Who', unreal.Pawn)], []),
    'SyncSword': ([('PS', ps_bp.generated_class())], []),
    'ThrowBall': ([('Thrower', chc), ('Dir', V3)], []),
    'LaunchBall': ([('Thrower', unreal.Pawn), ('Start', V3), ('Aim', V3)], []),
    'BallHit': ([('Thrower', unreal.Pawn), ('Other', unreal.Actor), ('Where', V3), ('Dir', V3)], []),
    'WeaponHit': ([('Attacker', unreal.Pawn), ('Victim', chc), ('Dir', V3), ('Weapon', 'int')], []),
    'SlashTarget': ([('Attacker', chc), ('Dir', V3)], [('Victim', chc)]),
    'Slash': ([('Attacker', chc), ('Dir', V3)], []),
    'SwapStart': ([('Old', chc), ('Target', chc)], []),
    'SwapEffects': ([('Old', chc), ('Target', chc)], []),
    'PlacePostIt': ([], []),
    'OpenSafe': ([('P', pkc), ('Who', unreal.Pawn)], []),
    'PullAlarm': ([('P', pkc), ('Who', unreal.Pawn)], []),
    'Fart': ([('P', pkc), ('Who', unreal.Pawn)], []),
    'ShopPay': ([('PS', ps_bp.generated_class()), ('Amount', 'int'), ('Note', 'string')], []),    # body: s34_shop.py
}
for f, (ins, outs) in GMF.items():
    ensure_fn(gm, f, inputs=ins, outputs=outs)
for f in ('HurtCharacter', 'DeathCry', 'StartPanic', 'WorldSound', 'RewardNPCKill', 'KillPlayer', 'UpdateCounts'):
    assert get_graph(gm, f) is not None, f'BP_GW_GameMode.{f} is missing (run s12 / s31 / s32 first)'
if not SKIP_GM:
    compile_bp(gm, quiet=True)
for fn, n in (('SlashTarget', 'BestD'),):
    g = get_graph(gm, fn)
    if n not in BT.list_variables(gm, g):
        BT.add_variable(gm, n, 'float', graph=g)
g = get_graph(gm, 'SlashTarget')
if 'BestT' not in BT.list_variables(gm, g):
    BT.add_object_variable(gm, 'BestT', chc, graph=g)

pc = load_bp('BP_GW_PlayerController')
kp = load_bp('BP_GW_KeyPrompt')
for v, t in (('NextAttackAt', 'float'), ('SeenBalls', 'int'), ('SeenSword', 'bool'), ('SeenSwapReady', 'bool'),
             ('PTStep', 'int'), ('PTWait', 'int'), ('PTReady', 'bool')):
    ensure_var(pc, v, t, category='GW')
ensure_var(pc, 'PickupPrompt', obj_class=kp.generated_class(), category='GW')
ensure_var(pc, 'PromptFor', obj_class=pkc, category='GW')
ensure_var(pc, 'NoPickup', obj_class=pkc, category='GW')
ensure_var(pc, 'SwapTarget', obj_class=chc, category='GW')
ensure_var(pc, 'SwapOld', obj_class=chc, category='GW')
ensure_var(pc, 'NoSwapChar', obj_class=chc, category='GW')
ensure_var(pc, 'SeenPawn', obj_class=unreal.Pawn, category='GW')
for v, t, r in (('KnownCode', 'int', REPL), ('KnownRound', 'int', REPL), ('PostReads', 'int', REPL), ('NextFartAt', 'float', None),
                ('AlarmGone', 'bool', None), ('SeenKnownRound', 'int', None), ('AlarmOn', 'bool', None)):
    ensure_var(pc, v, t, rep=r, category='GW')         # a PlayerController replicates to its owner only: the code stays secret
ensure_var(pc, 'PullAlarmComp', obj_class=unreal.AudioComponent, category='GW')
ensure_var(pc, 'NoAlarmComp', obj_class=unreal.AudioComponent, category='GW')
ensure_var(pc, 'FPItems', obj_class=fp.generated_class(), category='GW')
ensure_var(pc, 'FPOn', 'bool', category='GW')
ensure_var(pc, 'FPAttach', obj_class=unreal.Pawn, category='GW')
ensure_var(pc, 'DevAimTarget', obj_class=chc, category='GW')
ensure_var(pc, 'SwapDbg', 'string', category='GW')        # server side: the host's own tests use it
PCF = {
    'TryPickup': ([], [('Handled', 'bool')]),
    'GuestAttack': ([('Ch', chc)], []),                       # stub created by s34_shop.py; the body is ours
    'PickupClientTick': ([], []), 'PickupNotices': ([], []), 'RequestSwap': ([], []), 'SwapFinish': ([], []),
    'PickupNotice': ([('Msg', 'string')], []),
    'GuestOK': ([('Ch', chc), ('NeedHunt', 'bool')], [('Ok', 'bool')]),
    'NearPickupFor': ([('Ch', chc)], [('P', pkc)]),
    'AimDir': ([('Pitch', 'float'), ('Yaw', 'float')], [('Dir', V3)]),
    'SwapCast': ([('Ch', chc), ('A', unreal.Actor)], [('T', chc)]),
    'SwapTargetFor': ([('Ch', chc), ('Dir', V3)], [('T', chc)]),
    'DevAimLocal': ([('Mode', 'int'), ('Dist', 'float')], []), 'DevAimSpot': ([('Ch', chc), ('T', chc), ('Dist', 'float')], []),
    'PickupTestTick': ([], []), 'PTHost': ([('St', 'int')], []), 'PTClient': ([('St', 'int')], []), 'PTHostNet': ([('St', 'int')], []),
    'PTLog': ([('St', 'int')], []), 'PTAttack': ([], []), 'PTShots': ([('St', 'int')], []), 'PTShotSoon': ([('Delay', 'float')], []), 'PTShotNow': ([], []), 'DevLookAt': ([('Kind', 'int'), ('Up', 'float')], []),
    'PlayerOK': ([('Ch', chc)], [('Ok', 'bool')]), 'KnowsCode': ([], [('Ok', 'bool')]),
    'PromptLabel': ([('P', pkc)], [('Label', 'string')]), 'AlarmRinging': ([], [('On', 'bool')]), 'AlarmClientTick': ([], []),
    'FPItemsTick': ([], []),
}
for f, (ins, outs) in PCF.items():
    ensure_fn(pc, f, inputs=ins, outputs=outs)
EXF = {'GWPickup': [], 'GWGuestAttack': [('Pitch', 'float'), ('Yaw', 'float')], 'GWSwap': [('Pitch', 'float'), ('Yaw', 'float')],
       'GWDevGiveBall': [], 'GWDevGiveSword': [], 'GWDevGiveSwap': [], 'GWDevPickupSpawn': [],
       'GWDevAimAt': [('Mode', 'int'), ('Dist', 'float')], 'GWDevLearnCode': [], 'GWDevAlarmReset': [], 'GWDevFart': [],
       'GWDevGoTo': [('Kind', 'int')], 'GWDevBallAt': []}
for f, ins in EXF.items():
    ensure_fn(pc, f, inputs=ins, exec_fn=True)
assert get_graph(pc, 'DevOK') is not None, 'run u15_dev_menu.py first (DevOK)'
compile_bp(pc, quiet=True)
for fn, locs in (('NearPickupFor', [('BestD', 'float', None), ('BestP', None, pkc)]),
                 ('SwapCast', [('NoT', None, chc)]),
                 ('DevAimLocal', [('BestD', 'float', None), ('BestT', None, chc)]),
                 ('GWDevAimAt', [('BestD', 'float', None), ('BestT', None, chc)]),
                 ('DevAimSpot', [('Found', 'bool', None), ('Spot', V3, None)]),
                 ('SwapFinish', [('T2', None, chc), ('O2', None, chc), ('Lost', 'bool', None)]),
                 ('GWDevGoTo', [('BestT', None, pkc)]),
                 ('GWDevBallAt', [('BestD', 'float', None), ('BestT', None, chc)]),
                 ('DevLookAt', [('BestD', 'float', None), ('BestP', None, pkc)])):
    g = get_graph(pc, fn)
    have = BT.list_variables(pc, g)
    for n, t, o in locs:
        if n in have:
            continue
        if o is not None:
            BT.add_object_variable(pc, n, o, graph=g)
        elif isinstance(t, unreal.ScriptStruct):
            BT.add_struct_variable(pc, n, t, graph=g)
        else:
            BT.add_variable(pc, n, t, graph=g)
compile_bp(pc, quiet=True)

# ---------------------------------------------------------------- bodies: pickup actor
P = lambda var: f'GW|Get|{PK}|{var}'
PS_ = lambda var, ps='ps': f'(GW|Get|BP_GW_PlayerState|{var} :self {ps})'
sword_vis = '(Rendering|SetVisibility :self (Variables|Default|GetSwordRoot) :bNewVisibility sword :bPropagateToChildren true)'
VIS = lambda comp, on, prop='false': f'(Rendering|SetVisibility :self (Variables|Default|Get{comp}) :bNewVisibility {on} :bPropagateToChildren {prop})'
write(pk, 'ApplyLook', f'''
(fn ApplyLook ()
  (bind k (Variables|GW|GetKind))
  (bind taken (Variables|GW|GetTaken))
  (bind ball (and (== k 0) (not taken)))
  (bind sword (and (== k 1) (not taken)))
  (Rendering|SetVisibility :self (Variables|Default|GetBall) :bNewVisibility ball :bPropagateToChildren false)
  {sword_vis}
  {VIS('PostIt', '(== k 2)')}
  {VIS('SafeRoot', '(== k 3)', 'true')}
  {VIS('AlarmRoot', '(== k 4)', 'true')}
  {VIS('DoorHinge', '(and (== k 3) taken)', 'true')}
  {VIS('SafeInside', '(and (== k 3) taken)')}
  {VIS('Gold0', '(and (== k 3) taken)')}
  {VIS('Gold1', '(and (== k 3) taken)')}
  {VIS('Gold2', '(and (== k 3) taken)')}
  (Transformation|SetRelativeLocation :self (Variables|Default|GetAlarmHandle) :NewLocation (Math|Vector|MakeVector 7.0 0.0 (select taken -5.0 3.0)) :bSweep false :bTeleport true)
  ; the safe door swings open once (late joiners see it swing too), and shuts again for a new round
  (if (and (== k 3) (and taken (not (Variables|GW|GetDoorOpen))))
    (Variables|GW|SetDoorOpen true)
    (Variables|GW|SetOpenT0 (Utilities|Time|GetGameTimeinSeconds))
    (Utilities|Time|SetTimerbyFunctionName :Object self :FunctionName "DoorTick" :Time 0.016 :bLooping true))
  (if (and (== k 3) (and (not taken) (Variables|GW|GetDoorOpen)))
    (Variables|GW|SetDoorOpen false)
    (Utilities|Time|ClearTimerbyFunctionName :Object self :FunctionName "DoorTick")
    (Transformation|SetRelativeRotation :self (Variables|Default|GetDoorHinge) :NewRotation (Math|Rotator|MakeRotator :Roll 0.0 :Pitch 0.0 :Yaw 0.0) :bSweep false :bTeleport true))
  (bind mats (Variables|GW|GetBallMats))
  (bind vi (Variables|GW|GetVariant))
  (if (and (>= vi 0) (< vi (Utilities|Array|Length mats)))
    (Rendering|Material|SetMaterial :self (Variables|Default|GetBall) :ElementIndex 0 :Material (Utilities|Array|Get(acopy) mats vi))))
''', compile_after=False)
for f in ('OnRep_Kind', 'OnRep_Variant', 'OnRep_Taken'):
    write(pk, f, f'(fn {f} () (CallFunction|ApplyLook))', compile_after=False)
write(pk, 'DoorTick', '''
(fn DoorTick ()
  (bind u (Math|Float|Min(Float) (/ (- (Utilities|Time|GetGameTimeinSeconds) (Variables|GW|GetOpenT0)) 1.1) 1.0))
  (bind e (* (* u u) (- 3.0 (* 2.0 u))))
  (Transformation|SetRelativeRotation :self (Variables|Default|GetDoorHinge) :NewRotation (Math|Rotator|MakeRotator :Roll 0.0 :Pitch 0.0 :Yaw (* e -105.0)) :bSweep false :bTeleport true)
  (if (>= u 1.0)
    (Utilities|Time|ClearTimerbyFunctionName :Object self :FunctionName "DoorTick")))
''', compile_after=False)
# -GWPickupTest: the first pickup starts the test driver on this machine's player controller (s38 PickupTestTick)
write(pk, 'StartTest', '''
(fn StartTest ()
  (if (or (!= (Variables|GW|GetSlot) 0) (!= (Variables|GW|GetKind) 0))
    (return))
  (bind pc (Game|GetPlayerController :PlayerIndex 0))
  (if (GW|Call|/Script/Engine.KismetSystemLibrary|IsValid :Object pc)
    (Utilities|Time|SetTimerbyFunctionName :Object pc :FunctionName "PickupTestTick" :Time 1.0 :bLooping true)
    (Development|PrintString :InString "GW: pickup test driver started" :bPrintToScreen false)
    (else
      (Utilities|Time|SetTimerbyFunctionName :Object self :FunctionName "StartTest" :Time 1.0 :bLooping false))))
''', compile_after=False)
write(pk, 'EventGraph', '''
(event EventBeginPlay
  (CallFunction|ApplyLook)
  (if (and (Utilities|HasLaunchOption :OptionToCheck "GWPickupTest") (and (== (Variables|GW|GetSlot) 0) (== (Variables|GW|GetKind) 0)))
    (Utilities|Time|SetTimerbyFunctionName :Object self :FunctionName "StartTest" :Time 3.0 :bLooping false)))
''', compile_after=False)
compile_bp(pk)
print('BP_GW_Pickup', node_problems(pk))
save(pk)

# ---------------------------------------------------------------- bodies: held sword (swing = chop of the blade)
write(hs, 'OnRep_Holder', '''
(fn OnRep_Holder ()
  (bind h (Variables|GW|GetHolder))
  (if (not (GW|Call|/Script/Engine.KismetSystemLibrary|IsValid :Object h))
    (return))
  (Transformation|AttachActorToComponent :self self :Parent (GW|Get|/Script/Engine.Character|Mesh :self h) :SocketName "hand_r" :LocationRule "SnapToTarget" :RotationRule "SnapToTarget" :ScaleRule "KeepWorld" :bWeldSimulatedBodies false)
  (Transformation|SetActorRelativeTransform :self self :NewRelativeTransform (Variables|GW|GetHandRel) :bSweep false :bTeleport true))
''', compile_after=False)
write(hs, 'OnRep_SlashCount', '''
(fn OnRep_SlashCount ()
  (if (<= (Variables|GW|GetSlashCount) 0)
    (return))
  (Variables|GW|SetSwingT0 (Utilities|Time|GetGameTimeinSeconds))
  (Utilities|Time|SetTimerbyFunctionName :Object self :FunctionName "SwingTick" :Time 0.016 :bLooping true)
  (bind h (Variables|GW|GetHolder))
  (if (GW|Call|/Script/Engine.KismetSystemLibrary|IsValid :Object h)
    (Animation|PlayAnimMontage :self h :AnimMontage (Variables|GW|GetSlash) :InPlayRate 1.35)))
''', compile_after=False)
# raise (0-30 % of 0.34 s), chop through (30-75 %), come back (75-100 %)
write(hs, 'SwingTick', '''
(fn SwingTick ()
  (bind u (/ (- (Utilities|Time|GetGameTimeinSeconds) (Variables|GW|GetSwingT0)) 0.34))
  (if (>= u 1.0)
    (Utilities|Time|ClearTimerbyFunctionName :Object self :FunctionName "SwingTick")
    (Transformation|SetRelativeRotation :self (Variables|Default|GetSwordRoot) :NewRotation (Math|Rotator|MakeRotator :Roll 0.0 :Pitch 0.0 :Yaw 0.0) :bSweep false :bTeleport true)
    (return))
  (bind a (select (< u 0.3) (* (/ u 0.3) -75.0) (select (< u 0.75) (+ -75.0 (* (/ (- u 0.3) 0.45) 160.0)) (* (- 1.0 (/ (- u 0.75) 0.25)) 85.0))))
  (Transformation|SetRelativeRotation :self (Variables|Default|GetSwordRoot) :NewRotation (Math|Rotator|MakeRotator :Roll 0.0 :Pitch a :Yaw 0.0) :bSweep false :bTeleport true))
''', compile_after=False)
compile_bp(hs)
print('BP_GW_HeldSword', node_problems(hs))
save(hs)

# ---------------------------------------------------------------- bodies: thrown ball
write(tb, 'OnRep_Go', f'''
(fn OnRep_Go ()
  (if (<= (Variables|GW|GetGo) 0)
    (return))
  (bind mats (Variables|GW|GetBallMats))
  (bind vi (Variables|GW|GetVariant))
  (if (and (>= vi 0) (< vi (Utilities|Array|Length mats)))
    (Rendering|Material|SetMaterial :self (Variables|Default|GetBall) :ElementIndex 0 :Material (Utilities|Array|Get(acopy) mats vi)))
  (Variables|GW|SetT0 (Utilities|Time|GetGameTimeinSeconds))
  (Variables|GW|SetLastPos (Variables|GW|GetStartLoc))
  (Transformation|SetActorLocation :self self :NewLocation (Variables|GW|GetStartLoc) :bSweep false :bTeleport true)
  (Utilities|Time|SetTimerbyFunctionName :Object self :FunctionName "FlyTick" :Time 0.016 :bLooping true))
''', compile_after=False)
write(tb, 'OnRep_Landed', '''
(fn OnRep_Landed ()
  (if (> (Variables|GW|GetLanded) 0)
    (Variables|GW|SetDropT0 (Utilities|Time|GetGameTimeinSeconds))))
''', compile_after=False)
write(tb, 'FlyTick', f'''
(fn FlyTick ()
  (bind now (Utilities|Time|GetGameTimeinSeconds))
  (if (> (Variables|GW|GetLanded) 0)
    ; after the impact the ball just drops to the floor under the hit point
    (bind dt (- now (Variables|GW|GetDropT0)))
    (bind hl (Variables|GW|GetHitLoc))
    (bind z (Math|Float|Max(Float) (Variables|GW|GetFloorZ) (- (.z hl) (* 490.0 (* dt dt)))))
    (Transformation|SetActorLocation :self self :NewLocation (Math|Vector|MakeVector (.x hl) (.y hl) z) :bSweep false :bTeleport true)
    (if (<= z (Variables|GW|GetFloorZ))
      (Utilities|Time|ClearTimerbyFunctionName :Object self :FunctionName "FlyTick"))
    (return))
  (bind ft (- now (Variables|GW|GetT0)))
  (bind drop (* {-0.5 * BALL_G} (* ft ft)))
  (bind pos (+ (+ (Variables|GW|GetStartLoc) ({VMUL} :A (Variables|GW|GetVel) :B ft)) (Math|Vector|MakeVector 0.0 0.0 drop)))
  (if (Networking|HasAuthority)
    (bind (hit ok) (Collision|SphereTraceByProfile :Start (Variables|GW|GetLastPos) :End pos :Radius 5.0 :ProfileName "BlockAll" :bTraceComplex false :bIgnoreSelf true))
    (bind (bBlock bInit hTime hDist hLoc hImpact hNormal hImpNormal hPhys hActor) (Collision|BreakHitResult hit))
    (if (and ok (!= hActor (Variables|GW|GetThrower)))
      (CallFunction|OnBallHit :Other hActor :Where hLoc)
      (return)))
  (Variables|GW|SetLastPos pos)
  (Transformation|SetActorLocation :self self :NewLocation pos :bSweep false :bTeleport true))
''', compile_after=False)
write(tb, 'OnBallHit', f'''
(fn OnBallHit (Other Where)
  (Variables|GW|SetHitLoc Where)
  (bind gm {GMC}
    (:then
      ; first the damage (a victim's capsule stops colliding when it dies), then where the ball falls
      (GW|Call|BP_GW_GameMode|BallHit :self gm :Thrower (Variables|GW|GetThrower) :Other Other :Where Where :Dir (Math|Vector|Normalize (Variables|GW|GetVel)))
      (bind (fh fok) (Collision|LineTraceByChannel :Start (+ Where (Math|Vector|MakeVector 0.0 0.0 2.0)) :End (- Where (Math|Vector|MakeVector 0.0 0.0 400.0)) :TraceChannel "Visibility" :bTraceComplex false :bIgnoreSelf true))
      (bind (fb fi ft fd fl fImpact fn2 fin fp fa) (Collision|BreakHitResult fh))
      (Variables|GW|SetFloorZ (select fok (+ (.z fImpact) {BALL_R}) (- (.z Where) 400.0)))
      (Variables|GW|SetLanded 1)
      (Actor|SetLifeSpan :self self :InLifespan 3.0))
    (:CastFailed)))
''', compile_after=False)
compile_bp(tb)
print('BP_GW_ThrownBall', node_problems(tb))
save(tb)

# ---------------------------------------------------------------- bodies: swap ghost
write(sg, 'ApplyGhostLook', f'''
(fn ApplyGhostLook ()
  (bind b (Variables|Default|GetBody))
  (if ({ISVALID} :Object (Variables|GW|GetGhostMesh))
    (Components|SkeletalMesh|SetSkeletalMeshAsset :self b :NewMesh (Variables|GW|GetGhostMesh)))
  (if ({ISVALID} :Object (Variables|GW|GetGhostMat))
    (Rendering|Material|SetMaterial :self b :ElementIndex 0 :Material (Variables|GW|GetGhostMat))
    (Rendering|Material|SetMaterial :self b :ElementIndex 1 :Material (Variables|GW|GetGhostMat))))
''', compile_after=False)
write(sg, 'OnRep_GhostMesh', '(fn OnRep_GhostMesh () (CallFunction|ApplyGhostLook))', compile_after=False)
write(sg, 'OnRep_GhostMat', '(fn OnRep_GhostMat () (CallFunction|ApplyGhostLook))', compile_after=False)
write(sg, 'OnRep_Go', '(fn OnRep_Go () (CallFunction|StartFly))', compile_after=False)
write(sg, 'StartFly', f'''
(fn StartFly ()
  (if (or (Variables|GW|GetStarted) (<= (Variables|GW|GetGo) 0))
    (return))
  (Variables|GW|SetStarted true)
  (CallFunction|ApplyGhostLook)
  (Variables|GW|SetFlyT0 (Utilities|Time|GetGameTimeinSeconds))
  (Transformation|SetActorLocation :self self :NewLocation (Variables|GW|GetFromLoc) :bSweep false :bTeleport true)
  (Utilities|Time|SetTimerbyFunctionName :Object self :FunctionName "FlyTick" :Time 0.016 :bLooping true)
  ; the swapper watches its own ghost fly over (local camera only; the server's possession brings it back)
  (bind pc (Game|GetPlayerController :PlayerIndex 0))
  (bind sw (Variables|GW|GetSwapper))
  (if (and ({ISVALID} :Object pc) ({ISVALID} :Object sw))
    (if (== (Pawn|GetControlledPawn :self pc) sw)
      (Game|Player|SetViewTargetwithBlend :self pc :NewViewTarget self :BlendTime 0.2)
      (Development|PrintString :InString (cat "GW: swap ghost view on " (select (Networking|HasAuthority) "host" "client")) :bPrintToScreen false))))
''', compile_after=False)
write(sg, 'FlyTick', f'''
(fn FlyTick ()
  (bind u (Math|Float|Min(Float) (/ (- (Utilities|Time|GetGameTimeinSeconds) (Variables|GW|GetFlyT0)) {SWAP_FLY}) 1.0))
  (bind e (* (* u u) (- 3.0 (* 2.0 u))))
  (bind a (Variables|GW|GetFromLoc))
  (bind b (Variables|GW|GetToLoc))
  (bind p (+ (+ a ({VMUL} :A (- b a) :B e)) (Math|Vector|MakeVector 0.0 0.0 (* (Math|Trig|Sin(Degrees) (* u 180.0)) 110.0))))
  (Transformation|SetActorLocationAndRotation :self self :NewLocation p :NewRotation (Math|Rotator|MakeRotator :Roll 0.0 :Pitch 0.0 :Yaw (.yaw (Math|Rotator|FindLookatRotation :Start a :Target b))) :bSweep false :bTeleport true)
  (if (>= u 1.0)
    (Utilities|Time|ClearTimerbyFunctionName :Object self :FunctionName "FlyTick")
    (Rendering|SetActorHiddenInGame :self self :bNewHidden true)))
''', compile_after=False)
write(sg, 'EventGraph', '''
(event EventBeginPlay
  (CallFunction|ApplyGhostLook)
  (CallFunction|StartFly))
''', compile_after=False)
compile_bp(sg)
print('BP_GW_SwapGhost', node_problems(sg))
save(sg)

write(fp, 'StartSwing', '''
(fn StartSwing ()
  (Variables|GW|SetSwingT0 (Utilities|Time|GetGameTimeinSeconds))
  (Utilities|Time|SetTimerbyFunctionName :Object self :FunctionName "FPSwingTick" :Time 0.016 :bLooping true))
''', compile_after=False)
# a chop: the blade dips forward and across (0.3 s), then comes back
write(fp, 'FPSwingTick', '''
(fn FPSwingTick ()
  (bind u (/ (- (Utilities|Time|GetGameTimeinSeconds) (Variables|GW|GetSwingT0)) 0.3))
  (bind base (Variables|GW|GetBaseRot))
  (if (>= u 1.0)
    (Utilities|Time|ClearTimerbyFunctionName :Object self :FunctionName "FPSwingTick")
    (Transformation|SetRelativeRotation :self (Variables|Default|GetSwordRoot) :NewRotation base :bSweep false :bTeleport true)
    (return))
  (bind a (select (< u 0.35) (* (/ u 0.35) 70.0) (* (- 1.0 (/ (- u 0.35) 0.65)) 70.0)))
  (Transformation|SetRelativeRotation :self (Variables|Default|GetSwordRoot) :NewRotation (Math|Rotator|CombineRotators :A base :B (Math|Rotator|MakeRotator :Roll (* a -0.4) :Pitch (* a -1.0) :Yaw (* a 0.5))) :bSweep false :bTeleport true))
''', compile_after=False)
compile_bp(fp)
print('BP_GW_FPItems', node_problems(fp))
save(fp)

# ---------------------------------------------------------------- bodies: game mode
mv = lambda v: f'(Math|Vector|MakeVector {v[0]:.2f} {v[1]:.2f} {v[2]:.2f})'
mr = lambda r: f'(Math|Rotator|MakeRotator :Roll {r.roll:.3f} :Pitch {r.pitch:.3f} :Yaw {r.yaw:.3f})'
spawns = [f'  (CallFunction|SpawnPickup :Kind 0 :Slot {i} :Variant {i % len(BALL_MATS)} :Loc {mv((x, y, FELT_Z + BALL_R))} :Rot {mr(unreal.Rotator(0, 0, 0))})'
          for i, (x, y) in enumerate(BALLS)]
for j, x in enumerate(ARMOURS):
    g_, r_ = sword_spot(x)
    spawns.append(f'  (CallFunction|SpawnPickup :Kind 1 :Slot {len(BALLS) + j} :Variant 0 :Loc {mv((g_.x, g_.y, g_.z))} :Rot {mr(r_)})')
spawns.append(f'  (CallFunction|SpawnPickup :Kind 3 :Slot 10 :Variant 0 :Loc {mv(SAFE_FRONT)} :Rot {mr(unreal.Rotator(0, 0, SAFE_YAW))})')
ALARMS = {}
for room in ALARM_CANDIDATES:
    spot = wall_spot(room)
    if spot:
        ALARMS[room] = spot
        spawns.append(f'  (CallFunction|SpawnPickup :Kind 4 :Slot {11 + len(ALARMS)} :Variant 0 :Loc {mv(spot[0])} :Rot {mr(unreal.Rotator(0, 0, spot[1]))})')
print('alarm boxes', {k: (tuple(round(c) for c in v[0]), round(v[1])) for k, v in ALARMS.items()})
spawns.append('''  (for m (Actor|GetAllActorswithTag :Tag "GW_Toilet")
    (CallFunction|SpawnPickup :Kind 5 :Slot 30 :Variant 0 :Loc (Transformation|GetActorLocation :self m) :Rot (Transformation|GetActorRotation :self m)))
  (Variables|GW|SetSafeCode (Math|Random|RandomIntegerinRange 1000 9999))
  (CallFunction|PlacePostIt)''')
SET_PK = lambda var, val, obj='p': f'(GW|Set|{PK}|{var} :self {obj} :{var} {val})'
inrect = lambda r, v: f'(and (and (>= (.x {v}) {r[0]}.0) (<= (.x {v}) {r[1]}.0)) (and (>= (.y {v}) {r[2]}.0) (<= (.y {v}) {r[3]}.0)))'
# s39 (voice director): panic with a cause (2 = fire: the guests shout about fire, not about a gunshot) and the guests'
# reactions to a fart (cat 65 fart_react), used once s39 has created them
_s39 = get_graph(gm, 'StartPanicCause') is not None
ALARM_PANIC = ('(CallFunction|StartPanicCause :Loc (Transformation|GetActorLocation :self P) :Dur 10.0 :Cause 2)' if _s39 else
               '(CallFunction|StartPanic :Loc (Transformation|GetActorLocation :self P) :Dur 10.0)')
FART_REACT = '(CallFunction|SayNearPlayers :Cat 65 :PerPlayer 1 :Delay 1.2 :Spread 1.5)' if _s39 else '; (s39 fart_react not there yet)'
print('s39 present:', _s39)
GM_W = {
    'SpawnPickup': f'''
(fn SpawnPickup (Kind Slot Variant Loc Rot)
  (bind p (Game|SpawnActorfromClass :Class "{PK}" :SpawnTransform (Math|Transform|MakeTransform :Location Loc :Rotation Rot) :CollisionHandlingOverride "AlwaysSpawn"))
  {SET_PK('Kind', 'Kind')}
  {SET_PK('Slot', 'Slot')}
  {SET_PK('Variant', 'Variant')}
  {SET_PK('Taken', 'false')})
''',
    'PickupSpawn': '(fn PickupSpawn ()\n  (Variables|GW|SetPickupsOn true)\n' + '\n'.join(spawns) + f'''
  (Development|PrintString :InString (cat "GW: pickups spawned: {len(BALLS)} billiard balls, {len(ARMOURS)} swords, safe, {len(ALARMS)} fire alarms, toilets=" (Utilities|Array|Length (Actor|GetAllActorswithTag :Tag "GW_Toilet"))) :bPrintToScreen false))
''',
    # 4 Hz from ReactionsTick: spawn once, bring pickups back, empty inventories on a new round / a death, swords in hands
    'PickupTick': f'''
(fn PickupTick ()
  (if (not (Variables|GW|GetPickupsOn))
    (CallFunction|PickupSpawn))
  (bind s (CallFunction|GetGS))
  (bind now (CallFunction|Now))
  (if (!= (GW|Get|BP_GW_GameState|RoundNumber :self s) (Variables|GW|GetPickupRound))
    (Variables|GW|SetPickupRound (GW|Get|BP_GW_GameState|RoundNumber :self s))
    (for ps (CallFunction|GetGWPlayers)
      (GW|Set|BP_GW_PlayerState|Balls :self ps :Balls 0)
      (GW|Set|BP_GW_PlayerState|HasSword :self ps :HasSword false))
    ; balls, swords and the safe come back each round; the fire alarm is once per game; a new code, a new post-it
    (for p (Actor|GetAllActorsOfClass :ActorClass "{PK}")
      (bind k ({P('Kind')} :self p))
      (if (or (<= k 1) (== k 3))
        {SET_PK('Taken', 'false')}))
    (Variables|GW|SetSafeCode (Math|Random|RandomIntegerinRange 1000 9999))
    (CallFunction|PlacePostIt)
    (Development|PrintString :InString (cat "GW: pickups reset for round " (Variables|GW|GetPickupRound)) :bPrintToScreen false))
  (for p (Actor|GetAllActorsOfClass :ActorClass "{PK}")
    (if (and (and (<= ({P('Kind')} :self p) 1) ({P('Taken')} :self p)) (>= now ({P('BackAt')} :self p)))
      {SET_PK('Taken', 'false')}
      (Development|PrintString :InString (cat "GW: pickup back: slot " ({P('Slot')} :self p)) :bPrintToScreen false)))
  (for ps (CallFunction|GetGWPlayers)
    (if (not {PS_('IsAlive')})
      (if (or (> {PS_('Balls')} 0) {PS_('HasSword')})
        (GW|Set|BP_GW_PlayerState|Balls :self ps :Balls 0)
        (GW|Set|BP_GW_PlayerState|HasSword :self ps :HasSword false)))
    (CallFunction|SyncSword :PS ps))
  ; a sword left behind by a player who quit (its holder gone or dead): away with it
  (for h (Actor|GetAllActorsOfClass :ActorClass "{HS}")
    (bind hd (GW|Get|{HS}|Holder :self h))
    (if (not ({ISVALID} :Object hd))
      (Actor|DestroyActor :self h)
      (elif (GW|Get|BP_GW_Character|IsDead :self hd)
        (Actor|DestroyActor :self h)))))
''',
    'SyncSword': f'''
(fn SyncSword (PS)
  (bind cur (GW|Get|BP_GW_PlayerState|SwordActor :self PS))
  (bind c (Utilities|Casting|CastToBP_GW_Character (PlayerState|GetPawn :self PS))
    (:then
      (bind want (and (GW|Get|BP_GW_PlayerState|HasSword :self PS) (not (GW|Get|BP_GW_Character|IsDead :self c))))
      (if (and want ({ISVALID} :Object cur))
        (if (== (GW|Get|{HS}|Holder :self cur) c)
          (return)))
      (if ({ISVALID} :Object cur)
        (Actor|DestroyActor :self cur))
      (if want
        (bind h (Game|SpawnActorfromClass :Class "{HS}" :SpawnTransform (Math|Transform|MakeTransform :Location (Transformation|GetActorLocation :self c)) :CollisionHandlingOverride "AlwaysSpawn"))
        (GW|Set|BP_GW_PlayerState|SwordActor :self PS :SwordActor h)
        (GW|Set|{HS}|Holder :self h :Holder c)
        (Development|PrintString :InString (cat "GW: sword in the hand of " (PlayerState|GetPlayerName :self PS)) :bPrintToScreen false)))
    (:CastFailed
      (if ({ISVALID} :Object cur)
        (Actor|DestroyActor :self cur)))))
''',
    'TakePickup': f'''
(fn TakePickup (P Who)
  (bind ps (CallFunction|PSOf :P Who))
  (if (or (not ({ISVALID} :Object ps)) ({P('Taken')} :self P))
    (return))
  (bind k ({P('Kind')} :self P))
  {SET_PK('Taken', 'true', 'P')}
  {SET_PK('BackAt', f'(+ (CallFunction|Now) (select (== k 0) {BALL_BACK} {SWORD_BACK}))', 'P')}
  (if (== k 0)
    (GW|Set|BP_GW_PlayerState|Balls :self ps :Balls (+ {PS_('Balls')} 1))
    (CallFunction|WorldSound :Cat {CAT['ball_clack']} :Loc (Transformation|GetActorLocation :self P))
    {NEAR_SAY('(Transformation|GetActorLocation :self P)', REACT['ball'], 0.9)}
    (Development|PrintString :InString (cat "GW: pickup ball by " (CallFunction|NameOf :P Who) " balls=" {PS_('Balls')}) :bPrintToScreen false)
    (else
      (GW|Set|BP_GW_PlayerState|HasSword :self ps :HasSword true)
      (CallFunction|WorldSound :Cat {CAT['sword_swish']} :Loc (Transformation|GetActorLocation :self P))
      {NEAR_SAY('(Transformation|GetActorLocation :self P)', REACT['sword'], 0.8)}
      (Development|PrintString :InString (cat "GW: pickup sword by " (CallFunction|NameOf :P Who)) :bPrintToScreen false)
      (CallFunction|SyncSword :PS ps))))
''',
    # the ball leaves the right hand towards what the crosshair points at
    'ThrowBall': f'''
(fn ThrowBall (Thrower Dir)
  (bind cam (Transformation|GetWorldLocation :self (GW|Get|BP_GW_Character|FollowCamera :self Thrower)))
  (bind here (Transformation|GetActorLocation :self Thrower))
  (bind t0 (+ (Math|Float|Max(Float) (Math|Vector|DotProduct (- here cam) Dir) 0.0) 50.0))
  (bind far (+ cam (* Dir 6000.0)))
  (bind (hit ok) (Collision|LineTraceByProfile :Start (+ cam (* Dir t0)) :End far :ProfileName "BlockAll" :bTraceComplex false :bIgnoreSelf true))
  (bind (bBlock bInit hTime hDist hLoc hImpact hNormal hImpNormal hPhys hActor) (Collision|BreakHitResult hit))
  (bind aim (select ok hImpact far))
  (bind f2 (Math|Vector|Normalize (Math|Vector|MakeVector (.x Dir) (.y Dir) 0.0)))
  (bind start (+ here (+ (Math|Vector|MakeVector 0.0 0.0 45.0) (+ (* f2 45.0) (* (Math|Vector|MakeVector (- 0.0 (.y f2)) (.x f2) 0.0) 20.0)))))
  (CallFunction|LaunchBall :Thrower Thrower :Start start :Aim aim))
''',
    'LaunchBall': f'''
(fn LaunchBall (Thrower Start Aim)
  (bind b (Game|SpawnActorfromClass :Class "{TB}" :SpawnTransform (Math|Transform|MakeTransform :Location Start) :CollisionHandlingOverride "AlwaysSpawn"))
  (GW|Set|{TB}|Thrower :self b :Thrower Thrower)
  (GW|Set|{TB}|StartLoc :self b :StartLoc Start)
  (GW|Set|{TB}|Vel :self b :Vel (* (Math|Vector|Normalize (- Aim Start)) {BALL_SPEED}))
  (GW|Set|{TB}|Variant :self b :Variant (Math|Random|RandomIntegerinRange 0 {len(BALL_MATS) - 1}))
  (GW|Set|{TB}|Go :self b :Go 1)
  (CallFunction|WorldSound :Cat {CAT['sword_swish']} :Loc Start)
  (Development|PrintString :InString (cat "GW: ball thrown by " (CallFunction|NameOf :P Thrower) " towards " Aim) :bPrintToScreen false))
''',
    'BallHit': f'''
(fn BallHit (Thrower Other Where Dir)
  (CallFunction|WorldSound :Cat {CAT['ball_clack']} :Loc Where)
  (bind v (Utilities|Casting|CastToBP_GW_Character Other)
    (:then (CallFunction|WeaponHit :Attacker Thrower :Victim v :Dir Dir :Weapon 0))
    (:CastFailed
      (Development|PrintString :InString (cat "GW: ball hit " (Utilities|GetDisplayName :Object Other)) :bPrintToScreen false))))
''',
    # an NPC guest dies (the shop pays the kill), a detective loses 25 HP, other guest players are never hurt
    'WeaponHit': f'''
(fn WeaponHit (Attacker Victim Dir Weapon)
  (bind wname (select (== Weapon 0) "ball" "sword"))
  (if (== (GW|Get|BP_GW_Character|Kind :self Victim) 3)
    (CallFunction|RobotHurt :Victim Victim :Amount (select (== Weapon 0) 20.0 50.0) :Dir Dir)
    (return))
  (if (or (or (GW|Get|BP_GW_Character|IsDead :self Victim) (!= (GW|Get|BP_GW_Character|Kind :self Victim) 0)) (== Victim Attacker))
    (Development|PrintString :InString (cat "GW: " wname " hit ignored on " (Utilities|GetDisplayName :Object Victim)) :bPrintToScreen false)
    (return))
  (if (GW|Get|BP_GW_Character|IsSeeker :self Victim)
    (CallFunction|HurtCharacter :Victim Victim :Amount 25.0 :Impulse (* Dir 300.0) :Cause (select (== Weapon 0) "a été assommé d'une boule de billard" "a été pourfendu à l'épée"))
    (Development|PrintString :InString (cat "GW: " wname " hit detective " (CallFunction|NameOf :P Victim) " health=" (GW|Get|BP_GW_Character|Health :self Victim)) :bPrintToScreen false)
    (return))
  (if (Pawn|IsPlayerControlled :self Victim)
    (Development|PrintString :InString (cat "GW: " wname " hit guest player " (CallFunction|NameOf :P Victim) ": no effect") :bPrintToScreen false)
    (return))
  (Variables|GW|SetSwapLoc (Transformation|GetActorLocation :self Victim))
  (CallFunction|HurtCharacter :Victim Victim :Amount 1000.0 :Impulse (* Dir 700.0) :Cause "")
  (CallFunction|StartPanic :Loc (Variables|GW|GetSwapLoc) :Dur 12.0)
  (CallFunction|RewardNPCKill :Killer Attacker :Victim Victim)
  (Development|PrintString :InString (cat "GW: " wname " killed NPC " (Utilities|GetDisplayName :Object Victim) " by " (CallFunction|NameOf :P Attacker)) :bPrintToScreen false))
''',
    # who the sword reaches: NPC guests and detectives in a 2 m cone in front, nearest first, not through a wall
    'SlashTarget': f'''
(fn SlashTarget (Attacker Dir)
  (Variables|Default|SetBestD 1000000.0)
  (Variables|Default|SetBestT (Variables|GW|GetNoChar))
  (bind here (Transformation|GetActorLocation :self Attacker))
  (bind f2 (Math|Vector|Normalize (Math|Vector|MakeVector (.x Dir) (.y Dir) 0.0)))
  (for c (Actor|GetAllActorsOfClass :ActorClass {CHAR})
    (if (and (and (!= c Attacker) (not (GW|Get|BP_GW_Character|IsDead :self c))) (or (== (GW|Get|BP_GW_Character|Kind :self c) 3) (and (== (GW|Get|BP_GW_Character|Kind :self c) 0) (or (not (Pawn|IsPlayerControlled :self c)) (GW|Get|BP_GW_Character|IsSeeker :self c)))))
      (bind cl (Transformation|GetActorLocation :self c))
      (bind d (Math|Vector|Distance2D(Vector) cl here))
      (bind dz (- (.z cl) (.z here)))
      (if (and (and (< d {SLASH_RANGE}) (< (* dz dz) 14400.0)) (and (< d (Variables|Default|GetBestD)) (>= (Math|Vector|DotProduct f2 (Math|Vector|Normalize (Math|Vector|MakeVector (- (.x cl) (.x here)) (- (.y cl) (.y here)) 0.0))) {SLASH_COS})))
        (Variables|Default|SetBestD d)
        (Variables|Default|SetBestT c))))
  (bind t (Variables|Default|GetBestT))
  (if (not ({ISVALID} :Object t))
    (return t))
  (bind tl (Transformation|GetActorLocation :self t))
  (bind to (Math|Vector|Normalize (- tl here)))
  (bind (hit ok) (Collision|LineTraceByChannel :Start (+ (+ here (Math|Vector|MakeVector 0.0 0.0 40.0)) (* to 40.0)) :End (+ tl (Math|Vector|MakeVector 0.0 0.0 30.0)) :TraceChannel "Visibility" :bTraceComplex false :bIgnoreSelf true))
  (bind (bBlock bInit hTime hDist hLoc hImpact hNormal hImpNormal hPhys hActor) (Collision|BreakHitResult hit))
  (if (and ok (and (!= hActor t) (!= hActor Attacker)))
    (return (Variables|GW|GetNoChar)))
  (return t))
''',
    'Slash': f'''
(fn Slash (Attacker Dir)
  (bind ps (CallFunction|PSOf :P Attacker))
  (if ({ISVALID} :Object ps)
    (bind hsw (GW|Get|BP_GW_PlayerState|SwordActor :self ps))
    (if ({ISVALID} :Object hsw)
      (GW|Set|{HS}|SlashCount :self hsw :SlashCount (+ (GW|Get|{HS}|SlashCount :self hsw) 1))))
  (CallFunction|WorldSound :Cat {CAT['sword_swish']} :Loc (Transformation|GetActorLocation :self Attacker))
  (Variables|GW|SetSlashVictim (CallFunction|SlashTarget :Attacker Attacker :Dir Dir))
  (bind v (Variables|GW|GetSlashVictim))
  (if ({ISVALID} :Object v)
    (CallFunction|WorldSound :Cat {CAT['sword_hit']} :Loc (Transformation|GetActorLocation :self v))
    (CallFunction|WeaponHit :Attacker Attacker :Victim v :Dir Dir :Weapon 1)
    (else
      (Development|PrintString :InString (cat "GW: sword slash by " (CallFunction|NameOf :P Attacker) " hit nobody") :bPrintToScreen false))))
''',
    # the post-it: a random guest spot (NPC spawn marker + a step on the navmesh), on the floor, not in the cloakroom
    # nor on the stage; the old one goes away
    'PlacePostIt': f'''
(fn PlacePostIt ()
  (for p (Actor|GetAllActorsOfClass :ActorClass "{PK}")
    (if (== ({P('Kind')} :self p) 2)
      (Actor|DestroyActor :self p)))
  (bind pts (Actor|GetAllActorswithTag :Tag "GW_NPCSpawn"))
  (if (== (Utilities|Array|Length pts) 0)
    (return))
  (Variables|GW|SetPostTries 0)
  (Variables|GW|SetPostOK false)
  (while (and (not (Variables|GW|GetPostOK)) (< (Variables|GW|GetPostTries) 16))
    (Variables|GW|SetPostTries (+ (Variables|GW|GetPostTries) 1))
    (bind (np nok) (AI|Navigation|GetRandomReachablePointinRadius :Origin (Transformation|GetActorLocation :self (Utilities|Array|Get(acopy) pts (Math|Random|RandomIntegerinRange 0 (- (Utilities|Array|Length pts) 1)))) :Radius 180.0))
    (if nok
      (Variables|GW|SetPostSpot np)
      (bind sp (Variables|GW|GetPostSpot))
      (if (not (or {inrect(CLOAK, 'sp')} {inrect(STAGE, 'sp')}))
        (bind (fh fok) (Collision|LineTraceByChannel :Start (+ sp (Math|Vector|MakeVector 0.0 0.0 100.0)) :End (- sp (Math|Vector|MakeVector 0.0 0.0 200.0)) :TraceChannel "Visibility" :bTraceComplex true :bIgnoreSelf true))
        (bind (fb fi ft fd fl fImpact fn2 fin fp fa) (Collision|BreakHitResult fh))
        (if fok
          (Variables|GW|SetPostSpot (+ fImpact (Math|Vector|MakeVector 0.0 0.0 0.2)))
          (Variables|GW|SetPostOK true)))))
  (if (Variables|GW|GetPostOK)
    (CallFunction|SpawnPickup :Kind 2 :Slot 20 :Variant 0 :Loc (Variables|GW|GetPostSpot) :Rot (Math|Rotator|MakeRotator :Roll 0.0 :Pitch 0.0 :Yaw (Math|Random|RandomFloatinRange -180.0 180.0)))
    (Development|PrintString :InString (cat "GW: post-it at " (Variables|GW|GetPostSpot) " code " (Variables|GW|GetSafeCode)) :bPrintToScreen false)))
''',
    'OpenSafe': f'''
(fn OpenSafe (P Who)
  (bind ps (CallFunction|PSOf :P Who))
  (if (or ({P('Taken')} :self P) (not ({ISVALID} :Object ps)))
    (return))
  {SET_PK('Taken', 'true', 'P')}
  {SET_PK('BackAt', '100000000.0', 'P')}
  (CallFunction|ShopPay :PS ps :Amount {SAFE_MONEY} :Note "Coffre-fort ouvert : +{SAFE_MONEY} $")
  (CallFunction|WorldSound :Cat {CAT['safe_open']} :Loc (+ (Transformation|GetActorLocation :self P) (Math|Vector|MakeVector 0.0 0.0 60.0)))
  {NEAR_SAY('(Transformation|GetActorLocation :self P)', REACT['safe'], 1.6, 900.0)}
  (Development|PrintString :InString (cat "GW: safe opened by " (CallFunction|NameOf :P Who)) :bPrintToScreen false))
''',
    'PullAlarm': f'''
(fn PullAlarm (P Who)
  (for q (Actor|GetAllActorsOfClass :ActorClass "{PK}")
    (if (and (== ({P('Kind')} :self q) 4) ({P('Taken')} :self q))
      (return)))
  {SET_PK('Taken', 'true', 'P')}
  {SET_PK('BackAt', '100000000.0', 'P')}
  {SET_PK('RingUntil', '(+ (CallFunction|Now) 10.0)', 'P')}
  {ALARM_PANIC}
  (CallFunction|SayNearPlayers :Cat {REACT['alarm']} :PerPlayer 1 :Delay 2.5 :Spread 1.5)
  (Development|PrintString :InString (cat "GW: fire alarm pulled by " (CallFunction|NameOf :P Who)) :bPrintToScreen false))
''',
    'Fart': f'''
(fn Fart (P Who)
  (CallFunction|WorldSound :Cat {CAT['fart']} :Loc (+ (Transformation|GetActorLocation :self P) (Math|Vector|MakeVector 0.0 0.0 50.0)))
  {FART_REACT}
  (Development|PrintString :InString (cat "GW: fart by " (CallFunction|NameOf :P Who)) :bPrintToScreen false))
''',
    'SwapStart': f'''
(fn SwapStart (Old Target)
  (bind ps (CallFunction|PSOf :P Old))
  (if ({ISVALID} :Object ps)
    (GW|Set|BP_GW_PlayerState|SwapReadyAt :self ps :SwapReadyAt (+ (CallFunction|Now) {SWAP_RELOAD})))
  ; the target stops being an NPC: no brain, no motion
  (bind ai (Utilities|Casting|CastToAIController (Pawn|GetController :self Target))
    (:then
      (Pawn|UnPossess :self ai)
      ; DestroyActor on a controller does nothing here (see Zombify, s40_events2.py): a life span ends it
      (Actor|SetLifeSpan :self ai :InLifespan 0.1)
      (CallFunction|SwapEffects :Old Old :Target Target))
    (:CastFailed
      (CallFunction|SwapEffects :Old Old :Target Target))))
''',
    'SwapEffects': f'''
(fn SwapEffects (Old Target)
  (Components|Movement|StopMovementImmediately :self (GW|Get|/Script/Engine.Character|CharacterMovement :self Target))
  (GW|Call|BP_GW_Character|SetSprint :self Target :On false)
  ; walking again before the possession (a body left in MOVE_None would stay stuck on its new owner's machine)
  (GW|Call|BP_GW_Character|SetFrozen :self Target :Frozen false)
  (Variables|GW|SetSwapLoc (Transformation|GetActorLocation :self Old))
  (bind from (Variables|GW|GetSwapLoc))
  (bind g (Game|SpawnActorfromClass :Class "{SG}" :SpawnTransform (Math|Transform|MakeTransform :Location from) :CollisionHandlingOverride "AlwaysSpawn"))
  (GW|Set|{SG}|FromLoc :self g :FromLoc from)
  (GW|Set|{SG}|ToLoc :self g :ToLoc (Transformation|GetActorLocation :self Target))
  (GW|Set|{SG}|Swapper :self g :Swapper Old)
  (GW|Set|{SG}|GhostMesh :self g :GhostMesh (Components|SkeletalMesh|GetSkeletalMeshAsset :self (GW|Get|/Script/Engine.Character|Mesh :self Old)))
  (bind oi (GW|Get|BP_GW_Character|OutfitIndex :self Old))
  (bind mats (GW|Get|BP_GW_Character|GenGhostMats :self Old))
  (if (or (GW|Get|BP_GW_Character|IsSeeker :self Old) (== oi 32))
    (GW|Set|{SG}|GhostMat :self g :GhostMat (GW|Get|BP_GW_Character|GenDetectiveGhostMat :self Old))
    (elif (and (>= oi 0) (< oi (Utilities|Array|Length mats)))
      (GW|Set|{SG}|GhostMat :self g :GhostMat (Utilities|Array|Get(acopy) mats oi))))
  (GW|Set|{SG}|Go :self g :Go 1)
  (CallFunction|WorldSound :Cat {CAT['swap_whoosh']} :Loc from)
  (CallFunction|SayNearPlayers :Cat {REACT['ghost']} :PerPlayer 1 :Delay 0.7 :Spread 1.5)
  ; the old body drops dead like any guest (no announcement: nothing tells it was a player)
  (CallFunction|DeathCry :Victim Old)
  (GW|Call|BP_GW_Character|Die :self Old :Impulse (Math|Vector|MakeVector 0.0 0.0 -60.0))
  (CallFunction|StartPanic :Loc from :Dur 8.0)
  (Utilities|Array|Add :TargetArray (Variables|GW|GetPendingNPCRespawns) :NewItem (+ (CallFunction|Now) (Variables|GW|GetNPCRespawnDelay)))
  (Development|PrintString :InString (cat "GW: swap " (CallFunction|NameOf :P Old) " leaves " (Utilities|GetDisplayName :Object Old) " for " (Utilities|GetDisplayName :Object Target)) :bPrintToScreen false))
''',
}
if get_graph(gm, 'ShopPay') is not None and not BT.find_nodes(get_graph(gm, 'ShopPay'))[1:]:
    print('note: ShopPay has no body yet (s34_shop.py writes it)')
if not SKIP_GM:
    import shop_items
    for name, code in GM_W.items():           # one compile at the end: the game mode takes ~15 s per compile
        if name in shop_items.S40_OWNS:
            continue
        write(gm, name, code, compile_after=False)
    compile_bp(gm)
    print('BP_GW_GameMode', node_problems(gm))
    save(gm)

# ---------------------------------------------------------------- bodies: player controller
GATE = lambda name: f'''  (if (not (CallFunction|DevOK))
    (Development|PrintString :InString (cat "GW: dev {name} refused for " (PlayerState|GetPlayerName :self (GW|Get|/Script/Engine.Controller|PlayerState)) " (server not started with -GWDev)") :bPrintToScreen false)
    (return))'''
WHO = '(PlayerState|GetPlayerName :self (GW|Get|/Script/Engine.Controller|PlayerState))'
LOG = lambda msg: f'(Development|PrintString :InString (cat "GW: " {WHO} " {msg}") :bPrintToScreen false)'
SEND = lambda local, remote: f'''(if (Networking|HasAuthority)
    {local}
    (else
      (Development|ExecuteConsoleCommand :Command {remote} :SpecificPlayer self)))'''
NICE_PICK = '(select (== (GW|Get|' + PK + '|Kind :self p) 0) "Prendre une boule de billard" "Voler l\'épée")'
_chv = [str(v) for v in BT.list_variables(load_bp('BP_GW_Character'))]
DANCE = ('      (GW|Set|BP_GW_Character|DanceId :self t :DanceId 0)\n      (GW|Set|BP_GW_Character|DanceByPlayer :self t :DanceByPlayer false)'
         if 'DanceId' in _chv and 'DanceByPlayer' in _chv else '      ; (s36 social: DanceId not there yet)')
_has_view = 'ViewFP' in _chv                         # s37_view.py (camera agent)
VIEWFP = '(GW|Get|BP_GW_Character|ViewFP :self ch)' if _has_view else 'false'
FPC = f'{FOLDER}/BP_GW_FPItems.BP_GW_FPItems_C'
PC_W = {
    'GuestOK': f'''
(fn GuestOK (Ch NeedHunt)
  (bind ps {PSC}
    (:then
      (bind s {GSC}
        (:then
          (bind phase (GW|Get|BP_GW_GameState|Phase :self s))
          (return (and (and (== (GW|Get|BP_GW_PlayerState|GWRole :self ps) 1) (GW|Get|BP_GW_PlayerState|IsAlive :self ps)) (and (and (not (GW|Get|BP_GW_Character|IsDead :self Ch)) (not (GW|Get|BP_GW_Character|IsSeeker :self Ch))) (select NeedHunt (== phase 2) (or (== phase 1) (== phase 2)))))))
        (:CastFailed (return false))))
    (:CastFailed (return false))))
''',
    # nearest thing E can use here, by kind: 0 ball / 1 sword / 2 post-it / 3 safe (guests), 4 fire alarm (any living
    # player, once per game, during a round), 5 toilet (any living player)
    'NearPickupFor': f'''
(fn NearPickupFor (Ch)
  (Variables|Default|SetBestD 1000.0)
  (Variables|Default|SetBestP (Variables|GW|GetNoPickup))
  (bind ps {PSC}
    (:then
      (bind s {GSC}
        (:then
          (bind phase (GW|Get|BP_GW_GameState|Phase :self s))
          (bind rnd (GW|Get|BP_GW_GameState|RoundNumber :self s))
          (bind guest (CallFunction|GuestOK :Ch Ch :NeedHunt false))
          (bind alive (CallFunction|PlayerOK :Ch Ch))
          (bind here (Transformation|GetActorLocation :self Ch))
          (bind balls {PS_('Balls')})
          (bind sword {PS_('HasSword')})
          (bind known (== (Variables|GW|GetKnownRound) rnd))
          (Variables|GW|SetAlarmGone false)
          (for q (Actor|GetAllActorsOfClass :ActorClass "{PK}")
            (if (and (== ({P('Kind')} :self q) 4) ({P('Taken')} :self q))
              (Variables|GW|SetAlarmGone true)))
          (for p (Actor|GetAllActorsOfClass :ActorClass "{PK}")
            (bind k ({P('Kind')} :self p))
            (bind tk ({P('Taken')} :self p))
            (bind pl (Transformation|GetActorLocation :self p))
            (bind d (Math|Vector|Distance2D(Vector) pl here))
            (bind dz (- (.z pl) (.z here)))
            (bind reach (select (== k 2) 130.0 (select (== k 4) 140.0 (select (== k 5) 160.0 {REACH}))))
            (bind ok (select (== k 0) (and guest (and (not tk) (< balls 2))) (select (== k 1) (and guest (and (not tk) (not sword))) (select (== k 2) (and guest (not known)) (select (== k 3) (and guest (not tk)) (select (== k 4) (and alive (and (not (Variables|GW|GetAlarmGone)) (or (== phase 1) (== phase 2)))) alive))))))
            (if (and ok (and (< d reach) (and (< (* dz dz) 22500.0) (< d (Variables|Default|GetBestD)))))
              (Variables|Default|SetBestD d)
              (Variables|Default|SetBestP p)))
          (return (Variables|Default|GetBestP)))
        (:CastFailed (return (Variables|Default|GetBestP)))))
    (:CastFailed (return (Variables|Default|GetBestP)))))
''',
    'PlayerOK': f'''
(fn PlayerOK (Ch)
  (bind ps {PSC}
    (:then (return (and {PS_('IsAlive')} (not (GW|Get|BP_GW_Character|IsDead :self Ch)))))
    (:CastFailed (return false))))
''',
    'KnowsCode': f'''
(fn KnowsCode ()
  (bind s {GSC}
    (:then (return (and (> (Variables|GW|GetKnownRound) 0) (== (Variables|GW|GetKnownRound) (GW|Get|BP_GW_GameState|RoundNumber :self s)))))
    (:CastFailed (return false))))
''',
    'PromptLabel': f'''
(fn PromptLabel (P)
  (bind kc (CallFunction|KnowsCode))
  (bind k ({P('Kind')} :self P))
  (if (== k 0)
    (return "Prendre une boule de billard"))
  (if (== k 1)
    (return "Voler l'épée"))
  (if (== k 2)
    (return "Lire le post-it"))
  (if (== k 3)
    (return (select kc (cat "Ouvrir le coffre (code " (Variables|GW|GetKnownCode) ")") "Coffre-fort verrouillé (il faut le code)")))
  (if (== k 4)
    (return "Tirer l'alarme incendie"))
  (return "Péter (très fort)"))
''',
    'AlarmRinging': f'''
(fn AlarmRinging ()
  (bind now {SNOW})
  (for q (Actor|GetAllActorsOfClass :ActorClass "{PK}")
    (if (and (== ({P('Kind')} :self q) 4) (> ({P('RingUntil')} :self q) now))
      (return true)))
  (return false))
''',
    # E (InteractOther, s33): handled when something usable is in reach; the server checks it again (GWPickup)
    'TryPickup': f'''
(fn TryPickup ()
  (bind ch {MYCH}
    (:then
      (bind p (CallFunction|NearPickupFor :Ch ch))
      (if (not ({ISVALID} :Object p))
        (return false))
      (if (and (== ({P('Kind')} :self p) 3) (not (CallFunction|KnowsCode)))
        (CallFunction|PickupNotice :Msg "Le coffre est verrouillé : il faut le code. Un post-it traîne quelque part dans le manoir…")
        (return true))
      {SEND('(CallFunction|GWPickup)', '"ServerExec GWPickup"')}
      (return true))
    (:CastFailed (return false))))
''',
    'GWPickup': f'''
(fn GWPickup ()
  (bind ch {MYCH}
    (:then
      (bind p (CallFunction|NearPickupFor :Ch ch))
      (if (not ({ISVALID} :Object p))
        {LOG('E refused (nothing usable in reach)')}
        (return))
      (bind k ({P('Kind')} :self p))
      (bind gm {GMC}
        (:then
          (if (<= k 1)
            (GW|Call|BP_GW_GameMode|TakePickup :self gm :P p :Who ch)
            (return))
          (if (== k 2)
            (Variables|GW|SetKnownCode (GW|Get|BP_GW_GameMode|SafeCode :self gm))
            (Variables|GW|SetKnownRound (GW|Get|BP_GW_GameState|RoundNumber :self (GW|Call|BP_GW_GameMode|GetGS :self gm)))
            ; every read counts, the card opens on the owner's screen each time (s40_pc.py PickupNotices)
            (Variables|GW|SetPostReads (+ (Variables|GW|GetPostReads) 1))
            {LOG('read the safe code on the post-it')}
            (return))
          (if (== k 3)
            (if (CallFunction|KnowsCode)
              (GW|Call|BP_GW_GameMode|OpenSafe :self gm :P p :Who ch)
              (else
                {LOG('safe refused (does not know the code)')}))
            (return))
          (if (== k 4)
            (GW|Call|BP_GW_GameMode|PullAlarm :self gm :P p :Who ch)
            (return))
          (if (>= (GW|Call|BP_GW_GameMode|Now :self gm) (Variables|GW|GetNextFartAt))
            (Variables|GW|SetNextFartAt (+ (GW|Call|BP_GW_GameMode|Now :self gm) 5.0))
            (GW|Call|BP_GW_GameMode|Fart :self gm :P p :Who ch)))
        (:CastFailed)))
    (:CastFailed)))
''',
    # left click of a guest without gun ammo (s34_shop.py calls it): local or server, the server decides
    'GuestAttack': f'''
(fn GuestAttack (Ch)
  (bind rot (Pawn|GetControlRotation :self self))
  {SEND('(CallFunction|GWGuestAttack :Pitch (.pitch rot) :Yaw (.yaw rot))', '(cat "ServerExec GWGuestAttack " (.pitch rot) " " (.yaw rot))')})
''',
    # client aim is fresher than the server's copy of the view; trusted within ~10 degrees (as GWFire)
    'AimDir': '''
(fn AimDir (Pitch Yaw)
  (bind srv (Math|Vector|GetForwardVector (Pawn|GetControlRotation :self self)))
  (bind cli (Math|Vector|GetForwardVector (Math|Rotator|MakeRotator :Roll 0.0 :Pitch Pitch :Yaw Yaw)))
  (return (select (>= (Math|Vector|DotProduct srv cli) 0.985) cli srv)))
''',
    'GWGuestAttack': f'''
(fn GWGuestAttack (Pitch Yaw)
  (bind ch {MYCH}
    (:then
      (bind ps {PSC}
        (:then
          (bind gm {GMC}
            (:then
              (bind now (GW|Call|BP_GW_GameMode|Now :self gm))
              (if (not (CallFunction|GuestOK :Ch ch :NeedHunt true))
                {LOG('attack refused (not a living guest in the hunt)')}
                (return))
              (if (< now (Variables|GW|GetNextAttackAt))
                (return))
              (bind dir (CallFunction|AimDir :Pitch Pitch :Yaw Yaw))
              (bind sword {PS_('HasSword')})
              (bind balls {PS_('Balls')})
              (if (and sword (or (== balls 0) ({ISVALID} :Object (GW|Call|BP_GW_GameMode|SlashTarget :self gm :Attacker ch :Dir dir))))
                (Variables|GW|SetNextAttackAt (+ now 0.7))
                (GW|Call|BP_GW_GameMode|Slash :self gm :Attacker ch :Dir dir)
                (return))
              (if (> balls 0)
                (Variables|GW|SetNextAttackAt (+ now 0.5))
                (GW|Set|BP_GW_PlayerState|Balls :self ps :Balls (- balls 1))
                (GW|Call|BP_GW_GameMode|ThrowBall :self gm :Thrower ch :Dir dir)
                (return))
              {LOG('attack: no ball, no sword')})
            (:CastFailed)))
        (:CastFailed)))
    (:CastFailed)))
''',
    'SwapCast': f'''
(fn SwapCast (Ch A)
  (bind t (Utilities|Casting|CastToBP_GW_Character A)
    (:then
      (if (not (and (and (and (!= t Ch) (not (Pawn|IsPlayerControlled :self t))) (and (not (GW|Get|BP_GW_Character|IsDead :self t)) (== (GW|Get|BP_GW_Character|Kind :self t) 0))) (and (not (GW|Get|BP_GW_Character|IsSeeker :self t)) (<= (Math|Vector|Distance(Vector) (Transformation|GetActorLocation :self t) (Transformation|GetActorLocation :self Ch)) {SWAP_RANGE}))))
        (return (Variables|Default|GetNoT)))
      ; only an ordinary guest led by the NPC brain (not the barman, not a body already being taken)
      (bind nc (Utilities|Casting|CastToBP_GW_NPCController (Pawn|GetController :self t))
        (:then (return t))
        (:CastFailed (return (Variables|Default|GetNoT)))))
    (:CastFailed (return (Variables|Default|GetNoT)))))
''',
    # the NPC in the crosshair: a ray from the camera, then a 35 cm wide sweep for a near miss
    'SwapTargetFor': f'''
(fn SwapTargetFor (Ch Dir)
  (bind cam (Transformation|GetWorldLocation :self (GW|Get|BP_GW_Character|FollowCamera :self Ch)))
  (bind t0 (+ (Math|Float|Max(Float) (Math|Vector|DotProduct (- (Transformation|GetActorLocation :self Ch) cam) Dir) 0.0) 45.0))
  (bind a (+ cam (* Dir t0)))
  (bind b (+ cam (* Dir {SWAP_RANGE + 400.0})))
  (bind (hit ok) (Collision|LineTraceByProfile :Start a :End b :ProfileName "BlockAll" :bTraceComplex false :bIgnoreSelf true))
  (bind (bBlock bInit hTime hDist hLoc hImpact hNormal hImpNormal hPhys hActor) (Collision|BreakHitResult hit))
  (bind t1 (CallFunction|SwapCast :Ch Ch :A hActor))
  (if ({ISVALID} :Object t1)
    (return t1))
  (bind (sh sok) (Collision|SphereTraceByProfile :Start a :End b :Radius 35.0 :ProfileName "BlockAll" :bTraceComplex false :bIgnoreSelf true))
  (bind (sBlock sInit sTime sDist sLoc sImpact sNormal sImpNormal sPhys sActor) (Collision|BreakHitResult sh))
  (bind t2 (CallFunction|SwapCast :Ch Ch :A sActor))
  (Variables|GW|SetSwapDbg (cat (cat (Utilities|GetDisplayName :Object hActor) " / ") (Utilities|GetDisplayName :Object sActor)))
  (return t2))
''',
    # R: the body-swap gun (s34 sells it); feedback here, the server checks everything again
    'RequestSwap': f'''
(fn RequestSwap ()
  (bind ps {PSC}
    (:then
      (if (not {PS_('HasSwapGun')})
        (return))
      (bind left (- {PS_('SwapReadyAt')} {SNOW}))
      (if (> left 0.0)
        (CallFunction|PickupNotice :Msg (cat "Pistolet d'échange : prêt dans " (Math|Float|Round left) " s."))
        (return))
      (bind rot (Pawn|GetControlRotation :self self))
      {SEND('(CallFunction|GWSwap :Pitch (.pitch rot) :Yaw (.yaw rot))', '(cat "ServerExec GWSwap " (.pitch rot) " " (.yaw rot))')})
    (:CastFailed)))
''',
    'GWSwap': f'''
(fn GWSwap (Pitch Yaw)
  (bind ch {MYCH}
    (:then
      (bind ps {PSC}
        (:then
          (bind gm {GMC}
            (:then
              (if (not (CallFunction|GuestOK :Ch ch :NeedHunt false))
                {LOG('swap refused (not a living guest)')}
                (return))
              (if (not {PS_('HasSwapGun')})
                {LOG('swap refused (no swap gun)')}
                (return))
              (if (< (GW|Call|BP_GW_GameMode|Now :self gm) {PS_('SwapReadyAt')})
                {LOG('swap refused (recharging)')}
                (return))
              (if ({ISVALID} :Object (Variables|GW|GetSwapTarget))
                {LOG('swap refused (already swapping)')}
                (return))
              (bind t (CallFunction|SwapTargetFor :Ch ch :Dir (CallFunction|AimDir :Pitch Pitch :Yaw Yaw)))
              (if (not ({ISVALID} :Object t))
                (Development|PrintString :InString (cat (cat "GW: " {WHO}) (cat " swap: no guest in the crosshair (ray / sweep hit: " (cat (Variables|GW|GetSwapDbg) ")"))) :bPrintToScreen false)
                (return))
              (Variables|GW|SetSwapTarget t)
              (Variables|GW|SetSwapOld ch)
              (GW|Call|BP_GW_GameMode|SwapStart :self gm :Old ch :Target t)
              (Utilities|Time|SetTimerbyFunctionName :Object self :FunctionName "SwapFinish" :Time {SWAP_FLY} :bLooping false))
            (:CastFailed)))
        (:CastFailed)))
    (:CastFailed)))
''',
    # 1 s later: the player takes the new body (or becomes a ghost if it died meanwhile)
    'SwapFinish': f'''
(fn SwapFinish ()
  (Variables|Default|SetT2 (Variables|GW|GetSwapTarget))
  (Variables|Default|SetO2 (Variables|GW|GetSwapOld))
  (Variables|GW|SetSwapTarget (Variables|GW|GetNoSwapChar))
  (Variables|GW|SetSwapOld (Variables|GW|GetNoSwapChar))
  (bind t (Variables|Default|GetT2))
  (bind old (Variables|Default|GetO2))
  (if (or (not ({ISVALID} :Object old)) (!= (Pawn|GetControlledPawn :self self) old))
    {LOG('swap aborted (the pawn changed meanwhile)')}
    (return))
  (bind gm {GMC}
    (:then
      ; (t is checked first on its own: BP evaluates both sides of an or)
      (Variables|Default|SetLost true)
      (if ({ISVALID} :Object t)
        (Variables|Default|SetLost (or (GW|Get|BP_GW_Character|IsDead :self t) ({ISVALID} :Object (Pawn|GetController :self t)))))
      (if (Variables|Default|GetLost)
        {LOG('swap failed (the new body is gone): ghost')}
        (GW|Call|BP_GW_GameMode|KillPlayer :self gm :Victim old :Impulse (Math|Vector|MakeVector 0.0 0.0 0.0))
        (GW|Call|BP_GW_GameMode|UpdateCounts :self gm)
        (return))
      (Pawn|Possess :self self :InPawn t)
      (GW|Set|BP_GW_Character|Health :self t :Health (GW|Get|BP_GW_Character|Health :self old))
      (GW|Call|BP_GW_Character|SetFrozen :self t :Frozen false)
      (GW|Call|BP_GW_Character|SetSprint :self t :On false)
      (Animation|StopAnimMontage :self t)
{DANCE}
      (GW|Call|BP_GW_GameMode|UpdateCounts :self gm)
      (Development|PrintString :InString (cat "GW: swap done: " {WHO} " now controls " (Utilities|GetDisplayName :Object t) " (old body " (Utilities|GetDisplayName :Object old) " dead=" (GW|Get|BP_GW_Character|IsDead :self old) ")") :bPrintToScreen false))
    (:CastFailed)))
''',
    'PickupNotice': f'''
(fn PickupNotice (Msg)
  (bind hud (Variables|GW|GetHUDWidget))
  (if ({ISVALID} :Object hud)
    (GW|Set|{HUD}|LocalNotice :self hud :LocalNotice Msg)
    (GW|Set|{HUD}|LocalNoticeTime :self hud :LocalNoticeTime (Utilities|Time|GetRealTimeSeconds)))
  (Development|PrintString :InString (cat "GW: notice " Msg) :bPrintToScreen false))
''',
    # what changed in my inventory since the last tick -> a line on the HUD; my pawn changing (swap) -> log
    'PickupNotices': f'''
(fn PickupNotices ()
  (bind ps {PSC}
    (:then
      (bind b {PS_('Balls')})
      (if (!= b (Variables|GW|GetSeenBalls))
        (if (> b (Variables|GW|GetSeenBalls))
          (CallFunction|PickupNotice :Msg (cat "Boule de billard en poche (" b "/2) : clic gauche pour la lancer.")))
        (Variables|GW|SetSeenBalls b))
      (bind sw {PS_('HasSword')})
      (if (!= sw (Variables|GW|GetSeenSword))
        (if sw
          (CallFunction|PickupNotice :Msg "Épée volée ! Clic gauche pour frapper. Attention : tout le monde la voit."))
        (Variables|GW|SetSeenSword sw))
      (bind now {SNOW})
      (bind gun {PS_('HasSwapGun')})
      (bind ready (and gun (>= now {PS_('SwapReadyAt')})))
      (if (!= ready (Variables|GW|GetSeenSwapReady))
        (if ready
          (CallFunction|PickupNotice :Msg "Pistolet d'échange prêt : visez un invité et appuyez sur R.")
          (elif gun
            (CallFunction|PickupNotice :Msg (cat "Pistolet d'échange : rechargement (" (Math|Float|Round (- {PS_('SwapReadyAt')} now)) " s)."))))
        (Variables|GW|SetSeenSwapReady ready))
      (if (!= (Variables|GW|GetKnownRound) (Variables|GW|GetSeenKnownRound))
        (Variables|GW|SetSeenKnownRound (Variables|GW|GetKnownRound))
        (if (CallFunction|KnowsCode)
          (CallFunction|PickupNotice :Msg (cat "Le post-it dit : code du coffre " (Variables|GW|GetKnownCode) ". Le coffre-fort est dans le bureau."))))
      (bind p (Pawn|GetControlledPawn :self self))
      (if (!= p (Variables|GW|GetSeenPawn))
        (Variables|GW|SetSeenPawn p)
        (Development|PrintString :InString (cat "GW[" (select (Networking|HasAuthority) "host" "client") "] pawn now " (Utilities|GetDisplayName :Object p)) :bPrintToScreen false)))
    (:CastFailed)))
''',
    # first person (s37 BP_GW_Character.ViewFP): the stolen sword / a ball in front of the camera, only here; the sword
    # chops when my held sword (the replicated one everybody else sees) slashes
    'FPItemsTick': f'''
(fn FPItemsTick ()
  (Variables|GW|SetFPOn false)
  (bind fpi (Variables|GW|GetFPItems))
  (bind ch {MYCH}
    (:then
      (bind ps {PSC}
        (:then
          (bind sw {PS_('HasSword')})
          (bind ball (> {PS_('Balls')} 0))
          (Variables|GW|SetFPOn (and {VIEWFP} (and (or sw ball) (not (GW|Get|BP_GW_Character|IsDead :self ch)))))
          (if (not (Variables|GW|GetFPOn))
            (if ({ISVALID} :Object fpi)
              (Rendering|SetActorHiddenInGame :self fpi :bNewHidden true))
            (return))
          (if (not ({ISVALID} :Object fpi))
            (Variables|GW|SetFPItems (Game|SpawnActorfromClass :Class "{FPC}" :SpawnTransform (Math|Transform|MakeTransform) :CollisionHandlingOverride "AlwaysSpawn")))
          (bind f (Variables|GW|GetFPItems))
          (bind cam (GW|Get|BP_GW_Character|FollowCamera :self ch))
          (if (!= (Variables|GW|GetFPAttach) ch)
            (Variables|GW|SetFPAttach ch)
            (Transformation|AttachActorToComponent :self f :Parent cam :SocketName "None" :LocationRule "SnapToTarget" :RotationRule "SnapToTarget" :ScaleRule "KeepWorld" :bWeldSimulatedBodies false))
          (Rendering|SetActorHiddenInGame :self f :bNewHidden false)
          (Rendering|SetVisibility :self (GW|Get|{FPC}|SwordRoot :self f) :bNewVisibility sw :bPropagateToChildren true)
          (Rendering|SetVisibility :self (GW|Get|{FPC}|Ball :self f) :bNewVisibility (and ball (not sw)) :bPropagateToChildren false)
          (for h (Actor|GetAllActorsOfClass :ActorClass "{HS}")
            (if (== (GW|Get|{HS}|Holder :self h) ch)
              (if (!= (GW|Get|{HS}|SlashCount :self h) (GW|Get|{FPC}|SeenSlash :self f))
                (GW|Set|{FPC}|SeenSlash :self f :SeenSlash (GW|Get|{HS}|SlashCount :self h))
                (GW|Call|{FPC}|StartSwing :self f)))))
        (:CastFailed)))
    (:CastFailed
      (if ({ISVALID} :Object fpi)
        (Rendering|SetActorHiddenInGame :self fpi :bNewHidden true)))))
''',
    # "Au feu !" pulled by someone: the fire bell rings here too (2D, every client), 10 s
    'AlarmClientTick': f'''
(fn AlarmClientTick ()
  (bind ring (CallFunction|AlarmRinging))
  (if (== ring (Variables|GW|GetAlarmOn))
    (return))
  (Variables|GW|SetAlarmOn ring)
  (if (not ring)
    (if ({ISVALID} :Object (Variables|GW|GetPullAlarmComp))
      (GW|Call|/Script/Engine.AudioComponent|FadeOut :self (Variables|GW|GetPullAlarmComp) :FadeOutDuration 1.5 :FadeVolumeLevel 0.0))
    (Variables|GW|SetPullAlarmComp (Variables|GW|GetNoAlarmComp))
    (Development|PrintString :InString "GW: fire alarm bell stops here" :bPrintToScreen false)
    (return))
  (Development|PrintString :InString "GW: fire alarm bell rings here" :bPrintToScreen false)
  (bind s {GSC}
    (:then (Variables|GW|SetPullAlarmComp (Audio|SpawnSound2D :Sound (GW|Get|BP_GW_GameState|FireAlarm :self s) :VolumeMultiplier 0.4)))
    (:CastFailed)))
''',
    'PickupClientTick': f'''
(fn PickupClientTick ()
  (if (not (Pawn|IsLocalPlayerController))
    (return))
  (CallFunction|PickupNotices)
  (CallFunction|AlarmClientTick)
  (CallFunction|FPItemsTick)
  (Variables|GW|SetPromptFor (Variables|GW|GetNoPickup))
  (bind ch {MYCH}
    (:then
      (Variables|GW|SetPromptFor (CallFunction|NearPickupFor :Ch ch))
      (bind p (Variables|GW|GetPromptFor))
      (bind kp (Variables|GW|GetPickupPrompt))
      (if ({ISVALID} :Object p)
        (if (not ({ISVALID} :Object kp))
          (Variables|GW|SetPickupPrompt (Game|SpawnActorfromClass :Class "/Game/GW/Blueprints/BP_GW_KeyPrompt.BP_GW_KeyPrompt_C" :SpawnTransform (Math|Transform|MakeTransform :Location (Transformation|GetActorLocation :self p)) :CollisionHandlingOverride "AlwaysSpawn")))
        (bind k (GW|Get|{PK}|Kind :self p))
        (GW|Call|BP_GW_KeyPrompt|SetPrompt :self kp :Key "E" :Label (CallFunction|PromptLabel :P p))
        (Transformation|SetActorLocation :self kp :NewLocation (+ (Transformation|GetActorLocation :self p) (Math|Vector|MakeVector 0.0 0.0 (select (== k 0) 40.0 (select (== k 1) 25.0 (select (== k 3) 125.0 (select (== k 5) 100.0 (select (== k 4) -22.0 30.0))))))) :bSweep false :bTeleport true)
        (GW|Call|BP_GW_KeyPrompt|ShowPrompt :self kp :On true)
        (return))
      (if ({ISVALID} :Object kp)
        (GW|Call|BP_GW_KeyPrompt|ShowPrompt :self kp :On false)))
    (:CastFailed
      (if ({ISVALID} :Object (Variables|GW|GetPickupPrompt))
        (GW|Call|BP_GW_KeyPrompt|ShowPrompt :self (Variables|GW|GetPickupPrompt) :On false)))))
''',
    # ---------------- dev menu (u15 page Joueur) and tests
    'GWDevGiveBall': f'''
(fn GWDevGiveBall ()
{GATE('giveball')}
  (bind ps {PSC}
    (:then
      (GW|Set|BP_GW_PlayerState|Balls :self ps :Balls (Math|Integer|Min(Integer) (+ {PS_('Balls')} 1) 2))
      {LOG('dev: ball given')})
    (:CastFailed)))
''',
    'GWDevGiveSword': f'''
(fn GWDevGiveSword ()
{GATE('givesword')}
  (bind ps {PSC}
    (:then
      (GW|Set|BP_GW_PlayerState|HasSword :self ps :HasSword true)
      {LOG('dev: sword given')}
      (bind gm {GMC}
        (:then (GW|Call|BP_GW_GameMode|SyncSword :self gm :PS ps))
        (:CastFailed)))
    (:CastFailed)))
''',
    'GWDevGiveSwap': f'''
(fn GWDevGiveSwap ()
{GATE('giveswap')}
  (bind ps {PSC}
    (:then
      (GW|Set|BP_GW_PlayerState|HasSwapGun :self ps :HasSwapGun true)
      (GW|Set|BP_GW_PlayerState|SwapReadyAt :self ps :SwapReadyAt 0.0)
      {LOG('dev: swap gun given (charged)')})
    (:CastFailed)))
''',
    'GWDevPickupSpawn': f'''
(fn GWDevPickupSpawn ()
{GATE('pickupspawn')}
  (bind gm {GMC}
    (:then
      (if (not (GW|Get|BP_GW_GameMode|PickupsOn :self gm))
        (GW|Call|BP_GW_GameMode|PickupSpawn :self gm)))
    (:CastFailed)))
''',
    'GWDevLearnCode': f'''
(fn GWDevLearnCode ()
{GATE('learncode')}
  (bind gm {GMC}
    (:then
      (Variables|GW|SetKnownCode (GW|Get|BP_GW_GameMode|SafeCode :self gm))
      (Variables|GW|SetKnownRound (GW|Get|BP_GW_GameState|RoundNumber :self (GW|Call|BP_GW_GameMode|GetGS :self gm)))
      (Development|PrintString :InString (cat "GW: dev safe code learnt: " (Variables|GW|GetKnownCode) " round " (Variables|GW|GetKnownRound)) :bPrintToScreen false))
    (:CastFailed)))
''',
    'GWDevAlarmReset': f'''
(fn GWDevAlarmReset ()
{GATE('alarmreset')}
  (for q (Actor|GetAllActorsOfClass :ActorClass "{PK}")
    (if (== ({P('Kind')} :self q) 4)
      {SET_PK('Taken', 'false', 'q')}
      {SET_PK('RingUntil', '0.0', 'q')}))
  {LOG('dev: fire alarm re-armed')})
''',
    'GWDevFart': f'''
(fn GWDevFart ()
{GATE('fart')}
  (bind ch {MYCH}
    (:then
      (bind gm {GMC}
        (:then
          (GW|Call|BP_GW_GameMode|WorldSound :self gm :Cat {CAT['fart']} :Loc (Transformation|GetActorLocation :self ch))
          {LOG('dev: fart')})
        (:CastFailed)))
    (:CastFailed)))
''',
    # stand in front of the first interactable of a kind (tests, and the dev menu's "go to the post-it")
    'GWDevGoTo': f'''
(fn GWDevGoTo (Kind)
{GATE('goto')}
  (Variables|Default|SetBestT (Variables|GW|GetNoPickup))
  (for q (Actor|GetAllActorsOfClass :ActorClass "{PK}")
    (if (== ({P('Kind')} :self q) Kind)
      (Variables|Default|SetBestT q)))
  (bind t (Variables|Default|GetBestT))
  (bind ch {MYCH}
    (:then
      (if (not ({ISVALID} :Object t))
        {LOG('dev goto: none of that kind')}
        (return))
      (bind tl (Transformation|GetActorLocation :self t))
      ; where to stand: beside the table (balls), in front of the armour (swords), on the post-it / toilet marker,
      ; 85 cm in front of the safe / alarm box; then on the floor
      (bind ahead ({VMUL} :A (Transformation|GetActorForwardVector :self t) :B (select (or (== Kind 3) (== Kind 4)) 85.0 0.0)))
      (bind fx (+ (.x tl) (.x ahead)))
      (bind fy (select (== Kind 0) 1040.0 (select (== Kind 1) (- (.y tl) 115.0) (+ (.y tl) (.y ahead)))))
      (bind fz (select (or (== Kind 0) (or (== Kind 1) (== Kind 4))) 0.0 (.z tl)))
      (bind (np nok) (AI|Navigation|GetRandomReachablePointinRadius :Origin (Math|Vector|MakeVector fx fy fz) :Radius 40.0))
      (bind spot (select nok np (Math|Vector|MakeVector fx fy fz)))
      (Transformation|SetActorLocation :self ch :NewLocation (+ spot (Math|Vector|MakeVector 0.0 0.0 97.0)) :bSweep false :bTeleport true)
      (Pawn|SetControlRotation :self self :NewRotation (Math|Rotator|FindLookatRotation :Start (Transformation|GetActorLocation :self ch) :Target tl))
      (Development|PrintString :InString (cat "GW: dev goto kind " Kind " at " tl " stand " (Transformation|GetActorLocation :self ch)) :bPrintToScreen false))
    (:CastFailed)))
''',
    # tests: look at the nearest thing of a kind from the camera (Up: aim that many cm above its origin)
    'DevLookAt': f'''
(fn DevLookAt (Kind Up)
  (bind ch {MYCH}
    (:then
      (Variables|Default|SetBestD 100000000.0)
      (Variables|Default|SetBestP (Variables|GW|GetNoPickup))
      (for q (Actor|GetAllActorsOfClass :ActorClass "{PK}")
        (if (== ({P('Kind')} :self q) Kind)
          (bind d (Math|Vector|Distance(Vector) (Transformation|GetActorLocation :self q) (Transformation|GetActorLocation :self ch)))
          (if (< d (Variables|Default|GetBestD))
            (Variables|Default|SetBestD d)
            (Variables|Default|SetBestP q))))
      (bind t (Variables|Default|GetBestP))
      (if ({ISVALID} :Object t)
        (Pawn|SetControlRotation :self self :NewRotation (Math|Rotator|FindLookatRotation :Start (Transformation|GetWorldLocation :self (GW|Get|BP_GW_Character|FollowCamera :self ch)) :Target (+ (Transformation|GetActorLocation :self t) (Math|Vector|MakeVector 0.0 0.0 Up))))
        (Development|PrintString :InString (cat "GW: dev look at kind " Kind " " (Variables|Default|GetBestD) " cm") :bPrintToScreen false)))
    (:CastFailed)))
''',
    # QA: a ball thrown from the player's hand straight at the nearest NPC guest (no camera involved)
    'GWDevBallAt': f'''
(fn GWDevBallAt ()
{GATE('ballat')}
  (bind ch {MYCH}
    (:then
      (Variables|Default|SetBestD 100000000.0)
      (Variables|Default|SetBestT (Variables|GW|GetNoSwapChar))
      (bind here (Transformation|GetActorLocation :self ch))
      (for c (Actor|GetAllActorsOfClass :ActorClass {CHAR})
        (if (and (and (!= c ch) (not (GW|Get|BP_GW_Character|IsDead :self c))) (and (== (GW|Get|BP_GW_Character|Kind :self c) 0) (and (not (Pawn|IsPlayerControlled :self c)) (not (GW|Get|BP_GW_Character|IsSeeker :self c)))))
          (bind d (Math|Vector|Distance(Vector) (Transformation|GetActorLocation :self c) here))
          (if (< d (Variables|Default|GetBestD))
            (Variables|Default|SetBestD d)
            (Variables|Default|SetBestT c))))
      (if ({ISVALID} :Object (Variables|GW|GetDevAimTarget))
        (if (not (GW|Get|BP_GW_Character|IsDead :self (Variables|GW|GetDevAimTarget)))
          (Variables|Default|SetBestT (Variables|GW|GetDevAimTarget))))
      (bind t (Variables|Default|GetBestT))
      (if (not ({ISVALID} :Object t))
        (return))
      (bind tl (Transformation|GetActorLocation :self t))
      (bind to (Math|Vector|Normalize (- tl here)))
      (bind gm {GMC}
        (:then (GW|Call|BP_GW_GameMode|LaunchBall :self gm :Thrower ch :Start (+ (+ here (Math|Vector|MakeVector 0.0 0.0 30.0)) (* to 50.0)) :Aim (+ tl (Math|Vector|MakeVector 0.0 0.0 20.0))))
        (:CastFailed)))
    (:CastFailed)))
''',
    # Mode 0: nearest NPC guest (frozen, so it waits), 1: nearest detective; stand Dist cm from it, facing it
    'GWDevAimAt': f'''
(fn GWDevAimAt (Mode Dist)
{GATE('aimat')}
  (bind ch {MYCH}
    (:then
      (Variables|Default|SetBestD 100000000.0)
      (Variables|Default|SetBestT (Variables|GW|GetNoSwapChar))
      (bind here (Transformation|GetActorLocation :self ch))
      (for c (Actor|GetAllActorsOfClass :ActorClass {CHAR})
        (if (and (and (!= c ch) (not (GW|Get|BP_GW_Character|IsDead :self c))) (and (== (GW|Get|BP_GW_Character|Kind :self c) 0) (select (== Mode 1) (GW|Get|BP_GW_Character|IsSeeker :self c) (and (not (Pawn|IsPlayerControlled :self c)) ({ISVALID} :Object (Pawn|GetController :self c))))))
          (bind cl (Transformation|GetActorLocation :self c))
          ; a wall or furniture between us costs 10 m in the ranking: a visible guest wins over a nearer hidden one
          (bind (lh lok) (Collision|LineTraceByChannel :Start (+ (+ here (Math|Vector|MakeVector 0.0 0.0 50.0)) (* (Math|Vector|Normalize (- cl here)) 45.0)) :End (+ cl (Math|Vector|MakeVector 0.0 0.0 30.0)) :TraceChannel "Visibility" :bTraceComplex false :bIgnoreSelf true))
          (bind (lb li lt ld ll lImp lN lIN lP lActor) (Collision|BreakHitResult lh))
          (bind d (+ (Math|Vector|Distance(Vector) cl here) (select (and lok (!= lActor c)) 1000.0 0.0)))
          (if (< d (Variables|Default|GetBestD))
            (Variables|Default|SetBestD d)
            (Variables|Default|SetBestT c))))
      (bind t (Variables|Default|GetBestT))
      (if (not ({ISVALID} :Object t))
        {LOG('dev aim: no target')}
        (return))
      (if (== Mode 0)
        (GW|Call|BP_GW_Character|SetFrozen :self t :Frozen true)
        (AI|Navigation|StopMovement :self (Pawn|GetController :self t)))
      (Variables|GW|SetDevAimTarget t)
      (CallFunction|DevAimSpot :Ch ch :T t :Dist Dist)
      (Development|PrintString :InString (cat "GW: dev aim mode=" Mode " target=" (Utilities|GetDisplayName :Object t) " dist=" (Math|Vector|Distance(Vector) (Transformation|GetActorLocation :self t) (Transformation|GetActorLocation :self ch))) :bPrintToScreen false))
    (:CastFailed)))
''',
    'DevAimLocal': f'''
(fn DevAimLocal (Mode Dist)
  (bind ch {MYCH}
    (:then
      (Variables|Default|SetBestD 100000000.0)
      (Variables|Default|SetBestT (Variables|GW|GetNoSwapChar))
      (bind here (Transformation|GetActorLocation :self ch))
      (for c (Actor|GetAllActorsOfClass :ActorClass {CHAR})
        (if (and (and (!= c ch) (not (GW|Get|BP_GW_Character|IsDead :self c))) (and (== (GW|Get|BP_GW_Character|Kind :self c) 0) (select (== Mode 1) (GW|Get|BP_GW_Character|IsSeeker :self c) (and (not (Pawn|IsPlayerControlled :self c)) (not (GW|Get|BP_GW_Character|IsSeeker :self c))))))
          (bind d (Math|Float|Absolute(Float) (- (Math|Vector|Distance(Vector) (Transformation|GetActorLocation :self c) here) Dist)))
          (if (< d (Variables|Default|GetBestD))
            (Variables|Default|SetBestD d)
            (Variables|Default|SetBestT c))))
      ; the host knows the very target GWDevAimAt froze (a client only finds it by its distance)
      (if (and (Networking|HasAuthority) ({ISVALID} :Object (Variables|GW|GetDevAimTarget)))
        (Variables|Default|SetBestT (Variables|GW|GetDevAimTarget)))
      (bind t (Variables|Default|GetBestT))
      (if ({ISVALID} :Object t)
        (bind cam (Transformation|GetWorldLocation :self (GW|Get|BP_GW_Character|FollowCamera :self ch)))
        (Pawn|SetControlRotation :self self :NewRotation (Math|Rotator|FindLookatRotation :Start cam :Target (+ (Transformation|GetActorLocation :self t) (Math|Vector|MakeVector 0.0 0.0 15.0))))
        (Development|PrintString :InString (cat "GW: dev aim local -> " (Utilities|GetDisplayName :Object t) " at " (Variables|Default|GetBestD)) :bPrintToScreen false)))
    (:CastFailed)))
''',
    'DevAimSpot': '\n'.join(['(fn DevAimSpot (Ch T Dist)',
                             '  (Variables|Default|SetFound false)',
                             '  (bind tl (Transformation|GetActorLocation :self T))',
                             '  (bind away (Math|Vector|Normalize (Math|Vector|MakeVector (- (.x (Transformation|GetActorLocation :self Ch)) (.x tl)) (- (.y (Transformation|GetActorLocation :self Ch)) (.y tl)) 0.0)))',
                             '  (bind base (.yaw (Math|Rotator|MakeRotfromX away)))'] + [f'''  (if (not (Variables|Default|GetFound))
    (bind dir{k} (Math|Vector|GetForwardVector (Math|Rotator|MakeRotator :Roll 0.0 :Pitch 0.0 :Yaw (+ base {a}))))
    (bind (h{k} ok{k}) (Collision|SphereTraceByProfile :Start (+ tl (+ (Math|Vector|MakeVector 0.0 0.0 20.0) (* dir{k} 50.0))) :End (+ tl (+ (Math|Vector|MakeVector 0.0 0.0 20.0) (* dir{k} (+ Dist 380.0)))) :Radius 36.0 :ProfileName "BlockAll" :bTraceComplex false :bIgnoreSelf true))
    (if (not ok{k})
      (Variables|Default|SetFound true)
      (Variables|Default|SetSpot (+ tl (+ (Math|Vector|MakeVector 0.0 0.0 5.0) (* dir{k} Dist))))))''' for k, a in enumerate((0, 45, -45, 90, -90, 135, -135, 180))] + [
                             '  (if (not (Variables|Default|GetFound))',
                             '    (Variables|Default|SetSpot (+ tl (+ (Math|Vector|MakeVector 0.0 0.0 5.0) (* away Dist)))))',
                             '  (Transformation|SetActorLocation :self Ch :NewLocation (Variables|Default|GetSpot) :bSweep false :bTeleport true)',
                             '  (Pawn|SetControlRotation :self self :NewRotation (Math|Rotator|FindLookatRotation :Start (Variables|Default|GetSpot) :Target tl)))']),
}
PC_W['PTAttack'] = f'''
(fn PTAttack ()
  (bind ch {MYCH}
    (:then (CallFunction|GuestAttack :Ch ch))
    (:CastFailed)))
'''
DEV = lambda cmd: f'(CallFunction|DevServer :Cmd "{cmd}")'
# -GWPickupTest -GWPickupSolo on a lone host: everything as a guest against NPCs (balls, sword, swaps, post-it, safe,
# fire alarm twice, toilet, fart). -GWPickupTest on host + client: the host turns detective, the client (guest) throws
# at an NPC and at the host, slashes both, swaps (client camera follows), reads the post-it, opens the safe, farts.
HOST_STEPS = [
    (2, DEV('GWDevQuickTest 1')), (5, DEV('GWDevTeleport 5000 1040 130')),
    (6, '(CallFunction|TryPickup)'), (7, '(CallFunction|TryPickup)'), (8, '(CallFunction|TryPickup)'),
    (9, DEV('GWDevAimAt 0 450')), (10, '(CallFunction|DevAimLocal :Mode 0 :Dist 450.0)'), (11, '(CallFunction|DevAimLocal :Mode 0 :Dist 450.0)'), (12, '(CallFunction|PTAttack)'),
    (14, DEV('GWDevTeleport 2620 2215 130')), (15, '(CallFunction|TryPickup)'),
    (17, DEV('GWDevAimAt 0 140')), (18, '(CallFunction|DevAimLocal :Mode 0 :Dist 140.0)'), (19, '(CallFunction|PTAttack)'),
    (21, DEV('GWDevGiveSwap')), (22, DEV('GWDevAimAt 0 600')), (23, '(CallFunction|DevAimLocal :Mode 0 :Dist 600.0)'), (24, '(CallFunction|DevAimLocal :Mode 0 :Dist 600.0)'),
    (25, '(CallFunction|RequestSwap)'), (28, '(CallFunction|RequestSwap)'),
    (29, DEV('GWDevGiveSwap')), (30, DEV('GWDevAimAt 0 600')), (31, '(CallFunction|DevAimLocal :Mode 0 :Dist 600.0)'), (32, '(CallFunction|DevAimLocal :Mode 0 :Dist 600.0)'),
    (33, '(CallFunction|RequestSwap)'),
    # safe without the code (refused), the post-it, the safe again, the fire alarm twice (once per game), toilet, fart
    (36, DEV('GWDevGoTo 3')), (37, '(CallFunction|TryPickup)'), (38, DEV('GWDevGoTo 2')), (39, '(CallFunction|TryPickup)'),
    (41, DEV('GWDevGoTo 3')), (42, '(CallFunction|TryPickup)'), (44, DEV('GWDevGoTo 4')), (45, '(CallFunction|TryPickup)'),
    (47, '(CallFunction|TryPickup)'), (48, DEV('GWDevGoTo 5')), (49, '(CallFunction|TryPickup)'), (50, '(CallFunction|TryPickup)'),
    (51, DEV('GWDevFart')),
]
HOST_NET_STEPS = [(2, DEV('GWDevQuickTest 2'))]
CLIENT_STEPS = [
    (5, DEV('GWDevRole 1')), (7, DEV('GWDevTeleport 5000 1040 130')), (8, '(CallFunction|TryPickup)'),
    (10, DEV('GWDevAimAt 0 450')), (11, '(CallFunction|DevAimLocal :Mode 0 :Dist 450.0)'), (12, '(CallFunction|DevAimLocal :Mode 0 :Dist 450.0)'), (13, '(CallFunction|PTAttack)'),
    (15, DEV('GWDevGiveBall')), (16, DEV('GWDevAimAt 1 450')), (17, '(CallFunction|DevAimLocal :Mode 1 :Dist 450.0)'), (18, '(CallFunction|DevAimLocal :Mode 1 :Dist 450.0)'), (19, '(CallFunction|PTAttack)'),
    (21, DEV('GWDevGiveSword')), (22, DEV('GWDevAimAt 0 140')), (23, '(CallFunction|DevAimLocal :Mode 0 :Dist 140.0)'), (24, '(CallFunction|PTAttack)'),
    (26, DEV('GWDevAimAt 1 140')), (27, '(CallFunction|DevAimLocal :Mode 1 :Dist 140.0)'), (28, '(CallFunction|PTAttack)'),
    (30, DEV('GWDevGiveSwap')), (31, DEV('GWDevAimAt 0 600')), (32, '(CallFunction|DevAimLocal :Mode 0 :Dist 600.0)'), (33, '(CallFunction|DevAimLocal :Mode 0 :Dist 600.0)'),
    (34, '(CallFunction|RequestSwap)'),
    (38, DEV('GWDevGoTo 2')), (39, '(CallFunction|TryPickup)'), (41, DEV('GWDevGoTo 3')), (42, '(CallFunction|TryPickup)'),
    (44, DEV('GWDevGoTo 5')), (45, '(CallFunction|TryPickup)'),
]
PC_W['PTHost'] = '(fn PTHost (St)\n' + '\n'.join(f'  (if (== St {s}) {c})' for s, c in HOST_STEPS) + ')\n'
# -GWPickupShots (rendered QA): stand at each thing, look at it, "Shot showui" (GuessWho/Saved/Screenshots)
SHOT = '(Development|ExecuteConsoleCommand :Command "Shot showui" :SpecificPlayer self)'
SHOT_STEPS = [
    (2, DEV('GWDevQuickTest 1')), (4, DEV('GWDevGoTo 0')), (5, '(CallFunction|DevLookAt :Kind 0 :Up 0.0)'), (6, SHOT),
    (7, DEV('GWDevGoTo 1')), (8, '(CallFunction|DevLookAt :Kind 1 :Up 0.0)'), (9, SHOT),
    (10, '(CallFunction|TryPickup)'), (12, '(CallFunction|DevLookAt :Kind 1 :Up 0.0)'), (13, SHOT),
    (14, DEV('GWDevGoTo 3')), (15, '(CallFunction|DevLookAt :Kind 3 :Up 60.0)'), (16, SHOT),
    (17, DEV('GWDevLearnCode')), (18, '(CallFunction|TryPickup)'), (20, SHOT),
    (21, DEV('GWDevGoTo 4')), (22, '(CallFunction|DevLookAt :Kind 4 :Up 0.0)'), (23, SHOT),
    (24, '(CallFunction|TryPickup)'), (25, SHOT),
    (26, DEV('GWDevGoTo 2')), (28, '(CallFunction|DevLookAt :Kind 2 :Up 0.0)'), (29, SHOT),
    # the swap in first person (the ghost has its own camera): ghost in flight 0.45 s after R
    (30, DEV('GWDevGiveSwap')), (31, DEV('GWDevAimAt 0 500')), (32, '(CallFunction|DevAimLocal :Mode 0 :Dist 500.0)'),
    (33, '(CallFunction|DevAimLocal :Mode 0 :Dist 500.0)'), (34, '(CallFunction|RequestSwap)'), (34, '(CallFunction|PTShotSoon :Delay 0.45)'),
    (36, SHOT),
    # third person (s37 SetViewMode): the sword in the hand as the others see it, a slash, a ball
    (37, '(CallFunction|SetViewMode :FP false)'), (38, DEV('GWDevAimAt 0 160')), (39, '(CallFunction|DevAimLocal :Mode 0 :Dist 160.0)'),
    (40, SHOT), (41, '(CallFunction|PTAttack)'), (41, '(CallFunction|PTShotSoon :Delay 0.15)'),
    (43, DEV('GWDevAimAt 0 400')), (44, '(CallFunction|DevAimLocal :Mode 0 :Dist 400.0)'), (45, DEV('GWDevBallAt')), (45, '(CallFunction|PTShotSoon :Delay 0.08)'),
]
PC_W['PTShotSoon'] = '(fn PTShotSoon (Delay) (Utilities|Time|SetTimerbyFunctionName :Object self :FunctionName "PTShotNow" :Time Delay :bLooping false))'
PC_W['PTShotNow'] = '(fn PTShotNow () (Development|ExecuteConsoleCommand :Command "Shot showui" :SpecificPlayer self))'
PC_W['PTShots'] = '(fn PTShots (St)\n' + '\n'.join(f'  (if (== St {s}) {c})' for s, c in SHOT_STEPS) + ')\n'
PC_W['PTHostNet'] = '(fn PTHostNet (St)\n' + '\n'.join(f'  (if (== St {s}) {c})' for s, c in HOST_NET_STEPS) + ')\n'
PC_W['PTClient'] = '(fn PTClient (St)\n' + '\n'.join(f'  (if (== St {s}) {c})' for s, c in CLIENT_STEPS) + ')\n'
PC_W['PTLog'] = f'''
(fn PTLog (St)
  (bind ps {PSC}
    (:then
      (bind p (Pawn|GetControlledPawn :self self))
      (bind ch {MYCH}
        (:then
          (Development|PrintString :InString (cat "GW ptest " (select (Networking|HasAuthority) "host" "client") " step " St " role=" {PS_('GWRole')} " alive=" {PS_('IsAlive')} " balls=" {PS_('Balls')} " sword=" {PS_('HasSword')} " swapgun=" {PS_('HasSwapGun')} " readyIn=" (- {PS_('SwapReadyAt')} {SNOW}) " pawn=" (Utilities|GetDisplayName :Object p) " dead=" (GW|Get|BP_GW_Character|IsDead :self ch) " hp=" (GW|Get|BP_GW_Character|Health :self ch) " view=" (Utilities|GetDisplayName :Object (Pawn|GetViewTarget :self self)) " pickups=" (Utilities|Array|Length (Actor|GetAllActorsOfClass :ActorClass "{PK}")) " code=" (Variables|GW|GetKnownCode) "/r" (Variables|GW|GetKnownRound) " alarm=" (CallFunction|AlarmRinging)) :bPrintToScreen false))
        (:CastFailed
          (Development|PrintString :InString (cat "GW ptest " (select (Networking|HasAuthority) "host" "client") " step " St " pawn=" (Utilities|GetDisplayName :Object p) " (no character)") :bPrintToScreen false))))
    (:CastFailed)))
'''
PC_W['PickupTestTick'] = f'''
(fn PickupTestTick ()
  (if (not (Variables|GW|GetPTReady))
    (Variables|GW|SetPTWait (+ (Variables|GW|GetPTWait) 1))
    (if (Networking|HasAuthority)
      (if (or (or (Utilities|HasLaunchOption :OptionToCheck "GWPickupSolo") (Utilities|HasLaunchOption :OptionToCheck "GWPickupShots")) (or (>= (Utilities|Array|Length (Class|GameStateBase|GetPlayerArray :self (Game|GetGameState))) 2) (> (Variables|GW|GetPTWait) 90)))
        (Variables|GW|SetPTReady true))
      (else
        (if ({ISVALID} :Object (Pawn|GetControlledPawn :self self))
          (Variables|GW|SetPTReady true))))
    (return))
  (Variables|GW|SetPTStep (+ (Variables|GW|GetPTStep) 1))
  (bind st (Variables|GW|GetPTStep))
  (if (Networking|HasAuthority)
    (if (Utilities|HasLaunchOption :OptionToCheck "GWPickupShots")
      (CallFunction|PTShots :St st)
      (elif (Utilities|HasLaunchOption :OptionToCheck "GWPickupSolo")
        (CallFunction|PTHost :St st)
        (else
          (CallFunction|PTHostNet :St st))))
    (else
      (CallFunction|PTClient :St st)))
  (if (<= st 60)
    (CallFunction|PTLog :St st)))
'''
for name, code in PC_W.items():
    if name in shop_items.S40_OWNS:      # body in s40_inventory.py (run it after this script)
        continue
    write(pc, name, code, compile_after=False)
compile_bp(pc, quiet=True)

# ---------------------------------------------------------------- input: R = body-swap gun
INP = '/Game/GW/Input'
ia = unreal.load_asset(f'{INP}/IA_Swap') if EAL.does_asset_exist(f'{INP}/IA_Swap') else \
    AT.create_asset('IA_Swap', INP, unreal.InputAction, unreal.InputAction_Factory())
EAL.save_loaded_asset(ia, False)
# (no key mapping any more: the inventory's left click calls RequestSwap, s40_inventory.py)
wire_input(pc, 'IA_Swap', {'Started': 'RequestSwap'}, pos=(0, 4600))
compile_bp(pc)
print('BP_GW_PlayerController', node_problems(pc))
save(pc)
print('s38 done: felt z', FELT_Z, 'swords', [tuple(round(v, 1) for v in (sword_spot(x)[0].x, sword_spot(x)[0].y, sword_spot(x)[0].z)) for x in ARMOURS])
