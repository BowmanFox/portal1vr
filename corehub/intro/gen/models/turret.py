"""Turret / "16" part (64.0-73.97 s, film frames 1918-2217): own textures, materials and devices (prefix r11_tu).

Textures are procedural (numpy / cv2 drawing), coloured from the film's samples (no video pixels):
  rust walls: frames 2058, 2070, 2188 (walls seen frontally): dark parts ~(53 53 55), mean (75 70 68), rusty parts
    ~(113 101 94); vertical panel seams, horizontal seams ~ every panel height
  grey platform walls 105 (2028-2034), grey slabs 66 (2176), dark floor 37-44 (2020, 1980), black gaps 15 (2188)
  the "16" sign: white card (~232) with a black "16", a rule and a row of small icons (2184, 2192)
Brush materials: materials/corehub_intro/r11_tu_*.vmt (UnlitGeneric); the models' materials in models/corehub_intro."""
import math
import numpy as np
from lib.gen import Mesh, V, mat, ramp, save, write_texture, rot_x, rot_y, rot_z

TEX = 512
PANEL_W = 300.0          # world units per rust panel (horizontal)
PANEL_H = 300.0          # world units per rust panel (vertical)
TEX_PANELS = (2, 2)      # panels per texture repeat (u, v)
WALL = 'corehub_intro/r11_tu_wall'
WALL_DIM = 'corehub_intro/r11_tu_wall_dim'
WALL_DARK = 'corehub_intro/r11_tu_wall_dark'
WALL_A1 = 'corehub_intro/r11_tu_wall_a1'
WALL_B = 'corehub_intro/r11_tu_wall_b'
GREY = 'corehub_intro/r11_tu_grey'
GREY_MID = 'corehub_intro/r11_tu_grey_mid'
GREY_DARK = 'corehub_intro/r11_tu_grey_dark'
FLOOR = 'corehub_intro/r11_tu_floor'
BLACK = 'corehub_intro/r11_tu_black'
SIGN = 'corehub_intro/r11_tu_sign'


def _blur(a, sx, sy):
    from scipy.ndimage import gaussian_filter
    return gaussian_filter(a, (sy, sx), mode='wrap')


def rust_texture(seed=23):
    """512x512 RGB: 2 x 2 panels of grey-brown metal, fine vertical streaks of orange rust (the film's walls:
    2058, 2188: dark ~52, mean ~72, rusty ~110), light seams at the panel edges"""
    rng = np.random.default_rng(seed)
    n = TEX; pw = n // TEX_PANELS[0]; ph = n // TEX_PANELS[1]
    streak = _blur(rng.standard_normal((n, n)), 0.8, 22); streak /= streak.std()
    streak2 = _blur(rng.standard_normal((n, n)), 2.5, 40); streak2 /= streak2.std()
    blot = _blur(rng.standard_normal((n, n)), 10, 14); blot /= blot.std()
    fine = _blur(rng.standard_normal((n, n)), 0.6, 2); fine /= fine.std()
    bias = np.zeros((n, n))
    for i in range(TEX_PANELS[0]):
        for j in range(TEX_PANELS[1]):
            bias[j * ph:(j + 1) * ph, i * pw:(i + 1) * pw] = rng.normal(0.0, 0.25)
    yy = (np.arange(n)[:, None] % ph) / ph
    band = 0.35 * np.exp(-((yy - 0.25) / 0.12) ** 2) - 0.15
    r = 0.45 * streak + 0.35 * streak2 + 0.25 * blot + 0.12 * fine + bias + band
    rust = np.clip((r - 0.2) / 1.3, 0, 1)
    dark = np.array([48.0, 48.0, 50.0]); mid = np.array([74.0, 71.0, 70.0]); orange = np.array([132.0, 104.0, 82.0])
    base_t = np.clip(0.5 + 0.28 * streak2 + 0.22 * fine + 0.15 * blot, 0, 1)
    base = dark[None, None, :] * (1 - base_t[..., None]) + mid[None, None, :] * base_t[..., None]
    img = base * (1 - 0.8 * rust[..., None]) + orange[None, None, :] * 0.8 * rust[..., None]
    img *= (0.86 + 0.14 * np.clip(streak[..., None] * 0.5 + 1, 0, 1.4))
    for i in range(TEX_PANELS[0]):
        x = i * pw
        img[:, x % n, :] = img[:, x % n, :] * 0.4 + np.array([98.0, 95.0, 92.0]) * 0.6
        img[:, (x + 1) % n, :] *= 0.55
    for j in range(TEX_PANELS[1]):
        y = j * ph
        img[y % n, :, :] = img[y % n, :, :] * 0.4 + np.array([104.0, 100.0, 96.0]) * 0.6
        img[(y + 1) % n, :, :] *= 0.5
        img[(y + 2) % n, :, :] *= 0.75
    return np.clip(img * 1.13, 0, 255).astype(np.uint8)


def sign_texture():
    """256x256 test chamber sign: white card, black "16", a rule, a row of small pictograms, a small logo"""
    import cv2
    n = 256
    img = np.full((n, n, 3), 236, np.uint8)
    cv2.rectangle(img, (0, 0), (n - 1, n - 1), (205, 205, 205), 3)
    cv2.putText(img, '16', (58, 118), cv2.FONT_HERSHEY_SIMPLEX, 3.6, (22, 22, 22), 13, cv2.LINE_AA)
    cv2.line(img, (30, 152), (240, 152), (60, 60, 60), 2)
    cv2.line(img, (30, 158), (190, 158), (110, 110, 110), 3)
    for k in range(5):
        x = 30 + 42 * k
        c = (70, 70, 70) if k in (0, 1, 3) else (200, 200, 200)
        cv2.rectangle(img, (x, 178), (x + 32, 204), c, 2)
        cv2.circle(img, (x + 16, 191), 7, c, -1 if k in (1, 3) else 2)
    cv2.ellipse(img, (48, 232), (14, 6), 0, 0, 360, (90, 90, 90), 2)
    return img


def textures():
    write_texture('corehub_intro/r11_tu_rusttex', rust_texture())
    write_texture('corehub_intro/r11_tu_signtex', sign_texture(), clamp=True)


def brush_materials():
    base = 'corehub_intro/r11_tu_rusttex'
    mat('r11_tu_wall', (1.0, 1.0, 1.0), base=base, folder='corehub_intro', model=False)
    mat('r11_tu_wall_dim', (0.80, 0.80, 0.80), base=base, folder='corehub_intro', model=False)
    mat('r11_tu_wall_dark', (0.55, 0.55, 0.55), base=base, folder='corehub_intro', model=False)
    mat('r11_tu_wall_a1', (0.50, 0.50, 0.50), base=base, folder='corehub_intro', model=False)     # 1960 / 1990: p50 31-33
    mat('r11_tu_wall_b', (0.92, 0.92, 0.92), base=base, folder='corehub_intro', model=False)      # 2188: p50 61
    mat('r11_tu_grey', (0.412, 0.412, 0.412), folder='corehub_intro', model=False)          # platform walls (105)
    mat('r11_tu_grey_mid', (0.29, 0.29, 0.29), folder='corehub_intro', model=False)         # slabs (66-75)
    mat('r11_tu_grey_dark', (0.17, 0.17, 0.17), folder='corehub_intro', model=False)        # dark faces (37-44)
    mat('r11_tu_floor', (0.15, 0.15, 0.15), folder='corehub_intro', model=False)
    mat('r11_tu_black', (0.055, 0.055, 0.055), folder='corehub_intro', model=False)          # black gaps (15)
    mat('r11_tu_sign', (1.0, 1.0, 1.0), base='corehub_intro/r11_tu_signtex', folder='corehub_intro', model=False)


def materials():
    brush_materials()
    mat('r11_tu_rail', (0.035, 0.035, 0.04))
    mat('r11_tu_black_m', (0.03, 0.03, 0.03), nocull=True)
    ramp('r11_tu_dark', (0.16, 0.16, 0.17), (0.35, 0.55, 0.8, 1.0))          # tower: dark metal
    ramp('r11_tu_greym', (0.42, 0.42, 0.43), (0.45, 0.65, 0.85, 1.0))
    mat('r11_tu_col_band', (0.42, 0.42, 0.43), alpha=0.85, translucent=True, nocull=True)
    mat('r11_tu_col_side', (0.36, 0.36, 0.37), alpha=0.55, translucent=True, nocull=True)
    mat('r11_tu_col_dark', (0.10, 0.10, 0.11), nocull=True)
    mat('r11_tu_col_inner', (0.33, 0.33, 0.34), alpha=0.85, translucent=True, nocull=True)
    mat('r11_tu_glass', (0.50, 0.51, 0.53), alpha=0.10, translucent=True, nocull=True)
    mat('r11_tu_laser', (0.95, 0.66, 0.66), alpha=0.7, translucent=True, nocull=True)
    mat('r11_tu_laser_dim', (0.85, 0.45, 0.45), alpha=0.35, translucent=True, nocull=True)
    mat('r11_tu_glow', (0.80, 0.30, 0.32), alpha=0.13, translucent=True, nocull=True)
    mat('r11_tu_haze', (0.48, 0.48, 0.48), alpha=0.63, translucent=True, nocull=True)
    ramp('r11_tu_white', (0.86, 0.86, 0.86), (0.55, 0.7, 0.85, 1.0))
    mat('r11_tu_cyan', (0.30, 0.85, 0.88))


N = 12


def collar(k=1.0, R=61.06, n=N, tall=18.0, band='r11_tu_col_band'):
    """translucent 12-gon collar (axis model +Z, band face at Z = 0): light band 0.80-1.0 R, dark ring 0.72-0.80 R,
    inner band 0.62-0.72 R, translucent sleeve (as models/rust.py: no opaque outer wall)"""
    m = Mesh()
    def poly_ring(z, r0, r1, mt):
        for i in range(n):
            a0 = 2 * math.pi * (i + 0.5) / n; a1 = 2 * math.pi * (i + 1.5) / n
            m.quad(mt, V(r0 * math.cos(a0), r0 * math.sin(a0), z), V(r1 * math.cos(a0), r1 * math.sin(a0), z),
                   V(r1 * math.cos(a1), r1 * math.sin(a1), z), V(r0 * math.cos(a1), r0 * math.sin(a1), z))
    def sleeve(z0, z1, r, mt):
        for i in range(n):
            a0 = 2 * math.pi * (i + 0.5) / n; a1 = 2 * math.pi * (i + 1.5) / n
            m.quad(mt, V(r * math.cos(a0), r * math.sin(a0), z0), V(r * math.cos(a1), r * math.sin(a1), z0),
                   V(r * math.cos(a1), r * math.sin(a1), z1), V(r * math.cos(a0), r * math.sin(a0), z1))
    poly_ring(0.0, 0.80 * R, R, band)
    poly_ring(0.5, 0.72 * R, 0.80 * R, 'r11_tu_col_dark')
    poly_ring(0.0, 0.62 * R, 0.72 * R, 'r11_tu_col_inner')
    sleeve(0.0, tall, R, 'r11_tu_col_side')
    poly_ring(tall, 0.80 * R, R, band)
    return m.transform(scale=k)


def beam(length, r=1.0, material='r11_tu_laser'):
    """thin laser beam along model +X (0..length)"""
    m = Mesh()
    m.tube(V(0, 0, 0), V(length, 0, 0), r, material, n=6, caps=False)
    return m


# ------------------------------------------------------------------------------------------------ turret extras
# The stock turret (models/props_backstage/vacum_turret.mdl) has its head along model +Y and its eye toward +Z:
# shell Y -18..24, X +-9.5, front at Z ~14; the scene stands it up (model +Y = map up).
def wings(spread=1.0):
    """the deployed turret's side panels (film 2096-2140): a tall crescent on each side of the shell, light grey
    outside, a dark gun panel on the inner front. Model axes as the stock turret (Y up, Z = facing); spread 0..1"""
    m = Mesh()
    for sx in (-1, 1):
        x_in = 10.5 + 4.5 * spread; bulge = 6.0; z0, z1 = -19.0, 19.0; d0, d1 = -2.0, 8.0
        pts_out = []; pts_in = []
        for k in range(13):
            t = -1.0 + 2.0 * k / 12.0; y = 0.5 * (z0 + z1) + 0.5 * (z1 - z0) * t
            w = math.sqrt(max(0.0, 1.0 - t * t))
            pts_out.append((sx * (x_in + 1.0 + bulge * w), y)); pts_in.append((sx * (x_in + 0.6 * bulge * w), y))
        for k in range(12):
            (xa, ya), (xb, yb) = pts_out[k], pts_out[k + 1]; (xc, yc), (xd, yd) = pts_in[k], pts_in[k + 1]
            # front face (toward +Z)
            q = [V(xc, yc, d1), V(xa, ya, d1), V(xb, yb, d1), V(xd, yd, d1)]
            if sx < 0: q = q[::-1]
            m.quad('r11_tu_white3', *q)
            # outer edge
            q = [V(xa, ya, d0), V(xb, yb, d0), V(xb, yb, d1), V(xa, ya, d1)]
            if sx < 0: q = q[::-1]
            m.quad('r11_tu_white1', *q)
            q = [V(xd, yd, d0), V(xc, yc, d0), V(xc, yc, d1), V(xd, yd, d1)]
            if sx < 0: q = q[::-1]
            m.quad('r11_tu_white0', *q)
        # gun panel: dark plate on the inner front with two light rings
        xg = sx * (x_in + 1.2)
        m.box((xg - 2.6, -6.0, d1 - 0.5), (xg + 2.6, 9.0, d1 + 0.6), 'r11_tu_gun')
        for yy in (5.0, -2.0):
            m.tube(V(xg, yy, d1 + 0.6), V(xg, yy, d1 + 1.0), 1.4, 'r11_tu_white2', n=8)
    return m


def glow(r0=5.0, r1=24.0, length=30.0, n=16):
    """red glow cone in front of the turret's eye (film 2084-2140: a soft red light over the lower body), axis +X"""
    m = Mesh()
    for k in range(n):
        a0 = 2 * math.pi * k / n; a1 = 2 * math.pi * (k + 1) / n
        q = [V(0, r0 * math.cos(a0), r0 * math.sin(a0)), V(0, r0 * math.cos(a1), r0 * math.sin(a1)),
             V(length, r1 * math.cos(a1), r1 * math.sin(a1)), V(length, r1 * math.cos(a0), r1 * math.sin(a0))]
        m.quad('r11_tu_glow', *q)
    return m


def _annulus(m, z, r0, r1, a0, a1, material, steps=8, up=True):
    """flat annulus sector in the plane Z = z (angles in degrees), facing +Z when up"""
    for k in range(steps):
        t0 = math.radians(a0 + (a1 - a0) * k / steps); t1 = math.radians(a0 + (a1 - a0) * (k + 1) / steps)
        q = [V(r0 * math.cos(t0), r0 * math.sin(t0), z), V(r1 * math.cos(t0), r1 * math.sin(t0), z),
             V(r1 * math.cos(t1), r1 * math.sin(t1), z), V(r0 * math.cos(t1), r0 * math.sin(t1), z)]
        if r0 < 1e-6: q = [q[1], q[2], q[0]]
        if not up: q = q[::-1]
        m.poly(material, q)


def petal(R=100.0, hub=26.0, t=4.0):
    """one white iris petal (film 2142-2160): quarter disc in the +X+Y quadrant, corner on the axis, face at Z = 0
    facing +Z: white face with two seams, dark hub with a cyan light at the corner, dark sides"""
    m = Mesh()
    for a0, a1 in ((0, 29), (31, 59), (61, 90)):
        _annulus(m, 0.0, hub, R, a0, a1, 'r11_tu_petal', steps=6)
    for a0, a1 in ((29, 31), (59, 61)):
        _annulus(m, -0.3, hub, R, a0, a1, 'r11_tu_seam', steps=1)
    _annulus(m, 0.0, hub * 0.45, hub, 0, 90, 'r11_tu_hub', steps=6)
    _annulus(m, 0.2, 0.0, hub * 0.45, 0, 90, 'r11_tu_cyan', steps=4)
    _annulus(m, -t, 0.0, R, 0, 90, 'r11_tu_black_m', steps=8, up=False)
    for k in range(10):
        a0 = math.radians(9 * k); a1 = math.radians(9 * (k + 1))
        m.quad('r11_tu_petal_side', V(R * math.cos(a0), R * math.sin(a0), -t), V(R * math.cos(a1), R * math.sin(a1), -t),
               V(R * math.cos(a1), R * math.sin(a1), 0), V(R * math.cos(a0), R * math.sin(a0), 0))
    m.quad('r11_tu_petal_side', V(0, 0, 0), V(0, 0, -t), V(R, 0, -t), V(R, 0, 0))
    m.quad('r11_tu_petal_side', V(0, 0, -t), V(0, 0, 0), V(0, R, 0), V(0, R, -t))
    return m


def iris_frame(r0=40.0, r1=70.0, depth=60.0):
    """grey ring under the petals and a dark throat (axis +Z, face at Z = 0)"""
    m = Mesh()
    _annulus(m, 0.0, r0, r1, 0, 360, 'r11_tu_frame', steps=32)
    for k in range(32):
        a0 = 2 * math.pi * k / 32; a1 = 2 * math.pi * (k + 1) / 32
        m.quad('r11_tu_throat', V(r0 * math.cos(a1), r0 * math.sin(a1), 0), V(r0 * math.cos(a0), r0 * math.sin(a0), 0),
               V(r0 * math.cos(a0), r0 * math.sin(a0), -depth), V(r0 * math.cos(a1), r0 * math.sin(a1), -depth))
    return m


def tower_base(rf=81.0, tf=12.0, rt=62.0, n_col=6, col_h=600.0, n_stub=6, rs=50.0, r_tube=6.0, drop=160.0, out=260.0):
    """bottom of the turret tower (film 1918-1950), axis model +Z, the flange's top face at Z = 0:
    dark 12-sided flange (radius rf, thickness tf) with a lighter rim, dark columns up to col_h on a circle of radius
    rt, a faint glass cylinder, n_stub tube stubs under the flange (on radius rs, radius r_tube) with light bands,
    which bend outward by `out` while dropping `drop` (dark translucent tubes)"""
    m = Mesh(); n = 12
    def poly(r, a):
        return [(r * math.cos(2 * math.pi * (i + a) / n), r * math.sin(2 * math.pi * (i + a) / n)) for i in range(n)]
    # flange: top face, rim band, sides, bottom
    outer = poly(rf, 0.5); inner = poly(rf * 0.86, 0.5)
    for i in range(n):
        j = (i + 1) % n
        m.quad('r11_tu_flange_top', V(inner[i][0], inner[i][1], 0), V(outer[i][0], outer[i][1], 0), V(outer[j][0], outer[j][1], 0), V(inner[j][0], inner[j][1], 0))
        m.quad('r11_tu_flange_side', V(outer[i][0], outer[i][1], 0), V(outer[i][0], outer[i][1], -tf), V(outer[j][0], outer[j][1], -tf), V(outer[j][0], outer[j][1], 0))
        m.quad('r11_tu_flange_bot', V(outer[j][0], outer[j][1], -tf), V(outer[i][0], outer[i][1], -tf), V(0, 0, -tf), V(0, 0, -tf))
    m.poly('r11_tu_flange_in', [V(x, y, 0.5) for x, y in inner])
    # a second, smaller ring step under the flange
    st = poly(rf * 0.72, 0.5)
    for i in range(n):
        j = (i + 1) % n
        m.quad('r11_tu_flange_side', V(st[i][0], st[i][1], -tf), V(st[i][0], st[i][1], -tf - 10), V(st[j][0], st[j][1], -tf - 10), V(st[j][0], st[j][1], -tf))
        m.quad('r11_tu_flange_bot', V(st[j][0], st[j][1], -tf - 10), V(st[i][0], st[i][1], -tf - 10), V(0, 0, -tf - 10), V(0, 0, -tf - 10))
    # columns and glass
    for k in range(n_col):
        a = 2 * math.pi * (k + 0.5) / n_col; c = V(rt * math.cos(a), rt * math.sin(a), 0)
        m.obox(c + V(0, 0, col_h / 2), (3.5, 3.5, col_h / 2), rot_z(math.degrees(a)), 'r11_tu_col')
    for k in range(24):
        a0 = 2 * math.pi * k / 24; a1 = 2 * math.pi * (k + 1) / 24; r = rt - 3
        m.quad('r11_tu_tglass', V(r * math.cos(a0), r * math.sin(a0), 0), V(r * math.cos(a1), r * math.sin(a1), 0),
               V(r * math.cos(a1), r * math.sin(a1), col_h), V(r * math.cos(a0), r * math.sin(a0), col_h))
    # stubs and bent tubes
    for k in range(n_stub):
        a = 2 * math.pi * k / n_stub; d = V(math.cos(a), math.sin(a), 0)
        base = d * rs + V(0, 0, -tf - 10)
        m.tube(base, base + V(0, 0, -24), r_tube, 'r11_tu_stub', n=12, caps=False)
        for zz in (-6.0, -16.0):
            m.tube(base + V(0, 0, zz), base + V(0, 0, zz - 4), r_tube + 1.5, 'r11_tu_stub_band', n=12, caps=False)
        prev = base + V(0, 0, -24)
        for s in range(1, 9):
            u = s / 8.0; p = base + V(0, 0, -24) + d * (out * (1 - math.cos(u * math.pi / 2))) + V(0, 0, -drop * math.sin(u * math.pi / 2))
            m.tube(prev, p, r_tube, 'r11_tu_tube', n=10, caps=False); prev = p
    return m


def grey_band(r0=150.0, r1=190.0, n=12, h=6.0):
    """the light grey ring below the tower (film 1926-1960): flat 12-gon annulus (axis +Z, top at Z = 0)"""
    m = Mesh()
    def poly(r):
        return [(r * math.cos(2 * math.pi * (i + 0.5) / n), r * math.sin(2 * math.pi * (i + 0.5) / n)) for i in range(n)]
    a = poly(r0); b = poly(r1)
    for i in range(n):
        j = (i + 1) % n
        m.quad('r11_tu_band_top', V(a[i][0], a[i][1], 0), V(b[i][0], b[i][1], 0), V(b[j][0], b[j][1], 0), V(a[j][0], a[j][1], 0))
        m.quad('r11_tu_band_side', V(b[i][0], b[i][1], 0), V(b[i][0], b[i][1], -h), V(b[j][0], b[j][1], -h), V(b[j][0], b[j][1], 0))
        m.quad('r11_tu_band_side', V(a[j][0], a[j][1], 0), V(a[j][0], a[j][1], -h), V(a[i][0], a[i][1], -h), V(a[i][0], a[i][1], 0))
        m.quad('r11_tu_band_bot', V(a[j][0], a[j][1], -h), V(b[j][0], b[j][1], -h), V(b[i][0], b[i][1], -h), V(a[i][0], a[i][1], -h))
    return m


def sign(w=96.0, h=100.0, t=2.0):
    """the test chamber sign: front face in the plane X = 0 facing -X (w along Y, h along Z, centred), textured;
    model +Y is the sign's left as seen from the front"""
    m = Mesh()
    a, b, c, d = V(0, w / 2, h / 2), V(0, w / 2, -h / 2), V(0, -w / 2, -h / 2), V(0, -w / 2, h / 2)
    m.tri('r11_tu_signm', a, b, c, uv=[(0.0, 1.0), (0.0, 0.0), (1.0, 0.0)])
    m.tri('r11_tu_signm', a, c, d, uv=[(0.0, 1.0), (1.0, 0.0), (1.0, 1.0)])
    m.box((0.0, -w / 2, -h / 2), (t, w / 2, h / 2), 'r11_tu_signback', mats={'-x': None})
    return m


def scan_head(k=1.0):
    """the scanner head that passes the camera in 2156-2168: white cylinder on top (axis +Z, top at Z = 0), a white
    frame below it with a dark round lens facing -X, white side plates; model +Z up"""
    m = Mesh()
    m.add(Mesh().lathe([(-14.0, 0.0), (-14.0, 22.0), (0.0, 22.0), (0.0, 0.0)], 'r11_tu_white3', n=24))
    m.box((-14.0, -20.0, -48.0), (14.0, -14.0, -14.0), 'r11_tu_white2')
    m.box((-14.0, 14.0, -48.0), (14.0, 20.0, -14.0), 'r11_tu_white2')
    m.box((-10.0, -14.0, -46.0), (12.0, 14.0, -18.0), 'r11_tu_gun')
    m.add(Mesh().lathe([(0.0, 0.0), (0.0, 11.0), (1.0, 11.0), (1.0, 0.0)], 'r11_tu_black_m', n=20, axis='x'), offset=(-11.0, 0, -31.0))
    m.add(Mesh().lathe([(0.0, 11.0), (0.0, 13.0), (2.0, 13.0), (2.0, 11.0)], 'r11_tu_white1', n=20, axis='x'), offset=(-12.0, 0, -31.0))
    m.box((-6.0, 20.0, -40.0), (6.0, 30.0, -26.0), 'r11_tu_white1')
    return m.transform(scale=k)


def robot_arm(L1=60.0, L2=55.0, w=5.0):
    """white two-segment arm (film 2150-2156): from the shoulder at the origin down-left along -Z, segment 2 to the
    hand; joints as short cylinders; in the plane X = 0"""
    m = Mesh()
    a = np.array([0.0, 0.0, 0.0]); b = np.array([0.0, -18.0, -L1]); c = np.array([0.0, 6.0, -L1 - L2])
    for p, q in ((a, b), (b, c)):
        m.tube(V(*p), V(*q), w, 'r11_tu_white3', n=8)
    for p in (a, b, c):
        m.tube(V(*(p + [-w - 1, 0, 0])), V(*(p + [w + 1, 0, 0])), w + 2.0, 'r11_tu_white2', n=12)
    return m


def sheet(w, h, material):
    """flat quad in the plane X = 0 facing -X (w along Y, h along Z), centred"""
    m = Mesh()
    m.quad(material, V(0, w / 2, -h / 2), V(0, -w / 2, -h / 2), V(0, -w / 2, h / 2), V(0, w / 2, h / 2))
    return m


def ring_tube(L=160.0, rho=34.0, w=1.8):
    """the moving tube end of shot A (film 1958-1996): collar 1 at X = 0 and collar 2 at X = L (axes model +X, bands
    facing -X), the four rails between them"""
    m = Mesh()
    up = rot_y(90)                  # collar() is made about +Z; rot_y(90) turns +Z into +X
    m.add(collar(1.0), R=up)
    if L <= 0: return m
    m.add(collar(1.0), R=up, offset=(L, 0, 0))
    for a in range(4):
        ang = math.radians(45 + 90 * a); y, z = rho * math.cos(ang), rho * math.sin(ang)
        m.box((0.0, y - w / 2, z - w / 2), (L, y + w / 2, z + w / 2), 'r11_tu_rail')
    return m


def build():
    textures()
    materials()
    save(ring_tube(0.0), 'r11_tu_ringtube')
    # shot B: the small tube below the sign (collars R 12 every 17 units, rails rho 6.7), axis +Z, top collar at Z = 0
    t = Mesh()
    for k in list(range(9)) + list(range(-14, -2)):
        t.add(collar(24.0 / 61.06, tall=8.0), offset=(0, 0, -22.0 * k))
    for a in range(4):
        ang = math.radians(45 + 90 * a); y, z = 13.4 * math.cos(ang), 13.4 * math.sin(ang)
        t.box((y - 1.2, z - 1.2, -300.0), (y + 1.2, z + 1.2, 12.0), 'r11_tu_rail')
        t.box((y - 1.2, z - 1.2, 50.0), (y + 1.2, z + 1.2, 330.0), 'r11_tu_rail')
    save(t, 'r11_tu_smalltube')
    sl = Mesh(); sl.box((0.0, -300.0, -6.0), (100.0, 300.0, 6.0), 'r11_tu_slabm', mats={'+z': 'r11_tu_slabtop', '-z': 'r11_tu_slabbot'})
    save(sl, 'r11_tu_slab')
    save(petal(59.0, 15.0), 'r11_tu_petal')
    save(iris_frame(26.0, 44.0, 40.0), 'r11_tu_irisframe')
    m2 = Mesh(); m2.add(collar(20.0 / 61.06), R=rot_y(90))
    for yy in (-12.0, 12.0):
        m2.box((-3.0, yy - 3.0, 14.0), (3.0, yy + 3.0, 200.0), 'r11_tu_black_m')
    save(m2, 'r11_tu_ring2')
    mat('r11_tu_gun', (0.20, 0.20, 0.21))
    mat('r11_tu_slabm', (0.30, 0.30, 0.30)); mat('r11_tu_slabtop', (0.26, 0.26, 0.26)); mat('r11_tu_slabbot', (0.36, 0.36, 0.36))
    mat('r11_tu_petal', (0.88, 0.88, 0.87))
    mat('r11_tu_seam', (0.45, 0.45, 0.46))
    mat('r11_tu_hub', (0.30, 0.31, 0.32))
    mat('r11_tu_petal_side', (0.25, 0.25, 0.26))
    mat('r11_tu_frame', (0.40, 0.40, 0.41))
    mat('r11_tu_throat', (0.12, 0.12, 0.12), nocull=True)
    mat('r11_tu_signm', (1.0, 1.0, 1.0), base='corehub_intro/r11_tu_signtex')
    mat('r11_tu_signback', (0.5, 0.5, 0.5))
    mat('r11_tu_flange_top', (0.16, 0.16, 0.165))
    mat('r11_tu_flange_in', (0.10, 0.10, 0.105))
    mat('r11_tu_flange_side', (0.075, 0.075, 0.08))
    mat('r11_tu_flange_bot', (0.05, 0.05, 0.055))
    mat('r11_tu_col', (0.045, 0.045, 0.05))
    mat('r11_tu_tglass', (0.45, 0.46, 0.48), alpha=0.07, translucent=True, nocull=True)
    mat('r11_tu_stub', (0.12, 0.12, 0.13))
    mat('r11_tu_stub_band', (0.26, 0.26, 0.27))
    mat('r11_tu_tube', (0.10, 0.10, 0.11), alpha=0.6, translucent=True, nocull=True)
    mat('r11_tu_band_top', (0.40, 0.40, 0.40))
    mat('r11_tu_band_side', (0.30, 0.30, 0.30))
    mat('r11_tu_band_bot', (0.08, 0.08, 0.08))
    save(tower_base(), 'r11_tu_tower')
    save(grey_band(), 'r11_tu_band')
    save(sign(26.0, 26.0, 0.8), 'r11_tu_sign16')
    h = scan_head(0.75); h.shade('r11_tu_white', light=(-0.5, -0.4, 0.75)); save(h, 'r11_tu_scanhead')
    save(robot_arm(), 'r11_tu_arm')
    save(collar(1.0), 'r11_tu_collar')
    save(beam(1000.0), 'r11_tu_beam')
    w = wings(1.0); w.shade('r11_tu_white', light=(0.3, 0.4, 0.85)); save(w, 'r11_tu_wings')
    save(glow(), 'r11_tu_glow')
    save(sheet(4000.0, 3000.0, 'r11_tu_haze'), 'r11_tu_haze')
