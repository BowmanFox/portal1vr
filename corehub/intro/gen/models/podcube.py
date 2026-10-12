"""Models of the pod + cube shots (39.3-54.1 s), prefix r11_pc (see scenes/podcube.py).

Collars / rings of the three tubes (axis = model +Z, the face the camera approaches at Z = 0, the ring extends to
+Z): a 12-sided flat annulus (outer radius R = 61.06, the collars' light band) with a darker inner rim (0.68-0.74 R)
and the inner wall the camera sees just after passing it (radius 0.68 R). Tones sampled from the film:
  glass tube of the first straight (39.3-41.9 s): wide mid-grey annulus;
  ringed tube down to the junction (43.8-47.9 s): dark grey rings, dense (every ~120 units);
  cube tube (50.4-54.1 s): light grey rings every ~112 units.
The cube: a weighted storage cube (light corner pads, dark grooves, a round panel on every face), edge 2 * CUBE_H.
Round 3: procedural textures (rusty panels of the rooms, lit ceiling panels) and room parts (pipes, bars, X-braced
lattices, lit panel grids) used by scenes/podcube.py."""
import math
import numpy as np
from lib.gen import Mesh, V, mat, ramp, save, write_texture

R = 61.06
N = 12
CUBE_H = 22.0
A2_SCALE = 1.0

TONES = {
    # name: (face, rim, inner wall by shade level 0..3, outside); sampled from the film under the preview's faces
    # (out/pc/tones.py: A1 39.8-41.3 s, A2 44.3-46.3 s, C 51-53.5 s)
    'a1': (0.27, 0.12, (0.30, 0.31, 0.235, 0.19), 0.12),
    'a2': (0.21, 0.09, (0.21, 0.18, 0.13, 0.11), 0.09),
    'c': (0.32, 0.13, (0.276, 0.286, 0.239, 0.25), 0.12),
    'b': (0.20, 0.08, (0.14, 0.14, 0.14, 0.14), 0.06),
    'x': (0.45, 0.25, (0.42, 0.42, 0.42, 0.42), 0.20),
}


EDGE = {'c': 0.11, 'a1': 0.14, 'a2': 0.10}          # the cube tube's collars show a thin dark outline at the outer edge


def _blur(a, sx, sy):
    from scipy.ndimage import gaussian_filter
    return gaussian_filter(a, (sy, sx), mode='wrap')


def rust_texture(seed=7, n=512, panels=(2, 2)):
    """rusty wall panels of the rooms around the tubes (film 1322-1404 the wall behind the ringed tube: grey 55-102,
    mean 78; 1285-1298 the bend's wall: mean 44 with more rust): grey-teal metal, brown rust blotches and horizontal
    streaks, light seams at the panel edges (procedural)"""
    rng = np.random.default_rng(seed)
    pw = n // panels[0]; ph = n // panels[1]
    big = _blur(rng.standard_normal((n, n)), 22, 9); big /= big.std()
    streak = _blur(rng.standard_normal((n, n)), 28, 1.3); streak /= streak.std()
    fine = _blur(rng.standard_normal((n, n)), 2.5, 0.8); fine /= fine.std()
    bias = np.zeros((n, n))
    for i in range(panels[0]):
        for j in range(panels[1]):
            bias[j * ph:(j + 1) * ph, i * pw:(i + 1) * pw] = rng.normal(0.0, 0.5)
    r = 0.55 * big + 0.45 * streak + 0.2 * fine + bias
    rust = np.clip((r - 0.45) / 1.2, 0, 1) ** 1.3
    dark = np.array([64.0, 69.0, 70.0]); mid = np.array([100.0, 104.0, 104.0]); brown = np.array([112.0, 96.0, 82.0])
    bn = _blur(rng.standard_normal((n, n)), 10, 3); bn /= bn.std()
    t = np.clip(0.55 + 0.28 * bn + 0.15 * fine, 0, 1)
    img = dark[None, None, :] * (1 - t[..., None]) + mid[None, None, :] * t[..., None]
    img = img * (1 - rust[..., None] * 0.6) + brown[None, None, :] * rust[..., None] * 0.6
    img *= (0.86 + 0.14 * np.clip(streak[..., None] * 0.5 + 1, 0, 1.4))
    for i in range(panels[0]):
        x = i * pw
        img[:, x % n, :] = img[:, x % n, :] * 0.3 + 118.0 * 0.7; img[:, (x + 1) % n, :] *= 0.55
    for j in range(panels[1]):
        y = j * ph
        img[y % n, :, :] = img[y % n, :, :] * 0.35 + 112.0 * 0.65; img[(y + 1) % n, :, :] *= 0.55
        y2 = y + ph // 2; img[y2 % n, :, :] *= 0.7
    return np.clip(img, 0, 255).astype(np.uint8)


def panel_texture(n=256):
    """the lit ceiling panels of the bend room (film 1259-1275): bright rounded slabs (200-235) in a dark frame"""
    img = np.full((n, n, 3), 34.0)
    m = n // 16; yy, xx = np.mgrid[0:n, 0:n].astype(float)
    inner = (xx > m) & (xx < n - m) & (yy > 3 * m) & (yy < n - 3 * m)
    glow = 205.0 + 30.0 * np.exp(-(((xx - n / 2) / (0.35 * n)) ** 2 + ((yy - n / 2) / (0.25 * n)) ** 2))
    img[inner] = glow[inner][:, None]
    return np.clip(img, 0, 255).astype(np.uint8)


def textures():
    write_texture('corehub_intro/r11_pc_rusttex', rust_texture())
    write_texture('corehub_intro/r11_pc_paneltex', panel_texture())


def materials():
    textures()
    for nm, c in (('r11_pc_rust', 1.0), ('r11_pc_rust_mid', 0.73), ('r11_pc_rust_dim', 0.56), ('r11_pc_rust_dark', 0.42)):
        mat(nm, (c, c, c), base='corehub_intro/r11_pc_rusttex', folder='corehub_intro', model=False)
        mat(nm + '_m', (c, c, c), base='corehub_intro/r11_pc_rusttex', nocull=True)
    mat('r11_pc_lit', (1.0, 1.0, 1.0), base='corehub_intro/r11_pc_paneltex', nocull=True)
    mat('r11_pc_black', (0.035, 0.035, 0.04), nocull=True)
    mat('r11_pc_truss', (0.10, 0.10, 0.105), nocull=True)
    ramp('r11_pc_pipe', (0.80, 0.80, 0.80), factors=(0.30, 0.48, 0.70, 1.0), nocull=True)
    ramp('r11_pc_pipedk', (0.42, 0.42, 0.43), factors=(0.35, 0.55, 0.78, 1.0), nocull=True)
    mat('r11_pc_rail', (0.03, 0.03, 0.035))
    for k, (face, rim, wall, out) in TONES.items():
        mat('r11_pc_%s_face' % k, face, nocull=True)
        mat('r11_pc_%s_rim' % k, rim, nocull=True)
        mat('r11_pc_%s_edge' % k, EDGE.get(k, face), nocull=True)
        for i, w in enumerate(wall): mat('r11_pc_%s_wall%d' % (k, i), w, nocull=True)
        mat('r11_pc_%s_out' % k, out, nocull=True)
    mat('r11_pc_cross_in', (0.56, 0.57, 0.56), nocull=True)
    mat('r11_pc_cross_out', (0.33, 0.33, 0.33), nocull=True)
    mat('r11_pc_cross_j', (0.36, 0.36, 0.36), nocull=True)
    mat('r11_pc_cross_glass', (0.12, 0.12, 0.12), alpha=0.6, translucent=True, nocull=True)
    mat('r11_pc_concrete', (0.56, 0.57, 0.56), nocull=True)
    mat('r11_pc_cube_face', (0.50, 0.50, 0.50))
    ramp('r11_pc_cube_s', (0.86, 0.86, 0.87), factors=(0.62, 0.76, 0.89, 1.0))       # the film's cube: light corner pads
    mat('r11_pc_cube_dark', (0.30, 0.30, 0.31))                                       # grooves
    mat('r11_pc_cube_ring', (0.36, 0.36, 0.37), nocull=True)
    mat('r11_pc_cube_disc', (0.72, 0.72, 0.73), nocull=True)
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
    """weighted storage cube centred on the origin (edge 2h), as the film shows it (1580-1616): light rounded corner
    pads (the brightest parts), dark grooves between them, on every face a round panel (light disc in a dark ring)"""
    m = Mesh()
    m.box((-0.93 * h,) * 3, (0.93 * h,) * 3, 'r11_pc_cube_dark')
    c = 0.40 * h; e = h
    for sx in (-1, 1):
        for sy in (-1, 1):
            for sz in (-1, 1):
                lo = (sx * (h - 2 * c) if sx > 0 else -e, sy * (h - 2 * c) if sy > 0 else -e, sz * (h - 2 * c) if sz > 0 else -e)
                hi = (e if sx > 0 else -(h - 2 * c), e if sy > 0 else -(h - 2 * c), e if sz > 0 else -(h - 2 * c))
                b = Mesh(); b.box(lo, hi, 'r11_pc_cube_s'); b.shade('r11_pc_cube_s', levels=4, light=(0.4, -0.3, 0.85)); m.add(b)
    for ax in range(3):
        for sgn in (-1, 1):
            for rr, off, mt in ((0.50 * h, 0.95, 'r11_pc_cube_ring'), (0.36 * h, 1.02, 'r11_pc_cube_disc')):
                pts = []
                for k in range(20):
                    a = 2 * math.pi * k / 20; u, w = rr * math.cos(a), rr * math.sin(a)
                    p = [0.0, 0.0, 0.0]; p[ax] = sgn * h * off; p[(ax + 1) % 3] = u; p[(ax + 2) % 3] = w; pts.append(V(*p))
                if sgn < 0: pts = pts[::-1]
                m.poly(mt, pts)
    return m


def pod(L=42.0, r=12.0):
    """the white capsule in the ringed tube's far end (axis +Z), a stretched sphere"""
    m = Mesh(); m.sphere((0, 0, 0), 1.0, 'r11_pc_pod_s', n=16, m=10, squash=(r, r, L / 2))
    m.shade('r11_pc_pod_s', levels=4, light=(0.3, 0.5, -0.8))
    return m


def build():
    materials()
    for k in TONES:
        if k == 'a2': save(ring(k, scale=A2_SCALE), 'r11_pc_ring_%s' % k)
        else: save(ring(k, outer=1.35 if k == 'a1' else 1.0), 'r11_pc_ring_%s' % k)
    save(ring('x', scale=92.0 / 61.06 * 1.0, depth=12.0), 'r11_pc_ring_xl')    # narrow dark collars (film 1424-1431)          # the junction's vertical tube (radius 92 inside 0.68 R)
    save(cube(), 'r11_pc_cube')
    save(pod(), 'r11_pc_pod')


# ------------------------------------------------------------------------------------------- room parts (round 3)
def pipe(L, r, n=12, material='r11_pc_pipe', light=(0.15, 0.35, 0.92), cap='r11_pc_black'):
    """cylinder along +X from X = 0 to L (radius r), shaded; its open end at X = 0 dark (the film's black discs)"""
    m = Mesh()
    for k in range(n):
        a0 = 2 * math.pi * k / n; a1 = 2 * math.pi * (k + 1) / n
        a = V(0, r * math.cos(a0), r * math.sin(a0)); b = V(L, r * math.cos(a0), r * math.sin(a0))
        c = V(L, r * math.cos(a1), r * math.sin(a1)); d = V(0, r * math.cos(a1), r * math.sin(a1))
        m.quad(material, a, d, c, b)
    m.shade(material, levels=4, light=light)
    if cap:
        pts = [V(1.0, 0.92 * r * math.cos(2 * math.pi * k / n), 0.92 * r * math.sin(2 * math.pi * k / n)) for k in range(n)]
        m.poly(cap, pts[::-1])
    return m


def bar(m, a, b, w, material):
    """square bar of side w from a to b"""
    a = np.asarray(a, dtype=float); b = np.asarray(b, dtype=float); d = b - a; L = np.linalg.norm(d); t = d / L
    up = np.array([0, 0, 1.0]) if abs(t[2]) < 0.9 else np.array([1.0, 0, 0])
    u = np.cross(t, up); u /= np.linalg.norm(u); w2 = np.cross(t, u)
    R = np.array([t, u, w2]).T
    m.obox((a + b) / 2, (L / 2, w / 2, w / 2), R, material)
    return m


def truss(P0, dU, dV, nU, w=7.0, material='r11_pc_truss'):
    """X-braced lattice: nU bays along dU (vector of one bay), height dV; corner P0"""
    m = Mesh(); P0 = np.asarray(P0, dtype=float); dU = np.asarray(dU, dtype=float); dV = np.asarray(dV, dtype=float)
    bar(m, P0, P0 + dU * nU, w, material); bar(m, P0 + dV, P0 + dV + dU * nU, w, material)
    for k in range(nU + 1): bar(m, P0 + dU * k, P0 + dU * k + dV, w, material)
    for k in range(nU):
        bar(m, P0 + dU * k, P0 + dU * (k + 1) + dV, w * 0.8, material); bar(m, P0 + dU * k + dV, P0 + dU * (k + 1), w * 0.8, material)
    return m


def lit_panels(origin, du, dv, nu, nv, pu, pv, material='r11_pc_lit'):
    """nu x nv lit panels (pu x pv units) on the plane spanned by unit vectors du, dv from origin (gaps included)"""
    m = Mesh(); o = np.asarray(origin, dtype=float); du = np.asarray(du, dtype=float); dv = np.asarray(dv, dtype=float)
    gu, gv = pu * 0.12, pv * 0.25
    for i in range(nu):
        for j in range(nv):
            a = o + du * (i * pu) + dv * (j * pv); b = a + du * (pu - gu); c = b + dv * (pv - gv); d = a + dv * (pv - gv)
            m.tri(material, V(*a), V(*b), V(*c), uv=[(0, 0), (1, 0), (1, 1)]); m.tri(material, V(*a), V(*c), V(*d), uv=[(0, 0), (1, 1), (0, 1)])
    return m
