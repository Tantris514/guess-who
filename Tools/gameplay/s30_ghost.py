"""BP_GW_Ghost: a dead player keeps their own character, blue and see-through, and stays inside the manor.

- Look: BP_GW_GameMode.DressGhost (called by MakeGhost before possessing) copies the dead character's skeletal mesh and
  its ghost material (BP_GW_Character.GenGhostMats / GenDetectiveGhostMat, s29_gen_chars.py) into the replicated
  GhostMesh / GhostMat; ApplyGhostLook puts them on GhostBody, which plays the idle loop.
- Only the ghost's owner sees it (GhostBody: OnlyOwnerSee): the living must not get hints from ghosts hovering over a
  hidden player, and a ghost's flight is local to its owner anyway (spectator movement is not replicated).
- Third-person view like the living (GhostBoom / GhostCam); the body turns with the view.
- GhostClamp (50 Hz) keeps the ghost inside the manor's walls (BOUNDS: the GW_Arch walls' box in L_Manor, inset); it
  still drifts through inner walls and floors, as a ghost should.
Usage: ue_run.py s30_ghost.py
"""
import sys, importlib
sys.path.insert(0, r'J:\Projets\Unreal_Projects\Guess Who\Tools\gameplay')
import gw_lib; importlib.reload(gw_lib)
from gw_lib import *

REP = unreal.BlueprintVariableReplication
N = REP.REP_NOTIFY
BOUNDS = ((80.0, 5920.0), (80.0, 4320.0), (120.0, 900.0))    # x, y, z of the ghost's origin (feet 120 cm lower), 80 cm off the walls
ISVALID = 'GW|Call|/Script/Engine.KismetSystemLibrary|IsValid'

gh = load_bp('BP_GW_Ghost')
body = ensure_component(gh, 'GhostBody', unreal.SkeletalMeshComponent, 'CollisionComponent')
body.set_editor_property('relative_location', unreal.Vector(0, 0, -120))
body.set_editor_property('relative_rotation', unreal.Rotator(roll=0, pitch=0, yaw=-90))
body.set_editor_property('only_owner_see', True)
body.set_editor_property('cast_shadow', False)
body.set_collision_enabled(unreal.CollisionEnabled.NO_COLLISION)
body.set_editor_property('animation_mode', unreal.AnimationMode.ANIMATION_SINGLE_NODE)
ad = unreal.SingleAnimationPlayData()
ad.set_editor_property('anim_to_play', unreal.load_asset('/Game/Characters/Mannequins/Anims/Unarmed/MM_Idle'))
ad.set_editor_property('saved_looping', True)
ad.set_editor_property('saved_playing', True)
body.set_editor_property('animation_data', ad)
boom = ensure_component(gh, 'GhostBoom', unreal.SpringArmComponent, 'CollisionComponent')
boom.set_editor_property('target_arm_length', 330.0)
boom.set_editor_property('socket_offset', unreal.Vector(0, 40, 20))
boom.set_editor_property('use_pawn_control_rotation', True)
boom.set_editor_property('do_collision_test', True)
boom.set_editor_property('probe_channel', unreal.CollisionChannel.ECC_VISIBILITY)   # the walls block it: the view stays indoors
boom.set_editor_property('probe_size', 16.0)
ensure_component(gh, 'GhostCam', unreal.CameraComponent, 'GhostBoom')
ensure_var(gh, 'GhostMesh', obj_class=unreal.SkeletalMesh, rep=N, category='GW')
ensure_var(gh, 'GhostMat', obj_class=unreal.MaterialInterface, rep=N, category='GW')
for f in ('ApplyGhostLook', 'GhostClamp', 'OnRep_GhostMesh', 'OnRep_GhostMat'):
    ensure_fn(gh, f)
compile_bp(gh, quiet=True)
cdo(gh).set_editor_property('use_controller_rotation_yaw', True)

(x0, x1), (y0, y1), (z0, z1) = BOUNDS
CL = lambda v, lo, hi: f'(Math|Float|Max(Float) {lo} (Math|Float|Min(Float) {v} {hi}))'
G = {
    'ApplyGhostLook': f'''
(fn ApplyGhostLook ()
  (bind b (Variables|Default|GetGhostBody))
  (if ({ISVALID} :Object (Variables|GW|GetGhostMesh))
    (Components|SkeletalMesh|SetSkeletalMeshAsset :self b :NewMesh (Variables|GW|GetGhostMesh)))
  (if ({ISVALID} :Object (Variables|GW|GetGhostMat))
    (Rendering|Material|SetMaterial :self b :ElementIndex 0 :Material (Variables|GW|GetGhostMat))
    (Rendering|Material|SetMaterial :self b :ElementIndex 1 :Material (Variables|GW|GetGhostMat))))
''',
    'OnRep_GhostMesh': '(fn OnRep_GhostMesh () (CallFunction|ApplyGhostLook))',
    'OnRep_GhostMat': '(fn OnRep_GhostMat () (CallFunction|ApplyGhostLook))',
    'GhostClamp': f'''
(fn GhostClamp ()
  (bind l (Transformation|GetActorLocation :self self))
  (bind c (Math|Vector|MakeVector {CL('(.x l)', x0, x1)} {CL('(.y l)', y0, y1)} {CL('(.z l)', z0, z1)}))
  (if (> (Math|Vector|VectorLength (- l c)) 0.5)
    (if (> (Math|Vector|VectorLength (- l c)) 50.0)
      (Development|PrintString :InString (cat "GW: ghost brought back inside the manor from " l " to " c) :bPrintToScreen false))
    (Transformation|SetActorLocation :self self :NewLocation c :bSweep false :bTeleport true)))
''',
}
for name, code in G.items():
    write(gh, name, code, compile_after=False)
compile_bp(gh, quiet=True)
write(gh, 'EventGraph', '''
(event EventBeginPlay
  (CallFunction|ApplyGhostLook)
  (Utilities|Time|SetTimerbyFunctionName :Object self :FunctionName "GhostClamp" :Time 0.02 :bLooping true))
''', compile_after=False)
compile_bp(gh, quiet=True)
# the flight inputs (s14_npc_ghost_menu.py) live in the same EventGraph: make sure they are still wired
wire_input(gh, 'IA_Move', {'Triggered': 'GhostMove'}, pos=(0, 0), args={'GhostMove': {'Value': 'ActionValue'}})
wire_input(gh, 'IA_Look', {'Triggered': 'GhostLook'}, pos=(0, 400), args={'GhostLook': {'Value': 'ActionValue'}})
wire_input(gh, 'IA_MouseLook', {'Triggered': 'GhostLook'}, pos=(0, 800), args={'GhostLook': {'Value': 'ActionValue'}})
compile_bp(gh)
print('BP_GW_Ghost', node_problems(gh))
save(gh)

# ---------------------------------------------------------------- game mode: dress the ghost from the dead character
gm = load_bp('BP_GW_GameMode')
# PC is a Controller, MakeGhost's own type (a removed graph cannot be re-added under the same name in one editor
# session, so the signature is only ever created here, never rebuilt)
ensure_fn(gm, 'DressGhost', inputs=[('G', gh.generated_class()), ('PC', unreal.Controller)])
compile_bp(gm, quiet=True)
write(gm, 'DressGhost', f'''
(fn DressGhost (G PC)
  (bind old (Utilities|Casting|CastToBP_GW_Character (Pawn|GetControlledPawn :self PC))
    (:then
      (bind oi (GW|Get|BP_GW_Character|OutfitIndex :self old))
      (bind mats (GW|Get|BP_GW_Character|GenGhostMats :self old))
      (if (or (GW|Get|BP_GW_Character|IsSeeker :self old) (== oi 32))
        (GW|Set|BP_GW_Ghost|GhostMat :self G :GhostMat (GW|Get|BP_GW_Character|GenDetectiveGhostMat :self old))
        (elif (and (>= oi 0) (< oi (Utilities|Array|Length mats)))
          (GW|Set|BP_GW_Ghost|GhostMat :self G :GhostMat (Utilities|Array|Get(acopy) mats oi))))
      (GW|Set|BP_GW_Ghost|GhostMesh :self G :GhostMesh (Components|SkeletalMesh|GetSkeletalMeshAsset :self (GW|Get|/Script/Engine.Character|Mesh :self old)))
      (GW|Call|BP_GW_Ghost|ApplyGhostLook :self G))
    (:CastFailed)))
''', compile_after=False)
compile_bp(gm)
print('BP_GW_GameMode', node_problems(gm))
save(gm)
