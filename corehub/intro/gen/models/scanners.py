"""Scanners (74.0-83.1 s, film frames 2218-2491): own textures, materials and parts (prefix r11_sc).

The parts are built here as functions with the sizes as arguments; scenes/scanners.py measures the sizes from the film
and saves the models it needs (like lib.tube.add_bend_rails). Colours are sampled from the film frames (no pixels):
  shaft (2306, 2340): ring plates light grey 108-128 (lit side) / 72-88 (far side), thin dark outlines 30-45,
    rust walls between the ring levels (dark grey-brown with orange rust, streaks along the shaft), dark rails 25-60,
    scanner boards white 183, centre target white 156
  iris view (2455): petals white 255 (lit) / 135 (shaded), grey frame 122-125, rust wall 60-131, black posts 27,
    top beam 10, cyan lights (103 232 233), translucent yellow scan cones (166 161 93)
  round 3: the cake (2225) and the weighted cube (2253-2258) as own unlit models, the shaft's ring bands (cones or flat
    12-gon strips with lips), smaller scanner boards with mechanism, eyes with lenses
The starter's iris parts (iris_quarter, iris_frame, transfer_refined_iris_frame: lost models the old map places) are
still built under their names."""
import math
import numpy as np
from lib.gen import Mesh, V, mat, ramp, save, write_texture, rot_x, rot_y, rot_z
from models import iris as I

PETAL_SCALE = 64.0 / I.PETAL_R        # petal radius 64 (starter)
P = 'r11_sc'


# ------------------------------------------------------------------------------------------------ textures
def _blur(a, sx, sy):
    from scipy.ndimage import gaussian_filter
    return gaussian_filter(a, (sy, sx), mode='wrap')


def rust_texture(seed=23, n=512, panels=(4, 2)):
    """512x512 RGB rust panels, streaks along the texture's v axis (the shaft axis), `panels` per repeat (u, v)"""
    rng = np.random.default_rng(seed)
    pw = n // panels[0]; ph = n // panels[1]
    big = _blur(rng.standard_normal((n, n)), 8, 30); big /= big.std()
    streak = _blur(rng.standard_normal((n, n)), 1.0, 34); streak /= streak.std()
    fine = _blur(rng.standard_normal((n, n)), 0.7, 3); fine /= fine.std()
    bias = np.zeros((n, n))
    for i in range(panels[0]):
        for j in range(panels[1]):
            bias[j * ph:(j + 1) * ph, i * pw:(i + 1) * pw] = rng.normal(0.0, 0.5)
    r = 0.5 * big + 0.5 * streak + 0.18 * fine + bias
    rust = np.clip((r - 0.30) / 1.2, 0, 1) ** 1.1
    dark = np.array([36.0, 35.0, 35.0]); mid = np.array([62.0, 58.0, 56.0]); orange = np.array([132.0, 98.0, 70.0])
    bn = _blur(rng.standard_normal((n, n)), 2, 10); bn /= bn.std()
    base_t = np.clip(0.5 + 0.3 * bn + 0.2 * fine, 0, 1)
    base = dark[None, None, :] * (1 - base_t[..., None]) + mid[None, None, :] * base_t[..., None]
    img = base * (1 - rust[..., None]) + orange[None, None, :] * rust[..., None]
    img *= (0.86 + 0.14 * np.clip(streak[..., None] * 0.5 + 1, 0, 1.4))
    for i in range(panels[0]):
        x = i * pw
        img[:, x % n, :] = img[:, x % n, :] * 0.5 + 80.0 * 0.5
        img[:, (x + 1) % n, :] *= 0.55
    for j in range(panels[1]):
        y = j * ph
        img[y % n, :, :] = img[y % n, :, :] * 0.45 + 84.0 * 0.55
        img[(y + 1) % n, :, :] *= 0.55
    return np.clip(img, 0, 255).astype(np.uint8)


def choco_texture(seed=5, n=256):
    """chocolate shavings on the cake (film 2225: dark brown 50-70 with light flakes 110-140)"""
    rng = np.random.default_rng(seed)
    a = _blur(rng.standard_normal((n, n)), 1.2, 1.2); a /= a.std()
    b = _blur(rng.standard_normal((n, n)), 0.6, 0.6); b /= b.std()
    t = np.clip(0.5 + 0.22 * a + 0.12 * b, 0, 1)
    flake = (a > 1.0).astype(float) * 0.6 + (b > 1.6).astype(float) * 0.4
    dark = np.array([46.0, 30.0, 24.0]); light = np.array([118.0, 86.0, 66.0])
    img = dark[None, None] * (1 - t[..., None]) + light[None, None] * t[..., None]
    img = img * (1 - 0.5 * flake[..., None]) + np.array([150.0, 118.0, 92.0])[None, None] * 0.5 * flake[..., None]
    return np.clip(img, 0, 255).astype(np.uint8)


def textures():
    write_texture('models/corehub_intro/r11_sc_rusttex', rust_texture())
    write_texture('models/corehub_intro/r11_sc_chocotex', choco_texture())


def materials():
    I.materials()
    tex = 'models/corehub_intro/r11_sc_rusttex'
    mat('r11_sc_rust', (1.0, 1.0, 1.0), base=tex)
    mat('r11_sc_rust_dim', (0.72, 0.72, 0.72), base=tex)
    mat('r11_sc_rust_dark', (0.45, 0.45, 0.45), base=tex)
    ramp('r11_sc_ring', (0.50, 0.50, 0.50), (0.55, 0.70, 0.85, 1.0))       # ring plates (shaded by angle)
    mat('r11_sc_ring_top', (0.47, 0.47, 0.47))                              # ring plate seen from above
    mat('r11_sc_ring_lip', (0.33, 0.33, 0.33))
    mat('r11_sc_line', (0.13, 0.13, 0.13))                                  # dark outlines of the plates
    mat('r11_sc_rail', (0.10, 0.10, 0.105))
    mat('r11_sc_black', (0.02, 0.02, 0.02))
    mat('r11_sc_post', (0.10, 0.10, 0.10))
    mat('r11_sc_white', (0.78, 0.78, 0.78))
    mat('r11_sc_grey', (0.48, 0.48, 0.48))
    mat('r11_sc_target', (0.62, 0.62, 0.62))
    mat('r11_sc_red', (0.85, 0.40, 0.45), alpha=0.30, translucent=True, nocull=True)
    mat('r11_sc_yellow', (0.95, 0.85, 0.30), alpha=0.55, translucent=True, nocull=True)
    mat('r11_sc_cyan', (0.40, 0.92, 0.92))
    mat('r11_sc_col_band', (0.56, 0.56, 0.57))
    mat('r11_sc_col_wide', (0.40, 0.40, 0.40))
    mat('r11_sc_col_dark', (0.08, 0.08, 0.085))
    mat('r11_sc_col_in', (0.42, 0.42, 0.43))
    mat('r11_sc_plate', (0.48, 0.48, 0.48), alpha=0.86, translucent=True, nocull=True)
    ramp('r11_sc_eye', (0.50, 0.50, 0.50), (0.3, 0.55, 0.8, 1.0))
    mat('r11_sc_board_top', (0.80, 0.80, 0.80))
    mat('r11_sc_board', (0.40, 0.40, 0.40))
    mat('r11_sc_mech', (0.22, 0.22, 0.23))
    mat('r11_sc_plate_edge', (0.12, 0.12, 0.12), alpha=0.85, translucent=True, nocull=True)
    # cake (film 2225: shavings 46-150 brown, cherries 165 25 35, cream 225 212 196, doily 205 150 60, candle 228 216 140)
    mat('r11_sc_choco', (1.0, 1.0, 1.0), base='models/corehub_intro/r11_sc_chocotex')
    mat('r11_sc_choco_side', (0.62, 0.62, 0.62), base='models/corehub_intro/r11_sc_chocotex')
    ramp('r11_sc_cherry', (0.72, 0.10, 0.14), (0.45, 0.7, 0.9, 1.0))
    mat('r11_sc_cream', (0.88, 0.83, 0.77))
    ramp('r11_sc_doily', (0.80, 0.59, 0.24), (0.6, 0.8, 1.0))
    mat('r11_sc_candle', (0.90, 0.85, 0.55))
    mat('r11_sc_flame', (1.0, 0.95, 0.70))
    # weighted cube (film 2253-2258: corner blocks 150-200 lit / 90 shaded, body 55-75, dome 70-110, cyan strips)
    ramp('r11_sc_cube_c', (0.42, 0.42, 0.42), (0.30, 0.45, 0.62, 1.0))     # film 2255: frame mean 48 (the round-3 first try gave 71)
    ramp('r11_sc_cube_b', (0.15, 0.15, 0.16), (0.6, 0.75, 0.9, 1.0))       # body 30-40
    ramp('r11_sc_cube_dome', (0.27, 0.27, 0.28), (0.45, 0.6, 0.8, 1.0))    # dome 50-70
    mat('r11_sc_cube_rim', (0.16, 0.16, 0.17))
    mat('r11_sc_cube_cyan', (0.25, 0.62, 0.66))
    # shaft rings (film 2292-2320: light tops 105-125, dark inner lips 50-65)
    ramp('r11_sc_band', (0.50, 0.50, 0.50), (0.78, 0.86, 0.93, 1.0))
    mat('r11_sc_band_lip', (0.20, 0.20, 0.205))
    mat('r11_sc_band_mid', (0.33, 0.33, 0.33))                              # film 2340: 80-87 inside band B
    mat('r11_sc_band_under', (0.08, 0.08, 0.08))
    # scanner boards (film 2293: white plates 200-230 with black mechanism, grey eyes with dark lenses)
    mat('r11_sc_board_w', (0.86, 0.86, 0.86))
    mat('r11_sc_board_k', (0.10, 0.10, 0.10))
    mat('r11_sc_board_g', (0.52, 0.52, 0.52))
    mat('r11_sc_lens', (0.06, 0.06, 0.07))
    # brush materials
    mat('r11_sc_rail_b', (0.10, 0.10, 0.105), folder='corehub_intro', model=False)
    mat('r11_sc_floor', (0.13, 0.12, 0.115), folder='corehub_intro', model=False)
    mat('r11_sc_rust_b', (1.0, 1.0, 1.0), base=tex, folder='corehub_intro', model=False)
    mat('r11_sc_grey_b', (0.48, 0.48, 0.48), folder='corehub_intro', model=False)


# ------------------------------------------------------------------------------------------------ polygon helpers
def _ngon(r, n=12, phase=0.0):
    """vertices of a regular n-gon whose flat sides are at distance r from the centre (apothem r)"""
    R = r / math.cos(math.pi / n)
    return [(R * math.cos(phase + 2 * math.pi * (k + 0.5) / n), R * math.sin(phase + 2 * math.pi * (k + 0.5) / n)) for k in range(n)]


def annulus_z(m, z, r0, r1, material, n=12, up=True, phase=0.0):
    """flat n-gon annulus in the plane Z = z between apothems r0 < r1, facing +Z (up) or -Z"""
    A = _ngon(r0, n, phase); B = _ngon(r1, n, phase)
    for k in range(n):
        j = (k + 1) % n
        q = [V(A[k][0], A[k][1], z), V(B[k][0], B[k][1], z), V(B[j][0], B[j][1], z), V(A[j][0], A[j][1], z)]
        if not up: q = q[::-1]
        m.quad(material, *q)
    return m


def wall_z(m, z0, z1, r, material, n=12, inward=True, phase=0.0, uv=None):
    """n-gon prism wall between Z = z0 and z1 at apothem r; inward: visible from the axis. uv: (units per repeat along
    the axis, units per repeat around) -> texture coordinates (u along the axis, v around)"""
    A = _ngon(r, n, phase); side = 2 * r * math.tan(math.pi / n)
    for k in range(n):
        j = (k + 1) % n
        q = [V(A[k][0], A[k][1], z0), V(A[j][0], A[j][1], z0), V(A[j][0], A[j][1], z1), V(A[k][0], A[k][1], z1)]
        uvs = None
        if uv:
            su, sv = uv; c0 = k * side / sv; c1 = (k + 1) * side / sv
            uvs = [(z0 / su, c0), (z0 / su, c1), (z1 / su, c1), (z1 / su, c0)]
        if inward:
            q = q[::-1]
            if uvs: uvs = uvs[::-1]
        if uvs:
            m.tri(material, q[0], q[1], q[2], uv=[uvs[0], uvs[1], uvs[2]]); m.tri(material, q[0], q[2], q[3], uv=[uvs[0], uvs[2], uvs[3]])
        else:
            m.quad(material, *q)
    return m


# ------------------------------------------------------------------------------------------------ shaft parts
def ring_plate(r_in, r_out, t=12.0, line=None, n=12, phase=0.0, lip=True):
    """a ring plate of the shaft: flat n-gon annulus at Z = 0 seen from above (+Z), thickness t below it, a dark outline
    band of width `line` at its inner edge (the film's thin dark ring), an inner lip wall"""
    m = Mesh()
    line = line if line is not None else max(1.5, 0.025 * r_in)
    annulus_z(m, 0.0, r_in + line, r_out, 'r11_sc_ring_top', n, True, phase)
    annulus_z(m, 0.0, r_in, r_in + line, 'r11_sc_line', n, True, phase)
    if lip: wall_z(m, -t, 0.0, r_in, 'r11_sc_ring_lip', n, inward=True, phase=phase)
    annulus_z(m, -t, r_in, r_out, 'r11_sc_black', n, False, phase)
    return m


def shaft_wall(r, z0, z1, n=12, phase=0.0, material='r11_sc_rust', uv=(1024.0, 512.0)):
    """rust-panelled n-gon shaft wall (inside faces) from Z = z0 up to Z = z1"""
    m = Mesh(); wall_z(m, z0, z1, r, material, n, inward=True, phase=phase, uv=uv); return m


def rails_z(rho, z0, z1, width, angles=(45, 135, 225, 315), material='r11_sc_rail'):
    """square rails parallel to Z at distance rho from the axis, at the given angles (degrees)"""
    m = Mesh(); h = width / 2.0
    for a in angles:
        c, s = rho * math.cos(math.radians(a)), rho * math.sin(math.radians(a))
        m.obox(V(c, s, (z0 + z1) / 2.0), V(h, h, (z1 - z0) / 2.0), rot_z(a), material)
    return m


def cone(length, radius, material='r11_sc_red', n=16):
    """cone along +X from the apex at the origin, open base at X = length (translucent beams)"""
    m = Mesh()
    for k in range(n):
        a0 = 2 * math.pi * k / n; a1 = 2 * math.pi * (k + 1) / n
        m.tri(material, V(0, 0, 0), V(length, radius * math.cos(a0), radius * math.sin(a0)), V(length, radius * math.cos(a1), radius * math.sin(a1)))
    return m


def board(length=62.0, width=22.0):
    """a scanner board seen from above: white plate along -X from the origin (outer end), dark mechanism and a grey
    block at the inner end (film 2340: white 2:1 plates with dark details, an eye at the inner end)"""
    m = Mesh()
    m.box((-length, -width / 2, -4.0), (0.0, width / 2, 0.0), 'r11_sc_board', mats={'+z': 'r11_sc_board_top'})
    m.box((-length * 0.75, -width * 0.22, 0.0), (-length * 0.25, width * 0.22, 5.0), 'r11_sc_mech')
    m.box((-length - 10.0, -6.0, -6.0), (-length, 6.0, 3.0), 'r11_sc_grey')
    return m


def cake(R=18.5, H=14.0, n=32):
    """the cake seen from above (own model, unlit): chocolate cylinder on a scalloped gold doily, eight cherries on
    cream rings at 0.74 R, a candle in the middle. Axis +Z, bottom at Z = 0."""
    m = Mesh()
    top = [(R * math.cos(2 * math.pi * k / n), R * math.sin(2 * math.pi * k / n)) for k in range(n)]
    uv = [(0.5 + 0.5 * x / R, 0.5 + 0.5 * y / R) for x, y in top]
    for k in range(1, n - 1):
        m.tri('r11_sc_choco', V(*top[0], H), V(*top[k], H), V(*top[k + 1], H), uv=[uv[0], uv[k], uv[k + 1]])
    for k in range(n):
        j = (k + 1) % n; a, b = top[k], top[j]
        u0, u1 = k / n * 4, (k + 1) / n * 4
        m.tri('r11_sc_choco_side', V(*a, 0.5), V(*b, 0.5), V(*b, H), uv=[(u0, 0), (u1, 0), (u1, 0.4)])
        m.tri('r11_sc_choco_side', V(*a, 0.5), V(*b, H), V(*a, H), uv=[(u0, 0), (u1, 0.4), (u0, 0.4)])
    # doily: scalloped disc a little wider than the cake
    nd = 48; pts = []
    for k in range(nd):
        a = 2 * math.pi * k / nd; rr = R * (1.22 + 0.05 * math.cos(16 * a))
        pts.append((rr * math.cos(a), rr * math.sin(a)))
    for k in range(nd):
        j = (k + 1) % nd
        m.tri('r11_sc_doily', V(0, 0, 0.4), V(*pts[k], 0.0), V(*pts[j], 0.0))
    m.shade('r11_sc_doily', levels=3, light=(0.3, -0.2, 0.9))
    # cherries on cream rings
    for k in range(8):
        a = 2 * math.pi * (k + 0.5) / 8; c = V(0.74 * R * math.cos(a), 0.74 * R * math.sin(a), H)
        cr = [(c[0] + 0.17 * R * math.cos(2 * math.pi * i / 12), c[1] + 0.17 * R * math.sin(2 * math.pi * i / 12)) for i in range(12)]
        m.poly('r11_sc_cream', [V(x, y, H + 0.6) for x, y in cr])
        m.sphere(c + V(0, 0, 0.09 * R + 0.6), 0.115 * R, 'r11_sc_cherry', n=10, m=6)
    m.shade('r11_sc_cherry', levels=4, light=(0.35, -0.3, 0.88))
    # candle with a small flame
    m.tube(V(0, 0, H), V(0, 0, H + 0.6 * R), 0.06 * R, 'r11_sc_candle', n=8)
    m.sphere(V(0, 0, H + 0.68 * R), 0.06 * R, 'r11_sc_flame', n=8, m=5, squash=(1, 1, 1.6))
    return m


def cube(S=36.0, light=(0.35, -0.45, 0.82)):
    """weighted cube as the film shows it (2253-2258): dark body, big light corner blocks with chamfers, a large
    shallow dome in each face on a dark round plate, thin cyan strips on the face centre lines. Centred at the origin."""
    m = Mesh(); h = S / 2.0; k = S / 36.0
    m.box((-h + 1.5 * k,) * 3, (h - 1.5 * k,) * 3, 'r11_sc_cube_b')
    for ax in range(3):
        for sgn in (1.0, -1.0):
            n = np.zeros(3); n[ax] = sgn; u = np.zeros(3); u[(ax + 1) % 3] = 1.0; w = np.cross(n, u)
            # dark round plate and the dome
            steps = 24; r0 = 9.6 * k; zf = h - 0.6 * k
            ring = [(math.cos(2 * math.pi * i / steps), math.sin(2 * math.pi * i / steps)) for i in range(steps)]
            m.poly('r11_sc_cube_rim', [n * zf + (u * c + w * s) * r0 for c, s in ring])
            for lev in range(3):
                ra = 7.8 * k * math.cos(math.radians(25 * lev)); rb = 7.8 * k * math.cos(math.radians(25 * (lev + 1)))
                za = zf + 0.1 + 2.6 * k * math.sin(math.radians(25 * lev)); zb = zf + 0.1 + 2.6 * k * math.sin(math.radians(25 * (lev + 1)))
                for i in range(steps):
                    (ca, sa), (cb, sb) = ring[i], ring[(i + 1) % steps]
                    m.quad('r11_sc_cube_dome', n * za + (u * ca + w * sa) * ra, n * za + (u * cb + w * sb) * ra, n * zb + (u * cb + w * sb) * rb, n * zb + (u * ca + w * sa) * rb)
            m.poly('r11_sc_cube_dome', [n * (zf + 0.1 + 2.6 * k * math.sin(math.radians(75))) + (u * c + w * s) * 7.8 * k * math.cos(math.radians(75)) for c, s in ring])
            # cyan strips on the centre lines between the plate and the edges
            for (a, b) in ((u, w), (w, u)):
                for sg in (1.0, -1.0):
                    p0 = a * sg * 9.8 * k; p1 = a * sg * (h - 6.5 * k)
                    q = [n * (h - 1.45 * k) + p0 - b * 0.35 * k, n * (h - 1.45 * k) + p1 - b * 0.35 * k, n * (h - 1.45 * k) + p1 + b * 0.35 * k, n * (h - 1.45 * k) + p0 + b * 0.35 * k]
                    if np.dot(np.cross(q[1] - q[0], q[2] - q[0]), n) < 0: q = q[::-1]
                    m.poly('r11_sc_cube_cyan', q)
    # corner blocks with chamfered outer corners
    c0 = 6.5 * k
    for sx in (-1, 1):
        for sy in (-1, 1):
            for sz in (-1, 1):
                s = np.array([sx, sy, sz], dtype=float)
                blk = Mesh()
                lo = np.minimum(s * c0, s * h); hi = np.maximum(s * c0, s * h)
                blk.box(lo, hi, 'r11_sc_cube_c')
                m.add(blk)
                # chamfer: a triangle cutting the outer corner (drawn just outside)
                ch = 3.2 * k
                P = [s * h - np.eye(3)[i] * s[i] * ch + s * 0.05 for i in range(3)]
                if np.dot(np.cross(P[1] - P[0], P[2] - P[0]), s) < 0: P = P[::-1]
                m.poly('r11_sc_cube_c', P)
    m.shade('r11_sc_cube_c', levels=4, light=light)
    m.shade('r11_sc_cube_b', levels=4, light=light)
    m.shade('r11_sc_cube_dome', levels=4, light=light)
    return m


def band(r_in, z_in, r_out, z_out, lip=0.0, n=12, phase=0.0, under=True):
    """a ring band of the shaft: a 12-gon strip from (apothem r_in, z_in) to (r_out, z_out) seen from above (flat when
    z_in = z_out, a cone otherwise), a dark inner lip `lip` units deep below its inner edge, a black underside"""
    m = Mesh()
    A = _ngon(r_in, n, phase); B = _ngon(r_out, n, phase)
    for k in range(n):
        j = (k + 1) % n
        q = [V(A[k][0], A[k][1], z_in), V(B[k][0], B[k][1], z_out), V(B[j][0], B[j][1], z_out), V(A[j][0], A[j][1], z_in)]
        m.quad('r11_sc_band', *q)
        if under: m.quad('r11_sc_band_under', *[p - V(0, 0, 2.0) for p in q[::-1]])
    m.shade('r11_sc_band', levels=4, light=(0.25, -0.15, 0.95))
    if lip > 0: wall_z(m, z_in - lip, z_in, r_in, 'r11_sc_band_lip', n, inward=True, phase=phase)
    return m


def board2(length=44.0, width=15.0):
    """a smaller scanner board (film 2293: white plate ~2.9:1 with black mechanism slots and a grey block at the inner
    end); runs along -X from its origin (the outer end)"""
    m = Mesh()
    m.box((-length, -width / 2, -3.0), (0.0, width / 2, 0.0), 'r11_sc_board_g', mats={'+z': 'r11_sc_board_w'})
    for (x0, x1, y0, y1) in ((0.12, 0.30, -0.30, 0.30), (0.38, 0.62, -0.18, 0.18), (0.70, 0.86, -0.32, -0.05), (0.70, 0.86, 0.05, 0.32)):
        m.box((-length * x1, width * y0, 0.0), (-length * x0, width * y1, 0.4), 'r11_sc_board_k')
    m.box((-length * 0.62, -width * 0.06, 0.4), (-length * 0.38, width * 0.06, 2.4), 'r11_sc_board_w')
    m.box((-length - 6.0, -4.5, -4.5), (-length, 4.5, 2.0), 'r11_sc_board_g')
    return m


def eye(r=6.0):
    """scanner eye: grey ball with a dark lens facing +X"""
    m = Mesh().sphere(V(0, 0, 0), r, 'r11_sc_eye', n=12, m=8); m.shade('r11_sc_eye', levels=4, light=(0.3, -0.2, 0.9))
    m.lathe([(r * 0.82, 0.0), (r * 0.80, r * 0.42), (r * 0.70, r * 0.5)], 'r11_sc_lens', n=12, axis='x')
    return m


def collar_wide(R=61.06, tall=24.0, n=12):
    """collar of the final tube as the film shows it in the dark (82.6-83.0): one wide grey band 0.62-1.0 R"""
    m = Mesh()
    annulus_z(m, 0.0, 0.62 * R, R, 'r11_sc_col_wide', n, False)
    wall_z(m, 0.0, tall, 0.62 * R, 'r11_sc_col_dark', n, inward=True)
    wall_z(m, 0.0, tall, R, 'r11_sc_black', n, inward=False)
    annulus_z(m, tall, 0.62 * R, R, 'r11_sc_col_dark', n, True)
    return m


def collar_z(R=61.06, tall=30.0, n=12):
    """a tube collar of the final tube (light 12-gon band, dark groove, inner band), axis +Z, underside at Z = 0"""
    m = Mesh()
    annulus_z(m, 0.0, 0.78 * R, R, 'r11_sc_col_band', n, False)
    annulus_z(m, 0.0, 0.70 * R, 0.74 * R, 'r11_sc_col_in', n, False)
    annulus_z(m, 0.0, 0.74 * R, 0.78 * R, 'r11_sc_col_dark', n, False)
    wall_z(m, 0.0, tall, 0.70 * R, 'r11_sc_col_dark', n, inward=True)
    wall_z(m, 0.0, tall, R, 'r11_sc_black', n, inward=False)
    annulus_z(m, tall, 0.70 * R, R, 'r11_sc_col_band', n, True)
    return m


# ------------------------------------------------------------------------------------------------ starter parts (lost models)
def quarter_x(scale=PETAL_SCALE):
    """axis +X, petal in the +Y+Z quadrant, decorated side toward -X (as the opening iris' petal)"""
    return I.quarter().transform(scale=scale)


def ring_frame(r0=66.0, r1=78.0, depth=10.0, both=True):
    """grey ring round an iris, axis X, faces at X = 0 (toward -X) and X = depth (toward +X)"""
    m = Mesh()
    I.ring_x(m, 0.0, r0, r1, 'irisf_ring')
    I.ring_x(m, 0.0, r0 - 2.4, r0, 'irisf_ring_in')
    I.wall_x(m, 0.0, r0 - 2.4, depth, r0 - 2.4, 'irisf_ring_in', inward=True)
    I.wall_x(m, 0.0, r1, depth, r1, 'irisf_black', inward=False)
    if both:
        I.ring_x(m, depth, r0 - 2.4, r1, 'irisf_ring', down=False)
    return m


def build():
    textures(); materials()
    save(quarter_x(), 'iris_quarter')
    save(ring_frame(), 'iris_frame')
    save(ring_frame(), 'transfer_refined_iris_frame')
