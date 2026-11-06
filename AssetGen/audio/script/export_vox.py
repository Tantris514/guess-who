"""Exports voice_script.json (built by build_voice_script.py) as vox.py batch scripts: AssetGen/audio/scripts/cNN_*.py,
each defining ITEMS (cat, text, voice = char_id, gender, reg, line_id, whispered, nonverbal, gun, cause, dialogue_id,
turn, speaker, context). Batches are cut by priority (roster characters first: they are in the game tonight).
A batch file that already exists is NEVER rewritten (it may be rendering): new content goes to new batch numbers.
Category names follow vox.py / Tools/gameplay/voice_bank.py: chatter -> remark, kamikaze_react -> kamikaze_guest,
robot_react -> robot_guest. Usage: python -I -X utf8 export_vox.py   (prints the batches it wrote)"""
import json, os, re, sys, time

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(os.path.dirname(HERE), 'scripts')
LOG = r'J:\Projets\Unreal_Projects\Guess Who\Tools\agent_logs\voice.md'
ROSTER = ['char_colonel', 'char_comte', 'char_f_gown', 'char_m_tailcoat', 'char_minuit', 'char_odette']
EVENT_STAFF = ['char_barman', 'char_kamikaze', 'char_robot', 'char_bandit', 'char_bandit2', 'char_junkie', 'char_waiter']
CAT = {'chatter': 'remark', 'kamikaze_react': 'kamikaze_guest', 'robot_react': 'robot_guest'}
CORE = {'greet', 'greet_again', 'shout', 'calm'}


def item_of_line(l):
    it = dict(cat=CAT.get(l['category'], l['category']), text=l['text'], voice=l['voice_id'], gender=l['gender'],
              reg='design:laugh' if l['nonverbal'] else l['register'], line_id=l['line_id'], whispered=l['whispered'],
              nonverbal=l['nonverbal'], gun=l['gun'])
    if l['cause']:
        it['cause'] = l['cause']
    if l.get('context'):
        it['context'] = l['context']                 # 'dance' / 'bar' (social lines, from c13)
    return it


def items_of_dialogue(d):
    return [dict(cat='dialogue', text=t['text'], voice=t['voice_id'], gender=t['gender'], reg=t['register'],
                 line_id=t['line_id'], whispered=t['whispered'], nonverbal=False, gun=False,
                 dialogue_id=d['dialogue_id'], turn=t['turn'], speaker=t['speaker'],
                 **({'context': d['context']} if d.get('context') else {}))
            for t in d['turns']]


def plan(S):
    """[(batch name, description, items)] in priority order, covering every line and dialogue exactly once."""
    lines, dlgs = S['lines'], S['dialogues']
    new = [v['voice_id'] for v in S['voices'] if v.get('in_production')]
    newm = [c for c in new if next(v for v in S['voices'] if v['voice_id'] == c)['gender'] == 'm']
    newf = [c for c in new if c not in newm]
    roster_d = [d for d in dlgs if set(d['pair']) <= set(ROSTER)]
    cross_d = [d for d in dlgs if d not in roster_d and set(d['pair']) & set(ROSTER)]
    new_d = [d for d in dlgs if not set(d['pair']) & set(ROSTER)]
    sel = lambda chars, core: [l for l in lines if l['voice_id'] in chars and ((l['category'] in CORE) == core)]  # noqa: E731
    P = [('roster_dlg', 'dialogues between the 6 roster characters', [i for d in roster_d for i in items_of_dialogue(d)]),
         ('roster_core', 'roster greetings, follow-ups, cause shouts, calm + staff/event voices',
          [item_of_line(l) for l in sel(ROSTER, True)] + [item_of_line(l) for l in lines if l['voice_id'] in EVENT_STAFF]),
         ('roster_more', 'roster remarks, event lines, piano/fart reactions, laughs', [item_of_line(l) for l in sel(ROSTER, False)]),
         ('new_m_core', 'new male characters: greetings, follow-ups, shouts, calm', [item_of_line(l) for l in sel(newm, True)]),
         ('new_f_core', 'new female characters: greetings, follow-ups, shouts, calm', [item_of_line(l) for l in sel(newf, True)]),
         ('cross_dlg', 'dialogues roster x new characters', [i for d in cross_d for i in items_of_dialogue(d)]),
         ('new_dlg', 'dialogues between the new characters', [i for d in new_d for i in items_of_dialogue(d)]),
         ('new_m_more', 'new male characters: remarks, events, reactions, laughs', [item_of_line(l) for l in sel(newm, False)]),
         ('new_f_more', 'new female characters: remarks, events, reactions, laughs', [item_of_line(l) for l in sel(newf, False)])]
    return P


def main():
    S = json.load(open(os.path.join(HERE, 'voice_script.json'), encoding='utf-8'))
    os.makedirs(OUT, exist_ok=True)
    existing = {}                                   # line_id -> batch already exported (never exported twice)
    exported_text = {}
    for f in sorted(os.listdir(OUT)):
        if re.match(r'c\d\d_.*\.py$', f):
            ns = {}
            exec(compile(open(os.path.join(OUT, f), encoding='utf-8').read(), f, 'exec'), ns)
            for it in ns['ITEMS']:
                existing[it['line_id']] = f
                exported_text[it['line_id']] = it['text']
    n = max([int(f[1:3]) for f in os.listdir(OUT) if re.match(r'c\d\d_.*\.py$', f)] + [0])
    wrote = []
    # an id already exported must still mean the same text (ids drifted once when a wave was inserted, not appended)
    current = {i['line_id']: i['text'] for _, _, its in plan(S) for i in its}
    drift = [(k, exported_text[k], current.get(k)) for k in exported_text if current.get(k) != exported_text[k]]
    if drift:
        for d in drift[:10]:
            print('ID DRIFT', d)
        raise SystemExit(f'{len(drift)} exported line ids changed meaning: fix the wave order / texts before exporting')
    for name, desc, items in plan(S):
        items = [i for i in items if i['line_id'] not in existing]
        if not items:
            continue
        n += 1
        fn = f'c{n:02d}_{name}.py'
        chars = sorted({i['voice'] for i in items})
        with open(os.path.join(OUT, fn), 'w', encoding='utf-8') as fh:
            fh.write(f'"""{desc} ({len(items)} clips). Written by the voice director (content), '
                     f'source AssetGen/audio/script/wave_*.txt -> voice_script.json; voice = char_id (VOIX_ARCHITECTURE.md '
                     f'principle 2). Never edit: new content goes to a new batch."""\n')
            fh.write('ITEMS = [\n')
            for it in items:
                fh.write('    ' + repr(it) + ',\n')
            fh.write(']\n')
        for i in items:
            existing[i['line_id']] = fn
        wrote.append((fn, len(items), chars))
    if wrote:
        with open(LOG, 'a', encoding='utf-8') as lg:
            for fn, k, chars in wrote:
                lg.write(f"- {time.strftime('%Y-%m-%d %H:%M')} AssetGen/audio/scripts/{fn}: {k} clips; "
                         f"{', '.join(c.replace('char_', '') for c in chars)}\n")
    for w in wrote:
        print(w[0], w[1], len(w[2]), 'characters')
    print('total exported line ids', len(existing))


if __name__ == '__main__':
    main()
