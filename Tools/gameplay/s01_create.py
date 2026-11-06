import sys, importlib
sys.path.insert(0, r'J:\Projets\Unreal_Projects\Guess Who\Tools\gameplay')
import gw_lib; importlib.reload(gw_lib)
from gw_lib import *
for d in ['/Game/GW/Blueprints','/Game/GW/UI','/Game/GW/Input','/Game/GW/Audio','/Game/GW/Characters','/Game/GW/Maps/Dev']:
    EAL.make_directory(d)
if not EAL.does_asset_exist('/Game/GW/Blueprints/BP_GW_Character'):
    EAL.duplicate_asset('/Game/ThirdPerson/Blueprints/BP_ThirdPersonCharacter', '/Game/GW/Blueprints/BP_GW_Character')
    print('duplicated character')
specs = [('BP_GW_GameMode', unreal.GameModeBase), ('BP_GW_GameState', unreal.GameStateBase),
         ('BP_GW_PlayerState', unreal.PlayerState), ('BP_GW_PlayerController', unreal.PlayerController),
         ('BP_GW_NPCController', unreal.AIController), ('BP_GW_Ghost', unreal.SpectatorPawn),
         ('BP_GW_MenuGameMode', unreal.GameModeBase), ('BP_GW_MenuPlayerController', unreal.PlayerController)]
for n, p in specs:
    bp = load_or_create_bp(n, p)
    compile_bp(bp, quiet=True)
    save(bp)
ch = load_bp('BP_GW_Character'); compile_bp(ch, quiet=True); save(ch)
print('vars char', BT.list_variables(ch))
sub = unreal.get_engine_subsystem(unreal.SubobjectDataSubsystem)
for h in sub.k2_gather_subobject_data_for_blueprint(ch):
    d = sub.k2_find_subobject_data_from_handle(h)
    print(' ', unreal.SubobjectDataBlueprintFunctionLibrary.get_variable_name(d), unreal.SubobjectDataBlueprintFunctionLibrary.get_display_name(d))
