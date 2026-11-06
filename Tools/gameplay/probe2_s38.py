import sys
sys.path.insert(0, r'J:\Projets\Unreal_Projects\Guess Who\Tools\gameplay')
from gw_lib import *
pc = load_bp('BP_GW_PlayerController')
for q in ['vector * float', 'Multiply_VectorFloat', 'Vector * Float', 'ScaleVector']:
    print(q, find_types(pc, q, limit=10))
