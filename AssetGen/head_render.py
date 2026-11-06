"""Per-pixel render of a character's head from its GLB texture (char_closeup.py colours each triangle, too coarse to judge
a mask painted by project_front_tex.py).

  V:/ComfyUI/ComfyUI/ComfyUI/.venv/Scripts/python.exe -I head_render.py OUT.png NAME.glb [NAME.glb ...] [--top 0.22] [--size 420]
One orthographic front view per GLB, side by side: the top --top of the figure, z-buffered, texture sampled per pixel.
"""
import argparse
import os
import sys

import numpy as np
from PIL import Image

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import glb_mesh  # noqa: E402

p = argparse.ArgumentParser()
p.add_argument("out")
p.add_argument("glbs", nargs="+")
p.add_argument("--top", type=float, default=0.22)
p.add_argument("--size", type=int, default=420)
a = p.parse_args()


def head(path):
    g, v = glb_mesh.load(path)
    _, pos, idx, uv = glb_mesh.mesh(g, v)
    tex = glb_mesh.base_color(g, v)
    TH, TW, _ = tex.shape
    y0 = pos[:, 1].max() - a.top * (pos[:, 1].max() - pos[:, 1].min())
    tri = idx[(pos[idx][:, :, 1].max(1) > y0)]
    keep = pos[tri.ravel(), 0]
    xc, span = (keep.min() + keep.max()) / 2, pos[:, 1].max() - y0
    k = a.size / span
    S = a.size
    px = (pos[:, 0] - xc) * k + S / 2
    py = (pos[:, 1].max() - pos[:, 1]) * k
    im, zb = np.full((S, S, 3), 0.54), np.full((S, S), -1e9)
    for t in tri:
        A, B, C = t
        xs, ys = px[[A, B, C]], py[[A, B, C]]
        x0, x1 = max(int(xs.min()), 0), min(int(xs.max()) + 1, S - 1)
        y0_, y1 = max(int(ys.min()), 0), min(int(ys.max()) + 1, S - 1)
        if x1 < x0 or y1 < y0_:
            continue
        den = (ys[1] - ys[2]) * (xs[0] - xs[2]) + (xs[2] - xs[1]) * (ys[0] - ys[2])
        if abs(den) < 1e-9:
            continue
        gx, gy = np.meshgrid(np.arange(x0, x1 + 1), np.arange(y0_, y1 + 1))
        w0 = ((ys[1] - ys[2]) * (gx - xs[2]) + (xs[2] - xs[1]) * (gy - ys[2])) / den
        w1 = ((ys[2] - ys[0]) * (gx - xs[2]) + (xs[0] - xs[2]) * (gy - ys[2])) / den
        w2 = 1 - w0 - w1
        ok = (w0 >= 0) & (w1 >= 0) & (w2 >= 0)
        if not ok.any():
            continue
        gx, gy, w0, w1, w2 = gx[ok], gy[ok], w0[ok], w1[ok], w2[ok]
        z = w0 * pos[A, 2] + w1 * pos[B, 2] + w2 * pos[C, 2]
        front = z > zb[gy, gx]
        gx, gy, w0, w1, w2, z = gx[front], gy[front], w0[front], w1[front], w2[front], z[front]
        u = w0 * uv[A, 0] + w1 * uv[B, 0] + w2 * uv[C, 0]
        v_ = w0 * uv[A, 1] + w1 * uv[B, 1] + w2 * uv[C, 1]
        zb[gy, gx] = z
        im[gy, gx] = tex[np.clip((v_ * TH).astype(int), 0, TH - 1), np.clip((u * TW).astype(int), 0, TW - 1)]
    return Image.fromarray((im * 255).astype(np.uint8))


ims = [head(x) for x in a.glbs]
sheet = Image.new("RGB", (a.size * len(ims), a.size))
for i, im in enumerate(ims):
    sheet.paste(im, (i * a.size, 0))
sheet.save(a.out)
print("wrote", a.out)
