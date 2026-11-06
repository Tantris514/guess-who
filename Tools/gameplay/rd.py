import sys
sys.path.insert(0, r'J:\Projets\Unreal_Projects\Guess Who\Tools\gameplay')
from gw_lib import *
p = UE_ARGS[0]
bp = load_bp(p) if not p.startswith('/') else unreal.load_asset(p)
for gname in UE_ARGS[1:]:
    print('=====', gname)
    print(BT.read_graph_dsl(get_graph(bp, gname)))
