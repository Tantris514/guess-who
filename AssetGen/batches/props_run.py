"""Plain FIFO runner for a list of prop jobs (no slices): at most --ahead jobs of mine queued, each submitted ONCE,
polled through /history, collected with the pipeline's own code. A failed or vanished job is logged, never resubmitted.

  python -I -X utf8 props_run.py FEED.jsonl [--ahead 2]

FEED lines: same dicts as props_feeder.py. State: FEED.state.json. Stdout = one JSON line per event.
"""
import argparse
import json
import os
import sys
import time

sys.path.insert(0, r"J:\Projets\Unreal_Projects\Guess Who\Tools\props")
from props_feeder import ComfyMCP, collect, feed_lines, http, submit  # noqa: E402


def say(**kw):
    print(json.dumps({"t": time.strftime("%H:%M:%S"), **kw}, ensure_ascii=False), flush=True)


def main():
    p = argparse.ArgumentParser()
    p.add_argument("feed")
    p.add_argument("--ahead", type=int, default=2)
    a = p.parse_args()
    state = a.feed + ".state.json"
    st = json.load(open(state, encoding="utf-8")) if os.path.exists(state) else {"next": 0, "inflight": [], "done": [], "failed": []}
    lines = feed_lines(a.feed)
    mcp = None

    def save():
        with open(state + ".tmp", "w", encoding="utf-8") as f:
            json.dump(st, f, indent=1)
        os.replace(state + ".tmp", state)

    while st["next"] < len(lines) or st["inflight"]:
        try:
            q = http("/queue")
        except Exception as e:  # noqa: BLE001
            say(event="server_unreachable", error=str(e)[:120])
            time.sleep(30)
            continue
        queued = {r[1] for r in q["queue_running"] + q["queue_pending"]}
        for inf in list(st["inflight"]):
            label = inf["item"].get("name") or inf["item"].get("file")
            try:
                h = http(f"/history/{inf['pid']}").get(inf["pid"])
            except Exception:  # noqa: BLE001
                continue
            if h and (h.get("status", {}).get("completed") or h.get("status", {}).get("status_str") in ("success", "error")):
                status = h.get("status", {}).get("status_str")
                try:
                    res = collect(inf["item"], inf["pid"])
                except Exception as e:  # noqa: BLE001
                    res = "collect failed: " + str(e)[:300]
                ok = status == "success" and '"ok": true' in res
                st["inflight"].remove(inf)
                (st["done"] if ok else st["failed"]).append(label)
                say(event="done" if ok else "failed", name=label, status=status, result=res[:400])
                save()
            elif not h and inf["pid"] not in queued:
                inf["missing"] = inf.get("missing", 0) + 1
                if inf["missing"] >= 4:
                    st["inflight"].remove(inf)
                    st["failed"].append(label)
                    say(event="lost_not_resubmitted", name=label, pid=inf["pid"])
                    save()
            else:
                inf["missing"] = 0
        while st["next"] < len(lines) and len(st["inflight"]) < a.ahead:
            item = lines[st["next"]]
            label = item.get("name") or item.get("file")
            st["next"] += 1
            try:
                if mcp is None:
                    mcp = ComfyMCP()
                pid = submit(mcp, item)
                if not pid:
                    raise RuntimeError("no prompt_id")
                st["inflight"].append({"pid": pid, "item": item})
                say(event="submitted", name=label, pid=pid[:8])
            except Exception as e:  # noqa: BLE001
                st["failed"].append(label)
                say(event="submit_failed", name=label, error=str(e)[:300])
                if mcp:
                    try:
                        mcp.close()
                    except Exception:  # noqa: BLE001
                        pass
                mcp = None
            save()
        time.sleep(15)
    if mcp:
        mcp.close()
    say(event="all_finished", done=st["done"], failed=st["failed"])


if __name__ == "__main__":
    main()
