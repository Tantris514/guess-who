"""Many Z-Image Turbo concepts in ONE ComfyUI run (through comfy-mcp), so the 12 GB diffusion model and the
8 GB text encoder are loaded once per chunk instead of once per image (RAM is too tight to keep them cached:
a single-image run costs ~90 s, mostly model paging).

All prompts are encoded first: every KSampler's negative is ConditioningZeroOut(Combine(all prompts)), which
is ignored at cfg 1 but makes every sampler wait for every text encode (no text-encoder/UNet ping-pong).

  python -I -X utf8 zbatch.py JOBS.json [--cands 2] [--chunk 10] [--only name1,name2]
JOBS.json: list of {"name", "prompt", "seed", "w", "h", "steps"?}. Each job yields --cands images (latent batch).
Outputs: concepts/<name>/<name>_s<seed>_<k>.png (+ .txt sidecar with the prompt).
"""
import argparse
import json
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from assetgen import ComfyMCP, JOBS, ROOT, run_and_fetch  # noqa: E402


def build(jobs, cands):
    wf = {
        "1": {"class_type": "UNETLoader", "inputs": {"unet_name": "z_image_turbo_bf16.safetensors", "weight_dtype": "default"}},
        "2": {"class_type": "CLIPLoader", "inputs": {"clip_name": "qwen_3_4b.safetensors", "type": "lumina2", "device": "default"}},
        "3": {"class_type": "VAELoader", "inputs": {"vae_name": "ae.safetensors"}},
        "4": {"class_type": "ModelSamplingAuraFlow", "inputs": {"model": ["1", 0], "shift": 3.0}},
    }
    nid = 10
    texts = []
    for j in jobs:
        wf[str(nid)] = {"class_type": "CLIPTextEncode", "inputs": {"clip": ["2", 0], "text": j["prompt"]}}
        texts.append(str(nid))
        nid += 1
    barrier = texts[0]
    for t in texts[1:]:
        wf[str(nid)] = {"class_type": "ConditioningCombine", "inputs": {"conditioning_1": [barrier, 0], "conditioning_2": [t, 0]}}
        barrier = str(nid)
        nid += 1
    neg = str(nid)
    wf[neg] = {"class_type": "ConditioningZeroOut", "inputs": {"conditioning": [barrier, 0]}}
    nid += 1
    saves = {}
    for j, t in zip(jobs, texts):
        lat, ks, dec, sav = (str(nid + k) for k in range(4))
        nid += 4
        wf[lat] = {"class_type": "EmptySD3LatentImage", "inputs": {"width": int(j.get("w", 1024)), "height": int(j.get("h", 1024)), "batch_size": cands}}
        wf[ks] = {"class_type": "KSampler", "inputs": {"model": ["4", 0], "seed": int(j["seed"]), "steps": int(j.get("steps", 8)), "cfg": 1.0,
                                                        "sampler_name": "res_multistep", "scheduler": "simple", "positive": [t, 0],
                                                        "negative": [neg, 0], "latent_image": [lat, 0], "denoise": 1.0}}
        wf[dec] = {"class_type": "VAEDecode", "inputs": {"samples": [ks, 0], "vae": ["3", 0]}}
        prefix = f"gw/{j['name']}_s{j['seed']}"
        wf[sav] = {"class_type": "SaveImage", "inputs": {"images": [dec, 0], "filename_prefix": prefix}}
        saves[prefix.split("/", 1)[1]] = j
    return wf, saves


def main():
    p = argparse.ArgumentParser()
    p.add_argument("jobs")
    p.add_argument("--cands", type=int, default=2)
    p.add_argument("--chunk", type=int, default=10)
    p.add_argument("--only", default="")
    p.add_argument("--adopt", default="", help="collect an already queued run of exactly these jobs (one chunk)")
    a = p.parse_args()
    with open(a.jobs, encoding="utf-8-sig") as f:
        jobs = json.load(f)
    if a.only:
        keep = set(a.only.split(","))
        jobs = [j for j in jobs if j["name"] in keep]
    os.makedirs(JOBS, exist_ok=True)
    mcp = ComfyMCP()
    try:
        for c in range(0, len(jobs), a.chunk):
            chunk = jobs[c:c + a.chunk]
            wf, saves = build(chunk, a.cands)
            tag = f"zbatch_{int(time.time())}_{c}"
            job_path = os.path.join(JOBS, tag + ".json")
            with open(job_path, "w", encoding="utf-8") as f:
                json.dump(wf, f, indent=1)
            tmp = os.path.join(ROOT, "concepts", "_incoming", tag)
            try:
                pid, secs, files, mapping = run_and_fetch(mcp, job_path, tmp, 600 + 120 * len(chunk), prompt_id=a.adopt or None)
            except Exception as e:
                print(json.dumps({"ok": False, "chunk": [j["name"] for j in chunk], "error": str(e)[:1500]}), flush=True)
                continue
            done = {}
            for local, query in sorted(mapping.items()):
                fname = query.split("filename=")[1].split("&")[0]          # e.g. armchair_club_s11_00001_.png
                key = next((k for k in saves if fname.startswith(k + "_")), None)
                if not key:
                    continue
                j = saves[key]
                out_dir = os.path.join(ROOT, "concepts", j["name"])
                os.makedirs(out_dir, exist_ok=True)
                k = done.get(key, 0)
                done[key] = k + 1
                dst = os.path.join(out_dir, f"{key}_{k}.png")
                os.replace(os.path.join(tmp, local), dst)
                with open(dst[:-4] + ".txt", "w", encoding="utf-8") as f:
                    f.write(json.dumps({"seed": j["seed"], "batch_index": k, "w": j.get("w", 1024), "h": j.get("h", 1024),
                                        "steps": j.get("steps", 8), "prompt": j["prompt"]}))
            for left in os.listdir(tmp):
                os.remove(os.path.join(tmp, left))
            os.rmdir(tmp)
            print(json.dumps({"ok": True, "seconds": secs, "per_job": round(secs / len(chunk), 1),
                              "jobs": {k: v for k, v in done.items()}}), flush=True)
    finally:
        mcp.close()


if __name__ == "__main__":
    main()
