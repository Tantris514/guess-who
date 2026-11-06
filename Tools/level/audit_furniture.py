"""Offline interpenetration audit for the dressing (run after export_instances.py):

  * furniture footprints (dress_state.json: AABB + base/top heights) vs walls (room inner rect minus skins),
    columns, stairs, fireplaces, curtain/pilaster/door zones (colliding arch instances), and vs each other
  * rugs/runners vs thresholds, hearths, stage/steps and each other (z-fighting / poking through)
  * books vs shelf boards
  * table-top props (lamps, gramophone, radio, typewriter, telephone, candelabra, vases) must stand on furniture:
    a supporting top (table, console, sideboard, desk, bar, piano lid...) within 3 cm under their centre, never the floor
  * floor reserved for props that are still being generated (dress_state.json "reserved", label R:<name>) is
    audited like furniture, so the props will not collide when they arrive
Usage: python -I -X utf8 Tools/level/audit_furniture.py [--list]
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
ds = json.load(open(os.path.join(HERE, "dress_state.json"), encoding="utf-8"))
foot = ds["foot"]
reserved = [r for r in ds.get("reserved", []) if not r[7]]
wc = ds.get("wc", [])                 # W.C. partition, stall dividers, toilets, basins (kept out of "foot")
T = lay["wall_thickness"] / 2
SKIN = 1.9
WALLMOUNT = {"bookcase", "backbar", "cue_rack"}
STACK_OK = {("stage", "piano"), ("stage", "piano_grand"), ("stage", "gramophone"), ("stage", "palm_potted"),
            ("stage", "planter"), ("stage", "harp"), ("stage", "piano_bench")}
STACK_OK |= {("stage", p + n) for p in ("", "R:") for n in ("drum_kit", "double_bass", "microphone_stand")}
STACK_OK |= {("R:card_table+chairs", "R:card_table")}       # the table's own slot lies inside its group's slot


def ov3(a, b, tol=TOL):
    return all(min(a[1][k], b[1][k]) - max(a[0][k], b[0][k]) > tol for k in range(3))


F = []
for f in foot:
    x0, y0, x1, y1, label = f[:5]
    top = f[5] if len(f) > 5 else 120.0
    base = f[6] if len(f) > 6 else 0.0
    F.append(dict(label=label, box=([x0, y0, base], [x1, y1, top])))
for r in reserved:
    F.append(dict(label="R:" + r[4], box=([r[0], r[1], r[6]], [r[2], r[3], r[5]])))
for w in wc:
    F.append(dict(label="W:" + w[4], box=([w[0], w[1], w[6]], [w[2], w[3], w[5]])))

rooms = [(r["name"], r["rect"]) for r in lay["rooms"]]
cl = lay["cloakroom"]["rect"]
issues = defaultdict(list)

# 1. inside a room (inner rect minus skins); cloakroom interior counts as its own room
for f in F:
    lo, hi = f["box"]
    cx, cy = (lo[0] + hi[0]) / 2, (lo[1] + hi[1]) / 2
    if cl[0] < cx < cl[2] and cl[1] < cy < cl[3]:
        rect = (cl[0] + 20, 15, cl[2] - 20, cl[3] - 20)
    else:
        rect = next(((r[0] + T, r[1] + T, r[2] - T, r[3] - T) for n, r in rooms if r[0] < cx < r[2] and r[1] < cy < r[3]),
                    None)
    if rect is None:
        issues["outside any room"].append(f["label"])
        continue
    m = SKIN - (0.5 if f["label"] in WALLMOUNT else -1.0)
    if lo[0] < rect[0] + m - TOL or lo[1] < rect[1] + m - TOL or hi[0] > rect[2] - m + TOL or hi[1] > rect[3] - m + TOL:
        issues["into a wall"].append((f["label"], [round(v) for v in lo[:2]], [round(v) for v in hi[:2]]))

# 2. vs colliding architecture (stairs, columns, fireplaces, curtain/door blockers, cloakroom, pilasters, jambs)
ARCH = [i for i in inst if i["c"] != "NoCollision" and not i["a"].startswith("GW_Dress") and i["a"] not in (
    "GW_Floors", "GW_Ceilings", "GW_Walls", "GW_Paintings", "GW_Sconces", "GW_Garden") and i["hi"][2] > 2
        and abs(i["r"][0]) < 1]
for f in F:
    for i in ARCH:
        if ov3(f["box"], (i["lo"], i["hi"])):
            if f["label"] == "stage" or (f["label"] in WALLMOUNT and i["a"].startswith("GW_Room_")):
                continue
            issues["furniture x architecture"].append((f["label"], i["a"], i["m"], [round(v) for v in i["t"]]))
            break

# 3. furniture vs furniture
for a in range(len(F)):
    for b in range(a + 1, len(F)):
        A, B = F[a], F[b]
        if (A["label"], B["label"]) in STACK_OK or (B["label"], A["label"]) in STACK_OK:
            continue
        if A["label"].startswith("W:") and B["label"].startswith("W:"):
            continue
        if ov3(A["box"], B["box"]):
            issues["furniture x furniture"].append((A["label"], B["label"], [round(v) for v in A["box"][0][:2]]))

# 3b. table-top props must stand on furniture (never on the floor)
TABLETOP = {"lamp_table", "gramophone", "radio_cathedral", "typewriter", "telephone", "candelabra", "vase_flowers"}
SUPPORT = {"table_side", "side_table", "table_console", "console", "sideboard", "desk_partners", "desk", "table_dining",
           "long_table", "round_table", "bar", "champagne_table", "card_table", "writing_bureau", "piano_grand", "piano",
           "bar_cart"}
for f in F:
    if f["label"] not in TABLETOP:
        continue
    lo, hi = f["box"]
    cx, cy, base = (lo[0] + hi[0]) / 2, (lo[1] + hi[1]) / 2, lo[2]
    if not any(g["label"] in SUPPORT and g["box"][0][0] <= cx <= g["box"][1][0] and g["box"][0][1] <= cy <= g["box"][1][1]
               and abs(g["box"][1][2] - base) <= 3.0 for g in F):
        issues["table-top prop not on furniture"].append((f["label"], [round(cx), round(cy)], round(base, 1)))

# 4. rugs / runners
RUGS = [i for i in inst if i["m"] == "SM_GW_Plane" and i["mat"].startswith("MI_GW_Rug")]
FLAT = [i for i in inst if (i["a"] == "GW_Jambs" and i["mat"] == "MI_GW_Marble_White") or
        (i["a"].startswith("GW_Fire_") and i["mat"] == "MI_GW_Marble_Black")]
STEPS = [f for f in F if f["label"] == "stage"]
for r in RUGS:
    rb = ([r["lo"][0], r["lo"][1], -5], [r["hi"][0], r["hi"][1], 5])
    for i in FLAT:
        if ov3(rb, (i["lo"], i["hi"]), 0.5):
            issues["rug x threshold/hearth"].append((r["mat"], [round(v) for v in r["t"]]))
    for s in STEPS:
        if ov3(rb, ([s["box"][0][0], s["box"][0][1], -5], [s["box"][1][0], s["box"][1][1], 5]), 0.5):
            issues["rug x stage"].append((r["mat"], [round(v) for v in r["t"]]))
for a in range(len(RUGS)):
    for b in range(a + 1, len(RUGS)):
        A, B = RUGS[a], RUGS[b]
        if ov3((A["lo"], A["hi"]), (B["lo"], B["hi"]), -0.01) and abs(A["t"][2] - B["t"][2]) < 0.2:
            issues["rug x rug (coplanar)"].append((A["mat"], B["mat"]))

# 5. books vs shelves
BOOKS = [i for i in inst if i["mat"].startswith("MI_GW_Book_")]
SHELF = [i for i in inst if i["a"] in ("GW_Dress_library", "GW_Dress_study") and i["mat"] == "MI_GW_Wood_Walnut"
         and i["m"] == "SM_GW_Cube" and i["v"]]
grid = defaultdict(list)
for s in SHELF:
    for gx in range(int(s["lo"][0] // 100), int(s["hi"][0] // 100) + 1):
        for gy in range(int(s["lo"][1] // 100), int(s["hi"][1] // 100) + 1):
            grid[(gx, gy)].append(s)
nb = 0
for bk in BOOKS:
    seen = set()
    for s in grid[(int(bk["t"][0] // 100), int(bk["t"][1] // 100))]:
        if id(s) in seen:
            continue
        seen.add(id(s))
        if ov3((bk["lo"], bk["hi"]), (s["lo"], s["hi"]), 0.3):
            nb += 1
            if len(issues["book x shelf"]) < 10:
                issues["book x shelf"].append(([round(v, 1) for v in bk["lo"]], [round(v, 1) for v in s["lo"]],
                                               [round(v, 1) for v in s["hi"]]))
            break
total = sum(len(v) for k, v in issues.items() if k != "book x shelf") + nb
print(f"furniture objects: {len(F)} (incl. {len(reserved)} reserved slots), rugs: {len(RUGS)}, books: {len(BOOKS)}; issues: {total}")
for k, v in issues.items():
    n = nb if k == "book x shelf" else len(v)
    print(f"  {k}: {n}")
    if LIST:
        for x in v[:30]:
            print("     ", x)
