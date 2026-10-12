"""Tower (film 1644-1917, 54.85-63.96 s): own textures, materials and parts (prefix r11_tw).

Colours sampled from the film (frames 1664, 1682, 1760, 1790, 1850; sRGB 0..255):
  iris (closed 1644-1654, opening 1655-1662): flat grey 10, black edges
  collars: light band 114 (0.86-1.0 R), mid band 93 (0.76-0.86 R), dark ring 31-52 (0.60-0.74 R)
  rust panels: dark 55-61, rusty 100-160 (orange-brown), mean 70-90 on the lit tower wall, 30-60 on the dim walls
  concrete pillar: 100-137 with vertical streaks; flat grey wall 88; floor block 127; poles / ring bands 12-20
Textures are procedural (numpy), no video pixels."""
import math
import numpy as np
from lib.gen import Mesh, V, mat, ramp, save, write_texture, rot_x, rot_y, rot_z

PFX = 'r11_tw'
TEX = 512
PANEL_W = 256.0           # rust texture: 2 x 4 panels of PANEL_W x PANEL_H world units per repeat
PANEL_H = 128.0
TEX_PANELS = (2, 4)


def sc(v):
    """$color (gamma 2.2) that renders as the film's sRGB value v (0..255) on a white texture (dark values need it:
    the output is sRGB-encoded linear light)"""
    if isinstance(v, (tuple, list)): return tuple(sc(x) for x in v)
    x = v / 255.0
    lin = x / 12.92 if x <= 0.04045 else ((x + 0.055) / 1.055) ** 2.4
    return lin ** (1 / 2.2)


def _blur(a, sx, sy):
    from scipy.ndimage import gaussian_filter
    return gaussian_filter(a, (sy, sx), mode='wrap')


def rust_texture(seed=7):
    """512x512: dark grey metal panels with vertically streaked orange-brown rust and light seams (the tower wall)"""
    rng = np.random.default_rng(seed)
    n = TEX; pw = n // TEX_PANELS[0]; ph = n // TEX_PANELS[1]
    big = _blur(rng.standard_normal((n, n)), 14, 30); big /= big.std()
    streak = _blur(rng.standard_normal((n, n)), 1.2, 26); streak /= streak.std()
    fine = _blur(rng.standard_normal((n, n)), 0.8, 3); fine /= fine.std()
    bias = np.zeros((n, n))
    for i in range(TEX_PANELS[0]):
        for j in range(TEX_PANELS[1]):
            bias[j * ph:(j + 1) * ph, i * pw:(i + 1) * pw] = rng.normal(0.0, 0.5)
    r = 0.5 * big + 0.5 * streak + 0.2 * fine + bias
    rust = np.clip((r - 0.55) / 1.4, 0, 1) ** 1.2
    dark = np.array([44.0, 43.0, 43.0]); mid = np.array([62.0, 60.0, 59.0]); orange = np.array([132.0, 102.0, 86.0])
    bn = _blur(rng.standard_normal((n, n)), 3, 14); bn /= bn.std()
    base_t = np.clip(0.5 + 0.3 * bn + 0.2 * fine, 0, 1)
    base = dark[None, None, :] * (1 - base_t[..., None]) + mid[None, None, :] * base_t[..., None]
    img = base * (1 - rust[..., None]) + orange[None, None, :] * rust[..., None]
    img *= (0.85 + 0.15 * np.clip(streak[..., None] * 0.5 + 1, 0, 1.4))
    for i in range(TEX_PANELS[0]):
        x = i * pw
        img[:, x % n, :] = img[:, x % n, :] * 0.4 + 95 * 0.6
        img[:, (x + 1) % n, :] *= 0.6
    for j in range(TEX_PANELS[1]):
        y = j * ph
        img[y % n, :, :] = img[y % n, :, :] * 0.4 + 95 * 0.6
        img[(y + 1) % n, :, :] *= 0.55
    return np.clip(img, 0, 255).astype(np.uint8)


def concrete_texture(seed=3):
    """256x256 light concrete with soft vertical streaks (the pillar right of the tube, 100-137)"""
    rng = np.random.default_rng(seed)
    n = 256
    st = _blur(rng.standard_normal((n, n)), 6, 40); st /= st.std()
    bl = _blur(rng.standard_normal((n, n)), 20, 20); bl /= bl.std()
    fn = _blur(rng.standard_normal((n, n)), 1, 2); fn /= fn.std()
    v = 122 + 9 * st + 6 * bl + 3 * fn
    return np.repeat(np.clip(v, 0, 255)[..., None], 3, axis=2).astype(np.uint8)


def textures():
    write_texture('corehub_intro/%s_rust' % PFX, rust_texture())
    write_texture('corehub_intro/%s_concrete' % PFX, concrete_texture())


def bmat(name, color, base='lights/white002', **kw):
    """brush material corehub_intro/<name> (UnlitGeneric)"""
    mat(name, color, base=base, folder='corehub_intro', model=False, **kw)
    return 'corehub_intro/' + name


def brush_materials():
    M = {}
    rust = 'corehub_intro/%s_rust' % PFX
    M['wall'] = bmat(PFX + '_wall', (1.0, 1.0, 1.0), base=rust)
    M['wall_dim'] = bmat(PFX + '_wall_dim', (0.62, 0.62, 0.62), base=rust)
    M['wall_dark'] = bmat(PFX + '_wall_dark', (0.40, 0.40, 0.40), base=rust)
    M['concrete'] = bmat(PFX + '_concrete_b', (1.0, 1.0, 1.0), base='corehub_intro/%s_concrete' % PFX)
    M['grey'] = bmat(PFX + '_grey', (sc(88),) * 3)
    M['grey_dim'] = bmat(PFX + '_grey_dim', (sc(45),) * 3)
    M['block'] = bmat(PFX + '_block', (1.05, 1.05, 1.05), base='corehub_intro/%s_concrete' % PFX)
    M['floor'] = bmat(PFX + '_floor', (sc(26),) * 3)
    M['ledge'] = bmat(PFX + '_ledge', (sc(94),) * 3)
    M['slab'] = bmat(PFX + '_slab', (sc(64),) * 3)
    M['black'] = bmat(PFX + '_black', (sc(14),) * 3)
    M['iris'] = bmat(PFX + '_iris_b', (sc(10),) * 3)
    return M


def materials():
    brush_materials()
    mat(PFX + '_iris', (sc(10),) * 3)
    mat(PFX + '_iris_edge', (sc(3),) * 3)
    mat(PFX + '_rail', (sc(8),) * 3)
    # collars (1682: light band 114, mid band 93, dark ring ~40)
    mat(PFX + '_col_band', (sc(114),) * 3)
    mat(PFX + '_col_mid', (sc(93),) * 3)
    mat(PFX + '_col_dark', (sc(36),) * 3)
    mat(PFX + '_col_side', (sc(80),) * 3)
    mat(PFX + '_black', (sc(12),) * 3)
    mat(PFX + '_pole', (sc(16),) * 3)
    ramp(PFX + '_band', (sc(34),) * 3, (0.45, 0.65, 0.85, 1.0))
    mat(PFX + '_glass', (0.55, 0.56, 0.58), alpha=0.06, translucent=True, nocull=True)
    mat(PFX + '_white', (0.86, 0.86, 0.85))
    mat(PFX + '_whiteg', (0.55, 0.55, 0.56))
    mat(PFX + '_laser', (0.86, 0.30, 0.30), alpha=0.75, translucent=True, nocull=True)
    ramp(PFX + '_pipe', (0.42, 0.42, 0.43), (0.35, 0.55, 0.8, 1.0))
    ramp(PFX + '_dk', (0.13, 0.13, 0.135), (0.45, 0.65, 0.85, 1.0))


# ------------------------------------------------------------------------------------------------ parts
def iris_panel(h, t=6.0, x0=1.0):
    """one iris quarter: square h x h in the model's Y-Z plane (Y 0..h, Z 0..h), face at X = x0 facing -X (just
    behind the housing's face), depth t toward +X; grey 10 face, black edges"""
    m = Mesh()
    m.box((x0, 0.0, 0.0), (x0 + t, h, h), PFX + '_iris_edge', mats={'-x': PFX + '_iris'})
    return m


def iris_frame(h, outer, t=6.0):
    """housing of the iris: plate in the plane X = 0 (facing -X) from -outer..outer with a square hole -h..h"""
    m = Mesh(); M = PFX + '_iris'
    for lo, hi in (((-outer, -outer), (outer, -h)), ((-outer, h), (outer, outer)), ((-outer, -h), (-h, h)), ((h, -h), (outer, h))):
        m.box((0.0, lo[0], lo[1]), (t, hi[0], hi[1]), M)
    return m


def collar(R=61.06, n=12, tall=20.0):
    """tube collar (axis model +Z, face at Z = 0): 12-gon light band 0.86-1.0 R, mid band 0.76-0.86 R, dark ring
    0.60-0.76 R, side wall; both faces"""
    m = Mesh()

    def poly_ring(z, r0, r1, mt, up=True):
        for i in range(n):
            a0 = 2 * math.pi * (i + 0.5) / n; a1 = 2 * math.pi * (i + 1.5) / n
            q = [V(r0 * math.cos(a0), r0 * math.sin(a0), z), V(r1 * math.cos(a0), r1 * math.sin(a0), z),
                 V(r1 * math.cos(a1), r1 * math.sin(a1), z), V(r0 * math.cos(a1), r0 * math.sin(a1), z)]
            if not up: q = q[::-1]
            m.quad(mt, *q)

    def sleeve(z0, z1, r, mt, out=True):
        for i in range(n):
            a0 = 2 * math.pi * (i + 0.5) / n; a1 = 2 * math.pi * (i + 1.5) / n
            q = [V(r * math.cos(a0), r * math.sin(a0), z0), V(r * math.cos(a1), r * math.sin(a1), z0),
                 V(r * math.cos(a1), r * math.sin(a1), z1), V(r * math.cos(a0), r * math.sin(a0), z1)]
            if not out: q = q[::-1]
            m.quad(mt, *q)
    for z, up in ((0.0, False), (tall, True)):
        poly_ring(z, 0.86 * R, R, PFX + '_col_band', up)
        poly_ring(z, 0.76 * R, 0.86 * R, PFX + '_col_mid', up)
        poly_ring(z, 0.60 * R, 0.76 * R, PFX + '_col_dark', up)
    sleeve(0.0, tall, R, PFX + '_col_side', True)
    sleeve(0.0, tall, 0.60 * R, PFX + '_col_dark', False)
    return m


def band(Ri, Ro, T, n=8, mt=None):
    """dark octagonal ring band around the tower (axis model +Z, Z -T/2..T/2): flat annulus top and bottom, outer
    and inner walls (film 1800-1890: 12-20 grey)"""
    mt = mt or PFX + '_band'
    m = Mesh()
    def ring(z, r0, r1, up):
        for i in range(n):
            a0 = 2 * math.pi * (i + 0.5) / n; a1 = 2 * math.pi * (i + 1.5) / n
            q = [V(r0 * math.cos(a0), r0 * math.sin(a0), z), V(r1 * math.cos(a0), r1 * math.sin(a0), z),
                 V(r1 * math.cos(a1), r1 * math.sin(a1), z), V(r0 * math.cos(a1), r0 * math.sin(a1), z)]
            if not up: q = q[::-1]
            m.quad(mt, *q)
    def wall(r, z0, z1, out):
        for i in range(n):
            a0 = 2 * math.pi * (i + 0.5) / n; a1 = 2 * math.pi * (i + 1.5) / n
            q = [V(r * math.cos(a0), r * math.sin(a0), z0), V(r * math.cos(a1), r * math.sin(a1), z0),
                 V(r * math.cos(a1), r * math.sin(a1), z1), V(r * math.cos(a0), r * math.sin(a0), z1)]
            if not out: q = q[::-1]
            m.quad(mt, *q)
    ring(T / 2, Ri, Ro, True); ring(-T / 2, Ri, Ro, False)
    wall(Ro, -T / 2, T / 2, True); wall(Ri, -T / 2, T / 2, False)
    m.shade(mt, light=(-0.5, 0.3, 0.8))
    return m


def column(R, z0, z1, n=24, mt=None, tile=256.0):
    """rust cylinder (axis model +Z) with cylindrical texture coordinates (tile world units per repeat)"""
    mt = mt or PFX + '_colrust'
    m = Mesh()
    circ = 2 * math.pi * R
    for i in range(n):
        a0 = 2 * math.pi * i / n; a1 = 2 * math.pi * (i + 1) / n
        p = [V(R * math.cos(a0), R * math.sin(a0), z0), V(R * math.cos(a1), R * math.sin(a1), z0),
             V(R * math.cos(a1), R * math.sin(a1), z1), V(R * math.cos(a0), R * math.sin(a0), z1)]
        u0 = circ * i / n / tile; u1 = circ * (i + 1) / n / tile; v0 = z0 / tile; v1 = z1 / tile
        m.tri(mt, p[0], p[1], p[2], uv=[(u0, v0), (u1, v0), (u1, v1)])
        m.tri(mt, p[0], p[2], p[3], uv=[(u0, v0), (u1, v1), (u0, v1)])
    return m


def disc(R0, R1, T, n=24, mt=None):
    """platform disc (axis +Z): annulus R0..R1, thickness T (top at 0)"""
    mt = mt or PFX + '_dk'
    m = Mesh(); m.add(Mesh().lathe([(-T, R0), (-T, R1), (0.0, R1), (0.0, R0)], mt, n=n))
    m.shade(mt, light=(-0.4, 0.3, 0.85))
    return m


def save_tower(P):
    """tower parts at the scene's sizes (dict P)"""
    materials()
    mat(PFX + '_colrust', (P.get('col_tint', 0.8),) * 3, base='corehub_intro/%s_rust' % PFX)
    for k, (z, ro) in enumerate(P['bands']):
        save(band(P['band_ri'], ro, P['band_t']), '%s_band%d' % (PFX, k))
    save(column(P['col_r'], P['col_z0'], P['col_z1']), PFX + '_column')
    save(disc(P['disc_r0'], P['disc_r1'], P['disc_t']), PFX + '_disc')


def save_pipe(L, r):
    """thin horizontal pipe along model +X from -L/2 to L/2 (radius r) with flange rings every 600"""
    materials()
    m = Mesh()
    m.tube((-L / 2, 0, 0), (L / 2, 0, 0), r, PFX + '_pipe', n=10, caps=False)
    x = -L / 2 + 150
    while x < L / 2:
        m.tube((x - 4, 0, 0), (x + 4, 0, 0), r * 2.2, PFX + '_pipe', n=12)
        x += 600
    m.shade(PFX + '_pipe', light=(0.2, -0.3, 0.9))
    save(m, PFX + '_pipe')


def save_iris(h, outer):
    materials()
    save(iris_panel(h), PFX + '_iris_panel')
    save(iris_frame(h, outer), PFX + '_iris_frame')


def build():
    textures()
    materials()
    save(collar(), PFX + '_collar')
