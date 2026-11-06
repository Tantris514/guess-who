"""Camera comfort: locally hide characters that the camera is inside of / that stand between the camera and the
local player (hysteresis, no probe jitter), hide the own body when a wall pushes the camera into it, and the same
near-camera fade for the ghost spectator. Over-the-shoulder boom settings are applied by ApplyLook (s11)."""
import sys, importlib
sys.path.insert(0, r'J:\Projets\Unreal_Projects\Guess Who\Tools\gameplay')
import gw_lib; importlib.reload(gw_lib)
from gw_lib import *

ch = load_bp('BP_GW_Character')
gh = load_bp('BP_GW_Ghost')
CHC = ch.generated_class()
CHAR = '"/Game/GW/Blueprints/BP_GW_Character.BP_GW_Character_C"'
ISVALID = 'GW|Call|/Script/Engine.KismetSystemLibrary|IsValid'
FADE = 'GW|Call|BP_GW_Character|SetFadeHidden'

for bp in (ch, gh):
    ensure_var(bp, 'FadedChars', obj_class=CHC, array=True, category='GW')
ensure_fn(ch, 'CameraFadeTick')
ensure_fn(ch, 'SetFadeHidden', inputs=[('Hidden', 'bool')])
ensure_fn(gh, 'GhostFadeTick')
compile_bp(ch, quiet=True)
compile_bp(gh, quiet=True)


def unfade_all():
    return f'''(for f (Variables|GW|GetFadedChars)
        (if ({ISVALID} :Object f)
          ({FADE} :self f :Hidden false)))
      (Utilities|Array|Clear (Variables|GW|GetFadedChars))'''


def fade_loop(me, cam, head, near_in, near_out, seg_in, seg_out):
    # occluders: on the camera->own head line, or on the crosshair ray up to the player's depth
    occl = (f'(< (Math|Float|Min(Float) (Math|Float|Min(Float) (Math|Vector|GetPointDistancetoSegment (+ loc (Math|Vector|MakeVector 0.0 0.0 50.0)) {cam} {head}) '
            f'(Math|Vector|GetPointDistancetoSegment loc {cam} {head})) (Math|Float|Min(Float) (Math|Vector|GetPointDistancetoSegment (+ loc (Math|Vector|MakeVector 0.0 0.0 50.0)) {cam} aimEnd) '
            f'(Math|Vector|GetPointDistancetoSegment loc {cam} aimEnd))) (select was {seg_out} {seg_in}))') if head else 'false'
    cond = f'(!= c {me})' if me else 'true'
    return f'''(for c (Actor|GetAllActorsOfClass :ActorClass {CHAR})
    (if {cond}
      (bind was (Utilities|Array|ContainsItem (Variables|GW|GetFadedChars) c))
      (bind loc (Transformation|GetActorLocation :self c))
      (bind near (and (< (Math|Vector|Distance2D(Vector) loc {cam}) (select was {near_out} {near_in})) (< (Math|Float|Absolute(Float) (- (.z loc) (.z {cam}))) 130.0)))
      (bind hide (or near {occl}))
      (if (!= hide was)
        ({FADE} :self c :Hidden hide)
        (if hide
          (Utilities|Array|Add :TargetArray (Variables|GW|GetFadedChars) :NewItem c)
          (else
            (Utilities|Array|RemoveItem :TargetArray (Variables|GW|GetFadedChars) :Item c))))))'''


write(ch, 'SetFadeHidden', '''
(fn SetFadeHidden (Hidden)
  (Development|SetHiddeninGame :self (Variables|Character|GetMesh) :NewHidden Hidden :bPropagateToChildren true))
''', compile_after=False)
compile_bp(ch, quiet=True)
write(ch, 'CameraFadeTick', f'''
(fn CameraFadeTick ()
  (if (not (and (Pawn|IsLocallyControlled) (Pawn|IsPlayerControlled)))
    (if (> (Utilities|Array|Length (Variables|GW|GetFadedChars)) 0)
      {unfade_all()})
    (Development|SetHiddeninGame :self (Variables|Character|GetMesh) :NewHidden false :bPropagateToChildren true)
    ; nobody looks through this one: no more timer (EventReceiveRestarted starts it again, s44_npc_life.py), no camera rig (a remote player keeps his on the server: the shot ray starts there)
    (Variables|GW|SetFadeTimerOn false)
    (Utilities|Time|ClearTimerbyFunctionName :Object self :FunctionName "CameraFadeTick")
    (if (not (and (Networking|HasAuthority) (Pawn|IsPlayerControlled)))
      (CallFunction|SetLean :On true))
    (return))
  (bind cam (Transformation|GetWorldLocation :self (Variables|Camera|GetFollowCamera)))
  (bind head (+ (Transformation|GetActorLocation) (Math|Vector|MakeVector 0.0 0.0 60.0)))
  (bind camFwd (Transformation|GetForwardVector :self (Variables|Camera|GetFollowCamera)))
  (bind aimEnd (+ cam (* camFwd (Math|Vector|Distance(Vector) cam head))))
  ; first person (s37_view.py: the camera at the eyes) = own body hidden; capsules keep other meshes clear of the eyes,
  ; so the near fade shrinks to 25 / 35 cm there (a detective inspecting a suspect up close still sees him)
  (bind fp (< (Math|Vector|Distance(Vector) cam head) 55.0))
  (Development|SetHiddeninGame :self (Variables|Character|GetMesh) :NewHidden fp :bPropagateToChildren true)
  ; only a guest the camera is really inside of. Hiding whoever crossed the line of sight made guests vanish and reappear in full view (feedback 2026-11-05, s44_npc_life.py).
  {fade_loop('self', 'cam', None, '(select fp 25.0 42.0)', '(select fp 35.0 58.0)', 0, 0)})
''', compile_after=False)
compile_bp(ch)
ONLY = set(UE_ARGS)   # 'CameraFadeTick': only that graph (a full run also rewrites BP_GW_Ghost's EventGraph,
                      # which s30_ghost.py owns now: run s30 after a full s23 run)
if ONLY:
    print(node_problems(ch))
    save(ch)
if not ONLY:

    write(gh, 'GhostFadeTick', f'''
    (fn GhostFadeTick ()
      (if (not (and (Pawn|IsLocallyControlled) (Pawn|IsPlayerControlled)))
        (if (> (Utilities|Array|Length (Variables|GW|GetFadedChars)) 0)
          {unfade_all()})
        (return))
      (bind cam (Transformation|GetActorLocation))
      {fade_loop(None, 'cam', None, 80.0, 100.0, 0, 0)})
    ''', compile_after=False)
    write(gh, 'EventGraph', '''
    (event EventBeginPlay
      (Utilities|Time|SetTimerbyFunctionName :Object self :FunctionName "GhostFadeTick" :Time 0.05 :bLooping true))

    (event EventEndPlay (EndPlayReason)
      (for f (Variables|GW|GetFadedChars)
        (if (GW|Call|/Script/Engine.KismetSystemLibrary|IsValid :Object f)
          (GW|Call|BP_GW_Character|SetFadeHidden :self f :Hidden false))))
    ''', compile_after=False)
    compile_bp(gh)
    print(node_problems(ch), node_problems(gh))
    save(ch, gh)

    # ---- -GWCamTest (rendered listen-server host only): every 3 s put an NPC between camera and player (step 1),
    #      or the camera inside an NPC (step 2), or nothing (step 0), then take "Shot showui" for review.
    ensure_var(ch, 'CamTestStep', 'int', category='GW')
    ensure_fn(ch, 'CamTestTick')
    ensure_fn(ch, 'CamTestShot')
    g = get_graph(ch, 'CamTestTick')
    if 'BestD' not in BT.list_variables(ch, g):
        BT.add_variable(ch, 'BestD', 'float', graph=g)
    if 'BestT' not in BT.list_variables(ch, g):
        BT.add_object_variable(ch, 'BestT', CHC, graph=g)
    compile_bp(ch, quiet=True)
    write(ch, 'CamTestTick', f'''
    (fn CamTestTick ()
      (if (not (and (and (Pawn|IsLocallyControlled) (Pawn|IsPlayerControlled)) (Networking|HasAuthority)))
        (return))
      (Variables|GW|SetCamTestStep (+ (Variables|GW|GetCamTestStep) 1))
      (bind st (% (Variables|GW|GetCamTestStep) 3))
      (bind fwd (Math|Vector|GetForwardVector (Math|Rotator|MakeRotator :Yaw (.yaw (Pawn|GetControlRotation :self (Pawn|GetController))))))
      (Variables|Default|SetBestD 100000000.0)
      (bind me (Transformation|GetActorLocation))
      (for c (Actor|GetAllActorsOfClass :ActorClass {CHAR})
        (if (and (!= c self) (and ({ISVALID} :Object (Pawn|GetController :self c)) (not (Pawn|IsPlayerControlled :self c))))
          (bind d (Math|Vector|Distance(Vector) (Transformation|GetActorLocation :self c) me))
          (if (< d (Variables|Default|GetBestD))
            (Variables|Default|SetBestD d)
            (Variables|Default|SetBestT c))))
      (if (and (> st 0) ({ISVALID} :Object (Variables|Default|GetBestT)))
        (Transformation|SetActorLocation :self self :NewLocation (+ (Transformation|GetActorLocation :self (Variables|Default|GetBestT)) (* fwd (select (== st 1) 150.0 300.0))) :bSweep true :bTeleport true))
      (Utilities|Time|SetTimerbyFunctionName :Object self :FunctionName "CamTestShot" :Time 0.6 :bLooping false))
    ''', compile_after=False)
    write(ch, 'CamTestShot', '''
    (fn CamTestShot ()
      (Development|PrintString :InString (cat "GW camtest shot step=" (% (Variables|GW|GetCamTestStep) 3) " seeker=" (Variables|GW|GetIsSeeker) " faded=" (Utilities|Array|Length (Variables|GW|GetFadedChars))) :bPrintToScreen false)
      (Development|ExecuteConsoleCommand :Command "Shot showui"))
    ''', compile_after=False)
    compile_bp(ch)
    print(node_problems(ch))
    save(ch)
