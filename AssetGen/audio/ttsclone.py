"""Consistent majordome voice: clone the chosen VoiceDesign take (vo_welcome_s503) with Qwen3-TTS Base 1.7B for the other lines.
  python -I -X utf8 ttsclone.py   (reference copied to V:/ComfyUI/input/gw_vo_ref.flac)"""
import json, os, sys, time
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
from assetgen import JOBS, run_and_fetch  # noqa: E402
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "ui"))
from comfyclient import ComfyMCP  # noqa: E402

REF_TEXT = "Mesdames et messieurs, bienvenue au bal masqué."
LINES = {"hunt": "Que la chasse commence.", "detectives": "Les détectives l'emportent.", "guests": "Les invités l'emportent.",
         "thirty": "Plus que trente secondes."}
SEEDS = [601, 602]


def main():
    wf = {"1": {"class_type": "LoadAudio", "inputs": {"audio": "gw_vo_ref.flac"}}}
    nid = 10
    for key, text in LINES.items():
        for seed in SEEDS:
            t, s = str(nid), str(nid + 1); nid += 2
            wf[t] = {"class_type": "FB_Qwen3TTSVoiceClone", "inputs": {
                "target_text": text, "model_choice": "1.7B", "device": "auto", "precision": "bf16", "language": "French",
                "ref_audio": ["1", 0], "ref_text": REF_TEXT, "seed": seed, "max_new_tokens": 1024, "top_p": 0.8, "top_k": 20,
                "temperature": 0.8, "repetition_penalty": 1.05, "x_vector_only": False, "attention": "auto", "unload_model_after_generate": False}}
            wf[s] = {"class_type": "SaveAudio", "inputs": {"audio": [t, 0], "filename_prefix": f"gw_audio/voc_{key}_s{seed}"}}
    job = os.path.join(JOBS, f"ttsclone_{int(time.time())}.json")
    json.dump(wf, open(job, "w", encoding="utf-8"), indent=1, ensure_ascii=False)
    mcp = ComfyMCP()
    try:
        sub = mcp.call("run_workflow", workflow_path=job, wait=False)
        print(json.dumps(sub)[:300], flush=True)
    finally:
        mcp.close()


if __name__ == "__main__":
    main()
