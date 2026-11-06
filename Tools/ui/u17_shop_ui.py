"""WBP_Shop: the vendors' menu card (barman, junkie or waiter: PC.ShopKind picks the title and the prices;
the firecracker row only shows at the junkie's) (E near the barman, Tools/gameplay/s34_shop.py). Your money, one row per item
(key, name, short description, how many you have, price; rows you cannot afford are greyed out and disabled), the
last purchase / refusal from the server, a "Fermer" button. Mouse cursor on while it is open (PC.OpenShop sets the
input mode); E again, walking away or "Fermer" closes it. A full-screen backdrop catches the clicks so nothing
fires behind the card. Buttons call BP_GW_PlayerController.ShopBuy(Id) ("GWBuy <id>" on the server).
Usage: ue_run.py u17_shop_ui.py  (then Tools/gameplay/s34_shop.py if it ran before this widget existed)
"""
import sys
sys.path.insert(0, r'J:\Projets\Unreal_Projects\Guess Who\Tools\ui')
import importlib, uilib
importlib.reload(uilib)
from uilib import *
import gw_lib

import shop_items; importlib.reload(shop_items)                 # Tools/gameplay/shop_items.py: the catalogue
ITEMS = [(i, n, d, bp, k) for i, n, d, bp, jp, k, h in shop_items.ITEMS]
JPRICE = {i[0]: i[4] for i in shop_items.ITEMS}
VENDORS = shop_items.VENDORS
PCCAST = '(Utilities|Casting|CastToBP_GW_PlayerController (Widget|GetOwningPlayer))'
PSCAST = '(Utilities|Casting|CastToBP_GW_PlayerState (GW|Get|/Script/Engine.Controller|PlayerState :self (Widget|GetOwningPlayer)))'
OV = lambda n: f'(Variables|WBP_Shop|Get{n})'
BURG = (0.62, 0.16, 0.12, 1)

# the PC side must exist before the buttons bind to it (s34_shop.py writes the bodies)
pc = unreal.load_asset('/Game/GW/Blueprints/BP_GW_PlayerController')
if not (gw_lib.get_graph(pc, 'ShopBuy') and gw_lib.get_graph(pc, 'CloseShop') and 'ShopKind' in [str(v) for v in BT.list_variables(pc)]):
    ensure_fn(pc, 'ShopBuy', inputs=[('Id', 'int')])                  # only on a fresh project (s34 makes them too)
    ensure_fn(pc, 'CloseShop')
    ensure_var(pc, 'ShopKind', 'int', category='Shop')
    compile_bp(pc, quiet=True)

W = get_or_create('WBP_Shop')
clear_tree(W)
add(W, unreal.CanvasPanel, 'Root')
bd = add(W, unreal.Image, 'Backdrop', 'Root', var=True)
bd.widget.set_editor_property('brush', brush(None, (8, 8), 'image', tint=(0.0, 0.0, 0.0, 0.55)))
canvas(bd, FILL, z=0)
vis(bd, V.VISIBLE)                                            # swallows clicks: nothing fires behind the card
cs = add(W, unreal.SizeBox, 'CardSize', 'Root', var=True); size_box(cs, w=1120)
canvas(cs, ((0.5, 0.5), (0.5, 0.5)), (0.5, 0.5), auto=True, z=2); pivot(cs)
card = add(W, unreal.Border, 'Card', 'CardSize')
border_brush(card, 'T_UI_PanelSmall', 0.18, tint=(1, 1, 1, 0.97), pad=(46, 22, 46, 18), size=(200, 200))
body = add(W, unreal.VerticalBox, 'Body', 'Card')
t = add(W, unreal.TextBlock, 'Title', 'Body', var=True); text(t, "LE BAR D'ASHCOMBE", 'Display', 'Regular', 36, GOLD_HI, spacing=420, just='center')
box_slot(t, (0, 0, 0, 0), H.H_ALIGN_CENTER)
s = add(W, unreal.TextBlock, 'Sub', 'Body', var=True)
text(s, '« Qu’est-ce que je vous sers ? »  — le barman', 'Serif', 'Italic', 20, IVORY, just='center')
box_slot(s, (0, 2, 0, 2), H.H_ALIGN_CENTER)
dv = add(W, unreal.Image, 'Div', 'Body'); image(dv, 'T_UI_Divider', (220, 46), tint=(0.75, 0.58, 0.3, 1)); box_slot(dv, (0, 0, 0, 0), H.H_ALIGN_CENTER)
mr = add(W, unreal.HorizontalBox, 'MoneyRow', 'Body'); box_slot(mr, (0, 0, 0, 6), H.H_ALIGN_CENTER)
ml = add(W, unreal.TextBlock, 'MoneyLbl', 'MoneyRow'); text(ml, 'Votre bourse :  ', 'Serif', 'Regular', 22, IVORY)
box_slot(ml, (0, 0, 0, 0), H.H_ALIGN_LEFT, VA.V_ALIGN_CENTER)
tm = add(W, unreal.TextBlock, 'TxtMoney', 'MoneyRow', var=True); text(tm, '0 $', 'Display', 'Regular', 36, GOLD_HI, spacing=80)
box_slot(tm, (0, 0, 0, 0), H.H_ALIGN_LEFT, VA.V_ALIGN_CENTER); pivot(tm, 0.0, 0.5)
rows = add(W, unreal.VerticalBox, 'Rows', 'Body'); box_slot(rows, (0, 0, 0, 6), H.H_ALIGN_FILL)
for i, name, desc, price, key in ITEMS:
    b = add(W, unreal.Button, f'Buy{i}', 'Rows', var=True); box_slot(b, (0, 2, 0, 2), H.H_ALIGN_FILL)
    st = b.widget.get_editor_property('widget_style')
    for k, tint in (('normal', (0.0, 0.0, 0.0, 0.32)), ('hovered', (0.92, 0.73, 0.32, 0.2)), ('pressed', (0.92, 0.73, 0.32, 0.34)),
                    ('disabled', (0.0, 0.0, 0.0, 0.14))):
        st.set_editor_property(k, brush(None, (8, 8), 'image', tint=tint))
    st.set_editor_property('normal_padding', unreal.Margin(14, 3, 14, 3))
    st.set_editor_property('pressed_padding', unreal.Margin(14, 4, 14, 2))
    if EAL.does_asset_exist('/Game/GW/Audio/S_UI_Hover'):
        st.set_editor_property('hovered_slate_sound', slate_sound('S_UI_Hover'))
    b.widget.set_editor_property('widget_style', st)
    hb = add(W, unreal.HorizontalBox, f'RowH{i}', f'Buy{i}')
    hb.widget.slot.set_editor_property('horizontal_alignment', H.H_ALIGN_FILL)
    hb.widget.slot.set_editor_property('vertical_alignment', VA.V_ALIGN_CENTER)
    # one row per item, name beside the description: the rows must fit on the screen with the title and the close button
    ic = add(W, unreal.Image, f'Ico{i}', f'RowH{i}')
    _tp = f'/Game/GW/UI/Items/T_UI_Item_{i:02d}'
    ic.widget.set_editor_property('brush', brush(unreal.load_asset(_tp) if EAL.does_asset_exist(_tp) else None, (38, 38), 'image'))
    box_slot(ic, (0, 0, 10, 0), H.H_ALIGN_LEFT, VA.V_ALIGN_CENTER)
    iv = add(W, unreal.HorizontalBox, f'Info{i}', f'RowH{i}'); box_slot(iv, (0, 0, 10, 0), H.H_ALIGN_FILL, VA.V_ALIGN_CENTER, fill=1.0)
    nb = add(W, unreal.SizeBox, f'NameBox{i}', f'Info{i}'); size_box(nb, w=280); box_slot(nb, (0, 0, 8, 0), H.H_ALIGN_LEFT, VA.V_ALIGN_CENTER)
    nm = add(W, unreal.TextBlock, f'Name{i}', f'NameBox{i}', var=True); text(nm, name, 'Serif', 'Bold', 21, IVORY)
    de = add(W, unreal.TextBlock, f'Desc{i}', f'Info{i}'); text(de, desc, 'Serif', 'Italic', 15, IVORY_DIM, wrap=540)
    box_slot(de, (0, 0, 0, 0), H.H_ALIGN_LEFT, VA.V_ALIGN_CENTER, fill=1.0)
    ow = add(W, unreal.TextBlock, f'Own{i}', f'RowH{i}', var=True); text(ow, '', 'Sans', 'SemiBold', 16, IVORY, just='right')
    box_slot(ow, (0, 0, 14, 0), H.H_ALIGN_RIGHT, VA.V_ALIGN_CENTER)
    pb = add(W, unreal.SizeBox, f'PriceBox{i}', f'RowH{i}'); size_box(pb, w=100); box_slot(pb, (0, 0, 0, 0), H.H_ALIGN_RIGHT, VA.V_ALIGN_CENTER)
    pr = add(W, unreal.TextBlock, f'Price{i}', f'PriceBox{i}', var=True); text(pr, f'{price} $', 'Display', 'Regular', 26, GOLD_HI, just='right')
nt = add(W, unreal.TextBlock, 'TxtNote', 'Body', var=True); text(nt, '', 'Serif', 'Italic', 19, (0.95, 0.88, 0.62, 1), just='center', wrap=760)
box_slot(nt, (0, 4, 0, 8), H.H_ALIGN_CENTER)
ft = add(W, unreal.HorizontalBox, 'Foot', 'Body'); box_slot(ft, (0, 0, 0, 0), H.H_ALIGN_CENTER)
cb = add(W, unreal.Button, 'Close', 'Foot', var=True); button_style(cb, pad=(40, 8, 40, 8)); box_slot(cb, (0, 0, 24, 0), H.H_ALIGN_LEFT, VA.V_ALIGN_CENTER)
ct = add(W, unreal.TextBlock, 'CloseTxt', 'Close'); text(ct, 'FERMER', 'Display', 'Regular', 22, IVORY, spacing=300, just='center')
hn = add(W, unreal.TextBlock, 'Hint', 'Foot'); text(hn, 'E : fermer  ·  gagnez de l’argent : instruments, PNJ abattus, pièges, corps fouillés, objets volés', 'Sans', 'Regular', 15, IVORY_DIM)
box_slot(hn, (0, 0, 0, 0), H.H_ALIGN_LEFT, VA.V_ALIGN_CENTER)
compile_widget(W)

for v, typ in (('T', 'float'), ('Pulse', 'float'), ('LastMoney', 'int'), ('Kind', 'int')):
    ensure_var(W, v, typ, category='Shop')
ensure_fn(W, 'SetupShop')
ensure_fn(W, 'ShopTick', inputs=[('Dt', 'float')])
ensure_fn(W, 'Ease', inputs=[('V', 'float')], outputs=[('R', 'float')], pure=True)
ensure_fn(W, 'OnClose')
ensure_fn(W, 'ReadKind')
for i, *_ in ITEMS:
    ensure_fn(W, f'OnBuy{i}')
compile_bp(W, quiet=True)
local_var(W, 'ShopTick', 'Mn', 'int')

C = lambda c: f'(Utilities|Struct|MakeSlateColor :SpecifiedColor (Math|Color|MakeColor {c[0]} {c[1]} {c[2]} {c[3]}))'
OWN = {9: '(select (> {c} 0) (cat "×" {c}) "")', 1: '(select (> {a} 0) (cat "×" {a}) "")', 2: '(select (> {s} 0) (cat "×" {s}) "")', 3: '(select {l} "à vous" "")',
       4: '(select (> {g} 0) (cat "×" {g}) "")', 5: '(select (> {t} 0) (cat "×" {t}) "")', 6: '(select (> {b} 0) (cat "×" {b}) "")',
       7: '(select (> {tu} 0) (cat {tu} " en réserve") "")', 8: '(select {sw} "à vous" "")', 10: '(select {bl} "à vous" "")', 14: '(select (> {m} 0) (cat "×" {m}) "")'}
P = lambda v: f'(GW|Get|BP_GW_PlayerState|{v} :self ps)'
FMT = dict(c=P('Crackers'), a=P('Ammo'), s=P('Smokes'), l=P('HasLamp'), g=P('Gases'), t=P('Traps'), b=P('Bombs'), tu=P('TurretAmmo'), sw=P('HasSwapGun'), bl=P('HasBlade'), m=P('Masks'))
rows_code = []
KIND1 = '(== (Variables|Shop|GetKind) 1)'
for i, name, desc, price, key in ITEMS:
    owned = {3: P('HasLamp'), 8: P('HasSwapGun'), 10: P('HasBlade')}.get(i, 'false')
    pr = f'(select {KIND1} {JPRICE[i]} {price})'
    rows_code.append(f'''      (Widget|SetText(Text) :self {OV(f"Price{i}")} :InText (Utilities|Text|ToText(String) (cat {pr} " $")))
      (bind en{i} (and (and (>= (Variables|Default|GetMn) {pr}) (> {pr} 0)) (not {owned})))
      (Widget|SetIsEnabled :self {OV(f"Buy{i}")} :bInIsEnabled en{i})
      (Class|Text|SetColorandOpacity :self {OV(f"Name{i}")} :ColorAndOpacity (select en{i} {C(IVORY)} {C(IVORY_DIM)}))
      (Class|Text|SetColorandOpacity :self {OV(f"Price{i}")} :ColorAndOpacity (select en{i} {C(GOLD_HI)} {C(BURG)}))
      (Widget|SetText(Text) :self {OV(f"Own{i}")} :InText (Utilities|Text|ToText(String) {OWN[i].format(**FMT)}))''')
G = {
    'Ease': '(fn Ease (V) (bind c (- 1.0 (Math|Float|Max(Float) 0.0 (Math|Float|Min(Float) V 1.0)))) (return (- 1.0 (* (* c c) c))))',
    'ReadKind': f'''
(fn ReadKind ()
  (bind pc {PCCAST}
    (:then (Variables|Shop|SetKind (GW|Get|BP_GW_PlayerController|ShopKind :self pc)))
    (:CastFailed)))
''',
    'SetupShop': '''
(fn SetupShop ()
  (Variables|Shop|SetT 0.0)
  (Variables|Shop|SetLastMoney -1)
  (Widget|SetRenderOpacity :self (Variables|WBP_Shop|GetCardSize) :InOpacity 0.0)
  (Audio|PlaySound2D :Sound "/Game/GW/Audio/S_UI_Card.S_UI_Card" :VolumeMultiplier 0.8))
''',
    'ShopTick': f'''
(fn ShopTick (Dt)
  (Variables|Shop|SetT (+ (Variables|Shop|GetT) Dt))
  (bind t (Variables|Shop|GetT))
  (CallFunction|ReadKind)
  (Widget|SetText(Text) :self {OV('Title')} :InText (Utilities|Text|ToText(String) (select (== (Variables|Shop|GetKind) 1) "{VENDORS[1][0]}" (select (== (Variables|Shop|GetKind) 2) "{VENDORS[2][0]}" "{VENDORS[0][0]}"))))
  (Widget|SetText(Text) :self {OV('Sub')} :InText (Utilities|Text|ToText(String) (select (== (Variables|Shop|GetKind) 1) "{VENDORS[1][1]}" (select (== (Variables|Shop|GetKind) 2) "{VENDORS[2][1]}" "{VENDORS[0][1]}"))))
  (if (== (Variables|Shop|GetKind) 1)
    (Widget|SetVisibility :self {OV('Buy9')} :InVisibility "Visible")
    (else
      (Widget|SetVisibility :self {OV('Buy9')} :InVisibility "Collapsed")))
  ; the card opens: a quick scale + fade
  (bind e (CallFunction|Ease :V (/ t 0.2)))
  (Widget|SetRenderOpacity :self {OV('CardSize')} :InOpacity e)
  (Widget|Transform|SetRenderScale :self {OV('CardSize')} :Scale (Math|Vector2D|MakeVector2D (+ 0.94 (* 0.06 e)) (+ 0.94 (* 0.06 e))))
  (Widget|SetRenderOpacity :self {OV('Backdrop')} :InOpacity e)
  (Variables|Shop|SetPulse (Math|Float|Max(Float) 0.0 (- (Variables|Shop|GetPulse) (* Dt 3.0))))
  (Widget|Transform|SetRenderScale :self {OV('TxtMoney')} :Scale (Math|Vector2D|MakeVector2D (+ 1.0 (* 0.18 (Variables|Shop|GetPulse))) (+ 1.0 (* 0.18 (Variables|Shop|GetPulse)))))
  (bind ps {PSCAST}
    (:then
      (Variables|Default|SetMn {P('Money')})
      (if (and (>= (Variables|Shop|GetLastMoney) 0) (!= (Variables|Default|GetMn) (Variables|Shop|GetLastMoney)))
        (Variables|Shop|SetPulse 1.0))
      (Variables|Shop|SetLastMoney (Variables|Default|GetMn))
      (Widget|SetText(Text) :self {OV('TxtMoney')} :InText (Utilities|Text|ToText(String) (cat (Variables|Default|GetMn) " $")))
{chr(10).join(rows_code)}
      (bind fresh (< (- (GameState|GetServerWorldTimeSeconds :self (Game|GetGameState)) {P('ShopNoteAt')}) 4.0))
      (Widget|SetText(Text) :self {OV('TxtNote')} :InText (Utilities|Text|ToText(String) (select fresh {P('ShopNote')} ""))))
    (:CastFailed)))
''',
    'OnClose': f'''
(fn OnClose ()
  (bind pc {PCCAST}
    (:then (GW|Call|BP_GW_PlayerController|CloseShop :self pc))
    (:CastFailed)))
''',
    'EventGraph': '''
(event UserInterface|EventConstruct
  (CallFunction|SetupShop))

(event UserInterface|EventTick (MyGeometry InDeltaTime)
  (CallFunction|ShopTick :Dt InDeltaTime))
''',
}
for i, *_ in ITEMS:
    G[f'OnBuy{i}'] = f'''
(fn OnBuy{i} ()
  (Audio|PlaySound2D :Sound "/Game/GW/Audio/S_UI_Click.S_UI_Click" :VolumeMultiplier 0.6)
  (bind pc {PCCAST}
    (:then (GW|Call|BP_GW_PlayerController|ShopBuy :self pc :Id {i}))
    (:CastFailed)))
'''
for n, c in G.items():
    write(W, n, c, compile_after=False)
compile_bp(W, quiet=True)
for i, *_ in ITEMS:
    bind(W, f'Buy{i}', 'OnClicked', f'OnBuy{i}')
bind(W, 'Close', 'OnClicked', 'OnClose')
compile_bp(W)
print('WBP_Shop', node_problems(W))
compile_widget(W)
