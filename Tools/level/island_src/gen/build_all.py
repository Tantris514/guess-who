"""Regenerate every island exterior source asset and island_src/README.json.

  V:\\ComfyUI\\ComfyUI\\ComfyUI\\.venv\\Scripts\\python.exe -I build_all.py

Stages can also be run alone: gen_meshes.py / gen_textures.py / gen_audio.py [names...].
(README.json is only rewritten by this script.)
"""
import os

os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")       # keeps BLAS buffers small on a RAM-starved machine
os.environ.setdefault("OMP_NUM_THREADS", "1")

import datetime  # noqa: E402
import json  # noqa: E402
import sys  # noqa: E402

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import gen_audio  # noqa: E402
import gen_meshes  # noqa: E402
import gen_textures  # noqa: E402
from common import AUDIO_DIR, MESH_DIR, ROOT, TEX_DIR  # noqa: E402

PURPOSE = {
    "SM_GW_Island": "Heightfield island in world coordinates (place at origin, no rotation/scale): plateau under the manor "
                    "(z -45 +-15, <= -40 inside the footprint + 100 cm), irregular plateau edge 1200..2600 cm from the "
                    "footprint (wider north/east = lawn beyond the conservatory), steep rugged cliffs with ledges down to "
                    "the sea at z -2000, rocky shore band -2000..-2150, sea bed falling to -2600 at the grid border.",
    "SM_GW_Boulder_A": "Shore / cliff-foot boulder, rounded. Noise-displaced icosphere with fractured facets, flat base.",
    "SM_GW_Boulder_B": "Shore boulder, long and slabby.",
    "SM_GW_Boulder_C": "Shore boulder, tall crag.",
    "SM_GW_SeaGrid": "Flat sea surface grid for vertex wave displacement in the material; place at z -2000.",
    "SM_GW_TreeBent_A": "Wind-bent coastal tree, cypress-like (tall, leaning from the base, crown pushed downwind). Trunk and "
                        "branches only; put SM_GW_Crown_* at crown_anchors_ue.",
    "SM_GW_TreeBent_B": "Wind-bent coastal tree, pine-like (crooked dogleg trunk, flat top). Trunk and branches only.",
    "SM_GW_Crown_A": "Lumpy foliage blob for branch tips (flat-ish underside, streamed toward +X).",
    "SM_GW_Crown_B": "Lumpy foliage blob, variant.",
    "SM_GW_Bush_A": "Low lumpy coastal shrub, top swept toward +X.",
    "SM_GW_Bush_B": "Low lumpy coastal shrub, variant.",
    "T_GW_SeaNormal": "Sea ripple normal map: ~60 directional choppy wave components travelling along +U (wind), group "
                      "modulation and capillary chop. Linear (sRGB off), OpenGL green-up.",
    "T_GW_SeaFoam": "Foam mask: whitecaps on the highest crests with trailing foam, long wind streaks along U, bubbly "
                    "breakup. Mostly dark. Linear.",
    "T_GW_Clouds": "Storm-cloud density (white = dense cloud, dark = thin gaps), billowy, high contrast. Linear.",
    "T_GW_RainStreaks": "Falling-rain streak sheet: thin vertical streaks of varying length and brightness on black, "
                        "brighter toward the falling head (bottom). Linear.",
    "T_GW_RainGlass": "Window-pane rain normal map: drops of all sizes plus short running rivulets (thin beaded trails "
                      "that wipe the drops, heavy head drop at the bottom of the image). Linear, OpenGL green-up; flat "
                      "areas = (128,128,255).",
    "T_GW_RainGlassMask": "Coverage mask of the same drops and rivulets (white = water). Linear.",
    "T_GW_Rock_BaseColor": "Dark wet grey-brown cliff rock: irregular strata bands, wandering block joints and fine "
                           "cracks, vertical water staining, cavity darkening. sRGB.",
    "T_GW_Rock_Normal": "Normal map matching T_GW_Rock_BaseColor (same height field). Linear, OpenGL green-up.",
    "T_GW_Grass_BaseColor": "Dark wind-flattened coastal grass: ~34k painted blades lying along +U with a swirling flow, "
                            "dull green / olive / straw patches over dark thatch. sRGB.",
    "thunder_1": "Close strike: hard broadband crack with secondary snaps, tearing crackle and low thump, then a heavy "
                 "rolling rumble that decays.",
    "thunder_2": "Mid-distance strike: softer crack, long rolling rumble with many bursts that come and go.",
    "thunder_3": "Distant thunder: no crack, slow swell, deep muffled roll.",
    "rain_loop": "Heavy rain bed: hiss + body, dense far patter, closer ticks, ~10 drips. Seamless loop.",
    "wind_loop": "Storm wind: band-passed noise with slow gusts (12-14 dB swings, brighter in gusts) and a faint howl "
                 "(two narrow resonances gliding with the gusts). Seamless loop.",
    "sea_loop": "Rough surf on rocks: steady low rumble and wash, 5 wave crashes 4..8 s apart (swell, impact, crash, "
                "backwash fizz). Seamless loop.",
}


def foreign_files():
    mine = set(PURPOSE)
    out = []
    for d in (MESH_DIR, TEX_DIR, AUDIO_DIR):
        for fn in sorted(os.listdir(d)):
            stem = os.path.splitext(fn)[0]
            if stem not in mine:
                out.append(os.path.relpath(os.path.join(d, fn), ROOT).replace("\\", "/"))
    return out


def main():
    meshes = gen_meshes.build()
    textures = gen_textures.build()
    audio = gen_audio.build()

    def entry(kind, name, info, ext, sub):
        path = os.path.join(ROOT, sub, name + ext)
        e = {"file": f"{sub}/{name}{ext}", "purpose": PURPOSE[name]}
        e.update(info)
        e["size_bytes"] = os.path.getsize(path)
        if kind == "mesh":
            e["size_cm"] = [round(b - a, 1) for a, b in zip(info["bbox_min"], info["bbox_max"])]
        return e

    files = {}
    for n, i in meshes.items():
        e = entry("mesh", n, i, ".obj", "meshes")
        e["bbox_min_ue"] = e.pop("bbox_min")
        e["bbox_max_ue"] = e.pop("bbox_max")
        files[n] = e
    for n, i in textures.items():
        e = entry("tex", n, i, ".png", "tex")
        e["srgb"] = n.endswith("BaseColor")
        e["tileable"] = True
        files[n] = e
    for n, i in audio.items():
        e = entry("audio", n, i, ".wav", "audio")
        e["loop"] = n.endswith("_loop")
        files[n] = e

    pivots = {
        "SM_GW_Island": "world origin (mesh authored in world coordinates)",
        "SM_GW_SeaGrid": "grid centre, z 0 (place at z -2000)",
        "SM_GW_Crown_A": "bounding-box centre", "SM_GW_Crown_B": "bounding-box centre",
    }
    for n in files:
        if n.startswith("SM_GW_"):
            files[n]["pivot"] = pivots.get(n, "base centre, z 0 at the bottom" if "Tree" not in n else
                                           "trunk base at ground level (z 0)")

    readme = {
        "title": "Guess Who / Le Bal Masque - island exterior source assets (offline generated)",
        "generated": datetime.datetime.now().isoformat(timespec="seconds"),
        "regenerate": r"V:\ComfyUI\ComfyUI\ComfyUI\.venv\Scripts\python.exe -I gen\build_all.py  (run from island_src; "
                      r"stages alone: gen\gen_meshes.py, gen\gen_textures.py, gen\gen_audio.py [names])",
        "generators": ["gen/common.py", "gen/gen_meshes.py", "gen/gen_textures.py", "gen/gen_audio.py", "gen/build_all.py"],
        "conventions": {
            "units_axes": "UE centimetres, Z up. +X = north (downwind), +Y = east. Wind blows from -X toward +X.",
            "obj": "Same convention as Tools/level/gen_arch_meshes.py: 'v x -y z', 'vn nx -ny nz' (UE values with y "
                   "negated); faces wound so the geometric normal in OBJ space points outward (checked per face against "
                   "the smooth normals and by signed volume for closed meshes). Indexed v/vt/vn, smooth per-vertex "
                   "normals, one object per file, no materials/usemtl.",
            "uv": "Island: world xy / 400. Sea grid: world xy / 1000 (local; equals world if placed at x=y=0). Boulders, "
                  "crowns, bushes: per-face box projection, cm / 100 (1 UV per metre). Trees: u wraps the trunk "
                  "(2 tiles trunk, 1 on branches), v = length along the limb / 100.",
            "normal_maps": "Tangent space, +Z blue, OpenGL convention (green = +Y = up in the image). UE uses DirectX: "
                           "tick 'Flip Green Channel' when importing T_GW_SeaNormal, T_GW_RainGlass, T_GW_Rock_Normal.",
            "textures": "8-bit PNG. BaseColor maps are sRGB; every other map is linear data (turn sRGB off). All tile "
                        "seamlessly (periodic noise, wrapped stamping, wrap-mode filters; seam statistics checked).",
            "audio": "WAV PCM 16-bit, 48000 Hz, mono, peak-normalised to -3.0 dBFS, no clipped samples. Loops are "
                     "synthesised circularly (FFT-filtered periodic noise, periodic envelopes, closed phase tracks, "
                     "events wrapped modulo the loop), so the tail flows into the head like any two adjacent samples.",
        },
        "world": {
            "manor_footprint": "x 0..6000, y 0..4400, floor z 0; conservatory x 4000..6000, y 3200..4400",
            "sea_surface_z": -2000,
            "island_place_at": [0, 0, 0],
            "island_bbox_ue": [files["SM_GW_Island"]["bbox_min_ue"], files["SM_GW_Island"]["bbox_max_ue"]],
            "plateau_z": "-45 +-15 (range on the plateau " + str(files["SM_GW_Island"]["plateau_z_range"]) + ")",
            "sea_grid_place_at_suggested": [3000, 2200, -2000],
        },
        "files": files,
        "notes_and_deviations": [
            "Trees: the trunk continues 40 cm below the pivot (straight down to z -40, plus the closing cap, bbox min z "
            "about -53) so the tree can sit on uneven ground without floating. The pivot is still the trunk base at "
            "ground level.",
            "Island shore band: rock noise is clamped to -2150..-1992, so a few shore rock tops sit up to 8 cm above the "
            "-2000 sea level (they break the surf); otherwise the band is -2000..-2150.",
            "Island normals: every face points up (true heightfield); 'normal_face_disagree' counts the few faces on "
            "sharp crags whose smooth vertex normals lean away from the face normal (shading only, not flipped faces).",
            "Loops are seamless by construction (circular synthesis) rather than by a tail-to-head crossfade; "
            "loop_seam_step_percentile is the percentile of the last->first sample step among all sample steps "
            "(a value well inside 0..100 = no click).",
            "Texture seam_ratio = mean jump across the wrap seams / mean neighbour step (about 1.0 = seamless); "
            "sparse features (cracks, strata) crossing an edge can push it a little above 1.",
        ],
        "foreign_files_present": {
            "note": "Files found in these folders that the generators above do NOT produce (written by another "
                    "process during this session; left untouched and not described here).",
            "files": foreign_files(),
        },
    }
    with open(os.path.join(ROOT, "README.json"), "w", encoding="utf-8", newline="\n") as fh:
        json.dump(readme, fh, indent=1, default=float)
    print("README.json written:", len(files), "assets")


if __name__ == "__main__":
    main()
