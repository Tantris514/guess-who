"""M_GW_Body: matte fabric/skin material for the mannequin bodies (replaces the plastic look).

Masks are computed from PreSkinnedPosition (reference pose, cm, Z up, X sideways):
  skin  = head/neck (z >= NeckZ)  or hands (|x| >= HandX)  or, when ArmsSkin = 1, the arms (|x| >= ArmX and z >= ArmZMin)
  else  = TorsoColor above HipZ, LegColor below.
MI_GW_Body_M (sleeves/trousers) and MI_GW_Body_F (bare arms) are the parents of the runtime MIDs (ApplyLook)."""
import unreal

EAL = unreal.EditorAssetLibrary
MEL = unreal.MaterialEditingLibrary
at = unreal.AssetToolsHelpers.get_asset_tools()
D = '/Game/GW/Characters/Materials'
# Never delete/rebuild a material in place in the shared interactive editor (a referenced delete opens a modal
# "in use" dialog and corrupts the package). Each rebuild creates the next free version and re-parents the MIs.
ver = 1
while EAL.does_asset_exist(f'{D}/M_GW_CharSkin_v{ver}'):
    ver += 1
NAME = f'M_GW_CharSkin_v{ver}'
P = f'{D}/{NAME}'
m = at.create_asset(NAME, D, unreal.Material, unreal.MaterialFactoryNew())
X0 = -1800


def E(cls, x, y):
    return MEL.create_material_expression(m, cls, x, y)


def scalar(name, val, x, y):
    e = E(unreal.MaterialExpressionScalarParameter, x, y)
    e.set_editor_property('parameter_name', name)
    e.set_editor_property('default_value', val)
    return e


def vec(name, col, x, y):
    e = E(unreal.MaterialExpressionVectorParameter, x, y)
    e.set_editor_property('parameter_name', name)
    e.set_editor_property('default_value', unreal.LinearColor(*col, 1.0))
    return e


def bin_op(cls, a, b, x, y, a_out='', b_out=''):
    e = E(cls, x, y)
    MEL.connect_material_expressions(a, a_out, e, 'A')
    MEL.connect_material_expressions(b, b_out, e, 'B')
    return e


def mask(src, r, g, b, x, y):
    e = E(unreal.MaterialExpressionComponentMask, x, y)
    e.set_editor_property('r', r); e.set_editor_property('g', g); e.set_editor_property('b', b); e.set_editor_property('a', False)
    MEL.connect_material_expressions(src, '', e, '')
    return e


def sat(src, x, y):
    e = E(unreal.MaterialExpressionSaturate, x, y)
    MEL.connect_material_expressions(src, '', e, '')
    return e


def const(v, x, y):
    e = E(unreal.MaterialExpressionConstant, x, y)
    e.set_editor_property('r', v)
    return e


def step(value, threshold, x, y, sharp=0.6):
    """saturate((value - threshold) * sharp): ~1.7 cm soft edge"""
    d = bin_op(unreal.MaterialExpressionSubtract, value, threshold, x, y)
    k = const(sharp, x, y + 60)
    mul = bin_op(unreal.MaterialExpressionMultiply, d, k, x + 150, y)
    return sat(mul, x + 300, y)


pre = E(unreal.MaterialExpressionPreSkinnedPosition, X0 - 400, 0)
# PreSkinnedPosition only exists in the vertex shader: pass it through a vertex interpolator
pos = E(unreal.MaterialExpressionVertexInterpolator, X0 - 200, 0)
MEL.connect_material_expressions(pre, '', pos, 'VS')
px = mask(pos, True, False, False, X0 + 200, -100)
pz = mask(pos, False, False, True, X0 + 200, 100)
ax = E(unreal.MaterialExpressionAbs, X0 + 380, -100)
MEL.connect_material_expressions(px, '', ax, '')

neck = step(pz, scalar('NeckZ', 151.0, X0 + 380, 200), X0 + 600, 150)
hand = step(ax, scalar('HandX', 44.0, X0 + 380, -250), X0 + 600, -250)
armx = step(ax, scalar('ArmX', 17.5, X0 + 380, -400), X0 + 600, -400)
armz = step(pz, scalar('ArmZMin', 100.0, X0 + 380, 350), X0 + 600, 350)
arm = bin_op(unreal.MaterialExpressionMultiply, armx, armz, X0 + 1000, -400)
arm2 = bin_op(unreal.MaterialExpressionMultiply, arm, scalar('ArmsSkin', 0.0, X0 + 1000, -550), X0 + 1150, -450)
skin1 = bin_op(unreal.MaterialExpressionMax, neck, hand, X0 + 1000, -50)
skin = bin_op(unreal.MaterialExpressionMax, skin1, arm2, X0 + 1300, -200)
hips = step(pz, scalar('HipZ', 92.0, X0 + 380, 500), X0 + 600, 500, sharp=0.3)

glovex = step(ax, scalar('GloveX', 30.0, X0 + 380, -700), X0 + 600, -700)
glove1 = bin_op(unreal.MaterialExpressionMultiply, glovex, armz, X0 + 1000, -700)
glove = bin_op(unreal.MaterialExpressionMultiply, glove1, scalar('GloveOn', 0.0, X0 + 1000, -850), X0 + 1150, -750)
legc = vec('LegColor', (0.018, 0.018, 0.02), X0 + 1000, 450)
torc = vec('TorsoColor', (0.02, 0.02, 0.022), X0 + 1000, 600)
cloth = E(unreal.MaterialExpressionLinearInterpolate, X0 + 1300, 500)
MEL.connect_material_expressions(legc, '', cloth, 'A')
MEL.connect_material_expressions(torc, '', cloth, 'B')
MEL.connect_material_expressions(hips, '', cloth, 'Alpha')
skinc = vec('SkinColor', (0.42, 0.27, 0.2), X0 + 1300, 300)
base = E(unreal.MaterialExpressionLinearInterpolate, X0 + 1550, 200)
MEL.connect_material_expressions(cloth, '', base, 'A')
MEL.connect_material_expressions(skinc, '', base, 'B')
MEL.connect_material_expressions(skin, '', base, 'Alpha')
gl = E(unreal.MaterialExpressionLinearInterpolate, X0 + 1750, 200)
MEL.connect_material_expressions(base, '', gl, 'A')
MEL.connect_material_expressions(vec('GloveColor', (0.75, 0.73, 0.68), X0 + 1550, -100), '', gl, 'B')
MEL.connect_material_expressions(glove, '', gl, 'Alpha')
base = gl
rough = E(unreal.MaterialExpressionLinearInterpolate, X0 + 1550, 450)
MEL.connect_material_expressions(scalar('ClothRoughness', 0.82, X0 + 1300, 700), '', rough, 'A')
MEL.connect_material_expressions(scalar('SkinRoughness', 0.55, X0 + 1300, 800), '', rough, 'B')
MEL.connect_material_expressions(skin, '', rough, 'Alpha')
# a touch of sheen on the fabric: low specular for cloth, normal for skin
spec = E(unreal.MaterialExpressionLinearInterpolate, X0 + 1550, 650)
MEL.connect_material_expressions(const(0.3, X0 + 1300, 900), '', spec, 'A')
MEL.connect_material_expressions(const(0.5, X0 + 1300, 950), '', spec, 'B')
MEL.connect_material_expressions(skin, '', spec, 'Alpha')
MEL.connect_material_property(base, '', unreal.MaterialProperty.MP_BASE_COLOR)
MEL.connect_material_property(rough, '', unreal.MaterialProperty.MP_ROUGHNESS)
MEL.connect_material_property(spec, '', unreal.MaterialProperty.MP_SPECULAR)
m.set_editor_property('used_with_skeletal_mesh', True)
MEL.recompile_material(m)
EAL.save_loaded_asset(m, False)


def mic(name, arms):
    p = f'{D}/{name}'
    mi = unreal.load_asset(p) if EAL.does_asset_exist(p) else at.create_asset(name, D, unreal.MaterialInstanceConstant, unreal.MaterialInstanceConstantFactoryNew())
    MEL.set_material_instance_parent(mi, m)
    MEL.set_material_instance_scalar_parameter_value(mi, 'ArmsSkin', arms)
    if arms:
        MEL.set_material_instance_scalar_parameter_value(mi, 'ArmX', 15.5)  # Quinn's shoulders are narrower
    MEL.update_material_instance(mi)
    EAL.save_loaded_asset(mi, False)
    return mi


mic('MI_GW_Body_M', 0.0)
mic('MI_GW_Body_F', 1.0)
print(NAME, 'expressions:', len(MEL.get_material_expressions(m)) if hasattr(MEL, 'get_material_expressions') else '?',
      'errors?', MEL.get_num_material_expressions(m) if hasattr(MEL, 'get_num_material_expressions') else '')
