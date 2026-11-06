"""The user's second test of 2026-11-05 (Tools/agent_logs/feedback6_items.md). What cannot go through an owner script cheaply; the texts stay in their owners. Re-runnable.
Order after a change:
  python ue_run.py s43_feedback6.py kami settings view opts / ui\\u19_game_setup.py / ui\\u10_menu.py graph / s40_inventory.py ps ui gm pc / ui\\u14_hud.py / ui\\u15_dev_menu.py pc, data / ui\\u17_shop_ui.py
Parts:
  kami   imports SFX_Kamikaze_Alarm_Loop (Tools/audio/fb6_kamikaze_alarm.py), ATT_GW_KamiAlarm, BP_GW_KamiAlarm (follows the kamikaze on every machine, loops the shout in 3D until he falls);
         BP_GW_KamikazeController.Brain (no lines any more) and GM.SpawnSpecial (spawns the alarm), from s32's text
  kamisnd only the sound (0.2 s of silence after each shout, inside the file)
  settings the game setup's values on BP_GW_Settings (see u02's VARS)
  view   BP_GW_Character: ApplyView (s37's text); MoveKeys replaces the template's Move on IA_Move: while the same keys stay held the walking direction no longer follows the mouse at once. It starts from the
         camera and leans towards it at GS.MoveTurn degrees/s (dev menu, 0 = at once); a key change, first person or aiming take the camera's direction at once. The mouse alone never turns the body.
  opts   GM.ApplyOptions, AssignRoles, RoundTick, ResetToLobby from s12's text (MaxRounds, SeekersWanted, the setup screen's options)
"""
import sys, importlib, os, re
sys.path.insert(0, r'J:\Projets\Unreal_Projects\Guess Who\Tools\gameplay')
import gw_lib; importlib.reload(gw_lib)
from gw_lib import *

ARGS = set(UE_ARGS)
ROOT = r'J:\Projets\Unreal_Projects\Guess Who'
TOOLS = ROOT + r'\Tools'
AT = unreal.AssetToolsHelpers.get_asset_tools()
ISVALID = 'GW|Call|/Script/Engine.KismetSystemLibrary|IsValid'
REP = unreal.BlueprintVariableReplication
AC = '/Script/Engine.AudioComponent'
LOOP = '/Game/GW/Audio/Gen/kamikaze/SFX_Kamikaze_Alarm_Loop'
ATT = '/Game/GW/Audio/ATT_GW_KamiAlarm'


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


if 'kami' in ARGS or 'kamisnd' in ARGS:
    t = unreal.AssetImportTask()
    t.filename = ROOT + r'\AssetGen\audio\final\feedback6\SFX_Kamikaze_Alarm_Loop.wav'
    t.destination_path = '/Game/GW/Audio/Gen/kamikaze'; t.destination_name = 'SFX_Kamikaze_Alarm_Loop'; t.automated = True; t.replace_existing = True; t.save = False
    AT.import_asset_tasks([t])
    s = unreal.load_asset(LOOP)
    s.set_editor_property('sound_class_object', unreal.load_asset('/Game/GW/Audio/Classes/SC_GW_SFX'))
    s.set_editor_property('looping', True)
    print('sound', EAL.save_loaded_asset(s, False), 'duration', s.get_editor_property('duration'), 'looping', s.get_editor_property('looping'))

if 'kami' in ARGS:
    s = unreal.load_asset(LOOP)
    # full level within 6 m, gone at 50 m: louder and louder as he comes through the rooms
    a = unreal.load_asset(ATT) if EAL.does_asset_exist(ATT) else AT.create_asset('ATT_GW_KamiAlarm', '/Game/GW/Audio', unreal.SoundAttenuation, unreal.SoundAttenuationFactory())
    st = a.get_editor_property('attenuation')
    st.set_editor_property('attenuation_shape_extents', unreal.Vector(600.0, 0, 0))
    st.set_editor_property('falloff_distance', 4400.0)
    a.set_editor_property('attenuation', st)
    print('attenuation', EAL.save_loaded_asset(a, False))

    ch = load_bp('BP_GW_Character')
    al = load_or_create_bp('BP_GW_KamiAlarm', unreal.Actor)
    compile_bp(al, quiet=True)
    d = cdo(al)
    d.set_editor_property('replicates', True)
    d.set_editor_property('always_relevant', True)
    d.set_editor_property('replicate_movement', False)
    ensure_var(al, 'Ch', obj_class=ch.generated_class(), rep=REP.REPLICATED, category='FX')
    ensure_var(al, 'Started', 'bool', category='FX')
    ensure_fn(al, 'StopCry')
    au = ensure_component(al, 'Cry', unreal.AudioComponent, 'DefaultSceneRoot')
    au.set_editor_property('sound', s)
    au.set_editor_property('attenuation_settings', a)
    au.set_editor_property('volume_multiplier', 1.8)
    au.set_editor_property('auto_activate', False)
    compile_bp(al, quiet=True)
    write(al, 'StopCry', f'''
(fn StopCry ()
  (if (Variables|FX|GetStarted)
    (Variables|FX|SetStarted false)
    (GW|Call|{AC}|Stop :self (Variables|Default|GetCry))
    (Development|PrintString :InString "GW: kamikaze alarm off" :bPrintToScreen false)))
''', compile_after=False)
    write(al, 'EventGraph', f'''
(event EventTick (DeltaSeconds)
  (bind c (Variables|FX|GetCh))
  (if (not ({ISVALID} :Object c))
    (CallFunction|StopCry)
    (if (Networking|HasAuthority)
      (Actor|DestroyActor :self self))
    (return))
  (if (GW|Get|BP_GW_Character|IsDead :self c)
    (CallFunction|StopCry)
    (if (Networking|HasAuthority)
      (Actor|DestroyActor :self self))
    (return))
  (Transformation|SetActorLocation :self self :NewLocation (+ (Transformation|GetActorLocation :self c) (Math|Vector|MakeVector 0.0 0.0 60.0)) :bSweep false :bTeleport true)
  (if (not (Variables|FX|GetStarted))
    (Variables|FX|SetStarted true)
    (GW|Call|{AC}|Play :self (Variables|Default|GetCry) :StartTime 0.0)
    (Development|PrintString :InString (cat "GW: kamikaze alarm on, " (Utilities|GetDisplayName :Object (GW|Get|{AC}|Sound :self (Variables|Default|GetCry)))) :bPrintToScreen false)))
''', compile_after=False)
    print('BP_GW_KamiAlarm', compile_bp(al), node_problems(al))
    save(al)

    S = src('s32_events.py')
    ns = dict(globals())
    exec(re.search(r'^GMC = .*$', S, re.M).group(0), ns)
    exec(re.search(r'^def gm_call\(.*?\n\n', S, re.S | re.M).group(0), ns)
    exec(re.search(r'^KAMI_BOOM = .*$', S, re.M).group(0), ns)
    kami = load_bp('BP_GW_KamikazeController')
    rewrite(kami, 'Brain', eval("f'''" + re.search(r"write\(kami, 'Brain', f'''(.*?)''', compile_after=False\)", S, re.S).group(1) + "'''", ns))
    print('BP_GW_KamikazeController', compile_bp(kami), node_problems(kami))
    save(kami)

    exec(re.search(r"^CTRL = .*?^G = \{", S, re.S | re.M).group(0)[:-len('G = {')], ns)
    gm = load_bp('BP_GW_GameMode')
    rewrite(gm, 'SpawnSpecial', eval("f'''" + re.search(r"'SpawnSpecial': f'''(.*?)''',", S, re.S).group(1) + "'''", ns))
    print('BP_GW_GameMode', compile_bp(gm), [p for p in node_problems(gm) if 'SpawnSpecial' in p])
    save(gm)

if 'settings' in ARGS:
    sg = unreal.load_asset('/Game/GW/UI/BP_GW_Settings')
    VARS = [('GNPCs', 120), ('GHunt', 240), ('GHide', 20), ('GRounds', 0), ('GSeekers', 0), ('GAutoEv', 1), ('GEventEvery', 180), ('GMinPlayers', 2), ('GLobby', 8)]
    for n, _ in VARS:
        ensure_var(sg, n, 'int', category='GW')
    compile_bp(sg, quiet=True)
    d = cdo(sg)
    for n, v in VARS:
        d.set_editor_property(n, v)
    print('BP_GW_Settings', compile_bp(sg))
    save(sg)

if 'view' in ARGS:
    gs = load_bp('BP_GW_GameState')
    ensure_var(gs, 'MoveTurn', 'float', rep=REP.REPLICATED, category='GW')
    compile_bp(gs, quiet=True)
    cdo(gs).set_editor_property('MoveTurn', 120.0)
    print('BP_GW_GameState', compile_bp(gs))
    save(gs)
    ch = load_bp('BP_GW_Character')
    ensure_var(ch, 'MoveYaw', 'float', category='View')
    ensure_var(ch, 'MoveAt', 'float', category='View')
    ensure_var(ch, 'MoveKey', 'int', category='View')
    ensure_fn(ch, 'MoveRate', outputs=[('R', 'float')], pure=True)
    ensure_fn(ch, 'MoveKeys', inputs=[('VX', 'float'), ('VY', 'float')])
    compile_bp(ch, quiet=True)
    write(ch, 'MoveRate', '''
(fn MoveRate ()
  (bind s (Utilities|Casting|CastToBP_GW_GameState (Game|GetGameState))
    (:then (return (GW|Get|BP_GW_GameState|MoveTurn :self s)))
    (:CastFailed (return 120.0))))
''', compile_after=False)
    write(ch, 'MoveKeys', '''
(fn MoveKeys (VX VY)
  (bind now (Utilities|Time|GetGameTimeinSeconds))
  (bind cy (.yaw (Pawn|GetControlRotation :self (Pawn|GetController))))
  (bind key (+ (select (> VX 0.1) 1 (select (< VX -0.1) 2 0)) (* 3 (select (> VY 0.1) 1 (select (< VY -0.1) 2 0)))))
  (bind gap (- now (Variables|View|GetMoveAt)))
  (bind rate (CallFunction|MoveRate))
  (if (or (or (!= key (Variables|View|GetMoveKey)) (> gap 0.2)) (or (<= rate 0.0) (or (Variables|View|GetViewFP) (Variables|View|GetAiming))))
    (Variables|View|SetMoveYaw cy)
    (else
      (bind dy (Math|Rotator|NormalizeAxis (- cy (Variables|View|GetMoveYaw))))
      (bind stepy (* rate gap))
      (Variables|View|SetMoveYaw (+ (Variables|View|GetMoveYaw) (Math|Float|Clamp(Float) :Value dy :Min (* -1.0 stepy) :Max stepy)))))
  (Variables|View|SetMoveKey key)
  (Variables|View|SetMoveAt now)
  (bind r (Math|Rotator|MakeRotator :Roll 0.0 :Pitch 0.0 :Yaw (Variables|View|GetMoveYaw)))
  (Pawn|Input|AddMovementInput :WorldDirection (Math|Vector|GetForwardVector r) :ScaleValue VY)
  (Pawn|Input|AddMovementInput :WorldDirection (Math|Vector|GetRightVector r) :ScaleValue VX))
''', compile_after=False)
    _eg = get_graph(ch, 'EventGraph')
    for _n in list(BT.find_nodes(_eg)):
        if _n.get_class().get_name() == 'K2Node_CallFunction' and _n.get_node_title().replace(' ', '') in ('MoveHeld', 'MoveKeys'):
            BT.delete_node(_n)
    for _n in BT.find_nodes(_eg):
        if _n.get_class().get_name() == 'K2Node_EnhancedInputAction' and BT.get_node_infos([_n])[0].type_id.endswith('IA_Move'):
            print('IA_Move pins', [str(_p.get_pin_name()) for _p in _n.list_all_pins()])
    wire_input(ch, 'IA_Move', {'Triggered': 'MoveKeys'}, pos=(0, 2600), args={'MoveKeys': {'VX': 'ActionValue_X', 'VY': 'ActionValue_Y'}})
    rewrite(ch, 'ApplyView', re.search(r"'ApplyView': \'\'\'(.*?)\'\'\'", src('s37_view.py'), re.S).group(1))
    print('BP_GW_Character', compile_bp(ch), [p for p in node_problems(ch) if 'Move' in p or 'ApplyView' in p])
    save(ch)

if 'opts' in ARGS:
    S = src('s12_gamemode.py')
    ns = dict(globals())
    exec(re.search(r'^def gs_get\(.*?(?=^def local)', S, re.S | re.M).group(0), ns)
    gm = load_bp('BP_GW_GameMode')
    ensure_var(gm, 'MaxRounds', 'int', category='GW')
    ensure_var(gm, 'SeekersWanted', 'int', category='GW')
    compile_bp(gm, quiet=True)
    for n in ('ApplyOptions', 'AssignRoles', 'ResetToLobby', 'RoundTick'):
        m = re.search(r"W\['%s'\] = (f?)\'\'\'(.*?)\'\'\'" % n, S, re.S)
        rewrite(gm, n, eval("f'''" + m.group(2) + "'''", ns) if m.group(1) else m.group(2))
    print('BP_GW_GameMode', compile_bp(gm), [p for p in node_problems(gm) if any(k in p for k in ('ApplyOptions', 'AssignRoles', 'RoundTick', 'ResetToLobby'))])
    save(gm)

print('s43 done', sorted(ARGS))
