"""The user's test feedback of 2026-11-05: what can't go through its owner script cheaply (the texts stay in their owners, this re-renders only the graphs
that changed: running s32, s38 or s39 in full rewrites far more). Re-runnable. Order after a change (s41 last, it restores the models):
  python ue_run.py s42_feedback5.py audio icons / s34_shop.py fx / s40_inventory.py fx ps ch ui / s42_feedback5.py ch robot s38 s39 s34gm /
  s40_events2.py ch gm / s40_inventory.py gm pc / s41_item_models.py / ui\\u14_hud.py graph / ui\\u17_shop_ui.py / ui\\u15_dev_menu.py pc, data
Parts:
  audio  imports AssetGen/audio/final/feedback5 (Tools/audio/fb5_sounds.py) and the study's ambience without its clock
  icons  imports Props (images)/icons (Tools/props/item_icons.py) as /Game/GW/UI/Items/T_UI_Item_NN
  ch     BP_GW_Character.OnRep_IsDead (s11)
  robot  BP_GW_Beam, BP_GW_RobotController, the robot's game mode graphs, EventEvery (s32)
  s38    WeaponHit, SlashTarget, GWPickup      s39  EventVoiceTick      s34gm  UseGas, GasScale
"""
import sys, importlib, os, re, textwrap
sys.path.insert(0, r'J:\Projets\Unreal_Projects\Guess Who\Tools\gameplay')
import gw_lib; importlib.reload(gw_lib)
from gw_lib import *

ARGS = set(UE_ARGS)
ROOT = r'J:\Projets\Unreal_Projects\Guess Who'
TOOLS = ROOT + r'\Tools'
AT = unreal.AssetToolsHelpers.get_asset_tools()
FB = ROOT + r'\AssetGen\audio\final\feedback5'
SC_SFX = '/Game/GW/Audio/Classes/SC_GW_SFX'
ATT_V = '/Game/GW/Audio/ATT_GW_Voice'


def src(rel):
    return open(os.path.join(TOOLS, 'gameplay', rel), encoding='utf-8').read().replace('\r\n', '\n')


def rewrite(bp, name, code):
    """One graph, from its owner's text, whatever the graph holds now."""
    g = get_graph(bp, name)
    for node in list(BT.find_nodes(g)):
        if node.get_class().get_name() in ('K2Node_FunctionEntry', 'K2Node_FunctionResult'):
            for pin in node.list_all_pins():
                for other in list(pin.list_connected_pins()):
                    pin.break_single_pin_link(other)
            continue
        BT.delete_node(node)
    write(bp, name, code, compile_after=False)
    print(' ', bp.get_name(), name, [p for p in node_problems(bp) if name in p])


def imp(wav, dest, name, sc=SC_SFX, att=None, looping=False):
    t = unreal.AssetImportTask()
    t.filename = wav; t.destination_path = dest; t.destination_name = name; t.automated = True; t.replace_existing = True; t.save = False
    AT.import_asset_tasks([t])
    s = unreal.load_asset(f'{dest}/{name}')
    s.set_editor_property('sound_class_object', unreal.load_asset(sc))
    if att:
        s.set_editor_property('attenuation_settings', unreal.load_asset(att))
    s.set_editor_property('looping', looping)
    print('sound', dest, name, EAL.save_loaded_asset(s, False), s.get_editor_property('duration'))


if 'audio' in ARGS:
    for i in (1, 2, 3):
        imp(f'{FB}\\SFX_Zombie_Moan_{i:02d}.wav', '/Game/GW/Audio/Gen/zombie', f'SFX_Zombie_Moan_{i:02d}', att=ATT_V)
    imp(f'{FB}\\SFX_Shot_Hit.wav', '/Game/GW/Audio/Gen/sting', 'SFX_Shot_Hit')
    for i in (1, 2, 3, 4):
        imp(f'{FB}\\SFX_Robot_Step_{i:02d}.wav', '/Game/GW/Audio/Gen/robot_step', f'SFX_Robot_Step_{i:02d}', att=ATT_V)
    imp(f'{FB}\\SFX_Charge_Laser.wav', '/Game/GW/Audio/Gen/inv', 'SFX_Charge_Laser', att=ATT_V)
    imp(ROOT + r'\AssetGen\audio\final\ambience\AMB_Room_Study.wav', '/Game/GW/Audio', 'AMB_Room_Study', sc='/Game/GW/Audio/Classes/SC_GW_Ambience', looping=True)

if 'icons' in ARGS:
    D = ROOT + r'\Props (images)\icons'
    for f in sorted(os.listdir(D)):
        if not (f.endswith('.png') and f[:2].isdigit()):
            continue
        nm = f'T_UI_Item_{f[:2]}'
        t = unreal.AssetImportTask()
        t.filename = os.path.join(D, f); t.destination_path = '/Game/GW/UI/Items'; t.destination_name = nm; t.automated = True; t.replace_existing = True; t.save = False
        AT.import_asset_tasks([t])
        x = unreal.load_asset(f'/Game/GW/UI/Items/{nm}')
        x.set_editor_property('lod_group', unreal.TextureGroup.TEXTUREGROUP_UI)
        x.set_editor_property('compression_settings', unreal.TextureCompressionSettings.TC_EDITOR_ICON)
        x.set_editor_property('mip_gen_settings', unreal.TextureMipGenSettings.TMGS_NO_MIPMAPS)
        x.set_editor_property('never_stream', True)
        print('icon', nm, EAL.save_loaded_asset(x, False))

if 'ch' in ARGS:
    ch = load_bp('BP_GW_Character')
    rewrite(ch, 'OnRep_IsDead', re.search(r"W\['OnRep_IsDead'\] = '''(.*?)'''", src('s11_character.py'), re.S).group(1))
    print('BP_GW_Character', compile_bp(ch))
    save(ch)

if 'robot' in ARGS:
    S = src('s32_events.py')
    block = lambda a, b: S[S.index(a):S.index(b)]
    ns = dict(globals())
    exec(block('REP = unreal.BlueprintVariableReplication', 'def mi('), ns)
    exec(block('def mi(', 'MI_LASER = ') + S[S.index('MI_LASER = '):S.index('MI_BLAST = ')], ns)
    for fn in ('actor_bp', 'mesh', 'light'):
        exec(re.search(r'^def %s\(.*?(?=^\S)' % fn, S, re.S | re.M).group(0), ns)
    ns['ch'] = load_bp('BP_GW_Character')
    ns['chc'] = ns['ch'].generated_class()
    exec(block("beam = actor_bp('BP_GW_Beam')", '# ---------------------------------------------------------------- character: special looks'), ns)
    print('BP_GW_Beam', node_problems(ns['beam']))
    exec(block("gm = load_bp('BP_GW_GameMode')\nfor v, t in (('AutoEvents'", 'def controller('), ns)
    exec(block('def controller(', 'mv0 = lambda'), ns)
    exec(block('ROBOT_CHARGE, ROBOT_LOCK', "# ---------------------------------------------------------------- game mode: framework"), ns)
    exec(block('mv = lambda v:', 'for name, code in G.items():\n    write(gm, name, code, compile_after=False)\ncompile_bp(gm)'), ns)
    gm = ns['gm']
    for n in ('SpawnSpecial', 'HurtCharacter', 'RobotBeamEnd', 'RobotShot', 'RobotHurt', 'RobotDown', 'StartRobot'):
        rewrite(gm, n, ns['G'][n])
    rewrite(gm, 'RobotLaser', "(fn RobotLaser (From Victim) (return))")     # replaced by RobotShot (nothing calls it any more)
    print('BP_GW_GameMode', compile_bp(gm), [p for p in node_problems(gm) if 'Robot' in p or 'Hurt' in p])
    save(gm)

if 's38' in ARGS:
    S = src('s38_pickups.py')
    ns = dict(globals())
    for pat in (r"^FOLDER = .*$", r"^PK = .*$", r"^HS = .*$", r"^CHAR = .*$", r"^ISVALID = .*$", r"^GMC = .*$", r"^MYCH = .*$", r"^CAT = .*$", r"^SLASH_RANGE, SLASH_COS = .*$", r"^P = .*$", r"^PS_ = .*$", r"^WHO = .*$", r"^LOG = .*$", r"^mv = .*$"):
        m = re.search(pat, S, re.M)
        if m:
            exec(m.group(0), ns)
    if 'LOG' not in ns:
        exec(textwrap.dedent(re.search(r"^def LOG\(.*?(?=^\S)", S, re.S | re.M).group(0)), ns)
    gm = load_bp('BP_GW_GameMode')
    for n in ('WeaponHit', 'SlashTarget'):
        rewrite(gm, n, eval("f'''" + re.search(r"'%s': f'''(.*?)''',?\n" % n, S, re.S).group(1) + "'''", ns))
    print('BP_GW_GameMode', compile_bp(gm))
    save(gm)
    pc = load_bp('BP_GW_PlayerController')
    ensure_var(pc, 'PostReads', 'int', rep=unreal.BlueprintVariableReplication.REPLICATED, category='GW')
    compile_bp(pc, quiet=True)
    rewrite(pc, 'GWPickup', eval("f'''" + re.search(r"'GWPickup': f'''(.*?)''',?\n", S, re.S).group(1) + "'''", ns))
    print('BP_GW_PlayerController', compile_bp(pc))
    save(pc)

if 's39' in ARGS:
    S = src('s39_voice_director.py')
    sys.path.insert(0, os.path.join(TOOLS, 'gameplay'))
    import voice_bank as VB
    ns = dict(globals()); ns['VB'] = VB
    for pat in (r"^CAT = VB\.CAT$", r"^ISVALID = .*$", r"^NOW = .*$", r"^R_AREA = .*$", r"^BANDIT_GAP = .*$", r"^EVCAT = .*$", r"^EVCAUSE = .*$", r"^L = .*$", r"^SL = .*$", r"^LOC = .*$", r"^HEAD = .*$", r"^RF = .*$", r"^EVCAT_X = .*$", r"^EVCAUSE_X = .*$"):
        exec(re.search(pat, S, re.M).group(0), ns)
    gm = load_bp('BP_GW_GameMode')
    rewrite(gm, 'EventVoiceTick', eval("f'''" + re.search(r"W\['EventVoiceTick'\] = f'''(.*?)'''", S, re.S).group(1) + "'''", ns))
    print('BP_GW_GameMode', compile_bp(gm))
    save(gm)

if 's34gm' in ARGS:
    S = src('s34_shop.py')
    ns = dict(globals())
    for pat in (r"^ISVALID = .*$", r"^SHOP = .*$"):
        m = re.search(pat, S, re.M)
        if m:
            exec(m.group(0), ns)
    exec(re.search(r"^LOUD, GUN, SMOKE, GAS, SHRINK.*$", S, re.M).group(0), ns)
    exec(re.search(r"^def mv\(.*?(?=^\S)", S, re.S | re.M).group(0), ns)
    gm = load_bp('BP_GW_GameMode')
    ensure_var(gm, 'GasScale', 'float', category='Shop')
    compile_bp(gm, quiet=True)
    cdo(gm).set_editor_property('GasScale', 0.3)
    rewrite(gm, 'UseGas', eval("f'''" + re.search(r"G\['UseGas'\] = f'''(.*?)'''", S, re.S).group(1) + "'''", ns))
    print('BP_GW_GameMode', compile_bp(gm))
    save(gm)
print('s42 done', sorted(ARGS))
