"""Vertex-level check of the dance clips on the skinned Manny (ComfyUI venv python -I): how deep hand / forearm vertices
go inside the torso and thighs (nearest surface vertex within 4 cm + its normal: negative = inside), and the forearm twist the
hands ask for (large twists candy-wrap the wrist). Every 3rd frame. Prints a table; exit 1 if anything is > 2.5 cm
inside or twists > 100 deg.
"""
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from dance_core import Skeleton, Solver, swing_twist_x, qmul, qconj  # noqa: E402
from dances import ALL  # noqa: E402
from dance_qa import load_mesh, globals_from, skin  # noqa: E402


def vertex_normals(p, tris):
    n = np.zeros_like(p)
    fn = np.cross(p[tris[:, 1]] - p[tris[:, 0]], p[tris[:, 2]] - p[tris[:, 0]])
    for k in range(3):
        np.add.at(n, tris[:, k], fn)
    return n / (np.linalg.norm(n, axis=1, keepdims=True) + 1e-9)


def group(mesh, prefixes, thresh=0.5):
    idx = [i for i, nm in enumerate(mesh['names']) if nm.startswith(prefixes)]
    return np.where(mesh['W'][:, idx].sum(1) > thresh)[0]


def depth(p, nrm, probe, surf):
    """Signed distance of each probe vertex to the nearest surface vertex along its normal (cm, negative = inside)."""
    out = np.empty(len(probe))
    S = p[surf]
    for a in range(0, len(probe), 512):
        q = p[probe[a:a + 512]]
        d2 = ((q[:, None, :] - S[None, :, :]) ** 2).sum(-1)
        j = d2.argmin(1)
        sd = ((q - S[j]) * nrm[surf][j]).sum(1)
        near = np.sqrt(d2[np.arange(len(j)), j]) < 4.0           # only near-contact probes can be inside
        out[a:a + 512] = np.where(near, np.minimum(sd, 0.0), 0.0)
    return out


def main():
    sk = Skeleton()
    mesh = load_mesh('manny')
    torso = group(mesh, ('spine_', 'pelvis', 'clavicle', 'neck', 'head'), 0.6)
    thighs = group(mesh, ('thigh_',), 0.6)
    probes = {s: group(mesh, (f'hand_{s}', f'lowerarm_{s}', f'lowerarm_twist', 'index_', 'middle_', 'ring_', 'pinky_', 'thumb_'), 0.6) for s in 'lr'}
    side = lambda v, s: v[(mesh['v'][v, 0] > 0) == (s == 'l')]          # this side's vertices only
    probes = {s: side(v, s) for s, v in probes.items()}
    bad = False
    print(f'{"clip":12s} {"hand/forearm in torso":>22s} {"in thighs":>10s} {"max wrist twist":>16s}')
    for d in ALL:
        S = Solver(sk)
        n = int(round(d.length * 30))
        worst_t, worst_th, tw = 0.0, 0.0, 0.0
        for k in range(0, n, 6):
            lq, lt = S.solve(d.pose(k / 30))
            for s in 'lr':
                hi = sk.i(f'hand_{s}')
                tw = max(tw, abs(swing_twist_x(qmul(qconj(S.base_lq[hi]), lq[hi]))))
            p = skin(mesh, globals_from(mesh, dict(zip(sk.names, lq)), dict(zip(sk.names, lt))))
            nrm = vertex_normals(p, mesh['tris'])
            for s in 'lr':
                worst_t = min(worst_t, float(depth(p, nrm, probes[s], torso).min()))
                worst_th = min(worst_th, float(depth(p, nrm, probes[s], thighs).min()))
        flag = worst_t < -2.5 or worst_th < -2.5 or tw > 100
        bad |= flag
        print(f'{d.name:12s} {worst_t:22.1f} {worst_th:10.1f} {tw:16.0f}{"   <-- CHECK" if flag else ""}')
    return 1 if bad else 0


if __name__ == '__main__':
    sys.exit(main())
