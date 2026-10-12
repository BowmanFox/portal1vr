"""Factory (96.63-99.77 s, film frames 2896-2990) and lab (lab 1 99.97-105.27 s, frames 2996-3155; lab 2 105.67-109.64 s,
frames 3167-3286), rebuilt at film scale in cells C5 / C6 (y 9850..16300), each shot sealed by a shell of its own; the black
between the shots (and the film's fades at the cuts, measured from the frames' mean brightness) via SetScreenBlack.

factory: the camera rides a straight tube (+x) and pans 164 deg to the right about the vertical (it looks 8.5 deg off the
  tube axis at the start and 7 deg off the backward axis at the end): ride_export cannot measure that (no frame looks
  along the tube), so the camera comes from the COLMAP model (sfm/factory, all 95 frames; path straight to 0.002 of its
  length), aligned to the room axes (+x = travel, +z = up: vanishing points give pitch 0 and roll 0; fov 60 from
  vpfov.py: 59.9 / 58.6 / 60.5) and scaled by the collar passed at frame 2936 (outer edge of its white band 0.32 COLMAP
  units = 61.06 map units -> 190 map units per COLMAP unit; the camera accelerates from ~300 to ~800 units/s).
  out/fl/fac_measure.py writes data/fl_fac_ride.json. The hall is narrow at that scale (COLMAP points / depth probes):
  ceiling z +150, belts and grey machine slabs under the tube z -110 / -80, railing y -380, far wall y -700 (banded
  brown texture), +y wall y +350 (grey panels, light strip, cartons on a shelf), hanging arms y -430 / -610 / +230.
lab 1: ride_export (fl_lab1, anchor 3016) for the straight 2998-3050 (+x, 40.2 units per frame, collars and COLMAP
  agree); its bend solve failed (rails off the film), so 3051-3145 come from the COLMAP model aligned to that straight
  (out/fl/lab_align.py -> data/fl_lab1c_ride.json; 46 frames, 3 units / 0.1 deg residual), extrapolated to 3155.
lab 2: ride_export's anchor check fails (no exact axis view); COLMAP model 0 gives 3167-3209 (tube descending, +z up the
  tube, 143 units per COLMAP unit, out/fl/lab2_align.py -> data/fl_lab2_ride.json); models 1-3 chain badly (their
  orientation looks along the floor where the film looks down at it), so 3211-3286 are keys set from the film: the
  poses at 3221 / 3229.5 / 3237 solved exactly from the stub's top and the light strip (out/fl/lab2solve.py)."""
import json, math, os
import numpy as np
from lib import vmfedit as E, tube
from lib.gen import mat
from lib.ride import Ride, qangle

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BLACK = 'corehub_intro/void_black'
MDL = 'models/corehub_intro/%s.mdl'
F = 'corehub_intro/r11_fl/'

ORIGIN_FAC = (-14900.0, 11200.0, 0.0)        # cell C5 (x -16000..-9000): factory camera at frame 2896


def bmat(name, color):
    """brush material (UnlitGeneric flat colour) -> path"""
    mat(name, color, folder='corehub_intro/r11_fl', model=False)
    return F + name


def _tex_bands(rng, base, size=256):
    """brown factory wall: horizontal bands of different brightness (24-44 texels), thin dark seams, vertical grain
    (the film's walls, frames 2944 / 2980: median 33 18 9 .. 60 35 18)"""
    img = np.zeros((size, size, 3), np.float32); y = 0
    while y < size:
        h = int(rng.integers(24, 45)); k = float(rng.uniform(0.65, 1.3))
        img[y:y + h] = np.asarray(base, np.float32) * k; img[y:y + 2] *= 0.45; y += h
    grain = rng.normal(1.0, 0.12, (1, size, 1)) * rng.normal(1.0, 0.06, (size, size, 1))
    return np.clip(img * grain, 0, 255).astype(np.uint8)


def _tex_tiles(rng, base, line, cell=32, size=128, jitter=0.04):
    """square tiles of `cell` texels, 2-texel grout lines (lab walls and floors)"""
    img = np.zeros((size, size, 3), np.float32)
    for i in range(0, size, cell):
        for j in range(0, size, cell):
            img[i:i + cell, j:j + cell] = np.asarray(base, np.float32) * float(rng.uniform(1 - jitter, 1 + jitter))
    for i in range(0, size, cell):
        img[i:i + 2, :] = line; img[:, i:i + 2] = line
    return np.clip(img, 0, 255).astype(np.uint8)


def tmat(name, kind, *args):
    """brush material with an own procedural texture (corehub_intro/r11_fl/<name>.vtf) -> path"""
    from lib.gen import write_texture
    import zlib
    rng = np.random.default_rng(zlib.crc32(name.encode()))
    img = _tex_bands(rng, *args) if kind == 'bands' else _tex_tiles(rng, *args)
    write_texture(F + name + '_t', img)
    mat(name, 1.0, base=F + name + '_t', folder='corehub_intro/r11_fl', model=False)
    return F + name


def strip_mat():
    """the lab 2 light strip: violet / cyan bands along its length (film 107.5-108: 110 95 235 .. 95 190 215)"""
    from lib.gen import write_texture
    k = (0.5 + 0.5 * np.cos(np.linspace(0, 2 * np.pi, 256, endpoint=False)))[:, None, None]
    img = np.asarray((110, 95, 235), np.float32) * k + np.asarray((95, 190, 215), np.float32) * (1 - k)
    write_texture(F + 'r11_fl_l2strip_t', np.repeat(img, 64, axis=1).clip(0, 255).astype(np.uint8))
    mat('r11_fl_l2strip', 1.0, base=F + 'r11_fl_l2strip_t', folder='corehub_intro/r11_fl', model=False)
    return F + 'r11_fl_l2strip'


def tbox(v, ent, o, lo, hi, m, scale=1.0):
    """box() with the texture scale set on all its faces (map units per texel)"""
    o = np.asarray(o, dtype=float)
    pr = E.add_box(v, o + np.asarray(lo, dtype=float), o + np.asarray(hi, dtype=float), m, ent=ent)
    for sd in (pr.north, pr.south, pr.east, pr.west, pr.top, pr.bottom):
        sd.uaxis = sd.uaxis.copy(); sd.uaxis.scale = scale
        sd.vaxis = sd.vaxis.copy(); sd.vaxis.scale = scale
    return pr


def shell(v, lo, hi, mat=BLACK, t=32.0):
    """hollow box that seals a cell (inside faces `mat`)"""
    lo = np.asarray(lo, dtype=float); hi = np.asarray(hi, dtype=float)
    for ax in range(3):
        for side in (0, 1):
            a = lo.copy() - t; b = hi.copy() + t
            if side == 0: b[ax] = lo[ax]
            else: a[ax] = hi[ax]
            E.add_box(v, a, b, mat)


def box(v, ent, o, lo, hi, m):
    o = np.asarray(o, dtype=float)
    E.add_box(v, o + np.asarray(lo, dtype=float), o + np.asarray(hi, dtype=float), m, ent=ent)


def rails_x(v, ent, o, x0, x1, rho=34.0, w=1.8, m=tube.RAIL_MAT):
    """the four rails of a straight tube along +x through o (room y = z = 0)"""
    for sy in (1, -1):
        for sz in (1, -1):
            c = np.array([0.0, sy, sz]) * rho / math.sqrt(2.0)
            box(v, ent, o, (x0, c[1] - w / 2, c[2] - w / 2), (x1, c[1] + w / 2, c[2] + w / 2), m)


def camera_of(moments, origin, t0=None, t1=None):
    """[(t, pos, qangle)] from ride-json moments [t, n, mo, x, y, z, fx, fy, fz, ux, uy, uz] (room units)"""
    o = np.asarray(origin, dtype=float); out = []
    for m in moments:
        if t0 is not None and m[0] < t0: continue
        if t1 is not None and m[0] > t1: continue
        out.append((m[0], tuple(float(x) for x in o + np.array(m[3:6])), qangle(m[6:9], m[9:12])))
    return out


# ---------------------------------------------------------------------------------------------- factory
def build_factory(v, d):
    J = json.load(open(os.path.join(HERE, 'data', 'fl_fac_ride.json')))
    o = np.array(ORIGIN_FAC)
    cam = camera_of(J['moments'], o)
    d.override_camera(cam, fov=60.0)
    det = v.create_ent(classname='func_detail')
    ceil = bmat('r11_fl_fceil', (0.26, 0.15, 0.07))
    beam = bmat('r11_fl_fbeam', (0.05, 0.04, 0.03))
    wall = bmat('r11_fl_fwall', (0.19, 0.11, 0.055))
    side = bmat('r11_fl_fside', (0.06, 0.05, 0.04))
    grey = bmat('r11_fl_fgrey', (0.30, 0.29, 0.28))
    plat = bmat('r11_fl_fplat', (0.31, 0.31, 0.31))
    flo = bmat('r11_fl_ffloor', (0.17, 0.12, 0.08))
    belt = bmat('r11_fl_fbelt', (0.34, 0.20, 0.10))
    beige = bmat('r11_fl_fbeige', (0.62, 0.55, 0.46))
    org = bmat('r11_fl_forange', (0.55, 0.32, 0.10))
    light = bmat('r11_fl_flight', (0.92, 0.92, 0.90))
    post = bmat('r11_fl_fpost', (0.75, 0.75, 0.74))
    X0, X1 = -900.0, 3300.0
    box(v, det, o, (X0, -1000, 150), (X1, 420, 182), ceil)              # ceiling (lit brown panels)
    fwt = tmat('r11_fl_fwall_tx', 'bands', (58, 34, 17))
    tbox(v, det, o, (X0, -740, -320), (X1, -700, 150), fwt)             # far wall (-y): banded brown
    lwall = bmat('r11_fl_flwall', (0.31, 0.29, 0.27))
    lwt = tmat('r11_fl_flwall_tx', 'tiles', (106, 101, 95), (70, 66, 62), 64, 128, 0.08)
    tbox(v, det, o, (X0, 350, -320), (X1, 380, 150), lwt)               # left wall (+y): grey panels
    box(v, det, o, (X0, 110, 128), (X1, 350, 150), bmat('r11_fl_fmach', (0.33, 0.31, 0.29)))   # grey machinery over +y
    box(v, det, o, (X0, 300, -60), (X1, 350, -45), grey)                # conveyor shelf along the left wall
    box(v, det, o, (X0, 343, 40), (X1, 350, 52), light)                 # light strip on the left wall
    box(v, det, o, (X0, -1000, -232), (X1, 420, -200), flo)             # floor
    box(v, det, o, (X0, -130, -125), (X1, 130, -110), side)             # conveyor under the tube: belts, beige middle
    box(v, det, o, (X0, -110, -110), (X1, -28, -108), belt)
    box(v, det, o, (X0, 28, -110), (X1, 110, -108), belt)
    box(v, det, o, (X0, -22, -110), (X1, 22, -107), beige)
    for x0, x1 in ((-300, 440), (700, 1150), (1450, 1800), (2150, 2550)):  # grey machine slabs over the belts
        box(v, det, o, (x0, -125, -100), (x1, 125, -80), plat)
    for x in np.arange(X0, X1, 320.0):                                  # cross beams under the ceiling (round 3: every 320, brush budget)
        box(v, det, o, (x, -700, 128), (x + 18, 350, 150), beam)
    for y in (-520, -300, -120, 120):                                    # long beams
        box(v, det, o, (X0, y - 10, 110), (X1, y + 10, 130), beam)
    for z in (-60, -25):                                                 # railing along the -y conveyor
        box(v, det, o, (X0, -382, z - 2), (X1, -378, z + 2), side)
    # (round 3: the railing posts, 35 brushes, were dropped to keep the scene within its brush budget)
    for x in np.arange(-700.0, X1, 230.0):                              # hanging arms
        for y in (-430, -610):
            E.add_prop(v, MDL % 'r11_fl_arm', o + (x + (y == -610) * 110, y, 150), (0, 90, 0), cls='prop_static')
    for x in np.arange(-600.0, X1, 260.0):                              # grey arms hanging on the +y side
        E.add_prop(v, MDL % 'r11_fl_arm_g', o + (x, 230, 150), (0, -90, 0), cls='prop_static')
    for k, x in enumerate(np.arange(-760.0, X1, 210.0)):                 # grey machinery under the ceiling on the +y side
        E.add_prop(v, MDL % 'r11_fl_mach', o + (x, 118 + 20 * (k % 2), 150), (0, 90 * (k % 2), 0), cls='prop_static')
    for x in np.arange(-650.0, X1, 180.0):                              # arms on the conveyor (-y)
        E.add_prop(v, MDL % 'r11_fl_floorarm', o + (x, -260, -110), (0, 20, 0), cls='prop_static')
    for x in np.arange(-800.0, X1, 80.0):                               # cartons on the left conveyor
        E.add_prop(v, MDL % 'r11_fl_box_l', o + (x, 325, -45), (0, 0, 0), cls='prop_static')
    rails_x(v, det, o, X0, X1)
    for x in (100.0, 715.0, 1460.0, 2240.0, -700.0):
        E.add_prop(v, MDL % 'r11_fl_fcollar', o + (x, 0, 0), tube.axis_angles((1, 0, 0)), cls='prop_static')
    shell(v, o + (X0 - 100, -1100, -450), o + (X1 + 100, 520, 300))
    return cam


# ---------------------------------------------------------------------------------------------- helpers
def rails_path(v, P, o, name, rho=34.0, w=1.8, step=8.0):
    """the four rails swept along a horizontal polyline P (room coords, map units) as model <name>, placed at o + P[0]"""
    from lib.gen import save
    from models.tubekit import rail_sweep, materials as tk_materials
    tk_materials()
    P = np.asarray(P, dtype=float)
    keep = [0]
    for i in range(1, len(P)):
        if np.linalg.norm(P[i] - P[keep[-1]]) >= step: keep.append(i)
    if keep[-1] != len(P) - 1: keep.append(len(P) - 1)
    P = P[keep]
    T = np.gradient(P, axis=0); T /= np.linalg.norm(T, axis=1, keepdims=True)
    U = np.tile([0.0, 0.0, 1.0], (len(P), 1)); U -= T * np.sum(U * T, axis=1, keepdims=True); U /= np.linalg.norm(U, axis=1, keepdims=True)
    W = np.cross(T, U)
    save(rail_sweep(P - P[0], U, W, rho, w), name)
    E.add_prop(v, MDL % name, np.asarray(o, dtype=float) + P[0], (0, 0, 0), cls='prop_static')


def tube_body(v, P, o, name, R=66.0, n=16, material='r11_fl_glass1'):
    """glass tube wall (n-gon of radius R, faces outward, translucent: models/factorylab.py r11_fl_glass1) along a
    polyline P (room coords) as model <name>"""
    from lib.gen import save, Mesh
    P = np.asarray(P, dtype=float)
    if len(P) > 2:
        keep = [0]
        for i in range(1, len(P)):
            if np.linalg.norm(P[i] - P[keep[-1]]) >= 20.0: keep.append(i)
        if keep[-1] != len(P) - 1: keep.append(len(P) - 1)
        P = P[keep]
    T = np.gradient(P, axis=0) if len(P) > 2 else np.tile(P[1] - P[0], (2, 1))
    T = T / np.linalg.norm(T, axis=1, keepdims=True)
    U = np.tile([0.0, 0.0, 1.0], (len(P), 1)); U -= T * np.sum(U * T, axis=1, keepdims=True); U /= np.linalg.norm(U, axis=1, keepdims=True)
    W = np.cross(T, U); m = Mesh(); Q = P - P[0]
    for i in range(len(P) - 1):
        for k in range(n):
            a0 = 2 * math.pi * k / n; a1 = 2 * math.pi * (k + 1) / n
            p00 = Q[i] + R * (math.cos(a0) * U[i] + math.sin(a0) * W[i]); p01 = Q[i] + R * (math.cos(a1) * U[i] + math.sin(a1) * W[i])
            p10 = Q[i + 1] + R * (math.cos(a0) * U[i + 1] + math.sin(a0) * W[i + 1]); p11 = Q[i + 1] + R * (math.cos(a1) * U[i + 1] + math.sin(a1) * W[i + 1])
            q = [p00, p10, p11, p01]
            c = (p00 + p11) / 2 - (Q[i] + Q[i + 1]) / 2; nrm = np.cross(q[1] - q[0], q[3] - q[0])
            if nrm @ c < 0: q = q[::-1]
            m.quad(material, *q)
    save(m, name)
    E.add_prop(v, MDL % name, np.asarray(o, dtype=float) + P[0], (0, 0, 0), cls='prop_static')


def smooth_path(P, k=5):
    P = np.asarray(P, dtype=float); out = P.copy()
    for i in range(len(P)):
        a = max(0, i - k); b = min(len(P), i + k + 1); out[i] = P[a:b].mean(axis=0)
    return out


SQ_TRACK = """
::%(fn)s_tab <- [%(tab)s];
function %(fn)s(t) {
    local tab = ::%(fn)s_tab; local n = tab.len();
    if (t < tab[0][0] || t > tab[n - 1][0]) { MoveProp("%(name)s", Vector(tab[0][1], tab[0][2], tab[0][3] - 2600)); return; }
    local i = 0;
    while (i < n - 2 && t >= tab[i + 1][0]) i++;
    local f = (t - tab[i][0]) / (tab[i + 1][0] - tab[i][0]);
    MoveProp("%(name)s", Vector(tab[i][1] + (tab[i + 1][1] - tab[i][1]) * f, tab[i][2] + (tab[i + 1][2] - tab[i][2]) * f, tab[i][3] + (tab[i + 1][3] - tab[i][3]) * f));
}
"""


def track_hook(d, fn, name, rows):
    """Squirrel: move prop `name` along rows [(t, x, y, z)] (map coords, linear) while t is inside the rows' range;
    outside it the prop is parked below its place"""
    tab = ','.join('[%.4f,%.2f,%.2f,%.2f]' % tuple(r) for r in rows)
    d.append(SQ_TRACK % dict(fn=fn, tab=tab, name=name))
    d.hook('%s(t);' % fn)


def black_gap(d, t0, t1, p):
    """film is black between t0 and t1: park the camera inside a black box at p"""
    d.override_camera([(t0, tuple(p), (0.0, 0.0, 0.0)), (t1, tuple(p), (0.0, 0.0, 0.0))], fov=60.0)


# ---------------------------------------------------------------------------------------------- lab 1
ORIGIN_LAB1 = (-8500.0, 15700.0, 0.0)       # cell C6 (x -9000..-2000, y 9850..16300): camera at frame 2996


def build_lab1(v, d):
    """lab 1 (frames 2996-3155): the tube runs over a test chamber (+x, 40 units per frame, collars every ~480),
    the cube rides ahead of the camera to a pedestal; then the tube bends right (3051-3096) and runs along -y past the
    turret room while the camera pans to -x and looks down. Camera: ride_export (fl_lab1) in the straight 2996-3050,
    then the COLMAP model (sfm/lab1, aligned to the straight: 0.1 deg, 3 units) up to 3145, extrapolated to 3155."""
    o = np.array(ORIGIN_LAB1)
    R = json.load(open(os.path.join(HERE, 'data', 'fl_lab1_ride.json')))
    C = json.load(open(os.path.join(HERE, 'data', 'fl_lab1c_ride.json')))
    t_split = 3050 * 1001 / 30000.0 + 1.5 / 60.0
    mom = [m for m in R['moments'] if m[0] <= t_split]
    # COLMAP poses belong to the blended film frames (moments t_n and t_n + 1/60): place them at t_n + 1/120.
    # Round 3: frames 3145 (jump of 142 units) and 3148-3150 are outliers; from 3144 the camera goes on along -y at the
    # COLMAP speed of 3146-3147 (56 units per frame), turning as 3146-3147 say, and slows down short of the far wall
    # while the film fades out (the film still shows the wall area up to 3154)
    sh = 1 / 120.0
    cm = [[m[0] + sh] + m[1:] for m in C['moments'] if 3051 <= m[1] <= 3144]
    mom += cm
    a, b = np.array(cm[-6][3:6]), np.array(cm[-1][3:6]); vel = (b - a) / (cm[-1][0] - cm[-6][0]) * 0.8
    ori = {m[1]: m[6:12] for m in C['moments'] if m[1] in (3144, 3146, 3147)}
    for k in range(1, 24):
        t = cm[-1][0] + k / 60.0; n = 3144 + k / 2.0
        if n <= 3146: f = (n - 3144) / 2.0; ov = np.array(ori[3144]) * (1 - f) + np.array(ori[3146]) * f
        elif n <= 3147: f = n - 3146; ov = np.array(ori[3146]) * (1 - f) + np.array(ori[3147]) * f
        else: ov = np.array(ori[3147])
        ov[:3] /= np.linalg.norm(ov[:3]); ov[3:] /= np.linalg.norm(ov[3:])
        t47 = cm[-1][0] + 3 * 1001 / 30000.0                               # frame 3147: from here on (fading out) the camera
        p = b + vel * (min(t, t47) - cm[-1][0]) + 0.25 * vel * max(0.0, t - t47)   # slows down short of the far wall
        p[1] = max(p[1], -3700.0)
        mom.append([t, n, 'X'] + list(p) + list(ov))
    cam = camera_of(mom, o)
    d.override_camera(cam, fov=60.0)
    det = v.create_ent(classname='func_detail')
    tile = tmat('r11_fl_ltile_tx', 'tiles', (50, 50, 52), (92, 92, 95), 32, 128, 0.05)
    sky = bmat('r11_fl_lsky', (0.68, 0.75, 0.80))
    white = tmat('r11_fl_lwhite_tx', 'tiles', (222, 222, 224), (176, 176, 180), 32, 128, 0.02)
    red = bmat('r11_fl_lred', (0.80, 0.25, 0.20))
    XL, YW = 3650.0, 340.0
    tbox(v, det, o, (-400, YW, -1380), (XL, YW + 30, 160), tile)          # left wall (+y)
    tbox(v, det, o, (XL, -3775, -1380), (XL + 30, YW + 30, 150), tile)    # far wall (x 3650, behind the second tube)
    # sphere room, measured round 3 (COLMAP clusters of sfm/lab1 + film pixels unprojected / triangulated with the
    # camera, out/fl/r3/ptlab.py, unp.py, tri.py): far wall y -3745 (dark tiles, top z 145, sky above) with a white
    # tiled panel x 1720..3215 z -840..135 (and x 3215..3650 above z -330); side wall x 1680 (-x) from the far wall to
    # y -2945, then a wall x 1650 with a white-framed window (y -2935..-2470, z -830..-340); white floor z -1350 from the
    # far wall to y -2300 (x 1650..3520, dark beyond x 3520); exit sign z -1141 and an octagon z -1264 on the far wall
    lwhite = white; blk0 = bmat('r11_fl_lblack', (0.02, 0.02, 0.02))
    tbox(v, det, o, (1650, -3775, -1380), (XL, -3745, 145), tile)         # far wall
    tbox(v, det, o, (1720, -3745, -840), (3215, -3741, 135), lwhite)      # white panel
    tbox(v, det, o, (3215, -3745, -330), (XL, -3741, 135), lwhite)        # its upper part beyond the notch
    tbox(v, det, o, (1650, -3745, -1380), (1680, -2945, 130), tile)       # side wall (-x)
    tbox(v, det, o, (1620, -2945, -1380), (1650, -2100, 130), tile)       # window wall
    fr = bmat('r11_fl_lframe', (0.86, 0.86, 0.87))                        # the window: white frame
    for lo, hi in (((1650, -2950, -845), (1662, -2455, -830)), ((1650, -2950, -340), (1662, -2455, -325)),
                   ((1650, -2950, -830), (1662, -2935, -340)), ((1650, -2470, -830), (1662, -2455, -340))):
        box(v, det, o, lo, hi, fr)
    tbox(v, det, o, (1650, -3745, -1380), (3520, -1500, -1350), white)    # white floor
    tbox(v, det, o, (3520, -3745, -1380), (XL, -1500, -1350), tile)       # dark floor under the tube
    tbox(v, det, o, (1650, -1500, -1380), (XL, YW, -1350), tile)          # dark floor of the first chamber
    tbox(v, det, o, (-400, -2100, -1380), (1650, YW, -1350), tile)
    sgn = bmat('r11_fl_lsign', (0.75, 0.75, 0.74)); octm = bmat('r11_fl_loct', (0.55, 0.55, 0.56))
    box(v, det, o, (3120, -3745, -1165), (3240, -3740, -1120), sgn)       # exit sign
    box(v, det, o, (3000, -3745, -1305), (3085, -3735, -1222), octm)      # octagonal plate below it
    # tube: rails along the measured path (camera = tube axis)
    rails_x(v, det, o, -400, 2190)
    P = np.array([m[3:6] for m in cm if m[1] <= 3100]); P[:, 2] = 0.0
    rails_path(v, smooth_path(P, 3), o, 'r11_fl_lab1_bend')
    x2 = float(np.median([m[3] for m in cm if 3096 <= m[1] <= 3140]))
    y2 = float(P[-1][1])
    for sy in (1, -1):
        for sz in (1, -1):
            c = np.array([sy, 0.0, sz]) * 34.0 / math.sqrt(2.0)
            box(v, det, o, (x2 + c[0] - 0.9, -4500, c[2] - 0.9), (x2 + c[0] + 0.9, y2, c[2] + 0.9), tube.RAIL_MAT)
    for x in (660.0, 1134.0, 1600.0, 2199.0, 180.0, -300.0):              # dark rings in the first chamber, peach from 2199 on
        E.add_prop(v, MDL % ('r11_fl_lcollar1' if x > 2000 else ('r11_fl_lcollar' if 600 < x < 700 else 'r11_fl_lcollar0')), o + (x, 0, 0), tube.axis_angles((1, 0, 0)), cls='prop_static')
    for y in np.arange(-625.0, -3500.0, -470.0):                          # COLMAP: collar point clusters on the second tube (to -3445: film 3144)
        E.add_prop(v, MDL % 'r11_fl_lcollar', o + (x2, y, 0), tube.axis_angles((0, 1, 0)), cls='prop_static')
    Pb = smooth_path(np.array([m[3:6] for m in cm if m[1] <= 3096]) * (1, 1, 0), 3)
    Sb = np.r_[0.0, np.cumsum(np.linalg.norm(np.diff(Pb, axis=0), axis=1))]
    for sb in (630.0,):                                                    # a collar in the bend (round 3: film 3058 / 3062 ring sizes)
        i = int(np.searchsorted(Sb, sb)); i = min(i, len(Pb) - 2)
        E.add_prop(v, MDL % 'r11_fl_lcollar1', o + Pb[i], tube.axis_angles(Pb[i + 1] - Pb[i]), cls='prop_static')
    # pedestal with the orange petals under the tube at the end of the first straight
    E.add_prop(v, MDL % 'r11_fl_pedestal', o + (2125.0, 0, -22), (0, 0, 0), cls='prop_static')
    # the cube ahead of the camera (from its size: x 871 at 3010, 1572 at 3030, 2125 at 3044)
    rows = []
    for n, x, z in ((2996, 294.0, 0), (3009, 816.0, 0), (3018, 1177.0, 0), (3027, 1492.0, 0), (3036, 1809.0, 0), (3045, 2128.0, 0),
                    (3047, 2128.0, -45), (3049, 2128.0, -150), (3051, 2128.0, -300)):        # then it drops into the pedestal
        rows.append((n * 1001 / 30000.0, o[0] + x, o[1], o[2] + z))
    E.add_prop(v, MDL % 'r11_fl_cube', o + (294, 0, 0), (0, 0, 0), name='r11_fl_cube1')
    # dark enclosure the tube comes out of (2996-3005: black around, brown panels at the top left)
    dk = bmat('r11_fl_ldark', (0.03, 0.03, 0.03)); br = bmat('r11_fl_lbrown', (0.25, 0.17, 0.11))
    box(v, det, o, (-420, -150, 90), (560, 150, 120), dk)
    box(v, det, o, (-420, -700, 88), (560, -150, 120), br)                # film 2998-3003: brown wood ceiling across the top
    box(v, det, o, (-420, 150, 88), (560, 700, 120), br)
    box(v, det, o, (-420, 90, -150), (560, 120, 90), dk)
    box(v, det, o, (-420, -150, -120), (560, 150, -90), dk)
    box(v, det, o, (-420, -120, -90), (560, -90, 90), dk)
    box(v, det, o, (-420, -150, 120), (480, 400, 160), br)                # brown panels above / left of the mouth
    box(v, det, o, (-420, 150, -400), (480, 180, 120), br)
    E.add_prop(v, MDL % 'r11_fl_lplate', o + (560.0, 0, 0), tube.axis_angles((1, 0, 0)), cls='prop_static')   # tunnel end: round hole
    # the glass tube seen from outside in the bend and along -y (dark, faces outward: invisible from inside)
    tube_body(v, smooth_path(np.array([m[3:6] for m in cm if m[1] <= 3100]) * (1, 1, 0), 3), o, 'r11_fl_lab1_glass1')
    tube_body(v, np.array([[x2, y2, 0.0], [x2, -4500.0, 0.0]]), o, 'r11_fl_lab1_glass2')
    track_hook(d, 'FL_Cube1', 'r11_fl_cube1', rows)
    # three spheres hanging on red cables (COLMAP clusters on them and two-frame triangulation of their centres at
    # 104.25 / 104.5 s; radius 68 from their size in the film: 38 px at 862 units)
    for k, (x, y, z) in enumerate([(3070, -3340, -245), (2575, -3425, -285), (1955, -3290, -245)]):
        E.add_prop(v, MDL % 'r11_fl_sphere', o + (x, y, z), (0, math.degrees(math.atan2(-2500 - y, 3480 - x)), 0), cls='prop_static')
        box(v, det, o, (x - 3, y - 3, z + 60), (x + 3, y + 3, 400), red)
    shell(v, o + (-500, -4700, -1450), o + (XL + 150, YW + 150, 1200), mat=sky)
    return cam


# ---------------------------------------------------------------------------------------------- lab 2
ORIGIN_LAB2 = (-10500.0, 12300.0, 3800.0)     # cell C5 (x -10800..-9300, y 11300..16100 with the chamber): camera at frame 3167


def checker_mat(name, a, b, n=8, size=128):
    """checker texture (n x n squares of the two grey levels a, b) -> brush material path"""
    from lib.gen import write_texture
    k = size // n; ij = (np.arange(size)[:, None] // k + np.arange(size)[None, :] // k) % 2
    img = np.where(ij[..., None] == 1, np.asarray(a, np.float32), np.asarray(b, np.float32))
    img[::k, :] *= 0.85; img[:, ::k] *= 0.85
    write_texture(F + name + '_t', img.clip(0, 255).astype(np.uint8))
    mat(name, 1.0, base=F + name + '_t', folder='corehub_intro/r11_fl', model=False)
    return F + name


def build_lab2(v, d):
    """lab 2 (frames 3167-3286): the camera descends a dark vertical tube (-z, 40 units per frame; COLMAP model 0 of
    sfm/lab2, +z = up the tube, 143 units per COLMAP unit: out/fl/lab2_align.py -> data/fl_lab2_ride.json), comes out of
    the chamber's ceiling and flies over the white chamber, then dives into the glass cylinder and down below the floor.
    Round 3: 3210-3239 are COLMAP model 1 in its own level frame: floor plane fitted to the checker pad points, +y along
    the light strip, 91.2 units per COLMAP unit (camera height at 3210 = model 0's), out/fl/r3/l2floor.py, l2meas.py,
    l2export.py -> data/fl_lab2b_ride.json: the camera flies level at ~2060 above the floor while it pitches from 37 to
    80 deg down. The chamber is placed from the same frame: peach wall x -295, dark wall x 1174, light strip x 846..1157
    (y -627..3204), checker pad x -30..480 y 1106..1654, glass cylinder axis (170, 1880), radius ~255, top ~1250 above
    the floor. 3240-3286 (models 2/3 do not chain): set from the film, down the cylinder's axis."""
    o = np.array(ORIGIN_LAB2)
    J = json.load(open(os.path.join(HERE, 'data', 'fl_lab2_ride.json')))['models']
    mom = [m for m in J['0'] if m[1] <= 3209]
    M1 = json.load(open(os.path.join(HERE, 'data', 'fl_lab2b_ride.json')))
    m1 = [m for m in M1['moments'] if 3210 <= m[1] <= 3239]
    mom += m1
    CX, CY, ZF = 170.0, 1880.0, -3768.0
    last = m1[-1]; up0 = np.array(last[9:12]); up0[2] = 0.0; up0 /= np.linalg.norm(up0)
    keys = [(last[1], np.array(last[3:6]), np.array(last[6:9])),
            (3251, np.array([CX, CY, ZF + 2050]), np.array([0.0, 0.0, -1.0])),        # film 3248-3252: high above the top ring
            (3260, np.array([CX, CY, ZF + 1150]), np.array([0.0, 0.0, -1.0])),
            (3266, np.array([CX, CY, ZF - 120]), np.array([0.0, 0.0, -1.0])),        # film 3268-3284: dark tube, copper rings
            (3286, np.array([CX, CY, ZF - 450]), np.array([0.0, 0.0, -1.0]))]
    for (n0, p0, f0), (n1, p1, f1) in zip(keys, keys[1:]):
        for k in range(1 if n0 == last[1] else 0, int(round(2 * (n1 - n0)))):
            f = k / (2.0 * (n1 - n0)); n = n0 + k / 2.0; g = 0.5 - 0.5 * math.cos(math.pi * f)
            p = p0 + (p1 - p0) * g; fw = f0 + (f1 - f0) * g + np.array([1e-3, 0, 0]); fw /= np.linalg.norm(fw)
            up = up0 - fw * (up0 @ fw); up /= np.linalg.norm(up)
            mom.append([n * 1001 / 30000.0 + 1 / 120.0, n, 'S'] + list(p) + list(fw) + list(up))
    mom.sort(key=lambda m: m[0])
    cam = camera_of(mom, o)
    d.override_camera(cam, fov=60.0)
    E.add_prop(v, MDL % 'r11_fl_ringstack2', o + (CX, CY, ZF), (0, 0, 0), cls='prop_static')
    det = v.create_ent(classname='func_detail')
    shaft = bmat('r11_fl_l2shaft', (0.07, 0.07, 0.075))
    white = bmat('r11_fl_l2white', (0.80, 0.80, 0.80))
    floor = tmat('r11_fl_l2floor_tx', 'tiles', (208, 208, 210), (168, 168, 172), 32, 128, 0.02)
    peach = bmat('r11_fl_l2peach', (0.72, 0.60, 0.55))
    dark = tmat('r11_fl_l2dark_tx', 'tiles', (30, 30, 32), (62, 62, 66), 32, 128, 0.05)
    ZC = -1640.0                                                          # chamber ceiling (tube mouth): above the level flight
    shaft2 = bmat('r11_fl_l2shaft2', (0.20, 0.20, 0.21))                  # lit by the chamber near the mouth
    for z0, z1, m in ((-700, 700, shaft), (ZC, -700, shaft2)):
        for lo, hi in (((-170, -170, z0), (-150, 170, z1)), ((150, -170, z0), (170, 170, z1)),
                       ((-150, -170, z0), (150, -150, z1)), ((-150, 150, z0), (150, 170, z1))):
            box(v, det, o, lo, hi, m)
    for sx in (1, -1):
        for sy in (1, -1):
            c = np.array([sx, sy, 0.0]) * 34.0 / math.sqrt(2.0)
            box(v, det, o, (c[0] - 0.9, c[1] - 0.9, ZC), (c[0] + 0.9, c[1] + 0.9, 700), tube.RAIL_MAT)
    for z in np.arange(300.0, -1600.0, -300.0):
        E.add_prop(v, MDL % 'r11_fl_lcollar', o + (0, 0, z), (0, 0, 0), cls='prop_static')
    X0, X1, Y0, Y1 = -295.0, 1174.0, -1000.0, 3760.0
    # ceiling with the tube mouth
    box(v, det, o, (X0, Y0, ZC), (X1, -170, ZC + 30), white)
    box(v, det, o, (X0, 170, ZC), (X1, Y1, ZC + 30), white)
    box(v, det, o, (X0, -170, ZC), (-170, 170, ZC + 30), white)
    box(v, det, o, (170, -170, ZC), (X1, 170, ZC + 30), white)
    # floor with a hole under the cylinder (the camera drops through it at the end)
    HX0, HX1, HY0, HY1 = CX - 230, CX + 230, CY - 230, CY + 230
    for lo, hi in (((X0, Y0), (HX0, Y1)), ((HX1, Y0), (X1, Y1)), ((HX0, Y0), (HX1, HY0)), ((HX0, HY1), (HX1, Y1))):
        tbox(v, det, o, (lo[0], lo[1], ZF - 30), (hi[0], hi[1], ZF), floor)
    box(v, det, o, (X0 - 30, Y0, ZF - 30), (X0, Y1, -2400), peach)        # peach wall (-x), dark above it
    tbox(v, det, o, (X0 - 30, Y0, -2400), (X0, Y1, ZC), dark)
    tbox(v, det, o, (X1, Y0, ZF - 30), (X1 + 30, Y1, ZC), dark)           # dark wall (+x)
    tbox(v, det, o, (X0, Y0 - 30, ZF - 30), (X1, Y0, ZC), dark)
    tbox(v, det, o, (X0, Y1, ZF - 30), (X1, Y1 + 30, ZC), dark)
    tbox(v, det, o, (846, -627, ZF), (1157, 3204, ZF + 4), strip_mat(), 6.0)   # light strip on the floor (along y)
    tbox(v, det, o, (-30, 1106, ZF), (480, 1654, ZF + 2), checker_mat('r11_fl_l2check_tx', (150, 150, 152), (205, 205, 207)), 4.0)
    # below the floor: the black shaft the camera drops into at the end (the shell's black, brown collars)
    for z in (ZF - 130.0, ZF - 250.0, ZF - 370.0):
        E.add_prop(v, MDL % 'r11_fl_lcollar', o + (CX, CY, z), (0, 0, 0), cls='prop_static')
    shell(v, o + (X0 - 150, Y0 - 150, ZF - 760), o + (X1 + 150, Y1 + 150, 900))
    return cam


def apply(v, d):
    fac = build_factory(v, d)
    l1 = build_lab1(v, d)
    l2 = build_lab2(v, d)
    dark = tuple(np.array(ORIGIN_FAC) + (3350.0, 470.0, 270.0))          # inside the factory's black shell, facing its wall
    black_gap(d, fac[-1][0] + 0.004, l1[0][0] - 0.004, dark)
    black_gap(d, l1[-1][0] + 0.004, l2[0][0] - 0.004, dark)
    black_gap(d, l2[-1][0] + 0.004, 109.85, dark)
    # the film's fades at the cuts (mean brightness of the frames relative to the shot's level, gamma space)
    fades = [(2985, 1.0), (2986, 0.83), (2987, 0.646), (2988, 0.461), (2989, 0.289), (2990, 0.096), (2991, 0.0),
             (2995, 0.0), (2996, 0.16), (2997, 0.48), (2998, 0.87), (2999, 1.0),
             (3146, 1.0), (3147, 0.88), (3148, 0.74), (3149, 0.58), (3150, 0.44), (3151, 0.31), (3152, 0.145), (3153, 0.094),
             (3154, 0.065), (3155, 0.02), (3156, 0.0), (3166, 0.0), (3167, 0.37), (3168, 0.6), (3169, 0.85), (3170, 0.95), (3171, 1.0),
             (3283, 1.0), (3284, 0.72), (3285, 0.38), (3286, 0.06), (3287, 0.0)]
    # the game (and since Oct 12 the preview) draws the fade over the finished frame in gamma space: alpha = 255 (1 - r)
    rows = [(96.55, 0.0)] + [(n * 1001 / 30000.0 + 1 / 120.0, 255.0 * (1.0 - r)) for n, r in fades] + [(109.9, 255.0)]
    d.append(SQ_FADE % ','.join('[%.4f,%.1f]' % r for r in rows))
    d.hook('FL_Fade(t);')


SQ_FADE = """
::FL_fade_tab <- [%s];
function FL_Fade(t) {
    local tab = ::FL_fade_tab; local n = tab.len();
    if (t < tab[0][0] || t > tab[n - 1][0]) return;
    local i = 0;
    while (i < n - 2 && t >= tab[i + 1][0]) i++;
    local f = (t - tab[i][0]) / (tab[i + 1][0] - tab[i][0]);
    SetScreenBlack(tab[i][1] + (tab[i + 1][1] - tab[i][1]) * f);
}
"""
