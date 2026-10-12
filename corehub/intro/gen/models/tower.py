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
SLEEVE_SPLIT = 0.0        # (a mid-grey front half scored lower at 58.35-58.6 s)
DARK_SLEEVE = True        # film 1755-1758: the passing collar's inside shows as a wide dark arc
LWALL_GREY = 54           # film 1770-1870: the left third 48-56 (45 gave 42-45)
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
    M['glassbase'] = bmat(PFX + '_glassbase', (0.62, 0.61, 0.60), base='corehub_intro/%s_concrete' % PFX)
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
    mat(PFX + '_lwall', (sc(LWALL_GREY),) * 3)
    ramp(PFX + '_band', (sc(34),) * 3, (0.45, 0.65, 0.85, 1.0))
    mat(PFX + '_glass', (0.55, 0.56, 0.58), alpha=0.06, translucent=True, nocull=True)
    mat(PFX + '_white', (0.86, 0.86, 0.85))
    mat(PFX + '_whiteg', (0.55, 0.55, 0.56))
    mat(PFX + '_laser', (0.90, 0.32, 0.32), alpha=0.85, translucent=True, nocull=True)
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
    """tube collar (axis model +Z, face at Z = 0): 12-gon light band 0.86-1.0 R, mid band 0.78-0.86 R, thin dark ring
    0.73-0.78 R, open inside (film 1682 profile; 1749: the opening starts at ~0.73 R), outer side wall"""
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
        poly_ring(z, 0.78 * R, 0.86 * R, PFX + '_col_mid', up)
        poly_ring(z, 0.73 * R, 0.78 * R, PFX + '_col_dark', up)
    sleeve(0.0, tall, R, PFX + '_col_side', True)
    if DARK_SLEEVE:      # the inside: mid grey at the front, dark behind (film 1753: mid band ~15 px, dark ring ~15-20 px)
        if SLEEVE_SPLIT > 0: sleeve(0.0, tall * SLEEVE_SPLIT, 0.73 * R, PFX + '_col_mid', False)
        sleeve(tall * SLEEVE_SPLIT, tall, 0.73 * R, PFX + '_col_dark', False)
    else: sleeve(0.0, tall, 0.73 * R, PFX + '_col_mid', False)
    return m


def band(Ri, Ro, T, n=8, mt=None, rot=0.5):
    """dark octagonal ring band around the tower (axis model +Z, Z -T/2..T/2): flat annulus top and bottom, outer
    and inner walls (film 1800-1890: 12-20 grey)"""
    mt = mt or PFX + '_band'
    m = Mesh()
    def ring(z, r0, r1, up):
        for i in range(n):
            a0 = 2 * math.pi * (i + rot) / n; a1 = 2 * math.pi * (i + 1 + rot) / n
            q = [V(r0 * math.cos(a0), r0 * math.sin(a0), z), V(r1 * math.cos(a0), r1 * math.sin(a0), z),
                 V(r1 * math.cos(a1), r1 * math.sin(a1), z), V(r0 * math.cos(a1), r0 * math.sin(a1), z)]
            if not up: q = q[::-1]
            m.quad(mt, *q)
    def wall(r, z0, z1, out):
        for i in range(n):
            a0 = 2 * math.pi * (i + rot) / n; a1 = 2 * math.pi * (i + 1 + rot) / n
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
    # the column: dark grey with faint rust (film 1664: 72 69 68; 1757: 45-60) -> the concrete texture, darkened
    mat(PFX + '_colrust', (P.get('col_tint', 0.8),) * 3, base='corehub_intro/%s_concrete' % PFX)
    for k, (z, ro) in enumerate(P['bands']):
        ri, bt = P.get('band_dims', {}).get(k, (P['band_ri'], P['band_t']))
        save(band(ri, ro, bt, rot=P.get('band_rot', {}).get(k, 0.5)), '%s_band%d' % (PFX, k))
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


# ------------------------------------------------------------------------------------------------ inside the tower
def white_disc(R=48.0, n=32):
    """the white 4-segment disc (valve wheel) seen in the glass tower: face at X = 0 toward -X, 4 white quarter
    segments separated by dark spokes, dark hub and rim (film 1760-1792, 1848-1856)"""
    m = Mesh()
    def sector(r0, r1, a0, a1, mt, x=0.0):
        k = max(2, int(n * (a1 - a0) / (2 * math.pi)))
        for i in range(k):
            b0 = a0 + (a1 - a0) * i / k; b1 = a0 + (a1 - a0) * (i + 1) / k
            q = [V(x, r0 * math.cos(b0), r0 * math.sin(b0)), V(x, r1 * math.cos(b0), r1 * math.sin(b0)),
                 V(x, r1 * math.cos(b1), r1 * math.sin(b1)), V(x, r0 * math.cos(b1), r0 * math.sin(b1))]
            m.quad(mt, *q[::-1])
    gap = 0.16
    for q in range(4):
        a0 = q * math.pi / 2 + gap / 2 + math.pi / 4; a1 = (q + 1) * math.pi / 2 - gap / 2 + math.pi / 4
        sector(0.22 * R, 0.86 * R, a0, a1, PFX + '_white')
        sector(0.22 * R, 0.86 * R, a1, a1 + gap, PFX + '_spoke', x=0.5)
    sector(0.0, 0.22 * R, 0.0, 2 * math.pi, PFX + '_spoke', x=0.2)
    sector(0.86 * R, R, 0.0, 2 * math.pi, PFX + '_rimd', x=0.2)
    m.add(Mesh().lathe([(0.5, R), (14.0, R), (14.0, 0.0)], PFX + '_rimd', n=24, axis='x'))
    return m


def turret(h=46.0):
    """a turret: white egg (axis +Z) with a dark side slot and a red eye toward -X"""
    m = Mesh()
    m.sphere((0, 0, 0), h / 2, PFX + '_turw', n=12, m=8, squash=(0.55, 0.55, 1.0))
    m.shade(PFX + '_turw', levels=3, light=(-0.6, 0.3, 0.7))
    m.box((-0.3 * h, -2.0, -0.35 * h), (0.3 * h, 2.0, 0.3 * h), PFX + '_spoke')
    m.sphere((-0.27 * h, 0, 0.12 * h), 3.0, PFX + '_eye', n=6, m=4)
    return m


def laser(L, w=2.5):
    """red beam along +Z, 0..L"""
    m = Mesh(); m.box((-w, -w, 0.0), (w, w, L), PFX + '_laser'); return m


def arm(L1=110.0, L2=90.0, r=5.0):
    """white two-segment robot arm: from the origin along +Z then bent toward -Y, with dark joints"""
    m = Mesh()
    j = V(0, 0, L1); e = V(0, -L2 * 0.8, L1 + L2 * 0.6)
    m.tube((0, 0, 0), j, r, PFX + '_turw2', n=8); m.tube(j, e, r * 0.8, PFX + '_turw2', n=8)
    for q in (V(0, 0, 0), j, e): m.sphere(q, r * 1.6, PFX + '_spoke', n=8, m=6)
    return m


def diag_tube(L, ring_r=46.0, pitch=118.0, rail_sep=30.0):
    """a dark transport tube seen behind the glass tower: two black rails along +X (0..L) and dark ring collars"""
    m = Mesh()
    for sy in (1, -1):
        m.tube((0, sy * rail_sep / 2, 0), (L, sy * rail_sep / 2, 0), 3.5, PFX + '_pole', n=6, caps=False)
    x = pitch / 2
    while x < L:
        m.add(Mesh().lathe([(x - 7, ring_r - 9), (x - 7, ring_r), (x + 7, ring_r), (x + 7, ring_r - 9), (x - 7, ring_r - 9)], PFX + '_dk', n=16, axis='x'))
        x += pitch
    m.shade(PFX + '_dk', light=(-0.5, 0.4, 0.75))
    return m


def save_hangers(R=230.0, top=0.0, bottom=-380.0, n=7, r=9.0):
    """dark pipes hanging from the platform's underside (film 1664-1760: 6-8 pipes curving down to the floor and
    the horizontal pipes), on the front half of a circle of radius R (model origin = the platform's centre)"""
    materials()
    m = Mesh()
    for k in range(n):
        a = math.radians(110 + 140 * k / (n - 1))           # front half (toward -X, the camera)
        p0 = V(R * math.cos(a), R * math.sin(a), top); p1 = V(R * math.cos(a) * 1.35, R * math.sin(a) * 1.35, (top + bottom) / 2)
        p2 = V(R * math.cos(a) * 1.6, R * math.sin(a) * 1.6, bottom)
        m.tube(p0, p1, r, PFX + '_dk', n=8, caps=False); m.tube(p1, p2, r, PFX + '_dk', n=8, caps=False)
    m.add(Mesh().lathe([(top - 40, 0.0), (top - 40, 60.0), (top, 60.0), (top, 0.0)], PFX + '_dk', n=16))   # the hub below
    m.shade(PFX + '_dk', light=(-0.5, 0.4, 0.75))
    save(m, PFX + '_hangers')


def save_column(R, z0, z1, name):
    save(column(R, z0, z1), name)


def save_glass(W, H):
    """translucent light pane (model Y 0..W, Z 0..H, plane X = 0, both sides)"""
    materials()
    mat(PFX + '_glassf', (0.62, 0.63, 0.65), alpha=0.16, translucent=True, nocull=True)
    m = Mesh(); m.quad(PFX + '_glassf', V(0, 0, 0), V(0, W, 0), V(0, W, H), V(0, 0, H))
    save(m, PFX + '_glassfront')


def save_interior(beams, k=1.0):
    """k: size scale (the objects stand nearer than the film's tower, see scenes/tower.py: INT_K)"""
    materials()
    mat(PFX + '_spoke', (sc(40),) * 3)
    mat(PFX + '_rimd', (sc(28),) * 3)
    mat(PFX + '_eye', (0.95, 0.25, 0.25))
    ramp(PFX + '_turw', (0.85, 0.85, 0.84), (0.55, 0.8, 1.0))
    mat(PFX + '_turw2', (0.80, 0.80, 0.80))
    save(white_disc().transform(scale=0.9), PFX + '_wdisc')          # film 1830: disc radius ~27 px at ~730 units -> 43
    save(turret().transform(scale=k * 1.3), PFX + '_turret')
    save(arm().transform(scale=k), PFX + '_arm')
    cm = Mesh(); cm.box((-20, -20, -20), (20, 20, 20), PFX + '_dk'); cm.shade(PFX + '_dk', light=(-0.5, 0.4, 0.75)); save(cm, PFX + '_cube')
    save(diag_tube(1800.0).transform(scale=k), PFX + '_diag')
    save(diag_tube(1800.0), PFX + '_diag1')
    for i, L in enumerate(beams):
        save(laser(L, 6.0), '%s_laser%d' % (PFX, i))          # film 1790: beams ~7 px wide at ~730 units


def save_iris(h, outer):
    materials()
    save(iris_panel(h), PFX + '_iris_panel')
    save(iris_frame(h, outer), PFX + '_iris_frame')


def build():
    textures()
    materials()
    save(collar(), PFX + '_collar')
