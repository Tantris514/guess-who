"""Upscale finished 2D images to ~4096 px with SeedVR2 3B (one ComfyUI run through comfy-mcp), tile by tile.

The image is first Lanczos-resized to the target size on the CPU, cut into overlapping tiles of about 2 MP, each
tile is restored by SeedVR2 at 1x (one step, LAB colour correction against the input tile), and the tiles are
stitched back with feathered overlaps. Tiles keep VRAM low on the 12 GB card (no full 11 MP DiT pass).

  python -I -X utf8 seedvr_tiles.py NAME[:LONG_SIDE] ...      (reads paintings/final/<NAME>.png, writes <NAME>_4k.png)
Needs the ComfyUI venv python for numpy/PIL: run with V:/ComfyUI/ComfyUI/ComfyUI/.venv/Scripts/python.exe -I.
"""
import json
import os
import sys
import time

import numpy as np
from PIL import Image

ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ROOT)
from assetgen import COMFY_INPUT, JOBS, ComfyMCP, run_and_fetch  # noqa: E402

FINAL = os.path.join(ROOT, "paintings", "final")
TILE = 1408       # tile edge in output pixels (multiple of 32)
OVER = 192        # overlap between tiles


def tile_boxes(w, h):
    def starts(n):
        if n <= TILE:
            return [0]
        k = int(np.ceil((n - OVER) / (TILE - OVER)))
        step = (n - TILE) / (k - 1)
        return [int(round(i * step)) for i in range(k)]
    return [(x, y, min(x + TILE, w), min(y + TILE, h)) for y in starts(h) for x in starts(w)]


def main():
    jobs = []
    args = sys.argv[1:]
    adopt = None
    if "--adopt" in args:                      # collect an already finished/queued run of the same inputs
        k = args.index("--adopt")
        adopt = args[k + 1]
        args = args[:k] + args[k + 2:]
    for arg in args:
        name, _, long_side = arg.partition(":")
        long_side = int(long_side or 4096)
        src = Image.open(os.path.join(FINAL, f"{name}.png")).convert("RGB")
        s = long_side / max(src.size)
        size = (int(round(src.width * s / 16)) * 16, int(round(src.height * s / 16)) * 16)
        big = src.resize(size, Image.LANCZOS)
        boxes = tile_boxes(*size)
        for i, box in enumerate(boxes):
            fn = f"gw_sv_{name}_{i}.png"
            if not adopt:
                big.crop(box).save(os.path.join(COMFY_INPUT, fn))
            jobs.append({"name": name, "i": i, "box": box, "file": fn, "size": size})
    wf = {
        "1": {"class_type": "UNETLoader", "inputs": {"unet_name": "seedvr2_3b_int8_convrot.safetensors", "weight_dtype": "default"}},
        "2": {"class_type": "VAELoader", "inputs": {"vae_name": "seedvr2_ema_vae_fp16.safetensors"}},
    }
    nid = 10
    prefixes = {}
    for j in jobs:
        ids = [str(nid + k) for k in range(8)]
        nid += 8
        load, pre, enc, cond, ks, dec, post, save = ids
        wf[load] = {"class_type": "LoadImage", "inputs": {"image": j["file"]}}
        wf[pre] = {"class_type": "SeedVR2Preprocess", "inputs": {"resized_images": [load, 0]}}
        wf[enc] = {"class_type": "VAEEncodeTiled", "inputs": {"pixels": [pre, 0], "vae": ["2", 0], "tile_size": 512, "overlap": 128,
                                                              "temporal_size": 4096, "temporal_overlap": 8}}
        wf[cond] = {"class_type": "SeedVR2Conditioning", "inputs": {"model": ["1", 0], "vae_conditioning": [enc, 0]}}
        wf[ks] = {"class_type": "KSampler", "inputs": {"model": ["1", 0], "seed": 42, "steps": 1, "cfg": 1.0, "sampler_name": "euler",
                                                       "scheduler": "simple", "positive": [cond, 0], "negative": [cond, 1],
                                                       "latent_image": [enc, 0], "denoise": 1.0}}
        wf[dec] = {"class_type": "VAEDecodeTiled", "inputs": {"samples": [ks, 0], "vae": ["2", 0], "tile_size": 512, "overlap": 128,
                                                              "temporal_size": 4096, "temporal_overlap": 8}}
        wf[post] = {"class_type": "SeedVR2PostProcessing", "inputs": {"images": [dec, 0], "original_resized_images": [load, 0],
                                                                      "color_correction_method": "lab"}}
        prefix = f"sv_{j['name']}_t{j['i']}"
        wf[save] = {"class_type": "SaveImage", "inputs": {"images": [post, 0], "filename_prefix": f"gw/{prefix}"}}
        prefixes[prefix] = j
    os.makedirs(JOBS, exist_ok=True)
    job_path = os.path.join(JOBS, f"seedvr_{int(time.time())}.json")
    with open(job_path, "w", encoding="utf-8") as f:
        json.dump(wf, f, indent=1)
    tmp = os.path.join(ROOT, "paintings", "_incoming_sv")
    mcp = ComfyMCP()
    try:
        pid, secs, files, mapping = run_and_fetch(mcp, job_path, tmp, 3600, prompt_id=adopt)
    finally:
        mcp.close()
    tiles = {}
    for local, query in mapping.items():
        fname = query.split("filename=")[1].split("&")[0]
        key = next((k for k in prefixes if fname.startswith(k + "_")), None)
        if key:
            tiles[key] = Image.open(os.path.join(tmp, local)).convert("RGB")
    by_name = {}
    for key, j in prefixes.items():
        by_name.setdefault(j["name"], []).append((j, tiles.get(key)))
    for name, parts in by_name.items():
        w, h = parts[0][0]["size"]
        acc = np.zeros((h, w, 3), np.float64)
        wsum = np.zeros((h, w, 1), np.float64)
        for j, im in parts:
            if im is None:
                raise SystemExit(f"missing tile {j['i']} of {name}")
            x0, y0, x1, y1 = j["box"]
            a = np.asarray(im.resize((x1 - x0, y1 - y0), Image.LANCZOS), np.float64)
            # feather weight: ramps over OVER px at inner edges, flat 1 at the image border
            wy = np.ones(y1 - y0)
            wx = np.ones(x1 - x0)
            ramp = np.linspace(0.0, 1.0, OVER + 2)[1:-1]
            if y0 > 0:
                wy[:OVER] = ramp
            if y1 < h:
                wy[-OVER:] = ramp[::-1]
            if x0 > 0:
                wx[:OVER] = ramp
            if x1 < w:
                wx[-OVER:] = ramp[::-1]
            wgt = np.outer(wy, wx)[..., None]
            acc[y0:y1, x0:x1] += a * wgt
            wsum[y0:y1, x0:x1] += wgt
        out = Image.fromarray(np.clip(acc / np.maximum(wsum, 1e-6) + 0.5, 0, 255).astype(np.uint8))
        dst = os.path.join(FINAL, f"{name}_4k.png")
        out.save(dst)
        print(json.dumps({"name": name, "size": out.size, "tiles": len(parts), "seconds": secs, "file": dst}), flush=True)
    for fn in os.listdir(tmp):
        os.remove(os.path.join(tmp, fn))
    os.rmdir(tmp)


if __name__ == "__main__":
    main()
