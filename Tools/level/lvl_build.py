"""Geometry/spawn helpers for build_manor.py (runs inside the Unreal Editor).

Everything spawned is tagged GW_Gen plus a part tag (GW_Arch, GW_Light, GW_Dress, GW_Markers, GW_Cams, GW_Env).
Repeated pieces go into InstancedStaticMeshComponents: one actor per (part, group), one ISM per
(mesh, material, collision, shadow, visibility) combination.
"""
import math

import unreal

eas = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
sds = unreal.get_engine_subsystem(unreal.SubobjectDataSubsystem)
SDBL = unreal.SubobjectDataBlueprintFunctionLibrary

SHAPES = "/Game/GW/Meshes/Shapes/"
ARCH = "/Game/GW/Meshes/Arch/"
MATS = "/Game/GW/Materials/"
_mesh_cache, _mat_cache = {}, {}


def mesh(name):
    if name not in _mesh_cache:
        path = name if name.startswith("/") else (SHAPES if name in ("SM_GW_Cube", "SM_GW_Cylinder", "SM_GW_Plane",
                                                                        "SM_GW_Sphere", "SM_GW_Cone", "SM_GW_Cube_NoNanite",
                                                                        "SM_GW_Plane_NoNanite") else ARCH) + name
        m = unreal.load_asset(path)
        if m is None:
            raise RuntimeError("missing mesh " + path)
        _mesh_cache[name] = m
    return _mesh_cache[name]


def mat(name):
    if name not in _mat_cache:
        path = name if name.startswith("/") else MATS + name
        m = unreal.load_asset(path)
        if m is None:
            raise RuntimeError("missing material " + path)
        _mat_cache[name] = m
    return _mat_cache[name]


def rot(yaw=0.0, pitch=0.0, roll=0.0):
    return unreal.Rotator(roll=roll, pitch=pitch, yaw=yaw)


def xform(loc, yaw=0.0, pitch=0.0, roll=0.0, scale=(1, 1, 1)):
    return unreal.Transform(location=unreal.Vector(*loc), rotation=rot(yaw, pitch, roll),
                            scale=unreal.Vector(*scale))


def tag_actor(actor, part, label=None, folder=None, extra=()):
    tags = [unreal.Name("GW_Gen"), unreal.Name(part)] + [unreal.Name(t) for t in extra]
    actor.set_editor_property("tags", tags)
    if label:
        actor.set_actor_label(label)
    actor.set_folder_path(folder or f"GW/{part[3:]}")


class Batch:
    """Collect instances, then flush() spawns one actor per group with ISM components."""

    def __init__(self, part):
        self.part = part
        self.groups = {}
        self.count = 0

    def add(self, group, mesh_name, mat_name, loc, yaw=0.0, pitch=0.0, roll=0.0, scale=(1, 1, 1), coll=True,
            shadow=True, visible=True):
        if min(abs(s) for s in scale) < 1e-4:
            return
        key = (mesh_name, mat_name, coll, shadow, visible)
        self.groups.setdefault(group, {}).setdefault(key, []).append(xform(loc, yaw, pitch, roll, scale))
        self.count += 1

    # axis-aligned world box (cube mesh, -50..50)
    def box(self, group, mat_name, x0, x1, y0, y1, z0, z1, coll=True, shadow=True, mesh_name="SM_GW_Cube",
            visible=True):
        if x1 - x0 < 0.01 or y1 - y0 < 0.01 or z1 - z0 < 0.01:
            return
        self.add(group, mesh_name, mat_name, ((x0 + x1) / 2, (y0 + y1) / 2, (z0 + z1) / 2),
                 scale=((x1 - x0) / 100, (y1 - y0) / 100, (z1 - z0) / 100), coll=coll, shadow=shadow, visible=visible)

    def blocker(self, group, x0, x1, y0, y1, z0, z1, yaw=0.0, pitch=0.0):
        """Invisible collision box (navigation + player blocking)."""
        self.add(group, "SM_GW_Cube", "MI_GW_Plaster_Cream", ((x0 + x1) / 2, (y0 + y1) / 2, (z0 + z1) / 2),
                 yaw=yaw, pitch=pitch, scale=((x1 - x0) / 100, (y1 - y0) / 100, (z1 - z0) / 100), coll=True,
                 shadow=False, visible=False)

    def flush(self):
        n_comp = 0
        for group, d in self.groups.items():
            actor = eas.spawn_actor_from_class(unreal.Actor, unreal.Vector(0, 0, 0))
            tag_actor(actor, self.part, f"GW_{group}")
            handles = sds.k2_gather_subobject_data_for_instance(actor)
            root_h, err = sds.add_new_subobject(unreal.AddNewSubobjectParams(
                parent_handle=handles[0], new_class=unreal.SceneComponent, blueprint_context=None))
            root = SDBL.get_associated_object(SDBL.get_data(root_h))
            root.set_mobility(unreal.ComponentMobility.STATIC)
            for (mesh_name, mat_name, coll, shadow, visible), xforms in d.items():
                h, err = sds.add_new_subobject(unreal.AddNewSubobjectParams(
                    parent_handle=root_h, new_class=unreal.InstancedStaticMeshComponent, blueprint_context=None))
                if not err.is_empty():
                    raise RuntimeError(str(err))
                comp = SDBL.get_associated_object(SDBL.get_data(h))
                comp.set_mobility(unreal.ComponentMobility.STATIC)
                comp.set_static_mesh(mesh(mesh_name))
                if mat_name:
                    comp.set_material(0, mat(mat_name))
                if coll and not visible:
                    comp.set_collision_profile_name("InvisibleWall")      # blocks pawns/nav, not visibility traces
                elif coll:
                    comp.set_collision_profile_name("BlockAll")
                else:
                    comp.set_collision_profile_name("NoCollision")
                    comp.set_editor_property("can_ever_affect_navigation", False)
                comp.set_cast_shadow(bool(shadow and visible))
                if not visible:
                    comp.set_visibility(False)
                    comp.set_editor_property("hidden_in_game", True)
                    comp.set_editor_property("visible_in_ray_tracing", False)
                    comp.set_editor_property("affect_distance_field_lighting", False)
                comp.add_instances(xforms, False, False)
                n_comp += 1
            # SDS adds a movable DefaultSceneRoot; make the whole hierarchy static (parents first)
            rc = actor.root_component
            if rc:
                rc.set_mobility(unreal.ComponentMobility.STATIC)
            for c in actor.get_components_by_class(unreal.SceneComponent):
                c.set_mobility(unreal.ComponentMobility.STATIC)
        print(f"  {self.part}: {len(self.groups)} actors, {n_comp} ISM, {self.count} instances")
        self.groups = {}


class Face:
    """A room-side wall face. origin = inner corner where u = 0; d = along-wall unit; n = inward normal.

    Local box (u, v, z): u along the wall, v away from the wall into the room, z up.
    Meshes authored 'facing +Y, length along X' are placed with yaw = self.yaw.
    """

    def __init__(self, room, side, ox, oy, dx, dy, length, height, line):
        self.room, self.side = room, side
        self.ox, self.oy, self.dx, self.dy = ox, oy, dx, dy
        self.nx, self.ny = -dy, dx
        self.length, self.height = length, height
        self.line = line          # ('x'|'y', at)
        self.yaw = math.degrees(math.atan2(dy, dx))
        self.openings = []        # dicts: kind, u0, u1, z0, z1 (+ extra)
        self.obstacles = []       # (u0, u1, zmax, kind) spans where wainscot/panels/paintings skip

    def P(self, u, v, z):
        return (self.ox + self.dx * u + self.nx * v, self.oy + self.dy * u + self.ny * v, z)

    def u_of(self, x, y):
        return (x - self.ox) * self.dx + (y - self.oy) * self.dy

    def box(self, b, group, mat_name, u0, u1, v0, v1, z0, z1, coll=True, shadow=True, mesh_name="SM_GW_Cube"):
        if u1 - u0 < 0.01 or v1 - v0 < 0.01 or z1 - z0 < 0.01:
            return
        b.add(group, mesh_name, mat_name, self.P((u0 + u1) / 2, (v0 + v1) / 2, (z0 + z1) / 2), yaw=self.yaw,
              scale=((u1 - u0) / 100, (v1 - v0) / 100, (z1 - z0) / 100), coll=coll, shadow=shadow)

    def blocker(self, b, group, u0, u1, v0, v1, z0, z1):
        """Invisible collision box in face-local coordinates (keeps pawns / navmesh out of soft dressing)."""
        b.add(group, "SM_GW_Cube", "MI_GW_Plaster_Cream", self.P((u0 + u1) / 2, (v0 + v1) / 2, (z0 + z1) / 2),
              yaw=self.yaw, scale=((u1 - u0) / 100, (v1 - v0) / 100, (z1 - z0) / 100), coll=True, shadow=False,
              visible=False)

    def piece(self, b, group, mesh_name, mat_name, u, v, z, sx=1.0, sy=1.0, sz=1.0, coll=False, shadow=True,
              yaw_add=0.0, roll=0.0, pitch=0.0):
        b.add(group, mesh_name, mat_name, self.P(u, v, z), yaw=self.yaw + yaw_add, roll=roll, pitch=pitch,
              scale=(sx, sy, sz), coll=coll, shadow=shadow)

    def run(self, b, group, mesh_name, mat_name, u0, u1, v, z, sy=1.0, sz=1.0, shadow=True):
        """Linear profile mesh (100 long along X) stretched from u0 to u1."""
        if u1 - u0 < 1.0:
            return
        self.piece(b, group, mesh_name, mat_name, (u0 + u1) / 2, v, z, sx=(u1 - u0) / 100, sy=sy, sz=sz,
                   shadow=shadow)

    def free_spans(self, z, kinds=None, margin=0.0):
        """Spans of [0, length] not blocked at height z by openings/obstacles (optionally filtered by kind)."""
        blocks = []
        for o in self.openings:
            if (kinds is None or o["kind"] in kinds) and o["z0"] - 0.5 <= z <= o["z1"] + 0.5:
                blocks.append((o["u0"] - margin, o["u1"] + margin))
        for (u0, u1, zmax, kind) in self.obstacles:
            if (kinds is None or kind in kinds) and z <= zmax:
                blocks.append((u0 - margin, u1 + margin))
        blocks.sort()
        spans, cur = [], 0.0
        for a, c in blocks:
            if a > cur:
                spans.append((cur, min(a, self.length)))
            cur = max(cur, c)
        if cur < self.length:
            spans.append((cur, self.length))
        return [(a, c) for a, c in spans if c - a > 0.5]


def spawn(cls, loc, yaw=0.0, pitch=0.0, roll=0.0, part="GW_Light", label=None, folder=None, extra_tags=()):
    a = eas.spawn_actor_from_class(cls, unreal.Vector(*loc), rot(yaw, pitch, roll))
    tag_actor(a, part, label, folder, extra_tags)
    return a


def point_light(loc, intensity_cd, radius, color=None, temp=2700, shadows=False, source_radius=4.0, label=None,
                light_fn=None, part="GW_Light", indirect=1.0, volumetric=0.0):
    a = spawn(unreal.PointLight, loc, part=part, label=label)
    c = a.get_component_by_class(unreal.PointLightComponent)
    c.set_mobility(unreal.ComponentMobility.MOVABLE)
    c.set_editor_property("intensity_units", unreal.LightUnits.CANDELAS)
    c.set_editor_property("intensity", intensity_cd)
    c.set_editor_property("attenuation_radius", radius)
    c.set_editor_property("source_radius", source_radius)
    c.set_editor_property("soft_source_radius", source_radius * 2)
    c.set_editor_property("cast_shadows", shadows)
    c.set_editor_property("indirect_lighting_intensity", indirect)
    c.set_editor_property("volumetric_scattering_intensity", volumetric)
    if color is not None:
        c.set_editor_property("use_temperature", False)
        c.set_editor_property("light_color", unreal.Color(r=color[0], g=color[1], b=color[2], a=255))
    else:
        c.set_editor_property("use_temperature", True)
        c.set_editor_property("temperature", temp)
    if light_fn:
        c.set_editor_property("light_function_material", mat(light_fn))
    return a


def spot_light(loc, yaw, pitch, intensity_cd, radius, inner, outer, temp=2700, shadows=False, label=None):
    a = spawn(unreal.SpotLight, loc, yaw=yaw, pitch=pitch, label=label)
    c = a.get_component_by_class(unreal.SpotLightComponent)
    c.set_mobility(unreal.ComponentMobility.MOVABLE)
    c.set_editor_property("intensity_units", unreal.LightUnits.CANDELAS)
    c.set_editor_property("intensity", intensity_cd)
    c.set_editor_property("attenuation_radius", radius)
    c.set_editor_property("inner_cone_angle", inner)
    c.set_editor_property("outer_cone_angle", outer)
    c.set_editor_property("cast_shadows", shadows)
    c.set_editor_property("use_temperature", True)
    c.set_editor_property("temperature", temp)
    c.set_editor_property("source_radius", 3.0)
    return a


def rect_light(loc, yaw, w, h, intensity_cd, radius, color=(150, 175, 255), shadows=False, label=None):
    """Rect light emitting along its +X (forward)."""
    a = spawn(unreal.RectLight, loc, yaw=yaw, label=label)
    c = a.get_component_by_class(unreal.RectLightComponent)
    c.set_mobility(unreal.ComponentMobility.MOVABLE)
    c.set_editor_property("intensity_units", unreal.LightUnits.CANDELAS)
    c.set_editor_property("intensity", intensity_cd)
    c.set_editor_property("attenuation_radius", radius)
    c.set_editor_property("source_width", w)
    c.set_editor_property("source_height", h)
    c.set_editor_property("barn_door_angle", 70.0)
    c.set_editor_property("barn_door_length", 15.0)
    c.set_editor_property("cast_shadows", shadows)
    c.set_editor_property("use_temperature", False)
    c.set_editor_property("light_color", unreal.Color(r=color[0], g=color[1], b=color[2], a=255))
    return a


def target_point(loc, tag, yaw=0.0, part="GW_Markers", label=None):
    a = spawn(unreal.TargetPoint, loc, yaw=yaw, part=part, label=label, extra_tags=(tag,))
    return a
