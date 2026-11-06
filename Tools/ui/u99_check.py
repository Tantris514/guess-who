"""Compile-check every Blueprint the ui agent touched or depends on; save only the ui agent's assets."""
import sys
sys.path.insert(0, r'J:\Projets\Unreal_Projects\Guess Who\Tools\ui')
import importlib, uilib
importlib.reload(uilib)
from uilib import *
MINE = ['/Game/GW/UI/WBP_HUD', '/Game/GW/UI/WBP_MainMenu', '/Game/GW/UI/WBP_Options', '/Game/GW/UI/WBP_HowTo', '/Game/GW/UI/WBP_Pause',
        '/Game/GW/UI/BP_GW_Settings', '/Game/GW/Blueprints/BP_GW_MenuPlayerController', '/Game/GW/Blueprints/BP_GW_MenuGameMode']
LOCKED = ['/Game/GW/Blueprints/BP_GW_PlayerController', '/Game/GW/Blueprints/BP_GW_GameInstance']
OTHERS = ['/Game/GW/Blueprints/' + n for n in ['BP_GW_PlayerState', 'BP_GW_GameState', 'BP_GW_Character', 'BP_GW_NPCController', 'BP_GW_Ghost', 'BP_GW_GameMode']]
save_extra = set(UE_ARGS)
for p in MINE + LOCKED + OTHERS:
    bp = unreal.load_asset(p)
    if bp is None:
        print('MISSING', p); continue
    BT.compile_blueprint(bp)
    st = str(bp.get_editor_property('Status')).split('.')[-1]
    probs = node_problems(bp)
    if p in MINE or (p in LOCKED and 'locked' in save_extra):
        save(bp)
    print(bp.get_name(), st, probs if probs else '')
