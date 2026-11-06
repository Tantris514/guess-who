"""Exit 0 when none of the given assets is LOCKed by another agent in Tools/agent_logs/locks.md (prints holders otherwise).
Usage: python -I -X utf8 locks_free.py BP_GW_PlayerController BP_GW_GameMode ...   (also checks BUILD and HOOKS)"""
import sys

me = 'camera-combat'
held = {}
for line in open(r'J:\Projets\Unreal_Projects\Guess Who\Tools\agent_logs\locks.md', encoding='utf-8', errors='replace'):
    parts = line.split()
    if len(parts) < 3 or parts[0] not in ('LOCK', 'UNLOCK'):
        continue
    asset, who = parts[1].split('/')[-1], parts[2]
    if parts[0] == 'LOCK':
        held[asset] = who
    else:
        held.pop(asset, None)
want = set(sys.argv[1:]) | {'BUILD', 'HOOKS', 'GAMETEST'}   # a -game test holds .uasset files: saves fail
busy = {a: w for a, w in held.items() if a in want and (w != me or a == 'GAMETEST')}
if busy:
    print('busy:', busy)
    sys.exit(1)
print('free')
