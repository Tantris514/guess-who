"""The waiters' two clips (the user, 2026-11-05: "The server is not animated"): the right forearm level under the tray (BP_GW_Barman.Tray, mesh space (-28, 24, 115)), the palm up, the left hand behind the back.
Editor: python -I -X utf8 Tools/ui/ue_run.py Tools/anim/waiter_clips.py
BP_GW_Barman plays them directly (AnimSingleNode, like the zombie) on the mobile vendors: AS_GW_Waiter_Walk when he moves, AS_GW_Waiter_Idle when he stands; every machine picks from the replicated velocity. Same solver as the dances."""
import importlib, math, sys
import unreal
ANIM = r'J:\Projets\Unreal_Projects\Guess Who\Tools\anim'
if ANIM not in sys.path:
    sys.path.insert(0, ANIM)
import dance_core, dances
importlib.reload(dance_core); importlib.reload(dances)
from dance_core import Pose

DEST = '/Game/GW/Anims/Waiter'
SKEL = '/Game/Characters/Mannequins/Meshes/SK_Mannequin'
EAL = unreal.EditorAssetLibrary
AT = unreal.AssetToolsHelpers.get_asset_tools()
FPS = 30
# wrist relative to the right shoulder, in the chest frame (out, fwd, up): under the tray
TRAY_HAND = (9.0, 25.0, -34.0)
TRAY = dict(elbow_r=(0.55, -0.55, -0.6), palm_r=((0.1, 1.0, 0.0), (0.0, 0.0, 1.0), 1.0), curl_r=0.35, thumb_r=0.5,
            hand_l=(-2.0, -17.0, -42.0), elbow_l=(0.8, -0.6, -0.1), curl_l=0.8, clav_r=(1.0, 0.0))


class WaiterWalk:
    """Steps in place while the capsule moves at 150 cm/s: a 0.9 s cycle. In stance a foot slides back at the body's speed (+37 to -37 cm in 0.495 s), so it stays planted on the floor; the swing brings it forward."""
    name, length = 'AS_GW_Waiter_Walk', 0.9
    STANCE = 0.55

    def foot(self, u):
        if u < self.STANCE:
            k = u / self.STANCE
            return dict(x=10.0, y=37.0 - 74.0 * k, yaw=5.0, heel=22.0 * max(0.0, (k - 0.72) / 0.28), toe=12.0 * max(0.0, 1.0 - k / 0.12), lift=0.0, air=False)
        k = (u - self.STANCE) / (1.0 - self.STANCE)
        e = k * k * (3.0 - 2.0 * k)
        return dict(x=10.0, y=-37.0 + 74.0 * e, yaw=5.0, heel=22.0 * max(0.0, 1.0 - k / 0.25), toe=12.0 * max(0.0, (k - 0.7) / 0.3), lift=9.0 * math.sin(math.pi * k), air=True)

    def pose(self, t):
        T = self.length
        u = (t % T) / T
        ph = 2 * math.pi * u
        s, c2 = math.sin(ph), math.cos(2 * ph)
        return Pose(pelvis=(1.5 * s, 0.0, -2.5 + 0.9 * c2), pelvis_rot=(2.0, 1.0 * s, 4.0 * s), spine=(2.0, -0.6 * s, -3.5 * s), neck=(3.0, 0.5 * s, 2.0 * s),
                    hand_r=(TRAY_HAND[0], TRAY_HAND[1], TRAY_HAND[2] + 0.5 * c2), foot_l=self.foot(u), foot_r=self.foot((u + 0.5) % 1.0), knee_l=2.0, knee_r=2.0, **TRAY)


class WaiterIdle:
    name, length = 'AS_GW_Waiter_Idle', 4.0

    def pose(self, t):
        b = math.sin(2 * math.pi * t / self.length)
        return Pose(pelvis=(0.0, 0.0, -0.4 + 0.2 * b), spine=(2.0 + 0.5 * b, 0.0, 0.0), neck=(3.0, 0.0, 4.0 * math.sin(2 * math.pi * t / self.length + 1.0)),
                    hand_r=(TRAY_HAND[0], TRAY_HAND[1], TRAY_HAND[2] + 0.3 * b), foot_l=dict(x=12.0, y=1.0, yaw=8.0), foot_r=dict(x=12.0, y=-1.0, yaw=8.0), **TRAY)


if not EAL.does_directory_exist(DEST):
    EAL.make_directory(DEST)
skel = unreal.load_asset(SKEL)
sk = dance_core.Skeleton()
for clip in (WaiterWalk(), WaiterIdle()):
    path = f'{DEST}/{clip.name}'
    if EAL.does_asset_exist(path):
        seq = unreal.load_asset(path)
    else:
        f = unreal.AnimSequenceFactory()
        f.set_editor_property('target_skeleton', skel)
        seq = AT.create_asset(clip.name, DEST, unreal.AnimSequence, f)
    solver = dance_core.Solver(sk)
    n, keys = dance_core.bake(clip, solver, FPS)
    ctrl = seq.get_editor_property('controller')
    ctrl.open_bracket(unreal.Text(clip.name), False)
    ctrl.remove_all_bone_tracks(False)
    ctrl.set_frame_rate(unreal.FrameRate(FPS, 1), False)
    ctrl.set_number_of_frames(unreal.FrameNumber(n), False)
    fails = []
    for bi, bone in enumerate(sk.names):
        ctrl.add_bone_curve(bone, False)
        if not ctrl.set_bone_track_keys(bone, [unreal.Vector(*k[1][bi]) for k in keys], [unreal.Quat(*k[0][bi]) for k in keys], [unreal.Vector(1, 1, 1)] * len(keys), False):
            fails.append(bone)
    ctrl.close_bracket(False)
    seq.set_editor_property('enable_root_motion', False)
    print(clip.name, n, 'frames, failures', fails, 'saved', EAL.save_loaded_asset(seq, False), 'length', unreal.AnimationLibrary.get_sequence_length(seq))
    # read back in component space: is the right wrist under the tray? (mesh space: the tray's plate is near (-28, 24, 115))
    for fr in (0, n // 2):
        p = unreal.AnimationLibrary.get_bone_poses_for_frame(seq, ['root', 'pelvis', 'spine_01', 'spine_02', 'spine_03', 'clavicle_r', 'upperarm_r', 'lowerarm_r', 'hand_r'], fr, False)
        t = unreal.Transform()
        for q in p:
            t = unreal.MathLibrary.compose_transforms(q, t)
        print('  frame', fr, 'hand_r mesh space', [round(v, 1) for v in (t.translation.x, t.translation.y, t.translation.z)])
