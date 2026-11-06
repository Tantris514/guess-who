"""Recover outputs of a batch whose client died: copy V:/ComfyUI/output/<sub>/<name>_s<seed>_*.<ext> into gen/<name>/ with sidecars.
  collect.py JOBS.json [--sub gw_ui] [--ext png] [--gen DIR] [--model z_image_turbo_bf16]"""
import argparse, glob, json, os, shutil
ap = argparse.ArgumentParser(); ap.add_argument("jobs"); ap.add_argument("--sub", default="gw_ui"); ap.add_argument("--ext", default="png")
ap.add_argument("--gen", default=os.path.join(os.path.dirname(os.path.abspath(__file__)), "gen")); ap.add_argument("--model", default="z_image_turbo_bf16")
a = ap.parse_args()
for j in json.load(open(a.jobs, encoding="utf-8-sig")):
    key = f"{j['name']}_s{j['seed']}"
    src = sorted(glob.glob(os.path.join(r"V:\ComfyUI\output", a.sub, key + "_*." + a.ext)))
    d = os.path.join(a.gen, j["name"]); os.makedirs(d, exist_ok=True)
    for k, f in enumerate(src):
        dst = os.path.join(d, f"{key}_{k}.{a.ext}")
        shutil.copyfile(f, dst)
        json.dump({"model": a.model, "seed": j["seed"], "batch_index": k, "w": j.get("w"), "h": j.get("h"), "steps": j.get("steps", 8),
                   "prompt": j["prompt"], "recovered_from": f}, open(dst[:-len(a.ext) - 1] + ".txt", "w", encoding="utf-8"), ensure_ascii=False)
    print(key, len(src))
