"""Dump a rigged character for the offline deformation check (editor: ue_run.py deform_dump.py <name|quinn|manny>).

Writes AssetGen/chars/deform/<name>.json: reference-pose vertices, triangles, per-vertex bone weights, the bone
hierarchy with its reference local transforms, and the local bone poses of idle / walk / jog sampled over each cycle.
Tools/chars/deform_qa.py skins it with numpy (no GPU needed) and measures how the triangles stretch.
"""
import json
import os
import unreal

GS = unreal.GeometryScript_AssetUtils
MQ = unreal.GeometryScript_MeshQueries
LS = unreal.GeometryScript_List
BW = unreal.GeometryScript_BoneWeights
OUT = r'J:\Projets\Unreal_Projects\Guess Who\AssetGen\chars\deform'
BODY = {'manny': '/Game/Characters/Mannequins/Meshes/SKM_Manny_Simple', 'quinn': '/Game/Characters/Mannequins/Meshes/SKM_Quinn_Simple'}
ANIMS = {'idle': '/Game/Characters/Mannequins/Anims/Unarmed/MM_Idle',
         'walk': '/Game/Characters/Mannequins/Anims/Unarmed/Walk/MF_Unarmed_Walk_Fwd',
         'jog': '/Game/Characters/Mannequins/Anims/Unarmed/Jog/MF_Unarmed_Jog_Fwd'}
FRAMES = 24


def pick(res, typ):
    return next(x for x in (res if isinstance(res, tuple) else (res,)) if isinstance(x, typ))


def xf(t):
    q = t.rotation
    return [[q.x, q.y, q.z, q.w], [t.translation.x, t.translation.y, t.translation.z], [t.scale3d.x, t.scale3d.y, t.scale3d.z]]


name = UE_ARGS[0]
path = BODY.get(name, f'/Game/GW/Characters/Gen/{name}/SK_{name}')
dm = unreal.DynamicMesh()
GS.copy_mesh_from_skeletal_mesh(unreal.load_asset(path), dm, unreal.GeometryScriptCopyMeshFromAssetOptions(), unreal.GeometryScriptMeshReadLOD())
unreal.GeometryScript_MeshRepair.compact_mesh(dm)
verts = [[p.x, p.y, p.z] for p in LS.convert_vector_list_to_array(pick(MQ.get_all_vertex_positions(dm, False), unreal.GeometryScriptVectorList))]
tris = [[t.x, t.y, t.z] for t in LS.convert_triangle_list_to_array(pick(MQ.get_all_triangle_indices(dm, False), unreal.GeometryScriptTriangleList))]
weights = []
for vid in range(len(verts)):
    ws = next((x for x in BW.get_vertex_bone_weights(dm, vid) if isinstance(x, (list, unreal.Array))), [])
    weights.append([[w.bone_index, w.weight] for w in ws])
bones = [{'name': str(b.name), 'parent': b.parent_index, 'local': xf(b.local_transform), 'ref_world': xf(b.world_transform)}
         for b in pick(BW.get_all_bones_info(dm), unreal.Array)]
names = [b['name'] for b in bones]
anims = {}
for key, apath in ANIMS.items():
    seq = unreal.load_asset(apath)
    length = unreal.AnimationLibrary.get_sequence_length(seq)
    frames = []
    for i in range(FRAMES):
        poses = pick(unreal.AnimationLibrary.get_bone_poses_for_time(seq, names, length * i / FRAMES, False), unreal.Array)
        frames.append([xf(t) for t in poses])
    anims[key] = {'length': length, 'frames': frames}
os.makedirs(OUT, exist_ok=True)
json.dump({'name': name, 'verts': verts, 'tris': tris, 'weights': weights, 'bones': bones, 'anims': anims},
          open(os.path.join(OUT, f'{name}.json'), 'w'))
print(name, len(verts), 'verts', len(tris), 'tris', len(bones), 'bones', {k: round(v['length'], 2) for k, v in anims.items()})
