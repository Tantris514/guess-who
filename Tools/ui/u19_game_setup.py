"""WBP_GameSetup: the game's parameters, shown when hosting (the user, 2026-11-05: "make it paramattable when we start a game, put other params in a menu"). Art Deco, one row per value: label, < value >.
BtnHost (u10_menu.py OnHostAsk) opens it; COMMENCER saves the values in BP_GW_Settings (GN*, remembered between games, u02) and calls the menu's OnHostClicked, which turns them into travel options (HostOpts);
BP_GW_GameMode.ApplyOptions (s12) reads the options: NPCs, HuntTime, HideTime, MaxRounds, AutoEvents, EventEvery, MinPlayers, LobbyTime.
Add a row: one line in ROWS, one var in u02 VARS / s43 settings, one option in u10 HostOpts and s12 ApplyOptions.
Run: ue_run.py u19_game_setup.py, after s43_feedback6.py settings and before u10_menu.py. -GWSetupTest: the widget opens by itself in the main menu test (shots)."""
import sys
sys.path.insert(0, r'J:\Projets\Unreal_Projects\Guess Who\Tools\ui')
import importlib, uilib
importlib.reload(uilib)
from uilib import *

W = get_or_create('WBP_GameSetup')
SET = '/Game/GW/UI/BP_GW_Settings.BP_GW_Settings_C'
GI_CAST = '(Utilities|Casting|CastToBP_GW_GameInstance (Widget|GetGameInstance))'
MENU = unreal.load_asset('/Game/GW/UI/WBP_MainMenu').generated_class()
# var on the settings, label, min, max, step, default, format: 'n' number, 'npc', 'mmss', 's', 'rounds' (0 = no limit), 'seek' (0 = a third), 'onoff', 'every'
ROWS = [
    ('GNPCs', 'Invités non-joueurs', 30, 200, 10, 120, 'n'),
    ('GHunt', 'Durée de la chasse', 60, 900, 30, 240, 'mmss'),
    ('GHide', 'Temps pour se cacher', 10, 60, 5, 20, 's'),
    ('GRounds', 'Nombre de manches', 0, 20, 1, 0, 'rounds'),
    ('GAutoEv', 'Événements automatiques', 0, 1, 1, 1, 'onoff'),
    ('GEventEvery', 'Un événement toutes les', 60, 600, 30, 180, 'mmss'),
    ('GMinPlayers', 'Joueurs pour commencer', 1, 8, 1, 2, 'n'),
    ('GLobby', 'Attente au salon', 3, 30, 1, 8, 's'),
]
N = len(ROWS)


def tree():
    clear_tree(W)
    add(W, unreal.CanvasPanel, 'Root')
    d = add(W, unreal.Image, 'Dim', 'Root'); d.widget.set_editor_property('brush', brush(None, (8, 8), 'image', tint=(0, 0, 0, 0.62))); canvas(d, FILL, z=0)
    sz = add(W, unreal.SizeBox, 'PanelSize', 'Root', var=True); size_box(sz, w=980)
    canvas(sz, ((0.5, 0.5), (0.5, 0.5)), (0.5, 0.5), auto=True, z=5); pivot(sz)
    p = add(W, unreal.Border, 'Panel', 'PanelSize'); border_brush(p, 'T_UI_Panel', 0.25, tint=(1, 1, 1, 0.98), pad=(64, 36, 64, 36), size=(256, 256))
    v = add(W, unreal.VerticalBox, 'Body', 'Panel')
    t = add(W, unreal.TextBlock, 'Title', 'Body'); text(t, 'LA SOIRÉE', 'Display', 'Regular', 54, GOLD_HI, spacing=600, just='center'); box_slot(t, (0, 0, 0, 0), H.H_ALIGN_CENTER)
    dv = add(W, unreal.Image, 'TitleDiv', 'Body'); image(dv, 'T_UI_Divider', (300, 63)); box_slot(dv, (0, 0, 0, 8), H.H_ALIGN_CENTER)
    for i, r in enumerate(ROWS):
        h = add(W, unreal.HorizontalBox, f'Row{i}', 'Body'); box_slot(h, (0, 3, 0, 3), H.H_ALIGN_FILL)
        l = add(W, unreal.TextBlock, f'Lbl{i}', f'Row{i}'); text(l, r[1], 'Serif', 'Regular', 27, IVORY); box_slot(l, (0, 0, 12, 0), H.H_ALIGN_LEFT, VA.V_ALIGN_CENTER, fill=1)
        for bn, tx in ((f'Prev{i}', 'T_UI_ArrowL'), (f'Next{i}', None)):
            if tx is None:
                vb = add(W, unreal.SizeBox, f'ValBox{i}', f'Row{i}'); size_box(vb, w=210); box_slot(vb, (6, 0, 6, 0), H.H_ALIGN_CENTER, VA.V_ALIGN_CENTER)
                vt = add(W, unreal.TextBlock, f'Val{i}', f'ValBox{i}', var=True); text(vt, '', 'Display', 'Regular', 32, GOLD_HI, spacing=80, just='center')
            b = add(W, unreal.Button, bn, f'Row{i}', var=True); flat_button(b); box_slot(b, (0, 0, 0, 0), H.H_ALIGN_CENTER, VA.V_ALIGN_CENTER)
            a = add(W, unreal.Image, bn + 'Ico', bn); image(a, tx or 'T_UI_ArrowR', (34, 34))
    foot = add(W, unreal.HorizontalBox, 'Footer', 'Body'); box_slot(foot, (0, 18, 0, 0), H.H_ALIGN_CENTER)
    for bn, tx, wd in (('BtnBack', 'RETOUR', 220), ('BtnDefaults', 'PAR DÉFAUT', 260), ('BtnStart', 'COMMENCER', 320)):
        sb = add(W, unreal.SizeBox, bn + 'Box', 'Footer'); size_box(sb, w=wd, h=62); box_slot(sb, (8, 0, 8, 0), H.H_ALIGN_CENTER)
        b = add(W, unreal.Button, bn, bn + 'Box', var=True); button_style(b)
        tb = add(W, unreal.TextBlock, bn + 'Text', bn); text(tb, tx, 'Display', 'Regular', 25, GOLD_HI if bn == 'BtnStart' else IVORY, spacing=220, just='center')
    compile_widget(W)


def graph():
    ensure_var(W, 'MenuW', obj_class=MENU, category='UI')
    ensure_var(W, 'Vals', 'int', array=True, category='UI')
    for n in ('Mins', 'Maxs', 'Steps', 'Defs'):
        ensure_var(W, n, 'int', array=True, category='UI')
    ensure_fn(W, 'Show', inputs=[('I', 'int')])
    ensure_fn(W, 'ShowAll')
    ensure_fn(W, 'Bump', inputs=[('I', 'int'), ('Dir', 'int')])
    ensure_fn(W, 'Fmt', inputs=[('I', 'int'), ('V', 'int')], outputs=[('Out', 'string')], pure=True)
    for fn in ['OnStart', 'OnBack', 'OnDefaults', 'LoadVals', 'SaveVals'] + [f'P{i}' for i in range(N)] + [f'N{i}' for i in range(N)]:
        ensure_fn(W, fn)
    compile_bp(W, quiet=True)
    c = unreal.get_default_object(W.generated_class())
    c.set_editor_property('Mins', [r[2] for r in ROWS])
    c.set_editor_property('Maxs', [r[3] for r in ROWS])
    c.set_editor_property('Steps', [r[4] for r in ROWS])
    c.set_editor_property('Defs', [r[5] for r in ROWS])
    c.set_editor_property('Vals', [r[5] for r in ROWS])
    AG = lambda arr, i: f'(Utilities|Array|Get(acopy) (Variables|UI|Get{arr}) {i})'
    F = {'n': '(cat "" V)', 'mmss': '(cat (/ V 60) (select (< (% V 60) 10) ":0" ":") (% V 60))', 's': '(cat V " s")',
         'rounds': '(select (== V 0) "Sans limite" (cat "" V))', 'seek': '(select (== V 0) "Un sur trois" (cat "" V))', 'onoff': '(select (== V 0) "Non" "Oui")'}
    e = '(cat "" V)'
    for i, r in reversed(list(enumerate(ROWS))):
        e = f'(select (== I {i}) {F[r[6]]} {e})'
    G = {'Fmt': f'(fn Fmt (I V) (return {e}))'}
    G['Show'] = ''.join(['(fn Show (I)\n'] + [f'  (if (== I {i}) (Widget|SetText(Text) :self (Variables|WBP_GameSetup|GetVal{i}) :InText (Utilities|Text|ToText(String) (CallFunction|Fmt :I I :V {AG("Vals", "I")}))))\n' for i in range(N)]) + '  ; the frequency means nothing without the events\n  (if (or (== I 5) (== I 6))\n    (Widget|SetRenderOpacity :self (Variables|WBP_GameSetup|GetVal6) :InOpacity (select (== ' + AG('Vals', 5) + ' 0) 0.35 1.0))))'
    G['ShowAll'] = '(fn ShowAll ()\n' + '\n'.join(f'  (CallFunction|Show :I {i})' for i in range(N)) + ')'
    G['Bump'] = f'''
(fn Bump (I Dir)
  (bind nv (Math|Integer|Clamp(Integer) :Value (+ {AG("Vals", "I")} (* Dir {AG("Steps", "I")})) :Min {AG("Mins", "I")} :Max {AG("Maxs", "I")}))
  (Utilities|Array|SetArrayElem :TargetArray (Variables|UI|GetVals) :Index I :Item nv :bSizeToFit false)
  (Audio|PlaySound2D :Sound "/Game/GW/Audio/S_UI_Click.S_UI_Click" :VolumeMultiplier 0.6)
  (CallFunction|Show :I I))
'''
    for i in range(N):
        G[f'P{i}'] = f'(fn P{i} () (CallFunction|Bump :I {i} :Dir -1))'
        G[f'N{i}'] = f'(fn N{i} () (CallFunction|Bump :I {i} :Dir 1))'
    G['LoadVals'] = '(fn LoadVals ()\n  (bind gi ' + GI_CAST + '\n    (:then\n      (bind s (GW|Call|BP_GW_GameInstance|GWSettings :self gi))\n' + '\n'.join(
        f'      (Utilities|Array|SetArrayElem :TargetArray (Variables|UI|GetVals) :Index {i} :Item (Math|Integer|Clamp(Integer) :Value (GW|Get|{SET}|{r[0]} :self s) :Min {r[2]} :Max {r[3]}) :bSizeToFit false)' for i, r in enumerate(ROWS)) + '\n      (CallFunction|ShowAll))\n    (:CastFailed)))'
    G['SaveVals'] = '(fn SaveVals ()\n  (bind gi ' + GI_CAST + '\n    (:then\n      (bind s (GW|Call|BP_GW_GameInstance|GWSettings :self gi))\n' + '\n'.join(
        f'      (GW|Set|{SET}|{r[0]} :self s :{r[0]} {AG("Vals", i)})' for i, r in enumerate(ROWS)) + '\n      (GW|Call|BP_GW_GameInstance|GWSaveSettings :self gi)\n      (Development|PrintString :InString (cat "GW setup: saved npcs=" ' + AG('Vals', 0) + ' " hunt=" ' + AG('Vals', 1) + ' " rounds=" ' + AG('Vals', 3) + ') :bPrintToScreen false))\n    (:CastFailed)))'
    G['OnDefaults'] = '''
(fn OnDefaults ()
  (Variables|UI|SetVals (Variables|UI|GetDefs))
  (Audio|PlaySound2D :Sound "/Game/GW/Audio/S_UI_Back.S_UI_Back" :VolumeMultiplier 0.7)
  (CallFunction|ShowAll))
'''
    G['OnBack'] = '''
(fn OnBack ()
  (CallFunction|SaveVals)
  (Widget|RemovefromParent :self self))
'''
    G['OnStart'] = '''
(fn OnStart ()
  (CallFunction|SaveVals)
  (Audio|PlaySound2D :Sound "/Game/GW/Audio/S_UI_Confirm.S_UI_Confirm" :VolumeMultiplier 0.8)
  (bind m (Variables|UI|GetMenuW))
  (Widget|RemovefromParent :self self)
  (if (GW|Call|/Script/Engine.KismetSystemLibrary|IsValid :Object m)
    (GW|Call|/Game/GW/UI/WBP_MainMenu.WBP_MainMenu_C|OnHostClicked :self m)))
'''
    G['EventGraph'] = '''
(event UserInterface|EventConstruct
  (CallFunction|LoadVals))
'''
    for name, code in G.items():
        write(W, name, code, compile_after=False)
    for i in range(N):
        bind(W, f'Prev{i}', 'OnClicked', f'P{i}')
        bind(W, f'Next{i}', 'OnClicked', f'N{i}')
    bind(W, 'BtnBack', 'OnClicked', 'OnBack')
    bind(W, 'BtnDefaults', 'OnClicked', 'OnDefaults')
    bind(W, 'BtnStart', 'OnClicked', 'OnStart')
    compile_bp(W)
    print('WBP_GameSetup', node_problems(W))
    compile_widget(W)


tree()
graph()
