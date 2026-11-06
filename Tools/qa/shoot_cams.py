"""Rendered QA screenshots of L_Manor from every GW_ReviewCam, taken in the shared editor started with -Render (Tools/start_editor.ps1 -Render).

  python -I -X utf8 shoot_cams.py [--res 1280x720] [--wait 6] [--only Cam_Hall_FromCloak,Cam_Study] [--tag before]

Holds one Python remote-execution connection to the interactive editor, moves the level viewport to each camera,
lets Lumen/streaming settle for --wait seconds, then runs HighResShot. PNGs land in Tools/qa/shots/<tag>/.
"""
import argparse
import glob
import importlib.util
import json
import os
import shutil
import socket
import sys
import time

REMOTE_EXEC = r"J:\Projets\Unreal_Projects\Guess Who\UE_5.8\Engine\Plugins\Experimental\PythonScriptPlugin\Content\Python\remote_execution.py"
SHOT_DIR = r"J:\Projets\Unreal_Projects\Guess Who\GuessWho\Saved\Screenshots\WindowsEditor"
OUT_ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "shots")
spec = importlib.util.spec_from_file_location("remote_execution", REMOTE_EXEC)
rx = importlib.util.module_from_spec(spec)
spec.loader.exec_module(rx)
PROBE = "import unreal\nprint('GWMAIN' if unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem) is not None else 'GWCMD')"

SETUP = """
import unreal, json
try:
    # keep the viewport drawing at full rate while the editor window is in the background
    perf = unreal.get_default_object(unreal.load_class(None, '/Script/UnrealEd.EditorPerformanceSettings'))
    perf.set_editor_property('throttle_cpu_when_not_foreground', False)
    print('throttle off')
except Exception as e:
    print('throttle setting not changed:', e)
les = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
les.editor_set_game_view(True)
ues = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem)
eas = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
world = ues.get_editor_world()
cams = []
for a in eas.get_all_level_actors():
    if a.actor_has_tag('GW_ReviewCam'):
        l, r = a.get_actor_location(), a.get_actor_rotation()
        cams.append([a.get_actor_label(), [l.x, l.y, l.z], [r.pitch, r.yaw, r.roll]])
cams.sort()
print('GWJSON' + json.dumps({'world': world.get_name(), 'cams': cams}))
"""

MOVE = """
import unreal
ues = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem)
ues.set_level_viewport_camera_info(unreal.Vector({x}, {y}, {z}), unreal.Rotator(pitch={p}, yaw={yw}, roll={r}))
"""

SHOOT = """
import unreal
ues = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem)
unreal.SystemLibrary.execute_console_command(ues.get_editor_world(), 'HighResShot {res} filename={name}')
"""


class Editor:
    def __init__(self, port=6766):
        cfg = rx.RemoteExecutionConfig()
        cfg.multicast_group_endpoint = ("239.0.0.1", port)
        cfg.multicast_bind_address = "127.0.0.1"
        cfg.multicast_ttl = 0
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)   # free command port: the default 6776 collides between clients
        s.bind(("127.0.0.1", 0))
        cfg.command_endpoint = ("127.0.0.1", s.getsockname()[1])
        s.close()
        self.r = rx.RemoteExecution(cfg)
        self.r.start()
        deadline, tried = time.time() + 30, set()
        while time.time() < deadline:
            time.sleep(1.0)
            for n in list(self.r.remote_nodes):
                if n["node_id"] in tried:
                    continue
                tried.add(n["node_id"])
                try:
                    self.r.open_command_connection(n["node_id"])
                    if "GWMAIN" in self.run(PROBE):
                        return
                    self.r.close_command_connection()
                except Exception:
                    try:
                        self.r.close_command_connection()
                    except Exception:
                        pass
        raise SystemExit("ERROR: interactive editor not found")

    def run(self, code):
        res = self.r.run_command(code, unattended=True, exec_mode=rx.MODE_EXEC_FILE)
        out = "".join(e.get("output", "") for e in res.get("output", []))
        if not res.get("success"):
            raise RuntimeError(f"editor command failed: {str(res.get('result'))[-1500:]}\n{out[-1500:]}")
        return out

    def close(self):
        self.r.stop()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--res", default="1280x720")
    ap.add_argument("--wait", type=float, default=6.0)
    ap.add_argument("--only", default="")
    ap.add_argument("--tag", default="pass1")
    ap.add_argument("--port", type=int, default=6766, help="remote-exec multicast port (6766 = shared editor)")
    a = ap.parse_args()
    out_dir = os.path.join(OUT_ROOT, a.tag)
    os.makedirs(out_dir, exist_ok=True)
    ed = Editor(a.port)
    try:
        info = json.loads(ed.run(SETUP).split("GWJSON", 1)[1].strip())
        print("world:", info["world"], "cams:", len(info["cams"]))
        only = {s for s in a.only.split(",") if s}
        for label, (x, y, z), (p, yw, r) in info["cams"]:
            if only and label not in only:
                continue
            ed.run(MOVE.format(x=x, y=y, z=z, p=p, yw=yw, r=r))
            time.sleep(a.wait)
            name = f"GWQA_{label}"
            for old in glob.glob(os.path.join(SHOT_DIR, name + "*.png")):
                os.remove(old)
            ed.run(SHOOT.format(res=a.res, name=name))
            deadline, found = time.time() + 90, None
            while time.time() < deadline and not found:
                time.sleep(0.5)
                hits = glob.glob(os.path.join(SHOT_DIR, name + "*.png"))
                if hits and os.path.getsize(hits[0]) > 0:
                    time.sleep(0.5)
                    found = hits[0]
            if found:
                dst = os.path.join(out_dir, label + ".png")
                shutil.move(found, dst)
                print("ok", label, dst)
            else:
                print("MISSING", label)
    finally:
        ed.close()


if __name__ == "__main__":
    main()
