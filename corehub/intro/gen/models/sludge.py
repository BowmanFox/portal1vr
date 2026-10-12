"""Sludge / gallery (84.6-95.7 s): textures and models (prefix r11_sg). Colours sampled from the film's frames
(sRGB medians: sludge 27,18,6; black tiles 26 with light grid lines; white ledge 182; brown rust 71,42,30 / 38,25,19;
grey shaft rust 84,73,71 / 59,46,46; plank wall 40-90; white truss 175; pink collar band 189,138,119;
copper collar 147,107,79; pole 197,161,136; panel 131,118,96).

Brush materials (corehub_intro/r11_sg_*) carry procedural textures; models use flat ramp colours."""
import math
import numpy as np
from lib.gen import Mesh, V, mat, ramp, save, write_texture, rot_x, rot_y, rot_z

TEX = {}


def _noise(h, w, sigma, seed):
    from scipy.ndimage import gaussian_filter
    r = np.random.default_rng(seed).normal(0, 1, (h, w))
    r = gaussian_filter(r, sigma, mode='wrap')
    return r / (r.std() + 1e-9)


def textures():
    """procedural textures for the brushes -> materials corehub_intro/r11_sg_<name>"""
    if TEX: return TEX
    # black tiles: dark panels with thin light grid lines on the borders
    t = np.full((128, 128, 3), 26.0) + _noise(128, 128, 3, 1)[..., None] * 2.0
    t[:2, :] = 70; t[:, :2] = 70; t[-1:, :] = 50; t[:, -1:] = 50
    TEX['tile'] = t
    # sludge: very dark olive brown, mottled
    n1 = _noise(256, 256, 6, 2); n2 = _noise(256, 256, 1.5, 3)
    s = np.stack([27 + 6 * n1 + 3 * n2, 19 + 5 * n1 + 3 * n2, 6 + 2 * n1 + 1.5 * n2], -1)
    TEX['sludge'] = s
    # white ledge: light grey panels with faint seams
    w = np.full((128, 128, 3), 183.0) + _noise(128, 128, 4, 4)[..., None] * 4
    w[:2, :] = 150; w[:, :2] = 150
    TEX['white'] = w
    # brown rust (the wall between the shaft and the gallery)
    n1 = _noise(256, 256, 10, 5); n2 = _noise(256, 256, 2, 6)
    b = np.stack([55 + 20 * n1 + 8 * n2, 34 + 11 * n1 + 5 * n2, 25 + 7 * n1 + 4 * n2], -1)
    b[:3, :] *= 0.55; b[:, :3] *= 0.55
    TEX['brown'] = b
    # grey rust (shaft walls): horizontal bands of brick-like rows
    n1 = _noise(256, 256, 8, 7); n2 = _noise(256, 256, 1.5, 8)
    rows = (np.arange(256) // 16) % 2
    base = 70 + 10 * rows[:, None] + 12 * n1 + 6 * n2          # (film walls 55-64 at 85.5 s: as bright as these)
    g = np.stack([base, base * 0.87, base * 0.84], -1)
    g[::16, :] *= 0.6
    TEX['grey'] = g
    # plank wall of the rust room: horizontal planks (dark seams), rust streaks running down
    from scipy.ndimage import gaussian_filter1d
    rng = np.random.default_rng(9)
    rowv = np.repeat(rng.normal(0, 1, 16), 16)[:256]
    streak = gaussian_filter1d(_noise(256, 256, 0.7, 10), 9, axis=0, mode='wrap')
    rust = np.clip(gaussian_filter1d(_noise(256, 256, 1.2, 11), 12, axis=0, mode='wrap'), 0, None)
    pl = 58 + 12 * rowv[:, None] + 16 * streak
    p = np.stack([pl + 42 * rust, pl * 0.90 + 20 * rust, pl * 0.80 + 4 * rust], -1)
    p[::16, :] *= 0.45; p[1::16, :] *= 0.75
    TEX['plank'] = p
    for k, a in TEX.items():
        write_texture('corehub_intro/r11_sg_%s' % k, np.clip(a, 0, 255).astype(np.uint8))
        mat('r11_sg_%s' % k, (1, 1, 1), base='corehub_intro/r11_sg_%s' % k, folder='corehub_intro', model=False)
    mat('r11_sg_flat_black', (0.07, 0.07, 0.07), folder='corehub_intro', model=False)
    mat('r11_sg_mullion', (0.33, 0.33, 0.34), folder='corehub_intro', model=False)
    mat('r11_sg_debris', (0.78, 0.70, 0.58), folder='corehub_intro', model=False)
    return TEX


def materials():
    ramp('r11_sg_cu', (0.85, 0.48, 0.30), nocull=True)           # copper collar ring (lit 147,107,79 .. dark)
    ramp('r11_sg_pink', (0.80, 0.60, 0.52), nocull=True)         # light band of the collars (189,138,119)
    mat('r11_sg_groove', (0.09, 0.07, 0.06), nocull=True)
    ramp('r11_sg_truss', (0.75, 0.72, 0.72), nocull=True)        # white truss bars (175,167,168)
    ramp('r11_sg_ctruss', (0.55, 0.36, 0.28), nocull=True)       # copper truss of the shaft
    ramp('r11_sg_pole', (0.84, 0.70, 0.60), nocull=True)         # the pole (197,161,136)
    ramp('r11_sg_panel', (0.56, 0.50, 0.41), nocull=True)        # the square panel (131,118,96)
    ramp('r11_sg_wood', (0.45, 0.27, 0.16), nocull=True)
    ramp('r11_sg_whiteobj', (0.88, 0.88, 0.86), nocull=True)
    ramp('r11_sg_metal', (0.62, 0.58, 0.56), nocull=True)
    mat('r11_sg_bridge', (0.45, 0.85, 0.85), nocull=True)
    mat('r11_sg_lit', (0.93, 0.92, 0.86), nocull=True)            # lit band of the last collars (film 2858)
    mat('r11_sg_dark', (0.06, 0.05, 0.05), nocull=True)
    mat('r11_sg_sign', (0.35, 0.62, 0.68), nocull=True)
    ramp('r11_sg_cupl', (0.45, 0.25, 0.18), nocull=True)         # copper disc of the plate
    band_materials()
    for i, c in enumerate(((0.26, 0.23, 0.21), (0.17, 0.15, 0.14), (0.36, 0.33, 0.30))):
        mat('r11_sg_shard%d' % i, c, nocull=True)                  # broken plank fragments around the wall hole
    ramp('r11_sg_beam', (0.86, 0.82, 0.74), nocull=True)          # the white beam in the hole (film 2824)


BAND = [(0, (212, 210, 198)), (45, (220, 182, 162)), (70, (204, 153, 133)), (90, (176, 125, 108)), (120, (150, 106, 93)),
        (180, (118, 82, 72))]          # film 2744 (sRGB): the light band of the exit collars, by angle from the bottom


def band_materials():
    """r11_sg_band0..11: the light band's colour in 12 sectors (sector k centred at 30k deg from model +X = world down)"""
    a = [x for x, _ in BAND]; c = np.array([q for _, q in BAND], float)
    for k in range(12):
        th = abs(((30.0 * k + 180.0) % 360.0) - 180.0)
        col = [np.interp(th, a, c[:, i]) / 255.0 for i in range(3)]
        mat('r11_sg_band%d' % k, tuple(col), nocull=True)


def collar(scale=1.0, band='r11_sg_pink3'):
    """copper collar with a light inner band (axis = model +Z): light band 0.55R..R (R = 61.06), groove, copper ring;
    the inner wall dark copper bands (the film shows no light inside the collars). band='sectors': the band shaded by
    angle like the film's exit collars (light from below: model +X points down for a horizontal axis)"""
    m = Mesh(); R = 61.06 * scale; d = 18.0 * scale; n = 24             # thin: the film's collars show a narrow dark rim inside the band
    def ring(r0, r1, z, mt):
        for k in range(n):
            a0 = 2 * math.pi * k / n; a1 = 2 * math.pi * (k + 1) / n
            p = [V(r0 * math.cos(a0), r0 * math.sin(a0), z), V(r1 * math.cos(a0), r1 * math.sin(a0), z),
                 V(r1 * math.cos(a1), r1 * math.sin(a1), z), V(r0 * math.cos(a1), r0 * math.sin(a1), z)]
            m.quad(mt, *p)
    def wall(r, z0, z1, mt):
        for k in range(n):
            a0 = 2 * math.pi * k / n; a1 = 2 * math.pi * (k + 1) / n
            p = [V(r * math.cos(a0), r * math.sin(a0), z0), V(r * math.cos(a1), r * math.sin(a1), z0),
                 V(r * math.cos(a1), r * math.sin(a1), z1), V(r * math.cos(a0), r * math.sin(a0), z1)]
            m.quad(mt, *p)
    for z in (0.0, d):
        if band == 'sectors':
            for k in range(n):
                a0 = 2 * math.pi * k / n; a1 = 2 * math.pi * (k + 1) / n; am = math.degrees(a0 + a1) / 2.0
                p = [V(0.55 * R * math.cos(a0), 0.55 * R * math.sin(a0), z), V(R * math.cos(a0), R * math.sin(a0), z),
                     V(R * math.cos(a1), R * math.sin(a1), z), V(0.55 * R * math.cos(a1), 0.55 * R * math.sin(a1), z)]
                m.quad('r11_sg_band%d' % (int(round(am / 30.0)) % 12), *p)
        elif band == 'copper':
            ring(0.55 * R, 0.8 * R, z, 'r11_sg_cu2'); ring(0.8 * R, R, z, 'r11_sg_cu1')
        else:
            ring(0.55 * R, R, z, band)
        ring(R, 1.1 * R, z, 'r11_sg_groove')
    nb = 4
    for b in range(nb):                       # inner wall: dark copper bands
        wall(0.55 * R, d * b / nb, d * (b + 1) / nb, 'r11_sg_cu1' if b % 2 == 0 else 'r11_sg_cu0')
    wall(1.1 * R, 0.0, d, 'r11_sg_cu0')
    return m


def sleeve(scale=1.0, n=24):
    """copper collar of the gallery and shaft tubes (axis = model +Z): a ribbed copper sleeve, inner radius 52,
    outer 100, 70 long (the film shows it as stacked copper bands when it passes over the lens)"""
    m = Mesh(); ri = 52.0 * scale; ro = 80.0 * scale; L = 50.0 * scale
    def ann(r0, r1, z, mt):
        for k in range(n):
            a0 = 2 * math.pi * k / n; a1 = 2 * math.pi * (k + 1) / n
            m.quad(mt, V(r0 * math.cos(a0), r0 * math.sin(a0), z), V(r1 * math.cos(a0), r1 * math.sin(a0), z),
                   V(r1 * math.cos(a1), r1 * math.sin(a1), z), V(r0 * math.cos(a1), r0 * math.sin(a1), z))
    def cyl(r, z0, z1, mt):
        for k in range(n):
            a0 = 2 * math.pi * k / n; a1 = 2 * math.pi * (k + 1) / n
            m.quad(mt, V(r * math.cos(a0), r * math.sin(a0), z0), V(r * math.cos(a1), r * math.sin(a1), z0),
                   V(r * math.cos(a1), r * math.sin(a1), z1), V(r * math.cos(a0), r * math.sin(a0), z1))
    for z in (0.0, L):
        ann(ri, 0.72 * ro, z, 'r11_sg_cu2'); ann(0.72 * ro, 0.78 * ro, z, 'r11_sg_groove'); ann(0.78 * ro, ro, z, 'r11_sg_cu1')
    bands = 5
    for b in range(bands):
        z0 = L * b / bands; z1 = L * (b + 1) / bands
        cyl(ri, z0, z1, 'r11_sg_cu2' if b % 2 == 0 else 'r11_sg_cu0')
    cyl(ro, 0.0, L, 'r11_sg_cu0')
    return m


def ring(R, depth, n=24):
    """the dark copper ring that travels ahead of the camera in the shaft (axis = model +Z, outer radius R)"""
    m = Mesh()
    def ann(r0, r1, z, mt):
        for k in range(n):
            a0 = 2 * math.pi * k / n; a1 = 2 * math.pi * (k + 1) / n
            m.quad(mt, V(r0 * math.cos(a0), r0 * math.sin(a0), z), V(r1 * math.cos(a0), r1 * math.sin(a0), z),
                   V(r1 * math.cos(a1), r1 * math.sin(a1), z), V(r0 * math.cos(a1), r0 * math.sin(a1), z))
    def cyl(r, z0, z1, mt):
        for k in range(n):
            a0 = 2 * math.pi * k / n; a1 = 2 * math.pi * (k + 1) / n
            m.quad(mt, V(r * math.cos(a0), r * math.sin(a0), z0), V(r * math.cos(a1), r * math.sin(a1), z0),
                   V(r * math.cos(a1), r * math.sin(a1), z1), V(r * math.cos(a0), r * math.sin(a0), z1))
    ann(0.62 * R, R, 0.0, 'r11_sg_cu1')
    ann(0.50 * R, 0.62 * R, 0.0, 'r11_sg_cu2')
    cyl(0.50 * R, 0.0, depth, 'r11_sg_cu0')
    ann(0.50 * R, R, depth, 'r11_sg_cu0')
    cyl(R, 0.0, depth, 'r11_sg_cu0')
    return m


def truss(L, H, D, bar, mt='r11_sg_truss', bays=None, flat=False):
    """a lattice girder along +X: length L, height H (Z), depth D (Y); square bars of side `bar`; X diagonals"""
    m = Mesh(); b = bar / 2.0
    bays = bays or max(1, int(round(L / H)))
    for y in (0.0, D):
        for z in (0.0, H):
            m.box((0, y - b, z - b), (L, y + b, z + b), mt)
    for i in range(bays + 1):
        x = L * i / bays
        for y in (0.0, D):
            m.box((x - b, y - b, 0), (x + b, y + b, H), mt)
        for z in (0.0, H):
            m.box((x - b, 0, z - b), (x + b, D, z + b), mt)
    for i in range(bays):
        x0 = L * i / bays; x1 = L * (i + 1) / bays
        for y in (0.0, D):
            for a, c in (((x0, 0), (x1, H)), ((x0, H), (x1, 0))):
                p0 = V(a[0], y, a[1]); p1 = V(c[0], y, c[1]); m.tube(p0, p1, b * 1.2, mt, n=4)
    if flat:
        for t in m.tris:
            if t.mat == mt: t.mat = mt + '3'
    else:
        m.shade(mt, levels=4, light=(0.3, -0.6, 0.75))
    return m


def disc(m, c, r, nrm, mt, n=20, r0=0.0):
    """flat disc / annulus (two-sided) centred at c with normal nrm"""
    c = V(*c); nrm = np.asarray(nrm, float); nrm /= np.linalg.norm(nrm)
    a = np.cross(nrm, [0, 0, 1.0]) if abs(nrm[2]) < 0.9 else np.cross(nrm, [1.0, 0, 0]); a /= np.linalg.norm(a); b = np.cross(nrm, a)
    for k in range(n):
        t0 = 2 * math.pi * k / n; t1 = 2 * math.pi * (k + 1) / n
        p0 = c + r * (math.cos(t0) * a + math.sin(t0) * b); p1 = c + r * (math.cos(t1) * a + math.sin(t1) * b)
        if r0 > 0:
            q0 = c + r0 * (math.cos(t0) * a + math.sin(t0) * b); q1 = c + r0 * (math.cos(t1) * a + math.sin(t1) * b)
            m.quad(mt, q0, p0, p1, q1)
        else:
            m.tri(mt, c, p0, p1)
    return m


def build():
    textures(); materials()
