"""NPC voices and reactions: the sound bank, voice cues on characters, world sound cues, panic flight, corpses.

Sound bank (built by Tools/gameplay/voice_bank.py from AssetGen/audio/final/*/*_report.json, imported to
/Game/GW/Audio/Gen/<category>/): one entry per line, sorted by category so each category is one range.
- BP_GW_GameState class defaults (every machine): BankSounds / BankCat / BankFem (0 man, 1 woman, 2 any) / BankText
  (subtitles) / BankVox (1 = a voice line: one mouth, subtitles).
- BP_GW_GameMode class defaults (server): BankCat / BankFem / BankGun and the director's tables VB* (voice index,
  dialogue, turn, speaker, duration, cause, non-verbal, test-only, whispered, text), VCatFirst / VCatCount (category
  ranges), VVoiceName / VVoiceFem (voice = character id: char_colonel...), VDlgFirst / VDlgN / VDlgVA / VDlgVB.
- Voices: BP_GW_Character.Cue (RepNotify) = sequence * 10000 + bank index (9999 = stop talking); OnRep plays it on the
  character's head on every machine (3D, ATT_GW_Voice). WHO says WHAT and WHEN is the voice director's job
  (s39_voice_director.py: Say, QueueSay, PickSound, WorldSound, StartPanic, SayNearPlayers, DeathCry, ProcessCue,
  PanicTick, ChatterTick, OnRep_Cue). This script runs s39 at its end, so a re-run keeps the director.
- World sounds (piano, explosions...): BP_GW_SoundCue, a replicated actor whose Idx (RepNotify) plays at its location.
- Voices do not carry into other rooms: ATT_GW_Voice is short (3.5 m full, 13 m falloff) with occlusion traced on the
  Camera channel (walls block it, people do not: a crowd or the listener's own body must not muffle a voice);
  ATT_GW_Far (screams, piano, explosions) is occluded too.
- Corpses (CorpseTick): a body is removed 20 s after death (piles of ragdolls cost frames after an explosion).
ReactionsTick runs all of it from BP_GW_GameMode.RoundTick (s12_gamemode.py).
Usage: ue_run.py s31_reactions.py [fakebank | importonly | tablesonly]
  fakebank: adds test-only lines (used with -GWVoiceFakeBank); importonly: imports the WAVs, touches no Blueprint;
  tablesonly: imports, then only the bank arrays of GameState + GameMode (no graph written: for new lines between
  two full runs).
"""
import sys, importlib, json, os, glob, re
sys.path.insert(0, r'J:\Projets\Unreal_Projects\Guess Who\Tools\gameplay')
import gw_lib; importlib.reload(gw_lib)
from gw_lib import *
import voice_bank as VB; importlib.reload(VB)

try:
    UE_ARGS
except NameError:
    UE_ARGS = []
REP = unreal.BlueprintVariableReplication
CHAR = '"/Game/GW/Blueprints/BP_GW_Character.BP_GW_Character_C"'
NPCC = '"/Game/GW/Blueprints/BP_GW_NPCController.BP_GW_NPCController_C"'
CUE = '/Game/GW/Blueprints/BP_GW_SoundCue.BP_GW_SoundCue_C'
ISVALID = 'GW|Call|/Script/Engine.KismetSystemLibrary|IsValid'
GSC = '(Utilities|Casting|CastToBP_GW_GameState (Game|GetGameState))'
AUDIO = '/Game/GW/Audio'
GEN = f'{AUDIO}/Gen'
CAT = VB.CAT                                               # category ids, shared with s39 and the feature scripts
MUSIC = {}                                                 # file stem -> imported looping SoundWave (event music)
VOICE_CATS = VB.VOICE_CATS
# until the generated sounds exist, these keep the systems audible
PLACEHOLDER = {'gunshot': ['S_GW_Gunshot'], 'explosion': ['S_GW_Thud'], 'fire_loop': ['AMB_Fire'], 'sting': ['S_GW_Gong'],
               'piano': ['S_GW_Sombre'], 'power_down': ['S_GW_Thud'], 'power_up': ['S_GW_Chime'], 'laser': ['S_UI_Confirm'],
               'robot_step': ['S_GW_Thud']}
EAL_ = unreal.EditorAssetLibrary
AT = unreal.AssetToolsHelpers.get_asset_tools()


def attenuation(name, inner, falloff, occl=0.15):
    p = f'{AUDIO}/{name}'
    a = unreal.load_asset(p) if EAL_.does_asset_exist(p) else AT.create_asset(name, AUDIO, unreal.SoundAttenuation, unreal.SoundAttenuationFactory())
    s = a.get_editor_property('attenuation')
    s.set_editor_property('attenuation_shape_extents', unreal.Vector(inner, 0, 0))
    s.set_editor_property('falloff_distance', falloff)
    # a wall between speaker and listener: quieter and muffled (the user: "no voices from another room"). Traced on the
    # Camera channel: walls block it, characters do not (on Visibility the listener's own body and any guest standing
    # in between muffled the voices too: UE ignores only the sound's owner in that trace)
    for k, v in (('enable_occlusion', True), ('occlusion_trace_channel', unreal.CollisionChannel.ECC_CAMERA),
                 ('occlusion_volume_attenuation', occl), ('occlusion_low_pass_filter_frequency', 900.0),
                 ('occlusion_interpolation_time', 0.25)):
        try:
            s.set_editor_property(k, v)
        except Exception as e:
            print('   attenuation skip', k, e)
    a.set_editor_property('attenuation', s)
    EAL_.save_loaded_asset(a, False)
    return a


ATT_VOICE = attenuation('ATT_GW_Voice', 350.0, 1300.0, 0.08)  # the room you are in; through a wall: barely
ATT_FAR = attenuation('ATT_GW_Far', 1200.0, 7000.0, 0.35)     # the whole manor, louder near the source, muffled by walls
SC = {n: unreal.load_asset(f'{AUDIO}/Classes/{n}') for n in ('SC_GW_Voice', 'SC_GW_SFX')}


def fresh_import(path, folder, name):
    """Import a WAV, again when the source file changed since (re-mastered files keep their names)."""
    dest = f'{folder}/{name}'
    stamp = f'{os.path.getsize(path)}|{int(os.path.getmtime(path))}'
    if EAL_.does_asset_exist(dest) and EAL_.get_metadata_tag(unreal.load_asset(dest), 'GWSrcStamp') == stamp:
        return unreal.load_asset(dest)
    t = unreal.AssetImportTask()
    t.filename = path; t.destination_path = folder; t.automated = True; t.replace_existing = True; t.save = False
    AT.import_asset_tasks([t])
    s = unreal.load_asset(dest)
    EAL_.set_metadata_tag(s, 'GWSrcStamp', stamp)
    return s


def import_music(path):
    s = fresh_import(path, f'{GEN}/music', os.path.splitext(os.path.basename(path))[0])
    s.set_editor_property('sound_class_object', unreal.load_asset(f'{AUDIO}/Classes/SC_GW_Music'))
    s.set_editor_property('looping', True)
    EAL_.save_loaded_asset(s, False)
    return s


def import_wav(path, cat_name):
    s = fresh_import(path, f'{GEN}/{cat_name}', os.path.splitext(os.path.basename(path))[0])
    voice = CAT[cat_name] in VOICE_CATS
    s.set_editor_property('sound_class_object', SC['SC_GW_Voice' if voice else 'SC_GW_SFX'])
    near = ('robot_step', 'servo', 'ball_clack', 'sword_swish', 'sword_hit', 'swap_whoosh', 'safe_open')
    s.set_editor_property('attenuation_settings', ATT_VOICE if voice or cat_name in near else ATT_FAR)
    if cat_name in ('fire_loop', 'fire_alarm'):
        s.set_editor_property('looping', True)
    EAL_.save_loaded_asset(s, False)
    return s


# ---------------------------------------------------------------- the bank
B = VB.build(fake=1.0 if 'fakebank' in UE_ARGS else 0)
for p in B['music']:
    MUSIC[os.path.splitext(os.path.basename(p))[0]] = import_music(p)
have = {l['cat'] for l in B['lines']}
for cat_name, names in PLACEHOLDER.items():
    if cat_name not in have:
        for n in names:
            B['lines'].append(dict(path=None, asset=f'{AUDIO}/{n}', stem=n, cat=cat_name, cat_id=CAT[cat_name], fem=2,
                                   voice=None, text='', dur=1.0, cause=0, dlg=None, turn=0, spk=0, nv=False, gun=False,
                                   wh=False, test=False, key=n))
order = {d: i for i, d in enumerate(B['dialogues'])}
B['lines'].sort(key=VB.sort_key(order))
imported = {}
sounds = []
for l in B['lines']:
    if l['path'] is None:
        sounds.append(unreal.load_asset(l['asset']))
        continue
    if l['path'] not in imported:                          # test lines reuse a real file: one asset per file
        imported[l['path']] = import_wav(l['path'], l['cat'])
    sounds.append(imported[l['path']])
T = VB.tables(B)
print('bank', len(sounds), 'sounds; voices', len(T['VVoiceName']), T['VVoiceName'][:24], '; dialogues', len(T['VDlgFirst']),
      '; test lines', sum(T['VBTest']), '; skipped', B['skipped'])
print('by category', {k: T['VCatCount'][v] for k, v in CAT.items() if v < VB.NCAT and T['VCatCount'][v]})
if 'importonly' in UE_ARGS:
    # the long part (hundreds of WAVs) without touching any Blueprint: no BP lock needed; run again without it after
    print('importonly: assets imported, Blueprints untouched (the "stop" error below is expected)')
    raise RuntimeError('importonly stop')

# ---------------------------------------------------------------- game state: the bank (class defaults)
gsb = load_bp('BP_GW_GameState')
ensure_var(gsb, 'BankSounds', obj_class=unreal.SoundBase, array=True, category='Audio')
for v, t in (('BankCat', 'int'), ('BankFem', 'int'), ('BankVox', 'int'), ('BankCtx', 'int')):
    ensure_var(gsb, v, t, array=True, category='Audio')
ensure_var(gsb, 'PanicUntil', 'float', rep=REP.REPLICATED, category='GW')
compile_bp(gsb, quiet=True)
g = cdo(gsb)
g.set_editor_property('BankSounds', sounds)
g.set_editor_property('BankCat', T['BankCat'])
g.set_editor_property('BankFem', T['BankFem'])
g.set_editor_property('BankVox', T['BankVox'])
g.set_editor_property('BankCtx', T['VBCtx'])      # line context (staff moments: s34's local open line)
compile_bp(gsb, quiet=True)
save(gsb)
if 'tablesonly' in UE_ARGS:
    # new lines only (no graph changed since the last full run): the bank arrays on the game mode, nothing else
    gm = load_bp('BP_GW_GameMode')
    gm_cdo = cdo(gm)
    for k, v in T.items():
        if k != 'BankVox':
            gm_cdo.set_editor_property(k, v)
    compile_bp(gm)
    save(gm)
    print('tablesonly: GameState + GameMode bank tables saved;', len(sounds), 'sounds,', len(T['VDlgFirst']), 'dialogues')
    raise RuntimeError('tablesonly stop (expected)')

# ---------------------------------------------------------------- world sound cue actor
sc = load_or_create_bp('BP_GW_SoundCue', unreal.Actor)
ensure_var(sc, 'Idx', 'int', rep=REP.REP_NOTIFY, category='GW')
ensure_fn(sc, 'OnRep_Idx')
compile_bp(sc, quiet=True)
scd = cdo(sc)
scd.set_editor_property('replicates', True)
scd.set_editor_property('always_relevant', True)
scd.set_editor_property('initial_life_span', 20.0)
write(sc, 'OnRep_Idx', f'''
(fn OnRep_Idx ()
  (bind s {GSC}
    (:then
      (bind snds (GW|Get|BP_GW_GameState|BankSounds :self s))
      (if (and (>= (Variables|GW|GetIdx) 0) (< (Variables|GW|GetIdx) (Utilities|Array|Length snds)))
        (Audio|PlaySoundatLocation :Sound (Utilities|Array|Get(acopy) snds (Variables|GW|GetIdx)) :Location (Transformation|GetActorLocation :self self))))
    (:CastFailed)))
''', compile_after=False)
compile_bp(sc)
print('BP_GW_SoundCue', node_problems(sc))
save(sc)

# ---------------------------------------------------------------- character: voice cue (OnRep_Cue body: s39)
ch = load_bp('BP_GW_Character')
ensure_var(ch, 'Cue', 'int', rep=REP.REP_NOTIFY, category='GW')
ensure_fn(ch, 'OnRep_Kind')                                          # body: s32_events.py (special looks)
ensure_var(ch, 'Kind', 'int', rep=REP.REP_NOTIFY, category='GW')       # 0 guest NPC / player, 1 bandit, 2 kamikaze, 3 robot
ensure_var(ch, 'PickStamp', 'int', category='GW')
ensure_var(ch, 'DeadSince', 'float', category='GW')
ensure_var(ch, 'ShotSeen', 'int', category='GW')
ensure_var(ch, 'GenFemale', 'bool', array=True, category='Costume')
ensure_fn(ch, 'OnRep_Cue')
compile_bp(ch, quiet=True)
save(ch)

# ---------------------------------------------------------------- NPC controller: panic state (Think reads it)
npc = load_bp('BP_GW_NPCController')
ensure_var(npc, 'PanicUntil', 'float', category='GW')
ensure_var(npc, 'PanicFrom', struct=unreal.Vector.static_struct(), category='GW')
compile_bp(npc, quiet=True)
save(npc)

# ---------------------------------------------------------------- game mode
gm = load_bp('BP_GW_GameMode')
chc = ch.generated_class()
for v, t in (('NextChat', 'float'), ('PanicCalmAt', 'float'), ('Stamp', 'int')):
    ensure_var(gm, v, t, category='GW')
ensure_var(gm, 'LastSaid', 'int', array=True, category='GW')
ensure_var(gm, 'NoChar', obj_class=chc, category='GW')
ensure_var(gm, 'NextCorpse', 'float', category='GW')
ensure_var(gm, 'GunContext', 'bool', category='GW')
for v in ('BankGun', 'BankCat', 'BankFem'):
    ensure_var(gm, v, 'int', array=True, category='GW')        # the server's copy of the bank tags
V3 = unreal.Vector.static_struct()
# speech functions: bodies in s39_voice_director.py (run below)
ensure_fn(gm, 'PickSound', inputs=[('Cat', 'int'), ('Fem', 'int')], outputs=[('Idx', 'int')])
ensure_fn(gm, 'GenderOf', inputs=[('Ch', chc)], outputs=[('Fem', 'int')])
ensure_fn(gm, 'Say', inputs=[('Ch', chc), ('Cat', 'int')])
ensure_fn(gm, 'QueueSay', inputs=[('Ch', chc), ('Cat', 'int'), ('Delay', 'float')])
ensure_fn(gm, 'WorldSound', inputs=[('Cat', 'int'), ('Loc', V3)])
ensure_fn(gm, 'NearestNPC', inputs=[('Loc', V3), ('MaxD', 'float')], outputs=[('Ch', chc)])
ensure_fn(gm, 'StartPanic', inputs=[('Loc', V3), ('Dur', 'float')])
ensure_fn(gm, 'SayNearPlayers', inputs=[('Cat', 'int'), ('PerPlayer', 'int'), ('Delay', 'float'), ('Spread', 'float')])
for f in ('ProcessCue', 'PanicTick', 'ChatterTick', 'ReactionsTick', 'PianoTick', 'CorpseTick'):    # PianoTick: s33_piano.py
    ensure_fn(gm, f)
# hooks for the feature scripts (Tools/AGENTS_GAMEPLAY.md): s34_shop.py, s36_social.py, s35_turret.py own their bodies
for f in ('ShopTick', 'SocialTick', 'TurretTick', 'ShotWatchTick', 'PickupTick'):    # PickupTick: s38_pickups.py
    ensure_fn(gm, f)
ensure_fn(gm, 'RewardNPCKill', inputs=[('Killer', unreal.Pawn), ('Victim', chc)])     # body: s34_shop.py
ensure_fn(gm, 'DeathCry', inputs=[('Victim', chc)])
compile_bp(gm, quiet=True)
gr = get_graph(gm, 'NearestNPC')
if 'BestD' not in BT.list_variables(gm, gr):
    BT.add_variable(gm, 'BestD', 'float', graph=gr)
if 'BestT' not in BT.list_variables(gm, gr):
    BT.add_object_variable(gm, 'BestT', chc, graph=gr)
# the director's tables (class defaults; the variables are declared by s39, so run it first on a fresh project)
gm_cdo = cdo(gm)
for k, v in T.items():
    if k in ('BankVox',):
        continue
    try:
        gm_cdo.set_editor_property(k, v)
    except Exception as e:
        print('   (table', k, 'not set yet:', str(e)[:80], ')')

W = {
    'GenderOf': '''
(fn GenderOf (Ch)
  (if (or (GW|Get|BP_GW_Character|IsSeeker :self Ch) (!= (GW|Get|BP_GW_Character|Kind :self Ch) 0))
    (return 0))
  (bind oi (GW|Get|BP_GW_Character|OutfitIndex :self Ch))
  (bind fem (GW|Get|BP_GW_Character|GenFemale :self Ch))
  (if (and (>= oi 0) (< oi (Utilities|Array|Length fem)))
    (return (select (Utilities|Array|Get(acopy) fem oi) 1 0)))
  (return 0))
''',
    # nearest living guest NPC not picked yet in this batch (Stamp)
    'NearestNPC': f'''
(fn NearestNPC (Loc MaxD)
  (Variables|Default|SetBestD MaxD)
  (Variables|Default|SetBestT (Variables|GW|GetNoChar))
  (for a (Actor|GetAllActorsOfClass :ActorClass {CHAR})
    (if (and (and (not (Pawn|IsPlayerControlled :self a)) (not (GW|Get|BP_GW_Character|IsDead :self a))) (and (== (GW|Get|BP_GW_Character|Kind :self a) 0) (!= (GW|Get|BP_GW_Character|PickStamp :self a) (Variables|GW|GetStamp))))
      (bind d (Math|Vector|Distance(Vector) (Transformation|GetActorLocation :self a) Loc))
      (if (< d (Variables|Default|GetBestD))
        (Variables|Default|SetBestD d)
        (Variables|Default|SetBestT a))))
  (bind t (Variables|Default|GetBestT))
  (if ({ISVALID} :Object t)
    (GW|Set|BP_GW_Character|PickStamp :self t :PickStamp (Variables|GW|GetStamp)))
  (return t))
''',
    'ReactionsTick': '''
(fn ReactionsTick ()
  (Variables|GW|SetGunContext false)
  (CallFunction|ProcessCue)
  (CallFunction|ProcessCue)
  (CallFunction|ProcessCue)
  (CallFunction|PanicTick)
  (CallFunction|PianoTick)
  (CallFunction|ChatterTick)
  (CallFunction|CorpseTick)
  (CallFunction|ShotWatchTick)
  (CallFunction|ShopTick)
  (CallFunction|SocialTick)
  (CallFunction|TurretTick)
  (CallFunction|PickupTick))
''',
    # a shot anywhere (ShotCounter moved on any character) = the whole manor panics 10 s; while a fresh panic is
    # still running, no new round of screams (bandits fire every second)
    'ShotWatchTick': f'''
(fn ShotWatchTick ()
  (for c (Actor|GetAllActorsOfClass :ActorClass {CHAR})
    (if (!= (GW|Get|BP_GW_Character|ShotCounter :self c) (GW|Get|BP_GW_Character|ShotSeen :self c))
      (GW|Set|BP_GW_Character|ShotSeen :self c :ShotSeen (GW|Get|BP_GW_Character|ShotCounter :self c))
      ; tense music for 25 s after any shot (u14 MusicTick)
      (GW|Set|BP_GW_GameState|TenseUntil :self (CallFunction|GetGS) :TenseUntil (+ (GameState|GetServerWorldTimeSeconds :self (CallFunction|GetGS)) 25.0))
      (if (< (GW|Get|BP_GW_GameState|PanicUntil :self (CallFunction|GetGS)) (+ (CallFunction|Now) 4.0))
        (Development|PrintString :InString (cat "GW: gunshot panic from " (Utilities|GetDisplayName :Object c)) :bPrintToScreen false)
        (Variables|GW|SetGunContext true)
        (CallFunction|StartPanic :Loc (Transformation|GetActorLocation :self c) :Dur 10.0)
        (Variables|GW|SetGunContext false)))))
''',
    'CorpseTick': f'''
(fn CorpseTick ()
  (if (< (CallFunction|Now) (Variables|GW|GetNextCorpse))
    (return))
  (Variables|GW|SetNextCorpse (+ (CallFunction|Now) 2.0))
  (for c (Actor|GetAllActorsOfClass :ActorClass {CHAR})
    (if (and (GW|Get|BP_GW_Character|IsDead :self c) (not (Pawn|IsPlayerControlled :self c)))
      (if (<= (GW|Get|BP_GW_Character|DeadSince :self c) 0.0)
        (GW|Set|BP_GW_Character|DeadSince :self c :DeadSince (CallFunction|Now))
        (elif (> (- (CallFunction|Now) (GW|Get|BP_GW_Character|DeadSince :self c)) 20.0)
          (Actor|DestroyActor :self c))))))
''',
}
W.pop('CorpseTick')      # s44_npc_life.py renders it now (a corpse goes when nobody sees it)
for name, code in W.items():
    write(gm, name, code, compile_after=False)
    compile_bp(gm, quiet=True)
compile_bp(gm)
print('BP_GW_GameMode', [p for p in node_problems(gm) if any(k in p for k in W)])
save(gm)

# ---------------------------------------------------------------- the voice director (speech bodies, tables it declares)
_s39 = r'J:\Projets\Unreal_Projects\Guess Who\Tools\gameplay\s39_voice_director.py'
exec(compile(open(_s39, encoding='utf-8').read(), _s39, 'exec'), {'UE_ARGS': [a for a in UE_ARGS if a in ('nosave', 'nopc')], '__file__': _s39, '__name__': '__s39__'})
gm = load_bp('BP_GW_GameMode')
gm_cdo = cdo(gm)
for k, v in T.items():
    if k != 'BankVox':
        gm_cdo.set_editor_property(k, v)
compile_bp(gm, quiet=True)
save(gm)
print('categories', {k: v for k, v in CAT.items() if v < VB.NCAT})
