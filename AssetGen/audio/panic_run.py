"""Queue-safe runner for the panic/event audio jobs (replaces the retry loop of panic_tts.py, which resubmitted chunks when
comfy-mcp's 'job wait' errored on a long queue and so duplicated jobs in the shared ComfyUI queue).

Rules: each chunk is submitted ONCE (POST /prompt) and its prompt_id is written to a state file BEFORE waiting; waiting is
GET /history/<id> + GET /queue polling; a restart adopts the recorded ids instead of resubmitting. A chunk is resubmitted
only if ComfyUI reports it failed (history status 'error') AND it is no longer queued, at most --max-retries times.
Outputs are copied from V:/ComfyUI/output (the files the history lists). One chunk is in the queue at a time.

  python -I -X utf8 panic_run.py tts JOBS.json [--chunk 30] [--adopt CHUNK=PROMPT_ID ...]
  python -I -X utf8 panic_run.py sa3 JOBS.json [--chunk 6]  [--adopt CHUNK=PROMPT_ID ...]
State: logs/<jobs name>.state.json"""
import argparse, json, os, shutil, sys, time, urllib.request, uuid
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
URL = "http://127.0.0.1:8188"
OUTPUT = r"V:\ComfyUI\output"
GEN = os.path.join(HERE, "gen")


def http(path, data=None):
    req = urllib.request.Request(URL + path, data=json.dumps(data).encode() if data is not None else None,
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read().decode() or "{}")


def in_queue(pid):
    q = http("/queue")
    return any(e[1] == pid for e in q.get("queue_running", []) + q.get("queue_pending", []))


def wait(pid, poll=20, log=print):
    """Block until pid is in /history. Returns the history entry. Never resubmits."""
    t0 = time.time(); last = 0
    while True:
        try:
            h = http(f"/history/{pid}")
            if pid in h:
                return h[pid]
            if not in_queue(pid):
                time.sleep(5)   # the history write can lag the queue by a moment
                h = http(f"/history/{pid}")
                if pid in h:
                    return h[pid]
                return {"status": {"status_str": "missing"}}
        except Exception as e:  # ComfyUI busy / transient: keep polling, never resubmit
            log(json.dumps({"poll_error": str(e)[:200]}))
        if time.time() - last > 600:
            log(json.dumps({"waiting": pid, "minutes": round((time.time() - t0) / 60, 1)})); last = time.time()
        time.sleep(poll)


def in_queue_wait(poll=30):
    """Block until ComfyUI answers again (never restarts it). Returns True once it is reachable."""
    while True:
        try:
            http("/queue"); return True
        except Exception:
            time.sleep(poll)


def outputs(entry):
    files = []
    for node in entry.get("outputs", {}).values():
        for k in ("audio", "images"):
            for f in node.get(k, []) or []:
                files.append(os.path.join(OUTPUT, f.get("subfolder", ""), f["filename"]))
    return files


def collect_tts(files, items, pid):
    by = {}
    for j in items:
        by[f"{j['key']}_s{j['seed']}"] = j
    n = 0
    for src in files:
        b = os.path.basename(src)
        key = next((k for k in by if b.startswith(k + "_")), None)
        if not key or not os.path.exists(src):
            continue
        j = by[key]
        d = os.path.join(GEN, j["group"]); os.makedirs(d, exist_ok=True)
        dst = os.path.join(d, f"{key}_0{os.path.splitext(src)[1]}")
        shutil.copyfile(src, dst)
        side = {"model": "Qwen3-TTS-12Hz-1.7B-" + ("VoiceDesign" if j["mode"] == "design" else "Base (voice clone)"),
                "mode": j["mode"], "seed": j["seed"], "text": j["text"], "prompt": j["text"], "language": "French",
                "temperature": j.get("temperature", 0.8), "top_p": j.get("top_p", 0.8), "batch_index": 0, "prompt_id": pid}
        for k in ("instruct", "ref", "ref_text", "meta"):
            if k in j:
                side[k] = j[k]
        json.dump(side, open(os.path.splitext(dst)[0] + ".txt", "w", encoding="utf-8"), ensure_ascii=False)
        n += 1
    return n


def collect_sa3(files, items, pid):
    by = {f"{j['name']}_s{j['seed']}": j for j in items}
    done, n = {}, 0
    for src in sorted(files):
        b = os.path.basename(src)
        key = next((k for k in by if b.startswith(k + "_")), None)
        if not key or not os.path.exists(src):
            continue
        j = by[key]
        d = os.path.join(GEN, j["name"]); os.makedirs(d, exist_ok=True)
        k = done.get(key, 0); done[key] = k + 1
        dst = os.path.join(d, f"{key}_{k}{os.path.splitext(src)[1]}")
        shutil.copyfile(src, dst)
        json.dump({"model": "stable_audio_3_medium", "seed": j["seed"], "batch_index": k, "seconds": j["seconds"], "steps": j.get("steps", 8),
                   "cfg": j.get("cfg", 1.0), "prompt": j["prompt"], "prompt_id": pid}, open(os.path.splitext(dst)[0] + ".txt", "w", encoding="utf-8"))
        n += 1
    return n


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("kind", choices=["tts", "sa3"]); ap.add_argument("jobs"); ap.add_argument("--chunk", type=int, default=30)
    ap.add_argument("--adopt", nargs="*", default=[]); ap.add_argument("--max-retries", type=int, default=2)
    ap.add_argument("--all-at-once", action="store_true")
    a = ap.parse_args()
    jobs = json.load(open(a.jobs, encoding="utf-8-sig"))
    name = os.path.splitext(os.path.basename(a.jobs))[0]
    state_p = os.path.join(HERE, "logs", name + ".state.json")
    state = json.load(open(state_p)) if os.path.exists(state_p) else {"chunks": {}, "done": [], "retries": {}}
    for ad in a.adopt:
        c, pid = ad.split("="); state["chunks"][c] = pid
    save = lambda: json.dump(state, open(state_p, "w"), indent=1)  # noqa: E731
    save()
    log = lambda s: print(s, flush=True)  # noqa: E731
    if a.kind == "tts":
        from panic_tts import build
        chunks = []
        for mode in ("design", "clone"):
            sel = [j for j in jobs if j["mode"] == mode]
            chunks += [sel[c:c + a.chunk] for c in range(0, len(sel), a.chunk)]
        collect = collect_tts
    else:
        from audiobatch import build
        chunks = [jobs[c:c + a.chunk] for c in range(0, len(jobs), a.chunk)]
        collect = collect_sa3
    if a.all_at_once:   # queue every remaining chunk back to back (one model family stays loaded), each exactly once
        for ci, chunk in enumerate(chunks):
            c = str(ci)
            if c in state["done"] or state["chunks"].get(c):
                continue
            wf = build(chunk)[0]
            r = http("/prompt", {"prompt": wf, "client_id": "gw-panic-" + uuid.uuid4().hex[:8]})
            state["chunks"][c] = r["prompt_id"]; save()
            log(json.dumps({"submitted": c, "prompt_id": r["prompt_id"], "items": len(chunk)}))
    for ci, chunk in enumerate(chunks):
        c = str(ci)
        if c in state["done"]:
            continue
        while True:
            pid = state["chunks"].get(c)
            if not pid:
                wf = build(chunk)[0]
                r = http("/prompt", {"prompt": wf, "client_id": "gw-panic-" + uuid.uuid4().hex[:8]})
                pid = r["prompt_id"]
                state["chunks"][c] = pid; save()
                log(json.dumps({"submitted": c, "prompt_id": pid, "items": len(chunk)}))
            t0 = time.time()
            entry = wait(pid, log=log)
            st = entry.get("status", {}).get("status_str")
            if st == "success":
                n = collect(outputs(entry), chunk, pid)
                state["done"].append(c); save()
                log(json.dumps({"ok": True, "chunk": ci, "prompt_id": pid, "files": n, "of": len(chunk), "waited_s": round(time.time() - t0)}))
                break
            if st == "missing" and a.kind == "tts":
                # the job vanished (ComfyUI went down): keep what it already saved, resubmit only the rest (once)
                import glob as _g
                files = sum((sorted(_g.glob(os.path.join(OUTPUT, "gw_audio", "panic", f"{j['key']}_s{j['seed']}_*.flac")))[-1:]
                             for j in chunk), [])
                n = collect(files, chunk, pid)
                bases = [os.path.basename(f) for f in files]
                rest = [j for j in chunk if not any(b.startswith(f"{j['key']}_s{j['seed']}_") for b in bases)]
                log(json.dumps({"salvaged": n, "chunk": ci, "remaining": len(rest)}))
                if not rest:
                    state["done"].append(c); save(); break
                chunk = rest
                state["chunks"].pop(c, None); save()
                if in_queue_wait():
                    continue
            msgs = [m for m in entry.get("status", {}).get("messages", []) if m[0] == "execution_error"]
            err = msgs[0][1].get("exception_message", "")[:300] if msgs else st
            log(json.dumps({"ok": False, "chunk": ci, "prompt_id": pid, "status": st, "error": err}))
            r = state["retries"].get(c, 0)
            if r >= a.max_retries or in_queue(pid):
                log(json.dumps({"giving_up": ci})); break
            state["retries"][c] = r + 1; state["chunks"].pop(c, None); save()
            time.sleep(180)   # failed (e.g. out of VRAM): wait before ONE fresh submission
    log("ALL DONE")


if __name__ == "__main__":
    main()
