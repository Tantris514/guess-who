import sys, importlib
sys.path.insert(0, r'J:\Projets\Unreal_Projects\Guess Who\Tools\gameplay')
import gw_lib; importlib.reload(gw_lib)
from gw_lib import *
paths = ['/Game/GW/Blueprints/' + n for n in ['BP_GW_PlayerState', 'BP_GW_GameState', 'BP_GW_GameInstance', 'BP_GW_Character', 'BP_GW_NPCController', 'BP_GW_Ghost',
         'BP_GW_GameMode', 'BP_GW_PlayerController', 'BP_GW_MenuGameMode', 'BP_GW_MenuPlayerController']]  # WBP_* belong to the UI agent now
for p in paths:
    bp = unreal.load_asset(p)
    BT.compile_blueprint(bp)
    st = bp.get_editor_property('Status')
    probs = node_problems(bp)
    save(bp)
    print(bp.get_name(), str(st).split('.')[-1], probs if probs else '')
