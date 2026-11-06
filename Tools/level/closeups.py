"""Close-up verification shots of L_Manor from custom viewpoints (shared rendering editor).

  python -I -X utf8 Tools/level/closeups.py --tag lv_close [--only name,name]
Take `LOCK viewport level <time>` in Tools/agent_logs/locks.md first, UNLOCK afterwards.
"""
import argparse
import glob
import math
import os
import shutil
import sys
import time

QA = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "qa")
sys.path.insert(0, QA)
from shoot_cams import Editor, MOVE, SHOOT, SETUP, SHOT_DIR, OUT_ROOT  # noqa: E402

# name: (eye xyz, look-at xyz)
VIEWS = {
    "cl_cloak_frontdoor": ((3000, 330, 170), (3000, 15, 190)),
    "cl_ballroom_wdoor": ((2500, 3400, 180), (2015, 3400, 260)),
    "cl_dining_window": ((420, 450, 160), (15, 350, 150)),
    "cl_stair_west_wall": ((2700, 1250, 260), (2017, 1550, 260)),
    "cl_stair_spandrel": ((2750, 1200, 140), (2290, 1600, 160)),
    "cl_billiard_lamp": ((5350, 450, 170), (5000, 900, 120)),
    "cl_conservatory_glass": ((4300, 3400, 160), (5900, 4400, 450)),
    "cl_corridor_door": ((1400, 2050, 170), (1000, 1785, 230)),
    "np_stage": ((3200, 3650, 230), (3300, 4200, 120)),
    "np_stage_w": ((2750, 3850, 190), (2440, 4190, 100)),
    "np_lib_cards": ((1450, 3700, 200), (1750, 4050, 60)),
    "np_lib_projector": ((750, 3850, 180), (380, 4120, 90)),
    "np_hall_statue": ((3000, 1250, 170), (3000, 850, 90)),
    "np_conservatory": ((4750, 3750, 180), (5000, 4150, 70)),
    "np_billiard_cards": ((5180, 580, 170), (5450, 300, 60)),
    "np_corridor": ((1000, 2100, 170), (850, 2355, 50)),
    "np_dining": ((420, 1300, 170), (142, 900, 40)),
    "np_study": ((5000, 2780, 170), (5250, 2419, 60)),
    "np_ball_chaise": ((3480, 2820, 170), (3755, 2450, 40)),
}


def rot(eye, at):
    dx, dy, dz = at[0] - eye[0], at[1] - eye[1], at[2] - eye[2]
    return math.degrees(math.atan2(dz, math.hypot(dx, dy))), math.degrees(math.atan2(dy, dx))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--tag", default="lv_close")
    ap.add_argument("--only", default="")
    ap.add_argument("--res", default="1280x720")
    ap.add_argument("--wait", type=float, default=6.0)
    a = ap.parse_args()
    out = os.path.join(OUT_ROOT, a.tag)
    os.makedirs(out, exist_ok=True)
    ed = Editor(6766)
    try:
        ed.run(SETUP)
        only = {s for s in a.only.split(",") if s}
        for name, (eye, at) in VIEWS.items():
            if only and name not in only:
                continue
            p, yw = rot(eye, at)
            ed.run(MOVE.format(x=eye[0], y=eye[1], z=eye[2], p=p, yw=yw, r=0))
            time.sleep(a.wait)
            tag = "GWLV_" + name
            for old in glob.glob(os.path.join(SHOT_DIR, tag + "*.png")):
                os.remove(old)
            ed.run(SHOOT.format(res=a.res, name=tag))
            deadline, found = time.time() + 90, None
            while time.time() < deadline and not found:
                time.sleep(0.5)
                hits = glob.glob(os.path.join(SHOT_DIR, tag + "*.png"))
                if hits and os.path.getsize(hits[0]) > 0:
                    time.sleep(0.5)
                    found = hits[0]
            if found:
                shutil.move(found, os.path.join(out, name + ".png"))
                print("ok", name)
            else:
                print("MISSING", name)
    finally:
        ed.close()


if __name__ == "__main__":
    main()
