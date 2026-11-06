"""UI art batch through comfy-mcp with Z-Image Turbo (reuses AssetGen/zbatch.build: one run per chunk, all text encodes
first so the 12 GB UNet + 8 GB text encoder are paged in once per chunk).

  python -I -X utf8 uibatch.py JOBS.json [--cands 2] [--chunk 12] [--only a,b]
Outputs: AssetGen/ui/gen/<name>/<name>_s<seed>_<k>.png + .txt sidecar (prompt, seed).
"""
import argparse, json, os, sys, time
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
from assetgen import JOBS, run_and_fetch  # noqa: E402
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "ui"))
from comfyclient import ComfyMCP  # noqa: E402
from zbatch import build  # noqa: E402

GEN = os.path.join(HERE, "gen")


def main():
    p = argparse.ArgumentParser()
    p.add_argument("jobs"); p.add_argument("--cands", type=int, default=2); p.add_argument("--chunk", type=int, default=12)
    p.add_argument("--only", default="")
    a = p.parse_args()
    jobs = json.load(open(a.jobs, encoding="utf-8-sig"))
    if a.only:
        keep = set(a.only.split(",")); jobs = [j for j in jobs if j["name"] in keep]
    os.makedirs(JOBS, exist_ok=True)
    mcp = ComfyMCP()
    try:
        for c in range(0, len(jobs), a.chunk):
            chunk = jobs[c:c + a.chunk]
            wf, saves = build(chunk, a.cands)
            for node in wf.values():  # keep our files apart from the assets agent's
                if node["class_type"] == "SaveImage":
                    node["inputs"]["filename_prefix"] = node["inputs"]["filename_prefix"].replace("gw/", "gw_ui/")
            tag = f"uibatch_{int(time.time())}_{c}"
            job_path = os.path.join(JOBS, tag + ".json")
            json.dump(wf, open(job_path, "w", encoding="utf-8"), indent=1)
            tmp = os.path.join(GEN, "_incoming", tag)
            try:
                pid, secs, files, mapping = run_and_fetch(mcp, job_path, tmp, 900 + 150 * len(chunk))
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
                dst = os.path.join(out_dir, f"{key}_{k}.png")
                os.replace(os.path.join(tmp, local), dst)
                json.dump({"model": "z_image_turbo_bf16", "seed": j["seed"], "batch_index": k, "w": j.get("w", 1024), "h": j.get("h", 1024),
                           "steps": j.get("steps", 8), "prompt": j["prompt"], "prompt_id": pid}, open(dst[:-4] + ".txt", "w", encoding="utf-8"))
            for left in os.listdir(tmp):
                os.remove(os.path.join(tmp, left))
            os.rmdir(tmp)
            print(json.dumps({"ok": True, "seconds": secs, "per_job": round(secs / len(chunk), 1), "jobs": done}), flush=True)
    finally:
        mcp.close()


if __name__ == "__main__":
    main()
