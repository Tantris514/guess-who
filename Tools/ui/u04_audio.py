"""Import the mastered WAVs (AssetGen/audio/final) into /Game/GW/Audio, assign sound classes, loop flags, and create the
attenuation presets used by the ambient actors. Replaces the procedural placeholders (same asset names).
UE_ARGS: optional names to (re)import."""
import glob, os
import unreal
SRC = r'J:\Projets\Unreal_Projects\Guess Who\AssetGen\audio\final'
DST = '/Game/GW/Audio'
EAL = unreal.EditorAssetLibrary
AT = unreal.AssetToolsHelpers.get_asset_tools()
only = set(UE_ARGS)


def klass(name):
    if name.startswith('MUS_') or name.startswith('STG_'):
        return 'SC_GW_Music'
    if name.startswith('AMB_'):
        return 'SC_GW_Ambience'
    if name.startswith('S_UI_'):
        return 'SC_GW_UI'
    if name.startswith('VO_'):
        return 'SC_GW_Voice'
    return 'SC_GW_SFX'


files = [f for f in sorted(glob.glob(os.path.join(SRC, '*.wav'))) if not only or os.path.splitext(os.path.basename(f))[0] in only]
tasks = []
for f in files:
    t = unreal.AssetImportTask()
    t.filename = f; t.destination_path = DST; t.destination_name = os.path.splitext(os.path.basename(f))[0]
    t.automated = True; t.replace_existing = True; t.save = False
    tasks.append(t)
AT.import_asset_tasks(tasks)
for t in tasks:
    n = t.destination_name
    w = unreal.load_asset(f'{DST}/{n}')
    if not isinstance(w, unreal.SoundWave):
        print('FAILED', n, type(w)); continue
    w.set_editor_property('sound_class_object', unreal.load_asset(f'{DST}/Classes/{klass(n)}.{klass(n)}'))
    loop = n.startswith('MUS_') or n.startswith('AMB_')
    w.set_editor_property('looping', loop)
    if loop:
        try:
            w.set_editor_property('loading_behavior', unreal.SoundWaveLoadingBehavior.RETAIN_ON_LOAD)
        except Exception:
            pass
    EAL.save_loaded_asset(w, False)
print('imported', len(tasks), [t.destination_name for t in tasks])

# placeholder-only sounds that are no longer referenced keep their class too
for n in ('S_GW_Gunshot', 'S_GW_Thud', 'S_GW_Gong', 'S_GW_Chime', 'S_GW_Sombre'):
    p = f'{DST}/{n}'
    if EAL.does_asset_exist(p):
        w = unreal.load_asset(p)
        if w.get_editor_property('sound_class_object') is None:
            w.set_editor_property('sound_class_object', unreal.load_asset(f'{DST}/Classes/SC_GW_SFX.SC_GW_SFX'))
            EAL.save_loaded_asset(w, False)


def att(name, inner, falloff, spatial=True, lpf=True):
    p = f'{DST}/{name}'
    a = unreal.load_asset(p) if EAL.does_asset_exist(p) else AT.create_asset(name, DST, unreal.SoundAttenuation, unreal.SoundAttenuationFactory())
    s = a.get_editor_property('attenuation')
    s.set_editor_property('attenuate', True)
    s.set_editor_property('spatialize', spatial)
    s.set_editor_property('attenuation_shape', unreal.AttenuationShape.SPHERE)
    s.set_editor_property('attenuation_shape_extents', unreal.Vector(inner, 0, 0))
    s.set_editor_property('falloff_distance', falloff)
    s.set_editor_property('distance_algorithm', unreal.AttenuationDistanceModel.NATURAL_SOUND)
    if lpf:
        s.set_editor_property('attenuate_with_lpf', True)
        s.set_editor_property('lpf_radius_min', inner)
        s.set_editor_property('lpf_radius_max', inner + falloff)
    a.set_editor_property('attenuation', s)
    EAL.save_loaded_asset(a, False)
    return a


att('ATT_GW_Fire', 150.0, 1400.0)              # fireplace crackle: close, spatialized
att('ATT_GW_Gramophone', 250.0, 2600.0)        # gramophone on the ballroom stage
att('ATT_GW_Room', 900.0, 2400.0, spatial=False, lpf=False)   # room tones (crowd / glasses / rain): volume by distance only
print('attenuations ok')
