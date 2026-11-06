"""ComfyMCP from AssetGen/assetgen.py with a robust stderr drain (the original thread dies on non-UTF-8 bytes, after which
comfy-mcp can block on a full stderr pipe and the batch never returns)."""
import json, os, subprocess, sys, threading
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import assetgen  # noqa: E402


class ComfyMCP(assetgen.ComfyMCP):
    def __init__(self):
        env = dict(os.environ, COMFY_BIN=assetgen.COMFY_BIN, PYTHONIOENCODING="utf-8")
        self.proc = subprocess.Popen([assetgen.EXE], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                     env=env, text=True, encoding="utf-8", errors="replace", bufsize=1)
        threading.Thread(target=self._drain, daemon=True).start()
        self.msg_id = 0
        self._rpc("initialize", {"protocolVersion": "2025-06-18", "capabilities": {}, "clientInfo": {"name": "gw-ui", "version": "1"}})
        self._send({"jsonrpc": "2.0", "method": "notifications/initialized"})

    def _drain(self):
        try:
            for _ in self.proc.stderr:
                pass
        except Exception:
            pass
