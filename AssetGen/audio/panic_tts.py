"""Panic VO (guest reactions to a shot): Qwen3-TTS 1.7B VoiceDesign / VoiceClone jobs through comfy-mcp (same path as
ttsbatch.py / ttsclone.py). One ComfyUI run per chunk, one model per run (design and clone chunks are never mixed), and the
last TTS node of each run unloads its model so the shared GPU gets its memory back.

  python -I -X utf8 panic_tts.py JOBS.json [--chunk 24] [--only key1,key2]
JOBS.json: list of {"key", "group", "mode": "design"|"clone", "text", "seed",
                    design: "instruct";  clone: "ref" (file name in V:/ComfyUI/input), "ref_text";
                    optional "temperature", "top_p", "top_k", "meta" (free dict copied to the sidecar)}
Outputs: gen/<group>/<key>_s<seed>_0.flac + .txt sidecar (JSON).
"""
import argparse, json, os, sys, time
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
from assetgen import JOBS, run_and_fetch  # noqa: E402
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "ui"))
from comfyclient import ComfyMCP  # noqa: E402

GEN = os.path.join(HERE, "gen")


def build(items):
    wf, saves, refs, nid = {}, {}, {}, 100
    for i, j in enumerate(items):
        last = i == len(items) - 1
        t, s = str(nid), str(nid + 1); nid += 2
        common = {"model_choice": "1.7B", "device": "auto", "precision": "bf16", "language": "French", "seed": int(j["seed"]),
                  "max_new_tokens": 1024, "top_p": float(j.get("top_p", 0.8)), "top_k": int(j.get("top_k", 20)),
                  "temperature": float(j.get("temperature", 0.8)), "repetition_penalty": 1.05, "attention": "auto",
                  "unload_model_after_generate": last}
        if j["mode"] == "design":
            wf[t] = {"class_type": "FB_Qwen3TTSVoiceDesign", "inputs": dict(common, text=j["text"], instruct=j["instruct"])}
        else:
            if j["ref"] not in refs:
                rid = str(len(refs) + 1)
                refs[j["ref"]] = rid
                wf[rid] = {"class_type": "LoadAudio", "inputs": {"audio": j["ref"]}}
            wf[t] = {"class_type": "FB_Qwen3TTSVoiceClone", "inputs": dict(common, target_text=j["text"], ref_audio=[refs[j["ref"]], 0],
                                                                           ref_text=j["ref_text"], x_vector_only=False)}
        prefix = f"gw_audio/panic/{j['key']}_s{j['seed']}"
        wf[s] = {"class_type": "SaveAudio", "inputs": {"audio": [t, 0], "filename_prefix": prefix}}
        saves[prefix.rsplit("/", 1)[1]] = j
    return wf, saves


def main():
    p = argparse.ArgumentParser()
    p.add_argument("jobs"); p.add_argument("--chunk", type=int, default=24); p.add_argument("--only", default="")
    p.add_argument("--retries", type=int, default=6)
    a = p.parse_args()
    jobs = json.load(open(a.jobs, encoding="utf-8-sig"))
    if a.only:
        keep = set(a.only.split(",")); jobs = [j for j in jobs if j["key"] in keep]
    chunks = []
    for mode in ("design", "clone"):
        sel = [j for j in jobs if j["mode"] == mode]
        chunks += [sel[c:c + a.chunk] for c in range(0, len(sel), a.chunk)]
    os.makedirs(JOBS, exist_ok=True)
    mcp = ComfyMCP()
    try:
        for ci, chunk in enumerate(chunks):
            wf, saves = build(chunk)
            for attempt in range(a.retries):
                tag = f"panictts_{int(time.time())}_{ci}"
                job_path = os.path.join(JOBS, tag + ".json")
                json.dump(wf, open(job_path, "w", encoding="utf-8"), indent=1, ensure_ascii=False)
                tmp = os.path.join(GEN, "_incoming", tag)
                try:
                    pid, secs, files, mapping = run_and_fetch(mcp, job_path, tmp, 2400 + 60 * len(chunk))
                    break
                except Exception as e:
                    msg = str(e)
                    print(json.dumps({"ok": False, "chunk": ci, "attempt": attempt, "error": msg[:600]}), flush=True)
                    if attempt == a.retries - 1:
                        raise
                    time.sleep(120 if ("memory" in msg.lower() or "cuda" in msg.lower()) else 30)
            n = 0
            for local, query in sorted(mapping.items()):
                fname = query.split("filename=")[1].split("&")[0]
                key = next((k for k in saves if fname.startswith(k + "_")), None)
                if not key:
                    continue
                j = saves[key]
                out_dir = os.path.join(GEN, j["group"]); os.makedirs(out_dir, exist_ok=True)
                dst = os.path.join(out_dir, f"{key}_0{os.path.splitext(local)[1]}")
                os.replace(os.path.join(tmp, local), dst)
                side = {"model": "Qwen3-TTS-12Hz-1.7B-" + ("VoiceDesign" if j["mode"] == "design" else "Base (voice clone)"),
                        "mode": j["mode"], "seed": j["seed"], "text": j["text"], "prompt": j["text"], "language": "French",
                        "temperature": j.get("temperature", 0.8), "top_p": j.get("top_p", 0.8), "batch_index": 0, "prompt_id": pid}
                for k in ("instruct", "ref", "ref_text", "meta"):
                    if k in j:
                        side[k] = j[k]
                json.dump(side, open(os.path.splitext(dst)[0] + ".txt", "w", encoding="utf-8"), ensure_ascii=False)
                n += 1
            for left in os.listdir(tmp):
                os.remove(os.path.join(tmp, left))
            os.rmdir(tmp)
            print(json.dumps({"ok": True, "chunk": ci, "mode": chunk[0]["mode"], "seconds": secs, "files": n, "of": len(chunk)}), flush=True)
    finally:
        mcp.close()


if __name__ == "__main__":
    main()
