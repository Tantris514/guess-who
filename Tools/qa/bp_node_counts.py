"""Count the nodes in every graph of the big Blueprints, to find bloat (graphs rewritten again and again that keep
leftover nodes). Usage: python -I -X utf8 Tools\\ui\\ue_run.py Tools\\qa\\bp_node_counts.py
"""
import sys
sys.path.insert(0, r'J:\Projets\Unreal_Projects\Guess Who\Tools\gameplay')
import gw_lib
from gw_lib import BT

for name in ('BP_GW_GameMode', 'BP_GW_PlayerController', 'BP_GW_Character', 'BP_GW_NPCController', 'BP_GW_RobotController'):
    bp = gw_lib.load_bp(name)
    rows = []
    for g in unreal.BlueprintEditorLibrary.get_graphs(bp) if hasattr(unreal.BlueprintEditorLibrary, 'get_graphs') else []:
        rows.append((len(BT.find_nodes(g)), g.get_name()))
    if not rows:
        for gname in gw_lib.graph_names(bp):
            g = gw_lib.get_graph(bp, gname)
            rows.append((len(BT.find_nodes(g)), gname))
    rows.sort(reverse=True)
    print(f'{name}: {len(rows)} graphs, {sum(n for n, _ in rows)} nodes; biggest: ' + ', '.join(f'{g} {n}' for n, g in rows[:8]))
