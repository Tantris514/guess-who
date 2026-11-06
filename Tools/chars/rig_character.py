"""Rig generated characters onto the UE mannequin skeleton (editor: ue_run.py rig_character.py [name ...] [--test]).

The characters are generated in the mannequin's own reference A-pose (AssetGen/chars/templates), so rigging is a
weight transfer, and every existing animation, the AnimBP, the ragdoll and the head / hand_r attach bones keep working:
  1. import the GLB as a static mesh (/Game/GW/Characters/Gen/<name>/), copy it to a dynamic mesh, scale it to cm
     (manifest orientation.uniform_scale_to_cm), feet on z = 0;
  2. align it on the mannequin (Manny or Quinn, manifest "body"): an ICP on x/y translation only, using the generated
     surface points that lie within 8 cm of the body (cloth hanging away from it does not vote);
  3. copy the mannequin's bones, then TransferBoneWeightsFromMesh with InpaintWeights: vertices close to the body take
     its weights, the rest (coat tails, hat, hair volume) get smooth inpainted weights. For gowns ("gown" in the name)
     everything below the crotch is forced to inpaint, so the skirt follows the hips instead of splitting on the legs,
     then eased onto the pelvis with a light thigh sway (skirt_weights) and hung from root toward the floor (hem_drape);
  4. create SK_<name> on SK_Mannequin with the mesh's own bone proportions (Quinn stays Quinn), PA_Mannequin physics,
     and MI_<name> on M_GW_GenChar (gen_material.py) with the GLB's textures.
--test rigs a copy of Quinn shifted by (1.5, -2.5) cm and reports the recovered offset and the weight error.
"""
import importlib
import json
import math
import sys
import unreal

sys.path.insert(0, r'J:\Projets\Unreal_Projects\Guess Who\Tools\chars')
import gen_material as GM
importlib.reload(GM)

GS = unreal.GeometryScript_AssetUtils
SP = unreal.GeometryScript_MeshSpatial
MQ = unreal.GeometryScript_MeshQueries
MT = unreal.GeometryScript_MeshTransforms
LS = unreal.GeometryScript_List
MR = unreal.GeometryScript_MeshRepair
BW = unreal.GeometryScript_BoneWeights
WM = unreal.GeometryScript_WeightMaps
NA = unreal.GeometryScript_NewAssetUtils
EAL = unreal.EditorAssetLibrary
MAN_PATH = r'J:\Projets\Unreal_Projects\Guess Who\AssetGen\manifest.json'
BODY = {'manny': '/Game/Characters/Mannequins/Meshes/SKM_Manny_Simple', 'quinn': '/Game/Characters/Mannequins/Meshes/SKM_Quinn_Simple'}
SKELETON = unreal.load_asset('/Game/Characters/Mannequins/Meshes/SK_Mannequin')
PHYS = unreal.load_asset('/Game/Characters/Mannequins/Rigs/PA_Mannequin')
DEST = '/Game/GW/Characters/Gen'
SKIRT_LEG, SKIRT_BAND, SKIRT_HALF_W = 0.15, 30.0, 50.0   # gown skirts: thigh share at the hem, ease-in depth, side grading
HEM_TOP = 110.0                                           # gown skirts: height where the hang onto root starts (cm)
ARGS = list(globals().get('UE_ARGS') or [])
TEST = '--test' in ARGS
NAMES = [a for a in ARGS if not a.startswith('--')]


def pick(res, typ):
    return next(x for x in (res if isinstance(res, tuple) else (res,)) if isinstance(x, typ))


def positions(dm):
    return list(LS.convert_vector_list_to_array(pick(MQ.get_all_vertex_positions(dm, False), unreal.GeometryScriptVectorList)))


_bodies = {}


def body_mesh(body):
    if body not in _bodies:
        dm = unreal.DynamicMesh()
        GS.copy_mesh_from_skeletal_mesh(unreal.load_asset(BODY[body]), dm, unreal.GeometryScriptCopyMeshFromAssetOptions(), unreal.GeometryScriptMeshReadLOD())
        bvh = pick(SP.build_bvh_for_mesh(dm), unreal.GeometryScriptDynamicMeshBVH)
        _bodies[body] = (dm, bvh)
    return _bodies[body]


def bone_z(body, name):
    mod = unreal.SkeletonModifier()
    mod.set_skeletal_mesh(unreal.load_asset(BODY[body]))
    return mod.get_bone_transform(name, True).translation.z


def nearest(body, p):
    dm, bvh = body_mesh(body)
    r = SP.find_nearest_point_on_mesh(dm, bvh, p, unreal.GeometryScriptSpatialQueryOptions())
    tp = pick(r, unreal.GeometryScriptTrianglePoint)
    return tp.position if tp.valid else None


def align(dm, body, max_d=8.0, iters=12):
    """x/y translation that best seats the generated surface on the body (cm); applied to dm."""
    pts = positions(dm)
    step = max(1, len(pts) // 2500)
    pts = pts[::step]
    tx = ty = 0.0
    for _ in range(iters):
        sx = sy = 0.0
        n = 0
        for p in pts:
            q = unreal.Vector(p.x + tx, p.y + ty, p.z)
            c = nearest(body, q)
            if c is None:
                continue
            d = math.dist((q.x, q.y, q.z), (c.x, c.y, c.z))
            if d < max_d:
                sx += c.x - q.x
                sy += c.y - q.y
                n += 1
        if not n:
            break
        dx, dy = sx / n, sy / n
        tx, ty = tx + dx, ty + dy
        if abs(dx) < 0.03 and abs(dy) < 0.03:
            break
    MT.translate_mesh(dm, unreal.Vector(tx, ty, 0.0))
    return tx, ty, n


def rig(dm, body, gown, report):
    src, _ = body_mesh(body)
    BW.copy_bones_from_mesh(src, dm)
    opts = unreal.GeometryScriptTransferBoneWeightsOptions()
    opts.set_editor_property('transfer_method', unreal.TransferBoneWeightsMethod.INPAINT_WEIGHTS)
    opts.set_editor_property('radius_percentage', 0.03)          # ~6.5 cm on a 2.2 m character
    opts.set_editor_property('normal_threshold', 60.0)
    opts.set_editor_property('layered_mesh_support', True)
    opts.set_editor_property('num_smoothing_iterations', 6)
    opts.set_editor_property('smoothing_strength', 0.4)
    crotch = min(bone_z(body, 'thigh_l'), bone_z(body, 'thigh_r')) - 6.0
    if gown:                                                       # the skirt follows the hips, not the legs
        vals = [1.0 if p.z < crotch else 0.0 for p in positions(dm)]
        h = pick(WM.find_or_add_mesh_weight_map(dm, 'GWInpaint'), unreal.GeometryScriptWeightMapHandle)
        WM.set_mesh_weight_map_values(dm, pick(LS.convert_array_to_scalar_list(vals), unreal.GeometryScriptScalarList), h, False)
        opts.set_editor_property('inpaint_mask', 'GWInpaint')
        report['inpainted_skirt_verts'] = int(sum(vals))
    BW.transfer_bone_weights_from_mesh(src, dm, opts)
    # safety net: a vertex the inpaint left empty (a stray island) takes the closest body point's weights
    nv = len(positions(dm))
    empty = []
    for vid in range(nv):
        r = BW.get_vertex_bone_weights(dm, vid)
        ws = next((x for x in r if isinstance(x, (list, unreal.Array))), [])
        if abs(sum(w.weight for w in ws) - 1.0) > 0.02:
            empty.append(vid)
    if empty:
        near = unreal.DynamicMesh()
        dm.copy_mesh_to_mesh(near)
        co = unreal.GeometryScriptTransferBoneWeightsOptions()
        co.set_editor_property('transfer_method', unreal.TransferBoneWeightsMethod.CLOSEST_POINT_ON_SURFACE)
        BW.copy_bones_from_mesh(src, near)
        BW.transfer_bone_weights_from_mesh(src, near, co)
        for vid in empty:
            ws = next((x for x in BW.get_vertex_bone_weights(near, vid) if isinstance(x, (list, unreal.Array))), [])
            BW.set_vertex_bone_weights(dm, vid, ws)
    report['unweighted_fixed'] = len(empty)
    fold_fingers(dm)
    if gown:
        skirt_weights(dm, crotch)
        hem_drape(dm)


def fold_fingers(dm):
    """Generated fingers sit ~1 cm off the mannequin's, so their transferred weights mix the wrong phalanges (a pinky
    vertex on pinky_03 + metacarpal stretched 18x when the jog closes the fist): the hands follow hand_l / hand_r whole,
    keeping their generated relaxed shape."""
    bones = pick(BW.get_all_bones_info(dm), unreal.Array)
    hand = {str(b.name)[-1]: b.index for b in bones if str(b.name) in ('hand_l', 'hand_r')}
    finger = {b.index: hand[str(b.name)[-1]] for b in bones if str(b.name).startswith(('thumb', 'index', 'middle', 'ring', 'pinky'))}
    for vid in range(len(positions(dm))):
        ws = next(x for x in BW.get_vertex_bone_weights(dm, vid) if isinstance(x, (list, unreal.Array)))
        if not any(w.bone_index in finger for w in ws):
            continue
        mix = {}
        for w in ws:
            b = finger.get(w.bone_index, w.bone_index)
            mix[b] = mix.get(b, 0.0) + w.weight
        BW.set_vertex_bone_weights(dm, vid, [unreal.GeometryScriptBoneWeight(bone_index=b, weight=w) for b, w in mix.items()])


def skirt_weights(dm, crotch):
    """The inpaint leaves the whole skirt on an even pelvis / thigh_l / thigh_r mix, and linear blend skinning turns
    the thighs' opposite swings into a collapse: at a jog the hem rose 16 cm and 94 % of the skirt triangles stretched
    past 1.25x (Tools/chars/deform_qa.py). Below the crotch the weights ease, over SKIRT_BAND cm, to the pelvis plus a
    light sway from the thigh on the same side (graded across SKIRT_HALF_W cm), which brings that to ~6 %."""
    ix = {str(b.name): b.index for b in pick(BW.get_all_bones_info(dm), unreal.Array)}
    pel, tl, tr = ix['pelvis'], ix['thigh_l'], ix['thigh_r']

    def smooth(t):
        t = min(1.0, max(0.0, t))
        return t * t * (3 - 2 * t)

    for vid, p in enumerate(positions(dm)):
        if p.z >= crotch:
            continue
        t = smooth((crotch - p.z) / SKIRT_BAND)
        a = smooth(0.5 + 0.5 * p.x / SKIRT_HALF_W)                  # mannequin's left = +X = thigh_l
        mix = {}
        for w in next(x for x in BW.get_vertex_bone_weights(dm, vid) if isinstance(x, (list, unreal.Array))):
            mix[w.bone_index] = mix.get(w.bone_index, 0.0) + (1 - t) * w.weight
        for b, w in ((pel, 1 - SKIRT_LEG), (tl, SKIRT_LEG * a), (tr, SKIRT_LEG * (1 - a))):
            mix[b] = mix.get(b, 0.0) + t * w
        BW.set_vertex_bone_weights(dm, vid, [unreal.GeometryScriptBoneWeight(bone_index=b, weight=w) for b, w in mix.items() if w > 1e-4])


def hem_drape(dm):
    """A floor-length skirt carried by the pelvis sinks with it: the walk lowers the pelvis 7 cm and the jog pitches it,
    so the hem went 15 cm under the floor and its pooled edge showed as green spikes. Fabric hangs: from HEM_TOP cm
    down to the floor the skirt's pelvis / thigh weights hand over to root (feet level, never tilts). Only that share
    moves, so hands at hip height keep their weights. Hem now stays on the floor; the skirt shortens a little instead."""
    bones = pick(BW.get_all_bones_info(dm), unreal.Array)
    root = next(b.index for b in bones if str(b.name) == 'root')
    lower = {b.index for b in bones if str(b.name) in ('pelvis', 'root') or str(b.name).startswith('thigh')}
    for vid, p in enumerate(positions(dm)):
        if p.z >= HEM_TOP:
            continue
        ws = next(x for x in BW.get_vertex_bone_weights(dm, vid) if isinstance(x, (list, unreal.Array)))
        t = min(1.0, (HEM_TOP - p.z) / HEM_TOP)
        t = t * t * (3 - 2 * t) * sum(w.weight for w in ws if w.bone_index in lower)
        if t < 1e-4:
            continue
        mix = {w.bone_index: w.weight * (1 - t) for w in ws}
        mix[root] = mix.get(root, 0.0) + t
        BW.set_vertex_bone_weights(dm, vid, [unreal.GeometryScriptBoneWeight(bone_index=b, weight=w) for b, w in mix.items() if w > 1e-4])


def make_skeletal(dm, name, material):
    path = f'{DEST}/{name}/SK_{name}'
    if EAL.does_asset_exist(path):
        EAL.delete_asset(path)
    o = unreal.GeometryScriptCreateNewSkeletalMeshAssetOptions()
    o.set_editor_property('use_mesh_bone_proportions', True)
    o.set_editor_property('enable_recompute_normals', False)
    o.set_editor_property('enable_recompute_tangents', True)
    if material:
        o.set_editor_property('materials', {'M0': material})
    sk = pick(NA.create_new_skeletal_mesh_asset_from_mesh(dm, SKELETON, path, o), unreal.SkeletalMesh)
    sk.set_editor_property('physics_asset', PHYS)
    EAL.save_loaded_asset(sk, False)
    return sk


def import_static(name, glb, reimport=False):
    dest = f'{DEST}/{name}'
    found = [unreal.load_asset(p) for p in EAL.list_assets(dest, recursive=True)] if EAL.does_directory_exist(dest) else []
    meshes = [m for m in found if isinstance(m, unreal.StaticMesh)]
    if meshes and reimport:
        # importing over the old GLB import keeps its textures (char_minuit, 2026-11-02): drop that import first
        # (<dest>/<glb stem>/StaticMeshes|Textures|Materials); the MI below and the ghost MI (s29) are re-pointed
        for root in {m.get_path_name().split('/StaticMeshes/')[0] for m in meshes if '/StaticMeshes/' in m.get_path_name()}:
            EAL.delete_directory(root)
    if not meshes or reimport:
        t = unreal.AssetImportTask()
        t.filename = glb; t.destination_path = dest; t.automated = True; t.replace_existing = True; t.save = True
        unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks([t])
        meshes = [m for m in (unreal.load_asset(p) for p in t.get_editor_property('imported_object_paths')) if isinstance(m, unreal.StaticMesh)]
    return meshes[0]


if TEST:
    src, _ = body_mesh('quinn')
    dm = unreal.DynamicMesh()
    GS.copy_mesh_from_skeletal_mesh(unreal.load_asset(BODY['quinn']), dm, unreal.GeometryScriptCopyMeshFromAssetOptions(), unreal.GeometryScriptMeshReadLOD())
    BW.discard_bones_from_mesh(dm)
    MT.translate_mesh(dm, unreal.Vector(1.5, -2.5, 0.0))
    tx, ty, n = align(dm, 'quinn')
    rep = {}
    rig(dm, 'quinn', False, rep)
    sk = make_skeletal(dm, 'gw_rigtest', None)
    print(f'TEST align recovered ({tx:.2f}, {ty:.2f}) for a shift of (1.5, -2.5) -> residual ({tx + 1.5:.2f}, {ty - 2.5:.2f}) cm; '
          f'{n} pts; {rep}; asset {sk.get_path_name()}')

MAN = json.load(open(MAN_PATH, encoding='utf-8'))
changed = False
for e in MAN['assets']:
    if e.get('kind') != 'character' or e.get('status') != 'approved' or (NAMES and e['name'] not in NAMES):
        continue
    name, body = e['name'], e['body']
    sm = import_static(name, e['files']['glb'], '--reimport' in ARGS)
    dm = unreal.DynamicMesh()
    GS.copy_mesh_from_static_mesh(sm, dm, unreal.GeometryScriptCopyMeshFromAssetOptions(), unreal.GeometryScriptMeshReadLOD())
    # the GLB is split along every UV seam (hundreds of islands): inpainting cannot cross them, so weld first
    islands = MQ.get_num_connected_components(dm)
    wo = unreal.GeometryScriptWeldEdgesOptions()
    wo.set_editor_property('tolerance', 0.001)
    MR.weld_mesh_edges(dm, wo)
    MR.compact_mesh(dm)                                            # contiguous vertex ids for the per-vertex passes
    s = e['orientation']['uniform_scale_to_cm'] / 100.0
    MT.scale_mesh(dm, unreal.Vector(s, s, s), unreal.Vector(0, 0, 0), True)
    box = MQ.get_mesh_bounding_box(dm)
    MT.translate_mesh(dm, unreal.Vector(-(box.min.x + box.max.x) / 2, -(box.min.y + box.max.y) / 2, -box.min.z))
    tx, ty, n = align(dm, body)
    rep = {'align_cm': [round(tx, 2), round(ty, 2)], 'align_pts': n, 'islands': [islands, MQ.get_num_connected_components(dm)]}
    box = MQ.get_mesh_bounding_box(dm)
    rep['height_cm'] = round(box.max.z - box.min.z, 1)
    rig(dm, body, 'gown' in name or bool(e.get('gown')), rep)     # manifest "gown": true for robes whose name has no "gown"
    # the imported M_GLTF instance is not usable on a skeletal mesh: same textures on M_GW_GenChar (gen_material.py)
    tex = {str(t.parameter_info.name): t.parameter_value for t in sm.get_material(0).get_editor_property('texture_parameter_values')}
    mi = GM.instance(name, f'{DEST}/{name}', tex.get('BaseColorTexture'), tex.get('MetallicRoughnessTexture'), tex.get('NormalTexture'))
    sk = make_skeletal(dm, name, mi)
    rep['skeletal_mesh'] = sk.get_path_name()
    e['rig'] = rep
    changed = True
    print(name, rep)
if changed:
    with open(MAN_PATH, 'w', encoding='utf-8') as f:
        json.dump(MAN, f, indent=1, ensure_ascii=False)
