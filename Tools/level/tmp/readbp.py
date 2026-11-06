import sys
sys.path.insert(0, r"J:\Projets\Unreal_Projects\Guess Who\Tools\gameplay")
import gw_lib
bp = gw_lib.load_bp("BP_GW_Storm", "/Game/GW/Environment")
g = gw_lib.get_graph(bp, "EventGraph")
txt = gw_lib.BT.read_graph_dsl(g)
open(r"J:\Projets\Unreal_Projects\Guess Who\Tools\level\tmp\storm_graph.txt", "w", encoding="utf-8").write(txt)
print(len(txt), "chars;", len(gw_lib.BT.find_nodes(g)), "nodes")
cdo = unreal.get_default_object(bp.generated_class())
print("defaults", cdo.get_editor_property("Period"), cdo.get_editor_property("BoltLux"))
