"""BP_GW_NPCController (wandering AI), BP_GW_Ghost (spectator), main menu widget + menu controller."""
import sys, importlib
sys.path.insert(0, r'J:\Projets\Unreal_Projects\Guess Who\Tools\gameplay')
import gw_lib; importlib.reload(gw_lib)
from gw_lib import *

ISVALID = 'GW|Call|/Script/Engine.KismetSystemLibrary|IsValid'
which = UE_ARGS[0] if UE_ARGS else 'all'

# ------------------------------------------------------------------ NPC controller
# Guests do not walk a loop: each decision is a weighted draw -- a few steps within the room, a walk to another
# room's spawn point (sometimes through a detour waypoint), joining another guest to "talk" (they face each other and
# linger), or a long wander -- followed by a pause of very varied length, sometimes a small shuffle to turn around.
# Walking speed stays the players' own, so a disguised player can still pass for a guest.
# Panic (s31_reactions.py StartPanic sets PanicUntil / PanicFrom): sprint from point to point away from the cause.
if which in ('all', 'npc'):
    npc = load_bp('BP_GW_NPCController')
    CHC = cls('BP_GW_Character')
    V3 = unreal.Vector.static_struct()
    for v, t in (('HasFinal', 'bool'), ('ShuffleNext', 'bool'), ('PanicUntil', 'float')):
        ensure_var(npc, v, t, category='GW')
    for v in ('FinalDest', 'PanicFrom'):
        ensure_var(npc, v, struct=V3, category='GW')
    ensure_var(npc, 'Partner', obj_class=CHC, category='GW')
    ensure_var(npc, 'NoPartner', obj_class=CHC, category='GW')
    ensure_var(npc, 'Other', obj_class=CHC, category='GW')
    for f in ('ThinkWith', 'AfterArrive', 'ChooseMove', 'FleeFrom'):
        ensure_fn(npc, f, inputs=[('Ch', CHC)])
    ensure_fn(npc, 'GoTo', inputs=[('Dest', V3)])
    # social life (bodies in s36_social.py): bar crowd and ballroom dancing take over the brain while SocialMode != 0
    ensure_var(npc, 'SocialMode', 'int', category='GW')            # 0 none, 1 dancing, 2 bar crowd, 3 leaving
    ensure_fn(npc, 'SocialThink', inputs=[('Ch', CHC)], outputs=[('Handled', 'bool')])
    ensure_fn(npc, 'SocialCancel', inputs=[('Ch', CHC)])
    # seats and dancing with a guest (bodies in s40_events2.py): SocialMode 4 going to / sitting on a seat, 5 following a dancer
    ensure_fn(npc, 'SeatThink', inputs=[('Ch', CHC)], outputs=[('Handled', 'bool')])
    ensure_fn(npc, 'SitTry', inputs=[('Ch', CHC)], outputs=[('Ok', 'bool')])
    ensure_fn(npc, 'SitRelease', inputs=[('Ch', CHC)])
    compile_bp(npc, quiet=True)
    g = get_graph(npc, 'FleeFrom')
    if 'BestD' not in BT.list_variables(npc, g):
        BT.add_variable(npc, 'BestD', 'float', graph=g)
    if 'BestP' not in BT.list_variables(npc, g):
        BT.add_struct_variable(npc, 'BestP', V3, graph=g)
    CHAR = '"/Game/GW/Blueprints/BP_GW_Character.BP_GW_Character_C"'
    NPC_W = {}
    NPC_W['PickDestination'] = '''
(fn PickDestination ()
  (bind p (Pawn|GetControlledPawn :self self))
  (if (< (Math|Random|RandomFloat) 0.35)
    (if (== (Utilities|Array|Length (Variables|GW|GetPoints)) 0)
      (bind tagged (Actor|GetAllActorswithTag :Tag "GW_NPCSpawn"))
      (Variables|GW|SetPoints tagged))
    (if (> (Utilities|Array|Length (Variables|GW|GetPoints)) 0)
      (bind (pt pti) (Utilities|Array|RandomArrayItem (Variables|GW|GetPoints)))
      (bind (d1 ok1) (AI|Navigation|GetRandomReachablePointinRadius :Origin (Transformation|GetActorLocation :self pt) :Radius 250.0))
      (if ok1
        (return d1 ok1))))
  (bind (d2 ok2) (AI|Navigation|GetRandomReachablePointinRadius :Origin (Transformation|GetActorLocation :self p) :Radius 1400.0))
  (return d2 ok2))
'''
    NPC_W['Think'] = '''
(fn Think ()
  (bind ch (Utilities|Casting|CastToBP_GW_Character (Pawn|GetControlledPawn :self self))
    (:then (CallFunction|ThinkWith :Ch ch))
    (:CastFailed
      (Utilities|Time|ClearTimerbyFunctionName :Object self :FunctionName "Think"))))
'''
    NPC_W['ThinkWith'] = '''
(fn ThinkWith (Ch)
  (if (GW|Get|BP_GW_Character|IsDead :self Ch)
    (Utilities|Time|ClearTimerbyFunctionName :Object self :FunctionName "Think")
    (return))
  (bind now (Utilities|Time|GetGameTimeinSeconds))
  (bind since (- now (Variables|GW|GetMoveStartTime)))
  (bind speed (Math|Vector|VectorLength (Transformation|GetVelocity :self Ch)))
  (if (< now (Variables|GW|GetPanicUntil))
    ; panic beats the social life: stand up, stop dancing / leave the bar crowd, then run
    (if (== (Variables|GW|GetSocialMode) 4)
      (CallFunction|SitRelease :Ch Ch))
    (if (!= (Variables|GW|GetSocialMode) 0)
      (CallFunction|SocialCancel :Ch Ch))
    (if (not (GW|Get|BP_GW_Character|IsSprinting :self Ch))
      (GW|Call|BP_GW_Character|SetSprint :self Ch :On true))
    (if (or (not (Variables|GW|GetIsMoving)) (and (> since 0.8) (< speed 20.0)))
      (CallFunction|FleeFrom :Ch Ch))
    (return))
  (if (GW|Get|BP_GW_Character|IsSprinting :self Ch)
    (GW|Call|BP_GW_Character|SetSprint :self Ch :On false)
    (AI|Navigation|StopMovement :self self)
    (Variables|GW|SetIsMoving false)
    (Variables|GW|SetHasFinal false)
    (Variables|GW|SetNextMoveTime (+ now (Math|Random|RandomFloatinRange 0.3 2.5)))
    (return))
  ; on a seat, or dancing with a guest (s40_events2.py)
  (if (CallFunction|SeatThink :Ch Ch)
    (return))
  ; dancing on the ballroom floor / standing in the bar crowd (s36_social.py)
  (if (CallFunction|SocialThink :Ch Ch)
    (return))
  (if (Variables|GW|GetIsMoving)
    (if (or (and (> since 1.0) (< speed 3.0)) (> since 30.0))
      (AI|Navigation|StopMovement :self self)
      (Variables|GW|SetIsMoving false)
      (if (Variables|GW|GetHasFinal)
        (Variables|GW|SetHasFinal false)
        (CallFunction|GoTo :Dest (Variables|GW|GetFinalDest))
        (return))
      (CallFunction|AfterArrive :Ch Ch))
    (elif (>= now (Variables|GW|GetNextMoveTime))
      (CallFunction|ChooseMove :Ch Ch))))
'''
    NPC_W['AfterArrive'] = '''
(fn AfterArrive (Ch)
  (bind now (Utilities|Time|GetGameTimeinSeconds))
  (bind pt (Variables|GW|GetPartner))
  (if (GW|Call|/Script/Engine.KismetSystemLibrary|IsValid :Object pt)
    (Transformation|SetActorRotation :self Ch :NewRotation (Math|Rotator|MakeRotator :Yaw (.yaw (Math|Rotator|FindLookatRotation :Start (Transformation|GetActorLocation :self Ch) :Target (Transformation|GetActorLocation :self pt)))) :bTeleportPhysics false)
    (Variables|GW|SetNextMoveTime (+ now (Math|Random|RandomFloatinRange 8.0 18.0)))
    (return))
  (bind r (Math|Random|RandomFloat))
  (Variables|GW|SetNextMoveTime (+ now (select (< r 0.5) (Math|Random|RandomFloatinRange 1.5 6.0) (select (< r 0.82) (Math|Random|RandomFloatinRange 6.0 14.0) (Math|Random|RandomFloatinRange 14.0 24.0)))))
  (if (< (Math|Random|RandomFloat) 0.25)
    (Variables|GW|SetShuffleNext true)
    (Variables|GW|SetNextMoveTime (+ now (Math|Random|RandomFloatinRange 0.8 2.5)))))
'''
    NPC_W['GoTo'] = '''
(fn GoTo (Dest)
  (AI|Navigation|MovetoLocation :self self :Dest Dest :AcceptanceRadius 60.0 :bStopOnOverlap true :bUsePathfinding true :bProjectDestinationToNavigation true :bCanStrafe false :bAllowPartialPath true)
  (Variables|GW|SetIsMoving true)
  (Variables|GW|SetMoveStartTime (Utilities|Time|GetGameTimeinSeconds)))
'''
    NPC_W['ChooseMove'] = f'''
(fn ChooseMove (Ch)
  (bind here (Transformation|GetActorLocation :self Ch))
  (Variables|GW|SetPartner (Variables|GW|GetNoPartner))
  (if (Variables|GW|GetShuffleNext)
    (Variables|GW|SetShuffleNext false)
    (bind (sd sok) (AI|Navigation|GetRandomReachablePointinRadius :Origin here :Radius 110.0))
    (if sok
      (CallFunction|GoTo :Dest sd))
    (return))
  (if (< (Math|Random|RandomFloat) 0.14)
    (if (CallFunction|SitTry :Ch Ch)
      (return)))
  (bind r (Math|Random|RandomFloat))
  (if (< r 0.15)
    (bind all (Actor|GetAllActorsOfClass :ActorClass {CHAR}))
    (Variables|GW|SetOther (Utilities|Array|Get(acopy) all (Math|Random|RandomIntegerinRange 0 (- (Utilities|Array|Length all) 1))))
    (bind other (Variables|GW|GetOther))
    (if (and (and (!= other Ch) (not (Pawn|IsPlayerControlled :self other))) (and (not (GW|Get|BP_GW_Character|IsDead :self other)) (< (Math|Vector|Distance(Vector) (Transformation|GetActorLocation :self other) here) 1500.0)))
      (bind ol (Transformation|GetActorLocation :self other))
      (Variables|GW|SetPartner other)
      (CallFunction|GoTo :Dest (+ ol (* (Math|Vector|Normalize (- here ol)) 110.0)))
      (return)))
  (if (< r 0.40)
    (bind (hd hok) (AI|Navigation|GetRandomReachablePointinRadius :Origin here :Radius 500.0))
    (if hok
      (CallFunction|GoTo :Dest hd)
      (return)))
  (bind (dest ok) (CallFunction|PickDestination))
  (if (not ok)
    (Variables|GW|SetNextMoveTime (+ (Utilities|Time|GetGameTimeinSeconds) 1.5))
    (return))
  (if (and (> (Math|Vector|Distance(Vector) dest here) 1200.0) (< (Math|Random|RandomFloat) 0.35))
    (bind (wd wok) (AI|Navigation|GetRandomReachablePointinRadius :Origin (* (+ dest here) 0.5) :Radius 350.0))
    (if wok
      (Variables|GW|SetFinalDest dest)
      (Variables|GW|SetHasFinal true)
      (CallFunction|GoTo :Dest wd)
      (return)))
  (CallFunction|GoTo :Dest dest))
'''
    NPC_W['FleeFrom'] = '''
(fn FleeFrom (Ch)
  (bind here (Transformation|GetActorLocation :self Ch))
  (Variables|Default|SetBestD -1.0)
  (Variables|Default|SetBestP here)
  (for k (range 4)
    (bind (fd fok) (AI|Navigation|GetRandomReachablePointinRadius :Origin here :Radius 1700.0))
    (if fok
      (bind dd (Math|Vector|Distance(Vector) fd (Variables|GW|GetPanicFrom)))
      (if (> dd (Variables|Default|GetBestD))
        (Variables|Default|SetBestD dd)
        (Variables|Default|SetBestP fd))))
  (Variables|GW|SetHasFinal false)
  (CallFunction|GoTo :Dest (Variables|Default|GetBestP)))
'''
    NPC_W['EventGraph'] = """
(event EventOnPossess (PossessedPawn)
  (Variables|GW|SetIsMoving false)
  (Variables|GW|SetNextMoveTime (+ (Utilities|Time|GetGameTimeinSeconds) (Math|Random|RandomFloatinRange 0.5 5.0)))
  ; no RVO avoidance: it only runs on the server, so players cannot have it (client corrections);
  ; NPCs without it move exactly like players (no tell)
  (Utilities|Time|SetTimerbyFunctionName :Object self :FunctionName "Think" :Time 0.5 :bLooping true :InitialStartDelayVariance 0.4))
"""
    for k_ in ('ThinkWith', 'AfterArrive', 'ChooseMove', 'GoTo', 'EventGraph'):     # s44_npc_life.py renders these now
        NPC_W.pop(k_)
    for name, code in NPC_W.items():
        write(npc, name, code, compile_after=False)
        compile_bp(npc, quiet=True)
    compile_bp(npc)
    print(node_problems(npc))
    save(npc)

# ------------------------------------------------------------------ Ghost spectator pawn
if which in ('all', 'ghost'):
    gh = load_bp('BP_GW_Ghost')
    write(gh, 'GhostMove', '''
(fn GhostMove (Value)
  (bind (vx vy) (Math|Vector2D|BreakVector2D Value))
  (bind rot (Pawn|GetControlRotation :self (Pawn|GetController)))
  (Pawn|Input|AddMovementInput :WorldDirection (Math|Vector|GetForwardVector rot) :ScaleValue vy)
  (Pawn|Input|AddMovementInput :WorldDirection (Math|Vector|GetRightVector rot) :ScaleValue vx))
''', compile_after=False)
    write(gh, 'GhostLook', '''
(fn GhostLook (Value)
  (bind (vx vy) (Math|Vector2D|BreakVector2D Value))
  (Pawn|Input|AddControllerYawInput :Val vx)
  (Pawn|Input|AddControllerPitchInput :Val vy))
''', compile_after=False)
    compile_bp(gh, quiet=True)
    wire_input(gh, 'IA_Move', {'Triggered': 'GhostMove'}, pos=(0, 0), args={'GhostMove': {'Value': 'ActionValue'}})
    wire_input(gh, 'IA_Look', {'Triggered': 'GhostLook'}, pos=(0, 400), args={'GhostLook': {'Value': 'ActionValue'}})
    wire_input(gh, 'IA_MouseLook', {'Triggered': 'GhostLook'}, pos=(0, 800), args={'GhostLook': {'Value': 'ActionValue'}})
    compile_bp(gh)
    print(node_problems(gh))
    save(gh)

# ------------------------------------------------------------------ Main menu widget
if which in ('all', 'menu'):
    menu = unreal.load_asset('/Game/GW/UI/WBP_MainMenu')
    STATUS = '(Variables|WBP_MainMenu|GetTxtStatus)'
    write(menu, 'GetCleanName', '''
(fn GetCleanName ()
  (bind raw (Utilities|String|Trim :SourceString (Utilities|String|ToString(Text) (Widget|GetText(TextBox) :self (Variables|WBP_MainMenu|GetNameBox)))))
  (bind c1 (Utilities|String|Replace :SourceString raw :From " " :To "_"))
  (bind c2 (Utilities|String|Replace :SourceString c1 :From "?" :To ""))
  (bind c3 (Utilities|String|Replace :SourceString c2 :From "=" :To ""))
  (bind c4 (Utilities|String|Replace :SourceString c3 :From "#" :To ""))
  (bind c5 (Utilities|String|Left :SourceString c4 :Count 20))
  (return (select (== (Utilities|String|Len c5) 0) "Invité" c5)))
''', compile_after=False)
    write(menu, 'OnHostClicked', f'''
(fn OnHostClicked ()
  (CallFunction|StoreName)
  (Widget|SetText(Text) :self {STATUS} :InText (Utilities|Text|ToText(String) "Ouverture du manoir…"))
  (Game|OpenLevel(byName) :LevelName "/Game/GW/Maps/L_Manor" :bAbsolute true :Options (cat "listen?Name=" (CallFunction|GetCleanName))))
''', compile_after=False)
    write(menu, 'OnJoinClicked', f'''
(fn OnJoinClicked ()
  (bind ip (Utilities|String|Trim :SourceString (Utilities|String|ToString(Text) (Widget|GetText(TextBox) :self (Variables|WBP_MainMenu|GetIpBox)))))
  (bind host (select (== (Utilities|String|Len ip) 0) "127.0.0.1" ip))
  (CallFunction|StoreName)
  (Widget|SetText(Text) :self {STATUS} :InText (Utilities|Text|ToText(String) (cat "Connexion à " host "…")))
  (Development|ExecuteConsoleCommand :Command (cat "open " host "?Name=" (CallFunction|GetCleanName)) :SpecificPlayer (Widget|GetOwningPlayer)))
''', compile_after=False)
    write(menu, 'StoreName', '''
(fn StoreName ()
  (bind gi (Utilities|Casting|CastToBP_GW_GameInstance (Widget|GetGameInstance))
    (:then (GW|Set|BP_GW_GameInstance|PlayerName :self gi :PlayerName (CallFunction|GetCleanName)))
    (:CastFailed)))
''', compile_after=False)
    write(menu, 'EventGraph', f'''
(event UserInterface|EventConstruct
  (bind gi (Utilities|Casting|CastToBP_GW_GameInstance (Widget|GetGameInstance))
    (:then
      (if (> (Utilities|String|Len (GW|Get|BP_GW_GameInstance|PlayerName :self gi)) 0)
        (Widget|SetText(TextBox) :self (Variables|WBP_MainMenu|GetNameBox) :InText (Utilities|Text|ToText(String) (GW|Get|BP_GW_GameInstance|PlayerName :self gi))))
      (Widget|SetText(Text) :self {STATUS} :InText (Utilities|Text|ToText(String) (GW|Get|BP_GW_GameInstance|LastError :self gi)))
      (GW|Set|BP_GW_GameInstance|LastError :self gi :LastError ""))
    (:CastFailed)))
''', compile_after=False)
    write(menu, 'OnQuitClicked', '''
(fn OnQuitClicked ()
  (Game|QuitGame :SpecificPlayer (Widget|GetOwningPlayer) :QuitPreference "Quit" :bIgnorePlatformRestrictions false))
''', compile_after=False)
    compile_bp(menu, quiet=True)
    # button bindings -> functions
    _UO = unreal.get_default_object(unreal.UMGToolSet.static_class())
    g = get_graph(menu, 'EventGraph')
    ed = BGE.get_graph_editor(g)
    IN, OUT = unreal.EdGraphPinDirection.EGPD_INPUT, unreal.EdGraphPinDirection.EGPD_OUTPUT
    for btn, fn in (('BtnHost', 'OnHostClicked'), ('BtnJoin', 'OnJoinClicked'), ('BtnQuit', 'OnQuitClicked')):
        existing = [n for n in BT.find_nodes(g) if n.get_class().get_name() == 'K2Node_ComponentBoundEvent' and btn in n.get_node_title()]
        if not existing:
            _UO.call_method('BindToEventProperty', args=(menu, 'OnClicked', btn, unreal.Button.static_class()))
            existing = [n for n in BT.find_nodes(g) if n.get_class().get_name() == 'K2Node_ComponentBoundEvent' and btn in n.get_node_title()]
        ev = existing[0]
        then = gw_lib._pin(ev, 'then', OUT)
        if not then.list_connected_pins():
            call = ed.add_call_function_node(fn)
            p = ev.get_node_pos()
            call.set_node_pos(unreal.IntPoint(p.x + 420, p.y))
            assert then.try_create_connection(gw_lib._pin(call, 'execute', IN))
        print('bound', btn, '->', fn, ev.get_node_title())
    compile_bp(menu)
    print(node_problems(menu))
    save(menu)

    mpc = load_bp('BP_GW_MenuPlayerController')
    write(mpc, 'EventGraph', '''
(event EventBeginPlay
  (Utilities|FlowControl|DelayUntilNextTick)
  (if (Pawn|IsLocalPlayerController)
    (bind w (UserInterface|CreateWidget :Class "/Game/GW/UI/WBP_MainMenu.WBP_MainMenu_C" :OwningPlayer self))
    (UserInterface|Viewport|AddtoViewport :self w :ZOrder 0)
    (Input|SetInputModeUIOnly :PlayerController self :InWidgetToFocus w)
    (Variables|MouseInterface|SetShowMouseCursor true)))
''', compile_after=False)
    compile_bp(mpc)
    print(node_problems(mpc))
    save(mpc)
