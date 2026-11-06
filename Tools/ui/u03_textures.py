"""Import AssetGen/ui/final/*.png into /Game/GW/UI/Textures as UI textures (UserInterface2D, no mips, never stream).
UE_ARGS: optional list of texture names (without .png) to (re)import; default = all."""
import glob, os
import unreal
SRC = r'J:\Projets\Unreal_Projects\Guess Who\AssetGen\ui\final'
DST = '/Game/GW/UI/Textures'
EAL = unreal.EditorAssetLibrary
only = set(UE_ARGS)
files = [f for f in sorted(glob.glob(os.path.join(SRC, '*.png'))) if not only or os.path.splitext(os.path.basename(f))[0] in only]
tasks = []
for f in files:
    t = unreal.AssetImportTask()
    t.filename = f; t.destination_path = DST; t.destination_name = os.path.splitext(os.path.basename(f))[0]
    t.automated = True; t.replace_existing = True; t.save = False
    tasks.append(t)
unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks(tasks)
for t in tasks:
    p = f'{DST}/{t.destination_name}'
    tx = unreal.load_asset(p)
    if tx is None:
        print('FAILED', p); continue
    tx.set_editor_property('compression_settings', unreal.TextureCompressionSettings.TC_EDITOR_ICON)
    tx.set_editor_property('lod_group', unreal.TextureGroup.TEXTUREGROUP_UI)
    # big art shown minified (logo, cards, photos) keeps mips so thin strokes do not shimmer
    mips = any(k in t.destination_name for k in ('Logo', 'Card', 'Photo', 'How', 'Ico'))
    tx.set_editor_property('mip_gen_settings', unreal.TextureMipGenSettings.TMGS_SIMPLE_AVERAGE if mips else unreal.TextureMipGenSettings.TMGS_NO_MIPMAPS)
    tx.set_editor_property('never_stream', True)
    tx.set_editor_property('srgb', True)
    EAL.save_loaded_asset(tx, False)
print('imported', len(tasks), [t.destination_name for t in tasks])
