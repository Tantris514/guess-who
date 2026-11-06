"""Last one standing (the user, 2026-11-06): every player is a guest, the last one alive wins. Nobody is a detective any more;
IsSeeker and GWRole 2 still exist in the older scripts, they are simply never set (their branches are dead code).
This script owns the player-against-player damage and the bomb defusing, listed in shop_items.S40_OWNS so the older scripts skip them.
The rest of the rules live where they always did: s12 (AssignRoles, CheckWin, EndRound, RoundTick), s40_gm (GuestHit, BladeStrike, TurretHit, TrapFire, ChandBreak), s44 (NextOutfit draws the detective's model).
Order after a change:
  python ue_run.py s46_last_standing.py / s12_gamemode.py <functions> / s40_inventory.py gm pc / s44_npc_life.py gm
"""
import sys, importlib
sys.path.insert(0, r'J:\Projets\Unreal_Projects\Guess Who\Tools\gameplay')
import gw_lib; importlib.reload(gw_lib)
from gw_lib import *

CHAR = '"/Game/GW/Blueprints/BP_GW_Character.BP_GW_Character_C"'
ISVALID = 'GW|Call|/Script/Engine.KismetSystemLibrary|IsValid'
BOMB = '/Game/GW/Blueprints/Shop/BP_GW_Bomb.BP_GW_Bomb_C'
DFX = '/Game/GW/Blueprints/Shop/BP_GW_DefuseFX.BP_GW_DefuseFX_C'
SLASH_RANGE, SLASH_COS = 210.0, 0.5
PHASE = '(GW|Get|BP_GW_GameState|Phase :self (CallFunction|GetGS))'
LOG = lambda e: f'(Development|PrintString :InString {e} :bPrintToScreen false)'

gm = load_bp('BP_GW_GameMode')
psc = load_bp('BP_GW_PlayerState').generated_class()
ensure_fn(gm, 'RivalDown', inputs=[('PS', psc)])
compile_bp(gm, quiet=True)

G = {}
G['RivalDown'] = f'''
(fn RivalDown (PS)
  ; a rival player fell by this player's hand
  (if (not ({ISVALID} :Object PS))
    (return))
  (GW|Set|BP_GW_PlayerState|Kills :self PS :Kills (+ (GW|Get|BP_GW_PlayerState|Kills :self PS) 1))
  (GW|Set|BP_GW_PlayerState|GWScore :self PS :GWScore (+ (GW|Get|BP_GW_PlayerState|GWScore :self PS) 1))
  (CallFunction|ShopPay :PS PS :Amount 100 :Note "+100 $ : un rival de moins !"))
'''
G['HurtCharacter'] = f'''
(fn HurtCharacter (Victim Amount Impulse Cause)
  (if (and (== (GW|Get|BP_GW_Character|Kind :self Victim) 4) (not (GW|Get|BP_GW_Character|IsDead :self Victim)))
    (CallFunction|ZombieDown :Victim Victim :Impulse Impulse)
    (return))
  (if (== (GW|Get|BP_GW_Character|Kind :self Victim) 3)
    (CallFunction|RobotHurt :Victim Victim :Amount Amount :Dir (Math|Vector|Normalize Impulse))
    (return))
  (if (or (GW|Get|BP_GW_Character|IsDead :self Victim) (!= (GW|Get|BP_GW_Character|Kind :self Victim) 0))
    (return))
  (if (Pawn|IsPlayerControlled :self Victim)
    ; the 20 s when everyone scatters: no player can be hurt yet
    (if (== {PHASE} 1)
      (return))
    (GW|Set|BP_GW_Character|Health :self Victim :Health (- (GW|Get|BP_GW_Character|Health :self Victim) Amount))
    (if (<= (GW|Get|BP_GW_Character|Health :self Victim) 0.0)
      (CallFunction|Announce :Text (cat (CallFunction|NameOf :P Victim) " " Cause " !"))
      (CallFunction|DeathCry :Victim Victim)
      (CallFunction|KillPlayer :Victim Victim :Impulse Impulse)
      (CallFunction|UpdateCounts))
    (return))
  (CallFunction|DeathCry :Victim Victim)
  (GW|Call|BP_GW_Character|Die :self Victim :Impulse Impulse)
  (Utilities|Array|Add :TargetArray (Variables|GW|GetPendingNPCRespawns) :NewItem (+ (CallFunction|Now) (Variables|GW|GetNPCRespawnDelay))))
'''
G['WeaponHit'] = f'''
(fn WeaponHit (Attacker Victim Dir Weapon)
  ; billiard ball or sword: an NPC guest dies (the shop pays the kill), a rival player loses 25 HP
  (bind wname (select (== Weapon 0) "ball" "sword"))
  (if (== (GW|Get|BP_GW_Character|Kind :self Victim) 3)
    (CallFunction|RobotHurt :Victim Victim :Amount (select (== Weapon 0) 20.0 50.0) :Dir Dir)
    (return))
  (if (or (or (GW|Get|BP_GW_Character|IsDead :self Victim) (!= (GW|Get|BP_GW_Character|Kind :self Victim) 0)) (== Victim Attacker))
    {LOG('(cat "GW: " wname " hit ignored on " (Utilities|GetDisplayName :Object Victim))')}
    (return))
  (if (Pawn|IsPlayerControlled :self Victim)
    (CallFunction|HurtCharacter :Victim Victim :Amount 25.0 :Impulse (* Dir 300.0) :Cause (select (== Weapon 0) "a été assommé d'une boule de billard" "a été pourfendu à l'épée"))
    {LOG('(cat "GW: " wname " hit player, health=" (GW|Get|BP_GW_Character|Health :self Victim))')}
    (if (GW|Get|BP_GW_Character|IsDead :self Victim)
      (CallFunction|RivalDown :PS (CallFunction|PSOf :P Attacker))
      (CallFunction|StartPanic :Loc (Transformation|GetActorLocation :self Victim) :Dur 12.0))
    (return))
  (Variables|GW|SetSwapLoc (Transformation|GetActorLocation :self Victim))
  (CallFunction|HurtCharacter :Victim Victim :Amount 1000.0 :Impulse (* Dir 700.0) :Cause "")
  (CallFunction|StartPanic :Loc (Variables|GW|GetSwapLoc) :Dur 12.0)
  (CallFunction|RewardNPCKill :Killer Attacker :Victim Victim)
  {LOG('(cat "GW: " wname " killed NPC " (Utilities|GetDisplayName :Object Victim) " by " (CallFunction|NameOf :P Attacker))')})
'''
G['SlashTarget'] = f'''
(fn SlashTarget (Attacker Dir)
  ; who the sword reaches: guests (NPC or player) and the robot in a 2 m cone in front, nearest first, not through a wall
  (Variables|Default|SetBestD 1000000.0)
  (Variables|Default|SetBestT (Variables|GW|GetNoChar))
  (bind here (Transformation|GetActorLocation :self Attacker))
  (bind f2 (Math|Vector|Normalize (Math|Vector|MakeVector (.x Dir) (.y Dir) 0.0)))
  (for c (Actor|GetAllActorsOfClass :ActorClass {CHAR})
    (if (and (and (!= c Attacker) (not (GW|Get|BP_GW_Character|IsDead :self c))) (or (== (GW|Get|BP_GW_Character|Kind :self c) 3) (== (GW|Get|BP_GW_Character|Kind :self c) 0)))
      (bind cl (Transformation|GetActorLocation :self c))
      (bind d (Math|Vector|Distance2D(Vector) cl here))
      (bind dz (- (.z cl) (.z here)))
      (if (and (and (< d {SLASH_RANGE}) (< (* dz dz) 14400.0)) (and (< d (Variables|Default|GetBestD)) (>= (Math|Vector|DotProduct f2 (Math|Vector|Normalize (Math|Vector|MakeVector (- (.x cl) (.x here)) (- (.y cl) (.y here)) 0.0))) {SLASH_COS})))
        (Variables|Default|SetBestD d)
        (Variables|Default|SetBestT c))))
  (bind t (Variables|Default|GetBestT))
  (if (not ({ISVALID} :Object t))
    (return t))
  (bind tl (Transformation|GetActorLocation :self t))
  (bind to (Math|Vector|Normalize (- tl here)))
  (bind (hit ok) (Collision|LineTraceByChannel :Start (+ (+ here (Math|Vector|MakeVector 0.0 0.0 40.0)) (* to 40.0)) :End (+ tl (Math|Vector|MakeVector 0.0 0.0 30.0)) :TraceChannel "Visibility" :bTraceComplex false :bIgnoreSelf true))
  (bind (bBlock bInit hTime hDist hLoc hImpact hNormal hImpNormal hPhys hActor) (Collision|BreakHitResult hit))
  (if (and ok (and (!= hActor t) (!= hActor Attacker)))
    (return (Variables|GW|GetNoChar)))
  (return t))
'''
G['DefuseBomb'] = f'''
(fn DefuseBomb (B P)
  (if (not ({ISVALID} :Object B))
    (return))
  (Variables|Shop|SetTmpV (Transformation|GetActorLocation :self B))
  (Variables|Shop|SetBlastOwner (GW|Get|{BOMB}|OwnerPS :self B))
  (Actor|DestroyActor :self B)
  (Game|SpawnActorfromClass :Class "{DFX}" :SpawnTransform (Math|Transform|MakeTransform :Location (Variables|Shop|GetTmpV)) :CollisionHandlingOverride "AlwaysSpawn")
  (CallFunction|Announce :Text (cat (CallFunction|NameOf :P P) " a désamorcé une bombe !"))
  ; relief around (voice category 75 defuse_react)
  (Variables|GW|SetStamp (+ (Variables|GW|GetStamp) 1))
  (CallFunction|QueueSay :Ch (CallFunction|NearestNPC :Loc (Variables|Shop|GetTmpV) :MaxD 900.0) :Cat 75 :Delay 0.9)
  (CallFunction|ShopPay :PS (Variables|Shop|GetBlastOwner) :Amount 0 :Note "Votre bombe a été désamorcée…")
  {LOG('(cat "GW: bomb defused by " (CallFunction|NameOf :P P) " at " (Variables|Shop|GetTmpV))')})
'''
for name, code in G.items():
    write(gm, name, code, compile_after=False)
print('gm', compile_bp(gm), node_problems(gm), save(gm))

pc = load_bp('BP_GW_PlayerController')
write(pc, 'DefuseOk', '''
(fn DefuseOk ()
  ; any living guest
  (bind ps (Utilities|Casting|CastToBP_GW_PlayerState (GW|Get|/Script/Engine.Controller|PlayerState))
    (:then
      (if (!= (GW|Get|BP_GW_PlayerState|GWRole :self ps) 1)
        (return false))
      (bind ch (Utilities|Casting|CastToBP_GW_Character (Pawn|GetControlledPawn :self self))
        (:then (return (not (GW|Get|BP_GW_Character|IsDead :self ch))))
        (:CastFailed (return false))))
    (:CastFailed (return false))))
''', compile_after=False)
print('pc', compile_bp(pc), node_problems(pc), save(pc))
