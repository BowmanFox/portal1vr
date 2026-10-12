"""Capsule / ending (film 3575-3965, 119.3-132.3 s): own textures, materials and models (prefix r11_cp).

Colours from the film's frames (HD, means of small patches): vault floor tiles grey 117-129 (tiles 41 units, 3623);
the pod's cushions and lid greys, white foot, blue ring (3616-3628); ceiling / shutter tiles brown (86 59 31, tiles
62 units, 3830 / 3840); the iris petals dark wood brown before the cut (88 58 22, 3730) and light orange-brown after
it (136 86 45, 3815-3820) with a light bevelled ring (132 95 62); the dark recess (32 14 10) with an orange light
strip; the flat light grey beyond the recess (151 136 139); concrete 149; the cracked glass of the lid traced from
3660. Textures are procedural (numpy): no video pixels.
Models (all placed and switched on / off in time by scenes/capsule.py): r11_cp_ashaft, r11_cp_atube (A1 shaft and
tube), r11_cp_pod, r11_cp_crack (the pod and its fracture: the LOST p9_end_capsule_glazing / p9_end_v4_capsule_fracture
rebuilt), r11_cp_concrete (A3), r11_cp_ceiling, r11_cp_strip, r11_cp_frame, r11_cp_petal(_dk), r11_cp_btube (B),
r11_cp_shutter, r11_cp_lamp, r11_cp_rim2 (the light object at the right of the picture in B)."""
import math
import numpy as np
from lib.gen import Mesh, V, mat, ramp, save, write_texture, rot_x, rot_y, rot_z

TEX = 256


def _blur(a, sx, sy):
    from scipy.ndimage import gaussian_filter
    return gaussian_filter(a, (sy, sx), mode='wrap')


def _noise(rng, n, sx, sy):
    a = _blur(rng.standard_normal((n, n)), sx, sy); return a / (a.std() + 1e-9)


def tiles_texture(base, grout, tiles=4, seed=1, var=6.0, n=TEX, grain=4.0):
    """n x n RGB: tiles x tiles square tiles of colour `base` (per-tile variation), joints `grout`"""
    rng = np.random.default_rng(seed); t = n // tiles
    img = np.zeros((n, n, 3)) + np.array(base, float)
    img += (_noise(rng, n, 5, 5) * grain)[..., None]
    for i in range(tiles):
        for j in range(tiles):
            img[i * t:(i + 1) * t, j * t:(j + 1) * t] *= 1.0 + rng.normal(0, var / 100.0)
    for k in range(tiles):
        for w in (0, 1):
            img[(k * t + w) % n, :] = grout; img[:, (k * t + w) % n] = grout
    return np.clip(img, 0, 255).astype(np.uint8)


def rust_texture(seed=3, n=TEX):
    """shaft wall: dark grey-brown streaked metal with an orange vertical stripe (stripes along texture v)"""
    rng = np.random.default_rng(seed)
    streak = _noise(rng, n, 1.0, 30); big = _noise(rng, n, 20, 40); fine = _noise(rng, n, 2, 2)
    v = 0.45 + 0.12 * big + 0.05 * streak + 0.04 * fine
    dark = np.array([72.0, 66.0, 62.0]); light = np.array([170.0, 156.0, 144.0])
    img = dark[None, None] * (1 - v[..., None]) + light[None, None] * v[..., None]
    img[:, 12:22] = np.array([200.0, 90.0, 50.0]) * (0.85 + 0.1 * fine[:, 12:22, None])      # orange stripe
    img[:, 22:26] *= 0.5
    return np.clip(img, 0, 255).astype(np.uint8)


def concrete_texture(seed=7, n=TEX):
    rng = np.random.default_rng(seed)
    v = 149 + 9 * _noise(rng, n, 1.2, 1.2) + 6 * _noise(rng, n, 10, 10)
    return np.repeat(np.clip(v, 0, 255)[..., None], 3, axis=2).astype(np.uint8)


def textures():
    write_texture('corehub_intro/r11_cp_floortex', tiles_texture((124, 128, 130), (88, 90, 92), 4, seed=2, var=7))
    write_texture('corehub_intro/r11_cp_woodtex', tiles_texture((88, 59, 30), (50, 32, 15), 4, seed=4, var=5, grain=2.5))
    write_texture('corehub_intro/r11_cp_rusttex', rust_texture())
    write_texture('corehub_intro/r11_cp_concretetex', concrete_texture())


def brush_materials():
    textures()
    mat('r11_cp_black', (0.01, 0.01, 0.01), folder='corehub_intro', model=False)       # the cell's shell


def materials():
    brush_materials()
    mat('r11_cp_rail', (0.035, 0.035, 0.04))
    # collars of the descent tube: wide dark translucent bands (film 3600-3612: dark grey rings over the walls)
    mat('r11_cp_col', (0.12, 0.12, 0.12), alpha=0.50, translucent=True, nocull=True)
    mat('r11_cp_col_rim', (0.08, 0.08, 0.08), alpha=0.80, translucent=True, nocull=True)
    mat('r11_cp_col_lt', (0.42, 0.42, 0.42), alpha=0.5, translucent=True, nocull=True)
    mat('r11_cp_glass', (0.55, 0.56, 0.57), alpha=0.12, translucent=True, nocull=True)
    # the pod
    ramp('r11_cp_shell', (0.74, 0.75, 0.74), (0.55, 0.75, 0.9, 1.0))
    mat('r11_cp_lid', (0.45, 0.46, 0.46))
    mat('r11_cp_lid_edge', (0.12, 0.12, 0.12))
    mat('r11_cp_cushion', (0.56, 0.57, 0.57))
    mat('r11_cp_cushion_dk', (0.42, 0.43, 0.43))
    mat('r11_cp_foot', (0.93, 0.93, 0.92))
    mat('r11_cp_blue', (0.30, 0.78, 0.92))
    mat('r11_cp_crack', (0.95, 0.96, 0.97), alpha=0.38, translucent=True, nocull=True)
    mat('r11_cp_crack2', (0.90, 0.92, 0.93), alpha=0.26, translucent=True, nocull=True)
    mat('r11_cp_crack3', (0.97, 0.96, 0.90), alpha=0.75, translucent=True, nocull=True)
    # ceiling iris
    mat('r11_cp_petal', (0.55, 0.36, 0.20))
    mat('r11_cp_petal_dk', (0.345, 0.227, 0.086))
    mat('r11_cp_petal_ring', (0.52, 0.37, 0.24))
    mat('r11_cp_petal_ring_lt', (0.78, 0.70, 0.58))
    mat('r11_cp_strut', (0.22, 0.12, 0.06))
    mat('r11_cp_hub', (0.30, 0.15, 0.07))
    mat('r11_cp_green', (0.25, 0.75, 0.45))
    mat('r11_cp_frame', (0.40, 0.39, 0.38))
    mat('r11_cp_frame_lt', (0.55, 0.53, 0.51))
    mat('r11_cp_frame_out', (0.30, 0.26, 0.22))
    mat('r11_cp_frame_dk', (0.30, 0.29, 0.29))
    mat('r11_cp_wood_m', (1.0, 1.0, 1.0), base='corehub_intro/r11_cp_woodtex')
    mat('r11_cp_rust_m', (1.0, 1.0, 1.0), base='corehub_intro/r11_cp_rusttex')
    mat('r11_cp_rustdk_m', (0.40, 0.40, 0.40), base='corehub_intro/r11_cp_rusttex')
    mat('r11_cp_floor_m', (1.0, 1.0, 1.0), base='corehub_intro/r11_cp_floortex')
    mat('r11_cp_concrete_m', (1.0, 1.0, 1.0), base='corehub_intro/r11_cp_concretetex')
    mat('r11_cp_beige_m', (0.12, 0.08, 0.05))
    mat('r11_cp_recess', (0.10, 0.08, 0.06))
    mat('r11_cp_light', (0.68, 0.68, 0.68))
    mat('r11_cp_trim_w', (0.85, 0.85, 0.84))
    mat('r11_cp_recess_y', (0.62, 0.62, 0.62))
    mat('r11_cp_orange', (0.95, 0.38, 0.16))
    mat('r11_cp_trim', (0.35, 0.33, 0.31))
    mat('r11_cp_endring', (0.10, 0.10, 0.10))
    mat('r11_cp_endring_in', (0.05, 0.05, 0.05))
    mat('r11_cp_btube', (0.56, 0.55, 0.55))
    mat('r11_cp_bring', (0.86, 0.85, 0.85))
    mat('r11_cp_bring_dk', (0.20, 0.20, 0.20))
    mat('r11_cp_black_m', (0.02, 0.02, 0.02))
    mat('r11_cp_shut_edge', (0.10, 0.07, 0.04))
    mat('r11_cp_lamp', (0.70, 0.62, 0.52))
    mat('r11_cp_lamp_rim', (0.03, 0.03, 0.03))
    ramp('r11_cp_rimw', (0.86, 0.86, 0.87), (0.16, 0.22, 0.32, 0.48, 0.72, 1.0))
    ramp('r11_cp_rimg', (0.72, 0.72, 0.73), (0.03, 0.06, 0.12, 0.25, 0.50, 1.0))


def ring_z(m, z, r0, r1, material, n=32, a0=0.0, a1=360.0, up=False):
    """flat annulus in the plane Z = z facing -Z (up=False) or +Z"""
    k = max(1, int(round(n * (a1 - a0) / 360.0)))
    for i in range(k):
        b0 = math.radians(a0 + (a1 - a0) * i / k); b1 = math.radians(a0 + (a1 - a0) * (i + 1) / k)
        q = [V(r0 * math.cos(b0), r0 * math.sin(b0), z), V(r1 * math.cos(b0), r1 * math.sin(b0), z),
             V(r1 * math.cos(b1), r1 * math.sin(b1), z), V(r0 * math.cos(b1), r0 * math.sin(b1), z)]
        if up: m.quad(material, *q)
        else: m.quad(material, *q[::-1])
    return m


def wall_z(m, z0, z1, r, material, n=32, inward=True):
    for i in range(n):
        b0 = 2 * math.pi * i / n; b1 = 2 * math.pi * (i + 1) / n
        q = [V(r * math.cos(b0), r * math.sin(b0), z0), V(r * math.cos(b1), r * math.sin(b1), z0),
             V(r * math.cos(b1), r * math.sin(b1), z1), V(r * math.cos(b0), r * math.sin(b0), z1)]
        if inward: m.quad(material, *q[::-1])
        else: m.quad(material, *q)
    return m


# ------------------------------------------------------------------------------------------------ tube
COLLAR_R = 61.06


def collar(h=12.0):
    """descent-tube collar about model +Z: a dark translucent band (film 3600-3612: dark rings every ~75 units near
    the end of the tube, radii 60-250 px at 3606) with a darker rim"""
    m = Mesh(); R = COLLAR_R
    wall_z(m, -h, h, R, 'r11_cp_col', n=24, inward=True)
    ring_z(m, -h, 0.78 * R, R, 'r11_cp_col_rim', n=24, up=False)
    ring_z(m, h, 0.78 * R, R, 'r11_cp_col_rim', n=24, up=True)
    return m


def tube_glass(length=1400.0, R=58.0):
    m = Mesh(); wall_z(m, 0.0, length, R, 'r11_cp_glass', n=24, inward=True); return m


# ------------------------------------------------------------------------------------------------ the pod
POD_L = 176.0       # along model +X (head at +X); film 3616-3628: length / width 2.1-2.2
POD_W = 80.0
POD_H = 100.0       # shell rim above the floor: the camera stops 32 above it (film 3616-3628: 1/width -> 0 at 3631)


def stadium(L, W, n=10):
    """outline of a rounded rectangle (semicircle ends) along X, counter-clockwise"""
    r = W / 2.0; c = L / 2.0 - r; pts = []
    for k in range(n + 1):
        a = -math.pi / 2 + math.pi * k / n; pts.append((c + r * math.cos(a), r * math.sin(a)))
    for k in range(n + 1):
        a = math.pi / 2 + math.pi * k / n; pts.append((-c + r * math.cos(a), r * math.sin(a)))
    return pts


def _ring_prism(m, outer, inner, z, material):
    """flat band between two outlines with the same number of points (facing +Z)"""
    for k in range(len(outer)):
        a, b = outer[k], outer[(k + 1) % len(outer)]; c, d = inner[(k + 1) % len(inner)], inner[k]
        m.quad(material, V(a[0], a[1], z), V(b[0], b[1], z), V(c[0], c[1], z), V(d[0], d[1], z))


def pod():
    """the vault pod seen from above (film 3600-3631): grey shell, dark glass lid with three cushions, white foot
    with a blue ring at -X"""
    m = Mesh()
    outer = stadium(POD_L, POD_W, 12)
    m.prism(outer, 0.0, POD_H - 4, 'r11_cp_shell', top='r11_cp_shell')
    m.shade('r11_cp_shell', levels=4, light=(0.2, -0.3, 0.93))
    lid = stadium(POD_L - 14, POD_W - 12, 12)
    m.prism(lid, POD_H - 4, POD_H, 'r11_cp_lid_edge', top='r11_cp_lid')
    # cushions (film 3624-3631): a big rounded head cushion at +X, two body cushions below it
    zc = POD_H + 0.6
    head = [(x * 0.70 + 40, y * 0.82) for x, y in stadium(50, 52, 8)]
    m.poly('r11_cp_cushion', [(x, y, zc) for x, y in head])
    m.poly('r11_cp_cushion_dk', [(x, y, zc - 0.3) for x, y in [(x * 0.76 + 40, y * 0.90) for x, y in stadium(52, 54, 8)]])
    for x0, x1 in ((-2, 20), (-26, -5)):
        m.poly('r11_cp_cushion', [(x0, -23, zc), (x1, -23, zc), (x1, 23, zc), (x0, 23, zc)])
        m.poly('r11_cp_cushion_dk', [(x1 - 2.0, -23, zc + 0.3), (x1, -23, zc + 0.3), (x1, 23, zc + 0.3), (x1 - 2.0, 23, zc + 0.3)])
    # white foot block and blue ring at the -X end
    foot = [(x - POD_L / 2 + 28, y) for x, y in stadium(56, POD_W + 4, 10) if x <= 0.5]
    m.prism(foot, 0.0, POD_H + 2, 'r11_cp_foot', top='r11_cp_foot')
    ring = [(x - POD_L / 2 + 26, y * 1.02) for x, y in stadium(60, POD_W + 10, 10) if x <= -14]
    m.prism(ring, 0.0, POD_H - 14, 'r11_cp_blue', top='r11_cp_blue')
    return m


CRACK_LINES = [   # (width px, alpha level 0/1/2, [(px, py), ...]) traced from the film's cracked glass (3660)
    (14, 2, [(10, 222), (40, 227), (100, 240), (200, 252), (300, 255), (400, 250), (460, 240), (520, 232)]),   # bright rim streak
    (24, 0, [(0, 70), (60, 74), (120, 82), (180, 96), (230, 100), (290, 86)]),
    (16, 1, [(0, 130), (60, 140), (130, 146), (190, 150), (250, 130), (290, 92)]),
    (18, 0, [(330, 165), (390, 100), (470, 52), (560, 30), (640, 18)]),
    (16, 1, [(330, 165), (420, 140), (520, 112), (600, 120), (650, 130)]),
    (18, 0, [(330, 165), (440, 200), (500, 228), (560, 250), (650, 272)]),
    (14, 1, [(330, 165), (280, 200), (230, 216), (170, 240)]),
    (18, 0, [(150, 240), (120, 300), (90, 350), (40, 410)]),
    (16, 1, [(230, 250), (200, 320), (180, 410)]),
    (12, 1, [(290, 320), (250, 410)]),
    (12, 1, [(180, 96), (180, 130), (200, 150)]),
    (10, 1, [(470, 52), (520, 90), (600, 120)]),
]


def cracks(depth=7.0):
    """the cracked glass right under the stopped camera (A2): white translucent jagged bands, model coordinates of a
    camera looking down -Z with the picture's up = +X (picture right = -Y), `depth` below it"""
    m = Mesh(); F = 461.88
    def w(px, py): return np.array([-(py - 199.5) / F * depth, -(px - 319.5) / F * depth])
    lines = list(CRACK_LINES) + [(wid * 0.7, 1, [(x + 7, y - 6) for x, y in pts]) for wid, lev, pts in CRACK_LINES if lev == 0]
    for wid, lev, pts in lines:
        mtl = ('r11_cp_crack', 'r11_cp_crack2', 'r11_cp_crack3')[lev]
        P = [w(*q) for q in pts]; hw = wid / 2.0 / F * depth
        for a, b in zip(P, P[1:]):
            d = b - a; n = np.array([-d[1], d[0]]) / (np.linalg.norm(d) + 1e-9) * hw
            m.quad(mtl, V(a[0] - n[0], a[1] - n[1], 0), V(b[0] - n[0], b[1] - n[1], 0), V(b[0] + n[0], b[1] + n[1], 0), V(a[0] + n[0], a[1] + n[1], 0))
    return m


# ------------------------------------------------------------------------------------------------ ceiling iris
PET = 134.0        # half size of the closed iris square (petal = PET x PET)
RING_R = 124.0     # bevelled ring on the petals (film: R 117-131 from 3772 / 3800 / 3830)


def petal(face='r11_cp_petal'):
    """one petal in the +X+Y quadrant, corner on the axis, face toward -Z (seen from below) at z = 0
    (film: dark wood brown before the cut (3730: 88 58 22), light orange-brown after it (3820: 136 86 45))"""
    m = Mesh(); P = PET
    m.quad(face, V(0, 0, 0), V(0, P, 0), V(P, P, 0), V(P, 0, 0))                         # faces -Z
    m.box((0, 0, 0.1), (P, P, 3.0), face, mats={'-z': None})
    ring_z(m, -0.6, RING_R - 20, RING_R, 'r11_cp_petal_ring', n=40, a0=0, a1=90)        # film 3815: band ~19 units
    ring_z(m, -0.8, RING_R - 8, RING_R - 4, 'r11_cp_petal_ring_lt', n=40, a0=0, a1=90)
    ring_z(m, -0.6, 0.0, 30.0, 'r11_cp_hub', n=40, a0=0, a1=90)
    ring_z(m, -1.0, 0.0, 6.0, 'r11_cp_green', n=40, a0=0, a1=90)
    # diagonal strut to the corner, a bolt bar across its end
    d = np.array([1, 1, 0]) / math.sqrt(2); nn = np.array([-1, 1, 0]) / math.sqrt(2)
    for a, b, w in ((26.0, 1.42 * P, 3.2),):
        A = d * a; B = d * b
        m.quad('r11_cp_strut', V(*(A - nn * w + [0, 0, -1.5])), V(*(A + nn * w + [0, 0, -1.5])), V(*(B + nn * w + [0, 0, -1.5])), V(*(B - nn * w + [0, 0, -1.5])))
    E = d * (1.36 * P)
    m.quad('r11_cp_strut', V(*(E - nn * 12 - d * 2.5 + [0, 0, -1.6])), V(*(E - nn * 12 + d * 2.5 + [0, 0, -1.6])), V(*(E + nn * 12 + d * 2.5 + [0, 0, -1.6])), V(*(E + nn * 12 - d * 2.5 + [0, 0, -1.6])))
    # seams (dark edges)
    m.quad('r11_cp_strut', V(0, 0, -0.4), V(P, 0, -0.4), V(P, 1.2, -0.4), V(0, 1.2, -0.4))
    m.quad('r11_cp_strut', V(1.2, 0, -0.4), V(1.2, P, -0.4), V(0, P, -0.4), V(0, 0, -0.4))
    return m


def frame_ring():
    """dark ring round the tube mouth above the petals with four green lights on the diagonals (film 3716-3750)"""
    m = Mesh()
    ring_z(m, 0.0, 66.0, 101.0, 'r11_cp_frame_dk', n=40)
    ring_z(m, -0.2, 101.0, 134.0, 'r11_cp_frame', n=40)
    ring_z(m, -0.4, 126.0, 134.0, 'r11_cp_frame_lt', n=40)
    wall_z(m, 0.0, 30.0, 66.0, 'r11_cp_frame_dk', n=40, inward=True)
    for k in range(4):
        a = math.radians(45 + 90 * k); c = np.array([math.cos(a), math.sin(a)]) * 87
        m.add(ring_z(Mesh(), -0.8, 0.0, 7.0, 'r11_cp_green', n=12), offset=(c[0], c[1], 0))
    return m


def frame_out():
    """grey-brown ring round the frame that fills the open petals' gap out to the recess (film 3730-3746); switched
    off once the iris is closed (the margin round the closed petals is the dark recess, film 3800-3830)"""
    m = Mesh(); ring_z(m, 0.0, 134.0, 192.0, 'r11_cp_frame_out', n=40); return m


def lamp():
    """the round lamp on the shutter (film 3850-3950): beige disc in a black ring, facing -Z"""
    m = Mesh()
    ring_z(m, -1.0, 0.0, 26.0, 'r11_cp_lamp', n=32)
    ring_z(m, -0.5, 26.0, 32.0, 'r11_cp_lamp_rim', n=32)
    wall_z(m, -1.0, 0.0, 26.0, 'r11_cp_lamp_rim', n=32, inward=False)
    return m


SH_L = 1400.0
SH_W = 810.0       # +Y edge at y 13110 (film 3860-3930: the edge with its white trim at x 440-455)


def shutter():
    """the vault shutter: a tiled panel (tiles 62 units, like the ceiling), face toward -Z, leading edge at +X;
    origin at its -X -Y bottom corner"""
    m = Mesh()
    m.box((0, 0, 0), (SH_L, SH_W, 16.0), 'r11_cp_wood_m', mats={'+x': 'r11_cp_shut_edge', '-x': 'r11_cp_shut_edge', '+y': 'r11_cp_trim_w'})   # face (-Z) at z = 0
    m.uv_box(scale=248.0, only=['r11_cp_wood_m'])
    m.quad('r11_cp_trim_w', V(SH_L, SH_W - 5.0, -0.3), V(0, SH_W - 5.0, -0.3), V(0, SH_W - 2.5, -0.3), V(SH_L, SH_W - 2.5, -0.3))
    return m


def a_shaft(W=204.0, z0=0.0, z1=2050.0, zsplit=650.0):
    """A1 shaft (origin at the floor centre): four inward rust walls with orange stripes along Z (lit below zsplit,
    dark above) and the floor (lit tiles); single-sided so that nothing of it is seen from outside"""
    m = Mesh()
    for (za, zb, mt) in ((z0, zsplit, 'r11_cp_rust_m'), (zsplit, z1, 'r11_cp_rustdk_m')):
        m.quad(mt, V(W, -W, zb), V(W, W, zb), V(W, W, za), V(W, -W, za))            # +x wall, faces -x (inward)
        m.quad(mt, V(-W, W, zb), V(-W, -W, zb), V(-W, -W, za), V(-W, W, za))
        m.quad(mt, V(W, W, zb), V(-W, W, zb), V(-W, W, za), V(W, W, za))            # +y wall, faces -y
        m.quad(mt, V(-W, -W, zb), V(W, -W, zb), V(W, -W, za), V(-W, -W, za))
    m.quad('r11_cp_floor_m', V(-W, -W, 0), V(W, -W, 0), V(W, W, 0), V(-W, W, 0))
    m.uv_box(scale=256.0, only=['r11_cp_rust_m', 'r11_cp_rustdk_m'])
    m.uv_box(scale=164.0, only=['r11_cp_floor_m'])        # tiles 41 units (film 3623: 60 px at depth 317)
    return m


def a_tube(z_end=0.0, length=1850.0, collars=tuple(16.0 + 112.0 * k for k in range(16))):
    """A1 tube (origin at its lower end ring, axis +Z): four rails, dark collars, the end ring (inner R 51)"""
    m = Mesh(); rho = 34.0; w = 0.9
    for sx in (1, -1):
        for sy in (1, -1):
            c = np.array([sx, sy]) * rho / math.sqrt(2)
            m.box((c[0] - w, c[1] - w, 0.0), (c[0] + w, c[1] + w, length), 'r11_cp_rail')
    for z in collars:
        m.add(collar(), offset=(0, 0, z))
    ring_z(m, -1.0, 51.0, 96.0, 'r11_cp_endring', n=32)
    ring_z(m, -0.5, 96.0, 104.0, 'r11_cp_col_rim', n=32)
    wall_z(m, -1.0, 30.0, 51.0, 'r11_cp_endring_in', n=32, inward=True)
    m.add(tube_glass(length, 58.0))
    return m


def a_shaft_wrap():
    return a_shaft(zsplit=1.0)                # dim rust all the way (film 119.6-120.5: dark walls round the collars)


def b_tube(length=1500.0, R=61.0):
    """the tube above the ceiling iris as seen from below (A4 / B1), axis model +Z: dark inside with lighter
    rings every 110 units, four rails, a dark far end"""
    m = Mesh(); rho = 34.0; w = 1.0
    wall_z(m, 0.0, length, R, 'r11_cp_btube', n=24, inward=True)
    for k in range(1, int(length // 110)):
        z = k * 110.0
        wall_z(m, z, z + 14.0, R - 0.5, 'r11_cp_bring', n=24, inward=True)
        ring_z(m, z, R - 9, R, 'r11_cp_bring_dk', n=24)
    for sx in (1, -1):
        for sy in (1, -1):
            c = np.array([sx, sy]) * rho / math.sqrt(2)
            m.box((c[0] - w, c[1] - w, 0.0), (c[0] + w, c[1] + w, length), 'r11_cp_rail')
    ring_z(m, length, 0.0, R, 'r11_cp_black_m', n=24)
    return m


def ceiling(W=1300.0, rec=185.0, z_tiles=0.0, z_panel=42.0, hole=61.0, strip=True):
    """the vault ceiling seen from below (origin at the hub's x, y and the tiles' z): tiles with a square recess
    (dark inner walls, an orange light strip on the +Y wall, a beige back panel with the tube hole)"""
    m = Mesh(); zt = z_tiles; zp = z_panel
    # brown tiles, except beyond the recess on the +Y side (picture right): a flat light grey surface (film 3800: pink
    # in the red light right of the recess's orange strip; 3880-3930: light grey right of the shutter's edge)
    for (a, b, mt) in (((-W, -W), (W, -rec), 'r11_cp_wood_m'), ((-W, -rec), (-rec, rec), 'r11_cp_wood_m'),
                       ((rec, -rec), (W, rec), 'r11_cp_wood_m'), ((-W, rec), (W, W), 'r11_cp_light')):
        m.quad(mt, V(a[0], a[1], zt), V(a[0], b[1], zt), V(b[0], b[1], zt), V(b[0], a[1], zt))   # faces -Z
    m.uv_box(scale=248.0, only=['r11_cp_wood_m'])
    # recess walls (inward)
    m.quad('r11_cp_recess', V(rec, -rec, zp), V(rec, rec, zp), V(rec, rec, zt), V(rec, -rec, zt))         # inward
    m.quad('r11_cp_recess', V(-rec, rec, zp), V(-rec, -rec, zp), V(-rec, -rec, zt), V(-rec, rec, zt))
    m.quad('r11_cp_recess_y', V(rec, rec, zp), V(-rec, rec, zp), V(-rec, rec, zt), V(rec, rec, zt))
    m.quad('r11_cp_recess', V(-rec, -rec, zp), V(rec, -rec, zp), V(rec, -rec, zt), V(-rec, -rec, zt))
    if strip == 'only':
        m = Mesh()
    if strip:
        m.quad('r11_cp_orange', V(rec - 12, rec - 0.5, zp - 6), V(-rec + 12, rec - 0.5, zp - 6), V(-rec + 12, rec - 0.5, zt + 6), V(rec - 12, rec - 0.5, zt + 6))
    # back panel with a round hole (faces -Z)
    n = 32
    for k in range(n):
        a0 = 2 * math.pi * k / n; a1 = 2 * math.pi * (k + 1) / n
        def sq(a):
            c, s_ = math.cos(a), math.sin(a); t = rec / max(abs(c), abs(s_)); return (c * t, s_ * t)
        p0 = (hole * math.cos(a0), hole * math.sin(a0)); p1 = (hole * math.cos(a1), hole * math.sin(a1))
        q0 = sq(a0); q1 = sq(a1)
        m.quad('r11_cp_beige_m', V(p0[0], p0[1], zp), V(p1[0], p1[1], zp), V(q1[0], q1[1], zp), V(q0[0], q0[1], zp))
    return m


def concrete_wall(L=900.0, z0=-150.0, z1=330.0):
    """A3: the concrete wall the camera turns past (plane y = 0 facing -Y, origin at its centre), a dark trim near
    the top"""
    m = Mesh()
    m.quad('r11_cp_concrete_m', V(-L, 0, z0), V(L, 0, z0), V(L, 0, z1), V(-L, 0, z1))
    m.uv_box(scale=180.0, only=['r11_cp_concrete_m'])
    m.quad('r11_cp_trim', V(-L, -0.5, z1 - 22), V(L, -0.5, z1 - 22), V(L, -0.5, z1 - 14), V(-L, -0.5, z1 - 14))
    return m


def rim_cyl(L=520.0, R=62.0, light=(0.0, 0.55, -0.83), mat_='r11_cp_rimw'):
    """the light curved object at the right of the picture in B (axis model +X): shaded cylinder, outward faces
    (film 3757-3950: dark grey at its left edge, white toward the right)"""
    m = Mesh(); n = 32
    for k in range(n):
        a0 = 2 * math.pi * k / n; a1 = 2 * math.pi * (k + 1) / n
        q = [V(-L / 2, R * math.cos(a0), R * math.sin(a0)), V(L / 2, R * math.cos(a0), R * math.sin(a0)),
             V(L / 2, R * math.cos(a1), R * math.sin(a1)), V(-L / 2, R * math.cos(a1), R * math.sin(a1))]
        m.quad(mat_, *q[::-1])
    m.shade(mat_, levels=6, light=light)
    return m


def build():
    materials()
    save(pod(), 'r11_cp_pod')
    save(cracks(), 'r11_cp_crack')
    save(petal(), 'r11_cp_petal')
    save(petal('r11_cp_petal_dk'), 'r11_cp_petal_dk')
    save(frame_ring(), 'r11_cp_frame')
    save(frame_out(), 'r11_cp_frameout')
    save(lamp(), 'r11_cp_lamp')
    save(shutter(), 'r11_cp_shutter')
    save(rim_cyl(light=(0.0, 0.85, -0.5), mat_='r11_cp_rimg'), 'r11_cp_rim2')   # carried with the camera: light at its left edge, dark to the right
    save(a_shaft_wrap(), 'r11_cp_ashaft')
    save(a_tube(), 'r11_cp_atube')
    save(b_tube(), 'r11_cp_btube')
    save(ceiling(strip=False), 'r11_cp_ceiling')
    save(ceiling(strip='only'), 'r11_cp_strip')
    save(concrete_wall(), 'r11_cp_concrete')
