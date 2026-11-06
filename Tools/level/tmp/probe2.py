import sys
sys.path.insert(0, r"J:\Projets\Unreal_Projects\Guess Who\Tools\gameplay")
import gw_lib
bp = gw_lib.load_bp("BP_GW_Storm", "/Game/GW/Environment")
for flt in ("Math|Float|Floor", "Math|Trig|Sin", "Math|Float|Exp", "Math|Float|Abs", "Math|Float|Max", "Math|Float|Fraction",
            "Math|Float|Multiply", "Rendering|Material|SetScalarParameterValue", "Utilities|IsValid", "Game|GetGameState",
            "Variables|Default", "Math|Float|Select"):
    print(flt, gw_lib.find_types(bp, flt)[:10])
print(gw_lib.pins(bp, "Rendering|Material|SetScalarParameterValue"))
