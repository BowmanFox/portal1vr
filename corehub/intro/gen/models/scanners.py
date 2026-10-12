"""Scanners (74.0-83.1 s, film frames 2218-2491): own textures, materials and parts (prefix r11_sc).

The parts are built here as functions with the sizes as arguments; scenes/scanners.py measures the sizes from the film
and saves the models it needs (like lib.tube.add_bend_rails). Colours are sampled from the film frames (no pixels):
  shaft (2306, 2340): ring plates light grey 108-128 (lit side) / 72-88 (far side), thin dark outlines 30-45,
    rust walls between the ring levels (dark grey-brown with orange rust, streaks along the shaft), dark rails 25-60,
    scanner boards white 183, centre target white 156
  iris view (2455): petals white 255 (lit) / 135 (shaded), grey frame 122-125, rust wall 60-131, black posts 27,
    top beam 10, cyan lights (103 232 233), translucent yellow scan cones (166 161 93)
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


def textures():
    write_texture('models/corehub_intro/r11_sc_rusttex', rust_texture())


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
