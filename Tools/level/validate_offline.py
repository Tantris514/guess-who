"""Offline checks on instances.json (exported by export_instances.py):

  * exact duplicate instances
  * coplanar, same-facing, overlapping faces of axis-aligned boxes with different materials (z-fighting)
  * door openings + 1 m approach zones free of colliding geometry
  * stair step heights
Usage: python -I -X utf8 validate_offline.py
"""
import json
import math
import os
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
data = json.load(open(os.path.join(HERE, "instances.json"), encoding="utf-8"))
layout = json.load(open(os.path.join(ROOT, "Tools", "manor_layout.json"), encoding="utf-8"))
INST = data["instances"]
BOXES = ("SM_GW_Cube", "SM_GW_Cube_NoNanite", "SM_GW_BevelBox")
report = []


def axis_aligned(i):
    p, y, r = i["r"]
    return abs(p) < 0.01 and abs(r) < 0.01 and abs((y % 90 + 90) % 90) < 0.01 or abs((y % 90 + 90) % 90 - 90) < 0.01


# 1. duplicates
seen = defaultdict(list)
for i in INST:
    k = (i["m"], tuple(round(v, 1) for v in i["t"]), tuple(round(v, 3) for v in i["s"]), tuple(round(v, 1) for v in i["r"]))
    seen[k].append(i)
dups = [v for v in seen.values() if len(v) > 1]
report.append(f"duplicate instances: {len(dups)}")
for v in dups[:8]:
    report.append(f"   {v[0]['m']} {v[0]['mat']} at {[round(x) for x in v[0]['t']]} x{len(v)} ({v[0]['a']})")

# 2. z-fighting between axis-aligned visible cubes of different materials
faces = defaultdict(list)
for idx, i in enumerate(INST):
    if not i["v"] or i["m"] not in ("SM_GW_Cube", "SM_GW_Cube_NoNanite") or not axis_aligned(i):
        continue
    lo, hi = i["lo"], i["hi"]
    for ax in range(3):
        o = [k for k in range(3) if k != ax]
        rect = (lo[o[0]], hi[o[0]], lo[o[1]], hi[o[1]])
        faces[(ax, -1, round(lo[ax], 1))].append((idx, rect))
        faces[(ax, +1, round(hi[ax], 1))].append((idx, rect))
T0 = layout["wall_thickness"] / 2
AIR = [(r["rect"][0] + T0, r["rect"][1] + T0, 0.0, r["rect"][2] - T0, r["rect"][3] - T0, r["height"])
       for r in layout["rooms"]]
SOLID = [i for i in INST if i["v"] and i["m"] in ("SM_GW_Cube", "SM_GW_Cube_NoNanite") and axis_aligned(i)
         and "Glass" not in i["mat"]]
GRID = defaultdict(list)
for i in SOLID:
    for gx in range(int(i["lo"][0] // 200), int(i["hi"][0] // 200) + 1):
        for gy in range(int(i["lo"][1] // 200), int(i["hi"][1] // 200) + 1):
            GRID[(gx, gy)].append(i)


def is_air(p):
    if not any(a[0] < p[0] < a[3] and a[1] < p[1] < a[4] and a[2] < p[2] < a[5] for a in AIR):
        return False
    for i in GRID.get((int(p[0] // 200), int(p[1] // 200)), ()):
        if all(i["lo"][k] < p[k] < i["hi"][k] for k in range(3)):
            return False
    return True


def exposed(key, rect):
    ax, sg, c = key
    o = [k for k in range(3) if k != ax]
    pts = []
    for fu, fv in ((0.5, 0.5), (0.1, 0.1), (0.9, 0.1), (0.1, 0.9), (0.9, 0.9)):
        p = [0.0, 0.0, 0.0]
        p[ax] = c + sg * 0.2
        p[o[0]] = rect[0] + (rect[1] - rect[0]) * fu
        p[o[1]] = rect[2] + (rect[3] - rect[2]) * fv
        pts.append(p)
    return any(is_air(p) for p in pts)


zf = []
for key, lst in faces.items():
    if len(lst) < 2:
        continue
    lst.sort(key=lambda e: e[1][0])
    for a in range(len(lst)):
        ia, ra = lst[a]
        for b in range(a + 1, len(lst)):
            ib, rb = lst[b]
            if rb[0] >= ra[1]:
                break
            if INST[ia]["mat"] == INST[ib]["mat"]:
                continue
            ov0 = min(ra[1], rb[1]) - max(ra[0], rb[0])
            ov1 = min(ra[3], rb[3]) - max(ra[2], rb[2])
            if ov0 > 0.5 and ov1 > 0.5:
                rect = (max(ra[0], rb[0]), min(ra[1], rb[1]), max(ra[2], rb[2]), min(ra[3], rb[3]))
                if exposed(key, rect):
                    zf.append((key, INST[ia], INST[ib], ov0 * ov1))
report.append(f"coplanar same-facing overlaps (different materials): {len(zf)}")
for key, a, b, area in sorted(zf, key=lambda e: -e[3])[:25]:
    report.append(f"   axis{key[0]}{'+' if key[1] > 0 else '-'}@{key[2]}: {a['mat']}({a['a']}) vs {b['mat']}({b['a']}) "
                  f"area {area:.0f} at {[round(x) for x in a['t']]}")

# 3. doors clear
T = layout["wall_thickness"] / 2
coll = [i for i in INST if i["c"] not in ("NoCollision",)]


def blocked(box):
    hits = []
    for i in coll:
        lo, hi = i["lo"], i["hi"]
        if all(lo[k] < box[1][k] and hi[k] > box[0][k] for k in range(3)):
            hits.append(i)
    return hits


bad = 0
for d in layout["doors"] + [dict(axis="y", at=500, center=3000, width=200, h=250)]:
    c, w, at = d["center"], d["width"], d["at"]
    h = d.get("h", layout["door_height"])
    for depth, name in ((T + 4, "opening"), (T + 100, "approach")):
        if d["axis"] == "y":
            box = ((c - w / 2 + 4, at - depth, 20), (c + w / 2 - 4, at + depth, h - 10))
        else:
            box = ((at - depth, c - w / 2 + 4, 20), (at + depth, c + w / 2 - 4, h - 10))
        hits = blocked(box)
        if hits:
            bad += 1
            report.append(f"   door {d['axis']}={at} c={c} {name} blocked by "
                          + ", ".join(sorted(set(f"{x['m']}/{x['a']}" for x in hits)))[:300])
report.append(f"door checks failing: {bad}")

# 4. stairs
N = math.ceil(layout["gallery"]["z"] / 18.0)
report.append(f"stairs: {N} risers of {layout['gallery']['z'] / N:.2f} cm, treads "
              f"{(layout['gallery']['stairs'][0]['rect'][3] - layout['gallery']['stairs'][0]['rect'][1]) / N:.1f} cm")
print("\n".join(report))
