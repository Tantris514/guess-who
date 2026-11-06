"""WBP_Options (SaveGame-backed settings), WBP_HowTo (illustrated rule cards + controls), WBP_Pause (in-game menu, game keeps running).
UE_ARGS: 'options' | 'howto' | 'pause' | 'all' (default)."""
import sys
sys.path.insert(0, r'J:\Projets\Unreal_Projects\Guess Who\Tools\ui')
import importlib, uilib, uianim
importlib.reload(uilib); importlib.reload(uianim)
from uilib import *

which = UE_ARGS[0] if UE_ARGS else 'all'
ISVALID = 'GW|Call|/Script/Engine.KismetSystemLibrary|IsValid'
SET = '/Game/GW/UI/BP_GW_Settings.BP_GW_Settings_C'
GI_CAST = '(Utilities|Casting|CastToBP_GW_GameInstance (Widget|GetGameInstance))'
INK_C = (0.035, 0.025, 0.02, 1)
BURG_C = (0.33, 0.04, 0.05, 1)


def backdrop(W, blur=8, dim=0.55):
    bb = add(W, unreal.BackgroundBlur, 'Blur', 'Root'); canvas(bb, FILL, z=0)
    try:
        bb.widget.set_editor_property('blur_strength', float(blur))
    except Exception as e:
        print('blur prop', e)
    dm = add(W, unreal.Image, 'Dim', 'Root'); image(dm, 'T_UI_Vignette', (512, 288), tint=(0, 0, 0, 1)); canvas(dm, FILL, z=1)
    d2 = add(W, unreal.Image, 'Dim2', 'Root'); dm2 = d2.widget
    dm2.set_editor_property('brush', brush(None, (8, 8), 'image', tint=(0, 0, 0, dim))); canvas(d2, FILL, z=1)


def panel(W, name, w, h, parent='Root', z=5, tint=(1, 1, 1, 0.98)):
    sz = add(W, unreal.SizeBox, name + 'Size', parent, var=True); size_box(sz, w=w, h=h)
    canvas(sz, ((0.5, 0.5), (0.5, 0.5)), (0.5, 0.5), auto=True, z=z); pivot(sz)
    p = add(W, unreal.Border, name, name + 'Size')
    border_brush(p, 'T_UI_Panel', 0.25, tint=tint, pad=(64, 40, 64, 40), size=(256, 256))
    return p


def title(W, name, label, parent, size=58):
    t = add(W, unreal.TextBlock, name, parent); text(t, label, 'Display', 'Regular', size, GOLD_HI, spacing=600, just='center')
    box_slot(t, (0, 0, 0, 0), H.H_ALIGN_CENTER)
    d = add(W, unreal.Image, name + 'Div', parent); image(d, 'T_UI_Divider', (300, 63)); box_slot(d, (0, 0, 0, 8), H.H_ALIGN_CENTER)


def deco_button(W, name, label, parent, w=300, h=58, size=24):
    sb = add(W, unreal.SizeBox, name + 'Box', parent); size_box(sb, w=w, h=h)
    b = add(W, unreal.Button, name, name + 'Box', var=True); button_style(b)
    t = add(W, unreal.TextBlock, name + 'Text', name, var=True)
    text(t, label, 'Display', 'Regular', size, IVORY, spacing=240, just='center')
    return sb


def section(W, name, label, parent):
    t = add(W, unreal.TextBlock, name, parent); text(t, label, 'Display', 'Regular', 21, GOLD, spacing=520)
    box_slot(t, (0, 14, 0, 4), H.H_ALIGN_LEFT)


# ======================================================================================== OPTIONS
SLIDERS = [('Master', 'Volume général'), ('Music', 'Musique'), ('Sfx', 'Effets sonores'), ('UI', 'Interface'),
           ('Sens', 'Sensibilité de la souris'), ('Fov', 'Champ de vision')]
QUAL = ['FAIBLE', 'MOYEN', 'ÉLEVÉ', 'ÉPIQUE']
# ---- controls page. Every key of IMC_GW (+ jump) can be changed; the table is read from the contexts when this script runs,
# so a new action only needs a label here and a re-run of "u11_screens.py options". How: UInputMappingContext.UnmapAllKeysFromAction
# / MapKey at runtime (no WITH_EDITOR guard in the engine source, safe in a packaged build) + RequestRebuildControlMappingsUsingContext;
# the choices are saved in BP_GW_Settings (BindNames / BindKeys). The EnhancedInputUserSettings route is not usable from Blueprint
# here (no node returns the settings object). Movement cannot be changed: WASD share IA_Move with Swizzle / Negate modifiers, which
# a Blueprint cannot put on a runtime mapping.
KEY_LABELS = {'IA_Interact': 'Interagir', 'IA_Fire': 'Tirer / utiliser', 'IA_Sprint': 'Courir', 'IA_Jump': 'Sauter', 'IA_Scoreboard': 'Scores',
              'IA_Dance': 'Danser', 'IA_GW_Smoke': 'Fumigène', 'IA_GW_Gas': 'Gaz rétrécissant', 'IA_GW_Trap': 'Piège',
              'IA_GW_Lamp': 'Lampe', 'IA_GW_Bomb': 'Bombe', 'IA_GW_Cracker': 'Pétard', 'IA_Swap': "Pistolet d'échange",
              'IA_GW_View': 'Changer de vue', 'IA_GW_Drop': "Jeter l'objet", 'IA_GW_SlotPrev': 'Objet précédent', 'IA_GW_SlotNext': 'Objet suivant',
              'IA_GW_Slot1': 'Objet 1', 'IA_GW_Slot2': 'Objet 2', 'IA_GW_Slot3': 'Objet 3', 'IA_GW_Slot4': 'Objet 4'}
KEY_FIXED = ('IA_Menu', 'IA_DevMenu', 'IA_Look', 'IA_Move', 'IA_MouseLook')
KEY_ROWS_MAX = 24


def key_table():
    """[(action, context, default key, label)] from IMC_GW, then the keyboard jump of IMC_Default."""
    rows, seen = [], set()
    for path in ('/Game/GW/Input/IMC_GW', '/Game/Input/IMC_Default'):
        imc = unreal.load_asset(path)
        for m in imc.get_editor_property('default_key_mappings').get_editor_property('mappings'):
            a = m.get_editor_property('action')
            k = m.get_editor_property('key')
            n = a.get_name()
            if n in KEY_FIXED or n in seen or str(k.get_editor_property('key_name')).startswith('Gamepad'):
                continue
            seen.add(n)
            rows.append((a, imc, k, KEY_LABELS.get(n, n.replace('IA_GW_', '').replace('IA_', ''))))
    rows.sort(key=lambda r: (1, r[3]) if r[3].startswith('Objet ') else (0, ''))     # stable: the rest keeps its order; Objet 1-4 together at the end
    assert len(rows) <= KEY_ROWS_MAX, 'raise KEY_ROWS_MAX'
    return rows


def keys_setup():
    """Saved choices on BP_GW_Settings; the table (class defaults, so never stale from an old save file) and logic on the game instance."""
    sg = unreal.load_asset('/Game/GW/UI/BP_GW_Settings')
    ensure_var(sg, 'BindNames', 'string', array=True, category='GW')
    ensure_var(sg, 'BindKeys', struct=unreal.Key.static_struct(), array=True, category='GW')
    compile_bp(sg, quiet=True)
    save(sg)
    gi = unreal.load_asset('/Game/GW/Blueprints/BP_GW_GameInstance')
    ensure_var(gi, 'KeyActs', obj_class=unreal.InputAction, array=True, category='Keys')
    ensure_var(gi, 'KeyCtx', obj_class=unreal.InputMappingContext, array=True, category='Keys')
    ensure_var(gi, 'KeyDefs', struct=unreal.Key.static_struct(), array=True, category='Keys')
    ensure_var(gi, 'KeyTmp', struct=unreal.Key.static_struct(), category='Keys')
    ensure_var(gi, 'KeyLbl', 'string', category='Keys')
    KEY = unreal.Key.static_struct()
    for f, ins, outs, pure in (('GWKeyAt', [('I', 'int')], [('K', KEY)], False), ('GWApplyKeys', [], [], False),
                               ('GWSetBind', [('I', 'int'), ('K', KEY)], [], False), ('GWStoreBind', [('I', 'int'), ('K', KEY)], [], False),
                               ('GWResetBinds', [], [], False), ('GWKeyLabel', [('Key', 'string')], [('Out', 'string')], False),
                               ('GWKeyName', [('I', 'int')], [('Out', 'string')], False)):
        ensure_fn(gi, f, inputs=ins, outputs=outs, pure=pure)
    compile_bp(gi, quiet=True)
    rows = key_table()
    c = unreal.get_default_object(gi.generated_class())
    c.set_editor_property('KeyActs', [r[0] for r in rows])
    c.set_editor_property('KeyCtx', [r[1] for r in rows])
    c.set_editor_property('KeyDefs', [r[2] for r in rows])
    A = '(Utilities|Array|Get(acopy) (Variables|Keys|GetKeyActs) {})'
    C = '(Utilities|Array|Get(acopy) (Variables|Keys|GetKeyCtx) {})'
    D = '(Utilities|Array|Get(acopy) (Variables|Keys|GetKeyDefs) {})'
    NAMES = f'(GW|Get|{SET}|BindNames :self s)'
    KEYS_ = f'(GW|Get|{SET}|BindKeys :self s)'
    DISP = lambda k: f'(Utilities|String|ToString(Text) (Input|Key|GetKeyDisplayName :Key {k}))'
    # the engine's key names are English: what the hints and "Comment jouer" show
    FR_KEYS = '\n  '.join(f'(if (Utilities|String|EqualExactly(String) (Variables|Keys|GetKeyLbl) "{a}") (Variables|Keys|SetKeyLbl "{b}"))' for a, b in (
        ('Space Bar', 'Espace'), ('Left Shift', 'Maj'), ('Right Shift', 'Maj droite'), ('Left Ctrl', 'Ctrl'), ('Right Ctrl', 'Ctrl droit'), ('Left Alt', 'Alt'),
        ('Left Mouse Button', 'Clic gauche'), ('Right Mouse Button', 'Clic droit'), ('Middle Mouse Button', 'Clic molette'), ('Mouse Wheel Up', 'Molette haut'),
        ('Mouse Wheel Down', 'Molette bas'), ('Enter', 'Entrée'), ('Backspace', 'Retour'), ('Up', 'Haut'), ('Down', 'Bas'), ('Left', 'Gauche'), ('Right', 'Droite')))
    G = {
        # the key of row I: the saved choice, else the default
        'GWKeyAt': f"""
(fn GWKeyAt (I)
  (bind s (CallFunction|GWSettings))
  (bind ix (Utilities|Array|FindItem :TargetArray {NAMES} :ItemToFind (Utilities|GetObjectName :Object {A.format('I')})))
  (if (and (>= ix 0) (< ix (Utilities|Array|Length {KEYS_})))
    (return (Utilities|Array|Get(acopy) {KEYS_} ix)))
  (return {D.format('I')}))
""",
        'GWKeyName': f"""
(fn GWKeyName (I)
  (bind k (CallFunction|GWKeyAt :I I))
  (Variables|Keys|SetKeyLbl {DISP('k')})
  {FR_KEYS}
  (return (Variables|Keys|GetKeyLbl)))
""",
        # called when a level starts (WBP_HUD.SetupHUD) and after a change: only rows with a saved choice are touched
        'GWApplyKeys': f"""
(fn GWApplyKeys ()
  (bind s (CallFunction|GWSettings))
  (for i (range (Utilities|Array|Length (Variables|Keys|GetKeyActs)))
    (if (>= (Utilities|Array|FindItem :TargetArray {NAMES} :ItemToFind (Utilities|GetObjectName :Object {A.format('i')})) 0)
      (Mapping|UnmapAllKeysfromAction :self {C.format('i')} :Action {A.format('i')})
      (bind k (CallFunction|GWKeyAt :I i))
      (Mapping|MapKey :self {C.format('i')} :Action {A.format('i')} :ToKey k)
      (Input|RequestRebuildControlMappingsUsingContext :Context {C.format('i')} :bForceImmediately false))))
""",
        'GWStoreBind': f"""
(fn GWStoreBind (I K)
  (bind s (CallFunction|GWSettings))
  (bind nm (Utilities|GetObjectName :Object {A.format('I')}))
  (bind ix (Utilities|Array|FindItem :TargetArray {NAMES} :ItemToFind nm))
  (if (>= ix 0)
    (Utilities|Array|SetArrayElem :TargetArray {KEYS_} :Index ix :Item K)
    (else
      (Utilities|Array|Add :TargetArray {NAMES} :NewItem nm)
      (Utilities|Array|Add :TargetArray {KEYS_} :NewItem K))))
""",
        # a key already used by another row: that row takes this row's old key (no action is ever left without a key)
        'GWSetBind': f"""
(fn GWSetBind (I K)
  (Variables|Keys|SetKeyTmp (CallFunction|GWKeyAt :I I))
  (Variables|Keys|SetKeyLbl {DISP('K')})
  (for j (range (Utilities|Array|Length (Variables|Keys|GetKeyActs)))
    (if (!= j I)
      (bind kj (CallFunction|GWKeyAt :I j))
      (if (Utilities|String|EqualExactly(String) {DISP('kj')} (Variables|Keys|GetKeyLbl))
        (CallFunction|GWStoreBind :I j :K (Variables|Keys|GetKeyTmp)))))
  (CallFunction|GWStoreBind :I I :K K)
  (CallFunction|GWApplyKeys)
  (CallFunction|GWSaveSettings))
""",
        'GWResetBinds': f"""
(fn GWResetBinds ()
  (for i (range (Utilities|Array|Length (Variables|Keys|GetKeyActs)))
    (CallFunction|GWStoreBind :I i :K {D.format('i')}))
  (CallFunction|GWApplyKeys)
  (CallFunction|GWSaveSettings))
""",
        # a prompt or hint written with a default key ("E") shows the key the player chose
        'GWKeyLabel': f"""
(fn GWKeyLabel (Key)
  (Variables|Keys|SetKeyLbl Key)
  (for i (range (Utilities|Array|Length (Variables|Keys|GetKeyDefs)))
    (if (Utilities|String|EqualExactly(String) {DISP(D.format('i'))} Key)
      (Variables|Keys|SetKeyLbl (CallFunction|GWKeyName :I i))))
  (return (Variables|Keys|GetKeyLbl)))
""",
    }
    for n, code in G.items():
        write(gi, n, code, compile_after=False)
    compile_bp(gi)
    print('BP_GW_GameInstance', node_problems(gi), 'keys', [r[3] for r in rows])
    save(gi)
    return rows


def options_tree(W):
    clear_tree(W)
    add(W, unreal.CanvasPanel, 'Root')
    backdrop(W)
    p = panel(W, 'Panel', 1000, None)
    body = add(W, unreal.VerticalBox, 'Body', 'Panel')
    title(W, 'Title', 'OPTIONS', 'Body')

    def slider_row(key, label):
        row = add(W, unreal.HorizontalBox, f'Row{key}', 'Body'); box_slot(row, (0, 3, 0, 3), H.H_ALIGN_FILL)
        ls = add(W, unreal.SizeBox, f'Lbl{key}Size', f'Row{key}'); size_box(ls, w=330); box_slot(ls, (0, 0, 0, 0), H.H_ALIGN_LEFT, VA.V_ALIGN_CENTER)
        lt = add(W, unreal.TextBlock, f'Lbl{key}', f'Lbl{key}Size'); text(lt, label, 'Serif', 'Regular', 23, IVORY)
        sl = add(W, unreal.Slider, f'Sl{key}', f'Row{key}', var=True); slider_style(sl); box_slot(sl, (0, 0, 18, 0), H.H_ALIGN_FILL, VA.V_ALIGN_CENTER, fill=1.0)
        vs = add(W, unreal.SizeBox, f'Val{key}Size', f'Row{key}'); size_box(vs, w=92); box_slot(vs, (0, 0, 0, 0), H.H_ALIGN_RIGHT, VA.V_ALIGN_CENTER)
        vt = add(W, unreal.TextBlock, f'Val{key}', f'Val{key}Size', var=True); text(vt, '100 %', 'Sans', 'SemiBold', 21, GOLD_HI, just='right')

    section(W, 'SecSound', 'SON', 'Body')
    for k, l in SLIDERS[:4]:
        slider_row(k, l)
    section(W, 'SecCtl', 'CONTRÔLES', 'Body')
    for k, l in SLIDERS[4:]:
        slider_row(k, l)
    kb = deco_button(W, 'BtnKeys', 'CHANGER LES TOUCHES', 'Body', w=420, h=50, size=19); box_slot(kb, (0, 6, 0, 0), H.H_ALIGN_CENTER)
    section(W, 'SecDisp', 'AFFICHAGE', 'Body')
    qr = add(W, unreal.HorizontalBox, 'RowQ', 'Body'); box_slot(qr, (0, 4, 0, 4), H.H_ALIGN_FILL)
    ls = add(W, unreal.SizeBox, 'LblQSize', 'RowQ'); size_box(ls, w=330); box_slot(ls, (0, 0, 0, 0), H.H_ALIGN_LEFT, VA.V_ALIGN_CENTER)
    text(add(W, unreal.TextBlock, 'LblQ', 'LblQSize'), 'Qualité graphique', 'Serif', 'Regular', 23, IVORY)
    for i, q in enumerate(QUAL):
        sb = deco_button(W, f'BtnQ{i}', q, 'RowQ', w=140, h=50, size=19); box_slot(sb, (0, 0, 6, 0), H.H_ALIGN_LEFT, VA.V_ALIGN_CENTER)
    for key, label in (('Win', "Mode d'affichage"), ('Res', 'Résolution')):
        r = add(W, unreal.HorizontalBox, f'Row{key}', 'Body'); box_slot(r, (0, 4, 0, 4), H.H_ALIGN_FILL)
        ls = add(W, unreal.SizeBox, f'Lbl{key}Size', f'Row{key}'); size_box(ls, w=330); box_slot(ls, (0, 0, 0, 0), H.H_ALIGN_LEFT, VA.V_ALIGN_CENTER)
        text(add(W, unreal.TextBlock, f'Lbl{key}', f'Lbl{key}Size'), label, 'Serif', 'Regular', 23, IVORY)
        for side, glyph in (('Prev', '‹'), ('Next', '›')):
            if side == 'Next':
                vs = add(W, unreal.SizeBox, f'Txt{key}Size', f'Row{key}'); size_box(vs, w=300); box_slot(vs, (0, 0, 0, 0), H.H_ALIGN_CENTER, VA.V_ALIGN_CENTER)
                text(add(W, unreal.TextBlock, f'Txt{key}', f'Txt{key}Size', var=True), '', 'Display', 'Regular', 24, GOLD_HI, spacing=200, just='center')
            sb = deco_button(W, f'Btn{key}{side}', glyph, f'Row{key}', w=64, h=50, size=30); box_slot(sb, (0, 0, 0, 0), H.H_ALIGN_LEFT, VA.V_ALIGN_CENTER)
            call('RemoveWidget', W, infos(W)[f'Btn{key}{side}Text'].widget)
            button_style(infos(W)[f'Btn{key}{side}'], pad=(10, 6, 10, 6))
            ai = add(W, unreal.Image, f'Btn{key}{side}Arrow', f'Btn{key}{side}'); image(ai, 'T_UI_ArrowR' if side == 'Next' else 'T_UI_ArrowL', (26, 26))
    note = add(W, unreal.TextBlock, 'Note', 'Body', var=True)
    text(note, 'Les réglages sont enregistrés automatiquement.', 'Serif', 'Italic', 18, IVORY_DIM, just='center')
    box_slot(note, (0, 14, 0, 8), H.H_ALIGN_CENTER)
    fr = add(W, unreal.HorizontalBox, 'Footer', 'Body'); box_slot(fr, (0, 6, 0, 0), H.H_ALIGN_CENTER)
    sb = deco_button(W, 'BtnDefaults', 'PAR DÉFAUT', 'Footer', w=260); box_slot(sb, (0, 0, 24, 0), H.H_ALIGN_CENTER)
    sb = deco_button(W, 'BtnBack', 'RETOUR', 'Footer', w=260); box_slot(sb, (0, 0, 0, 0), H.H_ALIGN_CENTER)
    # ---- controls page (over the options panel): two columns, a label and a key selector per action
    kp = panel(W, 'KeysPanel', 1200, None, z=6)
    vis(infos(W)['KeysPanelSize'], V.COLLAPSED)
    kbody = add(W, unreal.VerticalBox, 'KeysBody', 'KeysPanel')
    title(W, 'KeysTitle', 'COMMANDES', 'KeysBody')
    khint = add(W, unreal.TextBlock, 'KeysHint', 'KeysBody')
    text(khint, 'Cliquez sur une touche, puis appuyez sur la nouvelle. Échap annule.', 'Serif', 'Italic', 19, IVORY_DIM, just='center')
    box_slot(khint, (0, 0, 0, 10), H.H_ALIGN_CENTER)
    kcols = add(W, unreal.HorizontalBox, 'KeysCols', 'KeysBody'); box_slot(kcols, (0, 0, 0, 6), H.H_ALIGN_FILL)
    kv = []
    for c in range(2):
        cv = add(W, unreal.VerticalBox, f'KeysCol{c}', 'KeysCols'); box_slot(cv, (12, 0, 12, 0), H.H_ALIGN_FILL, VA.V_ALIGN_TOP, fill=1.0)
        kv.append(f'KeysCol{c}')
    rows = key_table()
    half = (len(rows) + 1) // 2
    for i, (_, _, dk, label) in enumerate(rows):
        par = kv[0 if i < half else 1]
        r = add(W, unreal.HorizontalBox, f'KeyRow{i:02d}', par); box_slot(r, (0, 3, 0, 3), H.H_ALIGN_FILL)
        lt = add(W, unreal.TextBlock, f'KeyLbl{i:02d}', f'KeyRow{i:02d}'); text(lt, label, 'Serif', 'Regular', 22, IVORY)
        box_slot(lt, (0, 0, 8, 0), H.H_ALIGN_LEFT, VA.V_ALIGN_CENTER, fill=1.0)
        ksz = add(W, unreal.SizeBox, f'KeySz{i:02d}', f'KeyRow{i:02d}'); size_box(ksz, w=270, h=46); box_slot(ksz, (0, 0, 0, 0), H.H_ALIGN_RIGHT, VA.V_ALIGN_CENTER)
        ks = add(W, unreal.InputKeySelector, f'Key{i:02d}', f'KeySz{i:02d}', var=True)
        w = ks.widget
        st = w.get_editor_property('widget_style')
        m = (0.12, 0.3, 0.12, 0.3)
        st.set_editor_property('normal', brush(tex('T_UI_Button_Normal'), (512, 128), 'box', m))
        st.set_editor_property('hovered', brush(tex('T_UI_Button_Hover'), (512, 128), 'box', m))
        st.set_editor_property('pressed', brush(tex('T_UI_Button_Pressed'), (512, 128), 'box', m))
        w.set_editor_property('widget_style', st)
        ts = w.get_editor_property('text_style')
        ts.set_editor_property('font', font('Sans', 'SemiBold', 17))
        ts.set_editor_property('color_and_opacity', sc(GOLD_HI))
        w.set_editor_property('text_style', ts)
        w.set_editor_property('key_selection_text', unreal.Text('Appuyez…'))
        w.set_editor_property('no_key_specified_text', unreal.Text('—'))
        w.set_editor_property('allow_modifier_keys', True)
        w.set_editor_property('allow_gamepad_keys', False)
    kfix = add(W, unreal.TextBlock, 'KeysFixed', 'KeysBody')
    text(kfix, 'Fixes :  se déplacer W A S D ou flèches  ·  regarder souris  ·  menu Échap', 'Sans', 'Regular', 18, IVORY_DIM, just='center')
    box_slot(kfix, (0, 8, 0, 10), H.H_ALIGN_CENTER)
    kf = add(W, unreal.HorizontalBox, 'KeysFooter', 'KeysBody'); box_slot(kf, (0, 4, 0, 0), H.H_ALIGN_CENTER)
    sb = deco_button(W, 'BtnKeysReset', 'PAR DÉFAUT', 'KeysFooter', w=260); box_slot(sb, (0, 0, 24, 0), H.H_ALIGN_CENTER)
    sb = deco_button(W, 'BtnKeysBack', 'RETOUR', 'KeysFooter', w=260); box_slot(sb, (0, 0, 0, 0), H.H_ALIGN_CENTER)
    compile_widget(W)


def options_graph(W):
    uianim.install(W)
    key_rows = keys_setup()
    NK = len(key_rows)
    cls = unreal.load_asset('/Game/GW/UI/BP_GW_Settings').generated_class()
    ensure_var(W, 'S', obj_class=cls, category='UI')
    ensure_var(W, 'Res', struct=unreal.IntPoint.static_struct(), array=True, category='UI')
    ensure_var(W, 'ResIdx', 'int', category='UI')
    ensure_var(W, 'Quiet', 'bool', category='UI')
    fns = [('SetupOptions', []), ('Refresh', []), ('ApplyAudio', []), ('ApplyLook', []), ('SetQuality', [('Q', 'int')]),
           ('StepWin', [('D', 'int')]), ('StepRes', [('D', 'int')]), ('OnBack', []), ('OnDefaults', []), ('OptTick', [('Dt', 'float')]),
           ('Pct', [('V', 'float')])]
    for k, _ in SLIDERS:
        fns.append((f'On{k}', [('Value', 'float')]))
    for i in range(4):
        fns.append((f'OnQ{i}', []))
    for k in ('WinPrev', 'WinNext', 'ResPrev', 'ResNext', 'Keys', 'KeysBack', 'KeysReset'):
        fns.append((f'On{k}', []))
    fns.append(('RefreshKeys', []))
    fns.append(('PickKey', [('I', 'int'), ('SelectedKey', unreal.InputChord.static_struct())]))
    for i in range(NK):
        fns.append((f'OnKey{i:02d}', [('SelectedKey', unreal.InputChord.static_struct())]))
    for f, ins in fns:
        ensure_fn(W, f, inputs=ins, outputs=[('Out', 'string')] if f == 'Pct' else [])
    compile_bp(W, quiet=True)
    uianim.write_all(W)
    OV = lambda n: f'(Variables|WBP_Options|Get{n})'
    sg = lambda v: f'(GW|Get|{SET}|{v} :self (Variables|UI|GetS))'
    ss = lambda v, val: f'(GW|Set|{SET}|{v} :self (Variables|UI|GetS) :{v} {val})'
    settxt = lambda w, expr: f'(Widget|SetText(Text) :self {OV(w)} :InText (Utilities|Text|ToText(String) {expr}))'
    G = {}
    G['Pct'] = '(fn Pct (V) (return (cat (Math|Float|Round (* V 100.0)) " %")))'
    regs = '\n'.join(f'  (CallFunction|AddBtn :B {OV(b)})' for b in
                     [f'BtnQ{i}' for i in range(4)] + ['BtnWinPrev', 'BtnWinNext', 'BtnResPrev', 'BtnResNext', 'BtnDefaults', 'BtnBack', 'BtnKeys', 'BtnKeysBack', 'BtnKeysReset'])
    G['SetupOptions'] = f'''
(fn SetupOptions ()
  (Variables|UI|SetT 0.0)
  (Utilities|Array|Clear (Variables|UI|GetBtns))
  (Utilities|Array|Clear (Variables|UI|GetBtnHov))
{regs}
  (bind (res ok) (Rendering|GetSupportedFullscreenResolutions))
  (Variables|UI|SetRes res)
  (bind cur (Settings|GetScreenResolution :self (Settings|GetGameUserSettings)))
  (bind (cx cy) (Utilities|Struct|BreakIntPoint cur))
  (Variables|UI|SetResIdx (- (Utilities|Array|Length res) 1))
  (for i (range (Utilities|Array|Length res))
    (bind (rx ry) (Utilities|Struct|BreakIntPoint (Utilities|Array|Get(acopy) res i)))
    (if (and (== rx cx) (== ry cy))
      (Variables|UI|SetResIdx i)))
  (bind gi {GI_CAST}
    (:then
      (bind s (GW|Call|BP_GW_GameInstance|GWSettings :self gi))
      (Variables|UI|SetS s)
      (Class|Slider|SetValue :self {OV('SlMaster')} :Value {sg('MasterVol')})
      (Class|Slider|SetValue :self {OV('SlMusic')} :Value {sg('MusicVol')})
      (Class|Slider|SetValue :self {OV('SlSfx')} :Value {sg('SfxVol')})
      (Class|Slider|SetValue :self {OV('SlUI')} :Value {sg('UIVol')})
      (Class|Slider|SetValue :self {OV('SlSens')} :Value (/ (- {sg('MouseSens')} 0.2) 2.8))
      (Class|Slider|SetValue :self {OV('SlFov')} :Value (/ (- {sg('FOV')} 70.0) 40.0))
      (CallFunction|Refresh))
    (:CastFailed)))
'''
    qcol = '\n'.join(f'''  (Class|Button|SetBackgroundColor :self {OV(f"BtnQ{i}")} :BackgroundColor (select (== q {i}) (Math|Color|MakeColor 3.0 2.3 1.3 1.0) (Math|Color|MakeColor 0.45 0.45 0.45 1.0)))
  (Class|Button|SetColorandOpacity :self {OV(f"BtnQ{i}")} :ColorAndOpacity (select (== q {i}) (Math|Color|MakeColor 1.0 0.85 0.5 1.0) (Math|Color|MakeColor 0.6 0.6 0.6 1.0)))''' for i in range(4))
    G['Refresh'] = f'''
(fn Refresh ()
  (if (not ({ISVALID} :Object (Variables|UI|GetS)))
    (return))
  {settxt('ValMaster', '(CallFunction|Pct :V ' + sg('MasterVol') + ')')}
  {settxt('ValMusic', '(CallFunction|Pct :V ' + sg('MusicVol') + ')')}
  {settxt('ValSfx', '(CallFunction|Pct :V ' + sg('SfxVol') + ')')}
  {settxt('ValUI', '(CallFunction|Pct :V ' + sg('UIVol') + ')')}
  {settxt('ValSens', '(cat "× " (Utilities|String|Left :SourceString (Utilities|String|ToString(Float) ' + sg('MouseSens') + ') :Count 4))')}
  {settxt('ValFov', '(cat (Math|Float|Round ' + sg('FOV') + ') "°")')}
  (bind q {sg('Quality')})
{qcol}
  (bind wm {sg('WindowMode')})
  {settxt('TxtWin', '(select (== wm 0) "PLEIN ÉCRAN" (select (== wm 1) "PLEIN ÉCRAN FENÊTRÉ" "FENÊTRÉ"))')}
  (bind res (Variables|UI|GetRes))
  (if (> (Utilities|Array|Length res) 0)
    (bind (rx ry) (Utilities|Struct|BreakIntPoint (Utilities|Array|Get(acopy) res (Variables|UI|GetResIdx))))
    {settxt('TxtRes', '(cat rx " × " ry)')}
    (else
      {settxt('TxtRes', '"—"')})))
'''
    G['ApplyAudio'] = f'''
(fn ApplyAudio ()
  (bind gi {GI_CAST}
    (:then (GW|Call|BP_GW_GameInstance|GWApplyAudio :self gi))
    (:CastFailed)))
'''
    G['ApplyLook'] = f'''
(fn ApplyLook ()
  (bind pc (Utilities|Casting|CastToBP_GW_PlayerController (Widget|GetOwningPlayer))
    (:then (GW|Call|BP_GW_PlayerController|UIApplyLook :self pc :Sens {sg('MouseSens')}))
    (:CastFailed)))
'''
    for k, var in (('Master', 'MasterVol'), ('Music', 'MusicVol'), ('Sfx', 'SfxVol'), ('UI', 'UIVol')):
        G[f'On{k}'] = f'''
(fn On{k} (Value)
  (if ({ISVALID} :Object (Variables|UI|GetS))
    {ss(var, 'Value')}
    (CallFunction|ApplyAudio)
    (CallFunction|Refresh)))
'''
    G['OnSens'] = f'''
(fn OnSens (Value)
  (if ({ISVALID} :Object (Variables|UI|GetS))
    {ss('MouseSens', '(+ 0.2 (* Value 2.8))')}
    (CallFunction|ApplyLook)
    (CallFunction|Refresh)))
'''
    G['OnFov'] = f'''
(fn OnFov (Value)
  (if ({ISVALID} :Object (Variables|UI|GetS))
    {ss('FOV', '(Math|Float|Round (+ 70.0 (* Value 40.0)))')}
    (CallFunction|Refresh)))
'''
    G['SetQuality'] = f'''
(fn SetQuality (Q)
  (if ({ISVALID} :Object (Variables|UI|GetS))
    {ss('Quality', 'Q')}
    (bind gi {GI_CAST}
      (:then
        (GW|Call|BP_GW_GameInstance|GWApplyGraphics :self gi :Display false)
        (CallFunction|Refresh))
      (:CastFailed))))
'''
    for i in range(4):
        G[f'OnQ{i}'] = f'(fn OnQ{i} () (CallFunction|SetQuality :Q {i}))'
    G['StepWin'] = f'''
(fn StepWin (D)
  (if ({ISVALID} :Object (Variables|UI|GetS))
    {ss('WindowMode', '(% (+ (+ ' + sg('WindowMode') + ' D) 3) 3)')}
    (bind gi {GI_CAST}
      (:then
        (GW|Call|BP_GW_GameInstance|GWApplyGraphics :self gi :Display true)
        (CallFunction|Refresh))
      (:CastFailed))))
'''
    G['StepRes'] = f'''
(fn StepRes (D)
  (bind res (Variables|UI|GetRes))
  (bind n (Utilities|Array|Length res))
  (if (or (== n 0) (not ({ISVALID} :Object (Variables|UI|GetS))))
    (return))
  (Variables|UI|SetResIdx (Math|Integer|Clamp(Integer) :Value (+ (Variables|UI|GetResIdx) D) :Min 0 :Max (- n 1)))
  (bind (rx ry) (Utilities|Struct|BreakIntPoint (Utilities|Array|Get(acopy) res (Variables|UI|GetResIdx))))
  {ss('ResX', 'rx')}
  {ss('ResY', 'ry')}
  (bind gi {GI_CAST}
    (:then
      (GW|Call|BP_GW_GameInstance|GWApplyGraphics :self gi :Display true)
      (CallFunction|Refresh))
    (:CastFailed)))
'''
    G['OnWinPrev'] = '(fn OnWinPrev () (CallFunction|StepWin :D -1))'
    G['OnWinNext'] = '(fn OnWinNext () (CallFunction|StepWin :D 1))'
    G['OnResPrev'] = '(fn OnResPrev () (CallFunction|StepRes :D -1))'
    G['OnResNext'] = '(fn OnResNext () (CallFunction|StepRes :D 1))'
    G['OnDefaults'] = f'''
(fn OnDefaults ()
  (Class|Slider|SetValue :self {OV('SlMaster')} :Value 1.0)
  (Class|Slider|SetValue :self {OV('SlMusic')} :Value 0.7)
  (Class|Slider|SetValue :self {OV('SlSfx')} :Value 1.0)
  (Class|Slider|SetValue :self {OV('SlUI')} :Value 0.8)
  (Class|Slider|SetValue :self {OV('SlSens')} :Value 0.2857)
  (Class|Slider|SetValue :self {OV('SlFov')} :Value 0.5)
  (CallFunction|OnMaster :Value 1.0)
  (CallFunction|OnMusic :Value 0.7)
  (CallFunction|OnSfx :Value 1.0)
  (CallFunction|OnUI :Value 0.8)
  (CallFunction|OnSens :Value 0.2857)
  (CallFunction|OnFov :Value 0.5)
  (CallFunction|SetQuality :Q 3))
'''
    KEYSEL = 'GW|Call|/Script/UMG.InputKeySelector|SetSelectedKey'
    GIK = 'BP_GW_GameInstance'
    G['RefreshKeys'] = f'''
(fn RefreshKeys ()
  (bind gi {GI_CAST}
    (:then
''' + '\n'.join(f'''      (bind k{i} (GW|Call|{GIK}|GWKeyAt :self gi :I {i}))
      ({KEYSEL} :self {OV(f"Key{i:02d}")} :InSelectedKey (Utilities|Struct|MakeInputChord :Key k{i}))''' for i in range(NK)) + f''')
    (:CastFailed)))
'''
    # SetSelectedKey above fires OnKeySelected too: Quiet stops RefreshKeys from re-entering PickKey
    G['PickKey'] = f'''
(fn PickKey (I SelectedKey)
  (if (Variables|UI|GetQuiet)
    (return))
  (bind (pk ps pc pa pm) (Utilities|Struct|BreakInputChord SelectedKey))
  (bind nm (Utilities|String|ToString(Text) (Input|Key|GetKeyDisplayName :Key pk)))
  (Variables|UI|SetQuiet true)
  (if (not (or (Utilities|String|EqualExactly(String) nm "Escape") (or (Utilities|String|EqualExactly(String) nm "F2") (not (Input|Key|IsValidKey :Key pk)))))
    (bind gi {GI_CAST}
      (:then
        (GW|Call|{GIK}|GWSetBind :self gi :I I :K pk))
      (:CastFailed)))
  (CallFunction|RefreshKeys)
  (Variables|UI|SetQuiet false))
'''
    for i in range(NK):
        G[f'OnKey{i:02d}'] = f'(fn OnKey{i:02d} (SelectedKey) (CallFunction|PickKey :I {i} :SelectedKey SelectedKey))'
    G['OnKeys'] = f'''
(fn OnKeys ()
  (Variables|UI|SetQuiet true)
  (CallFunction|RefreshKeys)
  (Variables|UI|SetQuiet false)
  (Widget|SetVisibility :self {OV('KeysPanelSize')} :InVisibility "Visible")
  (Widget|SetVisibility :self {OV('PanelSize')} :InVisibility "Collapsed"))
'''
    G['OnKeysBack'] = f'''
(fn OnKeysBack ()
  (Audio|PlaySound2D :Sound "/Game/GW/Audio/S_UI_Back.S_UI_Back")
  (Widget|SetVisibility :self {OV('KeysPanelSize')} :InVisibility "Collapsed")
  (Widget|SetVisibility :self {OV('PanelSize')} :InVisibility "Visible"))
'''
    G['OnKeysReset'] = f'''
(fn OnKeysReset ()
  (bind gi {GI_CAST}
    (:then
      (GW|Call|{GIK}|GWResetBinds :self gi)
      (Variables|UI|SetQuiet true)
      (CallFunction|RefreshKeys)
      (Variables|UI|SetQuiet false))
    (:CastFailed)))
'''
    G['OnBack'] = f'''
(fn OnBack ()
  (Audio|PlaySound2D :Sound "/Game/GW/Audio/S_UI_Back.S_UI_Back")
  (bind gi {GI_CAST}
    (:then
      (GW|Call|BP_GW_GameInstance|GWSaveSettings :self gi)
      (Widget|RemovefromParent :self self))
    (:CastFailed
      (Widget|RemovefromParent :self self))))
'''
    G['OptTick'] = f'''
(fn OptTick (Dt)
  (bind t (+ (Variables|UI|GetT) Dt))
  (Variables|UI|SetT t)
  (bind e (CallFunction|Ease :V (/ t 0.35)))
  (bind p {OV('PanelSize')})
  (Widget|SetRenderOpacity :self p :InOpacity e)
  (bind sc (+ 0.96 (* 0.04 e)))
  (Widget|Transform|SetRenderScale :self p :Scale (Math|Vector2D|MakeVector2D sc sc))
  (CallFunction|AnimButtons :Dt Dt))
'''
    G['EventGraph'] = '''
(event UserInterface|EventConstruct
  (CallFunction|SetupOptions))

(event UserInterface|EventTick (MyGeometry InDeltaTime)
  (CallFunction|OptTick :Dt InDeltaTime))
'''
    for name, code in G.items():
        write(W, name, code, compile_after=False)
    compile_bp(W, quiet=True)
    for k, _ in SLIDERS:
        bind(W, f'Sl{k}', 'OnValueChanged', f'On{k}', unreal.Slider)
    for i in range(NK):
        bind(W, f'Key{i:02d}', 'OnKeySelected', f'OnKey{i:02d}', unreal.InputKeySelector)
    for b, fn in (('BtnKeys', 'OnKeys'), ('BtnKeysBack', 'OnKeysBack'), ('BtnKeysReset', 'OnKeysReset')):
        bind(W, b, 'OnClicked', fn)
    for i in range(4):
        bind(W, f'BtnQ{i}', 'OnClicked', f'OnQ{i}')
    for k in ('WinPrev', 'WinNext', 'ResPrev', 'ResNext'):
        bind(W, f'Btn{k}', 'OnClicked', f'On{k}')
    bind(W, 'BtnBack', 'OnClicked', 'OnBack')
    bind(W, 'BtnDefaults', 'OnClicked', 'OnDefaults')
    compile_bp(W)
    print(node_problems(W))
    compile_widget(W)


# ======================================================================================== HOW TO
CARDS = [
    ('Blend', 'T_UI_HowBlend', 'FONDEZ-VOUS', "Vous avez l'apparence exacte des convives. Marchez, flânez, arrêtez-vous comme eux. Courir est louche : chaque joueur vous cherche."),
    ('Hunt', 'T_UI_HowHunt', 'DÉMASQUEZ', "Tous les joueurs sont des invités. Après 20 secondes de dispersion, repérez qui agit bizarrement et frappez : fusil, lame, épée, piège, bombe, lustre."),
    ('Penalty', 'T_UI_HowPenalty', 'ENRICHISSEZ-VOUS', "Volez, fouillez, jouez, achetez : quatre objets en poche. Abattre un convive rapporte 100 $, mais son cri s'entend partout et vous trahit."),
    ('Ghost', 'T_UI_HowGhost', 'LES FANTÔMES', "Éliminé, vous devenez un fantôme : volez librement et regardez la fin de la manche."),
]
# (default key(s) as the engine names them, or fixed text; label), one list per row. The current key is read when the screen opens (GWKeyLabel).
KEYS = [[(None, 'WASD', 'se déplacer'), (None, 'SOURIS', 'regarder'), ('Left Shift', None, 'courir'), ('Space Bar', None, 'sauter'), ('Left Mouse Button', None, 'tirer, utiliser'),
         (None, 'CLIC DROIT', 'viser')],
        [('E', None, 'parler, acheter, fouiller'), (('1', '4'), None, 'objets'), ('Q', None, 'jeter'), ('C', None, 'vue'), ('V', None, 'danser'), ('Tab', None, 'scores'), (None, 'ÉCHAP', 'menu')]]


def howto_tree(W):
    clear_tree(W)
    add(W, unreal.CanvasPanel, 'Root')
    backdrop(W)
    panel(W, 'Panel', 1640, None)
    body = add(W, unreal.VerticalBox, 'Body', 'Panel')
    title(W, 'Title', 'COMMENT JOUER', 'Body', size=48)
    sub = add(W, unreal.TextBlock, 'Sub', 'Body')
    text(sub, "Manoir Ashcombe, 1932. Parmi les invités masqués se cachent des joueurs. Un seul quittera le bal.", 'Serif', 'Italic', 21, IVORY, just='center')
    box_slot(sub, (0, 0, 0, 16), H.H_ALIGN_CENTER)
    row = add(W, unreal.HorizontalBox, 'Cards', 'Body'); box_slot(row, (0, 0, 0, 14), H.H_ALIGN_CENTER)
    for key, tex_name, ttl, body_txt in CARDS:
        cs = add(W, unreal.SizeBox, f'Card{key}Size', 'Cards'); size_box(cs, w=356, h=512); box_slot(cs, (10, 0, 10, 0), H.H_ALIGN_CENTER, VA.V_ALIGN_TOP)
        pivot(cs)
        c = add(W, unreal.Border, f'Card{key}', f'Card{key}Size', var=True)
        border_brush(c, 'T_UI_Card', (0.12, 0.08, 0.12, 0.08), pad=(22, 22, 22, 20), size=(320, 480))
        v = add(W, unreal.VerticalBox, f'Card{key}V', f'Card{key}')
        im = add(W, unreal.Image, f'Card{key}Img', f'Card{key}V'); image(im, tex_name, (312, 172)); box_slot(im, (0, 0, 0, 12), H.H_ALIGN_CENTER)
        t = add(W, unreal.TextBlock, f'Card{key}Title', f'Card{key}V'); text(t, ttl, 'Display', 'Regular', 24, BURG_C, spacing=150, just='center', shadow=False)
        box_slot(t, (14, 0, 14, 6), H.H_ALIGN_CENTER)
        d = add(W, unreal.Image, f'Card{key}Div', f'Card{key}V'); image(d, 'T_UI_Divider', (200, 42), tint=(0.55, 0.42, 0.25, 1)); box_slot(d, (0, 0, 0, 6), H.H_ALIGN_CENTER)
        b = add(W, unreal.TextBlock, f'Card{key}Body', f'Card{key}V'); text(b, body_txt, 'Serif', 'Regular', 17, INK_C, just='center', wrap=296, shadow=False)
        box_slot(b, (0, 0, 0, 0), H.H_ALIGN_CENTER)
    win = add(W, unreal.TextBlock, 'Win', 'Body')
    text(win, "Le dernier joueur en vie gagne la manche. Si plusieurs survivent aux 4 minutes, ils se partagent la victoire.",
         'Serif', 'Regular', 20, IVORY, just='center', wrap=1400)
    box_slot(win, (0, 0, 0, 12), H.H_ALIGN_CENTER)
    i = 0
    for r, row in enumerate(KEYS):
        kr = add(W, unreal.HorizontalBox, f'Keys{r}', 'Body'); box_slot(kr, (0, 0, 0, 8 if r == 0 else 14), H.H_ALIGN_CENTER)
        for dk, fixed, lbl in row:
            kb = add(W, unreal.Border, f'Key{i}', f'Keys{r}'); border_brush(kb, 'T_UI_Field', (0.1, 0.2, 0.1, 0.2), pad=(12, 4, 12, 6), size=(128, 32))
            box_slot(kb, (8, 0, 6, 0), H.H_ALIGN_CENTER, VA.V_ALIGN_CENTER)
            text(add(W, unreal.TextBlock, f'Key{i}Text', f'Key{i}', var=True), (fixed or '?'), 'Sans', 'SemiBold', 17, GOLD_HI)
            lt = add(W, unreal.TextBlock, f'Key{i}Lbl', f'Keys{r}'); text(lt, lbl, 'Serif', 'Italic', 18, IVORY)
            box_slot(lt, (8, 0, 14, 0), H.H_ALIGN_CENTER, VA.V_ALIGN_CENTER)
            i += 1
    sb = deco_button(W, 'BtnBack', 'RETOUR', 'Body', w=280); box_slot(sb, (0, 0, 0, 0), H.H_ALIGN_CENTER)
    compile_widget(W)


def howto_graph(W):
    uianim.install(W)
    for f, ins in [('SetupHow', []), ('OnBack', []), ('HowTick', [('Dt', 'float')])]:
        ensure_fn(W, f, inputs=ins)
    compile_bp(W, quiet=True)
    uianim.write_all(W)
    OV = lambda n: f'(Variables|WBP_HowTo|Get{n})'
    cards = ' '.join(f'"{k}"' for k, *_ in CARDS)
    _kl = lambda k: f'(GW|Call|BP_GW_GameInstance|GWKeyLabel :self gi :Key "{k}")'
    _keys, _i = [], 0
    for _row in KEYS:
        for _dk, _fixed, _l in _row:
            if _dk:
                _val = f'(cat {_kl(_dk[0])} "-" {_kl(_dk[1])})' if isinstance(_dk, tuple) else _kl(_dk)
                _keys.append(f'(Widget|SetText(Text) :self {OV(f"Key{_i}Text")} :InText (Utilities|Text|ToText(String) {_val}))')
            _i += 1
    _keys = '\n      '.join(_keys)
    anim = '\n'.join(f'''  (bind e{i} (CallFunction|Ease :V (/ (- t (+ 0.15 (* {i} 0.09))) 0.45)))
  (Widget|SetRenderOpacity :self {OV(f"Card{k}")} :InOpacity e{i})
  (Widget|Transform|SetRenderTranslation :self {OV(f"Card{k}")} :Translation (Math|Vector2D|MakeVector2D 0.0 (* 36.0 (- 1.0 e{i}))))'''
                     for i, (k, *_) in enumerate(CARDS))
    G = {
        'SetupHow': f'''
(fn SetupHow ()
  (Variables|UI|SetT 0.0)
  (Utilities|Array|Clear (Variables|UI|GetBtns))
  (Utilities|Array|Clear (Variables|UI|GetBtnHov))
  (CallFunction|AddBtn :B {OV('BtnBack')})
  (bind gi (Utilities|Casting|CastToBP_GW_GameInstance (Widget|GetGameInstance))
    (:then
      {_keys})
    (:CastFailed)))
''',
        'OnBack': '''
(fn OnBack ()
  (Audio|PlaySound2D :Sound "/Game/GW/Audio/S_UI_Back.S_UI_Back")
  (Widget|RemovefromParent :self self))
''',
        'HowTick': f'''
(fn HowTick (Dt)
  (bind t (+ (Variables|UI|GetT) Dt))
  (Variables|UI|SetT t)
  (bind e (CallFunction|Ease :V (/ t 0.35)))
  (Widget|SetRenderOpacity :self {OV('PanelSize')} :InOpacity e)
{anim}
  (CallFunction|AnimButtons :Dt Dt))
''',
        'EventGraph': '''
(event UserInterface|EventConstruct
  (CallFunction|SetupHow))

(event UserInterface|EventTick (MyGeometry InDeltaTime)
  (CallFunction|HowTick :Dt InDeltaTime))
''',
    }
    for name, code in G.items():
        write(W, name, code, compile_after=False)
    compile_bp(W, quiet=True)
    bind(W, 'BtnBack', 'OnClicked', 'OnBack')
    compile_bp(W)
    print(node_problems(W))
    compile_widget(W)


# ======================================================================================== PAUSE
PBTN = [('BtnResume', 'REPRENDRE'), ('BtnOptions', 'OPTIONS'), ('BtnHowTo', 'COMMENT JOUER'), ('BtnLeave', 'QUITTER LA PARTIE')]


def pause_tree(W):
    clear_tree(W)
    add(W, unreal.CanvasPanel, 'Root')
    backdrop(W, blur=6, dim=0.45)
    panel(W, 'Panel', 640, 700)
    body = add(W, unreal.VerticalBox, 'Body', 'Panel')
    ic = add(W, unreal.Image, 'Icon', 'Body'); image(ic, 'T_UI_IcoMaskDeco', (84, 84)); box_slot(ic, (0, 0, 0, 0), H.H_ALIGN_CENTER)
    title(W, 'Title', 'INTERMÈDE', 'Body', size=44)
    sub = add(W, unreal.TextBlock, 'Sub', 'Body')
    text(sub, 'Le bal continue pendant que ce menu est ouvert.', 'Serif', 'Italic', 20, IVORY_DIM, just='center')
    box_slot(sub, (0, 0, 0, 18), H.H_ALIGN_CENTER)
    mv = add(W, unreal.VerticalBox, 'MainBtns', 'Body', var=True); box_slot(mv, (0, 0, 0, 0), H.H_ALIGN_CENTER)
    for n, l in PBTN:
        sb = deco_button(W, n, l, 'MainBtns', w=440, h=64, size=26); box_slot(sb, (0, 5, 0, 5), H.H_ALIGN_CENTER)
    cv = add(W, unreal.VerticalBox, 'Confirm', 'Body', var=True); box_slot(cv, (0, 0, 0, 0), H.H_ALIGN_CENTER)
    q = add(W, unreal.TextBlock, 'ConfirmText', 'Confirm', var=True)
    text(q, 'Quitter la partie et revenir au menu principal ?', 'Serif', 'Regular', 23, IVORY, just='center', wrap=500)
    box_slot(q, (0, 6, 0, 6), H.H_ALIGN_CENTER)
    qn = add(W, unreal.TextBlock, 'ConfirmNote', 'Confirm', var=True)
    text(qn, '', 'Serif', 'Italic', 19, (0.95, 0.55, 0.45, 1), just='center', wrap=500)
    box_slot(qn, (0, 0, 0, 14), H.H_ALIGN_CENTER)
    sb = deco_button(W, 'BtnYes', 'OUI, QUITTER', 'Confirm', w=400, h=62, size=25); box_slot(sb, (0, 4, 0, 4), H.H_ALIGN_CENTER)
    sb = deco_button(W, 'BtnNo', 'NON, RESTER', 'Confirm', w=400, h=62, size=25); box_slot(sb, (0, 4, 0, 4), H.H_ALIGN_CENTER)
    vis(cv, V.COLLAPSED)
    compile_widget(W)


def pause_graph(W):
    uianim.install(W)
    ensure_var(W, 'Closing', 'bool', category='UI')
    ensure_var(W, 'SubW', obj_class=unreal.UserWidget, category='UI')
    for f in ['SetupPause', 'ClosePause', 'OnResume', 'OnOptions', 'OnHowTo', 'OnLeave', 'OnYes', 'OnNo']:
        ensure_fn(W, f)
    ensure_fn(W, 'PauseTick', inputs=[('Dt', 'float')])
    compile_bp(W, quiet=True)
    uianim.write_all(W)
    OV = lambda n: f'(Variables|WBP_Pause|Get{n})'
    regs = '\n'.join(f'  (CallFunction|AddBtn :B {OV(b)})' for b, _ in PBTN + [('BtnYes', ''), ('BtnNo', '')])
    sub = lambda cls: f'''
  (bind w (UserInterface|CreateWidget :Class "/Game/GW/UI/{cls}.{cls}_C" :OwningPlayer (Widget|GetOwningPlayer)))
  (Variables|UI|SetSubW w)
  (UserInterface|Viewport|AddtoViewport :self w :ZOrder 60))
'''
    G = {
        'SetupPause': f'''
(fn SetupPause ()
  (Variables|UI|SetT 0.0)
  (Variables|UI|SetClosing false)
  (Utilities|Array|Clear (Variables|UI|GetBtns))
  (Utilities|Array|Clear (Variables|UI|GetBtnHov))
{regs}
  (Widget|SetVisibility :self {OV('Confirm')} :InVisibility "Collapsed")
  (Widget|SetVisibility :self {OV('MainBtns')} :InVisibility "Visible")
  (Audio|PlaySound2D :Sound "/Game/GW/Audio/S_UI_Card.S_UI_Card" :VolumeMultiplier 0.7)
  (bind pc (Utilities|Casting|CastToBP_GW_PlayerController (Widget|GetOwningPlayer))
    (:then (GW|Call|BP_GW_PlayerController|UISetPauseInput :self pc :Paused true))
    (:CastFailed)))
''',
        'ClosePause': f'''
(fn ClosePause ()
  (if (Variables|UI|GetClosing)
    (return))
  (Variables|UI|SetClosing true)
  (bind sw (Variables|UI|GetSubW))
  (if ({ISVALID} :Object sw)
    (Widget|RemovefromParent :self sw))
  (Audio|PlaySound2D :Sound "/Game/GW/Audio/S_UI_Back.S_UI_Back")
  (Widget|RemovefromParent :self self)
  (bind pc (Utilities|Casting|CastToBP_GW_PlayerController (Widget|GetOwningPlayer))
    (:then (GW|Call|BP_GW_PlayerController|UISetPauseInput :self pc :Paused false))
    (:CastFailed)))
''',
        'OnResume': '(fn OnResume () (CallFunction|ClosePause))',
        'OnOptions': '(fn OnOptions ()' + sub('WBP_Options'),
        'OnHowTo': '(fn OnHowTo ()' + sub('WBP_HowTo'),
        'OnLeave': f'''
(fn OnLeave ()
  (Widget|SetVisibility :self {OV('MainBtns')} :InVisibility "Collapsed")
  (Widget|SetVisibility :self {OV('Confirm')} :InVisibility "Visible")
  (Widget|SetText(Text) :self {OV('ConfirmNote')} :InText (Utilities|Text|ToText(String) (select (Networking|HasAuthority :self (Widget|GetOwningPlayer)) "Vous êtes l'hôte : la partie s'arrêtera pour tous les joueurs." ""))))
''',
        'OnNo': f'''
(fn OnNo ()
  (Widget|SetVisibility :self {OV('Confirm')} :InVisibility "Collapsed")
  (Widget|SetVisibility :self {OV('MainBtns')} :InVisibility "Visible"))
''',
        'OnYes': '''
(fn OnYes ()
  (Development|ExecuteConsoleCommand :Command "disconnect" :SpecificPlayer (Widget|GetOwningPlayer)))
''',
        'PauseTick': f'''
(fn PauseTick (Dt)
  (bind t (+ (Variables|UI|GetT) Dt))
  (Variables|UI|SetT t)
  (bind e (CallFunction|Ease :V (/ t 0.3)))
  (bind p {OV('PanelSize')})
  (Widget|SetRenderOpacity :self p :InOpacity e)
  (Widget|Transform|SetRenderTranslation :self p :Translation (Math|Vector2D|MakeVector2D 0.0 (* 24.0 (- 1.0 e))))
  (CallFunction|AnimButtons :Dt Dt))
''',
        'EventGraph': '''
(event UserInterface|EventConstruct
  (CallFunction|SetupPause))

(event UserInterface|EventTick (MyGeometry InDeltaTime)
  (CallFunction|PauseTick :Dt InDeltaTime))
''',
    }
    for name, code in G.items():
        write(W, name, code, compile_after=False)
    compile_bp(W, quiet=True)
    for b, fn in [('BtnResume', 'OnResume'), ('BtnOptions', 'OnOptions'), ('BtnHowTo', 'OnHowTo'), ('BtnLeave', 'OnLeave'), ('BtnYes', 'OnYes'), ('BtnNo', 'OnNo')]:
        bind(W, b, 'OnClicked', fn)
    compile_bp(W)
    print(node_problems(W))
    compile_widget(W)


if which in ('all', 'options'):
    W = get_or_create('WBP_Options'); options_tree(W); options_graph(W)
if which in ('all', 'howto'):
    W = get_or_create('WBP_HowTo'); howto_tree(W); howto_graph(W)
if which in ('all', 'pause'):
    W = get_or_create('WBP_Pause'); pause_tree(W); pause_graph(W)
