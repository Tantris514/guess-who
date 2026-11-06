"""One 256 px icon per inventory item, rendered on the CPU from the approved GLB models (no GPU, no ComfyUI: the shared editor runs -nullrhi, and
a rendered game run is not available while ComfyUI works or the user plays). A small z-buffer rasterizer: base-color texture, warm key light, cool
fill, a gold rim so dark items read on the dark HUD. Transparent background. Three items have no approved model (flashlight, firecracker, billiard
ball): they are lathed here from the same materials' colours. Re-runnable.
Output: Props (images)\\icons\\<id>_<name>.png, then ue_run.py Tools\\gameplay\\s42_feedback5.py icons imports them as /Game/GW/UI/Items/T_UI_Item_<id>.
Run: python -X utf8 Tools\\props\\item_icons.py [ids...]"""
import io
import json
import math
import os
import struct
import sys

import numpy as np
from PIL import Image

ROOT = r'J:\Projets\Unreal_Projects\Guess Who'
OUT = os.path.join(ROOT, 'Props (images)', 'icons')
SS, SIZE = 3, 256
MODELS = os.path.join(ROOT, 'AssetGen', 'models3d', '{0}_trellis_s42', '{0}.glb')
# id -> (file name, model or None, rotations applied in order about x / y / z in degrees, glTF axes: x right, y up, z towards the camera)
ITEMS = {
    1: ('fusil', 'rifle_old', (0, 12, 38)),
    2: ('fumigene', 'smoke_grenade', (15, 30, -12)),
    3: ('lampe', None, (0, 0, 0)),
    4: ('gaz', 'gas_canister', (12, 25, -10)),
    5: ('piege', 'door_trap', (35, -25, 0)),
    6: ('bombe', 'time_bomb', (10, 25, -8)),
    7: ('tourelle', 'turret_mg', (12, 28, 0)),
    8: ('echange', 'swap_pistol', (0, 15, 0)),
    9: ('petard', None, (0, 0, 0)),
    10: ('lame', 'hidden_blade', (8, 20, 35)),
    11: ('boule', None, (0, 0, 0)),
    12: ('epee', 'sword_knight', (0, 20, -40)),
    13: ('revolver', 'revolver', (0, 15, 0)),
    14: ('mascarade', None, (0, 0, 0)),
}


def read_glb(path):
    with open(path, 'rb') as f:
        data = f.read()
    n = struct.unpack('<I', data[12:16])[0]
    j = json.loads(data[20:20 + n])
    binstart = 20 + n + 8
    TYPES = {5126: ('f', 4), 5125: ('I', 4), 5123: ('H', 2), 5121: ('B', 1)}
    COMP = {'SCALAR': 1, 'VEC2': 2, 'VEC3': 3, 'VEC4': 4}

    def acc(i):
        a = j['accessors'][i]
        v = j['bufferViews'][a['bufferView']]
        off = binstart + v.get('byteOffset', 0) + a.get('byteOffset', 0)
        fmt, sz = TYPES[a['componentType']]
        nc = COMP[a['type']]
        stride = v.get('byteStride', 0) or sz * nc
        dt = np.dtype({'names': [f'c{k}' for k in range(nc)], 'formats': ['<' + fmt] * nc, 'offsets': [sz * k for k in range(nc)], 'itemsize': stride})
        arr = np.frombuffer(data, dtype=dt, count=a['count'], offset=off)
        return np.stack([arr[f'c{k}'].astype(float) for k in range(nc)], axis=1)

    P, N, UV, F, tex = [], [], [], [], None
    base = 0
    for mesh in j['meshes']:
        for pr in mesh['primitives']:
            p = acc(pr['attributes']['POSITION'])
            P.append(p)
            N.append(acc(pr['attributes']['NORMAL']) if 'NORMAL' in pr['attributes'] else np.zeros_like(p))
            UV.append(acc(pr['attributes']['TEXCOORD_0']) if 'TEXCOORD_0' in pr['attributes'] else np.zeros((len(p), 2)))
            F.append(acc(pr['indices']).astype(int).reshape(-1, 3) + base)
            base += len(p)
            m = j['materials'][pr['material']] if 'material' in pr else {}
            t = m.get('pbrMetallicRoughness', {}).get('baseColorTexture')
            if t and tex is None:
                im = j['images'][j['textures'][t['index']]['source']]
                v = j['bufferViews'][im['bufferView']]
                raw = data[binstart + v.get('byteOffset', 0):binstart + v.get('byteOffset', 0) + v['byteLength']]
                tex = np.asarray(Image.open(io.BytesIO(raw)).convert('RGB').resize((1024, 1024))).astype(float) / 255.0
    P, N, UV, F = np.vstack(P), np.vstack(N), np.vstack(UV), np.vstack(F)
    return P, N, UV, F, tex


def lathe(profile, seg=48):
    """profile: list of (radius, height, (r, g, b)). Returns a textureless mesh: per-vertex colours in C."""
    P, N, C, F = [], [], [], []
    k = len(profile)
    for i, (r, h, c) in enumerate(profile):
        a = profile[min(i + 1, k - 1)]
        b = profile[max(i - 1, 0)]
        dr, dh = a[0] - b[0], a[1] - b[1]
        L = math.hypot(dr, dh) or 1.0
        for s in range(seg):
            t = 2 * math.pi * s / seg
            P.append((r * math.cos(t), h, r * math.sin(t)))
            N.append((dh / L * math.cos(t), -dr / L, dh / L * math.sin(t)))
            C.append(c)
    for i in range(k - 1):
        for s in range(seg):
            a, b = i * seg + s, i * seg + (s + 1) % seg
            c, d = a + seg, b + seg
            F += [(a, c, b), (b, c, d)]
    return np.array(P, float), np.array(N, float), np.array(C, float), np.array(F, int)


def merged(parts):
    P, N, C, F, base = [], [], [], [], 0
    for (p, n, c, f), (rot, off) in parts:
        R = rotm(rot)
        P.append(p @ R.T + np.array(off)); N.append(n @ R.T); C.append(c); F.append(f + base)
        base += len(p)
    return np.vstack(P), np.vstack(N), np.vstack(C), np.vstack(F)


def rotm(r):
    ax, ay, az = [math.radians(v) for v in r]
    X = np.array([[1, 0, 0], [0, math.cos(ax), -math.sin(ax)], [0, math.sin(ax), math.cos(ax)]])
    Y = np.array([[math.cos(ay), 0, math.sin(ay)], [0, 1, 0], [-math.sin(ay), 0, math.cos(ay)]])
    Z = np.array([[math.cos(az), -math.sin(az), 0], [math.sin(az), math.cos(az), 0], [0, 0, 1]])
    return Z @ Y @ X


BRASS, DARK, RED, GREY, WHITE = (0.72, 0.52, 0.2), (0.08, 0.08, 0.09), (0.62, 0.07, 0.05), (0.42, 0.42, 0.44), (0.86, 0.84, 0.78)


def builtin(i):
    if i == 3:      # 1930s flashlight: a body, a wider head, a lens
        body = lathe([(0, -1, BRASS), (0.2, -1, BRASS), (0.2, 0.25, BRASS), (0.33, 0.45, BRASS), (0.33, 0.72, BRASS), (0.28, 0.73, WHITE), (0, 0.74, (1, 0.95, 0.75))])
        return merged([(body, ((0, 0, -50), (0, 0, 0)))])
    if i == 9:      # firecracker: a red tube, grey caps, a short fuse
        tube = lathe([(0, -0.8, GREY), (0.2, -0.8, GREY), (0.2, -0.72, RED), (0.2, 0.72, RED), (0.2, 0.8, GREY), (0, 0.82, GREY)])
        fuse = lathe([(0.025, 0.8, DARK), (0.025, 1.25, DARK), (0, 1.27, (0.9, 0.5, 0.1))], seg=10)
        return merged([(tube, ((0, 0, -35), (0, 0, 0))), (fuse, ((0, 0, -35), (0, 0, 0)))])
    if i == 11:     # a billiard ball, red with a white spot
        ball = lathe([(math.sin(k / 40 * math.pi), -math.cos(k / 40 * math.pi), WHITE if k > 34 else RED) for k in range(41)], seg=64)
        return merged([(ball, ((-35, 25, 0), (0, 0, 0)))])


def render(P, N, F, UV=None, tex=None, C=None, rot=(0, 0, 0)):
    R = rotm(rot)
    P = P @ R.T
    N = N @ R.T
    nl = np.linalg.norm(N, axis=1)
    lo, hi = P[:, :2].min(0), P[:, :2].max(0)
    span = (hi - lo).max()
    W = SIZE * SS
    s = W * 0.88 / span
    cx, cy = (lo + hi) / 2
    X = (P[:, 0] - cx) * s + W / 2
    Y = W / 2 - (P[:, 1] - cy) * s
    Z = P[:, 2]
    zb = np.full((W, W), -1e9)
    col = np.zeros((W, W, 3))
    if nl.min() < 0.5:                     # no normals in the file: from the faces
        a, b, c = P[F[:, 0]], P[F[:, 1]], P[F[:, 2]]
        fn = np.cross(b - a, c - a)
        N = np.zeros_like(P)
        for k in range(3):
            np.add.at(N, F[:, k], fn)
    N = N / (np.linalg.norm(N, axis=1, keepdims=True) + 1e-9)
    key, fill = np.array([-0.45, 0.6, 0.66]), np.array([0.7, -0.15, 0.5])
    key /= np.linalg.norm(key); fill /= np.linalg.norm(fill)
    for f in F:
        i0, i1, i2 = f
        x0, x1, x2, y0, y1, y2 = X[i0], X[i1], X[i2], Y[i0], Y[i1], Y[i2]
        xa, xb = int(max(min(x0, x1, x2), 0)), int(min(max(x0, x1, x2) + 1, W))
        ya, yb = int(max(min(y0, y1, y2), 0)), int(min(max(y0, y1, y2) + 1, W))
        if xa >= xb or ya >= yb:
            continue
        den = (y1 - y2) * (x0 - x2) + (x2 - x1) * (y0 - y2)
        if abs(den) < 1e-9:
            continue
        gx, gy = np.meshgrid(np.arange(xa, xb) + 0.5, np.arange(ya, yb) + 0.5)
        w0 = ((y1 - y2) * (gx - x2) + (x2 - x1) * (gy - y2)) / den
        w1 = ((y2 - y0) * (gx - x2) + (x0 - x2) * (gy - y2)) / den
        w2 = 1 - w0 - w1
        m = (w0 >= 0) & (w1 >= 0) & (w2 >= 0)
        if not m.any():
            continue
        z = w0 * Z[i0] + w1 * Z[i1] + w2 * Z[i2]
        vis = m & (z > zb[ya:yb, xa:xb])
        if not vis.any():
            continue
        w = np.stack([w0[vis], w1[vis], w2[vis]], axis=1)
        n = w @ N[f]
        n /= np.linalg.norm(n, axis=1, keepdims=True) + 1e-9
        if tex is not None:
            uv = w @ UV[f]
            u = np.clip((uv[:, 0] % 1.0) * 1023, 0, 1023).astype(int)
            v = np.clip((uv[:, 1] % 1.0) * 1023, 0, 1023).astype(int)
            base = tex[v, u]
        else:
            base = w @ C[f]
        lit = 0.38 + 1.05 * np.clip(n @ key, 0, 1)[:, None] * np.array([1.0, 0.95, 0.85]) + 0.32 * np.clip(n @ fill, 0, 1)[:, None] * np.array([0.8, 0.88, 1.0])
        rim = np.clip(1 - np.abs(n[:, 2]), 0, 1)[:, None] ** 3 * np.array([0.62, 0.46, 0.2])
        sub = zb[ya:yb, xa:xb]
        sub[vis] = z[vis]
        cc = col[ya:yb, xa:xb]
        cc[vis] = np.clip(base * lit + rim, 0, 1)
    alpha = (zb > -1e8).astype(float)
    img = np.dstack([col * alpha[..., None], alpha])
    # down-sample with premultiplied alpha, then a soft shadow is not needed: the HUD's slot is dark already
    small = img.reshape(SIZE, SS, SIZE, SS, 4).mean((1, 3))
    a = small[..., 3:]
    rgb = np.where(a > 1e-3, small[..., :3] / np.maximum(a, 1e-3), 0)
    rgb = np.clip(rgb, 0, 1) ** (1 / 1.15)
    return Image.fromarray((np.dstack([rgb, a]) * 255).astype(np.uint8), 'RGBA')


def mask_icon():
    """A gold masquerade mask, drawn in 2D: no 3D model for this one."""
    from PIL import ImageDraw
    S = 1024
    im = Image.new('RGBA', (S, S), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    top = [(80, 330), (240, 300), (420, 350), (512, 400), (604, 350), (784, 300), (944, 330), (900, 560), (720, 700), (580, 650), (512, 560), (444, 650), (304, 700), (124, 560)]
    d.polygon([(x, y + 14) for x, y in top], fill=(90, 58, 18, 255))
    d.polygon(top, fill=(214, 164, 72, 255))
    d.polygon([(110, 350), (240, 322), (420, 370), (512, 420), (604, 370), (784, 322), (914, 350), (905, 410), (120, 410)], fill=(245, 208, 120, 255))
    for cx in (320, 704):
        d.ellipse([cx - 95, 430, cx + 95, 560], fill=(0, 0, 0, 0))
    d.polygon([(905, 330), (960, 150), (1000, 170), (945, 360)], fill=(140, 28, 36, 255))
    return im.resize((256, 256), Image.LANCZOS)


os.makedirs(OUT, exist_ok=True)
want = {int(x) for x in sys.argv[1:]} or set(ITEMS)
for i, (name, model, rot) in ITEMS.items():
    if i not in want:
        continue
    if i == 14:
        mask_icon().save(os.path.join(OUT, f'{i:02d}_{name}.png'))
        continue
    if model:
        P, N, UV, F, tex = read_glb(MODELS.format(model))
        print(i, name, model, 'vertices', len(P), 'triangles', len(F), 'texture', tex is not None, flush=True)
        im = render(P, N, F, UV=UV, tex=tex, C=np.full((len(P), 3), 0.6), rot=rot)
    else:
        P, N, C, F = builtin(i)
        im = render(P, N, F, C=C, rot=rot)
    im.save(os.path.join(OUT, f'{i:02d}_{name}.png'))
# a contact sheet on the HUD's dark colour, for review
files = sorted(f for f in os.listdir(OUT) if f.endswith('.png') and f[:2].isdigit())
sheet = Image.new('RGBA', (7 * 200, 2 * 200), (10, 8, 7, 255))
for k, f in enumerate(files):
    im = Image.open(os.path.join(OUT, f)).resize((192, 192))
    sheet.alpha_composite(im, (k % 7 * 200 + 4, k // 7 * 200 + 4))
sheet.convert('RGB').save(os.path.join(OUT, '_planche.jpg'), quality=90)
print('icons in', OUT)
