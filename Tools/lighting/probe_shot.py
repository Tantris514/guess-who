"""Debug shots: python -I -X utf8 probe_shot.py <cam label | x,y,z,pitch,yaw> <out name> [wait] ["cmd1;cmd2"] ["undo1;undo2"]
Moves the editor viewport, runs console commands, waits, HighResShot -> Tools/qa/shots/probe/<name>.png, runs undo cmds.
One remote-exec connection per step (other agents' connections abort long-held ones)."""
import glob, os, shutil, sys, time
sys.path.insert(0, r"J:\Projets\Unreal_Projects\Guess Who\Tools\qa")
from shoot_cams import Editor, SHOT_DIR, OUT_ROOT  # noqa: E402


def run(code, tries=20):
    for i in range(tries):  # noqa
        ed = None
        try:
            ed = Editor(6766)
            return ed.run("import unreal\nues = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem)\n"
                          "w = ues.get_editor_world()\n" + code)
        except (SystemExit, OSError, RuntimeError) as e:
            err = e
            time.sleep(1.5)
        finally:
            if ed:
                ed.close()
    raise RuntimeError(f"remote exec failed: {err}")


def cmds_code(cmds):
    return "\n".join(f"unreal.SystemLibrary.execute_console_command(w, {c!r})" for c in cmds) or "pass"


def shoot(cam, name, wait=6, cmds=(), undo=(), res="1280x720"):
    out_dir = os.path.join(OUT_ROOT, "probe")
    os.makedirs(out_dir, exist_ok=True)
    if "," in cam:
        x, y, z, p, yw = (float(v) for v in cam.split(","))
        mv = f"ues.set_level_viewport_camera_info(unreal.Vector({x},{y},{z}), unreal.Rotator(pitch={p}, yaw={yw}, roll=0))"
    else:
        mv = ("a = [a for a in unreal.get_editor_subsystem(unreal.EditorActorSubsystem).get_all_level_actors() "
              f"if a.get_actor_label() == '{cam}'][0]\n"
              "ues.set_level_viewport_camera_info(a.get_actor_location(), a.get_actor_rotation())")
    shot = f"GWPR_{name}"
    try:
        run("unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).editor_set_game_view(True)\n" + mv + "\n" +
            cmds_code(cmds))
        time.sleep(wait)
        for old in glob.glob(os.path.join(SHOT_DIR, shot + "*.png")):
            os.remove(old)
        run(f"unreal.SystemLibrary.execute_console_command(w, 'HighResShot {res} filename={shot}')")
        t0, found = time.time(), None
        while time.time() - t0 < 60 and not found:
            time.sleep(0.5)
            h = glob.glob(os.path.join(SHOT_DIR, shot + "*.png"))
            if h and os.path.getsize(h[0]) > 0:
                time.sleep(0.5)
                found = h[0]
        if found:
            dst = os.path.join(out_dir, name + ".png")
            shutil.move(found, dst)
            print("ok", dst)
            return dst
        print("MISSING", name)
    finally:
        if undo:
            run(cmds_code(undo))


if __name__ == "__main__":
    a = sys.argv
    shoot(a[1], a[2], float(a[3]) if len(a) > 3 else 6,
          [c for c in (a[4] if len(a) > 4 else "").split(";") if c.strip()],
          [c for c in (a[5] if len(a) > 5 else "").split(";") if c.strip()])
