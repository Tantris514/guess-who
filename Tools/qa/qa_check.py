"""Read a game log from the automated dev test (-GWDevTest) and grade it: errors, then one line per expected feature.

  python -I -X utf8 Tools\\qa\\qa_check.py <game.log> [report.md]

Errors (must be 0): Accessed None, Blueprint runtime errors, LogScript warnings, fatal / ensure. Features: each CHECK
is a regex counted in the log ("GW: ..." lines printed by the game scripts). Required ones fail the run when missing;
optional ones only warn (features still being built tonight). Add a line to CHECKS when a feature lands.
Exit code 0 = pass, 1 = fail.
"""
import re
import sys
from collections import Counter

# (name, regex, minimum count, required)
CHECKS = [
    ('round starts (dev test round)', r'GW: dev .*test round started|GW: dev .*quick test', 1, True),
    ('hunt begins', r'GW music: state \d+ -> 2\b', 1, True),
    ('blackout event', r'world sound cat=22 ', 1, True),
    ('power back after blackout', r'world sound cat=23 ', 1, True),
    ('fire event (whoosh)', r'world sound cat=30 ', 1, True),
    ('kamikaze explosion', r'world sound cat=20 ', 1, True),
    ('event music', r'GW music: state -?\d+ -> [4-8]\b', 3, True),
    ('events end', r'GW: event \d ended', 3, True),
    ('piano / instruments', r'GW: instrument \d played by|GW: piano played by', 1, True),
    ('NPC drawn to the piano', r'walks to the piano', 1, False),
    ('curtain (loading screen)', r'GW: curtain lifts after', 1, False),
    ('NPC voices spoken', r'GW: say cat=|GW: VOX', 5, True),
    ('gunshot panic', r'GW: gunshot panic from', 1, False),
    ('NPC chatter', r'GW: chatter|GW: VOXCONV|GW: VOX.*(chatter|dialogue|remark)', 1, False),
    ("robot fires", r"world sound cat=26 ", 1, True),
    ('bandits hit', r'GW: bandit hit', 1, False),
    ('dev menu commands accepted', r'GW: dev ', 20, True),
    # features landing tonight (optional until their agent reports done)
    # shop & economy (Tools/gameplay/s34_shop.py; DevTestTick block 133-160 in Tools/ui/u15_dev_menu.py)
    ('shop: vendors spawned (barman, junkie, 2 waiters)', r'GW: barman spawned|GW: junkie spawned|GW: waiter spawned', 4, True),
    ('shop: purchase', r'GW: sold .* for \d+ \$ \(vendor \d\)', 2, True),
    ('shop: NPC-kill reward (+100 $, loud scream)', r'GW: shop .* 100 \$ -> .*un invité de moins', 1, True),
    ('shop: loud positional scream', r'GW: loud scream idx=\d+', 1, True),
    ('shop: bomb defused (E held 2 s)', r'GW: bomb defused by ', 1, True),
    ('shop: waiter walked away (shop closed)', r'GW: shop auto-closed \(vendor kind 2', 1, True),
    ('shop: junkie sale', r'GW: sold .* \(vendor 1\)', 1, True),
    ('turret fired', r'GW: turret', 1, False),
    # social life (Tools/gameplay/s36_social.py; DevTestTick steps 42-46 in Tools/ui/u15_dev_menu.py)
    ('dance: player starts (V)', r'GW: dance start \S+ id=[1-9]\b', 1, True),
    ('dance: player stops (V or moving)', r'GW: dance stop \S+ \((key|moved)\)', 1, True),
    ('dance: NPC dance group formed', r'GW: social dance group formed: [1-9]\d* NPCs', 1, True),
    ('dance: bar crowd formed', r'GW: social bar group formed: [1-9]\d* NPCs', 1, True),
    ('dance: NPCs dancing', r'GW: social NPC \S+ dances [1-9]\b', 1, False),
    ('dance: groups break up', r'GW: social (dance|bar) group (dispersed|flees)|GW: social groups dispersed', 1, False),
    # pickups & interactables (Tools/gameplay/s38_pickups.py; DevTestTick block 104-130 in Tools/ui/u15_dev_menu.py)
    ('pickups: billiard ball picked up', r'GW: pickup ball by ', 1, True),
    ('pickups: ball kills an NPC', r'GW: ball killed NPC ', 1, True),
    ('pickups: sword stolen', r'GW: pickup sword by |GW: sword in the hand of ', 1, True),
    ('pickups: sword kills an NPC', r'GW: sword killed NPC ', 1, True),
    ('pickups: body swap done', r'GW: swap done: .* now controls ', 1, True),
    ('pickups: safe opened (500 $)', r'GW: safe opened by ', 1, True),
    ('pickups: fire alarm pulled', r'GW: fire alarm pulled by ', 1, True),
    ('pickups: toilet fart', r'GW: fart by ', 1, True),
]
ERRORS = [
    ('Accessed None', r'Accessed None'),
    ('Blueprint runtime error', r'Blueprint Runtime Error|LogScript: Error'),
    ('LogScript warning', r'LogScript: Warning'),
    ('fatal / ensure', r'Fatal error|Ensure condition failed|appError'),
]


def main(path, out=None):
    text = open(path, encoding='utf-8', errors='replace').read()
    lines = text.splitlines()
    rep = [f'# QA report — {path}', '']
    fail = False
    rep.append('## Errors')
    for name, rx in ERRORS:
        hits = [l for l in lines if re.search(rx, l)]
        if hits:
            fail = True
            top = Counter(re.sub(r'^\[[^\]]*\]\[[^\]]*\]', '', h)[:160] for h in hits).most_common(5)
            rep.append(f'- FAIL {name}: {len(hits)}')
            rep += [f'  - {n}× {t}' for t, n in top]
        else:
            rep.append(f'- ok {name}: 0')
    rep += ['', '## Features']
    for name, rx, need, required in CHECKS:
        n = len(re.findall(rx, text))
        if n >= need:
            rep.append(f'- ok {name}: {n}')
        elif required:
            fail = True
            rep.append(f'- FAIL {name}: {n} (need {need})')
        else:
            rep.append(f'- (missing, optional) {name}: {n}')
    rep += ['', f'**{"FAIL" if fail else "PASS"}**']
    s = '\n'.join(rep)
    print(s)
    if out:
        open(out, 'w', encoding='utf-8').write(s + '\n')
    return 1 if fail else 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else None))
