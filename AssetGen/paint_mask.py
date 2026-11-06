"""Paint a masquerade mask onto a character's face texture by orthographic projection from the front image.

Masks generated as geometry come out as thick goggles. Instead, the 3D is made from the same character WITHOUT the
mask (an aligned image edit), and the mask is projected from the masked front image onto the face texture: it is
perfectly flush by construction.

  V:/ComfyUI/ComfyUI/ComfyUI/.venv/Scripts/python.exe -I paint_mask.py IN.glb OUT.glb MASKED.png UNMASKED.png FG_MASK.png HEIGHT_CM
        [--thresh 0.10] [--debug DEBUG.png]
MASKED / UNMASKED: aligned front images (template camera, 1024x1536, 0.1367 cm/px, centre 100 cm high).
FG_MASK: BiRefNet mask of the masked image (to register the mesh silhouette to the image).
The mask region = pixels in the head that differ between MASKED and UNMASKED. The mesh (scaled to HEIGHT_CM, feet at 0)
is registered to the image by a small shift/scale search on the head silhouette, then every visible front-facing head
texel inside the mask region takes the MASKED image colour (soft 3 px edge).
"""
import argparse
import io
import json
import os
import sys

import numpy as np
from PIL import Image, ImageDraw
from scipy import ndimage

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import glb_mesh  # noqa: E402

CM = 140.0 / 1024
p = argparse.ArgumentParser()
p.add_argument("src")
p.add_argument("dst")
p.add_argument("masked")
p.add_argument("unmasked")
p.add_argument("fg")
p.add_argument("height", type=float)
p.add_argument("--thresh", type=float, default=0.10)
p.add_argument("--debug", default="")
p.add_argument("--face-rows", default="", help="rows (image px) limiting the mask region, e.g. 200,300")
p.add_argument("--view", choices=["front", "back"], default="front", help="back: the image is a back view")
p.add_argument("--fy-range", default="", help="paint only triangles whose centroid height fraction is in [a,b] (default: head)")
p.add_argument("--min-nz", type=float, default=0.2, help="only paint triangles facing the camera at least this much")
p.add_argument("--no-diff", action="store_true", help="region = colour test (+ rows) only, not masked/unmasked difference")
p.add_argument("--cols", default="", help="columns (image px) limiting the region, e.g. 450,580")
p.add_argument("--colour", default="", help="optional colour test on the MASKED image (numpy expr over r,g,b,L,S,H)")
p.add_argument("--reg-colour", action="store_true",
               help="register by matching the mesh's own texture (luminance) to the UNMASKED image around the painted region, "
                    "instead of the head silhouette (wild hair, feathers: the silhouette does not locate the face)")
a = p.parse_args()

M = np.asarray(Image.open(a.masked).convert("RGB").resize((1024, 1536), Image.LANCZOS)).astype(np.float32) / 255
U = np.asarray(Image.open(a.unmasked).convert("RGB").resize((1024, 1536), Image.LANCZOS)).astype(np.float32) / 255
FG = np.asarray(Image.open(a.fg).convert("L").resize((1024, 1536), Image.BILINEAR)) > 127

# --- mask region: head pixels that changed between the two images (after aligning UNMASKED to MASKED on the head)
ys = np.where(FG.any(1))[0]
top = ys.min()
head_rows = slice(max(top - 10, 0), top + 260) if not a.fy_range else slice(0, 1536)
ga, gb = M[head_rows].mean(-1), U[head_rows].mean(-1)
Fq = np.fft.fft2(ga - ga.mean()) * np.conj(np.fft.fft2(gb - gb.mean()))
r = np.abs(np.fft.ifft2(Fq / np.maximum(np.abs(Fq), 1e-9)))
sy, sx = np.unravel_index(r.argmax(), r.shape)
sy = sy - r.shape[0] if sy > r.shape[0] // 2 else sy
sx = sx - r.shape[1] if sx > r.shape[1] // 2 else sx
U = np.roll(np.roll(U, sy, axis=0), sx, axis=1)
diff = np.abs(M - U).max(-1)
reg = np.zeros(diff.shape, bool)
reg[head_rows] = True if a.no_diff else diff[head_rows] > a.thresh
reg &= FG
if a.face_rows:
    r0, r1 = (int(x) for x in a.face_rows.split(","))
    lim = np.zeros_like(reg)
    lim[r0:r1] = True
    reg &= lim
if a.cols:
    c0, c1 = (int(x) for x in a.cols.split(","))
    limc = np.zeros_like(reg)
    limc[:, c0:c1] = True
    reg &= limc
if a.colour:
    import colorsys  # noqa: F401
    r_, g_, b_ = M[..., 0], M[..., 1], M[..., 2]
    mx, mn = M.max(-1), M.min(-1)
    L_ = (mx + mn) / 2
    S_ = np.where(mx - mn < 1e-6, 0, (mx - mn) / np.maximum(1 - np.abs(2 * L_ - 1), 1e-6))
    H_ = np.degrees(np.arctan2(np.sqrt(3) * (g_ - b_), 2 * r_ - g_ - b_)) % 360
    reg &= np.asarray(eval(a.colour, {"__builtins__": {}, "np": np}, {"r": r_, "g": g_, "b": b_, "L": L_, "S": S_, "H": H_}), bool)
reg = ndimage.binary_opening(reg, iterations=2)
reg = ndimage.binary_closing(reg, iterations=3)
lab, n = ndimage.label(reg)
if n == 0:
    raise SystemExit("no mask region found: the two images do not differ in the head")
sizes = ndimage.sum(reg, lab, range(1, n + 1))
keep = [i + 1 for i, s_ in enumerate(sizes) if s_ >= 0.15 * max(sizes)]
reg = np.isin(lab, keep)
reg = ndimage.binary_fill_holes(reg)
alpha = ndimage.gaussian_filter(reg.astype(np.float32), 1.5)
alpha = np.clip((alpha - 0.2) / 0.6, 0, 1)
ry, rx = np.where(reg)
info = {"unmasked_shift_px": [int(sx), int(sy)], "mask_region_px": int(reg.sum()), "mask_bbox_px": [int(rx.min()), int(ry.min()), int(rx.max()), int(ry.max())]}

# --- mesh in image coordinates
g, v = glb_mesh.load(a.src)
prim, pos, idx, uv = glb_mesh.mesh(g, v)
lo, hi = pos.min(0), pos.max(0)
s = a.height / (hi[1] - lo[1])
low_v = pos[:, 1] < lo[1] + 0.6 * (hi[1] - lo[1])
blo, bhi = pos[low_v].min(0), pos[low_v].max(0)
P = (pos - [(blo[0] + bhi[0]) / 2, lo[1], (blo[2] + bhi[2]) / 2]) * s
if a.view == "back":                         # look from behind: mirror x and depth
    P[:, 0] *= -1
    P[:, 2] *= -1
cen = P[idx].mean(1)
headT = np.where(cen[:, 1] > a.height * 0.80)[0]
if a.fy_range:
    f0, f1 = (float(x) for x in a.fy_range.split(","))
    paintT = np.where((cen[:, 1] >= f0 * a.height) & (cen[:, 1] <= f1 * a.height))[0]
    zT = np.arange(len(idx))
else:
    paintT, zT = headT, headT


def to_img(Pp, k, dx, dy):
    return 512 + Pp[:, 0] * k / CM + dx, 768 - (Pp[:, 1] * k - 100) / CM + dy


def sil(k, dx, dy):
    im = Image.new("L", (1024, 1536), 0)
    d = ImageDraw.Draw(im)
    x, y = to_img(P, k, dx, dy)
    for t in idx[regT]:
        d.polygon([(x[j], y[j]) for j in t], fill=255)
    return np.asarray(im) > 0


win = np.zeros_like(FG)
if a.fy_range:                              # body painting: register the whole figure below the neck
    regT = np.where(cen[:, 1] < 0.8 * a.height)[0][::3]
    win[int(768 - (0.8 * a.height - 100) / CM):] = True
else:
    regT = headT
    # head window around the painted region (the silhouette top may be a feather or a hat)
    win[max(int(ry.min()) - 70, 0): int(ry.max()) + 110] = True
best = None
if a.reg_colour:
    # painter's raster of the head triangles with their texture colour (nearest last), compared with the image's
    # luminance in a window around the painted region (normalised cross-correlation)
    tcol = glb_mesh.tri_colors(glb_mesh.base_color(g, v), uv, idx)
    tl = np.asarray(tcol, np.float32)[:, :3].mean(1)
    if tl.max() > 1.5:
        tl = tl / 255.0
    hz = headT[np.argsort(P[idx[headT]].mean(1)[:, 2] * (1 if a.view == "front" else -1))]
    wy0, wy1 = max(int(ry.min()) - 40, 0), int(ry.max()) + 60
    wx0, wx1 = max(int(rx.min()) - 40, 0), int(rx.max()) + 40
    ref = U[wy0:wy1, wx0:wx1].mean(-1)

    def ncc(k_, dx_, dy_):
        im = Image.new("L", (1024, 1536), 0)
        d = ImageDraw.Draw(im)
        x, y = to_img(P, k_, dx_, dy_)
        for t in hz:
            if x[idx[t]].max() < wx0 or x[idx[t]].min() > wx1 or y[idx[t]].max() < wy0 or y[idx[t]].min() > wy1:
                continue
            d.polygon([(x[j], y[j]) for j in idx[t]], fill=int(tl[t] * 254) + 1)
        r_ = np.asarray(im)[wy0:wy1, wx0:wx1].astype(np.float32)
        ok = r_ > 0
        if ok.sum() < 200:
            return -1.0
        a1, b1 = r_[ok] / 255.0, ref[ok]
        a1, b1 = a1 - a1.mean(), b1 - b1.mean()
        return float((a1 * b1).sum() / max(np.sqrt((a1 * a1).sum() * (b1 * b1).sum()), 1e-9))

    for k in (0.97, 0.985, 1.0, 1.015, 1.03):
        for dy in range(-30, 31, 5):
            for dx in range(-15, 16, 5):
                c_ = ncc(k, dx, dy)
                if best is None or c_ > best[0]:
                    best = (c_, k, dx, dy)
    _, k0, dx0, dy0 = best
    for dy in range(dy0 - 4, dy0 + 5, 2):
        for dx in range(dx0 - 4, dx0 + 5, 2):
            c_ = ncc(k0, dx, dy)
            if c_ > best[0]:
                best = (c_, k0, dx, dy)
    ncc_best, k, dx, dy = best
    info["registration"] = {"texture_ncc": round(ncc_best, 4), "scale": k, "dx": dx, "dy": dy}
else:
    for k in (0.98, 0.99, 1.0, 1.01, 1.02):
        for dy in range(-16, 17, 4):
            for dx in range(-12, 13, 4):
                m = sil(k, dx, dy)
                iou = (m & FG & win).sum() / max(((m | FG) & win).sum(), 1)
                if best is None or iou > best[0]:
                    best = (iou, k, dx, dy)
    _, k0, dx0, dy0 = best
    for dy in range(dy0 - 3, dy0 + 4):
        for dx in range(dx0 - 3, dx0 + 4):
            m = sil(k0, dx, dy)
            iou = (m & FG & win).sum() / max(((m | FG) & win).sum(), 1)
            if iou > best[0]:
                best = (iou, k0, dx, dy)
    iou, k, dx, dy = best
    info["registration"] = {"head_iou": round(float(iou), 4), "scale": k, "dx": dx, "dy": dy}

# --- z-buffer of the head (front view: larger z = nearer)
X, Y = to_img(P, k, dx, dy)
Z = P[:, 2]
zbuf = np.full((1536, 1024), -1e9, np.float32)
for t in idx[zT]:
    xs, ys_, zs = X[t], Y[t], Z[t]
    x0, x1 = int(max(np.floor(xs.min()), 0)), int(min(np.ceil(xs.max()), 1023))
    y0, y1 = int(max(np.floor(ys_.min()), 0)), int(min(np.ceil(ys_.max()), 1535))
    if x1 < x0 or y1 < y0:
        continue
    gx, gy = np.meshgrid(np.arange(x0, x1 + 1) + 0.5, np.arange(y0, y1 + 1) + 0.5)
    den = (ys_[1] - ys_[2]) * (xs[0] - xs[2]) + (xs[2] - xs[1]) * (ys_[0] - ys_[2])
    if abs(den) < 1e-9:
        continue
    l0 = ((ys_[1] - ys_[2]) * (gx - xs[2]) + (xs[2] - xs[1]) * (gy - ys_[2])) / den
    l1 = ((ys_[2] - ys_[0]) * (gx - xs[2]) + (xs[0] - xs[2]) * (gy - ys_[2])) / den
    l2 = 1 - l0 - l1
    inside = (l0 >= -1e-4) & (l1 >= -1e-4) & (l2 >= -1e-4)
    zz = l0 * zs[0] + l1 * zs[1] + l2 * zs[2]
    sub = zbuf[y0:y1 + 1, x0:x1 + 1]
    upd = inside & (zz > sub)
    sub[upd] = zz[upd]

# --- paint texels
ti = g["materials"][0]["pbrMetallicRoughness"]["baseColorTexture"]["index"]
bv = g["images"][g["textures"][ti]["source"]]["bufferView"]
im = Image.open(io.BytesIO(v[bv]))
mode = im.mode
tex = np.asarray(im.convert("RGB")).astype(np.float32) / 255
H, W = tex.shape[:2]
tri = P[idx]
nrm = np.cross(tri[:, 1] - tri[:, 0], tri[:, 2] - tri[:, 0])
nrm /= np.maximum(np.linalg.norm(nrm, axis=1, keepdims=True), 1e-12)
painted = 0
eps = 0.4                                   # cm: depth tolerance for visibility
for t_i in paintT:
    if nrm[t_i, 2] < a.min_nz:
        continue
    t = idx[t_i]
    if alpha[np.clip(Y[t].astype(int), 0, 1535), np.clip(X[t].astype(int), 0, 1023)].max() <= 0 and \
            alpha[int(np.clip(Y[t].mean(), 0, 1535)), int(np.clip(X[t].mean(), 0, 1023))] <= 0:
        # quick reject: no vertex/centroid near the region (dilated test below catches edges)
        bx0, by0 = int(X[t].min()) - 3, int(Y[t].min()) - 3
        if not alpha[max(by0, 0):int(Y[t].max()) + 4, max(bx0, 0):int(X[t].max()) + 4].any():
            continue
    u = uv[t, 0] % 1 * W
    w_ = uv[t, 1] % 1 * H
    x0, x1 = int(max(np.floor(u.min()) - 1, 0)), int(min(np.ceil(u.max()) + 1, W - 1))
    y0, y1 = int(max(np.floor(w_.min()) - 1, 0)), int(min(np.ceil(w_.max()) + 1, H - 1))
    gx, gy = np.meshgrid(np.arange(x0, x1 + 1) + 0.5, np.arange(y0, y1 + 1) + 0.5)
    den = (w_[1] - w_[2]) * (u[0] - u[2]) + (u[2] - u[1]) * (w_[0] - w_[2])
    if abs(den) < 1e-12:
        continue
    l0 = ((w_[1] - w_[2]) * (gx - u[2]) + (u[2] - u[1]) * (gy - w_[2])) / den
    l1 = ((w_[2] - w_[0]) * (gx - u[2]) + (u[0] - u[2]) * (gy - w_[2])) / den
    l2 = 1 - l0 - l1
    inside = (l0 >= -1e-4) & (l1 >= -1e-4) & (l2 >= -1e-4)   # no bleed into neighbouring UV charts
    if not inside.any():
        continue
    px = l0 * X[t[0]] + l1 * X[t[1]] + l2 * X[t[2]]
    py = l0 * Y[t[0]] + l1 * Y[t[1]] + l2 * Y[t[2]]
    pz = l0 * Z[t[0]] + l1 * Z[t[1]] + l2 * Z[t[2]]
    ix = np.clip(px.astype(int), 0, 1023)
    iy = np.clip(py.astype(int), 0, 1535)
    vis = inside & (pz >= zbuf[iy, ix] - eps)
    al = alpha[iy, ix] * vis
    if not (al > 0).any():
        continue
    src = M[iy, ix]
    sub = tex[y0:y1 + 1, x0:x1 + 1]
    sub[:] = sub * (1 - al[..., None]) + src * al[..., None]
    painted += int((al > 0).sum())
info["texels_painted"] = painted
out = Image.fromarray((np.clip(tex, 0, 1) * 255 + 0.5).astype(np.uint8))
if mode == "RGBA":
    out = out.convert("RGBA")
buf = io.BytesIO()
out.save(buf, "PNG")
v[bv] = buf.getvalue()
glb_mesh.save(a.dst, g, v)
if a.debug:
    dbg = (U * 0.5 + 0.5 * reg[..., None] * np.array([1, 0, 0])).clip(0, 1)
    x, y = to_img(P, k, dx, dy)
    Image.fromarray((dbg * 255).astype(np.uint8)).crop((312, max(top - 40, 0), 712, top + 300)).save(a.debug)
print(json.dumps(info))
