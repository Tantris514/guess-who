"""Music / SFX batch through comfy-mcp with Stable Audio 3 Medium (one API-format run per chunk: the checkpoint and the
T5Gemma encoder are loaded once). Prompts are written by hand (the template's Qwen reprompt step is skipped).

  python -I -X utf8 audiobatch.py JOBS.json [--chunk 12] [--only a,b]
JOBS.json: list of {"name", "prompt", "seconds", "seed", "cands"?, "steps"?, "cfg"?}
Outputs: AssetGen/audio/gen/<name>/<name>_s<seed>_<k>.flac + .txt sidecar (prompt, seed).
"""
import argparse, json, os, sys, time
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
from assetgen import JOBS, run_and_fetch  # noqa: E402
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "ui"))
from comfyclient import ComfyMCP  # noqa: E402

GEN = os.path.join(HERE, "gen")


def build(jobs):
    wf = {
        "1": {"class_type": "CheckpointLoaderSimple", "inputs": {"ckpt_name": "stable_audio_3_medium.safetensors"}},
        "2": {"class_type": "CLIPLoader", "inputs": {"clip_name": "t5gemma_b_b_ul2.safetensors", "type": "stable_audio", "device": "default"}},
        "3": {"class_type": "CLIPTextEncode", "inputs": {"clip": ["2", 0], "text": ""}},
    }
    nid = 10
    saves = {}
    for j in jobs:
        pos, lat, ks, dec, sav = (str(nid + k) for k in range(5))
        nid += 5
        wf[pos] = {"class_type": "CLIPTextEncode", "inputs": {"clip": ["2", 0], "text": j["prompt"]}}
        wf[lat] = {"class_type": "EmptyLatentAudio", "inputs": {"seconds": float(j["seconds"]), "batch_size": int(j.get("cands", 2))}}
        wf[ks] = {"class_type": "KSampler", "inputs": {"model": ["1", 0], "seed": int(j["seed"]), "steps": int(j.get("steps", 8)),
                                                        "cfg": float(j.get("cfg", 1.0)), "sampler_name": "lcm", "scheduler": "simple",
                                                        "positive": [pos, 0], "negative": ["3", 0], "latent_image": [lat, 0], "denoise": 1.0}}
        wf[dec] = {"class_type": "VAEDecodeAudio", "inputs": {"samples": [ks, 0], "vae": ["1", 2]}}
        prefix = f"gw_audio/{j['name']}_s{j['seed']}"
        wf[sav] = {"class_type": "SaveAudio", "inputs": {"audio": [dec, 0], "filename_prefix": prefix}}
        saves[prefix.split("/", 1)[1]] = j
    return wf, saves


def main():
    p = argparse.ArgumentParser()
    p.add_argument("jobs"); p.add_argument("--chunk", type=int, default=12); p.add_argument("--only", default="")
    a = p.parse_args()
    jobs = json.load(open(a.jobs, encoding="utf-8-sig"))
    if a.only:
        keep = set(a.only.split(",")); jobs = [j for j in jobs if j["name"] in keep]
    os.makedirs(JOBS, exist_ok=True)
    mcp = ComfyMCP()
    try:
        for c in range(0, len(jobs), a.chunk):
            chunk = jobs[c:c + a.chunk]
            wf, saves = build(chunk)
            tag = f"audiobatch_{int(time.time())}_{c}"
            job_path = os.path.join(JOBS, tag + ".json")
            json.dump(wf, open(job_path, "w", encoding="utf-8"), indent=1)
            tmp = os.path.join(GEN, "_incoming", tag)
            try:
                pid, secs, files, mapping = run_and_fetch(mcp, job_path, tmp, 1800 + 120 * len(chunk))
            except Exception as e:
                print(json.dumps({"ok": False, "chunk": [j["name"] for j in chunk], "error": str(e)[:1500]}), flush=True)
                continue
            done = {}
            for local, query in sorted(mapping.items()):
                fname = query.split("filename=")[1].split("&")[0]
                key = next((k for k in saves if fname.startswith(k + "_")), None)
                if not key:
                    continue
                j = saves[key]
                out_dir = os.path.join(GEN, j["name"]); os.makedirs(out_dir, exist_ok=True)
                k = done.get(key, 0); done[key] = k + 1
                ext = os.path.splitext(local)[1]
                dst = os.path.join(out_dir, f"{key}_{k}{ext}")
                os.replace(os.path.join(tmp, local), dst)
                json.dump({"model": "stable_audio_3_medium", "seed": j["seed"], "batch_index": k, "seconds": j["seconds"],
                           "steps": j.get("steps", 8), "cfg": j.get("cfg", 1.0), "prompt": j["prompt"], "prompt_id": pid},
                          open(os.path.splitext(dst)[0] + ".txt", "w", encoding="utf-8"))
            for left in os.listdir(tmp):
                os.remove(os.path.join(tmp, left))
            os.rmdir(tmp)
            print(json.dumps({"ok": True, "seconds": secs, "jobs": done}), flush=True)
    finally:
        mcp.close()


if __name__ == "__main__":
    main()
