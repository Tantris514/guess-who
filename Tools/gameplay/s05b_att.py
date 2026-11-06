import unreal
EAL = unreal.EditorAssetLibrary
p = '/Game/GW/Audio/ATT_GW_Gunshot'
if EAL.does_asset_exist(p):
    a = unreal.load_asset(p)
else:
    a = unreal.AssetToolsHelpers.get_asset_tools().create_asset('ATT_GW_Gunshot', '/Game/GW/Audio', unreal.SoundAttenuation, unreal.SoundAttenuationFactory())
s = a.get_editor_property('attenuation')
s.set_editor_property('attenuate', True)
s.set_editor_property('spatialize', True)
s.set_editor_property('falloff_distance', 7000.0)
s.set_editor_property('attenuation_shape_extents', unreal.Vector(600, 0, 0))
a.set_editor_property('attenuation', s)
EAL.save_loaded_asset(a, False)
print('ok', a.get_editor_property('attenuation').get_editor_property('falloff_distance'))
