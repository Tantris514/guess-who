"""Events, second round (the user's test feedback of 2026-11-03). Runs after s32_events.py, s14 npc and s39.

- Zombie event (Id 6, GM.StartZombie): each zombie falls GM.ZombieLife (15) s after it turned, bites once per GM.ZombieBite (8) s at most, 6 at a time; a guest turns (Kind 4, Zombify: 2 s scene, scream, groan, the skin goes
  desaturated grey-green with dark bruises: parameter ZombieAmount of M_GW_GenChar, added by this script, driven per
  character by SetScalarParameterValueOnMaterials; a shambling lean and a slow gait, no generated asset at all), walks
  slowly at the nearest guest (BP_GW_ZombieController), contaminates on touch (ZombieTick). A touched player becomes a
  zombie too (cured when the event ends, if still alive). Anyone may kill one (OnCharacterShot / HurtCharacter ->
  ZombieDown). At the end the NPC zombies fall.
- NPCs that see a kamikaze or a zombie run from it (ThreatTick).
- Breakers: BP_GW_Breaker on a wall, E (PC.TryBreaker -> GWBreaker): a living player closes them, the blackout event
  starts; once per game (GM.BreakerUsed; dev: GWDevBreakerReset). The natural blackout event stays.
- Fire: red flashing alarm lights in the rooms during the fire (BP_GW_AlarmLight, GM.FireAlarmOn / Off).
- Seats: NPCs sit on the props listed in GM.SitLoc / SitYaw (found here in L_Manor by mesh name, frozen GW_Manual
  props), SocialMode 4 + DanceId 10 (Tools/anim/dances.py Assis); 70 % stay 12-40 s, 30 % stay 60-150 s.
- Ballroom: a guest dancing there draws up to 3 NPCs within 4.5 m (SocialMode 5, DanceFollowTick): same dance, facing him.
- Dev: GWDevNPCCount N (GM.NPCCount, applied at once), GWDevBreakerReset, event 6. -GWEvTest: scripted headless test.
Usage: ue_run.py s40_events2.py [mat] [gm] [pc] [npc] [ch]  (default: all; mat patches the character master material).
"""
import sys, importlib, re, math
sys.path.insert(0, r'J:\Projets\Unreal_Projects\Guess Who\Tools\gameplay')
import gw_lib; importlib.reload(gw_lib)
from gw_lib import *

try:
    UE_ARGS
except NameError:
    UE_ARGS = []
PARTS = set(UE_ARGS) or {'mat', 'bps', 'ch', 'npc', 'gm', 'pc'}     # 'bandit': only BP_GW_BanditController, from s32's text
TOOLS = r'J:\Projets\Unreal_Projects\Guess Who\Tools'
REP = unreal.BlueprintVariableReplication
V3 = unreal.Vector.static_struct()
MEL = unreal.MaterialEditingLibrary
AT = unreal.AssetToolsHelpers.get_asset_tools()
CHAR = '"/Game/GW/Blueprints/BP_GW_Character.BP_GW_Character_C"'
NPCC = '"/Game/GW/Blueprints/BP_GW_NPCController.BP_GW_NPCController_C"'
ISVALID = 'GW|Call|/Script/Engine.KismetSystemLibrary|IsValid'
GSC = '(Utilities|Casting|CastToBP_GW_GameState (Game|GetGameState))'
GMC = '(Utilities|Casting|CastToBP_GW_GameMode (Game|GetGameMode))'
MYCH = '(Utilities|Casting|CastToBP_GW_Character (Pawn|GetControlledPawn :self self))'
NOW = '(CallFunction|Now)'
TNOW = '(Utilities|Time|GetGameTimeinSeconds)'
CH = lambda var, o: f'(GW|Get|BP_GW_Character|{var} :self {o})'
CHS = lambda var, o, v: f'(GW|Set|BP_GW_Character|{var} :self {o} :{var} {v})'
LOC = lambda o: f'(Transformation|GetActorLocation :self {o})'
DIST2 = lambda a, b: f'(Math|Vector|Distance2D(Vector) {a} {b})'
RF = lambda a, b: f'(Math|Random|RandomFloatinRange {float(a)} {float(b)})'
L = lambda n: f'(Variables|Default|Get{n})'
SL = lambda n, v: f'(Variables|Default|Set{n} {v})'
G_ = lambda n: f'(Variables|GW|Get{n})'
SG = lambda n, v: f'(Variables|GW|Set{n} {v})'
NC = lambda var, c: f'(GW|Get|BP_GW_NPCController|{var} :self {c})'
NCS = lambda var, c, v: f'(GW|Set|BP_GW_NPCController|{var} :self {c} :{var} {v})'


def log(expr):
    return f'(Development|PrintString :InString {expr} :bPrintToScreen false)'


CAT_SCREAM, CAT_SHOUT, CAT_GASP, CAT_POWER = 1, 2, 19, 22
ZOMBIE_MAX = 6       # at the same time (the user, 2026-11-05: it spread too fast)
MOANS = ['/Game/GW/Audio/Gen/zombie/SFX_Zombie_Moan_%02d' % i for i in (1, 2, 3)]      # Tools/audio/fb5_sounds.py: existing gasps pitched down
BALL = (2040.0, 3960.0, 2420.0, 4120.0)     # ballroom floor box (x0, x1, y0, y1), ground floor
GROAN = '/Game/GW/Audio/Gen/zombie/SFX_Zombie_Groan'

# ---------------------------------------------------------------- master material: ZombieAmount
if 'mat' in PARTS:
    masters = {}
    for p in EAL.list_assets('/Game/GW/Characters/Gen', recursive=True):
        n = p.split('/')[-1].split('.')[0]
        if n.startswith('MI_') and not n.endswith('_Ghost'):
            a = unreal.load_asset(p)
            if isinstance(a, unreal.MaterialInstanceConstant):
                par = a.get_editor_property('parent')
                while isinstance(par, unreal.MaterialInstance):
                    par = par.get_editor_property('parent')
                if par:
                    masters[par.get_path_name()] = par
    # P = UV (PreSkinnedPosition does not exist in a pixel shader: the material fell back to the default one)
    CODE = ('float n = sin(P.x * 37.0 + 2.0 * sin(P.y * 23.0)) * sin(P.y * 41.0 + 2.0 * sin(P.x * 29.0));\n'
            'float m = saturate(n * 1.3 + 0.8);\n'
            'float l = dot(C, float3(0.3, 0.59, 0.11));\n'
            'float3 z = lerp(l * float3(0.42, 0.52, 0.34), C * float3(0.55, 0.68, 0.5), 0.15);\n'
            'z *= lerp(float3(0.34, 0.2, 0.26), float3(1.0, 1.0, 1.0), m);\n'
            'return lerp(C, z, saturate(A));')
    for m in masters.values():
        if m.get_name() == 'M_GW_Ghost':
            continue
        if 'ZombieAmount' in [str(x) for x in MEL.get_scalar_parameter_names(m)]:
            cu = MEL.get_material_property_input_node(m, unreal.MaterialProperty.MP_BASE_COLOR)
            cu.set_editor_property('code', CODE)
            uv = MEL.create_material_expression(m, unreal.MaterialExpressionTextureCoordinate, -500, -650)
            assert MEL.connect_material_expressions(uv, '', cu, 'P')
            MEL.recompile_material(m)
            EAL.save_loaded_asset(m)
            print('zombie: pattern updated in', m.get_name())
            continue
        src = MEL.get_material_property_input_node(m, unreal.MaterialProperty.MP_BASE_COLOR)
        assert src, m.get_name()
        cu = MEL.create_material_expression(m, unreal.MaterialExpressionCustom, -200, -700)
        ci = [unreal.CustomInput(), unreal.CustomInput(), unreal.CustomInput()]
        for x, nm in zip(ci, 'CPA'):
            x.set_editor_property('input_name', nm)
        cu.set_editor_property('inputs', ci)
        cu.set_editor_property('code', CODE)
        cu.set_editor_property('output_type', unreal.CustomMaterialOutputType.CMOT_FLOAT3)
        cu.set_editor_property('description', 'Zombie')
        pos = MEL.create_material_expression(m, unreal.MaterialExpressionTextureCoordinate, -500, -650)
        amt = MEL.create_material_expression(m, unreal.MaterialExpressionScalarParameter, -500, -550)
        amt.set_editor_property('parameter_name', 'ZombieAmount')
        amt.set_editor_property('default_value', 0.0)
        out = MEL.get_material_property_input_node_output_name(m, unreal.MaterialProperty.MP_BASE_COLOR)
        assert MEL.connect_material_expressions(src, out, cu, 'C')
        assert MEL.connect_material_expressions(pos, '', cu, 'P')
        assert MEL.connect_material_expressions(amt, '', cu, 'A')
        assert MEL.connect_material_property(cu, '', unreal.MaterialProperty.MP_BASE_COLOR)
        MEL.recompile_material(m)
        EAL.save_loaded_asset(m)
        print('zombie: ZombieAmount added to', m.get_path_name())
    print('masters', list(masters))

ch = load_bp('BP_GW_Character')
chc = ch.generated_class()

# ---------------------------------------------------------------- the groan (Tools/audio/synth_zombie.py -> this import)
if 'bps' in PARTS:
    _wav = TOOLS + r'\audio\out_zombie\SFX_Zombie_Groan.wav'
    t = unreal.AssetImportTask()
    t.filename = _wav; t.destination_path = '/Game/GW/Audio/Gen/zombie'; t.automated = True; t.replace_existing = True; t.save = True
    AT.import_asset_tasks([t])
    s = unreal.load_asset(GROAN)
    s.set_editor_property('sound_class_object', unreal.load_asset('/Game/GW/Audio/Classes/SC_GW_SFX'))
    s.set_editor_property('attenuation_settings', unreal.load_asset('/Game/GW/Audio/ATT_GW_Voice'))
    EAL.save_loaded_asset(s, False)

    # ------------------------------------------------------------ breaker box and alarm light
    def emissive(name, color, strength):
        p = f'/Game/GW/Materials/{name}'
        m = unreal.load_asset(p) if EAL.does_asset_exist(p) else AT.create_asset(name, '/Game/GW/Materials', unreal.MaterialInstanceConstant, unreal.MaterialInstanceConstantFactoryNew())
        MEL.set_material_instance_parent(m, unreal.load_asset('/Game/GW/Materials/Master/M_GW_Emissive'))
        MEL.set_material_instance_vector_parameter_value(m, 'Color', unreal.LinearColor(*color))
        MEL.set_material_instance_scalar_parameter_value(m, 'Strength', strength)
        MEL.update_material_instance(m)
        EAL.save_loaded_asset(m)
        return m

    def part(bp, name, asset, mat, loc, scale, parent='DefaultSceneRoot'):
        c = ensure_component(bp, name, unreal.StaticMeshComponent, parent)
        c.set_editor_property('static_mesh', unreal.load_asset(asset))
        c.set_editor_property('override_materials', [mat])
        c.set_editor_property('relative_location', unreal.Vector(*loc))
        c.set_editor_property('relative_scale3d', unreal.Vector(*scale))
        c.set_editor_property('cast_shadow', False)
        c.set_collision_enabled(unreal.CollisionEnabled.NO_COLLISION)
        return c

    def actor(name):
        bp = load_or_create_bp(name, unreal.Actor)
        compile_bp(bp, quiet=True)
        d = cdo(bp)
        d.set_editor_property('replicates', True)
        d.set_editor_property('always_relevant', True)
        return bp

    GREY = emissive('MI_GW_BreakerGrey', (0.05, 0.055, 0.06, 1), 1.0)
    BLACK = emissive('MI_GW_BreakerBlack', (0.008, 0.008, 0.008, 1), 1.0)
    AMBER = emissive('MI_GW_BreakerLamp', (1.0, 0.35, 0.05, 1), 12.0)
    RED = emissive('MI_GW_AlarmBeacon', (1.0, 0.02, 0.01, 1), 60.0)
    br = actor('BP_GW_Breaker')
    CUBE, SPH = '/Engine/BasicShapes/Cube', '/Engine/BasicShapes/Sphere'
    part(br, 'Box', CUBE, GREY, (6, 0, 0), (0.12, 0.5, 0.7))
    part(br, 'Lamp', SPH, AMBER, (13, 18, 28), (0.05, 0.05, 0.05))
    pivot = ensure_component(br, 'LeverRoot', unreal.SceneComponent, 'DefaultSceneRoot')
    pivot.set_editor_property('relative_location', unreal.Vector(13, 0, 0))
    part(br, 'Lever', CUBE, BLACK, (6, 0, 12), (0.03, 0.03, 0.26), parent='LeverRoot')
    part(br, 'Grip', SPH, RED, (6, 0, 25), (0.07, 0.07, 0.07), parent='LeverRoot')
    ensure_var(br, 'Thrown', 'bool', rep=REP.REP_NOTIFY, category='GW')
    ensure_fn(br, 'OnRep_Thrown')
    compile_bp(br, quiet=True)
    write(br, 'OnRep_Thrown', '''
(fn OnRep_Thrown ()
  (Transformation|SetRelativeRotation :self (Variables|Default|GetLeverRoot) :NewRotation (Math|Rotator|MakeRotator :Pitch (select (Variables|GW|GetThrown) 120.0 0.0)) :bSweep false :bTeleport true))
''', compile_after=False)
    compile_bp(br)
    print('BP_GW_Breaker', node_problems(br))
    save(br)

    al = actor('BP_GW_AlarmLight')
    part(al, 'Beacon', SPH, RED, (0, 0, 0), (0.16, 0.16, 0.16))
    pl = ensure_component(al, 'Red', unreal.PointLightComponent, 'DefaultSceneRoot')
    pl.set_editor_property('light_color', unreal.Color(r=255, g=18, b=8, a=255))
    pl.set_editor_property('intensity', 0.0)
    pl.set_editor_property('attenuation_radius', 1700.0)
    pl.set_editor_property('cast_shadows', False)
    ensure_fn(al, 'Flash')
    ensure_var(al, 'FlashN', 'int', category='GW')
    compile_bp(al, quiet=True)
    write(al, 'Flash', '''
(fn Flash ()
  (Variables|GW|SetFlashN (+ (Variables|GW|GetFlashN) 1))
  (bind on (< (% (Variables|GW|GetFlashN) 8) 4))
  (Rendering|Components|Light|SetIntensity :self (Variables|Default|GetRed) :NewIntensity (select on 280000.0 0.0))
  (Rendering|SetVisibility :self (Variables|Default|GetBeacon) :bNewVisibility on :bPropagateToChildren false))
''', compile_after=False)
    write(al, 'EventGraph', '''
(event EventBeginPlay
  (Utilities|Time|SetTimerbyFunctionName :Object self :FunctionName "Flash" :Time 0.1 :bLooping true))
''', compile_after=False)
    cdo(al).set_editor_property('initial_life_span', 200.0)
    compile_bp(al)
    print('BP_GW_AlarmLight', node_problems(al))
    save(al)

# ---------------------------------------------------------------- character: the zombie's skin, gait and groan
if 'ch' in PARTS:
    ensure_var(ch, 'ZombieAmt', 'float', category='GW')
    ensure_var(ch, 'ZombieGroan', 'int', rep=REP.REP_NOTIFY, category='GW')
    ensure_var(ch, 'ZombieSnd', obj_class=unreal.SoundBase, category='GW')
    ensure_var(ch, 'ZombieSnds', obj_class=unreal.SoundBase, array=True, category='GW')
    ensure_var(ch, 'ZombieSince', 'float', category='GW')                          # server: when it turned (GM.ZombieLife later it falls)
    ensure_var(ch, 'ZombieBiteAt', 'float', category='GW')                         # server: its next contamination
    for f in ('ZombieVisual', 'ZombieAnim', 'ZombiePose', 'OnRep_ZombieGroan'):
        ensure_fn(ch, f)
    compile_bp(ch, quiet=True)
    if EAL.does_asset_exist(MOANS[0]):
        cdo(ch).set_editor_property('ZombieSnd', unreal.load_asset(MOANS[0]))
        cdo(ch).set_editor_property('ZombieSnds', [unreal.load_asset(m_) for m_ in MOANS])
    _clip = '/Game/GW/Anims/Dance/AS_GW_Dance_Assis'
    if EAL.does_asset_exist(_clip):
        _a = list(cdo(ch).get_editor_property('DanceAnims'))
        if len(_a) == 9:
            cdo(ch).set_editor_property('DanceAnims', _a + [unreal.load_asset(_clip)])
        _a = list(cdo(ch).get_editor_property('DanceAnims'))
        _clip = '/Game/GW/Anims/Dance/AS_GW_Dance_Zombie'
        if len(_a) == 10 and EAL.does_asset_exist(_clip):
            cdo(ch).set_editor_property('DanceAnims', _a + [unreal.load_asset(_clip)])
        print('DanceAnims', len(cdo(ch).get_editor_property('DanceAnims')))
    MESHC = '(Variables|Character|GetMesh)'
    write(ch, 'ZombieVisual', '''
(fn ZombieVisual ()
  (if (or (== (Variables|GW|GetKind) 4) (> (Variables|GW|GetZombieAmt) 0.0))
    (Utilities|Time|SetTimerbyFunctionName :Object self :FunctionName "ZombieAnim" :Time 0.08 :bLooping true)))
''', compile_after=False)
    # arms out: the shamble clip replaces the walk on this machine; repairs itself if a dance reset or a mesh swap took it away
    _SKM = 'GW|Call|/Script/Engine.SkeletalMeshComponent'
    _ZC = '(Utilities|Array|Get(acopy) (Variables|Dance|GetDanceAnims) 10)'
    write(ch, 'ZombiePose', f'''
(fn ZombiePose ()
  (if (<= (Utilities|Array|Length (Variables|Dance|GetDanceAnims)) 10)
    (return))
  (bind inst (Utilities|Casting|CastToAnimSingleNodeInstance ({_SKM}|GetAnimInstance :self {MESHC}))
    (:then
      (if (!= (GW|Call|/Script/Engine.AnimSingleNodeInstance|GetAnimationAsset :self inst) {_ZC})
        ({_SKM}|PlayAnimation :self {MESHC} :NewAnimToPlay {_ZC} :bLooping true)))
    (:CastFailed
      ({_SKM}|PlayAnimation :self {MESHC} :NewAnimToPlay {_ZC} :bLooping true))))
''', compile_after=False)
    write(ch, 'ZombieAnim', f'''
(fn ZombieAnim ()
  (if (Variables|GW|GetIsDead)
    (Utilities|Time|ClearTimerbyFunctionName :Object self :FunctionName "ZombieAnim")
    (return))
  (bind on (== (Variables|GW|GetKind) 4))
  (Variables|GW|SetZombieAmt (Math|Float|Clamp(Float) :Value (+ (Variables|GW|GetZombieAmt) (select on 0.05 -0.05)) :Min 0.0 :Max 1.0))
  (Rendering|Material|SetScalarParameterValueonMaterials :self {MESHC} :ParameterName "ZombieAmount" :ParameterValue (Variables|GW|GetZombieAmt))
  (if on
    (CallFunction|ZombiePose)
    (bind t (Utilities|Time|GetGameTimeinSeconds))
    (Class|CharacterMovementComponent|SetMaxWalkSpeed :self (Variables|Character|GetCharacterMovement) :MaxWalkSpeed 135.0)
    (Class|SkeletalMeshComponent|SetGlobalAnimRateScale :self {MESHC} :GlobalAnimRateScale 0.6)
    (Transformation|SetRelativeRotation :self {MESHC} :NewRotation (Math|Rotator|MakeRotator :Roll (- (* 3.0 (Math|Trig|Sin(Radians) (* t 2.3))) 11.0) :Pitch (* 9.0 (Math|Trig|Sin(Radians) (* t 1.6))) :Yaw -90.0) :bSweep false :bTeleport true)
    (return))
  (if (<= (Variables|GW|GetZombieAmt) 0.0)
    (Utilities|Time|ClearTimerbyFunctionName :Object self :FunctionName "ZombieAnim")
    (Class|SkeletalMeshComponent|SetGlobalAnimRateScale :self {MESHC} :GlobalAnimRateScale 1.0)
    ({_SKM}|SetAnimInstanceClass :self {MESHC} :NewClass "/Game/Characters/Mannequins/Anims/Unarmed/ABP_Unarmed.ABP_Unarmed_C")
    (Transformation|SetRelativeRotation :self {MESHC} :NewRotation (Math|Rotator|MakeRotator :Yaw -90.0) :bSweep false :bTeleport true)
    (Class|CharacterMovementComponent|SetMaxWalkSpeed :self (Variables|Character|GetCharacterMovement) :MaxWalkSpeed (Variables|GW|GetWalkSpeed))))
''', compile_after=False)
    write(ch, 'OnRep_ZombieGroan', f'''
(fn OnRep_ZombieGroan ()
  (Variables|GW|SetZombieSnd (Utilities|Array|Get(acopy) (Variables|GW|GetZombieSnds) (Math|Random|RandomIntegerinRange 0 2)))
  (Audio|SpawnSoundAttached :Sound (Variables|GW|GetZombieSnd) :AttachToComponent {MESHC} :AttachPointName "head" :LocationType "SnapToTarget" :VolumeMultiplier 0.75 :PitchMultiplier {RF(0.92, 1.08)} :bStopWhenAttachedToDestroyed true))
''', compile_after=False)
    compile_bp(ch)
    print('BP_GW_Character', [p for p in node_problems(ch) if 'Zombie' in p or 'Sight' in p])
    save(ch)

# ---------------------------------------------------------------- zombie AI (the helpers of s32_events.py)
if 'bps' in PARTS or 'bandit' in PARTS:
    _L = open(TOOLS + r'\gameplay\s32_events.py', encoding='utf-8').read().replace(chr(13), '').split('\n')
    _f = lambda pre: next(i for i in range(len(_L)) if _L[i].startswith(pre))
    _ns = {'unreal': unreal, 'ch': ch, 'chc': chc}
    exec('from gw_lib import *\nGMC = ' + repr(GMC) + '\nV3 = unreal.Vector.static_struct()\nDOOR = (3000.0, 300.0, 100.0)\nCHAR = ' + repr(CHAR) + '\nISVALID = ' + repr(ISVALID) + '\n' + '\n'.join(_L[_f('def controller('):_f('mv0 = lambda')]), _ns)
if 'bandit' in PARTS:
    exec('\n'.join(_L[_f('mv0 = lambda'):_f('save(bandit)') + 1]), _ns)
if 'bps' in PARTS:
    zc = _ns['controller']('BP_GW_ZombieController', [])
    write(zc, 'Think', _ns['THINK'], compile_after=False)
    write(zc, 'Roam', _ns['ROAM'], compile_after=False)
    write(zc, 'Brain', f'''
(fn Brain (Ch)
  (bind now {TNOW})
  ; the transformation scene: it stands and shakes first
  (if (< now (Variables|GW|GetWakeAt))
    (return))
  (Class|CharacterMovementComponent|SetMaxWalkSpeed :self (GW|Get|/Script/Engine.Character|CharacterMovement :self Ch) :MaxWalkSpeed 135.0)
  (if (>= now (Variables|GW|GetNextSay))
    (Variables|GW|SetNextSay (+ now {RF(7.0, 13.0)}))
    {CHS('ZombieGroan', 'Ch', f"(+ {CH('ZombieGroan', 'Ch')} 1)")})
  (if (< now (Variables|GW|GetNextScan))
    (return))
  (Variables|GW|SetNextScan (+ now 1.0))
  (Variables|GW|SetBestD 3500.0)
  (Variables|GW|SetTarget (Variables|GW|GetNoTarget))
  (bind here {LOC('Ch')})
  (for c (Actor|GetAllActorsOfClass :ActorClass {CHAR})
    (if (and (== {CH('Kind', 'c')} 0) (not {CH('IsDead', 'c')}))
      (bind d (Math|Vector|Distance(Vector) {LOC('c')} here))
      (if (< d (Variables|GW|GetBestD))
        (Variables|GW|SetBestD d)
        (Variables|GW|SetTarget c))))
  (bind t (Variables|GW|GetTarget))
  (if ({ISVALID} :Object t)
    (AI|Navigation|MovetoLocation :self self :Dest {LOC('t')} :AcceptanceRadius 30.0 :bStopOnOverlap false :bUsePathfinding true :bProjectDestinationToNavigation true :bCanStrafe false :bAllowPartialPath true)
    (Variables|GW|SetIsMoving true)
    (Variables|GW|SetMoveStart now)
    (else
      (CallFunction|Roam :Ch Ch :Rooms false))))
''', compile_after=False)
    write(zc, 'EventGraph', _ns['EG'].format(t=0.25), compile_after=False)
    compile_bp(zc)
    print('BP_GW_ZombieController', node_problems(zc))
    save(zc)

# ---------------------------------------------------------------- NPC controller: seats, dancing with a guest
if 'npc' in PARTS:
    npc = load_bp('BP_GW_NPCController')
    for v, t in (('SeatIdx', 'int'), ('SeatState', 'int'), ('SeatUntil', 'float'), ('SeatYaw', 'float')):
        ensure_var(npc, v, t, category='GW')
    for v in ('SeatSpot', 'SeatBack'):
        ensure_var(npc, v, struct=V3, category='GW')
    ensure_fn(npc, 'SitDown', inputs=[('Ch', chc)])
    ensure_fn(npc, 'FollowThink', inputs=[('Ch', chc)])
    compile_bp(npc, quiet=True)
    CMOV = '(GW|Get|/Script/Engine.Character|CharacterMovement :self Ch)'
    NW = {
        'SitTry': f'''
(fn SitTry (Ch)
  (if (!= {G_('SocialMode')} 0)
    (return false))
  (bind gm {GMC}
    (:then
      {SG('SeatIdx', f"(GW|Call|BP_GW_GameMode|SeatClaim :self gm :From {LOC('Ch')})")}
      (if (< {G_('SeatIdx')} 0)
        (return false))
      {SG('SeatSpot', f"(GW|Call|BP_GW_GameMode|SeatLoc :self gm :I {G_('SeatIdx')})")}
      {SG('SeatYaw', f"(GW|Call|BP_GW_GameMode|SeatYaw :self gm :I {G_('SeatIdx')})")}
      {SG('SeatState', '1')}
      {SG('SocialMode', '4')}
      ; some guests stay a long time, most a short while
      {SG('SeatUntil', f"(select (< (Math|Random|RandomFloat) 0.3) {RF(60, 150)} {RF(12, 40)})")}
      {SG('HasFinal', 'false')}
      {SG('Partner', G_('NoPartner'))}
      (CallFunction|GoTo :Dest (+ {G_('SeatSpot')} (* (Math|Vector|GetForwardVector (Math|Rotator|MakeRotator :Yaw {G_('SeatYaw')})) 75.0)))
      (return true))
    (:CastFailed (return false))))
''',
        'SitDown': f'''
(fn SitDown (Ch)
  (bind here {LOC('Ch')})
  (AI|Navigation|StopMovement :self self)
  {SG('IsMoving', 'false')}
  {SG('SeatBack', 'here')}
  {SG('SeatUntil', f"(+ {TNOW} {G_('SeatUntil')})")}
  {SG('SeatState', '2')}
  (Pawn|Components|CharacterMovement|DisableMovement :self {CMOV})
  (Transformation|SetActorLocationAndRotation :self Ch :NewLocation (Math|Vector|MakeVector (.x {G_('SeatSpot')}) (.y {G_('SeatSpot')}) (.z here)) :NewRotation (Math|Rotator|MakeRotator :Yaw {G_('SeatYaw')}) :bSweep false :bTeleport true)
  {CHS('DanceByPlayer', 'Ch', 'false')}
  {CHS('DanceId', 'Ch', '10')}
  {log(f'(cat "GW: EV sit " (Utilities|GetDisplayName :Object Ch) " seat=" {G_("SeatIdx")} " for " (- {G_("SeatUntil")} {TNOW}) " s")')})
''',
        'SitRelease': f'''
(fn SitRelease (Ch)
  (if (== {G_('SeatState')} 2)
    {CHS('DanceId', 'Ch', '0')}
    (Transformation|SetActorLocation :self Ch :NewLocation {G_('SeatBack')} :bSweep false :bTeleport true)
    (Pawn|Components|CharacterMovement|SetMovementMode :self {CMOV} :NewMovementMode "MOVE_Walking" :NewCustomMode 0)
    {log(f'(cat "GW: EV stand " (Utilities|GetDisplayName :Object Ch))')})
  {SG('SeatState', '0')}
  {SG('SocialMode', '0')}
  {SG('IsMoving', 'false')}
  {SG('NextMoveTime', f"(+ {TNOW} {RF(0.5, 3.0)})")}
  (bind gm {GMC}
    (:then (GW|Call|BP_GW_GameMode|SeatFree :self gm :I {G_('SeatIdx')}))
    (:CastFailed)))
''',
        'SeatThink': f'''
(fn SeatThink (Ch)
  (bind mode {G_('SocialMode')})
  (if (== mode 5)
    (CallFunction|FollowThink :Ch Ch)
    (return true))
  (if (!= mode 4)
    (return false))
  (bind now {TNOW})
  (if (== {G_('SeatState')} 2)
    (if (>= now {G_('SeatUntil')})
      (CallFunction|SitRelease :Ch Ch))
    (return true))
  (bind since (- now {G_('MoveStartTime')}))
  (if (or (and (> since 1.0) (< (Math|Vector|VectorLength (Transformation|GetVelocity :self Ch)) 3.0)) (> since 30.0))
    (if (< {DIST2(LOC('Ch'), G_('SeatSpot'))} 190.0)
      (CallFunction|SitDown :Ch Ch)
      (else
        (CallFunction|SitRelease :Ch Ch))))
  (return true))
''',
        'FollowThink': f'''
(fn FollowThink (Ch)
  (bind l {G_('Partner')})
  (if (not ({ISVALID} :Object l))
    (CallFunction|SocialCancel :Ch Ch)
    (return))
  (if (or (or {CH('IsDead', 'l')} (== {CH('DanceId', 'l')} 0)) (> {DIST2(LOC('l'), LOC('Ch'))} 800.0))
    {log(f'(cat "GW: EV follow ends " (Utilities|GetDisplayName :Object Ch))')}
    (CallFunction|SocialCancel :Ch Ch)
    (return))
  (bind d {DIST2(LOC('l'), LOC('Ch'))})
  (if (> d 230.0)
    (if (> (- {TNOW} {G_('MoveStartTime')}) 1.5)
      (if (!= {CH('DanceId', 'Ch')} 0)
        {CHS('DanceId', 'Ch', '0')})
      (CallFunction|GoTo :Dest (+ {LOC('l')} (* (Math|Vector|Normalize (- {LOC('Ch')} {LOC('l')})) 130.0))))
    (return))
  (if {G_('IsMoving')}
    (AI|Navigation|StopMovement :self self)
    {SG('IsMoving', 'false')})
  (CallFunction|FaceAt :P {LOC('l')})
  (if (!= {CH('DanceId', 'Ch')} {CH('DanceId', 'l')})
    {CHS('DanceByPlayer', 'Ch', 'false')}
    {CHS('DanceId', 'Ch', CH('DanceId', 'l'))}
    {log(f'(cat "GW: EV dances with guest " (Utilities|GetDisplayName :Object Ch) " dance=" {CH("DanceId", "l")})')}))
''',
    }
    gm0 = load_bp('BP_GW_GameMode')
    ensure_fn(gm0, 'SeatClaim', inputs=[('From', V3)], outputs=[('I', 'int')])
    ensure_fn(gm0, 'SeatLoc', inputs=[('I', 'int')], outputs=[('Loc', V3)])
    ensure_fn(gm0, 'SeatYaw', inputs=[('I', 'int')], outputs=[('Yaw', 'float')])
    ensure_fn(gm0, 'SeatFree', inputs=[('I', 'int')])
    compile_bp(gm0, quiet=True)
    for k_ in ('SitTry', 'SitDown', 'SitRelease', 'SeatThink'):      # s44_npc_life.py renders these now
        NW.pop(k_)
    for name, code in NW.items():
        write(npc, name, code, compile_after=False)
    compile_bp(npc)
    print('BP_GW_NPCController', [p for p in node_problems(npc) if any(k in p for k in ('Seat', 'Sit', 'Follow'))])
    save(npc)

# ---------------------------------------------------------------- game mode
if 'gm' in PARTS:
    gm = load_bp('BP_GW_GameMode')
    # seats: the frozen props of L_Manor (tag GW_Manual): one or more sitting spots, the prop's front is its local +Y
    w = unreal.EditorLevelLibrary.get_editor_world()
    if 'L_Manor' not in w.get_name():
        unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).load_level('/Game/GW/Maps/L_Manor')
        w = unreal.EditorLevelLibrary.get_editor_world()
    SPOTS = {'chair_dining': (0,), 'armchair_club': (0,), 'chair_wingback': (0,), 'chair_wicker': (0,), 'bench': (-38, 38), 'sofa_chesterfield': (-52, 52)}
    FWD = {'chair_dining': 6.0, 'armchair_club': 10.0, 'chair_wingback': 10.0, 'chair_wicker': 8.0, 'bench': 0.0, 'sofa_chesterfield': 8.0}
    sl, sy = [], []
    for a in unreal.GameplayStatics.get_all_actors_of_class(w, unreal.StaticMeshActor):
        m = a.static_mesh_component.static_mesh
        n = m.get_name() if m else ''
        if n in SPOTS and 'GW_Manual' in [str(t) for t in a.tags]:
            l = a.get_actor_location(); yaw = a.get_actor_rotation().yaw
            f = unreal.Vector(-math.sin(math.radians(yaw)), math.cos(math.radians(yaw)), 0)    # local +Y
            r = unreal.Vector(math.cos(math.radians(yaw)), math.sin(math.radians(yaw)), 0)     # local +X
            for o in SPOTS[n]:
                sl.append(unreal.Vector(l.x + f.x * FWD[n] + r.x * o, l.y + f.y * FWD[n] + r.y * o, l.z))
                sy.append(yaw + 90.0)
    print('seats', len(sl))

    # the breaker box: on a free wall of the service corridor
    def wall_spot():
        for (x, y, dx, dy) in ((2365, 1085, -1, 0), (2365, 1085, 0, 1), (4325, 1085, 1, 0), (4325, 1085, 0, -1), (1885, 1605, -1, 0), (1885, 1605, 0, -1), (2965, 1685, 1, 0)):
            ds = []
            for (o, oz) in ((0, 0), (18, 0), (-18, 0), (0, 22), (0, -22)):
                sx, sy_ = x - dy * o, y + dx * o
                h = unreal.SystemLibrary.line_trace_single(w, unreal.Vector(sx, sy_, 140 + oz), unreal.Vector(sx + dx * 900, sy_ + dy * 900, 140 + oz),
                                                           unreal.TraceTypeQuery.TRACE_TYPE_QUERY1, True, [], unreal.DrawDebugTrace.NONE, True)
                if not h:
                    break
                t = h.to_tuple()
                if t[7].x * -dx + t[7].y * -dy < 0.97:
                    break
                ds.append(t[3])
            if len(ds) == 5 and max(ds) - min(ds) < 2.0:
                d = ds[0] - 0.3
                return (x + dx * d, y + dy * d, 140.0), math.degrees(math.atan2(-dy, -dx))
        raise RuntimeError('no wall for the breaker')
    BLOC, BYAW = wall_spot()
    print('breaker at', BLOC, BYAW)
    for v, t in (('SitYaws', 'float'), ('SitBusy', 'float')):
        ensure_var(gm, v, t, array=True, category='GW')
    ensure_var(gm, 'SitLocs', struct=V3, array=True, category='GW')
    ensure_var(gm, 'VTestBring', obj_class=chc, category='Voice')
    for v, t in (('ZombieLife', 'float'), ('ZombieBite', 'float'), ('BreakerUsed', 'bool'), ('NextThreat', 'float'), ('NextZombie', 'float'), ('NextFollow', 'float'), ('ZombieN', 'int'),
                 ('EvTestOn', 'bool'), ('EvTestChecked', 'bool'), ('EvTestStep', 'int'), ('EvTestNext', 'float'), ('NextEvLog', 'float')):
        ensure_var(gm, v, t, category='GW')
    ensure_var(gm, 'BreakerRef', obj_class=load_bp('BP_GW_Breaker').generated_class(), category='GW')
    ensure_var(gm, 'AlarmLights', obj_class=unreal.Actor, array=True, category='GW')
    _pc0 = load_bp('BP_GW_PlayerController')               # EvTestTick calls it; its body is written below
    ensure_fn(_pc0, 'GWBreakerTest')
    compile_bp(_pc0, quiet=True)
    ensure_fn(gm, 'Zombify', inputs=[('Ch', chc)])
    ensure_fn(gm, 'ZombieTick')
    ensure_fn(gm, 'ThreatTick')
    ensure_fn(gm, 'DanceFollowTick')
    ensure_fn(gm, 'EvTestTick')
    ensure_fn(gm, 'BreakerClose', inputs=[('Who', unreal.Pawn)])
    ensure_fn(gm, 'FleeFromThreat', inputs=[('T', chc), ('R', 'float')])
    compile_bp(gm, quiet=True)
    def add_local(fn, n, t):
        g = get_graph(gm, fn)
        if n not in [str(x) for x in BT.list_variables(gm, g)]:
            if t == 'char':
                BT.add_object_variable(gm, n, chc, graph=g)
            else:
                BT.add_variable(gm, n, t, graph=g)
    ensure_var(gm, 'QAShotLoc', struct=unreal.Vector.static_struct(), category='GW')
    ensure_var(gm, 'QAFire', obj_class=unreal.Actor, category='GW')
    compile_bp(gm, quiet=True)
    add_local('SeatClaim', 'BestD', 'float'); add_local('SeatClaim', 'BestI', 'int')
    add_local('StartZombie', 'Z', 'char')
    add_local('DanceFollowTick', 'N', 'int'); add_local('DanceFollowTick', 'F', 'char');
    d = cdo(gm)
    d.set_editor_property('ZombieLife', 15.0)       # each zombie dies this long after it turned
    d.set_editor_property('ZombieBite', 8.0)        # a zombie contaminates once per this long, and never in its first moments
    d.set_editor_property('SitLocs', sl)
    d.set_editor_property('SitYaws', sy)
    d.set_editor_property('SitBusy', [0.0] * len(sl))
    NPCCAST = lambda o: f'(Utilities|Casting|CastToBP_GW_NPCController (Pawn|GetController :self {o}))'
    PCX = '(Utilities|Casting|CastToBP_GW_PlayerController (Game|GetPlayerController :PlayerIndex 0))'
    on_pc = lambda body: f'(bind pc {PCX} (:then {body}) (:CastFailed))'
    ROOMS = {'bal': (2925, 3565, 130), 'hall': (2845, 1485, 130), 'biblio': (1085, 3405, 130)}
    tp = lambda r: on_pc(f'(GW|Call|BP_GW_PlayerController|GWDevTeleport :self pc :X {float(ROOMS[r][0])} :Y {float(ROOMS[r][1])} :Z {float(ROOMS[r][2])})')
    ev = lambda i: log(f'"GW: EV test event {i}"') + ' ' + on_pc(f'(GW|Call|BP_GW_PlayerController|GWDevEvent :self pc :Id {i})')
    go = on_pc('(GW|Call|BP_GW_PlayerController|GWDevEventGo :self pc)')
    alive = on_pc('(GW|Call|BP_GW_PlayerController|DevEnsureAlive :self pc)')
    talk = log('"GW: EV test talk"') + ' ' + on_pc('(GW|Call|BP_GW_PlayerController|TryTalk :self pc)')
    # a guest brought 1.5 m in front of the host (few NPCs are near him at a given second)
    aim = f'''(bind me9 (Utilities|Casting|CastToBP_GW_Character (Game|GetPlayerPawn :PlayerIndex 0))
      (:then
        (Variables|GW|SetStamp (+ (Variables|GW|GetStamp) 1))
        (Variables|Voice|SetVTestBring (CallFunction|NearestNPC :Loc {LOC('me9')} :MaxD 100000.0))
        (if ({ISVALID} :Object (Variables|Voice|GetVTestBring))
          (Transformation|SetActorLocation :self (Variables|Voice|GetVTestBring) :NewLocation (+ {LOC('me9')} (* (Math|Vector|GetForwardVector (Pawn|GetControlRotation :self (Pawn|GetController :self me9))) 150.0)) :bSweep false :bTeleport true)))
      (:CastFailed))'''
    shoot = f'''(bind me (Utilities|Casting|CastToBP_GW_Character (Game|GetPlayerPawn :PlayerIndex 0))
      (:then
        (for zz (Actor|GetAllActorsOfClass :ActorClass {CHAR})
          (if (and (== {CH('Kind', 'zz')} 4) (not {CH('IsDead', 'zz')}))
            (if (not (Pawn|IsPlayerControlled :self zz))
              {log('"GW: EV test shoots a zombie"')}
              (CallFunction|OnCharacterShot :Shooter me :Victim zz :Dir (Math|Vector|MakeVector 1.0 0.0 0.0))
              (break)))))
      (:CastFailed))'''
    # a guest not in a dance group, brought beside the host
    bringfree = f'''(bind me8 (Utilities|Casting|CastToBP_GW_Character (Game|GetPlayerPawn :PlayerIndex 0))
      (:then
        (for c8 (Actor|GetAllActorsOfClass :ActorClass {NPCC})
          (if (and (== {NC('SocialMode', 'c8')} 0) (< {NC('PanicUntil', 'c8')} {TNOW}))
            {log('"GW: EV test brings a free guest"')}
            (Transformation|SetActorLocation :self (Pawn|GetControlledPawn :self c8) :NewLocation (+ {LOC('me8')} (Math|Vector|MakeVector 150.0 0.0 0.0)) :bSweep false :bTeleport true)
            (break))))
      (:CastFailed))'''
    # the camera 2.2 m from somebody sitting, looking at him, and a screenshot (rendered run)
    shotsit = f'''(bind me7 (Utilities|Casting|CastToBP_GW_Character (Game|GetPlayerPawn :PlayerIndex 0))
      (:then
        (for c7 (Actor|GetAllActorsOfClass :ActorClass {NPCC})
          (if (== {NC('SeatState', 'c7')} 2)
            (bind p7 (Pawn|GetControlledPawn :self c7))
            (if (not ({ISVALID} :Object p7))
              (return))
            (Transformation|SetActorLocation :self me7 :NewLocation (+ {LOC('p7')} (+ (* (Transformation|GetActorForwardVector :self p7) 260.0) (Math|Vector|MakeVector 0.0 0.0 10.0))) :bSweep false :bTeleport true)
            (Pawn|SetControlRotation :self (Game|GetPlayerController :PlayerIndex 0) :NewRotation (Math|Rotator|MakeRotator :Pitch -8.0 :Yaw (+ 180.0 (.yaw (Transformation|GetActorRotation :self p7)))))
            {log('"GW: EV test shot of a seated guest"')}
            (Utilities|Time|SetTimerbyFunctionName :Object (Game|GetPlayerController :PlayerIndex 0) :FunctionName "DevEventShotNow" :Time 0.6 :bLooping false)
            (break))))
      (:CastFailed))'''
    shotz = shotsit.replace(f"(== {NC('SeatState', 'c7')} 2)", f"({ISVALID} :Object (Pawn|GetControlledPawn :self c7))").replace(NPCC, '"/Game/GW/Blueprints/BP_GW_ZombieController.BP_GW_ZombieController_C"').replace('seated guest', 'zombie').replace(f"{NC('SeatState', 'c7')}", '0')
    # rendered QA: the host stands Dist cm from the nearest actor of a class, looks at it, screenshot 0.6 s later
    shotnear = lambda cls, dist, zlook, tag: f"""(bind me6 (Utilities|Casting|CastToBP_GW_Character (Game|GetPlayerPawn :PlayerIndex 0))
      (:then
        (for f6 (Actor|GetAllActorsOfClass :ActorClass "{cls}")
          (if (Math|Random|RandomBoolwithWeight :Weight 0.34)
            (for k6 (range 10)
              (bind (np6 ok6) (AI|Navigation|GetRandomReachablePointinRadius :Origin (Math|Vector|MakeVector (.x {LOC('f6')}) (.y {LOC('f6')}) 5.0) :Radius {dist}.0))
              (Variables|GW|SetQAShotLoc np6)
              (if (> (Math|Vector|Distance2D(Vector) np6 {LOC('f6')}) {dist * 0.6})
                (break)))
            (Transformation|SetActorLocation :self me6 :NewLocation (+ (Variables|GW|GetQAShotLoc) (Math|Vector|MakeVector 0.0 0.0 95.0)) :bSweep false :bTeleport true)
            (Pawn|SetControlRotation :self (Game|GetPlayerController :PlayerIndex 0) :NewRotation (Math|Rotator|FindLookatRotation :Start (+ (Variables|GW|GetQAShotLoc) (Math|Vector|MakeVector 0.0 0.0 155.0)) :Target (+ {LOC('f6')} (Math|Vector|MakeVector 0.0 0.0 {zlook}.0))))
            {log(f'(cat "GW: EV test shot {tag} at " {LOC("f6")})')}
            (Utilities|Time|SetTimerbyFunctionName :Object (Game|GetPlayerController :PlayerIndex 0) :FunctionName "DevEventShotNow" :Time 0.6 :bLooping false)
            (break))))
      (:CastFailed))"""
    FIREC = '/Game/GW/Blueprints/BP_GW_Fire.BP_GW_Fire_C'
    # one blaze at a known spot of the hall, the host Dist cm from it (rendered QA of the flames and the red lights)
    _hallf = '(Math|Vector|MakeVector 2845.0 1485.0 5.0)'
    firehall = lambda dist: f"""(bind me5 (Utilities|Casting|CastToBP_GW_Character (Game|GetPlayerPawn :PlayerIndex 0))
      (:then
        (if (not ({ISVALID} :Object (Variables|GW|GetQAFire)))
          (Variables|GW|SetQAFire (Game|SpawnActorfromClass :Class "{FIREC}" :SpawnTransform (Math|Transform|MakeTransform :Location {_hallf}) :CollisionHandlingOverride "AlwaysSpawn"))
          (Utilities|Array|Add :TargetArray {G_('Fires')} :NewItem (Variables|GW|GetQAFire)))
        (Transformation|SetActorLocation :self me5 :NewLocation (Math|Vector|MakeVector (- 2845.0 {dist}.0) 1385.0 100.0) :bSweep false :bTeleport true)
        (Pawn|SetControlRotation :self (Game|GetPlayerController :PlayerIndex 0) :NewRotation (Math|Rotator|MakeRotator :Pitch 2.0 :Yaw 0.0))
        {log(f'"GW: EV test shot fire in the hall at {dist} cm"')}
        (Utilities|Time|SetTimerbyFunctionName :Object (Game|GetPlayerController :PlayerIndex 0) :FunctionName "DevEventShotNow" :Time 0.5 :bLooping false))
      (:CastFailed))"""
    ALARMC = '/Game/GW/Blueprints/BP_GW_AlarmLight.BP_GW_AlarmLight_C'
    ZOMBC = '/Game/GW/Blueprints/BP_GW_ZombieController.BP_GW_ZombieController_C'
    # a zombie, picked at random, seen from the front
    shotzr = shotz.replace(f"({ISVALID} :Object (Pawn|GetControlledPawn :self c7))", "(and ({ISVALID} :Object (Pawn|GetControlledPawn :self c7)) (Math|Random|RandomBoolwithWeight :Weight 0.4))".replace("{ISVALID}", ISVALID))
    turrz = shoot.replace('EV test shoots a zombie', 'EV test turret on a zombie').replace('(CallFunction|OnCharacterShot :Shooter me :Victim zz :Dir (Math|Vector|MakeVector 1.0 0.0 0.0))', '(CallFunction|TurretHit :Gunner me :Victim zz :Dir (Math|Vector|MakeVector 1.0 0.0 0.0))')
    npcn = lambda n: log(f'"GW: EV test NPC count {n}"') + ' ' + on_pc(f'(GW|Call|BP_GW_PlayerController|GWDevNPCCount :self pc :N {n})')
    npclog = log(f'(cat "GW: EV test counted characters=" (Utilities|Array|Length (Actor|GetAllActorsOfClass :ActorClass {CHAR})) " npc controllers=" (Utilities|Array|Length (Actor|GetAllActorsOfClass :ActorClass {NPCC})))')
    shotnow = '(Utilities|Time|SetTimerbyFunctionName :Object (Game|GetPlayerController :PlayerIndex 0) :FunctionName "DevEventShotNow" :Time 0.1 :bLooping false)'
    STEPS = [(2, '(Variables|GW|SetAutoEvents false)'), (3, on_pc('(GW|Call|BP_GW_PlayerController|GWDevQuickTest :self pc :R 1)')), (5, tp('bal')),
             # kamikaze, the camera follows him so a player hears him
             (8, ev(4))] + [(s, go) for s in range(9, 19)] + [
             (24, alive), (25, tp('bal')),
             # E on guests (the player's own voice), greeting pairs happen on their own
             (28, aim), (29, talk), (31, aim), (32, talk), (34, aim), (35, talk),
             (36, on_pc('(GW|Call|BP_GW_PlayerController|GWDevEventStop :self pc)')), (37, bringfree), (38, on_pc('(GW|Call|BP_GW_PlayerController|GWDance :self pc)')), (44, on_pc('(GW|Call|BP_GW_PlayerController|GWDance :self pc)')),
             # the bandits walk out
             (46, tp('hall')), (47, ev(1)), (51, on_pc('(GW|Call|BP_GW_PlayerController|GWDevEventStop :self pc)')),
             # breakers
             (58, alive), (59, log('"GW: EV test breaker"') + ' ' + on_pc('(GW|Call|BP_GW_PlayerController|GWBreakerTest :self pc)')), (62, on_pc('(GW|Call|BP_GW_PlayerController|GWDevEventStop :self pc)')),
             (63, on_pc('(GW|Call|BP_GW_PlayerController|GWBreakerTest :self pc)')),
             # the fire
             (65, ev(2)), (66, go), (67, firehall(420)), (68, firehall(420)), (69, firehall(300)), (70, firehall(300)), (71, shotnear(FIREC, 420, 80, 'fire elsewhere')), (72, on_pc('(GW|Call|BP_GW_PlayerController|GWDevEventStop :self pc)')),
             # zombies, one shot
             (72, alive), (73, tp('bal')), (74, ev(6)), (75, go), (79, shotz), (81, shotzr), (82, shotzr), (83, shotzr), (84, shoot), (85, turrz), (86, go), (92, alive), (96, npcn(40)), (97, npclog), (98, on_pc('(GW|Call|BP_GW_PlayerController|GWDevEventStop :self pc)')),
             # a quiet moment with two guests beside the host: a voiced greeting pair
             (100, ev(5)), (101, go), (102, shotnow), (103, shotsit), (104, npcn(60)), (105, go), (106, shotnow), (107, npclog), (108, shotsit), (109, on_pc('(GW|Call|BP_GW_PlayerController|GWDevEventStop :self pc)')),
             (111, log('"GW: EV test end"')), (112, '(Development|ExecuteConsoleCommand :Command "quit")')]
    TESTBODY = '\n'.join(f'  (if (== st {s})\n    {c})' for s, c in STEPS)
    GW = {
        'SeatLoc': f'(fn SeatLoc (I) (return (Utilities|Array|Get(acopy) {G_("SitLocs")} I)))',
        'SeatYaw': f'(fn SeatYaw (I) (return (Utilities|Array|Get(acopy) {G_("SitYaws")} I)))',
        'SeatFree': f'''
(fn SeatFree (I)
  (if (and (>= I 0) (< I (Utilities|Array|Length {G_('SitBusy')})))
    (Utilities|Array|SetArrayElem :TargetArray {G_('SitBusy')} :Index I :Item 0.0 :bSizeToFit false)))
''',
        # the nearest-ish free seat within 15 m on this floor (a bit of randomness); reserved 3 min at most
        'SeatClaim': f'''
(fn SeatClaim (From)
  {SL('BestD', '1500.0')}
  {SL('BestI', '-1')}
  (bind now {NOW})
  (for i (range (Utilities|Array|Length {G_('SitLocs')}))
    (if (<= (Utilities|Array|Get(acopy) {G_('SitBusy')} i) now)
      (bind p (Utilities|Array|Get(acopy) {G_('SitLocs')} i))
      (if (< (Math|Float|Absolute(Float) (- (.z p) (.z From))) 170.0)
        (bind d (+ {DIST2('p', 'From')} {RF(0, 500)}))
        (if (< d {L('BestD')})
          {SL('BestD', 'd')}
          {SL('BestI', 'i')}))))
  (if (>= {L('BestI')} 0)
    (Utilities|Array|SetArrayElem :TargetArray {G_('SitBusy')} :Index {L('BestI')} :Item (+ now 180.0) :bSizeToFit false))
  (return {L('BestI')}))
''',
        # one guest turns, in sight of a player if possible
        'StartZombie': f'''
(fn StartZombie ()
  (Variables|GW|SetStamp (+ (Variables|GW|GetStamp) 1))
  {SG('ZombieN', '0')}
  (CallFunction|PlayerPawns)
  {SL('Z', '(Variables|GW|GetNoChar)')}
  (for p (Variables|Voice|GetVPl)
    (if (not ({ISVALID} :Object {L('Z')}))
      {SL('Z', f"(CallFunction|NearestNPC :Loc {LOC('p')} :MaxD 1800.0)")}))
  (if (not ({ISVALID} :Object {L('Z')}))
    {SL('Z', f"(CallFunction|NearestNPC :Loc (Math|Vector|MakeVector 3000.0 2200.0 100.0) :MaxD 100000.0)")})
  (if ({ISVALID} :Object {L('Z')})
    (CallFunction|Zombify :Ch {L('Z')})
    (CallFunction|SayNearPlayers :Cat {CAT_SHOUT} :PerPlayer 1 :Delay 2.0 :Spread 1.0)))
''',
        # the scene: a scream, 2 s standing and shaking while the skin turns, a groan; then it walks. Players: 1.5 s frozen.
        'Zombify': f'''
(fn Zombify (Ch)
  (if (or (or {CH('IsDead', 'Ch')} (!= {CH('Kind', 'Ch')} 0)) (>= {G_('ZombieN')} {ZOMBIE_MAX}))
    (return))
  {SG('ZombieN', f"(+ {G_('ZombieN')} 1)")}
  (CallFunction|Say :Ch Ch :Cat {CAT_SCREAM})
  {log(f'(cat "GW: EV zombify " (Utilities|GetDisplayName :Object Ch) " player=" (Pawn|IsPlayerControlled :self Ch) " n=" {G_("ZombieN")})')}
  {CHS('Kind', 'Ch', '4')}
  {CHS('ZombieSince', 'Ch', NOW)}
  {CHS('ZombieBiteAt', 'Ch', f"(+ {NOW} {G_('ZombieBite')})")}
  {CHS('ZombieGroan', 'Ch', f"(+ {CH('ZombieGroan', 'Ch')} 1)")}
  (GW|Call|BP_GW_Character|ZombieVisual :self Ch)
  (if (Pawn|IsPlayerControlled :self Ch)
    (return))
  (bind old (Pawn|GetController :self Ch))
  (bind oc (Utilities|Casting|CastToBP_GW_NPCController old)
    (:then
      (if (== {NC('SocialMode', 'oc')} 4)
        (GW|Call|BP_GW_NPCController|SitRelease :self oc :Ch Ch))
      (if (!= {NC('SocialMode', 'oc')} 0)
        (GW|Call|BP_GW_NPCController|SocialCancel :self oc :Ch Ch))
      (AI|Navigation|StopMovement :self oc)
      ; the guest's controller goes for good. DestroyActor on it does nothing here (measured in a -game run: the actor stays valid,
      ; one orphan per zombie for the round, Tools/qa/py_harness.py plan zomb4); a life span does end it
      (Pawn|UnPossess :self oc)
      (Actor|SetLifeSpan :self oc :InLifespan 0.1)
      (bind zc (Game|SpawnActorfromClass :Class "/Game/GW/Blueprints/BP_GW_ZombieController.BP_GW_ZombieController_C" :SpawnTransform (Math|Transform|MakeTransform :Location {LOC('Ch')}) :CollisionHandlingOverride "AlwaysSpawn"))
      (Pawn|Possess :self zc :InPawn Ch)
      (GW|Set|BP_GW_ZombieController|WakeAt :self zc :WakeAt (+ {TNOW} 2.0)))
    (:CastFailed)))
''',
        'ZombieDown': f'''
(fn ZombieDown (Victim Impulse)
  {log(f'(cat "GW: EV zombie down " (Utilities|GetDisplayName :Object Victim))')}
  (CallFunction|Say :Ch Victim :Cat {CAT_SCREAM})
  {CHS('TalkUntil', 'Victim', f"(+ {NOW} 600.0)")}
  (if (Pawn|IsPlayerControlled :self Victim)
    (CallFunction|KillPlayer :Victim Victim :Impulse Impulse)
    (CallFunction|UpdateCounts)
    (CallFunction|CheckWin)
    (return))
  (GW|Call|BP_GW_Character|Die :self Victim :Impulse Impulse)
  (Utilities|Array|Add :TargetArray (Variables|GW|GetPendingNPCRespawns) :NewItem (+ {NOW} (Variables|GW|GetNPCRespawnDelay))))
''',
        # NPC zombies fall, players are themselves again
        'EndZombie': f'''
(fn EndZombie ()
  (for c (Actor|GetAllActorsOfClass :ActorClass {CHAR})
    (if (and (== {CH('Kind', 'c')} 4) (not {CH('IsDead', 'c')}))
      (if (Pawn|IsPlayerControlled :self c)
        {CHS('Kind', 'c', '0')}
        (GW|Call|BP_GW_Character|ZombieVisual :self c)
        {log(f'(cat "GW: EV zombie player cured " (Utilities|GetDisplayName :Object c))')}
        (else
          (GW|Call|BP_GW_Character|Die :self c :Impulse (Math|Vector|MakeVector 0.0 0.0 100.0))
          (Utilities|Array|Add :TargetArray (Variables|GW|GetPendingNPCRespawns) :NewItem (+ {NOW} (Variables|GW|GetNPCRespawnDelay)))))))
  (CallFunction|SayNearPlayers :Cat 3 :PerPlayer 1 :Delay 1.0 :Spread 2.0))
''',
        'ZombieTick': f'''
(fn ZombieTick ()
  (bind all (Actor|GetAllActorsOfClass :ActorClass {CHAR}))
  {SG('NextZombie', f'(+ {NOW} 0.25)')}
  {SG('ZombieN', '0')}
  (for z all
    (if (and (== {CH('Kind', 'z')} 4) (not {CH('IsDead', 'z')}))
      (if (>= {NOW} (+ {CH('ZombieSince', 'z')} {G_('ZombieLife')}))
        ; its time is up: the body falls, the same way as when it is shot
        {log(f'(cat "GW: EV zombie expired " (Utilities|GetDisplayName :Object z) " after " (- {NOW} {CH("ZombieSince", "z")}))')}
        (CallFunction|ZombieDown :Victim z :Impulse (Math|Vector|MakeVector 0.0 0.0 -150.0))
        (else
          {SG('ZombieN', f"(+ {G_('ZombieN')} 1)")}
          ; one contamination per GM.ZombieBite seconds, a real touch
          (if (>= {NOW} {CH('ZombieBiteAt', 'z')})
            (bind zl {LOC('z')})
            (for c all
              (if (and (== {CH('Kind', 'c')} 0) (not {CH('IsDead', 'c')}))
                (bind cl {LOC('c')})
                (if (< {DIST2('zl', 'cl')} 90.0)
                  (if (< (Math|Float|Absolute(Float) (- (.z zl) (.z cl))) 90.0)
                    {CHS('ZombieBiteAt', 'z', f"(+ {NOW} {G_('ZombieBite')})")}
                    (CallFunction|Zombify :Ch c)
                    (break))))))))))
  ; nobody left: it is over
  (if (== {G_('ZombieN')} 0)
    (if (== (GW|Get|BP_GW_GameState|EventId :self (CallFunction|GetGS)) 6)
      {log('"GW: EV all zombies down"')}
      (CallFunction|EndEvent))))
''',
        # every NPC in sight of T within R runs from it
        'FleeFromThreat': f'''
(fn FleeFromThreat (T R)
  (bind tl {LOC('T')})
  (bind now {TNOW})
  (for c (Actor|GetAllActorsOfClass :ActorClass {NPCC})
    (bind p (Pawn|GetControlledPawn :self c))
    (if ({ISVALID} :Object p)
      (if (< (Math|Vector|Distance(Vector) {LOC('p')} tl) R)
        (if (< {NC('PanicUntil', 'c')} (+ now 1.5))
          (if (CallFunction|SeeFrom :A (+ {LOC('p')} (Math|Vector|MakeVector 0.0 0.0 60.0)) :B (+ tl (Math|Vector|MakeVector 0.0 0.0 60.0)))
            {NCS('PanicUntil', 'c', '(+ now 4.0)')}
            {NCS('PanicFrom', 'c', 'tl')}
            {NCS('IsMoving', 'c', 'false')}
            {NCS('NextMoveTime', 'c', 'now')}))))))
''',
        'ThreatTick': f'''
(fn ThreatTick ()
  {SG('NextThreat', f'(+ {NOW} 0.5)')}
  (for t (Actor|GetAllActorsOfClass :ActorClass {CHAR})
    (bind k {CH('Kind', 't')})
    (if (and (or (== k 2) (== k 4)) (not {CH('IsDead', 't')}))
      (CallFunction|FleeFromThreat :T t :R (select (== k 2) 1400.0 700.0)))))
''',
        'DanceFollowTick': f'''
(fn DanceFollowTick ()
  {SG('NextFollow', f'(+ {NOW} 2.5)')}
  (for p (Actor|GetAllActorsOfClass :ActorClass {CHAR})
    (if (Pawn|IsPlayerControlled :self p)
      (bind pl {LOC('p')})
      (if (and (and (and (> {CH('DanceId', 'p')} 0) (<= {CH('DanceId', 'p')} 5)) (< (.z pl) 300.0)) (and (and (> (.x pl) {BALL[0]}) (< (.x pl) {BALL[1]})) (and (> (.y pl) {BALL[2]}) (< (.y pl) {BALL[3]}))))
        {SL('N', '0')}
        (for c (Actor|GetAllActorsOfClass :ActorClass {NPCC})
          (if (and (== {NC('SocialMode', 'c')} 5) (== {NC('Partner', 'c')} p))
            {SL('N', f"(+ {L('N')} 1)")}))
        (if (< {L('N')} 3)
          (Variables|GW|SetStamp (+ (Variables|GW|GetStamp) 1))
          ; the nearest guests until a free one: those already dancing in a group stay with their group
          (for tr (range 6)
            (if (< {L('N')} 3)
              {SL('F', '(CallFunction|NearestNPC :Loc pl :MaxD 450.0)')}
              (if ({ISVALID} :Object {L('F')})
                (bind fc {NPCCAST(L('F'))}
                  (:then
                    (if (and (== {NC('SocialMode', 'fc')} 0) (< {NC('PanicUntil', 'fc')} {TNOW}))
                      {NCS('Partner', 'fc', 'p')}
                      {NCS('SocialMode', 'fc', '5')}
                      {NCS('MoveStartTime', 'fc', '-100.0')}
                      {NCS('HasFinal', 'fc', 'false')}
                      {SL('N', '3')}))
                  (:CastFailed))))))))))
''',
        'FireAlarmOn': f'''
(fn FireAlarmOn ()
  (bind pts (Actor|GetAllActorswithTag :Tag "GW_NPCSpawn"))
  (for i (range (Utilities|Array|Length pts))
    (if (== (% i 3) 0)
      (bind a (Game|SpawnActorfromClass :Class "/Game/GW/Blueprints/BP_GW_AlarmLight.BP_GW_AlarmLight_C" :SpawnTransform (Math|Transform|MakeTransform :Location (+ {LOC('(Utilities|Array|Get(acopy) pts i)')} (Math|Vector|MakeVector 0.0 0.0 180.0))) :CollisionHandlingOverride "AlwaysSpawn"))
      (Utilities|Array|Add :TargetArray {G_('AlarmLights')} :NewItem a))))
''',
        'FireAlarmOff': f'''
(fn FireAlarmOff ()
  (for a {G_('AlarmLights')}
    (if ({ISVALID} :Object a)
      (Actor|DestroyActor :self a)))
  (Utilities|Array|Clear {G_('AlarmLights')}))
''',
        'BreakerClose': f'''
(fn BreakerClose (Who)
  (if {G_('BreakerUsed')}
    {log('"GW: EV breaker: already used this game"')}
    (return))
  {SG('BreakerUsed', 'true')}
  (bind b {G_('BreakerRef')})
  (if ({ISVALID} :Object b)
    (GW|Set|BP_GW_Breaker|Thrown :self b :Thrown true))
  {log('"GW: EV breaker closed: blackout"')}
  (CallFunction|StartEvent :Id 3))
''',
        'Events2Tick': f'''
(fn Events2Tick ()
  (bind now {NOW})
  (if (not ({ISVALID} :Object {G_('BreakerRef')}))
    {SG('BreakerRef', f'(Game|SpawnActorfromClass :Class "/Game/GW/Blueprints/BP_GW_Breaker.BP_GW_Breaker_C" :SpawnTransform (Math|Transform|MakeTransform :Location (Math|Vector|MakeVector {BLOC[0]} {BLOC[1]} {BLOC[2]}) :Rotation (Math|Rotator|MakeRotator :Yaw {BYAW})) :CollisionHandlingOverride "AlwaysSpawn")')}
    (GW|Set|BP_GW_Breaker|Thrown :self {G_('BreakerRef')} :Thrown {G_('BreakerUsed')}))
  (CallFunction|EvTestTick)
  (bind s (CallFunction|GetGS))
  (if (!= (GW|Get|BP_GW_GameState|Phase :self s) 2)
    (return))
  (if (>= now {G_('NextThreat')})
    (CallFunction|ThreatTick))
  (if (and (>= now {G_('NextZombie')}) (== (GW|Get|BP_GW_GameState|EventId :self s) 6))
    (CallFunction|ZombieTick))
  (if (>= now {G_('NextFollow')})
    (CallFunction|DanceFollowTick)))
''',
        'EvTestTick': f'''
(fn EvTestTick ()
  (if (not {G_('EvTestChecked')})
    {SG('EvTestChecked', 'true')}
    {SG('EvTestOn', '(Utilities|HasLaunchOption :OptionToCheck "GWEvTest")')})
  (if (not {G_('EvTestOn')})
    (return))
  (bind now {NOW})
  (if (>= now {G_('NextEvLog')})
    {SG('NextEvLog', '(+ now 5.0)')}
    {log(f'(cat "GW: EV state t=" now " ev=" (GW|Get|BP_GW_GameState|EventId :self (CallFunction|GetGS)) " tense=" (- (GW|Get|BP_GW_GameState|TenseUntil :self (CallFunction|GetGS)) (GameState|GetServerWorldTimeSeconds :self (CallFunction|GetGS))) " zombies=" {G_("ZombieN")} " lights=" (Utilities|Array|Length {G_("AlarmLights")}) " fires=" (Utilities|Array|Length {G_("Fires")}))')})
  (if (< now {G_('EvTestNext')})
    (return))
  {SG('EvTestNext', '(+ now 2.0)')}
  {SG('EvTestStep', f"(+ {G_('EvTestStep')} 1)")}
  (bind st {G_('EvTestStep')})
{TESTBODY})
''',
    }
    for name, code in GW.items():
        write(gm, name, code, compile_after=False)
    _t = open(TOOLS + r'\gameplay\s31_reactions.py', encoding='utf-8').read()
    _m = re.search(r"'ShotWatchTick': f'''(.*?)'''", _t, re.S)
    write(gm, 'ShotWatchTick', _m.group(1).replace('{CHAR}', CHAR), compile_after=False)
    compile_bp(gm)
    KEYS = ('Seat', 'Zomb', 'Threat', 'Follow', 'Alarm', 'Breaker', 'Events2', 'EvTest', 'ShotWatch', 'Flee')
    print('BP_GW_GameMode', [p for p in node_problems(gm) if any(k in p for k in KEYS)])
    save(gm)

# ---------------------------------------------------------------- player controller: E on the breakers, dev
if 'pc' in PARTS:
    pc = load_bp('BP_GW_PlayerController')
    kp = load_bp('BP_GW_KeyPrompt')
    ensure_var(pc, 'BreakerPrompt', obj_class=kp.generated_class(), category='GW')
    ensure_var(pc, 'NoBreakerAim', obj_class=unreal.Actor, category='GW')
    ensure_fn(pc, 'BreakerNear', outputs=[('A', unreal.Actor)])
    ensure_fn(pc, 'TryBreaker', outputs=[('Handled', 'bool')])
    ensure_fn(pc, 'BreakerClientTick')
    ensure_fn(pc, 'GWBreaker', exec_fn=True)
    ensure_fn(pc, 'GWBreakerTest')
    ensure_fn(pc, 'GWDevNPCCount', inputs=[('N', 'int')], exec_fn=True)
    ensure_fn(pc, 'GWDevBreakerReset', exec_fn=True)
    compile_bp(pc, quiet=True)
    BR = '"/Game/GW/Blueprints/BP_GW_Breaker.BP_GW_Breaker_C"'
    CLOSE = f'''(bind gm {GMC}
        (:then (GW|Call|BP_GW_GameMode|BreakerClose :self gm :Who ch))
        (:CastFailed))'''
    GUARD = lambda ret: f'''(if (or (GW|Get|BP_GW_Character|IsDead :self ch) (!= (GW|Get|BP_GW_Character|Kind :self ch) 0))
        {ret})'''
    PW = {
        # the box within 2.2 m, not thrown yet
        'BreakerNear': f'''
(fn BreakerNear ()
  (bind p (Pawn|GetControlledPawn :self self))
  (if (not ({ISVALID} :Object p))
    (return (Variables|GW|GetNoBreakerAim)))
  (for b (Actor|GetAllActorsOfClass :ActorClass {BR})
    (if (and (not (GW|Get|BP_GW_Breaker|Thrown :self b)) (< (Math|Vector|Distance(Vector) {LOC('b')} {LOC('p')}) 220.0))
      (return b)))
  (return (Variables|GW|GetNoBreakerAim)))
''',
        'TryBreaker': f'''
(fn TryBreaker ()
  (bind ch {MYCH}
    (:then
      {GUARD('(return false)')}
      (if (not ({ISVALID} :Object (CallFunction|BreakerNear)))
        (return false))
      (if (Networking|HasAuthority)
        (CallFunction|GWBreaker)
        (else
          (Development|ExecuteConsoleCommand :Command "ServerExec GWBreaker" :SpecificPlayer self)))
      (return true))
    (:CastFailed (return false))))
''',
        'GWBreaker': f'''
(fn GWBreaker ()
  (bind ch {MYCH}
    (:then
      {GUARD('(return)')}
      (if (not ({ISVALID} :Object (CallFunction|BreakerNear)))
        (return))
      {CLOSE})
    (:CastFailed)))
''',
        # test only: the same close, from anywhere
        'GWBreakerTest': f'''
(fn GWBreakerTest ()
  (bind ch {MYCH}
    (:then
      {CLOSE})
    (:CastFailed)))
''',
        'BreakerClientTick': f'''
(fn BreakerClientTick ()
  (if (not (Pawn|IsLocalPlayerController))
    (return))
  (bind b (CallFunction|BreakerNear))
  (bind kp (Variables|GW|GetBreakerPrompt))
  (if ({ISVALID} :Object b)
    (if (not ({ISVALID} :Object kp))
      (Variables|GW|SetBreakerPrompt (Game|SpawnActorfromClass :Class "/Game/GW/Blueprints/BP_GW_KeyPrompt.BP_GW_KeyPrompt_C" :SpawnTransform (Math|Transform|MakeTransform :Location {LOC('b')}) :CollisionHandlingOverride "AlwaysSpawn")))
    (GW|Call|BP_GW_KeyPrompt|SetPrompt :self (Variables|GW|GetBreakerPrompt) :Key "E" :Label "Fermer les disjoncteurs")
    (Transformation|SetActorLocation :self (Variables|GW|GetBreakerPrompt) :NewLocation (+ {LOC('b')} (Math|Vector|MakeVector 0.0 0.0 55.0)) :bSweep false :bTeleport true)
    (GW|Call|BP_GW_KeyPrompt|ShowPrompt :self (Variables|GW|GetBreakerPrompt) :On true)
    (return))
  (if ({ISVALID} :Object kp)
    (GW|Call|BP_GW_KeyPrompt|ShowPrompt :self kp :On false)))
''',
        'GWDevNPCCount': f'''
(fn GWDevNPCCount (N)
  (if (not (CallFunction|DevOK))
    (return))
  (bind gm {GMC}
    (:then
      (GW|Set|BP_GW_GameMode|NPCCount :self gm :NPCCount N)
      (Variables|GW|SetDevCount 0)
      (for c (Actor|GetAllActorsOfClass :ActorClass {CHAR})
        (if (and (not (Pawn|IsPlayerControlled :self c)) (and (== {CH('Kind', 'c')} 0) (not {CH('IsDead', 'c')})))
          (Variables|GW|SetDevCount (+ (Variables|GW|GetDevCount) 1))
          (if (> (Variables|GW|GetDevCount) N)
            (if ({ISVALID} :Object (Pawn|GetController :self c))
              (Actor|DestroyActor :self (Pawn|GetController :self c)))
            (Actor|DestroyActor :self c))))
      (for i (range (- N (Variables|GW|GetDevCount)))
        (GW|Call|BP_GW_GameMode|SpawnNPC :self gm))
      (Development|PrintString :InString (cat "GW: dev NPC count " N) :bPrintToScreen false))
    (:CastFailed)))
''',
        'GWDevBreakerReset': f'''
(fn GWDevBreakerReset ()
  (if (not (CallFunction|DevOK))
    (return))
  (bind gm {GMC}
    (:then
      (GW|Set|BP_GW_GameMode|BreakerUsed :self gm :BreakerUsed false)
      (for b (Actor|GetAllActorsOfClass :ActorClass {BR})
        (GW|Set|BP_GW_Breaker|Thrown :self b :Thrown false)))
    (:CastFailed)))
''',
    }
    for name, code in PW.items():
        write(pc, name, code, compile_after=False)
    _t = open(TOOLS + r'\gameplay\s33_piano.py', encoding='utf-8').read().replace('\r\n', '\n')
    _m = re.search(r"write\(pc, 'InteractOther', '''(.*?)'''", _t, re.S)
    write(pc, 'InteractOther', _m.group(1), compile_after=False)
    compile_bp(pc)
    print('BP_GW_PlayerController', [p for p in node_problems(pc) if any(k in p for k in ('Breaker', 'NPCCount', 'Interact'))])
    save(pc)
print('s40 done')
