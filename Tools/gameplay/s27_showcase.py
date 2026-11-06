"""BP_GW_Showcase (dev only): rendered costume review in the L_Manor ballroom.

Spawned by BP_GW_GameMode when the host runs with -GWLineup. Every 2.5 s it advances one step: lineups of all 32
outfits (front), close-ups, side profiles, a detective, walking NPCs seen from the side, a ballroom crowd shot,
each captured with the console command "Shot" (no UI) into Saved/Screenshots."""
import sys, importlib
sys.path.insert(0, r'J:\Projets\Unreal_Projects\Guess Who\Tools\gameplay')
import gw_lib; importlib.reload(gw_lib)
from gw_lib import *

D = '/Game/GW/Blueprints/Dev'
EAL.make_directory(D)
sc = load_or_create_bp('BP_GW_Showcase', unreal.Actor, D)
CHC = cls('BP_GW_Character')
CHAR = '"/Game/GW/Blueprints/BP_GW_Character.BP_GW_Character_C"'
ISVALID = 'GW|Call|/Script/Engine.KismetSystemLibrary|IsValid'
ensure_var(sc, 'StepN', 'int', category='GW')
ensure_var(sc, 'Cam', obj_class=unreal.CameraActor, category='GW')
ensure_var(sc, 'Lineup', obj_class=CHC, array=True, category='GW')
ensure_var(sc, 'Walker', obj_class=CHC, category='GW')
for n in ('Step', 'Shot', 'SpawnLineup', 'FindWalker'):
    ensure_fn(sc, n)
ensure_fn(sc, 'Look', inputs=[('From', unreal.Vector.static_struct()), ('To', unreal.Vector.static_struct())])
ensure_fn(sc, 'SetOutfits', inputs=[('Base', 'int'), ('Yaw', 'float'), ('Seeker', 'bool')])
compile_bp(sc, quiet=True)
g = get_graph(sc, 'FindWalker')
if 'BestV' not in BT.list_variables(sc, g):
    BT.add_variable(sc, 'BestV', 'float', graph=g)

ROW_Y, ROW_X0, DX, FLOOR_Z = 3300.0, 2560.0, 125.0, 92.0

W = {}
W['Look'] = '''
(fn Look (From To)
  (Transformation|SetActorLocationAndRotation :self (Variables|GW|GetCam) :NewLocation From :NewRotation (Math|Rotator|FindLookatRotation :Start From :Target To) :bSweep false :bTeleport true))
'''
W['Shot'] = '''
(fn Shot ()
  (Development|PrintString :InString (cat "GW showcase shot step=" (Variables|GW|GetStepN)) :bPrintToScreen false)
  (Development|ExecuteConsoleCommand :Command "Shot"))
'''
W['SpawnLineup'] = f'''
(fn SpawnLineup ()
  (for i (range 8)
    (bind c (Game|SpawnActorfromClass :Class {CHAR} :SpawnTransform (Math|Transform|MakeTransform :Location (Math|Vector|MakeVector (+ {ROW_X0} (* i {DX})) {ROW_Y} {FLOOR_Z}) :Rotation (Math|Rotator|MakeRotator :Yaw -90.0)) :CollisionHandlingOverride "AlwaysSpawn"))
    (Utilities|Array|Add :TargetArray (Variables|GW|GetLineup) :NewItem c)))
'''
W['SetOutfits'] = '''
(fn SetOutfits (Base Yaw Seeker)
  (for i (range (Utilities|Array|Length (Variables|GW|GetLineup)))
    (bind c (Utilities|Array|Get(acopy) (Variables|GW|GetLineup) i))
    (GW|Set|BP_GW_Character|IsSeeker :self c :IsSeeker (and Seeker (== i 0)))
    (GW|Set|BP_GW_Character|OutfitIndex :self c :OutfitIndex (+ Base i))
    (Transformation|SetActorRotation :self c :NewRotation (Math|Rotator|MakeRotator :Yaw Yaw) :bTeleportPhysics true)))
'''
W['FindWalker'] = f'''
(fn FindWalker ()
  (Variables|Default|SetBestV 0.0)
  (for c (Actor|GetAllActorsOfClass :ActorClass {CHAR})
    (bind v (Math|Vector|VectorLength (Transformation|GetVelocity :self c)))
    (bind cl (Transformation|GetActorLocation :self c))
    ; walking NPCs inside the ballroom, women on even steps, men on odd steps
    (if (and (and (> v (Variables|Default|GetBestV)) (not (Pawn|IsPlayerControlled :self c)))
             (and (and (and (> (.x cl) 2150.0) (< (.x cl) 3850.0)) (and (> (.y cl) 2550.0) (< (.y cl) 4250.0)))
                  (== (>= (GW|Get|BP_GW_Character|OutfitIndex :self c) 16) (== (% (Variables|GW|GetStepN) 2) 0))))
      (Variables|Default|SetBestV v)
      (Variables|GW|SetWalker c))))
'''


def mv(x, y, z):
    return f'(Math|Vector|MakeVector {x} {y} {z})'


def lx(i):
    return ROW_X0 + i * DX


W['Step'] = f'''
(fn Step ()
  (Variables|GW|SetStepN (+ (Variables|GW|GetStepN) 1))
  (bind st (Variables|GW|GetStepN))
  (if (== st 1)
    (bind pc (Game|GetPlayerController :PlayerIndex 0))
    (Transformation|SetActorLocation :self (Pawn|GetControlledPawn :self pc) :NewLocation {mv(3000.0, 1000.0, 100.0)} :bSweep false :bTeleport true)
    (Variables|GW|SetCam (Game|SpawnActorfromClass :Class "/Script/Engine.CameraActor" :SpawnTransform (Math|Transform|MakeTransform :Location {mv(3000.0, 2750.0, 165.0)}) :CollisionHandlingOverride "AlwaysSpawn"))
    (CallFunction|SpawnLineup)
    (Game|Player|SetViewTargetwithBlend :self pc :NewViewTarget (Variables|GW|GetCam))
    (CallFunction|Look :From {mv(3000.0, 2700.0, 160.0)} :To {mv(3000.0, ROW_Y, 120.0)})
    (for k (range 16)
      (bind p (AI|SpawnAIFromClass :PawnClass {CHAR} :Location {mv('(Math|Random|RandomFloatinRange 2300.0 3700.0)', '(Math|Random|RandomFloatinRange 3500.0 4150.0)', 100.0)} :bNoCollisionFail true))
      (bind pc2 (Utilities|Casting|CastToBP_GW_Character p)
        (:then (GW|Set|BP_GW_Character|OutfitIndex :self pc2 :OutfitIndex (Math|Random|RandomIntegerinRange 0 31)))
        (:CastFailed))))
  ; front lineups of the 32 outfits (men 0-15, women 16-31), shot on the following step
  (if (== st 2) (CallFunction|SetOutfits :Base 0 :Yaw -90.0 :Seeker false) (Development|ExecuteConsoleCommand :Command "StartFPSChart"))
  (if (== st 30) (Development|ExecuteConsoleCommand :Command "StopFPSChart"))
  (if (== st 4) (CallFunction|SetOutfits :Base 8 :Yaw -90.0 :Seeker false))
  (if (== st 6) (CallFunction|SetOutfits :Base 16 :Yaw -90.0 :Seeker false))
  (if (== st 8) (CallFunction|SetOutfits :Base 24 :Yaw -90.0 :Seeker false))
  ; close-ups (two characters) front, then side profile
  (if (== st 10) (CallFunction|SetOutfits :Base 16 :Yaw -90.0 :Seeker false) (CallFunction|Look :From {mv(lx(2.5), 3010.0, 150.0)} :To {mv(lx(2.5), ROW_Y, 125.0)}))
  (if (== st 12) (CallFunction|SetOutfits :Base 2 :Yaw -90.0 :Seeker true) (CallFunction|Look :From {mv(lx(0.5), 3030.0, 150.0)} :To {mv(lx(0.5), ROW_Y, 125.0)}))
  (if (== st 14) (CallFunction|SetOutfits :Base 20 :Yaw 0.0 :Seeker false) (CallFunction|Look :From {mv(lx(3.5), 3060.0, 140.0)} :To {mv(lx(3.5), ROW_Y, 110.0)}))
  (if (== st 16) (CallFunction|SetOutfits :Base 4 :Yaw 0.0 :Seeker false) (CallFunction|Look :From {mv(lx(3.5), 3060.0, 140.0)} :To {mv(lx(3.5), ROW_Y, 110.0)}))
  (if (== st 18) (CallFunction|SetOutfits :Base 0 :Yaw -90.0 :Seeker false))
  (if (or (== st 19) (== st 31))
    ; face close-up from the character's actual facing (outfit 3 = top hat + mask, then a woman)
    (if (== st 31) (CallFunction|SetOutfits :Base 16 :Yaw -90.0 :Seeker false))
    (bind fc (Utilities|Array|Get(acopy) (Variables|GW|GetLineup) 3))
    (bind fl (Transformation|GetActorLocation :self fc))
    (CallFunction|Look :From (+ (+ fl (* (Transformation|GetActorForwardVector :self fc) 120.0)) {mv(0.0, 0.0, 78.0)}) :To (+ fl {mv(0.0, 0.0, 72.0)})))
  ; walking NPCs seen from their side
  (if (and (>= st 20) (<= st 27))
    (CallFunction|FindWalker)
    (bind w (Variables|GW|GetWalker))
    (if ({ISVALID} :Object w)
      (bind wl (Transformation|GetActorLocation :self w))
      (bind right (Math|Vector|GetRightVector (Transformation|GetActorRotation :self w)))
      ; look from the side facing the middle of the ballroom (never from inside a wall)
      (bind side (select (> (Math|Vector|DotProduct right (- (Math|Vector|MakeVector 3000.0 3400.0 0.0) wl)) 0.0) right (* right -1.0)))
      (CallFunction|Look :From (+ (+ wl (* side 260.0)) {mv(0.0, 0.0, 40.0)}) :To (+ wl {mv(0.0, 0.0, 10.0)}))))
  ; ballroom crowd
  (if (== st 28) (CallFunction|Look :From {mv(3850.0, 2550.0, 430.0)} :To {mv(3000.0, 3600.0, 90.0)}))
  (if (== st 29) (CallFunction|Look :From {mv(3900.0, 4300.0, 260.0)} :To {mv(2900.0, 3300.0, 90.0)}))
  ; capture on odd steps from 3 (and every walking step)
  (if (or (or (and (>= st 3) (== (% st 2) 1)) (and (>= st 20) (<= st 29))) (== st 32))
    (Utilities|Time|SetTimerbyFunctionName :Object self :FunctionName "Shot" :Time 1.2 :bLooping false)))
'''
for name in ('Look', 'Shot', 'SpawnLineup', 'SetOutfits', 'FindWalker', 'Step'):
    write(sc, name, W[name], compile_after=False)
    compile_bp(sc, quiet=True)
write(sc, 'EventGraph', '''
(event EventBeginPlay
  (Development|PrintString :InString "GW: showcase running" :bPrintToScreen false)
  (Utilities|Time|SetTimerbyFunctionName :Object self :FunctionName "Step" :Time 2.5 :bLooping true :InitialStartDelay 6.0))
''', compile_after=False)
compile_bp(sc)
print(node_problems(sc))
save(sc)

