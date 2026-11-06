"""DSL experiment for s38 (FlyTick vector maths), on a throwaway Blueprint in /Game/GW/Blueprints/Pickups."""
import sys, importlib
sys.path.insert(0, r'J:\Projets\Unreal_Projects\Guess Who\Tools\gameplay')
import gw_lib; importlib.reload(gw_lib)
from gw_lib import *
V3 = unreal.Vector.static_struct()
bp = load_or_create_bp('BP_GW_DslTest', unreal.Actor, '/Game/GW/Blueprints/Pickups')
ensure_var(bp, 'SL', struct=V3, category='GW')
ensure_var(bp, 'VL', struct=V3, category='GW')
ensure_var(bp, 'T0', 'float', category='GW')
VMUL = 'GW|Call|/Script/Engine.KismetMathLibrary|Multiply_VectorFloat'
tests = {
    'A': '(fn A () (bind ft (- (Utilities|Time|GetGameTimeinSeconds) (Variables|GW|GetT0))) (bind drop (* -150.0 (* ft ft))) (Transformation|SetActorLocation :self self :NewLocation (Math|Vector|MakeVector 0.0 0.0 drop) :bSweep false :bTeleport true))',
    'B': f'(fn B () (bind ft (- (Utilities|Time|GetGameTimeinSeconds) (Variables|GW|GetT0))) (Transformation|SetActorLocation :self self :NewLocation ({VMUL} :A (Variables|GW|GetVL) :B ft) :bSweep false :bTeleport true))',
    'C': f'(fn C () (bind ft (- (Utilities|Time|GetGameTimeinSeconds) (Variables|GW|GetT0))) (bind w ({VMUL} :A (Variables|GW|GetVL) :B ft)) (Transformation|SetActorLocation :self self :NewLocation (+ (Variables|GW|GetSL) w) :bSweep false :bTeleport true))',
    'D': '(fn D () (bind ft (- (Utilities|Time|GetGameTimeinSeconds) (Variables|GW|GetT0))) (bind v (Variables|GW|GetVL)) (Transformation|SetActorLocation :self self :NewLocation (* v ft) :bSweep false :bTeleport true))',
    'E': '(fn E () (bind ft (- (Utilities|Time|GetGameTimeinSeconds) (Variables|GW|GetT0))) (bind m (Math|Vector|MakeVector 0.0 0.0 ft)) (Transformation|SetActorLocation :self self :NewLocation (+ (Variables|GW|GetSL) m) :bSweep false :bTeleport true))',
    'F': '(fn F () (bind m (Math|Vector|MakeVector 0.0 0.0 5.0)) (Transformation|SetActorLocation :self self :NewLocation (+ (Variables|GW|GetSL) m) :bSweep false :bTeleport true))',
    'G': '(fn G () (bind a (Variables|GW|GetSL)) (bind m (Math|Vector|MakeVector 0.0 0.0 5.0)) (Transformation|SetActorLocation :self self :NewLocation (+ a m) :bSweep false :bTeleport true))',
}
for n in tests:
    ensure_fn(bp, n)
compile_bp(bp, quiet=True)
for n, code in tests.items():
    try:
        write(bp, n, code, compile_after=False)
        print('OK', n)
    except Exception as e:
        print('FAIL', n, str(e).splitlines()[0][:200])
compile_bp(bp)
print(node_problems(bp))
