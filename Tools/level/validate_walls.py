"""Offline check: wall decor (paintings + frames + picture lights, sconces, hall mouldings) must not overlap
door openings/casings/over-door cornices, window reveals/casings/curtains/pelmets, pilasters, columns, stairs and
handrails, fireplaces/mantels, bookcases, furniture standing against the wall, or each other.

  python -I -X utf8 Tools/level/validate_walls.py [--list]
Reads Tools/level/instances.json (export_instances.py), Tools/manor_layout.json and Tools/level/dress_state.json.
Overlap = AABB intersection deeper than TOL cm on all three axes.
"""
import json
import os
import sys
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
TOL = 1.0
LIST = "--list" in sys.argv
inst = json.load(open(os.path.join(HERE, "instances.json"), encoding="utf-8"))["instances"]
lay = json.load(open(os.path.join(ROOT, "Tools", "manor_layout.json"), encoding="utf-8"))
try:
    _ds = json.load(open(os.path.join(HERE, "dress_state.json"), encoding="utf-8"))
    foot = _ds["foot"]
    # floor reserved for props still being generated: the wall decor must already clear them
    foot = foot + [tuple(r[:7]) for r in _ds.get("reserved", []) if not r[7]] + [tuple(w) for w in _ds.get("wc", [])]
except (OSError, ValueError, KeyError):
    foot = []
T = lay["wall_thickness"] / 2

WALL_ACTORS = ("GW_Paintings", "GW_Sconces", "GW_WallDecor")


def ov(a, b, tol=TOL):
    return all(min(a[1][k], b[1][k]) - max(a[0][k], b[0][k]) > tol for k in range(3))


def box(i):
    return (i["lo"], i["hi"])


# ---- wall decor objects: union-find clusters of touching instances inside the wall-decor actors
# sloped pieces (raked stair dado) have meaningless AABBs; they follow the nosing line by construction
wall = [i for i in inst if i["a"] in WALL_ACTORS and i["v"] and "Mould" not in i["m"] and abs(i["r"][0]) < 1.0]
parent = list(range(len(wall)))


def find(k):
    while parent[k] != k:
        parent[k] = parent[parent[k]]
        k = parent[k]
    return k


cells = defaultdict(list)
for k, i in enumerate(wall):
    for gx in range(int(i["lo"][0] // 100), int(i["hi"][0] // 100) + 1):
        for gy in range(int(i["lo"][1] // 100), int(i["hi"][1] // 100) + 1):
            cells[(gx, gy)].append(k)
for lst in cells.values():
    for x in range(len(lst)):
        for y in range(x + 1, len(lst)):
            a, b = wall[lst[x]], wall[lst[y]]
            if ov(box(a), box(b), -0.6):
                ra, rb = find(lst[x]), find(lst[y])
                if ra != rb:
                    parent[ra] = rb
objs = defaultdict(list)
for k in range(len(wall)):
    objs[find(k)].append(wall[k])
OBJ = []
for members in objs.values():
    lo = [min(m["lo"][k] for m in members) for k in range(3)]
    hi = [max(m["hi"][k] for m in members) for k in range(3)]
    kind = "painting" if any(m["m"] == "SM_GW_Plane" for m in members) else (
        "sconce" if members[0]["a"] == "GW_Sconces" else "decor")
    OBJ.append(dict(kind=kind, lo=lo, hi=hi, at=[round((lo[0] + hi[0]) / 2), round((lo[1] + hi[1]) / 2),
                                                 round((lo[2] + hi[2]) / 2)]))

# ---- obstacles
OBS = []
for d in lay["doors"] + [dict(axis="y", at=500, center=3000, width=200, h=250)]:
    w, c, at = d["width"], d["center"], d["at"]
    h = d.get("h", lay["door_height"])
    ext = 34 if w >= 300 else 22                      # casing 16 + over-door cornice overhang
    top = h + 16 + (52 if w >= 300 else 12)
    a0, a1 = c - w / 2 - ext, c + w / 2 + ext
    if d["axis"] == "y":
        OBS.append(("door", ([a0, at - T - 25, 0], [a1, at + T + 25, top])))
    else:
        OBS.append(("door", ([at - T - 25, a0, 0], [at + T + 25, a1, top])))
for i in inst:
    if not i["v"] or i["a"] in WALL_ACTORS or abs(i["r"][0]) > 1.0:     # sloped pieces: AABB meaningless
        continue
    m, a, mat = i["m"], i["a"], i["mat"]
    kind = None
    if m.startswith("SM_GW_WindowCasing") or m == "SM_GW_Curtain":
        kind = "window"
    elif a.startswith("GW_Room_") and mat.startswith("MI_GW_Velvet") and m == "SM_GW_Cube":
        kind = "window"                                 # pelmets
    elif a.startswith("GW_Room_") and m == "SM_GW_Plane" and mat == "MI_GW_Window_Night":
        kind = "window"
    elif m.startswith("SM_GW_DoorCasing"):
        kind = "door"
    elif m.startswith("SM_GW_Column"):
        kind = "column"
    elif a == "GW_Hall_Stairs":
        kind = "stairs"
    elif a.startswith("GW_Fire_"):
        kind = "fireplace"
    elif a in ("GW_Room_hall", "GW_Room_ballroom") and (m == "SM_GW_BevelBox" or (
            m == "SM_GW_Cube" and i["hi"][2] - i["lo"][2] > 250 and min(i["hi"][0] - i["lo"][0],
                                                                        i["hi"][1] - i["lo"][1]) < 20
            and max(i["hi"][0] - i["lo"][0], i["hi"][1] - i["lo"][1]) < 60)):
        kind = "pilaster"
    elif a == "GW_Dress_ballroom" and m == "SM_GW_Curtain":
        kind = "stage"
    if kind:
        OBS.append((kind, box(i)))
for f in foot:
    x0, y0, x1, y1, label = f[:5]
    top = f[5] if len(f) > 5 else 120.0
    OBS.append(("bookcase" if label == "bookcase" else "furniture:" + label, ([x0, y0, 0], [x1, y1, top])))

# ---- checks
hits = defaultdict(list)
for o in OBJ:
    ob = (o["lo"], o["hi"])
    seen = set()
    for kind, bx in OBS:
        if ov(ob, bx) and kind.split(":")[0] not in seen:
            seen.add(kind.split(":")[0])
            hits[(o["kind"], kind.split(":")[0])].append((o["at"], kind))
for x in range(len(OBJ)):
    for y in range(x + 1, len(OBJ)):
        a, b = OBJ[x], OBJ[y]
        if ov((a["lo"], a["hi"]), (b["lo"], b["hi"])):
            hits[(a["kind"], b["kind"])].append((a["at"], b["kind"] + "@" + str(b["at"])))
total = sum(len(v) for v in hits.values())
print(f"wall-decor objects: {len(OBJ)} ({sum(o['kind'] == 'painting' for o in OBJ)} paintings, "
      f"{sum(o['kind'] == 'sconce' for o in OBJ)} sconces); obstacles: {len(OBS)}")
print(f"overlapping (object, obstacle-kind) pairs: {total}; offending objects: "
      f"{len(set(tuple(at) for v in hits.values() for at, _ in v))}")
for k, v in sorted(hits.items(), key=lambda kv: -len(kv[1])):
    print(f"  {k[0]:9s} x {k[1]:10s}: {len(v)}")
    if LIST:
        for at, what in v[:40]:
            print("      at", at, what)
