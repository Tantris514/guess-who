"""Writes audio_1.json: Stable Audio 3 jobs (music loops, stingers, SFX, ambiences)."""
import json, os
NOV = " Instrumental only, no vocals, no singing."
J = [
 # ---------------------------------------------------------------- music
 {"name": "mus_menu", "seed": 301, "seconds": 95, "cands": 2, "prompt":
  "Mysterious 1930s jazz noir instrumental, slow swing at 84 BPM in D minor, muted trumpet melody, soft clarinet countermelody, smoky piano chords, "
  "walking upright double bass, brushed snare drums, warm vintage recording, elegant and suspenseful, intrigue at a masquerade ball in an English manor at night, "
  "steady tempo and constant energy from start to end." + NOV},
 {"name": "mus_lobby", "seed": 302, "seconds": 70, "cands": 2, "prompt":
  "Relaxed elegant 1930s lounge jazz, gentle swing at 96 BPM in F major, solo piano melody with soft brushed drums and upright bass, warm and intimate, "
  "waiting in the lobby of a grand manor before the ball, steady tempo and constant energy." + NOV},
 {"name": "mus_party", "seed": 303, "seconds": 95, "cands": 2, "prompt":
  "1930s big band dance music played on an old gramophone record, cheerful foxtrot at 120 BPM in B flat major, clarinets and saxophone section, muted trumpets, "
  "banjo rhythm, tuba bass, lo-fi mono gramophone sound with gentle vinyl crackle, ballroom dancing, steady tempo and constant energy." + NOV},
 {"name": "mus_hunt", "seed": 304, "seconds": 95, "cands": 2, "prompt":
  "Suspenseful 1930s film noir underscore, slow steady pulse at 90 BPM in C minor, low pizzicato double bass ostinato, tense tremolo strings, muted brass swells, "
  "soft ticking percussion, mysterious and ominous, a detective stalks a masked suspect, constant tension from start to end." + NOV},
 {"name": "mus_final", "seed": 305, "seconds": 70, "cands": 2, "prompt":
  "Intense urgent 1930s film noir chase music, fast driving 140 BPM in C minor, pounding timpani and pizzicato bass ostinato, frantic tremolo strings, "
  "staccato brass stabs, fast ticking clock percussion, high constant tension, time is running out, steady from start to end." + NOV},
 # ---------------------------------------------------------------- stingers
 {"name": "sting_reveal", "seed": 306, "seconds": 6, "cands": 3, "prompt":
  "Short dramatic mysterious orchestral stinger: a harp glissando rising into a sustained low brass and string chord with a soft cymbal swell, 1930s film score, a secret is revealed." + NOV},
 {"name": "sting_start", "seed": 307, "seconds": 5, "cands": 3, "prompt":
  "Short bold 1930s jazz big band fanfare stinger, three punchy brass hits and a drum fill, energetic, the hunt begins." + NOV},
 {"name": "sting_detectives", "seed": 308, "seconds": 8, "cands": 3, "prompt":
  "Short triumphant 1930s film noir brass fanfare finale, bold heroic major chord ending with a timpani roll, the detectives solved the case." + NOV},
 {"name": "sting_guests", "seed": 309, "seconds": 8, "cands": 3, "prompt":
  "Short playful elegant 1930s jazz big band finale flourish, swinging clarinet run and brass ending with a cheeky final chord, celebration at a masquerade ball." + NOV},
 # ---------------------------------------------------------------- SFX
 {"name": "sfx_hover", "seed": 310, "seconds": 2, "cands": 3, "prompt": "A single very short soft high crystal glass tap, one tiny delicate tick, clean, dry, isolated sound effect."},
 {"name": "sfx_click", "seed": 311, "seconds": 2, "cands": 3, "prompt": "A single short crisp click of a vintage brass light switch, one click, clean, dry, isolated sound effect."},
 {"name": "sfx_confirm", "seed": 312, "seconds": 3, "cands": 3, "prompt": "A single elegant ding of a small brass hotel service bell, one strike, clean, isolated sound effect."},
 {"name": "sfx_back", "seed": 313, "seconds": 2, "cands": 3, "prompt": "A single soft short wooden click of a small jewelry box lid closing, one click, clean, dry, isolated sound effect."},
 {"name": "sfx_type", "seed": 314, "seconds": 2, "cands": 3, "prompt": "A single keystroke of a 1930s mechanical typewriter, one key press, clean, dry, isolated sound effect."},
 {"name": "sfx_card", "seed": 315, "seconds": 2, "cands": 3, "prompt": "A quick swish of a playing card being flipped over fast, short paper whoosh, clean, isolated sound effect."},
 {"name": "sfx_shot", "seed": 316, "seconds": 3, "cands": 3, "prompt": "A single loud 1930s revolver gunshot fired indoors in a large marble hall, sharp crack with a natural reverb tail, isolated sound effect."},
 {"name": "sfx_empty", "seed": 317, "seconds": 2, "cands": 3, "prompt": "A revolver hammer clicking on an empty chamber, a single dry metallic click, isolated sound effect."},
 {"name": "sfx_fall", "seed": 318, "seconds": 3, "cands": 3, "prompt": "A person collapsing and falling onto a wooden parquet floor, one heavy body thud with a cloth rustle, isolated sound effect."},
 {"name": "sfx_gong", "seed": 319, "seconds": 8, "cands": 2, "prompt": "A large deep brass gong struck once, long shimmering resonant decay, isolated sound effect."},
 {"name": "sfx_clock", "seed": 320, "seconds": 8, "cands": 2, "prompt": "An old grandfather clock chiming three deep resonant bell strikes, isolated sound effect."},
 {"name": "amb_crowd", "seed": 321, "seconds": 45, "cands": 2, "prompt":
  "Ambience of a crowded elegant party in a large ballroom, indistinct murmur of many voices with no intelligible words, soft distant laughter, steady, continuous background ambience."},
 {"name": "amb_glasses", "seed": 322, "seconds": 30, "cands": 2, "prompt":
  "Ambience of champagne glasses gently clinking at a party, occasional toasts and light cutlery on porcelain, no voices, steady continuous background ambience."},
 {"name": "amb_fire", "seed": 323, "seconds": 40, "cands": 2, "prompt":
  "A crackling wood fireplace, gentle fire crackle and soft pops, warm and calm, steady continuous ambience, close perspective."},
 {"name": "amb_rain", "seed": 324, "seconds": 40, "cands": 2, "prompt":
  "Steady gentle rain against tall windows at night, soft patter on glass, calm continuous ambience, no thunder."},
]
json.dump(J, open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "audio_1.json"), "w", encoding="utf-8"), indent=1, ensure_ascii=False)
print(len(J))
