"""Builds voice_script.json (the texts the audio agent renders) from the wave_*.txt sources in this folder.

Owner: the voice director (Tools/gameplay/s39_voice_director.py). Spec: VOIX_ARCHITECTURE.md (2026-11-02 night):
every voice is a CHARACTER (voice_id = char_id); an NPC wearing a character speaks only that character's lines;
dialogues are written for a pair of characters. Sources are only ever APPENDED (line ids are stable).

Source syntax ('#' comments):
  @dlg <char_A> <char_B> [topic]       a dialogue, then its turns:  A: text  /  B[gossip]: text
  @char <char_id>                      then that character's single lines:  <key>[<register>]: text
     keys: greet again remark calm piano fart laugh bark | shout.gun shout.fire shout.explosion shout.blackout
           shout.generic | fire blackout attack kamikaze robot (event lines) | fire_after blackout_after | barman
Default registers per key are in KEYS. Usage: python -I -X utf8 build_voice_script.py"""
import glob, json, os, re, unicodedata

HERE = os.path.dirname(os.path.abspath(__file__))
AUDIO = os.path.dirname(HERE)
ROOT = os.path.dirname(os.path.dirname(AUDIO))

# key -> (report category, cause, default register, nonverbal)
KEYS = {
    'greet': ('greet', None, 'warm', False), 'again': ('greet_again', None, 'neutral', False),
    'remark': ('chatter', None, 'neutral', False), 'calm': ('calm', None, 'awkward', False),
    'piano': ('piano_react', None, 'neutral', False), 'fart': ('fart_react', None, 'neutral', False),
    'laugh': ('laugh', None, 'laugh', True),
    'shout.gun': ('shout', 'gun', 'panic', False), 'shout.fire': ('shout', 'fire', 'panic', False),
    'shout.explosion': ('shout', 'explosion', 'panic', False), 'shout.blackout': ('shout', 'blackout', 'startled', False),
    'shout.generic': ('shout', 'generic', 'panic', False),
    'fire': ('fire', None, 'panic', False), 'blackout': ('blackout', None, 'startled', False),
    'attack': ('attack_guest', None, 'panic', False), 'kamikaze': ('kamikaze_react', None, 'panic', False),
    'robot': ('robot_react', None, 'panic', False), 'fire_after': ('fire_after', None, 'awkward', False),
    'blackout_after': ('blackout_after', None, 'awkward', False), 'barman': ('barman', None, 'neutral', False),
    'self.kamikaze': ('kamikaze', None, 'manic', False), 'self.robot': ('robot_voice', None, 'flat', False),
    'self.bandit': ('attack_bandit', None, 'threat', False),
}

# The 6 roster characters, the detective, staff and event characters (the 15 new ones come from AssetGen/chars/cast3.json)
CHARS = {
    'char_colonel': dict(gender='m', age=66, role='guest', display='Le Colonel',
        personality="Colonel de cavalerie en retraite, bourru et aboyeur, raconte Verdun à qui veut l'entendre (et à qui ne veut pas), "
                    "déteste le jazz, adore les chevaux et le cognac, sentimental sous la moustache.",
        card="A gruff retired French cavalry colonel in his mid-sixties, a harsh, gravelly, barking low voice, clipped military "
             "diction, loud and short-tempered but with a dry sense of humour."),
    'char_comte': dict(gender='m', age=70, role='guest', display='Le Comte',
        personality="Comte Vasilescu, vieil aristocrate roumain des Carpates, charme suave et un peu inquiétant, nocturne, ne mange "
                    "jamais, évite l'ail et les miroirs, humour noir très raffiné. Léger accent roumain (r roulés).",
        card="An elderly Romanian count in his seventies speaking French with a light Eastern European accent and rolled r's, "
             "a deep, velvety, slow and slightly sinister baritone, exquisitely polite, savouring every word."),
    'char_f_gown': dict(gender='f', age=30, role='guest', display='Sandra',
        personality="Sandra, mondaine en robe émeraude, trois fois fiancée et jamais mariée, reine des ragots, ironique et "
                    "séductrice, connaît le secret de tout le monde, ne supporte pas de ne pas être regardée.",
        card="A glamorous French socialite of about thirty, a smooth, warm mezzo-soprano voice with an amused, teasing tone, "
             "elegant Parisian diction, flirtatious and gossipy."),
    'char_m_tailcoat': dict(gender='m', age=35, role='guest', display='Victor',
        personality="Victor, gentleman en queue-de-pie, beau parleur, joueur et séducteur, criblé de dettes derrière son élégance, "
                    "vaniteux et drôle, cherche une héritière.",
        card="A charming French gentleman of about thirty-five, a smooth, bright baritone voice, quick and playful, a smooth "
             "talker with a confident smile in his voice."),
    'char_minuit': dict(gender='m', age=40, role='guest', display='Monsieur Minuit',
        personality="Monsieur Minuit, justicier masqué discret, laconique et grave, parle par phrases courtes et énigmatiques, "
                    "observe tout, veille, humour très sec.",
        card="A mysterious Frenchman of about forty, a low, quiet, grave and husky voice, slow and controlled, short cryptic "
             "sentences, almost a murmur, calm and intense."),
    'char_odette': dict(gender='f', age=28, role='guest', display='Odette',
        personality="Odette, vedette de cabaret montmartroise, gouailleuse et drôle, tutoie tout le monde, se moque gentiment des "
                    "riches, chaleureuse, accent parigot populaire.",
        card="A Parisian cabaret singer of about twenty-eight, a bright, slightly husky voice with a strong working-class "
             "Parisian (Montmartre) accent, cheeky, fast and warm, laughing easily."),
    'char_detective': dict(gender='m', age=45, role='detective', display='Le détective',
        personality="Détective en imperméable, sec, méthodique, peu bavard.",
        card="A dry, methodical French police detective in his forties, a flat, low, weary voice."),
    'char_barman': dict(gender='m', age=42, role='staff', display='Le barman',
        personality="Barman discret et pince-sans-rire, accent parisien populaire, vend tout et ne demande rien.",
        card="A friendly barman in his forties, a warm, relaxed, slightly hoarse baritone, working-class Parisian accent, "
             "discreet and witty."),
    'char_junkie': dict(gender='m', age=30, role='staff', display='Le junkie',
        personality="Revendeur nerveux planqué près des toilettes, débit pâteux, rires nerveux, paranoïaque.",
        card="A twitchy, wasted man of about thirty, a raspy, slurred, mumbling voice with nervous laughter, slightly paranoid."),
    'char_waiter': dict(gender='m', age=20, role='staff', display='Le serveur',
        personality="Jeune serveur poli et pressé.",
        card="A polite young waiter of about twenty, a clear, deferential male tenor voice, quick and formal."),
    'char_bandit': dict(gender='m', age=45, role='bandit', display='Le bandit',
        personality="Gangster brutal des bas-fonds parisiens.",
        card="A rough, menacing French gangster in his forties, a deep, hoarse, gravelly voice from the Paris underworld, "
             "working-class Parisian accent, brutal and threatening."),
    'char_bandit2': dict(gender='m', age=24, role='bandit', display='Le voyou',
        personality="Jeune voyou ricanant et nerveux.",
        card="A wiry, nasty young French hoodlum in his twenties, a raspy, nasal, sneering voice, fast, cocky and aggressive, "
             "Parisian street accent."),
    'char_kamikaze': dict(gender='m', age=35, role='kamikaze', display='Le kamikaze',
        personality="Fanatique exalté bardé de dynamite.",
        card="A crazed, wild-eyed Frenchman in his thirties, an unhinged, shrill, manic tenor voice, fanatical and exalted."),
    'char_robot': dict(gender='m', age=None, role='robot', display='Le robot',
        personality="Automate de sécurité, voix mécanique.",
        card="A very deep, slow, completely monotone male voice with no emotion at all, perfectly flat pitch, mechanical rhythm, "
             "every syllable evenly spaced and clearly articulated, like a 1930s science-fiction automaton."),
}

# English VoiceDesign cards for the 15 new characters (translated from cast3.json "voice")
CARDS_NEW = {
    'char_barnabe': "A dignified French butler of about sixty-five, a deep, calm, measured voice with impeccable formal diction, "
                    "short formal sentences, deadpan, a faint weary sigh, never raises his voice.",
    'char_rajan': "A cultured young Indian prince of about twenty-eight speaking very refined French with a light Indian accent, "
                  "a warm, velvety baritone, unhurried, courteous and charming, with a hint of royal irony.",
    'char_sonny': "A charismatic jazz bandleader of about thirty-five, a deep, warm, slightly raspy voice that swings, laughs "
                  "easily, confident, French with a light American accent and a few English words.",
    'char_ambroise': "An absent-minded old French archaeology professor of about seventy-two, a quavering but enthusiastic, "
                     "slightly high voice, an irregular pace that speeds up then stops, little stifled giggles.",
    'char_lucien': "A shy young French chauffeur of about twenty-four, a clear young male voice with a working-class Parisian "
                   "accent, fast when nervous, apologetic.",
    'char_tony': "A swaggering Italian-American gangster of about forty-five speaking approximate French with a strong Brooklyn "
                 "Italian accent, a deep, nasal, drawling voice, menacing under a friendly smile, throaty chuckles.",
    'char_tex': "A loud Texan oil millionaire of about fifty-five speaking French with a very strong Southern American accent, "
                "a big, booming, fat voice, boastful and jovial, a big laugh, talks too loud.",
    'char_morel': "A French ocean-liner captain of about fifty-eight, a deep, slightly gravelly old sailor's voice with a light "
                  "Breton accent, calm and authoritative, brief clear orders, slow storytelling.",
    'char_hortense_gown': "A haughty French duchess of about seventy-five, a high, quavering, very distinguished voice, pinched "
                          "aristocratic diction, cutting and indignant.",
    'char_vivienne_gown': "A young Hollywood starlet of about twenty-four speaking French with a charming American accent, a soft, "
                          "breathy, sugary voice, high little laughs, dramatic exclamations.",
    'char_ophelie_gown': "A mysterious young French widow of about thirty, a low, slow, velvety, almost whispered voice, "
                         "melancholic and ironic, long pauses.",
    'char_rosalie': "A bubbly young French chambermaid of about twenty-two, a lively, clear voice with a working-class northern "
                    "French accent, fast and chatty, little cries of surprise.",
    'char_lou_gown': "A magnetic blues singer of about thirty-five speaking French with a Southern American accent, a warm, deep, "
                     "smooth, slightly veiled female voice, slow and musical, motherly.",
    'char_clara': "A cheeky young Parisian newspaper reporter of about twenty-seven, a crisp, confident female voice, fast and "
                  "witty, a mocking tone, Parisian accent.",
    'char_mei_gown': "An elegant young Shanghai socialite of about twenty-six speaking very polished French with a light Chinese "
                     "accent, a soft, poised, melodious female voice, measured pace.",
}
WAVES = ['wave_n1.txt', 'wave_n2.txt', 'wave_r1.txt', 'wave_x1.txt', 'wave_r2.txt', 'wave_x2.txt', 'wave_s1.txt', 'wave_n3.txt']   # append only
STAFF_ROLES = {'char_barnabe': 'staff', 'char_lucien': 'staff', 'char_rosalie': 'staff'}   # in the roster, but staff


def load_cast3():
    p = os.path.join(AUDIO, '..', 'chars', 'cast3.json')
    out = {}
    if os.path.exists(p):
        for c in json.load(open(p, encoding='utf-8')).get('characters', []):
            v = c.get('voice', '')
            m = re.match(r'\s*(Homme|Femme), environ (\d+) ans\.\s*(.*)', v, re.S)
            cid = c.get('id') or c.get('name')
            out[cid] = dict(gender='m' if (m and m.group(1) == 'Homme') or c.get('body') == 'manny' else 'f',
                                age=int(m.group(2)) if m else None, role='guest', display=c.get('display', cid),
                                personality=(m.group(3) if m else v).strip(), card=CARDS_NEW.get(cid), in_production=True)
    return out


def norm(s):
    s = unicodedata.normalize('NFKD', s.lower())
    s = ''.join(c for c in s if not unicodedata.combining(c))
    return ' '.join(re.sub(r'[^a-z ]+', ' ', s).split())


def main():
    chars = dict(CHARS)
    for k, v in load_cast3().items():
        chars.setdefault(k, v)
    for k, r in STAFF_ROLES.items():
        if k in chars:
            chars[k]['role_note'] = 'roster (worn by NPCs and players), staff personality'
    dialogues, lines = [], []
    nlines = {}
    cur = None
    # ids are numbered in this order: APPEND new wave names at the end, never insert (alphabetical order shifted ids once)
    order = [os.path.join(HERE, f) for f in WAVES]
    extra = sorted(set(glob.glob(os.path.join(HERE, 'wave_*.txt'))) - set(order))
    assert not extra, f'add these waves to WAVES (at the end): {extra}'
    for src in order:
        for ln, raw in enumerate(open(src, encoding='utf-8'), 1):
            s = '' if raw.lstrip().startswith('#') else raw.strip()
            if not s:
                continue
            where = f'{os.path.basename(src)}:{ln}'
            if s.startswith('@dlg'):
                p = s.split()
                a, b = p[1], p[2]
                assert a in chars and b in chars and a != b, f'{where}: bad pair {a} {b}'
                did = f'CD{len(dialogues) + 1:04d}'
                ctx = next((w[1:] for w in p[3:] if w.startswith('!')), None)
                cur = {'kind': 'dlg', 'd': {'dialogue_id': did, 'pair': [a, b], 'topic': ' '.join(w for w in p[3:] if not w.startswith('!')),
                                            'speakers': {'A': a, 'B': b}, 'turns': []}}
                if ctx:
                    cur['d']['context'] = ctx
                dialogues.append(cur['d'])
                continue
            if s.startswith('@char'):
                c = s.split()[1]
                assert c in chars, f'{where}: unknown character {c}'
                cur = {'kind': 'char', 'c': c}
                continue
            m = re.match(r'^([A-Za-z_.]+)(?:@(\w+))?(?:\[(\w+)\])?\s*:\s*(.+)$', s)
            assert m and cur, f'{where}: cannot parse: {s}'
            key, lctx, reg, text = m.group(1), m.group(2), m.group(3), m.group(4).strip()
            if cur['kind'] == 'dlg':
                d = cur['d']
                assert key in ('A', 'B'), f'{where}: dialogue turns are A: / B:'
                t = len(d['turns']) + 1
                vid = d['speakers'][key]
                d['turns'].append({'line_id': f"{d['dialogue_id']}_{t}", 'turn': t, 'speaker': key, 'voice_id': vid,
                                   'gender': chars[vid]['gender'], 'text': text, 'register': reg or 'neutral',
                                   'whispered': reg == 'whisper'})
            else:
                assert key in KEYS, f'{where}: unknown key {key}'
                cat, cause, dreg, nv = KEYS[key]
                c = cur['c']
                short = c.replace('char_', '')
                k = f'{short}_{key.replace(".", "_")}'
                nlines[k] = nlines.get(k, 0) + 1
                r = reg or dreg
                lines.append({'line_id': f'L_{k}_{nlines[k]:02d}', 'category': cat, 'voice_id': c,
                              'gender': chars[c]['gender'], 'text': text, 'register': r, 'cause': cause,
                              'whispered': r == 'whisper', 'nonverbal': nv, 'gun': cause == 'gun'})
                if lctx:
                    lines[-1]['context'] = lctx
    for d in dialogues:
        assert 2 <= len(d['turns']) <= 4, f"{d['dialogue_id']} has {len(d['turns'])} turns"
    voices = [dict(voice_id=k, **{x: v.get(x) for x in ('gender', 'age', 'role', 'display', 'personality', 'card')},
                   in_production=bool(v.get('in_production'))) for k, v in chars.items()]
    out = {'version': 2, 'rule': 'voice_id = char_id; every NPC wearing a character speaks only its lines',
           'voices': voices, 'dialogues': dialogues, 'lines': lines}
    # duplicate texts: inside the script and against the legacy bank (panic report + the audio agent's legacy list)
    legacy = set()
    p = os.path.join(AUDIO, 'final', 'panic', 'panic_report.json')
    if os.path.exists(p):
        legacy |= {norm(e['text']) for e in json.load(open(p, encoding='utf-8')) if e.get('text')}
    lp = os.path.join(HERE, 'legacy_texts.json')
    if os.path.exists(lp):
        d = json.load(open(lp, encoding='utf-8'))
        legacy |= {norm(t if isinstance(t, str) else t.get('text', '')) for t in (d if isinstance(d, list) else d.get('texts', []))}
    # the other scripts in AssetGen/audio/scripts (not my cNN_ exports): their sentences are taken too
    sdir = os.path.join(AUDIO, 'scripts')
    for f in sorted(os.listdir(sdir)) if os.path.isdir(sdir) else []:
        if not f.endswith('.py') or f.startswith('_') or re.match(r'c\d\d_', f) or f in ('vox.py', 'vox_sched.py', 'voices_export.py'):
            continue
        try:
            import importlib.util, sys as _sys
            _sys.path.insert(0, sdir); _sys.path.insert(0, AUDIO)
            spec = importlib.util.spec_from_file_location('other_' + f[:-3], os.path.join(sdir, f))
            m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
            legacy |= {norm(it.get('text', '')) for it in m.ITEMS if not it.get('nonverbal')}
        except Exception as e:
            print('note: could not read', f, e)
    seen, dups = {}, 0
    for lid, t in [(t['line_id'], t['text']) for d in dialogues for t in d['turns']] + \
                  [(l['line_id'], l['text']) for l in lines if not l['nonverbal']]:
        n = norm(t)
        if n in seen:
            print('DUP in script', lid, seen[n], t); dups += 1
        if n in legacy:
            print('DUP legacy', lid, t); dups += 1
        seen[n] = lid
    json.dump(out, open(os.path.join(HERE, 'voice_script.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    per = {}
    for l in lines:
        per.setdefault(l['voice_id'], {}).setdefault(l['category'], 0)
        per[l['voice_id']][l['category']] += 1
    for d in dialogues:
        for t in d['turns']:
            per.setdefault(t['voice_id'], {}).setdefault('dialogue', 0)
            per[t['voice_id']]['dialogue'] += 1
    for c, v in per.items():
        print(f'{c:20s} {sum(v.values()):4d} {v}')
    pairs = {}
    for d in dialogues:
        k = '+'.join(sorted(d['pair']))
        pairs[k] = pairs.get(k, 0) + 1
    print('dialogues', len(dialogues), 'turns', sum(len(d['turns']) for d in dialogues), 'lines', len(lines),
          'clips', sum(len(d['turns']) for d in dialogues) + len(lines), '; pairs', len(pairs), '; duplicates', dups)


if __name__ == '__main__':
    main()
