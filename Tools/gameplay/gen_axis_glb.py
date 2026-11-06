"""Tiny glb with vertices at +X=1m, +Y=2m, +Z=3m to learn the glTF -> Unreal (Interchange) axis mapping."""
import json, struct, sys
pos = [(0, 0, 0), (1, 0, 0), (0, 2, 0), (0, 0, 3)]
idx = [0, 1, 2, 0, 1, 3, 0, 2, 3, 1, 2, 3]
pb = b''.join(struct.pack('<3f', *p) for p in pos)
ib = b''.join(struct.pack('<H', i) for i in idx)
ib += b'\0' * ((4 - len(ib) % 4) % 4)
binb = pb + ib
gltf = {"asset": {"version": "2.0"}, "scene": 0, "scenes": [{"nodes": [0]}], "nodes": [{"mesh": 0, "name": "axis"}],
        "meshes": [{"primitives": [{"attributes": {"POSITION": 0}, "indices": 1}]}],
        "buffers": [{"byteLength": len(binb)}],
        "bufferViews": [{"buffer": 0, "byteOffset": 0, "byteLength": len(pb)}, {"buffer": 0, "byteOffset": len(pb), "byteLength": len(idx) * 2}],
        "accessors": [{"bufferView": 0, "componentType": 5126, "count": 4, "type": "VEC3", "min": [0, 0, 0], "max": [1, 2, 3]},
                      {"bufferView": 1, "componentType": 5123, "count": len(idx), "type": "SCALAR"}]}
js = json.dumps(gltf).encode()
js += b' ' * ((4 - len(js) % 4) % 4)
out = struct.pack('<III', 0x46546C67, 2, 12 + 8 + len(js) + 8 + len(binb)) + struct.pack('<II', len(js), 0x4E4F534A) + js + struct.pack('<II', len(binb), 0x004E4942) + binb
open(sys.argv[1], 'wb').write(out)
print('ok', len(out))
