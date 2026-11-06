"""In-game rendered review (editor binary -game, -ExecutePythonScript): camera tour + screenshots, then quit.

Started by Tools/level/review_island.ps1. Each view is shot twice: storm as is, and with a forced lightning flash
(BP_GW_Storm ticking disabled, MPC_GW_Storm.Flash = 1, the Bolt light shown).
Screenshots: HighResShot -> GuessWho/Saved/Screenshots (the .ps1 copies them).
"""
import os

import unreal

WAIT0 = float(os.environ.get("GW_REVIEW_WAIT", "75"))      # shader compiles / streaming before the first shot
VIEWS = [  # name, location, look-at
    ("ext_south", (3000, -4200, 900), (3000, 1200, -200)),
    ("ext_west_cliff", (-3600, 5200, 300), (2500, 1500, -900)),
    ("ext_sea_east", (9800, -1500, 400), (4500, 2500, -1200)),
    ("hall_window_s", (3700, 900, 170), (3700, -2000, 120)),
    ("library_window_n", (1000, 3900, 170), (1000, 7000, 100)),
    ("conservatory_out", (4300, 3500, 170), (7500, 6500, 250)),
    ("billiard_window_e", (5300, 350, 170), (9000, 350, 80)),
    ("dining_window_w", (700, 1450, 170), (-3000, 1450, 120)),
    ("hall_lighthouse", (2300, 160, 180), (-1500, -17500, 500)),
    ("terrace_balustrade", (1500, -2400, 260), (2400, -600, 20)),
]
if os.environ.get("GW_REVIEW_SET") == "cams":       # the 17 interior review cameras (dress.build_cams)
    VIEWS = [
        ("Hall_FromCloak", (3000, 640, 170), (3000, 2300, 420)),
        ("Hall_FromGallery", (3300, 2300, 670), (2700, 600, 250)),
        ("Hall_Stairs", (3880, 650, 175), (2250, 1800, 320)),
        ("Ballroom_Stage", (3000, 2600, 170), (3000, 4300, 220)),
        ("Ballroom_Diag", (3880, 2520, 260), (2300, 4200, 200)),
        ("Library_Fire", (1500, 2650, 170), (100, 3500, 150)),
        ("Library_Shelves", (1900, 4300, 190), (300, 2600, 120)),
        ("Dining_Table", (1650, 380, 240), (300, 1500, 90)),
        ("Dining_Fire", (1600, 1500, 170), (40, 900, 160)),
        ("Billiard", (4150, 200, 210), (5600, 1300, 90)),
        ("Billiard_Bar", (5400, 600, 170), (4300, 1750, 140)),
        ("CorridorW", (1950, 2250, 170), (0, 2050, 170)),
        ("CorridorE", (4050, 1950, 170), (6000, 2150, 170)),
        ("Study", (4150, 3100, 170), (5900, 2600, 120)),
        ("Conservatory", (4140, 4120, 230), (5800, 3350, 200)),
        ("WC", (300, 2190, 170), (110, 1880, 80)),
        ("Cloakroom", (3000, 470, 170), (3000, 0, 150)),
    ]
if os.environ.get("GW_REVIEW_SET") == "wc":         # W.C. + stage close-ups
    VIEWS = [
        ("WC_from_door", (330, 2170, 165), (120, 1900, 70)),
        ("WC_stalls", (290, 2120, 175), (200, 1850, 60)),
        ("WC_basins", (180, 2050, 170), (220, 2385, 140)),
        ("WC_corridor_end", (900, 2100, 170), (360, 2170, 120)),
        ("Stage_band", (3000, 3600, 260), (3150, 4250, 120)),
        ("Gallery", (2300, 2250, 680), (3700, 2250, 560)),
    ]
if os.environ.get("GW_REVIEW_SET") == "props":      # the props of place_new_props.py
    VIEWS = [
        ("Stage", (3200, 3650, 230), (3300, 4200, 120)),
        ("Stage_w", (2750, 3850, 190), (2440, 4190, 100)),
        ("Lib_cards", (1450, 3700, 200), (1750, 4050, 60)),
        ("Lib_projector", (750, 3850, 180), (380, 4120, 90)),
        ("Hall_statue", (3000, 1250, 170), (3000, 850, 90)),
        ("Conservatory", (4750, 3750, 180), (5000, 4150, 70)),
        ("Billiard_cards", (5180, 580, 170), (5450, 300, 60)),
        ("Corridor", (1000, 2100, 170), (850, 2355, 50)),
        ("Dining", (420, 1300, 170), (142, 900, 40)),
        ("Study", (5000, 2780, 170), (5250, 2419, 60)),
        ("Ball_chaise", (3480, 2820, 170), (3755, 2450, 40)),
    ]
NOFLASH = os.environ.get("GW_REVIEW_SET") in ("cams", "wc", "props")
state = {"t": 0.0, "i": 0, "phase": "wait", "next": WAIT0, "cam": None, "storm": None, "bolt": None}
world = None


def look_rot(loc, tgt):
    return unreal.MathLibrary.find_look_at_rotation(unreal.Vector(*loc), unreal.Vector(*tgt))


def pc():
    return unreal.GameplayStatics.get_player_controller(world, 0)


def set_flash(on):
    if state["storm"] is None:
        acts = unreal.GameplayStatics.get_all_actors_of_class(
            world, unreal.load_class(None, "/Game/GW/Environment/BP_GW_Storm.BP_GW_Storm_C"))
        if acts:
            state["storm"] = acts[0]
            state["bolt"] = acts[0].get_component_by_class(unreal.DirectionalLightComponent)
    st = state["storm"]
    if st is None:
        return
    st.set_actor_tick_enabled(not on)
    mpc = unreal.load_asset("/Game/GW/Environment/MPC_GW_Storm")
    unreal.MaterialLibrary.set_scalar_parameter_value(world, mpc, "Flash", 1.0 if on else 0.0)
    if on and state["cam"]:                     # put the visible bolt where the camera looks
        import math
        yaw = state["cam"].get_actor_rotation().yaw
        unreal.MaterialLibrary.set_scalar_parameter_value(world, mpc, "BoltAz", math.radians(yaw) + 0.15)
        unreal.MaterialLibrary.set_scalar_parameter_value(world, mpc, "BoltSeed", 7.0)
    if state["bolt"]:
        state["bolt"].set_visibility(on, False)
        state["bolt"].set_intensity(120.0 if on else 0.0)


def shot(name):
    unreal.SystemLibrary.execute_console_command(world, f"HighResShot 1600x900 filename=island_{name}")


def tick(dt):
    global world
    state["t"] += dt
    if world is None:
        world = unreal.find_object(None, "/Game/GW/Maps/L_Manor.L_Manor")
        if world is None:
            return
    p = pc()
    if p and state["cam"]:
        p.set_view_target_with_blend(state["cam"], 0.0)
    if state["t"] < state["next"]:
        return
    i = state["i"]
    if NOFLASH and i % 2 == 1:                    # interior tour: no flash variant
        state["i"] = i + 1
        return
    if i >= len(VIEWS) * 2:
        if state["phase"] != "quit":
            state["phase"] = "quit"
            state["next"] = state["t"] + 4.0
            return
        unreal.SystemLibrary.quit_game(world, p, unreal.QuitPreference.QUIT, False)
        return
    name, loc, tgt = VIEWS[i // 2]
    flash = i % 2 == 1
    if state["phase"] in ("wait", "shot"):
        # move the camera, set the flash state, give it a moment
        if state["cam"] is None:            # borrow one of the level's review cameras (spawning is not exposed)
            cams = unreal.GameplayStatics.get_all_actors_with_tag(world, "GW_ReviewCam")
            if not cams:
                print("GW review: no GW_ReviewCam in the level")
                state["i"] = len(VIEWS) * 2
                return
            state["cam"] = cams[0]
            state["cam"].get_component_by_class(unreal.CameraComponent).set_field_of_view(80.0)
        state["cam"].set_actor_location_and_rotation(unreal.Vector(*loc), look_rot(loc, tgt), False, False)
        set_flash(flash)
        state["phase"] = "aim"
        state["next"] = state["t"] + (3.0 if not flash else 0.6)
    elif state["phase"] == "aim":
        shot(f"{i // 2:02d}_{name}{'_flash' if flash else ''}")
        state["phase"] = "shot"
        state["i"] = i + 1
        state["next"] = state["t"] + 1.5


def safe_tick(dt):
    try:
        tick(dt)
    except Exception as e:                      # report once, then end the tour (no per-tick error spam)
        if not state.get("err"):
            state["err"] = True
            print("GW review: ERROR", repr(e))
            state["i"] = len(VIEWS) * 2
            state["phase"] = "shot"


unreal.register_slate_post_tick_callback(safe_tick)
print("GW review: tour registered, first shot in", WAIT0, "s")
