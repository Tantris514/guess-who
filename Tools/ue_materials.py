"""Create the GuessWho master materials (run inside the editor with ue_py.py).

M_GW_Triplanar    world-aligned tiling surface (wood, plaster, wallpaper, fabric, carpet, marble)
                  BaseTex/RoughTex/NormalTex sampled triplanar, world-space normal output
M_GW_Parquet      procedural parquet (Pattern 0 = basket weave, 1 = herringbone) sampling a wood texture
M_GW_Checker      two-marble checkerboard floor (Diagonal 1 = 45 degrees, 0 = straight)
M_GW_Image        a single image on UV0 (paintings, rugs, windows), optional emissive
M_GW_Metal        brass / gold / silver / iron
M_GW_Emissive     glowing lamp shades and bulbs
M_GW_Fire         flickering emissive embers / flames (firebox)
M_GW_Flame        additive flame cards for the "Au feu !" event (BP_GW_Fire, s32_events.py)
M_GW_Beam         additive see-through cone, brighter at its silhouette (the robot's red sight cone)
M_GW_Smoke        translucent billowing smoke on spheres (fire smoke; Color / Density)
M_GW_Glass        thin translucent glass (conservatory) - use on non-Nanite meshes only
M_GW_LightFlicker light function (fireplace point lights)

Fixed vs. the first draft: CustomInput has no kwargs constructor; custom nodes return float4 (colour +
mask channel) split by component masks; sampler types match the default textures; usage flags set.
Re-runnable: existing masters are cleared and rebuilt in place (instances keep working).
"""
import unreal

mel = unreal.MaterialEditingLibrary
eal = unreal.EditorAssetLibrary
tools = unreal.AssetToolsHelpers.get_asset_tools()
FOLDER = "/Game/GW/Materials/Master"
DEFAULT_TEX = "/Engine/EngineMaterials/DefaultDiffuse"          # sRGB colour
DEFAULT_NORMAL = "/Engine/EngineMaterials/DefaultNormal"        # TC_Normalmap
DEFAULT_GRAY = "/Engine/EngineMaterials/Good64x64TilingNoiseHighFreq"  # TC_Grayscale linear
DEFAULT_LINEAR = "/Game/GW/Textures/Defaults/T_GW_Default_Linear"     # TC_Default, sRGB off (LinearColor sampler)
LINEAR_SRC = "J:/Projets/Unreal_Projects/Guess Who/Tools/level/tex/T_GW_Default_Rough.png"
ST = unreal.MaterialSamplerType


def ensure_linear_default():
    """Tiny mid-grey linear texture: default for SAMPLERTYPE_LINEAR_COLOR parameters (must match the sampler)."""
    if not eal.does_asset_exist(DEFAULT_LINEAR):
        t = unreal.AssetImportTask()
        t.filename = LINEAR_SRC
        t.destination_path = DEFAULT_LINEAR.rsplit("/", 1)[0]
        t.destination_name = DEFAULT_LINEAR.rsplit("/", 1)[1]
        t.automated = True
        t.replace_existing = True
        t.save = False
        tools.import_asset_tasks([t])
    tex = unreal.load_asset(DEFAULT_LINEAR)
    tex.set_editor_property("srgb", False)
    tex.set_editor_property("compression_settings", unreal.TextureCompressionSettings.TC_DEFAULT)
    eal.save_loaded_asset(tex)
    return tex
F1 = unreal.CustomMaterialOutputType.CMOT_FLOAT1
F3 = unreal.CustomMaterialOutputType.CMOT_FLOAT3
F4 = unreal.CustomMaterialOutputType.CMOT_FLOAT4
MP = unreal.MaterialProperty


def fresh_material(name):
    path = f"{FOLDER}/{name}"
    if eal.does_asset_exist(path):
        m = unreal.load_asset(path)
        mel.delete_all_material_expressions(m)
        for e in list(mel.get_material_expressions(m) or []):      # custom output nodes survive delete_all
            mel.delete_material_expression(m, e)
        return m
    return tools.create_asset(name, FOLDER, unreal.Material, unreal.MaterialFactoryNew())


def expr(mat, cls, x, y, **props):
    e = mel.create_material_expression(mat, cls, x, y)
    for k, v in props.items():
        e.set_editor_property(k, v)
    return e


def tex_param(mat, name, x, y, tex=DEFAULT_TEX, sampler=ST.SAMPLERTYPE_COLOR):
    return expr(mat, unreal.MaterialExpressionTextureObjectParameter, x, y,
                parameter_name=name, texture=unreal.load_asset(tex), sampler_type=sampler)


def scalar(mat, name, value, x, y):
    return expr(mat, unreal.MaterialExpressionScalarParameter, x, y, parameter_name=name, default_value=value)


def vector(mat, name, rgb, x, y):
    return expr(mat, unreal.MaterialExpressionVectorParameter, x, y, parameter_name=name,
                default_value=unreal.LinearColor(rgb[0], rgb[1], rgb[2], 1.0))


def custom(mat, code, inputs, x, y, out=F3, desc="Custom"):
    e = expr(mat, unreal.MaterialExpressionCustom, x, y, code=code, output_type=out, description=desc)
    ins = []
    for n in inputs:
        ci = unreal.CustomInput()
        ci.set_editor_property("input_name", n)
        ins.append(ci)
    e.set_editor_property("inputs", ins)
    return e


def wire(c, pairs):
    for src, pin in pairs:
        mel.connect_material_expressions(src, "", c, pin)


def mask(mat, src, x, y, r=False, g=False, b=False, a=False):
    e = expr(mat, unreal.MaterialExpressionComponentMask, x, y, r=r, g=g, b=b, a=a)
    mel.connect_material_expressions(src, "", e, "")
    return e


def lerp(mat, a, b, alpha, x, y):
    e = expr(mat, unreal.MaterialExpressionLinearInterpolate, x, y)
    mel.connect_material_expressions(a, "", e, "A")
    mel.connect_material_expressions(b, "", e, "B")
    mel.connect_material_expressions(alpha, "", e, "Alpha")
    return e


def usage(mat, nanite=True):
    for flag in ("used_with_instanced_static_meshes", "used_with_static_lighting"):
        try:
            mat.set_editor_property(flag, True)
        except Exception:
            pass
    if nanite:
        mat.set_editor_property("used_with_nanite", True)


def finish(mat):
    mel.layout_material_expressions(mat)
    mel.recompile_material(mat)
    eal.save_loaded_asset(mat)


TRIPLANAR = """
float3 n = abs(normalize(N));
n = pow(n, 6.0);
n /= max(n.x + n.y + n.z, 1e-4);
float3 p = P / max(Tile, 1.0);
p.z = P.z / max(TileH > 0.5 ? TileH : Tile, 1.0);
float2 ux = float2(p.y, -p.z);
float2 uy = float2(p.x, -p.z);
float2 uz = p.xy;
float3 cx = Texture2DSample(Tex, TexSampler, ux).rgb;
float3 cy = Texture2DSample(Tex, TexSampler, uy).rgb;
float3 cz = Texture2DSample(Tex, TexSampler, uz).rgb;
float rx = Texture2DSample(RTex, RTexSampler, ux).r;
float ry = Texture2DSample(RTex, RTexSampler, uy).r;
float rz = Texture2DSample(RTex, RTexSampler, uz).r;
float3 c = (cx * n.x + cy * n.y + cz * n.z) * Tint;
return float4(c, rx * n.x + ry * n.y + rz * n.z);
"""

TRIPLANAR_NORMAL = """
float3 Nw = normalize(N);
float3 w = pow(abs(Nw), 6.0);
w /= max(w.x + w.y + w.z, 1e-4);
float3 p = P / max(Tile, 1.0);
p.z = P.z / max(TileH > 0.5 ? TileH : Tile, 1.0);
float2 tx = Texture2DSample(NTex, NTexSampler, float2(p.y, -p.z)).rg * 2.0 - 1.0;
float2 ty = Texture2DSample(NTex, NTexSampler, float2(p.x, -p.z)).rg * 2.0 - 1.0;
float2 tz = Texture2DSample(NTex, NTexSampler, p.xy).rg * 2.0 - 1.0;
float3 nx = float3(0.0, tx.x, -tx.y);
float3 ny = float3(ty.x, 0.0, -ty.y);
float3 nz = float3(tz.x, tz.y, 0.0);
return normalize(Nw + (nx * w.x + ny * w.y + nz * w.z) * Strength);
"""

# returns rgb = wood colour, a = groove mask (1 in the joints)
PARQUET = """
float2 p = P.xy / max(PlankW, 1.0);
float L = max(round(Planks), 2.0);
float along = 0.0; float across = 0.0; float2 id = float2(0.0, 0.0);
if (Pattern < 0.5) {
    float2 blk = floor(p / L);
    float parity = fmod(abs(blk.x + blk.y), 2.0);
    float2 local = p - blk * L;
    float idx;
    if (parity < 0.5) { idx = floor(local.y); along = local.x / L; across = frac(local.y); }
    else              { idx = floor(local.x); along = local.y / L; across = frac(local.x); }
    id = blk * float2(13.1, 7.7) + idx * 3.3 + parity * 1.9;
} else {
    bool found = false;
    float m0 = floor(((p.x - p.y) + L) / (2.0 * L));
    for (int i = -1; i <= 1; i++) {
        float m = m0 + i;
        float2 q = p - m * float2(L, -L);
        float k = floor(q.x);
        if (!found && q.y >= k && q.y < k + L) {
            found = true; across = q.x - k; along = (q.y - k) / L; id = float2(m * 3.1, k + 0.37);
        }
        float k2 = floor(q.y);
        if (!found && q.x >= k2 + 1.0 && q.x < k2 + 1.0 + L) {
            found = true; across = q.y - k2; along = (q.x - k2 - 1.0) / L; id = float2(m * 3.1 + 1.7, k2 + 5.1);
        }
    }
}
float h  = frac(sin(dot(id, float2(12.9898, 78.233))) * 43758.5453);
float h2 = frac(h * 91.73 + 0.31);
float s = PlankW / max(TexCm, 1.0);
float2 tuv = RotTex > 0.5 ? float2(h2 + along * s * L, h + across * s) : float2(h + across * s, h2 + along * s * L);
float3 c = Texture2DSample(Tex, TexSampler, tuv).rgb * Tint;
c *= lerp(0.82, 1.10, h2);
float d = min(min(along, 1.0 - along) * L, min(across, 1.0 - across));
float groove = 1.0 - smoothstep(0.015, 0.05, d);
c *= lerp(1.0, 0.35, groove);
return float4(c, groove);
"""

# returns rgb = marble colour, a = grout mask
CHECKER = """
float2 p = P.xy / max(Tile, 1.0);
float2 r = Diagonal > 0.5 ? float2(p.x + p.y, p.y - p.x) * 0.70710678 : p;
float2 cell = floor(r);
float parity = fmod(abs(cell.x + cell.y), 2.0);
float2 uv = P.xy / (max(Tile, 1.0) * 2.7);
float3 a = Texture2DSample(TexA, TexASampler, uv).rgb * TintA;
float3 b = Texture2DSample(TexB, TexBSampler, uv * 1.13 + 0.37).rgb * TintB;
float3 col = parity < 0.5 ? a : b;
float2 f = frac(r);
float d = min(min(f.x, 1.0 - f.x), min(f.y, 1.0 - f.y));
float grout = 1.0 - smoothstep(0.0, 0.012, d);
col *= lerp(1.0, 0.5, grout);
return float4(col, grout);
"""

FIRE = """
float t = T;
float f = 0.78 + 0.12 * sin(t * 6.1 + P.x * 0.07) + 0.07 * sin(t * 11.7 + P.y * 0.05) + 0.05 * sin(t * 23.3 + P.z * 0.03);
float g = Texture2DSample(Noise, NoiseSampler, P.xy / 35.0 + float2(0.0, -t * 0.11)).r;
float g2 = Texture2DSample(Noise, NoiseSampler, P.xz / 25.0 + float2(t * 0.05, -t * 0.35)).r;
return Color * Strength * f * (0.35 + g * g2 * 1.6);
"""

# flame card: 3 vertical planes crossing at the fire's centre (BP_GW_Fire). h = height on the card (0 base, 1 top),
# r = distance from the vertical axis; a tongue that narrows upward, licked by moving sine turbulence, yellow at the
# base to deep orange at the tips. Additive, so overlapping cards only get brighter.
FLAME = """
float h = saturate((P.z - O.z) / H + 0.5);
float r = length(P.xy - O.xy) / W;
float seed = O.x * 0.013 + O.y * 0.007;
float n = 0.5 + 0.22 * sin(h * 13.0 - T * 7.3 + r * 4.0 + seed) + 0.18 * sin(h * 6.5 - T * 4.1 - r * 6.0 + seed * 2.0)
        + 0.10 * sin(h * 23.0 - T * 11.0 + seed * 3.0);
float w = pow(1.0 - h, 0.7) * (0.55 + 0.6 * n);
float shape = saturate((w - r) * 4.0) * saturate(h * 8.0 + 0.2) * saturate((1.0 - h) * 3.0);
float3 col = lerp(float3(1.0, 0.40, 0.04), float3(1.0, 0.10, 0.005), saturate(h * 1.3 + r * 0.6));
return col * (0.6 + 0.4 * shape) * Strength;
"""

FLAME_A = """
float h = saturate((P.z - O.z) / H + 0.5);
float r = length(P.xy - O.xy) / W;
float seed = O.x * 0.013 + O.y * 0.007;
float n = 0.5 + 0.22 * sin(h * 13.0 - T * 7.3 + r * 4.0 + seed) + 0.18 * sin(h * 6.5 - T * 4.1 - r * 6.0 + seed * 2.0)
        + 0.10 * sin(h * 23.0 - T * 11.0 + seed * 3.0);
float w = pow(1.0 - h, 0.7) * (0.55 + 0.6 * n);
float shape = saturate((w - r) * 4.0) * saturate(h * 8.0 + 0.2) * saturate((1.0 - h) * 3.0);
return saturate(shape * 1.5);
"""

BEAM = """
float f = 1.0 - abs(dot(normalize(N), normalize(V)));
return Color * Strength * (0.18 + 0.82 * f * f);
"""

SMOKE = """
float f = abs(dot(normalize(N), normalize(V)));
float n = 0.55 + 0.25 * sin(P.x * 0.021 + T * 0.6) * sin(P.y * 0.019 - T * 0.45) + 0.2 * sin(P.z * 0.032 - T * 1.2);
return saturate(Density * pow(f, 1.6) * n);
"""

FLICKER = """
float t = T;
float f = 0.80 + 0.10 * sin(t * 7.3) + 0.06 * sin(t * 13.9 + 1.3) + 0.04 * sin(t * 29.1 + 0.7);
return float3(f, f, f);
"""


def build_triplanar():
    m = fresh_material("M_GW_Triplanar")
    usage(m)
    m.set_editor_property("tangent_space_normal", False)
    tex = tex_param(m, "BaseTex", -1200, 0)
    rtex = tex_param(m, "RoughTex", -1200, 150, DEFAULT_GRAY, ST.SAMPLERTYPE_GRAYSCALE)
    ntex = tex_param(m, "NormalTex", -1200, 300, DEFAULT_NORMAL, ST.SAMPLERTYPE_NORMAL)
    pos = expr(m, unreal.MaterialExpressionWorldPosition, -1200, 450)
    nrm = expr(m, unreal.MaterialExpressionVertexNormalWS, -1200, 550)
    tile = scalar(m, "TileSize", 200.0, -1200, 650)
    tint = vector(m, "Tint", (1, 1, 1), -1200, 750)
    tileh = scalar(m, "TileHeight", 0.0, -1200, 950)
    c = custom(m, TRIPLANAR, ["Tex", "RTex", "P", "N", "Tile", "TileH", "Tint"], -700, 200, F4, "Triplanar")
    wire(c, ((tex, "Tex"), (rtex, "RTex"), (pos, "P"), (nrm, "N"), (tile, "Tile"), (tileh, "TileH"), (tint, "Tint")))
    mel.connect_material_property(mask(m, c, -450, 100, r=True, g=True, b=True), "", MP.MP_BASE_COLOR)
    # roughness = lerp(RoughMin, RoughMax, rough map); with no map set RoughMin == RoughMax
    rmin = scalar(m, "RoughMin", 0.6, -700, 450)
    rmax = scalar(m, "RoughMax", 0.6, -700, 520)
    mel.connect_material_property(lerp(m, rmin, rmax, mask(m, c, -450, 300, a=True), -300, 400), "", MP.MP_ROUGHNESS)
    mel.connect_material_property(scalar(m, "Specular", 0.5, -450, 600), "", MP.MP_SPECULAR)
    mel.connect_material_property(scalar(m, "Metallic", 0.0, -450, 680), "", MP.MP_METALLIC)
    strength = scalar(m, "NormalStrength", 0.0, -1200, 850)
    nn = custom(m, TRIPLANAR_NORMAL, ["NTex", "P", "N", "Tile", "TileH", "Strength"], -700, 800, F3,
                "Triplanar normal")
    wire(nn, ((ntex, "NTex"), (pos, "P"), (nrm, "N"), (tile, "Tile"), (tileh, "TileH"), (strength, "Strength")))
    mel.connect_material_property(nn, "", MP.MP_NORMAL)
    finish(m)


def build_parquet():
    m = fresh_material("M_GW_Parquet")
    usage(m)
    tex = tex_param(m, "WoodTex", -1000, 0)
    pos = expr(m, unreal.MaterialExpressionWorldPosition, -1000, 200)
    plank = scalar(m, "PlankWidth", 9.0, -1000, 300)
    planks = scalar(m, "PlanksPerBlock", 6.0, -1000, 400)
    pattern = scalar(m, "Pattern", 1.0, -1000, 500)
    texcm = scalar(m, "TexSizeCm", 90.0, -1000, 600)
    tint = vector(m, "Tint", (1, 1, 1), -1000, 700)
    rot = scalar(m, "RotateTex", 0.0, -1000, 800)
    c = custom(m, PARQUET, ["Tex", "P", "PlankW", "Planks", "Pattern", "TexCm", "Tint", "RotTex"], -600, 200, F4,
               "Parquet")
    wire(c, ((tex, "Tex"), (pos, "P"), (plank, "PlankW"), (planks, "Planks"), (pattern, "Pattern"),
             (texcm, "TexCm"), (tint, "Tint"), (rot, "RotTex")))
    mel.connect_material_property(mask(m, c, -350, 100, r=True, g=True, b=True), "", MP.MP_BASE_COLOR)
    r0 = scalar(m, "Roughness", 0.3, -600, 450)
    r1 = scalar(m, "GrooveRoughness", 0.8, -600, 520)
    mel.connect_material_property(lerp(m, r0, r1, mask(m, c, -350, 300, a=True), -200, 400), "", MP.MP_ROUGHNESS)
    mel.connect_material_property(scalar(m, "Specular", 0.5, -350, 600), "", MP.MP_SPECULAR)
    finish(m)


def build_checker():
    m = fresh_material("M_GW_Checker")
    usage(m)
    a = tex_param(m, "MarbleA", -1000, 0)
    b = tex_param(m, "MarbleB", -1000, 150)
    pos = expr(m, unreal.MaterialExpressionWorldPosition, -1000, 300)
    tile = scalar(m, "TileSize", 60.0, -1000, 400)
    diag = scalar(m, "Diagonal", 1.0, -1000, 500)
    ta = vector(m, "TintA", (1, 1, 1), -1000, 600)
    tb = vector(m, "TintB", (1, 1, 1), -1000, 700)
    c = custom(m, CHECKER, ["TexA", "TexB", "P", "Tile", "Diagonal", "TintA", "TintB"], -600, 200, F4, "Checker")
    wire(c, ((a, "TexA"), (b, "TexB"), (pos, "P"), (tile, "Tile"), (diag, "Diagonal"), (ta, "TintA"), (tb, "TintB")))
    mel.connect_material_property(mask(m, c, -350, 100, r=True, g=True, b=True), "", MP.MP_BASE_COLOR)
    r0 = scalar(m, "Roughness", 0.15, -600, 450)
    r1 = scalar(m, "GroutRoughness", 0.7, -600, 520)
    mel.connect_material_property(lerp(m, r0, r1, mask(m, c, -350, 300, a=True), -200, 400), "", MP.MP_ROUGHNESS)
    mel.connect_material_property(scalar(m, "Specular", 0.5, -350, 600), "", MP.MP_SPECULAR)
    finish(m)


def build_image():
    m = fresh_material("M_GW_Image")
    usage(m)
    t = expr(m, unreal.MaterialExpressionTextureSampleParameter2D, -700, 0,
             parameter_name="Image", texture=unreal.load_asset(DEFAULT_TEX))
    uv = expr(m, unreal.MaterialExpressionTextureCoordinate, -1300, 0)
    tu = scalar(m, "TileU", 1.0, -1300, 100)
    tv = scalar(m, "TileV", 1.0, -1300, 200)
    app = expr(m, unreal.MaterialExpressionAppendVector, -1100, 150)
    mel.connect_material_expressions(tu, "", app, "A")
    mel.connect_material_expressions(tv, "", app, "B")
    uvm = expr(m, unreal.MaterialExpressionMultiply, -900, 0)
    mel.connect_material_expressions(uv, "", uvm, "A")
    mel.connect_material_expressions(app, "", uvm, "B")
    mel.connect_material_expressions(uvm, "", t, "UVs")
    tint = vector(m, "Tint", (1, 1, 1), -700, 300)
    mul = expr(m, unreal.MaterialExpressionMultiply, -350, 0)
    mel.connect_material_expressions(t, "RGB", mul, "A")
    mel.connect_material_expressions(tint, "", mul, "B")
    mel.connect_material_property(mul, "", MP.MP_BASE_COLOR)
    glow = scalar(m, "Emissive", 0.0, -700, 400)
    emul = expr(m, unreal.MaterialExpressionMultiply, -350, 300)
    mel.connect_material_expressions(t, "RGB", emul, "A")
    mel.connect_material_expressions(glow, "", emul, "B")
    mel.connect_material_property(emul, "", MP.MP_EMISSIVE_COLOR)
    mel.connect_material_property(scalar(m, "Roughness", 0.55, -350, 500), "", MP.MP_ROUGHNESS)
    mel.connect_material_property(scalar(m, "Specular", 0.5, -350, 600), "", MP.MP_SPECULAR)
    finish(m)


def build_metal():
    m = fresh_material("M_GW_Metal")
    usage(m)
    mel.connect_material_property(vector(m, "Color", (0.95, 0.72, 0.36), -500, 0), "", MP.MP_BASE_COLOR)
    mel.connect_material_property(scalar(m, "Metallic", 1.0, -500, 200), "", MP.MP_METALLIC)
    mel.connect_material_property(scalar(m, "Roughness", 0.28, -500, 300), "", MP.MP_ROUGHNESS)
    finish(m)


def build_emissive():
    m = fresh_material("M_GW_Emissive")
    usage(m)
    col = vector(m, "Color", (1.0, 0.78, 0.5), -700, 0)
    strength = scalar(m, "Strength", 6.0, -700, 200)
    mul = expr(m, unreal.MaterialExpressionMultiply, -350, 0)
    mel.connect_material_expressions(col, "", mul, "A")
    mel.connect_material_expressions(strength, "", mul, "B")
    mel.connect_material_property(mul, "", MP.MP_EMISSIVE_COLOR)
    mel.connect_material_property(col, "", MP.MP_BASE_COLOR)
    mel.connect_material_property(scalar(m, "Roughness", 0.5, -350, 300), "", MP.MP_ROUGHNESS)
    finish(m)


def build_fire():
    m = fresh_material("M_GW_Fire")
    usage(m)
    noise = tex_param(m, "Noise", -900, 0, DEFAULT_GRAY, ST.SAMPLERTYPE_GRAYSCALE)
    pos = expr(m, unreal.MaterialExpressionWorldPosition, -900, 150)
    t = expr(m, unreal.MaterialExpressionTime, -900, 250)
    col = vector(m, "Color", (1.0, 0.42, 0.12), -900, 350)
    strength = scalar(m, "Strength", 12.0, -900, 450)
    c = custom(m, FIRE, ["Noise", "P", "T", "Color", "Strength"], -500, 150, F3, "Fire")
    wire(c, ((noise, "Noise"), (pos, "P"), (t, "T"), (col, "Color"), (strength, "Strength")))
    mel.connect_material_property(c, "", MP.MP_EMISSIVE_COLOR)
    mel.connect_material_property(vector(m, "Base", (0.05, 0.02, 0.01), -500, 400), "", MP.MP_BASE_COLOR)
    mel.connect_material_property(scalar(m, "Roughness", 0.9, -500, 500), "", MP.MP_ROUGHNESS)
    finish(m)


def build_flame():
    m = fresh_material("M_GW_Flame")
    usage(m, nanite=False)
    m.set_editor_property("blend_mode", unreal.BlendMode.BLEND_TRANSLUCENT)
    m.set_editor_property("shading_model", unreal.MaterialShadingModel.MSM_UNLIT)
    m.set_editor_property("two_sided", True)
    pos = expr(m, unreal.MaterialExpressionWorldPosition, -900, 0)
    obj = expr(m, unreal.MaterialExpressionObjectPositionWS, -900, 100)
    t = expr(m, unreal.MaterialExpressionTime, -900, 200)
    c = custom(m, FLAME, ["P", "O", "T", "H", "W", "Strength"], -500, 100, F3, "Flame")
    wire(c, ((pos, "P"), (obj, "O"), (t, "T"), (scalar(m, "Height", 160.0, -900, 300), "H"),
             (scalar(m, "Width", 70.0, -900, 400), "W"), (scalar(m, "Strength", 1.5, -900, 500), "Strength")))
    mel.connect_material_property(c, "", MP.MP_EMISSIVE_COLOR)
    a = custom(m, FLAME_A, ["P", "O", "T", "H", "W"], -500, 400, F1, "FlameAlpha")
    wire(a, ((pos, "P"), (obj, "O"), (t, "T"), (scalar(m, "Height", 160.0, -900, 300), "H"), (scalar(m, "Width", 70.0, -900, 400), "W")))
    mel.connect_material_property(a, "", MP.MP_OPACITY)
    finish(m)


def build_beam():
    m = fresh_material("M_GW_Beam")
    usage(m, nanite=False)
    m.set_editor_property("blend_mode", unreal.BlendMode.BLEND_ADDITIVE)
    m.set_editor_property("shading_model", unreal.MaterialShadingModel.MSM_UNLIT)
    n = expr(m, unreal.MaterialExpressionVertexNormalWS, -900, 0)
    v = expr(m, unreal.MaterialExpressionCameraVectorWS, -900, 100)
    c = custom(m, BEAM, ["N", "V", "Color", "Strength"], -500, 100, F3, "Beam")
    wire(c, ((n, "N"), (v, "V"), (vector(m, "Color", (1.0, 0.05, 0.02), -900, 200), "Color"),
             (scalar(m, "Strength", 0.6, -900, 300), "Strength")))
    mel.connect_material_property(c, "", MP.MP_EMISSIVE_COLOR)
    finish(m)


def build_smoke():
    m = fresh_material("M_GW_Smoke")
    usage(m, nanite=False)
    m.set_editor_property("blend_mode", unreal.BlendMode.BLEND_TRANSLUCENT)
    m.set_editor_property("shading_model", unreal.MaterialShadingModel.MSM_UNLIT)
    n = expr(m, unreal.MaterialExpressionVertexNormalWS, -900, 0)
    v = expr(m, unreal.MaterialExpressionCameraVectorWS, -900, 100)
    pos = expr(m, unreal.MaterialExpressionWorldPosition, -900, 200)
    t = expr(m, unreal.MaterialExpressionTime, -900, 300)
    c = custom(m, SMOKE, ["N", "V", "P", "T", "Density"], -500, 150, F1, "Smoke")
    wire(c, ((n, "N"), (v, "V"), (pos, "P"), (t, "T"), (scalar(m, "Density", 0.75, -900, 400), "Density")))
    mel.connect_material_property(c, "", MP.MP_OPACITY)
    mel.connect_material_property(vector(m, "Color", (0.035, 0.03, 0.028), -500, 400), "", MP.MP_EMISSIVE_COLOR)
    finish(m)


def build_glass():
    """Thin-translucent glass: no lit diffuse (the old lit translucency picked up the warm lamps and read as
    brown), only a faint specular reflection and a cool transmittance, so the night garden/sky shows through."""
    m = fresh_material("M_GW_Glass")
    usage(m, nanite=False)
    m.set_editor_property("blend_mode", unreal.BlendMode.BLEND_TRANSLUCENT)
    m.set_editor_property("shading_model", unreal.MaterialShadingModel.MSM_THIN_TRANSLUCENT)
    # TLM_SURFACE_PER_PIXEL_LIGHTING is the one displayed as "Surface ForwardShading" (required by ThinTranslucent)
    m.set_editor_property("translucency_lighting_mode", unreal.TranslucencyLightingMode.TLM_SURFACE_PER_PIXEL_LIGHTING)
    m.set_editor_property("two_sided", True)
    # black base colour: no lit "sheet" (the moon drew the iron grid's shadows on the panes); only reflections
    mel.connect_material_property(vector(m, "Color", (0.0, 0.0, 0.0), -500, 0), "", MP.MP_BASE_COLOR)
    mel.connect_material_property(scalar(m, "Opacity", 0.15, -500, 150), "", MP.MP_OPACITY)
    mel.connect_material_property(scalar(m, "Roughness", 0.03, -500, 250), "", MP.MP_ROUGHNESS)
    mel.connect_material_property(scalar(m, "Specular", 0.5, -500, 350), "", MP.MP_SPECULAR)
    mel.connect_material_property(scalar(m, "Metallic", 0.0, -500, 420), "", MP.MP_METALLIC)
    out = expr(m, unreal.MaterialExpressionThinTranslucentMaterialOutput, -200, 500)
    ok = mel.connect_material_expressions(vector(m, "Transmittance", (0.86, 0.93, 0.93), -500, 500), "", out,
                                          "TransmittanceColor")
    if not ok:
        raise RuntimeError("could not wire ThinTranslucent TransmittanceColor")
    finish(m)


NIGHTSKY = """
float3 d = normalize(P - C);
float h = saturate(d.z);
float3 sky = lerp(Horizon, Zenith, pow(h, 0.45));
sky *= smoothstep(-0.08, 0.02, d.z);
float2 cuv = d.xy / (d.z + 0.12) * CloudScale + float2(T * CloudSpeed, T * CloudSpeed * 0.35);
float c1 = Texture2DSample(Clouds, CloudsSampler, cuv).r;
float c2 = Texture2DSample(Clouds, CloudsSampler, cuv * 2.7 + float2(0.37, T * CloudSpeed * 1.6)).r;
float cl = c1 * 0.7 + c2 * 0.4;
float dens = smoothstep(Cover - 0.25, Cover + 0.15, cl) * smoothstep(-0.05, 0.12, d.z);
float3 cell = floor(d * StarScale);
float r = frac(sin(dot(cell, float3(12.9898, 78.233, 37.719))) * 43758.5453);
float3 fp = frac(d * StarScale) - 0.5;
float star = step(0.9965, r) * saturate(1.0 - length(fp) * 4.0) * smoothstep(0.03, 0.25, d.z);
float tw = 0.7 + 0.3 * sin(T * (2.0 + r * 9.0) + r * 60.0);
float3 m = normalize(MoonDir);
float md = saturate(dot(d, m));
float glow = pow(md, 180.0) * 0.6 + pow(md, 3000.0) * 6.0;
float3 col = sky + star * tw * StarBright * (1.0 - dens) + glow * float3(0.75, 0.82, 1.0) * MoonBright * (1.0 - dens * 0.85);
float lining = pow(md, 12.0) * (1.0 - smoothstep(0.55, 1.0, dens)) * dens;
float3 cloud = CloudColor * (0.6 + 0.4 * c2) + lining * float3(0.25, 0.28, 0.35) * MoonBright;
float fl = Flash * (0.55 + 0.45 * c1) * (0.4 + 0.6 * dens);
float az = atan2(d.y, d.x);
float el = asin(saturate(d.z));
float da = az - BoltAz;
da = da - 6.2831853 * floor((da + 3.14159265) / 6.2831853);
float tb = saturate((0.5 - el) / 0.48);
float wig = sin(el * 47.0 + BoltSeed * 3.1) * 0.012 + sin(el * 113.0 + BoltSeed * 7.7) * 0.006 + sin(el * 271.0 + BoltSeed * 1.3) * 0.003;
float bx = wig + tb * sin(BoltSeed * 2.3) * 0.05;
float core = 1.0 - smoothstep(0.0012, 0.0045, abs(da - bx));
float halo = 1.0 - smoothstep(0.0, 0.03, abs(da - bx));
float bolt = (core + halo * 0.12) * step(0.015, el) * step(el, 0.5) * smoothstep(0.35, 0.8, Flash);
return lerp(col, cloud, dens) + FlashColor * fl * (0.35 + h) + bolt * float3(0.9, 0.95, 1.0) * BoltBright;
"""


def build_nightsky():
    """Unlit sky dome material (two-sided, 'Is Sky'): navy gradient, twinkling stars, moon glow, drifting storm
    clouds (silver-lined toward the moon) lit from inside by lightning (MPC_GW_Storm.Flash, set by BP_GW_Storm)."""
    m = fresh_material("M_GW_NightSky")
    m.set_editor_property("shading_model", unreal.MaterialShadingModel.MSM_UNLIT)
    m.set_editor_property("two_sided", True)
    m.set_editor_property("is_sky", True)
    usage(m)
    pos = expr(m, unreal.MaterialExpressionWorldPosition, -900, 0)
    cen = expr(m, unreal.MaterialExpressionObjectPositionWS, -900, 100)
    t = expr(m, unreal.MaterialExpressionTime, -900, 200)
    clouds_tex = "/Game/GW/Textures/Island/T_GW_Clouds"
    clouds = tex_param(m, "Clouds", -900, 900, clouds_tex if eal.does_asset_exist(clouds_tex) else DEFAULT_GRAY,
                       ST.SAMPLERTYPE_GRAYSCALE)
    mpc = "/Game/GW/Environment/MPC_GW_Storm"
    if eal.does_asset_exist(mpc):
        flash = expr(m, unreal.MaterialExpressionCollectionParameter, -900, 1500,
                     collection=unreal.load_asset(mpc), parameter_name="Flash")
    else:
        flash = scalar(m, "Flash", 0.0, -900, 1500)
    if eal.does_asset_exist(mpc):
        b_az = expr(m, unreal.MaterialExpressionCollectionParameter, -900, 1700, collection=unreal.load_asset(mpc),
                    parameter_name="BoltAz")
        b_seed = expr(m, unreal.MaterialExpressionCollectionParameter, -900, 1800, collection=unreal.load_asset(mpc),
                      parameter_name="BoltSeed")
    else:
        b_az, b_seed = scalar(m, "BoltAz", 0.0, -900, 1700), scalar(m, "BoltSeed", 0.0, -900, 1800)
    c = custom(m, NIGHTSKY, ["P", "C", "T", "Zenith", "Horizon", "StarScale", "StarBright", "MoonDir", "MoonBright",
                             "Clouds", "CloudScale", "CloudSpeed", "Cover", "CloudColor", "Flash", "FlashColor",
                             "BoltAz", "BoltSeed", "BoltBright"],
               -450, 100, F3, "Night sky")
    wire(c, ((pos, "P"), (cen, "C"), (t, "T"), (vector(m, "Zenith", (0.002, 0.004, 0.012), -900, 300), "Zenith"),
             (vector(m, "Horizon", (0.012, 0.018, 0.035), -900, 400), "Horizon"),
             (scalar(m, "StarScale", 260.0, -900, 500), "StarScale"),
             (scalar(m, "StarBright", 1.5, -900, 600), "StarBright"),
             (vector(m, "MoonDir", (0.45, 0.66, 0.6), -900, 700), "MoonDir"),
             (scalar(m, "MoonBright", 1.0, -900, 800), "MoonBright"), (clouds, "Clouds"),
             (scalar(m, "CloudScale", 0.35, -900, 1000), "CloudScale"),
             (scalar(m, "CloudSpeed", 0.012, -900, 1100), "CloudSpeed"),
             (scalar(m, "CloudCover", 0.5, -900, 1200), "Cover"),
             (vector(m, "CloudColor", (0.005, 0.006, 0.009), -900, 1300), "CloudColor"),
             (flash, "Flash"), (vector(m, "FlashColor", (0.5, 0.55, 0.75), -900, 1600), "FlashColor"),
             (b_az, "BoltAz"), (b_seed, "BoltSeed"), (scalar(m, "BoltBright", 40.0, -900, 1900), "BoltBright")))
    mel.connect_material_property(c, "", MP.MP_EMISSIVE_COLOR)
    finish(m)


def build_light_flicker():
    m = fresh_material("M_GW_LightFlicker")
    m.set_editor_property("material_domain", unreal.MaterialDomain.MD_LIGHT_FUNCTION)
    t = expr(m, unreal.MaterialExpressionTime, -600, 0)
    c = custom(m, FLICKER, ["T"], -350, 0, F3, "Flicker")
    wire(c, ((t, "T"),))
    mel.connect_material_property(c, "", MP.MP_EMISSIVE_COLOR)
    finish(m)


def build_prop():
    """PBR for imported glTF props (replaces Interchange's M_GLTF so packaging needs no plugin content)."""
    m = fresh_material("M_GW_Prop")
    usage(m)
    bc = expr(m, unreal.MaterialExpressionTextureSampleParameter2D, -900, 0, parameter_name="BaseColor",
              texture=unreal.load_asset(DEFAULT_TEX), sampler_type=ST.SAMPLERTYPE_COLOR)
    # sampler types must match the default texture AND the textures the MIs set (dress.py forces BaseColor sRGB +
    # TC_Default, MetalRough linear + TC_Default, Normal TC_Normalmap), else the material fails to translate at cook
    mr = expr(m, unreal.MaterialExpressionTextureSampleParameter2D, -900, 300, parameter_name="MetalRough",
              texture=ensure_linear_default(), sampler_type=ST.SAMPLERTYPE_LINEAR_COLOR)
    nm = expr(m, unreal.MaterialExpressionTextureSampleParameter2D, -900, 600, parameter_name="Normal",
              texture=unreal.load_asset(DEFAULT_NORMAL), sampler_type=ST.SAMPLERTYPE_NORMAL)
    tint = vector(m, "Tint", (1, 1, 1), -900, -150)
    mul = expr(m, unreal.MaterialExpressionMultiply, -500, 0)
    mel.connect_material_expressions(bc, "RGB", mul, "A")
    mel.connect_material_expressions(tint, "", mul, "B")
    mel.connect_material_property(mul, "", MP.MP_BASE_COLOR)
    rs = scalar(m, "RoughnessScale", 1.0, -700, 350)
    rmul = expr(m, unreal.MaterialExpressionMultiply, -500, 300)
    mel.connect_material_expressions(mr, "G", rmul, "A")
    mel.connect_material_expressions(rs, "", rmul, "B")
    mel.connect_material_property(rmul, "", MP.MP_ROUGHNESS)
    ms = scalar(m, "MetallicScale", 1.0, -700, 450)
    mmul = expr(m, unreal.MaterialExpressionMultiply, -500, 450)
    mel.connect_material_expressions(mr, "B", mmul, "A")
    mel.connect_material_expressions(ms, "", mmul, "B")
    mel.connect_material_property(mmul, "", MP.MP_METALLIC)
    mel.connect_material_property(nm, "RGB", MP.MP_NORMAL)
    finish(m)


eal.make_directory(FOLDER)
for build in (build_triplanar, build_parquet, build_checker, build_image, build_metal, build_emissive,
              build_fire, build_flame, build_beam, build_smoke, build_glass, build_light_flicker, build_prop, build_nightsky):
    only = [a.lower() for a in globals().get("UE_ARGS", [])]      # e.g. ue_materials.py glass nightsky
    if only and build.__name__[6:] not in only:
        continue
    build()
    print("built", build.__name__)
