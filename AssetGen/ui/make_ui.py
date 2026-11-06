"""Builds the final UI textures in AssetGen/ui/final from the ComfyUI art (AssetGen/ui/gen) plus procedural Art Deco
pieces drawn with PIL (9-slice frames, buttons, slider parts, crosshair, dial). Run with the ComfyUI venv python:
  python -I make_ui.py [only_name ...]
Selections (which generated candidate is used) live in SEL below; every accepted file is recorded in ui_manifest.json.
"""
import json, math, os, sys
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageChops, ImageOps

HERE = os.path.dirname(os.path.abspath(__file__))
GEN = os.path.join(HERE, "gen")
OUT = os.path.join(HERE, "final")
os.makedirs(OUT, exist_ok=True)

GOLD_HI = (246, 222, 150)
GOLD = (212, 168, 74)
GOLD_LO = (138, 100, 32)
IVORY = (238, 228, 205)
LACQUER = (10, 9, 8)
EMERALD = (14, 62, 48)
BURGUNDY = (92, 18, 28)

SEL = {}            # name -> (gen file, notes); filled by select() calls below
ONLY = set(sys.argv[1:])
manifest_path = os.path.join(os.path.dirname(HERE), "ui_manifest.json")
manifest = json.load(open(manifest_path, encoding="utf-8")) if os.path.exists(manifest_path) else {"assets": []}


def record(name, path, source=None, notes=""):
    src = None
    if source:
        side = os.path.splitext(source)[0] + ".txt"
        src = {"file": source}
        if os.path.exists(side):
            meta = json.load(open(side, encoding="utf-8"))
            src.update({"model": meta.get("model", "z_image_turbo_bf16"), "seed": meta.get("seed"), "batch_index": meta.get("batch_index"),
                        "prompt": meta.get("prompt")})
    manifest["assets"] = [a for a in manifest["assets"] if a["name"] != name]
    manifest["assets"].append({"name": name, "kind": "ui_texture", "status": "approved", "file": path, "source": src,
                               "procedural": source is None or "procedural" in notes, "notes": notes})


def want(name):
    return not ONLY or name in ONLY


def gen(name, k):
    d = os.path.join(GEN, name)
    for f in sorted(os.listdir(d)):
        if f.endswith(f"_{k}.png"):
            return os.path.join(d, f)
    raise FileNotFoundError(f"{name} candidate {k}")


def save(img, name, source=None, notes=""):
    p = os.path.join(OUT, name + ".png")
    img.save(p)
    record(name, p, source, notes)
    print("wrote", name, img.size)
    return p


# ---------------------------------------------------------------- helpers
def key_black(img, lo=0.10, hi=0.32, unpremul=True):
    """Gold-on-black art -> RGBA. Alpha from the max channel, colour un-premultiplied so edges stay golden."""
    a = np.asarray(img.convert("RGB")).astype(np.float32) / 255.0
    m = a.max(axis=2)
    alpha = np.clip((m - lo) / (hi - lo), 0, 1)
    alpha = alpha * alpha * (3 - 2 * alpha)
    rgb = a
    if unpremul:
        rgb = np.clip(a / np.maximum(m[..., None], 1e-3) * np.clip(m[..., None] / hi, 0.55, 1.0) * 1.0, 0, 1)
        rgb = np.where(alpha[..., None] > 0.999, a, rgb)
    out = np.dstack([rgb, alpha])
    return Image.fromarray((out * 255).astype(np.uint8), "RGBA")


def key_green(img, spill=True):
    """Chroma-green background -> RGBA (for the foreground drapes)."""
    a = np.asarray(img.convert("RGB")).astype(np.float32) / 255.0
    r, g, b = a[..., 0], a[..., 1], a[..., 2]
    greenness = g - np.maximum(r, b)
    alpha = 1 - np.clip((greenness - 0.08) / 0.25, 0, 1)
    if spill:
        g2 = np.minimum(g, np.maximum(r, b) * 1.05)
        a = np.dstack([r, g2, b])
    alpha_img = Image.fromarray((alpha * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(1.2))
    out = Image.fromarray((np.clip(a, 0, 1) * 255).astype(np.uint8), "RGB").convert("RGBA")
    out.putalpha(alpha_img)
    return out


def crop_alpha(img, pad=0.06, square=True):
    bb = img.getchannel("A").point(lambda v: 255 if v > 8 else 0).getbbox()
    if not bb:
        return img
    x0, y0, x1, y1 = bb
    w, h = x1 - x0, y1 - y0
    if square:
        s = max(w, h)
        cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
        s = int(s * (1 + 2 * pad))
        box = (int(cx - s / 2), int(cy - s / 2), int(cx - s / 2) + s, int(cy - s / 2) + s)
    else:
        px, py = int(w * pad), int(h * pad)
        box = (x0 - px, y0 - py, x1 + px, y1 + py)
    canvas = Image.new("RGBA", (box[2] - box[0], box[3] - box[1]), (0, 0, 0, 0))
    canvas.paste(img.crop((max(box[0], 0), max(box[1], 0), min(box[2], img.width), min(box[3], img.height))),
                 (max(0, -box[0]), max(0, -box[1])))
    return canvas


def gold_fill(size, angle=90, hi=GOLD_HI, mid=GOLD, lo=GOLD_LO):
    """Metallic gold gradient (three stops, slightly banded like gold leaf)."""
    w, h = size
    y = np.linspace(0, 1, h)[:, None] * np.ones((1, w))
    x = np.linspace(0, 1, w)[None, :] * np.ones((h, 1))
    t = (y if angle == 90 else x)
    t = (t + 0.08 * np.sin(x * 9.0 + y * 5.0)) % 1.0
    stops = [(0.0, lo), (0.28, mid), (0.5, hi), (0.72, mid), (1.0, lo)]
    out = np.zeros((h, w, 3))
    for (t0, c0), (t1, c1) in zip(stops, stops[1:]):
        m = (t >= t0) & (t <= t1)
        f = ((t - t0) / (t1 - t0))[m][:, None]
        out[m] = np.array(c0) * (1 - f) + np.array(c1) * f
    return Image.fromarray(out.astype(np.uint8), "RGB")


def gold_layer(mask):
    """Colour a white-on-black L mask with gold leaf, return RGBA."""
    g = gold_fill(mask.size).convert("RGBA")
    g.putalpha(mask)
    return g


def lacquer(size, base=LACQUER, tint=EMERALD, noise=6, seed=1):
    rng = np.random.default_rng(seed)
    w, h = size
    y = np.linspace(-1, 1, h)[:, None]; x = np.linspace(-1, 1, w)[None, :]
    v = 1 - 0.35 * (x * x * 0.5 + y * y)
    arr = np.ones((h, w, 3)) * np.array(base) * v[..., None]
    arr += (np.array(tint) - np.array(base)) * 0.18 * (0.5 + 0.5 * y)[..., None]
    arr += rng.normal(0, noise * 0.25, (h, w, 1))
    return Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8), "RGB")


SS = 3  # supersampling for procedural drawing


def frame_mask(w, h, inset, line, gap, corner_step, double=True):
    """Deco double border with stepped (notched) corners, drawn at SS scale. Returns L mask (w*SS, h*SS)."""
    W, H = w * SS, h * SS
    m = Image.new("L", (W, H), 0)
    d = ImageDraw.Draw(m)
    def border(i, lw, step):
        i, lw, step = i * SS, lw * SS, step * SS
        # polygon with stepped corners
        pts = [(i + step, i), (W - i - step, i), (W - i - step, i + step), (W - i, i + step), (W - i, H - i - step),
               (W - i - step, H - i - step), (W - i - step, H - i), (i + step, H - i), (i + step, H - i - step),
               (i, H - i - step), (i, i + step), (i + step, i + step)]
        d.line(pts + [pts[0]], fill=255, width=int(lw), joint="curve")
    border(inset, line, corner_step)
    if double:
        border(inset + gap, max(1, line * 0.5), corner_step)
    return m


def downsample(img):
    return img.resize((img.width // SS, img.height // SS), Image.LANCZOS)


# ---------------------------------------------------------------- procedural pieces
def make_panel():
    """512x512 9-slice panel: black lacquer, double gold border with stepped corners, corner fans (generated art)."""
    w = h = 512
    fill = lacquer((w * SS, h * SS)).convert("RGBA")
    base = Image.new("RGBA", (w * SS, h * SS), (0, 0, 0, 0))
    inner = Image.new("L", (w * SS, h * SS), 0)
    ImageDraw.Draw(inner).rectangle((10 * SS, 10 * SS, (w - 10) * SS, (h - 10) * SS), fill=242)
    fill.putalpha(inner)
    base.alpha_composite(fill)
    m = frame_mask(w, h, 14, 3.0, 9, 26)
    base.alpha_composite(gold_layer(m))
    try:
        c = corner_piece(150)
        cS = c.resize((c.width * SS, c.height * SS), Image.LANCZOS)
        for flipx, flipy in ((0, 0), (1, 0), (0, 1), (1, 1)):
            p = cS
            if flipx: p = ImageOps.mirror(p)
            if flipy: p = ImageOps.flip(p)
            x = (w * SS - p.width - 6 * SS) if flipx else 6 * SS
            y = (h * SS - p.height - 6 * SS) if flipy else 6 * SS
            base.alpha_composite(p, (x, y))
    except FileNotFoundError:
        pass
    return downsample(base)


def corner_piece(size):
    src = gen("orn_corner", 0)
    k = key_black(Image.open(src), 0.16, 0.42)
    # keep only the fan + line junction (top-left 42 %)
    k = k.crop((0, 0, int(k.width * 0.42), int(k.height * 0.42)))
    bb = k.getchannel("A").point(lambda v: 255 if v > 20 else 0).getbbox()
    k = k.crop((bb[0], bb[1], bb[0] + max(bb[2] - bb[0], bb[3] - bb[1]), bb[1] + max(bb[2] - bb[0], bb[3] - bb[1])))
    return k.resize((size, size), Image.LANCZOS)


def make_button(state):
    """512x128 9-slice button. state: normal / hover / pressed / disabled."""
    w, h = 512, 128
    W, H = w * SS, h * SS
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    # body: elongated hexagon (deco chamfer)
    ch = 26 * SS
    body = Image.new("L", (W, H), 0)
    bd = ImageDraw.Draw(body)
    poly = [(ch, 8 * SS), (W - ch, 8 * SS), (W - 8 * SS, H // 2), (W - ch, H - 8 * SS), (ch, H - 8 * SS), (8 * SS, H // 2)]
    bd.polygon(poly, fill=255)
    if state == "hover":
        fill = Image.new("RGB", (W, H), (0, 0, 0))
        g = np.linspace(0, 1, H)[:, None] * np.ones((1, W))
        xx = np.abs(np.linspace(-1, 1, W))[None, :] * np.ones((H, 1))
        glow = np.exp(-((g - 0.5) ** 2) / 0.08) * (1 - 0.6 * xx)
        arr = np.array([60, 40, 12]) * glow[..., None] + np.array([16, 12, 8])
        fill = Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8), "RGB")
        alpha = 245
    elif state == "pressed":
        fill = lacquer((W, H), base=(4, 4, 3), tint=(30, 20, 6), noise=3, seed=3)
        alpha = 250
    else:
        fill = lacquer((W, H), base=(9, 8, 7), tint=EMERALD, noise=4, seed=2)
        alpha = 225 if state == "normal" else 160
    f = fill.convert("RGBA")
    f.putalpha(body.point(lambda v: v * alpha // 255))
    img.alpha_composite(f)
    # gold outline (two lines) following the chamfer
    m = Image.new("L", (W, H), 0)
    md = ImageDraw.Draw(m)
    lw = {"normal": 2.2, "hover": 3.2, "pressed": 2.6, "disabled": 1.6}[state] * SS
    md.line(poly + [poly[0]], fill=255, width=int(lw), joint="curve")
    inset = 9 * SS
    poly2 = [(ch + inset * 0.6, 8 * SS + inset), (W - ch - inset * 0.6, 8 * SS + inset), (W - 8 * SS - inset * 1.4, H // 2),
             (W - ch - inset * 0.6, H - 8 * SS - inset), (ch + inset * 0.6, H - 8 * SS - inset), (8 * SS + inset * 1.4, H // 2)]
    md.line(poly2 + [poly2[0]], fill=150 if state != "hover" else 230, width=int(1.0 * SS), joint="curve")
    # small diamonds at both ends
    for cx in (30 * SS, W - 30 * SS):
        r = 7 * SS
        md.polygon([(cx, H // 2 - r), (cx + r, H // 2), (cx, H // 2 + r), (cx - r, H // 2)], fill=255)
    gl = gold_layer(m)
    if state == "disabled":
        a = np.asarray(gl).astype(np.float32); a[..., :3] = a[..., :3].mean(axis=2, keepdims=True) * 0.7; a[..., 3] *= 0.6
        gl = Image.fromarray(a.astype(np.uint8), "RGBA")
    if state == "pressed":
        a = np.asarray(gl).astype(np.float32); a[..., :3] *= 0.78
        gl = Image.fromarray(a.astype(np.uint8), "RGBA")
    if state == "hover":
        halo = gl.getchannel("A").filter(ImageFilter.GaussianBlur(6 * SS))
        hl = Image.new("RGBA", (W, H), GOLD + (0,)); hl.putalpha(halo.point(lambda v: int(v * 0.55)))
        img.alpha_composite(hl)
    img.alpha_composite(gl)
    return downsample(img)


def make_field():
    """256x64 9-slice text field: dark inset with a gold underline."""
    w, h = 256, 64
    W, H = w * SS, h * SS
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    body = Image.new("RGBA", (W, H), (6, 5, 4, 200))
    m = Image.new("L", (W, H), 0)
    ImageDraw.Draw(m).rectangle((2 * SS, 2 * SS, W - 2 * SS, H - 2 * SS), fill=255)
    body.putalpha(m.point(lambda v: v * 200 // 255))
    img.alpha_composite(body)
    g = Image.new("L", (W, H), 0)
    gd = ImageDraw.Draw(g)
    gd.rectangle((2 * SS, H - 5 * SS, W - 2 * SS, H - 3 * SS), fill=255)
    gd.rectangle((2 * SS, 2 * SS, W - 2 * SS, H - 2 * SS), outline=70, width=SS)
    img.alpha_composite(gold_layer(g))
    return downsample(img)


def make_slider_parts():
    bar = Image.new("RGBA", (256 * SS, 8 * SS), (0, 0, 0, 0))
    m = Image.new("L", bar.size, 0)
    ImageDraw.Draw(m).rectangle((0, 0, bar.width, bar.height), fill=235)
    bar.alpha_composite(gold_layer(m))
    thumb = Image.new("RGBA", (48 * SS, 48 * SS), (0, 0, 0, 0))
    tm = Image.new("L", thumb.size, 0)
    c = 24 * SS; r = 18 * SS
    td = ImageDraw.Draw(tm)
    td.polygon([(c, c - r), (c + r, c), (c, c + r), (c - r, c)], fill=255)
    td.polygon([(c, c - r * 0.45), (c + r * 0.45, c), (c, c + r * 0.45), (c - r * 0.45, c)], fill=110)
    sh = tm.filter(ImageFilter.GaussianBlur(3 * SS))
    shadow = Image.new("RGBA", thumb.size, (0, 0, 0, 0)); shadow.putalpha(sh.point(lambda v: int(v * 0.7)))
    thumb.alpha_composite(shadow, (0, 2 * SS))
    thumb.alpha_composite(gold_layer(tm))
    return downsample(bar), downsample(thumb)


def make_crosshair():
    s = 128 * SS
    m = Image.new("L", (s, s), 0)
    d = ImageDraw.Draw(m)
    c = s // 2
    r = 22 * SS
    d.ellipse((c - r, c - r, c + r, c + r), outline=255, width=int(2.2 * SS))
    for ang in range(0, 360, 90):
        a = math.radians(ang)
        x0, y0 = c + math.cos(a) * (r + 6 * SS), c + math.sin(a) * (r + 6 * SS)
        x1, y1 = c + math.cos(a) * (r + 22 * SS), c + math.sin(a) * (r + 22 * SS)
        d.line((x0, y0, x1, y1), fill=255, width=int(2.4 * SS))
    for ang in range(45, 360, 90):
        a = math.radians(ang); rr = r - 7 * SS
        x, y = c + math.cos(a) * rr, c + math.sin(a) * rr
        q = 3.2 * SS
        d.polygon([(x, y - q), (x + q, y), (x, y + q), (x - q, y)], fill=255)
    d.ellipse((c - 2.6 * SS, c - 2.6 * SS, c + 2.6 * SS, c + 2.6 * SS), fill=255)
    # dark outline for readability on bright scenes
    halo = m.filter(ImageFilter.MaxFilter(5)).filter(ImageFilter.GaussianBlur(2 * SS))
    img = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    sh = Image.new("RGBA", (s, s), (0, 0, 0, 0)); sh.putalpha(halo.point(lambda v: int(v * 0.75)))
    img.alpha_composite(sh)
    ivory = Image.new("RGBA", (s, s), IVORY + (0,)); ivory.putalpha(m)
    img.alpha_composite(ivory)
    return downsample(img)


def make_dial():
    """Timer dial (256): gold ring, 60 ticks (12 major), sunburst centre; hand drawn separately (rotated in UMG)."""
    s = 256 * SS
    c = s // 2
    m = Image.new("L", (s, s), 0)
    d = ImageDraw.Draw(m)
    R = 120 * SS
    d.ellipse((c - R, c - R, c + R, c + R), outline=255, width=int(5 * SS))
    d.ellipse((c - R + 10 * SS, c - R + 10 * SS, c + R - 10 * SS, c + R - 10 * SS), outline=170, width=int(1.5 * SS))
    for i in range(60):
        a = math.radians(i * 6 - 90)
        major = i % 5 == 0
        r0 = R - (26 if major else 18) * SS
        r1 = R - 13 * SS
        w = (4 if major else 1.6) * SS
        d.line((c + math.cos(a) * r0, c + math.sin(a) * r0, c + math.cos(a) * r1, c + math.sin(a) * r1), fill=255, width=int(w))
    for i in range(24):  # sunburst rays in the face
        a = math.radians(i * 15 - 90)
        r1 = (52 if i % 2 == 0 else 36) * SS
        d.line((c + math.cos(a) * 14 * SS, c + math.sin(a) * 14 * SS, c + math.cos(a) * r1, c + math.sin(a) * r1), fill=90, width=int(2 * SS))
    face = Image.new("L", (s, s), 0)
    ImageDraw.Draw(face).ellipse((c - R + 3 * SS, c - R + 3 * SS, c + R - 3 * SS, c + R - 3 * SS), fill=255)
    img = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    bg = lacquer((s, s), base=(8, 7, 6), tint=EMERALD, seed=5).convert("RGBA"); bg.putalpha(face.point(lambda v: v * 235 // 255))
    img.alpha_composite(bg)
    img.alpha_composite(gold_layer(m))
    hand = Image.new("L", (s, s), 0)
    hd = ImageDraw.Draw(hand)
    hd.polygon([(c, c - 92 * SS), (c + 7 * SS, c - 20 * SS), (c, c + 18 * SS), (c - 7 * SS, c - 20 * SS)], fill=255)
    hd.ellipse((c - 9 * SS, c - 9 * SS, c + 9 * SS, c + 9 * SS), fill=255)
    hand_img = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    hs = Image.new("RGBA", (s, s), (0, 0, 0, 0)); hs.putalpha(hand.filter(ImageFilter.GaussianBlur(3 * SS)).point(lambda v: int(v * 0.6)))
    hand_img.alpha_composite(hs, (2 * SS, 3 * SS))
    iv = Image.new("RGBA", (s, s), IVORY + (0,)); iv.putalpha(hand)
    hand_img.alpha_composite(iv)
    # progress ring mask (white ring, tinted + revealed in UMG through a material-free trick: 60 segments)
    return downsample(img), downsample(hand_img)


def make_vignette(w=512, h=288):
    y = np.linspace(-1, 1, h)[:, None]; x = np.linspace(-1, 1, w)[None, :]
    r = np.sqrt((x * 0.85) ** 2 + y ** 2)
    a = np.clip((r - 0.45) / 0.75, 0, 1) ** 1.6
    img = np.zeros((h, w, 4), np.uint8); img[..., 3] = (a * 255).astype(np.uint8)
    return Image.fromarray(img, "RGBA")


def make_glow(size=128, color=GOLD_HI):
    y = np.linspace(-1, 1, size)[:, None]; x = np.linspace(-1, 1, size)[None, :]
    r = np.sqrt(x * x + y * y)
    a = np.clip(1 - r, 0, 1) ** 2.2
    img = np.zeros((size, size, 4), np.uint8)
    img[..., :3] = color; img[..., 3] = (a * 255).astype(np.uint8)
    return Image.fromarray(img, "RGBA")


def make_gradient_bar(w=512, h=64):
    """Horizontal fade (opaque centre, transparent ends) for banners behind HUD text."""
    x = np.abs(np.linspace(-1, 1, w))[None, :] * np.ones((h, 1))
    y = np.abs(np.linspace(-1, 1, h))[:, None] * np.ones((1, w))
    a = np.clip(1 - x ** 2.5, 0, 1) * np.clip(1 - y ** 6, 0, 1)
    img = np.zeros((h, w, 4), np.uint8); img[..., 3] = (a * 255).astype(np.uint8)
    return Image.fromarray(img, "RGBA")


def make_arrow(right=True, s=64):
    S = s * SS
    m = Image.new("L", (S, S), 0)
    d = ImageDraw.Draw(m)
    pts = [(S * 0.36, S * 0.18), (S * 0.68, S * 0.5), (S * 0.36, S * 0.82)]
    d.line(pts, fill=255, width=int(S * 0.11), joint="curve")
    img = gold_layer(m)
    if not right:
        img = ImageOps.mirror(img)
    return downsample(img)


def make_panel_small():
    """256x256 9-slice HUD frame: lacquer, double gold border, stepped corners, small corner diamonds (no fans)."""
    w = h = 256
    fill = lacquer((w * SS, h * SS), seed=9).convert("RGBA")
    inner = Image.new("L", (w * SS, h * SS), 0)
    ImageDraw.Draw(inner).rectangle((6 * SS, 6 * SS, (w - 6) * SS, (h - 6) * SS), fill=228)
    fill.putalpha(inner)
    base = Image.new("RGBA", (w * SS, h * SS), (0, 0, 0, 0)); base.alpha_composite(fill)
    m = frame_mask(w, h, 8, 2.2, 6, 14)
    d = ImageDraw.Draw(m)
    for cx, cy in ((22, 22), (w - 22, 22), (22, h - 22), (w - 22, h - 22)):
        r = 4.5 * SS; X, Y = cx * SS, cy * SS
        d.polygon([(X, Y - r), (X + r, Y), (X, Y + r), (X - r, Y)], fill=255)
    base.alpha_composite(gold_layer(m))
    return downsample(base)


def make_shade_left(w=512, h=64):
    x = np.linspace(0, 1, w)[None, :] * np.ones((h, 1))
    a = np.clip(1 - x, 0, 1) ** 1.35
    a = a * a * (3 - 2 * a)
    img = np.zeros((h, w, 4), np.uint8); img[..., 3] = (a * 255).astype(np.uint8)
    return Image.fromarray(img, "RGBA")


def make_card_frame(w=640, h=960):
    """Ivory invitation card (scoreboard / end card): paper + gold double border + corner fans."""
    try:
        paper = Image.open(gen("tex_paper", 0)).convert("RGB").resize((w * SS, h * SS), Image.LANCZOS)
    except FileNotFoundError:
        paper = Image.new("RGB", (w * SS, h * SS), IVORY)
    img = paper.convert("RGBA")
    m = frame_mask(w, h, 18, 3.0, 10, 30)
    img.alpha_composite(gold_layer(m))
    rnd = Image.new("L", img.size, 0)
    ImageDraw.Draw(rnd).rounded_rectangle((0, 0, img.width - 1, img.height - 1), radius=14 * SS, fill=255)
    img.putalpha(rnd)
    return downsample(img)


def halftone(img, cell=6, angle=45, ink=(26, 22, 18), paper=(232, 220, 190)):
    g = np.asarray(img.convert("L").filter(ImageFilter.GaussianBlur(0.8))).astype(np.float32) / 255
    h, w = g.shape
    out = Image.new("RGB", (w * 2, h * 2), paper)
    d = ImageDraw.Draw(out)
    ca, sa = math.cos(math.radians(angle)), math.sin(math.radians(angle))
    diag = int(math.hypot(w, h))
    for v in range(-diag, diag, cell):
        for u in range(-diag, diag, cell):
            x = u * ca - v * sa + w / 2; y = u * sa + v * ca + h / 2
            if 0 <= x < w and 0 <= y < h:
                dark = 1 - g[int(y), int(x)]
                r = cell * 1.42 * math.sqrt(max(dark, 0) ** 1.25)
                if r > 0.3:
                    d.ellipse((x * 2 - r, y * 2 - r, x * 2 + r, y * 2 + r), fill=ink)
    return out.resize((w, h), Image.LANCZOS)



def card_cutout(src, radius_frac=0.045):
    """Cut a generated card out of its white/ivory surround: find the dark card body, rounded-rect alpha."""
    im = Image.open(src).convert("RGB")
    a = np.asarray(im).astype(np.float32)
    lum = a.mean(axis=2)
    dark = lum < 150
    rows = np.where(dark.mean(axis=1) > 0.25)[0]; cols = np.where(dark.mean(axis=0) > 0.25)[0]
    x0, x1, y0, y1 = cols[0], cols[-1] + 1, rows[0], rows[-1] + 1
    ix, iy = int((x1 - x0) * 0.006) + 2, int((y1 - y0) * 0.006) + 2
    card = im.crop((x0 + ix, y0 + iy, x1 - ix, y1 - iy)).convert("RGBA")
    W, H = card.size
    m = Image.new("L", (W * SS, H * SS), 0)
    ImageDraw.Draw(m).rounded_rectangle((0, 0, W * SS - 1, H * SS - 1), radius=int(min(W, H) * radius_frac * SS), fill=255)
    card.putalpha(m.resize((W, H), Image.LANCZOS))
    return card


def keyed_icon(name, k, size=256, lo=0.12, hi=0.34):
    src = gen(name, k)
    ic = crop_alpha(key_black(Image.open(src), lo, hi), pad=0.04)
    return ic.resize((size, size), Image.LANCZOS), src


def drapes(src):
    im = Image.open(src)
    return key_green(im)


def with_shadow(img, radius=10, strength=0.85, pad=24):
    """Bake a soft dark halo under keyed art so it reads on busy backgrounds."""
    W, H = img.width + 2 * pad, img.height + 2 * pad
    base = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    a = Image.new("L", (W, H), 0); a.paste(img.getchannel("A"), (pad, pad))
    halo = a.filter(ImageFilter.MaxFilter(5)).filter(ImageFilter.GaussianBlur(radius))
    sh = Image.new("RGBA", (W, H), (0, 0, 0, 0)); sh.putalpha(halo.point(lambda v: int(min(255, v * strength * 1.4))))
    base.alpha_composite(sh)
    base.alpha_composite(img, (pad, pad))
    return base


def generated():
    if want("T_UI_BgBallroom"):
        src = gen("bg_ballroom", 0)
        save(Image.open(src).convert("RGB"), "T_UI_BgBallroom", src, "main menu background (far layer)")
    if want("T_UI_Drapes"):
        src = gen("fg_drapes", 0)
        save(drapes(src), "T_UI_Drapes", src, "foreground velvet drapes, chroma-keyed (near parallax layer)")
    if want("T_UI_Arrival"):
        src = gen("art_arrival", 0)
        save(Image.open(src).convert("RGB"), "T_UI_Arrival", src, "loading / connection art")
    if want("T_UI_CardInvite"):
        src = gen("card_invite", 1)
        save(card_cutout(src).resize((640, 960), Image.LANCZOS), "T_UI_CardInvite", src, "role reveal card (text plaque left empty, title in UMG)")
    if want("T_UI_CardDetective"):
        src = gen("card_detective", 1)
        save(card_cutout(src).resize((640, 960), Image.LANCZOS), "T_UI_CardDetective", src, "role reveal card (text plaque left empty, title in UMG)")
    for out, (name, k) in {"T_UI_IcoMask": ("ico_mask", 0), "T_UI_IcoMaskDeco": ("ico_mask", 1), "T_UI_IcoRevolver": ("ico_revolver", 0),
                           "T_UI_IcoGhost": ("ico_ghost", 0), "T_UI_IcoClock": ("ico_clock", 0)}.items():
        if want(out):
            ic, src = keyed_icon(name, k)
            save(ic, out, src, "gold icon keyed from black")
    for out, (name, k) in {"T_UI_HowBlend": ("howto_blend", 0), "T_UI_HowHunt": ("howto_hunt", 0),
                           "T_UI_HowPenalty": ("howto_penalty", 0), "T_UI_HowGhost": ("howto_ghost", 0)}.items():
        if want(out):
            src = gen(name, k)
            save(Image.open(src).convert("RGB").resize((768, 526), Image.LANCZOS), out, src, "how-to-play rule card illustration")
    for out, (name, k) in {"T_UI_PhotoDetectives": ("photo_detectives", 0), "T_UI_PhotoGuests": ("photo_guests", 0)}.items():
        if want(out):
            src = gen(name, k)
            im = Image.open(src).convert("RGB").resize((900, 616), Image.LANCZOS)
            im = ImageOps.autocontrast(im.convert("L"), cutoff=1).convert("RGB")
            save(halftone(im, cell=5), out, src, "newspaper photo: generated 1930s press photo + procedural halftone")
    if want("T_UI_Paper"):
        src = gen("tex_paper", 0); im = Image.open(src).convert("RGB")
        save(im.crop((60, 60, im.width - 60, im.height - 60)).resize((1024, 1024), Image.LANCZOS), "T_UI_Paper", src, "ivory paper")
    if want("T_UI_Newsprint"):
        src = gen("tex_newsprint", 1); im = Image.open(src).convert("RGB")
        save(im.crop((90, 90, im.width - 90, im.height - 90)).resize((1024, 1024), Image.LANCZOS), "T_UI_Newsprint", src, "aged newsprint")
    for out, (name, k) in {"T_UI_IcoHeart": ("ico_heart", 0), "T_UI_IcoPlayers": ("ico_players", 0), "T_UI_IcoGear": ("ico_gear", 1),
                           "T_UI_IcoBook": ("ico_book", 0), "T_UI_IcoDoor": ("ico_door", 0)}.items():
        if want(out):
            ic, src = keyed_icon(name, k)
            save(ic, out, src, "gold icon keyed from black")
    if want("T_UI_Logo"):
        src = os.path.join(GEN, "logo_ideo", "logo_ideo_s401_0.png")
        lg = crop_alpha(key_black(Image.open(src), 0.07, 0.30), pad=0.03, square=False)
        save(with_shadow(lg.resize((1200, int(1200 * lg.height / lg.width)), Image.LANCZOS), 12, 0.8, 28), "T_UI_Logo", src,
             "title logo, Ideogram v4 fp8 (lettering checked letter by letter: 'Le Bal Masqué', acute accent present), keyed from black; Z-Image alternative kept as T_UI_LogoAlt")
    if want("T_UI_LogoAlt"):
        src = os.path.join(GEN, "logo_z", "logo_z_s413_0.png")
        lg = crop_alpha(key_black(Image.open(src), 0.07, 0.30), pad=0.03, square=False)
        save(with_shadow(lg.resize((1200, int(1200 * lg.height / lg.width)), Image.LANCZOS), 12, 0.8, 28), "T_UI_LogoAlt", src,
             "alternative title logo, Z-Image Turbo (LE BAL MASQUÉ checked letter by letter)")
    if want("T_UI_Divider"):
        src = gen("orn_divider", 0)
        d = crop_alpha(key_black(Image.open(src), 0.14, 0.4), pad=0.02, square=False)
        save(d.resize((1024, int(1024 * d.height / d.width)), Image.LANCZOS), "T_UI_Divider", src, "deco divider keyed from black")
    if want("T_UI_Sunburst"):
        src = gen("orn_sunburst", 1)
        d = crop_alpha(key_black(Image.open(src), 0.14, 0.42), pad=0.02, square=False)
        save(d.resize((1024, int(1024 * d.height / d.width)), Image.LANCZOS), "T_UI_Sunburst", src, "deco sunburst fan keyed from black")


# ---------------------------------------------------------------- main
if __name__ == "__main__":
    generated()
    if want("T_UI_Button_Normal"):
        for st in ("normal", "hover", "pressed", "disabled"):
            save(make_button(st), f"T_UI_Button_{st.capitalize()}", notes="procedural PIL (deco chamfered button, 9-slice)")
    if want("T_UI_Field"):
        save(make_field(), "T_UI_Field", notes="procedural PIL (text field, 9-slice)")
    if want("T_UI_SliderBar"):
        b, t = make_slider_parts()
        save(b, "T_UI_SliderBar", notes="procedural PIL"); save(t, "T_UI_SliderThumb", notes="procedural PIL (gold diamond)")
    if want("T_UI_Crosshair"):
        save(make_crosshair(), "T_UI_Crosshair", notes="procedural PIL (deco ring crosshair, ivory + dark halo)")
    if want("T_UI_Dial"):
        dial, hand = make_dial()
        save(dial, "T_UI_Dial", notes="procedural PIL (timer dial)"); save(hand, "T_UI_DialHand", notes="procedural PIL")
    if want("T_UI_Vignette"):
        save(make_vignette(), "T_UI_Vignette", notes="procedural")
    if want("T_UI_Glow"):
        save(make_glow(), "T_UI_Glow", notes="procedural (gold dust mote)")
    if want("T_UI_ArrowR"):
        save(make_arrow(True), "T_UI_ArrowR", notes="procedural chevron"); save(make_arrow(False), "T_UI_ArrowL", notes="procedural chevron")
    if want("T_UI_PanelSmall"):
        save(make_panel_small(), "T_UI_PanelSmall", notes="procedural HUD frame (9-slice margin 0.18)")
    if want("T_UI_ShadeLeft"):
        save(make_shade_left(), "T_UI_ShadeLeft", notes="procedural (left-to-right shade)")
    if want("T_UI_FadeBar"):
        save(make_gradient_bar(), "T_UI_FadeBar", notes="procedural (banner fade)")
    if want("T_UI_Panel"):
        save(make_panel(), "T_UI_Panel", source=gen("orn_corner", 0), notes="procedural frame + generated corner fan (orn_corner_0), 9-slice margin 0.25")
    if want("T_UI_Card"):
        save(make_card_frame(), "T_UI_Card", source=gen("tex_paper", 0) if os.path.isdir(os.path.join(GEN, "tex_paper")) else None,
             notes="generated ivory paper + procedural gold border")
    json.dump(manifest, open(manifest_path, "w", encoding="utf-8"), indent=1, ensure_ascii=False)
