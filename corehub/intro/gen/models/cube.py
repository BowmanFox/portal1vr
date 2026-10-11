"""Weighted storage cubes: the one that flies up the tube ahead of the camera (30.5-32 s) and the one in the opening
room (11-13 s). Own mesh in the style of the video's cube: light corner blocks, dark edge channels, a round plate
in the middle of every face."""
import math
import numpy as np
from lib.gen import Mesh, V, mat, ramp, save, rot_x, rot_y, rot_z


def materials():
    ramp('cube_c', (0.80, 0.80, 0.79), (0.55, 0.70, 0.85, 1.0))        # corner blocks
    ramp('cube_b', (0.52, 0.52, 0.52), (0.50, 0.68, 0.84, 1.0))        # body panels
    ramp('cube_d', (0.30, 0.30, 0.305), (0.45, 0.65, 0.82, 1.0))       # channels between the corners
    ramp('cube_p', (0.86, 0.86, 0.85), (0.60, 0.74, 0.88, 1.0))        # round plates
    mat('cube_ring', (0.30, 0.30, 0.31))


def face_frames():
    """(normal, u, v) for the six faces"""
    out = []
    for ax in range(3):
        for sgn in (1, -1):
            n = np.zeros(3); n[ax] = sgn
            u = np.zeros(3); u[(ax + 1) % 3] = 1
            v = np.cross(n, u)
            out.append((n, u, v))
    return out


def cube_mesh(S=36.0, light=(0.3, -0.45, 0.84)):
    h = S / 2.0
    m = Mesh()
    k = S / 36.0
    # dark core with the edge channels
    core = Mesh().box((-h + 2.2 * k,) * 3, (h - 2.2 * k,) * 3, 'cube_d')
    m.add(core)
    # body panels: a slightly raised square on each face between the corner blocks
    for n, u, v in face_frames():
        a = 9.5 * k; z = h - 1.2 * k
        P = [n * z + u * su * a + v * sv * a for su, sv in ((-1, -1), (1, -1), (1, 1), (-1, 1))]
        m.poly('cube_b', P)
        for (i, j) in ((0, 1), (1, 2), (2, 3), (3, 0)):                 # short walls down to the core
            m.quad('cube_b', P[i] - n * (1.0 * k), P[j] - n * (1.0 * k), P[j], P[i])
    # eight corner blocks
    c0, c1 = 5.5 * k, h
    for sx in (-1, 1):
        for sy in (-1, 1):
            for sz in (-1, 1):
                lo = (min(sx * c0, sx * c1), min(sy * c0, sy * c1), min(sz * c0, sz * c1))
                hi = (max(sx * c0, sx * c1), max(sy * c0, sy * c1), max(sz * c0, sz * c1))
                m.box(lo, hi, 'cube_c')
    # round plate with a dark ring on each face
    for n, u, v in face_frames():
        steps = 20; r1, r0 = 8.3 * k, 6.7 * k; z1 = h + 0.1 * k; z0 = h - 1.2 * k
        ring = [(math.cos(2 * math.pi * i / steps), math.sin(2 * math.pi * i / steps)) for i in range(steps)]
        m.poly('cube_p', [n * z1 + (u * c + v * s) * r0 for c, s in ring])
        for i in range(steps):
            (ca, sa), (cb, sb) = ring[i], ring[(i + 1) % steps]
            A0 = n * z1 + (u * ca + v * sa) * r0; B0 = n * z1 + (u * cb + v * sb) * r0
            A1 = n * z0 + (u * ca + v * sa) * r1; B1 = n * z0 + (u * cb + v * sb) * r1
            m.quad('cube_ring', A0, A1, B1, B0)
    for base, lv in (('cube_c', 4), ('cube_b', 4), ('cube_d', 4), ('cube_p', 4)):
        m.shade(base, levels=lv, light=light)
    return m


def build():
    materials()
    save(cube_mesh(36.0), 'p9_joined_cube_v2')
