"""Master the selected Stable Audio 3 candidates into game-ready WAVs (AssetGen/audio/final) + QA report.

Music: beat-aligned loop search, equal-power crossfade of the loop tail into the pre-roll (seamless wrap), -16 LUFS, TP <= -1 dBTP.
Ambiences: crossfaded loops, quieter targets. One-shots: trimmed, faded, loudness-matched by max momentary loudness.
Every accepted file is recorded (prompt, seed) in AssetGen/ui_manifest.json (kind "audio").
"""
import json, os, sys
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import audiolib as A

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "final"); os.makedirs(OUT, exist_ok=True)
QA = os.path.join(HERE, "qa"); os.makedirs(QA, exist_ok=True)
MAN = os.path.join(os.path.dirname(HERE), "ui_manifest.json")

# name: (candidate, kind, params)
SEL = {
    # music loops (UE asset name, source, loop search window)
    "MUS_Menu":   ("mus_menu_s301_0", "music", dict(min_len=55, max_len=85, skip_start=2.0, avoid_end=4.0)),
    "MUS_Lobby":  ("mus_lobby_s302_0", "music", dict(min_len=35, max_len=58, skip_start=2.0, avoid_end=8.0)),
    "MUS_Party":  ("mus_party_s303_0", "music", dict(min_len=30, max_len=44, skip_start=10.0, avoid_end=40.0, gain=-3.0)),
    "MUS_Gramophone": ("mus_party_s303_1", "music", dict(min_len=30, max_len=48, skip_start=42.0, avoid_end=3.0, gain=-3.0, mono=True)),
    "MUS_Hunt":   ("mus_hunt_s304_1", "music", dict(min_len=50, max_len=85, skip_start=2.0, avoid_end=4.0)),
    "MUS_Final":  ("mus_final_s305_0", "music", dict(min_len=30, max_len=60, skip_start=2.0, avoid_end=4.0)),
    # stingers
    "STG_Reveal":     ("sting_reveal_s306_1", "sting", dict(lufs=-15.0)),
    "STG_Start":      ("sting_start_s307_2", "sting", dict(lufs=-15.0)),
    "STG_Detectives": ("sting_detectives_s308_2", "sting", dict(lufs=-15.0)),
    "STG_Guests":     ("sting_guests_s309_2", "sting", dict(lufs=-15.0)),
    # UI
    "S_UI_Hover":   ("sfx_hover_s310_2", "ui", dict(keep=0.22, mom=-30.0)),
    "S_UI_Click":   ("sfx_click_s311_0", "ui", dict(keep=0.16, mom=-24.0)),
    "S_UI_Confirm": ("sfx_confirm_s312_1", "ui", dict(keep=1.2, mom=-22.0)),
    "S_UI_Back":    ("sfx_back_s313_1", "ui", dict(keep=0.18, mom=-25.0)),
    "S_UI_Type":    ("sfx_type_s314_0", "ui", dict(keep=0.14, mom=-27.0)),
    "S_UI_Card":    ("sfx_card_s315_2", "ui", dict(keep=0.5, mom=-21.0)),
    # gameplay one-shots (3D ones mono)
    "S_GW_Gunshot": ("sfx_shot_s316_2", "oneshot", dict(mom=-9.0, mono=True)),
    "S_GW_Empty":   ("sfx_empty_s317_0", "oneshot", dict(mom=-20.0, mono=True, keep=0.5)),
    "S_GW_Thud":    ("sfx_fall_s318_0", "oneshot", dict(mom=-18.0, mono=True)),
    "S_GW_Gong":    ("sfx_gong_s319_1", "oneshot", dict(mom=-15.0)),
    "S_GW_ClockChime": ("sfx_clock_s320_1", "oneshot", dict(mom=-18.0)),
    # personal round-result cues played by the PlayerController (the side stinger comes from the HUD music director)
    "S_GW_Chime":   ("sfx_confirm_s312_2", "ui", dict(keep=1.5, mom=-21.0)),
    "S_GW_Sombre":  ("sfx_clock_s320_0", "oneshot", dict(mom=-21.0, keep=2.4)),
    # majordome voice lines (Qwen3-TTS VoiceDesign; each checked by faster-whisper transcription, qa/asr_report.json)
    "VO_Welcome":    ("vo_welcome_s503_0", "vo", {}),
    "VO_Hunt":       ("vo_hunt_c602_0", "vo", {}),
    "VO_Thirty":     ("vo_thirty_c602_0", "vo", {}),
    "VO_Detectives": ("vo_detectives_c602_0", "vo", {}),
    "VO_Guests":     ("vo_guests_c602_0", "vo", {}),
    # ambiences (loops)
    "AMB_Crowd":   ("amb_crowd_s321_1", "amb", dict(lufs=-24.0)),
    "AMB_Glasses": ("amb_glasses_s322_1", "amb", dict(lufs=-28.0)),
    "AMB_Fire":    ("amb_fire_s323_1", "amb", dict(lufs=-24.0, mono=True)),
    "AMB_Rain":    ("amb_rain_s324_1", "amb", dict(lufs=-27.0)),
}


def src_path(cand):
    name = cand.rsplit("_c6", 1)[0] if "_c6" in cand else cand.rsplit("_s", 1)[0]
    return os.path.join(HERE, "gen", name, cand + ".flac")


def master(name, cand, kind, p):
    x, sr = A.load(src_path(cand))
    x = A.highpass(x, sr, 22)
    info = {"source": cand}
    if kind == "music":
        lp = A.find_music_loop(x, sr, p["min_len"], p["max_len"], xfade=0.5, skip_start=p["skip_start"], avoid_end=p["avoid_end"])
        info["loop"] = lp
        y = A.make_loop(x, sr, lp["start"], lp["end"], 0.5)
        if p.get("mono"):
            y = A.to_mono(y)
        y, g, lim = A.gain_to(y, sr, target_lufs=-16.0 + p.get("gain", 0.0), tp_ceiling=-1.0)
        info["seam"] = A.seam_report(y, sr)
    elif kind == "amb":
        s, e = A.find_ambience_loop(x, sr, xfade=2.0)
        y = A.make_loop(x, sr, s, e, 2.0)
        if p.get("mono"):
            y = A.to_mono(y)
        y, g, lim = A.gain_to(y, sr, target_lufs=p["lufs"], tp_ceiling=-3.0)
        info["seam"] = A.seam_report(y, sr)
    elif kind == "sting":
        y = A.trim_oneshot(x, sr, floor_db=-50, tail_fade=0.6)
        y, g, lim = A.gain_to(y, sr, target_lufs=p["lufs"], tp_ceiling=-1.0)
    elif kind == "ui":
        y = A.onset_peak_trim(x, sr, keep=p["keep"])
        y, g, lim = A.gain_to(y, sr, target_mom=p["mom"], tp_ceiling=-3.0)
    elif kind == "vo":
        from scipy import signal as sg
        y = A.trim_oneshot(A.to_mono(x), sr, floor_db=-45, tail_fade=0.12)
        rng = np.random.default_rng(3)
        n = int(0.9 * sr); t = np.arange(n) / sr
        ir = rng.standard_normal(n) * np.exp(-t * 6.9 / 0.9); ir[0] = 0
        ir = sg.lfilter(*sg.butter(2, 4000 / (sr / 2)), ir)
        wet = sg.fftconvolve(y[:, 0], ir)[: len(y) + n] / np.sqrt(np.sum(ir ** 2)) * 0.18
        dry = np.concatenate([y[:, 0], np.zeros(n)])
        L = min(len(dry), len(wet))
        y = (dry[:L] + wet[:L])[:, None]
        try:
            import librosa
            f0, vflag, _ = librosa.pyin(y[:, 0].astype(np.float32), fmin=60, fmax=300, sr=sr)
            info["median_f0_hz"] = round(float(np.nanmedian(f0)), 1)
        except Exception as e:
            info["median_f0_hz"] = str(e)[:80]
        y, g, lim = A.gain_to(y, sr, target_lufs=-17.0, tp_ceiling=-1.0)
    else:
        y = A.trim_oneshot(x, sr, floor_db=-55, tail_fade=0.25)
        if p.get("keep"):
            y = y[: int(p["keep"] * sr)]
            fo = int(0.05 * sr); y[-fo:] *= np.linspace(1, 0, fo)[:, None] ** 2
        if p.get("mono"):
            y = A.to_mono(y)
        y, g, lim = A.gain_to(y, sr, target_mom=p["mom"], tp_ceiling=-1.0)
    y = y - y.mean(axis=0)  # DC
    out = os.path.join(OUT, name + ".wav")
    A.save_wav(out, y, sr)
    y2, _ = A.load(out)
    info.update({"gain_db": g, "limited": lim, "after": A.metrics(y2, sr), "file": out, "kind": kind})
    A.spectrogram_png(os.path.join(QA, "final_" + name + ".png"), y2, sr, name)
    return info


def main():
    only = set(sys.argv[1:])
    rep_path = os.path.join(QA, "final_report.json")
    report = json.load(open(rep_path)) if os.path.exists(rep_path) else {}
    man = json.load(open(MAN, encoding="utf-8")) if os.path.exists(MAN) else {"assets": []}
    for name, (cand, kind, p) in SEL.items():
        if only and name not in only:
            continue
        info = master(name, cand, kind, p)
        report[name] = info
        a = info["after"]
        extra = ""
        if "loop" in info:
            extra = f" loop={info['loop']['length_s']}s tempo={info['loop']['tempo']} sim={info['loop']['sim']} seam/p95={info['seam']['seam_vs_p95']}"
        elif "median_f0_hz" in info:
            extra = f" f0={info['median_f0_hz']}Hz"
        elif "seam" in info:
            extra = f" seam/p95={info['seam']['seam_vs_p95']}"
        print(f"{name:16s} <- {cand:24s} dur={a['duration']:6.2f} lufs={a['lufs']:6.1f} mom={a['max_momentary_lufs']:6.1f} tp={a['true_peak_dbtp']:5.1f} "
              f"gain={info['gain_db']:+.1f} lim={info['limited']}{extra}", flush=True)
        side = json.load(open(src_path(cand)[:-5] + ".txt", encoding="utf-8"))
        man["assets"] = [m for m in man["assets"] if m["name"] != name]
        man["assets"].append({"name": name, "kind": "audio_" + kind, "status": "approved", "file": info["file"],
                              "source": {"file": src_path(cand), "model": side.get("model"), "seed": side.get("seed"),
                                         "batch_index": side.get("batch_index"), "prompt": side.get("prompt")},
                              "qa": {k: a[k] for k in ("duration", "lufs", "max_momentary_lufs", "true_peak_dbtp", "clipped_samples", "dc")},
                              "loop": info.get("loop"), "seam": info.get("seam")})
    json.dump(report, open(rep_path, "w"), indent=1, default=lambda o: o.item() if hasattr(o, "item") else str(o))
    json.dump(man, open(MAN, "w", encoding="utf-8"), indent=1, ensure_ascii=False, default=lambda o: o.item() if hasattr(o, "item") else str(o))


if __name__ == "__main__":
    main()
