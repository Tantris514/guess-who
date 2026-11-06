"""Measure and search the torso fits of bodices and coats against the mannequins (editor: ue_run.py garment_fit.py [name ...]).

At each height of the garment, rays go out horizontally from the body's centre line. The skin radius comes from the
ray cast from inside (the torso is hit before any arm), the garment's outer radius from a ray cast from outside.
Where the skin is not at least CLEAR cm inside the garment's outer surface, the mannequin shows through (the flat
tinted patches) or will once the spine bends in the walk cycle. Only directions where the garment exists are scored,
so armholes and open backs do not count. Prints "BEST {...}" with overrides in s25_costume_import.py's format
(flare = x, flare_y = y scale factors, dy / dz in cm).
"""
import json
import math
import unreal

GS = unreal.GeometryScript_AssetUtils
SP = unreal.GeometryScript_MeshSpatial
MAN = json.load(open(r'J:\Projets\Unreal_Projects\Guess Who\AssetGen\manifest.json', encoding='utf-8'))
BODY = {'m': unreal.load_asset('/Game/Characters/Mannequins/Meshes/SKM_Manny_Simple'),
        'f': unreal.load_asset('/Game/Characters/Mannequins/Meshes/SKM_Quinn_Simple')}
CLEAR = 0.6                       # cm of cloth thickness kept over the skin in the reference pose (walk-cycle margin)
ARGS = [a for a in (globals().get('UE_ARGS') or [])]
CURRENT = json.loads(ARGS.pop(0)) if ARGS and ARGS[0].startswith('{') else {}


_bones = {}


def bone(body, name):             # cached: every SkeletonModifier copies the mesh (uncached, the editor ran out of memory)
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
AZ = [unreal.Vector(math.cos(a), math.sin(a), 0.0) for a in (2 * math.pi * i / 40 for i in range(40))]


def axis_y(b, z):                 # body centre line (y) at height z, from the spine chain
    pts = sorted((bone(b, n).z, bone(b, n).y) for n in CHAIN)
    if z <= pts[0][0]:
        return pts[0][1]
    for (z0, y0), (z1, y1) in zip(pts, pts[1:]):
        if z0 <= z <= z1:
            return y0 + (y1 - y0) * (z - z0) / max(1e-3, z1 - z0)
    return pts[-1][1]


skin_cache = {}


def skin(b, z):
    """[(direction, skin radius)] around the centre line at height z (cast from inside: the torso, never an arm)."""
    key = (b, round(z, 1))
    if key not in skin_cache:
        mesh, bvh = bodies[b]
        a = unreal.Vector(0.0, axis_y(b, z), z)
        out = []
        for d in AZ:
            p = hit(mesh, bvh, a, d)
            out.append((d, None if p is None else math.hypot(p.x - a.x, p.y - a.y)))
        skin_cache[key] = (a, out)
    return skin_cache[key]


best_all = {}
for e in MAN['assets']:
    n = e['name']
    if e.get('status') != 'approved' or e.get('kind') != 'costume' or not n.startswith(('bodice', 'coat')) or (ARGS and n not in ARGS):
        continue
    slot = 'bodice' if n.startswith('bodice') else 'coat'
    b = 'f' if slot == 'bodice' else 'm'
    sm = next((unreal.load_asset(p) for p in unreal.EditorAssetLibrary.list_assets(f'/Game/GW/Characters/Items/{n}', recursive=True)
               if isinstance(unreal.load_asset(p), unreal.StaticMesh)), None)
    dm = unreal.DynamicMesh()
    GS.copy_mesh_from_static_mesh(sm, dm, unreal.GeometryScriptCopyMeshFromAssetOptions(), unreal.GeometryScriptMeshReadLOD())
    gmesh, gbvh = with_bvh(dm)
    vs = verts(sm)
    xs, ys, zs = [v[0] for v in vs], [v[1] for v in vs], [v[2] for v in vs]
    cx, cy, mnz, mxz = (min(xs) + max(xs)) / 2, (min(ys) + max(ys)) / 2, min(zs), max(zs)
    rs = e['orientation']['uniform_scale_to_cm'] / 100.0
    spine, neck = bone(b, 'spine_03'), bone(b, 'neck_01')
    if slot == 'bodice':
        sk = next((x for x in MAN['assets'] if x['name'] == 'skirt_' + n.split('_', 1)[-1]), None)
        skirt_len = (sk or {}).get('size_cm', [0, 0, 112.0])[2] or 112.0
    lo_z = bone(b, 'spine_01').z                          # torso band scored: spine_01 up to below the collar
    hi_z = neck.z - 4.0

    def place(fx, fy, dy, dz):
        if slot == 'bodice':
            t = unreal.Vector(-rs * fx * cx, spine.y + dy - rs * fy * cy, 1.5 + skirt_len - 2.0 + dz - rs * mnz)
        else:
            t = unreal.Vector(-rs * fx * cx, spine.y + dy - rs * fy * cy, neck.z + 4.0 + dz - rs * mxz)
        return unreal.Vector(rs * fx, rs * fy, rs), t

    def score(fx, fy, dy, dz):
        s, t = place(fx, fy, dy, dz)
        z0, z1 = max(lo_z, t.z + s.z * mnz + 1.0), min(hi_z, t.z + s.z * mxz - 1.0)
        poke, n_cov, gaps, where = 0, 0, [], {'front': 0, 'back': 0, 'side': 0}
        z = 2.0 * math.ceil(z0 / 2.0)                 # fixed 2 cm grid so the skin rings are cached
        while z <= z1:
            a, ring = skin(b, z)
            for d, rb in ring:
                if rb is None:
                    continue
                o = a + d * 60.0
                lo = unreal.Vector((o.x - t.x) / s.x, (o.y - t.y) / s.y, (o.z - t.z) / s.z)
                ld = unreal.Vector(-d.x / s.x, -d.y / s.y, 0.0)
                p = hit(gmesh, gbvh, lo, ld.normal())
                if p is None:
                    continue                                  # no cloth in that direction (armhole, open back)
                w = unreal.Vector(p.x * s.x + t.x, p.y * s.y + t.y, p.z * s.z + t.z)
                rh = math.hypot(w.x - a.x, w.y - a.y)
                n_cov += 1
                if rh < rb + CLEAR:
                    poke += 1
                    where['front' if d.y > 0.5 else 'back' if d.y < -0.5 else 'side'] += 1
                else:
                    gaps.append(rh - rb)
            z += 2.0
        g = sorted(gaps)
        return (poke / max(1, n_cov), (sum(g) / len(g)) if g else 0.0, (g[int(len(g) * 0.9)] if g else 0.0), where, n_cov)

    defaults = {'bodice': {'flare': 1.0, 'flare_y': 1.0, 'dy': 0.0, 'dz': 0.0},
                'coat': {'flare': 1.13, 'flare_y': 1.22, 'dy': -1.0, 'dz': 0.0}}[slot]
    cur = {**defaults, **CURRENT.get(n, {})}
    pk, mg, g90, where, nc = score(cur['flare'], cur['flare_y'], cur['dy'], cur['dz'])
    print(f'{n} on {b}: CURRENT {cur} -> mannequin shows through on {pk * 100:.1f}% of the cloth rays '
          f'({where}), mean cloth gap {mg:.2f} cm, p90 {g90:.2f} (rays {nc})')
    # coordinate descent from a few seeds: show-through first, then the snuggest cloth (a bulky shell reads badly too)
    LIM = {'fx': (0.95, 1.4), 'fy': (0.95, 1.75), 'dy': (-6.0, 4.0), 'dz': (-5.0, 5.0)}
    STEP = {'fx': 0.03, 'fy': 0.04, 'dy': 0.5, 'dz': 0.5}
    memo = {}

    def J(p):
        key = tuple(round(p[k], 3) for k in ('fx', 'fy', 'dy', 'dz'))
        if key not in memo:
            pk2, mg2, g902, _, _ = score(*key)
            memo[key] = (pk2 + 0.004 * (mg2 + 0.5 * g902), pk2, mg2, g902)
        return memo[key]

    seeds = [{'fx': cur['flare'], 'fy': cur['flare_y'], 'dy': cur['dy'], 'dz': cur['dz']},
             {'fx': 1.12, 'fy': 1.4, 'dy': -2.0, 'dz': 1.5}, {'fx': 1.2, 'fy': 1.55, 'dy': -3.0, 'dz': 0.0}]
    best_p, best_j = None, None
    for p in seeds:
        while True:
            moved = False
            for k in ('fx', 'fy', 'dy', 'dz'):
                for sgn in (1, -1):
                    q = dict(p)
                    q[k] = min(LIM[k][1], max(LIM[k][0], p[k] + sgn * STEP[k]))
                    if J(q)[0] < J(p)[0] - 1e-6:
                        p, moved = q, True
            if not moved:
                break
        if best_j is None or J(p)[0] < best_j[0]:
            best_p, best_j = p, J(p)
    best = (None, None, None, best_p['fx'], best_p['fy'], best_p['dy'], best_p['dz'])
    pk, mg, g90, where, nc = score(*best[3:])
    print(f'   best: flare {best[3]:.2f} flare_y {best[4]:.2f} dy {best[5]} dz {best[6]} -> shows through {pk * 100:.1f}% ({where}), '
          f'mean gap {mg:.2f} cm, p90 {g90:.2f}')
    best_all[n] = {'flare': round(best[3], 2), 'flare_y': round(best[4], 2), 'dy': best[5], 'dz': best[6]}
print('BEST ' + json.dumps(best_all))
