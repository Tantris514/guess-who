"""M_GW_GenChar: master material of the generated characters (editor: ue_run.py gen_material.py).

The glTF import gives each character an instance of the Interchange plugin's M_GLTF, which is not flagged for skeletal
meshes, so in game the engine swaps it for the default material. This master is (used_with_skeletal_mesh, two-sided as
the GLB asks) and reads the generated PBR set:
  BaseColor (sRGB) x Tint;  ORM (linear: R occlusion, G roughness, B metallic);  Normal.
The generators paint metallic ~0.7 over everything (skin and satin came out as dark bronze), so Metallic is
B x MetallicScale with MetallicScale = 0 by default; RoughnessScale rescales G. Per-character instances (MI_<name>) are
made by Tools/chars/rig_character.py. Never rebuilt in place (see s24_body_material.py): a rebuild is a new _vN.
"""
import unreal

EAL = unreal.EditorAssetLibrary
MEL = unreal.MaterialEditingLibrary
AT = unreal.AssetToolsHelpers.get_asset_tools()
D = '/Game/GW/Characters/Gen'
ST = unreal.MaterialSamplerType
MP = unreal.MaterialProperty


def latest():
    v = 1
    while EAL.does_asset_exist(f'{D}/M_GW_GenChar_v{v + 1}'):
        v += 1
    return f'{D}/M_GW_GenChar_v{v}'


def build():
    v = 1
    while EAL.does_asset_exist(f'{D}/M_GW_GenChar_v{v}'):
        v += 1
    m = AT.create_asset(f'M_GW_GenChar_v{v}', D, unreal.Material, unreal.MaterialFactoryNew())

    def E(cls, x, y, **props):
        e = MEL.create_material_expression(m, cls, x, y)
        for k, val in props.items():
            e.set_editor_property(k, val)
        return e

    def tex(name, path, sampler, x, y):
        return E(unreal.MaterialExpressionTextureSampleParameter2D, x, y, parameter_name=name, texture=unreal.load_asset(path), sampler_type=sampler)

    def scalar(name, val, x, y):
        return E(unreal.MaterialExpressionScalarParameter, x, y, parameter_name=name, default_value=val)

    def mul(a, a_out, b, x, y):
        e = E(unreal.MaterialExpressionMultiply, x, y)
        MEL.connect_material_expressions(a, a_out, e, 'A')
        MEL.connect_material_expressions(b, '', e, 'B')
        return e

    base = tex('BaseColor', '/Engine/EngineMaterials/DefaultDiffuse', ST.SAMPLERTYPE_COLOR, -900, -300)
    orm = tex('ORM', '/Game/GW/Textures/Defaults/T_GW_Default_Linear', ST.SAMPLERTYPE_LINEAR_COLOR, -900, 50)
    nrm = tex('Normal', '/Engine/EngineMaterials/DefaultNormal', ST.SAMPLERTYPE_NORMAL, -900, 400)
    tint = E(unreal.MaterialExpressionVectorParameter, -900, -500, parameter_name='Tint', default_value=unreal.LinearColor(1, 1, 1, 1))
    MEL.connect_material_property(mul(base, 'RGB', tint, -500, -350), '', MP.MP_BASE_COLOR)
    rough = E(unreal.MaterialExpressionSaturate, -300, 50)
    MEL.connect_material_expressions(mul(orm, 'G', scalar('RoughnessScale', 1.0, -700, 150), -500, 50), '', rough, '')
    MEL.connect_material_property(rough, '', MP.MP_ROUGHNESS)
    MEL.connect_material_property(mul(orm, 'B', scalar('MetallicScale', 0.0, -700, 250), -500, 200), '', MP.MP_METALLIC)
    MEL.connect_material_property(orm, 'R', MP.MP_AMBIENT_OCCLUSION)
    MEL.connect_material_property(nrm, 'RGB', MP.MP_NORMAL)
    m.set_editor_property('two_sided', True)
    m.set_editor_property('used_with_skeletal_mesh', True)
    MEL.recompile_material(m)
    EAL.save_loaded_asset(m)
    return m


GHOST = f'{D}/M_GW_Ghost'


def build_ghost():
    """M_GW_Ghost: the dead player's own character, blue and see-through (translucent, unlit). The character's base
    colour, desaturated, keeps the face / clothes readable; a fresnel rim outlines the silhouette and carries most of
    the opacity. Parameters: BaseColor, Tint, Glow, Rim, RimExp, BaseOpacity."""
    if EAL.does_asset_exist(GHOST):
        return unreal.load_asset(GHOST)
    m = AT.create_asset('M_GW_Ghost', D, unreal.Material, unreal.MaterialFactoryNew())

    def E(cls, x, y, **props):
        e = MEL.create_material_expression(m, cls, x, y)
        for k, val in props.items():
            e.set_editor_property(k, val)
        return e

    def link(a, a_out, b, b_in):
        MEL.connect_material_expressions(a, a_out, b, b_in)

    def op(cls, a, b, x, y, a_out='', b_out=''):
        e = E(cls, x, y)
        link(a, a_out, e, 'A')
        link(b, b_out, e, 'B')
        return e

    def scalar(name, val, x, y):
        return E(unreal.MaterialExpressionScalarParameter, x, y, parameter_name=name, default_value=val)

    tex = E(unreal.MaterialExpressionTextureSampleParameter2D, -1200, -200, parameter_name='BaseColor',
            texture=unreal.load_asset('/Engine/EngineMaterials/DefaultDiffuse'), sampler_type=ST.SAMPLERTYPE_COLOR)
    lumw = E(unreal.MaterialExpressionConstant3Vector, -1200, 50, constant=unreal.LinearColor(0.3, 0.59, 0.11, 1))
    lum = op(unreal.MaterialExpressionDotProduct, tex, lumw, -950, -100, a_out='RGB')
    tint = E(unreal.MaterialExpressionVectorParameter, -1200, -450, parameter_name='Tint', default_value=unreal.LinearColor(0.22, 0.55, 1.0, 1))
    dark = op(unreal.MaterialExpressionMultiply, tint, E(unreal.MaterialExpressionConstant, -1000, -350, r=0.2), -800, -400)
    body = E(unreal.MaterialExpressionLinearInterpolate, -600, -300)
    link(dark, '', body, 'A')
    link(tint, '', body, 'B')
    link(lum, '', body, 'Alpha')
    glow = op(unreal.MaterialExpressionMultiply, body, scalar('Glow', 1.3, -800, -200), -400, -300)
    fres = E(unreal.MaterialExpressionFresnel, -1000, 250, exponent=3.0, base_reflect_fraction=0.0)
    link(scalar('RimExp', 3.0, -1200, 250), '', fres, 'ExponentIn')
    rimc = E(unreal.MaterialExpressionConstant3Vector, -800, 150, constant=unreal.LinearColor(0.55, 0.85, 1.0, 1))
    rim = op(unreal.MaterialExpressionMultiply, op(unreal.MaterialExpressionMultiply, fres, scalar('Rim', 2.0, -1000, 400), -800, 300), rimc, -600, 200)
    MEL.connect_material_property(op(unreal.MaterialExpressionAdd, glow, rim, -200, -100), '', MP.MP_EMISSIVE_COLOR)
    opac = op(unreal.MaterialExpressionAdd, scalar('BaseOpacity', 0.22, -800, 500),
              op(unreal.MaterialExpressionMultiply, fres, E(unreal.MaterialExpressionConstant, -800, 600, r=0.55), -600, 550), -400, 500)
    sat = E(unreal.MaterialExpressionSaturate, -200, 500)
    link(opac, '', sat, '')
    MEL.connect_material_property(sat, '', MP.MP_OPACITY)
    m.set_editor_property('blend_mode', unreal.BlendMode.BLEND_TRANSLUCENT)
    m.set_editor_property('shading_model', unreal.MaterialShadingModel.MSM_UNLIT)
    m.set_editor_property('used_with_skeletal_mesh', True)
    MEL.recompile_material(m)
    EAL.save_loaded_asset(m)
    return m


def ghost_instance(name, folder, base_tex):
    """MI_<name>_Ghost on M_GW_Ghost with the character's base colour (replaced if it exists)."""
    path = f'{folder}/MI_{name}_Ghost'
    mi = unreal.load_asset(path) if EAL.does_asset_exist(path) else \
        AT.create_asset(f'MI_{name}_Ghost', folder, unreal.MaterialInstanceConstant, unreal.MaterialInstanceConstantFactoryNew())
    MEL.set_material_instance_parent(mi, build_ghost())
    if base_tex:
        MEL.set_material_instance_texture_parameter_value(mi, 'BaseColor', base_tex)
    MEL.update_material_instance(mi)
    EAL.save_loaded_asset(mi)
    return mi


def instance(name, folder, base_tex, orm_tex, normal_tex):
    """MI_<name> on the latest master with the character's three textures (replaced if it exists)."""
    path = f'{folder}/MI_{name}'
    if EAL.does_asset_exist(path):
        mi = unreal.load_asset(path)
    else:
        mi = AT.create_asset(f'MI_{name}', folder, unreal.MaterialInstanceConstant, unreal.MaterialInstanceConstantFactoryNew())
    MEL.set_material_instance_parent(mi, unreal.load_asset(latest()))
    for p, t in (('BaseColor', base_tex), ('ORM', orm_tex), ('Normal', normal_tex)):
        if t:
            t.set_editor_property('lod_group', unreal.TextureGroup.TEXTUREGROUP_CHARACTER)
            EAL.save_loaded_asset(t)
            MEL.set_material_instance_texture_parameter_value(mi, p, t)
    MEL.update_material_instance(mi)
    EAL.save_loaded_asset(mi)
    return mi


if __name__ == '__main__' and not EAL.does_asset_exist(f'{D}/M_GW_GenChar_v1') or '--rebuild' in (globals().get('UE_ARGS') or []):
    print('built', build().get_path_name())
