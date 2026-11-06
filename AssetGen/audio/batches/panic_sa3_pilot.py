"""Stable Audio 3 Medium pilot (audiobatch.py): human screams / gasps (to compare with Qwen3-TTS) and the grand piano crash."""
import json, os
DRY = " Close microphone, dry room, realistic recording, no music, no background noise."
PIANO = (" Recorded in a large wooden ballroom, realistic acoustic grand piano with real strings and felt hammers, loud and startling,"
         " no other instruments, no melody.")
J = [
 {"name": "panic_sa_scream_f", "seed": 801, "seconds": 3, "cands": 4, "prompt":
  "A woman screams in terror: one short, piercing, high-pitched scream of fright, a real human voice." + DRY},
 {"name": "panic_sa_scream_m", "seed": 802, "seconds": 3, "cands": 4, "prompt":
  "A man yells in sudden terror: one short loud panicked scream, a real adult male human voice." + DRY},
 {"name": "panic_sa_gasp_f", "seed": 803, "seconds": 3, "cands": 3, "prompt":
  "A woman gasps loudly in shock and lets out a short frightened cry, a real human voice." + DRY},
 {"name": "piano_crash_low", "seed": 811, "seconds": 5, "cands": 3, "prompt":
  "Someone violently slams both forearms down on the low bass keys of an old grand piano: one loud dissonant cluster of many keys at once, "
  "held for about one second, then the low strings ring out and slowly decay with a long resonant sustain." + PIANO},
 {"name": "piano_crash_mid", "seed": 812, "seconds": 5, "cands": 3, "prompt":
  "Someone violently bangs both fists on the middle keys of an old grand piano: one harsh, loud dissonant cluster chord of many notes at once, "
  "held for about one second, then the strings ring out and decay." + PIANO},
 {"name": "piano_crash_double", "seed": 813, "seconds": 5, "cands": 3, "prompt":
  "Two quick violent slams of both fists on the keys of an old grand piano, bang bang, two loud dissonant clusters of many notes half a second apart, "
  "then the strings ring out and decay." + PIANO},
]
json.dump(J, open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "panic_sa3_pilot.json"), "w", encoding="utf-8"), indent=1)
print(len(J))
