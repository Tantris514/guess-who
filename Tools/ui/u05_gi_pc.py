"""New functions on BP_GW_GameInstance (settings SaveGame + audio/graphics apply) and BP_GW_PlayerController
(pause input swap, mouse sensitivity, Esc -> pause menu). Existing gameplay graphs are not touched, except the IA_Menu
input event which is re-wired from MenuPressed (double-Esc disconnect) to UIMenuPressed (pause menu).
UE_ARGS: 'gi' | 'pc' | 'all' (default)."""
import sys
sys.path.insert(0, r'J:\Projets\Unreal_Projects\Guess Who\Tools\ui')
import importlib, uilib
importlib.reload(uilib)
from uilib import *
import gw_lib

which = UE_ARGS[0] if UE_ARGS else 'all'
SET = '/Game/GW/UI/BP_GW_Settings.BP_GW_Settings_C'
MIX = '"/Game/GW/Audio/Classes/SM_GW_Settings.SM_GW_Settings"'
ISVALID = 'GW|Call|/Script/Engine.KismetSystemLibrary|IsValid'


def sget(v, obj='s'):
    return f'(GW|Get|{SET}|{v} :self {obj})'


if which in ('all', 'gi'):
    gi = unreal.load_asset('/Game/GW/Blueprints/BP_GW_GameInstance')
    ensure_var(gi, 'Settings', obj_class=unreal.load_asset('/Game/GW/UI/BP_GW_Settings').generated_class(), category='UI')
    ensure_fn(gi, 'GWSettings', outputs=[('S', unreal.load_asset('/Game/GW/UI/BP_GW_Settings').generated_class())])
    ensure_fn(gi, 'GWSaveSettings')
    ensure_fn(gi, 'GWApplyAudio')
    ensure_fn(gi, 'GWApplyGraphics', inputs=[('Display', 'bool')])
    compile_bp(gi, quiet=True)
    ensure_fn(gi, 'GWNewSettings', outputs=[('S', unreal.load_asset('/Game/GW/UI/BP_GW_Settings').generated_class())])
    compile_bp(gi, quiet=True)
    write(gi, 'GWNewSettings', f'''
(fn GWNewSettings ()
  (bind made (Utilities|Casting|CastToBP_GW_Settings (SaveGame|CreateSaveGameObject :SaveGameClass "{SET}"))
    (:then
      (Variables|UI|SetSettings made)
      (return made))
    (:CastFailed
      (return (Variables|UI|GetSettings)))))
''', compile_after=False)
    write(gi, 'GWSettings', f'''
(fn GWSettings ()
  (if ({ISVALID} :Object (Variables|UI|GetSettings))
    (return (Variables|UI|GetSettings)))
  (if (not (SaveGame|DoesSaveGameExist :SlotName "GW_Settings" :UserIndex 0))
    (bind n1 (CallFunction|GWNewSettings))
    (return n1))
  (bind loaded (Utilities|Casting|CastToBP_GW_Settings (SaveGame|LoadGamefromSlot :SlotName "GW_Settings" :UserIndex 0))
    (:then
      (Variables|UI|SetSettings loaded)
      (return loaded))
    (:CastFailed
      (bind n2 (CallFunction|GWNewSettings))
      (return n2))))
''', compile_after=False)
    write(gi, 'GWSaveSettings', '''
(fn GWSaveSettings ()
  (bind s (CallFunction|GWSettings))
  (SaveGame|SaveGametoSlot :SaveGameObject s :SlotName "GW_Settings" :UserIndex 0))
''', compile_after=False)
    ov = lambda cls, vol: (f'(Audio|SetSoundMixClassOverride :InSoundMixModifier {MIX} :InSoundClass "/Game/GW/Audio/Classes/{cls}.{cls}" '
                           f':Volume {vol} :Pitch 1.0 :FadeInTime 0.05 :bApplyToChildren false)')
    write(gi, 'GWApplyAudio', f'''
(fn GWApplyAudio ()
  (bind s (CallFunction|GWSettings))
  (bind m {sget('MasterVol')})
  (bind fx (* m {sget('SfxVol')}))
  {ov('SC_GW_Music', '(* m ' + sget('MusicVol') + ')')}
  {ov('SC_GW_SFX', 'fx')}
  {ov('SC_GW_Ambience', 'fx')}
  {ov('SC_GW_Voice', 'fx')}
  {ov('SC_GW_UI', '(* m ' + sget('UIVol') + ')')}
  (Audio|PushSoundMixModifier :InSoundMixModifier {MIX}))
''', compile_after=False)
    ensure_fn(gi, 'GWSetWindowMode', inputs=[('Mode', 'int')])
    compile_bp(gi, quiet=True)
    write(gi, 'GWSetWindowMode', '''
(fn GWSetWindowMode (Mode)
  (bind gus (Settings|GetGameUserSettings))
  (switch int Mode
    (:0 (Settings|SetFullscreenMode :self gus :InFullscreenMode "Fullscreen"))
    (:1 (Settings|SetFullscreenMode :self gus :InFullscreenMode "WindowedFullscreen"))
    (:Default (Settings|SetFullscreenMode :self gus :InFullscreenMode "Windowed"))))
''', compile_after=False)
    write(gi, 'GWApplyGraphics', f'''
(fn GWApplyGraphics (Display)
  (bind s (CallFunction|GWSettings))
  (bind gus (Settings|GetGameUserSettings))
  (Settings|SetOverallScalabilityLevel :self gus :Value {sget('Quality')})
  (if Display
    (CallFunction|GWSetWindowMode :Mode {sget('WindowMode')})
    (if (> {sget('ResX')} 0)
      (Settings|SetScreenResolution :self gus :Resolution (Utilities|Struct|MakeIntPoint :X {sget('ResX')} :Y {sget('ResY')}))))
  (Settings|ApplySettings :self gus :bCheckForCommandLineOverrides true))
''', compile_after=False)
    compile_bp(gi)
    print(node_problems(gi))
    save(gi)

if which in ('all', 'pc'):
    pc = unreal.load_asset('/Game/GW/Blueprints/BP_GW_PlayerController')
    ensure_fn(pc, 'UIMenuPressed')
    ensure_fn(pc, 'UISetPauseInput', inputs=[('Paused', 'bool')])
    ensure_fn(pc, 'UIApplyLook', inputs=[('Sens', 'float')])
    compile_bp(pc, quiet=True)
    # Esc closes the dev menu first (Tools/ui/u15_dev_menu.py, which writes the same body)
    write(pc, 'UIMenuPressed', f'''
(fn UIMenuPressed ()
  (bind dw (Variables|GW|GetDevMenuW))
  (if ({ISVALID} :Object dw)
    (if (Appearance|IsinViewport :self dw)
      (CallFunction|CloseDevMenu)
      (return)))
  (bind hud (Variables|GW|GetHUDWidget))
  (if ({ISVALID} :Object hud)
    (GW|Call|/Game/GW/UI/WBP_HUD.WBP_HUD_C|TogglePause :self hud)
    (else
      (CallFunction|MenuPressed))))
''', compile_after=False)
    ensure_var(pc, 'UILookIMCs', obj_class=unreal.InputMappingContext, array=True, category='UI')
    ensure_var(pc, 'UILookIdx', 'int', category='UI')
    compile_bp(pc, quiet=True)
    cdo = unreal.get_default_object(pc.generated_class())
    cdo.set_editor_property('UILookIMCs', [unreal.load_asset(f'/Game/GW/UI/Input/IMC_GW_Look_{i:02d}') for i in range(12)])
    cdo.set_editor_property('UILookIdx', 6)
    write(pc, 'UISetPauseInput', '''
(fn UISetPauseInput (Paused)
  (bind sub (LocalPlayerSubsystems|GetEnhancedInputLocalPlayerSubsystem))
  (bind look (Utilities|Array|Get(acopy) (Variables|UI|GetUILookIMCs) (Variables|UI|GetUILookIdx)))
  (if Paused
    (Input|RemoveMappingContext :self sub :MappingContext "/Game/Input/IMC_Default.IMC_Default")
    (Input|RemoveMappingContext :self sub :MappingContext "/Game/Input/IMC_MouseLook.IMC_MouseLook")
    (Input|RemoveMappingContext :self sub :MappingContext look)
    (Input|RemoveMappingContext :self sub :MappingContext "/Game/GW/Input/IMC_GW.IMC_GW")
    (Input|AddMappingContext :self sub :MappingContext "/Game/GW/UI/Input/IMC_GW_Pause.IMC_GW_Pause" :Priority 5)
    (Input|SetInputModeGameAndUI :PlayerController self :bHideCursorDuringCapture false)
    (Variables|MouseInterface|SetShowMouseCursor true)
    (else
      (Input|RemoveMappingContext :self sub :MappingContext "/Game/GW/UI/Input/IMC_GW_Pause.IMC_GW_Pause")
      (Input|AddMappingContext :self sub :MappingContext "/Game/Input/IMC_Default.IMC_Default" :Priority 0)
      (Input|AddMappingContext :self sub :MappingContext look :Priority 0)
      (Input|AddMappingContext :self sub :MappingContext "/Game/GW/Input/IMC_GW.IMC_GW" :Priority 1)
      (Input|SetInputModeGameOnly :PlayerController self)
      (Variables|MouseInterface|SetShowMouseCursor false))))
''', compile_after=False)
    write(pc, 'UIApplyLook', '''
(fn UIApplyLook (Sens)
  (bind sub (LocalPlayerSubsystems|GetEnhancedInputLocalPlayerSubsystem))
  (bind idx (Math|Integer|Clamp(Integer) :Value (Math|Float|Round (/ (Math|Float|Loge (/ (Math|Float|Max(Float) Sens 0.05) 0.25)) 0.2231436)) :Min 0 :Max 11))
  (for imc (Variables|UI|GetUILookIMCs)
    (Input|RemoveMappingContext :self sub :MappingContext imc))
  (Input|RemoveMappingContext :self sub :MappingContext "/Game/Input/IMC_MouseLook.IMC_MouseLook")
  (Variables|UI|SetUILookIdx idx)
  (Input|AddMappingContext :self sub :MappingContext (Utilities|Array|Get(acopy) (Variables|UI|GetUILookIMCs) idx) :Priority 0)
  (Development|PrintString :InString (cat "GW ui: look sensitivity step " idx) :bPrintToScreen false))
''', compile_after=False)
    compile_bp(pc, quiet=True)
    gw_lib.wire_input(pc, 'IA_Menu', {'Started': 'UIMenuPressed'}, pos=(0, 2400))
    compile_bp(pc)
    print(node_problems(pc))
    save(pc)
