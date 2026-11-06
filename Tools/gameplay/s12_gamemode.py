"""BP_GW_GameMode: round loop, roles, spawning, kills, scoring (server only)."""
import sys, importlib
sys.path.insert(0, r'J:\Projets\Unreal_Projects\Guess Who\Tools\gameplay')
import gw_lib; importlib.reload(gw_lib)
from gw_lib import *

gm = load_bp('BP_GW_GameMode')
PSC = cls('BP_GW_PlayerState')
CHC = cls('BP_GW_Character')
ISVALID = 'GW|Call|/Script/Engine.KismetSystemLibrary|IsValid'
CHAR = '"/Game/GW/Blueprints/BP_GW_Character.BP_GW_Character_C"'
GHOST = '"/Game/GW/Blueprints/BP_GW_Ghost.BP_GW_Ghost_C"'


def gs_get(var, gs='gs'):
    return f'(GW|Get|BP_GW_GameState|{var} :self {gs})'


def gs_set(var, val, gs='gs'):
    return f'(GW|Set|BP_GW_GameState|{var} :self {gs} :{var} {val})'


def ps_get(var, ps='ps'):
    return f'(GW|Get|BP_GW_PlayerState|{var} :self {ps})'


def ps_set(var, val, ps='ps'):
    return f'(GW|Set|BP_GW_PlayerState|{var} :self {ps} :{var} {val})'


def local(fn, name, typ=None, obj=None, struct=None, array=False):
    g = get_graph(gm, fn)
    if name in BT.list_variables(gm, g):
        return
    cont = gw_lib.ContainerType.ARRAY if array else None
    if obj is not None:
        BT.add_object_variable(gm, name, obj, graph=g, container_type=cont)
    elif struct is not None:
        BT.add_struct_variable(gm, name, struct, graph=g, container_type=cont)
    else:
        BT.add_variable(gm, name, typ, graph=g, container_type=cont)


local('GetGWPlayers', 'Result', obj=PSC, array=True)
local('StartRound', 'Players', obj=PSC, array=True)
local('AssignRoles', 'Players', obj=PSC, array=True)
ensure_fn(gm, 'LastAliveName', outputs=[('Name', 'string')])
local('AssignRoles', 'Best', 'int')
local('AssignRoles', 'BestCount', 'int')
local('UpdateCounts', 'H', 'int')
local('UpdateCounts', 'S', 'int')
local('SpawnPlayerPawn', 'T', struct=unreal.Transform.static_struct())
local('SeekerSpawnTransform', 'TT', struct=unreal.Transform.static_struct())
local('RandomSpawnTransform', 'Base', struct=unreal.Vector.static_struct())
local('UniqueName', 'Base', 'string')
local('UniqueName', 'Cand', 'string')
local('UniqueName', 'N', 'int')

W = {}
W['GetGS'] = '''
(fn GetGS ()
  (bind gs (Utilities|Casting|CastToBP_GW_GameState (Game|GetGameState))
    (:then (return gs))
    (:CastFailed (return))))
'''
W['Now'] = '''
(fn Now ()
  (return (GameState|GetServerWorldTimeSeconds :self (Game|GetGameState))))
'''
W['PSOf'] = '''
(fn PSOf (P)
  (bind ps (Utilities|Casting|CastToBP_GW_PlayerState (GW|Get|/Script/Engine.Pawn|PlayerState :self P))
    (:then (return ps))
    (:CastFailed (return))))
'''
W['NameOf'] = f'''
(fn NameOf (P)
  (bind ps (CallFunction|PSOf :P P))
  (if ({ISVALID} :Object ps)
    (return (PlayerState|GetPlayerName :self ps))
    (else (return "?"))))
'''
W['GetGWPlayers'] = '''
(fn GetGWPlayers ()
  (Utilities|Array|Clear (Variables|Default|GetResult))
  (for p (Class|GameStateBase|GetPlayerArray :self (Game|GetGameState))
    (bind ps (Utilities|Casting|CastToBP_GW_PlayerState p)
      (:then (Utilities|Array|Add (Variables|Default|GetResult) ps))
      (:CastFailed)))
  (return (Variables|Default|GetResult)))
'''
W['ApplyOptions'] = '''
(fn ApplyOptions ()
  (bind opts (Variables|GameMode|GetOptionsString))
  (Variables|GW|SetHideTime (GameOptions|GetIntOption :Options opts :Key "HideTime" :DefaultValue 20))
  (Variables|GW|SetHuntTime (GameOptions|GetIntOption :Options opts :Key "HuntTime" :DefaultValue 240))
  (Variables|GW|SetEndTime (GameOptions|GetIntOption :Options opts :Key "EndTime" :DefaultValue 8))
  (Variables|GW|SetLobbyCountdown (GameOptions|GetIntOption :Options opts :Key "LobbyTime" :DefaultValue 8))
  (Variables|GW|SetNPCCount (GameOptions|GetIntOption :Options opts :Key "NPCs" :DefaultValue 120))
  (Variables|GW|SetMinPlayers (GameOptions|GetIntOption :Options opts :Key "MinPlayers" :DefaultValue 2))
  ; the game setup screen (Tools/ui/u19_game_setup.py). Without the option (tests, dev runs) each keeps its class default
  (Variables|GW|SetMaxRounds (GameOptions|GetIntOption :Options opts :Key "MaxRounds" :DefaultValue 0))
  (Variables|GW|SetEventEvery (+ 0.0 (GameOptions|GetIntOption :Options opts :Key "EventEvery" :DefaultValue (Math|Float|Truncate (Variables|GW|GetEventEvery)))))
  (Variables|GW|SetAutoEvents (!= 0 (GameOptions|GetIntOption :Options opts :Key "AutoEvents" :DefaultValue (select (Variables|GW|GetAutoEvents) 1 0))))
  (Development|PrintString :InString (cat "GW: options hide=" (Variables|GW|GetHideTime) " hunt=" (Variables|GW|GetHuntTime) " npcs=" (Variables|GW|GetNPCCount) " min=" (Variables|GW|GetMinPlayers)) :bPrintToScreen false))
'''
W['CachePoints'] = f'''
(fn CachePoints ()
  (bind a1 (Actor|GetAllActorswithTag :Tag "GW_NPCSpawn"))
  (Variables|GW|SetNPCSpawnPoints a1)
  (if (== (Utilities|Array|Length (Variables|GW|GetNPCSpawnPoints)) 0)
    (bind a3 (Actor|GetAllActorsOfClass :ActorClass "/Script/Engine.PlayerStart"))
    (Variables|GW|SetNPCSpawnPoints a3))
  (bind a2 (Actor|GetAllActorswithTag :Tag "GW_SeekerSpawn"))
  (Variables|GW|SetSeekerSpawnPoints a2)
  (Development|PrintString :InString (cat "GW: spawn points npc=" (Utilities|Array|Length (Variables|GW|GetNPCSpawnPoints)) " seeker=" (Utilities|Array|Length (Variables|GW|GetSeekerSpawnPoints))) :bPrintToScreen false))
'''
W['RandomSpawnTransform'] = '''
(fn RandomSpawnTransform ()
  (if (== (Utilities|Array|Length (Variables|GW|GetNPCSpawnPoints)) 0)
    (CallFunction|CachePoints))
  (bind pts (Variables|GW|GetNPCSpawnPoints))
  (if (> (Utilities|Array|Length pts) 0)
    (bind (item itemIdx) (Utilities|Array|RandomArrayItem pts))
    (Variables|Default|SetBase (Transformation|GetActorLocation :self item))
    (else
      (Variables|Default|SetBase (Math|Vector|MakeVector 0.0 0.0 100.0))))
  (bind (navPt navOk) (AI|Navigation|GetRandomReachablePointinRadius :Origin (Variables|Default|GetBase) :Radius 350.0))
  (bind loc (select navOk (+ navPt (Math|Vector|MakeVector 0.0 0.0 96.0)) (+ (Variables|Default|GetBase) (Math|Vector|MakeVector 0.0 0.0 96.0))))
  (return (Math|Transform|MakeTransform :Location loc :Rotation (Math|Rotator|MakeRotator :Yaw (Math|Random|RandomFloatinRange -180.0 180.0)))))
'''
W['SeekerSpawnTransform'] = '''
(fn SeekerSpawnTransform ()
  (bind pts (Variables|GW|GetSeekerSpawnPoints))
  (bind n (Utilities|Array|Length pts))
  (if (> n 0)
    (bind a (Utilities|Array|Get(acopy) pts (% (Variables|GW|GetSeekerSpawnCursor) n)))
    (Variables|Default|SetTT (Math|Transform|MakeTransform :Location (+ (Transformation|GetActorLocation :self a) (Math|Vector|MakeVector 0.0 0.0 96.0)) :Rotation (Transformation|GetActorRotation :self a)))
    (Variables|GW|SetSeekerSpawnCursor (+ (Variables|GW|GetSeekerSpawnCursor) 1))
    (return (Variables|Default|GetTT))
    (else
      (bind rt (CallFunction|RandomSpawnTransform))
      (return rt))))
'''
W['SpawnPlayerPawn'] = f'''
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
  (GW|Set|BP_GW_Character|OutfitIndex :self ch :OutfitIndex (Math|Random|RandomIntegerinRange 0 (- (Variables|GW|GetNumOutfits) 1)))
  ; dev menu pick (Tools/ui/u15_dev_menu.py) kept across rounds
  (CallFunction|ApplyDevOutfit :PC PC :Ch ch)
  (GW|Set|BP_GW_Character|Health :self ch :Health 100.0)
  (Pawn|Possess :self PC :InPawn ch)
  (if Seeker
    (GW|Call|BP_GW_Character|SetFrozen :self ch :Frozen true))
  (return ch))
'''
W['SpawnNPC'] = f'''
(fn SpawnNPC ()
  (bind t (CallFunction|RandomSpawnTransform))
  (bind p (AI|SpawnAIFromClass :PawnClass {CHAR} :Location (.location t) :Rotation (.rotation t) :bNoCollisionFail true))
  (bind c (Utilities|Casting|CastToBP_GW_Character p)
    (:then
      (GW|Set|BP_GW_Character|OutfitIndex :self c :OutfitIndex (Math|Random|RandomIntegerinRange 0 (- (Variables|GW|GetNumOutfits) 1)))
      (GW|Set|BP_GW_Character|Health :self c :Health 100.0))
    (:CastFailed)))
'''
W['SpawnInitialNPCs'] = '''
(fn SpawnInitialNPCs ()
  (for i (range (Variables|GW|GetNPCCount))
    (CallFunction|SpawnNPC)))
'''
W['ClearRoundActors'] = f'''
(fn ClearRoundActors ()
  (bind chars (Actor|GetAllActorsOfClass :ActorClass {CHAR}))
  (for a chars
    (Actor|DestroyActor :self a))
  (bind ghosts (Actor|GetAllActorsOfClass :ActorClass {GHOST}))
  (for g ghosts
    (Actor|DestroyActor :self g)))
'''
W['MakeGhost'] = f'''
(fn MakeGhost (PC Location)
  (bind g (Game|SpawnActorfromClass :Class {GHOST} :SpawnTransform (Math|Transform|MakeTransform :Location (+ Location (Math|Vector|MakeVector 0.0 0.0 120.0))) :CollisionHandlingOverride "AlwaysSpawn" :Owner PC))
  ; the dead character's own look, blue and see-through (s30_ghost.py); PC still controls the body here
  (CallFunction|DressGhost :G g :PC PC)
  (Pawn|Possess :self PC :InPawn g))
'''
W['AssignRoles'] = f'''
(fn AssignRoles ()
  ; last one standing (the user, 2026-11-06): every player is a guest (GWRole 1), nobody is a detective any more
  (for ps (CallFunction|GetGWPlayers)
    {ps_set('GWRole', 1)}
    {ps_set('IsAlive', 'true')}))
'''
W['StartRound'] = f'''
(fn StartRound ()
  (bind gs (CallFunction|GetGS))
  (CallFunction|ClearRoundActors)
  (Utilities|Array|Clear (Variables|GW|GetPendingNPCRespawns))
  (CallFunction|CachePoints)
  (CallFunction|AssignRoles)
  (Variables|Default|SetPlayers (CallFunction|GetGWPlayers))
  (for ps (Variables|Default|GetPlayers)
    (bind pcon (PlayerState|GetPlayerController :self ps))
    (if ({ISVALID} :Object pcon)
      (CallFunction|SpawnPlayerPawn :PC pcon :Seeker (== {ps_get('GWRole')} 2))))
  (CallFunction|SpawnInitialNPCs)
  {gs_set('RoundNumber', '(+ ' + gs_get('RoundNumber') + ' 1)')}
  {gs_set('Winner', 0)}
  {gs_set('Message', '""')}
  {gs_set('Phase', 1)}
  {gs_set('PhaseEndTime', '(+ (CallFunction|Now) (Variables|GW|GetHideTime))')}
  (CallFunction|UpdateCounts)
  (CallFunction|Announce :Text "Nouvelle manche : un seul quittera le bal !")
  (Development|PrintString :InString (cat "GW: round " {gs_get('RoundNumber')} " started seekers=" {gs_get('SeekersAlive')} " hiders=" {gs_get('HidersAlive')}) :bPrintToScreen false))
'''
W['BeginHunt'] = f'''
(fn BeginHunt ()
  (bind gs (CallFunction|GetGS))
  {gs_set('Phase', 2)}
  {gs_set('PhaseEndTime', '(+ (CallFunction|Now) (Variables|GW|GetHuntTime))')}
  (for ps (CallFunction|GetGWPlayers)
    (bind c (Utilities|Casting|CastToBP_GW_Character (PlayerState|GetPawn :self ps))
      (:then (GW|Call|BP_GW_Character|SetFrozen :self c :Frozen false))
      (:CastFailed)))
  (CallFunction|Announce :Text "La chasse est ouverte !"))
'''
W['EndRound'] = f'''
(fn EndRound (W Msg)
  (bind gs (CallFunction|GetGS))
  (if (== {gs_get('Phase')} 3)
    (return))
  {gs_set('Phase', 3)}
  {gs_set('PhaseEndTime', '(+ (CallFunction|Now) (Variables|GW|GetEndTime))')}
  {gs_set('Winner', 'W')}
  {gs_set('Message', 'Msg')}
  ; W: 2 a survivor (or several, on time), 3 cancelled, 4 nobody left
  (for ps (CallFunction|GetGWPlayers)
    (if (and (== W 2) (and (== {ps_get('GWRole')} 1) {ps_get('IsAlive')}))
      {ps_set('GWScore', '(+ ' + ps_get('GWScore') + ' 3)')}))
  (Development|PrintString :InString (cat "GW: round over winner=" W " : " Msg) :bPrintToScreen false))
'''
W['ResetToLobby'] = f'''
(fn ResetToLobby ()
  (bind gs (CallFunction|GetGS))
  {gs_set('RoundNumber', 0)}
  (CallFunction|ClearRoundActors)
  (Utilities|Array|Clear (Variables|GW|GetPendingNPCRespawns))
  {gs_set('Phase', 0)}
  {gs_set('PhaseEndTime', 0.0)}
  {gs_set('Winner', 0)}
  {gs_set('Message', '""')}
  (for ps (CallFunction|GetGWPlayers)
    {ps_set('GWRole', 0)}
    {ps_set('IsAlive', 'true')}
    (bind pcon (PlayerState|GetPlayerController :self ps))
    (if ({ISVALID} :Object pcon)
      (CallFunction|SpawnPlayerPawn :PC pcon :Seeker false)))
  (CallFunction|SpawnInitialNPCs)
  (Development|PrintString :InString "GW: back to lobby" :bPrintToScreen false))
'''
W['UpdateCounts'] = f'''
(fn UpdateCounts ()
  (Variables|Default|SetH 0)
  (Variables|Default|SetS 0)
  (Variables|GW|SetHidersPresent 0)
  (Variables|GW|SetSeekersPresent 0)
  (for ps (CallFunction|GetGWPlayers)
    (bind role {ps_get('GWRole')})
    (if (== role 1)
      (Variables|GW|SetHidersPresent (+ (Variables|GW|GetHidersPresent) 1))
      (elif (== role 2)
        (Variables|GW|SetSeekersPresent (+ (Variables|GW|GetSeekersPresent) 1))))
    (if {ps_get('IsAlive')}
      (if (== role 1)
        (Variables|Default|SetH (+ (Variables|Default|GetH) 1))
        (elif (== role 2)
          (Variables|Default|SetS (+ (Variables|Default|GetS) 1))))))
  (bind gs (CallFunction|GetGS))
  {gs_set('HidersAlive', '(Variables|Default|GetH)')}
  {gs_set('SeekersAlive', '(Variables|Default|GetS)')})
'''
W['LastAliveName'] = f'''
(fn LastAliveName ()
  (for ps (CallFunction|GetGWPlayers)
    (if (and (== {ps_get('GWRole')} 1) {ps_get('IsAlive')})
      (return (PlayerState|GetPlayerName :self ps))))
  (return "?"))
'''
W['CheckWin'] = f'''
(fn CheckWin ()
  ; last one standing. Alone in a solo test round the round only ends when you die
  ; dev menu "Fin de manche automatique : Non" (Tools/ui/u15_dev_menu.py): solo tests keep the round going
  (if (Variables|GW|GetDevNoWin)
    (return))
  (bind gs (CallFunction|GetGS))
  (if (<= {gs_get('HidersAlive')} 0)
    (if (> (Variables|GW|GetHidersPresent) 0)
      (CallFunction|EndRound :W 4 :Msg "Personne n'a survécu : le manoir a gagné.")
      (else
        (CallFunction|EndRound :W 3 :Msg "Manche annulée : plus aucun invité dans la partie.")))
    (return))
  (if (and (== {gs_get('HidersAlive')} 1) (>= (Variables|GW|GetHidersPresent) 2))
    (bind last (CallFunction|LastAliveName))
    (CallFunction|EndRound :W 2 :Msg (cat last " est le dernier debout !"))))
'''
W['NameTaken'] = '''
(fn NameTaken (PC Name)
  (bind mine (GW|Get|/Script/Engine.Controller|PlayerState :self PC))
  (for ps (Class|GameStateBase|GetPlayerArray :self (Game|GetGameState))
    (if (and (!= ps mine) (Utilities|String|Equal,CaseInsensitive(String) (PlayerState|GetPlayerName :self ps) Name))
      (return true)))
  (return false))
'''
W['UniqueName'] = '''
(fn UniqueName (PC Wanted)
  ; trimmed to 20 chars; empty / role-like names become "Convive N"; duplicates get " 2", " 3"...
  (bind t (Utilities|String|Left :SourceString (Utilities|String|Trim :SourceString Wanted) :Count 20))
  (bind isDefault (or (== (Utilities|String|Len t) 0) (or (Utilities|String|Equal,CaseInsensitive(String) t "Invité") (or (Utilities|String|Equal,CaseInsensitive(String) t "Invite") (or (Utilities|String|Equal,CaseInsensitive(String) t "Détective") (Utilities|String|Equal,CaseInsensitive(String) t "Player"))))))
  (Variables|Default|SetBase (select isDefault "Convive" t))
  (Variables|Default|SetN 1)
  (Variables|Default|SetCand (select isDefault "Convive 1" t))
  (while (and (CallFunction|NameTaken :PC PC :Name (Variables|Default|GetCand)) (< (Variables|Default|GetN) 60))
    (Variables|Default|SetN (+ (Variables|Default|GetN) 1))
    (Variables|Default|SetCand (cat (Variables|Default|GetBase) " " (Variables|Default|GetN))))
  (return (Variables|Default|GetCand)))
'''
W['ProcessNPCRespawns'] = '''
(fn ProcessNPCRespawns ()
  (bind arr (Variables|GW|GetPendingNPCRespawns))
  (bind now (CallFunction|Now))
  (for i (range (Utilities|Array|Length arr))
    (if (<= (Utilities|Array|Get(acopy) arr i) now)
      (Utilities|Array|RemoveIndex :TargetArray arr :IndexToRemove i)
      (CallFunction|SpawnNPC)
      (break))))
'''
W['Announce'] = f'''
(fn Announce (Text)
  (bind gs (CallFunction|GetGS))
  {gs_set('LastEvent', 'Text')}
  {gs_set('LastEventTime', '(CallFunction|Now)')}
  (Development|PrintString :InString (cat "GW: " Text) :bPrintToScreen false))
'''
W['CanShoot'] = f'''
(fn CanShoot (Shooter)
  (bind gs (CallFunction|GetGS))
  ; nobody fires a hand gun from the mezzanine machine gun (s35_turret.py); bound first: an impure call inside the
  ; return expression would be pruned by the compiler and read as false
  (bind onTurret (CallFunction|IsOnTurret :P Shooter))
  (return (and (== {gs_get('Phase')} 2) (not onTurret))))
'''
W['KillPlayer'] = f'''
(fn KillPlayer (Victim Impulse)
  (bind pcon (Pawn|GetController :self Victim))
  (bind vps (CallFunction|PSOf :P Victim))
  (bind loc (Transformation|GetActorLocation :self Victim))
  (GW|Call|BP_GW_Character|Die :self Victim :Impulse Impulse)
  (if ({ISVALID} :Object vps)
    {ps_set('IsAlive', 'false', 'vps')})
  (if ({ISVALID} :Object pcon)
    (CallFunction|MakeGhost :PC pcon :Location loc)))
'''
W['OnCharacterShot'] = f'''
(fn OnCharacterShot (Shooter Victim Dir)
  (if (GW|Get|BP_GW_Character|IsDead :self Victim)
    (return))
  ; anyone may shoot a zombie, a zombified detective too (s40_events2.py)
  (if (== (GW|Get|BP_GW_Character|Kind :self Victim) 4)
    (Variables|GW|SetGunContext true)
    (CallFunction|ZombieDown :Victim Victim :Impulse (* Dir 700.0))
    (return))
  (if (GW|Get|BP_GW_Character|IsSeeker :self Victim)
    (return))
  ; voices: lines about a gunshot are allowed now (s31 PickSound; ReactionsTick turns it off again)
  (Variables|GW|SetGunContext true)
  (bind gs (CallFunction|GetGS))
  (bind sps (CallFunction|PSOf :P Shooter))
  (bind sname (CallFunction|NameOf :P Shooter))
  ; event characters (s32_events.py Kind): bullets bounce off the robot; a shot kamikaze blows up where he stands;
  ; a bandit just falls. None of them costs the detective anything.
  (bind kind (GW|Get|BP_GW_Character|Kind :self Victim))
  (if (== kind 3)
    (Development|PrintString :InString "GW: shot bounced off the robot" :bPrintToScreen false)
    (CallFunction|Announce :Text "Les balles ricochent sur le robot !")
    (return))
  (if (== kind 2)
    (CallFunction|Announce :Text (cat sname " a fait sauter le kamikaze !"))
    (CallFunction|Explode :Loc (Transformation|GetActorLocation :self Victim) :Radius 650.0 :Cause "a été soufflé par le kamikaze")
    (return))
  (if (== kind 1)
    (CallFunction|DeathCry :Victim Victim)
    (GW|Call|BP_GW_Character|Die :self Victim :Impulse (* Dir 700.0))
    (CallFunction|Announce :Text (cat sname " a abattu un bandit !"))
    (return))
  (if (Pawn|IsPlayerControlled :self Victim)
    (Development|PrintString :InString (cat "GW: hider killed: " (CallFunction|NameOf :P Victim)) :bPrintToScreen false)
    (CallFunction|Announce :Text (cat sname " a démasqué " (CallFunction|NameOf :P Victim) " !"))
    (CallFunction|DeathCry :Victim Victim)
    (CallFunction|KillPlayer :Victim Victim :Impulse (* Dir 700.0))
    (if ({ISVALID} :Object sps)
      {ps_set('Kills', '(+ ' + ps_get('Kills', 'sps') + ' 1)', 'sps')}
      {ps_set('GWScore', '(+ ' + ps_get('GWScore', 'sps') + ' 3)', 'sps')})
    (else
      (CallFunction|DeathCry :Victim Victim)
      (GW|Call|BP_GW_Character|Die :self Victim :Impulse (* Dir 700.0))
      ; an innocent guest down: screams, alarm lines, every NPC runs 15 s, then calm-down lines (s31_reactions.py)
      (CallFunction|StartPanic :Loc (Transformation|GetActorLocation :self Victim) :Dur 15.0)
      (Utilities|Array|Add :TargetArray (Variables|GW|GetPendingNPCRespawns) :NewItem (+ (CallFunction|Now) (Variables|GW|GetNPCRespawnDelay)))
      ; dev menu test round: shooting innocents never costs health (the user tests reactions by shooting guests)
      (if {gs_get('TestRound')}
        (CallFunction|Announce :Text (cat sname " a abattu un innocent (manche de test : pas de pénalité)"))
        (return))
      (GW|Set|BP_GW_Character|Health :self Shooter :Health (- (GW|Get|BP_GW_Character|Health :self Shooter) (Variables|GW|GetInnocentPenalty)))
      (Development|PrintString :InString (cat "GW: innocent shot, seeker health=" (GW|Get|BP_GW_Character|Health :self Shooter)) :bPrintToScreen false)
      (if ({ISVALID} :Object sps)
        {ps_set('Mistakes', '(+ ' + ps_get('Mistakes', 'sps') + ' 1)', 'sps')}
        {ps_set('GWScore', '(- ' + ps_get('GWScore', 'sps') + ' 1)', 'sps')})
      (if (<= (GW|Get|BP_GW_Character|Health :self Shooter) 0.0)
        (CallFunction|Announce :Text (cat sname " a abattu trop d'innocents et est éliminé !"))
        (CallFunction|KillPlayer :Victim Shooter :Impulse (* Dir -300.0))
        (else
          (CallFunction|Announce :Text (cat sname " a abattu un innocent ! (-" (Math|Float|Round (Variables|GW|GetInnocentPenalty)) " PV)"))))))
  (CallFunction|UpdateCounts))
'''
W['RoundTick'] = f'''
(fn RoundTick ()
  (bind gs (CallFunction|GetGS))
  (if (not ({ISVALID} :Object gs))
    (return))
  (CallFunction|ProcessNPCRespawns)
  (CallFunction|UpdateCounts)
  ; voices, panic, chatter (s31_reactions.py); events (s32_events.py)
  (CallFunction|ReactionsTick)
  (CallFunction|EventTick)
  (bind now (CallFunction|Now))
  (bind np (Utilities|Array|Length (Class|GameStateBase|GetPlayerArray :self gs)))
  (bind enough (>= np (Variables|GW|GetMinPlayers)))
  (bind pend {gs_get('PhaseEndTime')})
  (switch int {gs_get('Phase')}
    (:0
      (if enough
        (if (<= pend 0.0)
          {gs_set('PhaseEndTime', '(+ now (Variables|GW|GetLobbyCountdown))')}
          (elif (>= now pend)
            (CallFunction|StartRound)))
        (else
          (if (> pend 0.0)
            {gs_set('PhaseEndTime', 0.0)}))))
    ; dev menu test round (GS.TestRound, Tools/ui/u15_dev_menu.py): never cancelled for lack of players, the hunt
    ; never times out (the hide phase still ends on time), CheckWin is off through DevNoWin
    (:1
      (if (and (not enough) (not {gs_get('TestRound')}))
        (CallFunction|EndRound :W 3 :Msg "Manche annulée : pas assez de joueurs.")
        (elif (>= now pend)
          (CallFunction|BeginHunt)
          (else
            (CallFunction|CheckWin)))))
    (:2
      (if (and (not enough) (not {gs_get('TestRound')}))
        (CallFunction|EndRound :W 3 :Msg "Manche annulée : pas assez de joueurs.")
        (elif (and (>= now pend) (not {gs_get('TestRound')}))
          (CallFunction|EndRound :W 2 :Msg (cat "Le temps est écoulé : " {gs_get('HidersAlive')} (select (> {gs_get('HidersAlive')} 1) " survivants se partagent la victoire." " survivant remporte la victoire.")))
          (else
            (CallFunction|CheckWin)))))
    (:3
      (if (>= now pend)
        (if (and enough (or (<= (Variables|GW|GetMaxRounds) 0) (< {gs_get('RoundNumber')} (Variables|GW|GetMaxRounds))))
          (CallFunction|StartRound)
          (else
            (CallFunction|ResetToLobby)))))))
'''

EVENTS = f'''
(event Game|EventOnChangeName (Other NewName bNameChange)
  ; also catches the native SetName exec: enforce the same 20-char / unique rule for every rename
  (bind clean (CallFunction|UniqueName :PC Other :Wanted NewName))
  (if (Utilities|String|NotEqualExactly(String) clean NewName)
    (Game|ChangeName :self self :Controller Other :NewName clean :bNameChange false)))

(event EventBeginPlay
  (CallFunction|ApplyOptions)
  (CallFunction|CachePoints)
  (CallFunction|SpawnInitialNPCs)
  (Utilities|Time|SetTimerbyFunctionName :Object self :FunctionName "RoundTick" :Time 0.25 :bLooping true)
  (if (Utilities|HasLaunchOption :OptionToCheck "GWLineup")
    (Game|SpawnActorfromClass :Class "/Game/GW/Blueprints/Dev/BP_GW_Showcase.BP_GW_Showcase_C" :SpawnTransform (Math|Transform|MakeTransform) :CollisionHandlingOverride "AlwaysSpawn"))
  (Development|PrintString :InString "GW: game mode ready" :bPrintToScreen false))

(event Game|EventHandleStartingNewPlayer (NewPlayer)
  (bind gs (CallFunction|GetGS))
  (bind defname (CallFunction|UniqueName :PC NewPlayer :Wanted ""))
  (Game|ChangeName :self self :Controller NewPlayer :NewName defname :bNameChange false)
  (bind ps (Utilities|Casting|CastToBP_GW_PlayerState (GW|Get|/Script/Engine.Controller|PlayerState :self NewPlayer))
    (:then
      {ps_set('GWRole', 0)}
      (if (or (not ({ISVALID} :Object gs)) (== {gs_get('Phase')} 0))
        {ps_set('IsAlive', 'true')}
        (CallFunction|SpawnPlayerPawn :PC NewPlayer :Seeker false)
        (else
          {ps_set('IsAlive', 'false')}
          (CallFunction|MakeGhost :PC NewPlayer :Location (.location (CallFunction|RandomSpawnTransform)))))
      (Development|PrintString :InString (cat "GW: player joined " (PlayerState|GetPlayerName :self ps)) :bPrintToScreen false))
    (:CastFailed
      (Game|RestartPlayer :NewPlayer NewPlayer))))
'''

# ue_run.py s12_gamemode.py OnCharacterShot CanShoot -> rewrite only those functions (the whole script on the 18 MB
# GameMode ran the editor out of memory twice on 2026-11-02)
only = set(UE_ARGS) if UE_ARGS else None
sys.path.insert(0, r'J:\Projets\Unreal_Projects\Guess Who\Tools\gameplay')
import shop_items
for k_ in ('SpawnNPC', 'SpawnPlayerPawn'):      # s44_npc_life.py renders these now (shuffled cast, unseen spawns)
    W.pop(k_)
for name, code in W.items():
    if name in shop_items.S40_OWNS:      # body in s40_inventory.py (run it after this script)
        continue
    if only and name not in only:
        continue
    write(gm, name, code, compile_after=False)
    print('wrote', name)
if not only or 'EventGraph' in only:
    write(gm, 'EventGraph', EVENTS, compile_after=False)
    print('wrote EventGraph')
compile_bp(gm)
print(node_problems(gm))
save(gm)
