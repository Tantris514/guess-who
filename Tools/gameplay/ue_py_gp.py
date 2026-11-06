"""Run a Python file (or a snippet) inside the running Unreal Editor through Python remote execution.

  python -I -X utf8 ue_py.py path/to/script.py [args...]   (args visible in the script as UE_ARGS)
  python -I -X utf8 ue_py.py -c "print(unreal.SystemLibrary.get_engine_version())"
"""
import importlib.util
import json
import sys
import time

REMOTE_EXEC = r"J:\Projets\Unreal_Projects\Guess Who\UE_5.8\Engine\Plugins\Experimental\PythonScriptPlugin\Content\Python\remote_execution.py"
spec = importlib.util.spec_from_file_location("remote_execution", REMOTE_EXEC)
remote_execution = importlib.util.module_from_spec(spec)
spec.loader.exec_module(remote_execution)


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        return 2
    if sys.argv[1] == "-c":
        code = "import unreal\n" + sys.argv[2]
    else:
        with open(sys.argv[1], encoding="utf-8") as f:
            body = f.read()
        code = f"UE_ARGS = {json.dumps(sys.argv[2:])}\n__file__ = {json.dumps(sys.argv[1])}\n" + body

    config = remote_execution.RemoteExecutionConfig()
    config.multicast_group_endpoint = ("239.0.0.1", 6766)
    config.multicast_bind_address = "127.0.0.1"
    config.multicast_ttl = 0
    config.command_endpoint = ("127.0.0.1", 6791)  # private port: 6776 is often held by other agents
    remote = remote_execution.RemoteExecution(config)
    remote.start()
    try:
        deadline = time.time() + 20
        while not remote.remote_nodes and time.time() < deadline:
            time.sleep(0.25)
        if not remote.remote_nodes:
            print("ERROR: no Unreal Editor found (is it open with remote execution enabled?)")
            return 3
        remote.open_command_connection(remote.remote_nodes[0]["node_id"])
        result = remote.run_command(code, unattended=True, exec_mode=remote_execution.MODE_EXEC_FILE)
        for entry in result.get("output", []):
            text = entry.get("output", "").rstrip("\n")
            if text:
                print(("[warn] " if entry.get("type") == "Warning" else "[err] " if entry.get("type") == "Error" else "") + text)
        if not result.get("success"):
            print("FAILED:", result.get("result"))
            return 1
        return 0
    finally:
        remote.stop()


if __name__ == "__main__":
    sys.exit(main())
