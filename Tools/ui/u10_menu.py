"""WBP_MainMenu rebuilt: parallax ballroom + drapes + gold dust, logo intro, Art Deco buttons (hover scale + sounds),
name field, Héberger / Rejoindre (IP) / Options / Comment jouer / Quitter, « Connexion… » overlay, error panel, menu music.
Keeps the widget names the old graphs used (NameBox, IpBox, TxtStatus, BtnHost, BtnJoin, BtnQuit).
UE_ARGS: 'tree' | 'graph' | 'all' (default)."""
import sys
sys.path.insert(0, r'J:\Projets\Unreal_Projects\Guess Who\Tools\ui')
import importlib, uilib, uianim
importlib.reload(uilib); importlib.reload(uianim)
from uilib import *

which = UE_ARGS[0] if UE_ARGS else 'all'
W = get_or_create('WBP_MainMenu')
for stub in ('WBP_Options', 'WBP_HowTo'):
    s = get_or_create(stub)
    if 'Root' not in infos(s):
        add(s, unreal.CanvasPanel, 'Root'); compile_widget(s)

HAS_LOGO = EAL.does_asset_exist(f'{TEX}/T_UI_Logo')
BUTTONS = [('BtnHost', 'HÉBERGER UNE PARTIE'), ('BtnJoinOpen', 'REJOINDRE UNE PARTIE'), ('BtnOptions', 'OPTIONS'),
           ('BtnHowTo', 'COMMENT JOUER'), ('BtnQuit', 'QUITTER')]
MOTES = 18


def big_button(name, label, parent, width=470, height=66, size=27):
    sb = add(W, unreal.SizeBox, name + 'Box', parent)
    size_box(sb, w=width, h=height)
    b = add(W, unreal.Button, name, name + 'Box', var=True)
    button_style(b)
    t = add(W, unreal.TextBlock, name + 'Text', name)
    text(t, label, 'Display', 'Regular', size, IVORY, spacing=260, just='center', shadow=True)
    return sb


def build_tree():
    clear_tree(W)
    add(W, unreal.CanvasPanel, 'Root')
    # far layer: ballroom
    bs = add(W, unreal.ScaleBox, 'BgScale', 'Root'); canvas(bs, FILL, z=0)
    bs.widget.set_editor_property('stretch', unreal.Stretch.SCALE_TO_FILL)
    bg = add(W, unreal.Image, 'BgImage', 'BgScale', var=True); image(bg, 'T_UI_BgBallroom', (1920, 1088), tint=(0.78, 0.74, 0.70, 1)); pivot(bg)
    # gold dust
    d = add(W, unreal.CanvasPanel, 'Dust', 'Root', var=True); canvas(d, FILL, z=1)
    d.widget.set_editor_property('visibility', V.HIT_TEST_INVISIBLE)
    import random
    rnd = random.Random(7)
    for i in range(MOTES):
        m = add(W, unreal.Image, f'Mote{i}', 'Dust')
        sz = rnd.uniform(8, 26)
        image(m, 'T_UI_Glow', (sz, sz), tint=(1.0, 0.78, 0.42, 1))
        canvas(m, ((rnd.uniform(0.18, 0.98), rnd.uniform(0.45, 1.0)),) * 2, (0.5, 0.5), (0, 0), (sz, sz), auto=False)
    # near layer: velvet drapes
    ds = add(W, unreal.ScaleBox, 'DrapeScale', 'Root'); canvas(ds, FILL, z=2)
    ds.widget.set_editor_property('stretch', unreal.Stretch.SCALE_TO_FILL)
    ds.widget.set_editor_property('visibility', V.HIT_TEST_INVISIBLE)
    dr = add(W, unreal.Image, 'Drapes', 'DrapeScale', var=True); image(dr, 'T_UI_Drapes', (1920, 1088), tint=(0.62, 0.58, 0.56, 1)); pivot(dr)
    vg = add(W, unreal.Image, 'Vignette', 'Root'); image(vg, 'T_UI_Vignette', (512, 288), tint=(0, 0, 0, 0.92)); canvas(vg, FILL, z=3)
    vg.widget.set_editor_property('visibility', V.HIT_TEST_INVISIBLE)
    sh = add(W, unreal.Image, 'LeftShade', 'Root'); image(sh, 'T_UI_ShadeLeft', (512, 64), tint=(0, 0, 0, 0.88))
    canvas(sh, ((0, 0), (0, 1)), (0, 0), (0, 0), (980, 0), z=3)
    sh.widget.set_editor_property('visibility', V.HIT_TEST_INVISIBLE)
    # menu column
    col = add(W, unreal.VerticalBox, 'MenuCol', 'Root', var=True)
    canvas(col, ((0, 0.5), (0, 0.5)), (0, 0.5), (170, 10), auto=True, z=5)
    lb = add(W, unreal.SizeBox, 'LogoBox', 'MenuCol'); size_box(lb, w=620, h=277); box_slot(lb, (0, 0, 0, 0), H.H_ALIGN_CENTER)
    lo = add(W, unreal.Overlay, 'LogoOverlay', 'LogoBox')
    lsh = add(W, unreal.Image, 'LogoShade', 'LogoOverlay'); image(lsh, 'T_UI_Glow', (128, 128), tint=(0, 0, 0, 0.92))
    overlay_slot(lsh, H.H_ALIGN_FILL, VA.V_ALIGN_FILL); pivot(lsh)
    lsh.widget.set_editor_property('render_transform', unreal.WidgetTransform(unreal.Vector2D(0, 0), unreal.Vector2D(2.1, 2.0), unreal.Vector2D(0, 0), 0.0))
    li = add(W, unreal.Image, 'LogoImg', 'LogoOverlay', var=True); pivot(li)
    if HAS_LOGO:
        image(li, 'T_UI_Logo', (620, 277))
    overlay_slot(li, H.H_ALIGN_FILL, VA.V_ALIGN_FILL)
    lt = add(W, unreal.TextBlock, 'LogoText', 'LogoOverlay', var=True)
    text(lt, 'LE BAL\nMASQUÉ', 'Display', 'Regular', 104, GOLD_HI, spacing=420, just='center', outline=0)
    overlay_slot(lt, H.H_ALIGN_CENTER, VA.V_ALIGN_CENTER)
    vis(li, V.HIT_TEST_INVISIBLE if HAS_LOGO else V.COLLAPSED)
    vis(lt, V.COLLAPSED if HAS_LOGO else V.HIT_TEST_INVISIBLE)
    st = add(W, unreal.TextBlock, 'Subtitle', 'MenuCol', var=True)
    text(st, 'MANOIR ASHCOMBE  ·  1932', 'Display', 'Regular', 21, IVORY, spacing=520, just='center')
    box_slot(st, (0, 14, 0, 6), H.H_ALIGN_CENTER)
    dv = add(W, unreal.Spacer, 'ColSpacer', 'MenuCol'); dv.widget.set_editor_property('size', unreal.Vector2D(1, 16))
    ln = add(W, unreal.TextBlock, 'LblName', 'MenuCol'); text(ln, 'VOTRE NOM DE CONVIVE', 'Display', 'Regular', 17, GOLD, spacing=420, just='center')
    box_slot(ln, (0, 2, 0, 8), H.H_ALIGN_CENTER)
    nbx = add(W, unreal.SizeBox, 'NameBoxSize', 'MenuCol'); size_box(nbx, w=470); box_slot(nbx, (0, 0, 0, 18), H.H_ALIGN_CENTER)
    nb = add(W, unreal.EditableTextBox, 'NameBox', 'NameBoxSize', var=True); textbox_style(nb, 21)
    nb.widget.set_editor_property('hint_text', unreal.Text('Votre nom'))
    nb.widget.set_editor_property('justification', unreal.TextJustify.CENTER)
    for name, label in BUTTONS:
        sb = big_button(name, label, 'MenuCol')
        box_slot(sb, (0, 5, 0, 5), H.H_ALIGN_CENTER)
        if name == 'BtnJoinOpen':
            jp = add(W, unreal.HorizontalBox, 'JoinPanel', 'MenuCol', var=True); box_slot(jp, (0, 4, 0, 8), H.H_ALIGN_CENTER)
            ipsz = add(W, unreal.SizeBox, 'IpBoxSize', 'JoinPanel'); size_box(ipsz, w=300, h=56); box_slot(ipsz, (0, 0, 10, 0), H.H_ALIGN_FILL)
            ip = add(W, unreal.EditableTextBox, 'IpBox', 'IpBoxSize', var=True); textbox_style(ip, 21)
            ip.widget.set_editor_property('hint_text', unreal.Text("Code de partie ou adresse IP"))
            ip.widget.set_editor_property('text', unreal.Text(''))
            jb = big_button('BtnJoin', 'ENTRER', 'JoinPanel', width=160, height=56, size=24)
            box_slot(jb, (0, 0, 0, 0), H.H_ALIGN_FILL)
            vis(jp, V.COLLAPSED)
    ts = add(W, unreal.TextBlock, 'TxtStatus', 'MenuCol', var=True)
    text(ts, '', 'Serif', 'Italic', 19, IVORY, just='center', wrap=520); box_slot(ts, (0, 10, 0, 0), H.H_ALIGN_CENTER)
    # footer
    ft = add(W, unreal.TextBlock, 'Footer', 'Root')
    text(ft, "Partie en réseau local ou par Internet  ·  l'hôte ouvre le port 7777/UDP  ·  2 à 10 joueurs", 'Sans', 'Regular', 15,
         IVORY_DIM, just='right')
    canvas(ft, ((1, 1), (1, 1)), (1, 1), (-44, -26), auto=True, z=5)
    # error panel
    ep = add(W, unreal.Border, 'ErrorPanel', 'Root', var=True)
    border_brush(ep, 'T_UI_Panel', 0.25, tint=(1.0, 0.55, 0.5, 0.97), pad=(46, 26, 30, 26), size=(128, 128))
    canvas(ep, ((0.66, 0), (0.66, 0)), (0.5, 0), (0, 40), auto=True, z=8)
    eh = add(W, unreal.HorizontalBox, 'ErrorRow', 'ErrorPanel')
    ei = add(W, unreal.Image, 'ErrorIcon', 'ErrorRow'); image(ei, 'T_UI_IcoMask', (44, 44)); box_slot(ei, (0, 0, 18, 0), H.H_ALIGN_LEFT, VA.V_ALIGN_CENTER)
    et = add(W, unreal.TextBlock, 'TxtError', 'ErrorRow', var=True)
    text(et, '', 'Serif', 'Regular', 20, IVORY, wrap=720); box_slot(et, (0, 0, 16, 0), H.H_ALIGN_FILL, VA.V_ALIGN_CENTER)
    ec = add(W, unreal.Button, 'BtnErrClose', 'ErrorRow', var=True); flat_button(ec, press_snd='S_UI_Back')
    box_slot(ec, (0, 0, 0, 0), H.H_ALIGN_RIGHT, VA.V_ALIGN_CENTER)
    ect = add(W, unreal.TextBlock, 'BtnErrCloseText', 'BtnErrClose'); text(ect, '×', 'Serif', 'Regular', 34, GOLD_HI, just='center')
    vis(ep, V.COLLAPSED)
    # connecting overlay
    ov = add(W, unreal.Overlay, 'ConnectOverlay', 'Root', var=True); canvas(ov, FILL, z=10)
    cs = add(W, unreal.ScaleBox, 'ConnArtScale', 'ConnectOverlay'); cs.widget.set_editor_property('stretch', unreal.Stretch.SCALE_TO_FILL)
    overlay_slot(cs)
    ca = add(W, unreal.Image, 'ConnArt', 'ConnArtScale', var=True); image(ca, 'T_UI_Arrival', (1920, 1088), tint=(0.5, 0.48, 0.47, 1)); pivot(ca)
    cv = add(W, unreal.Image, 'ConnVignette', 'ConnectOverlay'); image(cv, 'T_UI_Vignette', (512, 288), tint=(0, 0, 0, 0.95)); overlay_slot(cv)
    cb = add(W, unreal.Image, 'ConnBand', 'ConnectOverlay'); image(cb, 'T_UI_FadeBar', (512, 420), tint=(0, 0, 0, 0.9))
    overlay_slot(cb, H.H_ALIGN_FILL, VA.V_ALIGN_BOTTOM, (0, 0, 0, 0))
    cbs = add(W, unreal.SizeBox, 'ConnBandSize', 'ConnectOverlay'); size_box(cbs, h=300); overlay_slot(cbs, H.H_ALIGN_FILL, VA.V_ALIGN_BOTTOM, (0, 0, 0, 40))
    cvb = add(W, unreal.VerticalBox, 'ConnBox', 'ConnBandSize')
    sp = add(W, unreal.Overlay, 'Spinner', 'ConnBox'); box_slot(sp, (0, 0, 0, 10), H.H_ALIGN_CENTER)
    sd = add(W, unreal.Image, 'SpinDial', 'Spinner'); image(sd, 'T_UI_Dial', (92, 92))
    sdh = add(W, unreal.Image, 'SpinHand', 'Spinner', var=True); image(sdh, 'T_UI_DialHand', (92, 92)); pivot(sdh)
    ct = add(W, unreal.TextBlock, 'TxtConnTitle', 'ConnBox', var=True)
    text(ct, 'CONNEXION', 'Display', 'Regular', 46, GOLD_HI, spacing=700, just='center'); box_slot(ct, (0, 0, 0, 2), H.H_ALIGN_CENTER)
    cx = add(W, unreal.TextBlock, 'TxtConn', 'ConnBox', var=True)
    text(cx, '', 'Serif', 'Italic', 23, IVORY, just='center'); box_slot(cx, (0, 0, 0, 14), H.H_ALIGN_CENTER)
    cc = big_button('BtnCancel', 'ANNULER', 'ConnBox', width=260, height=56, size=24); box_slot(cc, (0, 0, 0, 0), H.H_ALIGN_CENTER)
    vis(ov, V.COLLAPSED)
    compile_widget(W)
    print('menu tree:', len(infos(W)), 'widgets')


ISVALID = 'GW|Call|/Script/Engine.KismetSystemLibrary|IsValid'
GI_C = 'BP_GW_GameInstance'


def build_graph():
    uianim.install(W)
    ensure_var(W, 'Px', 'float', category='UI'); ensure_var(W, 'Py', 'float', category='UI')
    ensure_var(W, 'PendingAction', 'int', category='UI'); ensure_var(W, 'PendingAt', 'float', category='UI')
    ensure_var(W, 'PendingCmd', 'string', category='UI')
    ensure_var(W, 'Music', obj_class=unreal.AudioComponent, category='UI')
    ensure_var(W, 'Motes', obj_class=unreal.Widget, array=True, category='UI')
    ensure_var(W, 'SubW', obj_class=unreal.UserWidget, category='UI')
    ensure_var(W, 'ShotStep', 'int', category='UI')
    ensure_var(W, 'AutoDone', 'bool', category='UI')
    ensure_fn(W, 'HostOpts', outputs=[('Out', 'string')])
    for fn, ins in [('OnHostAsk', []), ('GetCleanName', []), ('StoreName', []), ('OnHostClicked', []), ('OnJoinClicked', []), ('OnQuitClicked', []),
                    ('OnJoinOpenClicked', []), ('OnOptionsClicked', []), ('OnHowToClicked', []), ('OnCancelClicked', []),
                    ('OnErrCloseClicked', []), ('ShowConnecting', [('Title', 'string'), ('Line', 'string')]), ('MenuTick', [('Dt', 'float')]),
                    ('SetupMenu', []), ('ShowError', [('Msg', 'string')]), ('ShotTick', []), ('CloseSub', []),
                    ('OnTyped', [('Text', 'text')])]:
        ensure_fn(W, fn, inputs=ins, outputs=[('Name', 'string')] if fn == 'GetCleanName' else [])
    compile_bp(W, quiet=True)
    uianim.write_all(W)
    MV = lambda n: f'(Variables|WBP_MainMenu|Get{n})'
    G = {}
    G['GetCleanName'] = f'''
(fn GetCleanName ()
  (bind raw (Utilities|String|Trim :SourceString (Utilities|String|ToString(Text) (Widget|GetText(TextBox) :self {MV('NameBox')}))))
  (bind c1 (Utilities|String|Replace :SourceString raw :From " " :To "_"))
  (bind c2 (Utilities|String|Replace :SourceString c1 :From "?" :To ""))
  (bind c3 (Utilities|String|Replace :SourceString c2 :From "=" :To ""))
  (bind c4 (Utilities|String|Replace :SourceString c3 :From "#" :To ""))
  (bind c5 (Utilities|String|Left :SourceString c4 :Count 20))
  (return (select (== (Utilities|String|Len c5) 0) (cat "Convive" (Math|Random|RandomIntegerinRange :Min 100 :Max 999)) c5)))
'''
    G['StoreName'] = '''
(fn StoreName ()
  (bind gi (Utilities|Casting|CastToBP_GW_GameInstance (Widget|GetGameInstance))
    (:then (GW|Set|BP_GW_GameInstance|PlayerName :self gi :PlayerName (CallFunction|GetCleanName)))
    (:CastFailed)))
'''
    G['ShowConnecting'] = f'''
(fn ShowConnecting (Title Line)
  (Widget|SetText(Text) :self {MV('TxtConnTitle')} :InText (Utilities|Text|ToText(String) Title))
  (Widget|SetText(Text) :self {MV('TxtConn')} :InText (Utilities|Text|ToText(String) Line))
  (Widget|SetVisibility :self {MV('ConnectOverlay')} :InVisibility "Visible")
  (Widget|SetRenderOpacity :self {MV('ConnectOverlay')} :InOpacity 0.0)
  (Audio|PlaySound2D :Sound "/Game/GW/Audio/S_UI_Confirm.S_UI_Confirm")
  (bind mus (Variables|UI|GetMusic))
  (if ({ISVALID} :Object mus)
    (GW|Call|/Script/Engine.AudioComponent|FadeOut :self mus :FadeOutDuration 1.2 :FadeVolumeLevel 0.0)))
'''
    SET_ = '/Game/GW/UI/BP_GW_Settings.BP_GW_Settings_C'
    S_ = lambda v: f'(GW|Get|{SET_}|{v} :self s)'
    # the game parameters saved by the setup screen (Tools/ui/u19_game_setup.py) become travel options: BP_GW_GameMode.ApplyOptions reads them
    G['HostOpts'] = f'''
(fn HostOpts ()
  (bind gi (Utilities|Casting|CastToBP_GW_GameInstance (Widget|GetGameInstance))
    (:then
      (bind s (GW|Call|BP_GW_GameInstance|GWSettings :self gi))
      (return (cat (cat "?NPCs=" {S_('GNPCs')} "?HuntTime=" {S_('GHunt')} "?HideTime=" {S_('GHide')}) (cat "?MaxRounds=" {S_('GRounds')}) (cat "?AutoEvents=" {S_('GAutoEv')} "?EventEvery=" {S_('GEventEvery')}) (cat "?MinPlayers=" {S_('GMinPlayers')} "?LobbyTime=" {S_('GLobby')}))))
    (:CastFailed
      (return ""))))
'''
    G['OnHostAsk'] = '''
(fn OnHostAsk ()
  (CallFunction|StoreName)
  (bind w (UserInterface|CreateWidget :Class "/Game/GW/UI/WBP_GameSetup.WBP_GameSetup_C" :OwningPlayer (Widget|GetOwningPlayer)))
  (Variables|UI|SetSubW w)
  (UserInterface|Viewport|AddtoViewport :self w :ZOrder 20)
  (bind sw (Utilities|Casting|CastToWBP_GameSetup w)
    (:then (GW|Set|/Game/GW/UI/WBP_GameSetup.WBP_GameSetup_C|MenuW :self sw :MenuW self))
    (:CastFailed)))
'''
    G['OnHostClicked'] = '''
(fn OnHostClicked ()
  (CallFunction|StoreName)
  (CallFunction|ShowConnecting :Title "OUVERTURE DU MANOIR" :Line "Les chandelles s'allument, les invités arrivent…")
  (Variables|UI|SetPendingCmd (cat "listen?Name=" (CallFunction|GetCleanName) (CallFunction|HostOpts)))
  (Variables|UI|SetPendingAction 1)
  (Variables|UI|SetPendingAt (+ (Utilities|Time|GetRealTimeSeconds) 0.9)))
'''
    G['OnJoinClicked'] = f'''
(fn OnJoinClicked ()
  (bind ip (Utilities|String|Trim :SourceString (Utilities|String|ToString(Text) (Widget|GetText(TextBox) :self {MV('IpBox')}))))
  (bind host (select (== (Utilities|String|Len ip) 0) "127.0.0.1" ip))
  (CallFunction|StoreName)
  (CallFunction|ShowConnecting :Title "CONNEXION" :Line (cat "Connexion au manoir de l'hôte (" host ")…"))
  ; 6 letters or digits = a game code (Source/GuessWho/GWOnline.cpp), anything else = an address
  (if (GWOnline|GWIsGameCode :Text ip)
    (Variables|UI|SetPendingCmd ip)
    (Variables|UI|SetPendingAction 3)
    (else
      (Variables|UI|SetPendingCmd (cat "open " host "?Name=" (CallFunction|GetCleanName)))
      (Variables|UI|SetPendingAction 2)))
  (Variables|UI|SetPendingAt (+ (Utilities|Time|GetRealTimeSeconds) 0.6)))
'''
    G['OnCancelClicked'] = f'''
(fn OnCancelClicked ()
  (bind pa (Variables|UI|GetPendingAction))
  (Variables|UI|SetPendingAction 0)
  (GWOnline|GWCancelOnline)
  (if (== pa 0)
    (Development|ExecuteConsoleCommand :Command "disconnect" :SpecificPlayer (Widget|GetOwningPlayer)))
  (Widget|SetVisibility :self {MV('ConnectOverlay')} :InVisibility "Collapsed")
  (Audio|PlaySound2D :Sound "/Game/GW/Audio/S_UI_Back.S_UI_Back")
  (bind mus (Variables|UI|GetMusic))
  (if ({ISVALID} :Object mus)
    (GW|Call|/Script/Engine.AudioComponent|FadeIn :self mus :FadeInDuration 1.5 :FadeVolumeLevel 1.0 :StartTime 0.0)))
'''
    G['OnQuitClicked'] = '''
(fn OnQuitClicked ()
  (Game|QuitGame :SpecificPlayer (Widget|GetOwningPlayer) :QuitPreference "Quit" :bIgnorePlatformRestrictions false))
'''
    G['OnJoinOpenClicked'] = f'''
(fn OnJoinOpenClicked ()
  (bind jp {MV('JoinPanel')})
  (if (Widget|IsVisible :self jp)
    (Widget|SetVisibility :self jp :InVisibility "Collapsed")
    (else
      (Widget|SetVisibility :self jp :InVisibility "Visible")
      (Widget|SetKeyboardFocus :self {MV('IpBox')}))))
'''
    sub = lambda cls: f'''
  (bind w (UserInterface|CreateWidget :Class "/Game/GW/UI/{cls}.{cls}_C" :OwningPlayer (Widget|GetOwningPlayer)))
  (Variables|UI|SetSubW w)
  (UserInterface|Viewport|AddtoViewport :self w :ZOrder 20))
'''
    G['OnOptionsClicked'] = '(fn OnOptionsClicked ()' + sub('WBP_Options')
    G['OnHowToClicked'] = '(fn OnHowToClicked ()' + sub('WBP_HowTo')
    G['OnErrCloseClicked'] = f'''
(fn OnErrCloseClicked ()
  (Widget|SetVisibility :self {MV('ErrorPanel')} :InVisibility "Collapsed"))
'''
    G['ShowError'] = f'''
(fn ShowError (Msg)
  (if (> (Utilities|String|Len Msg) 0)
    (Widget|SetText(Text) :self {MV('TxtError')} :InText (Utilities|Text|ToText(String) Msg))
    (Widget|SetVisibility :self {MV('ErrorPanel')} :InVisibility "Visible")
    (else
      (Widget|SetVisibility :self {MV('ErrorPanel')} :InVisibility "Collapsed"))))
'''
    btn_regs = '\n'.join(f'  (CallFunction|AddBtn :B {MV(n)})' for n, _ in BUTTONS + [('BtnJoin', ''), ('BtnCancel', '')])
    G['SetupMenu'] = f'''
(fn SetupMenu ()
  (Variables|UI|SetT 0.0)
  (Variables|UI|SetPendingAction 0)
  (Utilities|Array|Clear (Variables|UI|GetBtns))
  (Utilities|Array|Clear (Variables|UI|GetBtnHov))
{btn_regs}
  (Variables|UI|SetMotes (Widget|Panel|GetAllChildren :self {MV('Dust')}))
  (Widget|SetVisibility :self {MV('ConnectOverlay')} :InVisibility "Collapsed")
  (bind mus (Audio|CreateSound2D :Sound "/Game/GW/Audio/MUS_Menu.MUS_Menu" :VolumeMultiplier 1.0 :PitchMultiplier 1.0 :StartTime 0.0 :bPersistAcrossLevelTransition false :bAutoDestroy false))
  (Variables|UI|SetMusic mus)
  (if ({ISVALID} :Object mus)
    (GW|Call|/Script/Engine.AudioComponent|FadeIn :self mus :FadeInDuration 3.0 :FadeVolumeLevel 1.0 :StartTime 0.0))
  (bind gi (Utilities|Casting|CastToBP_GW_GameInstance (Widget|GetGameInstance))
    (:then
      (GW|Call|BP_GW_GameInstance|GWApplyAudio :self gi)
      (bind nm (GW|Get|BP_GW_GameInstance|PlayerName :self gi))
      (Widget|SetText(TextBox) :self {MV('NameBox')} :InText (Utilities|Text|ToText(String) (select (> (Utilities|String|Len nm) 0) nm (cat "Convive" (Math|Random|RandomIntegerinRange :Min 100 :Max 999)))))
      (CallFunction|ShowError :Msg (GW|Get|BP_GW_GameInstance|LastError :self gi))
      (GW|Set|BP_GW_GameInstance|LastError :self gi :LastError ""))
    (:CastFailed)))
'''
    # slide-in per element of the menu column (stagger by index), logo intro, parallax, dust, spinner, pending travel
    G['MenuTick'] = f'''
(fn MenuTick (Dt)
  (bind t (+ (Variables|UI|GetT) Dt))
  (Variables|UI|SetT t)
  ; logo intro: fade + settle
  (bind e (CallFunction|Ease :V (/ (- t 0.15) 1.6)))
  (bind lg {MV('LogoImg')})
  (Widget|SetRenderOpacity :self lg :InOpacity e)
  (Widget|SetRenderOpacity :self {MV('LogoText')} :InOpacity e)
  (bind ls (+ 1.0 (* 0.07 (- 1.0 e))))
  (Widget|Transform|SetRenderScale :self lg :Scale (Math|Vector2D|MakeVector2D ls ls))
  ; staggered slide-in of the column children
  (bind kids (Widget|Panel|GetAllChildren :self {MV('MenuCol')}))
  (for i (range (Utilities|Array|Length kids))
    (if (> i 0)
      (bind k (Utilities|Array|Get(acopy) kids i))
      (bind ke (CallFunction|Ease :V (/ (- t (+ 0.55 (* i 0.07))) 0.55)))
      (Widget|SetRenderOpacity :self k :InOpacity ke)
      (Widget|Transform|SetRenderTranslation :self k :Translation (Math|Vector2D|MakeVector2D (* -46.0 (- 1.0 ke)) 0.0))))
  ; parallax from the mouse
  (bind sc (Math|Float|Max(Float) (Viewport|GetViewportScale) 0.01))
  (bind vs (Viewport|GetViewportSize))
  (bind (vx vy) (Math|Vector2D|BreakVector2D vs))
  (bind mp (Viewport|GetMousePositiononViewport))
  (bind (mx my) (Math|Vector2D|BreakVector2D mp))
  (bind nx (- (* 2.0 (CallFunction|C01 :V (/ (* mx sc) (Math|Float|Max(Float) vx 1.0)))) 1.0))
  (bind ny (- (* 2.0 (CallFunction|C01 :V (/ (* my sc) (Math|Float|Max(Float) vy 1.0)))) 1.0))
  (Variables|UI|SetPx (Math|Interpolation|FInterpTo :Current (Variables|UI|GetPx) :Target nx :DeltaTime Dt :InterpSpeed 2.2))
  (Variables|UI|SetPy (Math|Interpolation|FInterpTo :Current (Variables|UI|GetPy) :Target ny :DeltaTime Dt :InterpSpeed 2.2))
  (bind px (Variables|UI|GetPx))
  (bind py (Variables|UI|GetPy))
  (bind bz (+ 1.07 (* 0.012 (Math|Trig|Sin(Radians) (* t 0.17)))))
  (bind bg {MV('BgImage')})
  (Widget|Transform|SetRenderScale :self bg :Scale (Math|Vector2D|MakeVector2D bz bz))
  (Widget|Transform|SetRenderTranslation :self bg :Translation (Math|Vector2D|MakeVector2D (* px -20.0) (* py -11.0)))
  (bind dr {MV('Drapes')})
  (Widget|Transform|SetRenderScale :self dr :Scale (Math|Vector2D|MakeVector2D 1.06 1.06))
  (Widget|Transform|SetRenderTranslation :self dr :Translation (Math|Vector2D|MakeVector2D (* px -46.0) (+ (* py -14.0) (* 4.0 (Math|Trig|Sin(Radians) (* t 0.6))))))
  ; gold dust: rise, sway, fade
  (bind motes (Variables|UI|GetMotes))
  (for j (range (Utilities|Array|Length motes))
    (bind mo (Utilities|Array|Get(acopy) motes j))
    (bind spd (+ 0.035 (* 0.011 (% j 5))))
    (bind ph (Math|Float|Fraction (+ (* t spd) (* j 0.137))))
    (Widget|Transform|SetRenderTranslation :self mo :Translation (Math|Vector2D|MakeVector2D (+ (* px (* -30.0 (+ 0.5 (* 0.1 (% j 4))))) (* 16.0 (Math|Trig|Sin(Radians) (+ (* t 0.8) j)))) (* ph -340.0)))
    (Widget|SetRenderOpacity :self mo :InOpacity (* 0.75 (Math|Trig|Sin(Radians) (* ph 3.14159)))))
  (CallFunction|AnimButtons :Dt Dt)
  ; connecting overlay
  (bind ov {MV('ConnectOverlay')})
  (if (Widget|IsVisible :self ov)
    (Widget|SetRenderOpacity :self ov :InOpacity (Math|Interpolation|FInterpTo :Current (Widget|GetRenderOpacity :self ov) :Target 1.0 :DeltaTime Dt :InterpSpeed 5.0))
    (Widget|Transform|SetRenderTransformAngle :self {MV('SpinHand')} :Angle (* t 120.0))
    (bind ca {MV('ConnArt')})
    (bind cz (+ 1.02 (* 0.04 (CallFunction|C01 :V (* t 0.02)))))
    (Widget|Transform|SetRenderScale :self ca :Scale (Math|Vector2D|MakeVector2D cz cz)))
  ; deferred travel (lets the overlay draw before the blocking map load)
  ; pa is a pure getter, re-read at every use: branch on it BEFORE resetting it (resetting first sent the host
  ; command down the console path -> "Command not recognized: listen?Name=...")
  (bind pa (Variables|UI|GetPendingAction))
  (if (and (> pa 0) (>= (Utilities|Time|GetRealTimeSeconds) (Variables|UI|GetPendingAt)))
    (if (== pa 1)
      (Variables|UI|SetPendingAction 0)
      (GWOnline|GWHostGame :Options (Variables|UI|GetPendingCmd))
      (else
        (if (== pa 3)
          (Variables|UI|SetPendingAction 0)
          (GWOnline|GWJoinByCode :Code (Variables|UI|GetPendingCmd) :PlayerName (CallFunction|GetCleanName))
          (else
            (Variables|UI|SetPendingAction 0)
            (Development|ExecuteConsoleCommand :Command (Variables|UI|GetPendingCmd) :SpecificPlayer (Widget|GetOwningPlayer)))))))
  ; a code that found nothing
  (bind oe (GWOnline|GWConsumeError))
  (if (> (Utilities|String|Len oe) 0)
    (Widget|SetVisibility :self ov :InVisibility "Collapsed")
    (CallFunction|ShowError :Msg oe)))
'''
    G['OnTyped'] = '''
(fn OnTyped (Text)
  (Audio|PlaySound2D :Sound "/Game/GW/Audio/S_UI_Type.S_UI_Type" :VolumeMultiplier 0.6 :PitchMultiplier (Math|Random|RandomFloatinRange 0.92 1.08)))
'''
    G['CloseSub'] = f'''
(fn CloseSub ()
  (bind w (Variables|UI|GetSubW))
  (if ({ISVALID} :Object w)
    (Widget|RemovefromParent :self w)))
'''
    # dev hook: -GWShot takes HighResShot screenshots of every menu screen, then quits
    G['ShotTick'] = f'''
(fn ShotTick ()
  (bind t (Variables|UI|GetT))
  (bind st (Variables|UI|GetShotStep))
  (bind pc (Widget|GetOwningPlayer))
  (if (and (== st 0) (> t 4.0))
    (Development|ExecuteConsoleCommand :Command "Shot showui" :SpecificPlayer pc)
    (Variables|UI|SetShotStep 1)
    (return))
  (if (and (== st 1) (> t 5.0))
    (CallFunction|OnOptionsClicked)
    (Variables|UI|SetShotStep 2)
    (return))
  (if (and (== st 2) (> t 7.0))
    (Development|ExecuteConsoleCommand :Command "Shot showui" :SpecificPlayer pc)
    (Variables|UI|SetShotStep 3)
    (return))
  (if (and (== st 3) (> t 7.5))
    (CallFunction|CloseSub)
    (CallFunction|OnHowToClicked)
    (Variables|UI|SetShotStep 4)
    (return))
  (if (and (== st 4) (> t 9.5))
    (Development|ExecuteConsoleCommand :Command "Shot showui" :SpecificPlayer pc)
    (Variables|UI|SetShotStep 5)
    (return))
  (if (and (== st 5) (> t 10.0))
    (CallFunction|CloseSub)
    (CallFunction|ShowError :Msg "Impossible de rejoindre la partie : vérifiez le code. Par adresse IP, vérifiez aussi le port 7777/UDP.")
    (CallFunction|OnJoinOpenClicked)
    (Variables|UI|SetShotStep 6)
    (return))
  (if (and (== st 6) (> t 11.0))
    (Development|ExecuteConsoleCommand :Command "Shot showui" :SpecificPlayer pc)
    (Variables|UI|SetShotStep 7)
    (return))
  (if (and (== st 7) (> t 11.5))
    (CallFunction|ShowConnecting :Title "CONNEXION" :Line "Connexion au manoir de l'hôte (192.168.1.20)…")
    (Variables|UI|SetShotStep 8)
    (return))
  (if (and (== st 8) (> t 13.0))
    (Development|ExecuteConsoleCommand :Command "Shot showui" :SpecificPlayer pc)
    (Variables|UI|SetShotStep 9)
    (return))
  (if (and (== st 9) (> t 14.0))
    (Game|QuitGame :SpecificPlayer pc :QuitPreference "Quit" :bIgnorePlatformRestrictions false)))
'''
    G['EventGraph'] = '''
(event UserInterface|EventConstruct
  (CallFunction|SetupMenu))

(event UserInterface|EventTick (MyGeometry InDeltaTime)
  (CallFunction|MenuTick :Dt InDeltaTime)
  (if (Utilities|HasLaunchOption :OptionToCheck "GWShot")
    (CallFunction|ShotTick))
  ; packaged-build test: -GWMenuHost / -GWMenuJoin run the real buttons' handlers once, 3 s after the menu opens
  (if (and (not (Variables|UI|GetAutoDone)) (> (Variables|UI|GetT) 3.0))
    (if (Utilities|HasLaunchOption :OptionToCheck "GWMenuHost")
      (Variables|UI|SetAutoDone true)
      (CallFunction|OnHostClicked)
      (else
        (if (Utilities|HasLaunchOption :OptionToCheck "GWMenuJoin")
          (Variables|UI|SetAutoDone true)
          (CallFunction|OnJoinClicked))))))
'''
    only = UE_ARGS[1] if len(UE_ARGS) > 1 else None
    for name, code in G.items():
        if only and name != only:
            continue
        write(W, name, code, compile_after=False)
        print('wrote', name)
    compile_bp(W, quiet=True)
    for b, fn in [('BtnHost', 'OnHostAsk'), ('BtnJoin', 'OnJoinClicked'), ('BtnQuit', 'OnQuitClicked'), ('BtnJoinOpen', 'OnJoinOpenClicked'),
                  ('BtnOptions', 'OnOptionsClicked'), ('BtnHowTo', 'OnHowToClicked'), ('BtnCancel', 'OnCancelClicked'),
                  ('BtnErrClose', 'OnErrCloseClicked')]:
        bind(W, b, 'OnClicked', fn)
    bind(W, 'NameBox', 'OnTextChanged', 'OnTyped', unreal.EditableTextBox)
    bind(W, 'IpBox', 'OnTextChanged', 'OnTyped', unreal.EditableTextBox)
    compile_bp(W)
    unreal.get_default_object(W.generated_class()).set_editor_property('is_focusable', True)
    print(node_problems(W))
    compile_widget(W)


if which in ('all', 'tree'):
    build_tree()
if which in ('all', 'graph'):
    build_graph()
