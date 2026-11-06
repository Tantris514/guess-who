"""Majordome voice lines with Qwen3-TTS VoiceDesign (1.7B, French) through comfy-mcp. One run, all lines x seeds.
  python -I -X utf8 ttsbatch.py
Outputs: AssetGen/audio/gen/vo_<key>/vo_<key>_s<seed>_0.flac + .txt sidecar."""
import json, os, sys, time
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
from assetgen import JOBS, run_and_fetch  # noqa: E402
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "ui"))
from comfyclient import ComfyMCP  # noqa: E402

INSTRUCT = ("Un majordome distingué d'un manoir anglais des années 1930, voix grave de baryton, posée et solennelle, "
            "diction impeccable, ton cérémonieux d'une annonce faite dans un grand salon, débit lent.")
LINES = {
    "welcome": "Mesdames et messieurs, bienvenue au bal masqué.",
    "hunt": "Que la chasse commence.",
    "detectives": "Les détectives l'emportent.",
    "guests": "Les invités l'emportent.",
    "thirty": "Plus que trente secondes.",
}
SEEDS = [501, 502, 503]


def main():
    wf, saves, nid = {}, {}, 1
    for key, text in LINES.items():
        for seed in SEEDS:
            t, s = str(nid), str(nid + 1); nid += 2
            wf[t] = {"class_type": "FB_Qwen3TTSVoiceDesign", "inputs": {
                "text": text, "instruct": INSTRUCT, "model_choice": "1.7B", "device": "auto", "precision": "bf16", "language": "French",
                "seed": seed, "max_new_tokens": 1024, "top_p": 0.8, "top_k": 20, "temperature": 0.8, "repetition_penalty": 1.05,
                "attention": "auto", "unload_model_after_generate": False}}
            prefix = f"gw_audio/vo_{key}_s{seed}"
            wf[s] = {"class_type": "SaveAudio", "inputs": {"audio": [t, 0], "filename_prefix": prefix}}
            saves[prefix.split("/", 1)[1]] = (key, seed, text)
    tag = f"ttsbatch_{int(time.time())}"
    job_path = os.path.join(JOBS, tag + ".json")
    json.dump(wf, open(job_path, "w", encoding="utf-8"), indent=1, ensure_ascii=False)
    mcp = ComfyMCP()
    try:
        tmp = os.path.join(HERE, "gen", "_incoming", tag)
        pid, secs, files, mapping = run_and_fetch(mcp, job_path, tmp, 3600)
        for local, query in sorted(mapping.items()):
            fname = query.split("filename=")[1].split("&")[0]
            k = next((k for k in saves if fname.startswith(k + "_")), None)
            if not k:
                continue
            key, seed, text = saves[k]
            d = os.path.join(HERE, "gen", f"vo_{key}"); os.makedirs(d, exist_ok=True)
            dst = os.path.join(d, f"{k}_0{os.path.splitext(local)[1]}")
            os.replace(os.path.join(tmp, local), dst)
            json.dump({"model": "Qwen3-TTS-12Hz-1.7B-VoiceDesign", "seed": seed, "text": text, "instruct": INSTRUCT, "prompt": text,
                       "batch_index": 0, "prompt_id": pid}, open(os.path.splitext(dst)[0] + ".txt", "w", encoding="utf-8"), ensure_ascii=False)
        for left in os.listdir(tmp):
            os.remove(os.path.join(tmp, left))
        os.rmdir(tmp)
        print(json.dumps({"ok": True, "seconds": secs, "files": len(mapping)}))
    finally:
        mcp.close()


if __name__ == "__main__":
    main()
