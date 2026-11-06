"""Width (X) and depth (Z) of a GLB mesh per height slice: profile.py FILE.glb [slices]"""
import sys

import numpy as np

sys.path.insert(0, __import__("os").path.dirname(__import__("os").path.abspath(__file__)))
import glb_mesh  # noqa: E402

gltf, views = glb_mesh.load(sys.argv[1])
prim, pos, idx, uv = glb_mesh.mesh(gltf, views)
n = int(sys.argv[2]) if len(sys.argv) > 2 else 20
lo, hi = pos[:, 1].min(), pos[:, 1].max()
for i in range(n):
    a, b = lo + (hi - lo) * i / n, lo + (hi - lo) * (i + 1) / n
    m = (pos[:, 1] >= a) & (pos[:, 1] < b)
    if m.any():
        p = pos[m]
        print(f"fy {i/n:.2f}-{(i+1)/n:.2f}  width {np.ptp(p[:,0]):.3f}  depth {np.ptp(p[:,2]):.3f}  x[{p[:,0].min():+.3f},{p[:,0].max():+.3f}]")
