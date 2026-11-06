"""Offline: placements for the storm-island exterior (L_Manor_Island), sampled on the island heightfield.

  V:/ComfyUI/ComfyUI/ComfyUI/.venv/Scripts/python.exe -I Tools/level/island_layout.py
-> Tools/level/island_src/layout.json (+ layout_preview.png). Deterministic (seeded).
Everything stays outside the house; tall things keep >= 700 cm from the walls (garden lamps: unshadowed lights
must not leak through the walls), low shrubs >= 380 cm (outside the gravel terrace).
"""
import json
import math
import os
import random

import numpy as np
from PIL import Image, ImageDraw

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, "island_src")
X0, Y0, STEP = -4500.0, -4500.0, 100.0
NX, NY = 151, 135
SEA = -2000.0
FOOT = (0.0, 0.0, 6000.0, 4400.0)
WIN_TYPES = {"std": (150, 260, 105), "tall": (180, 420, 105), "tall_hi": (180, 420, 530)}
WINDOWS = [("y", 0, 500, "std"), ("y", 0, 1000, "std"), ("y", 0, 1500, "std"),
           ("y", 0, 2300, "tall"), ("y", 0, 3700, "tall"), ("y", 0, 3000, "tall_hi"),
           ("y", 0, 4500, "std"), ("y", 0, 5000, "std"), ("y", 0, 5500, "std"),
           ("x", 0, 350, "std"), ("x", 0, 1450, "std"), ("x", 0, 2100, "std"), ("x", 0, 2850, "std"),
           ("x", 0, 3950, "std"),
           ("y", 4400, 400, "std"), ("y", 4400, 1000, "std"), ("y", 4400, 1600, "std"),
           ("y", 4400, 2250, "tall"), ("y", 4400, 3750, "tall"),
           ("x", 6000, 350, "std"), ("x", 6000, 1450, "std"), ("x", 6000, 2100, "std"), ("x", 6000, 2800, "std")]


def load_height():
    H = np.full((NX, NY), np.nan)
    with open(os.path.join(SRC, "meshes", "SM_GW_Island.obj"), encoding="ascii") as fh:
        for line in fh:
            if line.startswith("v "):
                _, x, y, z = line.split()
                x, y, z = float(x), -float(y), float(z)
                i, j = round((x - X0) / STEP), round((y - Y0) / STEP)
                if 0 <= i < NX and 0 <= j < NY:
                    H[i, j] = z
    assert not np.isnan(H).any(), "island grid not regular"
    return H


H = load_height()


def ground(x, y):
    fx, fy = (x - X0) / STEP, (y - Y0) / STEP
    i, j = int(np.clip(math.floor(fx), 0, NX - 2)), int(np.clip(math.floor(fy), 0, NY - 2))
    tx, ty = fx - i, fy - j
    return float(H[i, j] * (1 - tx) * (1 - ty) + H[i + 1, j] * tx * (1 - ty) + H[i, j + 1] * (1 - tx) * ty +
                 H[i + 1, j + 1] * tx * ty)


def slope(x, y):
    return max(abs(ground(x + 100, y) - ground(x - 100, y)), abs(ground(x, y + 100) - ground(x, y - 100))) / 200.0


def dist_house(x, y):
    qx = max(FOOT[0] - x, 0.0, x - FOOT[2])
    qy = max(FOOT[1] - y, 0.0, y - FOOT[3])
    return math.hypot(qx, qy) if (qx > 0 or qy > 0) else -min(x - FOOT[0], FOOT[2] - x, y - FOOT[1], FOOT[3] - y)


def plateau(x, y, margin=150.0):
    """On the flat top, at least `margin` cm from the cliff edge."""
    if ground(x, y) < -90:
        return False
    for a in range(0, 360, 45):
        if ground(x + math.cos(math.radians(a)) * margin, y + math.sin(math.radians(a)) * margin) < -120:
            return False
    return slope(x, y) < 0.25


rng = random.Random(1939)
out = dict(sea=dict(loc=[5000.0, 3800.0, SEA], scale=[0.84, 0.84, 1.0]), lamps=[], trees=[], bushes=[], boulders=[],
           rain=[], wind=[], sea_sounds=[], rain_sounds=[], plinth=[])


def far_from(x, y, pts, d):
    return all(math.hypot(x - p[0], y - p[1]) >= d for p in pts)


# garden lamps: on the terrace's outer edge, 750-950 cm from the walls, one per facade side (+ two at the front door)
lamp_targets = [(2550, -800), (3450, -800), (-800, 1000), (-800, 3400), (6800, 900), (6800, 2600), (1500, 5200),
                (4700, 5250)]
for (x, y) in lamp_targets:
    for _ in range(40):
        if plateau(x, y, 200) and dist_house(x, y) >= 700:
            break
        # walk toward the house until on the plateau
        x, y = x + (3000 - x) * 0.05, y + (2200 - y) * 0.05
    if plateau(x, y, 120) and dist_house(x, y) >= 650:
        out["lamps"].append([round(x), round(y), round(ground(x, y), 1)])
lamps = [(p[0], p[1]) for p in out["lamps"]]

# twisted trees: plateau, 800-2200 cm from the walls, mostly north and east (the lawn), apart from each other
readme = json.load(open(os.path.join(SRC, "README.json"), encoding="utf-8"))
anchors = {k: readme["files"][k]["crown_anchors_ue"] for k in ("SM_GW_TreeBent_A", "SM_GW_TreeBent_B")}
trees = []
tries = 0
while len(trees) < 11 and tries < 5000:
    tries += 1
    x, y = rng.uniform(-3000, 9000), rng.uniform(-3000, 7500)
    d = dist_house(x, y)
    if not (800 <= d <= 2400) or not plateau(x, y, 250):
        continue
    if y < -200 and len([t for t in trees if t[1] < -200]) >= 2:      # south (entrance side): few
        continue
    if not far_from(x, y, trees, 650) or not far_from(x, y, lamps, 350):
        continue
    trees.append((x, y))
for (x, y) in trees:
    mesh = rng.choice(["SM_GW_TreeBent_A", "SM_GW_TreeBent_B"])
    s = rng.uniform(0.75, 1.1)
    yaw = rng.uniform(-14, 14)                  # all lean downwind (+X): the storm comes from the west
    z = ground(x, y)
    crowns = []
    for (ax, ay, az) in anchors[mesh]:
        r = math.radians(yaw)
        wx = x + (ax * math.cos(r) - ay * math.sin(r)) * s
        wy = y + (ax * math.sin(r) + ay * math.cos(r)) * s
        crowns.append(dict(mesh=rng.choice(["SM_GW_Crown_A", "SM_GW_Crown_B"]), loc=[round(wx), round(wy),
                           round(z + az * s)], yaw=round(rng.uniform(-25, 25) + yaw, 1),
                           scale=round(s * rng.uniform(0.55, 0.85), 3)))
    out["trees"].append(dict(mesh=mesh, loc=[round(x), round(y), round(z, 1)], yaw=round(yaw, 1), scale=round(s, 3),
                             crowns=crowns))

# shrubs: clustered on the plateau beyond the gravel terrace (>= 420 cm), not right in front of the front door
bushes = []
tries = 0
while len(bushes) < 46 and tries < 20000:
    tries += 1
    if bushes and rng.random() < 0.6:
        bx, by = rng.choice(bushes)[:2]
        x, y = bx + rng.uniform(-260, 260), by + rng.uniform(-260, 260)
    else:
        x, y = rng.uniform(-3000, 9000), rng.uniform(-3000, 7500)
    d = dist_house(x, y)
    if not (420 <= d <= 2600) or not plateau(x, y, 120):
        continue
    if 2300 < x < 3700 and y < 0:                # entrance path
        continue
    if not far_from(x, y, bushes, 130) or not far_from(x, y, trees, 140) or not far_from(x, y, lamps, 160):
        continue
    bushes.append((x, y))
for (x, y) in bushes:
    out["bushes"].append(dict(mesh=rng.choice(["SM_GW_Bush_A", "SM_GW_Bush_B"]), loc=[round(x), round(y),
                              round(ground(x, y) - 8, 1)], yaw=round(rng.uniform(-20, 20), 1),
                              scale=round(rng.uniform(0.6, 1.25), 3)))

# boulders: along the waterline (sea surf) and a few on the cliff top
shore = [(i, j) for i in range(1, NX - 1) for j in range(1, NY - 1) if -2060 < H[i, j] < -1940]
rng.shuffle(shore)
bpts = []
for (i, j) in shore:
    x, y = X0 + i * STEP, Y0 + j * STEP
    if far_from(x, y, bpts, 600):
        bpts.append((x, y))
    if len(bpts) >= 34:
        break
for (x, y) in bpts:
    s = rng.uniform(1.2, 4.2)
    out["boulders"].append(dict(mesh=rng.choice(["SM_GW_Boulder_A", "SM_GW_Boulder_B", "SM_GW_Boulder_C"]),
                                loc=[round(x), round(y), round(ground(x, y) - 40 * s, 1)], yaw=round(rng.uniform(0, 360)),
                                scale=[round(s * rng.uniform(0.8, 1.2), 3), round(s * rng.uniform(0.8, 1.2), 3),
                                       round(s * rng.uniform(0.6, 1.0), 3)]))
edge = [(X0 + i * STEP, Y0 + j * STEP) for i in range(NX) for j in range(NY)
        if -110 < H[i, j] < -50 and 900 < dist_house(X0 + i * STEP, Y0 + j * STEP)]
rng.shuffle(edge)
etop = []
for (x, y) in edge:
    if slope(x, y) > 0.35 and far_from(x, y, etop, 900) and far_from(x, y, trees + lamps, 300):
        etop.append((x, y))
    if len(etop) >= 9:
        break
for (x, y) in etop:
    s = rng.uniform(0.6, 1.4)
    out["boulders"].append(dict(mesh=rng.choice(["SM_GW_Boulder_A", "SM_GW_Boulder_B", "SM_GW_Boulder_C"]),
                                loc=[round(x), round(y), round(ground(x, y) - 30 * s, 1)], yaw=round(rng.uniform(0, 360)),
                                scale=[round(s, 3), round(s * 1.1, 3), round(s * 0.8, 3)]))

# rain curtains: one plane outside every window (parallel to the facade, 130 cm out) + three layers outside each
# conservatory glass wall; planes are 100x100 (SM_GW_Plane) scaled; facing = outward normal of the facade
for (ax, at, c, wt) in WINDOWS:
    w, h, sill = WIN_TYPES[wt]
    out_sign = -1.0 if at == 0 else 1.0
    zc = sill + h / 2
    if ax == "y":
        out["rain"].append(dict(loc=[c, at + out_sign * 130, zc], size=[w + 220, h + 300], axis="y"))
    else:
        out["rain"].append(dict(loc=[at + out_sign * 130, c, zc], size=[w + 220, h + 300], axis="x"))
for d in (170, 420, 800):
    out["rain"].append(dict(loc=[5000, 4400 + d, 330], size=[2400 + d, 760], axis="y"))
    out["rain"].append(dict(loc=[6000 + d, 3800, 330], size=[1500 + d, 760], axis="x"))

# exterior ambience (outside, attenuated + low-passed): wind at the facade midpoints, sea from the cliffs,
# rain near the window rows
out["wind"] = [[3000, -450, 300], [-450, 2200, 300], [6450, 1300, 300], [2400, 4850, 300]]
cliff = sorted(edge, key=lambda p: -dist_house(*p))
out["sea_sounds"] = []
for want in ((3000, -2500), (-2500, 2200), (8500, 2200), (3000, 7000)):
    best = min(edge, key=lambda p: math.hypot(p[0] - want[0], p[1] - want[1]))
    out["sea_sounds"].append([round(best[0]), round(best[1]), round(ground(*best) + 200)])
out["rain_sounds"] = [[1000, -180, 250], [5000, -180, 250], [-180, 2000, 250], [6180, 2000, 250], [1000, 4580, 250],
                      [3000, 4580, 350]]

# stone plinth outside the outer walls (the house floor sits ~45 cm above the plateau)
for (x0, y0, x1, y1) in ((-45, -45, 6045, -15), (-45, 4415, 6045, 4445), (-45, -15, -15, 4415),
                         (6015, -15, 6045, 4415)):
    out["plinth"].append([x0, y0, x1, y1, -70, 12])

# front steps down from the front door (cloakroom, x 2912-3088) to the gravel, and a stone balustrade along the
# terrace in front of the south facade (only where the ground is plateau)
out["steps"] = [[2840, 3160, -40 - 34 * k - 34, -40 - 34 * k, -34 - 15 * k, -15 * k] for k in range(3)]
bal = []
for xs in range(-600, 6700, 240):
    ys = -900
    if plateau(xs, ys, 100) and not (2700 < xs < 3300):           # gap for the path to the front door
        bal.append([xs, ys, round(ground(xs, ys), 1)])
out["balustrade"] = bal
# a lighthouse on a rock ~200 m out to sea, south-south-west: blinks through the south windows (inside the sky dome,
# radius 300 m around (5000, 3800))
out["lighthouse"] = [-1500.0, -17500.0, SEA]
json.dump(out, open(os.path.join(SRC, "layout.json"), "w", encoding="utf-8"), indent=1)
print(f"lamps {len(out['lamps'])}, trees {len(out['trees'])} (crowns {sum(len(t['crowns']) for t in out['trees'])}), "
      f"bushes {len(out['bushes'])}, boulders {len(out['boulders'])}, rain planes {len(out['rain'])}")

# preview
S = 0.05
img = Image.new("RGB", (int(15000 * S), int(13400 * S)), (10, 20, 40))
dr = ImageDraw.Draw(img)
for i in range(NX):
    for j in range(NY):
        z = H[i, j]
        c = (40, 60, 40) if z > -90 else ((70, 65, 60) if z > -2000 else (15, 30, 55))
        px, py = (X0 + i * STEP + 4500) * S, (8900 - (Y0 + j * STEP)) * S
        dr.rectangle([px, py, px + STEP * S, py + STEP * S], fill=c)


def P(x, y):
    return ((x + 4500) * S, (8900 - y) * S)


dr.rectangle([P(0, 4400), P(6000, 0)], outline=(220, 200, 150), width=2)
for t in out["trees"]:
    p = P(*t["loc"][:2])
    dr.ellipse([p[0] - 6, p[1] - 6, p[0] + 6, p[1] + 6], fill=(30, 120, 40))
for bsh in out["bushes"]:
    p = P(*bsh["loc"][:2])
    dr.ellipse([p[0] - 3, p[1] - 3, p[0] + 3, p[1] + 3], fill=(90, 160, 70))
for bo in out["boulders"]:
    p = P(*bo["loc"][:2])
    dr.ellipse([p[0] - 4, p[1] - 4, p[0] + 4, p[1] + 4], fill=(160, 160, 160))
for la in out["lamps"]:
    p = P(*la[:2])
    dr.ellipse([p[0] - 5, p[1] - 5, p[0] + 5, p[1] + 5], fill=(255, 200, 80))
img.save(os.path.join(SRC, "layout_preview.png"))
