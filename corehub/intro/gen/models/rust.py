"""Rust room (32.7-38.9 s): own textures, materials and devices (prefix r11_ru).

Textures are procedural (numpy), coloured from the film's samples (no video pixels):
  rust panels: frame 1063 (wall y 3487 seen frontally from 1420 units): dark parts (38 37 37), mid (59 55 54),
    rusty parts (107 89 77), mean (65 58 54); vertical panel seams every ~580 units, horizontal every ~320
  floor: dark neutral grey 16-19 (frames 994, 1017), faint tile grid
Brush materials live in materials/corehub_intro/r11_ru_*.vmt (UnlitGeneric), the models' in models/corehub_intro."""
import math
import numpy as np
from lib.gen import Mesh, V, mat, ramp, save, write_texture, rot_x, rot_y, rot_z

PANEL_W = 580.0          # world units per panel (horizontal)
PANEL_H = 320.0          # world units per panel (vertical)
TEX_PANELS = (2, 4)      # panels per texture repeat (u, v)
TEX = 512
WALL_MAT = 'corehub_intro/r11_ru_wall'
WALL_DIM = 'corehub_intro/r11_ru_wall_dim'
WALL_DARK = 'corehub_intro/r11_ru_wall_dark'
FLOOR_MAT = 'corehub_intro/r11_ru_floor'
BLACK_MAT = 'corehub_intro/void_black'


def _blur(a, sx, sy):
    from scipy.ndimage import gaussian_filter
    return gaussian_filter(a, (sy, sx), mode='wrap')


def rust_texture(seed=11):
    """512x512 RGB: 2 x 4 panels of dark grey-brown metal with horizontally streaked orange rust and light seams"""
    rng = np.random.default_rng(seed)
    n = TEX; pw = n // TEX_PANELS[0]; ph = n // TEX_PANELS[1]
    # rust amount: large blotches + horizontal streaks
    big = _blur(rng.standard_normal((n, n)), 26, 10); big /= big.std()
    streak = _blur(rng.standard_normal((n, n)), 30, 1.2); streak /= streak.std()
    fine = _blur(rng.standard_normal((n, n)), 3, 0.7); fine /= fine.std()
    # per panel bias (some strips are rustier, as in the film)
    bias = np.zeros((n, n))
    for i in range(TEX_PANELS[0]):
        for j in range(TEX_PANELS[1]):
            bias[j * ph:(j + 1) * ph, i * pw:(i + 1) * pw] = rng.normal(0.0, 0.45) + (0.35 if i == 0 else -0.25)
    r = 0.55 * big + 0.45 * streak + 0.18 * fine + bias
    rust = np.clip((r - 0.35) / 1.1, 0, 1) ** 1.2
    dark = np.array([40.0, 39.0, 39.0]); mid = np.array([58.0, 54.0, 53.0]); orange = np.array([118.0, 92.0, 74.0])
    bn = _blur(rng.standard_normal((n, n)), 12, 2); bn /= bn.std()
    base_t = np.clip(0.5 + 0.3 * bn + 0.2 * fine, 0, 1)
    base = dark[None, None, :] * (1 - base_t[..., None]) + mid[None, None, :] * base_t[..., None]
    img = base * (1 - rust[..., None]) + orange[None, None, :] * rust[..., None]
    # thin dark scratches along the streaks
    img *= (0.88 + 0.12 * np.clip(streak[..., None] * 0.5 + 1, 0, 1.4))
    # seams: a light line and a dark line at the panel edges (horizontal and vertical)
    for i in range(TEX_PANELS[0]):
        x = i * pw
        img[:, x % n, :] = img[:, x % n, :] * 0.4 + np.array([88.0, 84.0, 80.0]) * 0.6
        img[:, (x + 1) % n, :] *= 0.6
        img[:, (x + pw // 2) % n, :] = img[:, (x + pw // 2) % n, :] * 0.75 + 15
    for j in range(TEX_PANELS[1]):
        y = j * ph
        img[y % n, :, :] = img[y % n, :, :] * 0.4 + np.array([92.0, 88.0, 84.0]) * 0.6
        img[(y + 1) % n, :, :] *= 0.55
    return np.clip(img, 0, 255).astype(np.uint8)


def floor_texture(seed=5, level=17.0):
    """256x256 dark neutral grey tiles (4 x 4 per repeat) with slightly lighter joints"""
    rng = np.random.default_rng(seed)
    n = 256; t = n // 4
    fn = _blur(rng.standard_normal((n, n)), 6, 6); fn /= fn.std()
    v = level + 2.5 * fn
    for k in range(4):
        for l in range(4):
            v[k * t:(k + 1) * t, l * t:(l + 1) * t] += rng.normal(0, 1.5)
    for k in range(4):
        v[k * t, :] += 9; v[:, k * t] += 9
        v[(k * t + 1) % n, :] -= 4; v[:, (k * t + 1) % n] -= 4
    img = np.repeat(np.clip(v, 0, 255)[..., None], 3, axis=2)
    return img.astype(np.uint8)


def textures():
    write_texture('corehub_intro/r11_ru_rust', rust_texture())
    write_texture('corehub_intro/r11_ru_floortex', floor_texture())


def brush_materials():
    base = 'corehub_intro/r11_ru_rust'
    mat('r11_ru_wall', (1.0, 1.0, 1.0), base=base, folder='corehub_intro', model=False)
    mat('r11_ru_wall_dim', (0.80, 0.80, 0.80), base=base, folder='corehub_intro', model=False)
    mat('r11_ru_wall_dark', (0.45, 0.45, 0.45), base=base, folder='corehub_intro', model=False)
    mat('r11_ru_wall_low', (0.66, 0.66, 0.66), base=base, folder='corehub_intro', model=False)     # shot B lower level
    mat('r11_ru_floor', (1.0, 1.0, 1.0), base='corehub_intro/r11_ru_floortex', folder='corehub_intro', model=False)


def materials():
    brush_materials()
    mat('r11_ru_black', (0.02, 0.02, 0.02))
    mat('r11_ru_rail', (0.035, 0.035, 0.04))
    ramp('r11_ru_dark', (0.16, 0.16, 0.17), (0.35, 0.55, 0.8, 1.0))          # dark tubes, clamps
    mat('r11_ru_tube_dark', (0.20, 0.20, 0.21), folder='corehub_intro', model=False)     # brush: the end tube
    mat('r11_ru_tube_rib', (0.38, 0.38, 0.39), folder='corehub_intro', model=False)
    ramp('r11_ru_grey', (0.42, 0.42, 0.43), (0.45, 0.65, 0.85, 1.0))         # port flanges, pipe rings
    ramp('r11_ru_flange', (0.30, 0.30, 0.31), (0.45, 0.65, 0.85, 1.0))       # glass T flanges
    mat('r11_ru_light', (0.50, 0.50, 0.50))
    mat('r11_ru_glass', (0.50, 0.51, 0.53), alpha=0.10, translucent=True, nocull=True)
    # collars of the rust room: translucent light grey 12-gon bands (film 1041, 1069: outer band, dark ring, inner band)
    # round 3: band 103-114 in the film's moments (E 1039-1071: over the lit wall and over black alike, the wall's
    # streaks show through faintly), but near collars show dark in the film (1101L, 1102E): 0.36 at alpha 0.85 scored
    # best over the collar samples (0.56 / 0.82 before: ssim -0.04, tone -0.07; 0.43 / 0.9: ssim -0.01)
    mat('r11_ru_col_band', (0.36, 0.36, 0.37), alpha=0.85, translucent=True, nocull=True)
    mat('r11_ru_col_side', (0.12, 0.12, 0.125), alpha=0.7, translucent=True, nocull=True)      # round 3: dark (near collars show dark rings)
    mat('r11_ru_col_dark', (0.10, 0.10, 0.11), nocull=True)
    mat('r11_ru_col_inner', (0.28, 0.28, 0.29), alpha=0.85, translucent=True, nocull=True)
    mat('r11_ru_glass_edge', (0.80, 0.80, 0.82), alpha=0.6, translucent=True, nocull=True)


N = 24


def ring_disc(m, x, r0, r1, material, n=N, face=-1):
    """flat annulus in the plane X = x (axis = model +X) facing -X (face -1) or +X"""
    for k in range(n):
        a0 = 2 * math.pi * k / n; a1 = 2 * math.pi * (k + 1) / n
        q = [V(x, r0 * math.cos(a0), r0 * math.sin(a0)), V(x, r1 * math.cos(a0), r1 * math.sin(a0)),
             V(x, r1 * math.cos(a1), r1 * math.sin(a1)), V(x, r0 * math.cos(a1), r0 * math.sin(a1))]
        if face < 0: q = q[::-1]
        m.quad(material, *q) if r0 > 1e-6 else m.tri(material, *([q[0], q[1], q[2]] if face > 0 else [q[0], q[1], q[2]]))
    return m


def cyl_x(m, x0, x1, r, material, n=N, inward=False):
    """open cylinder about the X axis"""
    for k in range(n):
        a0 = 2 * math.pi * k / n; a1 = 2 * math.pi * (k + 1) / n
        q = [V(x0, r * math.cos(a0), r * math.sin(a0)), V(x0, r * math.cos(a1), r * math.sin(a1)),
             V(x1, r * math.cos(a1), r * math.sin(a1)), V(x1, r * math.cos(a0), r * math.sin(a0))]
        if inward: q = q[::-1]
        m.quad(material, *q)
    return m


def port(k=1.0, closed=True, flange='r11_ru_grey3'):
    """round port in a wall, face at X = 0, the tube arriving from -X: grey flange, dark ring, light inner ring,
    black throat (film 990-996: rings of radius ~45-110 around the tube's end)"""
    m = Mesh()
    ring_disc(m, -14.0, 82.0, 112.0, flange)
    cyl_x(m, -14.0, 0.0, 112.0, 'r11_ru_grey1')
    ring_disc(m, -10.0, 66.0, 82.0, 'r11_ru_dark1')
    ring_disc(m, -12.0, 50.0, 66.0, 'r11_ru_grey2')
    cyl_x(m, -12.0, 40.0, 50.0, 'r11_ru_dark0', inward=True)
    if closed: ring_disc(m, 40.0, 0.0, 50.0, 'r11_ru_black')
    return m.transform(scale=k)


def support(height, k=1.0):
    """vertical support pipe (axis +Z, from z = -height to 0) with flange rings"""
    m = Mesh()
    m.add(Mesh().lathe([(0.0, 0.0), (0.0, 22.0), (height, 22.0), (height, 0.0)], 'r11_ru_grey', n=16))
    for z in (8.0, height * 0.5, height - 14.0):
        m.add(Mesh().lathe([(z - 5, 0.0), (z - 5, 30.0), (z + 5, 30.0), (z + 5, 0.0)], 'r11_ru_grey', n=16))
    m.shade('r11_ru_grey', light=(0.4, -0.6, 0.7))
    return m.transform(offset=(0, 0, -height)).transform(scale=k)


def glass_t(k=1.0, length=260.0, r=50.0, stand=352.0):
    """glass T-piece: glass cylinder along model +X (length, radius r, centred on the origin) with dark end flanges
    and a glass stand below (to z = -stand)"""
    m = Mesh()
    cyl_x(m, -length / 2, length / 2, r, 'r11_ru_glass', n=20)
    for x in (-length / 2, length / 2):
        m.add(Mesh().lathe([(x - 10, r - 6), (x - 10, r + 10), (x + 10, r + 10), (x + 10, r - 6)], 'r11_ru_flange', n=20, axis='x'))
    m.add(Mesh().lathe([(-stand, 0.0), (-stand, 38.0), (-r * 0.7, 38.0), (-r * 0.7, 0.0)], 'r11_ru_glass', n=16))
    m.add(Mesh().lathe([(-stand, 0.0), (-stand, 54.0), (-stand + 16, 54.0), (-stand + 16, 0.0)], 'r11_ru_flange', n=16))
    m.add(Mesh().lathe([(-r - 14, 0.0), (-r - 14, 50.0), (-r + 2, 50.0), (-r + 2, 0.0)], 'r11_ru_flange', n=16))
    for a in range(4):
        ang = math.radians(45 + 90 * a)
        m.tube((-stand, 30 * math.cos(ang), 30 * math.sin(ang)), (-r, 30 * math.cos(ang), 30 * math.sin(ang)), 2.5, 'r11_ru_flange', n=6)
    m.shade('r11_ru_flange', light=(0.4, -0.6, 0.7))
    # the stand runs along -Z: rotate the lathed parts (made about +Z) is already about Z; the cylinder is along X
    return m.transform(scale=k)


def dark_elbow(k=1.0, R=76.0, r=22.0, arc=(-135.0, 135.0)):
    """dark tube bent into a ring arc (major radius R, tube radius r) in the plane X = 0 (seen as a 'C')"""
    m = Mesh(); n = 28; a0, a1 = [math.radians(a) for a in arc]
    for i in range(n):
        t0 = a0 + (a1 - a0) * i / n; t1 = a0 + (a1 - a0) * (i + 1) / n
        c0 = V(0, R * math.cos(t0), R * math.sin(t0)); c1 = V(0, R * math.cos(t1), R * math.sin(t1))
        m.tube(c0, c1, r, 'r11_ru_dark', n=10, caps=False)
    m.shade('r11_ru_dark', light=(-0.8, -0.3, 0.5))
    return m.transform(scale=k)


def clamp(k=1.0, R=46.0, w=10.0):
    """dark clamp ring around the tube (radius R, axis +X) with four small blocks on the rail diagonals"""
    m = Mesh()
    m.add(Mesh().lathe([(-w / 2, R - 5), (-w / 2, R + 3), (w / 2, R + 3), (w / 2, R - 5)], 'r11_ru_dark', n=24, axis='x'))
    for a in range(4):
        ang = math.radians(45 + 90 * a); c = V(0, 34 * math.cos(ang), 34 * math.sin(ang))
        m.obox(c, (w / 2 + 2, 5.0, 5.0), rot_x(45 + 90 * a), 'r11_ru_dark')
        m.obox(c * (R / 34.0), (w / 2 + 2, 6.0, 6.0), rot_x(45 + 90 * a), 'r11_ru_dark')
    m.shade('r11_ru_dark', light=(-0.8, -0.3, 0.5))
    return m.transform(scale=k)


def collar(k=1.0, R=61.06, n=12, tall=18.0, band='r11_ru_col_band'):
    """rust-room collar (axis model +Z, the band's face at Z = 0): 12-gon light band 0.80-1.0 R, dark ring
    0.72-0.80 R, inner band 0.62-0.72 R, translucent sleeve (no opaque outer wall: the film's collars show the room
    through them when seen at an angle)"""
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
    # round 3: band 0.76-1.0 R, groove 0.70-0.76, inner band 0.62-0.70 (film E 1067 / 1069 radial profiles: light
    # band 0.75-1.0 of its outer edge, dark groove, a lighter band 0.67-0.73, the dark inside below 0.65)
    poly_ring(0.0, 0.76 * R, R, band)
    poly_ring(0.5, 0.70 * R, 0.76 * R, 'r11_ru_col_dark')
    poly_ring(0.0, 0.62 * R, 0.70 * R, 'r11_ru_col_inner')
    sleeve(0.0, tall, R, 'r11_ru_col_side')
    # no second band at the back (it showed as an extra light ring just before a pass, which the film never shows,
    # e.g. 1094E); a dark inside wall instead (film 1071E: dark ring inside the band when close)
    sleeve(0.0, tall, 0.62 * R, 'r11_ru_col_dark')
    return m.transform(scale=k)


def ribbed_tube(k=1.0, r=58.0, length=800.0, pitch=70.0, n=12):
    """dark tube along model +X (0..length) with lighter rib rings outside every `pitch` units (film 1063-1082)"""
    m = Mesh()
    cyl_x(m, 0.0, length, r, 'r11_ru_tdark', n=n, inward=True)
    cyl_x(m, 0.0, length, r + 4.0, 'r11_ru_tdark', n=n)
    ring_disc(m, 0.0, r, r + 4.0, 'r11_ru_tdark', n=n)
    x = 25.0
    while x < length:
        cyl_x(m, x, x + 8.0, r + 7.0, 'r11_ru_trib', n=n)
        ring_disc(m, x, r + 4.0, r + 7.0, 'r11_ru_trib', n=n)
        ring_disc(m, x + 8.0, r + 4.0, r + 7.0, 'r11_ru_trib', n=n, face=1)
        x += pitch
    return m.transform(scale=k)


def end_wall():
    """the far wall's end past x 4623 (shot A, shown 35.7-36.2 s): rust panels, x 0..577, face at y 0 facing -y,
    z 0..1200 (dark rust as r11_ru_wall_dark)"""
    m = Mesh()
    m.quad('r11_rux_endwall', V(0, 0, 0), V(577, 0, 0), V(577, 0, 1200), V(0, 0, 1200))
    m.quad('r11_rux_endwall', V(0, 0, 0), V(0, 0, 1200), V(577, 0, 1200), V(577, 0, 0))
    return m.uv_box(scale=1200.0)


def mouth_wall(y0=-300.0, y1=537.0, z0=-563.0, z1=637.0, h=66.0):
    """rust wall round the end tube's mouth (shot A, 35.85-36.2 s; film 1077-1082: rust panels all round the dark
    mouth): plane X = 0 facing -X, a square hole of half size h round the origin (the tube's axis)"""
    m = Mesh()
    def q(ya, yb, za, zb):
        if yb - ya < 1 or zb - za < 1: return
        m.quad('r11_rux_mouthwall', V(0, ya, za), V(0, ya, zb), V(0, yb, zb), V(0, yb, za))
    q(y0, -h, z0, z1); q(h, y1, z0, z1); q(-h, h, z0, -h); q(-h, h, h, z1)
    return m.uv_box(scale=1200.0)


def build():
    textures()
    materials()
    mat('r11_rux_endwall', (0.45, 0.45, 0.45), base='corehub_intro/r11_ru_rust')
    save(end_wall(), 'r11_rux_endwall')
    mat('r11_rux_mouthwall', (0.80, 0.80, 0.80), base='corehub_intro/r11_ru_rust')
    save(mouth_wall(), 'r11_rux_mouthwall')
    mat('r11_ru_tdark', (0.13, 0.13, 0.135), nocull=True)          # (0.20 tried in round 3: lower at 36.0 s)
    mat('r11_ru_trib', (0.24, 0.24, 0.25))
    save(ribbed_tube(1.0), 'r11_ru_endtube')
    save(collar(1.0), 'r11_ru_collar')
    save(port(0.39, closed=False), 'r11_ru_port_small_s065')
    save(collar(0.65), 'r11_ru_collar_s065')
    for k, tag in ((1.0, ''), (0.65, '_s065')):
        save(port(k), 'r11_ru_port' + tag)
        # the dividing wall's port (shot A, y 980) shows dark rings with one light ring in the film (33.75 s, frame
        # 1012): dark flange (round 3; was light grey, a light disc round the junction)
        save(port(k, closed=False, flange='r11_ru_dark1'), 'r11_ru_port_open' + tag)
        save(support(300.0, k), 'r11_ru_support' + tag)
        save(glass_t(k), 'r11_ru_glass_t' + tag)
        save(dark_elbow(k), 'r11_ru_elbow' + tag)
        save(clamp(k), 'r11_ru_clamp' + tag)
