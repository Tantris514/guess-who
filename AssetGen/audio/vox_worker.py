"""CPU side of the night run, beside vox_sched.py (which only feeds the GPU queue). Every few minutes:
  1. QA of every new take (panic_qa: loudness, pitch, speaker embedding, French ASR);
  2. register references refreshed (panic_select --refs-only logic + character aliases);
  3. per-character voice assets (voice_assets.py);
  4. every vox batch whose chunks are all rendered is published (vox.publish -> final/<batch>/<batch>_report.json);
     lines that failed QA get a retake job appended to the plan (new seeds, at most 3 tries per line);
  5. logs/published.log gets one line per publish (batch, counts) for the engine.
  python -X utf8 vox_worker.py      (system Python: needs faster_whisper / speechbrain)"""
import glob, json, os, sys, time, traceback
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from planlock import plan_lock  # noqa: E402
os.environ.setdefault("HF_HUB_OFFLINE", "1")
PLAN = os.path.join(HERE, "logs", "sched_plan.json")
STATE = os.path.join(HERE, "logs", "sched_state.json")
WSTATE = os.path.join(HERE, "logs", "worker_state.json")
PUB = os.path.join(HERE, "logs", "published.log")


def log(s):
    print(time.strftime("%H:%M:%S"), s, flush=True)


def load(p, d):
    try:
        return json.load(open(p, encoding="utf-8"))
    except Exception:
        return d


def chunk_status(plan, st):
    """{plan entry name: (n chunks, n done)}"""
    import vox_sched as S
    out = {}
    for e in plan:
        try:
            n = len(S.chunks_of(e))
        except Exception:
            continue
        done = sum(1 for i in range(n) if (st.get(f"{e['name']}#{i}") or {}).get("status") in ("done", "failed"))
        out[e["name"]] = (n, done)
    return out


def main():
    import panic_qa as Q
    import panic_select as PS
    import vox
    import voice_assets
    ws = load(WSTATE, {"published": {}, "tries": {}})
    while True:
        try:
            files = sorted(set(glob.glob(os.path.join(HERE, "gen", "voice_*", "*.flac")) + glob.glob(os.path.join(HERE, "gen", "panic_*", "*.flac"))
                               + glob.glob(os.path.join(HERE, "gen", "vox_*", "*.flac"))))
            Q.analyze(files)
            qa, emb = PS.load()
            refs = PS.choose_refs(qa, emb)
            from panic_voices import ALIAS
            for c, v in ALIAS.items():
                if v in refs:
                    refs[c] = dict(refs[v], alias_of=v)
            p = os.path.join(HERE, "qa", "panic_refs.json")
            json.dump(refs, open(p + ".tmp", "w", encoding="utf-8"), indent=1); os.replace(p + ".tmp", p)
            try:
                voice_assets.main()
            except Exception as e:
                log(f"voice assets: {e}")
            plan, st = load(PLAN, []), load(STATE, {})
            cs = chunk_status(plan, st)
            batches = {}
            for e in plan:
                if e["name"].startswith("vox_"):
                    b = e["name"][4:].split("_retry")[0]
                    batches.setdefault(b, []).append(e["name"])
            for b, names in batches.items():
                n_tot = sum(cs.get(n, (0, 0))[0] for n in names)
                n_done = sum(cs.get(n, (0, 0))[1] for n in names)
                sig = f"{n_done}/{n_tot}"
                if n_done == 0 or ws["published"].get(b) == sig:
                    continue
                final, missing = vox.publish(b)
                ws["published"][b] = sig
                cats = {}
                for r in final:
                    cats[r["category"]] = cats.get(r["category"], 0) + 1
                with open(PUB, "a", encoding="utf-8") as fh:
                    fh.write(f"{time.strftime('%H:%M:%S')} {b} {len(final)} lines {json.dumps(cats)} missing={len(missing)} chunks={sig}\n")
                # retakes for the lines that failed, once their batch is fully rendered
                if n_done == n_tot and missing:
                    # only lines that were rendered and failed (a batch may be partly pre-rendered, e.g. one character first)
                    qa_now = json.load(open(os.path.join(HERE, "qa", "panic_qa.json"), encoding="utf-8"))
                    rendered = {k.rsplit("_s", 1)[0] for k in qa_now if k.startswith("vx_" + b + "_")}
                    retry = [k for k in missing if ws["tries"].get(k, 0) < 3 and k in rendered]
                    if retry:
                        k = max(ws["tries"].get(x, 0) for x in retry) + 1
                        for x in retry:
                            ws["tries"][x] = ws["tries"].get(x, 0) + 1
                        out = os.path.join(HERE, "batches", f"vox_{b}_retry{k}_{int(time.time())}.json")
                        o, got = vox.jobs(b, seeds=2, seed_base=100 * k, only_keys=set(retry), out=out)
                        if got:
                            with plan_lock(PLAN):
                                plan = load(PLAN, [])
                                name = os.path.splitext(os.path.basename(out))[0]
                                # retakes go right after the entries already started, before untouched batches
                                pos = max([i for i, e in enumerate(plan) if any(c.startswith(e["name"] + "#") for c in st)] + [-1]) + 1
                                plan.insert(pos, {"name": name, "kind": "tts", "jobs": os.path.relpath(out, HERE).replace("\\", "/"), "chunk": 30})
                                json.dump(plan, open(PLAN + ".tmp", "w", encoding="utf-8"), indent=1); os.replace(PLAN + ".tmp", PLAN)
                            log(f"retakes for {b}: {len(got)} lines ({name})")
                json.dump(ws, open(WSTATE, "w", encoding="utf-8"), indent=1)
        except Exception:
            log(traceback.format_exc()[-1500:])
        time.sleep(180)


if __name__ == "__main__":
    main()
