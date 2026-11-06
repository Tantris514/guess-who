"""Stable Audio 3 Medium (audiobatch.py): event SFX and event music loops."""
import json, os
NOV = " Instrumental only, no vocals, no singing."
SFX = " Realistic sound effect, close, no music, no voices."
J = [
 {"name": "sfx_explosion", "seed": 821, "seconds": 6, "cands": 3, "prompt":
  "A huge explosion inside a grand mansion ballroom: a deep thunderous boom, shattering glass and chandeliers, falling debris and rubble." + SFX},
 {"name": "sfx_fire_whoosh", "seed": 822, "seconds": 4, "cands": 3, "prompt":
  "A fire suddenly ignites with a loud whoosh: flames burst up and roar." + SFX},
 {"name": "sfx_fire_crackle", "seed": 823, "seconds": 25, "cands": 2, "prompt":
  "A large fire burning steadily: crackling and popping wood, roaring flames, constant and even from start to end." + SFX},
 {"name": "sfx_power_down", "seed": 824, "seconds": 4, "cands": 3, "prompt":
  "Old 1930s electrical power failure: a heavy knife switch clunks off, the electric hum winds down and dies, then silence." + SFX},
 {"name": "sfx_power_up", "seed": 825, "seconds": 4, "cands": 3, "prompt":
  "Old 1930s electricity coming back on: a heavy switch clunks on, then a rising electric hum and buzzing light filaments." + SFX},
 {"name": "sfx_robot_steps", "seed": 826, "seconds": 10, "cands": 2, "prompt":
  "Heavy metallic robot footsteps: a giant iron automaton walks slowly on a wooden floor, loud separate clanking steps with a short hydraulic hiss, one step per second." + SFX},
 {"name": "sfx_servo", "seed": 827, "seconds": 3, "cands": 3, "prompt":
  "A mechanical servo motor whirring: a robot arm moves, electric motor whine and small gears, short." + SFX},
 {"name": "sfx_laser", "seed": 828, "seconds": 2, "cands": 4, "prompt":
  "A retro science fiction ray gun firing: one short electric laser zap, 1950s space movie sound effect." + SFX},
 {"name": "sfx_alarm_sting", "seed": 829, "seconds": 4, "cands": 3, "prompt":
  "A short sudden orchestral alarm sting: one loud dissonant brass stab with a timpani hit, 1930s film score, danger." + NOV},
 {"name": "mus_ev_attack", "seed": 831, "seconds": 70, "cands": 2, "prompt":
  "Frantic 1930s film noir action music, fast 152 BPM in D minor, stabbing staccato brass, racing tremolo strings, pounding timpani and snare drum, "
  "chaotic and urgent, a gang of bandits storms a masked ball, constant energy from start to end." + NOV},
 {"name": "mus_ev_fire", "seed": 832, "seconds": 70, "cands": 2, "prompt":
  "Urgent dramatic 1930s orchestral music, 132 BPM in E minor, swirling rising string runs, alarm-like brass calls, rolling timpani, "
  "a fire spreads through the manor, steady tempo and constant energy from start to end." + NOV},
 {"name": "mus_ev_blackout", "seed": 833, "seconds": 70, "cands": 2, "prompt":
  "Creepy suspenseful 1930s film score, slow 72 BPM in B minor, low pizzicato double bass, eerie tremolo strings, soft celesta notes and muted brass, "
  "groping in the dark during a power cut, quiet constant tension from start to end." + NOV},
 {"name": "mus_ev_robot", "seed": 834, "seconds": 70, "cands": 2, "prompt":
  "Menacing 1930s science-fiction serial music, heavy mechanical march at 96 BPM in C minor, low brass ostinato, eerie theremin melody, "
  "clanking metallic percussion, ominous and relentless, constant energy from start to end." + NOV},
]
json.dump(J, open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "event_sa3.json"), "w", encoding="utf-8"), indent=1)
print(len(J))
