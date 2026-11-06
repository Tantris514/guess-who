"""Objective check of the generated voice lines (I cannot listen): transcribe each candidate with faster-whisper (small, CPU, French)
and compare with the intended text. Needs the system Python's user site-packages (faster_whisper), so run WITHOUT -I:
  python -X utf8 asr_check.py"""
import difflib, glob, json, os, re, unicodedata
from faster_whisper import WhisperModel

HERE = os.path.dirname(os.path.abspath(__file__))


def norm(s):
    s = unicodedata.normalize("NFKD", s.lower())
    s = "".join(c for c in s if not unicodedata.combining(c))
    return re.sub(r"[^a-z ]+", " ", s).split()


m = WhisperModel("small", device="cpu", compute_type="int8")
res = {}
for f in sorted(glob.glob(os.path.join(HERE, "gen", "vo_*", "*.flac"))):
    meta = json.load(open(f[:-5] + ".txt", encoding="utf-8"))
    segs, info = m.transcribe(f, language="fr", beam_size=5, vad_filter=False)
    txt = " ".join(s.text.strip() for s in segs)
    ratio = difflib.SequenceMatcher(None, norm(meta["text"]), norm(txt)).ratio()
    res[os.path.basename(f)] = {"target": meta["text"], "heard": txt, "word_match": round(ratio, 3)}
    print(f"{os.path.basename(f):28s} match={ratio:.2f}  heard: {txt[:90]}", flush=True)
json.dump(res, open(os.path.join(HERE, "qa", "asr_report.json"), "w", encoding="utf-8"), indent=1, ensure_ascii=False)
