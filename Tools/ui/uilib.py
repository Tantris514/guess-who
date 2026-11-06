"""UMG + Blueprint helpers for the ui agent's build scripts (run inside the editor through Tools/ui/ue.sh)."""
import sys, importlib
import unreal
sys.path.insert(0, r'J:\Projets\Unreal_Projects\Guess Who\Tools\gameplay')
import gw_lib
importlib.reload(gw_lib)
from gw_lib import BT, BGE, EAL, ensure_var, ensure_fn, get_graph, compile_bp, node_problems  # noqa: F401
from gw_lib import write as _dsl_write


def clean_graph(bp, graph_name):
    """Empty a graph before a DSL rewrite. The transpiler only deletes stale nodes that are unreachable from an exec root,
    so an old body still wired to the function entry's parameter pins survived every rewrite (the HUD had ~14k dead nodes).
    Keeps the function entry and result nodes (they carry the signature; links broken), deletes everything else."""
    g = get_graph(bp, graph_name)
    if g is None:
        return 0
    n = 0
    for node in list(BT.find_nodes(g)):
        if node.get_class().get_name() in ('K2Node_FunctionEntry', 'K2Node_FunctionResult'):
            for p in node.list_all_pins():
                for c in list(p.list_connected_pins()):
                    p.break_single_pin_link(c)
            continue
        BT.delete_node(node)
        n += 1
    return n


def write(bp, graph_name, code, compile_after=True):
    clean_graph(bp, graph_name)
    _dsl_write(bp, graph_name, code, compile_after)


def save(*assets):
    """Save and verify (a -game test process holding the .uasset makes the save fail silently)."""
    import time
    for a in assets:
        ok = False
        for attempt in range(4):
            ok = EAL.save_loaded_asset(a, only_if_is_dirty=False)
            if ok:
                break
            time.sleep(2.0)
        print(('saved ' if ok else '!!! SAVE FAILED ') + a.get_path_name())

_UO = unreal.get_default_object(unreal.UMGToolSet.static_class())
UI = '/Game/GW/UI'
TEX = '/Game/GW/UI/Textures'
V = unreal.SlateVisibility
H = unreal.HorizontalAlignment
VA = unreal.VerticalAlignment

GOLD = (0.66, 0.40, 0.10, 1)        # linear-space colours (UMG colours are linear)
GOLD_HI = (0.92, 0.73, 0.32, 1)
IVORY = (0.86, 0.80, 0.66, 1)
IVORY_DIM = (0.55, 0.50, 0.42, 1)
INK = (0.025, 0.02, 0.016, 1)
BURGUNDY = (0.28, 0.02, 0.03, 1)
EMERALD = (0.02, 0.16, 0.10, 1)
BLACK = (0, 0, 0, 1)


def call(name, *a):
    return _UO.call_method(name, args=a)


def lc(c):
    return unreal.LinearColor(*c)


def sc(c):
    return unreal.SlateColor(specified_color=lc(c))


def font_obj(fam):
    return unreal.load_asset(f'{UI}/Fonts/F_GW_{fam}')


def tex(name):
    return unreal.load_asset(f'{TEX}/{name}')


def snd(name):
    return unreal.load_asset(f'/Game/GW/Audio/{name}')


# ---------------------------------------------------------------- widget tree
def get_or_create(name, folder=UI):
    p = f'{folder}/{name}'
    if EAL.does_asset_exist(p):
        return unreal.load_asset(p)
    return call('CreateWidgetBlueprint', folder, name, unreal.UserWidget.static_class())


def infos(wbp):
    return {str(w.widget_name): w for w in call('GetWidgets', wbp).widgets}


def add(wbp, cls, name, parent=None, var=False):
    ex = infos(wbp)
    if name in ex:
        info = ex[name]
    else:
        pw = ex[parent].widget if parent else None
        if isinstance(cls, type):
            cls = cls.static_class()
        info = call('AddWidget', wbp, cls, name, pw, -1)
    if var:
        call('ToggleWidgetAsVariable', wbp, info.widget, True)
    return info


def clear_tree(wbp, keep=()):
    """Remove every root-level widget (and so the whole tree)."""
    for name, inf in list(infos(wbp).items()):
        if name in keep:
            continue
        try:
            parent = inf.widget.get_parent()
        except Exception:
            parent = None
        if parent is None and name in infos(wbp):
            call('RemoveWidget', wbp, inf.widget)


# ---------------------------------------------------------------- styling
def font(fam='Serif', face='Regular', size=18, spacing=0, outline=0, outline_col=(0, 0, 0, 0.8)):
    f = unreal.SlateFontInfo()
    f.set_editor_property('font_object', font_obj(fam))
    f.set_editor_property('typeface_font_name', face)
    f.set_editor_property('size', size)
    f.set_editor_property('letter_spacing', spacing)
    if outline:
        o = unreal.FontOutlineSettings()
        o.set_editor_property('outline_size', outline)
        o.set_editor_property('outline_color', lc(outline_col))
        f.set_editor_property('outline_settings', o)
    return f


def text(info, value, fam='Serif', face='Regular', size=18, color=IVORY, spacing=0, just='left', wrap=0, shadow=True,
         outline=0, auto_wrap=False):
    t = info.widget
    t.set_editor_property('text', unreal.Text(value))
    t.set_editor_property('font', font(fam, face, size, spacing, outline))
    t.set_editor_property('color_and_opacity', sc(color))
    t.set_editor_property('justification', {'left': unreal.TextJustify.LEFT, 'center': unreal.TextJustify.CENTER,
                                            'right': unreal.TextJustify.RIGHT}[just])
    if wrap:
        t.set_editor_property('wrap_text_at', float(wrap))
    if auto_wrap:
        t.set_editor_property('auto_wrap_text', True)
    if shadow:
        t.set_editor_property('shadow_offset', unreal.Vector2D(1.5, 1.5))
        t.set_editor_property('shadow_color_and_opacity', unreal.LinearColor(0, 0, 0, 0.9))
    else:
        t.set_editor_property('shadow_color_and_opacity', unreal.LinearColor(0, 0, 0, 0))
    return t


def brush(tex_obj=None, size=(32, 32), draw='image', margin=None, tint=(1, 1, 1, 1)):
    b = unreal.SlateBrush()
    if tex_obj is not None:
        b.set_editor_property('resource_object', tex_obj)
    sz = unreal.DeprecateSlateVector2D()
    sz.set_editor_property('x', float(size[0])); sz.set_editor_property('y', float(size[1]))
    b.set_editor_property('image_size', sz)
    b.set_editor_property('draw_as', {'image': unreal.SlateBrushDrawType.IMAGE, 'box': unreal.SlateBrushDrawType.BOX,
                                      'border': unreal.SlateBrushDrawType.BORDER, 'none': unreal.SlateBrushDrawType.NO_DRAW_TYPE}[draw])
    if margin is not None:
        m = margin if isinstance(margin, (tuple, list)) else (margin,) * 4
        b.set_editor_property('margin', unreal.Margin(*m))
    b.set_editor_property('tint_color', sc(tint))
    return b


def image(info, tex_name, size=None, tint=(1, 1, 1, 1), draw='image', margin=None):
    t = tex(tex_name) if isinstance(tex_name, str) else tex_name
    if size is None:
        size = (t.blueprint_get_size_x(), t.blueprint_get_size_y()) if t else (32, 32)
    info.widget.set_editor_property('brush', brush(t, size, draw, margin, tint))
    return info.widget


def border_brush(info, tex_name, margin, tint=(1, 1, 1, 1), pad=None, size=(64, 64)):
    w = info.widget
    w.set_editor_property('background', brush(tex(tex_name), size, 'box', margin, tint))
    w.set_editor_property('brush_color', lc((1, 1, 1, 1)))
    if pad is not None:
        w.set_editor_property('padding', unreal.Margin(*pad))
    return w


def slate_sound(name):
    s = unreal.SlateSound()
    if name:
        s.set_editor_property('resource_object', snd(name))
    return s


def button_style(info, normal='T_UI_Button_Normal', hover='T_UI_Button_Hover', pressed='T_UI_Button_Pressed',
                 disabled='T_UI_Button_Disabled', margin=(0.12, 0.3, 0.12, 0.3), size=(512, 128), hover_snd='S_UI_Hover',
                 press_snd='S_UI_Click', pad=(28, 10, 28, 10)):
    w = info.widget
    st = w.get_editor_property('widget_style')
    st.set_editor_property('normal', brush(tex(normal), size, 'box', margin))
    st.set_editor_property('hovered', brush(tex(hover), size, 'box', margin))
    st.set_editor_property('pressed', brush(tex(pressed), size, 'box', margin))
    st.set_editor_property('disabled', brush(tex(disabled), size, 'box', margin))
    st.set_editor_property('normal_padding', unreal.Margin(*pad))
    st.set_editor_property('pressed_padding', unreal.Margin(pad[0], pad[1] + 2, pad[2], pad[3] - 2))
    try:
        if hover_snd and EAL.does_asset_exist(f'/Game/GW/Audio/{hover_snd}'):
            st.set_editor_property('hovered_slate_sound', slate_sound(hover_snd))
        if press_snd and EAL.does_asset_exist(f'/Game/GW/Audio/{press_snd}'):
            st.set_editor_property('pressed_slate_sound', slate_sound(press_snd))
    except Exception as e:
        print('sound style skipped', e)
    w.set_editor_property('widget_style', st)
    w.set_editor_property('background_color', lc((1, 1, 1, 1)))
    w.set_editor_property('color_and_opacity', lc((1, 1, 1, 1)))
    # pivot in the middle so the hover scale grows evenly
    w.set_editor_property('render_transform_pivot', unreal.Vector2D(0.5, 0.5))
    return w


def flat_button(info, hover_snd='S_UI_Hover', press_snd='S_UI_Click'):
    """Invisible button (no art) used for text links, arrows, card hit areas."""
    w = info.widget
    st = w.get_editor_property('widget_style')
    for k in ('normal', 'hovered', 'pressed', 'disabled'):
        st.set_editor_property(k, brush(None, (8, 8), 'none'))
    st.set_editor_property('normal_padding', unreal.Margin(4, 2, 4, 2))
    st.set_editor_property('pressed_padding', unreal.Margin(4, 3, 4, 1))
    if hover_snd and EAL.does_asset_exist(f'/Game/GW/Audio/{hover_snd}'):
        st.set_editor_property('hovered_slate_sound', slate_sound(hover_snd))
    if press_snd and EAL.does_asset_exist(f'/Game/GW/Audio/{press_snd}'):
        st.set_editor_property('pressed_slate_sound', slate_sound(press_snd))
    w.set_editor_property('widget_style', st)
    w.set_editor_property('render_transform_pivot', unreal.Vector2D(0.5, 0.5))
    return w


def slider_style(info, bar_h=16, thumb=26):
    w = info.widget
    st = w.get_editor_property('widget_style')
    bar = brush(tex('T_UI_SliderBar'), (256, 8), 'image', None, tint=(0.75, 0.6, 0.4, 0.85))
    for k in ('normal_bar_image', 'hovered_bar_image', 'disabled_bar_image'):
        try:
            st.set_editor_property(k, bar)
        except Exception:
            pass
    th = brush(tex('T_UI_SliderThumb'), (thumb, thumb))
    thh = brush(tex('T_UI_SliderThumb'), (thumb, thumb), tint=(1.25, 1.15, 1.0, 1))
    for k, b in (('normal_thumb_image', th), ('hovered_thumb_image', thh), ('disabled_thumb_image', th)):
        try:
            st.set_editor_property(k, b)
        except Exception:
            pass
    try:
        st.set_editor_property('bar_thickness', 2.0)
    except Exception:
        pass
    w.set_editor_property('widget_style', st)
    w.set_editor_property('slider_bar_color', lc((1, 1, 1, 1)))
    w.set_editor_property('slider_handle_color', lc((1, 1, 1, 1)))
    w.set_editor_property('step_size', 0.05)
    return w


def textbox_style(info, size=20):
    w = info.widget
    st = w.get_editor_property('widget_style')
    b = brush(tex('T_UI_Field'), (256, 64), 'box', (0.1, 0.2, 0.1, 0.2))
    bh = brush(tex('T_UI_Field'), (256, 64), 'box', (0.1, 0.2, 0.1, 0.2), tint=(1.3, 1.2, 1.0, 1))
    for k, v in (('background_image_normal', b), ('background_image_hovered', bh), ('background_image_focused', bh),
                 ('background_image_read_only', b)):
        st.set_editor_property(k, v)
    st.set_editor_property('padding', unreal.Margin(14, 8, 14, 9))
    try:
        ts = st.get_editor_property('text_style')
        ts.set_editor_property('font', font('Serif', 'Regular', size))
        ts.set_editor_property('color_and_opacity', sc(IVORY))
        st.set_editor_property('text_style', ts)
    except Exception:
        st.set_editor_property('font', font('Serif', 'Regular', size))
    st.set_editor_property('foreground_color', sc(IVORY))
    w.set_editor_property('widget_style', st)
    return w


# ---------------------------------------------------------------- slots
def canvas(info, anchors=((0, 0), (0, 0)), align=(0, 0), pos=(0, 0), size=(0, 0), auto=False, z=0):
    s = info.slot
    mn, mx = anchors
    ld = unreal.AnchorData()
    ld.set_editor_property('offsets', unreal.Margin(pos[0], pos[1], size[0], size[1]))
    ld.set_editor_property('anchors', unreal.Anchors(minimum=unreal.Vector2D(*mn), maximum=unreal.Vector2D(*mx)))
    ld.set_editor_property('alignment', unreal.Vector2D(*align))
    s.set_editor_property('layout_data', ld)
    s.set_editor_property('auto_size', auto)
    s.set_editor_property('z_order', z)


FILL = ((0, 0), (1, 1))


def box_slot(info, pad=(0, 0, 0, 0), h=H.H_ALIGN_FILL, v=VA.V_ALIGN_CENTER, fill=None):
    s = info.slot
    s.set_editor_property('padding', unreal.Margin(*pad))
    s.set_editor_property('horizontal_alignment', h)
    s.set_editor_property('vertical_alignment', v)
    if fill is not None:
        s.set_editor_property('size', unreal.SlateChildSize(float(fill), unreal.SlateSizeRule.FILL))


def overlay_slot(info, h=H.H_ALIGN_FILL, v=VA.V_ALIGN_FILL, pad=(0, 0, 0, 0)):
    s = info.slot
    s.set_editor_property('horizontal_alignment', h)
    s.set_editor_property('vertical_alignment', v)
    s.set_editor_property('padding', unreal.Margin(*pad))


def border_slot_content(info, h=H.H_ALIGN_FILL, v=VA.V_ALIGN_FILL):
    w = info.widget
    w.set_editor_property('horizontal_alignment', h)
    w.set_editor_property('vertical_alignment', v)


def size_box(info, w=None, h=None, min_w=None, min_h=None):
    sb = info.widget
    if w is not None:
        sb.set_editor_property('width_override', float(w)); sb.set_editor_property('override_width_override', True)
    if h is not None:
        sb.set_editor_property('height_override', float(h)); sb.set_editor_property('override_height_override', True)
    if min_w is not None:
        sb.set_editor_property('min_desired_width', float(min_w)); sb.set_editor_property('override_min_desired_width', True)
    if min_h is not None:
        sb.set_editor_property('min_desired_height', float(min_h)); sb.set_editor_property('override_min_desired_height', True)


def vis(info, v):
    info.widget.set_editor_property('visibility', v)


def pivot(info, x=0.5, y=0.5):
    info.widget.set_editor_property('render_transform_pivot', unreal.Vector2D(x, y))


def bind(wbp, widget_name, event, fn, widget_cls=unreal.Button):
    """Bind a widget delegate (OnClicked, OnValueChanged...) to a call of function fn (data pins forwarded by name)."""
    IN, OUT = unreal.EdGraphPinDirection.EGPD_INPUT, unreal.EdGraphPinDirection.EGPD_OUTPUT
    g = get_graph(wbp, 'EventGraph')
    ed = BGE.get_graph_editor(g)

    def find():
        return [n for n in BT.find_nodes(g) if n.get_class().get_name() == 'K2Node_ComponentBoundEvent'
                and widget_name in n.get_node_title() and event.replace('On', '') in n.get_node_title().replace(' ', '')]
    ev = find()
    if not ev:
        call('BindToEventProperty', wbp, event, widget_name, widget_cls.static_class())
        ev = find()
    assert ev, f'could not bind {widget_name}.{event}'
    ev = ev[0]
    then = gw_lib._pin(ev, 'then', OUT)
    if then.list_connected_pins():
        tgt = then.list_connected_pins()[0].get_owning_node()
        if tgt.get_node_title().replace(' ', '') == fn.replace(' ', ''):
            return ev
        for c in list(then.list_connected_pins()):
            then.break_single_pin_link(c)
    c = ed.add_call_function_node(fn)
    assert c is not None, f'no function {fn}'
    p = ev.get_node_pos()
    c.set_node_pos(unreal.IntPoint(p.x + 450, p.y))
    assert then.try_create_connection(gw_lib._pin(c, 'execute', IN))
    # forward data outputs (e.g. Value) to same-named inputs
    for p_out in ev.list_all_pins():
        if p_out.get_pin_direction() == OUT and str(p_out.get_pin_name()) not in ('then', 'OutputDelegate'):
            p_in = gw_lib._pin(c, str(p_out.get_pin_name()), IN)
            if p_in is not None:
                p_out.try_create_connection(p_in)
    return ev


def compile_widget(wbp):
    call('CompileWidgetBlueprint', wbp)
    save(wbp)


def local_var(bp, fn, name, typ):
    g = get_graph(bp, fn)
    if name not in BT.list_variables(bp, g):
        BT.add_variable(bp, name, typ, graph=g)
