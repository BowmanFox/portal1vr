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
import math
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
    for i, c in enumerate(((0.19, 0.15, 0.14), (0.25, 0.17, 0.14), (0.35, 0.19, 0.14), (0.47, 0.22, 0.13), (0.57, 0.245, 0.125), (0.66, 0.27, 0.125))):
        mat('r11_ic_burn%d' % i, c)
    mat('r11_ic_fire', (0.80, 0.36, 0.15))
    mat('r11_ic_fireglow', (0.74, 0.30, 0.13))
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
    mat('r11_ic_darkwall', (0.07, 0.06, 0.06))
    ramp('r11_ic_headmat', (0.93, 0.87, 0.62), (0.6, 0.72, 0.86, 1.0))


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


def rim(r0=64.0, r1=132.0):
    """12-sided frame round the opening in the rust wall, facing -X (film 110.9: light band at R ~82, dark inside)"""
    m = Mesh()
    I.ring_x(m, 0.0, r0, 76.0, 'r11_ic_darkgrey', n=12)
    I.ring_x(m, 0.0, 76.0, 88.0, 'r11_ic_lightgrey', n=12)
    I.ring_x(m, 0.0, 88.0, r1, 'r11_ic_rimout', n=12)          # film 110.9: about 66 outside the light band
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


def brush_materials():
    from lib.gen import write_texture
    write_texture('corehub_intro/r11_ic_rust_tex', rust_texture())
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
    hd = Mesh().tube((0, 0, 0), (0, 0, 115.0), 16.0, 'r11_ic_headmat', n=12, caps=True)       # the lit optical head hanging in front
    hd.sphere((0, 0, 0), 18.0, 'r11_ic_headmat', n=12, m=8)                                   # of the exit iris (film 3496-3515)
    hd.shade('r11_ic_headmat', levels=4, light=(-1.0, 0.3, 0.4))
    save(hd, 'r11_ic_head')       # their short cones at the iris (116.65-117.4)
    save(disc(), 'r11_ic_disc')
    save(rim(), 'r11_ic_rim')
    save(tcollar(73.0, light='r11_ic_tlight'), 'r11_ic_tcollar')          # final tube (Hough: light band about 66, grey ~90)
    save(tcollar(82.0), 'r11_ic_tcollar_b')        # first tube (light band about 74)
    mo = Mesh(); I.ring_x(mo, 0.0, 75.0, 92.0, 'r11_ic_tlight', n=12); I.ring_x(mo, 0.0, 60.0, 75.0, 'r11_ic_tband', n=12)
    save(mo, 'r11_ic_tcollar_m')        # the black mouth at the end of the final tube (light band about 72-90)
