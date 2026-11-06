"""Stable Audio 3: replacements for the big-band tracks with muted trumpets (MUS_Party, the reveal/party phase, and the
ballroom MUS_Gramophone): same 1930s dance feel, but strings, piano and clarinet only."""
import json, os
NOV = " Instrumental only, no vocals, no singing, no trumpets, no brass."
J = [
 {"name": "mus_party_soft", "seed": 341, "seconds": 95, "cands": 2, "prompt":
  "Elegant soft 1930s ballroom dance music, gentle foxtrot at 112 BPM in B flat major, lush warm string section, sweet clarinet melody, "
  "light stride piano, upright double bass, soft brushed drums, refined and cheerful, a masked ball in an English manor, "
  "steady tempo and constant energy from start to end." + NOV},
 {"name": "mus_hunt_soft", "seed": 343, "seconds": 95, "cands": 2, "prompt":
  "Suspenseful 1930s film noir underscore without brass, slow steady pulse at 90 BPM in C minor, low pizzicato double bass ostinato, "
  "tense tremolo strings, a sparse low clarinet line, soft piano notes, quiet ticking percussion, mysterious, a detective stalks a masked "
  "suspect, constant tension from start to end." + NOV},
 {"name": "mus_gramophone_soft", "seed": 342, "seconds": 95, "cands": 2, "prompt":
  "1930s dance record played on an old gramophone: gentle foxtrot at 112 BPM in B flat major, strings, clarinet and piano, upright bass, "
  "soft brushes, lo-fi mono gramophone sound with gentle vinyl crackle, steady tempo and constant energy from start to end." + NOV},
]
json.dump(J, open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "music_soft.json"), "w", encoding="utf-8"), indent=1)
print(len(J))
