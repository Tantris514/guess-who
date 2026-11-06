"""(in editor) Import textures (placeholders + approved AssetGen textures) and create/update every L_Manor MI.

  python -I -X utf8 Tools/ue_py.py "J:/Projets/Unreal_Projects/Guess Who/Tools/level/setup_materials.py"
Re-run whenever AssetGen/manifest.json gains textures, wallpapers, rugs, paintings or the window view:
generated textures replace the placeholders (tint reset to the generated look) and the whole level updates.
Writes Tools/level/materials_state.json (which MIs use generated vs placeholder textures, painting list).
"""
import json
import os
import sys

import unreal

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import importlib
import lvl_common
importlib.reload(lvl_common)
from lvl_common import load_manifest, find_asset, file_of, norm_name

eal = unreal.EditorAssetLibrary
mel = unreal.MaterialEditingLibrary
tools = unreal.AssetToolsHelpers.get_asset_tools()
TEX_PH = "/Game/GW/Textures/Placeholder"
TEX_GEN = "/Game/GW/Textures/Gen"
TEX_PAINT = "/Game/GW/Textures/Paintings"
MI_DIR = "/Game/GW/Materials"
MASTER = "/Game/GW/Materials/Master"
PH_DIR = os.path.join(HERE, "tex")
TC = unreal.TextureCompressionSettings

state = {"generated": {}, "placeholder": [], "paintings": []}


def import_texture(src, dest_dir, name, kind="color"):
    """kind: color | normal | gray. Skips re-import when the source file is unchanged."""
    path = f"{dest_dir}/{name}"
    stamp = f"{src}|{int(os.path.getmtime(src))}"
    if eal.does_asset_exist(path):
        tex = unreal.load_asset(path)
        if eal.get_metadata_tag(tex, "GW_Source") == stamp:
            return fix_pow2(tex)
    t = unreal.AssetImportTask()
    t.filename = src
    t.destination_path = dest_dir
    t.destination_name = name
    t.automated = True
    t.replace_existing = True
    t.save = False
    tools.import_asset_tasks([t])
    tex = unreal.load_asset(path)
    if tex is None:
        print("!! import failed", src)
        return None
    if kind == "normal":
        tex.set_editor_property("srgb", False)
        tex.set_editor_property("compression_settings", TC.TC_NORMALMAP)
    elif kind == "gray":
        tex.set_editor_property("srgb", False)
        tex.set_editor_property("compression_settings", TC.TC_GRAYSCALE)
    else:
        tex.set_editor_property("srgb", True)
        tex.set_editor_property("compression_settings", TC.TC_DEFAULT)
    try:
        tex.set_editor_property("max_texture_size", 2048)
    except Exception:
        pass
    eal.set_metadata_tag(tex, "GW_Source", stamp)
    eal.save_loaded_asset(tex)
    return fix_pow2(tex)


def src_size(tex):
    """Size of the source image (PNG header of the GW_Source file), independent of power-of-two stretching."""
    try:
        src = (eal.get_metadata_tag(tex, "GW_Source") or "").rsplit("|", 1)[0]
        with open(src, "rb") as fh:
            head = fh.read(24)
        if head[1:4] == b"PNG":
            return int.from_bytes(head[16:20], "big"), int.from_bytes(head[20:24], "big")
    except OSError:
        pass
    return tex.blueprint_get_size_x(), tex.blueprint_get_size_y()


def fix_pow2(tex):
    """Non power-of-two images (paintings, rugs, window) get no mips by default -> stretch to POT for mips."""
    w, h = src_size(tex)
    pot = lambda n: n > 0 and (n & (n - 1)) == 0  # noqa: E731
    if (not pot(w) or not pot(h)) and tex.get_editor_property("power_of_two_mode") !=             unreal.TexturePowerOfTwoSetting.STRETCH_TO_POWER_OF_TWO:
        tex.set_editor_property("power_of_two_mode", unreal.TexturePowerOfTwoSetting.STRETCH_TO_POWER_OF_TWO)
        tex.set_editor_property("mip_gen_settings", unreal.TextureMipGenSettings.TMGS_FROM_TEXTURE_GROUP)
        eal.save_loaded_asset(tex)
    return tex


def ph(name, kind="color"):
    return import_texture(os.path.join(PH_DIR, name + ".png"), TEX_PH, name, kind)


MANIFEST = load_manifest()


def gen_set(*names):
    """Import an approved tileable texture set -> dict(base, normal, rough) or None."""
    a = find_asset(MANIFEST, *names)
    if not a:
        return None
    key = norm_name(a["name"])
    base = file_of(a, "basecolor", "base_color", "albedo", "color", "diffuse", "image", "tile", "texture")
    if not base:
        return None
    out = {"base": import_texture(base, TEX_GEN, f"T_GW_{key}_BC", "color")}
    n = file_of(a, "normal", "normal_map")
    if n:
        out["normal"] = import_texture(n, TEX_GEN, f"T_GW_{key}_N", "normal")
    r = file_of(a, "roughness", "rough")
    if r:
        out["rough"] = import_texture(r, TEX_GEN, f"T_GW_{key}_R", "gray")
    out["name"] = a["name"]
    sz = a.get("size_cm") or []
    out["size"] = float(sz[0]) if sz and sz[0] else None
    out["size_h"] = float(sz[1]) if len(sz) > 1 and sz[1] else 0.0
    out["notes"] = a.get("notes", "")
    return out


def gen_image(*names, dest=TEX_GEN, prefix="T_GW_"):
    a = find_asset(MANIFEST, *names)
    if not a:
        return None
    img = file_of(a, "image", "basecolor", "color", "png", "texture")
    if not img:
        return None
    return import_texture(img, dest, prefix + norm_name(a["name"]), "color")


def mi(name, master):
    path = f"{MI_DIR}/{name}"
    if eal.does_asset_exist(path):
        inst = unreal.load_asset(path)
    else:
        inst = tools.create_asset(name, MI_DIR, unreal.MaterialInstanceConstant,
                                  unreal.MaterialInstanceConstantFactoryNew())
    mel.set_material_instance_parent(inst, unreal.load_asset(f"{MASTER}/{master}"))
    return inst


def params(inst, scalars=None, vectors=None, textures=None):
    for k, v in (scalars or {}).items():
        mel.set_material_instance_scalar_parameter_value(inst, k, float(v))
    for k, v in (vectors or {}).items():
        mel.set_material_instance_vector_parameter_value(inst, k, unreal.LinearColor(v[0], v[1], v[2], 1.0))
    for k, v in (textures or {}).items():
        if v is not None:
            mel.set_material_instance_texture_parameter_value(inst, k, v)
    mel.update_material_instance(inst)
    eal.save_loaded_asset(inst)


def triplanar(name, gen_names, ph_tex, ph_tint, tile, rough=(0.5, 0.5), gen_tint=(1, 1, 1), spec=0.5,
              metallic=0.0, normal_strength=0.7, ph_rough=None, gen_tile=None):
    inst = mi(name, "M_GW_Triplanar")
    g = gen_set(*gen_names) if gen_names else None
    if g:
        state["generated"][name] = g["name"]
        rr = g.get("rough")
        params(inst,
               scalars={"TileSize": gen_tile or g.get("size") or tile,
                        "TileHeight": 0.0 if gen_tile else g.get("size_h", 0.0), "RoughMin": rough[0] if rr else sum(rough) / 2,
                        "RoughMax": rough[1] if rr else sum(rough) / 2, "Specular": spec, "Metallic": metallic,
                        "NormalStrength": normal_strength if g.get("normal") else 0.0},
               vectors={"Tint": gen_tint},
               textures={"BaseTex": g["base"], "RoughTex": rr or DEFAULT_ROUGH,
                         "NormalTex": g.get("normal") or DEFAULT_NORMAL})
    else:
        state["placeholder"].append(name)
        params(inst,
               scalars={"TileSize": tile, "TileHeight": 0.0, "RoughMin": rough[0] if ph_rough else sum(rough) / 2,
                        "RoughMax": rough[1] if ph_rough else sum(rough) / 2, "Specular": spec,
                        "Metallic": metallic, "NormalStrength": 0.0},
               vectors={"Tint": ph_tint},
               textures={"BaseTex": ph_tex, "RoughTex": ph_rough or DEFAULT_ROUGH, "NormalTex": DEFAULT_NORMAL})
    return inst


DEFAULT_ROUGH = unreal.load_asset("/Engine/EngineMaterials/Good64x64TilingNoiseHighFreq")
DEFAULT_NORMAL = unreal.load_asset("/Engine/EngineMaterials/DefaultNormal")


def apply_lighting_overrides():
    """Fixture emissive strengths + ceiling tint are the lighting agent's call (Tools/lighting/look.py, pure data):
    re-apply them after a materials rebuild so they survive."""
    look_p = os.path.join(os.path.dirname(HERE), "lighting", "look.py")
    if not os.path.exists(look_p):
        return
    ns = {}
    exec(compile(open(look_p, encoding="utf-8").read(), look_p, "exec"), ns)
    n = 0
    for name, vals in ns.get("EMISSIVE", {}).items():
        inst = unreal.load_asset(f"{MI_DIR}/{name}")
        if inst is None:
            continue
        params(inst, scalars={k: v for k, v in vals.items() if not isinstance(v, tuple)},
               vectors={k: v for k, v in vals.items() if isinstance(v, tuple)})
        n += 1
    print(f"lighting overrides re-applied to {n} MIs")


def main():
    for d in (TEX_PH, TEX_GEN, TEX_PAINT, MI_DIR):
        eal.make_directory(d)
    P = {n: ph(n) for n in ("T_GW_PH_Wood", "T_GW_PH_MarbleLight", "T_GW_PH_MarbleDark", "T_GW_PH_Plaster",
                            "T_GW_PH_Fabric", "T_GW_PH_DamaskRed", "T_GW_PH_DecoGreen", "T_GW_PH_NavyGold",
                            "T_GW_PH_FloralCream", "T_GW_PH_Carpet", "T_GW_PH_Rug", "T_GW_PH_WindowNight",
                            "T_GW_PH_Painting0", "T_GW_PH_Painting1", "T_GW_PH_Painting2", "T_GW_PH_Painting3")}
    wood_r = ph("T_GW_PH_Wood_R", "gray")

    # ---- woods
    triplanar("MI_GW_Wood_Walnut", ["tex_wood_walnut", "wood_walnut"], P["T_GW_PH_Wood"], (0.50, 0.36, 0.27), 110,
              (0.32, 0.55), ph_rough=wood_r)
    triplanar("MI_GW_Wood_Mahogany", ["tex_wood_mahogany", "wood_mahogany"], P["T_GW_PH_Wood"], (0.62, 0.30, 0.20),
              110, (0.30, 0.5), ph_rough=wood_r)
    triplanar("MI_GW_Wood_Oak", ["tex_wood_oak", "wood_oak"], P["T_GW_PH_Wood"], (0.95, 0.82, 0.66), 110,
              (0.35, 0.6), ph_rough=wood_r)
    triplanar("MI_GW_Wood_Dark", ["tex_wood_walnut", "wood_walnut"], P["T_GW_PH_Wood"], (0.30, 0.21, 0.16), 110,
              (0.3, 0.5), gen_tint=(0.55, 0.5, 0.48), ph_rough=wood_r)
    # ---- plaster / paint
    triplanar("MI_GW_Plaster_Cream", ["tex_plaster_cream", "plaster_cream"], P["T_GW_PH_Plaster"], (0.80, 0.72, 0.58),
              300, (0.75, 0.9))
    # aged-ivory ceilings (~45% albedo, lighting agent's value from Tools/lighting/look.py): the bright 1.05 tint
    # over dark walnut reflected ~15x more than the walls and read as glowing coffers
    triplanar("MI_GW_Plaster_Ceiling", ["tex_plaster_cream", "plaster_cream"], P["T_GW_PH_Plaster"],
              (0.40, 0.37, 0.32), 300, (0.8, 0.9), gen_tint=(0.46, 0.43, 0.39))
    triplanar("MI_GW_Paint_Ivory", None, P["T_GW_PH_Plaster"], (0.78, 0.74, 0.64), 200, (0.4, 0.4), spec=0.5)
    triplanar("MI_GW_Lacquer_Black", None, P["T_GW_PH_Plaster"], (0.025, 0.022, 0.02), 200, (0.12, 0.12), spec=0.6)
    # ---- wallpapers (tile = size of one texture repeat in cm)
    triplanar("MI_GW_Wall_DamaskRed", ["wall_damask_red"], P["T_GW_PH_DamaskRed"], (1, 1, 1), 110, (0.6, 0.75))
    triplanar("MI_GW_Wall_DamaskGreen", ["wall_damask_green"], P["T_GW_PH_DecoGreen"], (1, 1, 1), 110, (0.55, 0.7))
    triplanar("MI_GW_Wall_NavyGold", ["wall_navy_gold"], P["T_GW_PH_NavyGold"], (1, 1, 1), 110, (0.55, 0.7))
    triplanar("MI_GW_Wall_FloralCream", ["wall_floral_cream"], P["T_GW_PH_FloralCream"], (1, 1, 1), 120, (0.65, 0.8))
    # ---- stone
    triplanar("MI_GW_Marble_White", ["tex_marble_white", "marble_white"], P["T_GW_PH_MarbleLight"], (1, 1, 1), 160,
              (0.08, 0.2), spec=0.6)
    triplanar("MI_GW_Marble_Black", ["tex_marble_black", "marble_black"], P["T_GW_PH_MarbleDark"], (1, 1, 1), 160,
              (0.08, 0.2), spec=0.6)
    triplanar("MI_GW_Marble_Green", ["tex_marble_green", "marble_green"], P["T_GW_PH_MarbleDark"], (0.30, 0.65, 0.45),
              160, (0.08, 0.2), spec=0.6)
    # ---- textiles
    triplanar("MI_GW_Velvet_Red", ["tex_velvet_red", "velvet_red"], P["T_GW_PH_Fabric"], (0.32, 0.025, 0.035), 90,
              (0.7, 0.9), spec=0.3)
    vel = gen_set("tex_velvet_red", "velvet_red")
    for name, tint in (("MI_GW_Velvet_Green", (0.03, 0.14, 0.08)), ("MI_GW_Velvet_Gold", (0.55, 0.38, 0.12)),
                       ("MI_GW_Velvet_Navy", (0.03, 0.04, 0.12))):
        inst = triplanar(name, None, P["T_GW_PH_Fabric"], tint, 90, (0.7, 0.9), spec=0.3)
        if vel:   # borrow the generated velvet's crush (normal) and sheen (roughness) maps
            params(inst, scalars={"TileSize": vel.get("size") or 50, "NormalStrength": 0.8 if vel.get("normal") else 0,
                                  "RoughMin": 0.6, "RoughMax": 0.95},
                   textures={"RoughTex": vel.get("rough") or DEFAULT_ROUGH,
                             "NormalTex": vel.get("normal") or DEFAULT_NORMAL})
    triplanar("MI_GW_Carpet_Red", ["tex_carpet_red", "carpet_red"], P["T_GW_PH_Carpet"], (1, 1, 1), 100, (0.85, 0.95),
              spec=0.25)
    triplanar("MI_GW_Felt_Green", None, P["T_GW_PH_Fabric"], (0.05, 0.22, 0.09), 60, (0.9, 0.9), spec=0.2)
    triplanar("MI_GW_Leather_Oxblood", None, P["T_GW_PH_Fabric"], (0.22, 0.04, 0.035), 60, (0.45, 0.45))
    triplanar("MI_GW_GoldLeaf", ["tex_gold_leaf", "gold_leaf"], P["T_GW_PH_Plaster"], (1.0, 0.74, 0.34), 60,
              (0.25, 0.45), metallic=1.0, gen_tint=(1, 1, 1))
    # book bindings, foliage, exterior
    for name, tint in (("MI_GW_Book_Oxblood", (0.25, 0.035, 0.03)), ("MI_GW_Book_Green", (0.04, 0.13, 0.06)),
                       ("MI_GW_Book_Navy", (0.03, 0.045, 0.13)), ("MI_GW_Book_Brown", (0.20, 0.10, 0.05)),
                       ("MI_GW_Book_Tan", (0.45, 0.30, 0.16)), ("MI_GW_Book_Black", (0.03, 0.028, 0.025))):
        triplanar(name, None, P["T_GW_PH_Fabric"], tint, 40, (0.45, 0.45), spec=0.4)
    triplanar("MI_GW_Foliage", None, P["T_GW_PH_Fabric"], (0.03, 0.09, 0.035), 30, (0.75, 0.75), spec=0.3)
    triplanar("MI_GW_Grass", None, P["T_GW_PH_Fabric"], (0.02, 0.05, 0.02), 150, (0.9, 0.9), spec=0.2)
    triplanar("MI_GW_Stone", ["tex_marble_white", "marble_white"], P["T_GW_PH_Plaster"], (0.42, 0.40, 0.37), 120,
              (0.6, 0.8), gen_tint=(0.45, 0.43, 0.40))
    triplanar("MI_GW_Bottle_Green", None, P["T_GW_PH_Plaster"], (0.02, 0.08, 0.03), 50, (0.08, 0.08), spec=0.8)
    triplanar("MI_GW_Bottle_Amber", None, P["T_GW_PH_Plaster"], (0.25, 0.10, 0.02), 50, (0.08, 0.08), spec=0.8)
    triplanar("MI_GW_Porcelain", None, P["T_GW_PH_Plaster"], (0.85, 0.85, 0.82), 50, (0.15, 0.15), spec=0.6)

    # ---- parquet
    oak = gen_set("tex_wood_oak", "wood_oak")
    walnut = gen_set("tex_wood_walnut", "wood_walnut")
    for name, g, ph_tint, pattern, plank, planks, gen_tint in (
            ("MI_GW_Parquet", oak, (0.95, 0.78, 0.58), 1, 9, 6, (1, 1, 1)),
            ("MI_GW_Parquet_Dark", walnut, (0.55, 0.38, 0.27), 1, 8, 6, (1, 1, 1)),
            ("MI_GW_Parquet_Basket", oak, (0.80, 0.60, 0.42), 0, 10, 4, (0.85, 0.8, 0.75))):
        inst = mi(name, "M_GW_Parquet")
        if g:
            state["generated"][name] = g["name"]
        else:
            state["placeholder"].append(name)
        horiz = bool(g) and "horizontal" in g.get("notes", "").lower()
        params(inst, scalars={"Pattern": pattern, "PlankWidth": plank, "PlanksPerBlock": planks,
                              "TexSizeCm": (g.get("size") or 90) if g else 90, "RotateTex": 1.0 if horiz else 0.0,
                              "Roughness": 0.28, "GrooveRoughness": 0.8},
               vectors={"Tint": gen_tint if g else ph_tint},
               textures={"WoodTex": g["base"] if g else P["T_GW_PH_Wood"]})

    # ---- checker floors
    mw = gen_set("tex_marble_white", "marble_white")
    mb = gen_set("tex_marble_black", "marble_black")
    mg = gen_set("tex_marble_green", "marble_green")
    white = mw["base"] if mw else P["T_GW_PH_MarbleLight"]
    black = mb["base"] if mb else P["T_GW_PH_MarbleDark"]
    green = mg["base"] if mg else P["T_GW_PH_MarbleDark"]
    for name, a, b, ta, tb, tile, diag in (
            ("MI_GW_Checker_Hall", white, black, (1, 1, 1), (1, 1, 1), 60, 1),
            ("MI_GW_Checker_Corridor", white, green, (1, 1, 1), (1, 1, 1) if mg else (0.3, 0.65, 0.45), 45, 0),
            ("MI_GW_Checker_Conservatory", white, white, (1, 1, 1), (0.78, 0.42, 0.28), 40, 1)):
        inst = mi(name, "M_GW_Checker")
        (state["generated"].__setitem__(name, "marble") if mw else state["placeholder"].append(name))
        params(inst, scalars={"TileSize": tile, "Diagonal": diag, "Roughness": 0.12, "GroutRoughness": 0.7},
               vectors={"TintA": ta, "TintB": tb}, textures={"MarbleA": a, "MarbleB": b})

    # ---- metals
    for name, colr, rough, metal in ((("MI_GW_Brass" if not gen_set("tex_brass", "brass") else "MI_GW_BrassPlain"),
                                      (0.92, 0.70, 0.36), 0.28, 1.0),
                                     ("MI_GW_Gold", (1.0, 0.77, 0.33), 0.22, 1.0),
                                     ("MI_GW_Silver", (0.94, 0.94, 0.96), 0.1, 1.0),
                                     ("MI_GW_Crystal", (0.97, 0.97, 1.0), 0.03, 1.0),
                                     ("MI_GW_Mirror", (0.85, 0.86, 0.88), 0.02, 1.0),
                                     ("MI_GW_Iron", (0.05, 0.05, 0.055), 0.45, 0.9),
                                     ("MI_GW_Chrome", (0.9, 0.9, 0.92), 0.08, 1.0)):
        params(mi(name, "M_GW_Metal"), scalars={"Metallic": metal, "Roughness": rough}, vectors={"Color": colr})
    # ---- emissive / fire / glass
    params(mi("MI_GW_LampGlow", "M_GW_Emissive"), scalars={"Strength": 6.0}, vectors={"Color": (1.0, 0.70, 0.40)})
    params(mi("MI_GW_Bulb", "M_GW_Emissive"), scalars={"Strength": 30.0}, vectors={"Color": (1.0, 0.78, 0.52)})
    params(mi("MI_GW_EmberGlow", "M_GW_Emissive"), scalars={"Strength": 4.0}, vectors={"Color": (1.0, 0.35, 0.08)})
    params(mi("MI_GW_Moon", "M_GW_Emissive"), scalars={"Strength": 40.0}, vectors={"Color": (0.85, 0.9, 1.0)})
    params(mi("MI_GW_LanternGlow", "M_GW_Emissive"), scalars={"Strength": 12.0}, vectors={"Color": (1.0, 0.75, 0.45)})
    params(mi("MI_GW_Fire", "M_GW_Fire"), scalars={"Strength": 14.0}, vectors={"Color": (1.0, 0.45, 0.13)})
    params(mi("MI_GW_Glass", "M_GW_Glass"), scalars={"Opacity": 0.1, "Roughness": 0.03})

    # ---- images: window view, garden backdrop, rugs
    win = gen_image("window_night", "window")
    if win:
        state["generated"]["MI_GW_Window_Night"] = "window_night"
    else:
        state["placeholder"].append("MI_GW_Window_Night")
    params(mi("MI_GW_Window_Night", "M_GW_Image"), scalars={"Emissive": 4.0, "Roughness": 0.1, "Specular": 0.8},
           textures={"Image": win or P["T_GW_PH_WindowNight"]})
    params(mi("MI_GW_Garden_Backdrop", "M_GW_Image"), scalars={"Emissive": 3.0, "Roughness": 0.9, "Specular": 0.1},
           textures={"Image": win or P["T_GW_PH_WindowNight"]})
    for name, keys in (("MI_GW_Rug_Persian", ("rug_persian",)), ("MI_GW_Rug_ArtDeco", ("rug_artdeco", "rug_art_deco"))):
        img = gen_image(*keys)
        (state["generated"].__setitem__(name, keys[0]) if img else state["placeholder"].append(name))
        tex_ = img or P["T_GW_PH_Rug"]
        sw, sh = src_size(tex_)
        state.setdefault("aspect", {})[name] = sw / max(1, sh)
        params(mi(name, "M_GW_Image"), scalars={"Roughness": 0.92, "Specular": 0.2},
               vectors={"Tint": (1, 1, 1) if img else ((1, 1, 1) if "Persian" in name else (0.5, 0.45, 0.35))},
               textures={"Image": img or P["T_GW_PH_Rug"]})

    # ---- corridor runner rug (tiled along its length by dress.py)
    img = gen_image("rug_runner", "runner")
    if img:
        state["generated"]["MI_GW_Rug_Runner"] = "rug_runner"
        sw, sh = src_size(img)
        state["runner_aspect"] = sw / max(1, sh)
        asp = state["runner_aspect"]
        L_run, W_run = 1900.0, 170.0                      # corridor runner size used by dress.py
        tu, tv = (max(1, round(L_run / (W_run * asp))), 1) if asp >= 1 else (1, max(1, round(L_run * asp / W_run)))
        params(mi("MI_GW_Rug_Runner", "M_GW_Image"), scalars={"Roughness": 0.92, "Specular": 0.2, "TileU": tu,
                                                              "TileV": tv}, textures={"Image": img})
    # ---- swap-in masters when a dedicated texture exists: chevron parquet (ballroom), brass
    chev = gen_set("tex_parquet_chevron", "parquet_chevron")
    inst = mi("MI_GW_Floor_Ballroom", "M_GW_Triplanar" if chev else "M_GW_Parquet")
    if chev:
        state["generated"]["MI_GW_Floor_Ballroom"] = chev["name"]
        # lighting agent 2026-11-02: satin, not mirror (the chandeliers blew out the near floor) and a deeper
        # honey tone (the pale oak read washed out under the warm practicals)
        params(inst, scalars={"TileSize": chev.get("size") or 120, "RoughMin": 0.40, "RoughMax": 0.62,
                              "NormalStrength": 0.6 if chev.get("normal") else 0.0, "Specular": 0.35},
               vectors={"Tint": (0.70, 0.62, 0.55)},
               textures={"BaseTex": chev["base"], "RoughTex": chev.get("rough") or DEFAULT_ROUGH,
                         "NormalTex": chev.get("normal") or DEFAULT_NORMAL})
    else:
        g = oak
        horiz = bool(g) and "horizontal" in g.get("notes", "").lower()
        params(inst, scalars={"Pattern": 1, "PlankWidth": 9, "PlanksPerBlock": 6,
                              "TexSizeCm": (g.get("size") or 90) if g else 90, "RotateTex": 1.0 if horiz else 0.0,
                              "Roughness": 0.25, "GrooveRoughness": 0.8},
               vectors={"Tint": (1, 1, 1) if g else (0.95, 0.78, 0.58)},
               textures={"WoodTex": g["base"] if g else P["T_GW_PH_Wood"]})
    brass = gen_set("tex_brass", "brass")
    if brass:
        state["generated"]["MI_GW_Brass"] = brass["name"]
        inst = mi("MI_GW_Brass", "M_GW_Triplanar")
        params(inst, scalars={"TileSize": brass.get("size") or 40, "RoughMin": 0.2, "RoughMax": 0.4, "Metallic": 1.0,
                              "NormalStrength": 0.4 if brass.get("normal") else 0.0, "Specular": 0.5},
               vectors={"Tint": (1, 1, 1)},
               textures={"BaseTex": brass["base"], "RoughTex": brass.get("rough") or DEFAULT_ROUGH,
                         "NormalTex": brass.get("normal") or DEFAULT_NORMAL})

    # ---- paintings: one MI per approved painting, plus 4 placeholder MIs
    paintings = []
    for key, a in sorted(MANIFEST.items()):
        if a.get("kind") != "painting":
            continue
        img = file_of(a, "image", "basecolor", "png")
        if not img:
            continue
        tex = import_texture(img, TEX_PAINT, "T_GW_Paint_" + key, "color")
        name = "MI_GW_Painting_" + key
        params(mi(name, "M_GW_Image"), scalars={"Roughness": 0.4, "Specular": 0.45}, textures={"Image": tex})
        size = src_size(tex)
        paintings.append({"mi": f"{MI_DIR}/{name}", "w": size[0], "h": size[1], "name": a["name"],
                          "rooms": a.get("rooms", []), "notes": a.get("notes", "")})
    for i in range(4):
        name = f"MI_GW_Painting_PH{i}"
        params(mi(name, "M_GW_Image"), scalars={"Roughness": 0.4, "Specular": 0.45},
               textures={"Image": P[f"T_GW_PH_Painting{i}"]})
    state["paintings"] = paintings
    apply_lighting_overrides()
    with open(os.path.join(HERE, "materials_state.json"), "w", encoding="utf-8") as fh:
        json.dump(state, fh, indent=1)
    print(f"MIs ok. generated: {len(state['generated'])}, placeholder: {len(state['placeholder'])}, "
          f"paintings: {len(paintings)}")


main()
