"""Offline walkable-lane check (ComfyUI venv python: numpy).

Rasterises every colliding instance (AABB, z 10-150 cm) at 10 cm, computes the clearance (distance to the nearest
obstacle) and checks that every door, a point 1.9 m inside each of its two rooms, and every room centre are connected
through cells with clearance >= R (default 100 cm, i.e. a 2 m wide lane), allowing narrower passage only within 1.6 m
of a door centre (doors are 1.8-4 m wide). Floor reserved for props still being generated (dress_state.json
"reserved") counts as an obstacle, so the lanes stay >= 2 m once those props arrive.
Prints per-pair results and writes lanes.png (red = obstacles, grey = clearance >= R, dark = narrower).
"""
import json
import os
import sys
from collections import deque

import numpy as np
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
R = float(sys.argv[1]) if len(sys.argv) > 1 else 100.0
C = 10.0
X0, Y0, X1, Y1 = -50, -50, 6050, 4450
W, H = int((X1 - X0) / C), int((Y1 - Y0) / C)
inst = json.load(open(os.path.join(HERE, "instances.json"), encoding="utf-8"))["instances"]
lay = json.load(open(os.path.join(ROOT, "Tools", "manor_layout.json"), encoding="utf-8"))
occ = np.zeros((H, W), bool)
for i in inst:
    if i["c"] == "NoCollision":
        continue
    lo, hi = i["lo"], i["hi"]
    if hi[2] < 10 or lo[2] > 150:
        continue
    a0, a1 = int(max(0, (lo[0] - X0) // C)), int(min(W, (hi[0] - X0) // C + 1))
    b0, b1 = int(max(0, (lo[1] - Y0) // C)), int(min(H, (hi[1] - Y0) // C + 1))
    occ[b0:b1, a0:a1] = True
try:
    _res = json.load(open(os.path.join(HERE, "dress_state.json"), encoding="utf-8")).get("reserved", [])
except (OSError, ValueError):
    _res = []
for r in _res:
    if r[7] or r[5] < 10 or r[6] > 150:
        continue
    a0, a1 = int(max(0, (r[0] - X0) // C)), int(min(W, (r[2] - X0) // C + 1))
    b0, b1 = int(max(0, (r[1] - Y0) // C)), int(min(H, (r[3] - Y0) // C + 1))
    occ[b0:b1, a0:a1] = True
occ[0, :] = occ[-1, :] = occ[:, 0] = occ[:, -1] = True
# chamfer distance transform (cm)
INF = 1e9
d = np.where(occ, 0.0, INF)
a, b = C, C * 1.41421356
for y in range(1, H):
    row, prev = d[y], d[y - 1]
    np.minimum(row, prev + a, out=row)
    np.minimum(row[1:], prev[:-1] + b, out=row[1:])
    np.minimum(row[:-1], prev[1:] + b, out=row[:-1])
    for x in range(1, W):
        if row[x - 1] + a < row[x]:
            row[x] = row[x - 1] + a
for y in range(H - 2, -1, -1):
    row, nxt = d[y], d[y + 1]
    np.minimum(row, nxt + a, out=row)
    np.minimum(row[1:], nxt[:-1] + b, out=row[1:])
    np.minimum(row[:-1], nxt[1:] + b, out=row[:-1])
    for x in range(W - 2, -1, -1):
        if row[x + 1] + a < row[x]:
            row[x] = row[x + 1] + a
pts = {}
for k, dr in enumerate(lay["doors"]):
    x, y = (dr["center"], dr["at"]) if dr["axis"] == "y" else (dr["at"], dr["center"])
    pts[f"door{k}_{dr['axis']}{dr['at']}_{dr['center']}"] = (x, y)
    for sg in (-1, 1):                      # both sides of every door must join the network through a 2 m lane
        o = sg * (lay["wall_thickness"] / 2 + 175)
        pts[f"side{k}{'ab'[sg > 0]}_{dr['axis']}{dr['at']}_{dr['center']}"] = (x, y + o) if dr["axis"] == "y" else (x + o, y)
try:
    _xd = json.load(open(os.path.join(HERE, "dress_state.json"), encoding="utf-8")).get("extra_doors", [])
except (OSError, ValueError):
    _xd = []
for k, dr in enumerate(_xd):                 # doorways built by the dressing (W.C.)
    x, y = (dr["center"], dr["at"]) if dr["axis"] == "y" else (dr["at"], dr["center"])
    pts[f"xdoor{k}"] = (x, y)
    for sg in (-1, 1):
        o = sg * (lay["wall_thickness"] / 2 + 175)
        pts[f"xside{k}{'ab'[sg > 0]}"] = (x, y + o) if dr["axis"] == "y" else (x + o, y)
pts["cloak_door"] = (3000, 500)
pts["side_cloak_hall"] = (3000, 690)
for r in lay["rooms"]:
    x0, y0, x1, y1 = r["rect"]
    pts["centre_" + r["name"]] = ((x0 + x1) / 2, (y0 + y1) / 2)
pts["centre_hall"] = (3000, 1500)
pts["centre_ballroom"] = (3000, 3300)
door_mask = np.zeros_like(occ)
yy, xx = np.mgrid[0:H, 0:W]
for k, (x, y) in pts.items():
    if k.startswith(("door", "xdoor")) or k == "cloak_door":
        cx, cy = (x - X0) / C, (y - Y0) / C
        door_mask |= (xx - cx) ** 2 + (yy - cy) ** 2 <= (160 / C) ** 2
free = (~occ) & ((d >= R) | door_mask)


def cell(p):
    return int((p[1] - Y0) // C), int((p[0] - X0) // C)


# connected components of `free`
lab = -np.ones_like(occ, dtype=np.int32)
n = 0
for k, p in pts.items():
    s = cell(p)
    if not free[s]:
        # snap to nearest free cell within 1 m
        best = None
        for dy in range(-10, 11):
            for dx in range(-10, 11):
                q = (s[0] + dy, s[1] + dx)
                if 0 <= q[0] < H and 0 <= q[1] < W and free[q]:
                    dd = dx * dx + dy * dy
                    if best is None or dd < best[0]:
                        best = (dd, q)
        if best is None:
            print("NOT FREE:", k, p)
            continue
        s = best[1]
        pts[k] = (s[1] * C + X0, s[0] * C + Y0)
    if lab[s] >= 0:
        continue
    q = deque([s])
    lab[s] = n
    while q:
        cy, cx = q.popleft()
        for ny, nx in ((cy + 1, cx), (cy - 1, cx), (cy, cx + 1), (cy, cx - 1)):
            if 0 <= ny < H and 0 <= nx < W and free[ny, nx] and lab[ny, nx] < 0:
                lab[ny, nx] = n
                q.append((ny, nx))
    n += 1
groups = {}
for k, p in pts.items():
    s = cell(p)
    groups.setdefault(int(lab[s]), []).append(k)
print(f"lane width >= {2 * R:.0f} cm: {len(groups)} connected group(s)")
for g, ks in groups.items():
    print(f"  group {g}: {len(ks)} points" + ("" if len(groups) == 1 else f" {ks}"))
img = np.zeros((H, W, 3), np.uint8)
img[...] = (40, 40, 40)
img[free] = (150, 150, 150)
img[occ] = (180, 30, 30)
Image.fromarray(img[::-1]).save(os.path.join(HERE, "lanes.png"))
