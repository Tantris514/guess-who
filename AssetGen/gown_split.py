"""Split a TRELLIS gown into a skirt (waist to floor) and a matching bodice (waist to shoulders).

  V:/ComfyUI/ComfyUI/ComfyUI/.venv/Scripts/python.exe -I gown_split.py COLOUR [COLOUR...]
Reads models3d/gown_<c>_trellis_s42/gown_<c>.glb, finds the waist (narrowest X slice between 60% and 85% of
the height), writes models3d/skirt_<c>/skirt_<c>.glb and models3d/bodice_<c>/bodice_<c>.glb with a software
QA render (qa_render.png) and a result.json carrying the waist height, for approve_model.py.
"""
import json
import os
import shutil
import subprocess
import sys

import numpy as np

ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ROOT)
import glb_mesh  # noqa: E402

PY = sys.executable


def waist(path):
    gltf, views = glb_mesh.load(path)
    _, pos, _, _ = glb_mesh.mesh(gltf, views)
    lo, hi = pos[:, 1].min(), pos[:, 1].max()
    best = None
    for f in np.arange(0.60, 0.86, 0.01):
        a, b = lo + (hi - lo) * f, lo + (hi - lo) * (f + 0.02)
        m = (pos[:, 1] >= a) & (pos[:, 1] < b)
        if m.sum() > 10:
            wdt = np.ptp(pos[m, 0])
            if best is None or wdt < best[1]:
                best = (f + 0.01, wdt)
    return round(float(best[0]), 3)


for c in sys.argv[1:]:
    src_dir = os.path.join(ROOT, "models3d", f"gown_{c}_trellis_s42")
    src = os.path.join(src_dir, f"gown_{c}.glb")
    fy = waist(src)
    res = json.load(open(os.path.join(src_dir, "result.json"), encoding="utf-8"))
    for part, expr in (("skirt", f"fy > {fy}"), ("bodice", f"fy < {fy}")):
        out_dir = os.path.join(ROOT, "models3d", f"{part}_{c}")
        os.makedirs(out_dir, exist_ok=True)
        dst = os.path.join(out_dir, f"{part}_{c}.glb")
        subprocess.run([PY, "-I", os.path.join(ROOT, "glb_mesh.py"), "cut", src, dst, "--drop", expr, "--keep-largest", "1"], check=True)
        subprocess.run([PY, "-I", os.path.join(ROOT, "glb_mesh.py"), "render", dst, os.path.join(out_dir, "qa_render.png"), "--size", "300"], check=True)
        r = dict(res, source_gown=src, waist_fy=fy, part=part)
        json.dump(r, open(os.path.join(out_dir, "result.json"), "w", encoding="utf-8"), indent=1)
    print(c, "waist at", fy)
