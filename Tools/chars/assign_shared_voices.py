"""Put every approved, rigged guest character in the cast and give those without recorded lines an existing voice of the same
gender (manifest "voice" = AssetGen/voices/<char_id>/voice.json; s29_gen_chars.py writes it to GenIds, the voice director reads it).
The user, 2026-11-06: no new voices, the new characters share the existing ones. Deterministic and idempotent; no editor needed.
python -I -X utf8 assign_shared_voices.py   then ue_run.py s29_gen_chars.py
"""
import json, random, shutil, sys, time
sys.path.insert(0, r'J:\Projets\Unreal_Projects\Guess Who\Tools\gameplay')
import voice_bank as VB

G = r'J:\Projets\Unreal_Projects\Guess Who\AssetGen'
MAN = G + r'\manifest.json'
NOT_GUESTS = {'char_bandit', 'char_bandit2', 'char_barman', 'char_junkie', 'char_kamikaze', 'char_robot', 'char_waiter',
              'char_detective'}
bank = VB.build()
pool = {0: [], 1: []}
for v in bank['voices']:
    if v not in NOT_GUESTS:
        pool[bank['vfem'].get(v, 0)].append(v)
man = json.load(open(MAN, encoding='utf-8'))
shutil.copy2(MAN, MAN + time.strftime('.bak-%Y%m%d-%H%M%S'))
added = shared = 0
next_i = {0: 0, 1: 0}
for f in pool:
    random.Random(1930 + f).shuffle(pool[f])
for e in man['assets']:
    if e.get('kind') != 'character' or e.get('status') != 'approved' or not e.get('rig'):
        continue
    if not e.get('outfits'):
        e['outfits'] = 'roster'
        added += 1
    if e['outfits'] != 'roster' or e['name'] in bank['voices'] or e.get('voice'):
        continue
    f = 1 if e.get('body') == 'quinn' else 0
    v = pool[f][next_i[f] % len(pool[f])]
    next_i[f] += 1
    e['voice'] = f'{G}\\voices\\{v}\\voice.json'
    shared += 1
json.dump(man, open(MAN, 'w', encoding='utf-8'), ensure_ascii=False, indent=2)
ids = VB.roster()
print('added to cast', added, 'given a shared voice', shared, 'cast', len(ids), 'distinct voices', len(set(ids)),
      'silent', [i for i in ids if i not in bank['voices']])
