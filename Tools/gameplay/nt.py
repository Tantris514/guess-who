import sys, importlib
sys.path.insert(0, r'J:\Projets\Unreal_Projects\Guess Who\Tools\gameplay')
import gw_lib; importlib.reload(gw_lib)
from gw_lib import *
# usage: nt.py BPName [graph] -- filter1 filter2 ...   ;  prefix filter with '?' to dump pins
args = list(UE_ARGS)
bp = load_bp(args[0]) if not args[0].startswith('/') else unreal.load_asset(args[0])
graph = 'EventGraph'
if args[1] != '--':
    graph = args[1]; args = args[1:]
for f in args[2:]:
    if f.startswith('?'):
        try:
            ins, outs = pins(bp, f[1:], graph)
            print('PINS', f[1:], '\n   IN :', ins, '\n   OUT:', outs)
        except Exception as e:
            print('PINS FAIL', f[1:], str(e)[-300:])
    else:
        r = find_types(bp, f, graph, 40)
        print(f'[{f}] ->', r)
