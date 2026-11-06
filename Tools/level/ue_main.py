"""Like Tools/ue_py.py, but only talks to the *interactive* shared editor (skips commandlet processes that also
expose Python remote execution). Usage: python -I -X utf8 ue_main.py path/to/script.py [args] | -c "code"
"""
import importlib.util
import json
import socket
import sys
import time

REMOTE_EXEC = r"J:\Projets\Unreal_Projects\Guess Who\UE_5.8\Engine\Plugins\Experimental\PythonScriptPlugin\Content\Python\remote_execution.py"
spec = importlib.util.spec_from_file_location("remote_execution", REMOTE_EXEC)
rx = importlib.util.module_from_spec(spec)
spec.loader.exec_module(rx)
PROBE = "import unreal\nprint('GWMAIN' if unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem) is not None else 'GWCMD')"


LOCKS = r"J:\Projets\Unreal_Projects\Guess Who\Tools\agent_logs\locks.md"


def wait_for_build(max_s=1800):
    """A packaged build's cook reads /Game while it runs (LOCK BUILD ... UNLOCK BUILD in locks.md): scripts save assets,
    so wait for the unlock instead of saving inside the cook."""
    t0 = time.time()
    while time.time() - t0 < max_s:
        try:
            lines = [l for l in open(LOCKS, encoding="utf-8").read().splitlines() if "BUILD" in l]
        except OSError:
            return
        # a running game test (LOCK GAMETEST) holds .uasset files open: saves then fail silently (Error Code 32)
        tests = [l for l in open(LOCKS, encoding="utf-8").read().splitlines() if "GAMETEST" in l]
        test_on = bool(tests) and tests[-1].startswith("LOCK GAMETEST")
        if (not lines or not lines[-1].startswith("LOCK BUILD")) and not test_on:
            return
        if time.time() - t0 < 1:
            print("waiting for UNLOCK BUILD / UNLOCK GAMETEST in locks.md", flush=True)
        time.sleep(15)


def main():
    wait_for_build()
    if sys.argv[1] == "-c":
        code = "import unreal\n" + sys.argv[2]
    else:
        path = sys.argv[1]
        code = (f"import unreal\nUE_ARGS = {json.dumps(sys.argv[2:])}\n__file__ = {json.dumps(path)}\n"
                f"exec(compile(open(__file__, encoding='utf-8').read(), __file__, 'exec'))")
    cfg = rx.RemoteExecutionConfig()
    cfg.multicast_group_endpoint = ("239.0.0.1", 6766)
    cfg.multicast_bind_address = "127.0.0.1"
    cfg.multicast_ttl = 0
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)   # free command port: the default 6776 collides between clients
    s.bind(("127.0.0.1", 0))
    cfg.command_endpoint = ("127.0.0.1", s.getsockname()[1])
    s.close()
    r = rx.RemoteExecution(cfg)
    r.start()
    try:
        # the editor answers discovery pings only between commands: while another agent's script runs (minutes),
        # keep looking instead of failing after 20 s
        deadline = time.time() + 900
        target = None
        tried = set()
        while time.time() < deadline and target is None:
            time.sleep(1.0)
            for n in list(r.remote_nodes):
                nid = n["node_id"]
                if nid in tried:
                    continue
                tried.add(nid)
                try:
                    r.open_command_connection(nid)
                    res = r.run_command(PROBE, unattended=True, exec_mode=rx.MODE_EXEC_FILE)
                    out = "".join(e.get("output", "") for e in res.get("output", []))
                    if "GWMAIN" in out:
                        target = nid
                        break
                    r.close_command_connection()
                except Exception:
                    tried.discard(nid)  # busy, not a commandlet: try it again
                    try:
                        r.close_command_connection()
                    except Exception:
                        pass
        if target is None:
            print("ERROR: interactive editor not found")
            return 3
        res = r.run_command(code, unattended=True, exec_mode=rx.MODE_EXEC_FILE)
        for e in res.get("output", []):
            t = e.get("output", "").rstrip("\n")
            if t and "Deprecat" not in t:
                print(("[err] " if e.get("type") == "Error" else "") + t)
        if not res.get("success"):
            print("FAILED:", str(res.get("result"))[-3000:])
            return 1
        return 0
    finally:
        r.stop()


if __name__ == "__main__":
    sys.exit(main())
