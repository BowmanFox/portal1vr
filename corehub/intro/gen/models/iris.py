"""Opening-room iris and the ascent tube (22-32.5 s): the four white petals, the grey frame with its dark intake,
the tube collars, the end cap and the cube that flies up ahead of the camera.

Rebuilt in Oct 2026 from the 2009 video (the original models were lost with the old PC). All parts have their
axis along model +X, which the map points up the shaft (entity angles 270 y 0). Sizes are world units, measured
from the video with tools/offline/ringtrack.py at the director's camera (see NOTES in gen/README.md):
  petal disc radius 43.6, hub 12.5, light 2.75 (closed disc at 22.82 s)
  frame ring 45.4 .. 53.7 at the ceiling (24-25.5 s), first collar ("mouth") about 45-60 units above it
  collars: outer radius 35.3, light band from 0.78 R, groove 0.74-0.78 R, inner band 0.68-0.74 R, about 25 tall
"""
import math
import numpy as np
from lib.gen import Mesh, V, mat, ramp, save, rot_x, rot_y, rot_z

N = 48            # segments of a full circle for round parts (the video's rings are smooth circles at the iris)


def ring_x(m, x, r0, r1, material, n=N, a0=0.0, a1=360.0, down=True):
    """flat annulus (or sector of one) in the plane X = x between radii r0 < r1, facing -X (down the shaft) when down"""
    steps = max(1, int(round(n * (a1 - a0) / 360.0)))
    for k in range(steps):
        t0 = math.radians(a0 + (a1 - a0) * k / steps); t1 = math.radians(a0 + (a1 - a0) * (k + 1) / steps)
        p = [(x, r0 * math.cos(t0), r0 * math.sin(t0)), (x, r1 * math.cos(t0), r1 * math.sin(t0)),
             (x, r1 * math.cos(t1), r1 * math.sin(t1)), (x, r0 * math.cos(t1), r0 * math.sin(t1))]
        # radial x tangential = +X, so this order faces +X; reverse it to face down the shaft (-X)
        if r0 < 1e-6: p = [p[1], p[2], p[0]]
        if down: p = p[::-1]
        m.poly(material, p)
    return m


def wall_x(m, x0, r0, x1, r1, material, n=N, a0=0.0, a1=360.0, inward=True):
    """conical/cylindrical wall about the X axis from (x0, r0) to (x1, r1); inward: visible from the axis side"""
    steps = max(1, int(round(n * (a1 - a0) / 360.0)))
    for k in range(steps):
        t0 = math.radians(a0 + (a1 - a0) * k / steps); t1 = math.radians(a0 + (a1 - a0) * (k + 1) / steps)
        p = [(x0, r0 * math.cos(t0), r0 * math.sin(t0)), (x0, r0 * math.cos(t1), r0 * math.sin(t1)),
             (x1, r1 * math.cos(t1), r1 * math.sin(t1)), (x1, r1 * math.cos(t0), r1 * math.sin(t0))]
        # tangential x axial = radially outward, so this order faces away from the axis
        if inward: p = p[::-1]
        m.quad(material, *p)
    return m


def materials():
    mat('iris_white', (0.86, 0.855, 0.85))               # petals (video 211-222)
    mat('iris_white_lo', (0.80, 0.795, 0.79))            # petal edge strip
    mat('iris_seam', (0.50, 0.50, 0.50))
    mat('iris_spoke', (0.45, 0.46, 0.47))
    mat('iris_hub', (0.315, 0.33, 0.34))                 # hub ring (video 80 84 86)
    mat('iris_hub_dark', (0.17, 0.18, 0.19))
    mat('iris_cyan', (0.30, 0.90, 0.90))
    mat('iris_cyan_rim', (0.15, 0.56, 0.58))
    mat('iris_side', (0.12, 0.12, 0.125))
    mat('irisf_ring', (0.31, 0.33, 0.345))               # frame ring (video 76 81 85)
    mat('irisf_ring_in', (0.20, 0.21, 0.22))
    ramp('irisf_cav', (0.20, 0.20, 0.20), (0.0, 0.0, 0.0, 0.0, 0.05, 0.25, 0.6, 1.0))   # cavity wall: black, grey only on the far side
    mat('irisf_black', (0.012, 0.012, 0.012))
    mat('asc_band', (0.305, 0.31, 0.31))                 # collar underside (video 74-80)
    mat('asc_band_in', (0.245, 0.25, 0.25))
    mat('asc_groove', (0.15, 0.15, 0.15))
    ramp('asc_wall', (0.10, 0.10, 0.10), (0.35, 0.55, 0.8, 1.0))
    mat('asc_black', (0.02, 0.02, 0.02))
    mat('asc_rail', (0.03, 0.03, 0.032))


# ------------------------------------------------------------------------------------------------ petals
PETAL_R = 43.6; HUB_R = 12.5; LIGHT_R = 2.75; PETAL_T = 2.0; HUB_DROP = 3.0


def quarter():
    """one 90-degree petal in the +Y+Z quadrant, corner on the axis; its lower face is X = 0"""
    m = Mesh()
    ring_x(m, 0.0, HUB_R - 0.2, PETAL_R - 0.9, 'iris_white', a0=0, a1=90)
    ring_x(m, 0.0, PETAL_R - 0.9, PETAL_R, 'iris_seam', a0=0, a1=90)                 # rim
    # spoke along the bisector, a little proud of the face, with the small bracket at the rim
    c, s = math.cos(math.radians(45)), math.sin(math.radians(45))
    sp = Mesh().box((-0.7, -1.45, HUB_R - 0.5), (0.0, 1.45, PETAL_R + 0.6), 'iris_spoke')
    sp.box((-1.0, -2.6, PETAL_R - 3.2), (0.0, 2.6, PETAL_R + 1.4), 'iris_spoke')
    m.add(sp, R=rot_x(-45))                 # the box runs along +Z; rotate it onto the bisector between +Y and +Z
    # hub quarter: dark ring, raised step, light in the middle (HUB_DROP below the petal face)
    wall_x(m, 0.0, HUB_R, -HUB_DROP, HUB_R - 1.2, 'iris_hub_dark', a0=0, a1=90, inward=False)
    ring_x(m, -HUB_DROP, 4.6, HUB_R - 1.2, 'iris_hub', a0=0, a1=90)
    ring_x(m, -HUB_DROP, LIGHT_R, 4.6, 'iris_cyan_rim', a0=0, a1=90)
    ring_x(m, -HUB_DROP, 0.0, LIGHT_R, 'iris_cyan', a0=0, a1=90, n=24)
    # the two straight edges (seen as thin dark lines) and the back
    for (y, z), out in (((1, 0), V(0, 0, -1)), ((0, 1), V(0, -1, 0))):     # edge along +Y faces -Z, edge along +Z faces -Y
        a = V(0, 0, 0); b = V(0, y * PETAL_R, z * PETAL_R)
        up = V(PETAL_T, 0, 0); dn = V(-HUB_DROP, 0, 0)
        q = [a + dn, b, b + up, a + up]
        nrm = np.cross(q[1] - q[0], q[2] - q[0])
        if nrm @ out < 0: q = q[::-1]
        m.quad('iris_side', *q)
    ring_x(m, PETAL_T, 0.0, PETAL_R, 'iris_side', a0=0, a1=90, down=False)
    wall_x(m, 0.0, PETAL_R, PETAL_T, PETAL_R, 'iris_side', a0=0, a1=90, inward=False)
    return m


# ------------------------------------------------------------------------------------------------ frame and tube
# Sizes solved from the video (tools/offline: ring regression over the 23.5-31.2 s hold and the ascent bundle solve):
#   frame ring 45.4 .. 53.7 at the ceiling; the tube mouth is 116.8 above it with radius 45.84; the collars have
#   radius 61.06 and sit at 933.4, 1488.0, 2351.9 and 3216.7 (set in scenes/iris.py); the camera climbs at 2087 u/s.
FRAME_R0 = 45.4; FRAME_R1 = 53.7          # light ring at the ceiling (X = 0)
MOUTH_X = 116.8; MOUTH_R = 45.84           # the tube's lower rim, seen from the room as the light double ring
MOUTH_RI = 0.84 * MOUTH_R                  # inner edge of the rim (38.5)
SLEEVE_H = 30.0                            # dark 12-sided sleeve above the rim
COLLAR_R = 61.06


def collar(m, x, R=COLLAR_R, tall=42.0, band='asc_band', band_in='asc_band_in', groove='asc_groove', wall='asc_wall', n=N):
    """a collar of the ascent tube, underside at X = x: light band (0.78-1 R), groove, inner band (0.68-0.74 R) and
    the dark inside wall the camera sees just after passing it"""
    r_in = 0.68 * R
    ring_x(m, x, 0.78 * R, R, band, n=n)
    ring_x(m, x + 2.0, 0.74 * R, 0.78 * R, groove, n=n)
    wall_x(m, x, 0.78 * R, x + 2.0, 0.78 * R, groove, n=n, inward=True)
    ring_x(m, x, r_in, 0.74 * R, band_in, n=n)
    wall_x(m, x, 0.74 * R, x + 2.0, 0.74 * R, groove, n=n, inward=False)
    w = Mesh(); wall_x(w, x, r_in, x + tall, r_in, wall, n=n, inward=True)
    w.shade(wall, levels=4, light=(0.0, -1.0, 0.0))
    m.add(w)
    wall_x(m, x, R, x + tall, R, 'asc_black', n=n, inward=False)                   # outside
    ring_x(m, x + tall, r_in, R, 'asc_black', n=n, down=False)                     # top
    return m


def frame():
    m = Mesh()
    ring_x(m, 0.0, FRAME_R0, FRAME_R1, 'irisf_ring')
    ring_x(m, 0.0, FRAME_R0 - 1.6, FRAME_R0, 'irisf_ring_in')
    wall_x(m, 0.0, FRAME_R1, 6.0, FRAME_R1, 'irisf_black', inward=False)
    # dark intake between the ring and the tube mouth: black, with a little light on the side away from the bed (model +Y)
    r0 = FRAME_R0 - 1.6
    w = Mesh(); wall_x(w, 0.0, r0, MOUTH_X, MOUTH_R + 0.6, 'irisf_cav', inward=True)
    w.shade('irisf_cav', levels=8, light=(0.0, -1.0, 0.0))      # an inward wall on the +Y side has its normal toward -Y
    m.add(w)
    wall_x(m, 0.0, r0 + 1.0, MOUTH_X + SLEEVE_H, MOUTH_R + 1.6, 'irisf_black', inward=False)      # its outside, seen from the shaft
    # the tube's lower rim: light band, dark line, thin light line, then the dark 12-sided sleeve
    ring_x(m, MOUTH_X, 0.89 * MOUTH_R, MOUTH_R, 'asc_band')
    ring_x(m, MOUTH_X + 0.8, 0.86 * MOUTH_R, 0.89 * MOUTH_R, 'asc_groove')
    ring_x(m, MOUTH_X, MOUTH_RI, 0.86 * MOUTH_R, 'asc_band')
    w = Mesh(); wall_x(w, MOUTH_X, MOUTH_RI, MOUTH_X + SLEEVE_H, MOUTH_RI, 'asc_wall', n=12, inward=True)
    w.shade('asc_wall', levels=4, light=(0.0, -1.0, 0.0))
    m.add(w)
    ring_x(m, MOUTH_X + SLEEVE_H, MOUTH_RI, MOUTH_R + 1.6, 'irisf_black', down=False)
    # the four rails come down from the tube through the intake to the petals' hubs (thin dark rods on the diagonals)
    for k in range(4):
        a = math.radians(45 + 90 * k); y, z = RAIL_RHO * math.cos(a), RAIL_RHO * math.sin(a)
        m.box((-20.0, y - 0.9, z - 0.9), (MOUTH_X + SLEEVE_H, y + 0.9, z + 0.9), 'asc_rail')
    return m


RAIL_RHO = 34.0


def cap():
    """closes the top of the ascent tube (never seen lit)"""
    m = Mesh(); ring_x(m, 0.0, 0.0, COLLAR_R, 'asc_black'); return m


def build():
    materials()
    save(quarter(), 'p9_joined_quarter_v3')
    save(frame(), 'p9_joined_frame_v6')
    up = rot_y(-90)        # the map places the collars and the cap unrotated (angles 0 0 0), so their axis is model +Z
    for name in ('p9_ascent_collar_plain_v4', 'p9_ascent_collar_recess_v4', 'p9_ascent_collar_end_v4'):
        save(collar(Mesh(), 0.0).transform(R=up), name)
    save(cap().transform(R=up), 'p9_ascent_cap_v1')
