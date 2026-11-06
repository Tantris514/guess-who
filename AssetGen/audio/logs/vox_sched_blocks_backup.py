"""Fair, non-stop queue feeder for the shared ComfyUI (coordinator rule, 2026-11-02 21:55):
  - plain FIFO submissions only (never front/priority);
  - at most 2 of my jobs in the queue at any time (running + pending): the next small chunk is submitted only when one ends;
  - small chunks (~5-10 min of GPU: 10 TTS lines, 1-2 Stable Audio prompts);
  - each chunk is submitted once; its prompt id is saved before waiting; finished chunks are collected from /history;
    a chunk that vanished (ComfyUI restart) keeps what it saved on disk and only the rest is resubmitted, once.

  python -I -X utf8 vox_sched.py            (runs until the plan is exhausted; re-reads logs/sched_plan.json every loop,
                                            so new job files can be appended while it runs)
Plan: logs/sched_plan.json = [{"name": "...", "kind": "tts"|"sa3", "jobs": "batches/x.json", "chunk": 10}, ...]
State: logs/sched_state.json. Log: logs/sched.log."""
import glob, json, os, sys, time, uuid
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import panic_run as R  # noqa: E402
from planlock import plan_lock  # noqa: E402

PLAN = os.path.join(HERE, "logs", "sched_plan.json")
STATE = os.path.join(HERE, "logs", "sched_state.json")
MAX_MINE = int(os.environ.get("VOX_MAX_MINE", "4"))   # coordinator 22:40: voices first, up to 4 of my jobs


def log(s):
    print(time.strftime("%H:%M:%S"), s, flush=True)


def load(p, default):
    try:
        return json.load(open(p, encoding="utf-8"))
    except Exception:
        return default


def save_state(st):
    json.dump(st, open(STATE + ".tmp", "w", encoding="utf-8"), indent=1)
    os.replace(STATE + ".tmp", STATE)


def chunks_of(entry):
    jobs = json.load(open(os.path.join(HERE, entry["jobs"]), encoding="utf-8-sig"))
    n = entry.get("chunk", 10)
    out = []
    if entry["kind"] == "tts":
        for mode in ("design", "clone"):
            sel = [j for j in jobs if j["mode"] == mode]
            out += [sel[i:i + n] for i in range(0, len(sel), n)]
    else:
        out = [jobs[i:i + n] for i in range(0, len(jobs), n)]
    return out


def my_jobs_in_queue():
    q = R.http("/queue")
    n = 0
    for e in q.get("queue_running", []) + q.get("queue_pending", []):
        pre = [str(v.get("inputs", {}).get("filename_prefix", "")) for v in e[2].values() if v.get("class_type") == "SaveAudio"]
        if pre and all(p.startswith("gw_audio/") for p in pre):
            n += 1
    return n


def build(kind, items):
    if kind == "tts":
        from panic_tts import build as b
    else:
        from audiobatch import build as b
    return b(items)[0]


def collect(kind, files, items, pid):
    return (R.collect_tts if kind == "tts" else R.collect_sa3)(files, items, pid)


def salvage(kind, items, pid):
    if kind != "tts":
        return 0, items
    files = sum((sorted(glob.glob(os.path.join(R.OUTPUT, "gw_audio", "panic", f"{j['key']}_s{j['seed']}_*.flac")))[-1:] for j in items), [])
    n = collect(kind, files, items, pid)
    bases = [os.path.basename(f) for f in files]
    rest = [j for j in items if not any(b.startswith(f"{j['key']}_s{j['seed']}_") for b in bases)]
    return n, rest


BLOCK_N = 6        # chunks per voice block (~40 min of TTS)
PAUSE_MIN = 45     # minutes between blocks (image jobs run)
AUDIO_LOG = r"J:\Projets\Unreal_Projects\Guess Who\Tools\agent_logs\audio.md"


def block_log(msg):
    log(msg)
    with open(AUDIO_LOG, "a", encoding="utf-8") as fh:
        fh.write(f"- {time.strftime('%H:%M')} {msg}\n")


OWN = ["dlg1", "rmk1", "dlg2", "shout1", "dlg3", "event1", "greet1", "nv1"]   # my own list: fills the gaps
SCRIPTS = os.path.join(HERE, "scripts")


def _plan_add(plan, entry, own):
    """Locked append: content batches go before my own gap fillers (plan order = priority)."""
    with plan_lock(PLAN):
        plan[:] = load(PLAN, [])
        if own:
            plan.append(entry)
        else:
            own_pos = [i for i, e in enumerate(plan) if e["name"][4:].split("_r")[0] in OWN]
            plan.insert(own_pos[0] if own_pos else len(plan), entry)
        json.dump(plan, open(PLAN + ".tmp", "w", encoding="utf-8"), indent=1)
        os.replace(PLAN + ".tmp", PLAN)


def auto_extend(st, plan, todo_left, own_left=0):
    """Add the next script batch when the lines lane runs low: content batches (any new AssetGen/audio/scripts/<batch>.py,
    oldest first, once unchanged for 60 s and once 80 % of its lines have their voice references) pre-empt my own list,
    which is only added (one at a time) when no content batch is waiting."""
    import vox
    a = st.setdefault("_auto", {"done": [], "claimed": None, "noref": {}})
    if todo_left >= 3:
        return False
    if a.get("claimed") is None:
        a["claimed"] = {n: f for n, f in vox.old_texts().items()}
    now = time.time()
    ext = sorted((p for p in glob.glob(os.path.join(SCRIPTS, "*.py")) if not os.path.basename(p).startswith("_")
                  and os.path.splitext(os.path.basename(p))[0] not in OWN), key=os.path.getmtime)
    cands = [os.path.splitext(os.path.basename(p))[0] for p in ext if now - os.path.getmtime(p) > 60]
    if own_left < 3:
        cands += OWN
    r = vox.refs()
    for b in cands:
        if b in a["done"] or not os.path.exists(os.path.join(SCRIPTS, b + ".py")):
            continue
        try:
            its = vox.load_script(b)
            ready = sum(1 for it in its if vox.ref_for(r, it["voice"], it["reg"].split(":")[-1])[1] or it["reg"].startswith("design:"))
            if ready < 0.8 * len(its):
                if not isinstance(a.get("waiting"), dict):
                    a["waiting"] = {}
                if a["waiting"].get(b) != ready:
                    log(f"auto: {b} waits for its voice references ({ready}/{len(its)} ready)")
                    a.setdefault("waiting", {})[b] = ready
                continue
            out, keys = vox.jobs(b, claimed=a["claimed"])
        except Exception as e:   # a script being written, or a bug on my side: log it and retry later, never skip it
            log(f"auto: batch {b} not usable yet: {e}"); continue
        a["noref"][b] = [it["key"] for it in its if it["key"] not in keys and vox.norm(it["text"]) in a["claimed"]
                         and a["claimed"][vox.norm(it["text"])] == it["key"]]
        a["done"].append(b)
        _plan_add(plan, {"name": f"vox_{b}", "kind": "tts", "jobs": os.path.relpath(out, HERE).replace("\\", "/"), "chunk": 30}, b in OWN)
        save_state(st)
        log(f"auto: added batch {b} ({len(keys)} lines, {len(a['noref'][b])} waiting for a reference)")
        return True
    # nothing new: lines that were waiting for a voice reference (every 5 min at most)
    if now - a.get("noref_t", 0) < 300:
        return False
    a["noref_t"] = now
    for b, keys in list(a["noref"].items()):
        if not keys:
            continue
        n = len([p for p in plan if p["name"].startswith("vox_" + b + "_r")]) + 1
        out, got = vox.jobs(b, only_keys=set(keys), out=os.path.join(HERE, "batches", f"vox_{b}_r{n}.json"))
        if got:
            a["noref"][b] = [k for k in keys if k not in got]
            _plan_add(plan, {"name": os.path.splitext(os.path.basename(out))[0], "kind": "tts",
                             "jobs": os.path.relpath(out, HERE).replace("\\", "/"), "chunk": 30}, b in OWN)
            save_state(st)
            log(f"auto: {b}: {len(got)} more lines now have their voice reference")
            return True
    return False


def main():
    st = load(STATE, {})
    idle_since = None
    while True:
        plan = load(PLAN, [])
        todo = []
        for entry in plan:
            try:
                chs = chunks_of(entry)
            except Exception as e:
                log(f"plan entry {entry.get('name')}: {e}"); continue
            for i, items in enumerate(chs):
                cid = f"{entry['name']}#{i}"
                s = st.get(cid, {})
                if not isinstance(s, dict):
                    continue
                if s.get("status") in ("done", "failed"):
                    continue
                todo.append((cid, entry["kind"], s.get("items") or items))
        # poll in-flight chunks
        for cid, kind, items in todo:
            s = st.get(cid)
            if not s or s.get("status") != "queued":
                continue
            try:
                h = R.http(f"/history/{s['pid']}")
            except Exception as e:
                log(f"history error {e}"); continue
            if s["pid"] in h:
                ent = h[s["pid"]]
                stt = ent.get("status", {}).get("status_str")
                if stt == "success":
                    n = collect(kind, R.outputs(ent), items, s["pid"])
                    s.update(status="done", files=n, done_at=time.strftime("%H:%M:%S"))
                    log(f"done {cid}: {n}/{len(items)} files ({round((time.time() - s['t']) / 60, 1)} min after submit)")
                else:
                    msgs = [m for m in ent.get("status", {}).get("messages", []) if m[0] == "execution_error"]
                    err = msgs[0][1].get("exception_message", "")[:200] if msgs else stt
                    n, rest = salvage(kind, items, s["pid"])
                    if s.get("retried") or not rest:
                        s.update(status="done" if not rest else "failed", error=err)
                    else:
                        s.update(status="pending", items=rest, retried=True, error=err)
                    log(f"error {cid}: {err}; salvaged {n}, {len(rest)} left")
                save_state(st)
            else:
                try:
                    q = R.http("/queue")
                except Exception:
                    continue
                if not any(e[1] == s["pid"] for e in q.get("queue_running", []) + q.get("queue_pending", [])):
                    time.sleep(5)
                    if s["pid"] in R.http(f"/history/{s['pid']}"):
                        continue
                    n, rest = salvage(kind, items, s["pid"])
                    s.update(status="pending" if rest else "done", items=rest or None, lost=s.get("lost", 0) + 1)
                    log(f"lost {cid} (not queued, no history): salvaged {n}, {len(rest)} to resubmit")
                    save_state(st)
        try:
            lane = {e["name"]: e.get("lane", "lines") for e in plan}
            pend = [c for c, _, _ in todo if (st.get(c) or {}).get("status") != "queued" and lane.get(c.split("#")[0], "lines") == "lines"]
            own_left = sum(1 for c in pend if c.split("#")[0][4:].split("_r")[0] in OWN)
            if auto_extend(st, plan, len(pend) - own_left, own_left):
                continue
        except Exception as e:
            log(f"auto_extend error: {e}")
        # VOICE BLOCKS (coordinator 23:15): up to BLOCK_N consecutive TTS chunks submitted with front=true, one running + one
        # waiting, so TTS runs back to back without a model swap; then a PAUSE_MIN pause during which at most 2 normal FIFO
        # jobs of mine stay queued, so the image jobs run. front only ever applies to my own next chunk.
        try:
            mine = my_jobs_in_queue()
        except Exception as e:
            log(f"comfy down? {e}"); time.sleep(30); continue
        lane_of = {e["name"]: e.get("lane", "lines") for e in plan}
        queued = [c for c, _, _ in todo if (st.get(c) or {}).get("status") == "queued"]
        queued_lanes = [lane_of.get(c.split("#")[0], "lines") for c in queued]
        def lane_rank(t):
            return queued_lanes.count(lane_of.get(t[0].split("#")[0], "lines"))
        cands = [t for t in todo if (st.get(t[0]) or {}).get("status") not in ("queued", "done", "failed")]
        cands.sort(key=lambda t: (lane_rank(t), todo.index(t)))
        B = st.setdefault("_block", {"mode": "block", "n": 0, "since": time.time(), "pause_until": 0})
        front_q = [c for c in queued if st[c].get("front")]
        normal_q = [c for c in queued if not st[c].get("front")]
        now = time.time()
        if B["mode"] == "block" and B["n"] >= BLOCK_N and not front_q:
            B.update(mode="pause", pause_until=now + PAUSE_MIN * 60)
            block_log(f"voice block end: {BLOCK_N} chunks since {time.strftime('%H:%M', time.localtime(B['since']))}; "
                      f"pause until {time.strftime('%H:%M', time.localtime(B['pause_until']))}")
            save_state(st)
        if B["mode"] == "pause" and now >= B["pause_until"]:
            B.update(mode="block", n=0, since=now)
            block_log("voice block start")
            save_state(st)
        to_submit = []
        if B["mode"] == "block":
            tts = [t for t in cands if t[1] == "tts"]
            k = min(2 - len(front_q), BLOCK_N - B["n"])
            to_submit = [(t, True) for t in tts[:max(0, k)]]
        if len(normal_q) < 2 and B["mode"] == "pause":
            rest = [t for t in cands if t not in [x for x, _ in to_submit]]
            to_submit += [(t, False) for t in rest[:2 - len(normal_q)]]
        for (cid, kind, items), front in to_submit:
            s = st.get(cid, {})
            if s.get("status") in ("queued", "done", "failed"):   # status may have changed while polling above
                continue
            items = s.get("items") or items
            wf = build(kind, items)
            body = {"prompt": wf, "client_id": "gw-vox-" + uuid.uuid4().hex[:8]}
            if front:
                body["front"] = True
            r = R.http("/prompt", body)
            st[cid] = dict(s, status="queued", pid=r["prompt_id"], t=time.time(), items=items, n=len(items), front=front)
            if front:
                B["n"] += 1
            save_state(st)
            log(f"submitted {cid} ({len(items)} items) -> {r['prompt_id'][:8]}{' FRONT (block chunk %d/%d)' % (B['n'], BLOCK_N) if front else ''}")
        if not any((st.get(c) or {}).get("status") in ("queued", None, "pending") for c, _, _ in todo):
            idle_since = idle_since or time.time()
            if time.time() - idle_since > 60:
                log("plan exhausted: idle (append to the plan to continue)")
                idle_since = time.time() + 1e9
        else:
            idle_since = None
        time.sleep(20)


if __name__ == "__main__":
    main()
