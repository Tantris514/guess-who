"""GPU timing per review camera in the shared editor viewport (ProfileGPU parsed from GuessWho.log).
  python -I -X utf8 perf.py [Cam_A,Cam_B,...] [screen_percentage]
The editor viewport is ~1014x550; screen percentage 190 renders ~1927x1045, i.e. about 1080p pixel count."""
import os, re, sys, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from probe_shot import run  # noqa: E402

LOG = r"J:\Projets\Unreal_Projects\Guess Who\GuessWho\Saved\Logs\GuessWho.log"
cams = (sys.argv[1] if len(sys.argv) > 1 and sys.argv[1] else
        "Cam_Hall_FromCloak,Cam_Ballroom_Diag,Cam_Library_Fire,Cam_Dining_Table,Cam_Billiard,Cam_Conservatory,"
        "Cam_CorridorW,Cam_Study").split(",")
sp = sys.argv[2] if len(sys.argv) > 2 else "190"
KEYS = ["Frame ", "Nanite::VisBuffer", "ShadowDepths", "LumenSceneUpdate", "RayTracingScene", "BasePass",
        "DiffuseIndirectAndAO", "Lights", "TranslucencyLightingVolume", "ComputeVolumetricFog", "PostProcessing",
        "Translucency"]
CV = os.environ.get("GW_SP_CVAR", "r.Editor.Viewport.ScreenPercentage")
old = run(f"print('SP', unreal.SystemLibrary.get_console_variable_float_value('{CV}'))").split("SP")[-1].strip()
run(f"unreal.SystemLibrary.execute_console_command(w, '{CV} {sp}')")
try:
    for cam in cams:
        run("a = [a for a in unreal.get_editor_subsystem(unreal.EditorActorSubsystem).get_all_level_actors() "
            f"if a.get_actor_label() == '{cam}'][0]\n"
            "ues.set_level_viewport_camera_info(a.get_actor_location(), a.get_actor_rotation())")
        time.sleep(6)
        size0 = os.path.getsize(LOG)
        run("unreal.SystemLibrary.execute_console_command(w, 'ProfileGPU')")
        time.sleep(5)
        with open(LOG, "rb") as fh:
            fh.seek(size0)
            txt = fh.read().decode("utf-8", "replace")
        res = re.findall(r"(\d{3,4}x\d{3,4}) -> (\d{3,4}x\d{3,4})", txt)
        found = {}
        for line in txt.splitlines():
            parts = line.split("┃")
            if len(parts) < 4:
                continue
            cols = parts[2].split("│")
            if len(cols) < 6:
                continue
            ms = cols[5].replace("ms", "").strip()
            name = parts[3].strip()
            for k in KEYS:
                if name.startswith(k):
                    try:
                        found[k] = max(found.get(k, 0.0), float(ms))
                    except ValueError:
                        pass
        print(f"{cam:22s} {(res[0][0] + '>' + res[0][1]) if res else '?':>20s}  GPU {found.get('Frame ', 0):5.2f} ms | " +
              "  ".join(f"{k.strip().replace('Compute','')}={v:.2f}" for k, v in found.items() if k != "Frame "))
finally:
    run(f"unreal.SystemLibrary.execute_console_command(w, '{CV} {old}')")
    print("restored", CV, old)
