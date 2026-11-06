"""Writes AssetGen/audio/scripts/_voicemap.json for the audio agent: {char_id: existing clone voice_id} when one of its
designed voices fits the character (each voice used by ONE character only), else {char_id: {gender, age, description}}
= a design request (one new voice per character, VOIX_ARCHITECTURE.md principle 2). Cards come from build_voice_script."""
import json, os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import build_voice_script as B

MAP = {'char_colonel': 'm4_colonel', 'char_comte': 'm1_baron', 'char_f_gown': 'f4_aviatrice', 'char_m_tailcoat': 'm6_dandy',
       'char_barman': 's1_barman', 'char_junkie': 's2_junkie', 'char_waiter': 's3_serveur',
       'char_bandit': 'b1_brute', 'char_bandit2': 'b2_voyou', 'char_kamikaze': 'k1_kamikaze', 'char_robot': 'r1_robot'}
assert len(set(MAP.values())) == len(MAP), 'a voice may belong to one character only'
S = json.load(open(os.path.join(HERE, 'voice_script.json'), encoding='utf-8'))
used = {l['voice_id'] for l in S['lines']} | {t['voice_id'] for d in S['dialogues'] for t in d['turns']}
out = {}
for v in S['voices']:
    c = v['voice_id']
    if c not in used:
        continue
    if c in MAP:
        out[c] = MAP[c]
    else:
        out[c] = {'gender': v['gender'], 'age': v['age'], 'description': v['card'], 'note_fr': v['personality'],
                  'display': v['display']}
p = os.path.join(os.path.dirname(HERE), 'scripts', '_voicemap.json')
json.dump(out, open(p, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
print(p, len(out), 'characters;', sum(isinstance(x, str) for x in out.values()), 'mapped,',
      sum(isinstance(x, dict) for x in out.values()), 'design requests:', [k for k, x in out.items() if isinstance(x, dict)])
