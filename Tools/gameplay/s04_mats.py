import unreal
EAL = unreal.EditorAssetLibrary
MEL = unreal.MaterialEditingLibrary
at = unreal.AssetToolsHelpers.get_asset_tools()
D = '/Game/GW/Characters/Materials'
EAL.make_directory(D)
def mic(name, parent_path):
    p = f'{D}/{name}'
    mi = unreal.load_asset(p) if EAL.does_asset_exist(p) else at.create_asset(name, D, unreal.MaterialInstanceConstant, unreal.MaterialInstanceConstantFactoryNew())
    MEL.set_material_instance_parent(mi, unreal.load_asset(parent_path))
    return mi
t = mic('MI_GW_Torso', '/Game/Characters/Mannequins/Materials/Manny/MI_Manny_02_New')
MEL.set_material_instance_static_switch_parameter_value(t, 'Logo?', False)
MEL.set_material_instance_scalar_parameter_value(t, 'EmissivePower', 0.0)
MEL.set_material_instance_vector_parameter_value(t, 'Paint Tint', unreal.LinearColor(0.05,0.05,0.06,1))
MEL.set_material_instance_scalar_parameter_value(t, 'MetalPaintRoughness', 0.45)
l = mic('MI_GW_HeadLegs', '/Game/Characters/Mannequins/Materials/Manny/MI_Manny_01_New')
MEL.set_material_instance_vector_parameter_value(l, 'Paint Tint', unreal.LinearColor(0.03,0.03,0.035,1))
MEL.set_material_instance_scalar_parameter_value(l, 'MetalPaintRoughness', 0.5)
tf = mic('MI_GW_Torso_F', '/Game/Characters/Mannequins/Materials/Quinn/MI_Quinn_02')
MEL.set_material_instance_static_switch_parameter_value(tf, 'Logo?', False)
MEL.set_material_instance_scalar_parameter_value(tf, 'EmissivePower', 0.0)
MEL.set_material_instance_scalar_parameter_value(tf, 'MetalPaintRoughness', 0.4)
lf = mic('MI_GW_HeadLegs_F', '/Game/Characters/Mannequins/Materials/Quinn/MI_Quinn_01')
MEL.set_material_instance_scalar_parameter_value(lf, 'MetalPaintRoughness', 0.5)
for m in (t, l, tf, lf):
    MEL.update_material_instance(m); EAL.save_loaded_asset(m, False)
# simple accessory material
p = f'{D}/M_GW_Accessory'
if not EAL.does_asset_exist(p):
    m = at.create_asset('M_GW_Accessory', D, unreal.Material, unreal.MaterialFactoryNew())
    c = MEL.create_material_expression(m, unreal.MaterialExpressionVectorParameter, -400, 0)
    c.set_editor_property('parameter_name', 'Color')
    c.set_editor_property('default_value', unreal.LinearColor(0.02,0.02,0.02,1))
    r = MEL.create_material_expression(m, unreal.MaterialExpressionScalarParameter, -400, 200)
    r.set_editor_property('parameter_name', 'Roughness')
    r.set_editor_property('default_value', 0.45)
    mt = MEL.create_material_expression(m, unreal.MaterialExpressionScalarParameter, -400, 300)
    mt.set_editor_property('parameter_name', 'Metallic')
    mt.set_editor_property('default_value', 0.0)
    MEL.connect_material_property(c, '', unreal.MaterialProperty.MP_BASE_COLOR)
    MEL.connect_material_property(r, '', unreal.MaterialProperty.MP_ROUGHNESS)
    MEL.connect_material_property(mt, '', unreal.MaterialProperty.MP_METALLIC)
    MEL.recompile_material(m)
    EAL.save_loaded_asset(m, False)
for name, col, met in [('MI_GW_Hat_Black', (0.015,0.015,0.017), 0.0), ('MI_GW_Hat_Fedora', (0.10,0.07,0.045), 0.0), ('MI_GW_Mask_Gold', (0.8,0.55,0.15), 1.0), ('MI_GW_Gun', (0.06,0.06,0.065), 1.0)]:
    mi = mic(name, p)
    MEL.set_material_instance_vector_parameter_value(mi, 'Color', unreal.LinearColor(*col, 1))
    MEL.set_material_instance_scalar_parameter_value(mi, 'Metallic', met)
    MEL.update_material_instance(mi); EAL.save_loaded_asset(mi, False)
print(EAL.list_assets(D))
