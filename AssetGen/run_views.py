"""Back + side (left) edits for an approved front, one after the other (one ComfyUI job at a time).
  python -I run_views.py NAME BODY "BACK_DESC" "SIDE_DESC" [--back-seeds a,b,c,d] [--side-seeds e,f,g,h]"""
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ROOT)
import char_prompts as cp  # noqa: E402

name, body, back_desc, side_desc = sys.argv[1:5]
bs = sys.argv[sys.argv.index("--back-seeds") + 1] if "--back-seeds" in sys.argv else "1,2,3,4"
ss = sys.argv[sys.argv.index("--side-seeds") + 1] if "--side-seeds" in sys.argv else "5,6,7,8"
front = os.path.join(ROOT, "chars", name, "front_approved.png")
for view, tpl, prompt, seeds in (("back", f"{body}_back.png", cp.BACK.format(desc=back_desc), bs),
                                 ("side", f"{body}_side.png", cp.SIDE.format(desc=side_desc), ss)):
    sd = seeds.split(",")
    dn = f"{sd[2]}:0.9,{sd[3]}:0.9" if len(sd) >= 4 else ""
    cmd = [sys.executable, "-I", os.path.join(ROOT, "char_edit.py"), name, view, os.path.join(ROOT, "chars", "templates", tpl), prompt,
           "--ref", front, "--seeds", seeds] + (["--denoise", dn] if dn else [])
    out = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace").stdout
    print(view)
    print("\n".join(l for l in out.splitlines() if l.startswith('{"seed"') or l.startswith("seconds")), flush=True)
