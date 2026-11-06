"""Helpers for the voice scripts (AssetGen/audio/scripts/*.py, read by vox.py)."""


def dialogue(items, did, ga, gb, turns, voices=None, **kw):
    """A 2-4 turn conversation between speaker A (gender ga) and B (gender gb). turns: [("A"|"B", text) | ("A", text, reg)].
    voices: optional {"A"|"B": voice_id} when the text needs a given character."""
    for t, turn in enumerate(turns, 1):
        sp, text = turn[0], turn[1]
        reg = turn[2] if len(turn) > 2 else "neutral"
        extra = dict(kw)
        if voices and sp in voices:
            extra["voice"] = voices[sp]
        items.append(dict(cat="dialogue", dialogue_id=did, turn=t, speaker=sp, gender=ga if sp == "A" else gb, text=text,
                          reg=reg, whispered=reg == "whisper", **extra))


def lines(items, cat, specs, **kw):
    """Single lines: specs = [(gender|None, text) | (gender, text, reg) | (gender, text, reg, extra_dict)]."""
    for s in specs:
        g, text = s[0], s[1]
        reg = s[2] if len(s) > 2 else kw.get("reg", "neutral")
        extra = dict(kw); extra.pop("reg", None)
        if len(s) > 3:
            extra.update(s[3])
        items.append(dict(cat=cat, gender=g, text=text, reg=reg, whispered=reg == "whisper", **extra))
