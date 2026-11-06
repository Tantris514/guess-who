"""Build /Game/GW/Maps/L_Manor from Tools/manor_layout.json (run inside the editor).

  python -I -X utf8 Tools/ue_py.py "J:/Projets/Unreal_Projects/Guess Who/Tools/build_manor.py" [parts...]
  parts: all (default) | arch | lights | env | dress | markers | cams | nav | settings

Idempotent: every spawned actor is tagged GW_Gen + a part tag (GW_Arch, GW_Light, GW_Env, GW_Dress,
GW_Markers, GW_Cams, GW_Nav) and the actors of the parts being rebuilt are deleted first.
Prerequisites: Tools/ue_materials.py, Tools/level/import_meshes.py, Tools/level/setup_materials.py.
Dressing (props from AssetGen/manifest.json + procedural fallbacks) lives in Tools/level/dress.py.
"""
import importlib
import json
import math
import os
import random
import sys

import unreal

ROOT = r"J:\Projets\Unreal_Projects\Guess Who"
sys.path.insert(0, os.path.join(ROOT, "Tools", "level"))
import lvl_common  # noqa: E402
import lvl_build  # noqa: E402
importlib.reload(lvl_common)
importlib.reload(lvl_build)
from lvl_build import Batch, Face, spawn, point_light, spot_light, rect_light, target_point, eas, mat  # noqa: E402

MAP = "/Game/GW/Maps/L_Manor"
ARGS = [a.lower() for a in globals().get("UE_ARGS", [])] or ["all"]
ALL = "all" in ARGS
PART_TAGS = {"arch": "GW_Arch", "lights": "GW_Light", "env": "GW_Env", "dress": "GW_Dress", "markers": "GW_Markers",
             "cams": "GW_Cams", "nav": "GW_Nav"}

L = lvl_common.load_layout()
T = L["wall_thickness"] / 2.0
DOOR_H = L["door_height"]
ROOMS = {r["name"]: r for r in L["rooms"]}
GAL = L["gallery"]
CLOAK = L["cloakroom"]
GZ = GAL["z"]

# ------------------------------------------------------------------ art direction per room
# upper: wall above the dado; wains: dado panelling; wh: dado height (0 = none); trim: baseboard/chair rail/casings
STYLE = {
    "dining": dict(floor="MI_GW_Parquet_Dark", upper="MI_GW_Wall_DamaskRed", wains="MI_GW_Wood_Walnut", wh=100,
                   trim="MI_GW_Wood_Dark", crown="MI_GW_Wood_Walnut", ceiling="coffered", beam="MI_GW_Wood_Walnut",
                   ring="MI_GW_GoldLeaf", ceil="MI_GW_Plaster_Ceiling"),
    "corridor_w": dict(floor="MI_GW_Checker_Corridor", upper="MI_GW_Wall_NavyGold", wains="MI_GW_Wood_Walnut", wh=100,
                       trim="MI_GW_Wood_Dark", crown="MI_GW_Paint_Ivory", ceiling="beams", beam="MI_GW_Paint_Ivory",
                       ring="MI_GW_GoldLeaf", ceil="MI_GW_Plaster_Ceiling"),
    "library": dict(floor="MI_GW_Parquet_Dark", upper="MI_GW_Wood_Walnut", wains="MI_GW_Wood_Walnut", wh=100,
                    trim="MI_GW_Wood_Dark", crown="MI_GW_Wood_Walnut", ceiling="coffered", beam="MI_GW_Wood_Walnut",
                    ring="MI_GW_Wood_Dark", ceil="MI_GW_Plaster_Ceiling"),
    "hall": dict(floor="MI_GW_Checker_Hall", upper="MI_GW_Plaster_Cream", wains="MI_GW_Wood_Walnut", wh=100,
                 trim="MI_GW_Wood_Dark", crown="MI_GW_Paint_Ivory", ceiling="coffered", beam="MI_GW_Paint_Ivory",
                 ring="MI_GW_GoldLeaf", ceil="MI_GW_Plaster_Ceiling", pilaster="MI_GW_Paint_Ivory"),
    "ballroom": dict(floor="MI_GW_Floor_Ballroom", upper="MI_GW_Wall_DamaskGreen", wains="MI_GW_Wood_Mahogany", wh=100,
                     trim="MI_GW_Wood_Mahogany", crown="MI_GW_Paint_Ivory", ceiling="coffered",
                     beam="MI_GW_Paint_Ivory", ring="MI_GW_GoldLeaf", ceil="MI_GW_Plaster_Ceiling",
                     pilaster="MI_GW_Paint_Ivory"),
    "billiard": dict(floor="MI_GW_Carpet_Red", upper="MI_GW_Wall_NavyGold", wains="MI_GW_Wood_Mahogany", wh=100,
                     trim="MI_GW_Wood_Dark", crown="MI_GW_Wood_Mahogany", ceiling="coffered",
                     beam="MI_GW_Wood_Mahogany", ring="MI_GW_Wood_Dark", ceil="MI_GW_Plaster_Ceiling"),
    "corridor_e": dict(floor="MI_GW_Checker_Corridor", upper="MI_GW_Wall_FloralCream", wains="MI_GW_Wood_Walnut",
                       wh=100, trim="MI_GW_Wood_Dark", crown="MI_GW_Paint_Ivory", ceiling="beams",
                       beam="MI_GW_Paint_Ivory", ring="MI_GW_GoldLeaf", ceil="MI_GW_Plaster_Ceiling"),
    "study": dict(floor="MI_GW_Parquet_Basket", upper="MI_GW_Wall_DamaskRed", wains="MI_GW_Wood_Mahogany", wh=100,
                  trim="MI_GW_Wood_Dark", crown="MI_GW_Wood_Mahogany", ceiling="beams", beam="MI_GW_Wood_Mahogany",
                  ring="MI_GW_Wood_Dark", ceil="MI_GW_Plaster_Ceiling"),
    "conservatory": dict(floor="MI_GW_Checker_Conservatory", upper="MI_GW_Plaster_Cream", wains=None, wh=0,
                         trim="MI_GW_Marble_White", crown="MI_GW_Paint_Ivory", ceiling="glass", beam="MI_GW_Iron",
                         ring="MI_GW_Iron", ceil="MI_GW_Plaster_Ceiling"),
    "cloakroom": dict(floor="MI_GW_Checker_Hall", upper="MI_GW_Plaster_Cream", wains="MI_GW_Wood_Walnut", wh=100,
                      trim="MI_GW_Wood_Dark", crown="MI_GW_Paint_Ivory", ceiling="plain", beam="MI_GW_Paint_Ivory",
                      ring="MI_GW_GoldLeaf", ceil="MI_GW_Plaster_Ceiling"),
}
CORE = "MI_GW_Plaster_Cream"
SKIN_W, SKIN_U = 2.0, 1.0           # wainscot board / wallpaper skin thickness
BEAM_D = 26.0                       # coffer beam depth

# windows on exterior walls: (line axis, at, centre along the line, type)
WIN_TYPES = {"std": (150, 260, 105), "tall": (180, 420, 105), "tall_hi": (180, 420, 530)}
WINDOWS = [("y", 0, 500, "std"), ("y", 0, 1000, "std"), ("y", 0, 1500, "std"),
           ("y", 0, 2300, "tall"), ("y", 0, 3700, "tall"), ("y", 0, 3000, "tall_hi"),
           ("y", 0, 4500, "std"), ("y", 0, 5000, "std"), ("y", 0, 5500, "std"),
           ("x", 0, 350, "std"), ("x", 0, 1450, "std"), ("x", 0, 2100, "std"), ("x", 0, 2850, "std"),
           ("x", 0, 3950, "std"),
           ("y", 4400, 400, "std"), ("y", 4400, 1000, "std"), ("y", 4400, 1600, "std"),
           ("y", 4400, 2250, "tall"), ("y", 4400, 3750, "tall"),
           ("x", 6000, 350, "std"), ("x", 6000, 1450, "std"), ("x", 6000, 2100, "std"), ("x", 6000, 2800, "std")]
# fireplaces: room, face side, world coordinate along the face line
FIREPLACES = [("dining", "W", 900, True), ("library", "W", 3400, True), ("billiard", "E", 900, False),
              ("study", "W", 2800, False)]
GLASS_LINES = {("y", 4400): (4000, 6000), ("x", 6000): (3200, 4400)}   # conservatory curtain walls

NO_WALL_DECOR = {("study", "N")}   # walls taken by built-in bookcases (dress.py)
WINDOW_GLASS = "/Game/GW/Environment/MI_GW_WindowGlass"   # rain glass (Tools/level/island_materials.py)
FIRE_INFO = []        # filled by arch: (room, x, y, yaw_into_room) for lights + dressing
FACES = {}            # room -> [Face]
PAINT_SLOTS = []      # (face, u, zc, size class) collected for paintings


def log(*a):
    print(*a)


# ------------------------------------------------------------------ level management
def ensure_level():
    les = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
    world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
    if world.get_path_name().split(".")[0] != MAP:
        if unreal.EditorAssetLibrary.does_asset_exist(MAP):
            les.load_level(MAP)
        else:
            les.new_level(MAP, False)
    world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
    assert world.get_path_name().split(".")[0] == MAP, world.get_path_name()
    les.set_current_level_by_name(MAP.rsplit("/", 1)[1])      # spawn into L_Manor, never into the island sublevel
    return world


def clear_part(tag):
    doomed = [a for a in eas.get_all_level_actors() if a.actor_has_tag("GW_Gen") and a.actor_has_tag(tag)]
    if doomed:
        eas.destroy_actors(doomed)
    log(f"  cleared {len(doomed)} {tag} actors")


# ------------------------------------------------------------------ geometry utils
def cut_rects(u0, u1, z0, z1, holes):
    """Rectangles covering [u0,u1]x[z0,z1] minus holes [(a0,a1,b0,b1)]."""
    hs = [(max(a0, u0), min(a1, u1), max(b0, z0), min(b1, z1)) for a0, a1, b0, b1 in holes]
    hs = [h for h in hs if h[1] - h[0] > 0.01 and h[3] - h[2] > 0.01]
    xs = sorted(set([u0, u1] + [h[0] for h in hs] + [h[1] for h in hs]))
    out, last = [], {}
    for i in range(len(xs) - 1):
        a, c = xs[i], xs[i + 1]
        mid = (a + c) / 2
        gaps = sorted((h[2], h[3]) for h in hs if h[0] <= mid <= h[1])
        cur, segs = z0, []
        for g0, g1 in gaps:
            if g0 > cur:
                segs.append((cur, g0))
            cur = max(cur, g1)
        if cur < z1:
            segs.append((cur, z1))
        for b0, b1 in segs:
            k = (round(b0, 2), round(b1, 2))
            if k in last and abs(out[last[k]][1] - a) < 0.01:
                r = out[last[k]]
                out[last[k]] = (r[0], c, b0, b1)
            else:
                last[k] = len(out)
                out.append((a, c, b0, b1))
    return out


def door_openings_on(line, lo, hi):
    out = []
    for d in L["doors"]:
        if (d["axis"], d["at"]) == line and lo < d["center"] < hi:
            out.append(d)
    return out


def windows_on(line, lo, hi):
    return [w for w in WINDOWS if (w[0], w[1]) == line and lo < w[2] < hi]


def wall_pieces():
    lines = {}
    for r in L["rooms"]:
        x0, y0, x1, y1 = r["rect"]
        lines.setdefault(("y", y0), []).append((x0, x1, +1, r["name"]))
        lines.setdefault(("y", y1), []).append((x0, x1, -1, r["name"]))
        lines.setdefault(("x", x0), []).append((y0, y1, +1, r["name"]))
        lines.setdefault(("x", x1), []).append((y0, y1, -1, r["name"]))
    pieces = []
    for line, segs in lines.items():
        bps = sorted(set([s[0] for s in segs] + [s[1] for s in segs]))
        prev = None
        for i in range(len(bps) - 1):
            a, c = bps[i], bps[i + 1]
            mid = (a + c) / 2
            neg = next((s[3] for s in segs if s[2] == -1 and s[0] <= mid <= s[1]), None)
            pos = next((s[3] for s in segs if s[2] == +1 and s[0] <= mid <= s[1]), None)
            if neg is None and pos is None:
                continue
            if prev and prev["neg"] == neg and prev["pos"] == pos and abs(prev["a1"] - a) < 0.01:
                prev["a1"] = c
            else:
                prev = dict(line=line, a0=a, a1=c, neg=neg, pos=pos)
                pieces.append(prev)
    for p in pieces:
        hs = [ROOMS[n]["height"] for n in (p["neg"], p["pos"]) if n]
        p["h"] = max(hs) + 20
        p["ext"] = p["neg"] is None or p["pos"] is None
        same = [q for q in pieces if q is not p and q["line"] == p["line"]]
        p["e0"] = p["a0"] - (T if p["line"][0] == "y" and not any(abs(q["a1"] - p["a0"]) < 0.01 for q in same) else 0)
        p["e1"] = p["a1"] + (T if p["line"][0] == "y" and not any(abs(q["a0"] - p["a1"]) < 0.01 for q in same) else 0)
    return pieces


def line_box(b, group, matn, line, a0, a1, z0, z1, t0=-T, t1=T, coll=True, shadow=True, mesh_name="SM_GW_Cube"):
    axis, at = line
    if axis == "y":
        b.box(group, matn, a0, a1, at + t0, at + t1, z0, z1, coll=coll, shadow=shadow, mesh_name=mesh_name)
    else:
        b.box(group, matn, at + t0, at + t1, a0, a1, z0, z1, coll=coll, shadow=shadow, mesh_name=mesh_name)


# ------------------------------------------------------------------ faces
def make_faces(name, rect, height):
    x0, y0, x1, y1 = rect
    X0, Y0, X1, Y1 = x0 + T, y0 + T, x1 - T, y1 - T
    return [Face(name, "S", X0, Y0, 1, 0, X1 - X0, height, ("y", y0)),
            Face(name, "E", X1, Y0, 0, 1, Y1 - Y0, height, ("x", x1)),
            Face(name, "N", X1, Y1, -1, 0, X1 - X0, height, ("y", y1)),
            Face(name, "W", X0, Y1, 0, -1, Y1 - Y0, height, ("x", x0))]


def line_point(line, c):
    return (c, line[1]) if line[0] == "y" else (line[1], c)


def add_openings(f):
    lo_hi = sorted([f.u_of(*f.P(0, 0, 0)[:2]), f.length])
    for d in L["doors"]:
        if (d["axis"], d["at"]) != f.line:
            continue
        u = f.u_of(*line_point(f.line, d["center"]))
        if 0 < u < f.length:
            f.openings.append(dict(kind="door", u0=u - d["width"] / 2, u1=u + d["width"] / 2, z0=0, z1=DOOR_H,
                                   w=d["width"], u=u))
    for w in WINDOWS:
        if (w[0], w[1]) != f.line:
            continue
        u = f.u_of(*line_point(f.line, w[2]))
        if 0 < u < f.length:
            ww, wh, sill = WIN_TYPES[w[3]]
            f.openings.append(dict(kind="window", u0=u - ww / 2, u1=u + ww / 2, z0=sill, z1=sill + wh, w=ww, h=wh,
                                   u=u, wtype=w[3]))
    return lo_hi


def crown_z(f):
    st = STYLE[f.room]
    return f.height - (BEAM_D if st["ceiling"] == "coffered" else 0)


# ------------------------------------------------------------------ building blocks
def raised_panels(b, f, group, matn, u0, u1, z0, z1, v, target=78.0, stile=11.0, rail=10.0):
    span = u1 - u0
    if span < 40 or z1 - z0 < 30:
        return
    n = max(1, int(round((span - stile) / (target + stile))))
    pw = (span - stile * (n + 1)) / n
    ph = (z1 - z0) - 2 * rail
    for i in range(n):
        uc = u0 + stile + i * (pw + stile) + pw / 2
        f.piece(b, group, "SM_GW_RaisedPanel", matn, uc, v, z0 + rail, sx=pw / 100, sz=ph / 100)


def pilaster(b, f, group, u, z_top, matn, cap="MI_GW_GoldLeaf", v0=SKIN_W):
    f.piece(b, group, "SM_GW_BevelBox", matn, u, v0 + 7, 16, sx=0.54, sy=0.16, sz=0.32, coll=True)
    f.box(b, group, matn, u - 21, u + 21, v0, v0 + 10, 32, z_top - 30, coll=True)
    for du in (-11, 0, 11):                       # flutes as gilded inlays
        f.box(b, group, cap, u + du - 1.2, u + du + 1.2, v0 + 10, v0 + 10.4, 60, z_top - 60, coll=False,
              shadow=False)
    f.piece(b, group, "SM_GW_BevelBox", cap, u, v0 + 6.5, z_top - 24, sx=0.50, sy=0.13, sz=0.12)
    f.piece(b, group, "SM_GW_BevelBox", matn, u, v0 + 7.5, z_top - 9, sx=0.56, sy=0.15, sz=0.18)


def door_casing(b, f, group, o, matn, grand=False):
    w = int(o["w"])
    f.piece(b, group, f"SM_GW_DoorCasing_{w}", matn, o["u"], SKIN_U, 0)
    top = o["z1"] + 16
    if grand:
        f.box(b, group, matn, o["u0"] - 22, o["u1"] + 22, SKIN_U, SKIN_U + 3, top, top + 34, coll=False)
        f.run(b, group, "SM_GW_Cornice", matn, o["u0"] - 34, o["u1"] + 34, SKIN_U, top + 34, sy=0.6, sz=0.6)
        f.piece(b, group, "SM_GW_BevelBox", "MI_GW_GoldLeaf", o["u"], SKIN_U + 3.5, top + 17, sx=0.5, sy=0.02,
                sz=0.2)
    else:
        f.run(b, group, "SM_GW_Cornice", matn, o["u0"] - 22, o["u1"] + 22, SKIN_U, top, sy=0.4, sz=0.4)


def window_dressing(b, f, group, o, room, curtains=True):
    st = STYLE[room]
    u, w, h, sill = o["u"], o["w"], o["h"], o["z0"]
    trim = st["trim"]
    # real glazing (rain on the panes) in the casement: the storm-island exterior (L_Manor_Island) shows through;
    # the old night-view image plane is only a fallback while the glass material does not exist
    if unreal.EditorAssetLibrary.does_asset_exist(WINDOW_GLASS):
        f.box(b, group, WINDOW_GLASS, u - w / 2 + 2, u + w / 2 - 2, -2 * T + 9.25, -2 * T + 9.75, sill + 2, sill + h - 2,
              coll=False, shadow=False, mesh_name="SM_GW_Cube_NoNanite")
    else:
        f.piece(b, group, "SM_GW_Plane", "MI_GW_Window_Night", u, -2 * T + 1, sill + h / 2, sx=w / 100, sy=h / 100,
                roll=90, shadow=False)
    f.box(b, group, trim, u - w / 2 - 6, u + w / 2 + 6, -2 * T + 4, 7, sill - 4, sill + 1, coll=False)
    fz0, fz1, fv0, fv1 = sill, sill + h, -2 * T + 6, -2 * T + 13
    frame = "MI_GW_Paint_Ivory"
    f.box(b, group, frame, u - w / 2, u - w / 2 + 7, fv0, fv1, fz0, fz1, coll=False)
    f.box(b, group, frame, u + w / 2 - 7, u + w / 2, fv0, fv1, fz0, fz1, coll=False)
    f.box(b, group, frame, u - w / 2, u + w / 2, fv0, fv1, fz1 - 7, fz1, coll=False)
    f.box(b, group, frame, u - w / 2, u + w / 2, fv0, fv1, fz0, fz0 + 8, coll=False)
    f.box(b, group, frame, u - 3, u + 3, fv0, fv1, fz0, fz1, coll=False)                   # mullion
    tz = fz0 + h * 0.72
    f.box(b, group, frame, u - w / 2, u + w / 2, fv0, fv1, tz - 3, tz + 3, coll=False)    # transom
    for k in (-0.25, 0.25):
        f.box(b, group, frame, u + k * w - 1, u + k * w + 1, fv0 + 1, fv1 - 2, fz0, fz1, coll=False, shadow=False)
    nbar = max(2, int((h * 0.72) / 50))
    for k in range(1, nbar):
        zz = fz0 + (h * 0.72) * k / nbar
        f.box(b, group, frame, u - w / 2, u + w / 2, fv0 + 1, fv1 - 2, zz - 1, zz + 1, coll=False, shadow=False)
    f.box(b, group, frame, u - w / 2, u + w / 2, fv0 + 1, fv1 - 2, tz + (fz1 - tz) / 2 - 1, tz + (fz1 - tz) / 2 + 1,
          coll=False, shadow=False)
    # casing on the room face
    f.piece(b, group, f"SM_GW_WindowCasing_{int(w)}", trim, u, SKIN_U, sill)
    if not curtains:
        return
    velvet = {"library": "MI_GW_Velvet_Green", "billiard": "MI_GW_Velvet_Green", "ballroom": "MI_GW_Velvet_Gold",
              "corridor_w": "MI_GW_Velvet_Navy", "corridor_e": "MI_GW_Velvet_Red"}.get(room, "MI_GW_Velvet_Red")
    ztop = min(sill + h + 60, crown_z(f) - 26)
    cw = 78
    for side in (-1, 1):
        # curtains hang 8 cm off the wall: clear of the stool, casing, dado panels, chair rail and baseboard
        f.piece(b, group, "SM_GW_Curtain", velvet, u + side * (w / 2 + cw / 2 - 18), 8.0, ztop,
                sx=cw / 100, sz=(ztop - 1) / 100)
        # gold tie-back tassel
        f.piece(b, group, "SM_GW_Ball", "MI_GW_Gold", u + side * (w / 2 + cw / 2 - 18), 22.0, 100,
                sx=0.07, sy=0.07, sz=0.1)
    pw = w + 2 * cw - 10
    f.blocker(b, group, u - pw / 2 + 10, u + pw / 2 - 10, 0, 27, 0, 200)
    f.box(b, group, velvet, u - pw / 2, u + pw / 2, SKIN_U, 25, ztop - 48, ztop + 2, coll=False)
    f.box(b, group, "MI_GW_Gold", u - pw / 2 - 1, u + pw / 2 + 1, SKIN_U, 26, ztop - 51, ztop - 47,
          coll=False, shadow=False)
    f.run(b, group, "SM_GW_Cornice", "MI_GW_GoldLeaf", u - pw / 2 - 4, u + pw / 2 + 4, SKIN_U, ztop + 2, sy=0.85,
          sz=0.25)


def fireplace(b, f, group, u, light_shadows):
    st = STYLE[f.room]
    H = crown_z(f)
    up = st["upper"]
    D = 45.0
    # chimney breast with firebox recess
    f.box(b, group, up, u - 135, u - 55, 0, D, 0, f.height)
    f.box(b, group, up, u + 55, u + 135, 0, D, 0, f.height)
    f.box(b, group, up, u - 55, u + 55, 0, D, 105, f.height)
    f.box(b, group, "MI_GW_Lacquer_Black", u - 55, u + 55, 0, 10, 0, 105)
    f.box(b, group, "MI_GW_Lacquer_Black", u - 55, u - 50, 10, D - 0.5, 0, 104.5, coll=False)
    f.box(b, group, "MI_GW_Lacquer_Black", u + 50, u + 55, 10, D - 0.5, 0, 104.5, coll=False)
    # marble surround, mantel, hearth
    marble = "MI_GW_Marble_Green" if f.room == "billiard" else "MI_GW_Marble_White"
    f.box(b, group, marble, u - 102, u - 56, D, D + 7, 0, 112)
    f.box(b, group, marble, u + 56, u + 102, D, D + 7, 0, 112)
    f.box(b, group, marble, u - 102, u + 102, D, D + 7, 105, 130)
    f.piece(b, group, "SM_GW_BevelBox", "MI_GW_GoldLeaf", u, D + 7.3, 117, sx=0.36, sy=0.01, sz=0.12)
    f.run(b, group, "SM_GW_Crown", marble, u - 100, u + 100, D + 7, 136, sy=0.45, sz=0.36)
    f.piece(b, group, "SM_GW_BevelBox", marble, u, D + 15, 140, sx=2.36, sy=0.34, sz=0.08, coll=True)
    f.box(b, group, "MI_GW_Marble_Black", u - 125, u + 125, D, D + 60, 0, 2.5)
    # grate, logs, embers, flames
    f.box(b, group, "MI_GW_EmberGlow", u - 38, u + 38, 14, 36, 1, 5, coll=False, shadow=False)
    for k, (du, dv, yaw) in enumerate(((-12, 24, 8), (14, 28, -6), (0, 20, 90))):
        f.piece(b, group, "SM_GW_Cylinder", "MI_GW_Wood_Dark", u + du, dv, 10 + 5 * (k == 2), sx=0.11, sy=0.11,
                sz=0.62 if k < 2 else 0.4, pitch=90, yaw_add=yaw, coll=False)
    for du, dv, s in ((-20, 26, 1.0), (-5, 24, 1.35), (10, 27, 1.15), (24, 25, 0.8), (2, 30, 0.9)):
        f.piece(b, group, "SM_GW_Flame", "MI_GW_Fire", u + du, dv, 6, sx=4.2 * s, sy=3.2 * s, sz=6.0 * s,
                coll=False, shadow=False)
    for du in (-36, -18, 0, 18, 36):
        f.box(b, group, "MI_GW_Iron", u + du - 1, u + du + 1, 36, 40, 0, 26, coll=False)
    f.box(b, group, "MI_GW_Iron", u - 40, u + 40, 37, 40, 22, 26, coll=False)
    # brass fender (+ an invisible blocker so nobody walks into the fire)
    f.box(b, group, "MI_GW_Brass", u - 110, u + 110, D + 52, D + 55, 2.5, 14, coll=False)
    f.blocker(b, group, u - 112, u + 112, D, D + 56, 0, 110)
    for side in (-1, 1):
        f.piece(b, group, "SM_GW_Ball", "MI_GW_Brass", u + side * 110, D + 53.5, 14, sx=0.07, sy=0.07, sz=0.07)
    # finishes wrapping the breast: baseboard + crown on front and returns
    trim = st["trim"]
    f.run(b, group, "SM_GW_Baseboard", trim, u - 135, u - 102, D, 0)
    f.run(b, group, "SM_GW_Baseboard", trim, u + 102, u + 135, D, 0)
    f.run(b, group, "SM_GW_Crown", st["crown"], u - 135, u + 135, D, H)
    for side in (-1, 1):
        uu = u + side * 135
        b.add(group, "SM_GW_Baseboard", trim, f.P(uu, D / 2, 0), yaw=f.yaw - side * 90,
              scale=(D / 100, 1, 1), coll=False)
        b.add(group, "SM_GW_Crown", st["crown"], f.P(uu, D / 2, H), yaw=f.yaw - side * 90,
              scale=(D / 100, 1, 1), coll=False)
    f.obstacles.append((u - 140, u + 140, 10000, "breast"))
    x, y, _ = f.P(u, 25, 0)
    FIRE_INFO.append(dict(room=f.room, x=x, y=y, yaw=math.degrees(math.atan2(f.ny, f.nx)), shadows=light_shadows,
                          face=f, u=u, front=D + 7))
    PAINT_SLOTS.append((f, u, 150 + (H - 150) * 0.45, "over", D + 7))


def coffered_ceiling(b, group, rect, H, st):
    X0, Y0, X1, Y1 = rect
    W, Dd = X1 - X0, Y1 - Y0
    nx, ny = max(2, int(round(W / 250))), max(2, int(round(Dd / 250)))
    bw, edge = 28.0, 36.0
    xs = [X0 + W * i / nx for i in range(1, nx)]
    ys = [Y0 + Dd * j / ny for j in range(1, ny)]
    beam = st["beam"]
    for x in xs:
        b.box(group, beam, x - bw / 2, x + bw / 2, Y0, Y1, H - BEAM_D, H, coll=False)
        b.box(group, st["ring"], x - bw / 2 + 5, x + bw / 2 - 5, Y0 + edge, Y1 - edge, H - BEAM_D - 0.6, H - BEAM_D,
              coll=False, shadow=False)
    for y in ys:
        b.box(group, beam, X0, X1, y - bw / 2, y + bw / 2, H - BEAM_D, H, coll=False)
        b.box(group, st["ring"], X0 + edge, X1 - edge, y - bw / 2 + 5, y + bw / 2 - 5, H - BEAM_D - 0.6, H - BEAM_D,
              coll=False, shadow=False)
    for (a0, a1, c0, c1) in ((X0, X1, Y0, Y0 + edge), (X0, X1, Y1 - edge, Y1), (X0, X0 + edge, Y0, Y1),
                             (X1 - edge, X1, Y0, Y1)):
        b.box(group, beam, a0, a1, c0, c1, H - BEAM_D, H, coll=False)
    for x in xs:
        for y in ys:
            b.add(group, "SM_GW_Backplate", st["ring"], (x, y, H - BEAM_D), roll=180, scale=(1.3, 1.3, 1.2),
                  coll=False, shadow=False)
    cx = [X0 + edge] + [x + bw / 2 for x in xs]
    cx1 = [x - bw / 2 for x in xs] + [X1 - edge]
    cy = [Y0 + edge] + [y + bw / 2 for y in ys]
    cy1 = [y - bw / 2 for y in ys] + [Y1 - edge]
    for i in range(nx):
        for j in range(ny):
            w, d = cx1[i] - cx[i], cy1[j] - cy[j]
            b.add(group, "SM_GW_CofferRing", st["ring"] if st["ring"] != "MI_GW_GoldLeaf" else beam,
                  ((cx[i] + cx1[i]) / 2, (cy[j] + cy1[j]) / 2, H), scale=(w / 100, d / 100, 1.0), coll=False,
                  shadow=False)
            if st["ring"] == "MI_GW_GoldLeaf":
                b.box(group, "MI_GW_GoldLeaf", cx[i] + 14, cx1[i] - 14, cy[j] + 14, cy1[j] - 14, H - 0.4, H - 0.1,
                      coll=False, shadow=False)


def beam_ceiling(b, group, rect, H, st, spacing=400):
    X0, Y0, X1, Y1 = rect
    long_x = (X1 - X0) >= (Y1 - Y0)
    if long_x:
        n = max(1, int((X1 - X0) / spacing))
        for i in range(1, n + 1):
            x = X0 + (X1 - X0) * i / (n + 1)
            b.box(group, st["beam"], x - 16, x + 16, Y0, Y1, H - 30, H, coll=False)
            b.box(group, st["ring"], x - 10, x + 10, Y0 + 2, Y1 - 2, H - 30.5, H - 30, coll=False, shadow=False)
    else:
        n = max(1, int((Y1 - Y0) / spacing))
        for i in range(1, n + 1):
            y = Y0 + (Y1 - Y0) * i / (n + 1)
            b.box(group, st["beam"], X0, X1, y - 16, y + 16, H - 30, H, coll=False)
            b.box(group, st["ring"], X0 + 2, X1 - 2, y - 10, y + 10, H - 30.5, H - 30, coll=False, shadow=False)


# ------------------------------------------------------------------ face finishing
def finish_face(b, f, group, pilasters=False, gallery=False):
    st = STYLE[f.room]
    wh = st["wh"]
    H = f.height
    cz = crown_z(f)
    trim = st["trim"]
    holes = [(o["u0"], o["u1"], o["z0"], o["z1"]) for o in f.openings]
    breast = [(a, c) for (a, c, zm, k) in f.obstacles if k == "breast"]
    skip = [(a, c) for (a, c, zm, k) in f.obstacles if k in ("breast", "skip")]
    hide = [(a, c, -1, zm) for (a, c, zm, k) in f.obstacles if k in ("breast", "skip")]
    # skins
    if wh > 0:
        for (a, c, z0, z1) in cut_rects(0, f.length, 0, wh, holes + hide):
            f.box(b, group, st["wains"], a, c, 0, SKIN_W, z0, z1, coll=False)
    for (a, c, z0, z1) in cut_rects(0, f.length, wh, H, holes + hide):
        f.box(b, group, st["upper"], a, c, 0, SKIN_U, z0, z1, coll=False)
    v_trim = SKIN_W if wh > 0 else SKIN_U
    # pilasters (become obstacles for panels)
    pil = []
    if pilasters:
        spacing = 330
        u = 70
        while u < f.length - 60:
            ok = all(not (o["u0"] - pm(o) < u < o["u1"] + pm(o)) for o in f.openings if o["z0"] < cz - 100)
            ok = ok and all(not (a - 40 < u < c + 40) for a, c in skip)
            ok = ok and all(not (a < u < c) for (a, c, zm, k) in f.obstacles if k == "nopil")
            if gallery:
                ok = ok and all(not (a - 30 < u < c + 30) for a, c in f.stair_spans)
            if ok:
                pil.append(u)
                u += spacing
            else:
                u += 20
        for u in pil:
            pilaster(b, f, group, u, cz - 1, st.get("pilaster", trim))
            f.obstacles.append((u - 30, u + 30, 10000, "pilaster"))
    # baseboard, chair rail, panels (doors / breasts / pilasters interrupt); they butt into the 16 cm casings
    for (a, c) in f.free_spans(10, kinds={"door", "breast", "skip", "stair"}, margin=16):
        f.run(b, group, "SM_GW_Baseboard", trim, a, c, v_trim, 0)
    if wh > 0:
        win = [(o["u0"] - 16, o["u1"] + 16) for o in f.openings if o["kind"] == "window" and o["z0"] < wh + 30]
        for (a, c) in f.free_spans(wh, kinds={"door", "breast", "skip", "stair"}, margin=16):
            for (a2, c2) in subtract_spans(a, c, win):
                f.run(b, group, "SM_GW_ChairRail", trim, a2, c2, SKIN_W - 1.0, wh - 4.5)
        for (a, c) in f.free_spans(60, kinds={"door", "breast", "pilaster", "skip", "stair"}, margin=16):
            raised_panels(b, f, group, st["wains"], a + 2, c - 2, 22, wh - 5, SKIN_W)
    # crown
    for (a, c) in f.free_spans(cz - 5, kinds={"breast", "skip"}):
        f.run(b, group, "SM_GW_Crown", st["crown"], a, c, SKIN_U, cz)
    # openings
    for o in f.openings:
        if o["kind"] == "door":
            door_casing(b, f, group, o, trim, grand=o["w"] >= 300)
        elif o["kind"] == "window":
            window_dressing(b, f, group, o, f.room, curtains=o["wtype"] != "tall_hi")
    # painting slots on the upper wall (not where built-in bookcases go)
    if f.room in ("conservatory", "library") or (f.room, f.side) in NO_WALL_DECOR:
        return
    zc = wh + (min(cz, 420) - wh) * 0.5 + 15 if wh > 0 else 200
    for (a, c) in f.free_spans(zc, kinds={"door", "window", "breast", "pilaster", "skip", "stair"}, margin=25):
        span = c - a
        if span < 110:
            continue
        n = max(1, int(span / 230))
        for i in range(n):
            PAINT_SLOTS.append((f, a + span * (i + 0.5) / n, zc, "wall", SKIN_U))


def subtract_spans(a, c, cuts):
    out, cur = [], a
    for (x0, x1) in sorted(cuts):
        if x1 <= cur or x0 >= c:
            continue
        if x0 > cur:
            out.append((cur, x0))
        cur = max(cur, x1)
    if cur < c:
        out.append((cur, c))
    return [(p, q) for p, q in out if q - p > 1]


def pm(o):
    """Pilaster clearance from an opening edge: curtains/pelmet (84) or casing+cornice (34/22) + half pilaster."""
    if o["kind"] == "window":
        return 118 if o.get("wtype") != "tall_hi" else 60
    return 64 if o["w"] >= 300 else 52


def door_jambs(b):
    for d in L["doors"]:
        line = (d["axis"], d["at"])
        c, w = d["center"], d["width"]
        a0, a1 = c - w / 2, c + w / 2
        # pick walnut / mahogany from the rooms on either side
        line_box(b, "Jambs", "MI_GW_Wood_Walnut", line, a0, a0 + 3, 0, DOOR_H, -T - 2.5, T + 2.5)
        line_box(b, "Jambs", "MI_GW_Wood_Walnut", line, a1 - 3, a1, 0, DOOR_H, -T - 2.5, T + 2.5)
        line_box(b, "Jambs", "MI_GW_Wood_Walnut", line, a0, a1, DOOR_H - 3, DOOR_H, -T - 2.5, T + 2.5, coll=False)
        line_box(b, "Jambs", "MI_GW_Marble_White", line, a0, a1, -2, 0.8, -T - 2.5, T + 2.5)   # threshold


def core_walls(b):
    for p in wall_pieces():
        line = p["line"]
        if line in GLASS_LINES:
            lo, hi = GLASS_LINES[line]
            if lo <= p["a0"] and p["a1"] <= hi:
                continue
        holes = []
        for d in door_openings_on(line, p["a0"], p["a1"]):
            holes.append((d["center"] - d["width"] / 2, d["center"] + d["width"] / 2, -1, DOOR_H))
        for w in windows_on(line, p["a0"], p["a1"]):
            ww, wh, sill = WIN_TYPES[w[3]]
            holes.append((w[2] - ww / 2, w[2] + ww / 2, sill, sill + wh))
        for (a, c, z0, z1) in cut_rects(p["e0"], p["e1"], 0, p["h"], holes):
            line_box(b, "Walls", CORE, line, a, c, z0, z1)


def floors_ceilings(b):
    for r in L["rooms"]:
        x0, y0, x1, y1 = r["rect"]
        st = STYLE[r["name"]]
        b.box("Floors", st["floor"], x0, x1, y0, y1, -50, 0)
        H = r["height"]
        if st["ceiling"] != "glass":
            b.box("Ceilings", st["ceil"], x0, x1, y0, y1, H, H + 20)
        rect = (x0 + T, y0 + T, x1 - T, y1 - T)
        if st["ceiling"] == "coffered":
            coffered_ceiling(b, "Ceil_" + r["name"], rect, H, st)
        elif st["ceiling"] == "beams":
            beam_ceiling(b, "Ceil_" + r["name"], rect, H, st)


# ------------------------------------------------------------------ hall: stairs, gallery, columns, cloakroom
def stairs_and_gallery(b, hall_faces):
    g = "Hall_Stairs"
    gx0, gy0, gx1, gy1 = GAL["rect"]
    for st in GAL["stairs"]:
        x0, y0, x1, y1 = st["rect"]
        west = x0 < 3000
        xa, xb = (2015 + SKIN_W, x1) if west else (x0, 3985 - SKIN_W)
        inner = x1 if west else x0
        sgn = 1 if west else -1          # direction from the wall to the open side
        N = int(math.ceil(GZ / 18.0))
        rise, run = GZ / N, (y1 - y0) / N
        alpha = math.degrees(math.atan2(rise, run))
        cx = (x0 + x1) / 2
        for i in range(N):
            ya, yb = y0 + i * run, y0 + (i + 1) * run
            top = (i + 1) * rise
            b.box(g, "MI_GW_Paint_Ivory", xa, xb, ya, yb, 0, top - 3)
            b.box(g, "MI_GW_Marble_White", xa, xb + sgn * 3 if west else xb, ya - 3, yb, top - 3, top)
            if not west:
                b.box(g, "MI_GW_Marble_White", xa - 3, xa, ya - 3, yb, top - 3, top)
            b.box(g, "MI_GW_Carpet_Red", cx - 75, cx + 75, ya - 3.6, yb, top, top + 0.9, coll=False, shadow=False)
            b.box(g, "MI_GW_Carpet_Red", cx - 75, cx + 75, ya - 4.4, ya - 3.4, top - rise + 0.9, top + 0.9,
                  coll=False, shadow=False)
            b.add(g, "SM_GW_Cylinder", "MI_GW_Brass", (cx, ya - 4.8, top - rise + 2.2), pitch=90,
                  scale=(0.012, 0.012, 1.62), coll=False, shadow=False)
            # balusters on the open side (two per tread)
            for k in (0.28, 0.78):
                yy = ya + run * k
                z_rail = (yy - y0 + 3) * rise / run + rise + 88
                b.add(g, "SM_GW_Baluster", "MI_GW_Paint_Ivory", (inner - sgn * 7, yy, top),
                      scale=(0.9, 0.9, (z_rail - top) / 80.0), coll=False)
        # ramp collision just under the nosing line (smooth walking + navmesh)
        ys, ye = y0 - 3 - run, y1 - run - 3
        L_r = (ye - ys) / math.cos(math.radians(alpha))
        th = 20.0
        ym = (ys + ye) / 2
        zm = GZ / 2 - 2 - (th / 2) / math.cos(math.radians(alpha))
        b.add(g, "SM_GW_Cube", CORE, ((xa + xb) / 2, ym, zm), yaw=90, pitch=alpha,
              scale=(L_r / 100, (xb - xa) / 100, th / 100), coll=True, shadow=False, visible=False)
        # handrail + side blocker along the open side
        y_r0, y_r1 = y0 - 12, y1
        z_r0 = (y_r0 - y0 + 3) * rise / run + rise + 88
        z_r1 = GZ + 88
        Lh = math.hypot(y_r1 - y_r0, z_r1 - z_r0)
        b.add(g, "SM_GW_Handrail", "MI_GW_Wood_Dark", (inner - sgn * 7, (y_r0 + y_r1) / 2, (z_r0 + z_r1) / 2),
              yaw=90, pitch=alpha, scale=(Lh / 100, 1.4, 1.4), coll=False)
        b.add(g, "SM_GW_Cube", CORE, (inner - sgn * 7, (y0 + y1) / 2, GZ / 2 + rise + 50), yaw=90, pitch=alpha,
              scale=(Lh / 100, 0.1, 1.0), coll=True, shadow=False, visible=False)
        # string board under the open edge (saw-tooth side gets a sloped fascia)
        b.add(g, "SM_GW_Cube", "MI_GW_Wood_Dark", (inner + sgn * 2, (y0 + y1) / 2, GZ / 2 - 4), yaw=90, pitch=alpha,
              scale=(Lh / 100, 0.04, 0.22), coll=False)
        # newels
        for (ny, z0) in ((y0 - 14, 0.0), (y1 - 4, GZ)):
            b.box(g, "MI_GW_Wood_Dark", inner - sgn * 7 - 13, inner - sgn * 7 + 13, ny - 13, ny + 13, z0, z0 + 112)
            b.add(g, "SM_GW_BevelBox", "MI_GW_Wood_Dark", (inner - sgn * 7, ny, z0 + 115), scale=(0.32, 0.32, 0.07))
            b.add(g, "SM_GW_Finial", "MI_GW_Brass", (inner - sgn * 7, ny, z0 + 118.5), scale=(1.1, 1.1, 1.1),
                  coll=False)
        # under-stair panelling on the open side (closed spandrel)
        b.box(g, "MI_GW_Wood_Dark", min(inner, inner + sgn * 1.5), max(inner, inner + sgn * 1.5), y0, y1, 0, 14,
              coll=False)
    # gallery slab, fascia, balustrade
    b.box(g, "MI_GW_Parquet", 2015, 3985, 1950, 2385, GZ - 3, GZ)
    b.box(g, "MI_GW_Plaster_Ceiling", 2015, 3985, 1950, 2385, GZ - 30, GZ - 3)
    b.box(g, "MI_GW_Paint_Ivory", 2290, 3710, 1934, 1950, GZ - 55, GZ)
    b.box(g, "MI_GW_GoldLeaf", 2290, 3710, 1935, 1937, GZ - 40, GZ - 36, coll=False, shadow=False)
    b.box(g, "MI_GW_GoldLeaf", 2290, 3710, 1935, 1937, GZ - 14, GZ - 11, coll=False, shadow=False)
    b.box(g, "MI_GW_Wood_Dark", 2290, 3710, 1942, 1960, GZ, GZ + 12)
    x = 2312.0
    while x < 3700:
        if all(abs(x - nx) > 18 for nx in (2290, 2645, 3000, 3355, 3710)):
            b.add(g, "SM_GW_Baluster", "MI_GW_Paint_Ivory", (x, 1951, GZ + 12), scale=(0.9, 0.9, 0.95), coll=False)
        x += 21.5
    b.add(g, "SM_GW_Handrail", "MI_GW_Wood_Dark", (3000, 1951, GZ + 88), scale=(14.3, 1.4, 1.4), coll=False)
    for nx in (2645, 3000, 3355):
        b.box(g, "MI_GW_Wood_Dark", nx - 12, nx + 12, 1939, 1963, GZ, GZ + 100)
        b.add(g, "SM_GW_BevelBox", "MI_GW_Wood_Dark", (nx, 1951, GZ + 103), scale=(0.3, 0.3, 0.06))
        b.add(g, "SM_GW_Finial", "MI_GW_Brass", (nx, 1951, GZ + 106), coll=False)
    b.blocker(g, 2290, 3710, 1944, 1958, GZ, GZ + 105)
    # columns carrying the gallery front
    for cxx in (2600, 3400):
        b.add(g, "SM_GW_BevelBox", "MI_GW_Marble_White", (cxx, 1950, 6), scale=(0.68, 0.68, 0.12))
        b.add(g, "SM_GW_ColumnBase", "MI_GW_Marble_White", (cxx, 1950, 12), coll=False)
        b.add(g, "SM_GW_ColumnShaft", "MI_GW_Marble_Green", (cxx, 1950, 30), scale=(1, 1, (GZ - 55 - 30 - 27) / 100),
              coll=True)
        b.add(g, "SM_GW_ColumnCapital", "MI_GW_GoldLeaf", (cxx, 1950, GZ - 55 - 27), coll=False)
        b.add(g, "SM_GW_BevelBox", "MI_GW_Paint_Ivory", (cxx, 1950, GZ - 55 - 4), scale=(0.74, 0.74, 0.08))
    # gallery level trims on the hall walls (W, N, E faces where y > 1950)
    for f in hall_faces:
        spans = []
        if f.side == "N":
            spans = [(0, f.length)]
        elif f.side in ("W", "E"):
            ua, ub = sorted((f.u_of(f.ox, 1950), f.u_of(f.ox, 2385)))
            spans = [(max(0, ua), min(f.length, ub))]
        for a, c in spans:
            st = STYLE["hall"]
            f.run(b, g, "SM_GW_Baseboard", st["trim"], a, c, SKIN_U, GZ)
            f.run(b, g, "SM_GW_ChairRail", st["trim"], a, c, SKIN_U, GZ + 95)
            f.run(b, g, "SM_GW_Crown", st["crown"], a, c, SKIN_U, GZ - 30, sy=0.7, sz=0.7)
    # the gallery wall: big paintings above the gallery floor (N wall, and W/E walls above the flights)
    for f in hall_faces:
        if f.side == "N":
            n = 6
            for i in range(n):
                PAINT_SLOTS.append((f, f.length * (i + 0.5) / n, GZ + 235, "gallery", SKIN_U))
        elif f.side in ("W", "E"):
            ua, ub = sorted((f.u_of(f.ox, 1150), f.u_of(f.ox, 2330)))
            for i in range(3):
                PAINT_SLOTS.append((f, ua + (ub - ua) * (i + 0.5) / 3, GZ + 235, "gallery", SKIN_U))
    # hall string course at gallery level on S/W/E walls (south of the gallery)
    for f in hall_faces:
        if f.side == "S":
            spans = f.free_spans(GZ - 20, kinds={"window", "pilaster", "skip"})
        elif f.side in ("W", "E"):
            ua, ub = sorted((f.u_of(f.ox, 15), f.u_of(f.ox, 1868)))   # stops where the flight reaches it
            spans = [(max(0, ua), min(f.length, ub))]
        else:
            continue
        for a, c in spans:
            f.run(b, g, "SM_GW_Cornice", "MI_GW_Paint_Ivory", a, c, SKIN_U, GZ - 30, sy=0.5, sz=0.5)


def cloakroom(b, hall_south):
    g = "Cloakroom"
    x0, y0, x1, y1 = CLOAK["rect"]
    t = CLOAK["wall_thickness"]
    H = CLOAK["height"]
    dd = CLOAK["door"]
    d0, d1, dh = dd["center"] - dd["width"] / 2, dd["center"] + dd["width"] / 2, dd["height"]
    y0i = 15
    # core
    b.box(g, CORE, x0, x0 + t, y0i, y1, 0, H)
    b.box(g, CORE, x1 - t, x1, y0i, y1, 0, H)
    for (a, c, z0, z1) in cut_rects(x0, x1, 0, H, [(d0, d1, -1, dh)]):
        b.box(g, CORE, a, c, y1 - t, y1, z0, z1)
    b.box(g, "MI_GW_Plaster_Ceiling", x0, x1, y0i, y1, H, H + 20)
    # door jambs + threshold
    b.box(g, "MI_GW_Wood_Walnut", d0, d0 + 3, y1 - t - 2.5, y1 + 2.5, 0, dh)
    b.box(g, "MI_GW_Wood_Walnut", d1 - 3, d1, y1 - t - 2.5, y1 + 2.5, 0, dh)
    b.box(g, "MI_GW_Wood_Walnut", d0, d1, y1 - t - 2.5, y1 + 2.5, dh - 3, dh, coll=False)
    hall_south.obstacles.append((hall_south.u_of(x0, 0) - 1, hall_south.u_of(x1, 0) + 1, 10000, "skip"))
    # interior faces (room style 'cloakroom')
    inner = [Face("cloakroom", "S", x0 + t, y0i, 1, 0, x1 - x0 - 2 * t, H, ("c", 0)),
             Face("cloakroom", "E", x1 - t, y0i, 0, 1, y1 - t - y0i, H, ("c", 1)),
             Face("cloakroom", "N", x1 - t, y1 - t, -1, 0, x1 - x0 - 2 * t, H, ("c", 2)),
             Face("cloakroom", "W", x0 + t, y1 - t, 0, -1, y1 - t - y0i, H, ("c", 3))]
    nf = inner[2]
    u = nf.u_of(dd["center"], y1 - t)
    nf.openings.append(dict(kind="door", u0=u - dd["width"] / 2, u1=u + dd["width"] / 2, z0=0, z1=dh, w=dd["width"],
                            u=u))
    for f in inner:
        finish_face(b, f, g)
    # decorative front double door on the south (exterior) wall, closed
    sf = inner[0]
    uc = sf.length / 2
    sf.piece(b, g, "SM_GW_DoorCasing_180", "MI_GW_Wood_Dark", uc, SKIN_U, 0)
    sf.obstacles.append((uc - 112, uc + 112, 330, "frontdoor"))      # keep wall decor off the front door
    for side in (-1, 1):
        a, c = (uc - 88, uc - 1) if side < 0 else (uc + 1, uc + 88)
        sf.box(b, g, "MI_GW_Wood_Walnut", a, c, SKIN_W, SKIN_W + 5, 0, 268)
        for z0, z1 in ((20, 120), (140, 250)):
            sf.piece(b, g, "SM_GW_RaisedPanel", "MI_GW_Wood_Walnut", (a + c) / 2, SKIN_W + 5, z0, sx=(c - a - 22) / 100,
                     sz=(z1 - z0) / 100)
        sf.piece(b, g, "SM_GW_Ball", "MI_GW_Brass", uc + side * 9, SKIN_W + 5, 115, sx=0.06, sy=0.06, sz=0.06)
    # brass coat rail with hooks on the west wall, bench on the east wall
    wf = inner[3]
    wf.box(b, g, "MI_GW_Wood_Dark", 60, wf.length - 60, SKIN_W, SKIN_W + 4, 165, 177, coll=False)
    k = 80.0
    while k < wf.length - 70:
        wf.piece(b, g, "SM_GW_Ball", "MI_GW_Brass", k, SKIN_W + 10, 172, sx=0.05, sy=0.05, sz=0.05)
        k += 35
    # outer (hall-side) faces: full-height walnut panelling with a cornice on top
    outer = [Face("cloakroom_out", "W", x0, y0i, 0, 1, y1 - y0i, H, ("c", 4)),
             Face("cloakroom_out", "N", x0 - 2, y1, 1, 0, x1 - x0 + 4, H, ("c", 5)),
             Face("cloakroom_out", "E", x1, y1, 0, -1, y1 - y0i, H, ("c", 6))]
    on = outer[1]
    u = on.u_of(dd["center"], y1)
    on.openings.append(dict(kind="door", u0=u - dd["width"] / 2, u1=u + dd["width"] / 2, z0=0, z1=dh,
                            w=dd["width"], u=u))
    for f in outer:
        holes = [(o["u0"], o["u1"], o["z0"], o["z1"]) for o in f.openings]
        for (a, c, z0, z1) in cut_rects(0, f.length, 0, H + 20, holes):
            f.box(b, g, "MI_GW_Wood_Walnut", a, c, 0, SKIN_W, z0, z1, coll=False)
        for (a, c) in f.free_spans(10, kinds={"door"}):
            f.run(b, g, "SM_GW_Baseboard", "MI_GW_Wood_Dark", a, c, SKIN_W, 0)
            f.run(b, g, "SM_GW_ChairRail", "MI_GW_Wood_Dark", a, c, SKIN_W - 1, 100)
            raised_panels(b, f, g, "MI_GW_Wood_Walnut", a + 2, c - 2, 22, 100, SKIN_W)
        for (a, c) in f.free_spans(200, kinds={"door"}):
            raised_panels(b, f, g, "MI_GW_Wood_Walnut", a + 2, c - 2, 130, H - 40, SKIN_W, target=70)
        f.run(b, g, "SM_GW_Cornice", "MI_GW_Paint_Ivory", -3, f.length + 3, 0, H - 10, sy=1.0, sz=1.0)
        for o in f.openings:
            door_casing(b, f, g, o, "MI_GW_Wood_Dark", grand=True)
    # urns on the cornice top, facing the hall
    for xx in (x0 + 40, x1 - 40):
        b.add(g, "SM_GW_Finial", "MI_GW_GoldLeaf", (xx, y1 - 10, H + 20), scale=(2.2, 2.2, 2.6), coll=False)
    return inner


# ------------------------------------------------------------------ conservatory glass house
def conservatory_glass(b):
    g = "Conservatory_Glass"
    glass = WINDOW_GLASS if unreal.EditorAssetLibrary.does_asset_exist(WINDOW_GLASS) else "MI_GW_Glass"
    H = ROOMS["conservatory"]["height"]
    for line, (lo, hi) in GLASS_LINES.items():
        a0, a1 = lo - (T if line[0] == "y" else 0), hi + (T if line[0] == "y" else 0)
        line_box(b, g, "MI_GW_Plaster_Cream", line, a0, a1, 0, 60)
        line_box(b, g, "MI_GW_Marble_White", line, a0, a1, 60, 66, -T - 3, T + 3)
        n = int(round((hi - lo) / 100))
        pts = [lo + (hi - lo) * i / n for i in range(n + 1)]
        for p in pts:
            line_box(b, g, "MI_GW_Iron", line, p - 4, p + 4, 66, H, -6, 6)
        for z0, z1 in ((66, 72), (300, 306), (H - 10, H + 10)):
            line_box(b, g, "MI_GW_Iron", line, a0, a1, z0, z1, -5, 5)
        for i in range(n):
            line_box(b, g, glass, line, pts[i] + 4, pts[i + 1] - 4, 72, H - 10, -0.5, 0.5,
                     shadow=False, mesh_name="SM_GW_Cube_NoNanite")
            # arched top tracery: small iron ribs
            line_box(b, g, "MI_GW_Iron", line, pts[i] + 4, pts[i + 1] - 4, H - 70, H - 66, -3, 3, shadow=True)
    # glass roof with iron rafters
    x0, y0, x1, y1 = ROOMS["conservatory"]["rect"]
    b.box(g, glass, x0, x1 + T, y0 + T, y1 + T, H + 8, H + 9, shadow=False, mesh_name="SM_GW_Cube_NoNanite")
    x = x0 + T
    while x <= x1 + 1:
        b.box(g, "MI_GW_Iron", x - 4, x + 4, y0 + T, y1 + T, H, H + 8, coll=False)
        x += 100
    y = y0 + T
    while y <= y1 + T + 1:
        b.box(g, "MI_GW_Iron", x0, x1 + T, y - 4, y + 4, H, H + 8, coll=False)
        y += 200
    # night-sky dome (unlit 'Is Sky' material: gradient, stars, moon glow) seen through the glass
    sky = "/Game/GW/Lighting/MI_GW_NightSky"      # the lighting agent's instance holds the real moon direction
    sky = sky if unreal.EditorAssetLibrary.does_asset_exist(sky) else "Master/M_GW_NightSky"
    b.add(g, "SM_GW_Sphere", sky, (5000, 3800, -2000), scale=(600, 600, 600), coll=False, shadow=False)
    # ornamental iron cresting along the roof edges
    for xx in range(int(x0) + 50, int(x1) + 1, 100):
        b.add(g, "SM_GW_Finial", "MI_GW_Iron", (xx, y1, H + 10), scale=(0.6, 0.6, 0.8), coll=False)


# ------------------------------------------------------------------ painting placement
def place_paintings(b):
    state_p = os.path.join(ROOT, "Tools", "level", "materials_state.json")
    try:
        paintings = json.load(open(state_p, encoding="utf-8")).get("paintings", [])
    except (OSError, ValueError):
        paintings = []
    ph = [dict(mi=f"/Game/GW/Materials/MI_GW_Painting_PH{i}", rooms=[]) for i in range(4)]
    portraits = [p for p in paintings if p["h"] >= p["w"]] or ph
    landscapes = [p for p in paintings if p["w"] > p["h"]] or portraits

    def pick(pool, room, counter):
        """Rotate through the paintings meant for this room (manifest `rooms`), else through all of them."""
        fit = [p for p in pool if not p.get("rooms") or room in p["rooms"]] or pool
        counter[room] = counter.get(room, rng.randrange(len(fit))) + 1
        return fit[counter[room] % len(fit)]["mi"]
    rng = random.Random(7)
    cp, cl = {}, {}
    placed = 0
    stag = lvl_common.find_asset(lvl_common.load_manifest(), "stag_head")
    for (f, u, zc, kind, v) in PAINT_SLOTS:
        room = f.room
        cz = crown_z(f)
        if stag and kind == "over" and room == "billiard":
            continue                       # the stag head (dress.py) hangs over the billiard-room fireplace
        if room == "library" and kind == "wall":
            continue           # bookcases
        if kind == "over":
            land = True
            s = 1.15
        else:
            land = room in ("billiard", "dining", "ballroom") and (int(u) // 7) % 2 == 0
            s = 1.0
            if room.startswith("corridor"):
                land = False
                s = 0.95
            if room == "hall":
                s = 1.5 if kind != "gallery" else 1.75
            if room == "ballroom":
                s = 1.35
        cw, ch = (100.0, 75.0) if land else (75.0, 100.0)
        cw, ch = cw * s, ch * s
        avail = cz - 30 - zc
        if zc + ch / 2 + 15 > cz - 25:
            zc = cz - 40 - ch / 2
        if avail < 40:
            continue
        m = pick(landscapes, room, cl) if land else pick(portraits, room, cp)
        tag = "L" if land else "P"
        frame = f"SM_GW_Frame_{tag}" if (room in ("hall", "ballroom", "dining") or kind == "over") \
            else (f"SM_GW_Frame2_{tag}" if room in ("study", "billiard") else f"SM_GW_Frame_{tag}")
        fmat = "MI_GW_GoldLeaf" if "Frame_" in frame else "MI_GW_Wood_Dark"
        f.piece(b, "Paintings", "SM_GW_Plane", m, u, v + 0.7, zc, sx=cw / 100, sy=ch / 100, roll=90, shadow=False)
        f.piece(b, "Paintings", frame, fmat, u, v, zc, sx=s, sy=1.0, sz=s)
        # brass picture light on the big ones
        if kind in ("over", "gallery"):
            f.piece(b, "Paintings", "SM_GW_Cylinder", "MI_GW_Brass", u, v + 12, zc + ch / 2 + 22, pitch=90,
                    sx=0.04, sy=0.04, sz=cw * 0.6 / 100, coll=False)
            f.box(b, "Paintings", "MI_GW_Brass", u - 1, u + 1, v, v + 12, zc + ch / 2 + 18, zc + ch / 2 + 21,
                  coll=False)
            PICTURE_LIGHTS.append((f, u, v + 14, zc + ch / 2 + 18))
        placed += 1
    log(f"  paintings placed: {placed} (approved paintings available: {len(paintings)})")


PICTURE_LIGHTS = []


# ------------------------------------------------------------------ chandeliers, sconces (geometry; lights later)
LIGHT_SPOTS = []      # dicts describing lights to spawn in the lights part


def chandelier(b, x, y, ceiling, drop, radius, arms=8, tiers=2, group="Chandeliers", shadows=False, key=1.0):
    zb = ceiling - drop
    b.add(group, "SM_GW_Backplate", "MI_GW_Brass", (x, y, ceiling), roll=180, scale=(2.0, 2.0, 1.5), coll=False,
          shadow=False)
    s = radius / 60.0
    rod0 = zb + 90 * s
    b.add(group, "SM_GW_Cylinder", "MI_GW_Brass", (x, y, (ceiling + rod0) / 2),
          scale=(0.03, 0.03, max(0.05, (ceiling - rod0) / 100)), coll=False, shadow=False)
    b.add(group, "SM_GW_ChandelierBody", "MI_GW_Brass", (x, y, zb), scale=(s, s, s * 0.9), coll=False)
    for t in range(tiers):
        R = radius * (1.0 - 0.38 * t)
        zr = zb + 22 * s + t * 34 * s
        b.add(group, "SM_GW_Torus", "MI_GW_Brass", (x, y, zr), scale=(R / 50, R / 50, 1.0), coll=False,
              shadow=False)
        n = arms if t == 0 else max(4, arms // 2)
        for k in range(n):
            a = 2 * math.pi * (k + 0.5 * t) / n
            ca, sa = math.cos(a), math.sin(a)
            px, py = x + ca * R, y + sa * R
            b.add(group, "SM_GW_Cube", "MI_GW_Brass", (x + ca * R / 2, y + sa * R / 2, zr - 4 * s),
                  yaw=math.degrees(a), scale=(R / 100, 0.02, 0.02), coll=False, shadow=False)
            b.add(group, "SM_GW_CandleCup", "MI_GW_Brass", (px, py, zr), scale=(1.2, 1.2, 1.0), coll=False,
                  shadow=False)
            b.add(group, "SM_GW_Cylinder", "MI_GW_Porcelain", (px, py, zr + 12), scale=(0.025, 0.025, 0.12),
                  coll=False, shadow=False)
            b.add(group, "SM_GW_Flame", "MI_GW_Bulb", (px, py, zr + 18), scale=(1.3, 1.3, 1.4), coll=False,
                  shadow=False)
            for dz in (-10, -22):
                b.add(group, "SM_GW_Drop", "MI_GW_Crystal", (px, py, zr + dz * s), scale=(0.8, 0.8, 1.0),
                      coll=False, shadow=False)
            # garland of drops between arms
            a2 = a + math.pi / n
            for j in range(3):
                rr = R * (0.94 - 0.05 * (j == 1))
                b.add(group, "SM_GW_Drop", "MI_GW_Crystal",
                      (x + math.cos(a2 - (1 - j) * 0.25 * math.pi / n * 2) * rr,
                       y + math.sin(a2 - (1 - j) * 0.25 * math.pi / n * 2) * rr, zr - 8 - 6 * (j == 1)),
                      scale=(0.6, 0.6, 0.7), coll=False, shadow=False)
    b.add(group, "SM_GW_Drop", "MI_GW_Crystal", (x, y, zb - 14 * s), scale=(2.0 * s, 2.0 * s, 2.2 * s), roll=180,
          coll=False, shadow=False)
    LIGHT_SPOTS.append(dict(kind="chandelier", loc=(x, y, zb + 30 * s), radius=radius, shadows=shadows, key=key))


def sconce(b, f, u, z, group="Sconces", key=1.0):
    v = SKIN_U
    f.piece(b, group, "SM_GW_Backplate", "MI_GW_Brass", u, v, z, roll=90, sx=1.0, sy=1.0, sz=1.0)
    f.box(b, group, "MI_GW_Brass", u - 1, u + 1, v + 3, v + 16, z - 1, z + 1, coll=False, shadow=False)
    f.box(b, group, "MI_GW_Brass", u - 13, u + 13, v + 15, v + 17, z - 1, z + 1, coll=False, shadow=False)
    for du in (-12, 12):
        f.piece(b, group, "SM_GW_Tulip", "MI_GW_LampGlow", u + du, v + 16, z + 1, sx=0.8, sy=0.8, sz=0.8,
                shadow=False)
    x, y, _ = f.P(u, v + 22, z + 10)
    LIGHT_SPOTS.append(dict(kind="sconce", loc=(x, y, z + 10), key=key))


def place_sconces(b):
    for room, faces in FACES.items():
        if room in ("conservatory", "library"):
            continue
        for f in faces:
            if (room, f.side) in NO_WALL_DECOR:
                continue
            cz = crown_z(f)
            z = 210 if room != "hall" else 230
            spans = f.free_spans(z, kinds={"door", "window", "breast", "pilaster", "skip", "stair"}, margin=30)
            for (a, c) in spans:
                span = c - a
                if span < 140:
                    continue
                if room.startswith("corridor"):
                    n = max(1, int(span / 330))
                    for i in range(n):
                        uu = a + span * (i + 1) / (n + 1)
                        if all(abs(uu - pu) > 70 for (pf, pu, *_r) in PAINT_SLOTS if pf is f):
                            sconce(b, f, uu, z, key=0.8)
                elif room in ("dining", "billiard", "study", "hall", "ballroom", "library"):
                    # flank breasts / doors: one sconce near each end of long runs
                    if span > 300:
                        for uu in (a + 45, c - 45):
                            if all(abs(uu - pu) > 70 for (pf, pu, *_r) in PAINT_SLOTS if pf is f):
                                sconce(b, f, uu, z)


# ------------------------------------------------------------------ ARCH part
def build_arch():
    b = Batch("GW_Arch")
    floors_ceilings(b)
    core_walls(b)
    door_jambs(b)
    hall_faces = None
    for r in L["rooms"]:
        name = r["name"]
        faces = make_faces(name, r["rect"], r["height"])
        for f in faces:
            add_openings(f)
        if name == "conservatory":
            faces = [f for f in faces if f.line not in GLASS_LINES]
        if name == "ballroom":                      # no pilasters behind the stage backdrop
            fn = next(f for f in faces if f.side == "N")
            fn.obstacles.append((fn.u_of(3560, 0), fn.u_of(2440, 0), 10000, "nopil"))
        if name == "hall":
            hall_faces = faces
            for f in faces:
                f.stair_spans = []
                if f.side in ("W", "E"):
                    for st in GAL["stairs"]:
                        sx0, sy0, sx1, sy1 = st["rect"]
                        ua, ub = sorted((f.u_of(f.ox, sy0 - 20), f.u_of(f.ox, 2385)))
                        if (f.side == "W") == (sx0 < 3000):
                            f.stair_spans.append((ua, ub))
                            f.obstacles.append((ua, ub, 10000, "stair"))
        FACES[name] = faces
    # fireplaces first (they become obstacles)
    for room, side, coord, shadows in FIREPLACES:
        f = next(ff for ff in FACES[room] if ff.side == side)
        u = f.u_of(*line_point(f.line, coord))
        fireplace(b, f, "Fire_" + room, u, shadows)
    cloak_faces = cloakroom(b, next(f for f in hall_faces if f.side == "S"))
    FACES["cloakroom"] = cloak_faces
    for name, faces in FACES.items():
        if name == "cloakroom":
            continue
        for f in faces:
            finish_face(b, f, "Room_" + name, pilasters=name in ("hall", "ballroom"), gallery=name == "hall")
    stairs_and_gallery(b, hall_faces)
    conservatory_glass(b)
    build_room_lights_geometry(b)
    import wall_decor                      # paintings, picture lights, sconces, hall mouldings, stair dado
    importlib.reload(wall_decor)
    wall_decor.place_all(globals(), b)
    b.flush()
    spots_p = os.path.join(ROOT, "Tools", "level", "light_spots.json")
    try:
        candles = json.load(open(spots_p, encoding="utf-8")).get("candles", [])      # written by the dress part
    except (OSError, ValueError):
        candles = []
    with open(spots_p, "w", encoding="utf-8") as fh:
        json.dump(dict(spots=LIGHT_SPOTS, fires=[{k: v for k, v in fi.items() if k != "face"} for fi in FIRE_INFO],
                       picture=[(f.P(u, v, z), math.degrees(math.atan2(f.ny, f.nx))) for (f, u, v, z) in PICTURE_LIGHTS],
                       windows=window_lights(), candles=candles), fh, indent=0)


def window_lights():
    out = []
    for room, faces in FACES.items():
        for f in faces:
            for o in f.openings:
                if o["kind"] == "window":
                    x, y, _ = f.P(o["u"], -12, 0)
                    out.append(dict(loc=(x, y, o["z0"] + o["h"] / 2), yaw=math.degrees(math.atan2(f.ny, f.nx)),
                                    w=o["w"], h=o["h"], room=room))
    return out


def build_room_lights_geometry(b):
    """Chandeliers (geometry now, light actors in the lights part)."""
    R = ROOMS
    chandelier(b, 3000, 1000, 1000, 330, 95, arms=12, tiers=3, shadows=True, key=4.0)        # hall
    for xx in (2500, 3500):
        chandelier(b, xx, 2160, GZ - 30, 60, 30, arms=6, tiers=1, key=0.8)                   # under gallery
    for yy, sh in ((2950, True), (3750, False)):                                              # ballroom
        chandelier(b, 3000, yy, 700, 230, 80, arms=10, tiers=3, shadows=sh, key=1.8)
    for xx, sh in ((700, True), (1300, False)):                                               # dining
        chandelier(b, xx, 900, 500, 175, 55, arms=8, tiers=2, shadows=sh, key=1.4)
    chandelier(b, 1000, 3400, 550, 200, 60, arms=8, tiers=2, shadows=False, key=1.6)         # library
    for xx in (4400, 5600):
        chandelier(b, xx, 900, 500, 150, 40, arms=6, tiers=1, key=1.3)                       # billiard
    chandelier(b, 5000, 2800, 450, 150, 42, arms=6, tiers=1, key=0.8)                        # study
    for xx in (600, 1400):
        chandelier(b, xx, 2100, 450, 120, 26, arms=5, tiers=1, key=0.45)                     # corridor W
    for xx in (4600, 5400):
        chandelier(b, xx, 2100, 450, 120, 26, arms=5, tiers=1, key=0.45)                     # corridor E
    chandelier(b, 3000, 250, 400, 90, 24, arms=5, tiers=1, key=0.45, group="Cloakroom_Light")  # cloakroom
    # conservatory: hanging iron-and-glass lanterns
    for (x, y) in ((4500, 3500), (5600, 3450), (4600, 4150), (5600, 4250), (5250, 3850)):
        g = "Conservatory_Lanterns"
        b.add(g, "SM_GW_Cylinder", "MI_GW_Iron", (x, y, 510), scale=(0.015, 0.015, 1.8), coll=False, shadow=False)
        b.box(g, "MI_GW_LanternGlow", x - 13, x + 13, y - 13, y + 13, 362, 400, coll=False, shadow=False)
        for dx in (-13, 13):
            for dy in (-13, 13):
                b.box(g, "MI_GW_Iron", x + dx - 1.5, x + dx + 1.5, y + dy - 1.5, y + dy + 1.5, 358, 404, coll=False,
                      shadow=False)
        b.add(g, "SM_GW_Cone", "MI_GW_Iron", (x, y, 410), scale=(0.36, 0.36, 0.14), coll=False, shadow=False)
        b.box(g, "MI_GW_Iron", x - 15, x + 15, y - 15, y + 15, 354, 358, coll=False, shadow=False)
        LIGHT_SPOTS.append(dict(kind="lantern", loc=(x, y, 380)))
    # billiard: long brass lamp with three green shades over the table
    g = "Billiard_Lamp"
    bx, by, z = 5000, 900, 199                 # shades' rims ~105 cm above the table rails (86 cm)
    b.box(g, "MI_GW_Brass", bx - 120, bx + 120, by - 2, by + 2, z + 10, z + 14, coll=False)
    for dx in (-110, 110):
        b.add(g, "SM_GW_Cylinder", "MI_GW_Brass", (bx + dx, by, (500 + z + 14) / 2),
              scale=(0.015, 0.015, (500 - z - 14) / 100), coll=False, shadow=False)
    for dx in (-85, 0, 85):
        b.add(g, "SM_GW_Tulip", "MI_GW_Felt_Green", (bx + dx, by, z + 12), roll=180, scale=(2.2, 2.2, 1.4),
              coll=False)
        b.add(g, "SM_GW_Flame", "MI_GW_Bulb", (bx + dx, by, z - 4), scale=(2, 2, 1.5), coll=False, shadow=False)
        LIGHT_SPOTS.append(dict(kind="billiard", loc=(bx + dx, by, z - 6)))


# ------------------------------------------------------------------ LIGHTS part
def build_lights():
    spots = json.load(open(os.path.join(ROOT, "Tools", "level", "light_spots.json"), encoding="utf-8"))
    n = 0
    for s in spots["spots"]:
        x, y, z = s["loc"]
        if s["kind"] == "chandelier":
            k = s["key"]
            point_light((x, y, z), 260 * k, 900 + 550 * k, temp=2700, shadows=s["shadows"],
                        source_radius=max(6, s["radius"] * 0.35), label="L_Chandelier")
        elif s["kind"] == "sconce":
            if s.get("key", 1.0) < 0.9 or n % 2 == 0:      # corridors: every sconce; rooms: every other one
                point_light((x, y, z), 45 * s.get("key", 1.0), 420, temp=2600, shadows=False, source_radius=3,
                            label="L_Sconce", indirect=0.8)
        elif s["kind"] == "lantern":
            point_light((x, y, z), 150, 900, temp=2400, shadows=False, source_radius=5, label="L_Lantern")
        elif s["kind"] == "billiard":
            spot_light((x, y, z), 0, -90, 900, 500, 30, 55, temp=2900, shadows=(abs(x - 5000) < 1),
                       label="L_BilliardLamp")
        n += 1
    for fi in spots["fires"]:
        x, y = fi["x"], fi["y"]
        yaw = math.radians(fi["yaw"])
        point_light((x + math.cos(yaw) * 45, y + math.sin(yaw) * 45, 45), 220, 1100, temp=1850,
                    shadows=fi["shadows"], source_radius=18, label="L_Fire", light_fn="Master/M_GW_LightFlicker")
        n += 1
    for (loc, yaw) in spots["picture"]:
        spot_light(tuple(loc), yaw + 180, -68, 120, 380, 20, 42, temp=2800, shadows=False, label="L_PictureLight")
        n += 1
    for w in spots["windows"]:
        rect_light(tuple(w["loc"]), w["yaw"], w["w"] * 0.9, w["h"] * 0.9, 9.0 * (w["h"] / 260), 900,
                   label="L_WindowMoon")
        n += 1
    log(f"  lights: {n}")


# ------------------------------------------------------------------ ENV part (outside, sky, fog, moon, post)
def build_env():
    b = Batch("GW_Env")
    g = "Garden"
    b.box(g, "MI_GW_Grass", -4000, 10000, -4000, 12000, -90, -62)
    b.box(g, "MI_GW_Stone", 3000, 7600, 4415, 5600, -62, -6)
    b.box(g, "MI_GW_Stone", 6015, 7600, 1800, 4415, -62, -6)
    for (x0, x1, y0, y1) in ((2600, 7800, 5650, 5800), (7650, 7800, 1500, 5800)):
        b.box(g, "MI_GW_Foliage", x0, x1, y0, y1, -10, 140, coll=False)
    for (x, y) in ((4200, 5400), (5000, 5400), (5800, 5400), (7300, 4300), (7300, 3300), (7300, 2300)):
        b.add(g, "SM_GW_ColumnBase", "MI_GW_Stone", (x, y, -6), scale=(1.4, 1.4, 1.4), coll=False)
        b.add(g, "SM_GW_Ball", "MI_GW_Foliage", (x, y, 19), scale=(1.1, 1.1, 1.2), coll=False)
    for (x, y) in ((4600, 5200), (7100, 3800), (7100, 2600)):
        b.add(g, "SM_GW_Cylinder", "MI_GW_Iron", (x, y, 140), scale=(0.08, 0.08, 2.9), coll=False)
        b.box(g, "MI_GW_LanternGlow", x - 12, x + 12, y - 12, y + 12, 285, 320, coll=False, shadow=False)
        b.add(g, "SM_GW_Cone", "MI_GW_Iron", (x, y, 330), scale=(0.34, 0.34, 0.2), coll=False)
        point_light((x, y, 300), 120, 1400, temp=2300, shadows=False, source_radius=8, label="L_GardenLamp",
                    part="GW_Env")
    # distant garden backdrop (night view image) and the moon
    b.add(g, "SM_GW_Plane", "MI_GW_Garden_Backdrop", (4500, 7600, 500), yaw=180, roll=90,
          scale=(60, 15, 1), coll=False, shadow=False)
    b.add(g, "SM_GW_Plane", "MI_GW_Garden_Backdrop", (9500, 3000, 500), yaw=90, roll=90,
          scale=(60, 15, 1), coll=False, shadow=False)
    b.add(g, "SM_GW_Sphere", "MI_GW_Moon", (16000, 20000, 14000), scale=(6, 6, 6), coll=False, shadow=False)
    b.flush()
    # moonlight (direction from the moon towards the house), dim sky light, fog for a navy night sky
    moon = spawn(unreal.DirectionalLight, (6000, 4400, 2000), yaw=234, pitch=-32, part="GW_Env", label="L_Moon")
    c = moon.get_component_by_class(unreal.DirectionalLightComponent)
    c.set_mobility(unreal.ComponentMobility.MOVABLE)
    c.set_editor_property("intensity", 2.5)
    c.set_editor_property("light_color", unreal.Color(r=150, g=175, b=255, a=255))
    c.set_editor_property("cast_shadows", True)
    c.set_editor_property("light_source_angle", 0.6)
    sky = spawn(unreal.SkyLight, (3000, 2200, 1500), part="GW_Env", label="SkyLight_Night")
    sc = sky.get_component_by_class(unreal.SkyLightComponent)
    sc.set_mobility(unreal.ComponentMobility.MOVABLE)
    sc.set_editor_property("intensity", 0.6)
    sc.set_editor_property("lower_hemisphere_is_black", True)
    sc.set_editor_property("real_time_capture", False)
    fog = spawn(unreal.ExponentialHeightFog, (3000, 2200, -100), part="GW_Env", label="Fog_Night")
    fc = fog.get_component_by_class(unreal.ExponentialHeightFogComponent)
    fc.set_editor_property("fog_density", 0.02)
    fc.set_editor_property("fog_height_falloff", 0.2)
    fc.set_editor_property("start_distance", 4000.0)
    fc.set_editor_property("fog_inscattering_luminance", unreal.LinearColor(0.004, 0.006, 0.014, 1.0))
    fc.set_editor_property("fog_max_opacity", 1.0)
    post_process()


def post_process():
    ppv = spawn(unreal.PostProcessVolume, (3000, 2200, 500), part="GW_Env", label="PP_Manor_Night")
    ppv.set_editor_property("unbound", True)
    ppv.set_editor_property("priority", 1.0)
    s = ppv.get_editor_property("settings")
    vals = {
        "auto_exposure_method": unreal.AutoExposureMethod.AEM_HISTOGRAM,
        "auto_exposure_min_brightness": 3.0,
        "auto_exposure_max_brightness": 6.0,
        "auto_exposure_bias": -0.6,
        "auto_exposure_speed_up": 2.0,
        "auto_exposure_speed_down": 1.0,
        "bloom_intensity": 0.45,
        "bloom_threshold": 1.5,
        "vignette_intensity": 0.35,
        "color_saturation": unreal.Vector4(0.93, 0.93, 0.93, 1.0),
        "color_gain": unreal.Vector4(1.0, 0.99, 0.97, 1.0),
        "color_contrast": unreal.Vector4(1.04, 1.04, 1.04, 1.0),
        "film_toe": 0.6,
        "motion_blur_amount": 0.0,
        "local_exposure_highlight_contrast_scale": 0.85,
        "local_exposure_shadow_contrast_scale": 0.9,
        "lumen_final_gather_quality": 1.5,
        "lumen_scene_lighting_quality": 1.5,
        "lumen_reflection_quality": 1.0,
        "lumen_max_trace_distance": 6000.0,
    }
    for k, v in vals.items():
        try:
            s.set_editor_property(k, v)
            s.set_editor_property("override_" + k, True)
        except Exception as e:
            log("   pp skip", k, e)
    ppv.set_editor_property("settings", s)


# ------------------------------------------------------------------ settings (world settings, game mode)
def world_settings(world):
    ws = world.get_world_settings()
    try:
        ws.set_editor_property("force_no_precomputed_lighting", True)
    except Exception as e:
        log("  ws skip", e)
    gm = unreal.EditorAssetLibrary.load_blueprint_class("/Game/GW/Blueprints/BP_GW_GameMode")
    if gm:
        ws.set_editor_property("default_game_mode", gm)
        log("  GameMode override = BP_GW_GameMode")
    else:
        log("  BP_GW_GameMode not found yet")


# ------------------------------------------------------------------ main
def _gw_lighting():
    """Lights + atmosphere are owned by the lighting agent (Tools/lighting); build_lights/build_env above are unused."""
    p = os.path.join(ROOT, "Tools", "lighting")
    if p not in sys.path:
        sys.path.insert(0, p)
    import rig
    importlib.reload(rig)
    return rig


def main():
    world = ensure_level()
    parts = ["arch", "lights", "env", "dress", "markers", "cams", "nav", "settings"] if ALL else ARGS
    if "arch" in parts:
        clear_part("GW_Arch")
        build_arch()
    if "lights" in parts:
        clear_part("GW_Light")
        _gw_lighting().build_lights(globals())      # lighting agent: Tools/lighting/rig.py (+ look.py numbers)
    if "env" in parts:
        clear_part("GW_Env")
        _gw_lighting().build_env(globals())         # garden, moon, sky, fog, haze, post-process
    if "dress" in parts or "markers" in parts or "cams" in parts or "nav" in parts:
        import dress
        importlib.reload(dress)
        # Tools/level/freeze_dress.py turned the props into hand-placed actors: never regenerate them
        if "dress" in parts and os.path.exists(os.path.join(os.path.dirname(os.path.abspath(__file__)), "level", "dress_frozen.flag")):
            print("  dress: FROZEN (Tools/level/dress_frozen.flag): the hand-placed props are kept, nothing regenerated")
            parts = [p for p in parts if p != "dress"]
        if "dress" in parts:
            clear_part("GW_Dress")
            dress.build_dress(globals())
            _gw_lighting().tune_dress_lights(globals())   # dress lamps + stage spots get the lighting look
        if "markers" in parts:
            clear_part("GW_Markers")
            dress.build_markers(globals())
        if "cams" in parts:
            clear_part("GW_Cams")
            dress.build_cams(globals())
        if "nav" in parts:
            clear_part("GW_Nav")
            dress.build_nav(globals())
    elif any(p in parts for p in ("arch", "env")):
        unreal.SystemLibrary.execute_console_command(world, "BuildPaths")      # geometry changed: rebuild nav
    if "settings" in parts:
        world_settings(world)
    les = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
    les.save_current_level()
    log("saved", MAP)


main()
