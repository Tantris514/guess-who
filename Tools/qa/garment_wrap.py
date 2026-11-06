"""Push bodices and coats off the mannequin where the body comes through (editor: ue_run.py garment_wrap.py [name ...]).

The cloth pieces are rigid shells cut from dress forms slimmer than the UE mannequins: in the reference pose the body
showed through 25-63 % of each bodice and a third of each coat (Tools/qa/garment_fit.py). Inflating the whole piece
until nothing pokes through made them puffy (4-5 cm of air all round), so instead the cloth is pushed out only where
the body intrudes:
  - placement exactly as s25_costume_import.py computes it (same bone, defaults, bounds);
  - around the body's centre line, per 1 cm height x 5 degree sector, the skin radius (ray from inside, so the arms
    never count) is compared with the innermost cloth vertex; the shortfall + CLEAR cm is the push for that cell;
  - the push field is dilated and blurred so the cloth bulges smoothly, and every vertex of the cell moves by it
    (outer and inner layers alike: the cloth keeps its thickness);
  - the mesh is written back to the static mesh asset (normals recomputed, materials and Nanite kept), and the
    original bounds are frozen in the manifest ("fit_bounds") so s25 keeps placing the piece the same way.
Re-run after any re-import of a piece from its GLB. Prints the show-through before / after for each piece.
"""
import json
import math
import unreal

GS = unreal.GeometryScript_AssetUtils
SP = unreal.GeometryScript_MeshSpatial
MQ = unreal.GeometryScript_MeshQueries
ME = unreal.GeometryScript_MeshEdits
LS = unreal.GeometryScript_List
MAN_PATH = r'J:\Projets\Unreal_Projects\Guess Who\AssetGen\manifest.json'
MAN = json.load(open(MAN_PATH, encoding='utf-8'))
BODY = {'m': unreal.load_asset('/Game/Characters/Mannequins/Meshes/SKM_Manny_Simple'),
        'f': unreal.load_asset('/Game/Characters/Mannequins/Meshes/SKM_Quinn_Simple')}
CLEAR = 1.0                       # cm of air kept between skin and cloth (walk-cycle spine bend)
DZ_BIN, AZ_BINS = 1.0, 72
# s25_costume_import.fit defaults for these slots (keep in sync)
DEFAULTS = {'bodice': {'flare': 1.0, 'flare_y': 1.0, 'dy': 0.0, 'dz': 0.0},
            'coat': {'flare': 1.13, 'flare_y': 1.22, 'dy': -1.0, 'dz': 0.0}}
ARGS = [a for a in (globals().get('UE_ARGS') or [])]
_bones = {}


def bone(body, name):
    if (body, name) not in _bones:
        mod = unreal.SkeletonModifier()
        mod.set_skeletal_mesh(BODY[body])
        _bones[(body, name)] = mod.get_bone_transform(name, True).translation
    return _bones[(body, name)]


def pick(res, typ):
    return next(x for x in (res if isinstance(res, tuple) else (res,)) if isinstance(x, typ))


def with_bvh(dm):
    return dm, pick(SP.build_bvh_for_mesh(dm), unreal.GeometryScriptDynamicMeshBVH)


def hit(mesh, bvh, origin, d):
    h = pick(SP.find_nearest_ray_intersection_with_mesh(mesh, bvh, origin, d, unreal.GeometryScriptSpatialQueryOptions()),
             unreal.GeometryScriptRayHitResult)
    return h.hit_position if h.hit else None


def verts(mesh, step=7):          # same sampling as s25_costume_import.verts
    md = mesh.get_static_mesh_description(0)
    n = md.get_vertex_count()
    return [(lambda v: (v.x, v.y, v.z))(md.get_vertex_position(unreal.VertexID(i)))
            for i in range(0, n, max(1, step if n > 4000 else 1))]


bodies = {}
for b in ('m', 'f'):
    dm = unreal.DynamicMesh()
    GS.copy_mesh_from_skeletal_mesh(BODY[b], dm, unreal.GeometryScriptCopyMeshFromAssetOptions(), unreal.GeometryScriptMeshReadLOD())
    bodies[b] = with_bvh(dm)
CHAIN = ('pelvis', 'spine_01', 'spine_02', 'spine_03', 'spine_04', 'spine_05', 'neck_01')


def axis_y(b, z):
    pts = sorted((bone(b, n).z, bone(b, n).y) for n in CHAIN)
    if z <= pts[0][0]:
        return pts[0][1]
    for (z0, y0), (z1, y1) in zip(pts, pts[1:]):
        if z0 <= z <= z1:
            return y0 + (y1 - y0) * (z - z0) / max(1e-3, z1 - z0)
    return pts[-1][1]


_skin = {}


def skin_r(b, zi, ai):
    """skin radius around the centre line at height bin zi, sector ai (None: no torso there)."""
    key = (b, zi, ai)
    if key not in _skin:
        z = zi * DZ_BIN
        a = 2 * math.pi * (ai + 0.5) / AZ_BINS
        o = unreal.Vector(0.0, axis_y(b, z), z)
        p = hit(*bodies[b], o, unreal.Vector(math.cos(a), math.sin(a), 0.0))
        _skin[key] = None if p is None else math.hypot(p.x - o.x, p.y - o.y)
    return _skin[key]


def smooth(field, zis, passes=2):
    """dilate (max 3x3) then blur (3x3 binomial), wrapping around in azimuth."""
    def get(f, zi, ai):
        return f.get((zi, ai % AZ_BINS), 0.0)
    dil = {(zi, ai): max(get(field, zi + i, ai + j) for i in (-1, 0, 1) for j in (-1, 0, 1)) for zi in zis for ai in range(AZ_BINS)}
    f = dil
    for _ in range(passes):
        w = {-1: 1, 0: 2, 1: 1}
        f = {(zi, ai): sum(get(f, zi + i, ai + j) * w[i] * w[j] for i in (-1, 0, 1) for j in (-1, 0, 1)) / 16.0
             for zi in zis for ai in range(AZ_BINS)}
    return {k: max(v, field.get(k, 0.0)) for k, v in f.items()}


def show_through(b, pos, zr):
    """fraction of occupied cells where the innermost cloth is closer than CLEAR/2 to the skin."""
    inner = {}
    for (x, y, z) in pos:
        if not zr[0] <= z <= zr[1]:
            continue
        ay = axis_y(b, z)
        zi, ai = int(round(z / DZ_BIN)), int((math.atan2(y - ay, x) % (2 * math.pi)) / (2 * math.pi) * AZ_BINS) % AZ_BINS
        r = math.hypot(x, y - ay)
        inner[(zi, ai)] = min(r, inner.get((zi, ai), 1e9))
    bad = [k for k, r in inner.items() if skin_r(b, *k) is not None and r < skin_r(b, *k) + CLEAR * 0.5]
    return len(bad) / max(1, len(inner)), inner


man_changed = False
for e in MAN['assets']:
    n = e['name']
    if e.get('status') != 'approved' or e.get('kind') != 'costume' or not n.startswith(('bodice', 'coat')) or (ARGS and n not in ARGS):
        continue
    slot = 'bodice' if n.startswith('bodice') else 'coat'
    b = 'f' if slot == 'bodice' else 'm'
    sm = next((unreal.load_asset(p) for p in unreal.EditorAssetLibrary.list_assets(f'/Game/GW/Characters/Items/{n}', recursive=True)
               if isinstance(unreal.load_asset(p), unreal.StaticMesh)), None)
    if not e.get('fit_bounds'):
        vs = verts(sm)
        xs, ys, zs = [v[0] for v in vs], [v[1] for v in vs], [v[2] for v in vs]
        e['fit_bounds'] = [min(xs), max(xs), min(ys), max(ys), min(zs), max(zs)]
        man_changed = True
    mnx, mxx, mny, mxy, mnz, mxz = e['fit_bounds']
    cx, cy = (mnx + mxx) / 2, (mny + mxy) / 2
    rs = e['orientation']['uniform_scale_to_cm'] / 100.0
    p = DEFAULTS[slot]
    spine, neck = bone(b, 'spine_03'), bone(b, 'neck_01')
    s = (rs * p['flare'], rs * p['flare_y'], rs)
    if slot == 'bodice':
        sk = next((x for x in MAN['assets'] if x['name'] == 'skirt_' + n.split('_', 1)[-1]), None)
        skirt_len = (sk or {}).get('size_cm', [0, 0, 112.0])[2] or 112.0
        t = (-s[0] * cx, spine.y + p['dy'] - s[1] * cy, 1.5 + skirt_len - 2.0 + p['dz'] - s[2] * mnz)
    else:
        t = (-s[0] * cx, spine.y + p['dy'] - s[1] * cy, neck.z + 4.0 + p['dz'] - s[2] * mxz)
    zr = (bone(b, 'thigh_l').z, neck.z - 2.0)                       # hips up to below the collar

    dm = unreal.DynamicMesh()
    GS.copy_mesh_from_static_mesh(sm, dm, unreal.GeometryScriptCopyMeshFromAssetOptions(), unreal.GeometryScriptMeshReadLOD())
    plist = pick(MQ.get_all_vertex_positions(dm, False), unreal.GeometryScriptVectorList)
    local = LS.convert_vector_list_to_array(plist)
    comp = [(v.x * s[0] + t[0], v.y * s[1] + t[1], v.z * s[2] + t[2]) for v in local]
    before, inner = show_through(b, comp, zr)
    push = {}
    for k, r in inner.items():
        rb = skin_r(b, *k)
        if rb is not None and r < rb + CLEAR:
            push[k] = rb + CLEAR - r
    zis = sorted({k[0] for k in inner})
    field = smooth(push, list(range(zis[0] - 3, zis[-1] + 4))) if zis else {}

    def at(z, ai_f):
        zf = z / DZ_BIN
        z0, a0 = int(math.floor(zf)), int(math.floor(ai_f))
        fz, fa = zf - z0, ai_f - a0
        g = lambda zi, ai: field.get((zi, ai % AZ_BINS), 0.0)
        return ((g(z0, a0) * (1 - fa) + g(z0, a0 + 1) * fa) * (1 - fz) + (g(z0 + 1, a0) * (1 - fa) + g(z0 + 1, a0 + 1) * fa) * fz)

    out, moved, maxd = [], 0, 0.0
    for (x, y, z), v in zip(comp, local):
        ay = axis_y(b, z)
        ang = math.atan2(y - ay, x) % (2 * math.pi)
        d = at(z, ang / (2 * math.pi) * AZ_BINS - 0.5) if zr[0] - 4 <= z <= zr[1] + 4 else 0.0
        if d > 1e-3:
            r = max(1e-3, math.hypot(x, y - ay))
            x, y = x + x / r * d, y + (y - ay) / r * d
            moved += 1
            maxd = max(maxd, d)
        out.append(unreal.Vector((x - t[0]) / s[0], (y - t[1]) / s[1], (z - t[2]) / s[2]))
    after, _ = show_through(b, [((v.x * s[0] + t[0]), (v.y * s[1] + t[1]), (v.z * s[2] + t[2])) for v in out], zr)
    ME.set_all_mesh_vertex_positions(dm, pick(LS.convert_array_to_vector_list(out), unreal.GeometryScriptVectorList))
    unreal.GeometryScript_Normals.recompute_normals(dm, unreal.GeometryScriptCalculateNormalsOptions())
    opts = unreal.GeometryScriptCopyMeshToAssetOptions()
    opts.set_editor_property('enable_recompute_normals', False)
    opts.set_editor_property('enable_recompute_tangents', True)
    opts.set_editor_property('replace_materials', False)
    opts.set_editor_property('apply_nanite_settings', False)
    GS.copy_mesh_to_static_mesh(dm, sm, opts, unreal.GeometryScriptMeshWriteLOD())
    ns = sm.get_editor_property('nanite_settings')
    if not ns.get_editor_property('enabled'):
        ns.set_editor_property('enabled', True)
        sm.set_editor_property('nanite_settings', ns)
    unreal.EditorAssetLibrary.save_loaded_asset(sm, False)
    e['wrap'] = {'body': b, 'clear_cm': CLEAR, 'placement': p, 'show_through_before': round(before, 3), 'after': round(after, 3)}
    man_changed = True
    print(f'{n:18s} on {b}: show-through {before * 100:5.1f}% -> {after * 100:4.1f}%   moved {moved}/{len(local)} verts, max push {maxd:.1f} cm')

if man_changed:
    with open(MAN_PATH, 'w', encoding='utf-8') as f:
        json.dump(MAN, f, indent=1, ensure_ascii=False)       # the manifest's own format
