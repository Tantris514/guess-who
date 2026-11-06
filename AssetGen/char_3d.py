"""3D for a generated character: TRELLIS.2 (single front view) or Pixal3D multi-view (pre-framed square views).

  python -I -X utf8 char_3d.py NAME trellis FRONT_IMAGE [--seed 42] [--workflow trellis2_game.json]
  python -I -X utf8 char_3d.py NAME pixal VIEWS_DIR [--seed 42]      (VIEWS_DIR holds front_sq.png [back_sq.png left_sq.png right_sq.png])
Outputs chars/<NAME>/3d_<engine>_s<seed>/: <NAME>.glb, qa_*.png, result.json. One ComfyUI job at a time.
"""
import argparse
import json
import os
import shutil
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ROOT)
import assetgen  # noqa: E402
from assetgen import COMFY_INPUT, JOBS, ComfyMCP, run_and_fetch  # noqa: E402


def collect(out, pid, secs, files, mapping, name, extra):
    keep = {}
    for local, query in mapping.items():
        fname = query.split("filename=")[1].split("&")[0]
        if "subfolder=3d" in query and "type=output" in query and local.endswith(".glb"):
            keep[local] = f"{name}.glb"
        elif "subfolder=qa" in query:
            keep[local] = "qa_" + fname.replace("render_", "").rsplit("_", 2)[0] + ".png"
    for local in files:
        src = os.path.join(out, local)
        if local in keep:
            os.replace(src, os.path.join(out, keep[local]))
        else:
            os.remove(src)
    if not any(v.endswith(".glb") for v in keep.values()):
        raise SystemExit(f"no GLB produced (prompt {pid})")
    json.dump(dict(extra, prompt_id=pid, seconds=secs, files=sorted(keep.values())),
              open(os.path.join(out, "result.json"), "w", encoding="utf-8"), indent=1)
    print(json.dumps({"ok": True, "dir": out, "seconds": secs, "files": sorted(keep.values())}))


def main():
    p = argparse.ArgumentParser()
    p.add_argument("name")
    p.add_argument("engine", choices=["trellis", "pixal"])
    p.add_argument("src")
    p.add_argument("--seed", type=int, default=42)
    p.add_argument("--workflow", default="trellis2_game.json")
    p.add_argument("--faces", type=int, default=60000)
    p.add_argument("--tex", type=int, default=2048)
    p.add_argument("--submit-only", action="store_true")
    p.add_argument("--front", action="store_true", help="with --submit-only: queue at the front (character slice only)")
    a = p.parse_args()
    out = os.path.join(ROOT, "chars", a.name, f"3d_{a.engine}_s{a.seed}")
    mcp = ComfyMCP()
    try:
        if a.engine == "trellis":
            # reuse assetgen.model (TRELLIS game workflow incl. BiRefNet + QA renders), then move its folder
            pid, secs, files = assetgen.model(mcp, a.name, a.src, tex=a.tex, faces=a.faces, seed=a.seed, workflow=a.workflow,
                                              tag="_char")
            src_dir = os.path.join(ROOT, "models3d", f"{a.name}_trellis_s{a.seed}_char")
            if os.path.exists(out):
                shutil.rmtree(out)
            shutil.move(src_dir, out)
            print(json.dumps({"ok": True, "dir": out, "seconds": secs, "files": files}))
            return
        wf = json.load(open(os.path.join(ROOT, "workflows", "pixal3d_mv_game.json"), encoding="utf-8"))
        nodes = {n["id"]: n for n in wf["nodes"]}
        present = {}
        for k, view in enumerate(("front", "left", "back", "right")):
            f = os.path.join(a.src, f"{view}_sq.png")
            if os.path.exists(f):
                fn = f"gw_mv_{a.name}_{view}.png"
                shutil.copyfile(f, os.path.join(COMFY_INPUT, fn))
                nodes[900 + k]["widgets_values"][0] = fn
                present[view] = f
            else:                                   # drop the unused view: node and its link
                lid = nodes[900 + k]["outputs"][0]["links"][0]
                wf["links"] = [l for l in wf["links"] if l[0] != lid]
                for i in nodes[324]["inputs"]:
                    if i.get("link") == lid:
                        i["link"] = None
                wf["nodes"] = [n for n in wf["nodes"] if n["id"] != 900 + k]
        for n in wf["nodes"]:
            if n["id"] in (3, 18, 23):          # structure / shape samplers
                n["widgets_values"][0] = a.seed
            if n["id"] == 186:
                n["widgets_values"][0] = a.faces
            if n["id"] == 288:
                n["widgets_values"][0] = a.tex
            if n["id"] == 372:
                n["widgets_values"][0] = f"3d/gw_{a.name}_pixal"
        job = os.path.join(JOBS, f"char3d_{a.name}_pixal_s{a.seed}.json")
        json.dump(wf, open(job, "w", encoding="utf-8"))
        os.makedirs(out, exist_ok=True)
        if a.submit_only:            # queue it and let char_jobs.py collect fetch the outputs later
            import subprocess
            sys.path.insert(0, ROOT)
            import char_jobs
            # UI -> API with comfy-cli's converter (as comfy-mcp does), then POST /prompt ourselves so that
            # --front (coordinator's character slice :25-:50) can be honoured.
            api_path = job.replace(".json", "_api.json")
            r = subprocess.run([r"V:\ComfyUI\comfy-mcp-env\Scripts\python.exe", "-I", os.path.join(ROOT, "ui2api.py"),
                                job, api_path], capture_output=True, text=True, timeout=300)
            if r.returncode != 0:
                raise SystemExit(f"ui2api failed: {r.stderr[-300:]}")
            api = json.load(open(api_path, encoding="utf-8"))
            body = {"prompt": api, "client_id": "gw-assets-collector"}
            if a.front:
                body["front"] = True
            pid = char_jobs.http_json("/prompt", body)["prompt_id"]
            d = char_jobs.load_pending()
            d[pid] = {"type": "3d", "name": a.name, "engine": "pixal3d_multiview", "out": out, "views": present,
                      "seed": a.seed, "faces": a.faces, "tex": a.tex, "front": a.front, "submitted": __import__("time").time()}
            char_jobs.save_pending(d)
            char_jobs.log(f"submitted {pid} {a.name} 3d pixal s{a.seed}")
            print(pid)
            return
        pid, secs, files, mapping = run_and_fetch(mcp, job, out, 7200)
        collect(out, pid, secs, files, mapping, a.name, {"engine": "pixal3d_multiview", "views": present, "seed": a.seed,
                                                           "faces": a.faces, "tex": a.tex})
    finally:
        mcp.close()


if __name__ == "__main__":
    main()
