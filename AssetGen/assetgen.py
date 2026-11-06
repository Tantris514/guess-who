"""Asset generation through the ComfyUI MCP (comfy-mcp) for the GuessWho project.

Every step goes through comfy-mcp tools: set_workflow_slot, run_workflow, job, fetch_outputs.

  python -I -X utf8 assetgen.py concept NAME "PROMPT" [--seed N] [--w 1024] [--h 1024] [--steps 8]
  python -I -X utf8 assetgen.py model NAME IMAGE [--engine trellis|pixal] [--tex 2048] [--faces 200000] [--seed N]
  python -I -X utf8 assetgen.py batch JOBS.json      (list of {"kind": "concept"|"model", ...same keys})
"""
import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import threading
import time

ROOT = os.path.dirname(os.path.abspath(__file__))
WF = os.path.join(ROOT, "workflows")
JOBS = os.path.join(WF, "jobs")
COMFY_INPUT = r"V:\ComfyUI\input"
EXE = r"V:\ComfyUI\comfy-mcp-env\Scripts\comfy-mcp.exe"
COMFY_BIN = r"V:\ComfyUI\comfy-mcp-env\Scripts\comfy.exe"


class ComfyMCP:
    def __init__(self):
        env = dict(os.environ, COMFY_BIN=COMFY_BIN)
        self.proc = subprocess.Popen([EXE], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                     env=env, text=True, encoding="utf-8", errors="replace", bufsize=1)
        threading.Thread(target=lambda: [None for _ in self.proc.stderr], daemon=True).start()
        self.msg_id = 0
        self._rpc("initialize", {"protocolVersion": "2025-06-18", "capabilities": {},
                                 "clientInfo": {"name": "gw-assetgen", "version": "1"}})
        self._send({"jsonrpc": "2.0", "method": "notifications/initialized"})

    def _send(self, msg):
        self.proc.stdin.write(json.dumps(msg) + "\n")
        self.proc.stdin.flush()

    def _rpc(self, method, params):
        self.msg_id += 1
        self._send({"jsonrpc": "2.0", "id": self.msg_id, "method": method, "params": params})
        while True:
            line = self.proc.stdout.readline()
            if not line:
                raise RuntimeError("comfy-mcp closed its stdout")
            resp = json.loads(line)
            if resp.get("id") == self.msg_id:
                return resp

    def call(self, tool, **args):
        resp = self._rpc("tools/call", {"name": tool, "arguments": args})
        result = resp.get("result") or {}
        text = "\n".join(c.get("text", "") for c in result.get("content", []) if c.get("type") == "text")
        if resp.get("error") or result.get("isError"):
            raise RuntimeError(f"{tool} failed: {resp.get('error') or text[:2000]}")
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            return text

    def close(self):
        self.proc.stdin.close()
        self.proc.terminate()


def find_key(obj, key):
    """Depth-first search for the first value of `key` in nested dicts/lists."""
    if isinstance(obj, dict):
        if key in obj:
            return obj[key]
        for v in obj.values():
            found = find_key(v, key)
            if found is not None:
                return found
    elif isinstance(obj, list):
        for v in obj:
            found = find_key(v, key)
            if found is not None:
                return found
    elif isinstance(obj, str):
        m = re.search(rf'"{key}"\s*:\s*"([^"]+)"', obj)
        if m:
            return m.group(1)
    return None


def submit_front(job_path):
    """POST job_path to /prompt with front=true (UI-format jobs go through ui2api.py first, as comfy-mcp does)."""
    import urllib.request
    wf = json.load(open(job_path, encoding="utf-8"))
    if "nodes" in wf:
        api_path = job_path.replace(".json", "_api.json")
        r = subprocess.run([r"V:\ComfyUI\comfy-mcp-env\Scripts\python.exe", "-I", os.path.join(ROOT, "ui2api.py"),
                            job_path, api_path], capture_output=True, text=True, timeout=300)
        if r.returncode != 0:
            raise RuntimeError(f"ui2api failed: {r.stderr[-300:]}")
        wf = json.load(open(api_path, encoding="utf-8"))
    body = json.dumps({"prompt": wf, "front": True, "client_id": "gw-cast3"}).encode()
    req = urllib.request.Request("http://127.0.0.1:8188/prompt", data=body, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read().decode("utf-8"))["prompt_id"]


def run_and_fetch(mcp, job_path, out_dir, timeout, prompt_id=None):
    """Submit job_path (or adopt an already submitted prompt_id), wait, fetch its outputs into out_dir.
    Env: GW_FRONT=1 queues it at the front (only inside the coordinator's slice for the caller's kind of job);
    GW_MIN_WAIT_S raises the wait (a FIFO job can sit behind other producers' jobs for hours)."""
    started = time.time()
    timeout = max(float(timeout), float(os.environ.get("GW_MIN_WAIT_S", 0)))
    if not prompt_id and os.environ.get("GW_FRONT") == "1":
        prompt_id = submit_front(job_path)
    if not prompt_id:
        submitted = mcp.call("run_workflow", workflow_path=job_path, wait=False)
        prompt_id = find_key(submitted, "prompt_id")
    if not prompt_id:
        raise RuntimeError(f"no prompt_id in run_workflow result: {str(submitted)[:800]}")
    # comfy-mcp's "job wait" sometimes errors while a job is still queued behind other agents' jobs: poll instead
    deadline = time.time() + float(timeout)
    while True:
        try:
            status = mcp.call("job", action="wait", prompt_id=prompt_id, timeout_seconds=min(600.0, max(30.0, deadline - time.time())))
        except RuntimeError:
            status = {"timed_out": True}
            time.sleep(20)
        if not (isinstance(status, dict) and status.get("timed_out")):
            break
        try:
            st = mcp.call("job", action="status", prompt_id=prompt_id)
            if isinstance(st, dict) and st.get("status") in ("completed", "success", "failed", "error"):
                break
        except RuntimeError:
            pass
        if time.time() > deadline:
            raise RuntimeError(f"job {prompt_id} timed out after {timeout}s")
    err = mcp.call("job", action="error", prompt_id=prompt_id)
    if isinstance(err, dict) and err.get("error"):
        raise RuntimeError(f"job {prompt_id} failed: {json.dumps(err['error'])[:1500]}")
    os.makedirs(out_dir, exist_ok=True)
    before = set(os.listdir(out_dir))
    mcp.call("fetch_outputs", prompt_id=prompt_id, out_dir=out_dir)
    files = sorted(set(os.listdir(out_dir)) - before)
    # fetch_outputs names files <prompt_id[:8]>_<index in the job's outputs list>.<ext>; keep the source URLs
    # so callers can tell which fetched file came from which node (e.g. the Save3DAdvanced GLB).
    status = mcp.call("job", action="status", prompt_id=prompt_id)
    urls = status.get("outputs", []) if isinstance(status, dict) else []
    mapping = {}
    for i, url in enumerate(urls):
        ext = os.path.splitext(url.split("filename=")[1].split("&")[0])[1]
        local = f"{prompt_id[:8]}_{i:03d}{ext}"
        if local in files:
            mapping[local] = url.split("?", 1)[1]
    return prompt_id, round(time.time() - started, 1), files, mapping


def prepare_job(template, job_name):
    os.makedirs(JOBS, exist_ok=True)
    job_path = os.path.join(JOBS, f"{job_name}.json")
    shutil.copyfile(os.path.join(WF, template), job_path)
    return job_path


def concept(mcp, name, prompt, seed=1, w=1024, h=1024, steps=8, **_):
    job = prepare_job("zimage_template.json", f"concept_{name}_{seed}")
    mcp.call("set_workflow_slot", workflow_path=job, stdout=False, overrides=[
        {"address": "57.text", "value": prompt},
        {"address": "57.seed", "value": int(seed)},
        {"address": "57.width", "value": int(w)},
        {"address": "57.height", "value": int(h)},
        {"address": "57.steps", "value": int(steps)},
        {"address": "9.filename_prefix", "value": f"gw/{name}_{seed}"},
    ])
    out = os.path.join(ROOT, "concepts", name)
    pid, secs, files, _ = run_and_fetch(mcp, job, out, 900)
    for fn in files:  # remember which seed/prompt produced which file
        with open(os.path.join(out, fn[:-4] + ".txt"), "w", encoding="utf-8") as f:
            f.write(json.dumps({"seed": seed, "w": w, "h": h, "steps": steps, "prompt": prompt}))
    return pid, secs, files


def model(mcp, name, image, engine="trellis", tex=2048, faces=200000, seed=42, upsample=1024, tag="", adopt="",
          submit_only=False, workflow="trellis2_game.json", **_):
    os.makedirs(COMFY_INPUT, exist_ok=True)
    input_name = f"gw_{name}.png"
    if not adopt:
        shutil.copyfile(image, os.path.join(COMFY_INPUT, input_name))
    job = prepare_job(workflow, f"model_{name}_{engine}")
    # Values the slot API does not expose are edited in the frontend JSON directly.
    with open(job, encoding="utf-8") as f:
        wf = json.load(f)
    for node in wf["nodes"]:
        if node["id"] == 186:            # DecimateMesh: target face count
            node["widgets_values"][0] = int(faces)
        elif node["id"] == 322:          # Save3DAdvanced: output prefix
            node["widgets_values"][0] = f"3d/gw_{name}_{engine}"
        elif node["id"] == 122:          # LoadImage
            node["widgets_values"][0] = input_name
        elif node["id"] == 18:           # first (512) shape pass: also seeded (it is the only pass in the 512 workflow)
            node["widgets_values"][0] = int(seed)
        elif node["id"] == 94:           # Trellis2UpsampleStage: target resolution (1024 fast, 1536 sharper)
            node["widgets_values"][0] = int(upsample)
    with open(job, "w", encoding="utf-8") as f:
        json.dump(wf, f)
    mcp.call("set_workflow_slot", workflow_path=job, stdout=False, overrides=[
        {"address": "316.value", "value": engine == "trellis"},
        {"address": "288.value", "value": int(tex)},
        {"address": "23.seed", "value": int(seed)},
    ])
    if submit_only:   # queue it now, collect later with adopt=<prompt_id>
        submitted = mcp.call("run_workflow", workflow_path=job, wait=False)
        return find_key(submitted, "prompt_id")
    out = os.path.join(ROOT, "models3d", f"{name}_{engine}_s{seed}{tag}")
    pid, secs, files, mapping = run_and_fetch(mcp, job, out, 7200, prompt_id=adopt or None)
    # Keep only what matters, under stable names: the textured final GLB (Save3DAdvanced, subfolder 3d)
    # and the QA renders (subfolder qa). Drop the intermediate texture previews.
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
        raise RuntimeError(f"no GLB produced (prompt {pid}); check ComfyUI log (OOM on dense meshes: lower upsample)")
    with open(os.path.join(out, "result.json"), "w", encoding="utf-8") as f:
        json.dump({"prompt_id": pid, "seconds": secs, "image": image, "seed": seed, "tex": tex, "faces": faces, "upsample": upsample,
                   "workflow": workflow,
                   "files": sorted(keep.values())}, f, indent=1)
    return pid, secs, sorted(keep.values())


def main():
    p = argparse.ArgumentParser()
    p.add_argument("kind", choices=["concept", "model", "batch"])
    p.add_argument("name")
    p.add_argument("arg", nargs="?")
    p.add_argument("--seed", type=int, default=1)
    p.add_argument("--w", type=int, default=1024)
    p.add_argument("--h", type=int, default=1024)
    p.add_argument("--steps", type=int, default=8)
    p.add_argument("--engine", default="trellis")
    p.add_argument("--tex", type=int, default=2048)
    p.add_argument("--faces", type=int, default=200000)
    p.add_argument("--ahead", type=int, default=1, help="batch: queue this many model jobs at once")
    a = p.parse_args()

    mcp = ComfyMCP()
    try:
        if a.kind == "batch":
            with open(a.name, encoding="utf-8-sig") as f:
                jobs = json.load(f)
        elif a.kind == "concept":
            jobs = [dict(kind="concept", name=a.name, prompt=a.arg, seed=a.seed, w=a.w, h=a.h, steps=a.steps)]
        else:
            jobs = [dict(kind="model", name=a.name, image=a.arg, engine=a.engine, tex=a.tex, faces=a.faces, seed=a.seed)]
        i = 0
        while i < len(jobs):
            group = jobs[i:i + a.ahead] if jobs[i]["kind"] == "model" else jobs[i:i + 1]
            group = [j for j in group if j["kind"] == group[0]["kind"]]
            i += len(group)
            if len(group) > 1:
                for j in group:
                    if not j.get("adopt"):
                        try:
                            j["adopt"] = model(mcp, submit_only=True, **j)
                        except Exception as e:
                            j["error"] = str(e)
            for j in group:
                fn = concept if j["kind"] == "concept" else model
                try:
                    if j.get("error"):
                        raise RuntimeError(j["error"])
                    pid, secs, files = fn(mcp, **{k: v for k, v in j.items() if k != "error"})
                    print(json.dumps({"ok": True, "name": j["name"], "kind": j["kind"], "seconds": secs, "files": files}), flush=True)
                except Exception as e:  # keep going through a batch
                    print(json.dumps({"ok": False, "name": j["name"], "kind": j["kind"], "error": str(e)[:1500]}), flush=True)
    finally:
        mcp.close()


if __name__ == "__main__":
    main()
