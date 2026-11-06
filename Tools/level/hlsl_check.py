"""Compile the Custom-node HLSL of ue_materials.py with the engine's dxcompiler.dll (headless editor can't).

python -I -X utf8 Tools/level/hlsl_check.py   -> prints OK / errors per snippet
"""
import ctypes, re, sys, os
from ctypes import wintypes

DLL = r"J:\Projets\Unreal_Projects\Guess Who\UE_5.8\Engine\Binaries\ThirdParty\ShaderConductor\Win64\dxcompiler.dll"
SRC = sys.argv[1] if len(sys.argv) > 1 else os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                                                          "ue_materials.py")


class GUID(ctypes.Structure):
    _fields_ = [("d1", ctypes.c_uint32), ("d2", ctypes.c_uint16), ("d3", ctypes.c_uint16), ("d4", ctypes.c_ubyte * 8)]

    def __init__(self, s):
        s = s.replace("-", "")
        super().__init__(int(s[0:8], 16), int(s[8:12], 16), int(s[12:16], 16),
                         (ctypes.c_ubyte * 8)(*bytes.fromhex(s[16:32])))


class DxcBuffer(ctypes.Structure):
    _fields_ = [("Ptr", ctypes.c_void_p), ("Size", ctypes.c_size_t), ("Encoding", ctypes.c_uint)]


def vcall(obj, index, restype, *argtypes):
    vtbl = ctypes.cast(ctypes.cast(obj, ctypes.POINTER(ctypes.c_void_p))[0], ctypes.POINTER(ctypes.c_void_p))
    return ctypes.WINFUNCTYPE(restype, ctypes.c_void_p, *argtypes)(vtbl[index])


dxc = ctypes.WinDLL(DLL)
CLSID = GUID("73e22d93-e6ce-47f3-b5bf-f0664f39c1b0")
IID_C3 = GUID("228B4687-5A6A-4730-900C-9702B2203F54")
IID_OR = GUID("CEDB484A-D4E9-445A-B991-CA21CA157DC2")
comp = ctypes.c_void_p()
hr = dxc.DxcCreateInstance(ctypes.byref(CLSID), ctypes.byref(IID_C3), ctypes.byref(comp))
assert hr == 0, hex(hr)


def compile_ps(src):
    b = src.encode("utf-8")
    buf = DxcBuffer(ctypes.cast(ctypes.c_char_p(b), ctypes.c_void_p), len(b), 65001)
    args = ["-T", "ps_6_0", "-E", "main", "-Vd", "-HV", "2018"]
    arr = (ctypes.c_wchar_p * len(args))(*args)
    res = ctypes.c_void_p()
    f = vcall(comp, 3, ctypes.c_long, ctypes.POINTER(DxcBuffer), ctypes.POINTER(ctypes.c_wchar_p), ctypes.c_uint32,
              ctypes.c_void_p, ctypes.POINTER(GUID), ctypes.POINTER(ctypes.c_void_p))
    hr = f(comp, ctypes.byref(buf), arr, len(args), None, ctypes.byref(IID_OR), ctypes.byref(res))
    assert hr == 0, hex(hr)
    status = ctypes.c_long()
    vcall(res, 3, ctypes.c_long, ctypes.POINTER(ctypes.c_long))(res, ctypes.byref(status))
    err = ctypes.c_void_p()
    vcall(res, 5, ctypes.c_long, ctypes.POINTER(ctypes.c_void_p))(res, ctypes.byref(err))
    msg = ""
    if err:
        ptr = vcall(err, 3, ctypes.c_void_p)(err)
        size = vcall(err, 4, ctypes.c_size_t)(err)
        if ptr and size:
            msg = ctypes.string_at(ptr, size).decode("utf-8", "replace")
    return status.value, msg


def main():
    text = open(SRC, encoding="utf-8").read()
    snippets = dict(re.findall(r'^([A-Z_]+) = """(.*?)"""', text, re.S | re.M))
    # input name -> hlsl type, as UE passes them
    tex_names = {"Tex", "RTex", "NTex", "TexA", "TexB", "Noise", "FTex", "RockC", "RockN", "Grass", "Rain", "Drops",
                 "Mask", "Clouds"}
    f3_names = {"P", "O", "N", "Tint", "TintA", "TintB", "Color", "C", "Zenith", "Horizon", "MoonDir", "Water",
                "FoamColor", "RockTint", "GrassTint", "GravelTint", "CloudColor", "FlashColor", "V"}
    f2_names = {"UV"}
    calls = re.findall(r'custom\(m, ([A-Z_]+), \[([^\]]*)\],\s*[^F]*?(F\d)', text, re.S)
    ok = True
    for name, inputs, out in calls:
        ins = [s.strip().strip('"') for s in inputs.split(",")]
        params, cargs = [], []
        for n in ins:
            if n in tex_names:
                params += [f"Texture2D {n}", f"SamplerState {n}Sampler"]; cargs += [n, n + "Sampler"]
            elif n in f3_names:
                params.append(f"float3 {n}"); cargs.append("float3(1,2,3)")
            elif n in f2_names:
                params.append(f"float2 {n}"); cargs.append("float2(1,2)")
            else:
                params.append(f"float {n}"); cargs.append("1.0")
        rt = {"F1": "float", "F3": "float3", "F4": "float4"}[out]
        globs = "".join(f"Texture2D {n}; SamplerState {n}Sampler;\n" for n in ins if n in tex_names)
        src = ("#define Texture2DSample(T,S,UV) T.Sample(S,UV)\n" + globs +
               f"{rt} CustomExpression({', '.join(params)}) {{\n{snippets[name]}\n}}\n"
               f"float4 main() : SV_Target {{ return (float4)CustomExpression({', '.join(cargs)}).xxxx; }}\n")
        status, msg = compile_ps(src)
        good = status == 0
        ok &= good
        print(f"{name:18s} {'OK' if good else 'FAIL'}")
        if msg.strip() and not good:
            print(msg[:1500])
    return 0 if ok else 1


sys.exit(main())
