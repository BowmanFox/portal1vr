# usage: pathclear.py VMF "t:x,y,z;t:x,y,z;..." [margin] -> brushes the camera path passes through (exact plane test)
import sys
import numpy as np
from srctools import VMF
v = VMF.parse(sys.argv[1]); margin = float(sys.argv[3]) if len(sys.argv) > 3 else 6.0
keys = [(float(a.split(':')[0]), np.array([float(c) for c in a.split(':')[1].split(',')])) for a in sys.argv[2].split(';')]
pts = []
for (t0, a), (t1, b) in zip(keys, keys[1:]):
    for k in range(16): f = k / 16; pts.append((t0 + (t1 - t0) * f, a + (b - a) * f))
out = {}
for e in [v.spawn] + list(v.entities):
    for so in e.solids:
        lo, hi = so.get_bbox()
        lo = np.array([lo.x, lo.y, lo.z]) - margin; hi = np.array([hi.x, hi.y, hi.z]) + margin
        cand = [(t, p) for t, p in pts if np.all(p > lo) and np.all(p < hi)]
        if not cand: continue
        planes = []
        for f in so.sides:
            p1, p2, p3 = (np.array([c.x, c.y, c.z]) for c in f.planes)
            n = np.cross(p3 - p1, p2 - p1); n = n / np.linalg.norm(n)   # outward normal (Hammer winding)
            planes.append((n, float(n @ p1)))
        for t, p in cand:
            if all(n @ p - d < margin for n, d in planes):
                out.setdefault((e['classname'], tuple(np.round(lo + margin)), tuple(np.round(hi - margin)), sorted(set(f.mat for f in so.sides))[0]), []).append(round(t, 3))
for k, ts in out.items(): print(k, ts[0], ts[-1], len(ts))
print('checked', len(pts), 'points; hits', len(out))
