"""Light-weight character edit jobs: a short-lived submitter and ONE long-lived collector (no comfy-mcp per job).

  python -I char_jobs.py submit NAME VIEW EDIT_INPUT.png PROMPT_FILE --seeds a,b --denoise a:0.8 \
        [--gate-template TPL.png] [--tag _x] [--ref REF.png]
      builds the Qwen-Image-Edit workflow (char_edit.build), copies the inputs to ComfyUI's input folder, POST /prompt,
      records the prompt_id in chars/pending.json and exits.
  python -I char_jobs.py collect [--once]
      polls /history/<prompt_id> for every pending job; when one is done, downloads its images (/view), writes
      chars/<name>/<view>/gen_s<seed><tag>.png + mask_s<seed><tag>.png, gates them (char_edit.gate) into gate.json,
      appends a line to logs/collector.log and removes the job from pending.json. Loops every 30 s.
  python -I char_jobs.py status
Run with the ComfyUI venv python (numpy/PIL).
"""
import json
import os
import shutil
import sys
import time
import urllib.parse
import urllib.request

import numpy as np
from PIL import Image

ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ROOT)
import char_edit  # noqa: E402

SERVER = "http://127.0.0.1:8188"
COMFY_INPUT = r"V:\ComfyUI\input"
PENDING = os.path.join(ROOT, "chars", "pending.json")
LOG = os.path.join(ROOT, "logs", "collector.log")


def http_json(path, data=None, timeout=60):
    req = urllib.request.Request(SERVER + path, data=json.dumps(data).encode() if data is not None else None,
                                 headers={"Content-Type": "application/json"} if data is not None else {})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode("utf-8"))


def load_pending():
    if not os.path.exists(PENDING):
        return {}
    d = json.load(open(PENDING, encoding="utf-8"))
    d.pop("_doc", None)
    return d


def save_pending(d):
    d = dict(d)
    d["_doc"] = "My queued ComfyUI character edit jobs (prompt_id -> how to post-process). Collected by char_jobs.py collect."
    tmp = PENDING + ".tmp"
    json.dump(d, open(tmp, "w", encoding="utf-8"), indent=1)
    os.replace(tmp, PENDING)


def log(msg):
    line = time.strftime("%H:%M:%S ") + msg
    print(line, flush=True)
    with open(LOG, "a", encoding="utf-8") as f:
        f.write(line + "\n")


def submit(args):
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument("name")
    p.add_argument("view")
    p.add_argument("edit_input")
    p.add_argument("prompt_file")
    p.add_argument("--seeds", required=True)
    p.add_argument("--denoise", default="")
    p.add_argument("--gate-template", default="")
    p.add_argument("--tag", default="")
    p.add_argument("--ref", default="")
    p.add_argument("--front", action="store_true")
    a = p.parse_args(args)
    seeds = [int(s) for s in a.seeds.split(",")]
    dn = {int(k): float(v) for k, v in (x.split(":") for x in a.denoise.split(",") if x)}
    prompt = open(os.path.join(ROOT, a.prompt_file), encoding="utf-8").read().strip()
    if a.view == "back" and a.ref and not prompt.startswith("Image 1"):
        import char_prompts as cp
        prompt = cp.BACK.format(desc=prompt)
    stamp = f"{a.name}_{a.view}{a.tag}_{seeds[0]}"
    tpl_in = f"gw_in_{stamp}.png"
    Image.open(os.path.join(ROOT, a.edit_input)).convert("RGB").save(os.path.join(COMFY_INPUT, tpl_in))
    ref_in = ""
    if a.ref:
        ref_in = f"gw_ref_{stamp}.png"
        Image.open(os.path.join(ROOT, a.ref)).convert("RGB").save(os.path.join(COMFY_INPUT, ref_in))
    wf = char_edit.build(tpl_in, ref_in, prompt, seeds, dn)
    # unique output prefixes per job (other sessions use the same seeds)
    for v in wf.values():
        if v.get("class_type") == "SaveImage":
            v["inputs"]["filename_prefix"] = v["inputs"]["filename_prefix"].replace("gw/char_", f"gw/{a.name}{a.tag}_{a.view}_")
    body = {"prompt": wf, "client_id": "gw-assets-collector"}
    if a.front:
        body["front"] = True
    r = http_json("/prompt", body)
    pid = r["prompt_id"]
    d = load_pending()
    d[pid] = {"name": a.name, "view": a.view, "tag": a.tag, "seeds": seeds,
              "gate_template": a.gate_template or a.edit_input, "edit_input": a.edit_input, "ref": a.ref,
              "denoise": {str(k): v for k, v in dn.items()}, "prompt_file": a.prompt_file, "front": a.front,
              "submitted": time.time()}
    save_pending(d)
    log(f"submitted {pid} {a.name} {a.view}{a.tag} seeds {a.seeds}" + (" FRONT" if a.front else ""))
    print(pid)


def fetch(fn, sub, typ):
    q = urllib.parse.urlencode({"filename": fn, "subfolder": sub, "type": typ})
    with urllib.request.urlopen(f"{SERVER}/view?{q}", timeout=120) as r:
        return r.read()


def process(pid, job, hist):
    import io
    out = os.path.join(ROOT, "chars", job["name"], job["view"])
    os.makedirs(out, exist_ok=True)
    tpl = char_edit.tpl_mask(os.path.join(ROOT, job["gate_template"]))
    H, W = tpl.shape
    files = []
    for node_out in hist.get("outputs", {}).values():
        for im in node_out.get("images", []):
            files.append(im)
    tag = job.get("tag", "")
    for im in files:
        fn = im["filename"]
        for s in job["seeds"]:
            kind = None
            if f"s{s}_img_" in fn:
                kind = "gen"
            elif f"s{s}_mask_" in fn:
                kind = "mask"
            if not kind:
                continue
            data = Image.open(io.BytesIO(fetch(fn, im.get("subfolder", ""), im.get("type", "output"))))
            if kind == "gen":
                data.convert("RGB").resize((W, H), Image.LANCZOS).save(os.path.join(out, f"gen_s{s}{tag}.png"))
            else:
                data.convert("L").resize((W, H), Image.BILINEAR).save(os.path.join(out, f"mask_s{s}{tag}.png"))
    gp = os.path.join(out, "gate.json")
    G = json.load(open(gp, encoding="utf-8")) if os.path.exists(gp) else {}
    lines = []
    for s in job["seeds"]:
        mp = os.path.join(out, f"mask_s{s}{tag}.png")
        if not os.path.exists(mp):
            lines.append(f"s{s}{tag}: missing")
            continue
        g = char_edit.gate(tpl, np.asarray(Image.open(mp)) > 127)
        g["pass"] = bool(g["coverage"] >= 0.95 and g["arm_coverage"] >= 0.92)
        g["denoise"] = job.get("denoise", {}).get(str(s), 1.0)
        g["template"] = job["gate_template"]
        g["edit_input"] = job["edit_input"]
        g["ref"] = job.get("ref", "")
        g["prompt_file"] = job.get("prompt_file", "")
        g["prompt_id"] = pid
        G[f"s{s}{tag}"] = g
        lines.append(f"s{s}{tag}: {g['coverage']}/{g['arm_coverage']} head {g['head_top_offset_px']} hands {g['hand_offset_px']}")
    json.dump(G, open(gp, "w", encoding="utf-8"), indent=1)
    log(f"collected {pid[:8]} {job['name']} {job['view']}{tag}: " + " | ".join(lines))


def process3d(pid, job, hist):
    out = job["out"]
    os.makedirs(out, exist_ok=True)
    got = []
    for node_out in hist.get("outputs", {}).values():
        for key in ("3d", "images", "result"):
            for it in node_out.get(key, []) if isinstance(node_out.get(key), list) else []:
                if not isinstance(it, dict) or "filename" not in it:
                    continue
                fn, sub, typ = it["filename"], it.get("subfolder", ""), it.get("type", "output")
                if typ != "output":
                    continue
                if fn.endswith(".glb") and sub.startswith("3d"):
                    dst = os.path.join(out, f"{job['name']}.glb")
                elif sub.startswith("qa") and fn.endswith(".png"):
                    dst = os.path.join(out, "qa_" + fn.replace("render_", "").rsplit("_", 2)[0] + ".png")
                else:
                    continue
                with open(dst, "wb") as f:
                    f.write(fetch(fn, sub, typ))
                got.append(os.path.basename(dst))
    json.dump({"prompt_id": pid, "engine": job.get("engine"), "views": job.get("views"), "seed": job.get("seed"),
               "faces": job.get("faces"), "tex": job.get("tex"), "files": sorted(got),
               "seconds_since_submit": round(time.time() - job.get("submitted", time.time()))},
              open(os.path.join(out, "result.json"), "w", encoding="utf-8"), indent=1)
    log(f"collected {pid[:8]} {job['name']} 3d -> {out} {sorted(got)}")


def collect(once=False):
    while True:
        d = load_pending()
        for pid, job in list(d.items()):
            try:
                h = http_json(f"/history/{pid}", timeout=30)
            except Exception as e:  # noqa: BLE001  server busy: try later
                log(f"history {pid[:8]} unavailable: {str(e)[:80]}")
                break
            if pid not in h:
                continue                                   # still queued or running
            hist = h[pid]
            status = hist.get("status", {}).get("status_str")
            try:
                if status == "success" and job.get("type") == "3d":
                    process3d(pid, job, hist)
                elif status == "success":
                    process(pid, job, hist)
                    LAST_EDIT_DONE[0] = time.time()
                else:
                    log(f"job {pid[:8]} {job['name']} {job.get('view', '3d')} ended with status {status}")
                d = load_pending()
                d.pop(pid, None)
                save_pending(d)
                with open(os.path.join(ROOT, "chars", "done.jsonl"), "a", encoding="utf-8") as f:
                    f.write(json.dumps({"prompt_id": pid, "status": status, **job}) + "\n")
            except Exception as e:  # noqa: BLE001
                log(f"processing {pid[:8]} failed: {e}")
        feed()
        if once:
            return
        t = time.localtime()
        time.sleep(15 if 29 <= t.tm_min < 52 else 30)


TODO = os.path.join(ROOT, "chars", "todo.json")
MAX_PENDING = 3          # coordinator: at most 3 of my jobs in the shared queue (voices have priority)


# Coordinator GPU rule v4 (2026-11-03 03:25): every clock hour VOICES :00-:30, CHARACTERS :30-:52, PROPS :52-:00.
# Submit only inside our slice, front=true, ONE job at a time, only if estimate + 5 min margin ends before :52.
# No new FIFO submissions outside the slice (queued ones drain); filler: queue completely empty -> one job <= 8 min.
SLICE = (30 * 60, 52 * 60)        # seconds within the hour
FILLER_MAX = 480
EST_3D = 300                      # Pixal3D 2 views: ran 145 s (02:30), keep a margin for model loads
EST_LOAD = 300                    # Qwen-Image-Edit load (03:23 waiter job: 850 s for 4 seeds = ~260 s load + 4 x 147 s)
EST_SEED_FRONT = 160              # 147 s per seed measured with Qwen loaded (03:38, 03:43)
EST_SEED_REF = 170                # 2-seed back with reference ran 558 s incl. the load (04:35)
MARGIN = 300                      # coordinator's 5 min margin (also covers the job already running); front jobs
                                  # are LIFO in ComfyUI (number = -counter), so only the running job is ahead of ours


def _read_todo():
    return json.load(open(TODO, encoding="utf-8")) if os.path.exists(TODO) else []


def _write_todo(todo):
    tmp = TODO + ".tmp"
    json.dump(todo, open(tmp, "w", encoding="utf-8"), indent=1)
    os.replace(tmp, TODO)


LAST_EDIT_DONE = [0.0]            # time my last Qwen edit finished (set by collect)


def estimate(item):
    if item["cmd"] == "3d":
        return EST_3D
    args = item["args"]
    n = len(args[args.index("--seeds") + 1].split(","))
    # Qwen still loaded when my previous edit finished inside this same slice (< 10 min ago): no reload
    load = 90 if time.time() - LAST_EDIT_DONE[0] < 600 else EST_LOAD
    return load + n * (EST_SEED_REF if "--ref" in args else EST_SEED_FRONT)


def _with_seeds(item, seeds):
    args = list(item["args"])
    args[args.index("--seeds") + 1] = ",".join(seeds)
    return {"cmd": item["cmd"], "args": args}


def run_item(item, front=False):
    import subprocess
    try:
        if item["cmd"] == "submit":
            submit(item["args"] + (["--front"] if front else []))
        elif item["cmd"] == "3d":
            r = subprocess.run([sys.executable, "-I", "-X", "utf8", os.path.join(ROOT, "char_3d.py")] + item["args"]
                               + ["--submit-only"] + (["--front"] if front else []),
                               capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=900)
            if r.returncode != 0:
                log(f"3d submit failed: {r.stderr[-300:]}")
    except Exception as e:  # noqa: BLE001
        log(f"feed failed for {item}: {e}")


def feed_front(remaining):
    """Character slice: one front job at a time, split into fewer seeds when needed so it ends before :52."""
    if any(j.get("front") for j in load_pending().values()):
        return
    # alternate with the Character Creator session (shared slice, coordinator 10:44): while one of its front jobs
    # (negative queue number, not ours) is waiting, let it go first
    try:
        mine = set(load_pending())
        q = http_json("/queue", timeout=30)
        if any(it[0] < 0 and it[1] not in mine for it in q["queue_pending"]):
            return
    except Exception:  # noqa: BLE001
        return
    todo = _read_todo()
    if not todo:
        return
    item = todo[0]
    budget = remaining - MARGIN
    rest = None
    if item["cmd"] == "submit":
        seeds = item["args"][item["args"].index("--seeds") + 1].split(",")
        k = len(seeds)
        while k > 1 and estimate(_with_seeds(item, seeds[:k])) > budget:
            k -= 1
        if k < len(seeds):
            rest = _with_seeds(item, seeds[k:])
            item = _with_seeds(item, seeds[:k])
    if estimate(item) > budget:
        # the head does not fit before :52: use the slice tail for the first short 3D job that does fit
        k3 = next((k for k, x in enumerate(todo) if x["cmd"] == "3d" and estimate(x) <= budget), None)
        if k3 is None:
            return
        item = todo[k3]
        todo = todo[:k3] + todo[k3 + 1:]
        _write_todo(todo)
        log(f"slice: front job {item['args'][0]} 3d (tail of slice, est {estimate(item)} s, {remaining} s left)")
        run_item(item, front=True)
        return
    todo = todo[1:] if rest is None else [rest] + todo[1:]
    _write_todo(todo)
    log(f"slice: front job {item['args'][0]} {item['args'][1]} (est {estimate(item)} s, {remaining} s left)")
    run_item(item, front=True)


def feed():
    """GPU rule v4: submit only inside the character slice (front, one at a time, see feed_front). Outside it no new
    submissions, except the filler: when the ComfyUI queue is completely empty, one short job (<= FILLER_MAX s) as FIFO.
    Jobs already queued as FIFO just drain."""
    t = time.localtime()
    s = t.tm_min * 60 + t.tm_sec
    if SLICE[0] <= s < SLICE[1]:
        feed_front(SLICE[1] - s)
        return
    try:
        q = http_json("/queue", timeout=30)
    except Exception:  # noqa: BLE001
        return
    if q["queue_running"] or q["queue_pending"]:
        return
    todo = _read_todo()
    for k, item in enumerate(todo):
        if estimate(item) <= FILLER_MAX:
            _write_todo(todo[:k] + todo[k + 1:])
            log(f"filler: queue empty, FIFO job {item['args'][0]} {item['args'][1]} (est {estimate(item)} s)")
            run_item(item)
            return


def status():
    d = load_pending()
    try:
        q = http_json("/queue", timeout=30)
        order = [it[1] for it in q["queue_running"]] + [it[1] for it in q["queue_pending"]]
    except Exception:  # noqa: BLE001
        order = []
    for pid, job in d.items():
        pos = order.index(pid) if pid in order else "?"
        print(pid[:8], job["name"], job.get("view", "3d") + job.get("tag", ""), "FRONT" if job.get("front") else "", "queue position", pos)


if __name__ == "__main__":
    cmd = sys.argv[1]
    if cmd == "submit":
        submit(sys.argv[2:])
    elif cmd == "collect":
        collect("--once" in sys.argv)
    else:
        status()
