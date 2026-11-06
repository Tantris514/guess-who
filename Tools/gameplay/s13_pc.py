"""BP_GW_PlayerController: local input/HUD + server-side Exec functions reached through ServerExec."""
import sys, importlib
sys.path.insert(0, r'J:\Projets\Unreal_Projects\Guess Who\Tools\gameplay')
import gw_lib; importlib.reload(gw_lib)
from gw_lib import *

pc = load_bp('BP_GW_PlayerController')
CHC = cls('BP_GW_Character')
ISVALID = 'GW|Call|/Script/Engine.KismetSystemLibrary|IsValid'
CHAR = '"/Game/GW/Blueprints/BP_GW_Character.BP_GW_Character_C"'
HUDREF = 'GW|Call|/Game/GW/UI/WBP_HUD.WBP_HUD_C|Refresh'

ga = get_graph(pc, 'AutoTestTick')
for _n in ('Moving', 'Total'):
    if _n not in BT.list_variables(pc, ga):
        BT.add_variable(pc, _n, 'int', graph=ga)
g = get_graph(pc, 'GWDebugShoot')
if 'BestD' not in BT.list_variables(pc, g):
    BT.add_variable(pc, 'BestD', 'float', graph=g)
if 'BestT' not in BT.list_variables(pc, g):
    BT.add_object_variable(pc, 'BestT', CHC, graph=g)

PS = '(GW|Get|/Script/Engine.Controller|PlayerState)'
# GWFire hands a guest's shot to GuestFire (body: s34_shop.py); declared here so this script compiles on its own
ensure_fn(pc, 'GuestFire', inputs=[('Ch', CHC), ('Start', unreal.Vector.static_struct()), ('Dir', unreal.Vector.static_struct())])

W = {}
W['SetupLocal'] = '''
(fn SetupLocal ()
  (bind sub (LocalPlayerSubsystems|GetEnhancedInputLocalPlayerSubsystem))
  (Input|AddMappingContext :self sub :MappingContext "/Game/Input/IMC_Default.IMC_Default" :Priority 0)
  (Input|AddMappingContext :self sub :MappingContext "/Game/Input/IMC_MouseLook.IMC_MouseLook" :Priority 0)
  (Input|AddMappingContext :self sub :MappingContext "/Game/GW/Input/IMC_GW.IMC_GW" :Priority 1)
  (Variables|GW|SetHUDWidget (UserInterface|CreateWidget :Class "/Game/GW/UI/WBP_HUD.WBP_HUD_C" :OwningPlayer self))
  (UserInterface|Viewport|AddtoViewport :self (Variables|GW|GetHUDWidget) :ZOrder 0)
  ; hides the first-seconds stalls (u16_curtain.py)
  (UserInterface|Viewport|AddtoViewport :self (UserInterface|CreateWidget :Class "/Game/GW/UI/WBP_Curtain.WBP_Curtain_C" :OwningPlayer self) :ZOrder 90)
  (Input|SetInputModeGameOnly :PlayerController self)
  (Variables|MouseInterface|SetShowMouseCursor false)
  (Variables|GW|SetLastPhase -1)
  (Variables|GW|SetLastMenuPress -100.0)
  (CallFunction|SendName)
  (Utilities|Time|SetTimerbyFunctionName :Object self :FunctionName "RefreshHUD" :Time 0.1 :bLooping true)
  (if (Utilities|HasLaunchOption :OptionToCheck "GWDevTest")
    (Utilities|Time|SetTimerbyFunctionName :Object self :FunctionName "DevTestTick" :Time 2.0 :bLooping true))
  (if (Utilities|HasLaunchOption :OptionToCheck "GWAutoTest")
    (Development|PrintString :InString "GW: autotest enabled on this client" :bPrintToScreen false)
    (Utilities|Time|SetTimerbyFunctionName :Object self :FunctionName "AutoTestTick" :Time 2.5 :bLooping true)))
'''
W['SendName'] = '''
(fn SendName ()
  (bind gi (Utilities|Casting|CastToBP_GW_GameInstance (Game|GetGameInstance))
    (:then
      (bind nm (GW|Get|BP_GW_GameInstance|PlayerName :self gi))
      (if (> (Utilities|String|Len nm) 0)
        (if (Networking|HasAuthority)
          (CallFunction|GWSetName :NewName nm)
          (else
            (Development|ExecuteConsoleCommand :Command (cat "ServerExec GWSetName " nm) :SpecificPlayer self)))))
    (:CastFailed)))
'''
W['GWSetName'] = '''
(fn GWSetName (NewName)
  ; BP_GW_GameMode.OnChangeName enforces 20 chars / unique / no role names for every rename path
  (if (> (Utilities|String|Len (Utilities|String|Trim :SourceString NewName)) 0)
    (Game|ChangeName :self (Game|GetGameMode) :Controller self :NewName NewName :bNameChange true)
    (Development|PrintString :InString (cat "GW: player renamed to " (PlayerState|GetPlayerName :self (GW|Get|/Script/Engine.Controller|PlayerState))) :bPrintToScreen false)))
'''
W['CheatTestTick'] = '''
(fn CheatTestTick ()
  ; -GWCheatTest: a client tries the engine cheats / native execs through ServerExec; the server must ignore them
  (Variables|GW|SetCheatStep (+ (Variables|GW|GetCheatStep) 1))
  (bind st (Variables|GW|GetCheatStep))
  (if (== st 2) (Development|ExecuteConsoleCommand :Command "ServerExec EnableCheats" :SpecificPlayer self))
  (if (== st 3) (Development|ExecuteConsoleCommand :Command "ServerExec Ghost" :SpecificPlayer self))
  (if (== st 4) (Development|ExecuteConsoleCommand :Command "ServerExec Slomo 0.2" :SpecificPlayer self))
  (if (== st 5) (Development|ExecuteConsoleCommand :Command "ServerExec DestroyAll BP_GW_Character_C" :SpecificPlayer self))
  (if (== st 6) (Development|ExecuteConsoleCommand :Command "SetName CeNomEstBeaucoupTropLongPourLeJeu" :SpecificPlayer self))
  (if (== st 7) (Development|ExecuteConsoleCommand :Command "ServerExec SetName Hote" :SpecificPlayer self))
  (if (== st 8) (Development|ExecuteConsoleCommand :Command "ServerExec Pause" :SpecificPlayer self))
  (if (== st 9) (Development|ExecuteConsoleCommand :Command "ServerExec GWStatus" :SpecificPlayer self))
  (if (== st 10) (Development|ExecuteConsoleCommand :Command "ServerExec SwitchLevel /Game/GW/Maps/Dev/L_GameplayTest" :SpecificPlayer self))
  (if (and (>= st 2) (<= st 10))
    (Development|PrintString :InString (cat "GW: cheat test step " st) :bPrintToScreen false)))
'''
W['ApplySeekerDoor'] = '''
(fn ApplySeekerDoor (Closed)
  (bind doors (Actor|GetAllActorswithTag :Tag "GW_SeekerDoor"))
  (for d doors
    (Rendering|SetActorHiddenInGame :self d :bNewHidden (not Closed))
    (Collision|SetActorEnableCollision :self d :bNewActorEnableCollision Closed)))
'''
W['MenuPressed'] = f'''
(fn MenuPressed ()
  (bind now (Utilities|Time|GetRealTimeSeconds))
  (if (< (- now (Variables|GW|GetLastMenuPress)) 3.0)
    (Development|ExecuteConsoleCommand :Command "disconnect" :SpecificPlayer self)
    (else
      (Variables|GW|SetLastMenuPress now)
      (bind hud (Variables|GW|GetHUDWidget))
      (if ({ISVALID} :Object hud)
        (GW|Set|/Game/GW/UI/WBP_HUD.WBP_HUD_C|LocalNotice :self hud :LocalNotice (select (Networking|HasAuthority) "Appuyez encore sur Échap pour quitter (la partie s'arrêtera pour tout le monde)." "Appuyez encore sur Échap pour revenir au menu principal."))
        (GW|Set|/Game/GW/UI/WBP_HUD.WBP_HUD_C|LocalNoticeTime :self hud :LocalNoticeTime now)))))
'''
W['RequestFire'] = '''
(fn RequestFire ()
  ; the aim travels with the shot; the server accepts it only near its own view (see GWFire)
  (bind rot (Pawn|GetControlRotation :self self))
  (if (Networking|HasAuthority)
    (CallFunction|GWFire :Pitch (.pitch rot) :Yaw (.yaw rot))
    (else
      (Development|ExecuteConsoleCommand :Command (cat "ServerExec GWFire " (.pitch rot) " " (.yaw rot)) :SpecificPlayer self))))
'''
W['RequestSprint'] = '''
(fn RequestSprint (On)
  (bind ch (Utilities|Casting|CastToBP_GW_Character (Pawn|GetControlledPawn :self self))
    (:then
      (GW|Call|BP_GW_Character|SetSprint :self ch :On On)
      (if (not (Networking|HasAuthority))
        (Development|ExecuteConsoleCommand :Command (select On "ServerExec GWSprint 1" "ServerExec GWSprint 0") :SpecificPlayer self)))
    (:CastFailed)))
'''
W['SprintOn'] = '(fn SprintOn () (CallFunction|RequestSprint :On true))'
W['SprintOff'] = '(fn SprintOff () (CallFunction|RequestSprint :On false))'
W['ScoresOn'] = '(fn ScoresOn () (Variables|GW|SetShowScores true))'
W['ScoresOff'] = '(fn ScoresOff () (Variables|GW|SetShowScores false))'
W['GWFire'] = '''
(fn GWFire (Pitch Yaw)
  (bind ch (Utilities|Casting|CastToBP_GW_Character (Pawn|GetControlledPawn :self self))
    (:then
      (bind cam (Transformation|GetWorldLocation :self (GW|Get|BP_GW_Character|FollowCamera :self ch)))
      (bind srvDir (Math|Vector|GetForwardVector (Pawn|GetControlRotation :self self)))
      (bind cliDir (Math|Vector|GetForwardVector (Math|Rotator|MakeRotator :Pitch Pitch :Yaw Yaw)))
      ; client aim is fresher than the last ServerMove rotation; trust it only within ~10 degrees
      (bind useCli (>= (Math|Vector|DotProduct srvDir cliDir) 0.985))
      (bind dir (select useCli cliDir srvDir))
      (if (not useCli)
        (Development|PrintString :InString "GW: fire aim too far from server view, using server rotation" :bPrintToScreen false))
      (bind t0 (Math|Float|Max(Float) (Math|Vector|DotProduct (- (Transformation|GetActorLocation :self ch) cam) dir) 0.0))
      ; a guest's left click: the shop rifle, or GuestAttack without bullets (s34_shop.py GuestFire)
      (if (GW|Get|BP_GW_Character|IsSeeker :self ch)
        (GW|Call|BP_GW_Character|ServerFire :self ch :Start (+ cam (* dir t0)) :Dir dir)
        (else
          (CallFunction|GuestFire :Ch ch :Start (+ cam (* dir t0)) :Dir dir))))
    (:CastFailed)))
'''
W['GWSprint'] = '''
(fn GWSprint (On)
  (bind ch (Utilities|Casting|CastToBP_GW_Character (Pawn|GetControlledPawn :self self))
    (:then
      (GW|Call|BP_GW_Character|SetSprint :self ch :On (!= On 0))
      (Development|PrintString :InString (cat "GW: sprint " (PlayerState|GetPlayerName :self (GW|Get|/Script/Engine.Controller|PlayerState)) " on=" On " speed=" (Class|CharacterMovementComponent|GetMaxWalkSpeed :self (GW|Get|/Script/Engine.Character|CharacterMovement :self ch))) :bPrintToScreen false))
    (:CastFailed)))
'''
W['GWDebugShoot'] = f'''
(fn GWDebugShoot (Mode)
  (if (not (Utilities|HasLaunchOption :OptionToCheck "GWAutoTest"))
    (Development|PrintString :InString "GW: GWDebugShoot refused (server not started with -GWAutoTest)" :bPrintToScreen false)
    (return))
  (bind ch (Utilities|Casting|CastToBP_GW_Character (Pawn|GetControlledPawn :self self))
    (:then
      (Variables|Default|SetBestD 100000000.0)
      (bind me (Transformation|GetActorLocation :self ch))
      (bind all (Actor|GetAllActorsOfClass :ActorClass {CHAR}))
      (for a all
        (if (and (and (not (GW|Get|BP_GW_Character|IsDead :self a)) (not (GW|Get|BP_GW_Character|IsSeeker :self a))) (== (Pawn|IsPlayerControlled :self a) (== Mode 1)))
          (bind d (Math|Vector|Distance(Vector) (Transformation|GetActorLocation :self a) me))
          (if (< d (Variables|Default|GetBestD))
            (Variables|Default|SetBestD d)
            (Variables|Default|SetBestT a))))
      (bind tgt (Variables|Default|GetBestT))
      (if ({ISVALID} :Object tgt)
        (bind tl (Transformation|GetActorLocation :self tgt))
        (bind away (Math|Vector|Normalize (- me tl)))
        (Transformation|SetActorLocation :self ch :NewLocation (+ tl (Math|Vector|MakeVector (* (.x away) 350.0) (* (.y away) 350.0) 0.0)) :bSweep false :bTeleport true)
        (bind start (+ (Transformation|GetActorLocation :self ch) (Math|Vector|MakeVector 0.0 0.0 60.0)))
        (bind dir (Math|Vector|Normalize (- (+ tl (Math|Vector|MakeVector 0.0 0.0 20.0)) start)))
        (Development|PrintString :InString (cat "GW: debug shoot mode=" Mode " target=" (Utilities|GetDisplayName :Object tgt) " dist=" (Variables|Default|GetBestD)) :bPrintToScreen false)
        (Pawn|SetControlRotation :self self :NewRotation (Math|Rotator|FindLookatRotation :Start start :Target tl))
        (GW|Call|BP_GW_Character|ServerFire :self ch :Start start :Dir dir)
        (else
          (Development|PrintString :InString (cat "GW: debug shoot mode=" Mode " found no target") :bPrintToScreen false))))
    (:CastFailed
      (Development|PrintString :InString "GW: debug shoot without a character pawn" :bPrintToScreen false))))
'''
W['GWStatus'] = f'''
(fn GWStatus ()
  (bind gs (Utilities|Casting|CastToBP_GW_GameState (Game|GetGameState))
    (:then
      (bind ps (Utilities|Casting|CastToBP_GW_PlayerState {PS})
        (:then
          (Development|PrintString :InString (cat "GW status: phase=" (GW|Get|BP_GW_GameState|Phase :self gs) " round=" (GW|Get|BP_GW_GameState|RoundNumber :self gs) " hiders=" (GW|Get|BP_GW_GameState|HidersAlive :self gs) " seekers=" (GW|Get|BP_GW_GameState|SeekersAlive :self gs) " me=" (PlayerState|GetPlayerName :self ps) " role=" (GW|Get|BP_GW_PlayerState|GWRole :self ps) " alive=" (GW|Get|BP_GW_PlayerState|IsAlive :self ps) " score=" (GW|Get|BP_GW_PlayerState|GWScore :self ps) " dilation=" (Utilities|Time|GetGlobalTimeDilation) " paused=" (Game|IsGamePaused) " characters=" (Utilities|Array|Length (Actor|GetAllActorsOfClass :ActorClass {CHAR})) " cheatmanager=" ({ISVALID} :Object (GW|Get|/Script/Engine.PlayerController|CheatManager)) " pawncollision=" (Collision|GetActorEnableCollision :self (Pawn|GetControlledPawn :self self))) :bPrintToScreen false))
        (:CastFailed)))
    (:CastFailed)))
'''
W['RefreshHUD'] = f'''
(fn RefreshHUD ()
  ; events seen from here: alarm sting, blackout + own flashlight (s32_events.py)
  (CallFunction|EventClientTick)
  (bind hud (Variables|GW|GetHUDWidget))
  (if ({ISVALID} :Object hud)
    ({HUDREF} :self hud :PC self :ShowScores (Variables|GW|GetShowScores)))
  (bind gs (Utilities|Casting|CastToBP_GW_GameState (Game|GetGameState))
    (:then
      (bind ps (Utilities|Casting|CastToBP_GW_PlayerState {PS})
        (:then
          (bind phase (GW|Get|BP_GW_GameState|Phase :self gs))
          (bind role (GW|Get|BP_GW_PlayerState|GWRole :self ps))
          (Input|ResetIgnoreMoveInput)
          (if (and (== phase 1) (and (== role 2) (GW|Get|BP_GW_PlayerState|IsAlive :self ps)))
            (Input|SetIgnoreMoveInput :bNewMoveInput true))
          (if (!= phase (Variables|GW|GetLastPhase))
            (if (and (== phase 2) (>= (Variables|GW|GetLastPhase) 0))
              (Audio|PlaySound2D :Sound "/Game/GW/Audio/S_GW_Gong.S_GW_Gong" :VolumeMultiplier 0.8))
            (if (== phase 3)
              (bind w (GW|Get|BP_GW_GameState|Winner :self gs))
              (if (or (and (== w 1) (== role 2)) (and (== w 2) (== role 1)))
                (Audio|PlaySound2D :Sound "/Game/GW/Audio/S_GW_Chime.S_GW_Chime" :VolumeMultiplier 0.7)
                (else
                  (Audio|PlaySound2D :Sound "/Game/GW/Audio/S_GW_Sombre.S_GW_Sombre" :VolumeMultiplier 0.7))))
            (CallFunction|ApplySeekerDoor :Closed (== phase 1))
            (Variables|GW|SetLastPhase phase)))
        (:CastFailed)))
    (:CastFailed)))
'''
W['AutoTestTick'] = f'''
(fn AutoTestTick ()
  (if (Utilities|HasLaunchOption :OptionToCheck "GWCheatTest")
    (CallFunction|CheatTestTick))
  (bind gs (Utilities|Casting|CastToBP_GW_GameState (Game|GetGameState))
    (:then
      (bind ps (Utilities|Casting|CastToBP_GW_PlayerState {PS})
        (:then
          (bind phase (GW|Get|BP_GW_GameState|Phase :self gs))
          (bind role (GW|Get|BP_GW_PlayerState|GWRole :self ps))
          (Variables|Default|SetMoving 0)
          (Variables|Default|SetTotal 0)
          (for a (Actor|GetAllActorsOfClass :ActorClass {CHAR})
            (if (not (Pawn|IsPlayerControlled :self a))
              (Variables|Default|SetTotal (+ (Variables|Default|GetTotal) 1))
              (if (> (Math|Vector|VectorLength (Transformation|GetVelocity :self a)) 20.0)
                (Variables|Default|SetMoving (+ (Variables|Default|GetMoving) 1)))))
          (Development|PrintString :InString (cat "GW[" (select (Networking|HasAuthority) "host" "client") "] npcs moving=" (Variables|Default|GetMoving) "/" (Variables|Default|GetTotal) " name=" (PlayerState|GetPlayerName :self ps) " score=" (GW|Get|BP_GW_PlayerState|GWScore :self ps)) :bPrintToScreen false)
          (Development|PrintString :InString (cat "GW[" (select (Networking|HasAuthority) "host" "client") "] view: phase=" phase " role=" role " alive=" (GW|Get|BP_GW_PlayerState|IsAlive :self ps) " hiders=" (GW|Get|BP_GW_GameState|HidersAlive :self gs) " pawn=" (Utilities|GetDisplayName :Object (Pawn|GetControlledPawn :self self))) :bPrintToScreen false)
          (bind hudw (Variables|GW|GetHUDWidget))
          (if ({ISVALID} :Object hudw)
            (Development|PrintString :InString (cat "GW HUD: " (GW|Call|/Game/GW/UI/WBP_HUD.WBP_HUD_C|DebugDump :self hudw)) :bPrintToScreen false))
          (if (and (== phase 2) (and (== role 1) (GW|Get|BP_GW_PlayerState|IsAlive :self ps)))
            (Variables|GW|SetAutoTestCount (+ (Variables|GW|GetAutoTestCount) 1))
            (CallFunction|RequestSprint :On (== (% (Variables|GW|GetAutoTestCount) 2) 1)))
          (if (and (== phase 2) (and (== role 2) (GW|Get|BP_GW_PlayerState|IsAlive :self ps)))
            (Variables|GW|SetAutoTestCount (+ (Variables|GW|GetAutoTestCount) 1))
            (bind k (% (Variables|GW|GetAutoTestCount) 4))
            (if (Utilities|HasLaunchOption :OptionToCheck "GWAutoNPC")
              (if (== k 1)
                (if (Networking|HasAuthority)
                  (CallFunction|GWDebugShoot :Mode 0)
                  (else
                    (Development|ExecuteConsoleCommand :Command "ServerExec GWDebugShoot 0" :SpecificPlayer self))))
              (return))
            (if (== k 2)
              (Development|PrintString :InString "GW: autotest real fire (GWFire)" :bPrintToScreen false)
              (CallFunction|RequestFire)
              (else
                (bind mode (select (== k 1) 0 1))
                (if (Networking|HasAuthority)
                  (CallFunction|GWDebugShoot :Mode mode)
                  (else
                    (Development|ExecuteConsoleCommand :Command (cat "ServerExec GWDebugShoot " mode) :SpecificPlayer self)))))))
        (:CastFailed)))
    (:CastFailed)))
'''
EVENTS = '''
(event EventBeginPlay
  (Utilities|FlowControl|DelayUntilNextTick)
  (if (Pawn|IsLocalPlayerController)
    (CallFunction|SetupLocal)))
'''

only = set(UE_ARGS)  # names of graphs to (re)write; empty = all
sys.path.insert(0, r'J:\Projets\Unreal_Projects\Guess Who\Tools\gameplay')
import shop_items
for name, code in W.items():
    if name in shop_items.S40_OWNS:      # body in s40_inventory.py (run it after this script)
        continue
    if only and name not in only:
        continue
    write(pc, name, code, compile_after=False)
    print('wrote', name)
if not only or 'EventGraph' in only:
    write(pc, 'EventGraph', EVENTS, compile_after=False)
    print('wrote EventGraph')
    compile_bp(pc, quiet=True)
    wire_input(pc, 'IA_Fire', {'Started': 'RequestFire'}, pos=(0, 1200))
    wire_input(pc, 'IA_Sprint', {'Started': 'SprintOn', 'Completed': 'SprintOff'}, pos=(0, 1600))
    wire_input(pc, 'IA_Scoreboard', {'Started': 'ScoresOn', 'Completed': 'ScoresOff'}, pos=(0, 2000))
    wire_input(pc, 'IA_Menu', {'Started': 'MenuPressed'}, pos=(0, 2400))
    print('wired inputs')
compile_bp(pc)
print(node_problems(pc))
save(pc)
