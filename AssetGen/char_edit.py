"""Dress a UE mannequin template with Qwen-Image-Edit-2511 (Lightning 4 steps) and gate the pose with BiRefNet masks.

  python -I -X utf8 char_edit.py NAME VIEW TEMPLATE.png "PROMPT" --seeds 1,2,3 [--ref EXTRA.png]
One ComfyUI run (through comfy-mcp): the template (image1) [+ a reference image2] -> N seeds -> each output is cut
out by BiRefNet. Outputs land in chars/<NAME>/<VIEW>/: gen_s<seed>.png (resized to the template size), mask_s<seed>.png,
and gate.json with, per seed: coverage = |gen & tpl| / |tpl| (template mask = luminance > 12), arm coverage (template
pixels farther than 22 cm from the centre column), head-top and hand offsets in px, pass flag.
Needs the ComfyUI venv python for numpy/PIL.
"""
import argparse
import json
import os
import shutil
import sys
import time

import numpy as np
from PIL import Image

ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ROOT)
from assetgen import COMFY_INPUT, JOBS, ComfyMCP, run_and_fetch  # noqa: E402

CM_PER_PX = 140.0 / 1024
ARM_PX = int(round(22.0 / CM_PER_PX))


def tpl_mask(path):
    a = np.asarray(Image.open(path).convert("RGB")).astype(np.float32)
    return a.mean(-1) > 12


def landmarks(m, ref=None):
    """head top row and hand tips. With ref (the template's hands), each hand is searched only in a window around the
    template hand (+-90 px across, up to 90 px below), so a flared coat or gown hem is never taken for a hand."""
    h, w = m.shape
    c = w // 2
    ys, xs = np.where(m[:, c - 60:c + 60])
    head = int(ys.min()) if len(ys) else -1
    hands = {}
    for side, sl in (("left_img", slice(0, c - ARM_PX)), ("right_img", slice(c + ARM_PX, w))):
        sub = np.zeros_like(m)
        sub[:, sl] = m[:, sl]
        # hands = lowest 40 px of the arm region (template hands end at ~57% of the height)
        sub[int(0.62 * h):] = False
        if ref and ref.get(side):
            rx, ry = ref[side]
            win = np.zeros_like(m)
            win[:int(ry) + 90, max(int(rx) - 90, 0):int(rx) + 90] = True
            sub &= win
        ys, xs = np.where(sub)
        if len(ys) == 0:
            hands[side] = None
            continue
        low = ys >= ys.max() - 40
        hands[side] = [float(xs[low].mean()), float(ys[low].mean())]
    return head, hands


def gate(tpl, gen):
    inter = tpl & gen
    cov = inter.sum() / max(tpl.sum(), 1)
    w = tpl.shape[1]
    xx = np.abs(np.arange(w) - w // 2)[None, :] > ARM_PX
    arm_t = tpl & xx
    arm_cov = (inter & xx).sum() / max(arm_t.sum(), 1)
    ht, hh = landmarks(tpl)
    gt, gh = landmarks(gen, hh)
    hand_off = {}
    for k in hh:
        if hh[k] and gh.get(k):
            hand_off[k] = round(float(np.hypot(hh[k][0] - gh[k][0], hh[k][1] - gh[k][1])), 1)
        else:
            hand_off[k] = None
    return {"coverage": round(float(cov), 4), "arm_coverage": round(float(arm_cov), 4),
            "head_top_offset_px": int(gt - ht) if gt >= 0 else None, "hand_offset_px": hand_off,
            "extra_area_ratio": round(float((gen & ~tpl).sum() / max(tpl.sum(), 1)), 3)}


def build(tpl_name, ref_name, prompt, seeds, denoise=None):
    wf = {
        "1": {"class_type": "UNETLoader", "inputs": {"unet_name": "qwen_image_edit_2511_fp8mixed.safetensors", "weight_dtype": "default"}},
        "2": {"class_type": "LoraLoaderModelOnly", "inputs": {"model": ["1", 0], "lora_name": "Qwen-Image-Edit-2511-Lightning-4steps-V1.0-bf16.safetensors", "strength_model": 1.0}},
        "3": {"class_type": "ModelSamplingAuraFlow", "inputs": {"model": ["2", 0], "shift": 3.1}},
        "4": {"class_type": "CFGNorm", "inputs": {"model": ["3", 0], "strength": 1.0}},
        "5": {"class_type": "CLIPLoader", "inputs": {"clip_name": "qwen_2.5_vl_7b_fp8_scaled.safetensors", "type": "qwen_image", "device": "default"}},
        "6": {"class_type": "VAELoader", "inputs": {"vae_name": "qwen_image_vae.safetensors"}},
        "7": {"class_type": "LoadImage", "inputs": {"image": tpl_name}},
        "8": {"class_type": "FluxKontextImageScale", "inputs": {"image": ["7", 0]}},
        "9": {"class_type": "VAEEncode", "inputs": {"pixels": ["8", 0], "vae": ["6", 0]}},
        "20": {"class_type": "LoadBackgroundRemovalModel", "inputs": {"bg_removal_name": "birefnet.safetensors"}},
    }
    pos = {"clip": ["5", 0], "vae": ["6", 0], "image1": ["8", 0], "prompt": prompt}
    neg = {"clip": ["5", 0], "vae": ["6", 0], "image1": ["8", 0], "prompt": ""}
    if ref_name:
        wf["10"] = {"class_type": "LoadImage", "inputs": {"image": ref_name}}
        wf["11"] = {"class_type": "FluxKontextImageScale", "inputs": {"image": ["10", 0]}}
        pos["image2"] = ["11", 0]
        neg["image2"] = ["11", 0]
    wf["12"] = {"class_type": "TextEncodeQwenImageEditPlus", "inputs": pos}
    wf["13"] = {"class_type": "TextEncodeQwenImageEditPlus", "inputs": neg}
    wf["14"] = {"class_type": "FluxKontextMultiReferenceLatentMethod", "inputs": {"conditioning": ["12", 0], "reference_latents_method": "index_timestep_zero"}}
    wf["15"] = {"class_type": "FluxKontextMultiReferenceLatentMethod", "inputs": {"conditioning": ["13", 0], "reference_latents_method": "index_timestep_zero"}}
    nid = 30
    for s in seeds:
        ks, dec, sv, rb, mi, sm = (str(nid + k) for k in range(6))
        nid += 6
        wf[ks] = {"class_type": "KSampler", "inputs": {"model": ["4", 0], "seed": int(s), "steps": 4, "cfg": 1.0, "sampler_name": "euler",
                                                       "scheduler": "simple", "positive": ["14", 0], "negative": ["15", 0],
                                                       "latent_image": ["9", 0], "denoise": (denoise or {}).get(s, 1.0)}}
        wf[dec] = {"class_type": "VAEDecode", "inputs": {"samples": [ks, 0], "vae": ["6", 0]}}
        wf[sv] = {"class_type": "SaveImage", "inputs": {"images": [dec, 0], "filename_prefix": f"gw/char_s{s}_img"}}
        wf[rb] = {"class_type": "RemoveBackground", "inputs": {"bg_removal_model": ["20", 0], "image": [dec, 0]}}
        wf[mi] = {"class_type": "MaskToImage", "inputs": {"mask": [rb, 0]}}
        wf[sm] = {"class_type": "SaveImage", "inputs": {"images": [mi, 0], "filename_prefix": f"gw/char_s{s}_mask"}}
    return wf


def main():
    p = argparse.ArgumentParser()
    p.add_argument("name")
    p.add_argument("view")
    p.add_argument("template")
    p.add_argument("prompt")
    p.add_argument("--seeds", default="1,2,3")
    p.add_argument("--ref", default="")
    p.add_argument("--adopt", default="", help="collect an already submitted prompt_id instead of submitting")
    p.add_argument("--gate-template", default="", help="template for the gate when the edit input is not the template")
    p.add_argument("--tag", default="", help="suffix for output file names (gen_s<seed><tag>.png)")
    p.add_argument("--denoise", default="", help="per-seed denoise, e.g. 23:0.9,24:0.9 (default 1.0)")
    a = p.parse_args()
    seeds = [int(s) for s in a.seeds.split(",")]
    out = os.path.join(ROOT, "chars", a.name, a.view)
    os.makedirs(out, exist_ok=True)
    tpl_in = f"gw_tpl_{os.path.basename(a.template)}"
    Image.open(a.template).convert("RGB").save(os.path.join(COMFY_INPUT, tpl_in))
    ref_in = ""
    if a.ref:
        ref_in = f"gw_ref_{a.name}_{a.view}.png"
        Image.open(a.ref).convert("RGB").save(os.path.join(COMFY_INPUT, ref_in))
    dn = {int(k): float(v) for k, v in (x.split(":") for x in a.denoise.split(",") if x)}
    wf = build(tpl_in, ref_in, a.prompt, seeds, dn)
    job = os.path.join(JOBS, f"char_{a.name}_{a.view}_{int(time.time())}.json")
    json.dump(wf, open(job, "w", encoding="utf-8"), indent=1)
    tmp = os.path.join(out, "_incoming")
    mcp = ComfyMCP()
    try:
        pid, secs, files, mapping = None, 0, [], {}
        for attempt in range(3):            # comfy-mcp's job wait occasionally errors while the job keeps running
            try:
                pid, secs, files, mapping = run_and_fetch(mcp, job, tmp, 14400, prompt_id=a.adopt or pid)
                break
            except RuntimeError as e:
                if "prompt_id" not in str(e) and "Error executing tool job" not in str(e):
                    raise
                if not pid and not a.adopt:
                    raise
                time.sleep(30)
    finally:
        mcp.close()
    gate_tpl = a.gate_template or a.template
    tpl = tpl_mask(gate_tpl)
    H, W = tpl.shape
    results = json.load(open(os.path.join(out, "gate.json"), encoding="utf-8")) if os.path.exists(os.path.join(out, "gate.json")) else {}
    for local, query in mapping.items():
        fname = query.split("filename=")[1].split("&")[0]
        for s in seeds:
            if fname.startswith(f"char_s{s}_img_"):
                Image.open(os.path.join(tmp, local)).convert("RGB").resize((W, H), Image.LANCZOS).save(os.path.join(out, f"gen_s{s}{a.tag}.png"))
            elif fname.startswith(f"char_s{s}_mask_"):
                Image.open(os.path.join(tmp, local)).convert("L").resize((W, H), Image.BILINEAR).save(os.path.join(out, f"mask_s{s}{a.tag}.png"))
    for s in seeds:
        mp = os.path.join(out, f"mask_s{s}{a.tag}.png")
        if not os.path.exists(mp):
            continue
        gen = np.asarray(Image.open(mp)) > 127
        g = gate(tpl, gen)
        g["pass"] = bool(g["coverage"] >= 0.95 and g["arm_coverage"] >= 0.92)
        g["prompt"] = a.prompt
        g["denoise"] = dn.get(s, 1.0)
        g["template"] = gate_tpl
        g["edit_input"] = a.template
        g["ref"] = a.ref
        results[f"s{s}{a.tag}"] = g
        print(json.dumps({"seed": s, **{k: v for k, v in g.items() if k not in ("prompt", "template", "ref")}}))
    json.dump(results, open(os.path.join(out, "gate.json"), "w", encoding="utf-8"), indent=1)
    shutil.rmtree(tmp, ignore_errors=True)
    print("seconds", secs)


if __name__ == "__main__":
    main()
