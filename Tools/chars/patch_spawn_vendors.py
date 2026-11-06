"""Rewrites only GameMode.SpawnVendors (same body as s34_shop.py G['SpawnVendors']): one BP_GW_Waiter + one BP_GW_Waiter2. Run with ue_run.py under a GM lock; a full s34 gm run stays equivalent."""
import sys, importlib
sys.path.insert(0, r'J:/Projets/Unreal_Projects/Guess Who/Tools/gameplay')
import gw_lib; importlib.reload(gw_lib)
from gw_lib import *
SHOP = '/Game/GW/Blueprints/Shop'
WAITER = f'{SHOP}/BP_GW_Waiter.BP_GW_Waiter_C'
WAITER2 = f'{SHOP}/BP_GW_Waiter2.BP_GW_Waiter2_C'
ISVALID = 'GW|Call|/Script/Engine.KismetSystemLibrary|IsValid'
def unbalanced(code):
    depth, quoted = 0, False
    for c in code:
        if c == '"':
            quoted = not quoted
        elif not quoted:
            depth += (c == '(') - (c == ')')
            if depth < 0:
                return depth
    return depth


def clean_graph(bp, graph_name):
    """Empty a graph before a rewrite (the transpiler keeps old nodes wired to the entry's parameter pins)."""
    g = get_graph(bp, graph_name)
    if g is None:
        return
    for node in list(BT.find_nodes(g)):
        if node.get_class().get_name() in ('K2Node_FunctionEntry', 'K2Node_FunctionResult'):
            for p in node.list_all_pins():
                for c in list(p.list_connected_pins()):
                    p.break_single_pin_link(c)
            continue
        BT.delete_node(node)


gm = load_bp('BP_GW_GameMode')
code = f'''
    (fn SpawnVendors ()
      (if (not ({ISVALID} :Object (Variables|Shop|GetBarman)))
        (CallFunction|SpawnBarman))
      (if (not (Variables|Shop|GetJunkieChecked))
        (Variables|Shop|SetJunkieChecked true)
        (CallFunction|SpawnJunkie))
      ; two waiters wander among the guests (AI pawns, not BP_GW_Character: bullets and bombs ignore them)
      ; the second one is BP_GW_Waiter2 (other skin, Tools/chars/make_waiter2.py)
      (if (< (Utilities|Array|Length (Variables|Shop|GetWaiters)) 2)
        (bind t (CallFunction|RandomSpawnTransform))
        (if (== (Utilities|Array|Length (Variables|Shop|GetWaiters)) 1)
          (bind w2 (AI|SpawnAIFromClass :PawnClass "{WAITER2}" :Location (.location t) :Rotation (.rotation t) :bNoCollisionFail true))
          (bind wc2 (Utilities|Casting|CastToBP_GW_Waiter w2)
            (:then
              (Utilities|Array|Add :TargetArray (Variables|Shop|GetWaiters) :NewItem wc2)
              (GW|Set|{WAITER}|NextMoveAt :self wc2 :NextMoveAt (+ (CallFunction|Now) (Math|Random|RandomFloatinRange 1.0 4.0)))
              (Development|PrintString :InString (cat "GW: waiter2 spawned at " (Transformation|GetActorLocation :self wc2)) :bPrintToScreen false))
            (:CastFailed))
          (else
            (bind w (AI|SpawnAIFromClass :PawnClass "{WAITER}" :Location (.location t) :Rotation (.rotation t) :bNoCollisionFail true))
            (bind wc (Utilities|Casting|CastToBP_GW_Waiter w)
              (:then
                (Utilities|Array|Add :TargetArray (Variables|Shop|GetWaiters) :NewItem wc)
                (GW|Set|{WAITER}|NextMoveAt :self wc :NextMoveAt (+ (CallFunction|Now) (Math|Random|RandomFloatinRange 1.0 4.0)))
                (Development|PrintString :InString (cat "GW: waiter spawned at " (Transformation|GetActorLocation :self wc)) :bPrintToScreen false))
              (:CastFailed))))))
'''
assert unbalanced(code) == 0
clean_graph(gm, 'SpawnVendors')
write(gm, 'SpawnVendors', code, compile_after=False)
print('GMCOMPILE', compile_bp(gm, quiet=True))
save(gm)
print('GMSAVED')
