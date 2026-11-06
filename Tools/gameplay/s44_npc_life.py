"""NPC life (user's feedback of 2026-11-05, 2): human-like guests, no pops, no guest parked for ever, cheap at 100+ NPCs.

Every guest has a personality rolled at possession (pace, sociability, need for rest, two favourite rooms, a mood that changes every
40-150 s). LifeNext picks the next activity from them: visit a point of interest (LifePts in the game mode: paintings, windows, the stage, the bar,
tables, curiosities, toilets, fireplaces; each has a dwell of its own and can chain, bar -> table), walk along the walls, sit, pause and look around, walk beside
another guest (LifeMode 3), stop in a chat circle that forms, gets latecomers, and breaks up one by one (LifeMode 5). While standing a guest glances
at things and passers-by. Turning goes through the AI focus and the movement component's rotation rate: no snap. Speed: 125-195 cm/s around the players' 165,
re-rolled per walk (a player walking at 165 sits in the middle of the range). A failed move means another target, never a teleport (LifeUnstick walks to the navmesh).
Server only; everything visible replicates as before (movement, DanceId). Nothing here needs per-tick work: the 2 Hz Think timer stays, GM lookups are random probes.

Parts: char (lean mode, pop fix of CameraFadeTick lives in s23), npc, gm, all by default; pois: only rebuilds the point table.
Run order: s14 npc, s36 npc, s40_events2 npc, s12, s23, s31, then this one last (owners skip the graphs listed in S44_OWNS, so re-running them is safe).
Usage: ue_run.py s44_npc_life.py [char] [npc] [gm] [pois]
"""
import sys, importlib, json, math
sys.path.insert(0, r'J:\Projets\Unreal_Projects\Guess Who\Tools\gameplay')
import gw_lib; importlib.reload(gw_lib)
from gw_lib import *

try:
    UE_ARGS
except NameError:
    UE_ARGS = []
PARTS = set(UE_ARGS) or {'char', 'npc', 'gm', 'pois'}
ROOT = r'J:\Projets\Unreal_Projects\Guess Who\Tools'
V3 = unreal.Vector.static_struct()
CHAR = '"/Game/GW/Blueprints/BP_GW_Character.BP_GW_Character_C"'
ISVALID = 'GW|Call|/Script/Engine.KismetSystemLibrary|IsValid'
GMC = '(Utilities|Casting|CastToBP_GW_GameMode (Game|GetGameMode))'
NPCC = lambda o: f'(Utilities|Casting|CastToBP_GW_NPCController (Pawn|GetController :self {o}))'
NOW = '(Utilities|Time|GetGameTimeinSeconds)'
RF = lambda a, b: f'(Math|Random|RandomFloatinRange {float(a)} {float(b)})'
RI = lambda a, b: f'(Math|Random|RandomIntegerinRange {a} {b})'
RND = '(Math|Random|RandomFloat)'
LOC = lambda o: f'(Transformation|GetActorLocation :self {o})'
DIST2 = lambda a, b: f'(Math|Vector|Distance2D(Vector) {a} {b})'
G_ = lambda v: f'(Variables|GW|Get{v})'
S_ = lambda v, x: f'(Variables|GW|Set{v} {x})'
SL = lambda v, x: f'(Variables|Default|Set{v} {x})'
L = lambda v: f'(Variables|Default|Get{v})'
CH = lambda v, o: f'(GW|Get|BP_GW_Character|{v} :self {o})'
CHS = lambda v, o, x: f'(GW|Set|BP_GW_Character|{v} :self {o} :{v} {x})'
NC = lambda v, o: f'(GW|Get|BP_GW_NPCController|{v} :self {o})'
NCS = lambda v, o, x: f'(GW|Set|BP_GW_NPCController|{v} :self {o} :{v} {x})'
CMOV = lambda o='Ch': f'(GW|Get|/Script/Engine.Character|CharacterMovement :self {o})'
MESH = lambda o='Ch': f'(GW|Get|/Script/Engine.Character|Mesh :self {o})'
MYPAWN = '(Utilities|Casting|CastToBP_GW_Character (Pawn|GetControlledPawn :self self))'
LOG = lambda m: f'(Development|PrintString :InString {m} :bPrintToScreen false)'
V = lambda x, y, z=0.0: f'(Math|Vector|MakeVector {x} {y} {z})'
KINDS = {'painting': 0, 'window': 1, 'stage': 2, 'bar': 3, 'table': 4, 'curio': 5, 'toilet': 6, 'fire': 7}
HOMES = [0, 2, 3, 4, 5, 7, 8]       # dining, library, hall, ballroom, billiard, study, conservatory (not the corridors)
chc = load_bp('BP_GW_Character').generated_class()


# ------------------------------------------------------------------ the points of interest, from the level's own data
def build_pois():
    layout = json.load(open(ROOT + r'\manor_layout.json', encoding='utf-8'))
    rooms = [tuple(r['rect']) for r in layout['rooms']]
    room_names = [r['name'] for r in layout['rooms']]
    inst = json.load(open(ROOT + r'\level\instances.json', encoding='utf-8'))['instances']
    props = json.load(open(ROOT + r'\level\props_layout.json', encoding='utf-8'))
    GALLERY = len(rooms)

    def room_of(x, y, z=0):
        if z > 450:
            return GALLERY
        for i, r in enumerate(rooms):
            if r[0] <= x < r[2] and r[1] <= y < r[3]:
                return i
        return -1

    def inward(x, y, r):
        d = [(x - r[0], (1, 0)), (r[2] - x, (-1, 0)), (y - r[1], (0, 1)), (r[3] - y, (0, -1))]
        return min(d)[1]

    pois = []                  # stand x, y, z; look x, y, z; kind; room

    def add(sx, sy, lx, ly, lz, kind, z=100.0):
        rm = room_of(sx, sy, z)
        if rm >= 0:
            pois.append(((sx, sy, z), (lx, ly, lz), KINDS[kind], rm))

    for e in inst:                                       # paintings and windows: on a wall, stand in front, inside the room
        if e['a'] == 'GW_Paintings' and e['m'].startswith('SM_GW_Frame'):
            x, y, zz = e['t']
            z = 600.0 if zz > 450 else 100.0
            rm = room_of(x + 1, y + 1, z)
            rect = (2000, 1950, 4000, 2400) if z > 450 else (rooms[rm] if rm >= 0 else None)
            if rect:
                nx, ny = inward(x, y, rect)
                d = 130.0 if z > 450 else 185.0
                add(x + nx * d, y + ny * d, x, y, zz, 'painting', z)
        elif 'WindowCasing' in e['m']:
            x = (e['lo'][0] + e['hi'][0]) / 2
            y = (e['lo'][1] + e['hi'][1]) / 2
            rm = room_of(x + 1, y + 1)
            if rm >= 0:
                nx, ny = inward(x, y, rooms[rm])
                add(x + nx * 120.0, y + ny * 120.0, x, y, 190.0, 'window')
    for x, y in ((4150, 3400), (5000, 4300), (5900, 3700), (5300, 4300)):     # conservatory glass
        add(x, y, x + (150 if x > 5500 else (-150 if x < 4500 else 0)), y + (150 if y > 4200 else 0), 180.0, 'window')
    fires = {}
    for e in inst:
        if e['a'].startswith('GW_Fire_'):
            fires.setdefault(e['a'], []).append(e['t'])
    for a, ts in fires.items():
        x, y = sum(t[0] for t in ts) / len(ts), sum(t[1] for t in ts) / len(ts)
        rm = room_of(x, y)
        if rm >= 0:
            nx, ny = inward(x, y, rooms[rm])
            for off in (-90, 0, 90):
                add(x + nx * 230.0 + ny * off, y + ny * 230.0 + nx * off, x, y, 130.0, 'fire')
    for x in (2640, 2780, 2920, 3080, 3220, 3360):       # the stage, from the foot of the steps' lane (s36 keeps it clear)
        add(float(x), 3600.0 + (x % 7) * 10, 3000.0, 4100.0, 190.0, 'stage')
    for x, y in ((4800, 1430), (4900, 1500), (1780, 1010), (1800, 1120)):      # beside the bar carts (the counter front belongs to the queues)
        add(float(x), float(y), 4790.0 if x > 3000 else 1900.0, 1560.0 if x > 3000 else 1010.0, 110.0, 'bar')
    RAD = {'table_dining': 260, 'billiard_table': 210, 'champagne_table': 120, 'card_table': 170, 'sideboard': 130, 'table_console': 120, 'bar_cart': 110, 'desk_partners': 170, 'writing_bureau': 120,
           'statue_dancer': 140, 'armor_suit': 130, 'globe_floor': 120, 'bust_marble': 120, 'clock_grandfather': 130, 'curio_cabinet': 130, 'gramophone': 130, 'harp': 150, 'birdcage': 120,
           'film_projector': 130, 'radio_cathedral': 120, 'dress_form': 120, 'stag_head': 180, 'drum_kit': 170, 'double_bass': 130, 'screen_folding': 130}
    TABLE = {'table_dining', 'billiard_table', 'champagne_table', 'card_table', 'sideboard', 'table_console', 'bar_cart', 'desk_partners', 'writing_bureau'}
    for p in props:
        m = p['mesh']
        if m in ('palm_potted', 'fern_stand', 'chaise_longue') and room_of(p['x'], p['y']) == room_names.index('conservatory'):
            RAD[m] = 120                                 # the plants are what there is to see in the conservatory
        if m in RAD:
            rm = room_of(p['x'], p['y'])
            if rm < 0:
                continue
            cx, cy = (rooms[rm][0] + rooms[rm][2]) / 2, (rooms[rm][1] + rooms[rm][3]) / 2
            dx, dy = cx - p['x'], cy - p['y']
            n = math.hypot(dx, dy) or 1.0
            add(p['x'] + dx / n * RAD[m], p['y'] + dy / n * RAD[m], p['x'], p['y'], max(p['z'], 110.0), 'table' if m in TABLE else 'curio')
    for x in (168.5, 286.0):                             # W.C. (dress_state wc_points)
        add(x, 2040.0, x, 1945.0, 80.0, 'toilet')
    w = unreal.EditorLevelLibrary.get_editor_world()
    good, dropped = [], 0
    for s, l, k, r in pois:                              # keep what the navmesh can reach; stand on it
        q = unreal.NavigationSystemV1.project_point_to_navigation(w, unreal.Vector(*s), None, None, unreal.Vector(120, 120, 150))
        if q is None or (abs(q.x) < 0.01 and abs(q.y) < 0.01):
            dropped += 1
            continue
        good.append(((q.x, q.y, s[2]), l, k, r))
    if not good:
        print('POI: no navmesh in the editor world: kept every point unprojected')
        good = pois
    good.sort(key=lambda p: p[3])
    first = [-1] * (GALLERY + 1)
    count = [0] * (GALLERY + 1)
    for i, p in enumerate(good):
        if first[p[3]] < 0:
            first[p[3]] = i
        count[p[3]] += 1
    from collections import Counter
    print('POI', len(good), 'dropped', dropped, 'by kind', Counter(p[2] for p in good), 'by room', dict(zip(room_names + ['gallery'], count)))
    rects = rooms + [(2000, 1950, 4000, 2400)]
    return good, first, count, rects


# ------------------------------------------------------------------ character: lean mode
if 'char' in PARTS:
    ch = load_bp('BP_GW_Character')
    ensure_var(ch, 'LeanOn', 'bool', category='GW')
    ensure_var(ch, 'FadeTimerOn', 'bool', category='GW')
    ensure_fn(ch, 'SetLean', inputs=[('On', 'bool')])
    compile_bp(ch, quiet=True)
    BOOM = '(Variables|Camera|GetCameraBoom)'
    write(ch, 'SetLean', f'''
(fn SetLean (On)
  (if (== On (Variables|GW|GetLeanOn))
    (return))
  (Variables|GW|SetLeanOn On)
  ; a guest nobody plays needs no camera rig: the spring arm's trace every frame and the transforms of everything under it (first-person hands, gun, flashlight) go away
  (Components|Tick|SetComponentTickEnabled :self {BOOM} :bEnabled (not On))
  (Components|Tick|SetComponentTickEnabled :self (Variables|Camera|GetFollowCamera) :bEnabled (not On))
  (Transformation|SetAbsolute :self {BOOM} :bNewAbsoluteLocation On :bNewAbsoluteRotation On :bNewAbsoluteScale On)
  (if (== (Variables|GW|GetKind) 0)
    (Transformation|SetAbsolute :self (Variables|Default|GetVisionRoot) :bNewAbsoluteLocation On :bNewAbsoluteRotation On :bNewAbsoluteScale On))
  (Actor|Tick|SetActorTickEnabled :self self :bEnabled (not On)))
''', compile_after=False)
    write(ch, 'EventGraph', '''
(event EventReceiveRestarted
  (if (Pawn|IsPlayerControlled)
    (CallFunction|SetLean :On false)
    (if (not (Variables|GW|GetFadeTimerOn))
      (Variables|GW|SetFadeTimerOn true)
      (Utilities|Time|SetTimerbyFunctionName :Object self :FunctionName "CameraFadeTick" :Time 0.05 :bLooping true))))
''', compile_after=False)
    compile_bp(ch)
    print('BP_GW_Character', [p for p in node_problems(ch) if 'Lean' in p or 'Restart' in p])
    c = cdo(ch)
    m = c.get_editor_property('mesh')
    m.set_editor_property('enable_update_rate_optimizations', True)
    m.set_editor_property('visibility_based_anim_tick_option', unreal.VisibilityBasedAnimTickOption.ONLY_TICK_MONTAGES_WHEN_NOT_RENDERED)
    compile_bp(ch, quiet=True)
    save(ch)

# ------------------------------------------------------------------ NPC controller: the brain
S44_NPC = ('ThinkWith', 'AfterArrive', 'ChooseMove', 'GoTo', 'SitTry', 'SitDown', 'SitRelease', 'SeatThink', 'SocialFaceNow', 'SocialFidget', 'SocialMove', 'EventGraph')
if 'npc' in PARTS:
    npc = load_bp('BP_GW_NPCController')
    for v, t in (('PPace', 'float'), ('PSocial', 'float'), ('PRest', 'float'), ('PHome', 'int'), ('PHome2', 'int'), ('Mood', 'int'), ('MoodUntil', 'float'),
                 ('LifeMode', 'int'), ('LifeUntil', 'float'), ('LifeChainN', 'int'), ('ChainKind', 'int'), ('LifeKindNow', 'int'), ('GlanceNext', 'float'), ('MoveFails', 'int'), ('LifeRoll', 'float'),
                 ('LifeSide', 'float'), ('LifeCircleI', 'int'), ('LifeFollowers', 'int'), ('GestNext', 'float'), ('LifeGest', 'bool'), ('FaceOn', 'bool'), ('StillSince', 'float'),
                 ('ToiletAt', 'float'), ('QLine', 'int'), ('QSlot', 'int'), ('QNext', 'float'), ('BlockN', 'int'), ('BlockRounds', 'int'), ('IgnoreUntil', 'float'), ('LodNext', 'float'), ('LodFar', 'bool'), ('SlideT', 'float'), ('SlideDur', 'float'), ('YawFrom', 'float'), ('YawTo', 'float'), ('LifeInitDone', 'bool')):
        ensure_var(npc, v, t, category='GW')
    for v in ('LifeDest', 'LifeFace', 'StillLoc', 'SlideFrom', 'SlideTo', 'QSpot'):
        ensure_var(npc, v, struct=V3, category='GW')
    ensure_var(npc, 'IgnoreWho', obj_class=chc, category='GW')
    ensure_fn(npc, 'LifeLod', inputs=[('Ch', chc)])
    ensure_fn(npc, 'LifeUnwedge', inputs=[('Ch', chc)])
    ensure_fn(npc, 'LifeBlockCheck', inputs=[('Ch', chc)], outputs=[('Handled', 'bool')])
    ensure_fn(npc, 'LifeQThink', inputs=[('Ch', chc)])
    ensure_fn(npc, 'LifeTryExtra', inputs=[('Ch', chc), ('Which', 'int')], outputs=[('Ok', 'bool')])
    for f in ('LifeInit', 'LifeThink', 'LifeNext', 'LifeArrive', 'LifeWall', 'LifeGlance', 'LifeFollow', 'LifeCircle', 'LifeDrop', 'LifeUnstick', 'LifeGesture', 'SitSlideStart'):
        ensure_fn(npc, f, inputs=[('Ch', chc)])
    ensure_fn(npc, 'LifeLookAround', inputs=[('Ch', chc), ('Dur', 'float')])
    ensure_fn(npc, 'LifeGoPoi', inputs=[('Ch', chc), ('Room', 'int'), ('Kind', 'int')], outputs=[('Ok', 'bool')])
    ensure_fn(npc, 'LifeTrySocial', inputs=[('Ch', chc)], outputs=[('Ok', 'bool')])
    ensure_fn(npc, 'LifeRoomPick', inputs=[('Ch', chc)], outputs=[('Room', 'int')])
    ensure_fn(npc, 'FaceAt', inputs=[('P', V3)])
    ensure_fn(npc, 'FaceRelease')
    ensure_fn(npc, 'PaceApply')
    ensure_fn(npc, 'LifeMove', inputs=[('Dest', V3), ('Accept', 'float')])
    ensure_fn(npc, 'SitSlideTick')
    # the game mode side must exist before the calls compile
    gm0 = load_bp('BP_GW_GameMode')
    GM_SIGS = {
        'LifeRoomOf': ([('Loc', V3)], [('I', 'int')]),
        'LifePoi': ([('Room', 'int'), ('Kind', 'int')], [('I', 'int')]),
        'LifePoiLoc': ([('I', 'int')], [('Loc', V3)]),
        'LifePoiLook': ([('I', 'int')], [('Loc', V3)]),
        'LifePoiKind': ([('I', 'int')], [('K', 'int')]),
        'LifeWallPoint': ([('Room', 'int')], [('Loc', V3)]),
        'LifeHome': ([], [('Room', 'int')]),
        'LifeRefresh': ([], []),
        'LifeSocial': ([('Ch', chc), ('Social', 'float')], [('Ok', 'bool')]),
        'LifeFindLeader': ([('Ch', chc)], [('Ok', 'bool')]),
        'LifeJoinCircle': ([('Ch', chc)], [('Ok', 'bool')]),
        'LifeFormCircle': ([('Ch', chc)], [('Ok', 'bool')]),
        'LifeCircleAdd': ([('Ch', chc), ('I', 'int')], []),
        'LifeCircleLeave': ([('I', 'int')], []),
        'LifeCircleOpen': ([('I', 'int')], [('Ok', 'bool')]),
        'LifeUnfollow': ([('Leader', chc)], []),
        'LifePasser': ([('Ch', chc)], [('Who', chc)]),
        'LifeUnseen': ([('Loc', V3), ('MinD', 'float')], [('Ok', 'bool')]),
        'LifeSpawnT': ([], [('T', unreal.Transform.static_struct())]),
        'NextOutfit': ([], [('I', 'int')]),
        'LifeState': ([], [('Text', 'string')]),
        'LifeBlocker': ([('Ch', chc), ('Dest', V3), ('Pace', 'float')], [('Who', chc), ('Yield', 'bool')]),
        'LifeQJoin': ([('Ch', chc)], [('Ok', 'bool')]),
        'LifeQTick': ([], []),
        'LifeQPack': ([('Line', 'int')], []),
        'LifeQMember': ([('Ch', chc), ('Line', 'int')], [('Ok', 'bool')]),
        'LifeQAssign': ([('Ch', chc), ('Line', 'int'), ('Slot', 'int')], []),
        'LifeDanceJoin': ([('Ch', chc)], [('Ok', 'bool')]),
    }
    ensure_var(gm0, 'LifeBlockOn', 'bool', category='GW')
    PURE = ('LifeRoomOf', 'LifePoiLoc', 'LifePoiLook', 'LifePoiKind', 'LifeCircleOpen')
    for f, (i_, o_) in GM_SIGS.items():
        ensure_fn(gm0, f, inputs=i_, outputs=o_, pure=f in PURE)
    compile_bp(gm0, quiet=True)
    compile_bp(npc, quiet=True)
    GMCALL = lambda body, fail='(:CastFailed)': f'(bind gm {GMC}\n    (:then {body})\n    {fail})'
    NW = {}
    NW['FaceAt'] = f'''
(fn FaceAt (P)
  (AI|SetFocalPoint :self self :FP P)
  (if {G_('FaceOn')}
    (return))
  {S_('FaceOn', 'true')}
  (bind ch {MYPAWN}
    (:then
      (Class|CharacterMovementComponent|SetOrientRotationtoMovement :self {CMOV('ch')} :bOrientRotationToMovement false)
      (Class|CharacterMovementComponent|SetUseControllerDesiredRotation :self {CMOV('ch')} :bUseControllerDesiredRotation true))
    (:CastFailed)))
'''
    NW['FaceRelease'] = f'''
(fn FaceRelease ()
  (if (not {G_('FaceOn')})
    (return))
  {S_('FaceOn', 'false')}
  (AI|ClearFocus :self self)
  (bind ch {MYPAWN}
    (:then
      (Class|CharacterMovementComponent|SetUseControllerDesiredRotation :self {CMOV('ch')} :bUseControllerDesiredRotation false)
      (Class|CharacterMovementComponent|SetOrientRotationtoMovement :self {CMOV('ch')} :bOrientRotationToMovement true))
    (:CastFailed)))
'''
    NW['PaceApply'] = f'''
(fn PaceApply ()
  (bind ch {MYPAWN}
    (:then
      (if {CH('IsSprinting', 'ch')}
        (return))
      {SL('Sp', f"(* (* {CH('WalkSpeed', 'ch')} {G_('PPace')}) {RF(0.93, 1.07)})")}
      (Class|CharacterMovementComponent|SetMaxWalkSpeed :self {CMOV('ch')} :MaxWalkSpeed (Math|Float|Clamp(Float) :Value {L('Sp')} :Min (* 0.76 {CH('WalkSpeed', 'ch')}) :Max (* 1.18 {CH('WalkSpeed', 'ch')}))))
    (:CastFailed)))
'''
    NW['GoTo'] = f'''
(fn GoTo (Dest)
  (CallFunction|FaceRelease)
  (CallFunction|PaceApply)
  {S_('LifeDest', 'Dest')}
  (AI|Navigation|MovetoLocation :self self :Dest Dest :AcceptanceRadius 60.0 :bStopOnOverlap true :bUsePathfinding true :bProjectDestinationToNavigation true :bCanStrafe false :bAllowPartialPath true)
  {S_('IsMoving', 'true')}
  {S_('MoveStartTime', NOW)})
'''
    NW['LifeMove'] = f'''
(fn LifeMove (Dest Accept)
  (CallFunction|FaceRelease)
  (CallFunction|PaceApply)
  {S_('LifeDest', 'Dest')}
  (AI|Navigation|MovetoLocation :self self :Dest Dest :AcceptanceRadius Accept :bStopOnOverlap false :bUsePathfinding true :bProjectDestinationToNavigation true :bCanStrafe false :bAllowPartialPath true)
  {S_('IsMoving', 'true')}
  {S_('MoveStartTime', NOW)})
'''
    NW['SocialMove'] = f'''
(fn SocialMove ()
  (CallFunction|LifeMove :Dest {G_('SocialSpot')} :Accept 10.0))
'''
    # a dance couple and the bar crowd turn to their partner instead of snapping
    NW['SocialFaceNow'] = f'''
(fn SocialFaceNow (Ch)
  (CallFunction|FaceAt :P {G_('SocialFace')}))
'''
    SOCSPOT = '(+ ' + G_('SocialHome') + ' ' + V(RF(-35, 35), '(select ' + G_('SocialSolo') + ' ' + RF(-35, 0) + ' ' + RF(-35, 35) + ')') + ')'
    NW['SocialFidget'] = f'''
(fn SocialFidget (Ch)
  {S_('SocialNext', f"(+ {NOW} {RF(6, 14)})")}
  {S_('SocialRoll', RND)}
  (bind r {G_('SocialRoll')})
  (if (== {G_('SocialMode')} 1)
    (if (== {CH('DanceId', 'Ch')} 0)
      (CallFunction|SocialCouple :Ch Ch)
      (return))
    (if (and {G_('SocialSolo')} (< r 0.3))
      {S_('SocialDance', f"(+ 1 (% (+ {G_('SocialDance')} {RI(0, 3)}) 5))")}
      {CHS('DanceId', 'Ch', G_('SocialDance'))})
    (CallFunction|SocialFaceNow :Ch Ch)
    (return))
  (if (< r 0.4)
    {CHS('DanceId', 'Ch', '0')}
    {S_('SocialSpot', SOCSPOT)}
    {S_('SocialArrived', 'false')}
    (return))
  (if (< r 0.65)
    {S_('LifeRoll', RF(-70, 70))}
    (CallFunction|FaceAt :P (+ {LOC('Ch')} (* (Math|Vector|GetForwardVector (Math|Rotator|MakeRotator :Yaw (+ (.yaw (Transformation|GetActorRotation :self Ch)) {G_('LifeRoll')}))) 200.0)))
    (return))
  (CallFunction|SocialGesture :Ch Ch))
'''
    NW['LifeInit'] = f'''
(fn LifeInit (Ch)
  {S_('LifeInitDone', 'true')}
  {S_('PPace', RF(0.84, 1.1))}
  {S_('PSocial', RF(0, 1))}
  {S_('PRest', RF(0, 1))}
  {S_('LifeMode', '0')}
  {S_('MoodUntil', '0.0')}
  {S_('ToiletAt', f"(+ {NOW} {RF(60, 400)})")}
  {S_('StillLoc', LOC('Ch'))}
  {S_('StillSince', NOW)}
  (Class|CharacterMovementComponent|SetRotationRate :self {CMOV()} :RotationRate (Math|Rotator|MakeRotator :Yaw {RF(230, 360)}))
  (Pawn|Components|CharacterMovement|SetAvoidanceEnabled :self {CMOV()} :bEnable true)
  (bind gm {GMC}
    (:then
      {S_('PHome', '(GW|Call|BP_GW_GameMode|LifeHome :self gm)')}
      {S_('PHome2', '(GW|Call|BP_GW_GameMode|LifeHome :self gm)')})
    (:CastFailed)))
'''
    NW['ThinkWith'] = f'''
(fn ThinkWith (Ch)
  (if {CH('IsDead', 'Ch')}
    (Utilities|Time|ClearTimerbyFunctionName :Object self :FunctionName "Think")
    (return))
  (if (not {G_('LifeInitDone')})
    (CallFunction|LifeInit :Ch Ch))
  (bind now {NOW})
  (if (>= now {G_('LodNext')})
    {S_('LodNext', f'(+ now {RF(1.5, 3.5)})')}
    (CallFunction|LifeLod :Ch Ch))
  (bind since (- now {G_('MoveStartTime')}))
  (bind speed (Math|Vector|VectorLength (Transformation|GetVelocity :self Ch)))
  (if (and {G_('FaceOn')} (> speed 40.0))
    (CallFunction|FaceRelease))
  (if (< now {G_('PanicUntil')})
    ; panic beats the social life: stand up, stop dancing / leave the bar crowd, then run
    (if (!= {G_('LifeMode')} 0)
      (CallFunction|LifeDrop :Ch Ch))
    (if (== {G_('SocialMode')} 4)
      (CallFunction|SitRelease :Ch Ch)
      (if (== {G_('SocialMode')} 4)
        (return)))
    (if (!= {G_('SocialMode')} 0)
      (CallFunction|SocialCancel :Ch Ch))
    (CallFunction|FaceRelease)
    (if (not {CH('IsSprinting', 'Ch')})
      (GW|Call|BP_GW_Character|SetSprint :self Ch :On true))
    (if (or (not {G_('IsMoving')}) (and (> since 0.8) (< speed 20.0)))
      (CallFunction|FleeFrom :Ch Ch))
    (return))
  (if {CH('IsSprinting', 'Ch')}
    (GW|Call|BP_GW_Character|SetSprint :self Ch :On false)
    (AI|Navigation|StopMovement :self self)
    {S_('IsMoving', 'false')}
    {S_('HasFinal', 'false')}
    {S_('NextMoveTime', f'(+ now {RF(0.3, 2.5)})')}
    (return))
  (if (== {G_('SeatState')} 5)
    (return))
  (if (and (!= {G_('LifeMode')} 0) (!= {G_('SocialMode')} 0))
    (CallFunction|LifeDrop :Ch Ch))
  (if (CallFunction|LifeBlockCheck :Ch Ch)
    (return))
  ; on a seat, or dancing with a guest (s40_events2.py)
  (if (CallFunction|SeatThink :Ch Ch)
    (return))
  ; dancing on the ballroom floor / standing in the bar crowd (s36_social.py)
  (if (CallFunction|SocialThink :Ch Ch)
    (return))
  (CallFunction|LifeThink :Ch Ch))
'''
    NW['LifeThink'] = f'''
(fn LifeThink (Ch)
  (bind now {NOW})
  (bind here {LOC('Ch')})
  (if (> {DIST2('here', G_('StillLoc'))} 40.0)
    {S_('StillLoc', 'here')}
    {S_('StillSince', 'now')})
  ; wedged for good (wants to walk, has not moved 40 cm in 20 s): a short slide to a free navmesh point, last resort, never a jump
  (if (and {G_('IsMoving')} (> (- now {G_('StillSince')}) 20.0))
    (CallFunction|LifeUnwedge :Ch Ch)
    (return))
  (if (== {G_('LifeMode')} 3)
    (CallFunction|LifeFollow :Ch Ch)
    (return))
  (if (== {G_('LifeMode')} 5)
    (CallFunction|LifeCircle :Ch Ch)
    (return))
  (if (== {G_('LifeMode')} 7)
    (CallFunction|LifeQThink :Ch Ch)
    (return))
  (if {G_('IsMoving')}
    (bind since (- now {G_('MoveStartTime')}))
    (bind speed (Math|Vector|VectorLength (Transformation|GetVelocity :self Ch)))
    (if (or (and (> since 1.0) (< speed 3.0)) (> since 45.0))
      (AI|Navigation|StopMovement :self self)
      {S_('IsMoving', 'false')}
      (if {G_('HasFinal')}
        {S_('HasFinal', 'false')}
        (CallFunction|LifeMove :Dest {G_('FinalDest')} :Accept 40.0)
        (return))
      (CallFunction|AfterArrive :Ch Ch)
      (return))
    ; a walk changes pace now and then
    (if (and (> since 3.0) (< {RND} 0.05))
      (CallFunction|PaceApply))
    (return))
  (if (or (>= now {G_('NextMoveTime')}) (> (- now {G_('StillSince')}) 75.0))
    (CallFunction|ChooseMove :Ch Ch)
    (return))
  (if (>= now {G_('GlanceNext')})
    (CallFunction|LifeGlance :Ch Ch)))
'''
    # end of any walk: at the target, or stopped short of it (blocked, no path)
    NW['AfterArrive'] = f'''
(fn AfterArrive (Ch)
  (bind now {NOW})
  (bind pt {G_('Partner')})
  (if ({ISVALID} :Object pt)
    (CallFunction|FaceAt :P {LOC('pt')})
    {S_('NextMoveTime', f'(+ now {RF(6, 15)})')}
    {S_('MoveFails', '0')}
    (return))
  (if (> {DIST2(LOC('Ch'), G_('LifeDest'))} 240.0)
    ; did not get there: something else, at once, no teleport
    {S_('MoveFails', f"(+ {G_('MoveFails')} 1)")}
    {S_('LifeMode', '0')}
    {S_('LifeChainN', '0')}
    {S_('NextMoveTime', f'(+ now {RF(0.2, 1.2)})')}
    (return))
  {S_('MoveFails', '0')}
  (if (== {G_('LifeMode')} 1)
    (CallFunction|LifeArrive :Ch Ch)
    (return))
  {S_('NextMoveTime', f'(+ now {RF(0.3, 2.0)})')}
  {S_('GlanceNext', f'(+ now {RF(0.3, 1.5)})')})
'''
    NW['LifeArrive'] = f'''
(fn LifeArrive (Ch)
  (bind now {NOW})
  (bind k {G_('LifeKindNow')})
  {S_('LifeMode', '2')}
  (CallFunction|FaceAt :P {G_('LifeFace')})
  {S_('LifeRoll', '(select (== k 0) ' + RF(3, 10) + ' (select (== k 1) ' + RF(4, 14) + ' (select (== k 2) ' + RF(5, 16) + ' (select (== k 3) ' + RF(6, 22) + ' (select (== k 4) ' + RF(4, 14) + ' (select (== k 6) ' + RF(6, 15) + ' (select (== k 7) ' + RF(6, 18) + ' ' + RF(3, 10) + ')))))))')}
  {S_('NextMoveTime', f"(+ now (* {G_('LifeRoll')} (+ 0.7 (* 0.8 {G_('PRest')}))))")}
  {S_('GlanceNext', f"(+ now {RF(1.5, 4.0)})")}
  ; bar then a table or a seat
  (if (== k 3)
    {S_('LifeChainN', '1')}
    {S_('ChainKind', '4')}))
'''
    NW['LifeRoomPick'] = f'''
(fn LifeRoomPick (Ch)
  {S_('LifeRoll', RND)}
  (bind r {G_('LifeRoll')})
  (if (< r 0.40)
    (return {G_('PHome')}))
  (if (< r 0.58)
    (return {G_('PHome2')}))
  (bind gm {GMC}
    (:then
      (bind cur (GW|Call|BP_GW_GameMode|LifeRoomOf :self gm :Loc {LOC('Ch')}))
      (bind oth (GW|Call|BP_GW_GameMode|LifeHome :self gm))
      (return (select (< r 0.85) cur oth)))
    (:CastFailed (return 4))))
'''
    NW['LifeGoPoi'] = f'''
(fn LifeGoPoi (Ch Room Kind)
  (bind gm {GMC}
    (:then
      {SL('Pi', '(GW|Call|BP_GW_GameMode|LifePoi :self gm :Room Room :Kind Kind)')}
      (if (< {L('Pi')} 0)
        (return false))
      (bind pl (GW|Call|BP_GW_GameMode|LifePoiLoc :self gm :I {L('Pi')}))
      {SL('Dst', f"(+ pl {V(RF(-55, 55), RF(-55, 55))})")}
      {S_('LifeFace', f"(GW|Call|BP_GW_GameMode|LifePoiLook :self gm :I {L('Pi')})")}
      {S_('LifeKindNow', f"(GW|Call|BP_GW_GameMode|LifePoiKind :self gm :I {L('Pi')})")}
      {S_('LifeMode', '1')}
      ; a long walk is rarely a straight line: a detour through the middle
      (if (and (> {DIST2(LOC('Ch'), L('Dst'))} 1300.0) (< {RND} 0.3))
        (bind (wd wok) (AI|Navigation|GetRandomReachablePointinRadius :Origin (* (+ {L('Dst')} {LOC('Ch')}) 0.5) :Radius 350.0))
        (if wok
          {S_('FinalDest', L('Dst'))}
          {S_('HasFinal', 'true')}
          (CallFunction|LifeMove :Dest wd :Accept 90.0)
          (return true)))
      (CallFunction|LifeMove :Dest {L('Dst')} :Accept 40.0)
      (return true))
    (:CastFailed (return false))))
'''
    NW['LifeWall'] = f'''
(fn LifeWall (Ch)
  (bind gm {GMC}
    (:then
      {S_('LifeMode', '4')}
      (bind rm (GW|Call|BP_GW_GameMode|LifeRoomOf :self gm :Loc {LOC('Ch')}))
      (bind wp (GW|Call|BP_GW_GameMode|LifeWallPoint :self gm :Room rm))
      (CallFunction|LifeMove :Dest wp :Accept 60.0))
    (:CastFailed)))
'''
    NW['LifeLookAround'] = f'''
(fn LifeLookAround (Ch Dur)
  {S_('LifeMode', '6')}
  {S_('NextMoveTime', f'(+ {NOW} Dur)')}
  {S_('GlanceNext', NOW)})
'''
    NW['LifeGlance'] = f'''
(fn LifeGlance (Ch)
  {S_('GlanceNext', f'(+ {NOW} {RF(2.2, 6.5)})')}
  {S_('LifeRoll', RND)}
  (bind r {G_('LifeRoll')})
  (if (> {CH('TalkUntil', 'Ch')} {NOW})
    (return))
  (if (and (== {G_('LifeMode')} 2) (< r 0.45))
    (CallFunction|FaceAt :P {G_('LifeFace')})
    (return))
  (if (< r 0.7)
    (bind gm {GMC}
      (:then
        (bind who (GW|Call|BP_GW_GameMode|LifePasser :self gm :Ch Ch))
        (if ({ISVALID} :Object who)
          (CallFunction|FaceAt :P {LOC('who')})
          (return)))
      (:CastFailed)))
  {S_('LifeRoll', RF(-75, 75))}
  (CallFunction|FaceAt :P (+ {LOC('Ch')} (* (Math|Vector|GetForwardVector (Math|Rotator|MakeRotator :Yaw (+ (.yaw (Transformation|GetActorRotation :self Ch)) {G_('LifeRoll')}))) 300.0))))
'''
    # walking beside another guest; when he stops, stand with him until he moves on or this guest has had enough
    NW['LifeFollow'] = f'''
(fn LifeFollow (Ch)
  (bind l {G_('Partner')})
  (bind now {NOW})
  (if (not ({ISVALID} :Object l))
    (CallFunction|LifeDrop :Ch Ch)
    {S_('NextMoveTime', f'(+ now {RF(0.3, 2.0)})')}
    (return))
  (if (or (or {CH('IsDead', 'l')} (>= now {G_('LifeUntil')})) (Pawn|IsPlayerControlled :self l))
    (CallFunction|LifeDrop :Ch Ch)
    {S_('NextMoveTime', f'(+ now {RF(0.3, 2.0)})')}
    (return))
  (bind lo {LOC('l')})
  (bind d {DIST2('lo', LOC('Ch'))})
  (bind ls (Math|Vector|VectorLength (Transformation|GetVelocity :self l)))
  (if (or (> ls 25.0) (> d 300.0))
    (CallFunction|FaceRelease)
    (bind rot (Transformation|GetActorRotation :self l))
    (AI|Navigation|MovetoLocation :self self :Dest (+ lo (+ (* (Math|Vector|GetForwardVector rot) -30.0) (* (Math|Vector|GetRightVector rot) {G_('LifeSide')}))) :AcceptanceRadius 25.0 :bStopOnOverlap false :bUsePathfinding true :bProjectDestinationToNavigation true :bCanStrafe false :bAllowPartialPath true)
    {S_('IsMoving', 'true')}
    {S_('MoveStartTime', 'now')}
    (Class|CharacterMovementComponent|SetMaxWalkSpeed :self {CMOV()} :MaxWalkSpeed (Math|Float|Clamp(Float) :Value (* (Math|Float|Max(Float) ls 150.0) (select (> d 230.0) 1.2 (select (< d 110.0) 0.88 1.0))) :Min 120.0 :Max 215.0))
    (return))
  (if {G_('IsMoving')}
    (AI|Navigation|StopMovement :self self)
    {S_('IsMoving', 'false')})
  (CallFunction|FaceAt :P lo))
'''
    NW['LifeGesture'] = f'''
(fn LifeGesture (Ch)
  (if {CH('GestureOn', 'Ch')}
    (return))
  {S_('GestNext', f'(+ {NOW} {RF(5, 12)})')}
  {S_('LifeRoll', RND)}
  (bind g {G_('LifeRoll')})
  {CHS('DanceByPlayer', 'Ch', 'false')}
  {S_('LifeGest', 'true')}
  {CHS('DanceId', 'Ch', '(select (< g 0.3) 0 (select (< g 0.62) 7 (select (< g 0.92) 6 8)))')})
'''
    NW['LifeCircle'] = f'''
(fn LifeCircle (Ch)
  (bind now {NOW})
  (bind gm {GMC}
    (:then
      (bind copen (GW|Call|BP_GW_GameMode|LifeCircleOpen :self gm :I {G_('LifeCircleI')}))
      (if (or (>= now {G_('LifeUntil')}) (not copen))
        (CallFunction|LifeDrop :Ch Ch)
        {S_('NextMoveTime', f'(+ now {RF(0.2, 1.6)})')}
        (return))
      (if {G_('IsMoving')}
        (bind since (- now {G_('MoveStartTime')}))
        (if (or (< {DIST2(LOC('Ch'), G_('LifeDest'))} 45.0) (or (and (> since 1.0) (< (Math|Vector|VectorLength (Transformation|GetVelocity :self Ch)) 3.0)) (> since 25.0)))
          (AI|Navigation|StopMovement :self self)
          {S_('IsMoving', 'false')}
          (CallFunction|FaceAt :P {G_('LifeFace')})
          {S_('GestNext', f'(+ now {RF(0.5, 3.0)})')}
          {S_('GlanceNext', f'(+ now {RF(3, 8)})')})
        (return))
      (if (>= now {G_('GestNext')})
        (CallFunction|LifeGesture :Ch Ch)
        (return))
      ; eyes on the others, a look away now and then
      (if (>= now {G_('GlanceNext')})
        {S_('GlanceNext', f'(+ now {RF(3, 8)})')}
        (CallFunction|FaceAt :P (+ {G_('LifeFace')} {V(RF(-120, 120), RF(-120, 120))}))))
    (:CastFailed)))
'''
    # out of a pair or a circle, whatever happened
    NW['LifeDrop'] = f'''
(fn LifeDrop (Ch)
  (bind m {G_('LifeMode')})
  {S_('LifeMode', '0')}
  {S_('LifeChainN', '0')}
  (if (and {G_('LifeGest')} ({ISVALID} :Object Ch))
    {S_('LifeGest', 'false')}
    (if (and (>= {CH('DanceId', 'Ch')} 6) (<= {CH('DanceId', 'Ch')} 8))
      {CHS('DanceId', 'Ch', '0')}))
  (bind gm {GMC}
    (:then
      (if (== m 5)
        (GW|Call|BP_GW_GameMode|LifeCircleLeave :self gm :I {G_('LifeCircleI')}))
      (if (== m 3)
        (GW|Call|BP_GW_GameMode|LifeUnfollow :self gm :Leader {G_('Partner')})
        {S_('Partner', G_('NoPartner'))}))
    (:CastFailed)))
'''
    NW['LifeUnstick'] = f'''
(fn LifeUnstick (Ch)
  {S_('MoveFails', '0')}
  {S_('LifeMode', '0')}
  {S_('LifeRoll', RF(-180, 180))}
  (bind here {LOC('Ch')})
  (bind (pp pok) (AI|Navigation|ProjectPointtoNavigation :Point here :QueryExtent {V(400.0, 400.0, 200.0)}))
  ; off the navmesh (a prop pushed him, a seat): walk straight back onto it. On it: a few steps in any direction
  (bind dest (select (and pok (> {DIST2('pp', 'here')} 30.0)) pp (+ here (* (Math|Vector|GetForwardVector (Math|Rotator|MakeRotator :Yaw {G_('LifeRoll')})) 180.0))))
  (CallFunction|FaceRelease)
  {S_('LifeDest', 'dest')}
  (AI|Navigation|MovetoLocation :self self :Dest dest :AcceptanceRadius 30.0 :bStopOnOverlap false :bUsePathfinding false :bProjectDestinationToNavigation false :bCanStrafe false :bAllowPartialPath true)
  {S_('IsMoving', 'true')}
  {S_('MoveStartTime', NOW)}
  {LOG(f'(cat "GW: life unstick " (Utilities|GetDisplayName :Object Ch) " at " here)')})
'''
    # NPC against NPC. Stalled while wanting to move, with someone within reach ahead: the one with the lower priority (standing guests never yield, then
    # the slower pace yields) steps aside to its right and carries on, like people in a corridor. Still jammed after 2 s: those two ignore each other's capsule for 1.5 s and walk through the jam.
    # far from every player the movement component runs at 20 Hz (a client interpolates anyway; only a host looking 22 m away could see it)
    NW['LifeLod'] = f'''
(fn LifeLod (Ch)
  (bind gm {GMC}
    (:then
      (bind d (GW|Call|BP_GW_GameMode|NearPlayerD :self gm :Loc {LOC('Ch')}))
      (bind far (> d (select {G_('LodFar')} 2000.0 2300.0)))
      (if (!= far {G_('LodFar')})
        {S_('LodFar', 'far')}
        (Components|Tick|SetComponentTickInterval :self {CMOV()} :TickInterval (select far 0.05 0.0))))
    (:CastFailed)))
'''
    NW['LifeBlockCheck'] = f'''
(fn LifeBlockCheck (Ch)
  (bind now {NOW})
  (if (and (> {G_('IgnoreUntil')} 0.0) (>= now {G_('IgnoreUntil')}))
    {S_('IgnoreUntil', '0.0')}
    (GW|Call|/Script/Engine.PrimitiveComponent|ClearMoveIgnoreActors :self (GW|Get|/Script/Engine.Character|CapsuleComponent :self Ch))
    (if ({ISVALID} :Object {G_('IgnoreWho')})
      (GW|Call|/Script/Engine.PrimitiveComponent|ClearMoveIgnoreActors :self (GW|Get|/Script/Engine.Character|CapsuleComponent :self {G_('IgnoreWho')}))))
  (if (not {G_('IsMoving')})
    {S_('BlockN', '0')}
    (return false))
  (bind vel (Math|Vector|VectorLength (Transformation|GetVelocity :self Ch)))
  (if (> vel 60.0)
    {S_('BlockRounds', '0')})
  (if (or (< (- now {G_('MoveStartTime')}) 1.0) (> vel 30.0))
    {S_('BlockN', '0')}
    (return false))
  ; stopping next to someone at the end of a walk is arriving, not being blocked; a queue waits by nature; after two rounds the normal failure takes over (another target)
  (if (or (< {DIST2(LOC('Ch'), G_('LifeDest'))} 130.0) (or (== {G_('LifeMode')} 7) (>= {G_('BlockRounds')} 2)))
    {S_('BlockN', '0')}
    (return false))
  (bind gm {GMC}
    (:then
      (if (not (GW|Get|BP_GW_GameMode|LifeBlockOn :self gm))
        (return false))
      (bind (who yld) (GW|Call|BP_GW_GameMode|LifeBlocker :self gm :Ch Ch :Dest {G_('LifeDest')} :Pace {G_('PPace')}))
      (if (not ({ISVALID} :Object who))
        {S_('BlockN', '0')}
        (return false))
      {S_('BlockN', f"(+ {G_('BlockN')} 1)")}
      (bind n {G_('BlockN')})
      (if (and yld (== n 1))
        (bind me {LOC('Ch')})
        (bind away (Math|Vector|Normalize (- me {LOC('who')})))
        (bind side (+ me (+ (* {V('(- 0.0 (.y away))', '(.x away)')} {RF(100, 145)}) (* away {RF(10, 50)}))))
        (if (and (== {G_('SocialMode')} 0) (not {G_('HasFinal')}))
          {S_('FinalDest', G_('LifeDest'))}
          {S_('HasFinal', 'true')})
        (CallFunction|FaceRelease)
        (AI|Navigation|MovetoLocation :self self :Dest side :AcceptanceRadius 30.0 :bStopOnOverlap false :bUsePathfinding true :bProjectDestinationToNavigation true :bCanStrafe false :bAllowPartialPath true)
        {S_('MoveStartTime', 'now')}
        (return true))
      (if (>= n 4)
        (GW|Call|/Script/Engine.PrimitiveComponent|IgnoreActorWhenMoving :self (GW|Get|/Script/Engine.Character|CapsuleComponent :self Ch) :Actor who :bShouldIgnore true)
        (GW|Call|/Script/Engine.PrimitiveComponent|IgnoreActorWhenMoving :self (GW|Get|/Script/Engine.Character|CapsuleComponent :self who) :Actor Ch :bShouldIgnore true)
        {S_('IgnoreWho', 'who')}
        {S_('IgnoreUntil', '(+ now 1.5)')}
        {S_('BlockN', '0')}
        {S_('BlockRounds', f"(+ {G_('BlockRounds')} 1)")}
        (AI|Navigation|MovetoLocation :self self :Dest {G_('LifeDest')} :AcceptanceRadius 30.0 :bStopOnOverlap false :bUsePathfinding true :bProjectDestinationToNavigation true :bCanStrafe false :bAllowPartialPath true)
        {S_('MoveStartTime', 'now')}
        (return true))
      ; wait a moment: the other one is stepping aside
      (return true))
    (:CastFailed (return false))))
'''
    # in line at a bar: wait, shuffle forward when the line moves, tell the barman at the counter
    NW['LifeQThink'] = f'''
(fn LifeQThink (Ch)
  (bind now {NOW})
  (if (>= now {G_('LifeUntil')})
    (CallFunction|LifeDrop :Ch Ch)
    ; a drink in hand: a table or a seat next
    {S_('LifeChainN', '1')}
    {S_('ChainKind', '4')}
    {S_('NextMoveTime', f'(+ now {RF(0.2, 1.5)})')}
    (return))
  (if {G_('IsMoving')}
    (bind since (- now {G_('MoveStartTime')}))
    (bind far {DIST2(LOC('Ch'), G_('QSpot'))})
    (if (or (< far 22.0) (or (and (> since 1.0) (< (Math|Vector|VectorLength (Transformation|GetVelocity :self Ch)) 3.0)) (> since 40.0)))
      (AI|Navigation|StopMovement :self self)
      {S_('IsMoving', 'false')}
      (CallFunction|FaceAt :P {G_('LifeFace')})
      (if (> far 45.0)
        {S_('QNext', f'(+ now {RF(0.4, 1.2)})')}))
    (return))
  (if (and (> {G_('QNext')} 0.0) (>= now {G_('QNext')}))
    {S_('QNext', '0.0')}
    (CallFunction|LifeMove :Dest {G_('QSpot')} :Accept 14.0)
    (return))
  (if (and (== {G_('QSlot')} 0) (>= now {G_('GestNext')}))
    (CallFunction|LifeGesture :Ch Ch)
    (return))
  (if (>= now {G_('GlanceNext')})
    {S_('GlanceNext', f'(+ now {RF(2.5, 7)})')}
    (if (< {RND} 0.65)
      (CallFunction|FaceAt :P {G_('LifeFace')})
      (else
        {S_('LifeRoll', RF(-80, 80))}
        (CallFunction|FaceAt :P (+ {LOC('Ch')} (* (Math|Vector|GetForwardVector (Math|Rotator|MakeRotator :Yaw (+ (.yaw (Transformation|GetActorRotation :self Ch)) {G_('LifeRoll')}))) 300.0)))))))
'''
    NW['LifeTryExtra'] = f'''
(fn LifeTryExtra (Ch Which)
  (bind gm {GMC}
    (:then
      (if (== Which 0)
        (bind q (GW|Call|BP_GW_GameMode|LifeQJoin :self gm :Ch Ch))
        (return q))
      (bind d (GW|Call|BP_GW_GameMode|LifeDanceJoin :self gm :Ch Ch))
      (return d))
    (:CastFailed (return false))))
'''
    NW['LifeUnwedge'] = f'''
(fn LifeUnwedge (Ch)
  (bind here {LOC('Ch')})
  (bind (nd nok) (AI|Navigation|GetRandomLocationinNavigableRadius :Origin here :Radius 320.0))
  {S_('StillSince', NOW)}
  (if (not nok)
    (return))
  (AI|Navigation|StopMovement :self self)
  (CallFunction|FaceRelease)
  {S_('IsMoving', 'false')}
  {S_('HasFinal', 'false')}
  {S_('MoveFails', '0')}
  {S_('SeatState', '5')}
  (Pawn|Components|CharacterMovement|DisableMovement :self {CMOV()})
  {S_('SlideTo', f"(Math|Vector|MakeVector (.x nd) (.y nd) (.z here))")}
  {S_('YawTo', '(.yaw (Transformation|GetActorRotation :self Ch))')}
  (CallFunction|SitSlideStart :Ch Ch)
  {LOG(f'(cat "GW: life unwedge " (Utilities|GetDisplayName :Object Ch) " at " here)')})
'''
    NW['LifeTrySocial'] = f'''
(fn LifeTrySocial (Ch)
  (bind gm {GMC}
    (:then
      (bind ok (GW|Call|BP_GW_GameMode|LifeSocial :self gm :Ch Ch :Social {G_('PSocial')}))
      (return ok))
    (:CastFailed (return false))))
'''
    NW['ChooseMove'] = f'''
(fn ChooseMove (Ch)
  (CallFunction|LifeNext :Ch Ch))
'''
    # the next thing to do. Weights by mood (0 mingle, 1 explore, 2 lounge, 3 sightsee) and personality
    NW['LifeNext'] = f'''
(fn LifeNext (Ch)
  (bind now {NOW})
  {S_('Partner', G_('NoPartner'))}
  (if (> {CH('TalkUntil', 'Ch')} now)
    {S_('NextMoveTime', CH('TalkUntil', 'Ch'))}
    (return))
  {S_('BlockRounds', '0')}
  (if {G_('LifeGest')}
    {S_('LifeGest', 'false')}
    {CHS('DanceId', 'Ch', '0')})
  (if (>= now {G_('MoodUntil')})
    {S_('MoodUntil', f'(+ now {RF(40, 150)})')}
    {S_('LifeRoll', RND)}
    {S_('Mood', f"(select (< {G_('LifeRoll')} (* 0.6 {G_('PSocial')})) 0 {RI(1, 3)})")})
  (if (>= {G_('MoveFails')} 3)
    (CallFunction|LifeUnstick :Ch Ch)
    (return))
  {S_('LifeMode', '0')}
  (if (> {G_('LifeChainN')} 0)
    {S_('LifeChainN', f"(- {G_('LifeChainN')} 1)")}
    (if (== {G_('ChainKind')} 9)
      (CallFunction|LifeWall :Ch Ch)
      (return))
    (if (and (== {G_('ChainKind')} 4) (< {RND} 0.5))
      (if (CallFunction|SitTry :Ch Ch)
        (return)))
    (if (CallFunction|LifeGoPoi :Ch Ch :Room (CallFunction|LifeRoomPick :Ch Ch) :Kind {G_('ChainKind')})
      (return)))
  (if (>= now {G_('ToiletAt')})
    {S_('ToiletAt', f'(+ now {RF(200, 600)})')}
    (if (CallFunction|LifeGoPoi :Ch Ch :Room 1 :Kind 6)
      (return)))
  (if (CallFunction|LifeTryExtra :Ch Ch :Which 1)
    (return))
  {S_('LifeRoll', RND)}
  (bind r {G_('LifeRoll')})
  (bind m {G_('Mood')})
  (bind pSoc (select (== m 0) 0.5 (+ 0.08 (* 0.25 {G_('PSocial')}))))
  (bind pSit (+ pSoc (+ 0.05 (+ (* 0.14 {G_('PRest')}) (select (== m 2) 0.22 0.0)))))
  (bind pPause (+ pSit 0.08))
  (bind pWall (+ pPause (select (== m 1) 0.22 0.1)))
  (if (< r pSoc)
    (if (CallFunction|LifeTrySocial :Ch Ch)
      (return)))
  (if (and (>= r pSoc) (< r pSit))
    (if (CallFunction|SitTry :Ch Ch)
      (return)))
  (if (and (>= r pSit) (< r pPause))
    (CallFunction|LifeLookAround :Ch Ch :Dur {RF(3, 9)})
    (return))
  (if (and (>= r pPause) (< r pWall))
    {S_('LifeChainN', RI(1, 3))}
    {S_('ChainKind', '9')}
    (CallFunction|LifeWall :Ch Ch)
    (return))
  ; a point of interest: the mood says which kind
  {S_('LifeRoll', RND)}
  (bind q {G_('LifeRoll')})
  (bind kk (select (== m 3) (select (< q 0.5) 0 (select (< q 0.75) 5 1)) (select (== m 2) (select (< q 0.35) 3 (select (< q 0.7) 4 7)) (select (== m 0) (select (< q 0.4) 3 (select (< q 0.7) 2 4)) (select (< q 0.3) 0 (select (< q 0.5) 5 (select (< q 0.7) 1 (select (< q 0.85) 2 4))))))))
  (if (== kk 3)
    (if (CallFunction|LifeTryExtra :Ch Ch :Which 0)
      (return)))
  (if (CallFunction|LifeGoPoi :Ch Ch :Room (CallFunction|LifeRoomPick :Ch Ch) :Kind kk)
    (return))
  (bind (hd hok) (AI|Navigation|GetRandomReachablePointinRadius :Origin {LOC('Ch')} :Radius 600.0))
  (if hok
    (CallFunction|LifeMove :Dest hd :Accept 60.0)
    (return))
  {S_('MoveFails', f"(+ {G_('MoveFails')} 1)")}
  {S_('NextMoveTime', f'(+ now {RF(0.5, 1.5)})')})
'''
    # seats: walk close, then slide into the seat in a moment instead of jumping there
    NW['SitTry'] = f'''
(fn SitTry (Ch)
  (if (!= {G_('SocialMode')} 0)
    (return false))
  (bind gm {GMC}
    (:then
      {S_('SeatIdx', f"(GW|Call|BP_GW_GameMode|SeatClaim :self gm :From {LOC('Ch')})")}
      (if (< {G_('SeatIdx')} 0)
        (return false))
      {S_('SeatSpot', f"(GW|Call|BP_GW_GameMode|SeatLoc :self gm :I {G_('SeatIdx')})")}
      {S_('SeatYaw', f"(GW|Call|BP_GW_GameMode|SeatYaw :self gm :I {G_('SeatIdx')})")}
      {S_('SeatState', '1')}
      {S_('SocialMode', '4')}
      {S_('LifeMode', '0')}
      ; random per sit, from a quick rest to a long one: nobody gets up in step
      {S_('LifeRoll', RND)}
      {S_('SeatUntil', f"(* (select (< {G_('LifeRoll')} 0.3) {RF(6, 20)} (select (< {G_('LifeRoll')} 0.72) {RF(20, 60)} (select (< {G_('LifeRoll')} 0.94) {RF(60, 120)} {RF(120, 190)}))) (+ 0.8 (* 0.4 {G_('PRest')})))")}
      {S_('HasFinal', 'false')}
      {S_('Partner', G_('NoPartner'))}
      (CallFunction|LifeMove :Dest (+ {G_('SeatSpot')} (* (Math|Vector|GetForwardVector (Math|Rotator|MakeRotator :Yaw {G_('SeatYaw')})) 75.0)) :Accept 25.0)
      (return true))
    (:CastFailed (return false))))
'''
    NW['SitSlideStart'] = f'''
(fn SitSlideStart (Ch)
  {S_('SlideFrom', LOC('Ch'))}
  {S_('YawFrom', '(.yaw (Transformation|GetActorRotation :self Ch))')}
  {S_('SlideT', '0.0')}
  {S_('SlideDur', f"(Math|Float|Clamp(Float) :Value (/ {DIST2(G_('SlideFrom'), G_('SlideTo'))} 130.0) :Min 0.35 :Max 1.0)")}
  (Utilities|Time|SetTimerbyFunctionName :Object self :FunctionName "SitSlideTick" :Time 0.03 :bLooping true))
'''
    NW['SitSlideTick'] = f'''
(fn SitSlideTick ()
  (bind ch {MYPAWN}
    (:then
      {S_('SlideT', f"(+ {G_('SlideT')} (* 0.03 (/ 1.0 {G_('SlideDur')})))")}
      (bind a (Math|Float|Min(Float) {G_('SlideT')} 1.0))
      (bind s (* a (* a (- 3.0 (* 2.0 a)))))
      (bind dy (Math|Rotator|NormalizeAxis (- {G_('YawTo')} {G_('YawFrom')})))
      (Transformation|SetActorLocationAndRotation :self ch :NewLocation (Math|Vector|Lerp(Vector) :A {G_('SlideFrom')} :B {G_('SlideTo')} :Alpha s) :NewRotation (Math|Rotator|MakeRotator :Yaw (+ {G_('YawFrom')} (* dy s))) :bSweep false :bTeleport true)
      (if (< {G_('SlideT')} 1.0)
        (return))
      (Utilities|Time|ClearTimerbyFunctionName :Object self :FunctionName "SitSlideTick")
      (if (== {G_('SeatState')} 3)
        {S_('SeatState', '2')}
        {S_('SeatUntil', f"(+ {NOW} {G_('SeatUntil')})")}
        {CHS('DanceByPlayer', 'ch', 'false')}
        {CHS('DanceId', 'ch', '10')}
        (return))
      ; standing: walking again
      (Pawn|Components|CharacterMovement|SetMovementMode :self {CMOV('ch')} :NewMovementMode "MOVE_Walking" :NewCustomMode 0)
      (if (== {G_('SeatState')} 5)
        {S_('SeatState', '0')}
        {S_('LifeMode', '0')}
        {S_('NextMoveTime', f'(+ {NOW} {RF(0.2, 1.0)})')}
        (return))
      {S_('SeatState', '0')}
      {S_('SocialMode', '0')}
      {S_('IsMoving', 'false')}
      {S_('NextMoveTime', f'(+ {NOW} {RF(0.2, 1.5)})')}
      {S_('StillSince', NOW)}
      (bind gm {GMC}
        (:then (GW|Call|BP_GW_GameMode|SeatFree :self gm :I {G_('SeatIdx')}))
        (:CastFailed)))
    (:CastFailed
      (Utilities|Time|ClearTimerbyFunctionName :Object self :FunctionName "SitSlideTick"))))
'''
    NW['SitDown'] = f'''
(fn SitDown (Ch)
  (bind here {LOC('Ch')})
  (AI|Navigation|StopMovement :self self)
  (CallFunction|FaceRelease)
  {S_('IsMoving', 'false')}
  {S_('SeatBack', 'here')}
  {S_('SeatState', '3')}
  (Pawn|Components|CharacterMovement|DisableMovement :self {CMOV()})
  {S_('SlideTo', f"(Math|Vector|MakeVector (.x {G_('SeatSpot')}) (.y {G_('SeatSpot')}) (.z here))")}
  {S_('YawTo', G_('SeatYaw'))}
  (CallFunction|SitSlideStart :Ch Ch)
  {LOG(f'(cat "GW: EV sit " (Utilities|GetDisplayName :Object Ch) " seat=" {G_("SeatIdx")} " for " {G_("SeatUntil")} " s")')})
'''
    NW['SitRelease'] = f'''
(fn SitRelease (Ch)
  (bind st {G_('SeatState')})
  (if (== st 4)
    (return))
  (if (or (== st 2) (== st 3))
    (Utilities|Time|ClearTimerbyFunctionName :Object self :FunctionName "SitSlideTick")
    {CHS('DanceId', 'Ch', '0')}
    {S_('SeatState', '4')}
    {S_('SlideTo', G_('SeatBack'))}
    {S_('YawTo', f"(+ {G_('SeatYaw')} {RF(-40, 40)})")}
    (CallFunction|SitSlideStart :Ch Ch)
    (return))
  {S_('SeatState', '0')}
  {S_('SocialMode', '0')}
  {S_('IsMoving', 'false')}
  {S_('NextMoveTime', f'(+ {NOW} {RF(0.5, 3.0)})')}
  (bind gm {GMC}
    (:then (GW|Call|BP_GW_GameMode|SeatFree :self gm :I {G_('SeatIdx')}))
    (:CastFailed)))
'''
    NW['SeatThink'] = f'''
(fn SeatThink (Ch)
  (bind mode {G_('SocialMode')})
  (if (== mode 5)
    (CallFunction|FollowThink :Ch Ch)
    (return true))
  (if (!= mode 4)
    (return false))
  (bind now {NOW})
  (bind st {G_('SeatState')})
  (if (or (== st 3) (== st 4))
    (return true))
  (if (== st 2)
    (if (>= now {G_('SeatUntil')})
      (CallFunction|SitRelease :Ch Ch))
    (return true))
  (bind since (- now {G_('MoveStartTime')}))
  (bind close (< {DIST2(LOC('Ch'), G_('SeatSpot'))} 130.0))
  (if (or close (or (and (> since 1.0) (< (Math|Vector|VectorLength (Transformation|GetVelocity :self Ch)) 3.0)) (> since 30.0)))
    (if close
      (CallFunction|SitDown :Ch Ch)
      (else
        (CallFunction|SitRelease :Ch Ch))))
  (return true))
'''
    NW['EventGraph'] = f'''
(event EventOnPossess (PossessedPawn)
  {S_('IsMoving', 'false')}
  {S_('LifeInitDone', 'false')}
  {S_('NextMoveTime', f'(+ {NOW} {RF(0.3, 6.0)})')}
  ; the 2 Hz brain; the variance keeps the guests out of step
  (Utilities|Time|SetTimerbyFunctionName :Object self :FunctionName "Think" :Time 0.5 :bLooping true :InitialStartDelayVariance 0.5))

(event EventOnUnPossess (UnpossessedPawn)
  (Utilities|Time|ClearTimerbyFunctionName :Object self :FunctionName "SitSlideTick")
  (bind ch (Utilities|Casting|CastToBP_GW_Character UnpossessedPawn)
    (:then
      ; a body taken over (swap gun, zombie) or dead goes back to the players' settings
      (Pawn|Components|CharacterMovement|SetAvoidanceEnabled :self {CMOV('ch')} :bEnable false)
      (Class|CharacterMovementComponent|SetRotationRate :self {CMOV('ch')} :RotationRate (Math|Rotator|MakeRotator :Yaw 500.0))
      (Components|Tick|SetComponentTickInterval :self {CMOV('ch')} :TickInterval 0.0)
      {S_('LodFar', 'false')}
      (Class|CharacterMovementComponent|SetUseControllerDesiredRotation :self {CMOV('ch')} :bUseControllerDesiredRotation false)
      (Class|CharacterMovementComponent|SetOrientRotationtoMovement :self {CMOV('ch')} :bOrientRotationToMovement true)
      (Class|CharacterMovementComponent|SetMaxWalkSpeed :self {CMOV('ch')} :MaxWalkSpeed {CH('WalkSpeed', 'ch')})
      {S_('FaceOn', 'false')}
      (if (and (>= {G_('SeatState')} 2) (not {CH('IsDead', 'ch')}))
        (Transformation|SetActorLocation :self ch :NewLocation {G_('SeatBack')} :bSweep false :bTeleport true)
        (Pawn|Components|CharacterMovement|SetMovementMode :self {CMOV('ch')} :NewMovementMode "MOVE_Walking" :NewCustomMode 0))
      (CallFunction|LifeDrop :Ch ch))
    (:CastFailed)))
'''
    for fn_, locs in (('PaceApply', [('Sp', 'float')]), ('LifeGoPoi', [('Pi', 'int')])):
        g = get_graph(npc, fn_)
        for n_, t_ in locs:
            if n_ not in BT.list_variables(npc, g):
                BT.add_variable(npc, n_, t_, graph=g)
    g = get_graph(npc, 'LifeGoPoi')
    if 'Dst' not in BT.list_variables(npc, g):
        BT.add_struct_variable(npc, 'Dst', V3, graph=g)
    compile_bp(npc, quiet=True)
    ok = True
    for name, code in NW.items():
        try:
            write(npc, name, code, compile_after=False)
        except Exception as e:
            ok = False
    compile_bp(npc)
    print('BP_GW_NPCController', ok, node_problems(npc))
    if ok:
        save(npc)

# ------------------------------------------------------------------ game mode: points, groups, outfits, unseen spawns
if 'gm' in PARTS:
    gm = load_bp('BP_GW_GameMode')
    for v, t in (('LifeCharsAt', 'float'), ('LifeNCir', 'int')):
        ensure_var(gm, v, t, category='GW')
    ensure_var(gm, 'LifeChars', obj_class=chc, array=True, category='GW')
    ensure_var(gm, 'LifeProbe', obj_class=chc, category='GW')
    ensure_var(gm, 'LifeOthers', obj_class=chc, array=True, category='GW')
    for v in ('LifePts', 'LifeLook', 'LifeRMin', 'LifeRMax', 'LifeCirC'):
        ensure_var(gm, v, struct=V3, array=True, category='GW')
    for v in ('LifeKind', 'LifeRFirst', 'LifeRCount', 'LifeHomes', 'LifeCirN', 'OutfitBag'):
        ensure_var(gm, v, 'int', array=True, category='GW')
    ensure_var(gm, 'LifeCirUntil', 'float', array=True, category='GW')
    ensure_var(gm, 'LifeQM', obj_class=chc, array=True, category='GW')
    for v in ('LifeQStart', 'LifeQDir', 'LifeQFace'):
        ensure_var(gm, v, struct=V3, array=True, category='GW')
    for v in ('LifeQCap', 'LifeQN'):
        ensure_var(gm, v, 'int', array=True, category='GW')
    ensure_var(gm, 'LifeQServe', 'float', array=True, category='GW')
    ensure_var(gm, 'LifeQNext', 'float', category='GW')
    locals_ = {'LifeFindLeader': [('Best', chc), ('BestD', 'float')], 'LifePasser': [('Best', chc), ('BestD', 'float')], 'LifeJoinCircle': [], 'LifeFormCircle': [('Slot', 'int'), ('Sum', V3), ('Taken', 'int'), ('Want', 'int')],
               'LifeSpawnT': [('Tr', unreal.Transform.static_struct())], 'LifePoi': [('Hit', 'int')], 'NextOutfit': [('Pick', 'int')], 'SpawnNPC': [('Sp', unreal.Transform.static_struct()), ('Oi', 'int')], 'SpawnPlayerPawn': [('Oi', 'int')], 'LifeState': [('A', 'int'), ('B', 'int'), ('C', 'int'), ('D', 'int'), ('E', 'int'), ('F', 'int')], 'LifeBlocker': [('Best', chc), ('BestD', 'float')], 'LifeQJoin': [('BestL', 'int'), ('BestR', 'float')], 'LifeQPack': [('Keep', 'int')]}
    compile_bp(gm, quiet=True)
    for fn_, locs in locals_.items():
        g = get_graph(gm, fn_)
        for n_, t_ in locs:
            if n_ in BT.list_variables(gm, g):
                continue
            if t_ is chc:
                BT.add_object_variable(gm, n_, chc, graph=g)
            elif isinstance(t_, str):
                BT.add_variable(gm, n_, t_, graph=g)
            else:
                BT.add_struct_variable(gm, n_, t_, graph=g)
    AG = lambda a, i: f'(Utilities|Array|Get(acopy) (Variables|GW|Get{a}) {i})'
    LEN = lambda a: f'(Utilities|Array|Length (Variables|GW|Get{a}))'
    GW_ = {}
    GW_['NextOutfit'] = f'''
(fn NextOutfit ()
  ; a look nobody present wears (corpses included): guests are all different up to NumOutfits (the user, 2026-11-06).
  ; Callers clear the new wearer's OutfitIndex to -1 first. The detective's model is a guest like any other (index 32, s26, s29)
  (Utilities|Array|Clear :TargetArray (Variables|GW|GetOutfitBag))
  (for i (range (Variables|GW|GetNumOutfits))
    (Utilities|Array|Add :TargetArray (Variables|GW|GetOutfitBag) :NewItem i))
  (for w (Actor|GetAllActorsOfClass :ActorClass {CHAR})
    (if (== {CH('Kind', 'w')} 0)
      (Utilities|Array|RemoveItem :TargetArray (Variables|GW|GetOutfitBag) :Item {CH('OutfitIndex', 'w')})))
  ; more guests than looks: only then a look comes twice
  (if (== {LEN('OutfitBag')} 0)
    (return (Math|Random|RandomIntegerinRange 0 (Math|Integer|Max(Integer) (- (Variables|GW|GetNumOutfits) 1) 0))))
  (return {AG('OutfitBag', f"(Math|Random|RandomIntegerinRange 0 (- {LEN('OutfitBag')} 1))")}))
'''
    GW_['LifeRoomOf'] = f'''
(fn LifeRoomOf (Loc)
  (if (> (.z Loc) 450.0)
    (return (- {LEN('LifeRMin')} 1)))
  (for i (range (- {LEN('LifeRMin')} 1))
    (bind a {AG('LifeRMin', 'i')})
    (bind b {AG('LifeRMax', 'i')})
    (if (and (and (>= (.x Loc) (.x a)) (< (.x Loc) (.x b))) (and (>= (.y Loc) (.y a)) (< (.y Loc) (.y b))))
      (return i)))
  (return 3))
'''
    HOMEI = RI(0, '(- ' + LEN('LifeHomes') + ' 1)')
    GW_['LifeHome'] = f'''
(fn LifeHome ()
  (if (== {LEN('LifeHomes')} 0)
    (return 4))
  (return {AG('LifeHomes', HOMEI)}))
'''
    # a few random draws in the room, then anywhere: the kind matters more than the room
    HITR = '(+ ' + AG('LifeRFirst', 'Room') + ' ' + RI(0, '(- ' + AG('LifeRCount', 'Room') + ' 1)') + ')'
    HITANY = HITR
    GW_['LifePoi'] = f'''
(fn LifePoi (Room Kind)
  (bind n {LEN('LifePts')})
  (if (== n 0)
    (return -1))
  (bind rv (and (>= Room 0) (< Room {LEN('LifeRCount')})))
  (if rv
    (if (> {AG('LifeRCount', 'Room')} 0)
      (for t (range 6)
        {SL('Hit', HITR)}
        (if (or (< Kind 0) (== {AG('LifeKind', L('Hit'))} Kind))
          (return {L('Hit')})))
      ; nothing of that kind here: anything else in this room, the guest stays where he likes to be (not for the bar or the toilets)
      (if (and (!= Kind 3) (!= Kind 6))
        (return {HITANY}))))
  (for t (range 24)
    {SL('Hit', RI(0, '(- n 1)'))}
    (if (or (< Kind 0) (== {AG('LifeKind', L('Hit'))} Kind))
      (return {L('Hit')})))
  (return {RI(0, '(- n 1)')}))
'''
    GW_['LifePoiLoc'] = f"(fn LifePoiLoc (I) (return {AG('LifePts', 'I')}))"
    GW_['LifePoiLook'] = f"(fn LifePoiLook (I) (return {AG('LifeLook', 'I')}))"
    GW_['LifePoiKind'] = f"(fn LifePoiKind (I) (return {AG('LifeKind', 'I')}))"
    GW_['LifeWallPoint'] = f'''
(fn LifeWallPoint (Room)
  (bind a {AG('LifeRMin', 'Room')})
  (bind b {AG('LifeRMax', 'Room')})
  (bind sideN (Variables|GW|GetLifeNCir))
  (Variables|GW|SetLifeNCir (+ sideN 1))
  (bind k (% sideN 4))
  (bind ax {RF(0.1, 0.9)})
  (bind x (select (== k 0) (+ (.x a) 125.0) (select (== k 1) (- (.x b) 125.0) (+ (.x a) (* ax (- (.x b) (.x a)))))))
  (bind y (select (== k 2) (+ (.y a) 125.0) (select (== k 3) (- (.y b) 125.0) (+ (.y a) (* ax (- (.y b) (.y a)))))))
  (return {V('x', 'y', '(.z a)')}))
'''
    GW_['LifeRefresh'] = f'''
(fn LifeRefresh ()
  (bind now (CallFunction|Now))
  (if (< now (+ (Variables|GW|GetLifeCharsAt) 2.0))
    (return))
  (Variables|GW|SetLifeCharsAt now)
  (Variables|GW|SetLifeChars (Actor|GetAllActorsOfClass :ActorClass {CHAR})))
'''
    GW_['LifeSocial'] = f'''
(fn LifeSocial (Ch Social)
  (CallFunction|LifeRefresh)
  (if (< {RND} 0.35)
    (if (CallFunction|LifeFindLeader :Ch Ch)
      (return true)))
  (if (CallFunction|LifeJoinCircle :Ch Ch)
    (return true))
  (bind ok (CallFunction|LifeFormCircle :Ch Ch))
  (return ok))
'''
    FREE = lambda o, extra='': f'''(and (and (not (Pawn|IsPlayerControlled :self {o})) (not {CH('IsDead', o)})) (and (== {CH('Kind', o)} 0) (!= {o} Ch)))'''
    GW_['LifeFindLeader'] = f'''
(fn LifeFindLeader (Ch)
  {SL('BestD', '800.0')}
  (bind n {LEN('LifeChars')})
  (if (== n 0)
    (return false))
  (bind here {LOC('Ch')})
  (for t (range 16)
    (bind o {AG('LifeChars', RI(0, '(- n 1)'))})
    (Variables|Default|SetBest o)
    (if ({ISVALID} :Object {L('Best')})
      (if (and (and (not (Pawn|IsPlayerControlled :self {L('Best')})) (not {CH('IsDead', L('Best'))})) (and (== {CH('Kind', L('Best'))} 0) (!= {L('Best')} Ch)))
        (if (< {DIST2(LOC(L('Best')), 'here')} {L('BestD')})
          (bind c {NPCC(L('Best'))}
            (:then
              (if (and (and (== {NC('SocialMode', 'c')} 0) {NC('IsMoving', 'c')}) (and (< {NC('LifeFollowers', 'c')} 2) (or (== {NC('LifeMode', 'c')} 1) (== {NC('LifeMode', 'c')} 4))))
                (bind me {NPCC('Ch')}
                  (:then
                    {NCS('LifeMode', 'me', '3')}
                    {NCS('Partner', 'me', L('Best'))}
                    {NCS('LifeSide', 'me', f"(select (== {NC('LifeFollowers', 'c')} 0) (select (Math|Random|RandomBool) 90.0 -90.0) (* -1.0 {NC('LifeSide', 'c')}))")}
                    {NCS('LifeUntil', 'me', f'(+ (CallFunction|Now) {RF(20, 70)})')}
                    {NCS('LifeFollowers', 'c', f"(+ {NC('LifeFollowers', 'c')} 1)")}
                    (return true))
                  (:CastFailed))))
            (:CastFailed))))))
  (return false))
'''
    GW_['LifeUnfollow'] = f'''
(fn LifeUnfollow (Leader)
  (if (not ({ISVALID} :Object Leader))
    (return))
  (bind c {NPCC('Leader')}
    (:then {NCS('LifeFollowers', 'c', f"(Math|Integer|Max(Integer) (- {NC('LifeFollowers', 'c')} 1) 0)")})
    (:CastFailed)))
'''
    GW_['LifeCircleOpen'] = f'''
(fn LifeCircleOpen (I)
  (if (or (< I 0) (>= I {LEN('LifeCirN')}))
    (return false))
  (return (and (>= {AG('LifeCirN', 'I')} 2) (> {AG('LifeCirUntil', 'I')} (CallFunction|Now)))))
'''
    GW_['LifeCircleLeave'] = f'''
(fn LifeCircleLeave (I)
  (if (or (< I 0) (>= I {LEN('LifeCirN')}))
    (return))
  (Utilities|Array|SetArrayElem :TargetArray (Variables|GW|GetLifeCirN) :Index I :Item (Math|Integer|Max(Integer) (- {AG('LifeCirN', 'I')} 1) 0) :bSizeToFit false))
'''
    GW_['LifeCircleAdd'] = f'''
(fn LifeCircleAdd (Ch I)
  (bind k {AG('LifeCirN', 'I')})
  (Utilities|Array|SetArrayElem :TargetArray (Variables|GW|GetLifeCirN) :Index I :Item (+ k 1) :bSizeToFit false)
  (Utilities|Array|SetArrayElem :TargetArray (Variables|GW|GetLifeCirUntil) :Index I :Item (+ (CallFunction|Now) 70.0) :bSizeToFit false)
  (bind c {NPCC('Ch')}
    (:then
      (AI|Navigation|StopMovement :self c)
      {NCS('LifeCircleI', 'c', 'I')}
      {NCS('LifeMode', 'c', '5')}
      {NCS('HasFinal', 'c', 'false')}
      {NCS('LifeFace', 'c', AG('LifeCirC', 'I'))}
      {NCS('LifeUntil', 'c', f"(+ (CallFunction|Now) (* {RF(14, 42)} (+ 0.7 (* 0.6 {NC('PSocial', 'c')}))))")}
      (bind ang (+ (* (float_) 137.5) {RF(-18, 18)}))
      (bind rad (+ 80.0 {RF(0, 25)}))
      (GW|Call|BP_GW_NPCController|LifeMove :self c :Dest (+ {AG('LifeCirC', 'I')} (* (Math|Vector|GetForwardVector (Math|Rotator|MakeRotator :Yaw ang)) rad)) :Accept 15.0))
    (:CastFailed)))
'''.replace('(float_)', '(Math|Conversions|ToFloat(Integer) k)' if False else 'k')
    GW_['LifeJoinCircle'] = f'''
(fn LifeJoinCircle (Ch)
  (bind here {LOC('Ch')})
  (bind now (CallFunction|Now))
  (for i (range {LEN('LifeCirN')})
    (bind k {AG('LifeCirN', 'i')})
    (if (and (>= k 2) (< k 5))
      (if (> {AG('LifeCirUntil', 'i')} now)
        (if (< {DIST2(AG('LifeCirC', 'i'), 'here')} 900.0)
          (CallFunction|LifeCircleAdd :Ch Ch :I i)
          (return true)))))
  (return false))
'''
    GW_['LifeFormCircle'] = f'''
(fn LifeFormCircle (Ch)
  (bind now (CallFunction|Now))
  {SL('Slot', '-1')}
  (for i (range {LEN('LifeCirN')})
    (if (or (<= {AG('LifeCirN', 'i')} 0) (<= {AG('LifeCirUntil', 'i')} now))
      {SL('Slot', 'i')}
      (break)))
  (if (< {L('Slot')} 0)
    (return false))
  (bind here {LOC('Ch')})
  {SL('Want', RI(1, 3))}
  {SL('Taken', '0')}
  {SL('Sum', 'here')}
  (Utilities|Array|Clear (Variables|GW|GetLifeOthers))
  (for o (Variables|GW|GetLifeChars)
    (if ({ISVALID} :Object o)
      (if (and (< {L('Taken')} {L('Want')}) (< {DIST2(LOC('o'), 'here')} 650.0))
        (if {FREE('o')}
          (bind c {NPCC('o')}
            (:then
              (if (and (and (== {NC('SocialMode', 'c')} 0) (> now {NC('PanicUntil', 'c')})) (or (== {NC('LifeMode', 'c')} 0) (or (== {NC('LifeMode', 'c')} 2) (== {NC('LifeMode', 'c')} 6))))
                (Utilities|Array|Add :TargetArray (Variables|GW|GetLifeOthers) :NewItem o)
                {SL('Taken', f"(+ {L('Taken')} 1)")}
                {SL('Sum', f"(+ {L('Sum')} {LOC('o')})")}))
            (:CastFailed))))))
  (if (== {L('Taken')} 0)
    (return false))
  (Utilities|Array|SetArrayElem :TargetArray (Variables|GW|GetLifeCirC) :Index {L('Slot')} :Item (* {L('Sum')} (/ 1.0 (+ {L('Taken')} 1))) :bSizeToFit false)
  (Utilities|Array|SetArrayElem :TargetArray (Variables|GW|GetLifeCirN) :Index {L('Slot')} :Item 0 :bSizeToFit false)
  (CallFunction|LifeCircleAdd :Ch Ch :I {L('Slot')})
  (for o (Variables|GW|GetLifeOthers)
    (CallFunction|LifeCircleAdd :Ch o :I {L('Slot')}))
  (return true))
'''
    GW_['LifePasser'] = f'''
(fn LifePasser (Ch)
  (CallFunction|LifeRefresh)
  (Variables|Default|SetBest (Variables|GW|GetNoChar))
  {SL('BestD', '550.0')}
  (bind n {LEN('LifeChars')})
  (if (== n 0)
    (return {L('Best')}))
  (bind here {LOC('Ch')})
  (for t (range 5)
    (Variables|GW|SetLifeProbe {AG('LifeChars', RI(0, '(- n 1)'))})
    (bind o (Variables|GW|GetLifeProbe))
    (if ({ISVALID} :Object o)
      (if (!= o Ch)
        (bind d {DIST2(LOC('o'), 'here')})
        (if (< d {L('BestD')})
          (if (> (Math|Vector|VectorLength (Transformation|GetVelocity :self o)) 30.0)
            {SL('BestD', 'd')}
            (Variables|Default|SetBest o))))))
  (return {L('Best')}))
'''
    GW_['LifeUnseen'] = f'''
(fn LifeUnseen (Loc MinD)
  (for ps (CallFunction|GetGWPlayers)
    (bind p (PlayerState|GetPawn :self ps))
    (if ({ISVALID} :Object p)
      (bind pl {LOC('p')})
      (if (< (Math|Vector|Distance(Vector) pl Loc) MinD)
        (return false))
      (bind (hit blocked) (Collision|LineTraceByChannel :Start (+ pl {V(0.0, 0.0, 60.0)}) :End (+ Loc {V(0.0, 0.0, 50.0)}) :TraceChannel "Visibility" :bTraceComplex false :bIgnoreSelf true))
      (if (not blocked)
        (return false))))
  (return true))
'''
    GW_['LifeSpawnT'] = f'''
(fn LifeSpawnT ()
  (for t (range 10)
    {SL('Tr', '(CallFunction|RandomSpawnTransform)')}
    (if (CallFunction|LifeUnseen :Loc (.location {L('Tr')}) :MinD 900.0)
      (return {L('Tr')})))
  (return {L('Tr')}))
'''
    GW_['LifeBlocker'] = f'''
(fn LifeBlocker (Ch Dest Pace)
  (CallFunction|LifeRefresh)
  (Variables|Default|SetBest (Variables|GW|GetNoChar))
  {SL('BestD', '125.0')}
  (bind here {LOC('Ch')})
  (bind ahead (Math|Vector|Normalize (- Dest here)))
  (for o (Variables|GW|GetLifeChars)
    (if ({ISVALID} :Object o)
      (if (and (!= o Ch) (not {CH('IsDead', 'o')}))
        (bind d {DIST2(LOC('o'), 'here')})
        (if (< d {L('BestD')})
          (if (> (Math|Vector|DotProduct ahead (Math|Vector|Normalize (- {LOC('o')} here))) -0.1)
            {SL('BestD', 'd')}
            (Variables|Default|SetBest o))))))
  (bind w {L('Best')})
  (if (not ({ISVALID} :Object w))
    (return w false))
  (bind c {NPCC('w')}
    (:then
      (if (not {NC('IsMoving', 'c')})
        (return w true))
      (return w (or (< Pace {NC('PPace', 'c')}) (and (== Pace {NC('PPace', 'c')}) (== {RI(0, 1)} 0)))))
    (:CastFailed (return w true))))
'''
    QSPOT = '(+ ' + AG('LifeQStart', 'Line') + ' (+ (* ' + AG('LifeQDir', 'Line') + ' (* Slot 100.0)) ' + V(RF(-10, 10), RF(-10, 10)) + '))'
    GW_['LifeQMember'] = f'''
(fn LifeQMember (Ch Line)
  (if (not ({ISVALID} :Object Ch))
    (return false))
  (if {CH('IsDead', 'Ch')}
    (return false))
  (bind c {NPCC('Ch')}
    (:then (return (and (== {NC('LifeMode', 'c')} 7) (== {NC('QLine', 'c')} Line))))
    (:CastFailed (return false))))
'''
    GW_['LifeQAssign'] = f'''
(fn LifeQAssign (Ch Line Slot)
  (bind c {NPCC('Ch')}
    (:then
      {NCS('QLine', 'c', 'Line')}
      {NCS('QSlot', 'c', 'Slot')}
      {NCS('QSpot', 'c', QSPOT)}
      {NCS('LifeFace', 'c', AG('LifeQFace', 'Line'))}
      ; the line moves up person by person, not as one block
      {NCS('QNext', 'c', f'(+ (CallFunction|Now) (+ (* Slot 0.3) {RF(0.1, 0.7)}))')})
    (:CastFailed)))
'''
    GW_['LifeQJoin'] = f'''
(fn LifeQJoin (Ch)
  {SL('BestL', '-1')}
  {SL('BestR', '10.0')}
  (for i (range {LEN('LifeQCap')})
    (bind k {AG('LifeQN', 'i')})
    (bind cp {AG('LifeQCap', 'i')})
    (if (< k cp)
      (bind rr (/ (+ k {RF(0.0, 0.6)}) cp))
      (if (< rr {L('BestR')})
        {SL('BestR', 'rr')}
        {SL('BestL', 'i')})))
  (bind ln {L('BestL')})
  (if (< ln 0)
    (return false))
  (bind sl {AG('LifeQN', 'ln')})
  (bind c {NPCC('Ch')}
    (:then
      (if (!= {NC('LifeMode', 'c')} 0)
        (GW|Call|BP_GW_NPCController|LifeDrop :self c :Ch Ch))
      (AI|Navigation|StopMovement :self c)
      {NCS('IsMoving', 'c', 'false')}
      {NCS('HasFinal', 'c', 'false')}
      {NCS('LifeMode', 'c', '7')}
      {NCS('LifeUntil', 'c', f'(+ (CallFunction|Now) {RF(90, 200)})')}
      {NCS('GestNext', 'c', '(+ (CallFunction|Now) 2.0)')}
      {NCS('GlanceNext', 'c', '(+ (CallFunction|Now) 4.0)')}
      (Utilities|Array|SetArrayElem :TargetArray (Variables|GW|GetLifeQM) :Index (+ (* ln 12) sl) :Item Ch :bSizeToFit true)
      (Utilities|Array|SetArrayElem :TargetArray (Variables|GW|GetLifeQN) :Index ln :Item (+ sl 1) :bSizeToFit false)
      (CallFunction|LifeQAssign :Ch Ch :Line ln :Slot sl)
      (return true))
    (:CastFailed (return false))))
'''
    # members who left (served, tired of waiting, panic, a dance...) drop out; everyone behind moves up
    GW_['LifeQPack'] = f'''
(fn LifeQPack (Line)
  (bind base (* Line 12))
  {SL('Keep', '0')}
  (for i (range {AG('LifeQN', 'Line')})
    (Variables|GW|SetLifeProbe {AG('LifeQM', '(+ base i)')})
    (bind isin (CallFunction|LifeQMember :Ch (Variables|GW|GetLifeProbe) :Line Line))
    (if isin
      (if (!= {L('Keep')} i)
        (Utilities|Array|SetArrayElem :TargetArray (Variables|GW|GetLifeQM) :Index (+ base {L('Keep')}) :Item (Variables|GW|GetLifeProbe) :bSizeToFit true)
        (CallFunction|LifeQAssign :Ch (Variables|GW|GetLifeProbe) :Line Line :Slot {L('Keep')}))
      {SL('Keep', f"(+ {L('Keep')} 1)")}))
  (Utilities|Array|SetArrayElem :TargetArray (Variables|GW|GetLifeQN) :Index Line :Item {L('Keep')} :bSizeToFit false))
'''
    # from SocialTick (4 Hz, during a round, calm only): serve the heads, keep the lines long
    GW_['LifeQTick'] = f'''
(fn LifeQTick ()
  (bind now (CallFunction|Now))
  (if (< now (Variables|GW|GetLifeQNext))
    (return))
  (Variables|GW|SetLifeQNext (+ now 1.0))
  (for ln (range {LEN('LifeQCap')})
    (CallFunction|LifeQPack :Line ln)
    (if (and (> {AG('LifeQN', 'ln')} 0) (>= now {AG('LifeQServe', 'ln')}))
      (Utilities|Array|SetArrayElem :TargetArray (Variables|GW|GetLifeQServe) :Index ln :Item (+ now {RF(6, 13)}) :bSizeToFit false)
      (Variables|GW|SetLifeProbe {AG('LifeQM', '(* ln 12)')})
      (bind hc {NPCC('(Variables|GW|GetLifeProbe)')}
        (:then
          (if (and (== {NC('QSlot', 'hc')} 0) (not {NC('IsMoving', 'hc')}))
            {NCS('LifeUntil', 'hc', 'now')})
          (if (< {RND} 0.4)
            (bind s (CallFunction|GetGS))
            (GW|Set|BP_GW_GameState|BarToasts :self s :BarToasts (+ (GW|Get|BP_GW_GameState|BarToasts :self s) 1))))
        (:CastFailed))))
  (bind sum (+ {AG('LifeQN', '0')} (+ {AG('LifeQN', '1')} {AG('LifeQN', '2')})))
  (if (< sum (/ (Variables|GW|GetNPCCount) 7))
    (Variables|GW|SetStamp (+ (Variables|GW|GetStamp) 1))
    (Variables|GW|SetLifeProbe (CallFunction|SocialPick :Loc {V('4420.0', '1000.0', '100.0')} :MaxD 5000.0))
    (if ({ISVALID} :Object (Variables|GW|GetLifeProbe))
      (CallFunction|LifeQJoin :Ch (Variables|GW|GetLifeProbe)))))
'''
    # a dance is on: anyone free nearby can walk onto the floor and dance alone
    GW_['LifeDanceJoin'] = f'''
(fn LifeDanceJoin (Ch)
  (if (not (Variables|GW|GetSocDanceOn))
    (return false))
  (if (> (CallFunction|Now) (- (Variables|GW|GetSocEndAt) 10.0))
    (return false))
  (if (or (> {RND} 0.5) (>= {LEN('SocDancers')} 28))
    (return false))
  (if (> {DIST2(LOC('Ch'), V('3000.0', '3330.0'))} 2300.0)
    (return false))
  (Variables|GW|SetSocAt {V(RF(2580, 3420), RF(2880, 3520), '100.0')})
  (bind at (Variables|GW|GetSocAt))
  (CallFunction|SocialAssign :Ch Ch :Mode 1 :Spot at :Face (+ at {V(RF(-150, 150), '400.0')}) :Dance {RI(1, 5)} :Until (+ (Variables|GW|GetSocEndAt) {RF(0, 7)}) :Solo true)
  (Utilities|Array|Add :TargetArray (Variables|GW|GetSocDancers) :NewItem Ch)
  (return true))
'''
    GW_['SpawnNPC'] = f'''
(fn SpawnNPC ()
  {SL('Sp', '(CallFunction|LifeSpawnT)')}
  (bind p (AI|SpawnAIFromClass :PawnClass {CHAR} :Location (.location {L('Sp')}) :Rotation (.rotation {L('Sp')}) :bNoCollisionFail true))
  (bind c (Utilities|Casting|CastToBP_GW_Character p)
    (:then
      (GW|Set|BP_GW_Character|OutfitIndex :self c :OutfitIndex -1)
      {SL('Oi', '(CallFunction|NextOutfit)')}
      (GW|Set|BP_GW_Character|OutfitIndex :self c :OutfitIndex {L('Oi')})
      (GW|Set|BP_GW_Character|Health :self c :Health 100.0))
    (:CastFailed)))
'''
    GW_['SpawnPlayerPawn'] = f'''
(fn SpawnPlayerPawn (PC Seeker)
  (bind old (Pawn|GetControlledPawn :self PC))
  (if ({ISVALID} :Object old)
    (Actor|DestroyActor :self old))
  (if Seeker
    (Variables|Default|SetT (CallFunction|SeekerSpawnTransform))
    (else
      (Variables|Default|SetT (CallFunction|RandomSpawnTransform))))
  (bind ch (Game|SpawnActorfromClass :Class {CHAR} :SpawnTransform (Variables|Default|GetT) :CollisionHandlingOverride "AdjustIfPossibleButAlwaysSpawn" :Owner PC))
  (GW|Set|BP_GW_Character|IsSeeker :self ch :IsSeeker Seeker)
  (GW|Set|BP_GW_Character|OutfitIndex :self ch :OutfitIndex -1)
  {SL('Oi', '(CallFunction|NextOutfit)')}
  (GW|Set|BP_GW_Character|OutfitIndex :self ch :OutfitIndex {L('Oi')})
  ; dev menu pick (Tools/ui/u15_dev_menu.py) kept across rounds
  (CallFunction|ApplyDevOutfit :PC PC :Ch ch)
  (GW|Set|BP_GW_Character|Health :self ch :Health 100.0)
  (Pawn|Possess :self PC :InPawn ch)
  (if Seeker
    (GW|Call|BP_GW_Character|SetFrozen :self ch :Frozen true))
  (return ch))
'''
    # a corpse is cleared when nobody can see it go (it used to vanish after 20 s in front of anyone)
    GW_['CorpseTick'] = f'''
(fn CorpseTick ()
  (if (< (CallFunction|Now) (Variables|GW|GetNextCorpse))
    (return))
  (Variables|GW|SetNextCorpse (+ (CallFunction|Now) 2.0))
  (for c (Actor|GetAllActorsOfClass :ActorClass {CHAR})
    (if (and {CH('IsDead', 'c')} (not (Pawn|IsPlayerControlled :self c)))
      (if (<= {CH('DeadSince', 'c')} 0.0)
        {CHS('DeadSince', 'c', '(CallFunction|Now)')}
        (elif (> (- (CallFunction|Now) {CH('DeadSince', 'c')}) 20.0)
          (bind out (CallFunction|LifeUnseen :Loc {LOC('c')} :MinD 700.0))
          (if (or out (> (- (CallFunction|Now) {CH('DeadSince', 'c')}) 180.0))
            (Actor|DestroyActor :self c)))))))
'''
    GW_['HoldNPC'] = f'''
(fn HoldNPC (Ch Until Face Stop)
  (if (not ({ISVALID} :Object Ch))
    (return))
  {CHS('TalkUntil', 'Ch', f"(Math|Float|Max(Float) {CH('TalkUntil', 'Ch')} Until)")}
  (bind c {NPCC('Ch')}
    (:then
      (if (!= {NC('SocialMode', 'c')} 0)
        (return))
      (if (and Stop {NC('IsMoving', 'c')})
        (AI|Navigation|StopMovement :self c)
        {NCS('IsMoving', 'c', 'false')}
        {NCS('HasFinal', 'c', 'false')})
      (bind here {LOC('Ch')})
      (if (> {DIST2('Face', 'here')} 30.0)
        (GW|Call|BP_GW_NPCController|FaceAt :self c :P Face))
      (if (not {NC('IsMoving', 'c')})
        {NCS('NextMoveTime', 'c', f"(Math|Float|Max(Float) {NC('NextMoveTime', 'c')} Until)")}))
    (:CastFailed)))
'''
    # dev menu: what the guests are doing right now
    GW_['LifeState'] = f'''
(fn LifeState ()
  {SL('A', '0')}
  {SL('B', '0')}
  {SL('C', '0')}
  {SL('D', '0')}
  {SL('E', '0')}
  {SL('F', '0')}
  (for o (Actor|GetAllActorsOfClass :ActorClass {CHAR})
    (if (and (not (Pawn|IsPlayerControlled :self o)) (and (not {CH('IsDead', 'o')}) (== {CH('Kind', 'o')} 0)))
      (bind c {NPCC('o')}
        (:then
          {SL('A', f"(+ {L('A')} 1)")}
          (if {NC('IsMoving', 'c')}
            {SL('B', f"(+ {L('B')} 1)")})
          (if (== {NC('LifeMode', 'c')} 5)
            {SL('C', f"(+ {L('C')} 1)")})
          (if (== {NC('LifeMode', 'c')} 3)
            {SL('D', f"(+ {L('D')} 1)")})
          (if (== {NC('LifeMode', 'c')} 7)
            {SL('F', f"(+ {L('F')} 1)")})
          (if (== {NC('SocialMode', 'c')} 4)
            {SL('E', f"(+ {L('E')} 1)")}))
        (:CastFailed))))
  (return (cat {L('A')} " PNJ : " {L('B')} " marchent, " {L('C')} " en cercle, " {L('D')} " en duo, " {L('E')} " assis, " {L('F')} " en file")))
'''
    ok = True
    for name, code in GW_.items():
        try:
            write(gm, name, code, compile_after=False)
        except Exception as e:
            ok = False
    if 'pois' in PARTS:
        good, first, count, rects = build_pois()
        d = cdo(gm)
        d.set_editor_property('LifePts', [unreal.Vector(*p[0]) for p in good])
        d.set_editor_property('LifeLook', [unreal.Vector(*p[1]) for p in good])
        d.set_editor_property('LifeKind', [p[2] for p in good])
        d.set_editor_property('LifeRFirst', [max(x, 0) for x in first])
        d.set_editor_property('LifeRCount', count)
        d.set_editor_property('LifeHomes', HOMES)
        d.set_editor_property('LifeRMin', [unreal.Vector(r[0], r[1], 600.0 if i == len(rects) - 1 else 100.0) for i, r in enumerate(rects)])
        d.set_editor_property('LifeRMax', [unreal.Vector(r[2], r[3], 100.0) for r in rects])
        d.set_editor_property('LifeCirC', [unreal.Vector(0, 0, 100)] * 24)
        d.set_editor_property('LifeCirN', [0] * 24)
        d.set_editor_property('LifeCirUntil', [0.0] * 24)
        # three lines: two in front of the billiard-room counter, heads against the stools; one at the dining-room bar cart
        d.set_editor_property('LifeQStart', [unreal.Vector(4280, 1452, 100), unreal.Vector(4560, 1452, 100), unreal.Vector(1860, 1140, 100)])
        d.set_editor_property('LifeQDir', [unreal.Vector(0, -1, 0), unreal.Vector(0, -1, 0), unreal.Vector(0, 1, 0)])
        d.set_editor_property('LifeQFace', [unreal.Vector(4280, 1700, 130), unreal.Vector(4560, 1700, 130), unreal.Vector(1900, 1010, 110)])
        d.set_editor_property('LifeQCap', [10, 10, 5])
        d.set_editor_property('LifeQN', [0, 0, 0])
        d.set_editor_property('LifeQServe', [0.0, 0.0, 0.0])
        d.set_editor_property('LifeBlockOn', True)
    compile_bp(gm)
    print('BP_GW_GameMode', ok, [p for p in node_problems(gm) if 'Life' in p or 'NextOutfit' in p])
    if ok:
        save(gm)
# ------------------------------------------------------------------ player controller: the dance repair walks a fifth of the guests per tick, not all of them 10 times a second
if 'pc' in UE_ARGS:
    pc = load_bp('BP_GW_PlayerController')
    ensure_var(pc, 'DanceWatchI', 'int', category='GW')
    compile_bp(pc, quiet=True)
    write(pc, 'DanceWatch', f'''
(fn DanceWatch ()
  (bind all (Actor|GetAllActorsOfClass :ActorClass {CHAR}))
  (bind n (Utilities|Array|Length all))
  (if (== n 0)
    (return))
  (for k (range (+ (/ n 5) 1))
    (Variables|GW|SetDanceWatchI (% (+ {G_('DanceWatchI')} 1) n))
    (GW|Call|BP_GW_Character|DanceCheck :self (Utilities|Array|Get(acopy) all {G_('DanceWatchI')}))))
''', compile_after=False)
    compile_bp(pc)
    print('BP_GW_PlayerController', [p for p in node_problems(pc) if 'DanceWatch' in p])
    save(pc)
print('done', sorted(PARTS))
