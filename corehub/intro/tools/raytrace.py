# usage: raytrace.py VMF cx cy cz pitch yaw roll [fx fy ...]  -> what surface each frame point (fractions) hits
import sys, math, numpy as np
from srctools import VMF, Vec
v = VMF.parse(sys.argv[1]); c = np.array([float(a) for a in sys.argv[2:5]]); P, Y, R = (math.radians(float(a)) for a in sys.argv[5:8])
pts = [(float(sys.argv[i]), float(sys.argv[i + 1])) for i in range(8, len(sys.argv), 2)] or [(0.5, 0.5)]
f = np.array([math.cos(P) * math.cos(Y), math.cos(P) * math.sin(Y), -math.sin(P)])
r0 = np.array([math.sin(Y), -math.cos(Y), 0.0]); u0 = np.cross(r0, f)
r = r0 * math.cos(R) + u0 * math.sin(R); u = np.cross(r, f)   # roll
brushes = []
for e in [v.spawn] + list(v.entities):
    if e['classname'] in ('func_detail', 'worldspawn', 'func_brush', 'func_wall', 'func_door', 'func_movelinear'):
        for so in e.solids:
            if any(k in s2.mat.lower() for s2 in so.sides for k in ('glass', 'trigger', 'clip', 'skybox')): continue
            planes = []
            for s in so.sides:
                n = s.normal(); p0 = s.planes[0]
                n = np.array([n.x, n.y, n.z]); planes.append((-n, float(np.dot(-n, [p0.x, p0.y, p0.z])), s.mat, e['classname']))
            brushes.append(planes)
def hit(o, d):
    best = (1e18, None)
    for planes in brushes:
        tmin, tmax, mat = 0.0, 1e18, None
        ok = True
        for n, dist, m, cls in planes:   # outward normal n, inside: n.x <= dist
            den = n @ d; num = dist - n @ o
            if abs(den) < 1e-9:
                if num < 0: ok = False; break
                continue
            t = num / den
            if den < 0:
                if t > tmin: tmin, mat = t, (m, cls)
            else:
                tmax = min(tmax, t)
            if tmin > tmax: ok = False; break
        if ok and mat and tmin < best[0]: best = (tmin, mat)
    return best
for fx, fy in pts:
    d = f + r * ((fx - 0.5) * 2 * 1.2) + u * ((0.5 - fy) * 2 * 0.75); d /= np.linalg.norm(d)
    t, m = hit(c, d)
    p = c + d * t if m else None
    print(f'({fx:.2f},{fy:.2f}) dist {t:.0f} at {None if p is None else np.round(p)} -> {m}')
