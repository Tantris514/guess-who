"""Width/depth profile of a GLB (glTF axes: Y up, Z front) by height bands, in real cm (uniform_scale_to_cm)."""
import json, struct, sys
path, scale = sys.argv[1], float(sys.argv[2])
b = open(path, 'rb').read()
jl = struct.unpack_from('<I', b, 12)[0]
js = json.loads(b[20:20 + jl])
binoff = 20 + jl + 8
pts = []
for mesh in js['meshes']:
    for prim in mesh['primitives']:
        acc = js['accessors'][prim['attributes']['POSITION']]
        bv = js['bufferViews'][acc['bufferView']]
        off = binoff + bv.get('byteOffset', 0) + acc.get('byteOffset', 0)
        stride = bv.get('byteStride', 12)
        for i in range(acc['count']):
            pts.append(struct.unpack_from('<3f', b, off + i * stride))
ys = [p[1] for p in pts]; y0, y1 = min(ys), max(ys)
print(f'height {(y1 - y0) * scale:.1f} cm, verts {len(pts)}')
for k in range(10, -1, -1):
    lo = y0 + (y1 - y0) * k / 10.0; hi = lo + (y1 - y0) / 10.0
    sel = [p for p in pts if lo <= p[1] <= hi] or [(0, 0, 0)]
    xs = [p[0] for p in sel]; zs = [p[2] for p in sel]
    print(f'  h {((lo - y0) * scale):6.1f}  width {(max(xs) - min(xs)) * scale:5.1f}  depth {(max(zs) - min(zs)) * scale:5.1f}  zc {((max(zs) + min(zs)) / 2) * scale:5.1f}')
