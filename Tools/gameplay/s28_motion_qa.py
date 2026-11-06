"""BP_GW_Showcase motion QA mode (dev only): -GWLineup -GWMotion.

Problems show only in motion. With NC characters in the cast (s29_gen_chars.py; 32 costume outfits without one):
k = 0..NC-1 walks each, NC the detective walking, NC+1 the detective sprinting, then NC+2.. every cast member
sprinting. For each k, a walking NPC in the
ballroom is dressed in it and followed by the camera: 6 frames from the
side, then 6 from the front, 0.15 s apart ("Shot", no UI). Each shot is logged as "GW mq shot k=.. v=.. f=.." so
Tools/qa/motion_sheets.py can label the frames. Re-running s27_showcase.py rewrites the EventGraph without this mode.
"""
import sys, importlib
sys.path.insert(0, r'J:\Projets\Unreal_Projects\Guess Who\Tools\gameplay')
import gw_lib; importlib.reload(gw_lib)
from gw_lib import *

sc = load_bp('BP_GW_Showcase', '/Game/GW/Blueprints/Dev')
CHAR = '"/Game/GW/Blueprints/BP_GW_Character.BP_GW_Character_C"'
ISVALID = 'GW|Call|/Script/Engine.KismetSystemLibrary|IsValid'
ensure_var(sc, 'MQTick', 'int', category='GW')
NC = len(cdo(load_bp('BP_GW_Character')).get_editor_property('GenChars')) or 32
LAST = 2 * NC + 1
for n in ('MotionStep', 'MotionSetup', 'FindMover'):
    ensure_fn(sc, n)
ensure_fn(sc, 'MotionShot', inputs=[('K', 'int'), ('Front', 'bool'), ('F', 'int'), ('Capture', 'bool')])
compile_bp(sc, quiet=True)
g = get_graph(sc, 'FindMover')
if 'BestV' not in BT.list_variables(sc, g):
    BT.add_variable(sc, 'BestV', 'float', graph=g)


def mv(x, y, z):
    return f'(Math|Vector|MakeVector {x} {y} {z})'


W = {}
W['MotionSetup'] = f'''
(fn MotionSetup ()
  (bind pc (Game|GetPlayerController :PlayerIndex 0))
  (Transformation|SetActorLocation :self (Pawn|GetControlledPawn :self pc) :NewLocation {mv(3000.0, 1000.0, 100.0)} :bSweep false :bTeleport true)
  (Variables|GW|SetCam (Game|SpawnActorfromClass :Class "/Script/Engine.CameraActor" :SpawnTransform (Math|Transform|MakeTransform :Location {mv(3000.0, 2750.0, 165.0)}) :CollisionHandlingOverride "AlwaysSpawn"))
  (Game|Player|SetViewTargetwithBlend :self pc :NewViewTarget (Variables|GW|GetCam))
  (for k (range 12)
    (bind p (AI|SpawnAIFromClass :PawnClass {CHAR} :Location {mv('(Math|Random|RandomFloatinRange 2400.0 3600.0)', '(Math|Random|RandomFloatinRange 2950.0 3950.0)', 100.0)} :bNoCollisionFail true))))
'''
# fastest NPC in the middle of the ballroom (a camera 220 cm away stays inside the room)
W['FindMover'] = f'''
(fn FindMover ()
  (Variables|Default|SetBestV 0.0)
  (for c (Actor|GetAllActorsOfClass :ActorClass {CHAR})
    (bind v (Math|Vector|VectorLength (Transformation|GetVelocity :self c)))
    (bind cl (Transformation|GetActorLocation :self c))
    (if (and (and (> v (Variables|Default|GetBestV)) (not (Pawn|IsPlayerControlled :self c)))
             (and (and (> (.x cl) 2400.0) (< (.x cl) 3600.0)) (and (> (.y cl) 2950.0) (< (.y cl) 3950.0))))
      (Variables|Default|SetBestV v)
      (Variables|GW|SetWalker c))))
'''
W['MotionShot'] = f'''
(fn MotionShot (K Front F Capture)
  (bind w (Variables|GW|GetWalker))
  (if ({ISVALID} :Object w)
    (bind wl (Transformation|GetActorLocation :self w))
    (bind right (Math|Vector|GetRightVector (Transformation|GetActorRotation :self w)))
    (bind side (select (> (Math|Vector|DotProduct right (- {mv(3000.0, 3400.0, 0.0)} wl)) 0.0) right (* right -1.0)))
    (bind dir (select Front (Transformation|GetActorForwardVector :self w) side))
    (CallFunction|Look :From (+ (+ wl (* dir 220.0)) {mv(0.0, 0.0, 20.0)}) :To (+ wl {mv(0.0, 0.0, 0.0)}))
    (if Capture
      (Development|PrintString :InString (cat "GW mq shot k=" K " v=" (select Front "front" "side") " f=" F " speed=" (Math|Vector|VectorLength (Transformation|GetVelocity :self w))) :bPrintToScreen false)
      (Development|ExecuteConsoleCommand :Command "Shot"))))
'''
W['MotionStep'] = f'''
(fn MotionStep ()
  (Variables|GW|SetMQTick (+ (Variables|GW|GetMQTick) 1))
  (bind tk (Variables|GW|GetMQTick))
  (if (== tk 1)
    (CallFunction|MotionSetup))
  (if (>= tk 30)
    (bind t (- tk 30))
    (bind k (/ t 16))
    (bind f (% t 16))
    (if (> k {LAST})
      (if (>= f 4)                    ; a few ticks after the last shot, so its screenshot is written
        (Game|QuitGame :SpecificPlayer (Game|GetPlayerController :PlayerIndex 0) :QuitPreference "Quit" :bIgnorePlatformRestrictions false))
      (else
        ; before the side frames and again before the front ones: the fastest NPC, dressed, sent 600 cm past the room
        ; centre (left alone, a wandering NPC often stops mid-sequence and the frames show it standing)
        (if (or (== f 0) (== f 9))
          (CallFunction|FindMover)
          (bind w (Variables|GW|GetWalker))
          (if ({ISVALID} :Object w)
            ; NC = detective walking; sprint speed from NC+1: the detective, then the cast again
            (GW|Set|BP_GW_Character|IsSeeker :self w :IsSeeker (or (== k {NC}) (== k {NC + 1})))
            (GW|Set|BP_GW_Character|OutfitIndex :self w :OutfitIndex (select (>= k {NC + 2}) (- k {NC + 2}) (select (>= k {NC}) 0 k)))
            (GW|Set|BP_GW_Character|IsSprinting :self w :IsSprinting (>= k {NC + 1}))
            (Class|CharacterMovementComponent|SetMaxWalkSpeed :self (GW|Get|/Script/Engine.Character|CharacterMovement :self w) :MaxWalkSpeed (select (>= k {NC + 1}) (GW|Get|BP_GW_Character|SprintSpeed :self w) (GW|Get|BP_GW_Character|WalkSpeed :self w)))
            (bind wl (Transformation|GetActorLocation :self w))
            (bind ctl (Utilities|Casting|CastToBP_GW_NPCController (Pawn|GetController :self w))
              (:then
                (GW|Set|BP_GW_NPCController|IsMoving :self ctl :IsMoving true)
                (GW|Set|BP_GW_NPCController|MoveStartTime :self ctl :MoveStartTime (Utilities|Time|GetGameTimeinSeconds))
                (AI|Navigation|MovetoLocation :self ctl :Dest (+ {mv(3000.0, 3450.0, 0.0)} (+ (* (Math|Vector|Normalize (- {mv(3000.0, 3450.0, 0.0)} (Math|Vector|MakeVector (.x wl) (.y wl) 0.0))) 600.0) {mv(0.0, 0.0, '(.z wl)')})) :AcceptanceRadius 60.0 :bStopOnOverlap true :bUsePathfinding true :bProjectDestinationToNavigation true :bCanStrafe false :bAllowPartialPath true))
              (:CastFailed))))
        (if (and (>= f 2) (<= f 8))
          (CallFunction|MotionShot :K k :Front false :F f :Capture (>= f 3)))
        (if (>= f 9)
          (CallFunction|MotionShot :K k :Front true :F f :Capture (>= f 10)))))))
'''
for name in ('MotionSetup', 'FindMover', 'MotionShot', 'MotionStep'):
    write(sc, name, W[name], compile_after=False)
    compile_bp(sc, quiet=True)
write(sc, 'EventGraph', '''
(event EventBeginPlay
  (Development|PrintString :InString "GW: showcase running" :bPrintToScreen false)
  (if (Utilities|HasLaunchOption :OptionToCheck "GWMotion")
    (Utilities|Time|SetTimerbyFunctionName :Object self :FunctionName "MotionStep" :Time 0.15 :bLooping true :InitialStartDelay 4.0)
    (else
      (Utilities|Time|SetTimerbyFunctionName :Object self :FunctionName "Step" :Time 2.5 :bLooping true :InitialStartDelay 6.0))))
''', compile_after=False)
compile_bp(sc)
print(node_problems(sc))
save(sc)
