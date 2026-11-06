"""Fit accessory components on BP_GW_Character and assign meshes/materials (placeholders or imported assets)."""
import sys, importlib, json
sys.path.insert(0, r'J:\Projets\Unreal_Projects\Guess Who\Tools\gameplay')
import gw_lib; importlib.reload(gw_lib)
from gw_lib import *
cfg = json.loads(UE_ARGS[0]) if UE_ARGS else {}
ch = load_bp('BP_GW_Character')
lib = unreal.SubobjectDataBlueprintFunctionLibrary
comps = subobjects(ch)
# bone 'head' frame: X up, Y forward, Z side. Accessories are modelled Z-up / Y-forward.
head_rot = unreal.MathLibrary.make_rotation_from_axes(unreal.Vector(0, 0, -1), unreal.Vector(0, 1, 0), unreal.Vector(1, 0, 0))
fits = {
    'HatMesh': cfg.get('HatMesh', [[13.5, 1.0, 0.0], 1.0]),
    'MaskMesh': cfg.get('MaskMesh', [[6.0, 1.2, 0.0], 1.0]),
}
for name, (loc, scale) in fits.items():
    t = lib.get_object(comps[name][1])
    t.set_editor_property('relative_location', unreal.Vector(*loc))
    t.set_editor_property('relative_rotation', head_rot)
    t.set_editor_property('relative_scale3d', unreal.Vector(scale, scale, scale))
g = lib.get_object(comps['GunMesh'][1])
gl, gr, gs = cfg.get('GunMesh', [[0, 0, 0], [0, 0, 0], 1.0])
g.set_editor_property('relative_location', unreal.Vector(*gl))
g.set_editor_property('relative_rotation', unreal.Rotator(*gr))
g.set_editor_property('relative_scale3d', unreal.Vector(gs, gs, gs))
c = cdo(ch)
A = '/Game/GW/Characters/Accessories/'
M = '/Game/GW/Characters/Materials/'
assign = {
    'TopHatMesh': cfg.get('TopHatMesh', A + 'SM_GW_TopHat'), 'FedoraMesh': cfg.get('FedoraMesh', A + 'SM_GW_Fedora'),
    'MaskStaticMesh': cfg.get('MaskStaticMesh', A + 'SM_GW_Mask'), 'RevolverMesh': cfg.get('RevolverMesh', A + 'SM_GW_Revolver'),
    'HatMatGuest': cfg.get('HatMatGuest', M + 'MI_GW_Hat_Black'), 'HatMatSeeker': cfg.get('HatMatSeeker', M + 'MI_GW_Hat_Fedora'),
    'MaskMat': cfg.get('MaskMat', M + 'MI_GW_Mask_Gold'), 'GunMat': cfg.get('GunMat', M + 'MI_GW_Gun'),
}
for k, p in assign.items():
    c.set_editor_property(k, unreal.load_asset(p) if p else None)


def tr(loc, rot, scale):
    return unreal.Transform(unreal.Vector(*loc), rot, unreal.Vector(scale, scale, scale))


# per-item relative transforms applied at runtime by ApplyLook (bone space of 'head' / 'weapon_r')
c.set_editor_property('HatRelTop', tr(*cfg.get('HatRelTop', [fits['HatMesh'][0], head_rot, fits['HatMesh'][1]])))
c.set_editor_property('HatRelFedora', tr(*cfg.get('HatRelFedora', [fits['HatMesh'][0], head_rot, fits['HatMesh'][1]])))
c.set_editor_property('MaskRel', tr(*cfg.get('MaskRel', [fits['MaskMesh'][0], head_rot, fits['MaskMesh'][1]])))
c.set_editor_property('GunRel', tr(gl, unreal.Rotator(*gr), gs))
compile_bp(ch)
save(ch)
c = cdo(load_bp('BP_GW_Character'))
print({k: (c.get_editor_property(k).get_name() if c.get_editor_property(k) else None) for k in assign})
print('hat rel', lib.get_object(subobjects(ch)['HatMesh'][1]).get_editor_property('relative_location'))
