"""(in editor) Rough illuminance budget: direct inverse-square lux at eye height (150 cm) at a few points per room
from every point/spot/rect light (no occlusion, no GI). Used to balance rooms for the narrow exposure range."""
import math
import unreal
eas = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
L = []
for a in eas.get_all_level_actors():
    for cls in (unreal.PointLightComponent, unreal.SpotLightComponent, unreal.RectLightComponent):
        c = a.get_component_by_class(cls)
        if c:
            p = c.get_world_location()
            L.append((p.x, p.y, p.z, c.get_editor_property("intensity"), c.get_editor_property("attenuation_radius"),
                      cls.__name__))
            break
PTS = {"hall": [(3000, 600), (3000, 1500), (2500, 2150)], "gallery": [(3000, 2170, 650)], "ballroom": [(3000, 2900), (3000, 3700)],
       "library": [(1000, 3000), (500, 3400)], "dining": [(1000, 500), (1000, 1400)], "billiard": [(5000, 400), (5500, 1400)],
       "study": [(4600, 2800), (5500, 2800)], "conservatory": [(5000, 3600), (4500, 4100)],
       "corridor_w": [(500, 2100), (1500, 2100)], "corridor_e": [(4500, 2100), (5500, 2100)], "cloakroom": [(3000, 250)]}
for room, pts in PTS.items():
    vals = []
    for p in pts:
        x, y = p[0], p[1]
        z = p[2] if len(p) > 2 else 150
        e = 0.0
        for (lx, ly, lz, I, r, k) in L:
            d2 = (lx - x) ** 2 + (ly - y) ** 2 + (lz - z) ** 2
            d = math.sqrt(d2)
            if d > r:
                continue
            fall = (1 - (d / r) ** 4) ** 2           # UE inverse-square falloff window
            e += I / (d2 / 10000.0) * fall
        vals.append(round(e, 1))
    print(f"{room:13s} lux {vals}")
print("lights:", len(L))
