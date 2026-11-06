"""Generate the architectural detail meshes for L_Manor as OBJ files (pure Python, no deps).

  python -I -X utf8 Tools/level/gen_arch_meshes.py      -> Tools/level/meshes/*.obj

Authoring convention (UE space, cm, Z up):
  * wall-mounted pieces face +Y (back at y=0 against the wall), length along X, centred on x=0
  * linear profiles: length 100 along X (-50..50), profile in (Y=depth, Z=height)
  * lathe pieces: axis Z, base at z=0
Interchange's OBJ import maps OBJ (x, y, z) -> UE (x, -y, z), so vertices are written with y negated and the
triangle winding is chosen so that the geometric normal (in OBJ space) matches the intended outward normal.
"""
import math
import os

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "meshes")
os.makedirs(OUT, exist_ok=True)


def sub(a, b): return (a[0] - b[0], a[1] - b[1], a[2] - b[2])
def cross(a, b): return (a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0])
def dot(a, b): return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]


def norm(a):
    l = math.sqrt(dot(a, a)) or 1.0
    return (a[0] / l, a[1] / l, a[2] / l)


class Mesh:
    def __init__(self, name):
        self.name = name
        self.v, self.vn, self.vt, self.f = [], [], [], []

    def _vert(self, p):
        self.v.append(p)
        return len(self.v)

    def _norm(self, n):
        self.vn.append(norm(n))
        return len(self.vn)

    def _uv(self, p, n):
        ax = max(range(3), key=lambda i: abs(n[i]))
        a, b = [(1, 2), (0, 2), (0, 1)][ax]
        self.vt.append((p[a] / 100.0, p[b] / 100.0))
        return len(self.vt)

    def tri(self, p0, p1, p2, out, normals=None):
        """Add a triangle (UE coords). out = intended outward normal; normals = optional per-vertex normals."""
        gn = cross(sub(p1, p0), sub(p2, p0))
        if dot(gn, gn) < 1e-12:
            return
        pts = [p0, p1, p2]
        nrm = list(normals) if normals else [out, out, out]
        # winding check in OBJ space (y negated)
        o = lambda p: (p[0], -p[1], p[2])
        gno = cross(sub(o(pts[1]), o(pts[0])), sub(o(pts[2]), o(pts[0])))
        if dot(gno, o(out)) < 0:
            pts = [pts[0], pts[2], pts[1]]
            nrm = [nrm[0], nrm[2], nrm[1]]
        face = []
        for p, n in zip(pts, nrm):
            vi = self._vert(p)
            ni = self._norm(n)
            ti = self._uv(p, n)
            face.append((vi, ti, ni))
        self.f.append(face)

    def quad(self, a, b, c, d, out, normals=None):
        if normals:
            self.tri(a, b, c, out, (normals[0], normals[1], normals[2]))
            self.tri(a, c, d, out, (normals[0], normals[2], normals[3]))
        else:
            self.tri(a, b, c, out)
            self.tri(a, c, d, out)

    def poly(self, pts, out):
        for t in ear_clip(pts, out):
            self.tri(*t, out)

    def write(self):
        path = os.path.join(OUT, self.name + ".obj")
        with open(path, "w", encoding="ascii") as fh:
            fh.write(f"o {self.name}\n")
            for p in self.v:
                fh.write(f"v {p[0]:.4f} {-p[1]:.4f} {p[2]:.4f}\n")
            for t in self.vt:
                fh.write(f"vt {t[0]:.4f} {t[1]:.4f}\n")
            for n in self.vn:
                fh.write(f"vn {n[0]:.4f} {-n[1]:.4f} {n[2]:.4f}\n")
            for face in self.f:
                fh.write("f " + " ".join(f"{a}/{b}/{c}" for a, b, c in face) + "\n")
        print(f"{self.name}: {len(self.f)} tris")


def ear_clip(pts3, out):
    """Triangulate a planar simple polygon given in 3D (projected on the plane normal to `out`)."""
    ax = max(range(3), key=lambda i: abs(out[i]))
    a, b = [(1, 2), (0, 2), (0, 1)][ax]
    p2 = [(p[a], p[b]) for p in pts3]
    area = sum(p2[i][0] * p2[(i + 1) % len(p2)][1] - p2[(i + 1) % len(p2)][0] * p2[i][1] for i in range(len(p2)))
    idx = list(range(len(p2)))
    if area < 0:
        idx.reverse()
    tris = []

    def is_convex(i0, i1, i2):
        (x0, y0), (x1, y1), (x2, y2) = p2[i0], p2[i1], p2[i2]
        return (x1 - x0) * (y2 - y0) - (y1 - y0) * (x2 - x0) > 1e-9

    def inside(pt, i0, i1, i2):
        (x, y) = pt
        (x0, y0), (x1, y1), (x2, y2) = p2[i0], p2[i1], p2[i2]
        d1 = (x - x1) * (y0 - y1) - (x0 - x1) * (y - y1)
        d2 = (x - x2) * (y1 - y2) - (x1 - x2) * (y - y2)
        d3 = (x - x0) * (y2 - y0) - (x2 - x0) * (y - y0)
        neg = d1 < 0 or d2 < 0 or d3 < 0
        pos = d1 > 0 or d2 > 0 or d3 > 0
        return not (neg and pos)

    guard = 0
    while len(idx) > 3 and guard < 10000:
        guard += 1
        n = len(idx)
        for k in range(n):
            i0, i1, i2 = idx[k - 1], idx[k], idx[(k + 1) % n]
            if not is_convex(i0, i1, i2):
                continue
            if any(inside(p2[j], i0, i1, i2) for j in idx if j not in (i0, i1, i2)):
                continue
            tris.append((pts3[i0], pts3[i1], pts3[i2]))
            idx.pop(k)
            break
        else:
            break
    if len(idx) == 3:
        tris.append(tuple(pts3[i] for i in idx))
    return tris


# ---------------------------------------------------------------- generators

def profile_extrude(name, prof, length=100.0, caps=True):
    """prof: closed polygon of (y, z). Extruded along X from -length/2 to +length/2."""
    m = Mesh(name)
    n = len(prof)
    area = sum(prof[i][0] * prof[(i + 1) % n][1] - prof[(i + 1) % n][0] * prof[i][1] for i in range(n))
    sgn = 1.0 if area > 0 else -1.0
    x0, x1 = -length / 2, length / 2
    for i in range(n):
        (y0, z0), (y1, z1) = prof[i], prof[(i + 1) % n]
        dy, dz = y1 - y0, z1 - z0
        out = (0.0, sgn * dz, -sgn * dy)
        m.quad((x0, y0, z0), (x1, y0, z0), (x1, y1, z1), (x0, y1, z1), out)
    if caps:
        m.poly([(x0, y, z) for y, z in prof], (-1.0, 0.0, 0.0))
        m.poly([(x1, y, z) for y, z in prof], (1.0, 0.0, 0.0))
    return m


def ring_extrude(name, w, h, prof, mapping, fill=True, mesh=None):
    """Picture-frame style extrusion of profile [(inset d, height c)] around a w x h rectangle.

    mapping(a, b, c) -> UE point; a in [-w/2, w/2], b in [-h/2, h/2], c = height toward the viewer.
    The outward normal of the plane is mapping's +c direction (computed numerically).
    """
    m = mesh or Mesh(name)
    origin = mapping(0, 0, 0)
    cdir = sub(mapping(0, 0, 1), origin)
    adir = sub(mapping(1, 0, 0), origin)
    bdir = sub(mapping(0, 1, 0), origin)

    def vec(da, db, dc):
        return tuple(adir[i] * da + bdir[i] * db + cdir[i] * dc for i in range(3))

    loops = []
    for d, c in prof:
        hw, hh = w / 2 - d, h / 2 - d
        loops.append([mapping(hw, hh, c), mapping(-hw, hh, c), mapping(-hw, -hh, c), mapping(hw, -hh, c)])
    # side outward directions in (a, b): +b (top edge between corners 0-1), -a, -b, +a
    side_dirs = [(0, 1), (-1, 0), (0, -1), (1, 0)]
    for k in range(len(prof) - 1):
        dd = prof[k + 1][0] - prof[k][0]
        dc = prof[k + 1][1] - prof[k][1]
        for s in range(4):
            sa, sb = side_dirs[s]
            out = vec(sa * dc, sb * dc, dd)
            if dot(out, out) < 1e-12:
                continue
            p0, p1 = loops[k][s], loops[k][(s + 1) % 4]
            q0, q1 = loops[k + 1][s], loops[k + 1][(s + 1) % 4]
            m.quad(p0, p1, q1, q0, out)
    if fill:
        last = loops[-1]
        m.quad(last[0], last[1], last[2], last[3], cdir)
    return m


def lathe(name, prof, seg=24, mesh=None, offset=(0.0, 0.0, 0.0), cap_flat=True):
    """prof: list of (r, z) from bottom to top. Smooth around the axis, crisp along the profile."""
    m = mesh or Mesh(name)
    ox, oy, oz = offset
    for i in range(len(prof) - 1):
        (r0, z0), (r1, z1) = prof[i], prof[i + 1]
        dr, dz = r1 - r0, z1 - z0
        if abs(dr) < 1e-9 and abs(dz) < 1e-9:
            continue
        nr, nz = dz, -dr
        l = math.hypot(nr, nz)
        nr, nz = nr / l, nz / l
        for s in range(seg):
            a0 = 2 * math.pi * s / seg
            a1 = 2 * math.pi * (s + 1) / seg
            c0, s0, c1, s1 = math.cos(a0), math.sin(a0), math.cos(a1), math.sin(a1)
            P = lambda r, z, c, s_: (ox + r * c, oy + r * s_, oz + z)
            n0 = (nr * c0, nr * s0, nz)
            n1 = (nr * c1, nr * s1, nz)
            am = (a0 + a1) / 2
            out = (nr * math.cos(am), nr * math.sin(am), nz)
            pa, pb, pc, pd = P(r0, z0, c0, s0), P(r0, z0, c1, s1), P(r1, z1, c1, s1), P(r1, z1, c0, s0)
            if r0 < 1e-6:
                m.tri(pa, pc, pd, out, (out, n1, n0))
            elif r1 < 1e-6:
                m.tri(pa, pb, pc, out, (n0, n1, out))
            else:
                m.quad(pa, pb, pc, pd, out, (n0, n1, n1, n0))
    return m


def box(m, x0, x1, y0, y1, z0, z1):
    c = [(x0, y0, z0), (x1, y0, z0), (x1, y1, z0), (x0, y1, z0), (x0, y0, z1), (x1, y0, z1), (x1, y1, z1), (x0, y1, z1)]
    m.quad(c[0], c[1], c[2], c[3], (0, 0, -1))
    m.quad(c[4], c[5], c[6], c[7], (0, 0, 1))
    m.quad(c[0], c[1], c[5], c[4], (0, -1, 0))
    m.quad(c[3], c[2], c[6], c[7], (0, 1, 0))
    m.quad(c[0], c[3], c[7], c[4], (-1, 0, 0))
    m.quad(c[1], c[2], c[6], c[5], (1, 0, 0))


# ---------------------------------------------------------------- the pieces

def wall_xz(a, b, c):           # wall-mounted, face +Y: a -> X, b -> Z, c -> Y
    return (a, c, b)


def build_all():
    # linear profiles (y = depth from wall, z = height)
    profile_extrude("SM_GW_Baseboard", [(0, 0), (2.2, 0), (2.2, 15), (1.6, 16), (1.6, 17.5), (2.6, 19),
                                        (2.2, 20.6), (1.0, 21.5), (0, 22)]).write()
    profile_extrude("SM_GW_ChairRail", [(0, 0), (1.5, 0), (2.6, 1.4), (3.6, 3.0), (3.6, 4.4), (2.6, 6.0),
                                        (1.2, 6.6), (0, 7)]).write()
    cove = [(19.5 - 16 * math.cos(math.radians(a)), -20.5 + 16 * math.sin(math.radians(a))) for a in range(0, 91, 10)]
    profile_extrude("SM_GW_Crown", [(0, -22), (2, -22), (2, -20.5), (3.5, -20.5)] + cove[1:] +
                    [(19.5, -3), (22, -3), (22, -1.5), (24, -1.5), (24, 0), (0, 0)]).write()
    profile_extrude("SM_GW_Architrave", [(0, 0), (1.5, 0), (1.5, 1), (2.8, 2), (2.8, 4), (2.0, 5), (2.0, 9),
                                         (2.5, 10), (2.5, 14), (1.8, 16), (0, 16)]).write()
    # small bolection moulding for applied wall-panel frames (4 cm wide, 2.6 cm proud), bottom at z=0
    profile_extrude("SM_GW_PanelMould", [(0, 0), (1.0, 0), (1.8, 0.6), (2.6, 1.6), (2.6, 2.4), (1.8, 3.4),
                                         (1.0, 4.0), (0, 4.0)]).write()
    profile_extrude("SM_GW_Cornice", [(0, 0), (4, 0), (4, 4), (7, 6), (9, 10), (10, 14), (14, 16), (14, 19),
                                      (17, 21), (17, 24), (24, 26), (30, 27), (30, 30), (0, 30)]).write()
    # handrail: centred on y=0, bottom at z=0
    hr = [(-3.0, 0), (3.0, 0), (3.0, 1.5), (4.2, 3.0)]
    hr += [(4.2 * math.cos(math.radians(a)), 3.0 + 4.2 * math.sin(math.radians(a))) for a in range(15, 166, 15)]
    hr += [(-4.2, 3.0), (-3.0, 1.5)]
    profile_extrude("SM_GW_Handrail", hr).write()

    # raised wainscot panel 100 x 100 (X by Z), face +Y, bottom at z=0
    ring_extrude("SM_GW_RaisedPanel", 100, 100,
                 [(0, 0), (0.6, 1.4), (2, 1.7), (3, 0.6), (6, 0.6), (14, 2.4), (15, 2.6)],
                 lambda a, b, c: (a, c, b + 50)).write()
    # coffer ring 100 x 100 in XY, hanging down from z=0 (c -> -Z)
    ring_extrude("SM_GW_CofferRing", 100, 100,
                 [(0, 0), (0, 14), (2, 14), (2, 12), (3.5, 11), (5, 10), (8, 6), (10, 4.5), (11, 4.5), (11, 2.5),
                  (13, 1), (13, 0)],
                 lambda a, b, c: (a, b, -c), fill=False).write()

    # picture frames: canvas opening 75 x 100 (portrait) / 100 x 75 (landscape), face +Y, centred
    gilt = [(0, 0), (0, 4.5), (1, 5.6), (2.5, 6.0), (3.6, 5.2), (4.6, 4.0), (5.6, 4.4), (6.6, 4.2),
            (7.6, 3.0), (8.6, 2.7), (9.3, 1.6), (10, 1.3), (10.5, 0.8)]
    plain = [(0, 0), (0, 3.5), (0.8, 4.2), (3.5, 4.2), (4.5, 3.4), (6, 3.0), (7, 1.6), (7.5, 0.8)]
    for tag, (cw, ch) in (("P", (75, 100)), ("L", (100, 75))):
        ring_extrude(f"SM_GW_Frame_{tag}", cw + 21, ch + 21, gilt, lambda a, b, c: (a, c, b), fill=False).write()
        ring_extrude(f"SM_GW_Frame2_{tag}", cw + 15, ch + 15, plain, lambda a, b, c: (a, c, b), fill=False).write()

    # door casings (3 visible sides: the bottom run is buried under the floor), face +Y, opening bottom at z=0
    cas = [(0, 0), (0, 1.5), (1, 2.6), (2.5, 2.8), (4, 2.0), (8, 2.0), (9, 2.5), (13, 2.5), (14, 1.6), (16, 1.6), (16, 0)]
    for w, hgt in ((180, 270), (220, 270), (320, 270), (400, 270), (200, 250)):
        ow, oh = w + 32, hgt + 16 + 40
        ring_extrude(f"SM_GW_DoorCasing_{w}", ow, oh, cas,
                     lambda a, b, c, oh=oh: (a, c, b + oh / 2 - 40), fill=False).write()
    # window casing for the standard window opening 150 x 260 and the tall hall window 180 x 420
    for w, hgt in ((150, 260), (180, 420)):
        ring_extrude(f"SM_GW_WindowCasing_{w}", w + 32, hgt + 32, cas,
                     lambda a, b, c, hgt=hgt: (a, c, b + hgt / 2), fill=False).write()

    # turned baluster 80 cm
    lathe("SM_GW_Baluster", [(0, 0), (4.5, 0), (4.5, 4), (3.6, 5), (3.6, 7), (2.3, 9), (2.3, 12), (3.8, 20),
                             (4.3, 28), (3.6, 36), (2.1, 42), (1.8, 48), (2.7, 52), (2.7, 55), (1.8, 58),
                             (2.1, 66), (3.1, 70), (3.1, 72), (4.5, 73), (4.5, 80), (0, 80)], seg=16).write()
    lathe("SM_GW_Finial", [(0, 0), (7, 0), (7, 2), (5, 3), (3, 5), (3, 7), (6, 10), (7, 14), (6, 18), (3, 21),
                           (1.5, 23), (0, 24)], seg=20).write()
    # column parts (shaft diameter 50)
    lathe("SM_GW_ColumnBase", [(0, 0), (32, 0), (32, 4), (30, 6), (31.5, 9), (30, 12), (28, 13), (27, 15),
                               (26, 16), (25.5, 18), (0, 18)], seg=32).write()
    lathe("SM_GW_ColumnCapital", [(0, 0), (25.5, 0), (26.5, 1.5), (26.5, 3.5), (25.5, 4.5), (25.5, 6), (28, 8),
                                  (31, 11), (34, 15), (35, 17), (35, 19), (0, 19)], seg=32).write()
    # fluted shaft r=25, h=100, 20 flutes
    m = Mesh("SM_GW_ColumnShaft")
    N, R, D = 120, 25.0, 1.6
    ring = []
    for i in range(N):
        a = 2 * math.pi * i / N
        f = max(0.0, math.cos(20 * a))
        r = R - D * (f ** 0.6)
        ring.append((r * math.cos(a), r * math.sin(a)))
    for i in range(N):
        (x0, y0), (x1, y1) = ring[i], ring[(i + 1) % N]
        # smooth normals from neighbours
        def vn(k):
            (xa, ya), (xb, yb) = ring[(k - 1) % N], ring[(k + 1) % N]
            return (yb - ya, -(xb - xa), 0.0)
        n0, n1 = vn(i), vn(i + 1)
        if dot(n0, (x0, y0, 0)) < 0:
            n0 = (-n0[0], -n0[1], 0)
        if dot(n1, (x1, y1, 0)) < 0:
            n1 = (-n1[0], -n1[1], 0)
        out = ((x0 + x1) / 2, (y0 + y1) / 2, 0)
        m.quad((x0, y0, 0), (x1, y1, 0), (x1, y1, 100), (x0, y0, 100), out, (n0, n1, n1, n0))
        m.tri((0, 0, 100), (x0, y0, 100), (x1, y1, 100), (0, 0, 1))
        m.tri((0, 0, 0), (x0, y0, 0), (x1, y1, 0), (0, 0, -1))
    m.write()

    # torus (R=50, r=2.5) for chandelier rings
    circ = [(50 + 2.5 * math.cos(math.radians(a)), 2.5 * math.sin(math.radians(a))) for a in range(-90, 271, 30)]
    lathe("SM_GW_Torus", circ, seg=40).write()
    # chandelier body (vase + stem), 100 tall, base at z=0 (bottom finial)
    lathe("SM_GW_ChandelierBody", [(0, 0), (2, 0), (3, 4), (5, 8), (10, 14), (16, 20), (18, 24), (16, 28),
                                   (8, 32), (4, 36), (3, 40), (3.5, 46), (5, 50), (3, 54), (2, 58), (2, 94),
                                   (5, 96), (5, 100), (0, 100)], seg=24).write()
    # candle sleeve + flame bulb
    lathe("SM_GW_CandleCup", [(0, 0), (1.2, 0), (3.5, 2.5), (4.2, 3.2), (3.0, 3.6), (1.6, 3.6), (1.6, 12),
                              (0, 12)], seg=16).write()
    lathe("SM_GW_Flame", [(0, 0), (1.3, 0.6), (1.9, 2.0), (1.8, 3.6), (1.2, 5.0), (0.5, 6.2), (0, 6.8)], seg=12).write()
    # tulip lamp shade (open top)
    lathe("SM_GW_Tulip", [(0, 0), (2, 0.2), (5, 2), (7, 6), (7.5, 10), (7.8, 14), (7.2, 14), (6.9, 10), (6.4, 6),
                          (4.5, 2.6), (0, 0.8)], seg=24).write()
    lathe("SM_GW_Backplate", [(0, 0), (8, 0), (8, 1), (7, 2), (4, 3), (2, 4.5), (0, 4.5)], seg=24).write()
    # crystal drop (octahedron-ish, 6 x 6 x 10)
    lathe("SM_GW_Drop", [(0, 0), (2.5, 4), (3, 6), (0, 10)], seg=6).write()
    # sphere-ish knob
    lathe("SM_GW_Ball", [(math.sin(math.radians(a)) * 50, 50 - math.cos(math.radians(a)) * 50) for a in range(0, 181, 15)],
          seg=24).write()

    # curtain: 100 wide (X -50..50), 100 tall hanging from z=0 down to z=-100, folds in Y, 1.2 thick
    m = Mesh("SM_GW_Curtain")
    NX, NZ = 64, 10
    def surf(u, t, side):
        amp = 3.5 + 3.0 * t
        x = -50 + 100 * u
        y = amp * math.sin(2 * math.pi * u * 4.0) + side * 0.6 + 6.5
        return (x, y, -100 * t)
    def snorm(u, t, side):
        amp = 3.5 + 3.0 * t
        dydx = amp * 2 * math.pi * 4.0 / 100 * math.cos(2 * math.pi * u * 4.0)
        return (-dydx * side, side * 1.0, 0.0)
    for side in (1, -1):
        for i in range(NX):
            for k in range(NZ):
                u0, u1, t0, t1 = i / NX, (i + 1) / NX, k / NZ, (k + 1) / NZ
                pts = [surf(u0, t0, side), surf(u1, t0, side), surf(u1, t1, side), surf(u0, t1, side)]
                nn = [snorm(u0, t0, side), snorm(u1, t0, side), snorm(u1, t1, side), snorm(u0, t1, side)]
                out = snorm((u0 + u1) / 2, (t0 + t1) / 2, side)
                m.quad(*pts, out, nn)
    for i in range(NX):          # top / bottom edges
        u0, u1 = i / NX, (i + 1) / NX
        for t, o in ((0.0, (0, 0, 1)), (1.0, (0, 0, -1))):
            m.quad(surf(u0, t, 1), surf(u1, t, 1), surf(u1, t, -1), surf(u0, t, -1), o)
    m.write()

    # bevelled box, centred, -50..50 (bevel on top and bottom edges)
    m = Mesh("SM_GW_BevelBox")
    ring_extrude(None, 100, 100, [(3, 0), (0, 3), (0, 97), (3, 100)], lambda a, b, c: (a, b, c - 50), fill=True, mesh=m)
    m.quad((-47, 47, -50), (47, 47, -50), (47, -47, -50), (-47, -47, -50), (0, 0, -1))
    m.write()


if __name__ == "__main__":
    build_all()
