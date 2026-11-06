"""Creates/refreshes the widget trees of WBP_HUD and WBP_MainMenu (layout only; graphs come later)."""
import unreal

EAL = unreal.EditorAssetLibrary
_UO = unreal.get_default_object(unreal.UMGToolSet.static_class())


class _UMG:
    def __getattr__(self, name):
        camel = ''.join(part.capitalize() for part in name.split('_'))
        return lambda *a: _UO.call_method(camel, args=a)


U = _UMG()
UI = '/Game/GW/UI'
ROBOTO = unreal.load_asset('/Engine/EngineFonts/Roboto')
MONO = unreal.load_asset('/Engine/EngineFonts/DroidSansMono')
GOLD = (0.83, 0.62, 0.26, 1)
IVORY = (0.93, 0.90, 0.82, 1)
GREY = (0.62, 0.60, 0.56, 1)
V = unreal.SlateVisibility


def lc(c):
    return unreal.LinearColor(*c)


def get_or_create(name):
    p = f'{UI}/{name}'
    if EAL.does_asset_exist(p):
        return unreal.load_asset(p)
    return U.create_widget_blueprint(UI, name, unreal.UserWidget.static_class())


def existing(wbp):
    return {str(w.widget_name): w for w in U.get_widgets(wbp).widgets}


def add(wbp, cls, name, parent=None):
    ex = existing(wbp)
    if name in ex:
        return ex[name]
    pw = ex[parent].widget if parent else None
    return U.add_widget(wbp, cls.static_class(), name, pw, -1)


def font(size, face='Regular', spacing=0, mono=False):
    f = unreal.SlateFontInfo()
    f.set_editor_property('font_object', MONO if mono else ROBOTO)
    f.set_editor_property('typeface_font_name', face)
    f.set_editor_property('size', size)
    f.set_editor_property('letter_spacing', spacing)
    return f


def text(info, value, size=16, color=IVORY, face='Regular', spacing=0, center=False, wrap=0, mono=False, shadow=True):
    t = info.widget
    t.set_editor_property('text', unreal.Text(value))
    t.set_editor_property('font', font(size, face, spacing, mono))
    t.set_editor_property('color_and_opacity', unreal.SlateColor(specified_color=lc(color)))
    if center:
        t.set_editor_property('justification', unreal.TextJustify.CENTER)
    if wrap:
        t.set_editor_property('wrap_text_at', float(wrap))
    if shadow:
        t.set_editor_property('shadow_offset', unreal.Vector2D(1.5, 1.5))
        t.set_editor_property('shadow_color_and_opacity', unreal.LinearColor(0, 0, 0, 0.85))


def canvas(info, anchors, align, pos=(0, 0), size=None, auto=True, z=0):
    s = info.slot
    mn, mx = anchors
    if size is None:
        size = (0, 0)
    ld = unreal.AnchorData()
    ld.set_editor_property('offsets', unreal.Margin(pos[0], pos[1], size[0], size[1]))
    ld.set_editor_property('anchors', unreal.Anchors(minimum=unreal.Vector2D(*mn), maximum=unreal.Vector2D(*mx)))
    ld.set_editor_property('alignment', unreal.Vector2D(*align))
    s.set_editor_property('layout_data', ld)
    s.set_editor_property('auto_size', auto)
    s.set_editor_property('z_order', z)


def vslot(info, pad=(0, 4, 0, 4), halign=unreal.HorizontalAlignment.H_ALIGN_CENTER):
    s = info.slot
    s.set_editor_property('padding', unreal.Margin(*pad))
    s.set_editor_property('horizontal_alignment', halign)


def var(wbp, info, on=True):
    U.toggle_widget_as_variable(wbp, info.widget, on)


def build_hud():
    w = get_or_create('WBP_HUD')
    root = add(w, unreal.CanvasPanel, 'Root')
    # blindfold
    b = add(w, unreal.Border, 'Blindfold', 'Root')
    canvas(b, ((0, 0), (1, 1)), (0, 0), auto=False, z=5)
    b.widget.set_editor_property('brush_color', unreal.LinearColor(0, 0, 0, 1))
    b.widget.set_editor_property('horizontal_alignment', unreal.HorizontalAlignment.H_ALIGN_CENTER)
    b.widget.set_editor_property('vertical_alignment', unreal.VerticalAlignment.V_ALIGN_CENTER)
    b.widget.set_editor_property('visibility', V.HIDDEN)
    var(w, b)
    t = add(w, unreal.TextBlock, 'BlindText', 'Blindfold')
    text(t, 'Vous avez les yeux bandés…', 30, IVORY, 'Light', 100, center=True, wrap=900)
    var(w, t)
    # top center
    tp = add(w, unreal.VerticalBox, 'TopPanel', 'Root')
    canvas(tp, ((0.5, 0), (0.5, 0)), (0.5, 0), (0, 22), z=6)
    r = add(w, unreal.TextBlock, 'TxtRole', 'TopPanel')
    text(r, 'SALLE D\'ATTENTE', 34, GOLD, 'Bold', 350, center=True)
    vslot(r)
    var(w, r)
    i = add(w, unreal.TextBlock, 'TxtInfo', 'TopPanel')
    text(i, '', 17, IVORY, 'Regular', 0, center=True, wrap=760)
    vslot(i)
    var(w, i)
    # top left status
    sp = add(w, unreal.VerticalBox, 'StatusPanel', 'Root')
    canvas(sp, ((0, 0), (0, 0)), (0, 0), (32, 26), z=6)
    for name, size, col in (('TxtTimer', 30, IVORY), ('TxtHiders', 17, IVORY), ('TxtHealth', 19, (0.95, 0.45, 0.35, 1))):
        x = add(w, unreal.TextBlock, name, 'StatusPanel')
        text(x, '', size, col, 'Bold' if name == 'TxtTimer' else 'Regular')
        vslot(x, (0, 2, 0, 2), unreal.HorizontalAlignment.H_ALIGN_LEFT)
        var(w, x)
    # crosshair
    c = add(w, unreal.TextBlock, 'Crosshair', 'Root')
    text(c, '+', 30, (1, 1, 1, 0.9), 'Light', center=True)
    canvas(c, ((0.5, 0.5), (0.5, 0.5)), (0.5, 0.5), z=4)
    c.widget.set_editor_property('visibility', V.HIDDEN)
    var(w, c)
    # center message
    m = add(w, unreal.TextBlock, 'TxtCenter', 'Root')
    text(m, '', 38, GOLD, 'Bold', 150, center=True, wrap=1100)
    canvas(m, ((0.5, 0.28), (0.5, 0.28)), (0.5, 0.5), z=7)
    var(w, m)
    # event feed
    ev = add(w, unreal.TextBlock, 'TxtEvent', 'Root')
    text(ev, '', 21, GOLD, 'Regular', 0, center=True, wrap=900)
    canvas(ev, ((0.5, 0.18), (0.5, 0.18)), (0.5, 0.5), z=7)
    var(w, ev)
    # scoreboard
    sb = add(w, unreal.Border, 'ScorePanel', 'Root')
    canvas(sb, ((0.5, 0.58), (0.5, 0.58)), (0.5, 0.5), z=8)
    sb.widget.set_editor_property('brush_color', unreal.LinearColor(0.01, 0.01, 0.01, 0.78))
    sb.widget.set_editor_property('padding', unreal.Margin(28, 20, 28, 20))
    sb.widget.set_editor_property('visibility', V.HIDDEN)
    var(w, sb)
    st = add(w, unreal.TextBlock, 'TxtScores', 'ScorePanel')
    text(st, '', 17, IVORY, 'Regular', mono=True)
    var(w, st)
    # hint
    h = add(w, unreal.TextBlock, 'TxtHint', 'Root')
    text(h, 'Tab : scores    ·    Maj : courir (louche !)    ·    Clic gauche : tirer (détective)    ·    Échap : quitter', 13, GREY, center=True)
    canvas(h, ((0.5, 1), (0.5, 1)), (0.5, 1), (0, -14), z=6)
    U.compile_widget_blueprint(w)
    EAL.save_loaded_asset(w, False)
    print('HUD widgets:', sorted(existing(w).keys()))


def button(w, name, label, parent, size=20):
    btn = add(w, unreal.Button, name, parent)
    btn.widget.set_editor_property('background_color', unreal.LinearColor(0.30, 0.22, 0.10, 1))
    var(w, btn)
    t = add(w, unreal.TextBlock, name + 'Text', name)
    text(t, label, size, GOLD, 'Bold', 250, center=True, shadow=False)
    t.slot.set_editor_property('padding', unreal.Margin(24, 8, 24, 8))
    return btn


def build_menu():
    w = get_or_create('WBP_MainMenu')
    add(w, unreal.CanvasPanel, 'Root')
    if 'Background' not in existing(w):  # later wrapped in a ScaleBox with the key art (s21_keyart.py)
        bg = add(w, unreal.Image, 'Background', 'Root')
        canvas(bg, ((0, 0), (1, 1)), (0, 0), auto=False, z=0)
        bg.widget.set_editor_property('color_and_opacity', unreal.LinearColor(0.035, 0.025, 0.02, 1))
        var(w, bg)
    box = add(w, unreal.Border, 'MenuBox', 'Root')
    canvas(box, ((0.5, 0.5), (0.5, 0.5)), (0.5, 0.5), z=1)
    box.widget.set_editor_property('brush_color', unreal.LinearColor(0.012, 0.010, 0.008, 0.86))
    box.widget.set_editor_property('padding', unreal.Margin(56, 40, 56, 36))
    vb = add(w, unreal.VerticalBox, 'MenuVBox', 'MenuBox')
    t = add(w, unreal.TextBlock, 'Title', 'MenuVBox'); text(t, 'LE BAL MASQUÉ', 58, GOLD, 'Bold', 520, center=True); vslot(t, (0, 0, 0, 2))
    t = add(w, unreal.TextBlock, 'Subtitle', 'MenuVBox'); text(t, 'MANOIR ASHCOMBE  ·  1932', 17, IVORY, 'Light', 600, center=True); vslot(t, (0, 0, 0, 6))
    t = add(w, unreal.TextBlock, 'Tagline', 'MenuVBox'); text(t, 'Fondez-vous parmi les invités… ou démasquez les imposteurs.', 15, GREY, 'Italic', 0, center=True); vslot(t, (0, 0, 0, 26))
    t = add(w, unreal.TextBlock, 'LblName', 'MenuVBox'); text(t, 'VOTRE NOM', 13, GREY, 'Bold', 200); vslot(t, (0, 4, 0, 4), unreal.HorizontalAlignment.H_ALIGN_FILL)
    nb = add(w, unreal.EditableTextBox, 'NameBox', 'MenuVBox'); vslot(nb, (0, 0, 0, 14), unreal.HorizontalAlignment.H_ALIGN_FILL); var(w, nb)
    nb.widget.set_editor_property('text', unreal.Text('Invité'))
    nb.widget.set_editor_property('hint_text', unreal.Text('Votre nom'))
    b = button(w, 'BtnHost', 'HÉBERGER UNE PARTIE', 'MenuVBox'); vslot(b, (0, 4, 0, 18), unreal.HorizontalAlignment.H_ALIGN_FILL)
    t = add(w, unreal.TextBlock, 'LblIp', 'MenuVBox'); text(t, 'ADRESSE IP DE L\'HÔTE', 13, GREY, 'Bold', 200); vslot(t, (0, 4, 0, 4), unreal.HorizontalAlignment.H_ALIGN_FILL)
    row = add(w, unreal.HorizontalBox, 'JoinRow', 'MenuVBox'); vslot(row, (0, 0, 0, 18), unreal.HorizontalAlignment.H_ALIGN_FILL)
    ip = add(w, unreal.EditableTextBox, 'IpBox', 'JoinRow'); var(w, ip)
    ip.widget.set_editor_property('text', unreal.Text('127.0.0.1'))
    ip.slot.set_editor_property('size', unreal.SlateChildSize(1.0, unreal.SlateSizeRule.FILL))
    ip.slot.set_editor_property('vertical_alignment', unreal.VerticalAlignment.V_ALIGN_CENTER)
    ip.slot.set_editor_property('padding', unreal.Margin(0, 0, 10, 0))
    b = button(w, 'BtnJoin', 'REJOINDRE', 'JoinRow')
    b = button(w, 'BtnQuit', 'QUITTER', 'MenuVBox', 16); vslot(b, (0, 4, 0, 10), unreal.HorizontalAlignment.H_ALIGN_FILL)
    t = add(w, unreal.TextBlock, 'TxtStatus', 'MenuVBox'); text(t, '', 15, IVORY, 'Regular', 0, center=True, wrap=560); vslot(t); var(w, t)
    t = add(w, unreal.TextBlock, 'TxtHelp', 'MenuVBox')
    text(t, 'Partie en réseau local ou par Internet (port 7777/UDP redirigé chez l\'hôte). 2 à 10 joueurs.', 12, GREY, 'Regular', 0, center=True, wrap=560, shadow=False)
    vslot(t, (0, 8, 0, 0))
    U.compile_widget_blueprint(w)
    EAL.save_loaded_asset(w, False)
    print('Menu widgets:', sorted(existing(w).keys()))


build_hud()
build_menu()
