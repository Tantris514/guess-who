"""Ideogram v4 (fp8, local) title-lettering batch through comfy-mcp: one API-format run, models loaded once.
Mirrors the official image_ideogram4_t2i template (DualModelGuider with the unconditional model, CFGOverride, Ideogram4Scheduler).

  python -I -X utf8 ideobatch.py JOBS.json [--preset Default|Quality|Turbo]
JOBS.json: list of {"name", "seed", "w", "h", "prompt" (structured JSON caption as a dict or string)}
Outputs: AssetGen/ui/gen/<name>/<name>_s<seed>_0.png + .txt sidecar.
"""
import argparse, json, os, sys, time
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
from assetgen import JOBS, run_and_fetch  # noqa: E402
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "ui"))
from comfyclient import ComfyMCP  # noqa: E402

GEN = os.path.join(HERE, "gen")
PRESETS = {"Quality": (48, 0.0, 1.5), "Default": (20, 0.0, 1.75), "Turbo": (12, 0.5, 1.75)}


def build(jobs, preset):
    steps, mu, std = PRESETS[preset]
    wf = {
        "1": {"class_type": "UNETLoader", "inputs": {"unet_name": "ideogram4_fp8_scaled.safetensors", "weight_dtype": "default"}},
        "2": {"class_type": "UNETLoader", "inputs": {"unet_name": "ideogram4_unconditional_fp8_scaled.safetensors", "weight_dtype": "default"}},
        "3": {"class_type": "CLIPLoader", "inputs": {"clip_name": "qwen3vl_8b_fp8_scaled.safetensors", "type": "ideogram4", "device": "default"}},
        "4": {"class_type": "VAELoader", "inputs": {"vae_name": "flux2-vae.safetensors"}},
        "5": {"class_type": "CFGOverride", "inputs": {"model": ["1", 0], "cfg": 3.0, "start_percent": 0.7, "end_percent": 1.0}},
        "6": {"class_type": "KSamplerSelect", "inputs": {"sampler_name": "euler"}},
    }
    nid = 10
    texts = []
    for j in jobs:
        p = j["prompt"] if isinstance(j["prompt"], str) else json.dumps(j["prompt"], ensure_ascii=False, indent=1)
        wf[str(nid)] = {"class_type": "CLIPTextEncode", "inputs": {"clip": ["3", 0], "text": p}}
        texts.append(str(nid)); nid += 1
    saves = {}
    for j, t in zip(jobs, texts):
        w, h = int(j["w"]) // 16 * 16, int(j["h"]) // 16 * 16
        neg, guid, lat, sch, noise, samp, dec, sav = (str(nid + k) for k in range(8)); nid += 8
        wf[neg] = {"class_type": "ConditioningZeroOut", "inputs": {"conditioning": [t, 0]}}
        wf[guid] = {"class_type": "DualModelGuider", "inputs": {"model": ["5", 0], "positive": [t, 0], "model_negative": ["2", 0],
                                                                 "negative": [neg, 0], "cfg": 7.0}}
        wf[lat] = {"class_type": "EmptyFlux2LatentImage", "inputs": {"width": w, "height": h, "batch_size": 1}}
        wf[sch] = {"class_type": "Ideogram4Scheduler", "inputs": {"steps": steps, "width": w, "height": h, "mu": mu, "std": std}}
        wf[noise] = {"class_type": "RandomNoise", "inputs": {"noise_seed": int(j["seed"])}}
        wf[samp] = {"class_type": "SamplerCustomAdvanced", "inputs": {"noise": [noise, 0], "guider": [guid, 0], "sampler": ["6", 0],
                                                                       "sigmas": [sch, 0], "latent_image": [lat, 0]}}
        wf[dec] = {"class_type": "VAEDecode", "inputs": {"samples": [samp, 0], "vae": ["4", 0]}}
        prefix = f"gw_ui/{j['name']}_s{j['seed']}"
        wf[sav] = {"class_type": "SaveImage", "inputs": {"images": [dec, 0], "filename_prefix": prefix}}
        saves[prefix.split("/", 1)[1]] = j
    return wf, saves


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("jobs"); ap.add_argument("--preset", default="Default"); ap.add_argument("--validate", action="store_true")
    a = ap.parse_args()
    jobs = json.load(open(a.jobs, encoding="utf-8-sig"))
    wf, saves = build(jobs, a.preset)
    os.makedirs(JOBS, exist_ok=True)
    tag = f"ideobatch_{int(time.time())}"
    job_path = os.path.join(JOBS, tag + ".json")
    json.dump(wf, open(job_path, "w", encoding="utf-8"), indent=1, ensure_ascii=False)
    mcp = ComfyMCP()
    try:
        if a.validate:
            print(json.dumps(mcp.call("validate_workflow", workflow_path=job_path))[:1500]); return
        tmp = os.path.join(GEN, "_incoming", tag)
        pid, secs, files, mapping = run_and_fetch(mcp, job_path, tmp, 3600)
        done = {}
        for local, query in sorted(mapping.items()):
            fname = query.split("filename=")[1].split("&")[0]
            key = next((k for k in saves if fname.startswith(k + "_")), None)
            if not key:
                continue
            j = saves[key]
            out_dir = os.path.join(GEN, j["name"]); os.makedirs(out_dir, exist_ok=True)
            k = done.get(key, 0); done[key] = k + 1
            dst = os.path.join(out_dir, f"{key}_{k}.png")
            os.replace(os.path.join(tmp, local), dst)
            json.dump({"model": "ideogram4_fp8_scaled", "preset": a.preset, "seed": j["seed"], "w": j["w"], "h": j["h"],
                       "prompt": j["prompt"], "prompt_id": pid}, open(dst[:-4] + ".txt", "w", encoding="utf-8"), ensure_ascii=False)
        for left in os.listdir(tmp):
            os.remove(os.path.join(tmp, left))
        os.rmdir(tmp)
        print(json.dumps({"ok": True, "seconds": secs, "jobs": done}), flush=True)
    finally:
        mcp.close()


if __name__ == "__main__":
    main()
