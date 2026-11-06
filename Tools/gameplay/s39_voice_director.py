"""Voice director (VOIX_ARCHITECTURE.md): the one place that decides who says what, when, on the server.

Principles (the user, 2026-11-02 night: "a real party, not a cheap video game"):
- A line is a one-time resource: every recorded sentence is said at most once per server session (GM.VUsed).
  Non-verbal sounds (screams, laughs) may repeat, never one of the last 12 again. A category that runs dry goes
  silent: silence beats repetition. Staff lines (barman, waiter, junkie) are service phrases: unused ones first, then
  reused. The robot's feedback ("cible détectée") may repeat, 10 s apart.
- A voice IS a character (principle 2): an NPC speaks with the voice of the cast character it wears (OutfitIndex ->
  BP_GW_Character.GenIds (s29) -> voice index in GM.VVoiceName) and only that character's lines; bandits by Variant
  (char_bandit / char_bandit2), the kamikaze, the robot, the detective have theirs. A character without recorded
  lines stays silent. Two NPCs wearing the same character never speak at the same time in one listening area.
- Conversations, not barks: ambient talk is mostly a dialogue written for the two characters standing together
  (VDlg* tables, either way round). If the guest's neighbours have none left with it, a guest a few metres away
  whose character has one walks over (WalkOver: Partner + GoTo), and they talk once it has arrived. Turns are timed
  from the clip durations with 0.2-0.55 s gaps; both face each other and hold still. Otherwise a single remark,
  sometimes answered by the neighbour (reply / laugh).
- Only what a player can hear exists: every line is placed around a player (a "listening area", R_AREA). Ambient and
  event speakers are guests within R_SPEAK of a player AND in sight of him (line trace on the Camera channel: walls
  block it, people do not): his room or the doorway. Elsewhere nobody talks.
- Priorities per area: P0 death scream, P1 alarm (at most 2 shouts + 1 bystander scream per area per 12 s), P2 event
  lines (one every 6-9 s per area), P3 calm-down after a panic, P4 ambient (one conversation at a time, then 15-25 s of
  silence), P5 reactions / a guest talking to an NPC (only when nothing else plays nearby). A P0-P2 line drops the
  lower queued lines around it (a dialogue's remaining turns go) and fades out lower lines being spoken (Cue 9999).
- Cause-matched shouts: the panic's cause (gun / fire / explosion / blackout / generic) comes from StartPanicCause or
  SetPanicCause, else is inferred: GunContext or a gunshot / laser / turret sound just now, an explosion sound just
  now, the fire event or a fire sound, the blackout. A burning victim's neighbours shout about fire. A line tagged
  with another cause is never picked, gun lines only with the gun cause; players far from the cause (> 18 m) only hear
  generic shouts (they heard a noise, they saw nothing).
- E on a guest (PC.TryTalk -> GWTalk -> GM.TalkTo): the player's own character speaks in its voice (a greeting, then
  "greet_again", then a remark, then a laugh), the NPC stops, turns and usually answers. NPC pairs start the very same
  exchange by themselves (GreetTick), so a conversation proves nothing. Detectives get nothing (no test).
- Reflexes: living disguised players are candidates like any guest for shouts, screams and reactions (Talkable Moving
  true), never for ambient conversations (Moving false).
- The kamikaze says none of his lines any more: he only shouts the alarm loop (BP_GW_KamiAlarm, s43_feedback6.py). Bandits taunt during the attack every 12-18 s.
- No subtitles (removed on request, 2026-11-04): voices are audio only.

Server log: "GW: VOX t= pri= cat= cause= conv= idx= dur= voice= svoice= nv= gun= test= kind= pd= loc= spk= text=" for
every line, VOXCONV / VOXWALK / VOXCUT / VOXDROP / VOXCAUSE / VOXTALK / VOXDRY, VOXP (player positions, test only).
Tools/qa/voice_log_check.py checks a log. Headless test: -GWVoiceTestA / B / C (VoiceTestTick: three ~4 min scripted
rounds: rooms, events, deaths, talks) and -GWVoiceFakeBank (test-only lines, imported by `s31_reactions.py fakebank`).

Usage: ue_run.py s39_voice_director.py   (s31_reactions.py runs it at its end, so a re-run of s31 keeps the director)
"""
import sys, importlib
sys.path.insert(0, r'J:\Projets\Unreal_Projects\Guess Who\Tools\gameplay')
import gw_lib; importlib.reload(gw_lib)
from gw_lib import *
import voice_bank as VB; importlib.reload(VB)

try:
    UE_ARGS
except NameError:
    UE_ARGS = []
REP = unreal.BlueprintVariableReplication
V3 = unreal.Vector.static_struct()
CAT = VB.CAT
NCAT = VB.NCAT
CHAR = '"/Game/GW/Blueprints/BP_GW_Character.BP_GW_Character_C"'
NPCC = '"/Game/GW/Blueprints/BP_GW_NPCController.BP_GW_NPCController_C"'
CUE = '/Game/GW/Blueprints/BP_GW_SoundCue.BP_GW_SoundCue_C'
ISVALID = 'GW|Call|/Script/Engine.KismetSystemLibrary|IsValid'
GSC = '(Utilities|Casting|CastToBP_GW_GameState (Game|GetGameState))'
GMC = '(Utilities|Casting|CastToBP_GW_GameMode (Game|GetGameMode))'
MYCH = '(Utilities|Casting|CastToBP_GW_Character (Pawn|GetControlledPawn :self self))'
NOW = '(CallFunction|Now)'
STOP = 9999                                  # Cue index meaning "stop talking" (fade out)

# ---------------------------------------------------------------- tuning (cm, s)
R_AREA = 1300.0        # a listening area: what a player hears around him (ATT_GW_Voice: 3.5 m full, 13 m falloff)
R_SPEAK = 1000.0       # ambient / event speakers stand within 10 m of a player, in sight
R_SHOUT = 1100.0
R_WALK = 900.0         # a guest this far may walk over for a conversation
FAR_CAUSE = 1800.0     # beyond this the player only heard a noise: generic shouts
P_DIALOGUE = 0.7
AMB_GAP = (15.0, 25.0)
EV_GAP = (6.0, 9.0)
KAMI_GAP = (7.0, 10.0)
ROBOT_GAP = (10.0, 14.0)
BANDIT_GAP = (12.0, 18.0)
TALK_RANGE = 260.0
# the last key is the fallback of EVCAT_X: zombies (6) used to fall through to the robot's lines. There are no zombie lines and no new voices: generic
# panic shouts about no cause in particular (the user, 2026-11-05)
EVCAT = {1: CAT['attack_guest'], 2: CAT['fire'], 3: CAT['blackout'], 4: CAT['kamikaze_guest'], 6: CAT['shout'], 5: CAT['robot_guest']}
EVCAUSE = {1: 1, 2: 2, 3: 4, 4: 0, 6: 0, 5: 0}

AG = lambda arr, i, cat='Voice': f'(Utilities|Array|Get(acopy) (Variables|{cat}|Get{arr}) {i})'
ADD = lambda arr, v, cat='Voice': f'(Utilities|Array|Add :TargetArray (Variables|{cat}|Get{arr}) :NewItem {v})'
SETE = lambda arr, i, v, cat='Voice': f'(Utilities|Array|SetArrayElem :TargetArray (Variables|{cat}|Get{arr}) :Index {i} :Item {v} :bSizeToFit false)'
DEL = lambda arr, i, cat='Voice': f'(Utilities|Array|RemoveIndex :TargetArray (Variables|{cat}|Get{arr}) :IndexToRemove {i})'
LEN = lambda arr, cat='Voice': f'(Utilities|Array|Length (Variables|{cat}|Get{arr}))'
V = lambda n: f'(Variables|Voice|Get{n})'
SV = lambda n, v: f'(Variables|Voice|Set{n} {v})'
L = lambda n: f'(Variables|Default|Get{n})'
SL = lambda n, v: f'(Variables|Default|Set{n} {v})'
CH = lambda var, o: f'(GW|Get|BP_GW_Character|{var} :self {o})'
CHS = lambda var, o, v: f'(GW|Set|BP_GW_Character|{var} :self {o} :{var} {v})'
LOC = lambda o: f'(Transformation|GetActorLocation :self {o})'
HEAD = lambda o: f'(+ (Transformation|GetActorLocation :self {o}) (Math|Vector|MakeVector 0.0 0.0 60.0))'
DIST = lambda a, b: f'(Math|Vector|Distance(Vector) {a} {b})'
RF = lambda a, b: f'(Math|Random|RandomFloatinRange {float(a)} {float(b)})'
NOCHAR = '(Variables|GW|GetNoChar)'
CUE_SET = lambda o, idx: CHS('Cue', o, f'(+ (* (+ (/ {CH("Cue", o)} 10000) 1) 10000) {idx})')
VNAME = lambda v: f'(select (>= {v} 0) {AG("VVoiceName", f"(Math|Integer|Max(Integer) {v} 0)")} "-")'
VOICEOF = lambda o: f'(CallFunction|VoiceOf :Ch {o})'


def log(expr):
    return f'(Development|PrintString :InString {expr} :bPrintToScreen false)'


ch = load_bp('BP_GW_Character')
chc = ch.generated_class()
gm = load_bp('BP_GW_GameMode')
gs = load_bp('BP_GW_GameState')
pc = load_bp('BP_GW_PlayerController')

# ================================================================ character: voice cache, mouth
for v, t in (('VoiceId', 'int'), ('VoiceKey', 'int'), ('TalkUntil', 'float'), ('TalkedAt', 'float'), ('TalkStep', 'int'),
             ('GestureOn', 'bool')):
    ensure_var(ch, v, t, category='Voice')
ensure_var(ch, 'TalkNPC', obj_class=chc, category='Voice')
ensure_var(ch, 'CueComp', obj_class=unreal.AudioComponent, category='Voice')
ensure_var(ch, 'GenIds', 'string', array=True, category='Costume')    # s29_gen_chars.py: char_id of each cast index
ensure_var(ch, 'Cue', 'int', rep=REP.REP_NOTIFY, category='GW')
ensure_fn(ch, 'OnRep_Cue')
# subtitles removed for good (2026-11-04): drop what earlier versions left in the assets
if 'Subtitle' in graph_names(ch):
    BT.remove_function_graph(ch, 'Subtitle')
for _bp, _v in ((ch, 'SubText'), (gs, 'BankText')):
    if _v in [str(x) for x in BT.list_variables(_bp)]:
        BT.remove_variable(_bp, _v)
ensure_var(gs, 'TenseUntil', 'float', rep=REP.REPLICATED, category='GW')   # server time: tense music after a gunshot (u14 MusicTick)
ensure_var(gs, 'BankVox', 'int', array=True, category='Audio')          # 1: a voice line (one mouth)
compile_bp(gs, quiet=True)
compile_bp(ch, quiet=True)
cdo(ch).set_editor_property('VoiceId', -1)
cdo(ch).set_editor_property('TalkedAt', -100.0)

# the music ducks under the panic / event voices heard nearby (P0-P2, GameState.BankVox = 2): a self-expiring mix,
# pushed again by every such line (UE restarts its duration), multiplied with the player's own volume settings
DUCK = '/Game/GW/Audio/SM_GW_Duck.SM_GW_Duck'
_AT = unreal.AssetToolsHelpers.get_asset_tools()
if not unreal.EditorAssetLibrary.does_asset_exist('/Game/GW/Audio/SM_GW_Duck'):
    _AT.create_asset('SM_GW_Duck', '/Game/GW/Audio', unreal.SoundMix, unreal.SoundMixFactory())
_mix = unreal.load_asset('/Game/GW/Audio/SM_GW_Duck')
try:
    _adj = unreal.SoundClassAdjuster()
    _adj.set_editor_property('sound_class_object', unreal.load_asset('/Game/GW/Audio/Classes/SC_GW_Music'))
    _adj.set_editor_property('volume_adjuster', 0.45)
    _adj.set_editor_property('pitch_adjuster', 1.0)
    _mix.set_editor_property('sound_class_effects', [_adj])
    for _k, _v in (('fade_in_time', 0.35), ('duration', 3.0), ('fade_out_time', 2.5)):
        _mix.set_editor_property(_k, _v)
    unreal.EditorAssetLibrary.save_loaded_asset(_mix, False)
except Exception as _e:
    print('SM_GW_Duck setup failed:', _e)

CHW = {
    # one mouth: a new voice line fades the previous one out; STOP only fades. Sound effects (robot steps) just play.
    'OnRep_Cue': f'''
(fn OnRep_Cue ()
  (bind i (% (Variables|GW|GetCue) 10000))
  (if (== i {STOP})
    (if ({ISVALID} :Object (Variables|Voice|GetCueComp))
      (GW|Call|/Script/Engine.AudioComponent|FadeOut :self (Variables|Voice|GetCueComp) :FadeOutDuration 0.25 :FadeVolumeLevel 0.0))
    (return))
  (bind s {GSC}
    (:then
      (bind snds (GW|Get|BP_GW_GameState|BankSounds :self s))
      (bind vox (GW|Get|BP_GW_GameState|BankVox :self s))
      ; QA: what this machine really plays (-GWEvTest)
      (if (Utilities|HasLaunchOption :OptionToCheck "GWEvTest")
        (if (and (>= i 0) (< i (Utilities|Array|Length snds)))
          {log('(cat "GW: CUEPLAY t=" (Utilities|Time|GetGameTimeinSeconds) " by=" (Utilities|GetDisplayName :Object self) " kind=" (Variables|GW|GetKind) " sound=" (Utilities|GetDisplayName :Object (Utilities|Array|Get(acopy) snds i)))')}))
      (if (and (>= i 0) (< i (Utilities|Array|Length snds)))
        (if (and (< i (Utilities|Array|Length vox)) (>= (Utilities|Array|Get(acopy) vox i) 1))
          (if (== (Utilities|Array|Get(acopy) vox i) 2)
            (bind me (Game|GetPlayerPawn :PlayerIndex 0))
            (if ({ISVALID} :Object me)
              (if (< (Math|Vector|Distance(Vector) (Transformation|GetActorLocation :self me) (Transformation|GetActorLocation :self self)) 1600.0)
                (Audio|PushSoundMixModifier :InSoundMixModifier "{DUCK}"))))
          (if ({ISVALID} :Object (Variables|Voice|GetCueComp))
            (GW|Call|/Script/Engine.AudioComponent|FadeOut :self (Variables|Voice|GetCueComp) :FadeOutDuration 0.12 :FadeVolumeLevel 0.0))
          (Variables|Voice|SetCueComp (Audio|SpawnSoundAttached :Sound (Utilities|Array|Get(acopy) snds i) :AttachToComponent (Variables|Character|GetMesh) :AttachPointName "head" :LocationType "SnapToTarget" :bStopWhenAttachedToDestroyed true))
          (else
            (Audio|SpawnSoundAttached :Sound (Utilities|Array|Get(acopy) snds i) :AttachToComponent (Variables|Character|GetMesh) :AttachPointName "head" :LocationType "SnapToTarget" :bStopWhenAttachedToDestroyed true)))))
    (:CastFailed)))
''',
}

# ================================================================ game mode: state
for v, t in (('VInit', 'bool'), ('VTestMode', 'bool'), ('VConv', 'int'), ('VNextAmb', 'float'), ('VNextEv', 'float'),
             ('VNextClean', 'float'), ('VNextGreet', 'float'), ('VNextLog', 'float'), ('VKamiNext', 'float'), ('VRobotNext', 'float'),
             ('VBanditNext', 'float'), ('VLastGun', 'float'), ('VLastBoom', 'float'), ('VLastFire', 'float'),
             ('VCauseSet', 'int'), ('VCauseAt', 'float'), ('VQL', 'int'), ('VQP', 'int'), ('VQK', 'int'), ('VQCat', 'int'),
             ('VTestChecked', 'bool'), ('VTestOn', 'bool'), ('VTestStep', 'int'), ('VTestNext', 'float'),
             ('VAmbCode', 'int'), ('VLines', 'int'), ('VPendCode', 'int'), ('VPendUntil', 'float'), ('VTestPart', 'int'),
             ('VSfxLogAt', 'float')):
    ensure_var(gm, v, t, category='Voice')
for v in ('VQC', 'VAmbA', 'VAmbB', 'VTmpC', 'VPendA', 'VPendB'):
    ensure_var(gm, v, obj_class=chc, category='Voice')
ensure_var(gm, 'VPl', obj_class=unreal.Pawn, array=True, category='Voice')
for v in ('VQChar', 'VAChar'):
    ensure_var(gm, v, obj_class=chc, array=True, category='Voice')
ensure_var(gm, 'VALoc', struct=V3, array=True, category='Voice')
for v in ('VQTime', 'VAStart', 'VAEnd', 'VAHold', 'VUsed', 'VBDur'):
    ensure_var(gm, v, 'float', array=True, category='Voice')
for v in ('VQLine', 'VQCats', 'VQPri', 'VQConv', 'VQVoice', 'VAPri', 'VACat', 'VAVoice', 'VBVoice', 'VBDlg', 'VBTurn',
          'VBSpk', 'VBCause', 'VBNV', 'VBTest', 'VBWh', 'VCatFirst', 'VCatCount', 'VCatOnce', 'VCatPri', 'VCatVoice',
          'VVoiceFem', 'VDlgFirst', 'VDlgN', 'VDlgVA', 'VDlgVB', 'VPairStart', 'VPairCount', 'VPairCode', 'VBCtx', 'VCVFirst', 'VCVCount'):
    ensure_var(gm, v, 'int', array=True, category='Voice')
for v in ('VBText', 'VVoiceName'):
    ensure_var(gm, v, 'string', array=True, category='Voice')
for v, t in (('BankCat', 'int'), ('BankFem', 'int'), ('BankGun', 'int'), ('LastSaid', 'int')):
    ensure_var(gm, v, t, array=True, category='GW')
ensure_var(gm, 'NoChar', obj_class=chc, category='GW')
ensure_var(gm, 'GunContext', 'bool', category='GW')
ensure_var(gm, 'PanicCalmAt', 'float', category='GW')
ensure_var(gm, 'Stamp', 'int', category='GW')

SIG = {
    # existing names other scripts call (keep them)
    'PickSound': ([('Cat', 'int'), ('Fem', 'int')], [('Idx', 'int')]),
    'GenderOf': ([('Ch', chc)], [('Fem', 'int')]),
    'Say': ([('Ch', chc), ('Cat', 'int')], []),
    'QueueSay': ([('Ch', chc), ('Cat', 'int'), ('Delay', 'float')], []),
    'WorldSound': ([('Cat', 'int'), ('Loc', V3)], []),
    'StartPanic': ([('Loc', V3), ('Dur', 'float')], []),
    'SayNearPlayers': ([('Cat', 'int'), ('PerPlayer', 'int'), ('Delay', 'float'), ('Spread', 'float')], []),
    'DeathCry': ([('Victim', chc)], []),
    'ProcessCue': ([], []), 'PanicTick': ([], []), 'ChatterTick': ([], []),
    # the director
    'VoiceInit': ([], []), 'PlayerPawns': ([], []), 'VoiceClean': ([], []), 'AmbientTick': ([], []),
    'EventVoiceTick': ([], []), 'PlayQueued': ([], []), 'VoiceTestTick': ([], []), 'VoiceTestLog': ([], []),
    'PendingTick': ([], []),
    'VoiceOf': ([('Ch', chc)], [('V', 'int')]),
    'NearPlayerD': ([('Loc', V3)], [('D', 'float')]),
    'SeeFrom': ([('A', V3), ('B', V3)], [('Ok', 'bool')]),
    'BusyNear': ([('Loc', V3), ('R', 'float'), ('MaxPri', 'int')], [('Ok', 'bool')]),
    'HoldNear': ([('Loc', V3), ('R', 'float'), ('MaxPri', 'int')], [('Ok', 'bool')]),
    'VoiceBusyNear': ([('Loc', V3), ('R', 'float'), ('V', 'int')], [('Ok', 'bool')]),
    'VoiceRecentNear': ([('Loc', V3), ('R', 'float'), ('V', 'int'), ('Since', 'float')], [('Ok', 'bool')]),
    'CountCat': ([('Loc', V3), ('R', 'float'), ('Cat', 'int'), ('Since', 'float')], [('N', 'int')]),
    'LineScore': ([('I', 'int'), ('Cause', 'int'), ('Fem', 'int'), ('Cur', 'int'), ('Once', 'int'), ('Special', 'bool'),
                   ('Test', 'bool'), ('Ctx', 'int')], [('S', 'int')]),
    'SocialModeOf': ([('Ch', chc)], [('M', 'int')]),
    'Gesture': ([('Ch', chc), ('Id', 'int')], []),
    'GestureTick': ([], []),
    'SoundScore': ([('I', 'int'), ('Fem', 'int'), ('Once', 'int'), ('Test', 'bool')], [('S', 'int')]),
    'PickLine': ([('Cat', 'int'), ('Ch', chc), ('Cause', 'int')], [('Idx', 'int')]),
    'Commit': ([('Ch', chc), ('Idx', 'int')], []),
    'Uncommit': ([('Idx', 'int')], []),
    'Utter': ([('Ch', chc), ('Idx', 'int'), ('Pri', 'int'), ('Conv', 'int')], []),
    'Schedule': ([('Ch', chc), ('Idx', 'int'), ('Pri', 'int'), ('At', 'float'), ('Conv', 'int'), ('Cat', 'int')], []),
    'DropConv': ([('Conv', 'int')], []),
    'Hush': ([('Loc', V3), ('R', 'float'), ('Pri', 'int'), ('Except', chc)], []),
    'HoldAt': ([('Loc', V3), ('Secs', 'float')], []),
    'Block': ([('Ch', chc), ('Until', 'float'), ('Hold', 'float'), ('Pri', 'int')], []),
    'Talkable': ([('Ch', chc), ('Moving', 'bool')], [('Ok', 'bool')]),
    'FreeToWalk': ([('Ch', chc)], [('Ok', 'bool')]),
    'FindSpeaker': ([('Loc', V3), ('MaxD', 'float'), ('Moving', 'bool')], [('Ch', chc)]),
    'FindPartner': ([('A', chc)], [('Ch', chc)]),
    'NearestTalker': ([('Loc', V3), ('MaxD', 'float')], [('Ch', chc)]),
    'SpecialNear': ([('Kind', 'int'), ('Loc', V3), ('R', 'float')], [('Ch', chc)]),
    'PickDialogue': ([('A', chc), ('B', chc)], [('Code', 'int')]),
    'StartDialogue': ([('A', chc), ('B', chc), ('Code', 'int')], []),
    'DialogueBeside': ([('A', chc)], [('Ok', 'bool')]),
    'WalkOver': ([('A', chc), ('PL', V3)], [('Ok', 'bool')]),
    'SendTo': ([('B', chc), ('A', chc)], []),
    'StartRemark': ([('A', chc)], [('Ok', 'bool')]),
    'AmbientWith': ([('PL', V3), ('A', chc)], []),
    'AmbientNudge': ([('Ch', chc)], []),
    'HoldNPC': ([('Ch', chc), ('Until', 'float'), ('Face', V3), ('Stop', 'bool')], []),
    'AreaLines': ([('PL', V3), ('Cat', 'int'), ('Pri', 'int'), ('N', 'int'), ('Delay', 'float'), ('Spread', 'float'),
                   ('Cause', 'int')], [('K', 'int')]),
    'AlarmShouts': ([('Loc', V3), ('Cause', 'int'), ('Scream', 'bool')], []),
    'CauseNow': ([], [('C', 'int')]),
    'SetPanicCause': ([('Cause', 'int')], []),
    'StartPanicCause': ([('Loc', V3), ('Dur', 'float'), ('Cause', 'int')], []),
    'SayNow': ([('Ch', chc), ('Cat', 'int'), ('Pri', 'int')], []),
    'CatPri': ([('Cat', 'int')], [('P', 'int')]),
    'TalkTo': ([('Who', chc), ('Ch', chc)], []),
    'GreetLine': ([('Ch', chc), ('St', 'int')], [('Idx', 'int')]),
    'GreetExchange': ([('A', chc), ('B', chc), ('St', 'int'), ('Reply', 'bool')], [('Ok', 'bool')]),
    'GreetPartner': ([('A', chc)], [('Ch', chc)]),
    'GreetTick': ([], []),
    'VoiceTestAim': ([('MaxD', 'float')], [('Ch', chc)]),
    'DevVoiceChat': ([('Loc', V3)], []),
    'StaffSay': ([('Cat', 'int'), ('Ctx', 'int'), ('Loc', V3)], [('Idx', 'int')]),
    'DevVoiceState': ([], []),
}
for f, (i, o) in SIG.items():
    ensure_fn(gm, f, inputs=i, outputs=o)
compile_bp(gm, quiet=True)

LOCALS = {
    'VoiceInit': [('N', 'int')],
    'VoiceOf': [('Key', 'int'), ('Vi', 'int')],
    'NearPlayerD': [('BestD', 'float')],
    'CountCat': [('Cnt', 'int')],
    'PickLine': [('Best', 'int'), ('Picks', 'int[]')],
    'PickSound': [('Best', 'int'), ('Picks', 'int[]'), ('Pick', 'int')],
    'Hush': [('N', 'int'), ('Drops', 'int[]'), ('Hit', 'bool')],
    'DropConv': [('N', 'int'), ('Unheard', 'bool')],
    'VoiceClean': [('N', 'int')],
    'FindSpeaker': [('Cands', 'char[]'), ('Cands2', 'char[]')],
    'FindPartner': [('BestD', 'float'), ('BestT', 'char')],
    'NearestTalker': [('BestD', 'float'), ('BestT', 'char')],
    'SpecialNear': [('BestD', 'float'), ('BestT', 'char')],
    'PickDialogue': [('Picks', 'int[]')],
    'DialogueBeside': [('Code', 'int')],
    'WalkOver': [('Code', 'int'), ('BestD', 'float'), ('BestT', 'char'), ('BestC', 'int')],
    'StartDialogue': [('T', 'float'), ('Sp', 'char')],
    'StartRemark': [('T', 'float'), ('I', 'int'), ('J', 'int'), ('B', 'char')],
    'AreaLines': [('T', 'float'), ('Got', 'int'), ('Done', 'bool'), ('Sp', 'char'), ('I', 'int')],
    'AlarmShouts': [('I', 'int'), ('Sc', 'char'), ('Have', 'int')],
    'DeathCry': [('I', 'int'), ('Cause', 'int')],
    'SayNow': [('I', 'int')],
    'TalkTo': [('I', 'int'), ('J', 'int'), ('B', 'char'), ('Step', 'int')],
    'AmbientWith': [('B', 'char')],
    'GreetLine': [('I', 'int')],
    'GreetExchange': [('I', 'int'), ('J', 'int')],
    'GreetPartner': [('BestD', 'float'), ('BestT', 'char')],
    'GreetTick': [('A', 'char'), ('B', 'char'), ('H', 'float')],
    'StartPanic': [('Cause', 'int')],
    'EventVoiceTick': [('Bd', 'char'), ('I', 'int')],
    'PendingTick': [('Code', 'int'), ('Ap', 'char'), ('Bp', 'char'), ('Quit', 'bool')],
    'VoiceTestAim': [('BestT', 'char')],
    'VoiceTestTick': [('Tc', 'char')],
    'DevVoiceState': [('N', 'int'), ('U', 'int'), ('D', 'int')],
    'StaffSay': [('Best', 'int'), ('Picks', 'int[]')],
}


def add_locals(bp, table):
    for fn, locs in table.items():
        g = get_graph(bp, fn)
        have = [str(x) for x in BT.list_variables(bp, g)]
        for n, t in locs:
            if n in have:
                continue
            arr = t.endswith('[]')
            t0 = t[:-2] if arr else t
            cont = gw_lib.ContainerType.ARRAY if arr else None
            if t0 == 'char':
                BT.add_object_variable(bp, n, chc, graph=g, container_type=cont)
            else:
                BT.add_variable(bp, n, t0, graph=g, container_type=cont)


add_locals(gm, LOCALS)

# ---------------------------------------------------------------- class defaults: category tables
cat_once, cat_pri, cat_voice = [0] * NCAT, [5] * NCAT, [0] * NCAT
for name, cid in CAT.items():
    if cid >= NCAT:
        continue
    voice = cid in VB.VOICE_CATS
    cat_voice[cid] = 1 if voice else 0
    if voice:
        cat_once[cid] = 0 if name in VB.NONVERBAL_CATS or name in VB.REPEAT_CATS else 2 if name in VB.STAFF_CATS else 1
    cat_pri[cid] = VB.PRI.get(name, 5)
d = cdo(gm)
d.set_editor_property('VCatOnce', cat_once)
d.set_editor_property('VCatPri', cat_pri)
d.set_editor_property('VCatVoice', cat_voice)
d.set_editor_property('VCauseSet', -1)

# ================================================================ game mode: functions
TALKABLE = lambda o: f'(CallFunction|Talkable :Ch {o} :Moving false)'
QARRS = ('VQTime', 'VQChar', 'VQLine', 'VQPri', 'VQConv', 'VQCats', 'VQVoice')
AARRS = ('VAChar', 'VALoc', 'VAStart', 'VAEnd', 'VAHold', 'VAPri', 'VACat', 'VAVoice')
QDEL = lambda i: '\n'.join(f'      {DEL(a, i)}' for a in QARRS)
ADEL = lambda i: '\n'.join(f'      {DEL(a, i)}' for a in AARRS)
W = {}
W['VoiceInit'] = f'''
(fn VoiceInit ()
  (Variables|Voice|SetVInit true)
  (Variables|Voice|SetVTestMode (Utilities|HasLaunchOption :OptionToCheck "GWVoiceFakeBank"))
  (Utilities|Array|Clear (Variables|Voice|GetVUsed))
  {SL('N', LEN('BankCat', 'GW'))}
  (for i (range {L('N')})
    {ADD('VUsed', '0.0')})
  {log('(cat "GW: VOXINIT lines=" (Utilities|Array|Length (Variables|GW|GetBankCat)) " voices=" (Utilities|Array|Length (Variables|Voice|GetVVoiceName)) " dialogues=" (Utilities|Array|Length (Variables|Voice|GetVDlgFirst)) " fakebank=" (Variables|Voice|GetVTestMode))')})
'''
# the voice of the character this pawn wears (cached while its look does not change); -1: no recorded voice
W['VoiceOf'] = f'''
(fn VoiceOf (Ch)
  (if (not ({ISVALID} :Object Ch))
    (return -1))
  (bind kind {CH('Kind', 'Ch')})
  (bind oi {CH('OutfitIndex', 'Ch')})
  {SL('Key', f"(+ (+ (+ 1 (* kind 100000)) (* {CH('Variant', 'Ch')} 10000)) (+ (select {CH('IsSeeker', 'Ch')} 5000 0) (+ oi 1)))")}
  (if (== {L('Key')} {CH('VoiceKey', 'Ch')})
    (return {CH('VoiceId', 'Ch')}))
  (bind names (Variables|Voice|GetVVoiceName))
  (bind ids {CH('GenIds', 'Ch')})
  (if (== kind 1)
    {SL('Vi', '(Utilities|Array|FindItem :TargetArray names :ItemToFind (select (== ' + CH('Variant', 'Ch') + ' 1) "char_bandit2" "char_bandit"))')}
    (elif (== kind 2)
      {SL('Vi', '(Utilities|Array|FindItem :TargetArray names :ItemToFind "char_kamikaze")')}
      (elif (== kind 3)
        {SL('Vi', '(Utilities|Array|FindItem :TargetArray names :ItemToFind "char_robot")')}
        (elif {CH('IsSeeker', 'Ch')}
          {SL('Vi', '(Utilities|Array|FindItem :TargetArray names :ItemToFind "char_detective")')}
          (elif (and (>= oi 0) (< oi (Utilities|Array|Length ids)))
            {SL('Vi', '(Utilities|Array|FindItem :TargetArray names :ItemToFind (Utilities|Array|Get(acopy) ids oi))')}
            (else
              {SL('Vi', '-1')}))))))
  {CHS('VoiceKey', 'Ch', L('Key'))}
  {CHS('VoiceId', 'Ch', L('Vi'))}
  (return {L('Vi')}))
'''
W['SocialModeOf'] = '''
(fn SocialModeOf (Ch)
  (bind c (Utilities|Casting|CastToBP_GW_NPCController (Pawn|GetController :self Ch))
    (:then (return (select (== (GW|Get|BP_GW_NPCController|SocialMode :self c) 3) 0 (GW|Get|BP_GW_NPCController|SocialMode :self c))))
    (:CastFailed (return 0))))
'''
# conversation body loops of s36 on the replicated DanceId (6 talking, 7 listening, 8 laughing): only for guests
# standing still outside a social group (those are s36's), and only once those loops exist (DanceAnims >= 8)
W['Gesture'] = f'''
(fn Gesture (Ch Id)
  (if (not ({ISVALID} :Object Ch))
    (return))
  (if (or (or (Pawn|IsPlayerControlled :self Ch) (!= {CH('Kind', 'Ch')} 0)) (GW|Get|BP_GW_Character|IsDead :self Ch))
    (return))
  (if (< (Utilities|Array|Length {CH('DanceAnims', 'Ch')}) 8)
    (return))
  (if (or (> (Math|Vector|VectorLength (Transformation|GetVelocity :self Ch)) 40.0) (!= (CallFunction|SocialModeOf :Ch Ch) 0))
    (return))
  (if (and (!= {CH('DanceId', 'Ch')} 0) (not {CH('GestureOn', 'Ch')}))
    (return))
  {CHS('DanceId', 'Ch', 'Id')}
  {CHS('GestureOn', 'Ch', 'true')})
'''
W['GestureTick'] = f'''
(fn GestureTick ()
  (bind now {NOW})
  (for c (Actor|GetAllActorsOfClass :ActorClass {CHAR})
    (if {CH('GestureOn', 'c')}
      (if (or (or (< {CH('TalkUntil', 'c')} now) (GW|Get|BP_GW_Character|IsDead :self c)) (!= (CallFunction|SocialModeOf :Ch c) 0))
        {CHS('GestureOn', 'c', 'false')}
        (if (and (>= {CH('DanceId', 'c')} 6) (<= {CH('DanceId', 'c')} 8))
          {CHS('DanceId', 'c', '0')})))))
'''
W['PlayerPawns'] = f'''
(fn PlayerPawns ()
  (Utilities|Array|Clear (Variables|Voice|GetVPl))
  (for ps (CallFunction|GetGWPlayers)
    (bind p (PlayerState|GetPawn :self ps))
    (if ({ISVALID} :Object p)
      {ADD('VPl', 'p')})))
'''
W['NearPlayerD'] = f'''
(fn NearPlayerD (Loc)
  {SL('BestD', '1000000.0')}
  (for p (Variables|Voice|GetVPl)
    (if ({ISVALID} :Object p)
      (bind d {DIST(LOC('p'), 'Loc')})
      (if (< d {L('BestD')})
        {SL('BestD', 'd')})))
  (return {L('BestD')}))
'''
W['SeeFrom'] = '''
(fn SeeFrom (A B)
  (bind (hit ok) (Collision|LineTraceByChannel :Start A :End B :TraceChannel "Camera" :bTraceComplex false :bIgnoreSelf true))
  (return (not ok)))
'''
# something of priority <= MaxPri playing or queued around Loc
W['BusyNear'] = f'''
(fn BusyNear (Loc R MaxPri)
  (bind now {NOW})
  (for i (range {LEN('VAEnd')})
    (if (and (> {AG('VAEnd', 'i')} now) (<= {AG('VAPri', 'i')} MaxPri))
      (if (< {DIST(AG('VALoc', 'i'), 'Loc')} R)
        (return true))))
  (for j (range {LEN('VQTime')})
    (if (<= {AG('VQPri', 'j')} MaxPri)
      (bind qc {AG('VQChar', 'j')})
      (if ({ISVALID} :Object qc)
        (if (< {DIST(LOC('qc'), 'Loc')} R)
          (return true)))))
  (return false))
'''
# a recent line's "after" time still running around Loc (ambient: a conversation and its silence; events: 6-9 s)
W['HoldNear'] = f'''
(fn HoldNear (Loc R MaxPri)
  (bind now {NOW})
  (for i (range {LEN('VAHold')})
    (if (and (> {AG('VAHold', 'i')} now) (<= {AG('VAPri', 'i')} MaxPri))
      (if (< {DIST(AG('VALoc', 'i'), 'Loc')} R)
        (return true))))
  (return false))
'''
# this voice already speaks (or is about to) around Loc: two NPCs wearing the same character never talk at once
W['VoiceBusyNear'] = f'''
(fn VoiceBusyNear (Loc R V)
  (bind now {NOW})
  (for i (range {LEN('VAEnd')})
    (if (and (> {AG('VAEnd', 'i')} now) (== {AG('VAVoice', 'i')} V))
      (if (< {DIST(AG('VALoc', 'i'), 'Loc')} R)
        (return true))))
  (for j (range {LEN('VQTime')})
    (if (== {AG('VQVoice', 'j')} V)
      (bind qc {AG('VQChar', 'j')})
      (if ({ISVALID} :Object qc)
        (if (< {DIST(LOC('qc'), 'Loc')} R)
          (return true)))))
  (return false))
'''
W['CountCat'] = f'''
(fn CountCat (Loc R Cat Since)
  {SL('Cnt', '0')}
  (for i (range {LEN('VAStart')})
    (if (and (>= {AG('VAStart', 'i')} Since) (== {AG('VACat', 'i')} Cat))
      (if (< {DIST(AG('VALoc', 'i'), 'Loc')} R)
        {SL('Cnt', f"(+ {L('Cnt')} 1)")})))
  (for j (range {LEN('VQTime')})
    (if (== {AG('VQCats', 'j')} Cat)
      (bind qc {AG('VQChar', 'j')})
      (if ({ISVALID} :Object qc)
        (if (< {DIST(LOC('qc'), 'Loc')} R)
          {SL('Cnt', f"(+ {L('Cnt')} 1)")}))))
  (return {L('Cnt')}))
'''
W['CatPri'] = f'''
(fn CatPri (Cat)
  (if (or (< Cat 0) (>= Cat {LEN('VCatPri')}))
    (return 5))
  (return {AG('VCatPri', 'Cat')}))
'''
# score of bank line I for a speaker of voice Cur (0: not allowed): its own voice only; about this very cause +8;
# never said +1 (staff); non-verbal: its own voice +4, else the right gender
W['LineScore'] = f'''
(fn LineScore (I Cause Fem Cur Once Special Test Ctx)
  (if (and (not Test) (== {AG('VBTest', 'I')} 1))
    (return 0))
  (bind nv (== {AG('VBNV', 'I')} 1))
  (bind used (> {AG('VUsed', 'I')} 0.0))
  (if (and used (and (not nv) (== Once 1)))
    (return 0))
  (if (and nv (Utilities|Array|ContainsItem :TargetArray (Variables|GW|GetLastSaid) :ItemToFind I))
    (return 0))
  (if (and (and (not nv) (== Once 0)) used)
    (if (< (- (CallFunction|Now) {AG('VUsed', 'I')}) 20.0)
      (return 0)))
  (bind c {AG('VBCause', 'I')})
  (if (and (== {AG('BankGun', 'I', 'GW')} 1) (!= Cause 1))
    (return 0))
  (if (and (!= c Cause) (!= c 0))
    (return 0))
  (bind lc {AG('VBCtx', 'I')})
  (if (and (!= lc 0) (!= lc Ctx))
    (return 0))
  (bind base (+ (+ (+ 1 (select (and (== c Cause) (!= Cause 0)) 8 0)) (select used 0 1)) (select (and (!= lc 0) (== lc Ctx)) 3 0)))
  (bind v {AG('VBVoice', 'I')})
  (if nv
    (if (>= v 0)
      (return (select (and (>= Cur 0) (== v Cur)) (+ base 4) 0)))
    (bind lf {AG('BankFem', 'I', 'GW')})
    (return (select (or (or (== lf 2) (== lf Fem)) Special) base 0)))
  (return (select (and (>= Cur 0) (== v Cur)) base 0)))
'''
W['PickLine'] = f'''
(fn PickLine (Cat Ch Cause)
  (if (or (or (< Cat 0) (>= Cat {LEN('VCatFirst')})) (not ({ISVALID} :Object Ch)))
    (return -1))
  (Utilities|Array|Clear (Variables|Default|GetPicks))
  {SL('Best', '0')}
  (bind once {AG('VCatOnce', 'Cat')})
  (bind fem (CallFunction|GenderOf :Ch Ch))
  (bind cur {VOICEOF('Ch')})
  (bind special (!= {CH('Kind', 'Ch')} 0))
  (bind test (Variables|Voice|GetVTestMode))
  (bind ctx (CallFunction|SocialModeOf :Ch Ch))
  (bind nv1 (+ {LEN('VVoiceName')} 1))
  (for blk (range 2)
    (if (or (== blk 0) (>= cur 0))
      (bind key (+ (* Cat nv1) (select (== blk 0) 0 (+ cur 1))))
      (if (< key {LEN('VCVCount')})
        (bind first {AG('VCVFirst', 'key')})
        (for k (range {AG('VCVCount', 'key')})
          (bind i (+ first k))
          (bind s (CallFunction|LineScore :I i :Cause Cause :Fem fem :Cur cur :Once once :Special special :Test test :Ctx ctx))
          (if (> s {L('Best')})
            (Utilities|Array|Clear (Variables|Default|GetPicks))
            {SL('Best', 's')}
            (Utilities|Array|Add :TargetArray (Variables|Default|GetPicks) :NewItem i)
            (elif (and (== s {L('Best')}) (> s 0))
              (Utilities|Array|Add :TargetArray (Variables|Default|GetPicks) :NewItem i)))))))
  (bind n (Utilities|Array|Length (Variables|Default|GetPicks)))
  (if (== n 0)
    (return -1))
  (return (Utilities|Array|Get(acopy) (Variables|Default|GetPicks) (Math|Random|RandomIntegerinRange 0 (- n 1)))))
'''
W['SoundScore'] = f'''
(fn SoundScore (I Fem Once Test)
  (if (and (not Test) (== {AG('VBTest', 'I')} 1))
    (return 0))
  (bind lc {AG('VBCtx', 'I')})
  (if (and (!= lc 0) (!= lc 4))
    (return 0))
  (bind used (> {AG('VUsed', 'I')} 0.0))
  (if (and used (== Once 1))
    (return 0))
  (bind lf {AG('BankFem', 'I', 'GW')})
  (bind g (select (or (or (== Fem 2) (== lf 2)) (== lf Fem)) 2 0))
  (if (== Once 0)
    (return (+ (+ 1 g) (select (Utilities|Array|ContainsItem :TargetArray (Variables|GW|GetLastSaid) :ItemToFind I) 0 4))))
  (return (+ (+ 1 g) (select used 0 4))))
'''
# kept for the other scripts (WorldSound, s34 LoudScream): a line of a category, gender-matched when possible
W['PickSound'] = f'''
(fn PickSound (Cat Fem)
  (if (not (Variables|Voice|GetVInit))
    (CallFunction|VoiceInit))
  (if (or (< Cat 0) (>= Cat {LEN('VCatFirst')}))
    (return -1))
  (Utilities|Array|Clear (Variables|Default|GetPicks))
  {SL('Best', '0')}
  (bind first {AG('VCatFirst', 'Cat')})
  (bind once {AG('VCatOnce', 'Cat')})
  (bind test (Variables|Voice|GetVTestMode))
  (for k (range {AG('VCatCount', 'Cat')})
    (bind i (+ first k))
    (bind s (CallFunction|SoundScore :I i :Fem Fem :Once once :Test test))
    (if (> s {L('Best')})
      (Utilities|Array|Clear (Variables|Default|GetPicks))
      {SL('Best', 's')}
      (Utilities|Array|Add :TargetArray (Variables|Default|GetPicks) :NewItem i)
      (elif (and (== s {L('Best')}) (> s 0))
        (Utilities|Array|Add :TargetArray (Variables|Default|GetPicks) :NewItem i))))
  (bind n (Utilities|Array|Length (Variables|Default|GetPicks)))
  (if (== n 0)
    (return -1))
  {SL('Pick', '(Utilities|Array|Get(acopy) (Variables|Default|GetPicks) (Math|Random|RandomIntegerinRange 0 (- n 1)))')}
  (if (== once 0)
    {ADD('LastSaid', L('Pick'), 'GW')}
    (if (> {LEN('LastSaid', 'GW')} 40)
      {DEL('LastSaid', '0', 'GW')})
    (else
      {SETE('VUsed', L('Pick'), '(Math|Float|Max(Float) ' + NOW + ' 0.01)')}))
  (return {L('Pick')}))
'''
W['Commit'] = f'''
(fn Commit (Ch Idx)
  (if (< Idx 0)
    (return))
  {SETE('VUsed', 'Idx', '(Math|Float|Max(Float) ' + NOW + ' 0.01)')}
  (if (or (== {AG('VBNV', 'Idx')} 1) (== {AG('VCatOnce', AG('BankCat', 'Idx', 'GW'))} 0))
    {ADD('LastSaid', 'Idx', 'GW')}
    (if (> {LEN('LastSaid', 'GW')} 12)
      {DEL('LastSaid', '0', 'GW')})))
'''
W['Uncommit'] = f'''
(fn Uncommit (Idx)
  (if (< Idx 0)
    (return))
  (if (== {AG('VBNV', 'Idx')} 0)
    {SETE('VUsed', 'Idx', '0.0')}))
'''
# speak now: the Cue on the character (every machine plays it), the mouth is busy, the area remembers it, one log line
W['Utter'] = f'''
(fn Utter (Ch Idx Pri Conv)
  (if (or (< Idx 0) (not ({ISVALID} :Object Ch)))
    (return))
  (bind now {NOW})
  (bind dur {AG('VBDur', 'Idx')})
  (bind loc {HEAD('Ch')})
  (bind sv {VOICEOF('Ch')})
  (if (<= Pri 2)
    (CallFunction|Hush :Loc loc :R {R_AREA} :Pri Pri :Except Ch))
  {CUE_SET('Ch', 'Idx')}
  {CHS('TalkUntil', 'Ch', f"(Math|Float|Max(Float) {CH('TalkUntil', 'Ch')} (+ now dur))")}
  {ADD('VAChar', 'Ch')}
  {ADD('VALoc', 'loc')}
  {ADD('VAStart', 'now')}
  {ADD('VAEnd', '(+ now dur)')}
  {ADD('VAPri', 'Pri')}
  {ADD('VACat', AG('BankCat', 'Idx', 'GW'))}
  {ADD('VAVoice', 'sv')}
  {ADD('VAHold', f"(+ (+ now dur) (select (<= Pri 2) {RF(*EV_GAP)} (select (== Pri 3) 12.0 (select (== Pri 5) 4.0 0.0))))")}
  (Variables|Voice|SetVLines (+ (Variables|Voice|GetVLines) 1))
  (CallFunction|Gesture :Ch Ch :Id (select (or (== {AG('BankCat', 'Idx', 'GW')} {CAT['laugh']}) (and (== {AG('VBNV', 'Idx')} 1) (== {AG('BankCat', 'Idx', 'GW')} {CAT['reply']}))) 8 6))
  (if (> Conv 0)
    (for q (range {LEN('VQTime')})
      (if (and (== {AG('VQConv', 'q')} Conv) (!= {AG('VQChar', 'q')} Ch))
        (CallFunction|Gesture :Ch {AG('VQChar', 'q')} :Id 7)
        (break))))
  (bind v {AG('VBVoice', 'Idx')})
  {log('(cat "GW: VOX t=" now " pri=" Pri " cat=" ' + AG('BankCat', 'Idx', 'GW') + ' " cause=" ' + AG('VBCause', 'Idx') + ' " conv=" Conv " idx=" Idx " dur=" dur " voice=" ' + VNAME('v') + ' " svoice=" ' + VNAME('sv') + ' " nv=" ' + AG('VBNV', 'Idx') + ' " gun=" ' + AG('BankGun', 'Idx', 'GW') + ' " test=" ' + AG('VBTest', 'Idx') + ' " kind=" ' + CH('Kind', 'Ch') + ' " pd=" (CallFunction|NearPlayerD :Loc loc) " loc=" loc " spk=" (Utilities|GetDisplayName :Object Ch) " text=" ' + AG('VBText', 'Idx') + ')')})
'''
W['Schedule'] = f'''
(fn Schedule (Ch Idx Pri At Conv Cat)
  (if (not ({ISVALID} :Object Ch))
    (return))
  {ADD('VQTime', 'At')}
  {ADD('VQChar', 'Ch')}
  {ADD('VQLine', 'Idx')}
  {ADD('VQPri', 'Pri')}
  {ADD('VQConv', 'Conv')}
  {ADD('VQCats', 'Cat')}
  {ADD('VQVoice', VOICEOF('Ch'))})
'''
# one due line per call (ReactionsTick calls it 3 times per tick)
W['ProcessCue'] = f'''
(fn ProcessCue ()
  (if (not (Variables|Voice|GetVInit))
    (CallFunction|VoiceInit))
  (bind now {NOW})
  (for i (range {LEN('VQTime')})
    (if (<= {AG('VQTime', 'i')} now)
      {SV('VQC', AG('VQChar', 'i'))}
      {SV('VQL', AG('VQLine', 'i'))}
      {SV('VQP', AG('VQPri', 'i'))}
      {SV('VQK', AG('VQConv', 'i'))}
      {SV('VQCat', AG('VQCats', 'i'))}
{QDEL('i')}
      (CallFunction|PlayQueued)
      (break))))
'''
W['PlayQueued'] = f'''
(fn PlayQueued ()
  (bind c (Variables|Voice|GetVQC))
  (bind p (Variables|Voice|GetVQP))
  (bind k (Variables|Voice|GetVQK))
  (bind line (Variables|Voice|GetVQL))
  (if (not ({ISVALID} :Object c))
    (CallFunction|Uncommit :Idx line)
    (CallFunction|DropConv :Conv k)
    (return))
  (if (and (GW|Get|BP_GW_Character|IsDead :self c) (> p 0))
    {log('(cat "GW: VOXDROP t=" (CallFunction|Now) " why=dead conv=" k " idx=" line)')}
    (CallFunction|DropConv :Conv k)
    (return))
  (if (< line 0)
    (CallFunction|SayNow :Ch c :Cat (Variables|Voice|GetVQCat) :Pri p)
    (return))
  (if (and (>= p 4) (> (CallFunction|NearPlayerD :Loc {HEAD('c')}) 1600.0))
    {log('(cat "GW: VOXDROP t=" (CallFunction|Now) " why=nobody pri=" p " conv=" k " idx=" line)')}
    (CallFunction|DropConv :Conv k)
    (return))
  (if (and (>= p 3) (CallFunction|BusyNear :Loc {HEAD('c')} :R {R_AREA} :MaxPri (- p 1)))
    {log('(cat "GW: VOXDROP t=" (CallFunction|Now) " why=busy pri=" p " conv=" k " idx=" line)')}
    (if (== k 0)
      (CallFunction|Uncommit :Idx line))
    (CallFunction|DropConv :Conv k)
    (return))
  (CallFunction|Utter :Ch c :Idx line :Pri p :Conv k))
'''
# the rest of a conversation goes; if nothing of it was heard yet (its first turn still queued), its lines stay unused
W['DropConv'] = f'''
(fn DropConv (Conv)
  (if (<= Conv 0)
    (return))
  {SL('Unheard', 'false')}
  (for j (range {LEN('VQTime')})
    (if (== {AG('VQConv', 'j')} Conv)
      (bind ql {AG('VQLine', 'j')})
      (if (and (>= ql 0) (<= {AG('VBTurn', '(Math|Integer|Max(Integer) ql 0)')} 1))
        {SL('Unheard', 'true')})))
  {SL('N', LEN('VQTime'))}
  (for k (range {L('N')})
    (bind i (- (- {L('N')} 1) k))
    (if (== {AG('VQConv', 'i')} Conv)
      (if {L('Unheard')}
        (CallFunction|Uncommit :Idx {AG('VQLine', 'i')}))
{QDEL('i')})))
'''
# a more urgent line starts at Loc: lower queued lines around go, lower lines being spoken fade out
W['Hush'] = f'''
(fn Hush (Loc R Pri Except)
  (bind now {NOW})
  (Utilities|Array|Clear (Variables|Default|GetDrops))
  {SL('N', LEN('VQTime'))}
  (for k (range {L('N')})
    (bind i (- (- {L('N')} 1) k))
    (if (> {AG('VQPri', 'i')} Pri)
      (bind qc {AG('VQChar', 'i')})
      {SL('Hit', 'true')}
      (if ({ISVALID} :Object qc)
        {SL('Hit', f"(< {DIST(LOC('qc'), 'Loc')} R)")})
      (if {L('Hit')}
        (if (> {AG('VQConv', 'i')} 0)
          (if (not (Utilities|Array|ContainsItem :TargetArray (Variables|Default|GetDrops) :ItemToFind {AG('VQConv', 'i')})) (Utilities|Array|Add :TargetArray (Variables|Default|GetDrops) :NewItem {AG('VQConv', 'i')}))
          (else
            (CallFunction|Uncommit :Idx {AG('VQLine', 'i')})
            {log('(cat "GW: VOXDROP t=" now " why=hush by=" Pri " pri=" ' + AG('VQPri', 'i') + ' " conv=0 idx=" ' + AG('VQLine', 'i') + ')')}
{QDEL('i')})))))
  (for cv (Variables|Default|GetDrops)
    {log('(cat "GW: VOXDROP t=" now " why=hush by=" Pri " conv=" cv)')}
    (CallFunction|DropConv :Conv cv))
  (for j (range {LEN('VAEnd')})
    (if (and (> {AG('VAEnd', 'j')} now) (> {AG('VAPri', 'j')} Pri))
      (if (< {DIST(AG('VALoc', 'j'), 'Loc')} R)
        (bind c {AG('VAChar', 'j')})
        {SETE('VAEnd', 'j', 'now')}
        (if (and ({ISVALID} :Object c) (!= c Except))
          {CUE_SET('c', STOP)}
          {CHS('TalkUntil', 'c', 'now')}
          {log('(cat "GW: VOXCUT t=" now " by=" Pri " pri=" ' + AG('VAPri', 'j') + ' " spk=" (Utilities|GetDisplayName :Object c))')})))))
'''
W['HoldAt'] = f'''
(fn HoldAt (Loc Secs)
  (bind now {NOW})
  {ADD('VAChar', NOCHAR)}
  {ADD('VALoc', 'Loc')}
  {ADD('VAStart', 'now')}
  {ADD('VAEnd', 'now')}
  {ADD('VAPri', '4')}
  {ADD('VACat', '0')}
  {ADD('VAVoice', '-1')}
  {ADD('VAHold', '(+ now Secs)')})
'''
W['Block'] = f'''
(fn Block (Ch Until Hold Pri)
  {ADD('VAChar', 'Ch')}
  {ADD('VALoc', HEAD('Ch'))}
  {ADD('VAStart', NOW)}
  {ADD('VAEnd', 'Until')}
  {ADD('VAPri', 'Pri')}
  {ADD('VACat', '0')}
  {ADD('VAVoice', '-1')}
  {ADD('VAHold', 'Hold')})
'''
W['VoiceClean'] = f'''
(fn VoiceClean ()
  (bind now {NOW})
  (if (< now (Variables|Voice|GetVNextClean))
    (return))
  (Variables|Voice|SetVNextClean (+ now 2.0))
  {SL('N', LEN('VAEnd'))}
  (for k (range {L('N')})
    (bind i (- (- {L('N')} 1) k))
    (if (and (and (< {AG('VAHold', 'i')} (- now 1.0)) (< {AG('VAEnd', 'i')} (- now 1.0))) (< {AG('VAStart', 'i')} (- now 60.0)))
{ADEL('i')})))
'''
W['Talkable'] = f'''
(fn Talkable (Ch Moving)
  (if (not ({ISVALID} :Object Ch))
    (return false))
  (if (GW|Get|BP_GW_Character|IsDead :self Ch)
    (return false))
  ; a disguised player has the same sound reflexes as any guest (Moving true: shouts, screams), not the ambient talk
  (if (and (Pawn|IsPlayerControlled :self Ch) (or (not Moving) {CH('IsSeeker', 'Ch')}))
    (return false))
  (if (or (!= {CH('Kind', 'Ch')} 0) (> {CH('TalkUntil', 'Ch')} {NOW}))
    (return false))
  (return (or Moving (< (Math|Vector|VectorLength (Transformation|GetVelocity :self Ch)) 40.0))))
'''
# may be sent across the room: not dancing / at the bar, not running from a panic
W['FreeToWalk'] = f'''
(fn FreeToWalk (Ch)
  (bind c (Utilities|Casting|CastToBP_GW_NPCController (Pawn|GetController :self Ch))
    (:then (return (and (== (GW|Get|BP_GW_NPCController|SocialMode :self c) 0) (< (GW|Get|BP_GW_NPCController|PanicUntil :self c) {NOW}))))
    (:CastFailed (return false))))
'''
# a guest in sight of Loc (a player's head) within MaxD whose character has a voice not already speaking there;
# preferably a voice not heard in this area for 45 s (the same character does not talk twice in a row)
W['FindSpeaker'] = f'''
(fn FindSpeaker (Loc MaxD Moving)
  (Utilities|Array|Clear (Variables|Default|GetCands))
  (Utilities|Array|Clear (Variables|Default|GetCands2))
  (bind since (- {NOW} 45.0))
  (for a (Actor|GetAllActorsOfClass :ActorClass {CHAR})
    (if (CallFunction|Talkable :Ch a :Moving Moving)
      (bind al {HEAD('a')})
      (if (< {DIST('al', 'Loc')} MaxD)
        (bind v {VOICEOF('a')})
        (if (and (>= v 0) (not (CallFunction|VoiceBusyNear :Loc Loc :R {R_AREA} :V v)))
          (if (CallFunction|SeeFrom :A Loc :B al)
            (if (CallFunction|VoiceRecentNear :Loc Loc :R {R_AREA} :V v :Since since)
              (Utilities|Array|Add :TargetArray (Variables|Default|GetCands2) :NewItem a)
              (else
                (Utilities|Array|Add :TargetArray (Variables|Default|GetCands) :NewItem a))))))))
  (bind n (Utilities|Array|Length (Variables|Default|GetCands)))
  (if (> n 0)
    (return (Utilities|Array|Get(acopy) (Variables|Default|GetCands) (Math|Random|RandomIntegerinRange 0 (- n 1)))))
  (bind n2 (Utilities|Array|Length (Variables|Default|GetCands2)))
  (if (== n2 0)
    (return {NOCHAR}))
  (return (Utilities|Array|Get(acopy) (Variables|Default|GetCands2) (Math|Random|RandomIntegerinRange 0 (- n2 1)))))
'''
W['VoiceRecentNear'] = f'''
(fn VoiceRecentNear (Loc R V Since)
  (for i (range {LEN('VAStart')})
    (if (and (>= {AG('VAStart', 'i')} Since) (== {AG('VAVoice', 'i')} V))
      (if (< {DIST(AG('VALoc', 'i'), 'Loc')} R)
        (return true))))
  (return false))
'''
# whom A answers to: the nearest idle guest within 2.3 m
W['FindPartner'] = f'''
(fn FindPartner (A)
  (bind al {LOC('A')})
  {SL('BestD', '230.0')}
  {SL('BestT', NOCHAR)}
  (for o (Actor|GetAllActorsOfClass :ActorClass {CHAR})
    (if (and (!= o A) {TALKABLE('o')})
      (bind d {DIST(LOC('o'), 'al')})
      (if (< d {L('BestD')})
        {SL('BestD', 'd')}
        {SL('BestT', 'o')})))
  (return {L('BestT')}))
'''
W['NearestTalker'] = f'''
(fn NearestTalker (Loc MaxD)
  {SL('BestD', 'MaxD')}
  {SL('BestT', NOCHAR)}
  (for o (Actor|GetAllActorsOfClass :ActorClass {CHAR})
    (if (CallFunction|Talkable :Ch o :Moving true)
      (bind d {DIST(LOC('o'), 'Loc')})
      (if (< d {L('BestD')})
        {SL('BestD', 'd')}
        {SL('BestT', 'o')})))
  (return {L('BestT')}))
'''
W['SpecialNear'] = f'''
(fn SpecialNear (Kind Loc R)
  {SL('BestD', 'R')}
  {SL('BestT', NOCHAR)}
  (for o (Actor|GetAllActorsOfClass :ActorClass {CHAR})
    (if (and (== {CH('Kind', 'o')} Kind) (not (GW|Get|BP_GW_Character|IsDead :self o)))
      (bind d {DIST(LOC('o'), 'Loc')})
      (if (< d {L('BestD')})
        {SL('BestD', 'd')}
        {SL('BestT', 'o')})))
  (return {L('BestT')}))
'''
# an unused dialogue written for these two characters (either way round): code = dialogue * 2 + swapped
W['PickDialogue'] = f'''
(fn PickDialogue (A B)
  (Utilities|Array|Clear (Variables|Default|GetPicks))
  (bind va {VOICEOF('A')})
  (bind vb {VOICEOF('B')})
  (if (or (or (< va 0) (< vb 0)) (== va vb))
    (return -1))
  (bind key (+ (* va {LEN('VVoiceName')}) vb))
  (if (>= key {LEN('VPairCount')})
    (return -1))
  (bind first {AG('VPairStart', 'key')})
  (bind test (Variables|Voice|GetVTestMode))
  (bind ma (CallFunction|SocialModeOf :Ch A))
  (bind mb (CallFunction|SocialModeOf :Ch B))
  (for k (range {AG('VPairCount', 'key')})
    (bind code {AG('VPairCode', '(+ first k)')})
    (bind f {AG('VDlgFirst', '(/ code 2)')})
    (bind dc {AG('VBCtx', 'f')})
    (if (and (and (<= {AG('VUsed', 'f')} 0.0) (or test (== {AG('VBTest', 'f')} 0))) (or (== dc 0) (or (== dc ma) (== dc mb))))
      (Utilities|Array|Add :TargetArray (Variables|Default|GetPicks) :NewItem code)))
  (bind n (Utilities|Array|Length (Variables|Default|GetPicks)))
  (if (== n 0)
    (return -1))
  (return (Utilities|Array|Get(acopy) (Variables|Default|GetPicks) (Math|Random|RandomIntegerinRange 0 (- n 1)))))
'''
# stop (if asked), stay a while, face Face (not while dancing / at the bar: the social brain places them)
W['HoldNPC'] = f'''
(fn HoldNPC (Ch Until Face Stop)
  (if (not ({ISVALID} :Object Ch))
    (return))
  {CHS('TalkUntil', 'Ch', f"(Math|Float|Max(Float) {CH('TalkUntil', 'Ch')} Until)")}
  (bind c (Utilities|Casting|CastToBP_GW_NPCController (Pawn|GetController :self Ch))
    (:then
      (if (!= (GW|Get|BP_GW_NPCController|SocialMode :self c) 0)
        (return))
      (if (and Stop (GW|Get|BP_GW_NPCController|IsMoving :self c))
        (AI|Navigation|StopMovement :self c)
        (GW|Set|BP_GW_NPCController|IsMoving :self c :IsMoving false)
        (GW|Set|BP_GW_NPCController|HasFinal :self c :HasFinal false))
      (bind here {LOC('Ch')})
      (if (> (Math|Vector|Distance2D(Vector) Face here) 30.0)
        (GW|Call|BP_GW_NPCController|FaceAt :self c :P Face))
      (if (not (GW|Get|BP_GW_NPCController|IsMoving :self c))
        (GW|Set|BP_GW_NPCController|NextMoveTime :self c :NextMoveTime (Math|Float|Max(Float) (GW|Get|BP_GW_NPCController|NextMoveTime :self c) Until))))
    (:CastFailed)))
'''
W['StartDialogue'] = f'''
(fn StartDialogue (A B Code)
  (if (not ({ISVALID} :Object A))
    (return))
  (if (not ({ISVALID} :Object B))
    (return))
  (bind d (/ Code 2))
  (bind swap (== (% Code 2) 1))
  (bind first {AG('VDlgFirst', 'd')})
  (Variables|Voice|SetVConv (+ (Variables|Voice|GetVConv) 1))
  (bind conv (Variables|Voice|GetVConv))
  {SL('T', f"(+ {NOW} 0.4)")}
  (for k (range {AG('VDlgN', 'd')})
    (bind idx (+ first k))
    (if (!= (== {AG('VBSpk', 'idx')} 1) swap)
      {SL('Sp', 'B')}
      (else
        {SL('Sp', 'A')}))
    (CallFunction|Commit :Ch {L('Sp')} :Idx idx)
    (CallFunction|Schedule :Ch {L('Sp')} :Idx idx :Pri 4 :At {L('T')} :Conv conv :Cat {CAT['dialogue']})
    {SL('T', f"(+ (+ {L('T')} {AG('VBDur', 'idx')}) {RF(0.2, 0.55)})")})
  (bind endt {L('T')})
  (CallFunction|HoldNPC :Ch A :Until (+ endt 1.0) :Face {LOC('B')} :Stop false)
  (CallFunction|HoldNPC :Ch B :Until (+ endt 1.0) :Face {LOC('A')} :Stop false)
  (CallFunction|Block :Ch A :Until endt :Hold (+ endt {RF(*AMB_GAP)}) :Pri 4)
  {log('(cat "GW: VOXCONV t=" (CallFunction|Now) " conv=" conv " dlg=" d " turns=" ' + AG('VDlgN', 'd') + ' " swap=" swap " len=" (- endt (CallFunction|Now)) " A=" (Utilities|GetDisplayName :Object A) " B=" (Utilities|GetDisplayName :Object B) " va=" ' + VNAME(VOICEOF('A')) + ' " vb=" ' + VNAME(VOICEOF('B')) + ')')})
'''
# a guest standing beside A (2.6 m) whose character shares an unused dialogue with A's
W['DialogueBeside'] = f'''
(fn DialogueBeside (A)
  (bind al {LOC('A')})
  (for o (Actor|GetAllActorsOfClass :ActorClass {CHAR})
    (if (and (!= o A) {TALKABLE('o')})
      (if (and (< {DIST(LOC('o'), 'al')} 260.0) (not (CallFunction|VoiceBusyNear :Loc {HEAD('o')} :R {R_AREA} :V {VOICEOF('o')})))
        {SL('Code', '(CallFunction|PickDialogue :A A :B o)')}
        (if (>= {L('Code')} 0)
          (CallFunction|StartDialogue :A A :B o :Code {L('Code')})
          (return true)))))
  (return false))
'''
# nobody beside A has a conversation left with it: the nearest guest (9 m) who has one walks over (PendingTick)
W['WalkOver'] = f'''
(fn WalkOver (A PL)
  (if ({ISVALID} :Object (Variables|Voice|GetVPendB))
    (return false))
  (if (not (CallFunction|FreeToWalk :Ch A))
    (return false))
  (bind al {LOC('A')})
  {SL('BestD', R_WALK)}
  {SL('BestT', NOCHAR)}
  {SL('BestC', '-1')}
  (for o (Actor|GetAllActorsOfClass :ActorClass {CHAR})
    (if (and (!= o A) {TALKABLE('o')})
      (bind d {DIST(LOC('o'), 'al')})
      (if (and (< d {L('BestD')}) (> d 260.0))
        (if (and (CallFunction|FreeToWalk :Ch o) (not (CallFunction|VoiceBusyNear :Loc {HEAD('o')} :R {R_AREA} :V {VOICEOF('o')})))
          {SL('Code', '(CallFunction|PickDialogue :A A :B o)')}
          (if (>= {L('Code')} 0)
            {SL('BestD', 'd')}
            {SL('BestT', 'o')}
            {SL('BestC', L('Code'))})))))
  (bind b {L('BestT')})
  (if (not ({ISVALID} :Object b))
    (return false))
  (bind now {NOW})
  (Variables|Voice|SetVPendA A)
  (Variables|Voice|SetVPendB b)
  (Variables|Voice|SetVPendCode {L('BestC')})
  (Variables|Voice|SetVPendUntil (+ now 14.0))
  (CallFunction|HoldNPC :Ch A :Until (+ now 15.0) :Face {LOC('b')} :Stop true)
  {CHS('TalkUntil', 'b', '(+ now 15.0)')}
  (CallFunction|SendTo :B b :A A)
  (CallFunction|HoldAt :Loc PL :Secs 15.0)
  {log('(cat "GW: VOXWALK t=" now " A=" (Utilities|GetDisplayName :Object A) " B=" (Utilities|GetDisplayName :Object b) " d=" ' + L('BestD') + ')')}
  (return true))
'''
W['SendTo'] = f'''
(fn SendTo (B A)
  (bind c (Utilities|Casting|CastToBP_GW_NPCController (Pawn|GetController :self B))
    (:then
      (bind al {LOC('A')})
      (GW|Set|BP_GW_NPCController|Partner :self c :Partner A)
      (GW|Set|BP_GW_NPCController|HasFinal :self c :HasFinal false)
      (GW|Call|BP_GW_NPCController|GoTo :self c :Dest (+ al (* (Math|Vector|Normalize (Math|Vector|MakeVector (- (.x {LOC('B')}) (.x al)) (- (.y {LOC('B')}) (.y al)) 0.0)) 110.0))))
    (:CastFailed)))
'''
# the walker has arrived: they talk (if their dialogue is still unused), else give up after 14 s
W['PendingTick'] = f'''
(fn PendingTick ()
  {SL('Bp', '(Variables|Voice|GetVPendB)')}
  {SL('Ap', '(Variables|Voice|GetVPendA)')}
  (bind b {L('Bp')})
  (bind a {L('Ap')})
  (if (not ({ISVALID} :Object b))
    (return))
  (bind now {NOW})
  {SL('Quit', "(or (> now (Variables|Voice|GetVPendUntil)) (< now (GW|Get|BP_GW_GameState|PanicUntil :self (CallFunction|GetGS))))")}
  (if (not ({ISVALID} :Object a))
    {SL('Quit', 'true')}
    (else
      (if (GW|Get|BP_GW_Character|IsDead :self a)
        {SL('Quit', 'true')})))
  (if (GW|Get|BP_GW_Character|IsDead :self b)
    {SL('Quit', 'true')})
  (if {L('Quit')}
    {log('(cat "GW: VOXWALK t=" now " gave up")')}
    (Variables|Voice|SetVPendB {NOCHAR})
    (if ({ISVALID} :Object a)
      {CHS('TalkUntil', 'a', 'now')})
    {CHS('TalkUntil', 'b', 'now')}
    (return))
  (if (and (< (Math|Vector|Distance2D(Vector) {LOC('a')} {LOC('b')}) 260.0) (< (Math|Vector|VectorLength (Transformation|GetVelocity :self b)) 60.0))
    (Variables|Voice|SetVPendB {NOCHAR})
    {SL('Code', '(Variables|Voice|GetVPendCode)')}
    (if (> {AG('VUsed', AG('VDlgFirst', f"(/ {L('Code')} 2)"))} 0.0)
      {CHS('TalkUntil', 'a', 'now')}
      {CHS('TalkUntil', 'b', 'now')}
      {SL('Code', '(CallFunction|PickDialogue :A a :B b)')})
    (if (>= {L('Code')} 0)
      (CallFunction|StartDialogue :A a :B b :Code {L('Code')}))))
'''
# a single remark; the neighbour sometimes laughs or answers a word
W['StartRemark'] = f'''
(fn StartRemark (A)
  {SL('I', f"(CallFunction|PickLine :Cat {CAT['chatter']} :Ch A :Cause 0)")}
  (bind idx {L('I')})
  (if (< idx 0)
    (return false))
  (Variables|Voice|SetVConv (+ (Variables|Voice|GetVConv) 1))
  (bind conv (Variables|Voice|GetVConv))
  (bind t0 (+ {NOW} 0.3))
  (CallFunction|Commit :Ch A :Idx idx)
  (CallFunction|Schedule :Ch A :Idx idx :Pri 4 :At t0 :Conv conv :Cat {CAT['chatter']})
  {SL('T', f"(+ t0 {AG('VBDur', 'idx')})")}
  {SL('B', '(CallFunction|FindPartner :A A)')}
  (bind b {L('B')})
  (if ({ISVALID} :Object b)
    (CallFunction|HoldNPC :Ch A :Until (+ {L('T')} 0.5) :Face {LOC('b')} :Stop false)
    (if (and (< (Math|Random|RandomFloat) 0.4) (!= {VOICEOF('b')} {VOICEOF('A')}))
      {SL('J', f"(CallFunction|PickLine :Cat {CAT['reply']} :Ch b :Cause 0)")}
      (if (< {L('J')} 0)
        {SL('J', f"(CallFunction|PickLine :Cat {CAT['laugh']} :Ch b :Cause 0)")})
      (if (>= {L('J')} 0)
        (CallFunction|Commit :Ch b :Idx {L('J')})
        (CallFunction|Schedule :Ch b :Idx {L('J')} :Pri 4 :At (+ {L('T')} {RF(0.25, 0.5)}) :Conv conv :Cat {CAT['reply']})
        {SL('T', f"(+ (+ {L('T')} 0.5) {AG('VBDur', L('J'))})")}
        (CallFunction|HoldNPC :Ch b :Until (+ {L('T')} 0.5) :Face {LOC('A')} :Stop false)))
    (else
      (CallFunction|HoldNPC :Ch A :Until (+ {L('T')} 0.5) :Face {LOC('A')} :Stop false)))
  (CallFunction|Block :Ch A :Until {L('T')} :Hold (+ {L('T')} {RF(*AMB_GAP)}) :Pri 4)
  (return true))
'''
# ambient talk around a player (PL = his head): a conversation (70 %) or a remark; nothing fits: 4-5 s of silence
W['AmbientWith'] = f'''
(fn AmbientWith (PL A)
  (if (not ({ISVALID} :Object A))
    (CallFunction|HoldAt :Loc PL :Secs 4.0)
    (return))
  ; often a plain greeting with whoever is close: the same exchange a guest gets by pressing E
  (if (and (< (Math|Random|RandomFloat) 0.45) (CallFunction|FreeToWalk :Ch A))
    {SL('B', '(CallFunction|GreetPartner :A A)')}
    (if ({ISVALID} :Object {L('B')})
      (if (CallFunction|GreetExchange :A A :B {L('B')} :St 0 :Reply true)
        {log(f'(cat "GW: VOXGREET t=" {NOW} " a=" (Utilities|GetDisplayName :Object A) " b=" (Utilities|GetDisplayName :Object {L("B")}))')}
        (return))))
  (if (< (Math|Random|RandomFloat) {P_DIALOGUE})
    (if (CallFunction|DialogueBeside :A A)
      (return))
    (if (CallFunction|WalkOver :A A :PL PL)
      (return)))
  (if (CallFunction|StartRemark :A A)
    (return))
  (CallFunction|HoldAt :Loc PL :Secs 5.0))
'''
W['AmbientTick'] = f'''
(fn AmbientTick ()
  (bind now {NOW})
  (if (< now (Variables|Voice|GetVNextAmb))
    (return))
  (Variables|Voice|SetVNextAmb (+ now 1.0))
  (CallFunction|PendingTick)
  (bind s (CallFunction|GetGS))
  (if (or (< now (GW|Get|BP_GW_GameState|PanicUntil :self s)) (!= (GW|Get|BP_GW_GameState|EventId :self s) 0))
    (return))
  (if (> (Variables|GW|GetPanicCalmAt) 0.0)
    (return))
  (for p (Variables|Voice|GetVPl)
    (bind pl {HEAD('p')})
    (if (not (or (CallFunction|HoldNear :Loc pl :R {R_AREA} :MaxPri 9) (CallFunction|BusyNear :Loc pl :R {R_AREA} :MaxPri 9)))
      {SV('VAmbA', f'(CallFunction|FindSpeaker :Loc pl :MaxD {R_SPEAK} :Moving false)')}
      (CallFunction|AmbientWith :PL pl :A (Variables|Voice|GetVAmbA))
      (return))))
'''
# s36 social groups (bar, dance floor) ask for talk through Say(chatter/reply): a hint, the director decides
W['AmbientNudge'] = f'''
(fn AmbientNudge (Ch)
  (if (not {TALKABLE('Ch')})
    (return))
  (bind s (CallFunction|GetGS))
  (if (or (< {NOW} (GW|Get|BP_GW_GameState|PanicUntil :self s)) (!= (GW|Get|BP_GW_GameState|EventId :self s) 0))
    (return))
  (for p (Variables|Voice|GetVPl)
    (bind pl {HEAD('p')})
    (if (< {DIST('pl', HEAD('Ch'))} {R_SPEAK})
      (if (and (CallFunction|SeeFrom :A pl :B {HEAD('Ch')}) (not (or (CallFunction|HoldNear :Loc pl :R {R_AREA} :MaxPri 9) (CallFunction|BusyNear :Loc pl :R {R_AREA} :MaxPri 9))))
        (CallFunction|AmbientWith :PL pl :A Ch)
        (return)))))
'''
# up to N lines of Cat around a player, each by another guest in sight, one after the other (the speaker is chosen
# for the line: a guest whose character has none left is skipped)
W['AreaLines'] = f'''
(fn AreaLines (PL Cat Pri N Delay Spread Cause)
  {SL('T', f"(+ {NOW} Delay)")}
  {SL('Got', '0')}
  {SL('Done', 'false')}
  (for tt (range 6)
    (if (and (< {L('Got')} N) (not {L('Done')}))
      {SL('Sp', f'(CallFunction|FindSpeaker :Loc PL :MaxD {R_SHOUT} :Moving true)')}
      (bind a {L('Sp')})
      (if (not ({ISVALID} :Object a))
        {SL('Done', 'true')}
        (else
          {SL('I', '(CallFunction|PickLine :Cat Cat :Ch a :Cause Cause)')}
          (if (>= {L('I')} 0)
            (CallFunction|Commit :Ch a :Idx {L('I')})
            (CallFunction|Schedule :Ch a :Idx {L('I')} :Pri Pri :At {L('T')} :Conv 0 :Cat Cat)
            {CHS('TalkUntil', 'a', f"(+ {L('T')} {AG('VBDur', L('I'))})")}
            {SL('T', f"(+ (+ {L('T')} {AG('VBDur', L('I'))}) Spread)")}
            {SL('Got', f"(+ {L('Got')} 1)")}
            (else
              {CHS('TalkUntil', 'a', f"(+ {NOW} 2.0)")}))))))
  (return {L('Got')}))
'''
# the first seconds of a panic: one bystander scream near the cause (if a player hears it), then at most 2 shouts per
# listening area per 12 s, about the cause near it, generic further away
W['AlarmShouts'] = f'''
(fn AlarmShouts (Loc Cause Scream)
  (bind now {NOW})
  (if Scream
    {SL('Sc', f'(CallFunction|NearestTalker :Loc Loc :MaxD 1500.0)')}
    (bind sc {L('Sc')})
    (if ({ISVALID} :Object sc)
      (if (and (< (CallFunction|NearPlayerD :Loc {LOC('sc')}) 1500.0) (== (CallFunction|CountCat :Loc {LOC('sc')} :R 900.0 :Cat {CAT['scream']} :Since (- now 8.0)) 0))
        {SL('I', f"(CallFunction|PickLine :Cat {CAT['scream']} :Ch sc :Cause 0)")}
        (if (>= {L('I')} 0)
          (CallFunction|Commit :Ch sc :Idx {L('I')})
          (CallFunction|Schedule :Ch sc :Idx {L('I')} :Pri 1 :At (+ now {RF(0.05, 0.3)}) :Conv 0 :Cat {CAT['scream']})
          {CHS('TalkUntil', 'sc', "(+ now 2.0)")}))))
  (for p (Variables|Voice|GetVPl)
    (bind pl {HEAD('p')})
    (bind near (or (< {DIST('pl', 'Loc')} {FAR_CAUSE}) (or (== Cause 2) (== Cause 4))))
    {SL('Have', f"(CallFunction|CountCat :Loc pl :R {R_AREA} :Cat {CAT['shout']} :Since (- now 12.0))")}
    (if (< {L('Have')} 2)
      (CallFunction|Hush :Loc pl :R {R_AREA} :Pri 1 :Except {NOCHAR})
      (CallFunction|AreaLines :PL pl :Cat {CAT['shout']} :Pri 1 :N (- 2 {L('Have')}) :Delay {RF(0.4, 0.7)} :Spread 0.1 :Cause (select near Cause 0)))))
'''
W['CauseNow'] = f'''
(fn CauseNow ()
  (bind now {NOW})
  (if (and (>= (Variables|Voice|GetVCauseSet) 0) (< (- now (Variables|Voice|GetVCauseAt)) 0.6))
    (return (Variables|Voice|GetVCauseSet)))
  (if (or (Variables|GW|GetGunContext) (< (- now (Variables|Voice|GetVLastGun)) 0.6))
    (return 1))
  (if (< (- now (Variables|Voice|GetVLastBoom)) 0.8)
    (return 3))
  (bind ev (GW|Get|BP_GW_GameState|EventId :self (CallFunction|GetGS)))
  (if (or (== ev 2) (< (- now (Variables|Voice|GetVLastFire)) 1.0))
    (return 2))
  (if (== ev 3)
    (return 4))
  (return 0))
'''
W['SetPanicCause'] = f'''
(fn SetPanicCause (Cause)
  (Variables|Voice|SetVCauseSet Cause)
  (Variables|Voice|SetVCauseAt {NOW}))
'''
W['StartPanicCause'] = '''
(fn StartPanicCause (Loc Dur Cause)
  (CallFunction|SetPanicCause :Cause Cause)
  (CallFunction|StartPanic :Loc Loc :Dur Dur))
'''
# every NPC runs for Dur seconds (s14 Think reads PanicUntil / PanicFrom), the voices are the director's
W['StartPanic'] = f'''
(fn StartPanic (Loc Dur)
  (bind now {NOW})
  (for c (Actor|GetAllActorsOfClass :ActorClass {NPCC})
    (GW|Set|BP_GW_NPCController|PanicUntil :self c :PanicUntil (+ now (* Dur (Math|Random|RandomFloatinRange 0.8 1.1))))
    (GW|Set|BP_GW_NPCController|PanicFrom :self c :PanicFrom Loc)
    (GW|Set|BP_GW_NPCController|IsMoving :self c :IsMoving false)
    (GW|Set|BP_GW_NPCController|NextMoveTime :self c :NextMoveTime now))
  (Variables|GW|SetPanicCalmAt (+ now (+ Dur 1.0)))
  (Variables|GW|SetStamp (+ (Variables|GW|GetStamp) 1))
  (if (not (Variables|Voice|GetVInit))
    (CallFunction|VoiceInit))
  (CallFunction|PlayerPawns)
  {SL('Cause', '(CallFunction|CauseNow)')}
  {log('(cat "GW: VOXCAUSE t=" now " src=panic cause=" ' + L('Cause') + ' " gunctx=" (Variables|GW|GetGunContext) " loc=" Loc)')}
  (CallFunction|AlarmShouts :Loc Loc :Cause {L('Cause')} :Scream true)
  (bind s {GSC}
    (:then (GW|Set|BP_GW_GameState|PanicUntil :self s :PanicUntil (Math|Float|Max(Float) (GW|Get|BP_GW_GameState|PanicUntil :self s) (+ now Dur))))
    (:CastFailed)))
'''
# P0: the victim's scream, then the neighbours shout (about fire if the victim burns)
W['DeathCry'] = f'''
(fn DeathCry (Victim)
  (if (not ({ISVALID} :Object Victim))
    (return))
  (if (not (Variables|Voice|GetVInit))
    (CallFunction|VoiceInit))
  (CallFunction|PlayerPawns)
  {SL('Cause', f"(select {CH('Burning', 'Victim')} 2 (CallFunction|CauseNow))")}
  {log('(cat "GW: VOXCAUSE t=" (CallFunction|Now) " src=death cause=" ' + L('Cause') + ' " gunctx=" (Variables|GW|GetGunContext) " burning=" ' + CH('Burning', 'Victim') + ' " loc=" ' + LOC('Victim') + ')')}
  {SL('I', f"(CallFunction|PickLine :Cat {CAT['scream']} :Ch Victim :Cause 0)")}
  (if (>= (CallFunction|CountCat :Loc {LOC('Victim')} :R {R_AREA} :Cat {CAT['scream']} :Since (- {NOW} 1.0)) 2)
    {SL('I', '-1')})
  (if (>= {L('I')} 0)
    (CallFunction|Commit :Ch Victim :Idx {L('I')})
    (CallFunction|Utter :Ch Victim :Idx {L('I')} :Pri 0 :Conv 0))
  {CHS('TalkUntil', 'Victim', f"(+ {NOW} 600.0)")}
  (CallFunction|AlarmShouts :Loc {LOC('Victim')} :Cause {L('Cause')} :Scream false))
'''
W['PanicTick'] = f'''
(fn PanicTick ()
  (if (and (> (Variables|GW|GetPanicCalmAt) 0.0) (>= {NOW} (Variables|GW|GetPanicCalmAt)))
    (Variables|GW|SetPanicCalmAt 0.0)
    (CallFunction|SayNearPlayers :Cat {CAT['calm']} :PerPlayer 2 :Delay 0.5 :Spread 2.0)))
'''
# other scripts ask for lines around the players (events, piano, calm): the director applies the area rules
W['SayNearPlayers'] = f'''
(fn SayNearPlayers (Cat PerPlayer Delay Spread)
  (if (not (Variables|Voice|GetVInit))
    (CallFunction|VoiceInit))
  (CallFunction|PlayerPawns)
  (bind pri (CallFunction|CatPri :Cat Cat))
  (if (<= pri 1)
    (CallFunction|AlarmShouts :Loc (Math|Vector|MakeVector 0.0 0.0 -100000.0) :Cause (CallFunction|CauseNow) :Scream false)
    (return))
  (if (== pri 2)
    (Variables|Voice|SetVNextEv (Math|Float|Min(Float) (Variables|Voice|GetVNextEv) (+ {NOW} Delay)))
    (return))
  (for p (Variables|Voice|GetVPl)
    (bind pl {HEAD('p')})
    (if (not (CallFunction|BusyNear :Loc pl :R {R_AREA} :MaxPri pri))
      (CallFunction|AreaLines :PL pl :Cat Cat :Pri pri :N (Math|Integer|Min(Integer) PerPlayer 2) :Delay Delay :Spread (Math|Float|Max(Float) Spread 0.8) :Cause 0))))
'''
EVCAT_X = ' '.join(f'(select (== ev {k}) {c}' for k, c in list(EVCAT.items())[:-1]) + f' {EVCAT[5]}' + ')' * (len(EVCAT) - 1)
EVCAUSE_X = ' '.join(f'(select (== ev {k}) {c}' for k, c in list(EVCAUSE.items())[:-1]) + f' {EVCAUSE[5]}' + ')' * (len(EVCAUSE) - 1)
# during an event: one line every 6-9 s per area (the event's own category); the bandits taunt now and then
W['EventVoiceTick'] = f'''
(fn EventVoiceTick ()
  (bind now {NOW})
  (if (< now (Variables|Voice|GetVNextEv))
    (return))
  (Variables|Voice|SetVNextEv (+ now 0.5))
  (bind s (CallFunction|GetGS))
  (bind ev (GW|Get|BP_GW_GameState|EventId :self s))
  (bind robot (GW|Get|BP_GW_GameState|RobotOn :self s))
  (if (and (== ev 0) (not robot))
    (return))
  (bind cat {EVCAT_X})
  (bind cause {EVCAUSE_X})
  (for p (Variables|Voice|GetVPl)
    (bind pl {HEAD('p')})
    (if (not (or (CallFunction|BusyNear :Loc pl :R {R_AREA} :MaxPri 2) (CallFunction|HoldNear :Loc pl :R {R_AREA} :MaxPri 2)))
      (if (or (!= ev 0) ({ISVALID} :Object (CallFunction|SpecialNear :Kind 3 :Loc pl :R 1600.0)))
        (if (== (CallFunction|AreaLines :PL pl :Cat (select (== ev 0) {EVCAT[5]} cat) :Pri 2 :N 1 :Delay 0.1 :Spread 0.0 :Cause cause) 0)
          (CallFunction|HoldAt :Loc pl :Secs 3.0)))))
  (if (and (== ev 1) (>= now (Variables|Voice|GetVBanditNext)))
    (Variables|Voice|SetVBanditNext (+ now {RF(*BANDIT_GAP)}))
    (for q (Variables|Voice|GetVPl)
      {SL('Bd', f"(CallFunction|SpecialNear :Kind 1 :Loc {LOC('q')} :R 1500.0)")}
      (if ({ISVALID} :Object {L('Bd')})
        {SL('I', f"(CallFunction|PickLine :Cat {CAT['attack_bandit']} :Ch {L('Bd')} :Cause 1)")}
        (if (>= {L('I')} 0)
          (CallFunction|Commit :Ch {L('Bd')} :Idx {L('I')})
          (CallFunction|Schedule :Ch {L('Bd')} :Idx {L('I')} :Pri 2 :At (+ now 0.2) :Conv 0 :Cat {CAT['attack_bandit']})
          (break))))))
'''
# a voice line asked for one character (kamikaze, robot, a burning guest, s36 groups...)
W['SayNow'] = f'''
(fn SayNow (Ch Cat Pri)
  (if (not ({ISVALID} :Object Ch))
    (return))
  (CallFunction|PlayerPawns)
  (bind now {NOW})
  (bind loc {HEAD('Ch')})
  (if (> (CallFunction|NearPlayerD :Loc loc) 1800.0)
    (return))
  (if (or (or (== Cat {CAT['chatter']}) (== Cat {CAT['reply']})) (== Cat {CAT['dialogue']}))
    (CallFunction|AmbientNudge :Ch Ch)
    (return))
  (if (== Cat {CAT['kamikaze']})
    (if (< now (Variables|Voice|GetVKamiNext))
      (return))
    (Variables|Voice|SetVKamiNext (+ now {RF(*KAMI_GAP)})))
  (if (== Cat {CAT['robot_voice']})
    (if (< now (Variables|Voice|GetVRobotNext))
      (return))
    (Variables|Voice|SetVRobotNext (+ now {RF(*ROBOT_GAP)})))
  (if (and (>= Pri 3) (CallFunction|BusyNear :Loc loc :R {R_AREA} :MaxPri (- Pri 1)))
    (return))
  (if (and (> Pri 1) (> {CH('TalkUntil', 'Ch')} now))
    (return))
  {SL('I', '(CallFunction|PickLine :Cat Cat :Ch Ch :Cause (CallFunction|CauseNow))')}
  (if (< {L('I')} 0)
    {log('(cat "GW: VOXDRY t=" now " cat=" Cat " spk=" (Utilities|GetDisplayName :Object Ch))')}
    (return))
  (CallFunction|Commit :Ch Ch :Idx {L('I')})
  (CallFunction|Utter :Ch Ch :Idx {L('I')} :Pri Pri :Conv 0))
'''
CATV = f'{AG("VCatVoice", "(Math|Integer|Clamp(Integer) :Value Cat :Min 0 :Max " + str(NCAT - 1) + ")")}'
W['Say'] = f'''
(fn Say (Ch Cat)
  (if (not ({ISVALID} :Object Ch))
    (return))
  (if (and (GW|Get|BP_GW_Character|IsDead :self Ch) (!= Cat {CAT['scream']}))
    (return))
  (if (not (Variables|Voice|GetVInit))
    (CallFunction|VoiceInit))
  (if (or (or (< Cat 0) (>= Cat {NCAT})) (== {CATV} 0))
    (bind sidx (CallFunction|PickSound :Cat Cat :Fem 2))
    (if (>= sidx 0)
      {CUE_SET('Ch', 'sidx')}
      (if (> (- {NOW} (Variables|Voice|GetVSfxLogAt)) 5.0)
        (Variables|Voice|SetVSfxLogAt {NOW})
        {log('(cat "GW: say cat=" Cat " idx=" sidx " by " (Utilities|GetDisplayName :Object Ch) " (sound effect)")')}))
    (return))
  (CallFunction|SayNow :Ch Ch :Cat Cat :Pri (CallFunction|CatPri :Cat Cat)))
'''
W['QueueSay'] = f'''
(fn QueueSay (Ch Cat Delay)
  (if (not ({ISVALID} :Object Ch))
    (return))
  (CallFunction|Schedule :Ch Ch :Idx -1 :Pri (CallFunction|CatPri :Cat Cat) :At (+ {NOW} Delay) :Conv 0 :Cat Cat))
'''
W['WorldSound'] = f'''
(fn WorldSound (Cat Loc)
  (bind now {NOW})
  (if (or (or (== Cat {CAT['gunshot']}) (== Cat {CAT['turret_fire']})) (== Cat {CAT['laser']}))
    (Variables|Voice|SetVLastGun now))
  (if (== Cat {CAT['explosion']})
    (Variables|Voice|SetVLastBoom now))
  (if (or (== Cat {CAT['fire_whoosh']}) (== Cat {CAT['fire_loop']}))
    (Variables|Voice|SetVLastFire now))
  (bind idx (CallFunction|PickSound :Cat Cat :Fem 2))
  (if (< idx 0)
    (return))
  (bind a (Game|SpawnActorfromClass :Class "{CUE}" :SpawnTransform (Math|Transform|MakeTransform :Location Loc) :CollisionHandlingOverride "AlwaysSpawn"))
  (GW|Set|BP_GW_SoundCue|Idx :self a :Idx idx)
  (if (and (< Cat {NCAT}) (== {CATV} 1))
    {log('(cat "GW: VOX t=" now " pri=5 cat=" Cat " cause=0 conv=0 idx=" idx " dur=" ' + AG('VBDur', 'idx') + ' " voice=" ' + VNAME(AG('VBVoice', 'idx')) + ' " svoice=world nv=" ' + AG('VBNV', 'idx') + ' " gun=0 test=" ' + AG('VBTest', 'idx') + ' " kind=9 pd=" (CallFunction|NearPlayerD :Loc Loc) " loc=" Loc " spk=world" Cat " text=" ' + AG('VBText', 'idx') + ')')}
    (else
      {log('(cat "GW: world sound cat=" Cat " idx=" idx " at " Loc)')})))
'''
# The same exchange for a guest pressing E and for two NPCs (the game is about hiding: a conversation proves nothing):
# A speaks first in its own voice (a greeting, "greet_again", a remark, a laugh), both stop and face each other, B answers.
W['GreetLine'] = f'''
(fn GreetLine (Ch St)
  {SL('I', f"(CallFunction|PickLine :Cat (select (== St 0) {CAT['greet']} (select (== St 1) {CAT['greet_again']} {CAT['chatter']})) :Ch Ch :Cause 0)")}
  (if (and (< {L('I')} 0) (< St 2))
    {SL('I', f"(CallFunction|PickLine :Cat (select (== St 0) {CAT['greet_again']} {CAT['chatter']}) :Ch Ch :Cause 0)")})
  (if (< {L('I')} 0)
    {SL('I', f"(CallFunction|PickLine :Cat {CAT['laugh']} :Ch Ch :Cause 0)")})
  (return {L('I')}))
'''
W['GreetExchange'] = f'''
(fn GreetExchange (A B St Reply)
  (bind now {NOW})
  (if (CallFunction|VoiceBusyNear :Loc {HEAD('A')} :R {R_AREA} :V {VOICEOF('A')})
    (return false))
  {SL('I', '(CallFunction|GreetLine :Ch A :St St)')}
  (if (< {L('I')} 0)
    {log('(cat "GW: VOXTALK t=" now " dry: " (Utilities|GetDisplayName :Object A))')}
    (return false))
  (bind dur {AG('VBDur', L('I'))})
  (CallFunction|HoldNPC :Ch A :Until (+ now (+ dur 3.0)) :Face {LOC('B')} :Stop true)
  (CallFunction|HoldNPC :Ch B :Until (+ now (+ dur 3.0)) :Face {LOC('A')} :Stop true)
  (CallFunction|Commit :Ch A :Idx {L('I')})
  (CallFunction|Utter :Ch A :Idx {L('I')} :Pri 5 :Conv 0)
  {log(f'(cat "GW: VOXGREETX reply=" Reply " va=" {VOICEOF("A")} " vb=" {VOICEOF("B")} " b=" (Utilities|GetDisplayName :Object B))')}
  (if (and Reply (not (Pawn|IsPlayerControlled :self B)))
    (if (and (!= {VOICEOF('B')} {VOICEOF('A')}) (not {CH('IsDead', 'B')}))
      {SL('J', '(CallFunction|GreetLine :Ch B :St St)')}
      (if (>= {L('J')} 0)
        (CallFunction|Commit :Ch B :Idx {L('J')})
        (CallFunction|Schedule :Ch B :Idx {L('J')} :Pri 5 :At (+ now (+ dur {RF(0.3, 0.6)})) :Conv 0 :Cat {CAT['greet']})
        (CallFunction|HoldNPC :Ch B :Until (+ now (+ (+ dur {AG('VBDur', L('J'))}) 2.0)) :Face {LOC('A')} :Stop true))))
  (return true))
'''
W['GreetPartner'] = f'''
(fn GreetPartner (A)
  (bind al {LOC('A')})
  {SL('BestD', '420.0')}
  {SL('BestT', NOCHAR)}
  (for o (Actor|GetAllActorsOfClass :ActorClass {CHAR})
    (if (and (!= o A) (CallFunction|Talkable :Ch o :Moving true))
      (if (not (Pawn|IsPlayerControlled :self o))
        (bind d {DIST(LOC('o'), 'al')})
        (if (< d {L('BestD')})
          (if (CallFunction|FreeToWalk :Ch o)
            {SL('BestD', 'd')}
            {SL('BestT', 'o')})))))
  (return {L('BestT')}))
'''
# NPC pairs greet each other by themselves: with voices around a player, silently (same stop, same faces) further away
W['GreetTick'] = f'''
(fn GreetTick ()
  (bind now {NOW})
  (if (< now (Variables|Voice|GetVNextGreet))
    (return))
  (Variables|Voice|SetVNextGreet (+ now {RF(3.0, 6.0)}))
  (bind s (CallFunction|GetGS))
  (if (or (< now (GW|Get|BP_GW_GameState|PanicUntil :self s)) (!= (GW|Get|BP_GW_GameState|EventId :self s) 0))
    (return))
  (if (> (Variables|GW|GetPanicCalmAt) 0.0)
    (return))
  (for p (Variables|Voice|GetVPl)
    (bind pl {HEAD('p')})
    (if (not (or (CallFunction|HoldNear :Loc pl :R {R_AREA} :MaxPri 9) (CallFunction|BusyNear :Loc pl :R {R_AREA} :MaxPri 9)))
      {SL('A', f'(CallFunction|FindSpeaker :Loc pl :MaxD {R_SPEAK} :Moving false)')}
      (if ({ISVALID} :Object {L('A')})
        (if (CallFunction|FreeToWalk :Ch {L('A')})
          {SL('B', f"(CallFunction|GreetPartner :A {L('A')})")}
          (if ({ISVALID} :Object {L('B')})
            (if (CallFunction|GreetExchange :A {L('A')} :B {L('B')} :St 0 :Reply true)
              {log(f'(cat "GW: VOXGREET t=" now " a=" (Utilities|GetDisplayName :Object {L("A")}) " b=" (Utilities|GetDisplayName :Object {L("B")}))')}
              (return)))))))
  (bind all (Actor|GetAllActorsOfClass :ActorClass {CHAR}))
  (if (== (Utilities|Array|Length all) 0)
    (return))
  (for tries (range 6)
    {SL('A', '(Utilities|Array|Get(acopy) all (Math|Random|RandomIntegerinRange 0 (- (Utilities|Array|Length all) 1)))')}
    (if (and (CallFunction|Talkable :Ch {L('A')} :Moving true) (not (Pawn|IsPlayerControlled :self {L('A')})))
      (if (and (CallFunction|FreeToWalk :Ch {L('A')}) (> (CallFunction|NearPlayerD :Loc {LOC(L('A'))}) {R_SPEAK}))
        {SL('B', f"(CallFunction|GreetPartner :A {L('A')})")}
        (if ({ISVALID} :Object {L('B')})
        {SL('H', f'(+ now {RF(3.0, 5.0)})')}
        (CallFunction|HoldNPC :Ch {L('A')} :Until {L('H')} :Face {LOC(L('B'))} :Stop true)
        (CallFunction|HoldNPC :Ch {L('B')} :Until {L('H')} :Face {LOC(L('A'))} :Stop true)
        (CallFunction|Gesture :Ch {L('A')} :Id 6)
        (CallFunction|Gesture :Ch {L('B')} :Id 7)
        {log('(cat "GW: VOXGREET t=" now " silent pair far from the players")')}
        (break))))))
'''
# E on a guest (PC.TryTalk -> GWTalk): the guest's OWN character speaks, like any guest; an NPC usually answers. Exactly
# what two NPCs do by themselves (GreetTick), so a conversation never tells a player from a guest.
W['TalkTo'] = f'''
(fn TalkTo (Who Ch)
  (if (not (Variables|Voice|GetVInit))
    (CallFunction|VoiceInit))
  (if (not (and ({ISVALID} :Object Who) ({ISVALID} :Object Ch)))
    (return))
  (CallFunction|PlayerPawns)
  (bind now {NOW})
  (if (< (- now {CH('TalkedAt', 'Who')}) 2.0)
    (return))
  (if (or (GW|Get|BP_GW_Character|IsDead :self Ch) (!= {CH('Kind', 'Ch')} 0))
    {log('(cat "GW: VOXTALK t=" now " target is not a guest: nothing")')}
    (return))
  {SL('Step', f"(select (and (== {CH('TalkNPC', 'Who')} Ch) (< (- now {CH('TalkedAt', 'Who')}) 25.0)) (+ {CH('TalkStep', 'Who')} 1) 0)")}
  {CHS('TalkStep', 'Who', L('Step'))}
  {CHS('TalkedAt', 'Who', 'now')}
  {CHS('TalkNPC', 'Who', 'Ch')}
  (if (or (CallFunction|BusyNear :Loc {HEAD('Who')} :R {R_AREA} :MaxPri 3) (> {CH('TalkUntil', 'Who')} now))
    {log('(cat "GW: VOXTALK t=" now " busy: " (Utilities|GetDisplayName :Object Who))')}
    (return))
  ; an NPC does not always answer: a silence must not unmask a player either
  (if (CallFunction|GreetExchange :A Who :B Ch :St {L('Step')} :Reply (< (Math|Random|RandomFloat) 0.8))
    {log('(cat "GW: VOXTALK t=" now " step=" ' + L('Step') + ' " who=" (Utilities|GetDisplayName :Object Who) " to=" (Utilities|GetDisplayName :Object Ch))')}))
'''
W['ChatterTick'] = '''
(fn ChatterTick ()
  (if (not (Variables|Voice|GetVInit))
    (CallFunction|VoiceInit))
  (CallFunction|PlayerPawns)
  (CallFunction|AmbientTick)
  (CallFunction|EventVoiceTick)
  (CallFunction|GreetTick)
  (CallFunction|VoiceClean)
  (CallFunction|GestureTick)
  (CallFunction|VoiceTestTick))
'''

# ---------------------------------------------------------------- headless test (-GWVoiceTest): a 12 min scripted round
ROOMS = {'hall': (2845, 1485, 130), 'bal': (2925, 3565, 130), 'biblio': (1085, 3405, 130), 'manger': (1085, 1685, 130),
         'billard': (4765, 1685, 130), 'bureau': (5085, 2485, 130), 'jardin': (4605, 3285, 130), 'galerie': (2450, 2170, 630)}
PCX = '(Utilities|Casting|CastToBP_GW_PlayerController (Game|GetPlayerController :PlayerIndex 0))'
PAWN0 = '(Game|GetPlayerPawn :PlayerIndex 0)'


def on_pc(body):
    return f'(bind pc {PCX} (:then {body}) (:CastFailed))'


def tp(room):
    x, y, z = ROOMS[room]
    return log(f'"GW: VOXTEST tp {room}"') + ' ' + \
        on_pc(f'(GW|Call|BP_GW_PlayerController|GWDevTeleport :self pc :X {float(x)} :Y {float(y)} :Z {float(z)})')


NEAREST = SL('Tc', f'(CallFunction|NearestTalker :Loc (Transformation|GetActorLocation :self {PAWN0}) :MaxD 1500.0)')
TALK = (f'{SL("Tc", "(CallFunction|VoiceTestAim :MaxD 900.0)")} ' + log('"GW: VOXTEST talk"') + ' ' +
        on_pc('(GW|Call|BP_GW_PlayerController|TryTalk :self pc)'))
SHOOT = (f'{NEAREST} (bind me0 (Utilities|Casting|CastToBP_GW_Character {PAWN0}) (:then (if ({ISVALID} :Object {L("Tc")}) '
         f'{log(chr(34) + "GW: VOXTEST shoot" + chr(34))} (CallFunction|OnCharacterShot :Shooter me0 :Victim {L("Tc")} '
         f':Dir (Math|Vector|MakeVector 1.0 0.0 0.0)))) (:CastFailed))')
BURN = (f'{NEAREST} (if ({ISVALID} :Object {L("Tc")}) {log(chr(34) + "GW: VOXTEST burn" + chr(34))} '
        f'(CallFunction|Ignite :Ch {L("Tc")} :From (Transformation|GetActorLocation :self {PAWN0})))')
BOOM = (f'{NEAREST} (if ({ISVALID} :Object {L("Tc")}) {log(chr(34) + "GW: VOXTEST boom" + chr(34))} '
        f'(CallFunction|Explode :Loc (Transformation|GetActorLocation :self {L("Tc")}) :Radius 250.0 :Cause "a sauté (test)"))')
EVENT = lambda i: log(f'"GW: VOXTEST event {i}"') + ' ' + on_pc(f'(GW|Call|BP_GW_PlayerController|GWDevEvent :self pc :Id {i})')
PIANO = log('"GW: VOXTEST piano"') + ' ' + on_pc('(GW|Call|BP_GW_PlayerController|GWDevPiano :self pc)')
# the machine runs one game test at a time, 5 min at most (locks.md GAMETEST): three parts of ~4 min of round each
QUICK = on_pc('(GW|Call|BP_GW_PlayerController|GWDevQuickTest :self pc :R 1)')
END = [(108, log('"GW: VOXTEST end"')), (110, '(Development|ExecuteConsoleCommand :Command "quit")')]
TEST_PARTS = {
    # A: conversations around the player, E on NPCs (greet, again, remark, laugh), the bar, the fire
    'A': [(2, '(Variables|GW|SetAutoEvents false)'), (3, QUICK), (5, tp('bal')), (18, TALK), (21, TALK), (24, TALK),
          (27, TALK), (32, tp('billard')), (46, TALK), (52, EVENT(2)), (84, tp('manger')), (92, TALK), (100, tp('jardin'))] + END,
    # B: a guest shot dead (gun lines), the blackout, the bandits' attack
    'B': [(2, '(Variables|GW|SetAutoEvents false)'), (3, QUICK), (5, tp('manger')), (16, SHOOT), (36, tp('biblio')),
          (42, EVENT(3)), (70, TALK), (90, tp('hall')), (94, EVENT(1))] + END,
    # C: a guest on fire (fire lines, never "il a tiré"), the kamikaze, the robot, the piano, an explosion
    'C': [(2, '(Variables|GW|SetAutoEvents false)'), (3, QUICK), (5, tp('jardin')), (12, BURN), (30, tp('bal')),
          (34, EVENT(4)), (70, tp('bureau')), (74, EVENT(5)), (88, tp('bal')), (92, PIANO), (98, tp('billard')),
          (102, BOOM)] + END,
}
W['VoiceTestTick'] = f"""
(fn VoiceTestTick ()
  (if (not (Variables|Voice|GetVTestChecked))
    (Variables|Voice|SetVTestChecked true)
    (Variables|Voice|SetVTestPart (select (Utilities|HasLaunchOption :OptionToCheck "GWVoiceTestA") 1 (select (Utilities|HasLaunchOption :OptionToCheck "GWVoiceTestB") 2 (select (Utilities|HasLaunchOption :OptionToCheck "GWVoiceTestC") 3 0))))
    (Variables|Voice|SetVTestOn (> (Variables|Voice|GetVTestPart) 0)))
  (if (not (Variables|Voice|GetVTestOn))
    (return))
  (bind now {NOW})
  (if (>= now (Variables|Voice|GetVNextLog))
    (Variables|Voice|SetVNextLog (+ now 1.0))
    (CallFunction|VoiceTestLog))
  (if (< now (Variables|Voice|GetVTestNext))
    (return))
  (Variables|Voice|SetVTestNext (+ now 2.0))
  (Variables|Voice|SetVTestStep (+ (Variables|Voice|GetVTestStep) 1))
  (bind st (Variables|Voice|GetVTestStep))
  (bind part (Variables|Voice|GetVTestPart))
""" + '\n'.join(f'  (if (and (== part {k}) (== st {s0}))\n    {c})' for k, steps in ((1, TEST_PARTS['A']), (2, TEST_PARTS['B']), (3, TEST_PARTS['C'])) for s0, c in steps) + ')\n'
W['VoiceTestLog'] = f'''
(fn VoiceTestLog ()
  (bind s (CallFunction|GetGS))
  (for p (Variables|Voice|GetVPl)
    {log('(cat "GW: VOXP t=" (CallFunction|Now) " p=" (Utilities|GetDisplayName :Object p) " loc=" ' + HEAD('p') + ' " ev=" (GW|Get|BP_GW_GameState|EventId :self s) " panic=" (> (GW|Get|BP_GW_GameState|PanicUntil :self s) (CallFunction|Now)))')}))
'''
# the test player walks up to the nearest guest NPC (1.4 m) and looks at it
W['VoiceTestAim'] = f'''
(fn VoiceTestAim (MaxD)
  (bind me {PAWN0})
  (if (not ({ISVALID} :Object me))
    (return {NOCHAR}))
  {SL('BestT', f'(CallFunction|NearestTalker :Loc {LOC("me")} :MaxD MaxD)')}
  (bind t {L('BestT')})
  (if (not ({ISVALID} :Object t))
    (return {NOCHAR}))
  (bind tl {LOC('t')})
  (bind ml {LOC('me')})
  (bind dir (Math|Vector|Normalize (Math|Vector|MakeVector (- (.x ml) (.x tl)) (- (.y ml) (.y tl)) 0.0)))
  (Transformation|SetActorLocation :self me :NewLocation (+ tl (+ (* dir 140.0) (Math|Vector|MakeVector 0.0 0.0 5.0))) :bSweep false :bTeleport true)
  (Pawn|SetControlRotation :self (Game|GetPlayerController :PlayerIndex 0) :NewRotation (Math|Rotator|MakeRotator :Yaw (.yaw (Math|Rotator|FindLookatRotation :Start {LOC('me')} :Target tl))))
  (return t))
'''

W['StaffSay'] = f'''
(fn StaffSay (Cat Ctx Loc)
  (if (not (Variables|Voice|GetVInit))
    (CallFunction|VoiceInit))
  (if (or (< Cat 0) (>= Cat {LEN('VCatFirst')}))
    (return -1))
  (Utilities|Array|Clear (Variables|Default|GetPicks))
  {SL('Best', '0')}
  (bind first {AG('VCatFirst', 'Cat')})
  (for k (range {AG('VCatCount', 'Cat')})
    (bind i (+ first k))
    (bind lc {AG('VBCtx', 'i')})
    (if (or (== lc Ctx) (== lc 0))
      (bind s (+ (select (== lc Ctx) 4 1) (select (> {AG('VUsed', 'i')} 0.0) 0 2)))
      (if (> s {L('Best')})
        (Utilities|Array|Clear (Variables|Default|GetPicks))
        {SL('Best', 's')}
        (Utilities|Array|Add :TargetArray (Variables|Default|GetPicks) :NewItem i)
        (elif (== s {L('Best')})
          (Utilities|Array|Add :TargetArray (Variables|Default|GetPicks) :NewItem i)))))
  (bind n (Utilities|Array|Length (Variables|Default|GetPicks)))
  (if (== n 0)
    (return -1))
  (bind idx (Utilities|Array|Get(acopy) (Variables|Default|GetPicks) (Math|Random|RandomIntegerinRange 0 (- n 1))))
  {SETE('VUsed', 'idx', '(Math|Float|Max(Float) ' + NOW + ' 0.01)')}
  (bind a (Game|SpawnActorfromClass :Class "{CUE}" :SpawnTransform (Math|Transform|MakeTransform :Location Loc) :CollisionHandlingOverride "AlwaysSpawn"))
  (GW|Set|BP_GW_SoundCue|Idx :self a :Idx idx)
  {log('(cat "GW: VOX t=" ' + NOW + ' " pri=5 cat=" Cat " cause=0 conv=0 idx=" idx " dur=" ' + AG('VBDur', 'idx') + ' " voice=" ' + VNAME(AG('VBVoice', 'idx')) + ' " svoice=world nv=0 gun=0 test=0 kind=9 pd=" (CallFunction|NearPlayerD :Loc Loc) " loc=" Loc " spk=staff" Ctx " text=" ' + AG('VBText', 'idx') + ')')}
  (return idx))
'''
# dev menu (u15, Son page): a conversation here now (the area's silence is lifted), and where the bank stands
W['DevVoiceChat'] = f'''
(fn DevVoiceChat (Loc)
  (bind now {NOW})
  (for i (range {LEN('VAHold')})
    (if (< {DIST(AG('VALoc', 'i'), 'Loc')} {R_AREA})
      {SETE('VAHold', 'i', 'now')}))
  (CallFunction|PlayerPawns)
  (bind pl (+ Loc (Math|Vector|MakeVector 0.0 0.0 60.0)))
  {SV('VAmbA', f'(CallFunction|FindSpeaker :Loc pl :MaxD {R_SPEAK} :Moving false)')}
  {log('(cat "GW: VOXDEV chat near " Loc " speaker=" (Utilities|GetDisplayName :Object (Variables|Voice|GetVAmbA)))')}
  (CallFunction|AmbientWith :PL pl :A (Variables|Voice|GetVAmbA)))
'''
W['DevVoiceState'] = f'''
(fn DevVoiceState ()
  (if (not (Variables|Voice|GetVInit))
    (CallFunction|VoiceInit))
  (bind test (Variables|Voice|GetVTestMode))
  {SL('N', '0')}
  {SL('U', '0')}
  {SL('D', '0')}
  (for i (range {LEN('VUsed')})
    (if (and (== {AG('VBNV', 'i')} 0) (and (>= {AG('VBVoice', 'i')} 0) (or test (== {AG('VBTest', 'i')} 0))))
      {SL('N', f"(+ {L('N')} 1)")}
      (if (> {AG('VUsed', 'i')} 0.0)
        {SL('U', f"(+ {L('U')} 1)")})))
  (for d (range {LEN('VDlgFirst')})
    (bind f {AG('VDlgFirst', 'd')})
    (if (and (<= {AG('VUsed', 'f')} 0.0) (or test (== {AG('VBTest', 'f')} 0)))
      {SL('D', f"(+ {L('D')} 1)")}))
  (bind msg (cat (cat (cat "Voix : " {L('U')}) (cat " répliques dites sur " {L('N')})) (cat (cat ", " {L('D')}) (cat " dialogues encore inédits, " (cat (Variables|Voice|GetVLines) " prises de parole")))))
  {log('(cat "GW: VOXDEV state " msg)')}
  (CallFunction|Announce :Text msg))
'''

# UE_ARGS: nopc (the player controller is locked by another agent: do it later with pconly), pconly, nosave,
# chonly (only the character's voice functions: no game mode or player controller compile)
CH_ONLY = 'chonly' in UE_ARGS
DO_GM = 'pconly' not in UE_ARGS
DO_PC = 'nopc' not in UE_ARGS and not CH_ONLY
if DO_GM:
    for name, code in ({} if CH_ONLY else W).items():
        write(gm, name, code, compile_after=False)
    if not CH_ONLY:
        compile_bp(gm)
    KEYS = ('Voice', 'Say', 'Talk', 'Panic', 'Cue', 'Line', 'Pick', 'Ambient', 'Area', 'Hush', 'Utter', 'Dialogue', 'Death',
            'Event', 'Speaker', 'Partner', 'Sound', 'Walk', 'Pending', 'Alarm', 'Cause', 'Hold', 'Busy', 'Commit', 'Schedule')
    if not CH_ONLY:
        print('BP_GW_GameMode', [p for p in node_problems(gm) if any(k in p for k in KEYS)][:40])

    for name, code in CHW.items():
        write(ch, name, code, compile_after=False)
    compile_bp(ch)
    print('BP_GW_Character', [p for p in node_problems(ch) if 'Cue' in p])
    if 'nosave' not in UE_ARGS:
        save(*((ch, gs) if CH_ONLY else (gm, ch, gs)))
        print('s39 saved', 'character, game state' if CH_ONLY else 'GM, character, game state')

# ================================================================ player controller: E on a guest NPC
if not DO_PC:
    print('s39: player controller skipped (nopc)')
else:
    ensure_var(pc, 'NoTalkChar', obj_class=chc, category='Voice')
    ensure_var(pc, 'TalkAim', obj_class=chc, category='Voice')
    ensure_fn(pc, 'TryTalk', outputs=[('Handled', 'bool')])
    ensure_fn(pc, 'TalkTarget', inputs=[('Me', chc)], outputs=[('Ch', chc)])
    ensure_fn(pc, 'GWTalk', exec_fn=True)
    compile_bp(pc, quiet=True)
    g = get_graph(pc, 'TalkTarget')
    have = [str(x) for x in BT.list_variables(pc, g)]
    if 'BestD' not in have:
        BT.add_variable(pc, 'BestD', 'float', graph=g)
    if 'BestT' not in have:
        BT.add_object_variable(pc, 'BestT', chc, graph=g)
    PCW = {
        # the guest NPC in front of me within 2.6 m (the server checks again with its own copy of the view)
        'TalkTarget': f'''
    (fn TalkTarget (Me)
      (bind here (Transformation|GetActorLocation :self Me))
      (bind fwd (Math|Vector|GetForwardVector (Pawn|GetControlRotation :self self)))
      (bind f2 (Math|Vector|Normalize (Math|Vector|MakeVector (.x fwd) (.y fwd) 0.0)))
      (Variables|Default|SetBestD {TALK_RANGE})
      (Variables|Default|SetBestT (Variables|Voice|GetNoTalkChar))
      (for c (Actor|GetAllActorsOfClass :ActorClass {CHAR})
        (if (and (!= c Me) (and (not (GW|Get|BP_GW_Character|IsDead :self c)) (== (GW|Get|BP_GW_Character|Kind :self c) 0)))
          (bind cl (Transformation|GetActorLocation :self c))
          (bind d (Math|Vector|Distance2D(Vector) cl here))
          (bind dz (- (.z cl) (.z here)))
          (if (and (and (< d (Variables|Default|GetBestD)) (< (* dz dz) 14400.0)) (> (Math|Vector|DotProduct f2 (Math|Vector|Normalize (Math|Vector|MakeVector (- (.x cl) (.x here)) (- (.y cl) (.y here)) 0.0))) 0.55))
            (Variables|Default|SetBestD d)
            (Variables|Default|SetBestT c))))
      (return (Variables|Default|GetBestT)))
    ''',
        'TryTalk': f'''
    (fn TryTalk ()
      (bind ch {MYCH}
        (:then
          (if (or (GW|Get|BP_GW_Character|IsDead :self ch) (GW|Get|BP_GW_Character|IsSeeker :self ch))
            (return false))
          (Variables|Voice|SetTalkAim (CallFunction|TalkTarget :Me ch))
          (if (not ({ISVALID} :Object (Variables|Voice|GetTalkAim)))
            (return false))
          ; face who I speak to, like any guest (this machine owns the pawn's rotation)
          (Transformation|SetActorRotation :self ch :NewRotation (Math|Rotator|MakeRotator :Yaw (.yaw (Math|Rotator|FindLookatRotation :Start (Transformation|GetActorLocation :self ch) :Target (Transformation|GetActorLocation :self (Variables|Voice|GetTalkAim))))) :bTeleportPhysics false)
          (if (Networking|HasAuthority)
            (CallFunction|GWTalk)
            (else
              (Development|ExecuteConsoleCommand :Command "ServerExec GWTalk" :SpecificPlayer self)))
          (return true))
        (:CastFailed (return false))))
    ''',
        'GWTalk': f'''
    (fn GWTalk ()
      (bind ch {MYCH}
        (:then
          (if (or (GW|Get|BP_GW_Character|IsDead :self ch) (GW|Get|BP_GW_Character|IsSeeker :self ch))
            (return))
          (bind t (CallFunction|TalkTarget :Me ch))
          (if (not ({ISVALID} :Object t))
            (Development|PrintString :InString "GW: VOXTALK refused (nobody in front)" :bPrintToScreen false)
            (return))
          (bind gm {GMC}
            (:then (GW|Call|BP_GW_GameMode|TalkTo :self gm :Who ch :Ch t))
            (:CastFailed)))
        (:CastFailed)))
    ''',
    }
    for name, code in PCW.items():
        write(pc, name, code, compile_after=False)
    compile_bp(pc)
    print('BP_GW_PlayerController', [p for p in node_problems(pc) if 'Talk' in p])

    if 'nosave' not in UE_ARGS:
        save(pc)
        print('s39 saved the player controller')
