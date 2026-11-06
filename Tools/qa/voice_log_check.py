"""Checks a game log against the voice rules (VOIX_ARCHITECTURE.md, Tools/gameplay/s39_voice_director.py).

Reads the server's "GW: VOX ..." lines (one per line spoken), VOXCONV / VOXCAUSE / VOXDROP / VOXCUT / VOXTALK / VOXWALK
and the player positions VOXP (-GWVoiceTest logs them every second), then reports:
  - repeats: a sentence said twice (text or bank line), except non-verbal sounds, staff and the robot's feedback;
  - cause: a gun line without a gunshot context, a shout whose cause is not the panic's cause;
  - spacing: ambient conversations closer than 15 s in one listening area, event lines closer than 6 s,
    more than 2 alarm shouts per area per 12 s;
  - overlap: how many voices play at once around a player (max, distribution), the same voice twice at once;
  - voices: a speaker with two voices, a line not in its speaker's voice, a dialogue with one voice;
  - distance: lines spoken far from every player;
  - Blueprint errors (Accessed None, runtime errors, script warnings).
Usage: python -I -X utf8 voice_log_check.py <log> [--json out.json]   (exit code 1 if a hard rule is broken)
"""
import json, math, re, sys
from collections import Counter, defaultdict

R_AREA = 1300.0
REPEATABLE_CATS = {12, 13, 15, 16, 62, 63, 68}   # kamikaze, robot feedback, barman, greetings, waiter, junkie
NONVERBAL_CATS = {1, 18, 19, 64}
NUM = r'(-?[\d.]+(?:e[-+]?\d+)?)'
VEC = r'X=' + NUM + r' Y=' + NUM + r' Z=' + NUM


def fnum(s):
    try:
        return float(s)
    except (TypeError, ValueError):
        return float('nan')


def kv(line, key, rx=r'(\S+)'):
    m = re.search(r'\b' + key + '=' + rx, line)
    return m.group(1) if m else None


def parse(path):
    vox, conv, cause, drops, cuts, talks, walks, pos, tests, errors = [], [], [], [], [], [], [], [], [], Counter()
    for raw in open(path, encoding='utf-8', errors='replace'):
        if 'Accessed None' in raw:
            errors['Accessed None'] += 1
        if 'Blueprint Runtime Error' in raw:
            errors['Blueprint Runtime Error'] += 1
        if 'LogScript: Error' in raw:
            errors['LogScript: Error'] += 1
        if 'LogScript: Warning' in raw:
            errors['LogScript: Warning'] += 1
        i = raw.find('GW: VOX')
        if i < 0:
            j = raw.find('GW: VOXTEST')
            continue
        s = raw[i + 4:].rstrip('\n')
        if s.startswith('VOX '):
            t = kv(s, 'text', r'(.*)$')
            m = re.search(r'loc=' + VEC, s)
            vox.append(dict(t=fnum(kv(s, 't')), pri=int(fnum(kv(s, 'pri'))), cat=int(fnum(kv(s, 'cat'))),
                            cause=int(fnum(kv(s, 'cause'))), conv=int(fnum(kv(s, 'conv'))), idx=int(fnum(kv(s, 'idx'))),
                            dur=fnum(kv(s, 'dur')), voice=kv(s, 'voice'), svoice=kv(s, 'svoice'),
                            nv=kv(s, 'nv') in ('1', 'true'), gun=kv(s, 'gun') in ('1', 'true'),
                            test=kv(s, 'test') in ('1', 'true'), kind=kv(s, 'kind'), pd=fnum(kv(s, 'pd')),
                            loc=tuple(map(fnum, m.groups())) if m else None, spk=kv(s, 'spk'), text=(t or '').strip()))
        elif s.startswith('VOXCONV'):
            conv.append(dict(t=fnum(kv(s, 't')), conv=int(fnum(kv(s, 'conv'))), dlg=kv(s, 'dlg'), va=kv(s, 'va'),
                             turns=int(fnum(kv(s, 'turns'))) if kv(s, 'turns') else None,
                             vb=kv(s, 'vb'), A=kv(s, 'A'), B=kv(s, 'B'), length=fnum(kv(s, 'len'))))
        elif s.startswith('VOXCAUSE'):
            cause.append(dict(t=fnum(kv(s, 't')), cause=int(fnum(kv(s, 'cause'))), src=kv(s, 'src')))
        elif s.startswith('VOXDROP'):
            drops.append(dict(t=fnum(kv(s, 't')), why=kv(s, 'why')))
        elif s.startswith('VOXCUT'):
            cuts.append(dict(t=fnum(kv(s, 't')), by=kv(s, 'by'), spk=kv(s, 'spk')))
        elif s.startswith('VOXTALK'):
            talks.append(s)
        elif s.startswith('VOXWALK'):
            walks.append(s)
        elif s.startswith('VOXP '):
            m = re.search(r'loc=' + VEC, s)
            if m:
                pos.append(dict(t=fnum(kv(s, 't')), p=kv(s, 'p'), loc=tuple(map(fnum, m.groups())),
                                ev=int(fnum(kv(s, 'ev'))), panic=kv(s, 'panic') in ('true', '1')))
        elif s.startswith('VOXTEST'):
            tests.append(s)
    return dict(vox=vox, conv=conv, cause=cause, drops=drops, cuts=cuts, talks=talks, walks=walks, pos=pos,
                tests=tests, errors=errors)


def dist(a, b):
    return math.dist(a, b) if a and b else float('inf')


def players_at(pos, t):
    """Each player's last known position at time t (VOXP every second)."""
    last = {}
    for p in pos:
        if p['t'] > t + 0.6:
            break
        last[p['p']] = p['loc']
    return last


def event_at(pos, t):
    ev = 0
    for p in pos:
        if p['t'] > t + 0.6:
            break
        ev = p['ev']
    return ev


def check(d):
    V = sorted(d['vox'], key=lambda x: x['t'])
    # a line cut by a more urgent one (VOXCUT: faded out) stops there
    for c in d['cuts']:
        for v in reversed(V):
            if v['spk'] == c.get('spk') and v['t'] <= c['t'] < v['t'] + v['dur']:
                v['dur'] = max(0.0, c['t'] - v['t'])
                break
    pos = sorted(d['pos'], key=lambda x: x['t'])
    # one mouth: a speaker's new line fades out the line it was still saying (OnRep_Cue)
    last = {}
    for v in V:
        p = last.get(v['spk'])
        if p is not None and p['t'] + p['dur'] > v['t'] and v['spk'] not in (None, 'world'):
            p['dur'] = max(0.0, v['t'] - p['t'])
        last[v['spk']] = v
    out = {'lines': len(V), 'errors': dict(d['errors'])}
    hard = []
    # ---- repeats
    once = [v for v in V if not v['nv'] and v['cat'] not in REPEATABLE_CATS and v['cat'] not in NONVERBAL_CATS]
    texts = Counter(v['text'] for v in once if v['text'])
    idxs = Counter(v['idx'] for v in once)
    out['repeated_texts'] = {t: n for t, n in texts.items() if n > 1}
    out['repeated_idx'] = sum(1 for n in idxs.values() if n > 1)
    if out['repeated_texts'] or out['repeated_idx']:
        hard.append('repeats')
    nvrep = 0
    lastnv = []
    for v in V:
        if v['nv']:
            if v['idx'] in lastnv[-3:]:
                nvrep += 1
            lastnv.append(v['idx'])
    out['nonverbal_back_to_back'] = nvrep
    # ---- cause
    causes = sorted(d['cause'], key=lambda c: c['t'])

    def cause_before(t, window=20.0):
        cs = [c for c in causes if t - window <= c['t'] <= t + 0.05]
        return cs[-1]['cause'] if cs else None
    gun_bad, cause_bad = [], []
    for v in V:
        if v['gun']:
            ok = cause_before(v['t']) == 1 or (event_at(pos, v['t']) == 1 and v['cat'] in (6, 7))
            if not ok:
                gun_bad.append((round(v['t'], 1), v['text']))
        if v['cat'] == 2 and v['cause'] != 0:
            c = cause_before(v['t'], 15.0)
            if c is not None and c != v['cause']:
                cause_bad.append((round(v['t'], 1), v['cause'], c, v['text']))
    out['gun_line_without_gunshot'] = gun_bad
    out['shout_cause_mismatch'] = cause_bad
    if gun_bad or cause_bad:
        hard.append('cause')
    # ---- spacing, per listening area (around the player who was nearest the speaker)
    convs = defaultdict(list)
    for v in V:
        if v['pri'] == 4 and v['conv'] > 0:
            convs[v['conv']].append(v)
    spans = sorted((min(x['t'] for x in vs), max(x['t'] + x['dur'] for x in vs), vs[0]['loc']) for vs in convs.values())
    amb_gaps = []

    def in_same_area(t, a, b):
        """a listening area is centred on a player: both places within R of where a player stood at time t"""
        pl = players_at(pos, t)
        if not pl:
            return dist(a, b) < R_AREA
        return any(dist(a, p) < R_AREA and dist(b, p) < R_AREA for p in pl.values())
    for i in range(1, len(spans)):
        s, e, loc = spans[i]
        prev = [p for p in spans[:i] if in_same_area(s, p[2], loc)]
        if prev:
            amb_gaps.append(s - max(p[1] for p in prev))
    out['ambient_conversations'] = len(spans)
    out['ambient_gap_min'] = round(min(amb_gaps), 1) if amb_gaps else None
    out['ambient_gaps_below_14s'] = sum(1 for g in amb_gaps if g < 14.0)
    out['ambient_overlaps'] = sum(1 for g in amb_gaps if g < 0)
    if out['ambient_overlaps']:
        hard.append('ambient overlap')
    p2 = [v for v in V if v['pri'] == 2 and v['kind'] in ('0', None)]
    ev_gaps = []
    for i in range(1, len(p2)):
        prev = [p for p in p2[:i] if in_same_area(p2[i]['t'], p['loc'], p2[i]['loc'])]
        if prev:
            ev_gaps.append(p2[i]['t'] - (prev[-1]['t'] + prev[-1]['dur']))
    out['event_lines'] = len(p2)
    out['event_gap_min'] = round(min(ev_gaps), 1) if ev_gaps else None
    out['event_gaps_below_5s'] = sum(1 for g in ev_gaps if g < 5.0)
    shouts = [v for v in V if v['cat'] == 2]
    worst = 0
    for v in shouts:
        n = sum(1 for w in shouts if 0 <= v['t'] - w['t'] < 12.0 and dist(w['loc'], v['loc']) < R_AREA)
        worst = max(worst, n)
    out['shouts'] = len(shouts)
    out['max_shouts_per_area_12s'] = worst
    # ---- overlap around each player
    sim = Counter()
    same_voice = 0
    worst_moments = []
    for v in V:
        t = v['t'] + 0.05
        for p, ploc in players_at(pos, t).items():
            playing = [w for w in V if w['t'] <= t < w['t'] + w['dur'] and dist(w['loc'], ploc) < R_AREA]
            if v in playing:
                sim[len(playing)] += 1
                # the line's own voice: generic (voiceless) screams of two victims wearing the same character are not
                # "the same voice talking twice"
                vs = Counter(w['voice'] for w in playing if w['voice'] not in (None, '-', 'world'))
                if any(n > 1 for n in vs.values()):
                    same_voice += 1
                if len(playing) >= 3:
                    worst_moments.append((round(t, 1), p, [(w['pri'], w['cat'], w['svoice']) for w in playing]))
    out['simultaneous_voices_hist'] = dict(sorted(sim.items()))
    out['max_simultaneous'] = max(sim) if sim else 0
    out['same_voice_at_once'] = same_voice
    out['worst_moments'] = worst_moments[:8]
    if same_voice:
        hard.append('same voice twice at once')
    # ---- voices
    by_spk = defaultdict(set)
    wrong = []
    for v in V:
        if v['svoice'] and v['svoice'] not in ('world',):
            by_spk[v['spk']].add(v['svoice'])
        if not v['nv'] and v['voice'] not in (None, '-') and v['svoice'] not in ('world',) and v['voice'] != v['svoice']:
            wrong.append((round(v['t'], 1), v['spk'], v['voice'], v['svoice']))
    out['speakers'] = len(by_spk)
    out['speakers_with_two_voices'] = {k: sorted(s) for k, s in by_spk.items() if len(s) > 1}
    out['line_not_in_speaker_voice'] = wrong
    out['one_voice_dialogues'] = [c['conv'] for c in d['conv'] if c['va'] == c['vb']]
    # ---- dialogue timing: gaps between turns (written 0.2-0.55 s), conversations cut short by a more urgent line
    gaps, cut, alternate_bad = [], 0, 0
    turns_by_conv = defaultdict(list)
    for v in V:
        if v['cat'] == 17:
            turns_by_conv[v['conv']].append(v)
    for c in d['conv']:
        ts = sorted(turns_by_conv.get(c['conv'], []), key=lambda x: x['t'])
        want = int(fnum(re.search(r'turns=(\d+)', str(c)).group(1))) if re.search(r'turns=(\d+)', str(c)) else None
        for a, b in zip(ts, ts[1:]):
            gaps.append(b['t'] - (a['t'] + a['dur']))
            if a['spk'] == b['spk']:
                alternate_bad += 1
        if c.get('turns') and len(ts) < c['turns']:
            cut += 1
    out['turn_gap_min'] = round(min(gaps), 2) if gaps else None
    out['turn_gap_max'] = round(max(gaps), 2) if gaps else None
    out['same_speaker_twice_in_a_row'] = alternate_bad
    out['conversations_cut'] = cut
    if wrong or out['one_voice_dialogues']:
        hard.append('voices')
    # ---- distance
    far = [v for v in V if v['pd'] == v['pd'] and v['pd'] > R_AREA and v['pri'] > 0 and v['kind'] == '0']
    out['lines_far_from_players'] = len(far)
    out['pd_median'] = round(sorted(v['pd'] for v in V if v['pd'] == v['pd'])[len(V) // 2], 0) if V else None
    # ---- summary
    out['by_priority'] = dict(sorted(Counter(v['pri'] for v in V).items()))
    out['by_category'] = dict(sorted(Counter(v['cat'] for v in V).items()))
    out['conversations'] = len(d['conv'])
    out['dialogue_turns'] = sum(1 for v in V if v['cat'] == 17)
    out['talks'] = len([t for t in d['talks'] if 'step=' in t])
    out['talk_refusals'] = len([t for t in d['talks'] if 'step=' not in t])
    out['walk_overs'] = len([w for w in d['walks'] if 'gave up' not in w])
    out['walk_gave_up'] = len([w for w in d['walks'] if 'gave up' in w])
    out['drops'] = dict(Counter(x['why'] for x in d['drops']))
    out['cuts'] = len(d['cuts'])
    out['panics'] = {f'{src}/cause{c}': n for (src, c), n in Counter((c['src'], c['cause']) for c in causes).most_common()}
    span = (V[-1]['t'] - V[0]['t']) / 60.0 if len(V) > 1 else 0
    out['minutes'] = round(span, 1)
    out['lines_per_minute'] = round(len(V) / span, 1) if span else None
    out['test_steps'] = len(d['tests'])
    errs = sum(d['errors'].values())
    if errs:
        hard.append('blueprint errors')
    out['hard_failures'] = hard
    return out


def combine(rs):
    """Totals over several runs (each run is its own session: repeats are checked per run)."""
    tot = {}
    for r in rs:
        for k, v in r.items():
            if k not in tot:
                tot[k] = v
            elif isinstance(v, bool) or v is None:
                continue
            elif isinstance(v, (int, float)) and isinstance(tot[k], (int, float)):
                tot[k] = (min if k.endswith('_min') else max if k.startswith('max_') or k.endswith('_max') or k == 'pd_median' else
                          (lambda a, b: a + b))(tot[k], v)
            elif isinstance(v, dict) and isinstance(tot[k], dict):
                m = dict(tot[k])
                for kk, vv in v.items():
                    m[kk] = m.get(kk, 0) + vv if isinstance(vv, (int, float)) else vv
                tot[k] = m
            elif isinstance(v, list) and isinstance(tot[k], list):
                tot[k] = tot[k] + v
            elif tot[k] is None:
                tot[k] = v
    if tot.get('minutes'):
        tot['minutes'] = round(tot['minutes'], 1)
    if 'lines' in tot and tot.get('minutes'):
        tot['lines_per_minute'] = round(tot['lines'] / tot['minutes'], 1)
    tot['hard_failures'] = sorted({h for r in rs for h in r['hard_failures']})
    return tot


def main():
    files = [a for a in sys.argv[1:] if not a.startswith('--') and not (len(sys.argv) > 2 and sys.argv[sys.argv.index(a) - 1] == '--json')]
    if not files:
        print(__doc__)
        return 2
    rs = []
    for f in files:
        r = check(parse(f))
        rs.append(r)
        if len(files) > 1:
            print(f'--- {f}: {r["lines"]} lines, {r["minutes"]} min, hard failures {r["hard_failures"]}')
    r = rs[0] if len(rs) == 1 else combine(rs)
    if len(rs) > 1:
        print(f'=== {len(rs)} runs combined')
    for k, v in r.items():
        print(f'{k:32s} {v}')
    if '--json' in sys.argv:
        json.dump(r, open(sys.argv[sys.argv.index('--json') + 1], 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    return 1 if r['hard_failures'] else 0


if __name__ == '__main__':
    sys.exit(main())
