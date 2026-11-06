"""WBP_HUD reskin (Art Deco) + music state machine + role-reveal card + newspaper end card + pause toggle.

Data flow kept: BP_GW_PlayerController.RefreshHUD -> Refresh(PC, ShowScores) -> RefreshWith(GS, PS, PC, ShowScores) sets the same
named widgets (TxtRole, TxtTimer, TxtHiders, TxtHealth, Blindfold/BlindText, Crosshair, TxtCenter, TxtNotice, ScorePanel/TxtScores),
Nothing is drawn at the top of the screen and there are no subtitles (user request, 2026-11-04). The user, 2026-11-05: "a way better UI, see my money and my life": two Art Deco panels on the bottom corners:
StatusPanel bottom-left (role, counts, large life number and bar), ClockPanel bottom-right (phase, timer, large money), the item slots between them (WBP_Inventory, s40_inventory.py). Any loss of life: red vignette,
red "-X" mid-screen, a thud, the panel shakes (HurtFlash, TxtHurtPop, StyleWith). Events are red text mid-screen (EventAnnounce), money gains a green "+X $" (MoneyPop).
DebugDump keeps its format. RefreshWith includes the coordinator's fixes (ghost banner, lobby countdown, end-of-round text).
Visual-only animation + music live in the widget's own Tick (StyleTick / MusicTick).
UE_ARGS: 'tree' | 'graph' | 'all' (default) [single function name]."""
import sys
sys.path.insert(0, r'J:\Projets\Unreal_Projects\Guess Who\Tools\ui')
import importlib, uilib
importlib.reload(uilib)
from uilib import *

which = UE_ARGS[0] if UE_ARGS else 'all'
W = unreal.load_asset('/Game/GW/UI/WBP_HUD')
INK_C = (0.03, 0.022, 0.016, 1)
BURG_C = (0.33, 0.04, 0.05, 1)
ISVALID = 'GW|Call|/Script/Engine.KismetSystemLibrary|IsValid'
AC = '/Script/Engine.AudioComponent'
SET = '/Game/GW/UI/BP_GW_Settings.BP_GW_Settings_C'


def build_tree():
    clear_tree(W)
    add(W, unreal.CanvasPanel, 'Root')
    # ---- crosshair
    c = add(W, unreal.Image, 'Crosshair', 'Root', var=True); image(c, 'T_UI_Crosshair', (84, 84))
    canvas(c, ((0.5, 0.5), (0.5, 0.5)), (0.5, 0.5), (0, 0), (84, 84), z=4); pivot(c); vis(c, V.HIDDEN)
    # ---- bottom-left: role, counts, life. Bottom-right: phase, timer, money. Same frame, same two rows, the slots between them
    PW = 340
    sp = add(W, unreal.Border, 'StatusPanel', 'Root', var=True)
    border_brush(sp, 'T_UI_PanelSmall', 0.18, tint=(1, 1, 1, 0.94), pad=(22, 14, 22, 12), size=(200, 200))
    canvas(sp, ((0, 1), (0, 1)), (0, 1), (26, -14), auto=True, z=6); pivot(sp)
    ssz = add(W, unreal.SizeBox, 'StatusSize', 'StatusPanel'); size_box(ssz, w=PW)
    sv = add(W, unreal.VerticalBox, 'StatusV', 'StatusSize')
    rh = add(W, unreal.HorizontalBox, 'RoleH', 'StatusV'); box_slot(rh, (0, 0, 0, 4), H.H_ALIGN_FILL)
    ri = add(W, unreal.Image, 'RoleIcon', 'RoleH', var=True); image(ri, 'T_UI_IcoMask', (26, 26)); box_slot(ri, (0, 0, 8, 0), H.H_ALIGN_LEFT, VA.V_ALIGN_CENTER)
    r = add(W, unreal.TextBlock, 'TxtRole', 'RoleH', var=True); text(r, "SALLE D'ATTENTE", 'Display', 'Regular', 20, GOLD_HI, spacing=200)
    box_slot(r, (0, 0, 0, 0), H.H_ALIGN_LEFT, VA.V_ALIGN_CENTER, fill=1)
    cr = add(W, unreal.HorizontalBox, 'CountRow', 'RoleH', var=True); box_slot(cr, (6, 0, 0, 0), H.H_ALIGN_RIGHT, VA.V_ALIGN_CENTER)
    h = add(W, unreal.TextBlock, 'TxtHiders', 'CountRow', var=True); text(h, '', 'Sans', 'SemiBold', 14, IVORY, just='right')
    box_slot(h, (0, 0, 0, 0), H.H_ALIGN_RIGHT, VA.V_ALIGN_CENTER)
    dv1 = add(W, unreal.Image, 'StatusRule', 'StatusV'); image(dv1, 'T_UI_SliderBar', (PW, 2), tint=(0.66, 0.40, 0.10, 0.8)); box_slot(dv1, (0, 0, 0, 2), H.H_ALIGN_FILL)
    hr = add(W, unreal.HorizontalBox, 'HealthRow', 'StatusV', var=True); box_slot(hr, (0, 0, 0, 0), H.H_ALIGN_FILL)
    hi = add(W, unreal.Image, 'HealthIcon', 'HealthRow', var=True); image(hi, 'T_UI_IcoHeart', (52, 52)); box_slot(hi, (0, 0, 10, 0), H.H_ALIGN_LEFT, VA.V_ALIGN_CENTER); pivot(hi)
    hp = add(W, unreal.TextBlock, 'TxtHealth', 'HealthRow', var=True); text(hp, '100', 'Display', 'Regular', 68, IVORY, just='left', outline=1)
    box_slot(hp, (0, 0, 14, 0), H.H_ALIGN_LEFT, VA.V_ALIGN_CENTER)
    hbv = add(W, unreal.VerticalBox, 'HealthBarV', 'HealthRow'); box_slot(hbv, (0, 0, 0, 0), H.H_ALIGN_FILL, VA.V_ALIGN_CENTER, fill=1)
    hl = add(W, unreal.TextBlock, 'HealthLabel', 'HealthBarV'); text(hl, 'VIE', 'Display', 'Regular', 16, GOLD, spacing=300); box_slot(hl, (0, 0, 0, 3), H.H_ALIGN_LEFT)
    hbo = add(W, unreal.Overlay, 'HealthBar', 'HealthBarV'); box_slot(hbo, (0, 0, 0, 0), H.H_ALIGN_FILL)
    hb1 = add(W, unreal.Image, 'HealthBarRim', 'HealthBar'); hb1.widget.set_editor_property('brush', brush(None, (120, 18), 'image', tint=GOLD)); overlay_slot(hb1)
    hb2 = add(W, unreal.Image, 'HealthBarBack', 'HealthBar'); hb2.widget.set_editor_property('brush', brush(None, (120, 14), 'image', tint=(0.015, 0.012, 0.01, 1))); overlay_slot(hb2, pad=(2, 2, 2, 2))
    hb3 = add(W, unreal.Image, 'HealthFill', 'HealthBar', var=True); hb3.widget.set_editor_property('brush', brush(None, (120, 14), 'image', tint=(1, 1, 1, 1))); overlay_slot(hb3, pad=(2, 2, 2, 2)); pivot(hb3, 0.0, 0.5)
    cp = add(W, unreal.Border, 'ClockPanel', 'Root', var=True)
    border_brush(cp, 'T_UI_PanelSmall', 0.18, tint=(1, 1, 1, 0.94), pad=(22, 14, 22, 12), size=(200, 200))
    canvas(cp, ((1, 1), (1, 1)), (1, 1), (-26, -14), auto=True, z=6); pivot(cp)
    csz = add(W, unreal.SizeBox, 'ClockSize', 'ClockPanel'); size_box(csz, w=PW)
    cv = add(W, unreal.VerticalBox, 'ClockV', 'ClockSize')
    sh = add(W, unreal.HorizontalBox, 'ClockRow', 'ClockV'); box_slot(sh, (0, 0, 0, 4), H.H_ALIGN_FILL)
    do = add(W, unreal.Overlay, 'DialBox', 'ClockRow'); box_slot(do, (0, 0, 8, 0), H.H_ALIGN_LEFT, VA.V_ALIGN_CENTER)
    image(add(W, unreal.Image, 'Dial', 'DialBox'), 'T_UI_Dial', (30, 30))
    dh = add(W, unreal.Image, 'DialHand', 'DialBox', var=True); image(dh, 'T_UI_DialHand', (30, 30)); pivot(dh)
    ph = add(W, unreal.TextBlock, 'TxtPhase', 'ClockRow', var=True); text(ph, 'SALON', 'Display', 'Regular', 20, GOLD_HI, spacing=200)
    box_slot(ph, (0, 0, 0, 0), H.H_ALIGN_LEFT, VA.V_ALIGN_CENTER, fill=1)
    t = add(W, unreal.TextBlock, 'TxtTimer', 'ClockRow', var=True); text(t, '', 'Display', 'Regular', 26, IVORY, spacing=100, just='right'); pivot(t, 1.0, 0.5)
    box_slot(t, (6, 0, 0, 0), H.H_ALIGN_RIGHT, VA.V_ALIGN_CENTER)
    dv2 = add(W, unreal.Image, 'ClockRule', 'ClockV'); image(dv2, 'T_UI_SliderBar', (PW, 2), tint=(0.66, 0.40, 0.10, 0.8)); box_slot(dv2, (0, 0, 0, 2), H.H_ALIGN_FILL)
    mr = add(W, unreal.HorizontalBox, 'MoneyRow', 'ClockV', var=True); box_slot(mr, (0, 0, 0, 0), H.H_ALIGN_FILL)
    ml = add(W, unreal.TextBlock, 'MoneyLabel', 'MoneyRow'); text(ml, 'ARGENT', 'Display', 'Regular', 16, GOLD, spacing=300); box_slot(ml, (0, 0, 0, 0), H.H_ALIGN_LEFT, VA.V_ALIGN_CENTER, fill=1)
    tm = add(W, unreal.TextBlock, 'TxtMoney', 'MoneyRow', var=True); text(tm, '0', 'Display', 'Regular', 68, IVORY, just='right', outline=1); box_slot(tm, (0, 0, 10, 0), H.H_ALIGN_RIGHT, VA.V_ALIGN_CENTER); pivot(tm, 1.0, 0.5)
    md = add(W, unreal.TextBlock, 'MoneySign', 'MoneyRow'); text(md, '$', 'Display', 'Regular', 52, GOLD_HI, just='right', outline=1); box_slot(md, (0, 0, 0, 0), H.H_ALIGN_RIGHT, VA.V_ALIGN_CENTER)
    # ---- hit: red vignette over the whole screen, red "-X" mid-screen (StyleWith, from the character's Health)
    hf = add(W, unreal.Image, 'HurtFlash', 'Root', var=True); image(hf, 'T_UI_Vignette', (512, 288), tint=(0.85, 0.02, 0.01, 1)); canvas(hf, FILL, z=3); vis(hf, V.HIDDEN)
    hpop = add(W, unreal.TextBlock, 'TxtHurtPop', 'Root', var=True); text(hpop, '', 'Display', 'Regular', 72, (0.92, 0.05, 0.03, 1), spacing=80, just='center', outline=3)
    hpop.widget.set_editor_property('shadow_offset', unreal.Vector2D(3.0, 3.0))
    canvas(hpop, ((0.5, 0.68), (0.5, 0.68)), (0.5, 0.5), auto=True, z=11); pivot(hpop); vis(hpop, V.HIDDEN)
    # ---- bomb defusing (s34_shop.py: a detective holds E for 2 s): 16 beads around the crosshair fill up, % below
    import math as _m
    dr = add(W, unreal.CanvasPanel, 'DefuseRing', 'Root', var=True)
    canvas(dr, ((0.5, 0.5), (0.5, 0.5)), (0.5, 0.5), (0, 0), (260, 300), z=9); pivot(dr); vis(dr, V.HIDDEN)
    for k in range(16):
        a_ = 2 * _m.pi * k / 16 - _m.pi / 2
        dd = add(W, unreal.Image, f'DefDot{k}', 'DefuseRing', var=True)
        dd.widget.set_editor_property('brush', brush(None, (14, 14), 'image', tint=(1, 1, 1, 1)))
        canvas(dd, ((0.5, 0.5), (0.5, 0.5)), (0.5, 0.5), (round(_m.cos(a_) * 96, 1), round(_m.sin(a_) * 96 - 20, 1)), (14, 14), z=1)
    dtx = add(W, unreal.TextBlock, 'TxtDefuse', 'DefuseRing', var=True)
    text(dtx, '', 'Display', 'Regular', 24, GOLD_HI, just='center', outline=1)
    canvas(dtx, ((0.5, 0.5), (0.5, 0.5)), (0.5, 0.5), (0, 118), auto=True, z=2)
    # ---- events: red, mid-screen, a few seconds (animated in StyleWith)
    ea = add(W, unreal.VerticalBox, 'EventAnnounce', 'Root', var=True); canvas(ea, ((0.5, 0.42), (0.5, 0.42)), (0.5, 0.5), auto=True, z=10); pivot(ea); vis(ea, V.HIDDEN)
    RED = (0.86, 0.035, 0.025, 1)
    r1a = add(W, unreal.Image, 'AnnRuleTop', 'EventAnnounce', var=True); r1a.widget.set_editor_property('brush', brush(None, (900, 4), 'image', tint=RED)); box_slot(r1a, (0, 0, 0, 8), H.H_ALIGN_CENTER); pivot(r1a)
    ev = add(W, unreal.TextBlock, 'TxtAnnounce', 'EventAnnounce', var=True); text(ev, '', 'Display', 'Regular', 84, RED, spacing=240, just='center', wrap=1500, outline=3)
    ev.widget.set_editor_property('shadow_offset', unreal.Vector2D(4.0, 4.0))
    box_slot(ev, (0, 0, 0, 0), H.H_ALIGN_CENTER)
    r2a = add(W, unreal.Image, 'AnnRuleBot', 'EventAnnounce', var=True); r2a.widget.set_editor_property('brush', brush(None, (900, 4), 'image', tint=RED)); box_slot(r2a, (0, 10, 0, 0), H.H_ALIGN_CENTER); pivot(r2a)
    # ---- money gained: green "+X $" that pops, rises and fades (StyleWith, driven by BP_GW_PlayerState.Money)
    mp = add(W, unreal.Overlay, 'MoneyPop', 'Root', var=True); canvas(mp, ((0.5, 0.63), (0.5, 0.63)), (0.5, 0.5), auto=True, z=11); pivot(mp); vis(mp, V.HIDDEN)
    mg = add(W, unreal.TextBlock, 'TxtMoneyGlow', 'MoneyPop', var=True); text(mg, '', 'Display', 'Regular', 78, (0.2, 1.0, 0.3, 0.5), spacing=80, just='center', shadow=False)
    overlay_slot(mg, H.H_ALIGN_CENTER, VA.V_ALIGN_CENTER); pivot(mg)
    mt = add(W, unreal.TextBlock, 'TxtMoneyPop', 'MoneyPop', var=True); text(mt, '', 'Display', 'Regular', 78, (0.16, 0.92, 0.2, 1), spacing=80, just='center', outline=3)
    mt.widget.set_editor_property('shadow_offset', unreal.Vector2D(3.0, 3.0))
    overlay_slot(mt, H.H_ALIGN_CENTER, VA.V_ALIGN_CENTER)
    # ---- short personal notices (shop refusals, "Échap encore pour quitter"...): low on the screen, above the key hint
    tn = add(W, unreal.TextBlock, 'TxtNotice', 'Root', var=True); text(tn, '', 'Serif', 'Bold', 24, GOLD_HI, just='center', wrap=900, outline=1)
    canvas(tn, ((0.5, 0.81), (0.5, 0.81)), (0.5, 0.5), auto=True, z=7)
    # ---- scoreboard: engraved invitation card
    sb = add(W, unreal.Border, 'ScorePanel', 'Root', var=True)
    border_brush(sb, 'T_UI_Card', (0.1, 0.07, 0.1, 0.07), pad=(54, 40, 54, 40), size=(360, 540))
    canvas(sb, ((0.5, 0.56), (0.5, 0.56)), (0.5, 0.5), auto=True, z=8); pivot(sb); vis(sb, V.HIDDEN)
    sv2 = add(W, unreal.VerticalBox, 'ScoreV', 'ScorePanel')
    stt = add(W, unreal.TextBlock, 'ScoreTitle', 'ScoreV'); text(stt, 'LISTE DES INVITÉS', 'Display', 'Regular', 38, BURG_C, spacing=420, just='center', shadow=False)
    box_slot(stt, (0, 0, 0, 0), H.H_ALIGN_CENTER)
    sst = add(W, unreal.TextBlock, 'ScoreSub', 'ScoreV', var=True)
    text(sst, 'Bal masqué du manoir Ashcombe — 1932', 'Serif', 'Italic', 19, INK_C, just='center', shadow=False)
    box_slot(sst, (0, 0, 0, 4), H.H_ALIGN_CENTER)
    sd = add(W, unreal.Image, 'ScoreDiv', 'ScoreV'); image(sd, 'T_UI_Divider', (300, 63), tint=(0.55, 0.42, 0.25, 1)); box_slot(sd, (0, 0, 0, 8), H.H_ALIGN_CENTER)
    cols = add(W, unreal.HorizontalBox, 'ScoreCols', 'ScoreV'); box_slot(cols, (0, 0, 0, 0), H.H_ALIGN_CENTER)
    for name, hdr, w, just in (('ColName', 'CONVIVE', 250, 'left'), ('ColRole', 'ÉTAT', 140, 'left'), ('ColScore', 'POINTS', 90, 'center'),
                               ('ColKills', 'RIVAUX', 120, 'center'), ('ColErr', '', 100, 'center')):
        cs = add(W, unreal.SizeBox, name + 'Size', 'ScoreCols'); size_box(cs, w=w); box_slot(cs, (4, 0, 4, 0), H.H_ALIGN_FILL, VA.V_ALIGN_TOP)
        cv = add(W, unreal.VerticalBox, name + 'V', name + 'Size')
        hh = add(W, unreal.TextBlock, name + 'Hdr', name + 'V'); text(hh, hdr, 'Display', 'Regular', 18, BURG_C, spacing=260, just=just, shadow=False)
        box_slot(hh, (0, 0, 0, 6), H.H_ALIGN_FILL)
        ct = add(W, unreal.TextBlock, name, name + 'V', var=True); text(ct, '', 'Serif', 'Regular', 21, INK_C, just=just, shadow=False)
        ct.widget.set_editor_property('line_height_percentage', 1.15)
        box_slot(ct, (0, 0, 0, 0), H.H_ALIGN_FILL)
    ts = add(W, unreal.TextBlock, 'TxtScores', 'ScoreV', var=True); text(ts, '', 'Sans', 'Regular', 10, INK_C, shadow=False); vis(ts, V.COLLAPSED)
    # ---- newspaper end card
    es = add(W, unreal.SizeBox, 'EndCard', 'Root', var=True); size_box(es, w=560)
    canvas(es, ((0.5, 0.57), (0.5, 0.57)), (0.5, 0.5), auto=True, z=9); pivot(es); vis(es, V.HIDDEN)
    eb2 = add(W, unreal.Border, 'EndPaper', 'EndCard'); border_brush(eb2, 'T_UI_Newsprint', 0.0, pad=(34, 22, 34, 24), size=(560, 800))
    ev2 = add(W, unreal.VerticalBox, 'EndV', 'EndPaper')
    mh = add(W, unreal.TextBlock, 'Masthead', 'EndV'); text(mh, "LE COURRIER D'ASHCOMBE", 'Display', 'Regular', 44, INK_C, spacing=120, just='center', shadow=False)
    box_slot(mh, (0, 0, 0, 0), H.H_ALIGN_CENTER)
    r1 = add(W, unreal.Image, 'Rule1', 'EndV'); image(r1, 'T_UI_SliderBar', (480, 3), tint=(0.03, 0.02, 0.015, 1)); box_slot(r1, (0, 2, 0, 2), H.H_ALIGN_FILL)
    dl = add(W, unreal.TextBlock, 'Dateline', 'EndV', var=True)
    text(dl, 'ÉDITION SPÉCIALE  ·  NUIT DU BAL MASQUÉ  ·  1932', 'Sans', 'SemiBold', 12, INK_C, spacing=60, just='center', shadow=False)
    box_slot(dl, (0, 0, 0, 0), H.H_ALIGN_CENTER)
    r2 = add(W, unreal.Image, 'Rule2', 'EndV'); image(r2, 'T_UI_SliderBar', (480, 3), tint=(0.03, 0.02, 0.015, 1)); box_slot(r2, (0, 2, 0, 10), H.H_ALIGN_FILL)
    c2 = add(W, unreal.TextBlock, 'TxtCenter', 'EndV', var=True)
    text(c2, '', 'Display', 'Regular', 48, INK_C, spacing=60, just='center', wrap=480, shadow=False)
    c2.widget.set_editor_property('line_height_percentage', 0.92)
    box_slot(c2, (0, 0, 0, 10), H.H_ALIGN_CENTER)
    ep = add(W, unreal.Image, 'EndPhoto', 'EndV', var=True); image(ep, 'T_UI_PhotoDetectives', (470, 321)); box_slot(ep, (0, 0, 0, 4), H.H_ALIGN_CENTER)
    cap = add(W, unreal.TextBlock, 'EndCaption', 'EndV', var=True)
    text(cap, 'Notre envoyé spécial au manoir Ashcombe.', 'Serif', 'Italic', 15, INK_C, just='center', shadow=False); box_slot(cap, (0, 0, 0, 8), H.H_ALIGN_CENTER)
    bd = add(W, unreal.TextBlock, 'EndBody', 'EndV', var=True)
    text(bd, '', 'Serif', 'Regular', 19, INK_C, just='center', wrap=480, shadow=False); box_slot(bd, (0, 0, 0, 8), H.H_ALIGN_CENTER)
    nx = add(W, unreal.TextBlock, 'EndNext', 'EndV', var=True)
    text(nx, '', 'Display', 'Regular', 22, BURG_C, spacing=300, just='center', shadow=False); box_slot(nx, (0, 0, 0, 0), H.H_ALIGN_CENTER)
    # ---- role reveal card
    rc = add(W, unreal.VerticalBox, 'RoleCard', 'Root', var=True); canvas(rc, ((0.5, 0.56), (0.5, 0.56)), (0.5, 0.5), auto=True, z=12); pivot(rc)
    vis(rc, V.HIDDEN)
    rco = add(W, unreal.Overlay, 'RoleCardO', 'RoleCard'); box_slot(rco, (0, 0, 0, 10), H.H_ALIGN_CENTER)
    rci = add(W, unreal.Image, 'RoleCardImg', 'RoleCardO', var=True); image(rci, 'T_UI_CardInvite', (340, 510)); overlay_slot(rci)
    rct = add(W, unreal.TextBlock, 'RoleCardTitle', 'RoleCardO', var=True)
    text(rct, 'INVITÉ', 'Display', 'Regular', 36, GOLD_HI, spacing=260, just='center'); overlay_slot(rct, H.H_ALIGN_CENTER, VA.V_ALIGN_BOTTOM, (0, 0, 0, 19))
    rsp = add(W, unreal.Overlay, 'RoleSubPlate', 'RoleCard'); box_slot(rsp, (0, 0, 0, 0), H.H_ALIGN_CENTER)
    rsb = add(W, unreal.Image, 'RoleSubBand', 'RoleSubPlate'); image(rsb, 'T_UI_FadeBar', (640, 64), tint=(0.0, 0.0, 0.0, 0.8)); overlay_slot(rsb)
    rcs = add(W, unreal.TextBlock, 'RoleCardSub', 'RoleSubPlate', var=True)
    text(rcs, '', 'Serif', 'Italic', 25, (0.97, 0.93, 0.84, 1), just='center', wrap=640)
    rcs.widget.set_editor_property('shadow_offset', unreal.Vector2D(2.0, 2.0))
    overlay_slot(rcs, H.H_ALIGN_CENTER, VA.V_ALIGN_CENTER, (70, 7, 70, 10))
    # ---- blindfold
    b = add(W, unreal.Border, 'Blindfold', 'Root', var=True); canvas(b, FILL, z=5)
    b.widget.set_editor_property('brush_color', unreal.LinearColor(0.004, 0.006, 0.005, 0.985))
    b.widget.set_editor_property('horizontal_alignment', H.H_ALIGN_FILL)
    b.widget.set_editor_property('vertical_alignment', VA.V_ALIGN_FILL)
    vis(b, V.HIDDEN)
    bo = add(W, unreal.Overlay, 'BlindO', 'Blindfold')
    bv = add(W, unreal.Image, 'BlindVignette', 'BlindO'); image(bv, 'T_UI_Vignette', (512, 288), tint=(0, 0, 0, 1)); overlay_slot(bv)
    bvb = add(W, unreal.VerticalBox, 'BlindV', 'BlindO', var=True); overlay_slot(bvb, H.H_ALIGN_CENTER, VA.V_ALIGN_CENTER)
    bi = add(W, unreal.Image, 'BlindIcon', 'BlindV', var=True); image(bi, 'T_UI_IcoMaskDeco', (150, 150), tint=(0.55, 0.45, 0.35, 0.65))
    box_slot(bi, (0, 0, 0, 10), H.H_ALIGN_CENTER); pivot(bi)
    bt0 = add(W, unreal.TextBlock, 'BlindTitle', 'BlindV'); text(bt0, 'LES YEUX BANDÉS', 'Display', 'Regular', 46, GOLD, spacing=620, just='center')
    box_slot(bt0, (0, 0, 0, 6), H.H_ALIGN_CENTER)
    bs = add(W, unreal.TextBlock, 'BlindSub', 'BlindV'); text(bs, 'Les invités se dispersent dans le manoir… La chasse commence dans', 'Serif', 'Italic', 23, IVORY, just='center')
    box_slot(bs, (0, 0, 0, 0), H.H_ALIGN_CENTER)
    bt = add(W, unreal.TextBlock, 'BlindText', 'BlindV', var=True); text(bt, '', 'Display', 'Regular', 160, GOLD_HI, spacing=0, just='center')
    box_slot(bt, (0, 0, 0, 0), H.H_ALIGN_CENTER); pivot(bt)
    # ---- hint
    hp2 = add(W, unreal.Overlay, 'HintPlate', 'Root', var=True); canvas(hp2, ((0.5, 1), (0.5, 1)), (0.5, 1), (0, -106), auto=True, z=6)
    hb = add(W, unreal.Image, 'HintBand', 'HintPlate'); image(hb, 'T_UI_FadeBar', (1040, 36), tint=(0.0, 0.0, 0.0, 0.75)); overlay_slot(hb)
    hn = add(W, unreal.TextBlock, 'TxtHint', 'HintPlate', var=True)
    text(hn, 'E : interagir   ·   1-4 : objets   ·   Q : jeter   ·   C : vue   ·   Espace : sauter   ·   Tab : scores   ·   Échap : menu', 'Sans', 'SemiBold', 15, (0.92, 0.88, 0.8, 1), just='center')
    hn.widget.set_editor_property('shadow_offset', unreal.Vector2D(1.5, 1.5))
    overlay_slot(hn, H.H_ALIGN_CENTER, VA.V_ALIGN_CENTER, (110, 6, 110, 8))
    # ---- interaction prompt ("E  Jouer du piano"): shown while the PC refreshes Prompt / PromptAt (piano, barman...)
    pp = add(W, unreal.HorizontalBox, 'PromptPlate', 'Root', var=True)
    canvas(pp, ((0.5, 0.74), (0.5, 0.74)), (0.5, 0.5), auto=True, z=8)
    pk = add(W, unreal.Overlay, 'PromptKeyBox', 'PromptPlate'); box_slot(pk, (0, 0, 16, 0), H.H_ALIGN_LEFT, VA.V_ALIGN_CENTER)
    kb = add(W, unreal.Image, 'PromptKeyRim', 'PromptKeyBox')
    kb.widget.set_editor_property('brush', brush(None, (56, 56), 'image', tint=GOLD_HI)); overlay_slot(kb)
    ki = add(W, unreal.Image, 'PromptKeyFace', 'PromptKeyBox')
    ki.widget.set_editor_property('brush', brush(None, (50, 50), 'image', tint=(0.02, 0.015, 0.01, 0.92)))
    overlay_slot(ki, H.H_ALIGN_CENTER, VA.V_ALIGN_CENTER)
    kt = add(W, unreal.TextBlock, 'TxtPromptKey', 'PromptKeyBox', var=True)
    text(kt, 'E', 'Display', 'Regular', 30, GOLD_HI, just='center'); overlay_slot(kt, H.H_ALIGN_CENTER, VA.V_ALIGN_CENTER)
    pt = add(W, unreal.TextBlock, 'TxtPrompt', 'PromptPlate', var=True)
    text(pt, '', 'Serif', 'Bold', 26, IVORY, outline=1); box_slot(pt, (0, 0, 0, 0), H.H_ALIGN_LEFT, VA.V_ALIGN_CENTER)
    compile_widget(W)
    print('HUD tree:', len(infos(W)))


def gs(v):
    return f'(GW|Get|BP_GW_GameState|{v} :self GS)'


def txt(widget, expr):
    return f'(Widget|SetText(Text) :self (Variables|WBP_HUD|Get{widget}) :InText (Utilities|Text|ToText(String) {expr}))'


HV = lambda n: f'(Variables|WBP_HUD|Get{n})'
# shop (Tools/gameplay/s34_shop.py): player state money, read in RefreshWith and StyleWith (PS parameter)
SPS = lambda v: f'(GW|Get|BP_GW_PlayerState|{v} :self PS)'
SHOP_SND = {k: f'"/Game/GW/Audio/Gen/shop_buy/{k}.{k}"' for k in ('SFX_Shop_Buy', 'SFX_Shop_Coins')}


def build_graph():
    for n in ['RoleT', 'TimerT', 'CenterT', 'NoticeT', 'PhaseT', 'NextT']:
        local_var(W, 'RefreshWith', n, 'string')
    local_var(W, 'BuildScores', 'Acc', 'string')
    for n in ['CN', 'CR', 'CS', 'CK', 'CE']:
        local_var(W, 'BuildScoreCols', n, 'string') if get_graph(W, 'BuildScoreCols') else None
    UIV = [('T', 'float'), ('MusState', 'int'), ('PhaseSeen', 'int'), ('PhaseDur', 'float'), ('CardT', 'float'), ('EndT', 'float'),
           ('LastEvStart', 'float'), ('AnnT', 'float'), ('GainSum', 'int'), ('HintBase', 'string'), ('VoAt', 'float'), ('LateMusAt', 'float'), ('WasTense', 'bool'), ('FovAt', 'float'),
           ('RoleSeen', 'int'), ('LastHealth', 'float'), ('HurtT', 'float'), ('ShotStep', 'int'), ('ShotAt', 'float'), ('PrevMus', 'int'), ('CardDone', 'bool'),
           ('LastMoney', 'int'), ('LastBuys', 'int'), ('GainT', 'float'), ('HurtSum', 'float'), ('SpendT', 'float')]                       # shop (s34_shop.py)
    for n, t in UIV:
        ensure_var(W, n, t, category='UI')
    ensure_var(W, 'MusA', obj_class=unreal.AudioComponent, category='UI')
    ensure_var(W, 'MusB', obj_class=unreal.AudioComponent, category='UI')
    ensure_var(W, 'VoSnd', obj_class=unreal.SoundBase, category='UI')
    ensure_var(W, 'PauseW', obj_class=unreal.UserWidget, category='UI')
    ensure_var(W, 'LocalNotice', 'string', category='GW')
    ensure_var(W, 'LocalNoticeTime', 'float', category='GW')
    ensure_var(W, 'Prompt', 'string', category='GW')            # set every 0.1 s by the PC while an action is near
    ensure_var(W, 'PromptKey', 'string', category='GW')
    ensure_var(W, 'PromptAt', 'float', category='GW')
    gsc = unreal.load_asset('/Game/GW/Blueprints/BP_GW_GameState').generated_class()
    psc = unreal.load_asset('/Game/GW/Blueprints/BP_GW_PlayerState').generated_class()
    for fn, ins, outs in [
        ('BuildScoreCols', [], []), ('SetupHUD', [], []), ('StyleTick', [('Dt', 'float')], []), ('StyleWith', [('GS', gsc), ('PS', psc), ('Dt', 'float')], []),
        ('MusicTick', [('GS', gsc), ('PS', psc)], []), ('SetMusicState', [('NewState', 'int'), ('Winner', 'int')], []),
        ('PlayMus', [('Snd', unreal.SoundBase), ('Vol', 'float'), ('Fade', 'float')], [('Comp', unreal.AudioComponent)]),
        ('FadeComp', [('Comp', unreal.AudioComponent), ('Dur', 'float')], []), ('ApplyFov', [], []), ('MusicTimer', [], []), ('TogglePause', [], []), ('ShotTick', [('GS', gsc), ('PS', psc)], []), ('Clamp01', [('V', 'float')], [('R', 'float')]),
        ('Ease', [('V', 'float')], [('R', 'float')]), ('DefuseHudTick', [], []), ('QueueVo', [('Snd', unreal.SoundBase), ('Delay', 'float')], []),
    ]:
        ensure_fn(W, fn, inputs=ins, outputs=outs, pure=fn in ('Clamp01', 'Ease'))
    for n in ['CN', 'CR', 'CS', 'CK', 'CE']:
        local_var(W, 'BuildScoreCols', n, 'string')
    # original signatures (Tools/gameplay/s10_signatures.py); the PlayerController calls DebugDump/Refresh by these names
    ensure_fn(W, 'FormatTime', inputs=[('Seconds', 'float')], outputs=[('Out', 'string')], pure=True)
    ensure_fn(W, 'BuildScores', outputs=[('Out', 'string')])
    ensure_fn(W, 'HealthOf', inputs=[('PC', unreal.PlayerController)], outputs=[('HP', 'float')], pure=True)
    ensure_fn(W, 'HeldNow', outputs=[('Id', 'int')])
    ensure_fn(W, 'DebugDump', outputs=[('Out', 'string')])
    compile_bp(W, quiet=True)
    has_vo = EAL.does_asset_exist('/Game/GW/Audio/VO_Hunt')
    G = {}
    G['Clamp01'] = '(fn Clamp01 (V) (return (Math|Float|Max(Float) 0.0 (Math|Float|Min(Float) V 1.0))))'
    G['Ease'] = '''
(fn Ease (V)
  (bind c (Math|Float|Max(Float) 0.0 (Math|Float|Min(Float) V 1.0)))
  (return (* (* c c) (- 3.0 (* 2.0 c)))))
'''
    G['ShowW'] = '''
(fn ShowW (W Show)
  (if Show
    (Widget|SetVisibility :self W :InVisibility "HitTestInvisible")
    (else
      (Widget|SetVisibility :self W :InVisibility "Hidden"))))
'''
    G['HeldNow'] = '''
(fn HeldNow ()
  (bind c (Utilities|Casting|CastToBP_GW_Character (Pawn|GetControlledPawn :self (Widget|GetOwningPlayer)))
    (:then (return (GW|Get|BP_GW_Character|HeldItem :self c)))
    (:CastFailed (return 0))))
'''
    G['HealthOf'] = '''
(fn HealthOf (PC)
  (bind ch (Utilities|Casting|CastToBP_GW_Character (Pawn|GetControlledPawn :self PC))
    (:then (return (GW|Get|BP_GW_Character|Health :self ch)))
    (:CastFailed (return -1.0))))
'''
    G['FormatTime'] = '''
(fn FormatTime (Seconds)
  (bind total (Math|Float|Truncate (+ Seconds 0.999)))
  (bind s (% total 60))
  (return (cat (/ total 60) (select (< s 10) ":0" ":") s)))
'''
    G['BuildScores'] = '''
(fn BuildScores ()
  (Variables|Default|SetAcc (cat (Utilities|String|RightPad :SourceString "JOUEUR" :ChCount 18) (Utilities|String|RightPad :SourceString "RÔLE" :ChCount 11) (Utilities|String|RightPad :SourceString "SCORE" :ChCount 7) (Utilities|String|RightPad :SourceString "DÉMASQUÉS" :ChCount 11) "ERREURS"))
  (for p (Class|GameStateBase|GetPlayerArray :self (Game|GetGameState))
    (bind ps (Utilities|Casting|CastToBP_GW_PlayerState p)
      (:then
        (bind role (GW|Get|BP_GW_PlayerState|GWRole :self ps))
        (Variables|Default|SetAcc (cat (Variables|Default|GetAcc) "
" (Utilities|String|RightPad :SourceString (Utilities|String|Left :SourceString (PlayerState|GetPlayerName :self ps) :Count 16) :ChCount 18) (Utilities|String|RightPad :SourceString (select (== role 2) "Détective" (select (== role 1) "Invité" "—")) :ChCount 11) (Utilities|String|RightPad :SourceString (Utilities|String|ToString(Integer) (GW|Get|BP_GW_PlayerState|GWScore :self ps)) :ChCount 7) (Utilities|String|RightPad :SourceString (Utilities|String|ToString(Integer) (GW|Get|BP_GW_PlayerState|Kills :self ps)) :ChCount 11) (GW|Get|BP_GW_PlayerState|Mistakes :self ps) (select (GW|Get|BP_GW_PlayerState|IsAlive :self ps) "" "   (éliminé)"))))
      (:CastFailed)))
  (return (Variables|Default|GetAcc)))
'''
    nl = '"\n"'
    G['BuildScoreCols'] = f'''
(fn BuildScoreCols ()
  (Variables|Default|SetCN "")
  (Variables|Default|SetCR "")
  (Variables|Default|SetCS "")
  (Variables|Default|SetCK "")
  (Variables|Default|SetCE "")
  (for p (Class|GameStateBase|GetPlayerArray :self (Game|GetGameState))
    (bind ps (Utilities|Casting|CastToBP_GW_PlayerState p)
      (:then
        (bind role (GW|Get|BP_GW_PlayerState|GWRole :self ps))
        (bind alive (GW|Get|BP_GW_PlayerState|IsAlive :self ps))
        (Variables|Default|SetCN (cat (Variables|Default|GetCN) (Utilities|String|Left :SourceString (PlayerState|GetPlayerName :self ps) :Count 18) (select alive "" "  †") {nl}))
        (Variables|Default|SetCR (cat (Variables|Default|GetCR) (select (== role 1) (select alive "En vie" "Éliminé") "—") {nl}))
        (Variables|Default|SetCS (cat (Variables|Default|GetCS) (GW|Get|BP_GW_PlayerState|GWScore :self ps) {nl}))
        (Variables|Default|SetCK (cat (Variables|Default|GetCK) (GW|Get|BP_GW_PlayerState|Kills :self ps) {nl}))
        (Variables|Default|SetCE ""))
      (:CastFailed)))
  {txt('ColName', '(Variables|Default|GetCN)')}
  {txt('ColRole', '(Variables|Default|GetCR)')}
  {txt('ColScore', '(Variables|Default|GetCS)')}
  {txt('ColKills', '(Variables|Default|GetCK)')}
  {txt('ColErr', '(Variables|Default|GetCE)')})
'''
    G['DebugDump'] = '''
(fn DebugDump ()
  (return (cat "role=" (Utilities|String|ToString(Text) (Widget|GetText(Text) :self (Variables|WBP_HUD|GetTxtRole))) " | timer=" (Utilities|String|ToString(Text) (Widget|GetText(Text) :self (Variables|WBP_HUD|GetTxtPhase))) " " (Utilities|String|ToString(Text) (Widget|GetText(Text) :self (Variables|WBP_HUD|GetTxtTimer))) " | " (Utilities|String|ToString(Text) (Widget|GetText(Text) :self (Variables|WBP_HUD|GetTxtHiders))) " | " (Utilities|String|ToString(Text) (Widget|GetText(Text) :self (Variables|WBP_HUD|GetTxtHealth))) " | center=" (Utilities|String|ToString(Text) (Widget|GetText(Text) :self (Variables|WBP_HUD|GetTxtCenter))) " | event=" (Utilities|String|ToString(Text) (Widget|GetText(Text) :self (Variables|WBP_HUD|GetTxtAnnounce))) " | notice=" (Utilities|String|ToString(Text) (Widget|GetText(Text) :self (Variables|WBP_HUD|GetTxtNotice))) " | blind=" (Widget|IsVisible :self (Variables|WBP_HUD|GetBlindfold)) " cross=" (Widget|IsVisible :self (Variables|WBP_HUD|GetCrosshair)) " scores=" (Widget|IsVisible :self (Variables|WBP_HUD|GetScorePanel)) " | money=" (Variables|UI|GetLastMoney) " | music=" (Variables|UI|GetMusState))))
'''
    G['Refresh'] = '''
(fn Refresh (PC ShowScores)
  (bind gsx (Utilities|Casting|CastToBP_GW_GameState (Game|GetGameState))
    (:then
      (bind psx (Utilities|Casting|CastToBP_GW_PlayerState (GW|Get|/Script/Engine.Controller|PlayerState :self PC))
        (:then
          (CallFunction|RefreshWith :GS gsx :PS psx :PC PC :ShowScores ShowScores))
        (:CastFailed)))
    (:CastFailed)))
'''
    G['RefreshWith'] = f'''
(fn RefreshWith (GS PS PC ShowScores)
  (bind phase {gs('Phase')})
  (bind role (GW|Get|BP_GW_PlayerState|GWRole :self PS))
  (bind alive (GW|Get|BP_GW_PlayerState|IsAlive :self PS))
  (bind now (GameState|GetServerWorldTimeSeconds :self GS))
  (bind pend {gs('PhaseEndTime')})
  (bind rem (Math|Float|Max(Float) (- pend now) 0.0))
  (bind remS (Math|Float|Truncate (+ rem 0.999)))
  (bind np (Utilities|Array|Length (Class|GameStateBase|GetPlayerArray :self GS)))
  (bind isSeeker (== role 2))
  (bind playing (or (== phase 1) (== phase 2)))
  (bind ghost (and (!= phase 0) (or (not alive) (== role 0))))
  (bind winner {gs('Winner')})
  (bind toLobby (or (== winner 3) (< np 2)))
  (if (== phase 0)
    (Variables|Default|SetRoleT "SALLE D'ATTENTE")
    (elif ghost
      (Variables|Default|SetRoleT (select (== role 0) "SPECTATEUR" "FANTÔME"))
      (elif isSeeker
        (Variables|Default|SetRoleT "DÉTECTIVE")
        (else
          (Variables|Default|SetRoleT "INVITÉ")))))
  (if (== phase 1)
    (Variables|Default|SetPhaseT "CACHETTE")
    (elif (== phase 2)
      (Variables|Default|SetPhaseT (select (<= rem 30.0) "DERNIÈRES SECONDES" "LA CHASSE"))
      (elif (== phase 3)
        (Variables|Default|SetPhaseT (select toLobby "RETOUR AU SALON" "MANCHE SUIVANTE"))
        (else
          (Variables|Default|SetPhaseT "SALON")))))
  (Variables|Default|SetTimerT (select (or (!= phase 0) (> pend 0.0)) (CallFunction|FormatTime :Seconds rem) "—"))
  ; dev menu test round: no countdown once the hunt runs (it never ends by itself)
  (if (and {gs('TestRound')} (== phase 2))
    (Variables|Default|SetTimerT "TEST")
    (Variables|Default|SetPhaseT "MANCHE DE TEST"))
  (Variables|Default|SetNextT (select toLobby (cat "Retour au salon dans " remS " s") (cat "Manche suivante dans " remS " s")))
  (if (== phase 3)
    (Variables|Default|SetCenterT (select (== winner 2) (select (== role 0) "LE BAL EST TERMINÉ" (select alive "VOUS AVEZ SURVÉCU !" "VOUS ÊTES TOMBÉ")) (select (== winner 4) "PERSONNE N'A SURVÉCU" "MANCHE ANNULÉE")))
    (else
      (Variables|Default|SetCenterT "")))
  ; personal notices: the server's word on your purchases / earnings, for 3.5 s
  (Variables|Default|SetNoticeT "")
  ; ("+25 $ : ..." is not repeated in words: the green popup says it)
  (if (and (< (- now {SPS('ShopNoteAt')}) 3.5) (and (> (Utilities|String|Len {SPS('ShopNote')}) 0) (Utilities|String|NotEqualExactly(String) (Utilities|String|Left :SourceString {SPS('ShopNote')} :Count 1) "+")))
    (Variables|Default|SetNoticeT {SPS('ShopNote')}))
  (if (< (- (Utilities|Time|GetRealTimeSeconds) (Variables|GW|GetLocalNoticeTime)) 3.0)
    (Variables|Default|SetNoticeT (Variables|GW|GetLocalNotice)))
  {txt('TxtRole', '(Variables|Default|GetRoleT)')}
  {txt('TxtTimer', '(Variables|Default|GetTimerT)')}
  {txt('TxtPhase', '(Variables|Default|GetPhaseT)')}
  {txt('TxtCenter', '(Variables|Default|GetCenterT)')}
  {txt('TxtNotice', '(Variables|Default|GetNoticeT)')}
  ; a ghost's way of moving (was in the instruction line at the top)
  {txt('TxtHint', '(select ghost "Vous êtes éliminé : volez librement (WASD + souris)    ·    Tab : scores    ·    Échap : menu" (Variables|UI|GetHintBase))')}
  (if (< (- (Utilities|Time|GetRealTimeSeconds) (Variables|GW|GetPromptAt)) 0.35)
    (Widget|SetVisibility :self {HV('PromptPlate')} :InVisibility "HitTestInvisible")
    {txt('TxtPrompt', '(Variables|GW|GetPrompt)')}
    {txt('TxtPromptKey', '(Variables|GW|GetPromptKey)')}
    (else
      (Widget|SetVisibility :self {HV('PromptPlate')} :InVisibility "Collapsed")))
  {txt('EndNext', '(Variables|Default|GetNextT)')}
  {txt('EndBody', gs('Message'))}
  {txt('TxtHiders', '(select (or playing (== phase 3)) (cat "Survivants : " ' + gs('HidersAlive') + ') (cat np " convive" (select (> np 1) "s" "")))')}
  {txt('TxtHealth', '(cat "" (Math|Float|Round (Math|Float|Max(Float) (CallFunction|HealthOf :PC PC) 0.0)))')}
  {txt('TxtMoney', '(cat "" ' + SPS('Money') + ')')}
  (bind blind (and isSeeker (and alive (== phase 1))))
  (CallFunction|ShowW :W (Variables|WBP_HUD|GetBlindfold) :Show blind)
  (if blind
    {txt('BlindText', 'remS')})
  ; crosshair: only with something aimed in hand (s40: rifle 1, swap gun 8, balls 11, revolver 13)
  (bind held (CallFunction|HeldNow))
  (CallFunction|ShowW :W (Variables|WBP_HUD|GetCrosshair) :Show (and (or (== held 1) (or (== held 8) (or (== held 11) (== held 13)))) (and alive (== phase 2))))
  (CallFunction|ShowW :W (Variables|WBP_HUD|GetHealthRow) :Show (and alive (not ghost)))
  ; the help line: while there is time to read it (salon, hiding, the first 20 s of the hunt), for a ghost, with Tab
  (CallFunction|ShowW :W (Variables|WBP_HUD|GetHintPlate) :Show (or ghost (or (!= phase 2) (or ShowScores (< (- (Variables|UI|GetPhaseDur) rem) 20.0)))))
  (bind scores (or ShowScores (== phase 3)))
  (CallFunction|ShowW :W (Variables|WBP_HUD|GetScorePanel) :Show scores)
  (if scores
    (bind sc (CallFunction|BuildScores))
    {txt('TxtScores', 'sc')}
    (CallFunction|BuildScoreCols)))
'''
    # ------------------------------------------------------------------ audio helpers
    G['PlayMus'] = f'''
(fn PlayMus (Snd Vol Fade)
  (bind c (Audio|CreateSound2D :Sound Snd :VolumeMultiplier Vol :PitchMultiplier 1.0 :StartTime 0.0 :bPersistAcrossLevelTransition false :bAutoDestroy true))
  (if ({ISVALID} :Object c)
    (GW|Call|{AC}|FadeIn :self c :FadeInDuration Fade :FadeVolumeLevel 1.0 :StartTime 0.0))
  (return c))
'''
    G['FadeComp'] = f'''
(fn FadeComp (Comp Dur)
  (if ({ISVALID} :Object Comp)
    (GW|Call|{AC}|FadeOut :self Comp :FadeOutDuration Dur :FadeVolumeLevel 0.0)))
'''
    G['QueueVo'] = '''
(fn QueueVo (Snd Delay)
  (Variables|UI|SetVoSnd Snd)
  (Variables|UI|SetVoAt (+ (Utilities|Time|GetRealTimeSeconds) Delay)))
'''
    vo = (lambda key, d: f'(CallFunction|QueueVo :Snd "/Game/GW/Audio/VO_{key}.VO_{key}" :Delay {d})') if has_vo else (lambda key, d: '')
    # music states: 0 lobby, 1 party, 2 hunt, 3 last 30 s, 4-8 event tracks (3 + event id), 20 round over (Default)
    EVENT_TRACKS = {4: 'MUS_Event_Attack', 5: 'MUS_Event_Fire', 6: 'MUS_Event_Blackout', 7: 'MUS_Event_Attack',
                    8: 'MUS_Event_Robot'}
    EVENT_MUSIC_CASES = '\n'.join(f'''    (:{st}
      (CallFunction|FadeComp :Comp (Variables|UI|GetMusA) :Dur 1.0)
      (CallFunction|FadeComp :Comp (Variables|UI|GetMusB) :Dur 0.8)
      (bind e{st} (CallFunction|PlayMus :Snd "/Game/GW/Audio/Gen/music/{t}.{t}" :Vol 0.85 :Fade 0.8))
      (Variables|UI|SetMusB e{st}))''' for st, t in EVENT_TRACKS.items()
        if unreal.EditorAssetLibrary.does_asset_exist(f'/Game/GW/Audio/Gen/music/{t}'))
    G['SetMusicState'] = f'''
(fn SetMusicState (NewState Winner)
  (Variables|UI|SetPrevMus (Variables|UI|GetMusState))
  (Variables|UI|SetMusState NewState)
  (bind old (Variables|UI|GetPrevMus))
  (Variables|UI|SetLateMusAt 0.0)
  (Development|PrintString :InString (cat "GW music: state " old " -> " NewState) :bPrintToScreen false)
  (switch int NewState
    (:0
      (CallFunction|FadeComp :Comp (Variables|UI|GetMusA) :Dur 2.0)
      (CallFunction|FadeComp :Comp (Variables|UI|GetMusB) :Dur 2.0)
      (bind a0 (CallFunction|PlayMus :Snd "/Game/GW/Audio/MUS_Lobby.MUS_Lobby" :Vol 0.75 :Fade 3.0))
      (Variables|UI|SetMusA a0)
      (if (< old 0)
        {vo('Welcome', 2.0)}))
    (:1
      (CallFunction|FadeComp :Comp (Variables|UI|GetMusA) :Dur 1.5)
      (CallFunction|FadeComp :Comp (Variables|UI|GetMusB) :Dur 1.5)
      (bind a1 (CallFunction|PlayMus :Snd "/Game/GW/Audio/MUS_Party.MUS_Party" :Vol 1.0 :Fade 2.5))
      (Variables|UI|SetMusA a1)
      (Audio|PlaySound2D :Sound "/Game/GW/Audio/STG_Reveal.STG_Reveal" :VolumeMultiplier 0.9))
    (:2
      ; the hunt: the party simply goes on, a little quieter (no stress music for the clock)
      (bind ma (Variables|UI|GetMusA))
      (CallFunction|FadeComp :Comp (Variables|UI|GetMusB) :Dur 1.0)
      (if (or (>= old 4) (not ({ISVALID} :Object ma)))
        (bind a2 (CallFunction|PlayMus :Snd "/Game/GW/Audio/MUS_Party.MUS_Party" :Vol 0.7 :Fade 3.0))
        (Variables|UI|SetMusA a2)
        (else
          (GW|Call|{AC}|AdjustVolume :self ma :AdjustVolumeDuration 3.0 :AdjustVolumeLevel 0.7)))
      (if (not (and (>= old 4) (<= old 8)))
        (Audio|PlaySound2D :Sound "/Game/GW/Audio/STG_Start.STG_Start" :VolumeMultiplier 0.7)
        {vo('Hunt', 3.0)}))
{EVENT_MUSIC_CASES}
    (:3
      (bind ma3 (Variables|UI|GetMusA))
      (if ({ISVALID} :Object ma3)
        (GW|Call|{AC}|AdjustVolume :self ma3 :AdjustVolumeDuration 2.0 :AdjustVolumeLevel 0.2))
      (CallFunction|FadeComp :Comp (Variables|UI|GetMusB) :Dur 1.5)
      (bind b3 (CallFunction|PlayMus :Snd "/Game/GW/Audio/MUS_Final.MUS_Final" :Vol 0.95 :Fade 1.5))
      (Variables|UI|SetMusB b3)
      (Audio|PlaySound2D :Sound "/Game/GW/Audio/S_GW_ClockChime.S_GW_ClockChime" :VolumeMultiplier 0.55)
      {vo('Thirty', 2.2)})
    (:Default
      (CallFunction|FadeComp :Comp (Variables|UI|GetMusA) :Dur 1.5)
      (CallFunction|FadeComp :Comp (Variables|UI|GetMusB) :Dur 0.8)
      ; (no announcer here: the recorded line says "the guests win", and there is one winner now)
      (if (== Winner 2)
        (Audio|PlaySound2D :Sound "/Game/GW/Audio/STG_Guests.STG_Guests" :VolumeMultiplier 0.9)
        (elif (== Winner 4)
          (Audio|PlaySound2D :Sound "/Game/GW/Audio/STG_Detectives.STG_Detectives" :VolumeMultiplier 0.9)))
      (Variables|UI|SetLateMusAt (+ (Utilities|Time|GetRealTimeSeconds) 6.5)))))
'''
    G['MusicTick'] = f'''
(fn MusicTick (GS PS)
  (bind phase {gs('Phase')})
  (bind rem (- {gs('PhaseEndTime')} (GameState|GetServerWorldTimeSeconds :self GS)))
  (bind ev {gs('EventId')})
  ; the user, 2026-11-05: MUS_Event_Attack (a stab every 0.78 s, the "TIN TIN TIN") is gone from the events and from gunfire. The music stays on the party;
  ; when shooting starts, one single stab (SFX_Shot_Hit, cut from that track). TenseUntil runs 25 s after the last shot: no second stab during a fight
  (bind tense (< (GameState|GetServerWorldTimeSeconds :self GS) {gs('TenseUntil')}))
  (if (!= tense (Variables|UI|GetWasTense))
    (Variables|UI|SetWasTense tense)
    (if (and tense (== phase 2))
      (Audio|PlaySound2D :Sound "/Game/GW/Audio/Gen/sting/SFX_Shot_Hit.SFX_Shot_Hit" :VolumeMultiplier 0.55)
      (Development|PrintString :InString "GW music: one shot hit" :bPrintToScreen false)))
  (bind want (select (== phase 0) 0 (select (== phase 1) 1 (select (== phase 2) 2 20))))
  (if (!= want (Variables|UI|GetMusState))
    (CallFunction|SetMusicState :NewState want :Winner {gs('Winner')}))
  (bind rt (Utilities|Time|GetRealTimeSeconds))
  (bind lm (Variables|UI|GetLateMusAt))
  (if (and (> lm 0.0) (>= rt lm))
    (Variables|UI|SetLateMusAt 0.0)
    (bind a4 (CallFunction|PlayMus :Snd "/Game/GW/Audio/MUS_Lobby.MUS_Lobby" :Vol 0.55 :Fade 4.0))
    (Variables|UI|SetMusA a4))
  (bind vs (Variables|UI|GetVoSnd))
  (if (and ({ISVALID} :Object vs) (>= rt (Variables|UI|GetVoAt)))
    (Audio|PlaySound2D :Sound vs :VolumeMultiplier 1.0)
    (Variables|UI|SetVoAt 1000000000.0)))
'''
    G['ApplyFov'] = f'''
(fn ApplyFov ()
  (bind gi (Utilities|Casting|CastToBP_GW_GameInstance (Widget|GetGameInstance))
    (:then
      (bind s (GW|Call|BP_GW_GameInstance|GWSettings :self gi))
      (bind ch (Utilities|Casting|CastToBP_GW_Character (Player|GetOwningPlayerPawn))
        (:then
          (Camera|SetFieldOfView :self (GW|Get|BP_GW_Character|FollowCamera :self ch) :InFieldOfView (GW|Get|{SET}|FOV :self s)))
        (:CastFailed)))
    (:CastFailed)))
'''
    G['TogglePause'] = '''
(fn TogglePause ()
  (bind pw (Variables|UI|GetPauseW))
  (if (not (GW|Call|/Script/Engine.KismetSystemLibrary|IsValid :Object pw))
    (bind w0 (UserInterface|CreateWidget :Class "/Game/GW/UI/WBP_Pause.WBP_Pause_C" :OwningPlayer (Widget|GetOwningPlayer)))
    (Variables|UI|SetPauseW w0)
    (UserInterface|Viewport|AddtoViewport :self w0 :ZOrder 50)
    (return))
  (if (Appearance|IsinViewport :self pw)
    (bind pp (Utilities|Casting|CastToWBP_Pause pw)
      (:then (GW|Call|/Game/GW/UI/WBP_Pause.WBP_Pause_C|ClosePause :self pp))
      (:CastFailed))
    (else
      (bind w (UserInterface|CreateWidget :Class "/Game/GW/UI/WBP_Pause.WBP_Pause_C" :OwningPlayer (Widget|GetOwningPlayer)))
      (Variables|UI|SetPauseW w)
      (UserInterface|Viewport|AddtoViewport :self w :ZOrder 50))))
'''
    G['MusicTimer'] = '''
(fn MusicTimer ()
  (bind gsx (Utilities|Casting|CastToBP_GW_GameState (Game|GetGameState))
    (:then
      (bind psx (Utilities|Casting|CastToBP_GW_PlayerState (GW|Get|/Script/Engine.Controller|PlayerState :self (Widget|GetOwningPlayer)))
        (:then
          (CallFunction|MusicTick :GS gsx :PS psx))
        (:CastFailed)))
    (:CastFailed)))
'''
    G['SetupHUD'] = f'''
(fn SetupHUD ()
  (Utilities|Time|SetTimerbyFunctionName :Object self :FunctionName "MusicTimer" :Time 0.2 :bLooping true)
  (Variables|UI|SetMusState -1)
  (Variables|UI|SetPhaseSeen -1)
  (Variables|UI|SetRoleSeen -1)
  (Variables|UI|SetCardT 99.0)
  (Variables|UI|SetEndT 99.0)
  (Variables|UI|SetLastHealth 100.0)
  (Variables|UI|SetLastMoney -1)
  (Variables|UI|SetLastBuys -1)
  (Variables|UI|SetGainT 99.0)
  (Widget|SetVisibility :self {HV('RoleCard')} :InVisibility "Hidden")
  (Widget|SetVisibility :self {HV('EndCard')} :InVisibility "Hidden")
  (Variables|UI|SetAnnT 99.0)
  (Variables|UI|SetLastEvStart -1.0)
  (bind gi (Utilities|Casting|CastToBP_GW_GameInstance (Widget|GetGameInstance))
    (:then
      (GW|Call|BP_GW_GameInstance|GWApplyAudio :self gi)
      (GW|Call|BP_GW_GameInstance|GWApplyKeys :self gi)
      (Variables|UI|SetHintBase (cat (GW|Call|BP_GW_GameInstance|GWKeyLabel :self gi :Key "E") " : interagir   ·   " (GW|Call|BP_GW_GameInstance|GWKeyLabel :self gi :Key "1") "-" (GW|Call|BP_GW_GameInstance|GWKeyLabel :self gi :Key "4") " : objets   ·   " (GW|Call|BP_GW_GameInstance|GWKeyLabel :self gi :Key "Q") " : jeter   ·   " (GW|Call|BP_GW_GameInstance|GWKeyLabel :self gi :Key "C") " : vue   ·   " (GW|Call|BP_GW_GameInstance|GWKeyLabel :self gi :Key "Space Bar") " : sauter   ·   " (GW|Call|BP_GW_GameInstance|GWKeyLabel :self gi :Key "Tab") " : scores   ·   Échap : menu"))
      (bind s (GW|Call|BP_GW_GameInstance|GWSettings :self gi))
      (bind pc (Utilities|Casting|CastToBP_GW_PlayerController (Widget|GetOwningPlayer))
        (:then (GW|Call|BP_GW_PlayerController|UIApplyLook :self pc :Sens (GW|Get|{SET}|MouseSens :self s)))
        (:CastFailed)))
    (:CastFailed)))
'''
    G['StyleTick'] = '''
(fn StyleTick (Dt)
  (Variables|UI|SetT (+ (Variables|UI|GetT) Dt))
  (bind gsx (Utilities|Casting|CastToBP_GW_GameState (Game|GetGameState))
    (:then
      (bind psx (Utilities|Casting|CastToBP_GW_PlayerState (GW|Get|/Script/Engine.Controller|PlayerState :self (Widget|GetOwningPlayer)))
        (:then
          (CallFunction|StyleWith :GS gsx :PS psx :Dt Dt))
        (:CastFailed)))
    (:CastFailed)))
'''
    G['StyleWith'] = f'''
(fn StyleWith (GS PS Dt)
  (bind t (Variables|UI|GetT))
  (bind phase {gs('Phase')})
  (bind role (GW|Get|BP_GW_PlayerState|GWRole :self PS))
  (bind alive (GW|Get|BP_GW_PlayerState|IsAlive :self PS))
  (bind now (GameState|GetServerWorldTimeSeconds :self GS))
  (bind rem (Math|Float|Max(Float) (- {gs('PhaseEndTime')} now) 0.0))
  ; phase change bookkeeping: dial duration, role card, end card
  (if (!= phase (Variables|UI|GetPhaseSeen))
    (Variables|UI|SetPhaseDur (Math|Float|Max(Float) rem 1.0))
    (Variables|UI|SetCardDone false)
    (if (== phase 3)
      (Variables|UI|SetEndT 0.0)
      (Audio|PlaySound2D :Sound "/Game/GW/Audio/S_UI_Card.S_UI_Card" :VolumeMultiplier 0.8))
    (Variables|UI|SetPhaseSeen phase))
  ; role card: once per hiding phase, as soon as the (separately replicated) role is known
  (if (and (and (== phase 1) (not (Variables|UI|GetCardDone))) (or (== role 1) (== role 2)))
    (Variables|UI|SetCardDone true)
    (Variables|UI|SetCardT 0.0)
    (Audio|PlaySound2D :Sound "/Game/GW/Audio/S_UI_Card.S_UI_Card" :VolumeMultiplier 1.0))
  ; dial hand: sweeps once over the phase
  (bind frac (CallFunction|Clamp01 :V (- 1.0 (/ rem (Math|Float|Max(Float) (Variables|UI|GetPhaseDur) 1.0)))))
  (Widget|Transform|SetRenderTransformAngle :self {HV('DialHand')} :Angle (select (== phase 0) (* t 6.0) (* frac 360.0)))
  ; timer colour: last 30 s of the hunt pulse burgundy/gold
  (bind urgent (and (== phase 2) (<= rem 30.0)))
  (bind pulse (* 0.5 (+ 1.0 (Math|Trig|Sin(Radians) (* t 7.0)))))
  (Class|Text|SetColorandOpacity :self {HV('TxtTimer')} :ColorAndOpacity (Utilities|Struct|MakeSlateColor :SpecifiedColor (select urgent (Math|Color|MakeColor (+ 0.7 (* 0.3 pulse)) (* 0.25 pulse) (* 0.08 pulse) 1.0) (Math|Color|MakeColor 0.86 0.8 0.66 1.0))))
  (bind ts (select urgent (+ 1.0 (* 0.06 pulse)) 1.0))
  (Widget|Transform|SetRenderScale :self {HV('TxtTimer')} :Scale (Math|Vector2D|MakeVector2D ts ts))
  ; role icon
  (bind ghost (and (!= phase 0) (or (not alive) (== role 0))))
  (if ghost
    (GW|Call|/Script/UMG.Image|SetBrushFromTexture :self {HV('RoleIcon')} :Texture "/Game/GW/UI/Textures/T_UI_IcoGhost.T_UI_IcoGhost" :bMatchSize false)
    (elif (== role 2)
      (GW|Call|/Script/UMG.Image|SetBrushFromTexture :self {HV('RoleIcon')} :Texture "/Game/GW/UI/Textures/T_UI_IcoRevolver.T_UI_IcoRevolver" :bMatchSize false)
      (else
        (GW|Call|/Script/UMG.Image|SetBrushFromTexture :self {HV('RoleIcon')} :Texture "/Game/GW/UI/Textures/T_UI_IcoMask.T_UI_IcoMask" :bMatchSize false))))
  ; life: any loss (trap, shot, explosion, zombie...): red vignette, red "-X", a thud, the panel shakes; quick losses add up. The bar goes from gold to red, pulses under 25
  (bind hp (CallFunction|HealthOf :PC (Widget|GetOwningPlayer)))
  (bind lastHp (Variables|UI|GetLastHealth))
  (if (and (>= hp 0.0) (< hp (- lastHp 0.5)))
    (Variables|UI|SetHurtSum (+ (select (< (Variables|UI|GetHurtT) 1.3) (Variables|UI|GetHurtSum) 0.0) (- lastHp hp)))
    (Variables|UI|SetHurtT 0.0)
    {txt('TxtHurtPop', '(cat "-" (Math|Float|Round (Variables|UI|GetHurtSum)))')}
    (Audio|PlaySound2D :Sound "/Game/GW/Audio/S_GW_Thud.S_GW_Thud" :VolumeMultiplier 1.0)
    (Development|PrintString :InString (cat "GW hud: hurt " lastHp " -> " hp) :bPrintToScreen false))
  (Variables|UI|SetLastHealth hp)
  (Variables|UI|SetHurtT (+ (Variables|UI|GetHurtT) Dt))
  (bind ht (Variables|UI|GetHurtT))
  (bind hurt (- 1.0 (CallFunction|Clamp01 :V (/ ht 0.6))))
  (bind frac01 (CallFunction|Clamp01 :V (/ hp 100.0)))
  (bind low (- 1.0 (CallFunction|Clamp01 :V (/ (- frac01 0.25) 0.5))))
  (bind beat (select (< frac01 0.25) (* 0.5 (+ 1.0 (Math|Trig|Sin(Radians) (* t 8.0)))) 0.0))
  (bind hr (+ 0.92 (* 0.08 hurt)))
  (bind hg (+ (* (+ 0.73 (* -0.68 low)) (- 1.0 hurt)) (* 0.9 hurt)))
  (bind hb (+ (* (+ 0.32 (* -0.29 low)) (- 1.0 hurt)) (* 0.8 hurt)))
  (Class|Image|SetColorandOpacity :self {HV('HealthFill')} :ColorAndOpacity (Math|Color|MakeColor hr hg hb (- 1.0 (* 0.35 beat))))
  (Widget|Transform|SetRenderScale :self {HV('HealthFill')} :Scale (Math|Vector2D|MakeVector2D (Math|Float|Max(Float) frac01 0.001) 1.0))
  (Class|Text|SetColorandOpacity :self {HV('TxtHealth')} :ColorAndOpacity (Utilities|Struct|MakeSlateColor :SpecifiedColor (Math|Color|MakeColor (+ 0.86 (* 0.1 low)) (* 0.8 (- 1.0 (* 0.85 (Math|Float|Max(Float) low hurt)))) (* 0.66 (- 1.0 (* 0.9 (Math|Float|Max(Float) low hurt)))) 1.0)))
  (bind hs (+ 1.0 (* 0.3 hurt)))
  (Widget|Transform|SetRenderScale :self {HV('HealthIcon')} :Scale (Math|Vector2D|MakeVector2D hs hs))
  (Widget|Transform|SetRenderTranslation :self {HV('StatusPanel')} :Translation (Math|Vector2D|MakeVector2D (* (* hurt 9.0) (Math|Trig|Sin(Radians) (* t 55.0))) (* (* hurt -4.0) (Math|Trig|Cos(Radians) (* t 41.0)))))
  (if (< ht 0.9)
    (Widget|SetVisibility :self {HV('HurtFlash')} :InVisibility "HitTestInvisible")
    (Widget|SetRenderOpacity :self {HV('HurtFlash')} :InOpacity (* (- 1.0 (CallFunction|Clamp01 :V (/ ht 0.9))) 1.0))
    (else
      (Widget|SetVisibility :self {HV('HurtFlash')} :InVisibility "Hidden")))
  (if (< ht 1.6)
    (Widget|SetVisibility :self {HV('TxtHurtPop')} :InVisibility "HitTestInvisible")
    (bind hin (CallFunction|Ease :V (/ ht 0.12)))
    (bind hps (+ (+ 0.6 (* 0.6 hin)) (* -0.2 (CallFunction|Ease :V (/ (- ht 0.12) 0.2)))))
    (Widget|Transform|SetRenderScale :self {HV('TxtHurtPop')} :Scale (Math|Vector2D|MakeVector2D hps hps))
    (Widget|Transform|SetRenderTranslation :self {HV('TxtHurtPop')} :Translation (Math|Vector2D|MakeVector2D 0.0 (* 60.0 (CallFunction|Ease :V (/ ht 1.6)))))
    (Widget|SetRenderOpacity :self {HV('TxtHurtPop')} :InOpacity (* hin (- 1.0 (CallFunction|Ease :V (/ (- ht 1.0) 0.6)))))
    (else
      (Widget|SetVisibility :self {HV('TxtHurtPop')} :InVisibility "Hidden")))
  ; crosshair breathing
  (bind cs (+ 1.0 (* 0.04 (Math|Trig|Sin(Radians) (* t 2.2)))))
  (Widget|Transform|SetRenderScale :self {HV('Crosshair')} :Scale (Math|Vector2D|MakeVector2D cs cs))
  ; events: red name mid-screen for 4.5 s: slams in, rules spread, fades out (s32_events.py sets EventId / EventName / EventStart)
  (bind evst {gs('EventStart')})
  (if (and (!= {gs('EventId')} 0) (!= evst (Variables|UI|GetLastEvStart)))
    (Variables|UI|SetLastEvStart evst)
    (if (< (- now evst) 4.0)
      (Variables|UI|SetAnnT 0.0)
      {txt('TxtAnnounce', gs('EventName'))}))
  (bind at (+ (Variables|UI|GetAnnT) Dt))
  (Variables|UI|SetAnnT at)
  (if (and (< at 4.5) (!= phase 3))
    (Widget|SetVisibility :self {HV('EventAnnounce')} :InVisibility "HitTestInvisible")
    (bind ain (CallFunction|Ease :V (/ at 0.22)))
    (bind aout (CallFunction|Ease :V (/ (- at 3.7) 0.8)))
    (bind asc (+ (+ 1.0 (* 0.7 (- 1.0 ain))) (* 0.02 (Math|Trig|Sin(Radians) (* at 9.0)))))
    (Widget|Transform|SetRenderScale :self {HV('TxtAnnounce')} :Scale (Math|Vector2D|MakeVector2D asc asc))
    (Widget|SetRenderOpacity :self {HV('EventAnnounce')} :InOpacity (* ain (- 1.0 aout)))
    (bind arule (CallFunction|Ease :V (/ (- at 0.1) 0.5)))
    (Widget|Transform|SetRenderScale :self {HV('AnnRuleTop')} :Scale (Math|Vector2D|MakeVector2D arule 1.0))
    (Widget|Transform|SetRenderScale :self {HV('AnnRuleBot')} :Scale (Math|Vector2D|MakeVector2D arule 1.0))
    (else
      (Widget|SetVisibility :self {HV('EventAnnounce')} :InVisibility "Hidden")))
  ; role reveal card: flip in, hold, fly up and fade
  (bind ct (+ (Variables|UI|GetCardT) Dt))
  (Variables|UI|SetCardT ct)
  (bind card {HV('RoleCard')})
  (if (< ct 4.2)
    (Widget|SetVisibility :self card :InVisibility "HitTestInvisible")
    (GW|Call|/Script/UMG.Image|SetBrushFromTexture :self {HV('RoleCardImg')} :Texture "/Game/GW/UI/Textures/T_UI_CardInvite.T_UI_CardInvite" :bMatchSize false)
    {txt('RoleCardTitle', '"INVITÉ"')}
    {txt('RoleCardSub', '"Fondez-vous dans la foule. Trouvez les autres joueurs. Soyez le dernier debout."')}
    (bind fin (CallFunction|Ease :V (/ ct 0.45)))
    (bind fout (CallFunction|Ease :V (/ (- ct 3.3) 0.6)))
    (bind sx (* (Math|Float|Max(Float) fin 0.02) (- 1.0 (* 0.55 fout))))
    (bind sy (* (+ 1.0 (* 0.12 (- 1.0 fin))) (- 1.0 (* 0.55 fout))))
    (Widget|Transform|SetRenderScale :self card :Scale (Math|Vector2D|MakeVector2D sx sy))
    (Widget|Transform|SetRenderTranslation :self card :Translation (Math|Vector2D|MakeVector2D 0.0 (* fout -420.0)))
    (Widget|SetRenderOpacity :self card :InOpacity (- 1.0 fout))
    (Widget|SetRenderOpacity :self {HV('BlindV')} :InOpacity fout)
    (else
      (Widget|SetVisibility :self card :InVisibility "Hidden")
      (Widget|SetRenderOpacity :self {HV('BlindV')} :InOpacity 1.0)))
  ; newspaper end card: spin in (1930s film headline), scoreboard slides right
  (bind et3 (+ (Variables|UI|GetEndT) Dt))
  (Variables|UI|SetEndT et3)
  (bind endc {HV('EndCard')})
  (bind sp {HV('ScorePanel')})
  (if (== phase 3)
    (Widget|SetVisibility :self endc :InVisibility "HitTestInvisible")
    (GW|Call|/Script/UMG.Image|SetBrushFromTexture :self {HV('EndPhoto')} :Texture "/Game/GW/UI/Textures/T_UI_PhotoGuests.T_UI_PhotoGuests" :bMatchSize false)
    (bind sn (CallFunction|Ease :V (/ et3 0.9)))
    (Widget|Transform|SetRenderTransformAngle :self endc :Angle (+ -3.0 (* -720.0 (- 1.0 sn))))
    (bind sc3 (+ 0.05 (* 0.95 sn)))
    (Widget|Transform|SetRenderScale :self endc :Scale (Math|Vector2D|MakeVector2D sc3 sc3))
    (Widget|Transform|SetRenderTranslation :self endc :Translation (Math|Vector2D|MakeVector2D -330.0 0.0))
    (bind so (CallFunction|Ease :V (/ (- et3 0.7) 0.5)))
    (Widget|Transform|SetRenderTranslation :self sp :Translation (Math|Vector2D|MakeVector2D (* 390.0 so) 0.0))
    (else
      (Widget|SetVisibility :self endc :InVisibility "Hidden")
      (Widget|Transform|SetRenderTranslation :self sp :Translation (Math|Vector2D|MakeVector2D 0.0 0.0))
      (Widget|Transform|SetRenderTransformAngle :self sp :Angle 0.0)))
  ; money gained (BP_GW_PlayerState.Money went up): coins + a green "+X $" that pops, rises and fades; gains in quick
  ; succession add up. The cash register when a purchase is confirmed (s34_shop.py)
  (bind mon {SPS('Money')})
  (bind buys {SPS('ShopBuys')})
  (if (and (>= (Variables|UI|GetLastMoney) 0) (> mon (Variables|UI|GetLastMoney)))
    (Variables|UI|SetGainSum (+ (select (< (Variables|UI|GetGainT) 1.3) (Variables|UI|GetGainSum) 0) (- mon (Variables|UI|GetLastMoney))))
    (Variables|UI|SetGainT 0.0)
    {txt('TxtMoneyPop', '(cat "+" (Variables|UI|GetGainSum) " $")')}
    {txt('TxtMoneyGlow', '(cat "+" (Variables|UI|GetGainSum) " $")')}
    (Audio|PlaySound2D :Sound {SHOP_SND['SFX_Shop_Coins']} :VolumeMultiplier 0.8))
  (if (and (>= (Variables|UI|GetLastBuys) 0) (> buys (Variables|UI|GetLastBuys)))
    (Audio|PlaySound2D :Sound {SHOP_SND['SFX_Shop_Buy']} :VolumeMultiplier 0.9))
  (if (and (>= (Variables|UI|GetLastMoney) 0) (< mon (Variables|UI|GetLastMoney)))
    (Variables|UI|SetSpendT 0.0))
  (Variables|UI|SetSpendT (+ (Variables|UI|GetSpendT) Dt))
  (Variables|UI|SetLastMoney mon)
  (Variables|UI|SetLastBuys buys)
  (Variables|UI|SetGainT (+ (Variables|UI|GetGainT) Dt))
  (bind gt (Variables|UI|GetGainT))
  (bind mg0 (- 1.0 (CallFunction|Clamp01 :V (/ gt 0.8))))
  (bind mr0 (- 1.0 (CallFunction|Clamp01 :V (/ (Variables|UI|GetSpendT) 0.8))))
  (Class|Text|SetColorandOpacity :self {HV('TxtMoney')} :ColorAndOpacity (Utilities|Struct|MakeSlateColor :SpecifiedColor (Math|Color|MakeColor (Math|Float|Max(Float) (* 0.86 (- 1.0 mg0)) (* 0.92 mr0)) (Math|Float|Max(Float) (* (+ 0.8 (* -0.75 mr0)) (- 1.0 mg0)) (* 0.92 mg0)) (* (+ 0.66 (* -0.62 mr0)) (- 1.0 (* 0.75 mg0))) 1.0)))
  (bind ms0 (+ 1.0 (* 0.18 (Math|Float|Max(Float) mg0 mr0))))
  (Widget|Transform|SetRenderScale :self {HV('TxtMoney')} :Scale (Math|Vector2D|MakeVector2D ms0 ms0))
  (if (< gt 2.0)
    (Widget|SetVisibility :self {HV('MoneyPop')} :InVisibility "HitTestInvisible")
    (bind gin (CallFunction|Ease :V (/ gt 0.14)))
    (bind gset (CallFunction|Ease :V (/ (- gt 0.14) 0.18)))
    (bind gsc (- (+ 0.4 (* 1.0 gin)) (* 0.4 gset)))
    (Widget|Transform|SetRenderScale :self {HV('MoneyPop')} :Scale (Math|Vector2D|MakeVector2D gsc gsc))
    (Widget|Transform|SetRenderTranslation :self {HV('MoneyPop')} :Translation (Math|Vector2D|MakeVector2D 0.0 (* -90.0 (CallFunction|Ease :V (/ gt 2.0)))))
    (Widget|SetRenderOpacity :self {HV('MoneyPop')} :InOpacity (* gin (- 1.0 (CallFunction|Ease :V (/ (- gt 1.3) 0.7)))))
    (bind gfl (CallFunction|Ease :V (/ gt 0.55)))
    (bind gfs (+ 1.0 (* 0.55 gfl)))
    (Widget|Transform|SetRenderScale :self {HV('TxtMoneyGlow')} :Scale (Math|Vector2D|MakeVector2D gfs gfs))
    (Widget|SetRenderOpacity :self {HV('TxtMoneyGlow')} :InOpacity (- 1.0 gfl))
    (else
      (Widget|SetVisibility :self {HV('MoneyPop')} :InVisibility "Hidden")))
  ; blindfold countdown heartbeat
  (bind bp (+ 1.0 (* 0.05 (Math|Float|Max(Float) 0.0 (Math|Trig|Sin(Radians) (* t 6.28))))))
  (Widget|Transform|SetRenderScale :self {HV('BlindText')} :Scale (Math|Vector2D|MakeVector2D bp bp))
  ; bomb defusing ring (detective holding E)
  (CallFunction|DefuseHudTick)
  ; FOV preference (twice a second)
  (if (Utilities|HasLaunchOption :OptionToCheck "GWShot")
    (CallFunction|ShotTick :GS GS :PS PS))
  (if (> (- t (Variables|UI|GetFovAt)) 0.5)
    (Variables|UI|SetFovAt t)
    (CallFunction|ApplyFov)))
'''
    shot = '(Development|ExecuteConsoleCommand :Command "Shot showui" :SpecificPlayer (Widget|GetOwningPlayer))'
    G['ShotTick'] = f'''
(fn ShotTick (GS PS)
  (bind t (Variables|UI|GetT))
  (bind st (Variables|UI|GetShotStep))
  (bind phase {gs('Phase')})
  (bind rem (- {gs('PhaseEndTime')} (GameState|GetServerWorldTimeSeconds :self GS)))
  (bind ct (Variables|UI|GetCardT))
  (if (and (== st 0) (and (== phase 0) (> t 6.0)))
    {shot}
    (Variables|UI|SetShotStep 1)
    (return))
  (if (and (<= st 1) (and (== phase 1) (> ct 1.3)))
    {shot}
    (Variables|UI|SetShotStep 2)
    (return))
  (if (and (== st 2) (and (== phase 1) (> ct 4.8)))
    {shot}
    (Variables|UI|SetShotStep 3)
    (return))
  (if (and (<= st 3) (and (== phase 2) (> (- (Variables|UI|GetPhaseDur) rem) 4.0)))
    {shot}
    (Variables|UI|SetShotAt t)
    (Variables|UI|SetShotStep 30)
    (return))
  (if (and (== st 30) (> t (+ (Variables|UI|GetShotAt) 1.0)))
    (CallFunction|TogglePause)
    (Variables|UI|SetShotAt t)
    (Variables|UI|SetShotStep 4)
    (return))
  (if (and (== st 4) (> t (+ (Variables|UI|GetShotAt) 1.2)))
    {shot}
    (Variables|UI|SetShotStep 5)
    (return))
  (if (and (== st 5) (> t (+ (Variables|UI|GetShotAt) 2.2)))
    (CallFunction|TogglePause)
    (Variables|UI|SetShotStep 6)
    (return))
  (if (and (== st 6) (and (== phase 2) (<= rem 27.0)))
    {shot}
    (Variables|UI|SetShotStep 7)
    (return))
  (if (and (>= st 6) (and (< st 8) (and (== phase 3) (> (Variables|UI|GetEndT) 1.8))))
    {shot}
    (Variables|UI|SetShotStep 8)
    (Variables|UI|SetShotAt t)
    (return))
  (if (and (== st 8) (> t (+ (Variables|UI|GetShotAt) 1.5)))
    (Variables|UI|SetShotStep 9)
    (Game|QuitGame :SpecificPlayer (Widget|GetOwningPlayer) :QuitPreference "Quit" :bIgnorePlatformRestrictions false)))
'''
    G['DefuseHudTick'] = f'''
(fn DefuseHudTick ()
  (bind pc (Utilities|Casting|CastToBP_GW_PlayerController (Widget|GetOwningPlayer))
    (:then
      (bind on (GW|Get|BP_GW_PlayerController|DefuseHold :self pc))
      (bind p (GW|Get|BP_GW_PlayerController|DefuseProgress :self pc))
      (CallFunction|ShowW :W {HV('DefuseRing')} :Show on)
      (if on
        {txt('TxtDefuse', '(cat "DÉSAMORÇAGE  " (Math|Float|Truncate (* p 100.0)) " %   ·   relâcher E annule")')}
        (Class|Image|SetColorandOpacity :self {HV('DefDot0')} :ColorAndOpacity (select (> p 0.0312) (Math|Color|MakeColor 1.0 0.86 0.45 1.0) (Math|Color|MakeColor 0.32 0.05 0.04 0.55)))
        (Class|Image|SetColorandOpacity :self {HV('DefDot1')} :ColorAndOpacity (select (> p 0.0938) (Math|Color|MakeColor 1.0 0.86 0.45 1.0) (Math|Color|MakeColor 0.32 0.05 0.04 0.55)))
        (Class|Image|SetColorandOpacity :self {HV('DefDot2')} :ColorAndOpacity (select (> p 0.1562) (Math|Color|MakeColor 1.0 0.86 0.45 1.0) (Math|Color|MakeColor 0.32 0.05 0.04 0.55)))
        (Class|Image|SetColorandOpacity :self {HV('DefDot3')} :ColorAndOpacity (select (> p 0.2188) (Math|Color|MakeColor 1.0 0.86 0.45 1.0) (Math|Color|MakeColor 0.32 0.05 0.04 0.55)))
        (Class|Image|SetColorandOpacity :self {HV('DefDot4')} :ColorAndOpacity (select (> p 0.2812) (Math|Color|MakeColor 1.0 0.86 0.45 1.0) (Math|Color|MakeColor 0.32 0.05 0.04 0.55)))
        (Class|Image|SetColorandOpacity :self {HV('DefDot5')} :ColorAndOpacity (select (> p 0.3438) (Math|Color|MakeColor 1.0 0.86 0.45 1.0) (Math|Color|MakeColor 0.32 0.05 0.04 0.55)))
        (Class|Image|SetColorandOpacity :self {HV('DefDot6')} :ColorAndOpacity (select (> p 0.4062) (Math|Color|MakeColor 1.0 0.86 0.45 1.0) (Math|Color|MakeColor 0.32 0.05 0.04 0.55)))
        (Class|Image|SetColorandOpacity :self {HV('DefDot7')} :ColorAndOpacity (select (> p 0.4688) (Math|Color|MakeColor 1.0 0.86 0.45 1.0) (Math|Color|MakeColor 0.32 0.05 0.04 0.55)))
        (Class|Image|SetColorandOpacity :self {HV('DefDot8')} :ColorAndOpacity (select (> p 0.5312) (Math|Color|MakeColor 1.0 0.86 0.45 1.0) (Math|Color|MakeColor 0.32 0.05 0.04 0.55)))
        (Class|Image|SetColorandOpacity :self {HV('DefDot9')} :ColorAndOpacity (select (> p 0.5938) (Math|Color|MakeColor 1.0 0.86 0.45 1.0) (Math|Color|MakeColor 0.32 0.05 0.04 0.55)))
        (Class|Image|SetColorandOpacity :self {HV('DefDot10')} :ColorAndOpacity (select (> p 0.6562) (Math|Color|MakeColor 1.0 0.86 0.45 1.0) (Math|Color|MakeColor 0.32 0.05 0.04 0.55)))
        (Class|Image|SetColorandOpacity :self {HV('DefDot11')} :ColorAndOpacity (select (> p 0.7188) (Math|Color|MakeColor 1.0 0.86 0.45 1.0) (Math|Color|MakeColor 0.32 0.05 0.04 0.55)))
        (Class|Image|SetColorandOpacity :self {HV('DefDot12')} :ColorAndOpacity (select (> p 0.7812) (Math|Color|MakeColor 1.0 0.86 0.45 1.0) (Math|Color|MakeColor 0.32 0.05 0.04 0.55)))
        (Class|Image|SetColorandOpacity :self {HV('DefDot13')} :ColorAndOpacity (select (> p 0.8438) (Math|Color|MakeColor 1.0 0.86 0.45 1.0) (Math|Color|MakeColor 0.32 0.05 0.04 0.55)))
        (Class|Image|SetColorandOpacity :self {HV('DefDot14')} :ColorAndOpacity (select (> p 0.9062) (Math|Color|MakeColor 1.0 0.86 0.45 1.0) (Math|Color|MakeColor 0.32 0.05 0.04 0.55)))
        (Class|Image|SetColorandOpacity :self {HV('DefDot15')} :ColorAndOpacity (select (> p 0.9688) (Math|Color|MakeColor 1.0 0.86 0.45 1.0) (Math|Color|MakeColor 0.32 0.05 0.04 0.55)))
        (bind ps (+ 1.0 (* 0.05 (Math|Trig|Sin(Radians) (* (Variables|UI|GetT) (+ 8.0 (* p 14.0)))))))
        (Widget|Transform|SetRenderScale :self {HV('DefuseRing')} :Scale (Math|Vector2D|MakeVector2D ps ps))))
    (:CastFailed)))
'''
    G['EventGraph'] = '''
(event UserInterface|EventConstruct
  (CallFunction|SetupHUD))

(event UserInterface|EventTick (MyGeometry InDeltaTime)
  (CallFunction|StyleTick :Dt InDeltaTime))
'''
    only = UE_ARGS[1] if len(UE_ARGS) > 1 else None
    for name, code in G.items():
        if only and name != only:
            continue
        write(W, name, code, compile_after=False)
        print('wrote', name)
    compile_bp(W)
    print(node_problems(W))
    compile_widget(W)


if which in ('all', 'tree'):
    build_tree()
if which in ('all', 'graph'):
    build_graph()
