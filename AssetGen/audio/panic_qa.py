"""Objective QA of the panic candidates (nobody listens before the user does): loudness, pitch, voiced fraction (whisper check),
speaker embedding (ECAPA, CPU) and French ASR (faster-whisper small, CPU) against the intended text.
Needs the system Python's user site-packages (faster_whisper, speechbrain), so run WITHOUT -I:
  python -X utf8 panic_qa.py [glob ...]      (default: gen/panic_*/*.flac and gen/piano_*/*.flac)
Results are cached in qa/panic_qa.json (key = file name, refreshed when the file changes); embeddings in qa/panic_emb.npz."""
import difflib, glob, json, os, re, sys, unicodedata, warnings
import numpy as np
warnings.filterwarnings("ignore")
os.environ.setdefault("HF_HUB_OFFLINE", "1")
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import audiolib as A  # noqa: E402

QA = os.path.join(HERE, "qa"); os.makedirs(QA, exist_ok=True)
CACHE = os.path.join(QA, "panic_qa.json")
EMB = os.path.join(QA, "panic_emb.npz")
NO_ASR = ("scream", "gasp", "piano", "_sa_")


def norm(s):
    s = unicodedata.normalize("NFKD", s.lower())
    s = "".join(c for c in s if not unicodedata.combining(c))
    return re.sub(r"[^a-z ]+", " ", s).split()


def word_match(target, heard):
    a, b = norm(target), norm(heard)
    w = difflib.SequenceMatcher(None, a, b).ratio()
    c = difflib.SequenceMatcher(None, "".join(a), "".join(b)).ratio()
    return round(w, 3), round(c, 3)


_asr = _enc = None


def asr(path):
    global _asr
    if _asr is None:
        from faster_whisper import WhisperModel
        _asr = WhisperModel("small", device="cpu", compute_type="int8")
    segs, info = _asr.transcribe(path, language="fr", beam_size=5, vad_filter=False, condition_on_previous_text=False)
    return " ".join(s.text.strip() for s in segs).strip()


def embed(x16):
    global _enc
    import torch
    if _enc is None:
        from speechbrain.inference.speaker import EncoderClassifier
        from speechbrain.utils.fetching import LocalStrategy
        snap = glob.glob(os.path.expanduser("~/.cache/huggingface/hub/models--speechbrain--spkrec-ecapa-voxceleb/snapshots/*"))[0]
        _enc = EncoderClassifier.from_hparams(source=snap, savedir=snap, run_opts={"device": "cpu"}, local_strategy=LocalStrategy.NO_LINK)
    with torch.no_grad():
        e = _enc.encode_batch(torch.tensor(x16, dtype=torch.float32)[None]).squeeze().numpy()
    return e / (np.linalg.norm(e) + 1e-9)


def voice_metrics(x, sr):
    import librosa
    mono = x.mean(axis=1).astype(np.float32)
    m = A.metrics(x, sr)
    # active part: frames within 35 dB of the loudest 25 ms frame
    fl = int(0.025 * sr)
    e = np.array([np.sqrt(np.mean(mono[i:i + fl] ** 2) + 1e-20) for i in range(0, max(1, len(mono) - fl), fl)])
    act = 20 * np.log10(e + 1e-12) > 20 * np.log10(e.max() + 1e-12) - 35
    idx = np.where(act)[0]
    active_s = (idx[-1] - idx[0] + 1) * 0.025 if len(idx) else 0.0
    f0, vflag, vprob = librosa.pyin(mono, fmin=60, fmax=1100, sr=sr, frame_length=1024, hop_length=256)
    hop_t = 256 / sr
    # voiced fraction measured over the active span only
    fi = np.arange(len(f0)) * hop_t
    if len(idx):
        span = (fi >= idx[0] * 0.025) & (fi <= (idx[-1] + 1) * 0.025)
    else:
        span = np.ones_like(fi, bool)
    vf = float(np.mean(vflag[span])) if span.any() else 0.0
    f0v = f0[vflag & span]
    return {"duration": m["duration"], "active_s": round(active_s, 2), "lufs": m["lufs"], "max_mom": m["max_momentary_lufs"],
            "peak_dbfs": m["peak_dbfs"], "lead_s": m["lead_silence_s"], "trail_s": m["trail_silence_s"], "gap_s": m["longest_inner_silence_s"],
            "voiced_frac": round(vf, 3), "f0_med": round(float(np.median(f0v)), 1) if len(f0v) else 0.0,
            "f0_p90": round(float(np.percentile(f0v, 90)), 1) if len(f0v) else 0.0, "centroid": m["centroid_hz"], "flatness": m["flatness"]}


def analyze(files):
    import librosa
    cache = json.load(open(CACHE, encoding="utf-8")) if os.path.exists(CACHE) else {}
    embs = dict(np.load(EMB)) if os.path.exists(EMB) else {}
    for f in files:
        b = os.path.basename(f)
        mt = os.path.getmtime(f)
        if b in cache and cache[b].get("mtime") == mt and (b in embs or any(t in b for t in ("piano",))):
            continue
        side_p = os.path.splitext(f)[0] + ".txt"
        side = json.load(open(side_p, encoding="utf-8")) if os.path.exists(side_p) else {}
        x, sr = A.load(f)
        r = {"file": f, "mtime": mt, "text": side.get("text", ""), "seed": side.get("seed")}
        r.update(voice_metrics(x, sr))
        if "piano" not in b:
            x16 = librosa.resample(x.mean(axis=1).astype(np.float32), orig_sr=sr, target_sr=16000)
            embs[b] = embed(x16)
        if r["text"] and not any(t in b for t in NO_ASR):
            heard = asr(f)
            r["heard"] = heard
            r["word_match"], r["char_match"] = word_match(r["text"], heard)
        cache[b] = r
        print(f"{b:44s} dur={r['duration']:5.2f} act={r['active_s']:5.2f} lufs={r['lufs']:6.1f} vf={r['voiced_frac']:.2f} "
              f"f0={r['f0_med']:6.1f}/{r['f0_p90']:6.1f} cen={r['centroid']:5d} "
              + (f"wm={r['word_match']:.2f} cm={r['char_match']:.2f} heard: {r['heard'][:60]}" if "heard" in r else ""), flush=True)
        json.dump(cache, open(CACHE + ".tmp", "w", encoding="utf-8"), indent=1, ensure_ascii=False)
        os.replace(CACHE + ".tmp", CACHE)
        np.savez(EMB + ".tmp.npz", **embs)
        os.replace(EMB + ".tmp.npz", EMB)
    return cache, embs


def sim(embs, a, b):
    return round(float(np.dot(embs[a], embs[b])), 3)


if __name__ == "__main__":
    pats = sys.argv[1:] or [os.path.join(HERE, "gen", "panic_*", "*.flac"), os.path.join(HERE, "gen", "piano_*", "*.flac")]
    files = sorted(set(sum((glob.glob(p if os.path.isabs(p) else os.path.join(HERE, p)) for p in pats), [])))
    analyze(files)
