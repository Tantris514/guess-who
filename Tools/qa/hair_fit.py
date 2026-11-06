"""Measure and search the hair fits against the mannequin skulls (run in the editor: ue_run.py hair_fit.py [name ...]).

Rays are cast from outside toward the head centre over ~1500 directions. Along each one, the body's outer radius
(skull) and the hair's outer radius are compared: where the hair's outer surface is not at least 0.15 cm outside the
skull, the scalp shows through (bald patch or poke-through). Only the scalp is scored (crown, back, temples, the
front above the hairline), not the face. For each hair piece the current fit (s25_costume_import.py FIT_DEFAULTS)
is reported, then a grid over scale / dz / dy picks the snuggest fit that covers the scalp.
Prints a JSON line "BEST {...}" with overrides in s25's format.
"""
import json
import math
import unreal

GS = unreal.GeometryScript_AssetUtils
SP = unreal.GeometryScript_MeshSpatial
MAN = json.load(open(r'J:\Projets\Unreal_Projects\Guess Who\AssetGen\manifest.json', encoding='utf-8'))
BODY = {'m': unreal.load_asset('/Game/Characters/Mannequins/Meshes/SKM_Manny_Simple'),
        'f': unreal.load_asset('/Game/Characters/Mannequins/Meshes/SKM_Quinn_Simple')}
CURRENT = {'hair_chignon': {'scale': 1.18, 'dz': 1.5, 'dy': 2.0}, 'hair_fingerwave_bob': {'scale': 1.12, 'dz': 0.75, 'dy': 1.0},
           'hair_wavy_back': {'scale': 1.18, 'dz': 0.75, 'dy': 4.0}}     # keep in sync with s25 FIT_DEFAULTS
ARGS = [a for a in (globals().get('UE_ARGS') or [])]


def bone(body, name):
    mod = unreal.SkeletonModifier()
    mod.set_skeletal_mesh(BODY[body])
    return mod.get_bone_transform(name, True)


def pick(res, typ):
    return next(x for x in (res if isinstance(res, tuple) else (res,)) if isinstance(x, typ))


def with_bvh(dm):
    return dm, pick(SP.build_bvh_for_mesh(dm), unreal.GeometryScriptDynamicMeshBVH)


def ray(mesh, bvh, origin, d):
    hit = pick(SP.find_nearest_ray_intersection_with_mesh(mesh, bvh, origin, d, unreal.GeometryScriptSpatialQueryOptions()),
               unreal.GeometryScriptRayHitResult)
    return hit.ray_parameter if hit.hit else None


def verts(mesh, step=7):          # same sampling as s25_costume_import.verts (the fit uses these bounds)
    md = mesh.get_static_mesh_description(0)
    n = md.get_vertex_count()
    out = []
    for i in range(0, n, max(1, step if n > 4000 else 1)):
        v = md.get_vertex_position(unreal.VertexID(i))
        out.append((v.x, v.y, v.z))
    return out


def fib_dirs(n):
    out = []
    ga = math.pi * (3 - math.sqrt(5))
    for i in range(n):
        z = 1 - 2 * (i + 0.5) / n
        r = math.sqrt(1 - z * z)
        out.append(unreal.Vector(r * math.cos(ga * i), r * math.sin(ga * i), z))
    return out


R0 = 40.0
skull = {}
for b in ('m', 'f'):
    dm = unreal.DynamicMesh()
    GS.copy_mesh_from_skeletal_mesh(BODY[b], dm, unreal.GeometryScriptCopyMeshFromAssetOptions(), unreal.GeometryScriptMeshReadLOD())
    mesh, bvh = with_bvh(dm)
    h = bone(b, 'head').translation
    c = unreal.Vector(0.0, h.y + 1.5, h.z + 8.0)
    scalp, face = [], []
    for d in fib_dirs(1500):
        t = ray(mesh, bvh, c + d * R0, d * -1.0)
        if t is None:
            continue
        rb = R0 - t
        p = c + d * rb
        top = p.z > c.z + 7.5                                          # crown, including the front above the hairline
        upper = p.z > c.z + 2.0 and p.y < c.y + 5.0                    # temples and sides above the ears, behind the brow
        back = p.y < c.y - 3.0 and p.z > c.z - 4.0                     # back of the head down to the occipital
        if (top or upper or back) and p.z > h.z + 3.0:
            scalp.append((d, rb))
        elif p.y > c.y + 6.0 and h.z - 2.0 < p.z < c.z + 2.0:          # brow, eyes, nose (a fringe may cover the upper forehead)
            face.append((d, rb))
    skull[b] = (c, h, scalp, face)
    print(f'body {b}: centre {c.x:.1f},{c.y:.1f},{c.z:.1f}  scalp rays {len(scalp)}  face rays {len(face)}')

ch = unreal.load_asset('/Game/GW/Blueprints/BP_GW_Character')
pools = unreal.get_default_object(ch.generated_class())
best_all = {}
for a in MAN['assets']:
    n = a['name']
    if a.get('status') != 'approved' or not n.startswith('hair') or (ARGS and n not in ARGS):
        continue
    body = 'f' if any(w in n for w in ('bob', 'chignon')) else 'm'
    sm = unreal.load_asset(f'/Game/GW/Characters/Items/{n}/{n}') or next(
        (unreal.load_asset(p) for p in unreal.EditorAssetLibrary.list_assets(f'/Game/GW/Characters/Items/{n}', recursive=True)
         if isinstance(unreal.load_asset(p), unreal.StaticMesh)), None)
    dm = unreal.DynamicMesh()
    GS.copy_mesh_from_static_mesh(sm, dm, unreal.GeometryScriptCopyMeshFromAssetOptions(), unreal.GeometryScriptMeshReadLOD())
    hmesh, hbvh = with_bvh(dm)
    vs = verts(sm)
    xs, ys, zs = [v[0] for v in vs], [v[1] for v in vs], [v[2] for v in vs]
    cx, mxy, mxz = (min(xs) + max(xs)) / 2, max(ys), max(zs)
    rs = (a.get('orientation') or {}).get('uniform_scale_to_cm', 100.0) / 100.0
    c, h, scalp, face = skull[body]

    def outer(d, s, t):
        o = (c + d * R0 - t) * (1.0 / s)
        tl = ray(hmesh, hbvh, o, d * -1.0)
        return None if tl is None else R0 - tl * s

    def score(k, dz, dy, with_face=True):
        s = rs * k
        t = unreal.Vector(-s * cx, 10.0 + h.y + dy - s * mxy, 181.5 + dz - s * mxz)
        cov, gaps, miss = 0, [], []
        for d, rb in scalp:
            rh = outer(d, s, t)
            if rh is not None and rh >= rb + 0.15:
                cov += 1
                gaps.append(rh - rb)
            else:
                miss.append(c + d * rb)
        g = sorted(gaps)
        fc = 0.0
        if with_face:                                                  # hair hanging over the forehead / eyes
            fc = sum(1 for d, rb in face if (outer(d, s, t) or -1.0) >= rb + 0.15) / len(face)
        return cov / len(scalp), (sum(g) / len(g) if g else 0.0), (g[int(len(g) * 0.9)] if g else 0.0), miss, fc

    cur = CURRENT.get(n, {})
    cv, mg, g90, miss, fc = score(cur.get('scale', 1.0), cur.get('dz', 0.0), cur.get('dy', 0.0))
    print(f'{n} on {body}: CURRENT {cur or "default"} -> covers {cv * 100:.1f}% of scalp, mean gap {mg:.2f} cm, p90 {g90:.2f}, over face {fc * 100:.1f}%')
    if miss:
        zs_ = sorted(p.z for p in miss); ys_ = sorted(p.y for p in miss)
        print(f'   uncovered: {len(miss)} rays, z {zs_[0]:.1f}..{zs_[-1]:.1f}, y {ys_[0]:.1f}..{ys_[-1]:.1f}, '
              f'|x|>6: {sum(1 for p in miss if abs(p.x) > 6)}, top(z>{c.z + 7.5:.0f}): {sum(1 for p in miss if p.z > c.z + 7.5)}, back(y<{c.y - 3:.0f}): {sum(1 for p in miss if p.y < c.y - 3)}')
    results = []
    for ki in range(14):
        k = 0.94 + 0.03 * ki
        for dz in (-1.5, -0.75, 0.0, 0.75, 1.5, 2.25, 3.0):
            for dy in (-1.0, 0.0, 1.0, 2.0, 3.0, 4.0, 5.0, 6.0):
                cv2, mg2, g902, _, fc2 = score(k, dz, dy)
                results.append((cv2, mg2, g902, k, dz, dy, fc2))
    clear = [r for r in results if r[6] <= 0.03] or results           # keep the face clear
    top_cov = max(r[0] for r in clear)
    ok = [r for r in clear if r[0] >= min(0.985, top_cov - 0.005)]
    best = min(ok, key=lambda r: (r[1] + 0.5 * r[2], r[3]))          # snuggest among the ones that cover
    print(f'   best cover available {top_cov * 100:.1f}% (face clear); chosen k={best[3]:.2f} dz={best[4]} dy={best[5]} -> '
          f'{best[0] * 100:.1f}%, mean gap {best[1]:.2f} cm, p90 {best[2]:.2f}, over face {best[6] * 100:.1f}%')
    for r in sorted(ok, key=lambda r: (r[1] + 0.5 * r[2], r[3]))[:4]:
        print(f'      alt k={r[3]:.2f} dz={r[4]} dy={r[5]}: {r[0] * 100:.1f}% gap {r[1]:.2f} p90 {r[2]:.2f} face {r[6] * 100:.1f}%')
    best_all[n] = {'scale': round(best[3], 2), 'dz': best[4], 'dy': best[5]}
print('BEST ' + json.dumps(best_all))
