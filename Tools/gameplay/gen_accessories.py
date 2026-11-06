"""Procedural placeholder accessories (OBJ, centimetres, Unreal axes: X right, Y forward, Z up).

Hats/mask: origin = attachment point (hat: centre of the brim underside; mask: head centre at eye level).
Revolver: modelled directly in the mannequin's weapon_r bone frame (barrel +Z, top +X).
Usage: python gen_accessories.py <outdir>
"""
import math
import os
import sys

out = sys.argv[1]
os.makedirs(out, exist_ok=True)


class Mesh:
    def __init__(self):
        self.v, self.n, self.f = [], [], []

    def quad(self, a, b, c, d):
        # a,b,c,d counter-clockwise seen from outside
        nx, ny, nz = _normal(a, b, c)
        base = len(self.v)
        self.v += [a, b, c, d]
        self.n += [(nx, ny, nz)] * 4
        self.f.append((base, base + 1, base + 2))
        self.f.append((base, base + 2, base + 3))

    def tri(self, a, b, c):
        nx, ny, nz = _normal(a, b, c)
        base = len(self.v)
        self.v += [a, b, c]
        self.n += [(nx, ny, nz)] * 3
        self.f.append((base, base + 1, base + 2))

    def save(self, path):
        # Interchange's OBJ import maps OBJ (x, y, z) -> UE (x, -y, z): write y negated and reverse the
        # winding so the geometric normal stays outward after the mirror.
        with open(path, 'w') as fh:
            for x, y, z in self.v:
                fh.write(f'v {x:.4f} {-y:.4f} {z:.4f}\n')
            for x, y, z in self.n:
                fh.write(f'vn {x:.4f} {-y:.4f} {z:.4f}\n')
            for a, b, c in self.f:
                fh.write(f'f {a+1}//{a+1} {c+1}//{c+1} {b+1}//{b+1}\n')


def _normal(a, b, c):
    ux, uy, uz = b[0] - a[0], b[1] - a[1], b[2] - a[2]
    vx, vy, vz = c[0] - a[0], c[1] - a[1], c[2] - a[2]
    nx, ny, nz = uy * vz - uz * vy, uz * vx - ux * vz, ux * vy - uy * vx
    ln = math.sqrt(nx * nx + ny * ny + nz * nz) or 1
    return nx / ln, ny / ln, nz / ln


def frustum(m, r0, r1, z0, z1, seg=40, cap_top=True, cap_bottom=True, cx=0.0, cy=0.0):
    for i in range(seg):
        a0, a1 = 2 * math.pi * i / seg, 2 * math.pi * (i + 1) / seg
        p = lambda r, a, z: (cx + r * math.cos(a), cy + r * math.sin(a), z)
        m.quad(p(r0, a0, z0), p(r0, a1, z0), p(r1, a1, z1), p(r1, a0, z1))
        if cap_top:
            m.tri((cx, cy, z1), p(r1, a0, z1), p(r1, a1, z1))
        if cap_bottom:
            m.tri((cx, cy, z0), p(r0, a1, z0), p(r0, a0, z0))


def box(m, x0, x1, y0, y1, z0, z1, shear_xz=0.0):
    def P(x, y, z):
        return (x, y, z + shear_xz * x)
    c = [P(x0, y0, z0), P(x1, y0, z0), P(x1, y1, z0), P(x0, y1, z0), P(x0, y0, z1), P(x1, y0, z1), P(x1, y1, z1), P(x0, y1, z1)]
    m.quad(c[0], c[3], c[2], c[1])  # bottom
    m.quad(c[4], c[5], c[6], c[7])  # top
    m.quad(c[0], c[1], c[5], c[4])
    m.quad(c[1], c[2], c[6], c[5])
    m.quad(c[2], c[3], c[7], c[6])
    m.quad(c[3], c[0], c[4], c[7])


def zcyl(m, r, x, y, z0, z1, seg=20):
    """Cylinder along the Z axis centred at (x, y)."""
    frustum(m, r, r, z0, z1, seg, cx=x, cy=y)


# --- top hat
m = Mesh()
frustum(m, 15.5, 15.5, 0.0, 0.8, 48)            # brim
frustum(m, 9.4, 9.9, 0.8, 17.5, 48)              # crown (slight flare)
frustum(m, 9.55, 9.6, 0.8, 3.4, 48, cap_top=False, cap_bottom=False)  # band
m.save(os.path.join(out, 'SM_GW_TopHat.obj'))

# --- fedora
m = Mesh()
frustum(m, 15.0, 14.2, 0.0, 0.9, 48)             # brim (slight slope)
frustum(m, 9.6, 8.2, 0.9, 11.0, 48)              # crown
frustum(m, 9.65, 9.4, 0.9, 3.2, 48, cap_top=False, cap_bottom=False)  # ribbon
m.save(os.path.join(out, 'SM_GW_Fedora.obj'))

# --- venetian/domino mask: curved band in front of the eyes (arc around the head centre)
m = Mesh()
R0, R1, H = 10.6, 11.3, 5.2
seg = 24
span = math.radians(160)
for i in range(seg):
    a0 = math.pi / 2 - span / 2 + span * i / seg
    a1 = math.pi / 2 - span / 2 + span * (i + 1) / seg
    # wing shape: taller at the sides
    h0 = H * (1.0 + 0.35 * abs(math.cos(a0)))
    h1 = H * (1.0 + 0.35 * abs(math.cos(a1)))
    P = lambda r, a, z: (r * math.cos(a), r * math.sin(a), z)
    m.quad(P(R1, a0, -h0 / 2), P(R1, a1, -h1 / 2), P(R1, a1, h1 / 2), P(R1, a0, h0 / 2))   # outside
    m.quad(P(R0, a1, -h1 / 2), P(R0, a0, -h0 / 2), P(R0, a0, h0 / 2), P(R0, a1, h1 / 2))   # inside
    m.quad(P(R0, a0, h0 / 2), P(R1, a0, h0 / 2), P(R1, a1, h1 / 2), P(R0, a1, h1 / 2))     # top
    m.quad(P(R0, a1, -h1 / 2), P(R1, a1, -h1 / 2), P(R1, a0, -h0 / 2), P(R0, a0, -h0 / 2)) # bottom
m.save(os.path.join(out, 'SM_GW_Mask.obj'))

# --- revolver in weapon_r bone frame: barrel along +Z, top along +X, grip down (-X)
m = Mesh()
zcyl(m, 0.85, 3.4, 0.0, 5.5, 19.0)               # barrel
zcyl(m, 2.1, 2.4, 0.0, 1.2, 5.6, 18)             # drum
box(m, 0.8, 4.6, -0.9, 0.9, -1.5, 6.2)           # frame
box(m, -8.5, 1.0, -1.25, 1.25, -3.6, 0.6, shear_xz=0.28)  # grip (raked back)
box(m, -1.6, 0.9, -0.35, 0.35, 0.8, 4.2)         # trigger guard
box(m, 4.2, 5.2, -0.3, 0.3, 17.6, 18.6)          # front sight
m.save(os.path.join(out, 'SM_GW_Revolver.obj'))
print('ok', os.listdir(out))
