"""Opening room (0-21.7 s): the models the r10dm map places in the relaxation chamber, rebuilt in Oct 2026 from the
2009 video (the compiled originals were lost with the old PC; only their placements survived in the map).

Every model keeps its old name and is built in the coordinates of its old placement (origin and angles in the map),
so the map needs no change. Sizes and positions were measured on the video with the film camera of the base
director (fov 60): feature points tracked over many frames and triangulated (tools in the agent's scratch folder:
cam.py / track_*.py), outlines unprojected onto the floor (z 0) or onto known planes, then checked by drawing each
model over the film frames.

  pod (p9_opening_bed_body_metric_v4 + _cover_metric_v4 + _damage_v5), placed at (-12853.5, -167.0, 0) yaw 44.15:
      the cyan window tracked over 16.9-21.5 s (centre triangulated at model (-8.6, 63.6, 38.2)), the big dome hole
      triangulated at (-8.2, 28.3, 68.5) (0.5 px over 18 frames), the plinth's floor edge unprojected at 18.5 / 21.5 s
      (model (-24, 56) .. (-14, -49): the pod's long axis is model Y, front +Y); length 132, width 60, rim 45 (55 at
      the head end), dome to 74; window extents fitted to the film's cyan region within 2-6 px at 17.5-21.5 s.
  slab, foreground pieces, cube, bottles, handsets, chips, cable, housing, door: see their sections below.
"""
import math
import numpy as np
from lib.gen import Mesh, V, mat, ramp, save, rot_x, rot_y, rot_z

PI = math.pi


# ------------------------------------------------------------------------------------------------ helpers
def sel(a, b, n=2.6, N=48, phase=0.0):
    """superellipse outline (x half-axis a, y half-axis b, exponent n) as N (x, y) points, counter-clockwise from +x"""
    out = []
    for k in range(N):
        t = 2 * PI * k / N + phase
        c, s = math.cos(t), math.sin(t)
        out.append((a * math.copysign(abs(c) ** (2.0 / n), c), b * math.copysign(abs(s) ** (2.0 / n), s)))
    return np.array(out)


def loft(m, rings, mat_fn):
    """connect closed rings (list of (N,3) arrays, bottom to top, points counter-clockwise seen from +z): faces outward.
    mat_fn(k, j) -> material of the quad between ring k and k+1 at segment j (or a string)"""
    for k in range(len(rings) - 1):
        A, B = rings[k], rings[k + 1]; N = len(A)
        for j in range(N):
            j2 = (j + 1) % N
            mm = mat_fn(k, j) if callable(mat_fn) else mat_fn
            if mm is None: continue
            m.quad(mm, A[j], A[j2], B[j2], B[j])
    return m


def cap(m, ring, mat, up=True):
    """fan-close a ring (facing +z when up)"""
    c = ring.mean(axis=0); N = len(ring)
    for j in range(N):
        j2 = (j + 1) % N
        if up: m.tri(mat, c, ring[j], ring[j2])
        else: m.tri(mat, c, ring[j2], ring[j])
    return m


def ring3(xy, z, sx=1.0, sy=1.0, dx=0.0, dy=0.0):
    return np.array([(dx + x * sx, dy + y * sy, z) for x, y in xy])


# ------------------------------------------------------------------------------------------------ pod
# pod frame: x lateral, y toward the front (window, dome), z up; origin on the floor under the middle of the body.
POD = dict(phi=0.0, front=(-3.5, 72.0), A=66.0, B=30.0, n=3.0, roll=0.0, pitch=0.0, yaw_extra=0.0, lift=0.0,
           dome_y=30.0, dome_ax=21.0, dome_ay=32.0, dome_az=29.0, rim=45.0, rise=10.0, win_lo=-20.0)


def pod_frame():
    """4x4-ish: returns (R, T) mapping pod-frame points to model coordinates"""
    phi = math.radians(POD['phi'] + POD['yaw_extra'])
    yp = np.array([-math.sin(phi), math.cos(phi), 0.0]); xp = np.array([math.cos(phi), math.sin(phi), 0.0])
    R = np.stack([xp, yp, [0, 0, 1.0]], axis=1)                     # columns: pod axes in model coords
    R = R @ rot_y(POD['roll']) @ rot_x(POD['pitch'])
    front = np.array([POD['front'][0], POD['front'][1], 0.0])
    T = front - R @ np.array([0.0, POD['A'], 0.0]) + np.array([0, 0, POD['lift']])
    return R, T


def pod_materials():
    ramp('r11_op_pod_w', (0.92, 0.915, 0.91), (0.17, 0.27, 0.37, 0.47, 0.58, 0.69, 0.81, 0.94))
    ramp('r11_op_pod_in', (0.80, 0.80, 0.80), (0.35, 0.55, 0.75, 1.0))
    mat('r11_op_pod_base', (0.27, 0.27, 0.27))
    mat('r11_op_pod_base_d', (0.17, 0.17, 0.17))
    mat('r11_op_pod_seam', (0.10, 0.10, 0.10))
    mat('r11_op_pod_cyan', (0.21, 0.72, 0.82))
    mat('r11_op_pod_cyan_d', (0.14, 0.52, 0.62))
    mat('r11_op_pod_hole', (0.02, 0.02, 0.02))


LIGHT_POD = (-0.55, 0.35, 0.76)      # pod frame: from the camera's right side (pod -x), front and above


def pod_body():
    A, B, n = POD['A'], POD['B'], POD['n']
    N = 72
    base = sel(B, A, n, N)
    m = Mesh()
    # outer white wall: (z, scale); the rim rises toward the back (head) end
    prof = [(9.0, 0.66), (12.0, 0.80), (16.0, 0.89), (21.0, 0.95), (27.0, 0.985), (34.5, 0.999), (35.5, 1.0), (41.5, 0.995), (42.5, 0.993), (45.0, 0.975)]
    rise = POD.get('rise', 6.0)

    def zt(y, z):           # heights above the window row are lifted toward the back
        if z <= 42.5: return z
        f = min(1.0, max(0.0, -y / A)); f = f * f * (3 - 2 * f)
        return z + rise * f
    rings = [np.array([(x * s_, y * s_, zt(y, z)) for x, y in base]) for z, s_ in prof]
    ang = np.degrees(np.arctan2(base[:, 0], base[:, 1]))           # 0 at +y (front), positive toward +x
    a_lo, a_hi = POD.get('win_lo', -34.0), POD.get('win_hi', 56.0)
    zs = [z for z, s_ in prof]

    def wmat(k, j):
        z0 = zs[k]; a = ang[j]
        if a_lo - 3 < a < a_hi + 3 and z0 == 41.5: return 'r11_op_pod_seam'
        if a_lo - 3 < a < a_hi + 3 and z0 == 34.5: return 'r11_op_pod_cyan_d'
        if a_lo < a < a_hi and z0 == 35.5:
            return 'r11_op_pod_cyan' if j % 3 else 'r11_op_pod_cyan_d'
        if z0 == 35.5 and (a_lo - 3 < a <= a_lo or a_hi <= a < a_hi + 3): return 'r11_op_pod_cyan_d'
        return 'r11_op_pod_w'
    loft(m, rings, wmat)
    # rim: flat ring on top, then the inner wall down to the cushion
    top = rings[-1]
    lip = np.array([(x * 0.94, y * 0.95, zt(y, 45.6)) for x, y in base])
    inner = np.array([(x * 0.87, y * 0.90, zt(y, 45.6)) for x, y in base])
    loft(m, [top, lip, inner], 'r11_op_pod_w')
    cush = ring3(base, 30.0, 0.80, 0.85)
    k0 = len(m.tris)
    loft(m, [inner, cush], 'r11_op_pod_in')
    for t in m.tris[k0:]: t.p = t.p[::-1]                          # the inner wall faces the tub's axis
    cap(m, cush, 'r11_op_pod_in')
    cap(m, rings[0], 'r11_op_pod_base_d', up=False)
    m.shade('r11_op_pod_w', levels=8, light=LIGHT_POD)
    m.shade('r11_op_pod_in', levels=4, light=LIGHT_POD)
    # dark plinth under the body (its -x side edge on the floor measured from model (-24, 56) to (-14, -49))
    pl = Mesh()
    pb = sel(B * POD.get('plinth_w', 0.66), A * POD.get('plinth_l', 0.86), 3.0, 40)
    loft(pl, [ring3(pb, 0.0), ring3(pb, 10.5)], 'r11_op_pod_base')
    cap(pl, ring3(pb, 10.5), 'r11_op_pod_base_d')
    m.add(pl)
    return m


def pod_cover():
    """the dome over the front half: half superellipsoid on the rim"""
    A, B = POD['A'], POD['B']
    m = Mesh()
    cy, cz = POD['dome_y'], POD['rim']
    ax, ay, az = POD['dome_ax'], POD['dome_ay'], POD['dome_az']
    N, M = 40, 10
    rings = []
    for i in range(M + 1):
        th = (PI / 2) * i / M                     # 0 at the base, pi/2 at the top
        r = math.cos(th) ** 0.85; z = cz + az * math.sin(th)
        rings.append(ring3(sel(ax, ay, 2.3, N), z, r, r, 0.0, cy))
    rings[-1] = np.repeat(rings[-1].mean(axis=0, keepdims=True), N, axis=0)
    loft(m, rings, 'r11_op_pod_w')
    m.shade('r11_op_pod_w', levels=8, light=LIGHT_POD)
    # dark seam where it sits on the body
    loft(m, [ring3(sel(ax, ay, 2.3, N), cz - 1.2, 1.01, 1.01, 0.0, cy), ring3(sel(ax, ay, 2.3, N), cz + 0.3, 1.01, 1.01, 0.0, cy)], 'r11_op_pod_seam')
    return m


def dome_point(p):
    """the point of the dome surface on the ray from the dome centre through p (pod frame)"""
    c = np.array([0.0, POD['dome_y'], POD['rim']]); d = np.asarray(p, float) - c
    k = 1.0 / math.sqrt((d[0] / POD['dome_ax']) ** 2 + (d[1] / POD['dome_ay']) ** 2 + (d[2] / POD['dome_az']) ** 2)
    return c + d * k, d / np.linalg.norm(d)


CAM_195 = (-124.54, 306.98, 127.94)      # film camera at 19.5 s in the pod's model coordinates


def dome_hit(p):
    """first point of the dome surface on the line of sight from the 19.5 s camera through p (pod frame): the holes
    then appear where the film shows them over 17-21.7 s even though the dome is only an approximation"""
    R, T = pod_frame()
    o = np.linalg.solve(R, np.array(CAM_195) - T)
    c = np.array([0.0, POD['dome_y'], POD['rim']]); s_ = np.array([POD['dome_ax'], POD['dome_ay'], POD['dome_az']])
    d = np.asarray(p, float) - o; d /= np.linalg.norm(d)
    oo = (o - c) / s_; dd = d / s_
    a = dd @ dd; b = 2 * oo @ dd; cc = oo @ oo - 1.0
    disc = b * b - 4 * a * cc
    if disc < 0: return dome_point(p)
    k = (-b - math.sqrt(disc)) / (2 * a)
    q = o + d * k
    n = (q - c) / s_ ** 2; n /= np.linalg.norm(n)
    return q, n


def pod_damage():
    """black holes punched in the dome; the big one triangulated over 17.6-21.6 s at model (-8.2, 28.3, 68.5)"""
    m = Mesh()
    R, T = pod_frame()
    big = np.linalg.solve(R, np.array([-8.2, 28.3, 68.5]) - T)       # pod frame
    for (p0, r) in ((big, 2.6), (big + np.array([5.0, 0.0, 2.6]), 1.1), (big + np.array([11.0, 0.0, -1.0]), 0.8)):
        p, nrm = dome_hit(p0)
        u = np.cross(nrm, [0, 0, 1.0]); u /= np.linalg.norm(u); w = np.cross(nrm, u)
        cen = p + nrm * 0.4
        pts = [cen + r * (math.cos(2 * PI * k / 10) * u + 0.85 * math.sin(2 * PI * k / 10) * w) for k in range(10)]
        for k in range(10):
            m.tri('r11_op_pod_hole', cen, pts[k], pts[(k + 1) % 10])
    return m


def to_model(mesh):
    R, T = pod_frame()
    return Mesh().add(mesh, R=R, offset=T)


# ------------------------------------------------------------------------------------------------ broken slab and the pieces in front of it
# Model origin of all four is the map point (-13000, 0, 0) with angles 0: model coordinates = world - (-13000, 0, 0).
# Slab: right end at world x -12951 (bottom-right on the floor at (-12949..-12951, 147..153) from 12.5 s and 15 s,
# top-right corner at (-12951, 127.4, 58) from 12.5 / 13 / 14 s); the face runs west along y 127, 240 long.
SLAB = dict(x0=49.0, y=127.0, L=240.0, T=12.0,
            top=[(0, 58), (12, 55), (26, 57), (45, 58), (62, 60), (80, 61), (100, 59), (118, 57), (140, 56), (160, 55),
                 (180, 52), (200, 48), (215, 40), (228, 33), (240, 24)])


def slab_materials():
    ramp('r11_op_slab_f', (0.60, 0.59, 0.57), (0.55, 0.70, 0.85, 1.0))          # smooth front / back faces (film 130-160)
    mat('r11_op_slab_hi', (0.76, 0.76, 0.75))                                     # light streaks on the face
    mat('r11_op_slab_top', (0.55, 0.53, 0.51), base='concrete/concretewall001c')   # broken top: rough concrete
    mat('r11_op_slab_end', (0.30, 0.29, 0.28), base='concrete/concretewall001c')
    ramp('r11_op_beam', (0.48, 0.48, 0.47), (0.30, 0.45, 0.70, 1.0))
    ramp('r11_op_beam_d', (0.40, 0.40, 0.40), (0.40, 0.58, 0.78, 1.0))
    mat('r11_op_beam_end', (0.50, 0.49, 0.47), base='concrete/concretewall001c')
    ramp('r11_op_rslab', (0.80, 0.80, 0.79), (0.45, 0.62, 0.80, 1.0))
    mat('r11_op_rod', (0.25, 0.25, 0.25))


LIGHT_SLAB = (0.35, -0.75, 0.55)


def slab():
    """vertical concrete slab with a broken top, face toward -y; the face has the film's vertical light streaks"""
    s = SLAB; m = Mesh()
    x0, y, T = s['x0'], s['y'], s['T']
    top = s['top']
    yf, yb = y - T / 2, y + T / 2
    for (u0, h0), (u1, h1) in zip(top, top[1:]):
        xa, xb = x0 - u0, x0 - u1
        # front (-y) and back (+y) faces as vertical strips, light streak strips on the front
        hi = 40 <= u0 < 120                      # the film's broad bright band on the face (12-13.5 s)
        m.quad('r11_op_slab_hi' if hi else 'r11_op_slab_f', (xa, yf, 0), (xb, yf, 0), (xb, yf, h1), (xa, yf, h0))
        m.quad('r11_op_slab_f', (xb, yb, 0), (xa, yb, 0), (xa, yb, h0), (xb, yb, h1))
        # broken top: a rough cap, a little lower at the back
        m.quad('r11_op_slab_top', (xa, yf, h0), (xb, yf, h1), (xb, yb, h1 - 3), (xa, yb, h0 - 3))
    # ends
    xa = x0; h = top[0][1]
    m.quad('r11_op_slab_end', (xa, yb, 0), (xa, yf, 0), (xa, yf, h), (xa, yb, h - 3))
    xb = x0 - top[-1][0]; h = top[-1][1]
    m.quad('r11_op_slab_end', (xb, yf, 0), (xb, yb, 0), (xb, yb, h - 3), (xb, yf, h))
    m.shade('r11_op_slab_f', levels=4, light=LIGHT_SLAB)
    m.uv_box(64.0, only={'r11_op_slab_top', 'r11_op_slab_end'})
    return m


def beam(m, a, b, w, h, mat_side, mat_end, up=(0, 0, 1.0)):
    """square-section beam from point a to point b (width w across, height h along 'up')"""
    a, b = V(a), V(b); d = b - a; L = np.linalg.norm(d); d /= L
    u = np.cross(V(up), d); u /= np.linalg.norm(u); v = np.cross(d, u)
    c = (a + b) / 2
    R = np.stack([d, u, v], axis=1)
    bx = Mesh().box((-L / 2, -w / 2, -h / 2), (L / 2, w / 2, h / 2), mat_side, mats={'+x': mat_end, '-x': mat_end})
    m.add(bx, R=R, offset=c)
    return m


def fg_broken_beam():
    """dark square beam from the floor (model (-124, -55, 8), 12.5 s on z 8) up to its broken end"""
    m = Mesh()
    beam(m, BEAM['a'], BEAM['b'], 12.0, 12.0, 'r11_op_beam_d', 'r11_op_beam_end')
    m.shade('r11_op_beam_d', levels=4, light=LIGHT_SLAB)
    m.uv_box(64.0, only={'r11_op_beam_end'})
    return m


BEAM = dict(a=(-124.0, -55.0, 6.0), b=(-82.0, 51.0, 27.0))
ANGLED = dict(a=(-53.0, 75.0, 20.0), b=(33.0, 43.5, 18.0), w=13.0, h=15.0)


def fg_angled_beam():
    """light concrete block lying in front of the slab: ends triangulated at world (-13053, 75, 30) (2 views) and
    (-12967, 43.5, 24.7) (3 views, 1-2 px)"""
    m = Mesh()
    beam(m, ANGLED['a'], ANGLED['b'], ANGLED['w'], ANGLED['h'], 'r11_op_beam', 'r11_op_beam_end')
    m.tube((-75.0, 118.0, 34.0), (-40.0, 70.0, 1.0), 0.8, 'r11_op_rod', n=5)
    m.shade('r11_op_beam', levels=4, light=LIGHT_SLAB)
    m.uv_box(64.0, only={'r11_op_beam_end'})
    return m


def fg_rounded_slab():
    m = Mesh()
    out = sel(22.0, 11.0, 3.2, 28)
    ring_lo = ring3(out, 0.0); ring_hi = ring3(out, 6.0)
    pc = Mesh(); loft(pc, [ring_lo, ring_hi], 'r11_op_rslab'); cap(pc, ring_hi, 'r11_op_rslab'); cap(pc, ring_lo, 'r11_op_rslab', up=False)
    pc.shade('r11_op_rslab', levels=4, light=LIGHT_SLAB)
    m.add(pc, R=rot_z(31) @ rot_x(6), offset=(-61.0, 8.0, 3.0))
    return m


def build():
    pod_materials(); slab_materials(); cube_materials(); housing_materials(); door_materials()
    save(door(), 'r11_op_door')
    save(housing(), 'p9_opening_housing_mesh_v1')
    build_small()
    save(opening_cube(), 'p9_opening_cube_metric_v3')
    save(to_model(pod_body()), 'p9_opening_bed_body_metric_v4')
    save(to_model(pod_cover()), 'p9_opening_bed_cover_metric_v4')
    save(to_model(pod_damage()), 'p9_opening_bed_damage_v5')
    save(slab(), 'p9_opening_slab_metric_v8')
    save(fg_broken_beam(), 'p9_foreground_broken_beam_v2')
    save(fg_angled_beam(), 'p9_foreground_angled_beam_v2')
    save(fg_rounded_slab(), 'p9_foreground_rounded_slab_v2')


# ------------------------------------------------------------------------------------------------ cube on the pile (11-12.8 s, left edge)
CUBE_S = 46.0
CUBE_LIFT = 9.0          # world units up (the placement is tilted: pitch 327.5, yaw 171, roll 337.7)


def opening_cube():
    """a weighted cube like the ascent cube (models/cube.py's generator), own materials, scaled to the film"""
    from models import cube as C
    from lib.mesh import angle_matrix
    Rw = angle_matrix(327.468677, 171.00375, 337.703231)
    up = Rw.T @ np.array([0, 0, 1.0])
    # the cube's own light: the film lights it from the camera side and above (world), expressed in model coordinates
    m = C.cube_mesh(CUBE_S, light=tuple(Rw.T @ np.array([0.45, -0.55, 0.70])))
    m.transform(offset=up * CUBE_LIFT)
    for t in m.tris:
        if t.mat.startswith('cube_'):
            t.mat = 'r11_op_' + t.mat
    return m


def cube_materials():
    ramp('r11_op_cube_c', (0.80, 0.80, 0.79), (0.55, 0.70, 0.85, 1.0))
    ramp('r11_op_cube_b', (0.52, 0.52, 0.52), (0.50, 0.68, 0.84, 1.0))
    ramp('r11_op_cube_d', (0.30, 0.30, 0.305), (0.45, 0.65, 0.82, 1.0))
    ramp('r11_op_cube_p', (0.86, 0.86, 0.85), (0.60, 0.74, 0.88, 1.0))
    mat('r11_op_cube_ring', (0.30, 0.30, 0.31))


# ------------------------------------------------------------------------------------------------ things on the floor
# bottles: lying (map roll 90), so their long axis is model +Z (cap end +Z for the front bottle); sizes from 18 s:
#   front bottle (white, cap toward the camera) radius 11.5, 43 long; back bottle (grey ribbed tin) radius 12.6, 36 long
def bottle_materials():
    ramp('r11_op_btl_w', (0.86, 0.86, 0.85), (0.30, 0.45, 0.62, 0.80, 1.0))
    ramp('r11_op_btl_g', (0.52, 0.52, 0.51), (0.35, 0.50, 0.66, 0.82, 1.0))
    mat('r11_op_btl_rib', (0.30, 0.30, 0.30))
    mat('r11_op_btl_cap', (0.18, 0.18, 0.18))
    mat('r11_op_black', (0.035, 0.035, 0.035))
    ramp('r11_op_blk', (0.22, 0.22, 0.22), (0.25, 0.45, 0.7, 1.0))
    ramp('r11_op_chip', (0.32, 0.31, 0.30), (0.25, 0.45, 0.7, 1.0))
    mat('r11_op_wire', (0.10, 0.10, 0.10))


def bottle_front():
    R, L = 11.5, 43.0
    z0 = -L * 0.5
    prof = [(z0, 0.0), (z0, R * 0.9), (z0 + 1.5, R), (L * 0.18, R), (L * 0.30, R * 0.93), (L * 0.40, R * 0.72), (L * 0.46, R * 0.40),
            (L * 0.46, 3.6), (L * 0.5, 3.6), (L * 0.5, 0.0)]
    m = Mesh()
    m.lathe(prof, 'r11_op_btl_w', n=20, axis='z')
    # faint ribs on the body
    for k in range(4):
        z = z0 + 5 + k * 6.5
        m.lathe([(z, R + 0.15), (z + 1.0, R + 0.15)], 'r11_op_btl_rib', n=20, axis='z')
    m.lathe([(L * 0.5 + 0.05, 0.0), (L * 0.5 + 0.05, 2.4)], 'r11_op_btl_cap', n=12, axis='z')
    m.shade('r11_op_btl_w', levels=5, light=(0.2, 0.9, 0.4))
    return m


def bottle_back():
    R, L = 12.6, 36.0
    z0 = -L * 0.5
    m = Mesh()
    m.lathe([(z0, 0.0), (z0, R * 0.92), (z0 + 1.2, R), (-z0 - 1.2, R), (-z0, R * 0.92), (-z0, 0.0)], 'r11_op_btl_g', n=20, axis='z')
    for k in range(6):
        z = z0 + 4 + k * 5.6
        m.lathe([(z, R + 0.2), (z + 1.2, R + 0.2)], 'r11_op_btl_rib', n=20, axis='z')
    m.shade('r11_op_btl_g', levels=5, light=(0.2, 0.9, 0.4))
    return m


def handset_back():
    """black rod lying on the floor (measured at 18 / 19.5 s): from (28, -1) to (-12, -12) relative to the map origin"""
    m = Mesh()
    m.tube((28.0, -1.0, -8.1), (-12.0, -12.0, -8.1), 3.2, 'r11_op_blk', n=8)
    m.shade('r11_op_blk', levels=4, light=(-0.4, -0.3, 0.85))
    return m


def handset_front():
    m = Mesh()
    m.tube((7.0, 8.0, 7.7), (12.0, 0.0, 8.2), 2.2, 'r11_op_blk', n=7)
    m.tube((12.0, 0.0, 8.2), (13.6, -9.0, 7.7), 2.2, 'r11_op_blk', n=7)
    m.shade('r11_op_blk', levels=4, light=(-0.4, -0.3, 0.85))
    return m


def rock(m, c, r, mat, seed, flat=0.7):
    """irregular dark fragment: a squashed, jittered icosphere-like blob"""
    rng = np.random.RandomState(seed)
    s = Mesh().sphere((0, 0, 0), 1.0, mat, n=7, m=5)
    jit = {}
    for t in s.tris:
        for i in range(3):
            key = tuple(np.round(t.p[i], 4))
            if key not in jit: jit[key] = 0.75 + 0.5 * rng.rand()
            t.p[i] = t.p[i] * jit[key] * np.array([r, r * 0.85, r * flat])
    s.flat()
    m.add(s, offset=c)
    return m


def chip(r, seed):
    m = Mesh(); rock(m, (0, 0, 0), r, 'r11_op_chip', seed)
    m.shade('r11_op_chip', levels=4, light=(0.0, 0.0, -1.0))      # seen from below: the faces toward the floor are the lit ones
    return m


def wire():
    """the cable that hangs from the ceiling over the pod (5-6.8 s): from the ceiling at world (-12765.9, -211, 269) to
    (-12840.9, -160.5, 150) (on the camera ray of the film's line at 6 s), relative to its map origin"""
    m = Mesh()
    m.tube((25.5, -9.6, 79.6), (-49.5, 40.9, -39.4), 0.55, 'r11_op_wire', n=5)
    return m


def build_small():
    bottle_materials()
    save(bottle_front(), 'p9_bottle_front_v2')
    save(bottle_back(), 'p9_bottle_back_v2')
    save(handset_back(), 'p9_handset_back_side_v3')
    save(handset_front(), 'p9_handset_front_v1')
    save(chip(5.5, 1), 'p9_joined_early_chip_0_v3')
    save(chip(2.0, 2), 'p9_joined_early_chip_1_v3')
    save(chip(3.8, 3), 'p9_joined_early_chip_2_v3')
    save(wire(), 'p9_joined_early_wire_v2')


# ------------------------------------------------------------------------------------------------ ceiling housing (10-11.3 s)
# The square recess with the round intake that the camera sees as it tips down at 10-11 s. Measured on the film at
# 10.34 s and 10.6 s (outline unprojected onto the ceiling z 274): square 137-145 across centred on world (-13066, -45),
# intake about 100-120 across; the map's ceiling hole for it is 151.7 square at (-13064.75, -40.15), which it fills. Placed by the map at (-13000, 0, 0), angles 0 (model = world + (13000, 0, 0)); the
# director tints it with the ceiling's exposure (scenes/opening.py) so it darkens with the ceiling as in the film.
HOUSING = dict(cx=-64.75, cy=-40.15, z=274.0, half=75.85, band=11.0, R=52.0, depth=60.0)   # fills the map's 151.7 square ceiling hole


def housing_materials():
    mat('r11_op_hs_band', (0.52, 0.52, 0.52))
    mat('r11_op_hs_band_side', (0.40, 0.40, 0.40))
    mat('r11_op_hs_inner', (0.30, 0.30, 0.30))
    ramp('r11_op_hs_wall', (0.50, 0.50, 0.50), (0.04, 0.10, 0.25, 0.55, 1.0))
    mat('r11_op_hs_top', (0.02, 0.02, 0.02))


def housing():
    h = HOUSING; m = Mesh()
    cx, cy, z0, a, b, R = h['cx'], h['cy'], h['z'], h['half'], h['band'], h['R']
    z1 = z0 + 3.0                     # band recessed 3 above the ceiling
    z2 = z0 + 7.0                     # inner square 7 above the ceiling
    # band: square ring facing down at z1, between half-size a and a-b; its outer side walls from the ceiling up
    sq = lambda s, z: [(cx - s, cy - s, z), (cx + s, cy - s, z), (cx + s, cy + s, z), (cx - s, cy + s, z)]
    o, i = sq(a, z1), sq(a - b, z1)
    for k in range(4):
        k2 = (k + 1) % 4
        m.quad('r11_op_hs_band', o[k], i[k], i[k2], o[k2])                     # faces -z (seen from below)
        oc = sq(a, z0)
        m.quad('r11_op_hs_band_side', oc[k], o[k], o[k2], oc[k2])              # side wall, faces inward
    # step up to the inner square
    i2 = sq(a - b, z2)
    for k in range(4):
        k2 = (k + 1) % 4
        m.quad('r11_op_hs_band_side', i[k], i2[k], i2[k2], i[k2])
    # inner square with the round intake: annulus-like fan between the square (a-b) and the circle R at z2
    N = 48
    s = a - b
    for j in range(N):
        t0 = 2 * PI * j / N; t1 = 2 * PI * (j + 1) / N
        def sqpt(t):
            c, sn = math.cos(t), math.sin(t); k = s / max(abs(c), abs(sn))
            return (cx + k * c, cy + k * sn, z2)
        p0 = (cx + R * math.cos(t0), cy + R * math.sin(t0), z2); p1 = (cx + R * math.cos(t1), cy + R * math.sin(t1), z2)
        m.quad('r11_op_hs_inner', sqpt(t0), p0, p1, sqpt(t1))
    # intake: cylinder wall (seen from inside / below), lit toward its far side, and a black top
    w = Mesh()
    for j in range(N):
        t0 = 2 * PI * j / N; t1 = 2 * PI * (j + 1) / N
        a0 = (cx + R * math.cos(t0), cy + R * math.sin(t0)); a1 = (cx + R * math.cos(t1), cy + R * math.sin(t1))
        w.quad('r11_op_hs_wall', (a0[0], a0[1], z2), (a0[0], a0[1], z2 + h['depth']), (a1[0], a1[1], z2 + h['depth']), (a1[0], a1[1], z2))
    w.shade('r11_op_hs_wall', levels=5, light=(0.75, -0.6, 0.0))     # the side away from the camera (+x, -y) is lit
    m.add(w)
    top = [(cx + R * math.cos(2 * PI * j / N), cy + R * math.sin(2 * PI * j / N), z2 + h['depth']) for j in range(N)]
    m.poly('r11_op_hs_top', top[::-1])                              # clockwise seen from above: faces down
    return m


# ------------------------------------------------------------------------------------------------ round door (11-15.5 s)
# The round door on the far wall under the exit signs. The map has a stock portaldoor.mdl there (scale 1.4) that the
# preview draws lying flat under the floor; this own model replaces it (scenes/opening.py) so preview and game agree.
# Film at 12.5 s: a disc of ~70 px (radius about 82 units at the wall, ~1100 away), light face, dark rim, a dark
# vertical split with a hub and two dark arcs ") (" on the halves. Model: face toward +X, centre at the origin.
def door_materials():
    mat('r11_op_door_face', (0.72, 0.72, 0.71))
    mat('r11_op_door_rim', (0.30, 0.30, 0.30))
    mat('r11_op_door_dark', (0.22, 0.22, 0.22))
    mat('r11_op_door_back', (0.10, 0.10, 0.10))


def door(R=82.0):
    m = Mesh()
    N = 48

    def disc(r0, r1, x, mat_, a0=0.0, a1=360.0, n=N):
        steps = max(1, int(round(n * (a1 - a0) / 360.0)))
        for k in range(steps):
            t0 = math.radians(a0 + (a1 - a0) * k / steps); t1 = math.radians(a0 + (a1 - a0) * (k + 1) / steps)
            p = [(x, r0 * math.cos(t0), r0 * math.sin(t0)), (x, r1 * math.cos(t0), r1 * math.sin(t0)),
                 (x, r1 * math.cos(t1), r1 * math.sin(t1)), (x, r0 * math.cos(t1), r0 * math.sin(t1))]
            # (radial x tangential) = +X: this order faces +X
            if r0 < 1e-6: m.tri(mat_, p[0], p[1], p[2])
            else: m.quad(mat_, *p)
    disc(0.0, R * 0.86, 0.0, 'r11_op_door_face')
    disc(R * 0.86, R, 0.0, 'r11_op_door_rim')
    # dark arcs ") (" on both halves, the split and the hub, slightly proud of the face
    for sgn in (1, -1):
        c = sgn * R * 0.05
        for k in range(10):
            a0 = math.radians(-50 + 10 * k); a1 = math.radians(-50 + 10 * (k + 1))
            r_in, r_out = R * 0.52, R * 0.60
            p = [(0.3, c + sgn * r_in * math.cos(a0), r_in * math.sin(a0)), (0.3, c + sgn * r_out * math.cos(a0), r_out * math.sin(a0)),
                 (0.3, c + sgn * r_out * math.cos(a1), r_out * math.sin(a1)), (0.3, c + sgn * r_in * math.cos(a1), r_in * math.sin(a1))]
            nrm = np.cross(np.subtract(p[1], p[0]), np.subtract(p[2], p[0]))
            if nrm[0] < 0: p = p[::-1]
            m.quad('r11_op_door_dark', *p)
    m.box((0.0, -1.2, -R * 0.86), (0.4, 1.2, R * 0.86), 'r11_op_door_dark')
    disc(0.0, R * 0.09, 0.5, 'r11_op_door_dark')
    # back (never seen) so the wall behind is not visible through the disc from odd angles
    b = Mesh(); b.lathe([(0.0, R), (-6.0, R), (-6.0, 0.0)], 'r11_op_door_back', n=24, axis='x')
    m.add(b)
    return m
