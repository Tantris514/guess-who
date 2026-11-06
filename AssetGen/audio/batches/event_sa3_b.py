"""Stable Audio 3 Medium, second pass: more scream/cry variety (male cries, female gasps, older voices), power-up and lasers."""
import json, os
DRY = " Close microphone, dry room, realistic recording, no music, no background noise."
SFX = " Realistic sound effect, close, no music, no voices."
J = [
 {"name": "panic_sa_cry_m", "seed": 804, "seconds": 2, "cands": 4, "prompt":
  "A man cries out in sudden shock: one short, sharp, frightened shout 'ah!', a real adult male human voice." + DRY},
 {"name": "panic_sa_gasp2_f", "seed": 805, "seconds": 2, "cands": 3, "prompt":
  "A woman gasps in horror: a sharp, loud, sudden intake of breath with a small frightened cry, a real human voice." + DRY},
 {"name": "panic_sa_scream_of", "seed": 806, "seconds": 3, "cands": 3, "prompt":
  "An older woman screams in terror: one short shrill shriek of fright, a real human voice." + DRY},
 {"name": "panic_sa_scream_om", "seed": 807, "seconds": 3, "cands": 3, "prompt":
  "An older man bellows in terror: one short, hoarse, panicked scream, a real adult male human voice." + DRY},
 {"name": "sfx_power_up2", "seed": 835, "seconds": 4, "cands": 3, "prompt":
  "A big old electrical dynamo spins up after a power cut: a heavy switch clunks, then a rising electric whine and hum getting higher and louder, "
  "buzzing light bulbs flicker back on." + SFX},
 {"name": "sfx_laser2", "seed": 836, "seconds": 2, "cands": 4, "prompt":
  "A retro 1950s science fiction ray gun shot: a single fast descending electronic 'pew' zap with a short metallic ring." + SFX},
]
json.dump(J, open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "event_sa3_b.json"), "w", encoding="utf-8"), indent=1)
print(len(J))
