"""Night feeder for the props pipeline, following the coordinator's GPU rule v4 (2026-11-03 03:27):
  - each clock hour: VOICES :00-:30, CHARACTERS :30-:52, PROPS :52-:00;
  - props submit only in their slice, front=true, one job at a time, ending before :00 (submitted :52-:55; TRELLIS
    2-4 min); a front job of mine still pending outside :52-:56 is taken back out of the queue (my own entry only);
  - no FIFO submissions, except one short filler job when the queue is completely empty (nothing running/pending).
A front TRELLIS job is submitted through comfy-mcp like any other, then its API prompt is copied from /queue, my
pending entry deleted and re-posted with front=true (no other job is touched). Polls every 15 s.

Work comes from JSONL files in AssetGen/batches/ (one job per line, appended by hand after reviews), in this order:
  feed_models.jsonl    TRELLIS jobs of approved concepts, same dicts as make_models.py output
  feed_priority.jsonl  concept retries etc., same formats
  feed_concepts.jsonl  {"kind": "concepts", "file": "batches/<chunk>.json", "cands": 3}   (Z-Image chunk, few prompts)
Submission uses the pipeline's own code (assetgen.model(submit_only=True), zbatch.build + comfy-mcp run_workflow);
collection runs the pipeline's own tools with --adopt (zbatch.py ... --adopt PID, assetgen.py batch with "adopt").
Never resubmits a job that is still queued; a job that vanished (ComfyUI restart) is resubmitted once.
State: AssetGen/logs/props_feeder_state.json ; events: AssetGen/logs/props_feeder.log

  python -I -X utf8 props_feeder.py [--slots 2] [--until "2026-11-03 11:00"]
"""
import argparse
import datetime
import json
import os
import subprocess
import sys
import time
import urllib.request

AG = r"J:\Projets\Unreal_Projects\Guess Who\AssetGen"
sys.path.insert(0, AG)
from assetgen import JOBS, ComfyMCP, find_key, model  # noqa: E402
from zbatch import build  # noqa: E402

STATE = os.path.join(AG, "logs", "props_feeder_state.json")
LOG = os.path.join(AG, "logs", "props_feeder.log")
FEEDS = [os.path.join(AG, "batches", f) for f in ("feed_priority.jsonl", "feed_models.jsonl", "feed_concepts.jsonl")]


def log(**kw):
    kw = {"t": time.strftime("%H:%M:%S"), **kw}
    with open(LOG, "a", encoding="utf-8") as f:
        f.write(json.dumps(kw, ensure_ascii=False) + "\n")


def http(path):
    return json.load(urllib.request.urlopen("http://127.0.0.1:8188" + path, timeout=20))


def load_state():
    if os.path.exists(STATE):
        return json.load(open(STATE, encoding="utf-8"))
    return {"taken": {os.path.basename(f): 0 for f in FEEDS}, "inflight": []}


def save_state(st):
    tmp = STATE + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(st, f, indent=1)
    os.replace(tmp, STATE)


def feed_lines(path):
    if not os.path.exists(path):
        return []
    with open(path, encoding="utf-8") as f:
        return [json.loads(x) for x in f if x.strip()]


def post(path, payload):
    req = urllib.request.Request("http://127.0.0.1:8188" + path, data=json.dumps(payload).encode("utf-8"),
                                 headers={"Content-Type": "application/json"}, method="POST")
    with urllib.request.urlopen(req, timeout=60) as r:
        body = r.read()
    return json.loads(body) if body else {}


def to_front(pid):
    """Move MY just-submitted FIFO job to the front: copy its API prompt from /queue, delete my pending entry,
    re-post it with front=true. Returns the new prompt id (or the old one if it is already running)."""
    q = http("/queue")
    if any(r[1] == pid for r in q["queue_running"]):
        return pid
    entry = next((r for r in q["queue_pending"] if r[1] == pid), None)
    if not entry:
        raise RuntimeError(f"{pid} not pending, cannot move it to the front")
    post("/queue", {"delete": [pid]})
    if any(r[1] == pid for r in http("/queue")["queue_pending"]):
        raise RuntimeError(f"could not remove {pid} from the queue")
    extra = entry[3] if len(entry) > 3 and isinstance(entry[3], dict) else {}
    res = post("/prompt", {"prompt": entry[2], "front": True, "extra_data": extra,
                           **({"client_id": extra["client_id"]} if extra.get("client_id") else {})})
    return res["prompt_id"]


def submit(mcp, item, front=False):
    if item["kind"] == "concepts":
        jobs = json.load(open(os.path.join(AG, item["file"]), encoding="utf-8-sig"))
        wf, _ = build(jobs, int(item.get("cands", 3)))
        if front:   # API format already: post it directly at the front
            return post("/prompt", {"prompt": wf, "front": True, "client_id": "gw-props-feeder"})["prompt_id"]
        os.makedirs(JOBS, exist_ok=True)
        path = os.path.join(JOBS, f"zbatch_{int(time.time())}_feed.json")
        with open(path, "w", encoding="utf-8") as f:
            json.dump(wf, f, indent=1)
        res = mcp.call("run_workflow", workflow_path=path, wait=False)
        return find_key(res, "prompt_id")
    job = {k: v for k, v in item.items() if k not in ("kind", "adopt") and not k.startswith("_")}
    pid = model(mcp, submit_only=True, **job)      # comfy-mcp converts the UI workflow; then move it if asked
    return to_front(pid) if (front and pid) else pid


AUDIO_LOG = r"J:\Projets\Unreal_Projects\Guess Who\Tools\agent_logs\audio.md"


def voice_block_active():
    """True while the voice agent is inside a front-chunk block (its log: 'voice block start' / 'voice block end')."""
    try:
        lines = [x for x in open(AUDIO_LOG, encoding="utf-8", errors="replace") if "voice block" in x]
    except OSError:
        return False
    return bool(lines) and "voice block start" in lines[-1]


def collect(item, pid):
    if item["kind"] == "concepts":
        n = len(json.load(open(os.path.join(AG, item["file"]), encoding="utf-8-sig")))
        cmd = ["zbatch.py", item["file"], "--cands", str(item.get("cands", 3)), "--chunk", str(n), "--adopt", pid]
    else:
        tmp = os.path.join(AG, "batches", f"_adopt_{item['name']}.json")
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump([{**item, "kind": "model", "adopt": pid}], f, indent=1)
        cmd = ["assetgen.py", "batch", tmp]
    r = subprocess.run([sys.executable, "-I", "-X", "utf8"] + cmd, cwd=AG, capture_output=True, text=True,
                       encoding="utf-8", errors="replace", timeout=1800)
    out = (r.stdout or "").strip().splitlines()
    return out[-1][:1200] if out else (r.stderr or "")[-800:]


def take(st, order):
    """Next unsubmitted line of the first feed (in `order`) that has one."""
    for k in order:
        lines = feed_lines(os.path.join(AG, "batches", k))
        n = st["taken"].get(k, 0)
        if n < len(lines):
            st["taken"][k] = n + 1
            return lines[n]
    return None


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--slots", type=int, default=2, help="plain FIFO jobs queued at most")
    p.add_argument("--until", default="2026-11-03 11:00")
    a = p.parse_args()
    until = datetime.datetime.strptime(a.until, "%Y-%m-%d %H:%M")
    st = load_state()
    mcp = None
    log(event="start", slots=a.slots, inflight=[i["pid"][:8] for i in st["inflight"]])
    while True:
        # 1. finished / vanished jobs
        try:
            q = http("/queue")
            queued = {r[1] for r in q["queue_running"] + q["queue_pending"]}
            server_ok = True
        except Exception as e:  # noqa: BLE001
            server_ok = False
            log(event="server_unreachable", error=str(e)[:120])
        if server_ok:
            for inf in list(st["inflight"]):
                pid = inf["pid"]
                try:
                    h = http(f"/history/{pid}").get(pid)
                except Exception:  # noqa: BLE001
                    continue
                if h and (h.get("status", {}).get("completed") or h.get("status", {}).get("status_str") in ("success", "error")):
                    status = h.get("status", {}).get("status_str")
                    try:
                        res = collect(inf["item"], pid)
                    except Exception as e:  # noqa: BLE001
                        res = "collect failed: " + str(e)[:300]
                    log(event="done", pid=pid[:8], name=inf["item"].get("name") or inf["item"].get("file"), status=status, result=res)
                    st["inflight"].remove(inf)
                elif not h and pid not in queued:
                    inf["missing"] = inf.get("missing", 0) + 1
                    if inf["missing"] >= 3:          # 3 checks in a row: lost (ComfyUI restarted)
                        st["inflight"].remove(inf)
                        if inf["item"].get("_resubmitted"):
                            log(event="lost_again_dropped", pid=pid[:8], item=inf["item"].get("name") or inf["item"].get("file"))
                        else:
                            inf["item"]["_resubmitted"] = True
                            st.setdefault("retry", []).append(inf["item"])
                            log(event="lost_will_resubmit_once", pid=pid[:8])
                else:
                    inf["missing"] = 0
            save_state(st)
        # 1b. GPU rule v4 (coordinator 03:27): slices VOICES :00-:30, CHARACTERS :30-:52, PROPS :52-:00. Props submit
        #     only in their slice, front=true, one job at a time, ending before :00 (submitted :52-:55, TRELLIS 2-4 min).
        #     A front job of mine still PENDING outside :52-:56 is taken back out (my own entry) for the next slice.
        #     Filler: when the queue is completely empty, one short FIFO job (<= 8 min) is allowed at any time.
        now = datetime.datetime.now()
        running, pending = set(), set()
        if server_ok:
            try:
                q = http("/queue")
                running = {r[1] for r in q["queue_running"]}
                pending = {r[1] for r in q["queue_pending"]}
            except Exception:  # noqa: BLE001
                server_ok = False
        if server_ok:
            for inf in list(st["inflight"]):
                if inf.get("front") and inf["pid"] in pending and not (52 <= now.minute < 57):
                    try:
                        post("/queue", {"delete": [inf["pid"]]})
                        if inf["pid"] not in {r[1] for r in http("/queue")["queue_pending"]}:
                            st["inflight"].remove(inf)
                            st.setdefault("front_retry", []).append(inf["item"])
                            log(event="front_withdrawn_outside_slice", pid=inf["pid"][:8], name=inf["item"].get("name"))
                    except Exception as e:  # noqa: BLE001
                        log(event="withdraw_failed", pid=inf["pid"][:8], error=str(e)[:200])
            save_state(st)
        # 2. one front job in the props slice, or one filler when the queue is empty (approved TRELLIS first)
        if server_ok and now < until:
            mode = None
            if 52 <= now.minute < 56 and not any(i.get("front") for i in st["inflight"]):
                mode = "front"
            elif not running and not pending and not any(i.get("filler") for i in st["inflight"]):
                mode = "filler"
            item = None
            if mode:
                # front slice: TRELLIS only (2-4 min, ends before :00); fillers alternate TRELLIS / concept chunk
                models_first = ["feed_models.jsonl", "feed_priority.jsonl", "feed_concepts.jsonl"]
                concepts_first = ["feed_priority.jsonl", "feed_concepts.jsonl", "feed_models.jsonl"]
                if mode == "front":
                    order = ["feed_models.jsonl"]
                else:
                    st["filler_n"] = st.get("filler_n", 0) + 1
                    order = concepts_first if st["filler_n"] % 2 == 0 else models_first
                item = (st["front_retry"].pop(0) if st.get("front_retry") else
                        st["retry"].pop(0) if (st.get("retry") and mode != "front") else
                        take(st, order))
            if item:
                front = mode == "front"
                try:
                    if mcp is None:
                        mcp = ComfyMCP()
                    pid = submit(mcp, item, front=front)
                    if not pid:
                        raise RuntimeError("no prompt_id")
                    st["inflight"].append({"pid": pid, "item": item, "at": time.strftime("%H:%M"), "front": front,
                                           "filler": not front})
                    log(event="submitted", pid=pid[:8], name=item.get("name") or item.get("file"), mode=mode)
                except Exception as e:  # noqa: BLE001
                    log(event="submit_failed", item=item.get("name") or item.get("file"), error=str(e)[:300])
                    st.setdefault("front_retry", []).insert(0, item)
                    try:
                        mcp.close()
                    except Exception:  # noqa: BLE001
                        pass
                    mcp = None
                save_state(st)
        if not st["inflight"] and datetime.datetime.now() >= until:
            log(event="stop_until_reached")
            break
        time.sleep(15)


if __name__ == "__main__":
    main()
