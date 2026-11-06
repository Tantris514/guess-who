"""Prints the locks still open in Tools/agent_logs/locks.md (each LOCK paired with the UNLOCK of the same asset and
owner; a "(pid N)" tag right after the time is part of the key). Exit code 1 if a game test must not start now:
an open /Game asset, GAMETEST, BUILD or HOOKS lock (a test during a compile makes its saves fail), or the build
manager's smoke-test window (rule of 2026-11-03 07:31: from LOCK BUILD until 20 min after UNLOCK BUILD, unless the
build manager's own LOCK GAMETEST came and went after that UNLOCK BUILD).
Usage: python -I -X utf8 locks_open.py [--quiet]"""
import datetime, re, sys
LOCKS = r'J:\Projets\Unreal_Projects\Guess Who\Tools\agent_logs\locks.md'
st = {}
last_unlock_build = None        # (line index, HH:MM)
smoke_after = False
lines = open(LOCKS, encoding='utf-8').read().splitlines()
for i, l in enumerate(lines):
    s = l.strip()
    m = re.match(r'^(UN)?LOCK (\S+) (\S+)(.*)$', s)
    if not m:
        continue
    pm = re.match(r'^ \d\d:\d\d \(pid (\d+)\)', m.group(4))
    k = (m.group(2).replace('C:/Program Files/Git', ''), m.group(3), pm.group(1) if pm else '')
    if m.group(1):
        st.pop(k, None)
    else:
        st[k] = s
    if m.group(2) == 'BUILD' and m.group(1):
        tm = re.search(r'\b(\d\d):(\d\d)\b', m.group(4))
        last_unlock_build = (i, tm.group(0) if tm else None)
        smoke_after = False
    if m.group(2) == 'GAMETEST' and 'build' in m.group(3) and last_unlock_build and m.group(1):
        smoke_after = True       # the build manager's smoke test has run (its UNLOCK GAMETEST) since that build
blocking = [v for (a, o, p), v in st.items() if a.startswith('/Game') or a in ('GAMETEST', 'BUILD', 'HOOKS')]
if last_unlock_build and last_unlock_build[1] and not smoke_after:
    now = datetime.datetime.now()
    h, mnt = map(int, last_unlock_build[1].split(':'))
    t = now.replace(hour=h, minute=mnt, second=0, microsecond=0)
    if t > now + datetime.timedelta(hours=1):
        t -= datetime.timedelta(days=1)
    if now - t < datetime.timedelta(minutes=20):
        blocking.append(f'build smoke-test window: UNLOCK BUILD at {last_unlock_build[1]} + 20 min')
if '--quiet' not in sys.argv:
    print('\n'.join(blocking) if blocking else 'free')
sys.exit(1 if blocking else 0)
