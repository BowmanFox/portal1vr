"""Incinerator (film 109.9-118.35 s, frames 3293-3547): models for the rebuilt shot in cell C7 (scenes/incinerator.py).

All r11_ic_* parts are round about model +Z unless noted (the shaft runs along map Z). Sizes are map units at the
scale of the measured camera (COLMAP model 1 times S1, see data/ic_cam_ride.json); colours sampled from the film.
  r11_ic_collar      shaft collar: light 12-sided band (film grey 118) with the dark inner band, axis +Z, top face up
  r11_ic_ringdark    dark 12-sided ring (the shaft's frame rings between the collars)
  r11_ic_funnel      the burnt funnel at the bottom of the shaft (dark, swirls of glow toward the fire)
  r11_ic_bowl        the orange bowl round the shaft mouth
  r11_ic_fire        the glowing bottom (yellow-orange disc)
  r11_ic_petal       iris quarter for the wall iris (axis model +X, petal in +Y+Z), radius 64
  r11_ic_disc        the white disc (closed hatch) at the far wall, axis +X
Older starter models (kept, the old map refers to them): p9_end_shaft_iris_quarter, ending_iris_frame."""
import math, os
import numpy as np
from lib.gen import Mesh, V, mat, ramp, save, rot_x, rot_y, rot_z
from models import iris as I

PETAL_SCALE = 64.0 / I.PETAL_R        # petal radius 64


def ring_frame(r0=66.0, r1=78.0, depth=10.0):
    """grey ring round an iris, axis X, faces at X = 0 (toward -X) and X = depth (toward +X)"""
    m = Mesh()
    I.ring_x(m, 0.0, r0, r1, 'irisf_ring')
    I.ring_x(m, 0.0, r0 - 2.4, r0, 'irisf_ring_in')
    I.wall_x(m, 0.0, r0 - 2.4, depth, r0 - 2.4, 'irisf_ring_in', inward=True)
    I.wall_x(m, 0.0, r1, depth, r1, 'irisf_black', inward=False)
    I.ring_x(m, depth, r0 - 2.4, r1, 'irisf_ring', down=False)
    return m


def materials():
    mat('r11_ic_lightgrey', (0.47, 0.47, 0.47))
    mat('r11_ic_midgrey', (0.36, 0.36, 0.37))
    mat('r11_ic_darkgrey', (0.20, 0.16, 0.15))
    mat('r11_ic_black', (0.02, 0.02, 0.02))
    mat('r11_ic_orange', (0.53, 0.215, 0.115))
    mat('r11_ic_orange_hi', (0.60, 0.25, 0.12))
    mat('r11_ic_orange_lo', (0.40, 0.17, 0.10))
    # funnel bands top .. bottom: the film's radial luminance from inside the funnel (115.1: 108 at the centre, 84 at r 100,
    # 68 at r 200, 52 at r 300 px) on the camera's sight lines to the bands (older ramp was 10-20 levels brighter)
    for i, c in enumerate(((0.21, 0.155, 0.14), (0.25, 0.16, 0.14), (0.30, 0.175, 0.14), (0.38, 0.195, 0.14), (0.46, 0.22, 0.14), (0.58, 0.265, 0.15))):
        mat('r11_ic_burn%d' % i, c)
    mat('r11_ic_fire', (0.74, 0.34, 0.15))
    mat('r11_ic_fireglow', (0.66, 0.30, 0.15))
    mat('r11_ic_white', (0.88, 0.88, 0.87))
    mat('r11_ic_cyan', (0.30, 0.85, 0.85))
    mat('r11_ic_glowmat', (0.96, 0.92, 0.55))
    mat('r11_ic_red', (0.95, 0.35, 0.35), alpha=0.26, translucent=True, nocull=True)
    mat('r11_ic_yellow', (0.98, 0.88, 0.45), alpha=0.32, translucent=True, nocull=True)
    mat('r11_ic_yellow_faint', (0.98, 0.88, 0.45), alpha=0.2, translucent=True, nocull=True)
    mat('r11_ic_tband', (0.30, 0.29, 0.29))
    mat('r11_ic_tlight', (0.37, 0.37, 0.37))
    mat('r11_ic_rimout', (0.26, 0.25, 0.25))
    mat('r11_ic_pipe', (0.13, 0.12, 0.12))
    mat('r11_ic_darkwall', (0.13, 0.12, 0.12))         # the shaft's dark rim wall (film 3342-3350: 30-40)
    ramp('r11_ic_headmat', (0.93, 0.87, 0.62), (0.6, 0.72, 0.86, 1.0))
    mat('r11_ic_headdk', (0.45, 0.40, 0.25))
    mat('r11_ic_headmat2', (0.80, 0.74, 0.50))
    mat('r11_ic_fan', (0.80, 0.78, 0.77), alpha=float(os.environ.get('IC_FANA', 0.2)), translucent=True, nocull=True)
    mat('r11_ic_fc_light', (0.33, 0.33, 0.33)); mat('r11_ic_fc_dark', (0.12, 0.12, 0.12)); mat('r11_ic_fc_mid', (0.20, 0.20, 0.20))
    mat('r11_ic_fc_sleeve', (0.30, 0.30, 0.30))
    ramp('r11_ic_dk', (0.17, 0.17, 0.18))
    mat('r11_ic_yfan', (0.98, 0.86, 0.45), alpha=0.42, translucent=True, nocull=True)
    mat('r11_ic_lobe', (0.98, 0.88, 0.45), alpha=float(os.environ.get('IC_LOBEA', 0.5)), translucent=True, nocull=True)
    # own turret / cube / can (film 3342-3354: shell ~225 lit, ~100 in shade; gaps and legs dark)
    ramp('r11_ic_tsh', (0.88, 0.88, 0.89), (0.36, 0.46, 0.57, 0.69, 0.82, 0.95))
    mat('r11_ic_tgap', (0.09, 0.09, 0.09))
    mat('r11_ic_teye', (0.85, 0.16, 0.14))
    ramp('r11_ic_tleg', (0.30, 0.30, 0.31), (0.45, 0.7, 1.0))
    ramp('r11_ic_cubef', (0.80, 0.80, 0.81))
    ramp('r11_ic_cubec', (0.52, 0.52, 0.53))
    mat('r11_ic_cubed', (0.86, 0.86, 0.87))
    ramp('r11_ic_can', (0.40, 0.37, 0.35))


def lathe_z(m, prof, material, n=12, phase=15.0):
    """surface of revolution about +Z from a profile [(z, r), ...], visible from the axis side"""
    for (z0, r0), (z1, r1) in zip(prof, prof[1:]):
        for k in range(n):
            a0 = math.radians(phase + 360.0 * k / n); a1 = math.radians(phase + 360.0 * (k + 1) / n)
            p = [V(r0 * math.cos(a0), r0 * math.sin(a0), z0), V(r0 * math.cos(a1), r0 * math.sin(a1), z0),
                 V(r1 * math.cos(a1), r1 * math.sin(a1), z1), V(r1 * math.cos(a0), r1 * math.sin(a0), z1)]
            # make the face point toward the axis (inward)
            c = sum(p) / 4.0; nrm = np.cross(p[1] - p[0], p[3] - p[0])
            if nrm @ np.array([c[0], c[1], 0.0]) > 0: p = p[::-1]
            if abs(r0) < 1e-6: m.tri(material, p[0], p[2], p[3]) if False else m.poly(material, p)
            else: m.poly(material, p)
    return m


def annulus_z(m, z, r0, r1, material, n=12, up=True, phase=15.0):
    for k in range(n):
        a0 = math.radians(phase + 360.0 * k / n); a1 = math.radians(phase + 360.0 * (k + 1) / n)
        p = [V(r0 * math.cos(a0), r0 * math.sin(a0), z), V(r1 * math.cos(a0), r1 * math.sin(a0), z),
             V(r1 * math.cos(a1), r1 * math.sin(a1), z), V(r0 * math.cos(a1), r0 * math.sin(a1), z)]
        if r0 < 1e-6: p = [p[1], p[2], p[0]]
        if not up: p = p[::-1]
        m.poly(material, p)
    return m


def collar(R=61.0):
    """light band 0.72..1 R on top, dark inner band 0.55..0.72 R, black outside and below"""
    m = Mesh()
    annulus_z(m, 0.0, 0.72 * R, R, 'r11_ic_lightgrey')
    annulus_z(m, 0.0, 0.55 * R, 0.72 * R, 'r11_ic_darkgrey')
    lathe_z(m, [(0.0, 0.55 * R), (-0.35 * R, 0.55 * R)], 'r11_ic_black')
    annulus_z(m, -0.35 * R, 0.55 * R, R, 'r11_ic_black', up=False)
    return m


def band_ring(r_in, r_out, mat_band='r11_ic_lightgrey', edge=None, depth=6.0, n=12):
    """flat 12-sided ring facing +Z (seen by the camera looking down the shaft): band r_in..r_out, an optional dark
    inner edge from `edge` to r_in, black underside and rims"""
    m = Mesh()
    annulus_z(m, 0.0, r_in, r_out, mat_band, n=n)
    if edge: annulus_z(m, 0.0, edge, r_in, 'r11_ic_darkgrey', n=n)
    ri = edge or r_in
    annulus_z(m, -depth, ri, r_out, 'r11_ic_black', n=n, up=False)
    lathe_z(m, [(0.0, ri), (-depth, ri)], 'r11_ic_black', n=n)
    return m


def probe(L=54.0, rad=7.0, n=10):
    """scanner probe pointing along +X: white body from x = 0 to L, black lens cap at the tip (x = L), dark mount at
    the back"""
    m = Mesh()
    m.tube((0, 0, 0), (L, 0, 0), rad, 'r11_ic_white', n=n, caps=False)
    m.tube((L, 0, 0), (L + 6.0, 0, 0), rad * 0.85, 'r11_ic_black', n=n, caps=True)
    m.tube((-14.0, 0, 0), (0, 0, 0), rad * 1.35, 'r11_ic_darkgrey', n=n, caps=True)
    return m


def cone(length, r0, r1, material, n=12):
    """open cone along +X from radius r0 at x = 0 to r1 at x = length (beams and scan cones)"""
    m = Mesh(); m.tube((0, 0, 0), (length, 0, 0), r0, material, n=n, caps=False, radius2=r1); return m


def tcollar(R=61.06, n=12, sleeve=True, light='r11_ic_lightgrey'):
    """collar of the horizontal tubes (film 3299-3330, 3518-3547): 12-sided, light band 0.8-1.0 R, dark grey band
    0.62-0.8 R, mid band 0.5-0.62 R, facing -X (toward a camera coming along +X), black sleeve 0.4 R deep"""
    m = Mesh()
    I.ring_x(m, 0.0, 0.80 * R, R, light, n=n)
    I.ring_x(m, 0.0, R, 1.15 * R, 'r11_ic_darkgrey', n=n)
    I.ring_x(m, 0.0, 0.62 * R, 0.80 * R, 'r11_ic_tband', n=n)
    I.ring_x(m, 0.0, 0.50 * R, 0.62 * R, 'r11_ic_midgrey', n=n)
    if sleeve: I.wall_x(m, 0.0, 0.50 * R, 0.4 * R, 0.50 * R, 'r11_ic_tband', n=n, inward=True)
    return m


def tcollar_first(R=82.0, n=12):
    """collar of the first tube, from the film's radial profile at 110.75 (camera 125 before the collar at x 1216):
    light band 0.69-1.0 R (grey 85), dark ring 0.56-0.69 R (30), grey 0.43-0.56 R (50), lit sleeve 0.43 R deep 0.4 R"""
    m = Mesh()
    I.ring_x(m, 0.0, 0.69 * R, R, 'r11_ic_fc_light', n=n)
    I.ring_x(m, 0.0, R, 1.15 * R, 'r11_ic_darkgrey', n=n)
    I.ring_x(m, 0.0, 0.56 * R, 0.69 * R, 'r11_ic_fc_dark', n=n)
    I.ring_x(m, 0.0, 0.43 * R, 0.56 * R, 'r11_ic_fc_mid', n=n)
    I.wall_x(m, 0.0, 0.43 * R, 0.4 * R, 0.43 * R, 'r11_ic_fc_sleeve', n=n, inward=True)
    return m


def ringdark(R=100.0, w=0.25):
    m = Mesh()
    annulus_z(m, 0.0, (1 - w) * R, R, 'r11_ic_midgrey')
    annulus_z(m, -2.0, (1 - w) * R, R, 'r11_ic_black', up=False)
    return m


def funnel(r_top, r_bot, h):
    """burnt funnel from radius r_top at z=0 down to r_bot at z=-h, then the glowing bottom"""
    m = Mesh()
    steps = 6
    prof = [(-h * k / steps, r_top + (r_bot - r_top) * k / steps) for k in range(steps + 1)]
    for k, ((z0, r0), (z1, r1)) in enumerate(zip(prof, prof[1:])):
        lathe_z(m, [(z0, r0), (z1, r1)], 'r11_ic_burn%d' % min(5, k), n=12)
    annulus_z(m, -h, 0.5 * r_bot, r_bot, 'r11_ic_burn5', n=12)
    annulus_z(m, -h, 0.2 * r_bot, 0.5 * r_bot, 'r11_ic_fireglow', n=12)
    annulus_z(m, -h, 0.0, 0.2 * r_bot, 'r11_ic_fire', n=12)
    # grey 12-sided rim round the funnel mouth (film 3440-3480: light band outside a dark band)
    annulus_z(m, 0.0, r_top, r_top * 1.16, 'r11_ic_darkgrey', n=12)
    annulus_z(m, 0.0, r_top * 1.16, r_top * 1.36, 'r11_ic_lightgrey', n=12)
    return m


def bowl(prof):
    m = Mesh(); lathe_z(m, prof, 'r11_ic_orange', n=24); return m


def rim(r0=64.0, r1=170.0):
    """12-sided frame round the opening in the rust wall, facing -X (film 110.75 / 110.85 radial profiles: dark ring
    R 88-109 (~28), light band 109-126 (~85), grey outside (~66))"""
    m = Mesh()
    I.ring_x(m, 0.0, r0, 88.0, 'r11_ic_darkgrey', n=12)
    I.ring_x(m, 0.0, 88.0, 109.0, 'r11_ic_fc_dark', n=12)
    I.ring_x(m, 0.0, 109.0, 126.0, 'r11_ic_fc_light', n=12)
    I.ring_x(m, 0.0, 126.0, r1, 'r11_ic_rimout', n=12)
    I.wall_x(m, 0.0, r0, 30.0, r0, 'r11_ic_black', n=12, inward=True)
    return m


def disc(R=74.0):
    """white disc with a dark cross, facing -X (toward a camera coming along +X)"""
    m = Mesh()
    I.ring_x(m, 0.0, 0.0, R, 'r11_ic_white', n=24)
    I.ring_x(m, 0.0, R, R * 1.25, 'r11_ic_midgrey', n=24)
    for ang in (0, 90):
        b = Mesh().box((-0.5, -0.04 * R, -R), (0.0, 0.04 * R, R), 'r11_ic_midgrey')
        m.add(b, R=rot_x(ang))
    I.ring_x(m, -0.6, 0.0, 0.12 * R, 'r11_ic_cyan', n=12)
    return m


def rust_texture(n=512, seed=7):
    """the film's rust wall: dark panels (about 170 units) with brown vertical streaks and darker seams.
    Colours sampled from film frames 3305 / 3530 (dark 20-40, brown about 95 68 48)."""
    rng = np.random.default_rng(seed)
    dark = np.array([46.0, 45.0, 44.0]); brown = np.array([124.0, 96.0, 72.0])
    img = np.zeros((n, n, 3))
    xs = np.arange(n)
    # panel grid (3 x 3 per tile, jittered borders)
    bx = np.sort(np.r_[0, rng.integers(150, 190), rng.integers(330, 370), n]); by = np.sort(np.r_[0, rng.integers(150, 190), rng.integers(320, 360), n])
    def smooth1(k, w):
        a = rng.random(k); kk = np.ones(w) / w
        return np.convolve(np.r_[a, a[:w]], kk, 'same')[:k]
    for i in range(3):
        for j in range(3):
            y0, y1, x0, x1 = by[i], by[i + 1], bx[j], bx[j + 1]
            amt = rng.uniform(0.25, 0.75)
            col = smooth1(x1 - x0, 9) * 0.5 + smooth1(x1 - x0, 31) * 0.9          # vertical streaks
            row = smooth1(y1 - y0, 41) * 0.9 + 0.3                               # slow variation down the panel
            b = np.clip(amt * (col[None, :] * row[:, None]) * 1.3 - 0.1, 0, 1) ** 1.3
            img[y0:y1, x0:x1] = dark * (1 - b[..., None]) + brown * b[..., None]
            img[y0:y1, x0:x1] *= rng.uniform(0.85, 1.15)
    for b in bx[1:-1]: img[:, max(0, b - 2):b + 1] *= 0.55
    for b in by[1:-1]: img[max(0, b - 2):b + 1, :] *= 0.55
    img += rng.normal(0, 2.0, img.shape)
    return np.clip(img, 0, 255).astype(np.uint8)


# ------------------------------------------------------------------ own unlit turret, cube and can
# The stock vacum_turret / vacum_cube / food_can render BLACK in the game's unlit cells: own models instead.
# Turret after the idea of gen/models/turret.py (own copy, prefix r11_ic): model +Z up, eye toward -X, origin = the eye;
# shell 42 high x 2 * T_W wide x 2 * T_D deep at k = 1 (the stock model's size); the film's falling turret shows white
# shell panels with dark gaps between them, a red eye and dark legs.
T_TOP, T_BOT, T_W, T_D = 18.5, -23.5, 8.2, 7.6
TURRET_K = 1.0          # falling turret: fitted to the film's picture at the shaft's scale (S1)
TURRET_K_TOP = 2.5
CUBE_S = 38.0
HEAD_K = float(os.environ.get('IC_HEADK', 1.3))
RUST_TEX = int(os.environ.get('IC_RUST', 1))      # (the higher-contrast rust_texture2 scored lower: 110.25-111.0 ssim 0.49 vs 0.52)


def _shell_r(z, W=T_W):
    if z >= T_TOP or z <= T_BOT: return 0.0
    zc = -3.0
    if z >= zc:
        u = (z - zc) / (T_TOP - zc); return W * max(0.0, 1 - u ** 1.9) ** 0.55
    u = (zc - z) / (zc - T_BOT); return W * max(0.0, 1 - u ** 2.3) ** 0.5


def turret(k=1.0, n=20, light=(-0.75, 0.45, 0.5), gaps=True, legs=True):
    m = Mesh()
    zs = list(np.linspace(T_BOT, T_TOP, 22))
    body = Mesh().lathe([(z, _shell_r(z)) for z in zs], 'r11_ic_tsh', n=n, phase=0.0)
    body.transform(R=np.diag([T_D / T_W, 1.0, 1.0]))
    body.shade('r11_ic_tsh', levels=6, light=light)
    m.add(body)
    if gaps:
        # dark gaps between the side panels and the centre body, front and back (the film sees the turret's back)
        for side in (-1.0, 1.0):
            for yy, w in ((-4.6, 0.75), (4.6, 0.75)):
                zz = np.linspace(T_BOT + 1.5, T_TOP - 1.5, 26)
                for z0, z1 in zip(zz, zz[1:]):
                    r0 = _shell_r(z0); r1 = _shell_r(z1)
                    y0 = yy * r0 / T_W; y1 = yy * r1 / T_W
                    if r0 <= abs(y0) + w or r1 <= abs(y1) + w: continue
                    x0 = side * (T_D / T_W) * math.sqrt(max(0.0, r0 ** 2 - y0 ** 2))
                    x1 = side * (T_D / T_W) * math.sqrt(max(0.0, r1 ** 2 - y1 ** 2))
                    q = [V(x0 + side * 0.08, y0 - w, z0), V(x1 + side * 0.08, y1 - w, z1), V(x1 + side * 0.08, y1 + w, z1), V(x0 + side * 0.08, y0 + w, z0)]
                    if side > 0: q = q[::-1]
                    m.quad('r11_ic_tgap', *q)
    # the eye (facing -X)
    xe = -T_D - 0.1
    for r0, r1, mt in ((1.7, 2.6, 'r11_ic_tgap'), (0.0, 1.7, 'r11_ic_teye')):
        for j in range(16):
            a0 = 2 * math.pi * j / 16; a1 = 2 * math.pi * (j + 1) / 16
            q = [V(xe, r0 * math.cos(a0), r0 * math.sin(a0)), V(xe, r1 * math.cos(a0), r1 * math.sin(a0)),
                 V(xe, r1 * math.cos(a1), r1 * math.sin(a1)), V(xe, r0 * math.cos(a1), r0 * math.sin(a1))][::-1]
            if r0 < 1e-6: m.poly(mt, [q[0], q[1], q[2]])
            else: m.quad(mt, *q)
    if legs:
        lg = Mesh()
        for pts in (((-2.0, 4.0, -20.0), (-3.0, 10.5, -27.0), (-5.0, 12.5, -49.0)),
                    ((-2.0, -4.0, -20.0), (-3.0, -10.5, -27.0), (-5.0, -12.5, -49.0)),
                    ((3.0, 0.0, -21.0), (8.0, 0.0, -28.0), (9.0, 0.0, -50.0))):
            for a, b in zip(pts, pts[1:]):
                lg.tube(V(*a), V(*b), 1.4, 'r11_ic_tleg', n=6)
        lg.shade('r11_ic_tleg', levels=3, light=light)
        m.add(lg)
    return m.transform(scale=k)


def turret_open(k=1.0, light=(0.6, 0.4, 0.7)):
    """the turret with its side panels spread (film 3432-3456): narrower body, a white wing out on each side with a
    dark gun plate on its inner face"""
    m = turret(1.0, light=light, gaps=False)
    m.transform(R=np.diag([1.0, 0.75, 1.0]))
    for sy in (-1.0, 1.0):
        w = Mesh().sphere((0.0, 0.0, 0.0), 1.0, 'r11_ic_tsh', n=12, m=8, squash=(6.5, 4.0, 15.0))
        w.shade('r11_ic_tsh', levels=6, light=light)
        m.add(w, R=rot_x(sy * 12.0), offset=(1.0, sy * 10.5, -3.0))
        m.box((-6.6, sy * 9.5 - 1.6, -9.0), (-1.0, sy * 9.5 + 1.6, 7.0), 'r11_ic_tgap')
    return m.transform(scale=k)


def yfans(R=115.0, alpha_w=((-36.0, 21.0), (0.0, 9.0), (36.0, 22.0))):
    """the three yellow scan fans converging on the falling turret (film 3452-3490): flat wedges in the model's YZ plane
    facing -X, apex at the origin, opening toward +Z (picture up) at the given angles from vertical (+ = picture right =
    model -Y) and widths (degrees)"""
    m = Mesh()
    for a, w in alpha_w:
        p = []
        for j in range(5):
            phi = math.radians(a - w / 2 + w * j / 4.0)
            p.append(V(0.0, -R * math.sin(phi), R * math.cos(phi)))
        for j in range(4):
            m.tri('r11_ic_yfan', V(0.0, 0.0, 0.0), p[j + 1], p[j])
    return m


def cube(s=50.0, light=(0.4, -0.5, 0.75)):
    """storage cube (film 3361-3384: light grey faces, a round plate in the middle of each face, darker corner
    pieces), centred at the origin"""
    m = Mesh(); h = s / 2.0
    m.box((-h, -h, -h), (h, h, h), 'r11_ic_cubef')
    c = 0.3 * s
    for sx in (-1, 1):
        for sy in (-1, 1):
            for sz in (-1, 1):
                p = np.array([sx, sy, sz]) * (h - c / 2 + 0.6)
                m.box(p - c / 2, p + c / 2, 'r11_ic_cubec')
    disc = Mesh(); annulus_z(disc, 0.0, 0.0, 0.2 * s, 'r11_ic_cubed', n=16); annulus_z(disc, 0.0, 0.2 * s, 0.26 * s, 'r11_ic_cubec0', n=16)
    for R in (np.eye(3), rot_x(180), rot_x(90), rot_x(-90), rot_y(90), rot_y(-90)):
        m.add(disc, R=R, offset=R @ np.array([0.0, 0.0, h + 0.4]))
    m.shade('r11_ic_cubef', levels=4, light=light); m.shade('r11_ic_cubec', levels=4, light=light)
    return m


def can(r=7.0, hgt=18.0, light=(0.4, -0.5, 0.75)):
    m = Mesh(); m.tube((0, 0, -hgt / 2), (0, 0, hgt / 2), r, 'r11_ic_can', n=10, caps=True)
    m.shade('r11_ic_can', levels=4, light=light)
    return m


def head():
    """the lit optical head hanging in front of the exit iris (film 3500-3508: pale yellow body ~60 wide hanging from
    the top, a round mouth facing the camera at its lower end); origin = the mouth, model +Z up, mouth toward -X"""
    m = Mesh()
    body = Mesh().lathe([(-6.0, 0.0), (-6.0, 20.0), (4.0, 28.0), (30.0, 31.0), (60.0, 27.0), (100.0, 21.0), (170.0, 16.0), (170.0, 0.0)][::-1],
                        'r11_ic_headmat', n=14)
    body.shade('r11_ic_headmat', levels=4, light=(-1.0, 0.3, 0.5))
    m.add(body, R=np.diag([0.8, 1.0, 1.0]), offset=(0.0, 0.0, 6.0))
    face = Mesh(); annulus_z(face, 0.0, 9.0, 15.0, 'r11_ic_headdk', n=16); annulus_z(face, 0.0, 0.0, 9.0, 'r11_ic_headmat2', n=16)
    m.add(face, R=rot_y(-90), offset=(-25.0, 0.0, 14.0))
    return m


def lobes(L=80.0, r=40.0):
    """the head's three yellow light lobes (film 3504: up behind the head, down-left and down-right toward the camera,
    round ends ~95 across): translucent cones from the mouth"""
    m = Mesh()
    for d in ((-0.3, 0.0, 1.0), (-0.35, 0.55, -0.75), (-0.35, -0.55, -0.75)):
        d = np.array(d) / np.linalg.norm(d)
        m.tube((0, 0, 8.0), tuple(d * L + np.array([0, 0, 8.0])), 6.0, 'r11_ic_lobe', n=16, caps=True, radius2=r)
    return m


def rust_texture2(n=1024, seed=11, panels=3):
    """the film's rust walls (3519-3546, the end wall seen frontally): grey metal (median 60 60 62, dark 44) with vertical
    orange-brown rust streaks over about a quarter of the area (75th percentile 83 69 60, 90th 99 82 64, 97th 111 91 80),
    light horizontal seams with a dark line below, darker vertical seams; panels/tile per side, own noise"""
    from scipy.ndimage import gaussian_filter
    rng = np.random.default_rng(seed)
    def nz(sy, sx):
        a = gaussian_filter(rng.standard_normal((n, n)), (sy, sx), mode='wrap'); return a / a.std()
    streak = 0.45 * nz(60, 3.5) + 0.35 * nz(25, 8.0) + 0.55 * nz(90, 30.0)
    fine = nz(1.0, 1.0)
    pw = n // panels
    bias = np.zeros((n, n))
    for i in range(panels):
        for j in range(panels):
            bias[j * pw:(j + 1) * pw, i * pw:(i + 1) * pw] = rng.normal(0.0, 0.35)
    yy = (np.arange(n)[:, None] % pw) / pw
    drip = 0.5 * np.exp(-((yy - 0.08) / 0.10) ** 2)          # rust runs down from the horizontal seams
    r = streak + bias + drip
    thr = np.quantile(r, 0.72)
    rust = np.clip((r - thr) / 1.5, 0, 1) ** 0.8
    base = (58.0 + 5.0 * nz(20, 20) + 2.5 * fine)[..., None] * np.array([1.0, 1.0, 1.03])[None, None, :]
    rc = np.array([88.0, 70.0, 56.0])[None, None, :] * (1 - rust[..., None]) + np.array([128.0, 96.0, 70.0])[None, None, :] * rust[..., None]
    w = np.clip(rust * 1.6, 0, 1)[..., None]
    img = base * (1 - w) + rc * w
    for j in range(panels):                                  # seams
        y = j * pw
        img[y % n:(y + 3) % n or n, :, :] = np.array([104.0, 98.0, 92.0])
        img[(y + 3) % n:(y + 6) % n or n, :, :] *= 0.45
    for i in range(panels):
        x = i * pw + pw // 2
        img[:, x:x + 3, :] *= 0.6
    return np.clip(img, 0, 255).astype(np.uint8)


def brush_materials():
    from lib.gen import write_texture
    write_texture('corehub_intro/r11_ic_rust_tex', rust_texture2() if RUST_TEX == 2 else rust_texture())
    mat('r11_ic_rust', (1, 1, 1), base='corehub_intro/r11_ic_rust_tex', folder='corehub_intro', model=False)
    mat('r11_ic_orange', (0.53, 0.215, 0.115), folder='corehub_intro', model=False)
    mat('r11_ic_orange_dk', (0.42, 0.18, 0.11), folder='corehub_intro', model=False)
    mat('r11_ic_dark', (0.09, 0.085, 0.085), folder='corehub_intro', model=False)


def build():
    I.materials(); materials(); brush_materials()
    # the shaft irises lie flat: axis +Z, petal in the +X+Y quadrant, decorated side up (seen by the descending camera).
    save(I.quarter().transform(scale=PETAL_SCALE).transform(R=rot_y(90)), 'p9_end_shaft_iris_quarter')
    save(ring_frame(), 'ending_iris_frame')
    save(ring_frame(58.0, 70.0, 6.0), 'r11_ic_frame_s')        # light ring round the closed first iris (film 110.9)
    save(collar(61.0), 'r11_ic_collar')
    save(ringdark(100.0), 'r11_ic_ringdark')
    save(I.quarter().transform(scale=PETAL_SCALE), 'r11_ic_petal')
    save(I.quarter().transform(scale=56.0 / I.PETAL_R), 'r11_ic_petal_s')
    save(Mesh().sphere((0, 0, 0), 22.0, 'r11_ic_glowmat', n=14, m=9), 'r11_ic_glow')
    save(cone(470.0, 1.5, 9.0, 'r11_ic_yellow_faint'), 'r11_ic_longcone')       # final scanners' long cones (115.3-116.65)
    save(cone(45.0, 3.0, 15.0, 'r11_ic_yellow_faint'), 'r11_ic_scancone')
    save(head().transform(scale=HEAD_K), 'r11_ic_head')      # (film 3504: the body ~145 px wide at 262 units)
    save(lobes(95.0 * HEAD_K / 1.3, 50.0 * HEAD_K / 1.3), 'r11_ic_lobes')
    save(disc(), 'r11_ic_disc')
    save(rim(), 'r11_ic_rim')
    save(tcollar(73.0, light='r11_ic_tlight'), 'r11_ic_tcollar')          # final tube (Hough: light band about 66, grey ~90)
    save(tcollar_first(82.0), 'r11_ic_tcollar_b')        # first tube
    mo = Mesh(); I.ring_x(mo, 0.0, 75.0, 92.0, 'r11_ic_tlight', n=12); I.ring_x(mo, 0.0, 60.0, 75.0, 'r11_ic_tband', n=12)
    save(mo, 'r11_ic_tcollar_m')        # the black mouth at the end of the final tube (light band about 72-90)
    save(turret(TURRET_K, light=(0.6, 0.4, 0.7)), 'r11_ic_turret')     # the falling turret, seen from its back (film 3338-3420)
    save(turret_open(TURRET_K), 'r11_ic_turret_open')                  # the turret again near the camera in the funnel (3430-3462)
    save(yfans(), 'r11_ic_yfans')
    save(turret(TURRET_K_TOP), 'r11_ic_turret_top')         # the turret held above the white disc (film 3300-3336)
    save(cube(CUBE_S), 'r11_ic_cube')
    dc = cube(CUBE_S * 0.8)                                  # the falling debris cubes are dark in the film (3460-3490)
    for t in dc.tris: t.mat = t.mat.replace('r11_ic_cubef', 'r11_ic_dk').replace('r11_ic_cubec', 'r11_ic_dk').replace('r11_ic_cubed', 'r11_ic_dk1')
    save(dc, 'r11_ic_cube_s')
    db = Mesh().box((-22.0, -16.0, -14.0), (22.0, 16.0, 14.0), 'r11_ic_dk'); db.shade('r11_ic_dk', levels=4, light=(0.4, -0.5, 0.75))
    save(db, 'r11_ic_dbox')                                  # dark boxes / cans falling ahead of the camera (film 3354-3384)
    dcy = Mesh().tube((0, 0, -16.0), (0, 0, 16.0), 11.0, 'r11_ic_dk', n=12, caps=True); dcy.shade('r11_ic_dk', levels=4, light=(0.4, -0.5, 0.75))
    save(dcy, 'r11_ic_dcan')
    save(can(), 'r11_ic_can')
