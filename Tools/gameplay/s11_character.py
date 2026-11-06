"""BP_GW_Character: graphs + defaults (one class for NPCs, hiders and seekers)."""
import sys, importlib
sys.path.insert(0, r'J:\Projets\Unreal_Projects\Guess Who\Tools\gameplay')
import gw_lib; importlib.reload(gw_lib)
from gw_lib import *

ch = load_bp('BP_GW_Character')
ISVALID = 'GW|Call|/Script/Engine.KismetSystemLibrary|IsValid'
SETVEC = 'GW|Call|/Script/Engine.MaterialInstanceDynamic|SetVectorParameterValue'

W = {}
W['ApplyLook'] = f'''
(fn ApplyLook ()
  (bind mesh (Variables|Character|GetMesh))
  (bind seeker (Variables|GW|GetIsSeeker))
  (bind female (and (not seeker) (>= (Variables|GW|GetOutfitIndex) (Utilities|Array|Length (Variables|GW|GetTorsoColors)))))
  (Components|SkeletalMesh|SetSkeletalMeshAsset :self mesh :NewMesh (select female (Variables|GW|GetBodyFemale) (Variables|GW|GetBodyMale)))
  (Variables|GW|SetTorsoMID (Rendering|Material|CreateDynamicMaterialInstance :self mesh :ElementIndex 1 :SourceMaterial (select female (Variables|GW|GetTorsoMatF) (Variables|GW|GetTorsoMatM))))
  (Variables|GW|SetLegsMID (Rendering|Material|CreateDynamicMaterialInstance :self mesh :ElementIndex 0 :SourceMaterial (select female (Variables|GW|GetLegsMatF) (Variables|GW|GetLegsMatM))))
  (bind tc (Variables|GW|GetTorsoColors))
  (bind lcs (Variables|GW|GetLegColors))
  (bind hf (Variables|GW|GetHatFlags))
  (bind idx (Math|Integer|Max(Integer) (Variables|GW|GetOutfitIndex) 0))
  (bind torso (select seeker (Variables|GW|GetSeekerTorso) (Utilities|Array|Get(acopy) tc (% idx (Math|Integer|Max(Integer) (Utilities|Array|Length tc) 1)))))
  (bind legs (select seeker (Variables|GW|GetSeekerLegs) (Utilities|Array|Get(acopy) lcs (% idx (Math|Integer|Max(Integer) (Utilities|Array|Length lcs) 1)))))
  ({SETVEC} :self (Variables|GW|GetTorsoMID) :ParameterName "Paint Tint" :Value torso)
  ({SETVEC} :self (Variables|GW|GetLegsMID) :ParameterName "Paint Tint" :Value legs)
  (bind hat (Variables|Default|GetHatMesh))
  (bind hatOn (or seeker (and (not female) (Utilities|Array|Get(acopy) hf (% idx (Math|Integer|Max(Integer) (Utilities|Array|Length hf) 1))))))
  (Components|StaticMesh|SetStaticMesh :self hat :NewMesh (select seeker (Variables|GW|GetFedoraMesh) (Variables|GW|GetTopHatMesh)))
  (Rendering|SetVisibility :self hat :bNewVisibility hatOn)
  (Transformation|SetRelativeTransform :self hat :NewTransform (select seeker (Variables|GW|GetHatRelFedora) (Variables|GW|GetHatRelTop)))
  (bind hatMat (select seeker (Variables|GW|GetHatMatSeeker) (Variables|GW|GetHatMatGuest)))
  (if ({ISVALID} :Object hatMat)
    (Rendering|Material|SetMaterial :self hat :ElementIndex 0 :Material hatMat))
  (bind mask (Variables|Default|GetMaskMesh))
  (Components|StaticMesh|SetStaticMesh :self mask :NewMesh (Variables|GW|GetMaskStaticMesh))
  (Rendering|SetVisibility :self mask :bNewVisibility (not seeker))
  (Transformation|SetRelativeTransform :self mask :NewTransform (Variables|GW|GetMaskRel))
  (if ({ISVALID} :Object (Variables|GW|GetMaskMat))
    (Rendering|Material|SetMaterial :self mask :ElementIndex 0 :Material (Variables|GW|GetMaskMat)))
  (Variables|Pawn|SetUseControllerRotationYaw seeker)
  ; over-the-shoulder: the detective's body never covers the screen-centre crosshair; guests get a relaxed view
  (bind boom (Variables|Camera|GetCameraBoom))
  ; detective: the boom pivot itself sits on the right shoulder (his yaw follows the aim), so even a wall-compressed
  ; arm keeps the body left of the crosshair; guests turn freely, so their pivot stays centred
  (Transformation|SetRelativeLocation :self boom :NewLocation (select seeker (Math|Vector|MakeVector 0.0 48.0 66.0) (Math|Vector|MakeVector 0.0 0.0 8.5)))
  (Class|SpringArmComponent|SetTargetArmLength :self boom :TargetArmLength (select seeker 230.0 330.0))
  (Class|SpringArmComponent|SetSocketOffset :self boom :SocketOffset (select seeker (Math|Vector|MakeVector 0.0 18.0 8.0) (Math|Vector|MakeVector 0.0 40.0 52.0)))
  (Class|CharacterMovementComponent|SetOrientRotationtoMovement :self (Variables|Character|GetCharacterMovement) :bOrientRotationToMovement (not seeker))
  (bind gun (Variables|Default|GetGunMesh))
  (Components|StaticMesh|SetStaticMesh :self gun :NewMesh (Variables|GW|GetRevolverMesh))
  (Rendering|SetVisibility :self gun :bNewVisibility seeker)
  (Transformation|SetRelativeTransform :self gun :NewTransform (Variables|GW|GetGunRel))
  (if ({ISVALID} :Object (Variables|GW|GetGunMat))
    (Rendering|Material|SetMaterial :self gun :ElementIndex 0 :Material (Variables|GW|GetGunMat))))
'''

W['AttachAccessories'] = '''
(fn AttachAccessories ()
  (bind mesh (Variables|Character|GetMesh))
  (Transformation|AttachComponentToComponent :self (Variables|Default|GetHatMesh) :Parent mesh :SocketName "head" :LocationRule "KeepRelative" :RotationRule "KeepRelative" :ScaleRule "KeepRelative")
  (Transformation|AttachComponentToComponent :self (Variables|Default|GetMaskMesh) :Parent mesh :SocketName "head" :LocationRule "KeepRelative" :RotationRule "KeepRelative" :ScaleRule "KeepRelative")
  (Transformation|AttachComponentToComponent :self (Variables|Default|GetGunMesh) :Parent mesh :SocketName "weapon_r" :LocationRule "KeepRelative" :RotationRule "KeepRelative" :ScaleRule "KeepRelative"))
'''

W['GoRagdoll'] = '''
(fn GoRagdoll ()
  (Collision|SetCollisionEnabled :self (Variables|Character|GetCapsuleComponent) :NewType "NoCollision")
  (bind cm (Variables|Character|GetCharacterMovement))
  (Components|Movement|StopMovementImmediately :self cm)
  (Pawn|Components|CharacterMovement|DisableMovement :self cm)
  (bind mesh (Variables|Character|GetMesh))
  (Collision|SetCollisionProfileName :self mesh :InCollisionProfileName "Ragdoll")
  (Physics|SetSimulatePhysics :self mesh :bSimulate true)
  (Physics|AddImpulsetoAllBodiesBelow :self mesh :Impulse (Variables|GW|GetHitImpulse) :BoneName "pelvis" :bVelChange true :bIncludeSelf true)
  (Audio|PlaySoundatLocation :Sound (Variables|GW|GetThudSound) :Location (Transformation|GetActorLocation) :VolumeMultiplier 0.8 :AttenuationSettings "/Game/GW/Audio/ATT_GW_Gunshot.ATT_GW_Gunshot"))
'''

W['PlayShotFX'] = '''
(fn PlayShotFX ()
  (bind gun (Variables|Default|GetGunMesh))
  (bind start (Transformation|GetWorldLocation :self gun))
  (Audio|PlaySoundatLocation :Sound (Variables|GW|GetGunshotSound) :Location start :AttenuationSettings "/Game/GW/Audio/ATT_GW_Gunshot.ATT_GW_Gunshot")
  (Rendering|Components|Light|SetIntensity :self (Variables|Default|GetMuzzleLight) :NewIntensity 40000.0)
  (Rendering|Debug|DrawDebugLine :LineStart start :LineEnd (Variables|GW|GetShotEnd) :LineColor "(R=1.0,G=0.82,B=0.45,A=1.0)" :Duration 0.12 :Thickness 1.2)
  (Utilities|Time|SetTimerbyFunctionName :Object self :FunctionName "MuzzleOff" :Time 0.07 :bLooping false))
'''

W['MuzzleOff'] = '''
(fn MuzzleOff ()
  (Rendering|Components|Light|SetIntensity :self (Variables|Default|GetMuzzleLight) :NewIntensity 0.0))
'''

W['SetSprint'] = '''
(fn SetSprint (On)
  (Variables|GW|SetIsSprinting On)
  (Class|CharacterMovementComponent|SetMaxWalkSpeed :self (Variables|Character|GetCharacterMovement) :MaxWalkSpeed (select On (Variables|GW|GetSprintSpeed) (Variables|GW|GetWalkSpeed))))
'''

W['SetFrozen'] = '''
(fn SetFrozen (Frozen)
  (bind cm (Variables|Character|GetCharacterMovement))
  (if Frozen
    (Pawn|Components|CharacterMovement|DisableMovement :self cm)
    (else
      (Pawn|Components|CharacterMovement|SetMovementMode :self cm :NewMovementMode "MOVE_Walking"))))
'''

W['ServerFire'] = '''
(fn ServerFire (Start Dir)
  (bind now (Utilities|Time|GetGameTimeinSeconds))
  (if (or (Variables|GW|GetIsDead) (not (Variables|GW|GetIsSeeker)))
    (return))
  (if (< (- now (Variables|GW|GetLastFireTime)) (Variables|GW|GetFireCooldown))
    (return))
  (bind gmode (Utilities|Casting|CastToBP_GW_GameMode (Game|GetGameMode))
    (:then
      (if (not (GW|Call|BP_GW_GameMode|CanShoot :self gmode :Shooter self))
        (return))
      (Variables|GW|SetLastFireTime now)
      (bind traceEnd (+ Start (* Dir 8000.0)))
      (bind (hit ok) (Collision|LineTraceByProfile :Start Start :End traceEnd :ProfileName "BlockAll" :bIgnoreSelf true))
      (bind (bBlock bInit hTime hDist hLoc hImpact hNormal hImpNormal hPhys hActor) (Collision|BreakHitResult hit))
      (Variables|GW|SetShotEnd (select ok hImpact traceEnd))
      (Variables|GW|SetShotTime (GameState|GetServerWorldTimeSeconds :self (Game|GetGameState)))
      (Variables|GW|SetShotCounter (+ (Variables|GW|GetShotCounter) 1))
      (Development|PrintString :InString (cat "GW: shot by " (Utilities|GetDisplayName :Object self) " hit " (Utilities|GetDisplayName :Object hActor)) :bPrintToScreen false)
      (if ok
        (bind victim (Utilities|Casting|CastToBP_GW_Character hActor)
          (:then
            (GW|Call|BP_GW_GameMode|OnCharacterShot :self gmode :Shooter self :Victim victim :Dir Dir))
          (:CastFailed))))
    (:CastFailed)))
'''

W['Die'] = '''
(fn Die (Impulse)
  (if (Variables|GW|GetIsDead)
    (return))
  (Variables|GW|SetHitImpulse Impulse)
  (Variables|GW|SetIsDead true)
  (bind ai (Utilities|Casting|CastToAIController (Pawn|GetController))
    (:then
      (Pawn|UnPossess :self ai)
      ; DestroyActor on a controller does nothing here (see Zombify, s40_events2.py): a life span ends it
      (Actor|SetLifeSpan :self ai :InLifespan 0.1))
    (:CastFailed)))
'''

W['OnRep_OutfitIndex'] = '(fn OnRep_OutfitIndex () (CallFunction|ApplyLook))'
W['OnRep_IsSeeker'] = '(fn OnRep_IsSeeker () (CallFunction|ApplyLook))'
W['OnRep_IsDead'] = '''
(fn OnRep_IsDead ()
  (if (Variables|GW|GetIsDead)
    (CallFunction|GoRagdoll)
    ; a dead robot's eyes and vision cone go out (s32_events.py)
    (if (== (Variables|GW|GetKind) 3)
      (Rendering|Components|Light|SetIntensity :self (Variables|Default|GetEyeGlow) :NewIntensity 0.0)
      (Rendering|Components|Light|SetIntensity :self (Variables|Default|GetVisionLight) :NewIntensity 0.0)
      (Rendering|SetVisibility :self (Variables|Default|GetVisionRoot) :bNewVisibility false :bPropagateToChildren true))))
'''
W['OnRep_ShotCounter'] = '''
(fn OnRep_ShotCounter ()
  ; only fresh shots: a late join / relevancy refresh replays the counter but not an old ShotTime
  (if (and (> (Variables|GW|GetShotCounter) 0) (< (- (GameState|GetServerWorldTimeSeconds :self (Game|GetGameState)) (Variables|GW|GetShotTime)) 0.5))
    (CallFunction|PlayShotFX)))
'''

EVENTS = '''
(event EventBeginPlay
  (CallFunction|AttachAccessories)
  (Utilities|Time|SetTimerbyFunctionName :Object self :FunctionName "CameraFadeTick" :Time 0.05 :bLooping true :InitialStartDelayVariance 0.02)
  (if (Utilities|HasLaunchOption :OptionToCheck "GWCamTest")
    (Utilities|Time|SetTimerbyFunctionName :Object self :FunctionName "CamTestTick" :Time 3.0 :bLooping true))
  (Class|CharacterMovementComponent|SetMaxWalkSpeed :self (Variables|Character|GetCharacterMovement) :MaxWalkSpeed (select (Variables|GW|GetIsSprinting) (Variables|GW|GetSprintSpeed) (Variables|GW|GetWalkSpeed)))
  (CallFunction|ApplyLook)
  (if (Variables|GW|GetIsDead)
    (CallFunction|GoRagdoll)))
'''

def remove_jump_input():
    """NPCs never jump: drop the template's IA_Jump / touch-jump events (JumpMaxCount is 0 as well)."""
    g = get_graph(ch, 'EventGraph')
    doomed = []
    for n in BT.find_nodes(g):
        tid = BT.get_node_infos([n])[0].type_id
        if tid.endswith('IA_Jump') or 'EventTouchJump' in tid:
            doomed.append(n)
            for p in n.list_all_pins():
                for c in p.list_connected_pins():
                    o = c.get_owning_node()
                    if o.get_node_title() in ('Jump', 'Stop Jumping'):
                        doomed.append(o)
    for n in {x.get_path_name(): x for x in doomed}.values():
        BT.delete_node(n)
    print('removed jump nodes:', len(doomed))


only = set(UE_ARGS)  # names of graphs to (re)write; empty = all
if not only or 'jump' in only:
    remove_jump_input()
for name, code in W.items():
    if only and name not in only:
        continue
    write(ch, name, code, compile_after=False)
    print('wrote', name)
if not only or 'EventGraph' in only:
    write(ch, 'EventGraph', EVENTS, compile_after=False)
    print('wrote EventGraph')
ok = compile_bp(ch)
print(node_problems(ch))
save(ch)
