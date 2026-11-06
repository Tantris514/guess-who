"""Build BP_GW_Character's costume fit table + outfit pools from AssetGen/manifest.json.

- character_item (hat_top, hat_fedora, mask_venetian, revolver) and costume pieces (kind "costume") with
  status "approved" are imported (glTF/Interchange, Nanite on) into /Game/GW/Characters/Items/<name>.
- Each piece gets a bone + a bone-space transform computed from the body mesh's reference pose
  (SkeletonModifier, per body: Manny for men's pieces, Quinn for women's) and the piece's vertices.
- Placeholders (procedural OBJ) stay in the table so slots without approved assets keep working.
Usage: ue_run.py s25_costume_import.py [json overrides {"<name>": {"dz": cm, "dy": cm, "scale": k, "flare": k}}]
"""
import sys, importlib, json, os, math
sys.path.insert(0, r'J:\Projets\Unreal_Projects\Guess Who\Tools\gameplay')
import gw_lib; importlib.reload(gw_lib)
from gw_lib import *

OV = json.loads(UE_ARGS[0]) if UE_ARGS and UE_ARGS[0].startswith('{') else {}
# measured fits (Tools/qa/hair_fit.py, ray-cast scalp coverage on the mannequin skulls): the real-size hair shells
# were cut from narrower heads, so crowns and temples showed through (chignon covered 60 % of the scalp, the bob 77 %).
# Now 96 / 93 / 92 % with the face clear. Command-line overrides still win.
FIT_DEFAULTS = {'hair_chignon': {'scale': 1.18, 'dz': 1.5, 'dy': 2.0},
                'hair_fingerwave_bob': {'scale': 1.12, 'dz': 0.75, 'dy': 1.0},
                'hair_wavy_back': {'scale': 1.18, 'dz': 0.75, 'dy': 4.0}}
for _n, _o in FIT_DEFAULTS.items():
    OV[_n] = {**_o, **OV.get(_n, {})}
MAN = json.load(open(r'J:\Projets\Unreal_Projects\Guess Who\AssetGen\manifest.json', encoding='utf-8'))
BODY = {'m': unreal.load_asset('/Game/Characters/Mannequins/Meshes/SKM_Manny_Simple'),
        'f': unreal.load_asset('/Game/Characters/Mannequins/Meshes/SKM_Quinn_Simple')}
_bones = {}


def bone(body, name):
    key = (body, name)
    if key not in _bones:
        mod = unreal.SkeletonModifier()
        mod.set_skeletal_mesh(BODY[body])
        _bones[key] = mod.get_bone_transform(name, True)
    return _bones[key]


def import_glb(name, glb):
    dest = f'/Game/GW/Characters/Items/{name}'
    found = [p for p in EAL.list_assets(dest, recursive=True)] if EAL.does_directory_exist(dest) else []
    meshes = [unreal.load_asset(p) for p in found if p.split('.')[-1] == name or '/StaticMeshes/' in p]
    meshes = [m for m in meshes if isinstance(m, unreal.StaticMesh)]
    if not meshes or OV.get(name, {}).get('reimport'):
        t = unreal.AssetImportTask()
        t.filename = glb; t.destination_path = dest; t.automated = True; t.replace_existing = True; t.save = True
        unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks([t])
        meshes = [unreal.load_asset(p) for p in t.get_editor_property('imported_object_paths')]
        meshes = [m for m in meshes if isinstance(m, unreal.StaticMesh)]
    m = meshes[0]
    ns = m.get_editor_property('nanite_settings')
    if not ns.get_editor_property('enabled'):
        ns.set_editor_property('enabled', True)
        m.set_editor_property('nanite_settings', ns)
        EAL.save_loaded_asset(m, False)
    return m


def verts(mesh, step=7):
    md = mesh.get_static_mesh_description(0)
    n = md.get_vertex_count()
    out = []
    for i in range(0, n, max(1, step if n > 4000 else 1)):
        v = md.get_vertex_position(unreal.VertexID(i))
        out.append((v.x, v.y, v.z))
    return out


def band(vs, z0, z1):
    sel = [v for v in vs if z0 <= v[2] <= z1]
    return sel or vs


def comp_to_bone(body, bname, s, t):
    """piece transform in body component space (scale s then translate t) -> relative to the bone."""
    tc = unreal.Transform(unreal.Vector(*t), unreal.Rotator(0, 0, 0), unreal.Vector(*s))
    return unreal.MathLibrary.make_relative_transform(tc, bone(body, bname))


COLORS = {'black': (0.012, 0.012, 0.014), 'blue': (0.012, 0.02, 0.07), 'emerald': (0.008, 0.09, 0.045),
          'champagne': (0.5, 0.42, 0.28), 'burgundy': (0.16, 0.012, 0.025), 'white': (0.7, 0.68, 0.64),
          'ivory': (0.6, 0.55, 0.45), 'satin': (0.45, 0.4, 0.33), 'gold': (0.5, 0.36, 0.12)}


def color_of(name, notes=''):
    for k, c in COLORS.items():
        if k in name:
            return c
    for k, c in COLORS.items():
        if k in notes.lower():
            return c
    return (0.03, 0.03, 0.035)


def slot_of(a):
    s = (a.get('slot') or '').lower()
    n = a['name'].lower()
    if 'seeker' in s or 'detective' in n:                         # the detective's own coat, never in a guest pool
        return 'seekercoat'
    if 'skirt' in s or n.startswith('skirt'):
        return 'skirt'
    if 'stole' in s or n.startswith('stole'):
        return 'stole'
    if 'bodice' in s or n.startswith('bodice') or s in ('torso_f', 'top_f'):
        return 'bodice'
    if 'coat' in s or 'jacket' in s or n.startswith('coat') or s in ('torso_m', 'torso'):
        return 'coat'
    if 'hair' in s or n.startswith('hair'):
        female = any(w in (n + ' ' + s + ' ' + (a.get('notes') or '').lower()) for w in ('bob', 'chignon', 'women', 'female', 'ladies', '_f'))
        return 'hair_f' if female else 'hair_m'
    if 'mask' in s or n.startswith('mask'):
        return 'mask'
    if 'cloche' in n or 'cloche' in s:
        return 'cloche'
    if 'hat_top' in n:
        return 'tophat'
    if 'fedora' in n:
        return 'fedora'
    if 'revolver' in n:
        return 'revolver'
    if 'glove' in s or 'glove' in n:
        return 'gloves'
    return None


def fit(slot, mesh, name, entry=None):
    """-> (bone, rel transform, body)"""
    o = OV.get(name, {})
    if slot == 'seekercoat':                                       # placed like any coat on Manny
        slot = 'coat'
    vs = verts(mesh)
    xs, ys, zs = [v[0] for v in vs], [v[1] for v in vs], [v[2] for v in vs]
    mnx, mxx, mny, mxy, mnz, mxz = min(xs), max(xs), min(ys), max(ys), min(zs), max(zs)
    if (entry or {}).get('fit_bounds'):        # frozen before Tools/qa/garment_wrap.py pushed the cloth off the body
        mnx, mxx, mny, mxy, mnz, mxz = entry['fit_bounds']
    W, D, H = mxx - mnx, mxy - mny, mxz - mnz
    cx, cy = (mnx + mxx) / 2, (mny + mxy) / 2
    k = o.get('scale', 1.0)
    # real-size scale from the assets agent (glb units -> cm); UE imported 1 glb unit = 100 cm
    real = ((entry or {}).get('orientation') or {}).get('uniform_scale_to_cm')
    rs = (real / 100.0 * k) if real else None
    if slot == 'skirt' and rs:
        body = 'f'
        pel = bone(body, 'pelvis').translation
        # TRELLIS gowns are slim bias-cut: widen a little and deepen more so hips and a walking stride stay inside
        flare = o.get('flare', 1.2)
        top = band(vs, mxz - 0.08 * H, mxz)
        tcx = (max(v[0] for v in top) + min(v[0] for v in top)) / 2
        tcy = (max(v[1] for v in top) + min(v[1] for v in top)) / 2
        t = (-rs * flare * tcx, pel.y + 1.0 + o.get('dy', 0) - rs * flare * o.get('flare_y', 1.4) * tcy, 1.5 + o.get('dz', 0) - rs * mnz)
        return 'pelvis', comp_to_bone(body, 'pelvis', (rs * flare, rs * flare * o.get('flare_y', 1.4), rs), t), body
    if slot in ('bodice', 'coat', 'stole') and rs:
        body = 'm' if slot == 'coat' else 'f'
        spine = bone(body, 'spine_03').translation
        neck = bone(body, 'neck_01').translation
        if slot == 'bodice':        # meets the skirt cut: gown pieces share the real scale; overlap 2 cm to hide the seam
            suffix = name.split('_', 1)[-1]
            sk = next((x for x in MAN['assets'] if x['name'] == 'skirt_' + suffix), None)
            skirt_len = (sk or {}).get('size_cm', [0, 0, 112.0])[2] or 112.0
            bottom = 1.5 + skirt_len - 2.0 + o.get('dz', 0)
            fx, fy = o.get('flare', 1.0), o.get('flare_y', 1.0)    # bust/back room (Tools/qa/garment_fit.py)
            t = (-rs * fx * cx, spine.y + o.get('dy', 0) - rs * fy * cy, bottom - rs * mnz)
            return 'spine_03', comp_to_bone(body, 'spine_03', (rs * fx, rs * fy, rs), t), body
        else:                       # coats / stoles: collar at the neck
            topz = neck.z + (4.0 if slot == 'coat' else -1.0) + o.get('dz', 0)
            # dress-form shells are slimmer than the mannequin: open them up so back/shoulders stay inside
            fx = o.get('flare', 1.13 if slot == 'coat' else 1.0)
            fy = o.get('flare_y', 1.22 if slot == 'coat' else 1.0)
            t = (-rs * fx * cx, spine.y + o.get('dy', -1.0) - rs * fy * cy, topz - rs * mxz)
            bname = 'spine_05' if slot == 'stole' else 'spine_03'
            return bname, comp_to_bone(body, bname, (rs * fx, rs * fy, rs), t), body
        bname = 'spine_03'
        return bname, comp_to_bone(body, bname, (rs, rs, rs), t), body
    if slot == 'skirt':
        body = 'f'
        pel = bone(body, 'pelvis').translation
        waist = pel.z + 7.0 + o.get('dz', 0)                      # waistband a bit above the pelvis joint
        s = (waist - 1.0) / H * k                                  # hem ~1 cm above the floor
        top = band(vs, mxz - 0.08 * H, mxz)
        tw = max(v[0] for v in top) - min(v[0] for v in top)
        tcx = (max(v[0] for v in top) + min(v[0] for v in top)) / 2
        tcy = (max(v[1] for v in top) + min(v[1] for v in top)) / 2
        sxy = s
        if tw * s < 33.0:                                          # waistband must clear the hips
            sxy = 33.0 / tw
        sxy *= o.get('flare', 1.0)
        t = (-sxy * tcx, pel.y + 1.0 + o.get('dy', 0) - sxy * tcy, waist - s * mxz)
        return 'pelvis', comp_to_bone(body, 'pelvis', (sxy, sxy, s), t), body
    if slot in ('coat', 'bodice', 'stole'):
        body = 'm' if slot == 'coat' else 'f'
        neck = bone(body, 'neck_01').translation
        ua = bone(body, 'upperarm_r').translation
        shoulders = 2 * abs(ua.x) + (8.0 if slot == 'coat' else 5.0) + (12.0 if slot == 'stole' else 0.0)
        top = band(vs, mxz - 0.25 * H, mxz)                        # shoulder line = widest part of the top quarter
        sw = max(v[0] for v in top) - min(v[0] for v in top)
        s = shoulders / sw * k
        topz = neck.z + (2.0 if slot == 'coat' else -2.0) + o.get('dz', 0)
        bname = 'spine_05' if slot == 'stole' else 'spine_03'
        spine = bone(body, 'spine_03').translation
        t = (-s * cx, spine.y + o.get('dy', 0) - s * cy, topz - s * mxz)
        return bname, comp_to_bone(body, bname, (s, s, s), t), body
    if slot in ('hair_m', 'hair_f'):
        body = 'f' if slot == 'hair_f' else 'm'
        head = bone(body, 'head').translation
        s = rs if rs else (20.5 if slot == 'hair_f' else 19.0) / W * k
        topz = 181.5 + o.get('dz', 0)
        t = (-s * cx, 10.0 + head.y + o.get('dy', 0) - s * mxy, topz - s * mxz)  # fringe at the forehead
        return 'head', comp_to_bone(body, 'head', (s, s, s), t), body
    if slot == 'mask':
        body = 'm'
        head = bone(body, 'head').translation
        s = rs if rs else 18.5 / W * k
        cz = (mnz + mxz) / 2
        # front of the mask ~15 cm ahead of the head bone (the mannequin face protrudes to ~13.5 at eye level)
        t = (-s * cx, head.y + 15.0 + o.get('dy', 0) - s * mxy, head.z + 6.5 + o.get('dz', 0) - s * cz)
        return 'head', comp_to_bone(body, 'head', (s, s, s), t), body
    if slot in ('tophat', 'fedora', 'cloche'):
        body = 'm' if slot != 'cloche' else 'f'
        head = bone(body, 'head').translation
        h = {'tophat': 19.0, 'fedora': 15.0, 'cloche': 14.0}[slot]
        s = h / H * k
        basez = {'tophat': 176.0, 'fedora': 175.0, 'cloche': 170.5}[slot] + o.get('dz', 0)
        t = (-s * cx, head.y + 1.0 + o.get('dy', 0) - s * cy, basez - s * mnz)
        return 'head', comp_to_bone(body, 'head', (s, s, s), t), body
    if slot == 'revolver':                                         # barrel +Y, top +Z after import
        # held in the right hand: SKM_Manny_Simple has no weapon_r bone, and attaching to it fell back to the
        # component root (the gun lay on the floor between the detective's feet)
        s = 24.0 / D * k
        gx, gy, gz = cx, mny + 0.2 * D, mnz + 0.3 * H
        f = unreal.Transform(unreal.Vector(-s * gx, -s * gy, -s * gz), unreal.Rotator(0, 0, 0), unreal.Vector(s, s, s))
        hand, mid = bone('m', 'hand_r').translation, bone('m', 'middle_01_r').translation
        idx, pinky = bone('m', 'index_01_r').translation, bone('m', 'pinky_01_r').translation
        # "low ready" (camera agent, 2026-11-03, user: "the gun in his hand is glitchy"): with the barrel along the
        # fingers, the relaxed (unarmed) hand hanging at the side held the revolver straight down, the grip poking out
        # in front of the open fingers. Now the grip runs down the palm along the fingers and the barrel leaves the
        # thumb / index web, tilted 'tilt' degrees from the thumb direction (forward when the arm hangs) toward the
        # fingers: pointed forward-down, as a detective carries it. Rendered check: Tools/gameplay/gunshot_render.ps1.
        fing = (mid - hand).normal()                               # the fingers (down when the arm hangs)
        thumb = idx - pinky                                        # across the palm, thumb side
        thumb = (thumb - fing * thumb.dot(fing)).normal()
        th = math.radians(o.get('tilt', 35.0))
        fwd = (thumb * math.cos(th) + fing * math.sin(th)).normal()   # barrel
        up = (thumb * math.sin(th) - fing * math.cos(th)).normal()    # top of the gun; the grip hangs along the fingers
        side = fwd.cross(up)
        grip = hand + (mid - hand) * o.get('along', 0.4) + side * o.get('side', 0.0) + up * o.get('dz', 0.0)
        rot = unreal.MathLibrary.make_rotation_from_axes(side, fwd, up)
        comp = unreal.MathLibrary.compose_transforms(f, unreal.Transform(grip, rot, unreal.Vector(1, 1, 1)))
        return 'hand_r', unreal.MathLibrary.make_relative_transform(comp, bone('m', 'hand_r')), 'm'
    return None


# ---------------------------------------------------------------------------------------------------------
ch = load_bp('BP_GW_Character')
c = cdo(ch)
pools = {k: [] for k in ('PoolShellM', 'PoolShellF', 'PoolSkirt', 'PoolHairM', 'PoolHairF', 'PoolMask')}
fit_meshes, fit_rels, fit_bones, fit_cols = [], [], [], []
singles = {}
A = '/Game/GW/Characters/Accessories/'


def add_fit(mesh, bname, rel, col):
    if mesh in fit_meshes:
        i = fit_meshes.index(mesh)
        fit_rels[i], fit_bones[i], fit_cols[i] = rel, unreal.Name(bname), unreal.LinearColor(*col, 1.0)
    else:
        fit_meshes.append(mesh); fit_rels.append(rel); fit_bones.append(unreal.Name(bname)); fit_cols.append(unreal.LinearColor(*col, 1.0))


# placeholders (procedural, modelled in canonical accessory space)
head_rot = unreal.MathLibrary.make_rotation_from_axes(unreal.Vector(0, 0, -1), unreal.Vector(0, 1, 0), unreal.Vector(1, 0, 0))
ph = {'SM_GW_TopHat': ('head', unreal.Transform(unreal.Vector(13.5, 1.0, 0), head_rot, unreal.Vector(1, 1, 1))),
      'SM_GW_Fedora': ('head', unreal.Transform(unreal.Vector(13.5, 1.0, 0), head_rot, unreal.Vector(1, 1, 1))),
      'SM_GW_Mask': ('head', unreal.Transform(unreal.Vector(6.0, 1.2, 0), head_rot, unreal.Vector(1, 1, 1))),
      'SM_GW_Revolver': ('weapon_r', unreal.Transform())}
for n, (b, rel) in ph.items():
    add_fit(unreal.load_asset(A + n), b, rel, (0.02, 0.02, 0.02))
singles = {'tophat': unreal.load_asset(A + 'SM_GW_TopHat'), 'fedora': unreal.load_asset(A + 'SM_GW_Fedora'),
           'revolver': unreal.load_asset(A + 'SM_GW_Revolver'), 'cloche': None}
mask_placeholder = unreal.load_asset(A + 'SM_GW_Mask')

report = []
for a in MAN['assets']:
    if a.get('status') != 'approved' or a.get('kind') not in ('character_item', 'costume'):
        continue
    slot = slot_of(a)
    glb = a.get('files', {}).get('glb')
    if not slot or not glb or not os.path.exists(glb) or slot == 'gloves':
        report.append(f'skip {a["name"]} slot={slot}')
        continue
    mesh = import_glb(a['name'], glb)
    r = fit(slot, mesh, a['name'], a)
    if not r:
        continue
    bname, rel, body = r
    add_fit(mesh, bname, rel, color_of(a['name'], a.get('notes') or ''))
    target = {'skirt': 'PoolSkirt', 'coat': 'PoolShellM', 'bodice': 'PoolShellF',
              'hair_m': 'PoolHairM', 'hair_f': 'PoolHairF', 'mask': 'PoolMask'}.get(slot)
    if target:
        pools[target].append(mesh)
    else:
        singles[slot] = mesh
    report.append(f'{a["name"]:22s} {slot:8s} -> {bname:9s} scale {rel.scale3d.x:.3f}/{rel.scale3d.z:.3f}')

# skirts and bodices cut from the same gown share their colour suffix: sort both by it so index k matches
for key in ('PoolSkirt', 'PoolShellF', 'PoolShellM', 'PoolHairM', 'PoolHairF', 'PoolMask'):
    pools[key].sort(key=lambda m: m.get_name().split('_', 1)[-1])
if not pools['PoolMask']:
    pools['PoolMask'] = [mask_placeholder]
for k, v in pools.items():
    c.set_editor_property(k, v)
c.set_editor_property('TopHatMesh', singles['tophat'])
c.set_editor_property('FedoraMesh', singles['fedora'])
c.set_editor_property('RevolverMesh', singles['revolver'])
c.set_editor_property('ClocheMesh', singles.get('cloche'))
c.set_editor_property('StoleMesh', singles.get('stole'))
c.set_editor_property('SeekerShell', singles.get('seekercoat'))
c.set_editor_property('FitMeshes', fit_meshes)
c.set_editor_property('FitRels', fit_rels)
c.set_editor_property('FitBones', fit_bones)
c.set_editor_property('FitColors', fit_cols)
c.set_editor_property('NumPerBody', 16)
c.set_editor_property('BodyMatM', unreal.load_asset('/Game/GW/Characters/Materials/MI_GW_Body_M'))
c.set_editor_property('BodyMatF', unreal.load_asset('/Game/GW/Characters/Materials/MI_GW_Body_F'))
SKIN = [(0.42, 0.27, 0.20), (0.55, 0.38, 0.29), (0.30, 0.18, 0.12), (0.62, 0.45, 0.36), (0.20, 0.12, 0.08), (0.48, 0.32, 0.24)]
c.set_editor_property('SkinTones', [unreal.LinearColor(*t, 1.0) for t in SKIN])
compile_bp(ch, quiet=True)
save(ch)
gm = load_bp('BP_GW_GameMode')
cdo(gm).set_editor_property('NumOutfits', 32)
compile_bp(gm, quiet=True)
save(gm)
print('\n'.join(report))
print('pools', {k: [m.get_name() for m in v] for k, v in pools.items()}, 'fits', len(fit_meshes))
