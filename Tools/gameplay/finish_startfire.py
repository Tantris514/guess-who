"""Writes only GM.StartFire from s32_events.py's text, without a full s32 run (its other parts are older than the s40 graphs)."""
import sys, re
sys.path.insert(0, r'J:\Projets\Unreal_Projects\Guess Who\Tools\gameplay')
from gw_lib import *
s = open(r'J:\Projets\Unreal_Projects\Guess Who\Tools\gameplay\s32_events.py', encoding='utf-8').read().replace('\r\n', '\n')
body = re.search(r"\(fn StartFire \(\)\n.*?\n'''", s, re.S).group(0)[:-4]
cats = re.findall(r"\{CAT\['(\w+)'\]\}", body)
m = {c: re.search(r"['\"]%s['\"]\s*:\s*(\d+)" % c, s).group(1) for c in set(cats)}
for c, v in m.items():
    body = body.replace("{CAT['%s']}" % c, v)
print('cats', m)
gm = load_bp('BP_GW_GameMode')
write(gm, 'StartFire', body, compile_after=False)
compile_bp(gm)
print('BP_GW_GameMode', [p for p in node_problems(gm) if 'Fire' in p])
save(gm)
