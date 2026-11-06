"""Import the approved key art (AssetGen manifest) and put it behind the main menu (ScaleBox, scale-to-fill)."""
import json
import unreal
EAL = unreal.EditorAssetLibrary
_UO = unreal.get_default_object(unreal.UMGToolSet.static_class())
m = json.load(open(r'J:\Projets\Unreal_Projects\Guess Who\AssetGen\manifest.json', encoding='utf-8'))
ka = next(a for a in m['assets'] if a['name'] == 'keyart' and a.get('status') == 'approved')
t = unreal.AssetImportTask()
t.filename = ka['files']['image']; t.destination_path = '/Game/GW/UI'; t.destination_name = 'T_GW_KeyArt'
t.automated = True; t.replace_existing = True; t.save = False
unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks([t])
tex = unreal.load_asset('/Game/GW/UI/T_GW_KeyArt')
tex.set_editor_property('compression_settings', unreal.TextureCompressionSettings.TC_EDITOR_ICON)
tex.set_editor_property('lod_group', unreal.TextureGroup.TEXTUREGROUP_UI)
tex.set_editor_property('mip_gen_settings', unreal.TextureMipGenSettings.TMGS_NO_MIPMAPS)
tex.set_editor_property('never_stream', True)
EAL.save_loaded_asset(tex, False)
w = unreal.load_asset('/Game/GW/UI/WBP_MainMenu')
infos = {str(i.widget_name): i for i in _UO.call_method('GetWidgets', args=(w,)).widgets}
bg = infos['Background']
if 'BgScale' not in infos:
    wrapped = _UO.call_method('WrapWidgets', args=(w, [bg.widget], unreal.ScaleBox.static_class()))
    _UO.call_method('RenameWidget', args=(w, wrapped[0].widget, 'BgScale'))
    infos = {str(i.widget_name): i for i in _UO.call_method('GetWidgets', args=(w,)).widgets}
sb = infos['BgScale']
sb.widget.set_editor_property('stretch', unreal.Stretch.SCALE_TO_FILL)
brush = unreal.SlateBrush()
brush.set_editor_property('resource_object', tex)
_sz = unreal.DeprecateSlateVector2D()
_sz.set_editor_property('x', 1920.0)
_sz.set_editor_property('y', 1088.0)
brush.set_editor_property('image_size', _sz)
img = infos['Background'].widget
img.set_editor_property('brush', brush)
img.set_editor_property('color_and_opacity', unreal.LinearColor(0.72, 0.70, 0.68, 1.0))
# slightly more transparent panel so the art shows around it
infos['MenuBox'].widget.set_editor_property('brush_color', unreal.LinearColor(0.01, 0.008, 0.006, 0.80))
_UO.call_method('CompileWidgetBlueprint', args=(w,))
EAL.save_loaded_asset(w, False)
print(_UO.call_method('GetWidgetDescription', args=(w, None, 3)).description[:1500])
