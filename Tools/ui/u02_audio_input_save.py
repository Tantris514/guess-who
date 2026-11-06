"""Sound classes + settings sound mix, the UI input mapping contexts, and the settings SaveGame Blueprint.

  /Game/GW/Audio/Classes: SC_GW_Master <- SC_GW_Music, SC_GW_SFX, SC_GW_Ambience, SC_GW_Voice, SC_GW_UI ; SM_GW_Settings
  /Game/GW/UI/Input: IMC_GW_Look (Mouse2D -> IA_MouseLook, Negate + Scalar(sensitivity)), IMC_GW_Pause (Escape -> IA_Menu)
  /Game/GW/UI/BP_GW_Settings (SaveGame): volumes, sensitivity, FOV, quality, window mode, resolution
"""
import sys
import unreal
sys.path.insert(0, r'J:\Projets\Unreal_Projects\Guess Who\Tools\gameplay')
import importlib, gw_lib
importlib.reload(gw_lib)
from gw_lib import BT, ensure_var, compile_bp, save, EAL

AT = unreal.AssetToolsHelpers.get_asset_tools()
CLS = '/Game/GW/Audio/Classes'


def get_or_create(name, folder, cls, factory):
    p = f'{folder}/{name}'
    if EAL.does_asset_exist(p):
        return unreal.load_asset(p)
    return AT.create_asset(name, folder, cls, factory)


master = get_or_create('SC_GW_Master', CLS, unreal.SoundClass, unreal.SoundClassFactory())
kids = {}
for n in ['Music', 'SFX', 'Ambience', 'Voice', 'UI']:
    sc = get_or_create(f'SC_GW_{n}', CLS, unreal.SoundClass, unreal.SoundClassFactory())
    sc.set_editor_property('parent_class', master)
    kids[n] = sc
master.set_editor_property('child_classes', list(kids.values()))
for sc in [master] + list(kids.values()):
    EAL.save_loaded_asset(sc, False)

mix = get_or_create('SM_GW_Settings', CLS, unreal.SoundMix, unreal.SoundMixFactory())
adj = []
for n, sc in kids.items():
    a = unreal.SoundClassAdjuster()
    a.set_editor_property('sound_class_object', sc)
    a.set_editor_property('volume_adjuster', 1.0)
    a.set_editor_property('pitch_adjuster', 1.0)
    adj.append(a)
mix.set_editor_property('sound_class_effects', adj)
EAL.save_loaded_asset(mix, False)
print('sound classes + mix ok')

# ---------------------------------------------------------------- input contexts
INP = '/Game/GW/UI/Input'
look_p = f'{INP}/IMC_GW_Look'
if not EAL.does_asset_exist(look_p):
    EAL.duplicate_asset('/Game/Input/IMC_MouseLook', look_p)
look = unreal.load_asset(look_p)
dk = look.get_editor_property('default_key_mappings')
maps = list(dk.get_editor_property('mappings'))
for i, m in enumerate(maps):
    mods = list(m.get_editor_property('modifiers'))
    if not any(isinstance(x, unreal.InputModifierScalar) for x in mods):
        sc = unreal.new_object(unreal.InputModifierScalar, outer=look)
        sc.set_editor_property('scalar', unreal.Vector(1.0, 1.0, 1.0))
        mods.append(sc)
        m.set_editor_property('modifiers', mods)
        maps[i] = m
dk.set_editor_property('mappings', maps)
look.set_editor_property('default_key_mappings', dk)
EAL.save_loaded_asset(look, False)
print('IMC_GW_Look', [[type(x).__name__ for x in m.get_editor_property('modifiers')] for m in look.get_editor_property('default_key_mappings').get_editor_property('mappings')])

pause_p = f'{INP}/IMC_GW_Pause'
if EAL.does_asset_exist(pause_p):
    pause = unreal.load_asset(pause_p)
else:
    pause = AT.create_asset('IMC_GW_Pause', INP, unreal.InputMappingContext, unreal.InputMappingContext_Factory())
pause.unmap_all()
ia_menu = unreal.load_asset('/Game/GW/Input/IA_Menu')
k = unreal.Key(); k.set_editor_property('key_name', 'Escape')
pause.map_key(ia_menu, k)
EAL.save_loaded_asset(pause, False)
print('IMC_GW_Pause', [(m.get_editor_property('action').get_name(), str(m.get_editor_property('key').get_editor_property('key_name')))
                       for m in pause.get_editor_property('default_key_mappings').get_editor_property('mappings')])

# ---------------------------------------------------------------- settings SaveGame
path = '/Game/GW/UI/BP_GW_Settings'
if EAL.does_asset_exist(path):
    sg = unreal.load_asset(path)
else:
    sg = BT.create('/Game/GW/UI', 'BP_GW_Settings', unreal.SaveGame.static_class())
VARS = [('MasterVol', 'float', 1.0), ('MusicVol', 'float', 0.7), ('SfxVol', 'float', 1.0), ('UIVol', 'float', 0.8),
        ('MouseSens', 'float', 1.0), ('FOV', 'float', 90.0), ('Quality', 'int', 3), ('WindowMode', 'int', 1),
        ('ResX', 'int', 0), ('ResY', 'int', 0), ('Version', 'int', 1),
        # the game setup screen (u19_game_setup.py), remembered between games
        ('GNPCs', 'int', 120), ('GHunt', 'int', 240), ('GHide', 'int', 20), ('GRounds', 'int', 0), ('GSeekers', 'int', 0), ('GAutoEv', 'int', 1), ('GEventEvery', 'int', 180), ('GMinPlayers', 'int', 2), ('GLobby', 'int', 8)]
for n, t, _ in VARS:
    ensure_var(sg, n, t, category='GW')
compile_bp(sg, quiet=True)
cdo = unreal.get_default_object(sg.generated_class())
for n, t, v in VARS:
    cdo.set_editor_property(n, v)
compile_bp(sg)
save(sg)
print('settings defaults', {n: cdo.get_editor_property(n) for n, _, _ in VARS})

# ---------------------------------------------------------------- look sensitivity steps
# IMC mapping modifiers cannot be edited at runtime from Blueprint in this engine build (the Mappings property is editor-only),
# so the sensitivity is a set of 12 contexts with a fixed Scalar each: s_i = 0.25 * 1.25^i (0.25 .. 2.91).
for i in range(12):
    s = 0.25 * (1.25 ** i)
    p = f'{INP}/IMC_GW_Look_{i:02d}'
    if not EAL.does_asset_exist(p):
        EAL.duplicate_asset('/Game/Input/IMC_MouseLook', p)
    imc = unreal.load_asset(p)
    dk = imc.get_editor_property('default_key_mappings')
    maps = list(dk.get_editor_property('mappings'))
    for j, m in enumerate(maps):
        mods = [x for x in m.get_editor_property('modifiers') if not isinstance(x, unreal.InputModifierScalar)]
        sc = unreal.new_object(unreal.InputModifierScalar, outer=imc)
        sc.set_editor_property('scalar', unreal.Vector(s, s, 1.0))
        mods.append(sc)
        m.set_editor_property('modifiers', mods)
        maps[j] = m
    dk.set_editor_property('mappings', maps)
    imc.set_editor_property('default_key_mappings', dk)
    EAL.save_loaded_asset(imc, False)
print('look IMCs', [round(0.25 * 1.25 ** i, 3) for i in range(12)])
