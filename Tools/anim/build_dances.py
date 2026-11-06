"""Builds the 1930s dance clips in /Game/GW/Anims/Dance (AnimSequence on SK_Mannequin) from Tools/anim/dances.py.

Editor: python -I -X utf8 Tools/ui/ue_run.py Tools/anim/build_dances.py [DanceName ...]
- Every bone is keyed at 30 fps; the last key equals the first, so the loop is seamless.
- Re-runnable: an existing asset keeps its object (the Blueprint references stay valid) and gets its tracks rewritten.
- Afterwards it checks the skeleton (bone names and reference pose against Tools/anim/sk_mannequin.json) and samples
  each clip back through the engine (foot heights per frame) as a first sanity check; Tools/anim/ue_eval.py dumps the
  evaluated poses for the full offline QA (dance_qa.py ue=...).
Order of the clips = BP_GW_Character.DanceAnims = DanceId - 1 (s36_social.py reads DANCES too).
"""
import importlib
import sys

import unreal

ANIM = r'J:\Projets\Unreal_Projects\Guess Who\Tools\anim'
if ANIM not in sys.path:
    sys.path.insert(0, ANIM)
import dance_core  # noqa: E402
import dances  # noqa: E402
importlib.reload(dance_core)
importlib.reload(dances)

DEST = '/Game/GW/Anims/Dance'
SKEL = '/Game/Characters/Mannequins/Meshes/SK_Mannequin'
PREVIEW = '/Game/Characters/Mannequins/Meshes/SKM_Manny_Simple'
FPS = 30
EAL = unreal.EditorAssetLibrary
AT = unreal.AssetToolsHelpers.get_asset_tools()
APE = unreal.AnimPoseExtensions
only = set(UE_ARGS) if 'UE_ARGS' in globals() else set()   # noqa: F821

skel = unreal.load_asset(SKEL)
sk = dance_core.Skeleton()

# ---------------------------------------------------------------- skeleton check
ref = APE.get_reference_pose(skel)
ue_names = [str(n) for n in APE.get_bone_names(ref)]
missing = [n for n in sk.names if n not in ue_names]
extra = [n for n in ue_names if n not in sk.names]
worst = 0.0
for i, n in enumerate(sk.names):
    if n in ue_names:
        t = APE.get_ref_bone_pose(ref, n, unreal.AnimPoseSpaces.LOCAL)
        d = t.translation - unreal.Vector(*sk.ref_t[i])
        worst = max(worst, d.length())
print(f'skeleton: {len(ue_names)} bones, missing from UE {missing}, not in dump {extra}, worst ref translation diff {worst:.3f} cm')
assert not missing, 'the dump does not match SK_Mannequin'

if not EAL.does_directory_exist(DEST):
    EAL.make_directory(DEST)


def get_seq(name):
    path = f'{DEST}/{name}'
    if EAL.does_asset_exist(path):
        return unreal.load_asset(path)
    f = unreal.AnimSequenceFactory()
    f.set_editor_property('target_skeleton', skel)
    seq = AT.create_asset(name, DEST, unreal.AnimSequence, f)
    print('created', path)
    return seq


built = []
for k, dance in enumerate(dances.ALL):
    name = f'AS_GW_Dance_{dance.name}'
    if only and dance.name not in only and name not in only:
        built.append(unreal.load_asset(f'{DEST}/{name}'))
        continue
    solver = dance_core.Solver(sk)
    n, keys = dance_core.bake(dance, solver, FPS)
    seq = get_seq(name)
    ctrl = seq.get_editor_property('controller')
    ctrl.open_bracket(unreal.Text(f'GW dance {dance.name}'), False)
    ctrl.remove_all_bone_tracks(False)
    ctrl.set_frame_rate(unreal.FrameRate(FPS, 1), False)
    ctrl.set_number_of_frames(unreal.FrameNumber(n), False)
    fails = []
    for bi, bone in enumerate(sk.names):
        ctrl.add_bone_curve(bone, False)
        pos = [unreal.Vector(*kk[1][bi]) for kk in keys]
        rot = [unreal.Quat(*kk[0][bi]) for kk in keys]
        scl = [unreal.Vector(1.0, 1.0, 1.0)] * len(keys)
        if not ctrl.set_bone_track_keys(bone, pos, rot, scl, False):
            fails.append(bone)
    ctrl.close_bracket(False)
    seq.set_editor_property('enable_root_motion', False)
    try:
        seq.set_preview_skeletal_mesh(unreal.load_asset(PREVIEW))
    except Exception:
        pass
    EAL.set_metadata_tag(seq, 'GWDance', f'{k + 1} {dance.label}')
    EAL.save_loaded_asset(seq, False)
    length = unreal.AnimationLibrary.get_sequence_length(seq)
    nk = unreal.AnimationLibrary.get_num_frames(seq)
    # engine read-back: foot (ankle) height and pelvis height over the loop
    lo, hi, pz = 1e9, -1e9, []
    for f in range(0, n + 1, 3):
        poses = unreal.AnimationLibrary.get_bone_poses_for_frame(seq, ['pelvis', 'foot_l', 'foot_r'], f, False)
        pz.append(poses[0].translation.z)
    print(f'{name}: {n} frames ({length:.2f} s, engine frames {nk}), drops {solver.stats["pelvis_drops"]}, '
          f'track failures {fails}, pelvis z {min(pz):.1f}..{max(pz):.1f}')
    built.append(seq)
print('dance clips:', [b.get_name() for b in built])
