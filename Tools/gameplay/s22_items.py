"""Import approved character_item GLBs from AssetGen/manifest.json and fit them on BP_GW_Character.

Items: mask_venetian -> MaskStaticMesh, hat_top -> TopHatMesh, hat_fedora -> FedoraMesh, revolver -> RevolverMesh.
GLB convention (assets agent): Y-up, front +Z, height normalised to 1 m, pivot = bbox centre.
After the glTF import (cm, Z-up, front +Y) each mesh gets a per-item relative transform in bone space
(HatRelTop/HatRelFedora/MaskRel on 'head', GunRel on 'weapon_r'), applied at runtime by ApplyLook.
Placeholders stay for items that are not approved yet. Optional arg: JSON {"item": {"size_cm": h, ...}} overrides.
"""
import sys, importlib, json, os
sys.path.insert(0, r'J:\Projets\Unreal_Projects\Guess Who\Tools\gameplay')
import gw_lib; importlib.reload(gw_lib)
from gw_lib import *

over = json.loads(UE_ARGS[0]) if UE_ARGS else {}
man = json.load(open(r'J:\Projets\Unreal_Projects\Guess Who\AssetGen\manifest.json', encoding='utf-8'))
items = {a['name']: a for a in man['assets'] if a.get('kind') == 'character_item' and a.get('status') == 'approved'}
print('approved character items:', sorted(items))
head_rot = unreal.MathLibrary.make_rotation_from_axes(unreal.Vector(0, 0, -1), unreal.Vector(0, 1, 0), unreal.Vector(1, 0, 0))
gun_rot = unreal.MathLibrary.make_rotation_from_axes(unreal.Vector(0, 1, 0), unreal.Vector(0, 0, 1), unreal.Vector(1, 0, 0))
# target sizes (cm) if the manifest has none: hats = height, mask = width, revolver = length
DEFAULT = {'hat_top': 18.0, 'hat_fedora': 12.0, 'mask_venetian': 17.0, 'revolver': 24.0}
SLOT = {'hat_top': 'TopHatMesh', 'hat_fedora': 'FedoraMesh', 'mask_venetian': 'MaskStaticMesh', 'revolver': 'RevolverMesh'}
MATVAR = {'hat_top': 'HatMatGuest', 'hat_fedora': 'HatMatSeeker', 'mask_venetian': 'MaskMat', 'revolver': 'GunMat'}


def import_glb(name, glb):
    dest = f'/Game/GW/Characters/Items/{name}'
    t = unreal.AssetImportTask()
    t.filename = glb; t.destination_path = dest; t.automated = True; t.replace_existing = True; t.save = True
    unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks([t])
    for p in t.get_editor_property('imported_object_paths'):
        a = unreal.load_asset(p)
        if isinstance(a, unreal.StaticMesh):
            ns = a.get_editor_property('nanite_settings')
            ns.set_editor_property('enabled', True)
            a.set_editor_property('nanite_settings', ns)
            EAL.save_loaded_asset(a, False)
            return a
    for p in EAL.list_assets(dest, recursive=True):
        a = unreal.load_asset(p)
        if isinstance(a, unreal.StaticMesh):
            return a
    raise RuntimeError(f'no static mesh imported for {name}')


def fit(name, mesh, size):
    b = mesh.get_bounding_box()
    mn, mx = b.min, b.max
    cx, cy, cz = (mn.x + mx.x) / 2, (mn.y + mx.y) / 2, (mn.z + mx.z) / 2
    if name.startswith('hat'):
        s = size / max(mx.z - mn.z, 0.01)
        f = unreal.Transform(unreal.Vector(-s * cx, -s * cy, -s * mn.z), unreal.Rotator(0, 0, 0), unreal.Vector(s, s, s))
        place = unreal.Transform(unreal.Vector(13.5, 1.0, 0.0), head_rot, unreal.Vector(1, 1, 1))
    elif name.startswith('mask'):
        s = size / max(mx.x - mn.x, 0.01)
        f = unreal.Transform(unreal.Vector(-s * cx, 11.8 - s * mx.y, -s * cz), unreal.Rotator(0, 0, 0), unreal.Vector(s, s, s))
        place = unreal.Transform(unreal.Vector(6.0, 1.2, 0.0), head_rot, unreal.Vector(1, 1, 1))
    else:  # revolver: barrel +Y, top +Z after import; grip = back-bottom of the bbox
        L, H = mx.y - mn.y, mx.z - mn.z
        s = size / max(L, 0.01)
        gx, gy, gz = cx, mn.y + 0.2 * L, mn.z + 0.3 * H
        f = unreal.Transform(unreal.Vector(-s * gx, -s * gy, -s * gz), unreal.Rotator(0, 0, 0), unreal.Vector(s, s, s))
        place = unreal.Transform(unreal.Vector(0, 0, 0), gun_rot, unreal.Vector(1, 1, 1))
    rel = unreal.MathLibrary.compose_transforms(f, place)
    print(f'{name}: bounds {[round(v, 1) for v in (mn.x, mn.y, mn.z, mx.x, mx.y, mx.z)]} scale {s:.4f}')
    return rel


ch = load_bp('BP_GW_Character')
c = cdo(ch)
for name, slot in SLOT.items():
    a = items.get(name)
    if not a or not a.get('files', {}).get('glb'):
        continue
    mesh = import_glb(name, a['files']['glb'])
    sz = over.get(name, {}).get('size_cm')
    if sz is None:
        dims = a.get('size_cm') or []
        if name.startswith('hat') and len(dims) == 3 and dims[2] > 0:
            sz = dims[2]
        elif name.startswith('mask') and len(dims) == 3 and dims[0] > 0:
            sz = dims[0]
        elif name == 'revolver' and len(dims) == 3 and max(dims) > 0:
            sz = max(dims)
        else:
            sz = DEFAULT[name]
    rel = fit(name, mesh, float(sz))
    c.set_editor_property(slot, mesh)
    c.set_editor_property(MATVAR[name], None)  # keep the generated textures
    relvar = {'hat_top': 'HatRelTop', 'hat_fedora': 'HatRelFedora', 'mask_venetian': 'MaskRel', 'revolver': 'GunRel'}[name]
    c.set_editor_property(relvar, rel)
    print('fitted', name, '->', slot, mesh.get_path_name())
compile_bp(ch)
save(ch)
