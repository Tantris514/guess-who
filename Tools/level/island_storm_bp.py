"""(in editor) BP_GW_Storm (/Game/GW/Environment): lightning flashes + thunder, identical on every machine.

  level/run.sh level/island_storm_bp.py [probe]

No replication needed: every machine derives the same strike schedule from the replicated server clock
(GameState.GetServerWorldTimeSeconds). Time is cut into Period-long slots; a hash of the slot index decides whether
a bolt strikes in it, when (2 s .. Period-6 s into the slot) and how far away it is (thunder delay 1.2..5 s,
volume, which of the three thunder waves). On a strike:
  * MPC_GW_Storm.Flash follows a double-flicker envelope (~0.8 s): sky clouds, rain curtains, glass drops flash;
  * the Bolt directional light (shadowed: it only enters through the windows) spikes, hidden the rest of the time;
  * after the delay the thunder wave plays (2D, SC_GW_SFX), once per strike, skipped for strikes long past
    (late joiners).
"""
import sys

import unreal

GP = r"J:\Projets\Unreal_Projects\Guess Who\Tools\gameplay"
if GP not in sys.path:
    sys.path.insert(0, GP)
import importlib  # noqa: E402

import gw_lib  # noqa: E402

importlib.reload(gw_lib)
from gw_lib import (BT, ensure_var, ensure_component, write, compile_bp, node_problems, save,  # noqa: E402
                    load_or_create_bp, get_graph)

ENV = "/Game/GW/Environment"
ARGS = [a.lower() for a in globals().get("UE_ARGS", [])]

bp = load_or_create_bp("BP_GW_Storm", unreal.Actor, folder=ENV)
if "probe" in ARGS:
    for flt in ("SetScalarParameterValue", "GetServerWorldTimeSeconds", "Floor", "Sin", "Exp", "Abs", "PlaySound2D",
                "SetIntensity", "SetVisibility", "FMax", "Clamp", "IsValid"):
        print(flt, gw_lib.find_types(bp, flt)[:12])
    raise SystemExit

ensure_var(bp, "Period", "float", category="Storm")
ensure_var(bp, "BoltLux", "float", category="Storm")
ensure_var(bp, "LastThunder", "float", category="Storm")
bolt = ensure_component(bp, "Bolt", unreal.DirectionalLightComponent, "DefaultSceneRoot")
bolt.set_editor_property("intensity", 0.0)
bolt.set_editor_property("light_color", unreal.Color(r=200, g=214, b=255, a=255))
bolt.set_editor_property("cast_shadows", True)
bolt.set_editor_property("visible", False)
bolt.set_editor_property("forward_shading_priority", -1)   # the moon stays the one for translucency: no "competing lights" message on screen
bolt.set_mobility(unreal.ComponentMobility.MOVABLE)
for k, v in (("atmosphere_sun_light", False), ("use_temperature", False), ("cast_volumetric_shadow", False)):
    try:
        bolt.set_editor_property(k, v)
    except Exception as e:
        print("  bolt skip", k, e)

MPC = '"/Game/GW/Environment/MPC_GW_Storm.MPC_GW_Storm"'
TH = '"/Game/GW/Environment/Audio/SW_GW_Thunder{}.SW_GW_Thunder{}"'
ISVALID = "GW|Call|/Script/Engine.KismetSystemLibrary|IsValid"


def h(seed):
    """frac(abs(sin(slot * seed)) * 43758.5453) as a DSL expression (slot = slot index as float)."""
    return f"(Math|Float|Fraction (* (Math|Float|Absolute(Float) (Math|Trig|Sin(Radians) (* slot {seed}))) 43758.5453))"


code = f"""
(event EventTick (DeltaSeconds)
  (bind gs (Game|GetGameState))
  (if ({ISVALID} :Object gs)
    (bind t (GameState|GetServerWorldTimeSeconds :self gs))
    (bind per (Variables|Storm|GetPeriod))
    (bind q (/ t per))
    (bind slot (- q (Math|Float|Fraction q)))
    (bind h1 {h(12.9898)})
    (bind h2 {h(78.233)})
    (bind h3 {h(39.3468)})
    (bind ts (+ (* slot per) (+ 2.0 (* h1 (- per 8.0)))))
    (bind dt (- t ts))
    (bind live (and (> h3 0.22) (and (>= dt 0.0) (< dt 1.6))))
    (bind e1 (Math|Float|Exp (* dt -9.0)))
    (bind e2 (select (> dt 0.22) (* 0.85 (Math|Float|Exp (* (- dt 0.22) -7.0))) 0.0))
    (bind e3 (select (> dt 0.55) (* 0.45 (Math|Float|Exp (* (- dt 0.55) -10.0))) 0.0))
    (bind env (select live (Math|Float|Max(Float) e1 (Math|Float|Max(Float) e2 e3)) 0.0))
    (Rendering|Material|SetScalarParameterValue :Collection {MPC} :ParameterName "Flash" :ParameterValue env)
    (Rendering|Material|SetScalarParameterValue :Collection {MPC} :ParameterName "BoltAz" :ParameterValue (* h2 6.2831853))
    (Rendering|Material|SetScalarParameterValue :Collection {MPC} :ParameterName "BoltSeed"
      :ParameterValue (* (Math|Float|Fraction (* slot 0.6180339)) 100.0))
    (Rendering|Components|Light|SetIntensity :self (Variables|Default|GetBolt)
      :NewIntensity (* env (Variables|Storm|GetBoltLux)))
    (Rendering|SetVisibility :self (Variables|Default|GetBolt) :bNewVisibility (> env 0.003)
      :bPropagateToChildren false)
    (bind delay (+ 1.2 (* h2 3.8)))
    (if (and (> h3 0.22) (and (>= dt delay) (and (< dt (+ delay 0.6)) (!= slot (Variables|Storm|GetLastThunder)))))
      (Variables|Storm|SetLastThunder slot)
      (Development|PrintString :InString "GW storm: thunder" :bPrintToScreen false :bPrintToLog true)
      (bind vol (+ 0.5 (* 0.5 (- 1.0 h2))))
      (if (< h1 0.34)
        (Audio|PlaySound2D :Sound {TH.format(1, 1)} :VolumeMultiplier vol)
        (elif (< h1 0.67)
          (Audio|PlaySound2D :Sound {TH.format(2, 2)} :VolumeMultiplier vol)
          (else
            (Audio|PlaySound2D :Sound {TH.format(3, 3)} :VolumeMultiplier vol)))))))
"""
g = get_graph(bp, "EventGraph")
for n in list(BT.find_nodes(g)):         # start from an empty event graph on every rebuild
    try:
        BT.delete_node(n)
    except Exception:
        pass
write(bp, "EventGraph", code, compile_after=False)
ok = compile_bp(bp)
cdo = unreal.get_default_object(bp.generated_class())       # defaults once the variables exist on the class
for k, v in (("Period", 21.0), ("BoltLux", 120.0), ("LastThunder", -1.0)):
    try:
        cdo.set_editor_property(k, v)
    except Exception as e:
        print("  default skip", k, e)
ok = compile_bp(bp) and ok
for p in node_problems(bp):
    print("  ", p)
save(bp)
print("BP_GW_Storm", "OK" if ok else "FAILED")
