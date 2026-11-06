"""Import the local OFL fonts (AssetGen/ui/fonts) as FontFace assets and build composite Font assets in /Game/GW/UI/Fonts.

Fonts (all SIL Open Font License, licence files copied next to the TTFs):
  F_GW_Display = League Gothic (condensed 1930s poster gothic)       typefaces: Regular
  F_GW_Serif   = STIX General (Times-like book serif, full accents)  typefaces: Regular, Bold, Italic, BoldItalic
  F_GW_Sans    = Source Sans Pro                                     typefaces: Regular, SemiBold, Italic
"""
import os
import unreal

SRC = r'J:\Projets\Unreal_Projects\Guess Who\AssetGen\ui\fonts'
DST = '/Game/GW/UI/Fonts'
EAL = unreal.EditorAssetLibrary
AT = unreal.AssetToolsHelpers.get_asset_tools()

FAMILIES = {
    'F_GW_Display': [('Regular', 'LeagueGothic-Regular')],
    'F_GW_Serif': [('Regular', 'STIXGeneral-Regular'), ('Bold', 'STIXGeneral-Bold'), ('Italic', 'STIXGeneral-Italic'), ('BoldItalic', 'STIXGeneral-BoldItalic')],
    'F_GW_Sans': [('Regular', 'SourceSansPro-Regular'), ('SemiBold', 'SourceSansPro-SemiBold'), ('Italic', 'SourceSansPro-Italic')],
}


def import_face(stem):
    path = f'{DST}/FF_{stem.replace("-", "_")}'
    if EAL.does_asset_exist(path):
        return unreal.load_asset(path)
    t = unreal.AssetImportTask()
    t.filename = os.path.join(SRC, stem + '.ttf')
    t.destination_path = DST
    t.destination_name = 'FF_' + stem.replace('-', '_')
    t.automated = True
    t.replace_existing = True
    t.save = False
    AT.import_asset_tasks([t])
    objs = t.get_editor_property('imported_object_paths')
    print('imported', stem, list(objs))
    a = unreal.load_asset(path)
    if not isinstance(a, unreal.FontFace):
        print('  WARNING: not a FontFace:', type(a))
    return a


for fam, faces in FAMILIES.items():
    parts = []
    for tname, stem in faces:
        ff = import_face(stem)
        ff.set_editor_property('loading_policy', unreal.FontLoadingPolicy.INLINE)
        EAL.save_loaded_asset(ff, False)
        parts.append(f'(Name="{tname}",Font=(FontFaceAsset="{ff.get_path_name()}"))')
    path = f'{DST}/{fam}'
    if EAL.does_asset_exist(path):
        font = unreal.load_asset(path)
    else:
        font = AT.create_asset(fam, DST, unreal.Font, unreal.FontFactory())
    font.set_editor_property('font_cache_type', unreal.FontCacheType.RUNTIME)
    cf = font.get_editor_property('composite_font')
    # FallbackTypeface: DroidSansFallback (engine) for any glyph the face lacks (e.g. guillemets in League Gothic)
    txt = ('(DefaultTypeface=(Fonts=(' + ','.join(parts) + ')),FallbackTypeface=(Typeface=(Fonts=((Name="Regular",'
           'Font=(FontFaceAsset="/Engine/EngineFonts/Faces/DroidSansFallback.DroidSansFallback")))),'
           'ScalingFactor=1.000000),SubTypefaces=,bEnableAscentDescentOverride=True)')
    cf.import_text(txt)
    font.set_editor_property('composite_font', cf)
    EAL.save_loaded_asset(font, False)
    print(fam, font.get_editor_property('composite_font').export_text()[:160])
