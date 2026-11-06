"""Wall decor for L_Manor (arch part): paintings + picture lights, wall sconces, hall panel mouldings and the
raked stair dado. Everything is placed against exact clearance rectangles per wall face, so no item ever
overlaps a door (opening + casing + over-door cornice), a window (reveal, casing, curtains, pelmet), a pilaster,
a fireplace breast, the stairs, the gallery, bookcases, furniture standing against the wall (dress_state.json
footprints with heights), or another wall item.

Called from build_manor.build_arch():  wall_decor.place_all(globals(), batch)
"""
import json
import math
import os
import random

M = 12.0           # clearance around every wall item (cm)


# ------------------------------------------------------------------ clearance rectangles (face-local u, z)
def face_blocks(G, f, foot):
    st = G["STYLE"][f.room]
    cz = G["crown_z"](f)
    wh = st["wh"]
    H = f.height
    GZ = G["GZ"]
    R = []
    for o in f.openings:
        if o["kind"] == "door":
            grand = o["w"] >= 300
            R.append((o["u0"] - (58 if grand else 40), o["u1"] + (58 if grand else 40), -1,
                      o["z1"] + 16 + (56 if grand else 16), "door"))
        elif o.get("wtype") == "tall_hi":
            R.append((o["u0"] - 24, o["u1"] + 24, o["z0"] - 24, o["z1"] + 24, "window"))
        else:
            R.append((o["u0"] - 84, o["u1"] + 84, -1, cz + 1, "window"))
    for (a, c, zm, k) in f.obstacles:
        if k in ("breast", "pilaster", "nopil"):
            R.append((a, c, -1, H + 1, k))
        elif k in ("skip", "frontdoor"):
            R.append((a, c, -1, zm, k))
        elif k == "stair":
            R.append((a, c, -1, GZ + 112, k))
    R.append((-50, f.length + 50, cz - 28, H + 50, "crown"))
    R.append((-50, f.length + 50, -50, (wh + 14) if wh > 0 else 26, "dado"))
    if f.room == "hall":
        for (ua, ub, zone) in hall_zones(G, f):
            if zone == "gallery":
                R.append((ua, ub, GZ - 62, GZ + 112, "gallery"))
            else:
                R.append((ua, ub, GZ - 40, GZ - 6, "stringcourse"))
    # furniture / bookcases / wall-mounted dressing within 1 m of the wall
    for fp in foot:
        x0, y0, x1, y1 = fp[:4]
        top = fp[5] if len(fp) > 5 else 120.0
        us, vs = [], []
        for (x, y) in ((x0, y0), (x1, y0), (x0, y1), (x1, y1)):
            us.append(f.u_of(x, y))
            vs.append((x - f.ox) * f.nx + (y - f.oy) * f.ny)
        if min(vs) < 100 and max(vs) > -5 and max(us) > 0 and min(us) < f.length:
            R.append((min(us) - 8, max(us) + 8, -1, top + 25, "furniture:" + str(fp[4])))
    return R


def hall_zones(G, f):
    """u-ranges of a hall face: 'gallery' where the gallery runs along the wall, else 'open'."""
    if f.side == "N":
        return [(0, f.length, "gallery")]
    if f.side in ("W", "E"):
        ua, ub = sorted((f.u_of(f.ox, 1950), f.u_of(f.ox, 2385)))
        uo0, uo1 = sorted((f.u_of(f.ox, 15), f.u_of(f.ox, 1950)))
        return [(ua, ub, "gallery"), (uo0, uo1, "open")]
    return [(0, f.length, "open")]


def free_intervals(f, blocks, z0, z1, lo=0.0, hi=None):
    hi = f.length if hi is None else hi
    cuts = sorted((a, c) for (a, c, b0, b1, k) in blocks if b0 < z1 and b1 > z0)
    out, cur = [], lo
    for a, c in cuts:
        if c <= cur:
            continue
        if a > cur:
            out.append((cur, min(a, hi)))
        cur = max(cur, c)
        if cur >= hi:
            break
    if cur < hi:
        out.append((cur, hi))
    return [(a, c) for a, c in out if c - a > 1]


def clear(blocks, u0, u1, z0, z1, ignore=()):
    return all(not (a < u1 and c > u0 and b0 < z1 and b1 > z0) for (a, c, b0, b1, k) in blocks
               if k not in ignore)


# ------------------------------------------------------------------ pieces
def panel_frame(b, f, g, u0, u1, z0, z1, mat="MI_GW_Paint_Ivory", fillet="MI_GW_GoldLeaf", v=None):
    v = G_SKIN_U if v is None else v
    if u1 - u0 < 40 or z1 - z0 < 40:
        return
    f.run(b, g, "SM_GW_PanelMould", mat, u0, u1, v, z0)
    f.run(b, g, "SM_GW_PanelMould", mat, u0, u1, v, z1 - 4)
    f.piece(b, g, "SM_GW_PanelMould", mat, u0 + 4, v, (z0 + z1) / 2, sx=(z1 - z0 - 8) / 100, pitch=90)
    f.piece(b, g, "SM_GW_PanelMould", mat, u1, v, (z0 + z1) / 2, sx=(z1 - z0 - 8) / 100, pitch=90)
    if fillet:
        i = 9.0
        f.box(b, g, fillet, u0 + i, u1 - i, v, v + 0.5, z0 + i, z0 + i + 0.8, coll=False, shadow=False)
        f.box(b, g, fillet, u0 + i, u1 - i, v, v + 0.5, z1 - i - 0.8, z1 - i, coll=False, shadow=False)
        f.box(b, g, fillet, u0 + i, u0 + i + 0.8, v, v + 0.5, z0 + i, z1 - i, coll=False, shadow=False)
        f.box(b, g, fillet, u1 - i - 0.8, u1 - i, v, v + 0.5, z0 + i, z1 - i, coll=False, shadow=False)


def painting(b, f, mi, u, zc, land, s, v, frame_kind="gilt", light=False):
    cw, ch = ((100.0, 75.0) if land else (75.0, 100.0))
    cw, ch = cw * s, ch * s
    tag = "L" if land else "P"
    frame = f"SM_GW_Frame_{tag}" if frame_kind == "gilt" else f"SM_GW_Frame2_{tag}"
    fmat = "MI_GW_GoldLeaf" if frame_kind == "gilt" else "MI_GW_Wood_Dark"
    f.piece(b, "Paintings", "SM_GW_Plane", mi, u, v + 0.7, zc, sx=cw / 100, sy=ch / 100, roll=90, shadow=False)
    f.piece(b, "Paintings", frame, fmat, u, v, zc, sx=s, sy=1.0, sz=s)
    if light:
        f.piece(b, "Paintings", "SM_GW_Cylinder", "MI_GW_Brass", u, v + 12, zc + ch / 2 + 22, pitch=90,
                sx=0.04, sy=0.04, sz=cw * 0.6 / 100, coll=False)
        f.box(b, "Paintings", "MI_GW_Brass", u - 1, u + 1, v, v + 12, zc + ch / 2 + 18, zc + ch / 2 + 21, coll=False)
        G_PICTURE.append((f, u, v + 14, zc + ch / 2 + 18))


def frame_size(land, s, frame_kind):
    cw, ch = ((100.0, 75.0) if land else (75.0, 100.0))
    pad = 21.0 if frame_kind == "gilt" else 15.0
    return (cw + pad) * s, (ch + pad) * s


G_SKIN_U = 1.0
G_PICTURE = []


# ------------------------------------------------------------------ main entry
def place_all(G, b):
    global G_SKIN_U, G_PICTURE
    G_SKIN_U = G["SKIN_U"]
    G_PICTURE = G["PICTURE_LIGHTS"]
    root = G["ROOT"]
    try:
        foot = json.load(open(os.path.join(root, "Tools", "level", "dress_state.json"), encoding="utf-8"))["foot"]
    except (OSError, ValueError, KeyError):
        foot = []
    try:
        paintings = json.load(open(os.path.join(root, "Tools", "level", "materials_state.json"),
                                   encoding="utf-8")).get("paintings", [])
    except (OSError, ValueError):
        paintings = []
    ph = [dict(mi=f"/Game/GW/Materials/MI_GW_Painting_PH{i}", rooms=[]) for i in range(4)]
    portraits = [p for p in paintings if p["h"] >= p["w"]] or ph
    landscapes = [p for p in paintings if p["w"] > p["h"]] or portraits
    rng = random.Random(7)
    counters = {}

    def pick(land, room):
        pool = landscapes if land else portraits
        fit = [p for p in pool if not p.get("rooms") or room in p["rooms"]] or pool
        key = (land, room)
        counters[key] = counters.get(key, rng.randrange(len(fit))) + 1
        return fit[counters[key] % len(fit)]["mi"]

    stag = G["lvl_common"].find_asset(G["lvl_common"].load_manifest(), "stag_head")
    stats = dict(paintings=0, sconces=0, frames=0, skipped=0)
    blocks_by_face = {}
    for room, faces in G["FACES"].items():
        for f in faces:
            if room not in G["STYLE"]:
                continue
            blocks_by_face[id(f)] = (f, face_blocks(G, f, foot))

    # 1. over-mantel paintings (on the chimney breast)
    for (f, u, zc, kind, v) in G["PAINT_SLOTS"]:
        if kind != "over" or (stag and f.room == "billiard"):
            continue
        fb = blocks_by_face[id(f)][1]
        s = 1.15
        W, Hh = frame_size(True, s, "gilt")
        cz = G["crown_z"](f)
        zc = min(zc, cz - 40 - Hh / 2 - 30)
        zc = max(zc, 150 + Hh / 2)
        painting(b, f, pick(True, f.room), u, zc, True, s, v, "gilt", light=True)
        fb.append((u - W / 2 - M, u + W / 2 + M, zc - Hh / 2 - M, zc + Hh / 2 + 40, "painting"))
        stats["paintings"] += 1

    # 2. hall: panel-moulding frames (lower and upper zones) with a painting centred in each
    GZ = G["GZ"]
    for room in ("hall",):
        for f in G["FACES"].get(room, []):
            fb = blocks_by_face[id(f)][1]
            zones = [(G["STYLE"]["hall"]["wh"] + 22, GZ - 50, 1.45, "lower"), (GZ + 128, G["crown_z"](f) - 40, 1.7,
                                                                             "upper")]
            for (z0, z1, s, zname) in zones:
                if f.side == "N" and zname == "lower":
                    z1 = GZ - 70
                for (a, c) in free_intervals(f, fb, z0, z1):
                    n = max(1, int(math.ceil((c - a) / 420.0)))
                    w = (c - a) / n
                    for k in range(n):
                        pa, pc = a + k * w + 14, a + (k + 1) * w - 14
                        if pc - pa < 70 or z1 - z0 < 90:
                            continue
                        panel_frame(b, f, "WallDecor", pa, pc, z0, z1)
                        stats["frames"] += 1
                        for (e0, e1, f0, f1) in ((pa - 2, pa + 7, z0, z1), (pc - 7, pc + 2, z0, z1),
                                                 (pa, pc, z0 - 2, z0 + 7), (pa, pc, z1 - 7, z1 + 2)):
                            fb.append((e0, e1, f0, f1, "frame"))
                        um, zm = (pa + pc) / 2, (z0 + z1) / 2
                        for land in (False, True):
                            for ss in (s, s * 0.85, s * 0.7):
                                W, Hh = frame_size(land, ss, "gilt")
                                if W + 2 * 30 <= pc - pa and Hh + 2 * 25 <= z1 - z0:
                                    break
                            else:
                                continue
                            if clear(fb, um - W / 2 - M, um + W / 2 + M, zm - Hh / 2 - M, zm + Hh / 2 + 40):
                                painting(b, f, pick(land, "hall"), um, zm, land, ss, G["SKIN_U"], "gilt",
                                         light=(zname == "upper"))
                                fb.append((um - W / 2 - M, um + W / 2 + M, zm - Hh / 2 - M, zm + Hh / 2 + 40,
                                           "painting"))
                                stats["paintings"] += 1
                            break
            stair_dado(G, b, f)
    stair_spandrels(G, b)

    # 2b. conservatory: ivory panel-moulding frames on the two masonry walls (no paintings in a glasshouse)
    for f in G["FACES"].get("conservatory", []):
        fb = blocks_by_face[id(f)][1]
        for (a, c) in free_intervals(f, fb, 60, 520):
            n = max(1, int(math.ceil((c - a) / 300.0)))
            w = (c - a) / n
            for k in range(n):
                pa, pc = a + k * w + 16, a + (k + 1) * w - 16
                if pc - pa >= 70:
                    panel_frame(b, f, "WallDecor", pa, pc, 60, 520, fillet=None)
                    stats["frames"] += 1

    # 3. other rooms: paintings evenly spread in the free wall intervals
    for room, faces in G["FACES"].items():
        if room in ("hall", "conservatory", "library") or room not in G["STYLE"]:
            continue
        for f in faces:
            fb = blocks_by_face[id(f)][1]
            st = G["STYLE"][room]
            cz = G["crown_z"](f)
            wh = st["wh"]
            zc = wh + (min(cz, 420) - wh) * 0.5 + 15 if wh > 0 else 200
            corridor = room.startswith("corridor")
            s = 0.95 if corridor else (1.35 if room == "ballroom" else 1.0)
            kind = "plain" if room in ("study", "billiard") else "gilt"
            for (a, c) in free_intervals(f, fb, zc - 80, zc + 80):
                span = c - a
                land_pref = (room in ("billiard", "dining", "ballroom", "study")) and not corridor
                placed = False
                for land in ((land_pref, not land_pref) if land_pref else (False,)):
                    W, Hh = frame_size(land, s, kind)
                    need = W + 2 * M
                    if span < need:
                        continue
                    n = max(1, min(int(span / (230 if corridor else 260)), int((span + 40) / (need + 40))))
                    for i in range(n):
                        u = a + span * (i + 0.5) / n
                        if clear(fb, u - W / 2 - M, u + W / 2 + M, zc - Hh / 2 - M, zc + Hh / 2 + M):
                            painting(b, f, pick(land, room), u, zc, land, s, G["SKIN_U"], kind)
                            fb.append((u - W / 2 - M, u + W / 2 + M, zc - Hh / 2 - M, zc + Hh / 2 + M, "painting"))
                            stats["paintings"] += 1
                            placed = True
                    if placed:
                        break
                if not placed and span > 60:
                    stats["skipped"] += 1

    # 4. sconces in the gaps between paintings / openings (corridors: every gap, rooms: alternate gaps)
    for room, faces in G["FACES"].items():
        if room in ("conservatory", "library") or room not in G["STYLE"]:
            continue
        corridor = room.startswith("corridor")
        for f in faces:
            fb = blocks_by_face[id(f)][1]
            z = 230 if room == "hall" else 205
            gaps = free_intervals(f, fb, z - 14 - M, z + 32 + M)
            take = 0
            for (a, c) in gaps:
                if c - a < (60 if corridor else 90):
                    continue
                if not corridor and room != "cloakroom":
                    take += 1
                    if take % 2 == 0:
                        continue
                u = (a + c) / 2
                G["sconce"](b, f, u, z, key=0.8 if corridor else 1.0)
                fb.append((u - 18 - M, u + 18 + M, z - 14 - M, z + 32 + M, "sconce"))
                stats["sconces"] += 1
    print(f"  wall decor: {stats['paintings']} paintings, {stats['sconces']} sconces, {stats['frames']} moulding "
          f"frames, {stats['skipped']} wall gaps too small for a painting")


# ------------------------------------------------------------------ raked dado along the stair flights (wall side)
def stair_dado(G, b, f):
    if f.side not in ("W", "E"):
        return
    GZ, GAL = G["GZ"], G["GAL"]
    for st in GAL["stairs"]:
        x0, y0, x1, y1 = st["rect"]
        if (f.side == "W") != (x0 < 3000):
            continue
        N = int(math.ceil(GZ / 18.0))
        rise, run = GZ / N, (y1 - y0) / N
        alpha = math.degrees(math.atan2(rise, run))
        zn = lambda y: (y - y0 + 3) * rise / run + rise  # noqa: E731  nosing line
        sgn = -1 if f.side == "W" else 1          # pitch sign: the flight rises toward -u on W, +u on E
        g = "WallDecor"
        v = G["SKIN_U"]
        inv = lambda z: y0 - 3 + (z - rise) * run / rise  # noqa: E731  y where the nosing line reaches z
        ya = y0 - 20
        # wall string (sloped board just above the treads) and raked dado rail; both die into the string-course
        # cornice (GZ-40) instead of crossing it
        for (yb, z_off, mesh, mat, sy, sz, vv) in (
                (min(y1, inv(GZ - 42 - 14)), 2, "SM_GW_Cube", "MI_GW_Wood_Dark", 0.03, 0.24, v + 1.5),
                (min(y1, inv(GZ - 42 - 99)), 92, "SM_GW_ChairRail", G["STYLE"]["hall"]["trim"], 1.0, 1.0, v)):
            L = (yb - ya) / math.cos(math.radians(alpha))
            ym = (ya + yb) / 2
            f.piece(b, g, mesh, mat, f.u_of(f.ox, ym), vv, zn(ym) + z_off, sx=L / 100, sy=sy, sz=sz,
                    pitch=sgn * alpha, coll=False)
        # raised panels stepping up between string and rail, frames stepping up above the rail
        seg = 2 * run
        y = y0 + 6
        while y + seg <= y1 - 4:
            ylo, yhi = y, y + seg
            ua, ub = sorted((f.u_of(f.ox, ylo), f.u_of(f.ox, yhi)))
            zb = zn(yhi) + 18
            zt = min(zn(ylo) + 86, GZ - 44)        # stay under the string-course cornice
            if zt - zb > 24:
                f.piece(b, g, "SM_GW_RaisedPanel", "MI_GW_Wood_Walnut", (ua + ub) / 2, v, zb,
                        sx=(ub - ua - 10) / 100, sz=(zt - zb) / 100)
            y += seg
        y = y0 + 6
        seg = 4 * run
        while y + seg <= y1 - 4:
            ylo, yhi = y, y + seg
            ua, ub = sorted((f.u_of(f.ox, ylo), f.u_of(f.ox, yhi)))
            zb = zn(yhi) + 118
            zt = GZ - 52
            if zt - zb >= 70:
                panel_frame(b, f, g, ua + 10, ub - 10, zb, zt)
            y += seg


# ------------------------------------------------------------------ panelled spandrels (open side under each flight)
def stair_spandrels(G, b):
    """The closed triangle under each flight (seen from the hall) gets stepped raised panels."""
    from lvl_build import Face
    GZ, GAL = G["GZ"], G["GAL"]
    for st in GAL["stairs"]:
        x0, y0, x1, y1 = st["rect"]
        west = x0 < 3000
        inner = x1 if west else x0
        N = int(math.ceil(GZ / 18.0))
        rise, run = GZ / N, (y1 - y0) / N
        zn = lambda y: (y - y0 + 3) * rise / run + rise  # noqa: E731
        # face on the open side, normal pointing into the hall
        if west:
            f = Face("hall", "spandrel", inner, y1, 0, -1, y1 - y0, GZ, ("s", 0))
        else:
            f = Face("hall", "spandrel", inner, y0, 0, 1, y1 - y0, GZ, ("s", 1))
        seg = 2 * run
        y = y0 + 2 * run
        while y + seg <= y1 - 2:
            ylo, yhi = y, y + seg
            zt = zn(ylo) - 40
            if zt - 26 >= 30:
                ua, ub = sorted((f.u_of(inner, ylo), f.u_of(inner, yhi)))
                f.piece(b, "WallDecor", "SM_GW_RaisedPanel", "MI_GW_Paint_Ivory", (ua + ub) / 2, 0.0, 26,
                        sx=(ub - ua - 8) / 100, sz=(zt - 26) / 100)
            y += seg
