"""Ashcombe Manor, 1932, night: the lighting look (all tunable numbers live here).

Units: candelas for local lights, lux for the moon, cd/m2 for emissive-ish values, EV100 for exposure.
The camera is white-balanced for ~4300 K, so 2700 K practicals read amber, 1850 K fires orange and the
8000 K moon blue. See rig.py for how each entry is used.
"""

# ------------------------------------------------------------------ camera / grade (unbound PostProcessVolume)
EXPOSURE = dict(
    method="histogram",        # min == max would be a fixed exposure; a 0.6 EV window lets dark rooms open up a little
    min_ev=2.6, max_ev=3.1, bias=0.0,
    speed_up=1.2, speed_down=0.9, low_percent=60.0, high_percent=95.0,
)
GRADE = dict(
    white_temp=3900.0, white_tint=0.0,
    saturation=0.88, contrast=1.05,
    saturation_highlights=0.84,
    gain_shadows=(0.97, 0.99, 1.06),       # slightly cool shadows
    offset_shadows=(0.0, 0.0005, 0.0018),
    gain_highlights=(1.03, 1.0, 0.96),     # warm highlights
    gamma=(1.0, 1.0, 1.0),
    film_slope=0.88, film_toe=0.55, film_shoulder=0.26, film_black_clip=0.0, film_white_clip=0.04,
    bloom=0.4, bloom_threshold=-1.0,
    vignette=0.32,
    local_exposure_highlights=0.72, local_exposure_shadows=0.9,
    grain=0.0, fringe=0.0, sharpen=0.0,
)
# per-room bounded post volumes (blended over ROOM_BLEND_RADIUS cm at the doors): ev = exposure compensation
ROOM_GRADE = {
    "library": dict(ev=0.8), "dining": dict(ev=0.5, saturation=0.84), "billiard": dict(ev=0.5, saturation=0.88),
    "study": dict(ev=0.6, saturation=0.86), "ballroom": dict(ev=-0.45), "hall": dict(ev=-0.35), "gallery": dict(ev=0.0),
    "conservatory": dict(ev=-0.5), "corridor_w": dict(ev=-0.15), "corridor_e": dict(ev=-0.7), "cloakroom": dict(ev=-0.8),
}
ROOM_BLEND_RADIUS = 160.0
LUMEN = dict(
    final_gather_quality=2.0, scene_lighting_quality=1.0, scene_detail=1.5, reflection_quality=1.5,
    max_trace_distance=6000.0, final_gather_update_speed=1.5, scene_lighting_update_speed=1.5,
    max_reflection_bounces=1, skylight_leaking=0.0, diffuse_color_boost=1.0,
)

# ------------------------------------------------------------------ moon, sky, fog
MOON = dict(
    # direction the moon is IN, measured in the XY plane from +X (east) towards +Y (north): -82 = south (a touch east),
    # so it shines straight into the south windows (hall high window, dining, billiard) and the conservatory roof
    azimuth=-82.0,
    # 40 lux lit the new island exterior (L_Manor_Island, seen through the real window glass) like daylight and the
    # moonlit volumetric fog outside hid it in a bright haze: 12 lux, volumetric 36 (indoor shafts ~45 % of before,
    # outdoor haze dark enough for the storm and the lightning to read) - level agent, 2026-11-03
    elevation=34.0, lux=12.0, temp=8200.0, source_angle=0.55, volumetric=36.0, specular=0.6,
)
SKY = dict(intensity=1.0, tint=(0.62, 0.74, 1.0), volumetric=0.0)
FOG = dict(
    density=0.02, falloff=0.2, height=-100.0, start=1500.0, max_opacity=0.92,
    sky_luminance=(0.02, 0.03, 0.065),          # storm night beyond the volumetric range (was navy 0.10/0.16/0.38)
    volumetric=True, vol_extinction_scale=1.8, vol_distribution=0.55, vol_albedo=(0.92, 0.94, 1.0),
    vol_distance=2200.0, vol_start=0.0, vol_emissive=(0.0, 0.0, 0.0),
)
# local fog volumes (label, centre, actor scale, radial extinction, height extinction). Tried for denser air in the
# hall/dining/billiard, but LocalFogVolumes showed no visible effect in this project's volumetric fog (even at
# extinction 20), so none are placed; the shafts come from the global volumetric fog + the moon's scattering.
HAZE = []

# ------------------------------------------------------------------ chandeliers (per room)
# pool = shadowed down-facing spot under the chandelier (floor lux on axis), glow = unshadowed point at the candle
# ring (lux reaching the ceiling right above). temp in K. small = the hall's two little under-gallery chandeliers.
# one point light per chandelier at the candle ring, cd = peak (sideways) intensity, shaped by an IES curve
CHANDELIER = {
    "hall":       dict(cd=1250, radius=2600, temp=2750, shadows=True, vol=0.6, ies="IES_GW_ChandelierTall"),
    "hall_small": dict(cd=320, radius=900, temp=2700, shadows=False, vol=0.3),
    "ballroom":   dict(cd=700, radius=2000, temp=2800, shadows=True, vol=0.5),
    "dining":     dict(cd=750, radius=1600, temp=2900, shadows=True, vol=0.4),
    "library":    dict(cd=720, radius=1800, temp=2650, shadows=True, vol=0.3),
    "billiard":   dict(cd=130, radius=1300, temp=2600, shadows=False, vol=0.3),
    "study":      dict(cd=170, radius=1300, temp=2650, shadows=True, vol=0.3),
    "corridor_w": dict(cd=210, radius=1000, temp=2700, shadows=False, vol=0.3),
    "corridor_e": dict(cd=110, radius=1000, temp=2700, shadows=False, vol=0.3),
    "cloakroom":  dict(cd=50, radius=700, temp=2500, shadows=True, vol=0.2),
}
# which ballroom/dining chandelier gets the shadow when a room has two (cost): "all" or "first"
CHANDELIER_SHADOW_POLICY = {"ballroom": "all", "dining": "first", "corridor_w": "first"}

SCONCE = {"default": dict(cd=60, radius=480, temp=2600),     # cd = peak (upwards, tulip uplighter)
          "corridor_w": dict(cd=44, radius=450, temp=2600), "corridor_e": dict(cd=26, radius=450, temp=2600),
          "hall": dict(cd=50, radius=600, temp=2650), "ballroom": dict(cd=45, radius=550, temp=2650),
          "dining": dict(cd=60, radius=480, temp=2550), "billiard": dict(cd=45, radius=460, temp=2550),
          "study": dict(cd=55, radius=450, temp=2550), "cloakroom": dict(cd=18, radius=350, temp=2450)}
SCONCE_ALL_LIT = True

FIRE = {"library": dict(cd=950, shadows=True), "dining": dict(cd=480, shadows=True),
        "billiard": dict(cd=560, shadows=True), "study": dict(cd=650, shadows=True)}
# spot out of the firebox: low, wide fan (little reaches the ceiling) + small glow on the surround
FIRE_COMMON = dict(temp=1850, radius=1400, source_radius=20, height=38, forward=30, pitch=-14, cone=(32, 62),
                   vol=0.4, indirect=1.2, glow=dict(cd=30, radius=420, forward=12, height=30))

PICTURE = dict(cd=26, radius=320, cone=(28, 58), temp=2850, source_radius=2.0)

LANTERN = dict(cd=70, radius=650, temp=2300, vol=0.6)              # conservatory hanging lanterns
GARDEN_LAMP = dict(cd=90, radius=1500, temp=2200, vol=1.0)

BILLIARD_LAMP = dict(cd=1200, radius=520, cone=(26, 52), temp=3000, shadows="centre", vol=1.6, source_radius=6)

# dress lamps (spawned by dress.py, retuned here): by kind (table/floor/bar from their height above the floor)
LAMP = {"table": dict(cd=55, radius=450, temp=2500), "floor": dict(cd=80, radius=520, temp=2500),
        "bar": dict(cd=45, radius=420, temp=2400)}          # cd = peak (straight down), IES_GW_Shade
LAMP_ROOM_SCALE = {"library": 1.6, "study": 1.4, "corridor_w": 0.9, "corridor_e": 0.8, "hall": 1.1, "dining": 1.0,
                   "billiard": 1.2}
KEY_LAMPS = [(1180, 3970, dict(shadows=True, cd=75)),        # library partners-desk lamp
             (5480, 2700, dict(shadows=True, cd=120))]        # study desk lamp: the study's key
STAGE_SPOT = dict(cd=3800, radius=2200, cone=(10, 22), temp=3300, shadows=True, vol=1.2)

# extra motivated lights that the dressing implies (x, y, z): candelabras, bar back-light, footlights
CANDLES = [  # (label, (x, y, z), cd, radius, shadows)
    ("L_Candle_DiningTable", (850, 900, 132), 50, 560, True),
    ("L_Candle_DiningTable", (1250, 900, 132), 50, 560, False),
    ("L_Candle_Sideboard", (430, 1745, 148), 14, 300, False),
    ("L_Candle_Sideboard", (1470, 1745, 148), 14, 300, False),
    ("L_Candle_Champagne", (2400, 2750, 113), 12, 280, False),
    ("L_Candle_Champagne", (3600, 2750, 113), 12, 280, False),
    ("L_Candle_Champagne", (2400, 3600, 113), 12, 280, False),
    ("L_Candle_Champagne", (3600, 3600, 113), 12, 280, False),
]
CANDLE_TEMP = 1900
BAR_BACKLIGHT = dict(dy=24, z=218, w=500, h=8, cd=70, radius=380, temp=2350, pitch=-70)   # from the bar lamp
FOOTLIGHTS = dict(loc=(3000, 3895, 66), w=980, h=6, cd=160, radius=900, temp=2500, pitch=28)

# windows: rect lights in the reveals (cool sky fill), cd/m2 of window; moonlit side brighter
WINDOW = dict(lum_moon_side=10.0, lum_dark_side=5.0, temp=9000, radius=900, vol=0.0, specular=0.8)

# fixture emissive (material instances owned by the level agent; strengths are lighting's call)
EMISSIVE = {
    "MI_GW_Bulb": dict(Strength=14.0, Color=(1.0, 0.80, 0.56)),
    "MI_GW_LampGlow": dict(Strength=5.0, Color=(1.0, 0.74, 0.46)),
    "MI_GW_LanternGlow": dict(Strength=7.0, Color=(1.0, 0.76, 0.48)),
    "MI_GW_Fire": dict(Strength=10.0),
    "MI_GW_EmberGlow": dict(Strength=3.0),
    "MI_GW_Moon": dict(Strength=60.0, Color=(0.82, 0.88, 1.0)),
    "MI_GW_Window_Night": dict(Emissive=2.2),
    "MI_GW_Garden_Backdrop": dict(Emissive=0.35),
    # not a fixture, but it is the light's main reflector: the bright ivory plaster (tint 1.05) over dark walnut
    # reflected ~15x more than the walls and read as glowing coffers. Aged ivory, ~45% albedo.
    "MI_GW_Plaster_Ceiling": dict(Tint=(0.46, 0.43, 0.39)),
}

# night-sky dome (the level agent's M_GW_NightSky on the conservatory dome): lighting's instance with the moon where
# the moonlight comes from; rig.build_env assigns it to the dome
NIGHT_SKY = dict(Zenith=(0.035, 0.06, 0.16), Horizon=(0.10, 0.13, 0.22), StarBright=3.0, MoonBright=2.5)

# per-room Lumen bounce scaling of the lights in that room (the red dining room drowns in its own bounce)
ROOM_INDIRECT = {"dining": 0.85, "billiard": 1.2, "library": 1.6, "study": 1.3}

# brass picture lights over the built-in bookcases (rect light per bookcase run, cd per metre of bookcase)
BOOKCASE = dict(rooms=("library", "study"), spacing=150.0, out=34.0, dz=24.0, pitch=-62.0, cd_per_m=26.0,
                radius=520.0, temp=2700)

# IES curves (angle from straight down, relative intensity); point lights using them are pitched -90 so the
# profile's nadir points at the floor
IES = {
    # candle chandelier with crystals: most light sideways (walls, faces), less straight down, little up
    "IES_GW_Chandelier": [(0, 0.62), (25, 0.68), (50, 0.85), (70, 1.0), (95, 1.0), (115, 0.7), (135, 0.3),
                          (155, 0.12), (180, 0.07)],
    # big hall chandelier hung 7 m up: keep more of it for the floor
    "IES_GW_ChandelierTall": [(0, 1.0), (30, 0.95), (55, 0.9), (80, 0.8), (100, 0.62), (125, 0.3), (150, 0.12),
                              (180, 0.07)],
    # fabric-shaded table/floor lamp: bright pool below, glow through the shade, a little out of the top
    "IES_GW_Shade": [(0, 1.0), (30, 0.98), (42, 0.75), (55, 0.32), (75, 0.2), (110, 0.18), (140, 0.24),
                     (160, 0.38), (180, 0.4)],
    # tulip wall sconce opening upwards
    "IES_GW_Sconce": [(0, 0.3), (60, 0.35), (90, 0.5), (115, 0.8), (140, 1.0), (180, 1.0)],
}
