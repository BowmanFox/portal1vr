"""r10by: tubes hanging from the turret-lift collar to the floor ring, with a pale skirt under the collar.
Local frame = world axes (QC $origin 0 0 0 -90 maps SMD x to world x); origin at the collar centre (4575 58 1340)."""
import math
TRIS = []
def add(a, b, c, mat, hint):
    ux, uy, uz = (b[i] - a[i] for i in range(3)); vx, vy, vz = (c[i] - a[i] for i in range(3))
    n = (uy * vz - uz * vy, uz * vx - ux * vz, ux * vy - uy * vx)
    if sum(n[i] * hint[i] for i in range(3)) < 0: b, c = c, b; n = tuple(-x for x in n)
    l = math.sqrt(sum(x * x for x in n)) or 1.0; n = tuple(x / l for x in n)
    TRIS.append((mat, [(a, n), (b, n), (c, n)]))
def quad(a, b, c, d, mat, hint):
    add(a, b, c, mat, hint); add(a, c, d, mat, hint)
def bez(p0, p1, p2, t):
    return tuple((1 - t) ** 2 * p0[i] + 2 * (1 - t) * t * p1[i] + t * t * p2[i] for i in range(3))
def norm(v):
    l = math.sqrt(sum(x * x for x in v)) or 1.0; return tuple(x / l for x in v)
def cross(a, b): return (a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0])
def tube(pts, r, mat, sides=10):
    rings = []
    for i, c in enumerate(pts):
        t = norm(tuple(pts[min(i + 1, len(pts) - 1)][k] - pts[max(i - 1, 0)][k] for k in range(3)))
        up = (0, 0, 1) if abs(t[2]) < 0.9 else (1, 0, 0)
        n = norm(cross(t, up)); b = cross(t, n)
        rings.append([(tuple(c[k] + r * (math.cos(2 * math.pi * j / sides) * n[k] + math.sin(2 * math.pi * j / sides) * b[k]) for k in range(3)),
                       tuple(math.cos(2 * math.pi * j / sides) * n[k] + math.sin(2 * math.pi * j / sides) * b[k] for k in range(3))) for j in range(sides)])
    for i in range(len(rings) - 1):
        for j in range(sides):
            a, ha = rings[i][j]; b2, _ = rings[i][(j + 1) % sides]; c, _ = rings[i + 1][(j + 1) % sides]; d, _ = rings[i + 1][j]
            quad(a, b2, c, d, mat, ha)
# six tubes: from the collar's underside (radius 78) bulging out (radius 118) and down into the floor ring (radius 40)
ZF = 944 + 22 - 1340
for k in range(6):
    a = math.radians(30 + 60 * k)
    p0 = (78 * math.cos(a), 78 * math.sin(a), -4)
    p1 = (125 * math.cos(a), 125 * math.sin(a), -150)
    p2 = (40 * math.cos(a), 40 * math.sin(a), ZF)
    tube([bez(p0, p1, p2, i / 18) for i in range(19)], 7.5, 'r10_tu_tube')
# pale skirt under the collar (the video's light band below the dark platform, 64.25-65 s)
S = 36
for j in range(S):
    t0, t1 = 2 * math.pi * j / S, 2 * math.pi * (j + 1) / S
    for (r, hint_s) in ((132, 1), (118, -1)):
        a = (r * math.cos(t0), r * math.sin(t0), -10); b = (r * math.cos(t1), r * math.sin(t1), -10)
        c = (r * math.cos(t1), r * math.sin(t1), -34); d = (r * math.cos(t0), r * math.sin(t0), -34)
        quad(a, b, c, d, 'r10_tu_skirt', (hint_s * math.cos(t0), hint_s * math.sin(t0), 0))
    a = (118 * math.cos(t0), 118 * math.sin(t0), -34); b = (132 * math.cos(t0), 132 * math.sin(t0), -34)
    c = (132 * math.cos(t1), 132 * math.sin(t1), -34); d = (118 * math.cos(t1), 118 * math.sin(t1), -34)
    quad(a, b, c, d, 'r10_tu_skirt', (0, 0, -1))
    a = (118 * math.cos(t0), 118 * math.sin(t0), -10); b = (132 * math.cos(t0), 132 * math.sin(t0), -10)
    c = (132 * math.cos(t1), 132 * math.sin(t1), -10); d = (118 * math.cos(t1), 118 * math.sin(t1), -10)
    quad(a, b, c, d, 'r10_tu_skirt', (0, 0, 1))
with open('r10_tu_tubes.smd', 'w') as f:
    f.write('version 1\nnodes\n0 "root" -1\nend\nskeleton\ntime 0\n0 0 0 0 0 0 0\nend\ntriangles\n')
    for mat, vs in TRIS:
        f.write(mat + '\n')
        for (p, n) in vs:
            f.write('0 %.4f %.4f %.4f %.4f %.4f %.4f 0 0\n' % (p[0], p[1], p[2], n[0], n[1], n[2]))
    f.write('end\n')
open('r10_tu_tubes.qc', 'w').write('$modelname "corehub_intro/r10_tu_tubes.mdl"\n$origin 0 0 0 -90\n$body body "r10_tu_tubes.smd"\n'
    '$cdmaterials "models/corehub_intro"\n$surfaceprop "metal"\n$staticprop\n$sequence idle "r10_tu_tubes.smd" fps 1\n')
M = '../runtime/game/corehub_intro/materials/models/corehub_intro/'
open(M + 'r10_tu_tube.vmt', 'w').write('"UnlitGeneric"\n{\n"$basetexture" "lights/white002"\n"$color" "[0.075 0.075 0.078]"\n"$model" "1"\n}\n')
open(M + 'r10_tu_skirt.vmt', 'w').write('"UnlitGeneric"\n{\n"$basetexture" "lights/white002"\n"$color" "[0.42 0.42 0.42]"\n"$model" "1"\n}\n')
print('tris', len(TRIS))
