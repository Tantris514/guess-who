"""Extract the textures embedded in a GLB:  glb_tex.py FILE.glb OUT_PREFIX  -> OUT_PREFIX_<i>.png"""
import json
import struct
import sys

data = open(sys.argv[1], "rb").read()
clen = struct.unpack_from("<I", data, 12)[0]
gltf = json.loads(data[20:20 + clen])
base = 28 + clen
for i, img in enumerate(gltf.get("images", [])):
    bv = gltf["bufferViews"][img["bufferView"]]
    blob = data[base + bv.get("byteOffset", 0): base + bv.get("byteOffset", 0) + bv["byteLength"]]
    open(f"{sys.argv[2]}_{i}.png", "wb").write(blob)
    print(f"{sys.argv[2]}_{i}.png", len(blob))
