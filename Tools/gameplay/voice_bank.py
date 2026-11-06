"""Voice bank builder (pure Python, no editor needed): reads every AssetGen/audio/final/*/*_report.json and returns the
rows the engine uses, sorted so that each category is one contiguous range of the bank (the director only scans the
range of the category it needs). Used by s31_reactions.py (import + class defaults), s39_voice_director.py (tables)
and Tools/qa/voice_log_check.py.

Rule (VOIX_ARCHITECTURE.md principle 2, the user, 2026-11-02 night): a voice IS a character. voice_id = char_id
(char_colonel, char_f_gown, ...); every NPC wearing that character speaks only its lines. Legacy voices of the first
panic bank are mapped to their character (LEGACY); other legacy guest voices belong to nobody, so their spoken lines
are dropped (their non-verbal rows stay, generic). Rows without a voice are kept only when non-verbal (generic screams).

Robust to partial data: a missing duration_s is read from the WAV, a missing cause is inferred from the text, a missing
speaker comes from the turn's voice, a dialogue is kept only when all its turns 1..N exist with exactly two different
voices. Texts are de-duplicated globally (normalised): a sentence is in the game once. Non-verbal rows (screams,
laughs, gasps, murmurs) keep no text and may repeat.

python -I -X utf8 voice_bank.py [fake_scale]   -> prints a summary (categories, voices, dialogues) without the editor
"""
import glob, json, os, re, unicodedata, wave

ROOT = r'J:\Projets\Unreal_Projects\Guess Who\AssetGen\audio\final'
MANIFEST = r'J:\Projets\Unreal_Projects\Guess Who\AssetGen\manifest.json'
# engine category ids (s31 CAT). Voice categories: 1..19 and 60..79; the rest are sound effects.
CAT = {'scream': 1, 'shout': 2, 'calm': 3, 'chatter': 4, 'reply': 5, 'attack_guest': 6, 'attack_bandit': 7, 'fire': 8,
       'fire_after': 9, 'blackout': 10, 'blackout_after': 11, 'kamikaze': 12, 'robot_voice': 13, 'piano_react': 14,
       'barman': 15, 'greet': 16, 'dialogue': 17, 'laugh': 18, 'gasp': 19,
       'explosion': 20, 'fire_loop': 21, 'power_down': 22, 'power_up': 23, 'robot_step': 24, 'servo': 25, 'laser': 26,
       'sting': 27, 'piano': 28, 'gunshot': 29, 'fire_whoosh': 30, 'fire_alarm': 31,
       'smoke_hiss': 32, 'gas_hiss': 33, 'shop_buy': 34, 'bomb_beep': 35, 'defuse': 36, 'trap_click': 37,
       'turret_fire': 38, 'turret_empty': 39, 'dance_music': 40,
       'ball_clack': 41, 'sword_swish': 42, 'sword_hit': 43, 'swap_whoosh': 44,
       'harp': 45, 'drums': 46, 'bass': 47, 'fart': 48, 'safe_open': 49,
       'kamikaze_guest': 60, 'robot_guest': 61, 'waiter': 62, 'junkie': 63, 'murmur': 64,
       'fart_react': 65, 'safe_react': 66, 'alarm_react': 67, 'greet_again': 68,
       # reactions asked by the feature agents (2026-11-03): pickups, shop, social
       'ghost_react': 69, 'sword_react': 70, 'ball_react': 71, 'bomb_near': 72, 'smoke_react': 73,
       'shrink_react': 74, 'defuse_react': 75, 'dance_end': 76, 'bar_toast': 77}
ALIAS = {'remark': 'chatter', 'robot': 'robot_voice', 'kamikaze_react': 'kamikaze_guest', 'robot_react': 'robot_guest',
         'serveur': 'waiter', 'serveuse': 'waiter', 'greeting': 'greet', 'answer': 'greet', 'again': 'greet_again'}
NCAT = 80                                    # CatFirst / CatCount array size
VOICE_CATS = {v for v in CAT.values() if v < 20 or 60 <= v < 80}
NONVERBAL_CATS = {'scream', 'laugh', 'gasp', 'murmur'}
STAFF_CATS = {'barman', 'waiter', 'junkie'}  # service phrases: unused first, then reused
# gameplay feedback ("cible détectée"), the kamikaze's own threats (an event comes back every round) and greetings (said
# by every guest all evening: the E key and the NPC pairs): may repeat, unused ones first, never within 20 s
REPEAT_CATS = {'robot_voice', 'kamikaze', 'greet', 'greet_again'}
CAUSE = {'generic': 0, 'gun': 1, 'fire': 2, 'explosion': 3, 'blackout': 4}
CAUSE_NAME = {v: k for k, v in CAUSE.items()}
# priority of a category when somebody asks for it (the director: P0 death .. P5 reactions)
PRI = {'scream': 1, 'shout': 1, 'attack_guest': 2, 'attack_bandit': 2, 'fire': 2, 'blackout': 2, 'kamikaze': 2,
       'robot_voice': 2, 'kamikaze_guest': 2, 'robot_guest': 2, 'calm': 3, 'fire_after': 3, 'blackout_after': 3,
       'chatter': 4, 'reply': 4, 'dialogue': 4, 'piano_react': 5, 'greet': 5, 'greet_again': 5, 'barman': 5,
       'waiter': 5, 'junkie': 5, 'laugh': 5, 'gasp': 5, 'murmur': 5, 'fart_react': 5, 'safe_react': 5, 'alarm_react': 5,
       'ghost_react': 5, 'sword_react': 5, 'ball_react': 5, 'shrink_react': 5, 'dance_end': 5, 'bar_toast': 4,
       'bomb_near': 3, 'smoke_react': 3, 'defuse_react': 3}
ALIAS.update({'alarm_pull': 'alarm_react', 'applause': 'dance_end', 'toast': 'bar_toast', 'bravo': 'dance_end'})
# first panic bank voices -> their character (the content agent, 2026-11-02 night); sa3_* = generic screams
LEGACY = {'m4_colonel': 'char_colonel', 'm1_baron': 'char_comte', 'b1_brute': 'char_bandit', 'b2_voyou': 'char_bandit2',
          'k1_kamikaze': 'char_kamikaze', 'r1_robot': 'char_robot',
          # the content agent's clone map (AssetGen/audio/scripts/_voicemap.json): same voice, so the same character
          'f4_aviatrice': 'char_f_gown', 'm6_dandy': 'char_m_tailcoat', 's1_barman': 'char_barman'}
# line contexts (report "context"): 1-2 social groups (said only there, s36 SocialMode 1 / 2); 3-8 staff moments
# (StaffSay; the sale line WorldSound(15/62/63) takes sale or context-free lines only); 9 smoke (coughs)
CONTEXT = {'dance': 1, 'bar': 2, 'open': 3, 'sale': 4, 'no_money': 5, 'danger_sold': 6, 'walk_away': 7,
           'detective_near': 8, 'smoke': 9}
GUN_WORDS = re.compile(r"\b(tir|tiré|tirer|tire|tirez|tirent|tireur|armes|armés|balle|balles|arme|armé|fusil|revolver|"
                       r"pistolet|abattu|coup de feu|coups de feu|flingue|détonation)\b", re.I)
FIRE_WORDS = re.compile(r"\b(feu|brûle|brûlent|brûler|flamme|flammes|fumée|incendie|cendres)\b", re.I)
BOOM_WORDS = re.compile(r"\b(explos\w*|bombe|boum|sauté|déflagration|souffle)\b", re.I)
DARK_WORDS = re.compile(r"\b(noir|lumière|lumières|vois rien|vois plus|panne|obscurité|bougie|électricité)\b", re.I)


def norm(s):
    s = unicodedata.normalize('NFKD', (s or '').lower())
    s = ''.join(c for c in s if not unicodedata.combining(c))
    return ' '.join(re.sub(r'[^a-z ]+', ' ', s).split())


def wav_duration(path):
    try:
        with wave.open(path, 'rb') as w:
            return w.getnframes() / float(w.getframerate() or 44100)
    except Exception:
        return 2.0


def infer_cause(text, gun):
    if gun or GUN_WORDS.search(text or ''):
        return CAUSE['gun']
    for rx, c in ((FIRE_WORDS, 'fire'), (BOOM_WORDS, 'explosion'), (DARK_WORDS, 'blackout')):
        if rx.search(text or ''):
            return CAUSE[c]
    return CAUSE['generic']


def char_voice(v):
    """A report voice_id -> the character it belongs to (None: nobody's voice)."""
    if not v:
        return None
    v = str(v).strip()
    if '\\' in v or '/' in v:                    # a path to AssetGen/voices/<char_id>/...: the folder is the id
        parts = [p for p in v.replace('\\', '/').split('/') if p]
        v = next((p for p in reversed(parts) if p.startswith('char_')), parts[-1] if parts else '')
    if v.startswith('char_'):
        return v
    return LEGACY.get(v)


SFX_BY_NAME = (('SFX_Event_Alarm', 'sting'), ('SFX_Explosion', 'explosion'), ('SFX_Fire_Crackle', 'fire_loop'),
               ('SFX_Fire_Whoosh', 'fire_whoosh'), ('SFX_Laser', 'laser'), ('SFX_Power_Down', 'power_down'),
               ('SFX_Power_Up', 'power_up'), ('SFX_Robot_Servo', 'servo'), ('SFX_Robot_Step', 'robot_step'),
               ('SFX_Piano', 'piano'), ('SFX_Gunshot', 'gunshot'))


def voice_id(e):
    """A manifest character's voice id (= its char id). Its "voice" field may be the path of
    AssetGen/voices/<char_id>/voice.json: the folder name is the id."""
    v = str(e.get('voice') or '').strip()
    if v and ('\\' in v or '/' in v or v.endswith('.json')):
        v = os.path.basename(os.path.dirname(v.replace('\\', '/')))
    return v or e['name']


def roster():
    """Character ids NPCs can wear, in s29's cast order (approved, rigged, outfits = roster)."""
    try:
        man = json.load(open(MANIFEST, encoding='utf-8'))
    except Exception:
        return []
    return [voice_id(e) for e in man.get('assets', [])
            if e.get('kind') == 'character' and e.get('status') == 'approved' and e.get('rig') and e.get('outfits') == 'roster']


def read_reports(root=ROOT):
    rows = []
    for rp in sorted(glob.glob(os.path.join(root, '*', '*_report.json'))):
        try:
            data = json.load(open(rp, encoding='utf-8'))
        except Exception as e:
            print('voice_bank: unreadable report', rp, e)
            continue
        entries = data if isinstance(data, list) else data.get('files', data.get('entries', list(data.values()) if isinstance(data, dict) else []))
        for e in entries:
            if isinstance(e, dict) and (e.get('file') or e.get('path')):
                rows.append((rp, e))
    return rows


def build(root=ROOT, fake=0):
    """-> dict(lines=[...], music=[paths], voices=[ids], vfem={}, dialogues=[...], skipped={}). A line is a dict:
    path, stem, cat, cat_id, fem, voice, text, dur, cause, dlg, turn, spk, nv, gun, wh, test, key."""
    music, lines, seen = [], [], set()
    dlg_rows = {}
    skipped = {'missing_file': 0, 'unknown_cat': 0, 'dup_text': 0, 'dup_of': 0, 'bad_dialogue': 0, 'nobody_voice': 0}
    for rp, e in read_reports(root):
        f = e.get('file') or e.get('path')
        f = f if os.path.isabs(f) else os.path.join(os.path.dirname(rp), f)
        if not os.path.exists(f):
            skipped['missing_file'] += 1
            continue
        stem = os.path.splitext(os.path.basename(f))[0]
        cat = str(e.get('category') or '').strip().lower()
        cat = ALIAS.get(cat, cat)
        if cat == 'music':
            music.append(f)
            continue
        if cat == 'sfx':
            cat = next((c for pre, c in SFX_BY_NAME if stem.startswith(pre)), '')
        if cat not in CAT:
            skipped['unknown_cat'] += 1
            continue
        if e.get('dup_of') or e.get('incomplete'):
            skipped['dup_of'] += 1
            continue
        g = str(e.get('gender') or '').lower()[:1]
        fem = {'m': 0, 'h': 0, 'f': 1}.get(g, 2)
        nv = bool(e.get('nonverbal')) or cat in NONVERBAL_CATS
        voiced = CAT[cat] in VOICE_CATS and not nv
        voice = char_voice(e.get('voice_id'))
        if voiced and voice is None:
            skipped['nobody_voice'] += 1           # a legacy voice no character owns: never in a character's mouth
            continue
        text = '' if nv else str(e.get('text') or '').strip()
        try:
            dur = float(e.get('duration_s'))
        except (TypeError, ValueError):
            dur = wav_duration(f)
        gun = bool(e.get('gun')) or bool(GUN_WORDS.search(text))
        c = e.get('cause')
        cause = CAUSE.get(str(c).lower(), None) if c else None
        if cause is None:
            cause = infer_cause(text, gun) if cat in ('shout', 'scream') or gun else CAUSE['generic']
        if gun:
            cause = CAUSE['gun']
        line = dict(path=f, stem=stem, cat=cat, cat_id=CAT[cat], fem=fem, voice=voice, text=text, dur=round(dur, 3),
                    cause=cause, dlg=None, turn=0, spk=0, nv=nv, gun=gun,
                    wh=bool(e.get('whispered')) or bool(e.get('murmured')), test=False,
                    key=e.get('line_id') or e.get('key') or stem,
                    ctx=CONTEXT.get(str(e.get('context') or '').strip().lower(), 0))
        if cat == 'dialogue':
            did = str(e.get('dialogue_id') or '')
            if not did:
                skipped['bad_dialogue'] += 1
                continue
            try:
                line['turn'] = int(e.get('turn') or 0)
            except (TypeError, ValueError):
                line['turn'] = 0
            sp = e.get('speaker')
            line['spk'] = None if sp is None else (1 if str(sp).upper().startswith('B') else 0)
            line['dlg'] = did
            dlg_rows.setdefault(did, []).append(line)
            continue
        k = norm(text)
        if k and k in seen:
            skipped['dup_text'] += 1
            continue
        if k:
            seen.add(k)
        lines.append(line)
    # dialogues: whole or nothing (turns 1..N, two different characters A / B, no sentence already in the game)
    dialogues = []
    for did in sorted(dlg_rows):
        rs = sorted(dlg_rows[did], key=lambda r: r['turn'])
        if rs and rs[0]['spk'] is None:            # no speaker field: A is the first turn's voice
            for r in rs:
                r['spk'] = 0 if r['voice'] == rs[0]['voice'] else 1
        turns = [r['turn'] for r in rs]
        va = {r['voice'] for r in rs if r['spk'] == 0}
        vb = {r['voice'] for r in rs if r['spk'] == 1}
        keys = [norm(r['text']) for r in rs]
        ok = (turns == list(range(1, len(rs) + 1)) and 2 <= len(rs) <= 6 and len(va) == 1 and len(vb) == 1
              and va != vb and None not in va | vb and all(keys) and len(set(keys)) == len(keys)
              and not any(k in seen for k in keys))
        if not ok:
            skipped['bad_dialogue'] += 1
            continue
        seen.update(keys)
        dialogues.append(did)
        lines.extend(rs)
    if fake:
        lines.extend(fake_lines(lines, fake))
    order = {d: i for i, d in enumerate(dialogues)}
    fake_dlgs = sorted({l['dlg'] for l in lines if l['test'] and l['dlg']})
    for d in fake_dlgs:
        order[d] = len(order)
    dialogues = dialogues + fake_dlgs
    lines.sort(key=sort_key(order))
    voices = sorted({l['voice'] for l in lines if l['voice']})
    vfem = {}
    for l in lines:
        if l['voice'] and l['fem'] != 2:
            vfem.setdefault(l['voice'], l['fem'])
    return dict(lines=lines, music=music, voices=voices, vfem=vfem, dialogues=dialogues, skipped=skipped)


def sort_key(order):
    """Bank order: category, then dialogue (turns together), then voice (no voice first), so that every (category,
    voice) is one contiguous block (VCVFirst / VCVCount)."""
    return lambda l: (l['cat_id'], order.get(l['dlg'], -1), l['turn'], l['voice'] or '', l['test'], l['stem'])


def tables(b):
    """The class-default arrays the director reads (lists, same order as b['lines'])."""
    L = b['lines']
    vidx = {v: i for i, v in enumerate(b['voices'])}
    # (category, voice + 1) blocks: a speaker's lines of a category, and the voiceless ones (generic screams) at + 0
    nv1 = len(b['voices']) + 1
    cvf, cvc = [0] * (NCAT * nv1), [0] * (NCAT * nv1)
    for i, l in enumerate(L):
        if l['cat_id'] < NCAT and l['cat'] != 'dialogue':
            key = l['cat_id'] * nv1 + vidx.get(l['voice'], -1) + 1
            if cvc[key] == 0:
                cvf[key] = i
            elif cvf[key] + cvc[key] != i:
                raise ValueError(f'bank not sorted by (category, voice) at {i}')
            cvc[key] += 1
    first, count = [0] * NCAT, [0] * NCAT
    for i, l in enumerate(L):
        c = l['cat_id']
        if c < NCAT:
            if count[c] == 0:
                first[c] = i
            count[c] += 1
    dfirst, dn, dva, dvb = [], [], [], []
    dlg_index = {}
    for i, l in enumerate(L):
        if l['cat'] == 'dialogue' and l['dlg'] not in dlg_index:
            dlg_index[l['dlg']] = len(dfirst)
            rs = [x for x in L if x['dlg'] == l['dlg']]
            dfirst.append(i)
            dn.append(len(rs))
            dva.append(vidx[next(x['voice'] for x in rs if x['spk'] == 0)])
            dvb.append(vidx[next(x['voice'] for x in rs if x['spk'] == 1)])
    # per character pair (A voice * NV + B voice): the dialogue codes written for it (code = dialogue * 2 + swapped)
    nv = len(b['voices'])
    by_pair = {}
    for d, (va, vb) in enumerate(zip(dva, dvb)):
        by_pair.setdefault(va * nv + vb, []).append(d * 2)
        by_pair.setdefault(vb * nv + va, []).append(d * 2 + 1)
    pstart, pcount, pcode = [0] * (nv * nv), [0] * (nv * nv), []
    for key in sorted(by_pair):
        pstart[key] = len(pcode)
        pcount[key] = len(by_pair[key])
        pcode.extend(by_pair[key])
    return dict(
        VPairStart=pstart, VPairCount=pcount, VPairCode=pcode, VCVFirst=cvf, VCVCount=cvc,
        VBVoice=[vidx.get(l['voice'], -1) for l in L], VBDlg=[dlg_index.get(l['dlg'], -1) for l in L],
        VBTurn=[l['turn'] for l in L], VBSpk=[l['spk'] or 0 for l in L], VBDur=[float(l['dur']) for l in L],
        VBCause=[l['cause'] for l in L], VBNV=[1 if l['nv'] else 0 for l in L], VBTest=[1 if l['test'] else 0 for l in L],
        VBWh=[1 if l['wh'] else 0 for l in L], VBText=[l['text'] for l in L], VCatFirst=first, VCatCount=count,
        VBCtx=[l.get('ctx', 0) for l in L],
        VVoiceName=list(b['voices']), VVoiceFem=[b['vfem'].get(v, 0) for v in b['voices']],
        VDlgFirst=dfirst, VDlgN=dn, VDlgVA=dva, VDlgVB=dvb,
        BankCat=[l['cat_id'] for l in L], BankFem=[l['fem'] for l in L], BankGun=[1 if l['gun'] else 0 for l in L],
        # 1 = a voice line (one mouth, subtitles); 2 = a voice line of the panic/event tiers (P0-P2): the music ducks
        BankVox=[(2 if PRI.get(l['cat'], 5) <= 2 else 1) if l['cat_id'] in VOICE_CATS else 0 for l in L])


def fake_lines(real, scale):
    """Test-only rows (BankTest = 1: never picked unless the server runs with -GWVoiceFakeBank) so the director can be
    exercised headless before the real content exists. Voices are the roster characters (what NPCs wear) and the event
    characters; they reuse one real sound file and are tagged in their text."""
    import random
    rnd = random.Random(1234)
    snd = next((l['path'] for l in real if l['cat'] == 'calm'), None) or next((l['path'] for l in real), None)
    if not snd:
        return []
    out = []
    fem = {}
    try:
        for e in json.load(open(MANIFEST, encoding='utf-8')).get('assets', []):
            if e.get('kind') == 'character':
                fem[voice_id(e)] = 1 if e.get('body') == 'quinn' else 0
    except Exception:
        pass
    guests = roster() or ['char_colonel', 'char_comte', 'char_f_gown', 'char_m_tailcoat', 'char_minuit', 'char_odette']

    def add(cat, per, cause=0, gun=False, nv=False, who=None):
        for v in (who or guests):
            for i in range(per):
                out.append(dict(path=snd, stem=f'TEST_{cat}_{cause}_{v}_{i:02d}', cat=cat, cat_id=CAT[cat], fem=fem.get(v, 0),
                                voice=v, text='' if nv else f'[test {cat}{"/" + CAUSE_NAME[cause] if cat == "shout" else ""} {v[5:]} {i + 1}]',
                                dur=round(rnd.uniform(1.2, 3.6), 2), cause=cause, dlg=None, turn=0, spk=0, nv=nv, gun=gun,
                                wh=cat == 'calm' and rnd.random() < 0.5, test=True, key=f'test_{cat}_{cause}_{v}_{i}'))
    s = scale
    n = 0
    for a in guests:
        for b in guests:
            if a >= b:
                continue
            for _ in range(max(1, int(4 * s))):
                n += 1
                for t in range(1, rnd.choice((2, 3, 3, 4)) + 1):
                    v = a if t % 2 else b
                    out.append(dict(path=snd, stem=f'TEST_dlg{n:03d}_{t}', cat='dialogue', cat_id=CAT['dialogue'], fem=fem.get(v, 0),
                                    voice=v, text=f'[test dialogue {n} {a[5:]}+{b[5:]}, tour {t}]', dur=round(rnd.uniform(1.4, 4.0), 2),
                                    cause=0, dlg=f'test{n:03d}', turn=t, spk=0 if t % 2 else 1, nv=False, gun=False, wh=False,
                                    test=True, key=f'test_dlg{n}_{t}'))
    p = max(1, int(round(s)))
    add('chatter', 12 * p); add('greet', 6 * p); add('greet_again', 3 * p); add('calm', 4 * p)
    add('shout', 3 * p, 1, gun=True); add('shout', 2 * p, 2); add('shout', 2 * p, 3); add('shout', 2 * p, 4); add('shout', 3 * p, 0)
    add('fire', 2 * p); add('blackout', 2 * p); add('attack_guest', 2 * p); add('kamikaze_guest', 1 * p); add('robot_guest', 1 * p)
    add('fire_after', 1 * p); add('blackout_after', 1 * p); add('piano_react', 2 * p); add('fart_react', 1 * p)
    add('laugh', 2, nv=True)
    add('kamikaze', 8, who=['char_kamikaze']); add('robot_voice', 6, who=['char_robot'])
    add('attack_bandit', 5, who=['char_bandit', 'char_bandit2'])
    return out


def summary(b):
    from collections import Counter
    L = b['lines']
    real = [l for l in L if not l['test']]
    print('lines', len(L), 'real', len(real), 'test', len(L) - len(real))
    print('by category (real):', dict(Counter(l['cat'] for l in real if l['cat_id'] in VOICE_CATS)))
    print('voices', len(b['voices']), b['voices'][:30])
    print('dialogues', len(b['dialogues']), 'roster', roster())
    print('shout causes:', dict(Counter(CAUSE_NAME[l['cause']] for l in real if l['cat'] == 'shout')))
    print('gun lines:', sum(l['gun'] for l in real), 'nonverbal:', sum(l['nv'] for l in real), 'skipped:', b['skipped'])
    print('distinct texts:', len({norm(l['text']) for l in real if l['text']}))
    t = tables(b)
    print('table sizes', {k: len(v) for k, v in t.items() if k.startswith('VDlg') or k == 'VVoiceName'})


if __name__ == '__main__':
    import sys
    summary(build(fake=float(sys.argv[1]) if len(sys.argv) > 1 else 0))
