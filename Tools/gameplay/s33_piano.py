"""Instruments: near the grand piano (or the harp, the drums, the double bass), E bangs out a cacophony heard all over
the manor (a lure for the detectives). Instrument i: marker tag, fallback spot, sound category, prompt label (INSTR);
GameState.InstrSpot(I) / PC NearInstrument() / server GWPlay(I) / GM PlayInstrument(Who, I) generalise the piano
(index 0, still reached by PlayPiano for the dev menu). The drums and bass only exist once their marker is placed.
GM.OnInstrumentPlayed(Who) is the money hook (body: s34_shop.py).

- Where: BP_GW_GameState.PianoSpot finds the TargetPoint tagged GW_Piano (level, in front of the keys; fallback: the
  keyboard side of the stage piano). Every machine finds it itself, so the client can show its own prompt.
- Player: IA_Interact (E) -> BP_GW_PlayerController.RequestInteract. Near the piano (3.3 m, alive, not a ghost), the
  host calls GWPiano directly and a client sends "ServerExec GWPiano"; the server checks the distance again.
- Server: BP_GW_GameMode.PlayPiano(Who): 1 s anti-spam only (the user wants no cooldown; GameState.PianoNext), the
  piano crash (cat 'piano', ATT_GW_Far: heard everywhere, louder near), then guests near every player react
  (cat 'piano_react', silent until those voices exist).
- NPCs drift to it: PianoTick (from ReactionsTick, hunt only) sends the guest nearest the piano to the keys every
  70-150 s; it stands there a while as if tempted, but never plays (the user's rule: only players play).
- Prompt: a key cap "E" + "Jouer du piano" floats in the world just in front of the keys while you are near
  (BP_GW_KeyPrompt, a local actor with a screen-space WBP_KeyPrompt, u18_key_prompt.py), no HUD banner.
- The E key (RequestInteract): the piano first, else InteractOther, which tries TryShop, TryTurret, TryPickup,
  TryDefuse (bodies in s34_shop.py / s35_turret.py / s38_pickups.py, each returns Handled), and last TryTalk (a guest
  NPC in front answers: s39_voice_director.py).
- Dev menu (Son page): GWDevPiano (crash now, no distance check), GWDevNPCPiano (an NPC goes and plays).
Usage: ue_run.py s33_piano.py  (after s31_reactions.py and s32_events.py; then u15_dev_menu.py)
"""
import sys, importlib
sys.path.insert(0, r'J:\Projets\Unreal_Projects\Guess Who\Tools\gameplay')
import gw_lib; importlib.reload(gw_lib)
from gw_lib import *

REP = unreal.BlueprintVariableReplication
ISVALID = 'GW|Call|/Script/Engine.KismetSystemLibrary|IsValid'
GSC = '(Utilities|Casting|CastToBP_GW_GameState (Game|GetGameState))'
GMC = '(Utilities|Casting|CastToBP_GW_GameMode (Game|GetGameMode))'
MYCH = '(Utilities|Casting|CastToBP_GW_Character (Pawn|GetControlledPawn :self self))'
HUD = '/Game/GW/UI/WBP_HUD.WBP_HUD_C'
CAT_PIANO, CAT_REACT = 28, 14                       # s31_reactions.py CAT
FALLBACK = (2895.0, 4000.0, 60.0)                   # keyboard side of S(g, "piano_grand", 2850, 4130, -70, z=60)
NEAR = 330.0
COOLDOWN = 1.0
OFF = (0.0, 0.0, -100000.0)                         # no fallback: the instrument needs its level marker
INSTR = [('GW_Piano', FALLBACK, 28, 'Jouer du piano'),
         ('GW_Instrument_Harp', (3150.0, 4190.0, 60.0), 45, 'Jouer de la harpe'),     # harp at (3150, 4280) on the stage
         ('GW_Instrument_Drums', OFF, 46, 'Jouer de la batterie'),
         ('GW_Instrument_Bass', OFF, 47, 'Jouer de la contrebasse')]
V3S = unreal.Vector.static_struct()


def sel(field):
    """(select (== I 0) a (select (== I 1) b ...)) over the 4 instruments for a per-index value expression."""
    e = field(len(INSTR) - 1)
    for i in range(len(INSTR) - 2, -1, -1):
        e = f'(select (== I {i}) {field(i)} {e})'
    return e
EAL = unreal.EditorAssetLibrary
AT = unreal.AssetToolsHelpers.get_asset_tools()

# ---------------------------------------------------------------- input: E
INP = '/Game/GW/Input'
ia = unreal.load_asset(f'{INP}/IA_Interact') if EAL.does_asset_exist(f'{INP}/IA_Interact') else \
    AT.create_asset('IA_Interact', INP, unreal.InputAction, unreal.InputAction_Factory())
EAL.save_loaded_asset(ia, False)
imc = unreal.load_asset(f'{INP}/IMC_GW')
if not any(m.get_editor_property('action') == ia for m in imc.get_editor_property('default_key_mappings').get_editor_property('mappings')):
    k = unreal.Key()
    k.set_editor_property('key_name', 'E')
    imc.map_key(ia, k)
    EAL.save_loaded_asset(imc, False)

# ---------------------------------------------------------------- game state: where the piano is, shared cooldown
gs = load_bp('BP_GW_GameState')
ensure_var(gs, 'PianoNext', 'float', rep=REP.REPLICATED, category='GW')
ensure_var(gs, 'PianoLoc', struct=unreal.Vector.static_struct(), category='GW')
ensure_var(gs, 'PianoKnown', 'bool', category='GW')
ensure_fn(gs, 'PianoSpot', outputs=[('Loc', unreal.Vector.static_struct())])
ensure_var(gs, 'InstrKnown', 'bool', category='GW')
for i in range(len(INSTR)):
    ensure_var(gs, f'InstrLoc{i}', struct=V3S, category='GW')
ensure_fn(gs, 'InstrInit')
ensure_fn(gs, 'InstrSpot', inputs=[('I', 'int')], outputs=[('Loc', V3S), ('Ok', 'bool')])
compile_bp(gs, quiet=True)
write(gs, 'InstrInit', '(fn InstrInit ()\n  (Variables|GW|SetInstrKnown true)\n' + ''.join(f'''  (Variables|GW|SetInstrLoc{i} (Math|Vector|MakeVector {fb[0]} {fb[1]} {fb[2]}))
  (bind t{i} (Actor|GetAllActorswithTag :Tag "{tag}"))
  (if (> (Utilities|Array|Length t{i}) 0)
    (Variables|GW|SetInstrLoc{i} (Transformation|GetActorLocation :self (Utilities|Array|Get(acopy) t{i} 0))))
''' for i, (tag, fb, _, _) in enumerate(INSTR)) + ')\n', compile_after=False)
write(gs, 'InstrSpot', f'''
(fn InstrSpot (I)
  (if (not (Variables|GW|GetInstrKnown))
    (CallFunction|InstrInit))
  (bind loc {sel(lambda i: f'(Variables|GW|GetInstrLoc{i})')})
  (return loc (> (.z loc) -50000.0)))
''', compile_after=False)
write(gs, 'PianoSpot', f'''
(fn PianoSpot ()
  (if (not (Variables|GW|GetPianoKnown))
    (Variables|GW|SetPianoKnown true)
    (Variables|GW|SetPianoLoc (Math|Vector|MakeVector {FALLBACK[0]} {FALLBACK[1]} {FALLBACK[2]}))
    (bind pts (Actor|GetAllActorswithTag :Tag "GW_Piano"))
    (if (> (Utilities|Array|Length pts) 0)
      (Variables|GW|SetPianoLoc (Transformation|GetActorLocation :self (Utilities|Array|Get(acopy) pts 0)))))
  (return (Variables|GW|GetPianoLoc)))
''', compile_after=False)
compile_bp(gs)
print('BP_GW_GameState', node_problems(gs))
save(gs)

# ---------------------------------------------------------------- game mode: the crash, NPC pianists
gm = load_bp('BP_GW_GameMode')
chc = unreal.load_asset('/Game/GW/Blueprints/BP_GW_Character').generated_class()
for v, t in (('NextNPCPiano', 'float'), ('PianoNPCUntil', 'float')):
    ensure_var(gm, v, t, category='GW')
ensure_var(gm, 'PianoNPC', obj_class=chc, category='GW')
ensure_fn(gm, 'PlayPiano', inputs=[('Who', unreal.Pawn)])
ensure_fn(gm, 'PlayInstrument', inputs=[('Who', unreal.Pawn), ('I', 'int')])
ensure_fn(gm, 'OnInstrumentPlayed', inputs=[('Who', unreal.Pawn), ('I', 'int')])      # money hook: s34_shop.py
for i in range(len(INSTR)):
    ensure_var(gm, f'InstrNext{i}', 'float', category='GW')
ensure_fn(gm, 'PianoTick')
ensure_fn(gm, 'SendNPCToPiano')
compile_bp(gm, quiet=True)
write(gm, 'PlayPiano', '(fn PlayPiano (Who) (CallFunction|PlayInstrument :Who Who :I 0))', compile_after=False)
write(gm, 'PlayInstrument', f'''
(fn PlayInstrument (Who I)
  (bind s {GSC}
    (:then
      (bind (loc ok) (GW|Call|BP_GW_GameState|InstrSpot :self s :I I))
      (if (or (not ok) (< (CallFunction|Now) {sel(lambda i: f'(Variables|GW|GetInstrNext{i})')}))
        (return))
''' + ''.join(f'''      (if (== I {i})
        (Variables|GW|SetInstrNext{i} (+ (CallFunction|Now) {COOLDOWN})))
''' for i in range(len(INSTR))) + f'''      (GW|Set|BP_GW_GameState|PianoNext :self s :PianoNext (+ (CallFunction|Now) {COOLDOWN}))
      (CallFunction|WorldSound :Cat {sel(lambda i: str(INSTR[i][2]))} :Loc (+ loc (Math|Vector|MakeVector 0.0 0.0 100.0)))
      (Development|PrintString :InString (cat "GW: instrument " I " played by " (Utilities|GetDisplayName :Object Who)) :bPrintToScreen false)
      (CallFunction|OnInstrumentPlayed :Who Who :I I)
      (if (Math|Random|RandomBoolwithWeight :Weight 0.6)
        (CallFunction|SayNearPlayers :Cat {CAT_REACT} :PerPlayer 1 :Delay 2.2 :Spread 1.5)))
    (:CastFailed)))
''', compile_after=False)
write(gm, 'SendNPCToPiano', f'''
(fn SendNPCToPiano ()
  (bind s {GSC}
    (:then
      (Variables|GW|SetStamp (+ (Variables|GW|GetStamp) 1))
      (Variables|GW|SetPianoNPC (CallFunction|NearestNPC :Loc (GW|Call|BP_GW_GameState|PianoSpot :self s) :MaxD 2600.0))
      (Variables|GW|SetPianoNPCUntil (+ (CallFunction|Now) 25.0))
      (if ({ISVALID} :Object (Variables|GW|GetPianoNPC))
        (bind c (Utilities|Casting|CastToBP_GW_NPCController (Pawn|GetController :self (Variables|GW|GetPianoNPC)))
          (:then
            (GW|Set|BP_GW_NPCController|HasFinal :self c :HasFinal false)
            (GW|Call|BP_GW_NPCController|GoTo :self c :Dest (GW|Call|BP_GW_GameState|PianoSpot :self s))
            (Development|PrintString :InString (cat "GW: NPC " (Utilities|GetDisplayName :Object (Variables|GW|GetPianoNPC)) " walks to the piano") :bPrintToScreen false))
          (:CastFailed))))
    (:CastFailed)))
''', compile_after=False)
write(gm, 'PianoTick', f'''
(fn PianoTick ()
  (bind s {GSC}
    (:then
      (bind npc (Variables|GW|GetPianoNPC))
      (if ({ISVALID} :Object npc)
        (if (< (Math|Vector|Distance2D(Vector) (Transformation|GetActorLocation :self npc) (GW|Call|BP_GW_GameState|PianoSpot :self s)) 220.0)
          (Development|PrintString :InString (cat "GW: NPC " (Utilities|GetDisplayName :Object npc) " lingers by the piano") :bPrintToScreen false)
          (Variables|GW|SetPianoNPC (Variables|GW|GetNoChar))
          (return))
        (if (or (> (CallFunction|Now) (Variables|GW|GetPianoNPCUntil)) (GW|Get|BP_GW_Character|IsDead :self npc))
          (Variables|GW|SetPianoNPC (Variables|GW|GetNoChar)))
        (return))
      (if (<= (Variables|GW|GetNextNPCPiano) 0.0)
        (Variables|GW|SetNextNPCPiano (+ (CallFunction|Now) (Math|Random|RandomFloatinRange 45.0 100.0)))
        (return))
      (if (< (CallFunction|Now) (Variables|GW|GetNextNPCPiano))
        (return))
      (Variables|GW|SetNextNPCPiano (+ (CallFunction|Now) (Math|Random|RandomFloatinRange 70.0 150.0)))
      ; hunt only, not while the piano still rings or the guests panic
      (if (or (!= (GW|Get|BP_GW_GameState|Phase :self s) 2) (or (< (CallFunction|Now) (GW|Get|BP_GW_GameState|PianoNext :self s)) (< (CallFunction|Now) (GW|Get|BP_GW_GameState|PanicUntil :self s))))
        (return))
      (CallFunction|SendNPCToPiano))
    (:CastFailed)))
''', compile_after=False)
compile_bp(gm)
print('BP_GW_GameMode', node_problems(gm))
save(gm)

# ---------------------------------------------------------------- the in-world key prompt (local, never replicated)
kp = load_or_create_bp('BP_GW_KeyPrompt', unreal.Actor)
wc = ensure_component(kp, 'Prompt', unreal.WidgetComponent, 'DefaultSceneRoot')
wc.set_editor_property('space', unreal.WidgetSpace.SCREEN)
wc.set_editor_property('draw_size', unreal.IntPoint(340, 72))
wc.set_editor_property('pivot', unreal.Vector2D(0.5, 0.5))
wc.set_editor_property('widget_class', unreal.load_asset('/Game/GW/UI/WBP_KeyPrompt').generated_class())
wc.set_collision_enabled(unreal.CollisionEnabled.NO_COLLISION)
ensure_fn(kp, 'SetPrompt', inputs=[('Key', 'string'), ('Label', 'string')])
ensure_fn(kp, 'ShowPrompt', inputs=[('On', 'bool')])
ensure_fn(kp, 'Watch')
ensure_var(kp, 'ShownAt', 'float', category='GW')
ensure_var(kp, 'HideIt', 'bool', category='GW')
compile_bp(kp, quiet=True)
cdo(kp).set_editor_property('replicates', False)
write(kp, 'SetPrompt', '''
(fn SetPrompt (Key Label)
  (bind w (Utilities|Casting|CastToWBP_KeyPrompt (GW|Call|/Script/UMG.WidgetComponent|GetUserWidgetObject :self (Variables|Default|GetPrompt)))
    (:then (GW|Call|/Game/GW/UI/WBP_KeyPrompt.WBP_KeyPrompt_C|SetPrompt :self w :Key Key :Label Label))
    (:CastFailed)))
''', compile_after=False)
write(kp, 'ShowPrompt', '''
(fn ShowPrompt (On)
  (if On
    (Variables|GW|SetShownAt (Utilities|Time|GetRealTimeSeconds)))
  (Rendering|SetVisibility :self (Variables|Default|GetPrompt) :bNewVisibility On :bPropagateToChildren false))
''', compile_after=False)
# safety net for every floating prompt (piano, shop, turret, pickups, dance): a prompt its owner stopped refreshing, or one
# more than 9 m from the local player (or with no local player), hides itself. Owners call ShowPrompt every 0.1 s.
write(kp, 'Watch', '''
(fn Watch ()
  (bind wc (Variables|Default|GetPrompt))
  (if (not (GW|Call|/Script/Engine.SceneComponent|IsVisible :self wc))
    (return))
  (Variables|GW|SetHideIt (> (- (Utilities|Time|GetRealTimeSeconds) (Variables|GW|GetShownAt)) 0.6))
  (bind me (Game|GetPlayerPawn :PlayerIndex 0))
  (if (GW|Call|/Script/Engine.KismetSystemLibrary|IsValid :Object me)
    (if (> (Math|Vector|Distance(Vector) (Transformation|GetActorLocation :self me) (Transformation|GetActorLocation)) 900.0)
      (Variables|GW|SetHideIt true))
    (else
      (Variables|GW|SetHideIt true)))
  (if (Variables|GW|GetHideIt)
    (Rendering|SetVisibility :self wc :bNewVisibility false :bPropagateToChildren false)))
''', compile_after=False)
write(kp, 'EventGraph', '''
(event EventBeginPlay
  (Rendering|SetVisibility :self (Variables|Default|GetPrompt) :bNewVisibility false :bPropagateToChildren false))

(event EventTick (DeltaSeconds)
  (CallFunction|Watch))
''', compile_after=False)
compile_bp(kp)
print('BP_GW_KeyPrompt', node_problems(kp))
save(kp)

# ---------------------------------------------------------------- player controller: E, server check, prompt
pc = load_bp('BP_GW_PlayerController')
ensure_var(pc, 'PianoPrompt', obj_class=kp.generated_class(), category='GW')
for f in ('TryShop', 'TryTurret', 'TryDefuse', 'TryPickup', 'TryTalk'):    # bodies: s34_shop.py, s35_turret.py, s38_pickups.py, s39_voice_director.py
    ensure_fn(pc, f, outputs=[('Handled', 'bool')])
ensure_fn(pc, 'InteractOther')
ensure_fn(pc, 'NearPiano', outputs=[('Ok', 'bool')])
ensure_fn(pc, 'NearInstrument', outputs=[('Idx', 'int')])
ensure_fn(pc, 'GWPlay', inputs=[('I', 'int')], exec_fn=True)
ensure_var(pc, 'InstrPrompts', obj_class=unreal.Actor, array=True, category='GW')
ensure_var(pc, 'NoPrompt', obj_class=unreal.Actor, category='GW')
ensure_var(pc, 'NearBest', 'float', category='GW')
ensure_var(pc, 'NearIdx', 'int', category='GW')
ensure_fn(pc, 'RequestInteract')
ensure_fn(pc, 'PianoClientTick')                     # called by EventClientTick (s32_events.py)
ensure_fn(pc, 'GWPiano', exec_fn=True)
compile_bp(pc, quiet=True)
write(pc, 'NearPiano', f'''
(fn NearPiano ()
  (bind ch {MYCH}
    (:then
      (bind s {GSC}
        (:then
          (bind pl (GW|Call|BP_GW_GameState|PianoSpot :self s))
          (bind dz (- (.z (Transformation|GetActorLocation :self ch)) (.z pl)))
          (return (and (not (GW|Get|BP_GW_Character|IsDead :self ch)) (and (< (Math|Vector|Distance2D(Vector) (Transformation|GetActorLocation :self ch) pl) {NEAR}) (< (* dz dz) 62500.0)))))
        (:CastFailed)))
    (:CastFailed)))
''', compile_after=False)
write(pc, 'NearInstrument', f'''
(fn NearInstrument ()
  (Variables|GW|SetNearIdx -1)
  (Variables|GW|SetNearBest {NEAR})
  (bind ch {MYCH}
    (:then
      (if (GW|Get|BP_GW_Character|IsDead :self ch)
        (return -1))
      (bind s {GSC}
        (:then
          (for i (range {len(INSTR)})
            (bind (il iok) (GW|Call|BP_GW_GameState|InstrSpot :self s :I i))
            (bind dz (- (.z (Transformation|GetActorLocation :self ch)) (.z il)))
            (bind d (Math|Vector|Distance2D(Vector) (Transformation|GetActorLocation :self ch) il))
            (if (and (and iok (< (* dz dz) 62500.0)) (< d (Variables|GW|GetNearBest)))
              (Variables|GW|SetNearBest d)
              (Variables|GW|SetNearIdx i)))
          (return (Variables|GW|GetNearIdx)))
        (:CastFailed (return -1))))
    (:CastFailed (return -1))))
''', compile_after=False)
write(pc, 'GWPlay', f'''
(fn GWPlay (I)
  (if (!= (CallFunction|NearInstrument) I)
    (Development|PrintString :InString (cat "GW: instrument " I " refused for " (PlayerState|GetPlayerName :self (GW|Get|/Script/Engine.Controller|PlayerState)) " (too far)") :bPrintToScreen false)
    (return))
  (bind gm {GMC}
    (:then (GW|Call|BP_GW_GameMode|PlayInstrument :self gm :Who (Pawn|GetControlledPawn :self self) :I I))
    (:CastFailed)))
''', compile_after=False)
write(pc, 'RequestInteract', '''
(fn RequestInteract ()
  (Variables|GW|SetNearIdx (CallFunction|NearInstrument))
  (if (>= (Variables|GW|GetNearIdx) 0)
    (if (Networking|HasAuthority)
      (CallFunction|GWPlay :I (Variables|GW|GetNearIdx))
      (else
        (Development|ExecuteConsoleCommand :Command (cat "ServerExec GWPlay " (Variables|GW|GetNearIdx)) :SpecificPlayer self)))
    (return))
  (CallFunction|InteractOther))
''', compile_after=False)
# InteractOther's body is now in s40_inventory.py (TryHold added); this one stands until s40 runs
write(pc, 'InteractOther', '''
(fn InteractOther ()
  (if (CallFunction|TryShop)
    (return))
  (if (CallFunction|TryTurret)
    (return))
  (if (CallFunction|TryPickup)
    (return))
  (if (CallFunction|TryBreaker)
    (return))
  (if (CallFunction|TryDefuse)
    (return))
  ; last: a guest NPC in front of me answers (s39_voice_director.py TryTalk -> GWTalk -> GM.TalkTo)
  (CallFunction|TryTalk))
''', compile_after=False)
write(pc, 'GWPiano', f'''
(fn GWPiano ()
  (if (not (CallFunction|NearPiano))
    (Development|PrintString :InString (cat "GW: piano refused for " (PlayerState|GetPlayerName :self (GW|Get|/Script/Engine.Controller|PlayerState)) " (too far)") :bPrintToScreen false)
    (return))
  (bind gm {GMC}
    (:then (GW|Call|BP_GW_GameMode|PlayPiano :self gm :Who (Pawn|GetControlledPawn :self self)))
    (:CastFailed)))
''', compile_after=False)
write(pc, 'PianoClientTick', f'''
(fn PianoClientTick ()
  (if (not (Pawn|IsLocalPlayerController))
    (return))
  ; never leave early here: this loop is what hides a prompt once the player has walked away, died or become a ghost
  (Variables|GW|SetNearIdx (CallFunction|NearInstrument))
  (bind s {GSC}
    (:then
      (if (== (Utilities|Array|Length (Variables|GW|GetInstrPrompts)) 0)
        (for i (range {len(INSTR)})
          (bind (pl pok) (GW|Call|BP_GW_GameState|InstrSpot :self s :I i))
          (if pok
            (bind a (Game|SpawnActorfromClass :Class "/Game/GW/Blueprints/BP_GW_KeyPrompt.BP_GW_KeyPrompt_C" :SpawnTransform (Math|Transform|MakeTransform :Location (+ pl (Math|Vector|MakeVector 0.0 0.0 130.0))) :CollisionHandlingOverride "AlwaysSpawn"))
            (GW|Call|BP_GW_KeyPrompt|SetPrompt :self a :Key "E" :Label {sel(lambda k: '"' + INSTR[k][3] + '"').replace('(== I ', '(== i ')})
            (Utilities|Array|Add :TargetArray (Variables|GW|GetInstrPrompts) :NewItem a)
            (else
              (Utilities|Array|Add :TargetArray (Variables|GW|GetInstrPrompts) :NewItem (Variables|GW|GetNoPrompt))))))
      (for j (range (Utilities|Array|Length (Variables|GW|GetInstrPrompts)))
        (bind pa (Utilities|Array|Get(acopy) (Variables|GW|GetInstrPrompts) j))
        (if ({ISVALID} :Object pa)
          (bind kp (Utilities|Casting|CastToBP_GW_KeyPrompt pa)
            (:then (GW|Call|BP_GW_KeyPrompt|ShowPrompt :self kp :On (== j (Variables|GW|GetNearIdx))))
            (:CastFailed)))))
    (:CastFailed)))
''', compile_after=False)
compile_bp(pc, quiet=True)
wire_input(pc, 'IA_Interact', {'Started': 'RequestInteract'}, pos=(0, 3200))
compile_bp(pc)
print('BP_GW_PlayerController', node_problems(pc))
save(pc)
