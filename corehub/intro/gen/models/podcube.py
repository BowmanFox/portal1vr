"""Models of the pod + cube shots (39.3-54.1 s), prefix r11_pc (see scenes/podcube.py).

Collars / rings of the three tubes (axis = model +Z, the face the camera approaches at Z = 0, the ring extends to
+Z): a 12-sided flat annulus (outer radius R = 61.06, the collars' light band) with a darker inner rim (0.68-0.74 R)
and the inner wall the camera sees just after passing it (radius 0.68 R). Tones sampled from the film:
  glass tube of the first straight (39.3-41.9 s): wide mid-grey annulus;
  ringed tube down to the junction (43.8-47.9 s): dark grey rings, dense (every ~120 units);
  cube tube (50.4-54.1 s): light grey rings every ~112 units.
The cube: a weighted storage cube (rounded corner blocks, a round panel on every face), edge 2 * CUBE_H."""
import math
import numpy as np
from lib.gen import Mesh, V, mat, ramp, save

R = 61.06
N = 12
CUBE_H = 22.0

TONES = {
    # name: (face, rim, inner wall by shade level 0..3, outside); sampled from the film under the preview's faces
    # (out/pc/tones.py: A1 39.8-41.3 s, A2 44.3-46.3 s, C 51-53.5 s)
    'a1': (0.27, 0.12, (0.30, 0.31, 0.235, 0.19), 0.12),
    'a2': (0.21, 0.09, (0.21, 0.18, 0.13, 0.11), 0.09),
    'c': (0.32, 0.13, (0.276, 0.286, 0.239, 0.25), 0.12),
    'b': (0.20, 0.08, (0.14, 0.14, 0.14, 0.14), 0.06),
    'x': (0.18, 0.10, (0.30, 0.30, 0.30, 0.30), 0.08),
}


EDGE = {'c': 0.11, 'a1': 0.14, 'a2': 0.10}          # the cube tube's collars show a thin dark outline at the outer edge


def materials():
    mat('r11_pc_rail', (0.03, 0.03, 0.035))
    for k, (face, rim, wall, out) in TONES.items():
        mat('r11_pc_%s_face' % k, face, nocull=True)
        mat('r11_pc_%s_rim' % k, rim, nocull=True)
        mat('r11_pc_%s_edge' % k, EDGE.get(k, face), nocull=True)
        for i, w in enumerate(wall): mat('r11_pc_%s_wall%d' % (k, i), w, nocull=True)
        mat('r11_pc_%s_out' % k, out, nocull=True)
    mat('r11_pc_cross_in', (0.56, 0.57, 0.56), nocull=True)
    mat('r11_pc_cross_out', (0.33, 0.33, 0.33), nocull=True)
    mat('r11_pc_concrete', (0.56, 0.57, 0.56), nocull=True)
    mat('r11_pc_cube_face', (0.50, 0.50, 0.50))
    ramp('r11_pc_cube_s', (0.80, 0.80, 0.81), factors=(0.62, 0.76, 0.89, 1.0))       # the film's cube: light grey faces
    mat('r11_pc_cube_dark', (0.45, 0.45, 0.46))
    mat('r11_pc_cube_disc', (0.62, 0.62, 0.63))
    ramp('r11_pc_pod_s', (0.92, 0.93, 0.94), factors=(0.45, 0.65, 0.85, 1.0))


def _poly(r, n=N, phase=None):
    ph = math.pi / n if phase is None else phase
    return [(r * math.cos(ph + 2 * math.pi * k / n), r * math.sin(ph + 2 * math.pi * k / n)) for k in range(n)]


def annulus(m, z, r0, r1, material, n=N):
    a = _poly(r0, n); b = _poly(r1, n)
    for k in range(n):
        j = (k + 1) % n
        m.quad(material, V(a[k][0], a[k][1], z), V(b[k][0], b[k][1], z), V(b[j][0], b[j][1], z), V(a[j][0], a[j][1], z))


def wall(m, z0, z1, r, material, n=N):
    a = _poly(r, n)
    for k in range(n):
        j = (k + 1) % n
        m.quad(material, V(a[k][0], a[k][1], z0), V(a[j][0], a[j][1], z0), V(a[j][0], a[j][1], z1), V(a[k][0], a[k][1], z1))


def ring(kind, depth=42.0, r_in=0.68, r_rim=0.74, scale=1.0, outer=1.0):
    """a collar of tube `kind` ('a1', 'a2', 'c'), axis +Z; outer: the face's outer radius in R (the glass tube's
    collars are wide flat rings, their grey face reaching ~1.35 R in the film)"""
    m = Mesh(); Rr = R * scale
    annulus(m, 0.0, r_rim * Rr, 0.95 * Rr, 'r11_pc_%s_face' % kind)
    annulus(m, 0.0, 0.95 * Rr, Rr, 'r11_pc_%s_edge' % kind)
    if outer > 1.0: annulus(m, 0.0, Rr, outer * Rr, 'r11_pc_%s_face' % kind)
    annulus(m, 0.0, r_in * Rr, r_rim * Rr, 'r11_pc_%s_rim' % kind)
    w = Mesh(); wall(w, 0.0, depth * scale, r_in * Rr, 'r11_pc_%s_wall' % kind)
    w.shade('r11_pc_%s_wall' % kind, levels=4, light=(0.3, 0.8, 0.2))
    m.add(w)
    wall(m, 0.0, depth * scale, Rr, 'r11_pc_%s_out' % kind)
    annulus(m, depth * scale, r_in * Rr, Rr, 'r11_pc_%s_out' % kind)
    return m


def cube(h=CUBE_H):
    """weighted storage cube centred on the origin (edge 2h): light faces, darker corner blocks, a round panel"""
    m = Mesh()
    b = Mesh(); b.box((-h, -h, -h), (h, h, h), 'r11_pc_cube_s'); b.shade('r11_pc_cube_s', levels=4, light=(0.4, -0.3, 0.85)); m.add(b)
    c = 0.36 * h; e = h + 0.8
    for sx in (-1, 1):
        for sy in (-1, 1):
            for sz in (-1, 1):
                lo = (sx * (h - c) if sx > 0 else -e, sy * (h - c) if sy > 0 else -e, sz * (h - c) if sz > 0 else -e)
                hi = (e if sx > 0 else -(h - c), e if sy > 0 else -(h - c), e if sz > 0 else -(h - c))
                m.box(lo, hi, 'r11_pc_cube_dark')
    # a round panel on every face
    for ax in range(3):
        for sgn in (-1, 1):
            pts = []
            for k in range(16):
                a = 2 * math.pi * k / 16; u, w = 0.42 * h * math.cos(a), 0.42 * h * math.sin(a)
                p = [0.0, 0.0, 0.0]; p[ax] = sgn * (h + 0.4); p[(ax + 1) % 3] = u; p[(ax + 2) % 3] = w; pts.append(V(*p))
            if sgn < 0: pts = pts[::-1]
            if ax == 1: pts = pts[::-1]
            m.poly('r11_pc_cube_disc', pts)
    return m


def pod(L=60.0, r=18.0):
    """the white capsule in the ringed tube's far end (axis +Z), a stretched sphere"""
    m = Mesh(); m.sphere((0, 0, 0), 1.0, 'r11_pc_pod_s', n=16, m=10, squash=(r, r, L / 2))
    m.shade('r11_pc_pod_s', levels=4, light=(0.3, 0.5, -0.8))
    return m


def build():
    materials()
    for k in TONES:
        save(ring(k, outer=1.35 if k == 'a1' else 1.0), 'r11_pc_ring_%s' % k)
    save(ring('x', scale=92.0 / 61.06 * 1.0), 'r11_pc_ring_xl')          # the junction's vertical tube (radius 92 inside 0.68 R)
    save(cube(), 'r11_pc_cube')
    save(pod(), 'r11_pc_pod')
