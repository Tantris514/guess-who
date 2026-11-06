"""Social life: dancing (any player with V, NPC couples and solos on the ballroom floor) and the crowd at the bar.

Dances (Tools/anim/dances.py, built by Tools/anim/build_dances.py into /Game/GW/Anims/Dance): 1 Charleston,
2 Lindy hop, 3 Valse lente, 4 Shimmy, 5 Truckin'. Couples (facing each other ~1 m apart) dance 1-3.
- BP_GW_Character.DanceId (int, RepNotify; 0 = not dancing): OnRep -> ApplyDance plays the loop as a single-node
  animation on the mesh, 0 restores ABP_Unarmed. Dead characters are never touched (ragdoll). DanceShown remembers
  what this machine shows; DanceCheck (every 0.1 s from SocialClientTick, all characters) repairs it when a mesh swap
  re-initialised the animation (late joiners, ApplyLook) or the replication was missed. DanceByPlayer (server only):
  set when a player started the dance (V), so a body swap never leaves a pawn dancing someone else's dance.
- Player: V (IA_Dance) -> RequestDance -> GWDance on the server (toggle; a random dance, never the same twice in a
  row). Moving stops it: the client asks at once (GWDanceStop) and the server sweep checks too (SocialSweep).
  On the dance floor a key cap "V Danser" floats over the player (BP_GW_KeyPrompt, local).
- NPCs (BP_GW_GameMode.SocialTick, from ReactionsTick, 4 Hz): during a round, every 60-120 s 4-8 guests walk to the
  dance floor in front of the stage (pairs facing each other, solos facing the stage), dance 15-40 s and leave one
  by one; every 90-160 s 6-10 guests gather in front of the billiard-room bar (some against the counter, two small
  circles), linger 20-40 s with small shuffles and chatter lines (Say / QueueSay), then leave one by one. The NPC
  brain part is BP_GW_NPCController.SocialThink (called from ThinkWith, s14_npc_ghost_menu.py). A panic, any event
  or the robot disperses both groups at once (the guests flee) and no group forms until 20 s after it is calm.
- Music: while the NPCs dance (GameState.DanceOn) the ballroom gramophone (GW_Audio ambient, MUS_Gramophone) swells.
- Dev menu (u15_dev_menu.py): Joueur -> "Danser (V)" (GWDance), PNJ -> "PNJ : danser maintenant" (GWDevDanceNow),
  "PNJ : foule au bar maintenant" (GWDevBarNow).
- Headless test: -GWSocialTest (host: plays a scripted test, logs "GW socialtest ..."), -GWSocialWatch (a client:
  dances through ServerExec and logs what it sees of everybody's dances).
Usage: ue_run.py Tools/anim/build_dances.py, then ue_run.py s36_social.py [char npc gm pc] (default: all, in that
order), then s14_npc_ghost_menu.py npc, then u15_dev_menu.py.
"""
import sys, importlib, math
sys.path.insert(0, r'J:\Projets\Unreal_Projects\Guess Who\Tools\gameplay')
sys.path.insert(0, r'J:\Projets\Unreal_Projects\Guess Who\Tools\anim')
import gw_lib; importlib.reload(gw_lib)
from gw_lib import *
import dances as DZ; importlib.reload(DZ)

REP = unreal.BlueprintVariableReplication
V3 = unreal.Vector.static_struct()
CHAR = '"/Game/GW/Blueprints/BP_GW_Character.BP_GW_Character_C"'
ISVALID = 'GW|Call|/Script/Engine.KismetSystemLibrary|IsValid'
GSC = '(Utilities|Casting|CastToBP_GW_GameState (Game|GetGameState))'
GMC = '(Utilities|Casting|CastToBP_GW_GameMode (Game|GetGameMode))'
MYCH = '(Utilities|Casting|CastToBP_GW_Character (Pawn|GetControlledPawn :self self))'
SKM = 'GW|Call|/Script/Engine.SkeletalMeshComponent'
PROMPT = '/Game/GW/Blueprints/BP_GW_KeyPrompt.BP_GW_KeyPrompt_C'
ABP = '/Game/Characters/Mannequins/Anims/Unarmed/ABP_Unarmed.ABP_Unarmed_C'
N = len(DZ.DANCES)
PAIRS = list(DZ.PAIR_DANCES)
G_TALK, G_LISTEN, G_LAUGH = (N + 1 + i for i in range(3))   # conversation loops (DZ.GESTURES); s39 voice director uses them too
CAT_CHATTER, CAT_REPLY = 4, 5                    # s31_reactions.py CAT
CAT_DANCE_END, CAT_BAR_TOAST = 76, 77            # voice director (s39): "Bravo !" / "Encore !", "Santé !"
mv = lambda x, y, z=100.0: f'(Math|Vector|MakeVector {float(x)} {float(y)} {float(z)})'
R = lambda a, b: f'(Math|Random|RandomFloatinRange {float(a)} {float(b)})'

# ---------------------------------------------------------------- places (Tools/level/dress.py, dress_state.json)
# Ballroom dance floor in front of the stage (stage + steps from y 3820, piano on it, GW_Piano (2911, 3963)): anchors
# 300 cm apart; a couple stands +-52 cm around one. Kept clear: the lane in front of the stage steps (x 2820..3180
# for y > 3560), the champagne tables and chairs (x < 2450, x > 3510), the south door (y < 2850).
FLOOR = (3000.0, 3330.0)
ANCHORS = [(x, y) for y in (2940, 3140, 3340, 3540) for x in (2640, 2850, 3060, 3270)] + [(2640, 3700), (3340, 3700)]      # 18: the floor really fills up (feedback 2026-11-05)
DANCE_FLOOR_RECT = (2560.0, 2860.0, 3440.0, 3790.0)        # x0, y0, x1, y1: the "V Danser" prompt shows inside
# Billiard-room bar: counter x 4135..4705, front y 1558, stools y 1504..1546, barman behind at (4420, 1690), bar cart
# at x > 4770. Front slots stand behind the stools facing the counter; two conversation circles further back.
BAR = (4420.0, 1330.0)
BAR_SPOTS, BAR_FACES = [], []
for x in (4205, 4315, 4425, 4535, 4645):
    BAR_SPOTS.append((x, 1452))
    BAR_FACES.append((x, 1700))
for cx, cy, r in ((5000, 1480, 78), (5330, 1450, 80)):      # east of the two queue lines (s44_npc_life.py, x 4280 and 4560)
    for a in (45, 135, 225, 315):
        BAR_SPOTS.append((round(cx + r * math.cos(math.radians(a))), round(cy + r * math.sin(math.radians(a)))))
        BAR_FACES.append((cx, cy))
N_FRONT = 5
log = lambda msg: f'(Development|PrintString :InString {msg} :bPrintToScreen false)'
PARTS = set(UE_ARGS) or {'char', 'npc', 'gm', 'pc'}
chc = load_bp('BP_GW_Character').generated_class()
NOW = '(Utilities|Time|GetGameTimeinSeconds)'
NAME = '(Utilities|GetDisplayName :Object Ch)'

# ---------------------------------------------------------------- input: V
if 'pc' in PARTS:
    INP = '/Game/GW/Input'
    AT = unreal.AssetToolsHelpers.get_asset_tools()
    ia = unreal.load_asset(f'{INP}/IA_Dance') if EAL.does_asset_exist(f'{INP}/IA_Dance') else \
        AT.create_asset('IA_Dance', INP, unreal.InputAction, unreal.InputAction_Factory())
    EAL.save_loaded_asset(ia, False)
    imc = unreal.load_asset(f'{INP}/IMC_GW')
    maps = imc.get_editor_property('default_key_mappings').get_editor_property('mappings')
    used_v = [str(m.get_editor_property('action').get_name()) for m in maps if str(m.get_editor_property('key').get_editor_property('key_name')) == 'V']
    if not any(m.get_editor_property('action') == ia for m in maps):
        k = unreal.Key()
        k.set_editor_property('key_name', 'V')
        imc.map_key(ia, k)
        EAL.save_loaded_asset(imc, False)
    print('V was mapped to', used_v)


# ---------------------------------------------------------------- dance clips
anims = []
for d in DZ.ALL:                                     # DanceId 1-5 dances, 6 talking, 7 listening, 8 laughing
    p = f'/Game/GW/Anims/Dance/AS_GW_Dance_{d.name}'
    assert EAL.does_asset_exist(p), f'{p} missing: run Tools/anim/build_dances.py first'
    anims.append(unreal.load_asset(p))

# ---------------------------------------------------------------- character: DanceId and its animation
if 'char' in PARTS:
    ch = load_bp('BP_GW_Character')
    chc = ch.generated_class()
    ensure_var(ch, 'DanceId', 'int', rep=REP.REP_NOTIFY, category='GW')
    ensure_var(ch, 'DanceShown', 'int', category='GW')
    ensure_var(ch, 'DanceByPlayer', 'bool', category='GW')
    ensure_var(ch, 'DanceAnims', obj_class=unreal.AnimSequence, array=True, category='Dance')
    ensure_fn(ch, 'OnRep_DanceId')
    ensure_fn(ch, 'ApplyDance')
    ensure_fn(ch, 'DanceCheck')
    compile_bp(ch, quiet=True)
    cdo(ch).set_editor_property('DanceAnims', anims)
    mesh_tpl = None
    for c in cdo(ch).get_components_by_class(unreal.SkeletalMeshComponent):
        mesh_tpl = c
    print('character mesh anim class:', mesh_tpl.get_editor_property('anim_class') if mesh_tpl else None)
    CHW = {
        'ApplyDance': f'''
    (fn ApplyDance ()
      (bind id (Variables|GW|GetDanceId))
      (Variables|GW|SetDanceShown id)
      ; a ragdoll keeps its physics pose: never touch the animation of the dead
      (if (Variables|GW|GetIsDead)
        (return))
      (bind m (Variables|Character|GetMesh))
      (bind clips (Variables|Dance|GetDanceAnims))
      (if (and (> id 0) (<= id (Utilities|Array|Length clips)))
        ({SKM}|PlayAnimation :self m :NewAnimToPlay (Utilities|Array|Get(acopy) clips (- id 1)) :bLooping true)
        (return))
      ({SKM}|SetAnimInstanceClass :self m :NewClass "{ABP}"))
    ''',
        'OnRep_DanceId': '(fn OnRep_DanceId () (CallFunction|ApplyDance))',
        # this machine shows what DanceId says; repairs a dance lost to a mesh swap (SetSkeletalMesh re-inits the anim)
        'DanceCheck': f'''
    (fn DanceCheck ()
      (if (Variables|GW|GetIsDead)
        (return))
      (bind id (Variables|GW|GetDanceId))
      (if (!= id (Variables|GW|GetDanceShown))
        (CallFunction|ApplyDance)
        (return))
      (bind clips (Variables|Dance|GetDanceAnims))
      (if (and (> id 0) (<= id (Utilities|Array|Length clips)))
        ; in single-node mode the anim instance is the single-node instance playing the clip
        (bind inst (Utilities|Casting|CastToAnimSingleNodeInstance ({SKM}|GetAnimInstance :self (Variables|Character|GetMesh)))
          (:then
            (if (!= (GW|Call|/Script/Engine.AnimSingleNodeInstance|GetAnimationAsset :self inst) (Utilities|Array|Get(acopy) clips (- id 1)))
              (CallFunction|ApplyDance)))
          (:CastFailed
            (CallFunction|ApplyDance)))))
    ''',
    }
    for name, code in CHW.items():
        write(ch, name, code, compile_after=False)
        compile_bp(ch, quiet=True)
    compile_bp(ch)
    print('BP_GW_Character', node_problems(ch))
    save(ch)


# ---------------------------------------------------------------- game state: dance music on
if 'char' in PARTS:
    gs = load_bp('BP_GW_GameState')
    ensure_var(gs, 'DanceOn', 'bool', rep=REP.REPLICATED, category='GW')
    ensure_var(gs, 'DanceClaps', 'int', rep=REP.REPLICATED, category='GW')      # +1: the dancers stop, applause
    ensure_var(gs, 'BarToasts', 'int', rep=REP.REPLICATED, category='GW')       # +1: glasses clink at the bar
    compile_bp(gs)
    save(gs)


# ---------------------------------------------------------------- NPC controller: the social part of the brain
if 'npc' in PARTS:
    npc = load_bp('BP_GW_NPCController')
    for v, t in (('SocialMode', 'int'), ('SocialDance', 'int'), ('SocialUntil', 'float'), ('SocialNext', 'float'), ('SocialTries', 'int'),
                 ('SocialRoll', 'float'), ('SocialArrived', 'bool'), ('SocialSolo', 'bool'), ('SocialSeen', 'bool')):
        ensure_var(npc, v, t, category='GW')
    for v in ('SocialSpot', 'SocialHome', 'SocialFace'):
        ensure_var(npc, v, struct=V3, category='GW')
    ensure_fn(npc, 'SocialThink', inputs=[('Ch', chc)], outputs=[('Handled', 'bool')])
    for f in ('SocialCancel', 'SocialArrive', 'SocialFaceNow', 'SocialFidget', 'SocialLeave', 'SocialGesture',
              'SocialStartDance', 'SocialCouple'):
        ensure_fn(npc, f, inputs=[('Ch', chc)])
    ensure_fn(npc, 'SocialMove')
    compile_bp(npc, quiet=True)
    NOW = '(Utilities|Time|GetGameTimeinSeconds)'
    NAME = '(Utilities|GetDisplayName :Object Ch)'
    NPW = {
        'SocialCancel': f'''
    (fn SocialCancel (Ch)
      (if ({ISVALID} :Object Ch)
        (if (!= (GW|Get|BP_GW_Character|DanceId :self Ch) 0)
          (GW|Set|BP_GW_Character|DanceId :self Ch :DanceId 0)))
      (Variables|GW|SetSocialMode 0)
      (Variables|GW|SetSocialArrived false)
      (Variables|GW|SetSocialTries 0)
      (Variables|GW|SetPartner (Variables|GW|GetNoPartner)))
    ''',
        'SocialFaceNow': '''
    (fn SocialFaceNow (Ch)
      (Transformation|SetActorRotation :self Ch :NewRotation (Math|Rotator|MakeRotator :Yaw (.yaw (Math|Rotator|FindLookatRotation :Start (Transformation|GetActorLocation :self Ch) :Target (Variables|GW|GetSocialFace)))) :bTeleportPhysics false))
    ''',
        'SocialArrive': f'''
    (fn SocialArrive (Ch)
      (bind far (Math|Vector|Distance2D(Vector) (Transformation|GetActorLocation :self Ch) (Variables|GW|GetSocialSpot)))
      (if (> far 260.0)
        (if (< (Variables|GW|GetSocialTries) 2)
          (Variables|GW|SetSocialTries (+ (Variables|GW|GetSocialTries) 1))
          {log(f'(cat "GW: social NPC " {NAME} " retries its spot (" far " cm away, at " (Transformation|GetActorLocation :self Ch) ")")')}
          (CallFunction|GoTo :Dest (Variables|GW|GetSocialSpot))
          (return))
        {log(f'(cat "GW: social NPC " {NAME} " gave up (could not reach its spot, " far " cm away, at " (Transformation|GetActorLocation :self Ch) ")")')}
        (CallFunction|SocialCancel :Ch Ch)
        (return))
      (Variables|GW|SetSocialArrived true)
      (CallFunction|SocialFaceNow :Ch Ch)
      (Variables|GW|SetSocialNext (+ {NOW} {R(5, 12)}))
      (if (not (Variables|GW|GetSocialSeen))
        (Variables|GW|SetSocialSeen true)
        (if (== (Variables|GW|GetSocialMode) 2)
          {log(f'(cat "GW: social NPC " {NAME} " joins the bar crowd")')}))
      (if (== (Variables|GW|GetSocialMode) 2)
        (CallFunction|SocialGesture :Ch Ch))
      (if (and (== (Variables|GW|GetSocialMode) 1) (!= (GW|Get|BP_GW_Character|DanceId :self Ch) (Variables|GW|GetSocialDance)))
        (if (Variables|GW|GetSocialSolo)
          (CallFunction|SocialStartDance :Ch Ch)
          (else
            (CallFunction|SocialCouple :Ch Ch)))))
    ''',
        'SocialStartDance': f'''
    (fn SocialStartDance (Ch)
      (GW|Set|BP_GW_Character|DanceByPlayer :self Ch :DanceByPlayer false)
      (GW|Set|BP_GW_Character|DanceId :self Ch :DanceId (Variables|GW|GetSocialDance))
      {log(f'(cat "GW: social NPC " {NAME} " dances " (Variables|GW|GetSocialDance))')})
    ''',
        # the second partner to arrive starts both dances in the same frame (BP_GW_GameMode.SocialCoupleStart)
        'SocialCouple': f'''
    (fn SocialCouple (Ch)
      (bind gm {GMC}
        (:then (GW|Call|BP_GW_GameMode|SocialCoupleStart :self gm :Ch Ch))
        (:CastFailed)))
    ''',
        # every 6-14 s once there: a solo dancer may change dance, a couple keeps facing; the bar crowd shuffles or turns
        'SocialFidget': f'''
    (fn SocialFidget (Ch)
      (Variables|GW|SetSocialNext (+ {NOW} {R(6, 14)}))
      (Variables|GW|SetSocialRoll (Math|Random|RandomFloat))
      (bind r (Variables|GW|GetSocialRoll))
      (if (== (Variables|GW|GetSocialMode) 1)
        (if (== (GW|Get|BP_GW_Character|DanceId :self Ch) 0)
          (CallFunction|SocialCouple :Ch Ch)
          (return))
        (if (and (Variables|GW|GetSocialSolo) (< r 0.3))
          (Variables|GW|SetSocialDance (+ 1 (% (+ (Variables|GW|GetSocialDance) (Math|Random|RandomIntegerinRange 0 {N - 2})) {N})))
          (GW|Set|BP_GW_Character|DanceId :self Ch :DanceId (Variables|GW|GetSocialDance)))
        (CallFunction|SocialFaceNow :Ch Ch)
        (return))
      (if (< r 0.4)
        (GW|Set|BP_GW_Character|DanceId :self Ch :DanceId 0)
        (Variables|GW|SetSocialSpot (+ (Variables|GW|GetSocialHome) (Math|Vector|MakeVector {R(-35, 35)} (select (Variables|GW|GetSocialSolo) {R(-35, 0)} {R(-35, 35)}) 0.0)))
        (Variables|GW|SetSocialArrived false)
        (return))
      (if (< r 0.65)
        (Transformation|SetActorRotation :self Ch :NewRotation (Math|Rotator|MakeRotator :Yaw (+ (.yaw (Transformation|GetActorRotation :self Ch)) (select (Math|Random|RandomBool) {R(25, 70)} {R(-70, -25)}))) :bTeleportPhysics false)
        (return))
      (CallFunction|SocialGesture :Ch Ch))
    ''',
        # the bar crowd's body language: plain idle, listening (hands behind the back), talking (hand gestures), laughing
        'SocialGesture': f'''
    (fn SocialGesture (Ch)
      (Variables|GW|SetSocialRoll (Math|Random|RandomFloat))
      (bind g (Variables|GW|GetSocialRoll))
      (GW|Set|BP_GW_Character|DanceByPlayer :self Ch :DanceByPlayer false)
      (GW|Set|BP_GW_Character|DanceId :self Ch :DanceId (select (< g 0.3) 0 (select (< g 0.6) {G_LISTEN} (select (< g 0.9) {G_TALK} {G_LAUGH})))))
    ''',
        'SocialLeave': f'''
    (fn SocialLeave (Ch)
      (if (!= (GW|Get|BP_GW_Character|DanceId :self Ch) 0)
        (GW|Set|BP_GW_Character|DanceId :self Ch :DanceId 0))
      (Variables|GW|SetSocialMode 3)
      (Variables|GW|SetSocialArrived false)
      (Variables|GW|SetSocialTries 0)
      (Variables|GW|SetPartner (Variables|GW|GetNoPartner))
      (Variables|GW|SetSocialUntil (+ {NOW} {R(0.4, 2.2)}))
      (AI|Navigation|StopMovement :self self)
      (Variables|GW|SetIsMoving false)
      {log(f'(cat "GW: social NPC " {NAME} " leaves")')})
    ''',
        # returns true while the social life drives this guest (ThinkWith then skips its own wandering)
        'SocialThink': f'''
    (fn SocialThink (Ch)
      (bind mode (Variables|GW|GetSocialMode))
      (if (== mode 0)
        (return false))
      (bind now {NOW})
      (if (== mode 3)
        (if (< now (Variables|GW|GetSocialUntil))
          (return true))
        (Variables|GW|SetSocialMode 0)
        (if (Math|Random|RandomBoolwithWeight :Weight 0.7)
          (bind (d ok) (CallFunction|PickDestination))
          (if ok
            (Variables|GW|SetHasFinal false)
            (CallFunction|GoTo :Dest d)
            (return true)))
        (Variables|GW|SetNextMoveTime now)
        (return false))
      (if (>= now (Variables|GW|GetSocialUntil))
        (CallFunction|SocialLeave :Ch Ch)
        (return true))
      (if (Variables|GW|GetSocialArrived)
        ; someone else sent this guest away (the piano): drop the social life
        (if (Variables|GW|GetIsMoving)
          (CallFunction|SocialCancel :Ch Ch)
          (return false))
        (if (>= now (Variables|GW|GetSocialNext))
          (CallFunction|SocialFidget :Ch Ch))
        (return true))
      (if (Variables|GW|GetIsMoving)
        (bind since (- now (Variables|GW|GetMoveStartTime)))
        (bind speed (Math|Vector|VectorLength (Transformation|GetVelocity :self Ch)))
        (if (or (< (Math|Vector|Distance2D(Vector) (Transformation|GetActorLocation :self Ch) (Variables|GW|GetSocialSpot)) 20.0) (or (and (> since 1.0) (< speed 3.0)) (> since 35.0)))
          (AI|Navigation|StopMovement :self self)
          (Variables|GW|SetIsMoving false)
          (CallFunction|SocialArrive :Ch Ch))
        (return true))
      ; the bar crowd leaves one by one (SocialAddBar): no jam in the doors
      (if (< now (Variables|GW|GetNextMoveTime))
        (return true))
      (CallFunction|SocialMove)
      (return true))
    ''',
        # walks to the exact spot: couples end up ~1 m apart facing each other, not wherever the crowd let them stop
        'SocialMove': '''
    (fn SocialMove ()
      (AI|Navigation|MovetoLocation :self self :Dest (Variables|GW|GetSocialSpot) :AcceptanceRadius 10.0 :bStopOnOverlap false :bUsePathfinding true :bProjectDestinationToNavigation true :bCanStrafe false :bAllowPartialPath true)
      (Variables|GW|SetIsMoving true)
      (Variables|GW|SetMoveStartTime (Utilities|Time|GetGameTimeinSeconds)))
    ''',
    }
    if get_graph(load_bp('BP_GW_GameMode'), 'SocialCoupleStart') is None:      # the gm part has not run yet
        NPW['SocialCouple'] = '(fn SocialCouple (Ch) (CallFunction|SocialStartDance :Ch Ch))'
        print('SocialCouple: GameMode.SocialCoupleStart missing, couples start one by one until the gm part runs')
    for k_ in ('SocialFaceNow', 'SocialFidget', 'SocialMove'):      # s44_npc_life.py renders these now
        NPW.pop(k_)
    for name, code in NPW.items():
        write(npc, name, code, compile_after=False)
        compile_bp(npc, quiet=True)
    compile_bp(npc)
    print('BP_GW_NPCController', node_problems(npc))
    save(npc)


# ---------------------------------------------------------------- game mode: groups
if 'gm' in PARTS:
    gm = load_bp('BP_GW_GameMode')
    for v, t in (('SocNextDance', 'float'), ('SocNextBar', 'float'), ('SocEndAt', 'float'), ('SocBarEnd', 'float'),
                 ('SocDanceClear', 'float'), ('SocBarClear', 'float'), ('SocCalmAt', 'float'), ('SocNextDanceChat', 'float'),
                 ('SocNextBarChat', 'float'), ('SocYaw', 'float'), ('SocDanceOn', 'bool'), ('SocBarOn', 'bool'),
                 ('SocN', 'int'), ('SocM', 'int'), ('SocDance', 'int'), ('SocPairs', 'int')):
        ensure_var(gm, v, t, category='GW')
    for v in ('SocAt', 'SocDir', 'SocFrom'):
        ensure_var(gm, v, struct=V3, category='GW')
    for v in ('SocA', 'SocB', 'SocTalk', 'SocTalk2'):
        ensure_var(gm, v, obj_class=chc, category='GW')
    ensure_var(gm, 'SocDancers', obj_class=chc, array=True, category='GW')
    ensure_var(gm, 'SocBarGuests', obj_class=chc, array=True, category='GW')
    ensure_var(gm, 'SocAnchors', struct=V3, array=True, category='GW')
    ensure_var(gm, 'SocBarSpots', struct=V3, array=True, category='GW')
    ensure_var(gm, 'SocBarFaces', struct=V3, array=True, category='GW')
    ensure_var(gm, 'SocOrder', 'int', array=True, category='GW')
    ensure_var(gm, 'SocAnchorIdx', 'int', array=True, category='GW')
    ensure_var(gm, 'SocFrontIdx', 'int', array=True, category='GW')
    ensure_var(gm, 'SocCircleIdx', 'int', array=True, category='GW')
    ensure_var(gm, 'SocPairDances', 'int', array=True, category='GW')
    ensure_fn(gm, 'SocialPick', inputs=[('Loc', V3), ('MaxD', 'float')], outputs=[('Ch', chc)])
    ensure_fn(gm, 'SocialAssign', inputs=[('Ch', chc), ('Mode', 'int'), ('Spot', V3), ('Face', V3), ('Dance', 'int'),
                                          ('Until', 'float'), ('Solo', 'bool')])
    ensure_fn(gm, 'SocialReady', inputs=[('Ch', chc)], outputs=[('Ok', 'bool')])
    ensure_fn(gm, 'SocialAlive', inputs=[('Ch', chc)], outputs=[('Ok', 'bool')])
    ensure_fn(gm, 'SocialCoupleStart', inputs=[('Ch', chc)])
    ensure_fn(gm, 'SocialPurge')
    ensure_var(gm, 'SocClapped', 'bool', category='GW')
    ensure_var(gm, 'SocK', 'int', category='GW')
    ensure_fn(gm, 'SocialSayIn', inputs=[('Which', 'int'), ('Reply', 'float')])
    _g = get_graph(gm, 'SocialSayIn')                      # its first version took the group array
    if BT._param_name_exists(_g, 'Group', True):
        BT.remove_function_param(_g, 'Group', True)
    # for the voice director (s39) and the chatter: two guests of a group standing together (Which 0 any, 1 dance, 2 bar)
    ensure_fn(gm, 'SocialTalkPair', inputs=[('Which', 'int')], outputs=[('A', chc), ('B', chc), ('Ok', 'bool')])
    ensure_fn(gm, 'SocialPartners', inputs=[('A', chc), ('B', chc)])
    ensure_var(gm, 'SocUseBar', 'bool', category='GW')
    ensure_var(gm, 'SocGroup', obj_class=chc, array=True, category='GW')
    ensure_fn(gm, 'SocialStartDance', inputs=[('Force', 'bool')])
    ensure_fn(gm, 'SocialStartBar', inputs=[('Force', 'bool')])
    ensure_fn(gm, 'SocialAddBar', inputs=[('Slot', 'int')])
    ensure_fn(gm, 'SocialEndGroup', inputs=[('Which', 'int')])
    ensure_fn(gm, 'SocialDisperse', inputs=[('Flee', 'bool')])
    # bandits, the kamikaze and the robot are local dangers: a group flees when one comes near, none forms near one
    ensure_fn(gm, 'SocialThreatAt', inputs=[('Loc', V3), ('R', 'float')], outputs=[('Near', 'bool'), ('From', V3)])
    ensure_fn(gm, 'SocialFlee', inputs=[('Which', 'int'), ('From', V3)])
    for f in ('SocialTick', 'SocialSweep', 'SocialChat', 'SocialAddPair', 'SocialAddSolo'):
        ensure_fn(gm, f)
    compile_bp(gm, quiet=True)
    for fn, locs in (('SocialPick', [('BestD', 'float'), ('Score', 'float')]), ('SocialTalkPair', [('BestD', 'float')])):
        g = get_graph(gm, fn)
        for n_, t_ in locs:
            if n_ not in BT.list_variables(gm, g):
                BT.add_variable(gm, n_, t_, graph=g)
    g = get_graph(gm, 'SocialPick')
    if 'BestT' not in BT.list_variables(gm, g):
        BT.add_object_variable(gm, 'BestT', chc, graph=g)
    d = cdo(gm)
    d.set_editor_property('SocAnchors', [unreal.Vector(x, y, 100.0) for x, y in ANCHORS])
    d.set_editor_property('SocAnchorIdx', list(range(len(ANCHORS))))
    d.set_editor_property('SocBarSpots', [unreal.Vector(x, y, 100.0) for x, y in BAR_SPOTS])
    d.set_editor_property('SocBarFaces', [unreal.Vector(x, y, 100.0) for x, y in BAR_FACES])
    d.set_editor_property('SocFrontIdx', list(range(N_FRONT)))
    d.set_editor_property('SocCircleIdx', list(range(N_FRONT, len(BAR_SPOTS))))
    d.set_editor_property('SocPairDances', PAIRS)
    NPCC = '(Utilities|Casting|CastToBP_GW_NPCController (Pawn|GetController :self {}))'
    GSC_ = GSC
    SET = lambda c, var, val: f'(GW|Set|BP_GW_NPCController|{var} :self {c} :{var} {val})'
    GET = lambda c, var: f'(GW|Get|BP_GW_NPCController|{var} :self {c})'
    GMW = {
        # a free guest near Loc (with some randomness so it is not always the same ones): not a player, alive, a plain
        # guest, not picked yet in this batch (Stamp), not the piano visitor, not panicking, not already in a group
        'SocialPick': f'''
    (fn SocialPick (Loc MaxD)
      (Variables|Default|SetBestD 100000000.0)
      (Variables|Default|SetBestT (Variables|GW|GetNoChar))
      (bind now (CallFunction|Now))
      (for a (Actor|GetAllActorsOfClass :ActorClass {CHAR})
        (if (and (and (not (Pawn|IsPlayerControlled :self a)) (not (GW|Get|BP_GW_Character|IsDead :self a))) (and (== (GW|Get|BP_GW_Character|Kind :self a) 0) (!= (GW|Get|BP_GW_Character|PickStamp :self a) (Variables|GW|GetStamp))))
          (if (and (!= a (Variables|GW|GetPianoNPC)) (< (Math|Vector|Distance(Vector) (Transformation|GetActorLocation :self a) Loc) MaxD))
            (bind c {NPCC.format('a')}
              (:then
                (if (and (and (== {GET('c', 'SocialMode')} 0) (!= {GET('c', 'LifeMode')} 7)) (>= now {GET('c', 'PanicUntil')}))
                  (Variables|Default|SetScore (+ (Math|Vector|Distance(Vector) (Transformation|GetActorLocation :self a) Loc) {R(0, 900)}))
                  (if (< (Variables|Default|GetScore) (Variables|Default|GetBestD))
                    (Variables|Default|SetBestD (Variables|Default|GetScore))
                    (Variables|Default|SetBestT a))))
              (:CastFailed)))))
      (bind t (Variables|Default|GetBestT))
      (if ({ISVALID} :Object t)
        (GW|Set|BP_GW_Character|PickStamp :self t :PickStamp (Variables|GW|GetStamp)))
      (return t))
    ''',
        'SocialAssign': f'''
    (fn SocialAssign (Ch Mode Spot Face Dance Until Solo)
      (bind c {NPCC.format('Ch')}
        (:then
          (AI|Navigation|StopMovement :self c)
          {SET('c', 'IsMoving', 'false')}
          {SET('c', 'HasFinal', 'false')}
          {SET('c', 'ShuffleNext', 'false')}
          {SET('c', 'Partner', GET('c', 'NoPartner'))}
          {SET('c', 'SocialMode', 'Mode')}
          {SET('c', 'SocialSpot', 'Spot')}
          {SET('c', 'SocialHome', 'Spot')}
          {SET('c', 'SocialFace', 'Face')}
          {SET('c', 'SocialDance', 'Dance')}
          {SET('c', 'SocialUntil', 'Until')}
          {SET('c', 'SocialSolo', 'Solo')}
          {SET('c', 'SocialArrived', 'false')}
          {SET('c', 'SocialSeen', 'false')}
          {SET('c', 'NextMoveTime', '(CallFunction|Now)')})
        (:CastFailed)))
    ''',
        'SocialAddPair': f'''
    (fn SocialAddPair ()
      (Variables|GW|SetSocA (CallFunction|SocialPick :Loc {mv(*FLOOR)} :MaxD 3600.0))
      (Variables|GW|SetSocB (CallFunction|SocialPick :Loc {mv(*FLOOR)} :MaxD 3600.0))
      (bind a (Variables|GW|GetSocA))
      (bind b (Variables|GW|GetSocB))
      (if (not (and ({ISVALID} :Object a) ({ISVALID} :Object b)))
        (return))
      (Variables|GW|SetSocYaw {R(0, 180)})
      (Variables|GW|SetSocDir (* (Math|Vector|GetForwardVector (Math|Rotator|MakeRotator :Yaw (Variables|GW|GetSocYaw))) 52.0))
      (bind at (Variables|GW|GetSocAt))
      (bind off (Variables|GW|GetSocDir))
      (bind pd (Variables|GW|GetSocPairDances))
      (Variables|GW|SetSocDance (Utilities|Array|Get(acopy) pd (Math|Random|RandomIntegerinRange 0 (- (Utilities|Array|Length pd) 1))))
      (CallFunction|SocialAssign :Ch a :Mode 1 :Spot (+ at off) :Face (- at off) :Dance (Variables|GW|GetSocDance) :Until (+ (Variables|GW|GetSocEndAt) {R(0, 7)}) :Solo false)
      (CallFunction|SocialAssign :Ch b :Mode 1 :Spot (- at off) :Face (+ at off) :Dance (Variables|GW|GetSocDance) :Until (+ (Variables|GW|GetSocEndAt) {R(0, 7)}) :Solo false)
      (CallFunction|SocialPartners :A a :B b)
      (Utilities|Array|Add :TargetArray (Variables|GW|GetSocDancers) :NewItem a)
      (Utilities|Array|Add :TargetArray (Variables|GW|GetSocDancers) :NewItem b)
      (Variables|GW|SetSocPairs (+ (Variables|GW|GetSocPairs) 1)))
    ''',
        'SocialAddSolo': f'''
    (fn SocialAddSolo ()
      (Variables|GW|SetSocA (CallFunction|SocialPick :Loc {mv(*FLOOR)} :MaxD 3600.0))
      (bind a (Variables|GW|GetSocA))
      (if (not ({ISVALID} :Object a))
        (return))
      (bind at (Variables|GW|GetSocAt))
      (Variables|GW|SetSocYaw {R(-60, 60)})
      (CallFunction|SocialAssign :Ch a :Mode 1 :Spot at :Face (+ at (* (Math|Vector|GetForwardVector (Math|Rotator|MakeRotator :Yaw (+ 90.0 (Variables|GW|GetSocYaw)))) 400.0)) :Dance (Math|Random|RandomIntegerinRange 1 {N}) :Until (+ (Variables|GW|GetSocEndAt) {R(0, 7)}) :Solo true)
      (Utilities|Array|Add :TargetArray (Variables|GW|GetSocDancers) :NewItem a))
    ''',
        'SocialStartDance': f'''
    (fn SocialStartDance (Force)
      (if (Variables|GW|GetSocDanceOn)
        (if (not Force)
          (return))
        (CallFunction|SocialEndGroup :Which 1))
      (bind now (CallFunction|Now))
      (Variables|GW|SetStamp (+ (Variables|GW|GetStamp) 1))
      (Utilities|Array|Clear (Variables|GW|GetSocDancers))
      (Variables|GW|SetSocPairs 0)
      (Variables|GW|SetSocN (Math|Random|RandomIntegerinRange (Math|Integer|Max(Integer) 6 (/ (Variables|GW|GetNPCCount) 10)) (Math|Integer|Max(Integer) 8 (/ (Variables|GW|GetNPCCount) 6))))
      (Variables|GW|SetSocEndAt (+ now (+ 12.0 {R(40, 90)})))
      (Variables|GW|SetSocOrder (Variables|GW|GetSocAnchorIdx))
      (Utilities|Array|Shuffle (Variables|GW|GetSocOrder))
      (for ai (Variables|GW|GetSocOrder)
        (if (< (Utilities|Array|Length (Variables|GW|GetSocDancers)) (Variables|GW|GetSocN))
          (Variables|GW|SetSocAt (+ (Utilities|Array|Get(acopy) (Variables|GW|GetSocAnchors) ai) (Math|Vector|MakeVector {R(-25, 25)} {R(-25, 25)} 0.0)))
          (if (and (>= (- (Variables|GW|GetSocN) (Utilities|Array|Length (Variables|GW|GetSocDancers))) 2) (Math|Random|RandomBoolwithWeight :Weight 0.6))
            (CallFunction|SocialAddPair)
            (else
              (CallFunction|SocialAddSolo)))))
      (bind k (Utilities|Array|Length (Variables|GW|GetSocDancers)))
      (if (== k 0)
        {log('"GW: social dance: no guest free to dance"')}
        (return))
      (Variables|GW|SetSocDanceOn true)
      (Variables|GW|SetSocClapped false)
      (Variables|GW|SetSocDanceClear (+ (Variables|GW|GetSocEndAt) 9.0))
      (Variables|GW|SetSocNextDanceChat (+ now 10.0))
      (GW|Set|BP_GW_GameState|DanceOn :self (CallFunction|GetGS) :DanceOn true)
      {log('(cat "GW: social dance group formed: " k " NPCs, " (Variables|GW|GetSocPairs) " pairs, dancing until +" (- (Variables|GW|GetSocEndAt) now) " s")')})
    ''',
        'SocialAddBar': f'''
    (fn SocialAddBar (Slot)
      (Variables|GW|SetSocA (CallFunction|SocialPick :Loc {mv(*BAR)} :MaxD 3800.0))
      (bind a (Variables|GW|GetSocA))
      (if (not ({ISVALID} :Object a))
        (return))
      (Variables|GW|SetSocK (Utilities|Array|Length (Variables|GW|GetSocBarGuests)))
      (CallFunction|SocialAssign :Ch a :Mode 2 :Spot (+ (Utilities|Array|Get(acopy) (Variables|GW|GetSocBarSpots) Slot) (Math|Vector|MakeVector {R(-10, 10)} {R(-10, 10)} 0.0)) :Face (Utilities|Array|Get(acopy) (Variables|GW|GetSocBarFaces) Slot) :Dance 0 :Until (+ (Variables|GW|GetSocBarEnd) {R(0, 8)}) :Solo (< Slot {N_FRONT}))
      (Utilities|Array|Add :TargetArray (Variables|GW|GetSocBarGuests) :NewItem a)
      (bind ca {NPCC.format('a')}
        (:then {SET('ca', 'NextMoveTime', '(+ (CallFunction|Now) (* (Variables|GW|GetSocK) 1.1))')})
        (:CastFailed)))
    ''',
        'SocialStartBar': f'''
    (fn SocialStartBar (Force)
      (if (Variables|GW|GetSocBarOn)
        (if (not Force)
          (return))
        (CallFunction|SocialEndGroup :Which 2))
      (bind now (CallFunction|Now))
      (Variables|GW|SetStamp (+ (Variables|GW|GetStamp) 1))
      (Utilities|Array|Clear (Variables|GW|GetSocBarGuests))
      (Variables|GW|SetSocN (Math|Random|RandomIntegerinRange 6 10))
      (Variables|GW|SetSocM 0)        ; the counter belongs to the queues now (s44_npc_life.py)
      (Variables|GW|SetSocBarEnd (+ now (+ 14.0 {R(20, 40)})))
      (Variables|GW|SetSocOrder (Variables|GW|GetSocFrontIdx))
      (Utilities|Array|Shuffle (Variables|GW|GetSocOrder))
      (for si (Variables|GW|GetSocOrder)
        (if (< (Utilities|Array|Length (Variables|GW|GetSocBarGuests)) (Variables|GW|GetSocM))
          (CallFunction|SocialAddBar :Slot si)))
      (Variables|GW|SetSocOrder (Variables|GW|GetSocCircleIdx))
      (Utilities|Array|Shuffle (Variables|GW|GetSocOrder))
      (for si (Variables|GW|GetSocOrder)
        (if (< (Utilities|Array|Length (Variables|GW|GetSocBarGuests)) (Variables|GW|GetSocN))
          (CallFunction|SocialAddBar :Slot si)))
      (bind k (Utilities|Array|Length (Variables|GW|GetSocBarGuests)))
      (if (== k 0)
        {log('"GW: social bar: no guest free"')}
        (return))
      (Variables|GW|SetSocBarOn true)
      (Variables|GW|SetSocBarClear (+ (Variables|GW|GetSocBarEnd) 10.0))
      (Variables|GW|SetSocNextBarChat (+ now 9.0))
      {log('(cat "GW: social bar group formed: " k " NPCs, lingering until +" (- (Variables|GW|GetSocBarEnd) now) " s")')})
    ''',
        # bookkeeping once everybody left by themselves (members still on their way are sent off)
        'SocialEndGroup': f'''
    (fn SocialEndGroup (Which)
      (if (== Which 1)
        (for m (Variables|GW|GetSocDancers)
          (if (CallFunction|SocialAlive :Ch m)
            (bind c {NPCC.format('m')}
              (:then
                (if (== {GET('c', 'SocialMode')} 1)
                  (GW|Call|BP_GW_NPCController|SocialLeave :self c :Ch m)))
              (:CastFailed))))
        (Utilities|Array|Clear (Variables|GW|GetSocDancers))
        (Variables|GW|SetSocDanceOn false)
        (GW|Set|BP_GW_GameState|DanceOn :self (CallFunction|GetGS) :DanceOn false)
        {log('"GW: social dance group dispersed"')})
      (if (== Which 2)
        (for m (Variables|GW|GetSocBarGuests)
          (if (CallFunction|SocialAlive :Ch m)
            (bind c {NPCC.format('m')}
              (:then
                (if (== {GET('c', 'SocialMode')} 2)
                  (GW|Call|BP_GW_NPCController|SocialLeave :self c :Ch m)))
              (:CastFailed))))
        (Utilities|Array|Clear (Variables|GW|GetSocBarGuests))
        (Variables|GW|SetSocBarOn false)
        {log('"GW: social bar group dispersed"')}))
    ''',
        # a couple member arrived: if the partner is there too both start the same dance in this frame (in step on
        # every client); alone if the partner is gone or no longer dancing
        'SocialCoupleStart': f'''
    (fn SocialCoupleStart (Ch)
      (bind c {NPCC.format('Ch')}
        (:then
          (bind dance {GET('c', 'SocialDance')})
          (bind pt {GET('c', 'Partner')})
          (GW|Set|BP_GW_Character|DanceByPlayer :self Ch :DanceByPlayer false)
          (if (not (CallFunction|SocialAlive :Ch pt))
            (GW|Set|BP_GW_Character|DanceId :self Ch :DanceId dance)
            {log('(cat "GW: social NPC " (Utilities|GetDisplayName :Object Ch) " dances " dance " (partner gone)")')}
            (return))
          (bind pc {NPCC.format('pt')}
            (:then
              (if (== {GET('pc', 'SocialMode')} 1)
                (if {GET('pc', 'SocialArrived')}
                  (GW|Set|BP_GW_Character|DanceId :self Ch :DanceId dance)
                  (GW|Set|BP_GW_Character|DanceByPlayer :self pt :DanceByPlayer false)
                  (GW|Set|BP_GW_Character|DanceId :self pt :DanceId dance)
                  {log('(cat "GW: social couple " (Utilities|GetDisplayName :Object Ch) " + " (Utilities|GetDisplayName :Object pt) " dances " dance " together")')})
                (else
                  (GW|Set|BP_GW_Character|DanceId :self Ch :DanceId dance))))
            (:CastFailed
              (GW|Set|BP_GW_Character|DanceId :self Ch :DanceId dance))))
        (:CastFailed)))
    ''',
        # members destroyed (corpse removal, respawns) or dead leave the group arrays, from the end down
        'SocialPurge': '''
    (fn SocialPurge ()
      (Variables|GW|SetSocK (- (Utilities|Array|Length (Variables|GW|GetSocDancers)) 1))
      (while (>= (Variables|GW|GetSocK) 0)
        (if (not (CallFunction|SocialAlive :Ch (Utilities|Array|Get(acopy) (Variables|GW|GetSocDancers) (Variables|GW|GetSocK))))
          (Utilities|Array|RemoveIndex :TargetArray (Variables|GW|GetSocDancers) :IndexToRemove (Variables|GW|GetSocK)))
        (Variables|GW|SetSocK (- (Variables|GW|GetSocK) 1)))
      (Variables|GW|SetSocK (- (Utilities|Array|Length (Variables|GW|GetSocBarGuests)) 1))
      (while (>= (Variables|GW|GetSocK) 0)
        (if (not (CallFunction|SocialAlive :Ch (Utilities|Array|Get(acopy) (Variables|GW|GetSocBarGuests) (Variables|GW|GetSocK))))
          (Utilities|Array|RemoveIndex :TargetArray (Variables|GW|GetSocBarGuests) :IndexToRemove (Variables|GW|GetSocK)))
        (Variables|GW|SetSocK (- (Variables|GW|GetSocK) 1))))
    ''',
        # valid and alive; the validity test has its own branch (a Blueprint 'and' would read a destroyed corpse)
        'SocialAlive': f'''
    (fn SocialAlive (Ch)
      (if (not ({ISVALID} :Object Ch))
        (return false))
      (return (not (GW|Get|BP_GW_Character|IsDead :self Ch))))
    ''',
        'SocialReady': f'''
    (fn SocialReady (Ch)
      (if (not ({ISVALID} :Object Ch))
        (return false))
      (if (GW|Get|BP_GW_Character|IsDead :self Ch)
        (return false))
      (bind c {NPCC.format('Ch')}
        (:then (return {GET('c', 'SocialArrived')}))
        (:CastFailed (return false))))
    ''',
        # a guest of the group says a small-talk line; the guest standing next to it may answer
        'SocialSayIn': f'''
    (fn SocialSayIn (Which Reply)
      (bind (a b ok) (CallFunction|SocialTalkPair :Which Which))
      (if (not (CallFunction|SocialReady :Ch a))
        (return))
      (CallFunction|Say :Ch a :Cat {CAT_CHATTER})
      (if (and ok (Math|Random|RandomBoolwithWeight :Weight Reply))
        (CallFunction|QueueSay :Ch b :Cat {CAT_REPLY} :Delay {R(1.8, 2.8)})))
    ''',
        # A: a random guest of the group who has arrived; B: the nearest other arrived guest of that group within 2.5 m
        # (Ok false when there is none). Both NPC controllers get Partner = the other one.
        'SocialTalkPair': f'''
    (fn SocialTalkPair (Which)
      (Variables|GW|SetSocTalk (Variables|GW|GetNoChar))
      (Variables|GW|SetSocTalk2 (Variables|GW|GetNoChar))
      (Variables|GW|SetSocUseBar (or (== Which 2) (and (== Which 0) (or (== (Utilities|Array|Length (Variables|GW|GetSocDancers)) 0) (and (> (Utilities|Array|Length (Variables|GW|GetSocBarGuests)) 0) (Math|Random|RandomBool))))))
      (if (Variables|GW|GetSocUseBar)
        (Variables|GW|SetSocGroup (Variables|GW|GetSocBarGuests))
        (else
          (Variables|GW|SetSocGroup (Variables|GW|GetSocDancers))))
      (bind n (Utilities|Array|Length (Variables|GW|GetSocGroup)))
      (if (== n 0)
        (return (Variables|GW|GetSocTalk) (Variables|GW|GetSocTalk2) false))
      (Variables|GW|SetSocTalk (Utilities|Array|Get(acopy) (Variables|GW|GetSocGroup) (Math|Random|RandomIntegerinRange 0 (- n 1))))
      (bind a (Variables|GW|GetSocTalk))
      (if (not (CallFunction|SocialReady :Ch a))
        (return a (Variables|GW|GetSocTalk2) false))
      (Variables|Default|SetBestD 250.0)
      (for m (Variables|GW|GetSocGroup)
        (if (and (!= m a) (CallFunction|SocialReady :Ch m))
          (bind dd (Math|Vector|Distance(Vector) (Transformation|GetActorLocation :self m) (Transformation|GetActorLocation :self a)))
          (if (< dd (Variables|Default|GetBestD))
            (Variables|Default|SetBestD dd)
            (Variables|GW|SetSocTalk2 m))))
      (bind b (Variables|GW|GetSocTalk2))
      (if (not ({ISVALID} :Object b))
        (return a b false))
      (CallFunction|SocialPartners :A a :B b)
      (return a b true))
    ''',
        'SocialPartners': f'''
    (fn SocialPartners (A B)
      (bind ca {NPCC.format('A')}
        (:then
          {SET('ca', 'Partner', 'B')}
          (bind cb {NPCC.format('B')}
            (:then {SET('cb', 'Partner', 'A')})
            (:CastFailed)))
        (:CastFailed)))
    ''',
        'SocialChat': f'''
    (fn SocialChat ()
      (bind now (CallFunction|Now))
      (if (and (Variables|GW|GetSocBarOn) (>= now (Variables|GW|GetSocNextBarChat)))
        (Variables|GW|SetSocNextBarChat (+ now {R(4, 9)}))
        (CallFunction|SocialSayIn :Which 2 :Reply 0.5)
        (if (Math|Random|RandomBoolwithWeight :Weight 0.3)
          (bind s {GSC_}
            (:then
              (GW|Set|BP_GW_GameState|BarToasts :self s :BarToasts (+ (GW|Get|BP_GW_GameState|BarToasts :self s) 1))
              {log('"GW: social toast at the bar"')}
              (bind (ta tb tok) (CallFunction|SocialTalkPair :Which 2))
              (if (CallFunction|SocialReady :Ch ta)
                (CallFunction|Say :Ch ta :Cat {CAT_BAR_TOAST})))
            (:CastFailed))))
      (if (and (Variables|GW|GetSocDanceOn) (>= now (Variables|GW|GetSocNextDanceChat)))
        (Variables|GW|SetSocNextDanceChat (+ now {R(8, 16)}))
        (CallFunction|SocialSayIn :Which 1 :Reply 0.35)))
    ''',
        # dances that must stop: the dead, anyone moving, a dance left over by a body swap (a player in a pawn that an
        # NPC was dancing in, or an NPC in a pawn a player was dancing in)
        'SocialSweep': f'''
    (fn SocialSweep ()
      (for c (Actor|GetAllActorsOfClass :ActorClass {CHAR})
        (if (!= (GW|Get|BP_GW_Character|DanceId :self c) 0)
          (if (GW|Get|BP_GW_Character|IsDead :self c)
            (GW|Set|BP_GW_Character|DanceId :self c :DanceId 0)
            (elif (Pawn|IsPlayerControlled :self c)
              (if (or (not (GW|Get|BP_GW_Character|DanceByPlayer :self c)) (> (Math|Vector|VectorLength (Transformation|GetVelocity :self c)) 40.0))
                (if (GW|Get|BP_GW_Character|DanceByPlayer :self c)
                  {log('(cat "GW: dance stop " (Utilities|GetDisplayName :Object c) " (moved)")')}
                  (else
                    {log('(cat "GW: dance stop " (Utilities|GetDisplayName :Object c) " (body swap)")')}))
                (GW|Set|BP_GW_Character|DanceByPlayer :self c :DanceByPlayer false)
                (GW|Set|BP_GW_Character|DanceId :self c :DanceId 0))
              (else
                (if (or (GW|Get|BP_GW_Character|DanceByPlayer :self c) (> (Math|Vector|VectorLength (Transformation|GetVelocity :self c)) 80.0))
                  {log('(cat "GW: dance stop NPC " (Utilities|GetDisplayName :Object c) " (moving or body swap)")')}
                  (GW|Set|BP_GW_Character|DanceByPlayer :self c :DanceByPlayer false)
                  (GW|Set|BP_GW_Character|DanceId :self c :DanceId 0))))))))
    ''',
        'SocialTick': f'''
    (fn SocialTick ()
      (bind s (CallFunction|GetGS))
      (if (not ({ISVALID} :Object s))
        (return))
      (bind now (CallFunction|Now))
      (bind phase (GW|Get|BP_GW_GameState|Phase :self s))
      (CallFunction|SocialPurge)
      (CallFunction|SocialSweep)
      ; a panic or an event starting: no social life, groups disperse (the guests flee)
      (if (or (< now (GW|Get|BP_GW_GameState|PanicUntil :self s)) (!= (GW|Get|BP_GW_GameState|EventId :self s) 0))
        (Variables|GW|SetSocCalmAt now)
        (if (or (Variables|GW|GetSocDanceOn) (Variables|GW|GetSocBarOn))
          (CallFunction|SocialDisperse :Flee true))
        (return))
      ; a bandit, the kamikaze or the robot (it stays all round) coming near a group: that group runs from it
      (bind (dn df) (CallFunction|SocialThreatAt :Loc {mv(*FLOOR)} :R 1600.0))
      (if (and dn (Variables|GW|GetSocDanceOn))
        (CallFunction|SocialFlee :Which 1 :From df))
      (bind (bn bf) (CallFunction|SocialThreatAt :Loc {mv(*BAR)} :R 1500.0))
      (if (and bn (Variables|GW|GetSocBarOn))
        (CallFunction|SocialFlee :Which 2 :From bf))
      (if (and (Variables|GW|GetSocDanceOn) (and (not (Variables|GW|GetSocClapped)) (>= now (Variables|GW|GetSocEndAt))))
        (Variables|GW|SetSocClapped true)
        (GW|Set|BP_GW_GameState|DanceClaps :self s :DanceClaps (+ (GW|Get|BP_GW_GameState|DanceClaps :self s) 1))
        {log('"GW: social applause (the dance ends)"')}
        (bind (ea eb eok) (CallFunction|SocialTalkPair :Which 1))
        (if (CallFunction|SocialReady :Ch ea)
          (CallFunction|Say :Ch ea :Cat {CAT_DANCE_END})))
      (if (and (Variables|GW|GetSocDanceOn) (>= now (Variables|GW|GetSocDanceClear)))
        (CallFunction|SocialEndGroup :Which 1))
      (if (and (Variables|GW|GetSocBarOn) (>= now (Variables|GW|GetSocBarClear)))
        (CallFunction|SocialEndGroup :Which 2))
      (CallFunction|SocialChat)
      ; new groups only during a round (hiding or hunt)
      (if (not (or (== phase 1) (== phase 2)))
        (Variables|GW|SetSocNextDance 0.0)
        (Variables|GW|SetSocNextBar 0.0)
        ; back in the lobby: the round's guests are gone, end the groups (and the louder gramophone) now
        (if (and (== phase 0) (Variables|GW|GetSocDanceOn))
          (CallFunction|SocialEndGroup :Which 1))
        (if (and (== phase 0) (Variables|GW|GetSocBarOn))
          (CallFunction|SocialEndGroup :Which 2))
        (return))
      (if (<= (Variables|GW|GetSocNextDance) 0.0)
        (Variables|GW|SetSocNextDance (+ now {R(30, 70)})))
      (if (<= (Variables|GW|GetSocNextBar) 0.0)
        (Variables|GW|SetSocNextBar (+ now {R(40, 90)})))
      (if (< now (+ (Variables|GW|GetSocCalmAt) 20.0))
        (return))
      (bind (dn2 df2) (CallFunction|SocialThreatAt :Loc {mv(*FLOOR)} :R 2300.0))
      (bind (bn2 bf2) (CallFunction|SocialThreatAt :Loc {mv(*BAR)} :R 2100.0))
      ; the queues at the bars
      (CallFunction|LifeQTick)
      ; someone plays the piano or an instrument: the floor fills now
      (if (< now (GW|Get|BP_GW_GameState|PianoNext :self (CallFunction|GetGS)))
        (Variables|GW|SetSocNextDance now))
      (if (and (and (not (Variables|GW|GetSocDanceOn)) (>= now (Variables|GW|GetSocNextDance))) (not dn2))
        (Variables|GW|SetSocNextDance (+ now {R(70, 110)}))
        (CallFunction|SocialStartDance :Force false))
      (if (and (and (not (Variables|GW|GetSocBarOn)) (>= now (Variables|GW|GetSocNextBar))) (not bn2))
        (Variables|GW|SetSocNextBar (+ now {R(90, 160)}))
        (CallFunction|SocialStartBar :Force false)))
    ''',
    }
    FLEE = f'''
        (for m (Variables|GW|Get{{arr}})
          (if (CallFunction|SocialAlive :Ch m)
            (bind c {NPCC.format('m')}
              (:then
                (if (and Flee (< {GET('c', 'PanicUntil')} now))
                  (Variables|GW|SetSocFrom (select fok fl (- (Transformation|GetActorLocation :self m) (* (Math|Random|RandomUnitVector) 300.0))))
                  {SET('c', 'PanicUntil', f'(+ now {R(3, 6)})')}
                  {SET('c', 'PanicFrom', '(Variables|GW|GetSocFrom)')}
                  {SET('c', 'IsMoving', 'false')}
                  {SET('c', 'NextMoveTime', 'now')})
                (if (!= {GET('c', 'SocialMode')} 0)
                  (GW|Call|BP_GW_NPCController|SocialCancel :self c :Ch m)))
              (:CastFailed))))'''
    GMW['SocialThreatAt'] = f'''
    (fn SocialThreatAt (Loc R)
      (for c (Actor|GetAllActorsOfClass :ActorClass {CHAR})
        (if (and (!= (GW|Get|BP_GW_Character|Kind :self c) 0) (not (GW|Get|BP_GW_Character|IsDead :self c)))
          (if (< (Math|Vector|Distance2D(Vector) (Transformation|GetActorLocation :self c) Loc) R)
            (return true (Transformation|GetActorLocation :self c)))))
      (return false Loc))
    '''
    FLEE_FROM = FLEE.replace("(Variables|GW|SetSocFrom (select fok fl (- (Transformation|GetActorLocation :self m) (* (Math|Random|RandomUnitVector) 300.0))))",
                             "(Variables|GW|SetSocFrom From)").replace("(and Flee (< ", "(and true (< ")
    GMW['SocialFlee'] = f'''
    (fn SocialFlee (Which From)
      (bind now (CallFunction|Now))
      (if (== Which 1){FLEE_FROM.format(arr='SocDancers')}
        (Utilities|Array|Clear (Variables|GW|GetSocDancers))
        (Variables|GW|SetSocDanceOn false)
        (GW|Set|BP_GW_GameState|DanceOn :self (CallFunction|GetGS) :DanceOn false)
        {log('(cat "GW: social dance group flees (danger at " From ")")')})
      (if (== Which 2){FLEE_FROM.format(arr='SocBarGuests')}
        (Utilities|Array|Clear (Variables|GW|GetSocBarGuests))
        (Variables|GW|SetSocBarOn false)
        {log('(cat "GW: social bar group flees (danger at " From ")")')}))
    '''
    GMW['SocialDisperse'] = f'''
    (fn SocialDisperse (Flee)
      (bind now (CallFunction|Now))
      (bind (fl fok) (CallFunction|EventFocus)){FLEE.format(arr='SocDancers')}{FLEE.format(arr='SocBarGuests')}
      (Utilities|Array|Clear (Variables|GW|GetSocDancers))
      (Utilities|Array|Clear (Variables|GW|GetSocBarGuests))
      (Variables|GW|SetSocDanceOn false)
      (Variables|GW|SetSocBarOn false)
      (GW|Set|BP_GW_GameState|DanceOn :self (CallFunction|GetGS) :DanceOn false)
      {log('"GW: social groups dispersed (panic / event): the guests flee"')})
    '''
    for name, code in GMW.items():
        write(gm, name, code, compile_after=False)
        compile_bp(gm, quiet=True)
    compile_bp(gm)
    print('BP_GW_GameMode', node_problems(gm))
    save(gm)


# ---------------------------------------------------------------- player controller: V, server, client tick, test
if 'pc' in PARTS:
    pc = load_bp('BP_GW_PlayerController')
    for v, t in (('LastDance', 'int'), ('DanceStopSent', 'float'), ('DanceMusicOn', 'bool'), ('SocTestStep', 'int'),
                 ('SocTestOn', 'bool')):
        ensure_var(pc, v, t, category='GW')
    ensure_var(pc, 'GramoComp', obj_class=unreal.AudioComponent, category='GW')
    ensure_var(pc, 'GramoSound', obj_class=unreal.SoundBase, category='Audio')
    ensure_var(pc, 'ClapSounds', obj_class=unreal.SoundBase, array=True, category='Audio')
    ensure_var(pc, 'ClinkSounds', obj_class=unreal.SoundBase, array=True, category='Audio')
    for v, t in (('LastClaps', 'int'), ('LastToasts', 'int'), ('SfxInit', 'bool')):
        ensure_var(pc, v, t, category='GW')
    ensure_fn(pc, 'SocialSfx')
    ensure_var(pc, 'DancePrompt', obj_class=unreal.load_asset('/Game/GW/Blueprints/BP_GW_KeyPrompt').generated_class(), category='GW')
    for f in ('RequestDance', 'DanceWatch', 'DanceMusic', 'DancePromptTick', 'DanceAutoStop', 'SocialTestTick'):
        ensure_fn(pc, f)
    ensure_fn(pc, 'SocialTestLog', inputs=[('St', 'int')])
    ensure_fn(pc, 'SocialClientTick')                      # called by EventClientTick (s32_events.py)
    ensure_fn(pc, 'GWDance', exec_fn=True)
    ensure_fn(pc, 'GWDanceStop', exec_fn=True)
    compile_bp(pc, quiet=True)
    cdo(pc).set_editor_property('GramoSound', unreal.load_asset('/Game/GW/Audio/MUS_Gramophone'))
    _sfx = lambda kind: [unreal.load_asset(f'/Game/GW/Audio/Social/SFX_Social_{kind}_0{k}') for k in (1, 2, 3)
                         if EAL.does_asset_exist(f'/Game/GW/Audio/Social/SFX_Social_{kind}_0{k}')]
    cdo(pc).set_editor_property('ClapSounds', _sfx('Applause'))
    cdo(pc).set_editor_property('ClinkSounds', _sfx('Clink'))
    print('social sfx:', len(_sfx('Applause')), 'applause,', len(_sfx('Clink')), 'clinks')
    PNAME = '(PlayerState|GetPlayerName :self (GW|Get|/Script/Engine.Controller|PlayerState))'
    X0, Y0, X1, Y1 = DANCE_FLOOR_RECT
    SERVER = lambda cmd: f'''(if (Networking|HasAuthority)
        (CallFunction|{cmd})
        (else
          (Development|ExecuteConsoleCommand :Command "ServerExec {cmd}" :SpecificPlayer self)))'''
    PCW = {
        'RequestDance': f'(fn RequestDance ()\n  {SERVER("GWDance")})\n',
        # V on the server: toggle; a random dance, never the same one twice in a row
        'GWDance': f'''
    (fn GWDance ()
      (bind ch {MYCH}
        (:then
          (if (GW|Get|BP_GW_Character|IsDead :self ch)
            (return))
          (if (!= (GW|Get|BP_GW_Character|DanceId :self ch) 0)
            (GW|Set|BP_GW_Character|DanceByPlayer :self ch :DanceByPlayer false)
            (GW|Set|BP_GW_Character|DanceId :self ch :DanceId 0)
            {log(f'(cat "GW: dance stop " {PNAME} " (key)")')}
            (return))
          (Variables|GW|SetLastDance (+ 1 (% (+ (Variables|GW|GetLastDance) (Math|Random|RandomIntegerinRange 0 {N - 2})) {N})))
          (GW|Set|BP_GW_Character|DanceByPlayer :self ch :DanceByPlayer true)
          (GW|Set|BP_GW_Character|DanceId :self ch :DanceId (Variables|GW|GetLastDance))
          {log(f'(cat "GW: dance start " {PNAME} " id=" (Variables|GW|GetLastDance))')})
        (:CastFailed)))
    ''',
        'GWDanceStop': f'''
    (fn GWDanceStop ()
      (bind ch {MYCH}
        (:then
          (if (!= (GW|Get|BP_GW_Character|DanceId :self ch) 0)
            (GW|Set|BP_GW_Character|DanceByPlayer :self ch :DanceByPlayer false)
            (GW|Set|BP_GW_Character|DanceId :self ch :DanceId 0)
            {log(f'(cat "GW: dance stop " {PNAME} " (moved)")')}))
        (:CastFailed)))
    ''',
        'DanceWatch': f'''
    (fn DanceWatch ()
      (for c (Actor|GetAllActorsOfClass :ActorClass {CHAR})
        (GW|Call|BP_GW_Character|DanceCheck :self c)))
    ''',
        # my own dance stops as soon as I move (the server sweep would catch it a little later)
        'DanceAutoStop': f'''
    (fn DanceAutoStop ()
      (bind ch {MYCH}
        (:then
          (if (and (!= (GW|Get|BP_GW_Character|DanceId :self ch) 0) (> (Math|Vector|VectorLength (Transformation|GetVelocity :self ch)) 40.0))
            (if (> {NOW} (Variables|GW|GetDanceStopSent))
              (Variables|GW|SetDanceStopSent (+ {NOW} 0.5))
              {SERVER("GWDanceStop")})))
        (:CastFailed)))
    ''',
        # while the guests dance, the ballroom gramophone plays louder
        'DanceMusic': f'''
    (fn DanceMusic ()
      (bind s {GSC}
        (:then
          (bind on (GW|Get|BP_GW_GameState|DanceOn :self s))
          (if (== on (Variables|GW|GetDanceMusicOn))
            (return))
          (Variables|GW|SetDanceMusicOn on)
          (if (not ({ISVALID} :Object (Variables|GW|GetGramoComp)))
            (for a (Actor|GetAllActorswithTag :Tag "GW_Audio")
              (bind amb (Utilities|Casting|CastToAmbientSound a)
                (:then
                  (bind ac (GW|Get|/Script/Engine.AmbientSound|AudioComponent :self amb))
                  (if ({ISVALID} :Object ac)
                    (if (== (GW|Get|/Script/Engine.AudioComponent|Sound :self ac) (Variables|Audio|GetGramoSound))
                      (Variables|GW|SetGramoComp ac))))
                (:CastFailed))))
          (if ({ISVALID} :Object (Variables|GW|GetGramoComp))
            (GW|Call|/Script/Engine.AudioComponent|AdjustVolume :self (Variables|GW|GetGramoComp) :AdjustVolumeDuration (select on 2.5 4.0) :AdjustVolumeLevel (select on 2.1 1.0))
            {log('(cat "GW: dance music " on)')}))
        (:CastFailed)))
    ''',
        # applause at the dance floor when a dance group ends, clinking glasses at the bar (local, from GS counters)
        'SocialSfx': f'''
    (fn SocialSfx ()
      (bind s {GSC}
        (:then
          (bind claps (GW|Get|BP_GW_GameState|DanceClaps :self s))
          (bind toasts (GW|Get|BP_GW_GameState|BarToasts :self s))
          (if (not (Variables|GW|GetSfxInit))
            (Variables|GW|SetSfxInit true)
            (Variables|GW|SetLastClaps claps)
            (Variables|GW|SetLastToasts toasts)
            (return))
          (if (!= claps (Variables|GW|GetLastClaps))
            (Variables|GW|SetLastClaps claps)
            (bind cs (Variables|Audio|GetClapSounds))
            (if (> (Utilities|Array|Length cs) 0)
              (Audio|PlaySoundatLocation :Sound (Utilities|Array|Get(acopy) cs (Math|Random|RandomIntegerinRange 0 (- (Utilities|Array|Length cs) 1))) :Location {mv(FLOOR[0], FLOOR[1], 160.0)})))
          (if (!= toasts (Variables|GW|GetLastToasts))
            (Variables|GW|SetLastToasts toasts)
            (bind ks (Variables|Audio|GetClinkSounds))
            (if (> (Utilities|Array|Length ks) 0)
              (Audio|PlaySoundatLocation :Sound (Utilities|Array|Get(acopy) ks (Math|Random|RandomIntegerinRange 0 (- (Utilities|Array|Length ks) 1))) :Location {mv(4420.0, 1380.0, 150.0)}))))
        (:CastFailed)))
    ''',
        # on the dance floor and not dancing: a "V Danser" key cap floats over me (local only)
        'DancePromptTick': f'''
    (fn DancePromptTick ()
      (bind ch {MYCH}
        (:then
          (bind p (Transformation|GetActorLocation :self ch))
          (bind on (and (and (and (> (.x p) {X0}) (< (.x p) {X1})) (and (> (.y p) {Y0}) (< (.y p) {Y1}))) (and (< (.z p) 300.0) (and (== (GW|Get|BP_GW_Character|DanceId :self ch) 0) (not (GW|Get|BP_GW_Character|IsDead :self ch))))))
          (if (not ({ISVALID} :Object (Variables|GW|GetDancePrompt)))
            (if (not on)
              (return))
            (Variables|GW|SetDancePrompt (Game|SpawnActorfromClass :Class "{PROMPT}" :SpawnTransform (Math|Transform|MakeTransform :Location (+ p (Math|Vector|MakeVector 0.0 0.0 125.0))) :CollisionHandlingOverride "AlwaysSpawn"))
            (GW|Call|BP_GW_KeyPrompt|SetPrompt :self (Variables|GW|GetDancePrompt) :Key "V" :Label "Danser"))
          (Transformation|SetActorLocation :self (Variables|GW|GetDancePrompt) :NewLocation (+ p (Math|Vector|MakeVector 0.0 0.0 125.0)) :bSweep false :bTeleport true)
          (GW|Call|BP_GW_KeyPrompt|ShowPrompt :self (Variables|GW|GetDancePrompt) :On on))
        (:CastFailed
          (if ({ISVALID} :Object (Variables|GW|GetDancePrompt))
            (GW|Call|BP_GW_KeyPrompt|ShowPrompt :self (Variables|GW|GetDancePrompt) :On false)))))
    ''',
        'SocialClientTick': '''
    (fn SocialClientTick ()
      (if (not (Pawn|IsLocalPlayerController))
        (return))
      (CallFunction|DanceWatch)
      (CallFunction|DanceAutoStop)
      (CallFunction|DanceMusic)
      (CallFunction|SocialSfx)
      (CallFunction|DancePromptTick)
      (if (and (not (Variables|GW|GetSocTestOn)) (or (Utilities|HasLaunchOption :OptionToCheck "GWSocialTest") (or (Utilities|HasLaunchOption :OptionToCheck "GWSocialWatch") (Utilities|HasLaunchOption :OptionToCheck "GWDanceShots"))))
        (Variables|GW|SetSocTestOn true)
        (Utilities|Time|SetTimerbyFunctionName :Object self :FunctionName "SocialTestTick" :Time 2.0 :bLooping true)))
    ''',
    }
    # headless test script (host: -GWSocialTest; a client: -GWSocialWatch)
    HOST_STEPS = [
        (3, '(CallFunction|DevServer :Cmd "GWDevQuickTest 1")'), (5, '(CallFunction|DevServer :Cmd "GWDevAutoEvents 0")'),
        (6, '(CallFunction|DevServer :Cmd "GWDevTeleport 3000 3200 130")'),
        (7, '(CallFunction|RequestDance)'), (10, '(CallFunction|RequestDance)'), (12, '(CallFunction|RequestDance)'),
        (13, '(AI|Navigation|SimpleMovetoLocation :Controller self :Goal (Math|Vector|MakeVector 3000.0 2950.0 100.0))'),
        (16, '(CallFunction|DevServer :Cmd "GWDevDanceNow")'), (24, '(CallFunction|DevServer :Cmd "GWDevBarNow")'),
        (28, '(CallFunction|RequestDance)'), (34, '(CallFunction|DevServer :Cmd "GWDevNPCKill")'),
        (40, '(CallFunction|DevServer :Cmd "GWDevEvent 3")'), (46, '(CallFunction|DevServer :Cmd "GWDevEventStop")'),
        (52, '(CallFunction|DevServer :Cmd "GWDevDanceNow")'), (54, '(CallFunction|DevServer :Cmd "GWDevBarNow")'),
        (99, '(CallFunction|DevServer :Cmd "GWDevTestEnd")')]
    CLIENT_STEPS = [(4, '(CallFunction|DevServer :Cmd "GWDevRespawn")'), (9, '(CallFunction|RequestDance)'), (14, '(CallFunction|RequestDance)'), (18, '(CallFunction|RequestDance)'),
                    (22, '(CallFunction|RequestDance)')]
    # rendered check (-GWDanceShots, never while the user plays): a ghost camera over the dance floor and the bar
    ROT = lambda yaw, pitch: f'(Pawn|SetControlRotation :self self :NewRotation (Math|Rotator|MakeRotator :Pitch {pitch} :Yaw {yaw}))'
    SHOT = '(Development|ExecuteConsoleCommand :Command "HighResShot 1600x900" :SpecificPlayer self)'
    SHOT_STEPS = [(3, '(CallFunction|DevServer :Cmd "GWDevQuickTest 1")'), (4, '(CallFunction|DevServer :Cmd "GWDevAutoEvents 0")'),
                  (5, '(CallFunction|DevServer :Cmd "GWDevDanceNow")'), (6, '(CallFunction|DevServer :Cmd "GWDevBarNow")'),
                  (7, '(CallFunction|DevServer :Cmd "GWDevGhost")'),
                  # the dance floor from its south edge, eye height, then from above the chairs
                  (14, '(CallFunction|DevServer :Cmd "GWDevTeleport 3000 2880 175")'), (15, ROT(90.0, -5.0)),
                  (16, SHOT), (17, SHOT), (18, SHOT), (19, SHOT),
                  (20, '(CallFunction|DevServer :Cmd "GWDevTeleport 2560 2900 300")'), (21, ROT(55.0, -16.0)),
                  (22, SHOT), (23, SHOT),
                  # the bar crowd from the billiard table side
                  (24, '(CallFunction|DevServer :Cmd "GWDevTeleport 4420 950 200")'), (25, ROT(90.0, -8.0)),
                  (27, SHOT), (28, SHOT), (29, SHOT),
                  (30, '(CallFunction|DevServer :Cmd "GWDevTeleport 4900 1150 230")'), (31, ROT(150.0, -10.0)),
                  (32, SHOT), (33, SHOT), (35, '(CallFunction|DevServer :Cmd "GWDevTestEnd")')]
    PCW['SocialTestTick'] = '''
    (fn SocialTestTick ()
      (Variables|GW|SetSocTestStep (+ (Variables|GW|GetSocTestStep) 1))
      (bind st (Variables|GW|GetSocTestStep))
      (if (Utilities|HasLaunchOption :OptionToCheck "GWDanceShots")
    ''' + '\n'.join(f'    (if (== st {s}) {c})' for s, c in SHOT_STEPS) + '''
        (elif (Utilities|HasLaunchOption :OptionToCheck "GWSocialTest")
    ''' + '\n'.join(f'      (if (== st {s}) {c})' for s, c in HOST_STEPS) + '''
          (else
    ''' + '\n'.join(f'        (if (== st {s}) {c})' for s, c in CLIENT_STEPS) + ''')))
      (if (<= st 100)
        (CallFunction|SocialTestLog :St st)))
    '''
    PCW['SocialTestLog'] = f'''
    (fn SocialTestLog (St)
      (bind p (Pawn|GetControlledPawn :self self))
      (bind s {GSC}
        (:then
          (Development|PrintString :InString (cat "GW socialtest step " St " auth=" (Networking|HasAuthority) " danceOn=" (GW|Get|BP_GW_GameState|DanceOn :self s) " phase=" (GW|Get|BP_GW_GameState|Phase :self s) " pawn=" (Utilities|GetDisplayName :Object p)) :bPrintToScreen false)
          (for c (Actor|GetAllActorsOfClass :ActorClass {CHAR})
            (if (or (!= (GW|Get|BP_GW_Character|DanceId :self c) 0) (Pawn|IsPlayerControlled :self c))
              (bind head (cat "GW socialtest   " (Utilities|GetDisplayName :Object c) " player=" (Pawn|IsPlayerControlled :self c) " dance=" (GW|Get|BP_GW_Character|DanceId :self c) " shown=" (GW|Get|BP_GW_Character|DanceShown :self c) " dead=" (GW|Get|BP_GW_Character|IsDead :self c) " at=" (Transformation|GetActorLocation :self c)))
              (bind inst (Utilities|Casting|CastToAnimSingleNodeInstance ({SKM}|GetAnimInstance :self (GW|Get|/Script/Engine.Character|Mesh :self c)))
                (:then
                  (Development|PrintString :InString (cat head " clip=" (Utilities|GetDisplayName :Object (GW|Call|/Script/Engine.AnimSingleNodeInstance|GetAnimationAsset :self inst))) :bPrintToScreen false))
                (:CastFailed
                  (Development|PrintString :InString (cat head " clip=ABP") :bPrintToScreen false)))))
          (if (Networking|HasAuthority)
            (bind gm {GMC}
              (:then
                (Development|PrintString :InString (cat "GW socialtest   groups: dance=" (GW|Get|BP_GW_GameMode|SocDanceOn :self gm) " (" (Utilities|Array|Length (GW|Get|BP_GW_GameMode|SocDancers :self gm)) ") bar=" (GW|Get|BP_GW_GameMode|SocBarOn :self gm) " (" (Utilities|Array|Length (GW|Get|BP_GW_GameMode|SocBarGuests :self gm)) ")") :bPrintToScreen false))
              (:CastFailed))))
        (:CastFailed)))
    '''
    PCW.pop('DanceWatch', None)   # POP_DW: s44_npc_life.py renders it now
    for name, code in PCW.items():
        write(pc, name, code, compile_after=False)
        compile_bp(pc, quiet=True)
    compile_bp(pc, quiet=True)
    wire_input(pc, 'IA_Dance', {'Started': 'RequestDance'}, pos=(0, 4400))
    compile_bp(pc)
    print('BP_GW_PlayerController', node_problems(pc))
    save(pc)
    print('s36 done: dances', [a.get_name() for a in anims])

