"""Scanners (74.0-83.1 s, film frames 2218-2491), rebuilt at film fov 60 in the space above cells C2 and C3
(x -9000..5000, y 3200..9750, z 6000..15500), sealed by black shells. Shots (cuts from moments/ncc.npy):
  A 2218-2249  the cake and the scanner arm, split picture (see shot_a)
  B 2250-2261  the cube passing close below the camera
  C 2262-2467  down the scanner shaft (12-sided rust shaft, grey ring plates, scanner boards, red beams), past the
               scan head, then up to the open iris (measured: COLMAP run 'sc', see shot_c)
  D 2468-2491  through the iris into the tube, collars in the dark, fade to black
Models and materials: models/scanners.py (prefix r11_sc)."""
import json, math, os
import numpy as np
from lib import vmfedit as E
from lib.gen import Mesh, V, save, rot_x, rot_y, rot_z
from lib.ride import qangle
from models import scanners as SM

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CELL = ((-9000.0, 3200.0, 6000.0), (7200.0, 9750.0, 15500.0))   # above C2-C3, reaching over C4 to x 7200 (free at this height) so shot D's far collars and floor are sealed
BLACK = 'corehub_intro/void_black'
FT = 1001.0 / 30000.0


def basis_of(ang):
    """forward vector of a Source QAngle"""
    p, y = math.radians(ang[0]), math.radians(ang[1])
    return np.array([math.cos(p) * math.cos(y), math.cos(p) * math.sin(y), -math.sin(p)])


def ftime(n, mo='E'):
    return n * FT + (FT / 2.0 if mo == 'L' else 0.0)


def shell(v, lo, hi, mat=BLACK, t=32.0):
    """hollow box sealing a part of the cell (inside faces `mat`), clamped to the cell"""
    lo = np.maximum(np.asarray(lo, dtype=float), np.asarray(CELL[0]) + 40)
    hi = np.minimum(np.asarray(hi, dtype=float), np.asarray(CELL[1]) - 40)
    for ax in range(3):
        for side in (0, 1):
            a = lo.copy() - t; b = hi.copy() + t
            if side == 0: b[ax] = lo[ax]
            else: a[ax] = hi[ax]
            E.add_box(v, a, b, mat)


def model(name, mesh):
    save(mesh, name)
    return 'models/corehub_intro/%s.mdl' % name


def prop(v, mdl, origin, angles=(0, 0, 0), name=None):
    return E.add_prop(v, mdl if mdl.startswith('models/') else 'models/corehub_intro/%s.mdl' % mdl, origin, angles, name=name)


# ------------------------------------------------------------------------------------------------ screen black
FADE = [(73.9, 0.0), (74.62, 0.0), (74.75, 80.0), (74.9, 120.0), (75.04, 170.0), (75.06, 120.0), (75.15, 60.0), (75.25, 0.0), (82.82, 0.0), (82.92, 150.0), (83.02, 200.0), (83.1, 235.0), (83.15, 255.0), (83.2, 255.0)]


def fades(d):
    d.append('''scFade <- [%s];
function Sc_Fade(t) {
    if(t>=73.95 && t<83.2) SetScreenBlack(Lerp1(scFade,t));
}''' % ','.join('[%.4f,%.1f]' % r for r in FADE))
    d.hook('Sc_Fade(t);', late=True)


# ------------------------------------------------------------------------------------------------ shot A
# 2218-2249: the film shows two pictures side by side (seam at x 640 of 1280 in 2219-2236: the cake being scanned on
# the left, a close iris petal on the right), then darkness. Built as one static camera looking along +x (up +z) with
# the parts placed where the film shows them at the sample times (depths from their sizes) and switched by Sc_ShotA:
#   2218: the tube view (dark rails converging to a grey ring at (316, 237) px, petal fragments at the top)
#   2223-2232: cake (37 wide) 210 px wide at (185, 75) px -> 81 ahead; petal (R 43.6) filling the right half -> 57 ahead
#   2231-2236: white scanner arm on the left; 2240-2249: dark posts over rust (screen darkening, film mean 46 -> 21)
A_ORIGIN = np.array([-7000.0, 4200.0, 9000.0])


def img_pt(px, py, d):
    """camera at the origin looking +x, up +z: the point at depth d seen at pixel (px, py) of the 640x400 frame"""
    return np.array([d, -(px - 319.5) * d / 461.88, -(py - 199.5) * d / 461.88])


def shot_a(v, d):
    o = A_ORIGIN
    cam = [(ftime(2218), tuple(o), (0.0, 0.0, 0.0)), (ftime(2249, 'L') + 0.001, tuple(o), (0.0, 0.0, 0.0))]   # from 2218E
    d.override_camera(cam, fov=60.0)
    det = v.create_ent(classname='func_detail')
    # rust background
    E.add_box(v, o + np.array([700.0, -900.0, -700.0]), o + np.array([720.0, 900.0, 700.0]), 'corehub_intro/r11_sc_rust_b', ent=det)
    # group T (tube view): two dark rails converging toward the ring, the ring, petal fragments at the top
    t = Mesh()
    for (px0, py0), (px1, py1) in (((40.0, 0.0), (250.0, 240.0)), ((140.0, 0.0), (300.0, 232.0))):
        a = img_pt(px0, py0, 60.0); b = img_pt(px1, py1, 420.0)
        dd = b - a; L = np.linalg.norm(dd); dd /= L
        R3 = np.c_[dd, np.cross([0, 0, 1.0], dd) / np.linalg.norm(np.cross([0, 0, 1.0], dd)), np.cross(dd, np.cross([0, 0, 1.0], dd) / np.linalg.norm(np.cross([0, 0, 1.0], dd)))]
        t.obox((a + b) / 2, V(L / 2, 4.5, 4.5), R3, 'r11_sc_mech')
    ring = Mesh(); SM.annulus_z(ring, 0.0, 52.0, 76.0, 'r11_sc_grey', 12, True); SM.annulus_z(ring, 0.0, 48.0, 52.0, 'r11_sc_line', 12, True)
    t.add(ring.transform(R=rot_y(-90)), offset=img_pt(316, 237, 420.0))
    pt = SM.I.quarter()
    t.add(pt, R=rot_x(0), offset=img_pt(20.0, -40.0, 90.0))
    t.add(pt, R=rot_x(-90), offset=img_pt(560.0, -10.0, 90.0))
    prop(v, model('r11_sc_a_tube', t), o, (0, 0, 0), 'r11_sc_a_tube')
    # group C: the cake and its grey ring (left), the petal with its hub and the grey frame (right)
    prop(v, 'models/props/cake/cake.mdl', o + img_pt(185.0, 95.0, 93.0), (-90.0, 0.0, 0.0), 'r11_sc_a_cake')
    cr = Mesh(); SM.annulus_z(cr, 0.0, 44.0, 60.0, 'r11_sc_ring_lip', 12, True)
    prop(v, model('r11_sc_a_cakering', cr.transform(R=rot_y(-90))), o + img_pt(185.0, 330.0, 260.0), (0, 0, 0), 'r11_sc_a_cakering')
    pp = Mesh(); pp.add(SM.I.quarter(), R=rot_x(180))
    fr = Mesh(); SM.annulus_z(fr, 0.0, 6.0, 13.0, 'r11_sc_grey', 16, True)
    pp.add(fr.transform(R=rot_y(-90)), offset=(4.0, 0.0, 0.0))
    prop(v, model('r11_sc_a_petal', pp), o + img_pt(335.0, 228.0, 57.0), (0, 0, 0), 'r11_sc_a_petal')
    prop(v, 'transfer_scan_link', o + img_pt(95.0, -20.0, 110.0), (-80.0, 0.0, 0.0), 'r11_sc_a_arm0')
    prop(v, 'transfer_scan_link', o + img_pt(110.0, 330.0, 110.0), (-100.0, 0.0, 0.0), 'r11_sc_a_arm1')
    # group D: dark posts and a beam over the rust (2240-2249)
    gd = Mesh()
    for px in (150.0, 470.0):
        c = img_pt(px, 200.0, 300.0); gd.box(c + np.array([-10.0, -18.0, -400.0]), c + np.array([10.0, 18.0, 400.0]), 'r11_sc_mech')
    c = img_pt(320.0, 120.0, 300.0); gd.box(c + np.array([-10.0, -500.0, -14.0]), c + np.array([10.0, 500.0, 14.0]), 'r11_sc_mech')
    prop(v, model('r11_sc_a_dark', gd), o + np.array([0.0, 0.0, -700.0]), (0, 0, 0), 'r11_sc_a_dark')     # starts inside the shell (a prop outside it makes the map leak); the hook moves it
    d.append('''function Sc_ShotA(t) {
    if(t<73.9 || t>75.2) return;
    local hid=Vector(0,0,-3000);
    MoveProp("r11_sc_a_tube",(t<74.12)?Vector(%.2f,%.2f,%.2f):hid);
    local c=(t>=74.12 && t<74.62);
    MoveProp("r11_sc_a_cake",(c&&t<74.45)?Vector(%.2f,%.2f,%.2f):hid);
    MoveProp("r11_sc_a_cakering",(c&&t<74.45)?Vector(%.2f,%.2f,%.2f):hid);
    MoveProp("r11_sc_a_petal",c?Vector(%.2f,%.2f,%.2f):hid);
    MoveProp("r11_sc_a_arm0",(t>=74.42&&t<74.66)?Vector(%.2f,%.2f,%.2f):hid);
    MoveProp("r11_sc_a_arm1",(t>=74.42&&t<74.66)?Vector(%.2f,%.2f,%.2f):hid);
    MoveProp("r11_sc_a_dark",(t>=74.62)?Vector(%.2f,%.2f,%.2f):hid);
}''' % tuple(list(o) + list(o + img_pt(185.0, 95.0, 93.0)) + list(o + img_pt(185.0, 330.0, 260.0)) + list(o + img_pt(335.0, 228.0, 57.0))
              + list(o + img_pt(95.0, -20.0, 110.0)) + list(o + img_pt(110.0, 330.0, 110.0)) + list(o)))
    d.hook('Sc_ShotA(t);', late=True)
    shell(v, o + np.array([-200.0, -1000.0, -800.0]), o + np.array([800.0, 1000.0, 800.0]))


# ------------------------------------------------------------------------------------------------ shot D
D_ORIGIN = np.array([2500.0, 8600.0, 7200.0])      # the iris' centre; the tube runs along +x
D_PETAL_R = 43.6                                   # 2455 (iris 208 ahead): straight edges 40 px off the axes, outer arcs 132 px -> R 42-46
# camera along +x: 2468E 161 before the iris (petals' outer arcs 177 px), iris passed at 2470.3, port wall (ring R 60:
# 75 px at 2472, 143 at 2474) passed at 2475.5, then collars every 3 frames 360 apart (82.7: collars 245 / 60 px)
D_KEYS = [(2468.0, -161.0), (2470.3, 0.0), (2475.5, 470.0), (2479.5, 950.0), (2492.0, 2450.0)]
D_PORT_X = 470.0
D_COLLAR0 = 950.0; D_COLLAR_STEP = 360.0
D_FLOOR = -260.0; D_FLOOR_END = 3200.0


def shot_d(v, d):
    o = D_ORIGIN; cam = []
    for n in range(2468, 2492):
        for mo in 'EL':
            fr = n + (0.5 if mo == 'L' else 0.0)
            x = float(np.interp(fr, [k[0] for k in D_KEYS], [k[1] for k in D_KEYS]))
            cam.append((ftime(n, mo), tuple(o + np.array([x, 0.0, 0.0])), (0.0, 0.0, 0.0)))
    d.override_camera(cam, fov=60.0)
    det = v.create_ent(classname='func_detail')
    # iris: four petals slid apart along the diagonals, axis +x (model axis +X: angles 0 0 roll)
    sc = D_PETAL_R / SM.I.PETAL_R
    pet = model('r11_sc_petal_d', SM.I.quarter().transform(scale=sc))
    off = 25.5                                     # 2455: straight edges 18 units off the axes (diagonal 25.5)
    for k in range(4):
        a = math.radians(45 + 90 * k)
        prop(v, pet, o + np.array([0.0, off * math.cos(a), off * math.sin(a)]), (0.0, 0.0, -90.0 + 90 * k + 90), 'r11_sc_d_petal%d' % k)
    # the wall around the iris (rust) and the wall with the port further on
    rust = Mesh()
    for x0, hole in ((-6.0, 1.25 * D_PETAL_R + 18.0), (D_PORT_X, 62.0)):
        # square slab with a square hole, facing -x (toward the camera)
        H = 1600.0
        for (y0, y1, z0, z1) in ((-H, -hole, -H, H), (hole, H, -H, H), (-hole, hole, -H, -hole), (-hole, hole, hole, H)):
            q = [V(x0, y0, z0), V(x0, y0, z1), V(x0, y1, z1), V(x0, y1, z0)]
            uv = [(y0 / 768.0, z0 / 768.0), (y0 / 768.0, z1 / 768.0), (y1 / 768.0, z1 / 768.0), (y1 / 768.0, z0 / 768.0)]
            rust.tri('r11_sc_rust', q[0], q[1], q[2], uv=[uv[0], uv[1], uv[2]]); rust.tri('r11_sc_rust', q[0], q[2], q[3], uv=[uv[0], uv[2], uv[3]])
    prop(v, model('r11_sc_d_walls', rust), o)
    # grey iris frame behind the petals (seen in the gaps), the tube's mouth: dark 12-gon line, grey ring
    fr = Mesh()
    SM.annulus_z(fr, 0.0, 37.0, 1.25 * D_PETAL_R + 18.0, 'r11_sc_grey', 12, True)
    SM.annulus_z(fr, 0.0, 35.0, 37.0, 'r11_sc_line', 12, True)
    SM.annulus_z(fr, -30.0, 14.0, 22.0, 'r11_sc_grey', 12, True)
    prop(v, model('r11_sc_d_frame', fr.transform(R=rot_y(-90))), o + np.array([3.0, 0.0, 0.0]))
    # rails along the tube (from the iris to the end)
    for k in range(4):
        a = math.radians(45 + 90 * k); c = np.array([0.0, 34.0 * math.cos(a), 34.0 * math.sin(a)])
        E.add_box(v, o + c + np.array([-10.0, -0.9, -0.9]), o + c + np.array([D_FLOOR_END + 400.0, 0.9, 0.9]), 'corehub_intro/r11_sc_rail_b', ent=det)
    # port ring in the second wall and the collars beyond it (12-gon collars, axis +x)
    col = model('r11_sc_collar', SM.collar_wide().transform(R=rot_y(90)))
    xs = [D_PORT_X] + [D_COLLAR0 + D_COLLAR_STEP * k for k in range(6)]
    for k, x in enumerate(xs):
        prop(v, col, o + np.array([x, 0.0, 0.0]), (0, 0, 0), 'r11_sc_d_collar%d' % k)
    # dark floor beyond the port wall
    E.add_box(v, o + np.array([D_PORT_X, -2000.0, D_FLOOR - 16]), o + np.array([D_FLOOR_END + 1000.0, 2000.0, D_FLOOR]), 'corehub_intro/r11_sc_floor', ent=det)
    # the shell must enclose every prop (a prop outside it makes the map leak): reach past the last collar
    shell(v, o + np.array([-800.0, -1700.0, -1700.0]), o + np.array([max(D_FLOOR_END + 1200.0, max(xs) + 400.0), 1700.0, 1700.0]))


# ------------------------------------------------------------------------------------------------ shot C
C_ORIGIN = np.array([-3000.0, 6500.0, 14200.0])    # map position of the shaft coordinates' origin (camera at 2340)


def _slerp_basis(f0, u0, f1, u1, a):
    """interpolate two camera bases (forward, up) by the rotation between them"""
    def mat(f, u):
        f = f / np.linalg.norm(f); u = u - f * (u @ f); u /= np.linalg.norm(u); return np.c_[f, np.cross(u, f), u]
    M0, M1 = mat(np.asarray(f0), np.asarray(u0)), mat(np.asarray(f1), np.asarray(u1))
    Rr = M1 @ M0.T
    ang = math.acos(max(-1.0, min(1.0, (np.trace(Rr) - 1) / 2)))
    if ang < 1e-9: return M0[:, 0], M0[:, 2]
    ax = np.array([Rr[2, 1] - Rr[1, 2], Rr[0, 2] - Rr[2, 0], Rr[1, 0] - Rr[0, 1]]) / (2 * math.sin(ang))
    K = np.array([[0, -ax[2], ax[1]], [ax[2], 0, -ax[0]], [-ax[1], ax[0], 0]]); th = ang * a
    Ra = np.eye(3) + math.sin(th) * K + (1 - math.cos(th)) * K @ K
    M = Ra @ M0
    return M[:, 0], M[:, 2]


def c_track():
    """the measured camera of shot C (shaft coordinates): [(t, p, f, u)] at the blended frames' mid times"""
    J = json.load(open(os.path.join(HERE, 'data', 'sc_c_ride.json')))
    return [(m[0], np.array(m[3:6]), np.array(m[6:9]), np.array(m[9:12])) for m in J['moments']]


def c_camera(tr, t0, t1, origin, smooth=None):
    """60 Hz camera samples between t0 and t1 interpolated from the track (positions linear, orientation slerp)"""
    ts = np.array([x[0] for x in tr]); P = np.array([x[1] for x in tr])
    if smooth:
        from scipy.ndimage import gaussian_filter1d
        P = gaussian_filter1d(P, smooth, axis=0, mode='nearest')
    out = []; n0 = int(math.ceil(t0 / FT - 1e-6)); t = n0 * FT
    while t <= t1 + 1e-6:
        for tt in (t, t + FT / 2.0):
            if tt > t1 + 1e-6: break
            i = int(np.clip(np.searchsorted(ts, tt) - 1, 0, len(ts) - 2)); a = float(np.clip((tt - ts[i]) / (ts[i + 1] - ts[i]), 0.0, 1.0))
            if tt < ts[0]: a = (tt - ts[0]) / (ts[1] - ts[0]); i = 0
            if tt > ts[-1]: a = 1.0 + (tt - ts[-1]) / (ts[-1] - ts[-2]); i = len(ts) - 2
            p = P[i] + (P[i + 1] - P[i]) * a
            f, u = _slerp_basis(tr[i][2], tr[i][3], tr[i + 1][2], tr[i + 1][3], float(np.clip(a, 0, 1)))
            out.append((tt, tuple(float(x) for x in origin + p), qangle(f, u)))
        t += FT
    return out


# shaft geometry (shaft coordinates: axis = the camera's path in 2278-2402, z up, origin = camera at 2340, scale 50
# map units per COLMAP unit, from the boards: point clusters 86 long = scanner_board.mdl):
#   boards (white clusters) in pairs: z +50 at 44/223 deg, -128 at 130/318, -318 at 43/223, r 50..115
#   black posts: 4 at r ~128, angles 65/157/249/339 (dark clusters at every level; film 2340: bars at those angles,
#     ending on the floor at 72 px from the centre), ~11 thick
#   translucent grey plates (12-gon holes, apothem ~125): edges r(2340) 262/206/150 px -> z -220/-280/-385; also
#     -50, -110 (dark clusters); ring at -460 (65..105, film 2340: 64.5/69.5/105.5 px edges)
#   floor z -715 (rust), white target radius 23 at -690 (film: 17-20 px at 2340)
C_SCALE = 50.0
C_POSTS = dict(r=128.0, angles=(65.0, 157.0, 249.0, 339.0), w=11.0, z0=-715.0, z1=900.0)
C_PLATES = [(50.0, 125.0), (-50.0, 125.0), (-110.0, 125.0), (-165.0, 125.0), (-220.0, 125.0), (-280.0, 125.0), (-330.0, 125.0), (-385.0, 125.0)]
C_RING = (-460.0, 65.0, 105.0)
C_FLOOR = -715.0
C_BOARDS = [(50.0, 44.0), (50.0, 223.0), (-128.0, 130.0), (-128.0, 318.0), (-318.0, 43.0), (-318.0, 223.0)]
C_PLATE_OUT = 163.0                                # film 2340: ring bands 150-196 px at -385 -> 125..163
C_WALL_R = 330.0
C_HEAD = dict(z=-372.0, arm_angle=225.0)
C_CUBE = dict(n0=2255.0, z0=302.0, vz=-9.6, size=35.6)     # film 2255 / 2290 / 2306: cube 45 / 235 / 330 below the camera
C_RED = [((-128.0, 318.0), (-0.45, 0.35, -1.0), 420.0, 10.0)]


def shaft_c(v, o):
    det = v.create_ent(classname='func_detail')
    # plates (one model each, translucent grey 12-gon annuli)
    pl = Mesh(); SM.annulus_z(pl, 0.0, 1.0, C_PLATE_OUT / 125.0, 'r11_sc_plate', 12, True)
    for k, (z, a) in enumerate(C_PLATES):
        m = Mesh()
        SM.annulus_z(m, 0.0, a + 4.0, C_PLATE_OUT, 'r11_sc_plate', 12, True, phase=math.radians(15))
        SM.annulus_z(m, 0.0, a, a + 4.0, 'r11_sc_plate_edge', 12, True, phase=math.radians(15))
        SM.annulus_z(m, -2.0, a, C_PLATE_OUT, 'r11_sc_plate', 12, False, phase=math.radians(15))
        prop(v, model('r11_sc_plate%d' % k, m), o + np.array([0.0, 0.0, z]), (0, 0, 0), 'r11_sc_c_plate%d' % k)
    z, a0, a1 = C_RING
    m = Mesh(); SM.annulus_z(m, 0.0, a0, a1, 'r11_sc_ring_top', 12, True); SM.annulus_z(m, 0.0, a0 - 3, a0, 'r11_sc_line', 12, True)
    SM.wall_z(m, -14.0, 0.0, a1, 'r11_sc_ring_lip', 12, inward=False)
    prop(v, model('r11_sc_ring460', m), o + np.array([0.0, 0.0, z]), (0, 0, 0), 'r11_sc_c_ring')
    # posts
    P = C_POSTS
    for k, ang in enumerate(P['angles']):
        c = o + np.array([P['r'] * math.cos(math.radians(ang)), P['r'] * math.sin(math.radians(ang)), 0.0])
        E.add_box(v, c + np.array([-P['w'] / 2, -P['w'] / 2, P['z0']]), c + np.array([P['w'] / 2, P['w'] / 2, P['z1']]), 'corehub_intro/r11_sc_rail_b', ent=det)
    # boards: scanner_board.mdl runs along model -X from its origin (86 long): origin at the outer end, pointing in
    bm = model('r11_sc_board', SM.board())
    for k, (z, ang) in enumerate(C_BOARDS):
        a = math.radians(ang); r0 = 112.0
        prop(v, bm, o + np.array([r0 * math.cos(a), r0 * math.sin(a), z]), (0.0, ang, 0.0), 'r11_sc_c_board%d' % k)
    # floor (rust) and the white target
    fl = Mesh(); q = [V(-900, -900, 0), V(900, -900, 0), V(900, 900, 0), V(-900, 900, 0)]
    uv = [(-900 / 600.0, -900 / 600.0), (900 / 600.0, -900 / 600.0), (900 / 600.0, 900 / 600.0), (-900 / 600.0, 900 / 600.0)]
    fl.tri('r11_sc_rust', q[0], q[1], q[2], uv=[uv[0], uv[1], uv[2]]); fl.tri('r11_sc_rust', q[0], q[2], q[3], uv=[uv[0], uv[2], uv[3]])
    SM.annulus_z(fl, 2.0, 0.0, 23.0, 'r11_sc_target', 24, True)
    SM.annulus_z(fl, 2.0, 23.0, 38.0, 'r11_sc_grey', 12, True)
    prop(v, model('r11_sc_floor_c', fl), o + np.array([0.0, 0.0, C_FLOOR]), (0, 0, 0), 'r11_sc_c_floor')
    # shaft wall beyond the plates (dim rust, 12-gon)
    prop(v, model('r11_sc_wall_c', SM.shaft_wall(C_WALL_R, C_FLOOR, 1200.0, material='r11_sc_rust_dark', uv=(600.0, 400.0))), o, (0, 0, 0), 'r11_sc_c_wall')
    # eyes at the boards' inner ends, red beams from some of them
    eye = Mesh().sphere(V(0, 0, 0), 4.0, 'r11_sc_eye', n=12, m=8); eye.shade('r11_sc_eye', levels=4, light=(0.3, -0.2, 0.9))
    em = model('r11_sc_eye', eye)
    for k, (z, ang) in enumerate(C_BOARDS):
        a = math.radians(ang); r0 = 26.0
        prop(v, em, o + np.array([r0 * math.cos(a), r0 * math.sin(a), z - 10.0]), (0, 0, 0), 'r11_sc_c_eye%d' % k)
    red = []
    for k, ((z, ang), dvec, ln, rad) in enumerate(C_RED):
        a = math.radians(ang); p0 = o + np.array([26.0 * math.cos(a), 26.0 * math.sin(a), z - 10.0]); red.append(p0)
        dv = np.array(dvec, dtype=float); dv /= np.linalg.norm(dv)
        from lib.tube import frame_angles
        left = np.cross([0, 0, 1.0], dv) if abs(dv[2]) < 0.95 else np.array([0, 1.0, 0])
        prop(v, model('r11_sc_red%d' % k, SM.cone(ln, rad)), p0, frame_angles(dv, left), 'r11_sc_c_red%d' % k)
    # scan head on its arm, yellow cones pointing up (toward the descending camera)
    hz = C_HEAD['z']; aa = math.radians(C_HEAD['arm_angle'])
    prop(v, 'transfer_scan_head', o + np.array([0.0, 0.0, hz]), (90.0, 0.0, 0.0), 'r11_sc_c_head')
    prop(v, 'transfer_scan_cones', o + np.array([0.0, 0.0, hz]), (90.0, 0.0, 0.0), 'r11_sc_c_cones')
    arm = Mesh().box((0.0, -7.0, -7.0), (C_WALL_R, 7.0, 7.0), 'r11_sc_white')
    prop(v, model('r11_sc_arm', arm), o + np.array([0.0, 0.0, hz - 30.0]), (0.0, C_HEAD['arm_angle'], 0.0), 'r11_sc_c_arm')
    prop(v, 'r11_sc_arm', o + np.array([0.0, 0.0, hz - 30.0]), (0.0, C_HEAD['arm_angle'] - 180.0, 0.0), 'r11_sc_c_arm2')
    # the cube falling ahead of the camera (moved by Sc_Cube)
    cb = prop(v, 'models/props_backstage/vacum_cube.mdl', o + np.array([0.0, 0.0, C_CUBE['z0']]), (20, 30, 10), 'r11_sc_c_cube')
    cb['rendercolor'] = '120 120 120'
    shell(v, o + np.array([-1000.0, -1000.0, C_FLOOR - 300.0]), o + np.array([1000.0, 1000.0, 1300.0]))
    return red


# cube below the camera (film: 2253 top face filling the view, 2255 ~45 below, 2262 ~110, 2290 ~235, 2306 ~330)
C_CUBE_D = [(2250.0, 18.0), (2253.0, 30.0), (2255.0, 45.0), (2258.0, 70.0), (2262.0, 140.0), (2270.0, 220.0), (2290.0, 330.0), (2306.0, 420.0), (2330.0, 560.0), (2345.0, 750.0)]


def head_hook(d, o, red):
    """the scan head rises to meet the camera on its arm (film: small at the centre 79.75 s (cones ~60 px, ~540 below
    the camera), big 80.25 s (cones ~300 px, ~110 below)), then drops away after 80.53 s (2416-2428: it shrinks)"""
    hz = C_HEAD['z']
    d.append('scRed <- [%s];' % ','.join('Vector(%.2f,%.2f,%.2f)' % tuple(p) for p in red))
    d.append('''scHeadZ <- [[78.9,-900.0],[79.75,-745.0],[80.25,%.1f],[80.53,%.1f],[81.2,%.1f]];
function Sc_Head(t) {
    if(t<74.0 || t>81.2) return;
    foreach(i,nm in ["r11_sc_c_red0"]) MoveProp(nm,(t>80.0)?Vector(0,0,-3000):scRed[i]);
    local f=(t-78.9)/1.1; if(f>1)f=1; if(f<0)f=0;
    local z=Lerp1(scHeadZ,t);
    local p=(t<78.9)?Vector(0,0,-3000):Vector(%.2f+(%.2f)*f, %.2f+(%.2f)*f, %.2f+z);
    foreach(nm in ["r11_sc_c_head","r11_sc_c_cones"]) MoveProp(nm,p);
    MoveProp("r11_sc_c_arm",(t<78.9)?Vector(0,0,-3000):p+Vector(0,0,-30));
    MoveProp("r11_sc_c_arm2",(t<78.9)?Vector(0,0,-3000):p+Vector(0,0,-30));
    MoveProp("r11_sc_c_ring",(t>80.62)?Vector(0,0,-3000):Vector(%.2f,%.2f,%.2f));
}''' % (hz, hz, hz - 650.0 * (81.2 - 80.53), o[0] + 40.0, -50.0, o[1] + 40.0, -40.0, o[2], o[0], o[1], o[2] + C_RING[0]))
    d.hook('Sc_Head(t);', late=True)


def cube_hook(d, o, cam):
    ts = np.array([c[0] for c in cam]); zs = np.array([c[1][2] for c in cam]); xs = np.array([c[1][0] for c in cam]); ys = np.array([c[1][1] for c in cam])
    rows = []
    for n, dz in C_CUBE_D:
        t = ftime(n) + FT / 4
        p = np.array([float(np.interp(t, ts, xs)), float(np.interp(t, ts, ys)), float(np.interp(t, ts, zs))])
        k = int(np.argmin(np.abs(ts - t))); f = basis_of(cam[k][2])
        # along the camera's view while it still looks at an angle (shot B), on the axis below once it looks down
        side = max(0.0, min(1.0, (2290.0 - n) / 25.0)) * np.array([45.0, 45.0, 0.0])     # film 2270: upper left
        q = p + f * dz if n <= 2262 else np.array([o[0], o[1], p[2] - dz]) + side
        rows.append((t, q[0], q[1], q[2]))
    d.append('''scCube <- [%s];
function Sc_Cube(t) {
    if(t<74.9 || t>78.4) return;
    local e=Entities.FindByName(null,"r11_sc_c_cube"); if(e==null) return;
    if(t>=scCube[scCube.len()-1][0]){e.SetOrigin(Vector(0,0,-3000));return;}
    local i=0; while(i<scCube.len()-2 && t>=scCube[i+1][0]) i++;
    local a=scCube[i], b=scCube[i+1], f=(t-a[0])/(b[0]-a[0]); if(f<0)f=0;
    e.SetOrigin(Vector(a[1]+(b[1]-a[1])*f, a[2]+(b[2]-a[2])*f, a[3]+(b[3]-a[3])*f));
    local n=t*29.97002997-2255.0;
    e.__KeyValueFromString("angles",(18+1.1*n)+" "+(35+2.2*n)+" "+(8+0.7*n));
}''' % ','.join('[%.4f,%.2f,%.2f,%.2f]' % r for r in rows))
    d.hook('Sc_Cube(t);', late=True)


def shot_c(v, d):
    tr = c_track()
    tr = [x for x in tr if 2264 <= int(round((x[0] - FT / 4) / FT)) <= 2412]
    cam = c_camera(tr, ftime(2250), ftime(2412, 'L'), C_ORIGIN)
    # 2413-2421: the camera goes on down past the scan head (COLMAP lost it): hold the orientation, descend
    last = cam[-1]; p0 = np.array(last[1]); t0 = last[0]
    for n in range(2413, 2430):
        for mo in 'EL':
            t = ftime(n, mo); cam.append((t, tuple(p0 + np.array([0.0, 0.0, -4.0 * (t - t0) / FT])), last[2]))
    d.override_camera(cam, fov=60.0)
    red = shaft_c(v, C_ORIGIN)
    cube_hook(d, C_ORIGIN, cam)
    head_hook(d, C_ORIGIN, red)


# ------------------------------------------------------------------------------------------------ shot C, part 2
# frames 2415-2467: COLMAP model 0 (2422-2466; 2422-2430 shifted onto the later part, see out/sc/tools/align_c2.py),
# iris-chamber frame: +x toward the rust wall (x = 0), z = the camera's up at 2454, origin = the iris centre,
# scale 17.5 (petals R 60: film 2455 petals 133 px at 208 units; rails 34 at the mouth 75 px)
C2_ORIGIN = np.array([1200.0, 5200.0, 9000.0])
# film 2455 at the wall (208 ahead, 0.45 units per px): posts x 0-60 / 484-538 px, beams y 15-50 / 372-400 px,
# grey mount x 245-410 y 0-25, yellow cones x 280-380 y 30-115
C2_POSTS = [((-8.0, 160.0), 70.0), ((-8.0, -81.0), 24.0)]           # (x, y), width: dark vertical posts
C2_BEAMS = [(-8.0, 84.0, 16.0), (-8.0, -80.0, 14.0)]                # x, z, height: dark horizontal beams (top / bottom)
C2_HEAD = np.array([-24.0, 0.0, 78.0])                              # scan head above the iris, cones pointing down (-z)


def c2_track():
    J = json.load(open(os.path.join(HERE, 'data', 'sc_c2_ride.json')))
    return [(m[0], np.array(m[3:6]), np.array(m[6:9]), np.array(m[9:12])) for m in J['moments']]


def chamber_c2(v, o):
    det = v.create_ent(classname='func_detail')
    # rust wall with the iris opening
    rust = Mesh(); H = 700.0; hole = 1.25 * D_PETAL_R + 18.0
    for (y0, y1, z0, z1) in ((-H, -hole, -H, H), (hole, H, -H, H), (-hole, hole, -H, -hole), (-hole, hole, hole, H)):
        q = [V(0.0, y0, z0), V(0.0, y0, z1), V(0.0, y1, z1), V(0.0, y1, z0)]
        uv = [(y0 / 640.0, z0 / 640.0), (y0 / 640.0, z1 / 640.0), (y1 / 640.0, z1 / 640.0), (y1 / 640.0, z0 / 640.0)]
        rust.tri('r11_sc_rust', q[0], q[1], q[2], uv=[uv[0], uv[1], uv[2]]); rust.tri('r11_sc_rust', q[0], q[2], q[3], uv=[uv[0], uv[2], uv[3]])
    prop(v, model('r11_sc_c2_wall', rust), o)
    # the iris (same parts as shot D), the tube behind it
    pet = model('r11_sc_petal_d', SM.I.quarter().transform(scale=D_PETAL_R / SM.I.PETAL_R))
    off = 25.5
    for k in range(4):
        a = math.radians(45 + 90 * k)
        prop(v, pet, o + np.array([-1.0, off * math.cos(a), off * math.sin(a)]), (0.0, 0.0, 90.0 * k), 'r11_sc_c2_petal%d' % k)
    prop(v, 'r11_sc_d_frame', o + np.array([2.0, 0.0, 0.0]))
    for k in range(4):
        a = math.radians(45 + 90 * k); c = np.array([0.0, 34.0 * math.cos(a), 34.0 * math.sin(a)])
        E.add_box(v, o + c + np.array([0.0, -0.9, -0.9]), o + c + np.array([900.0, 0.9, 0.9]), 'corehub_intro/r11_sc_rail_b', ent=det)
    E.add_box(v, o + np.array([700.0, -300.0, -300.0]), o + np.array([720.0, 300.0, 300.0]), 'corehub_intro/r11_sc_rust_b', ent=det)
    # dark posts and beams in front of the wall
    for (x, y), w in C2_POSTS:
        E.add_box(v, o + np.array([x - w / 2, y - w / 2, -500.0]), o + np.array([x + w / 2, y + w / 2, 500.0]), 'corehub_intro/r11_sc_rail_b', ent=det)
    for x, z, h in C2_BEAMS:
        E.add_box(v, o + np.array([x - 8.0, -500.0, z - h / 2]), o + np.array([x + 8.0, 500.0, z + h / 2]), 'corehub_intro/r11_sc_rail_b', ent=det)
    # scan head hanging from a grey block, cones down toward the iris
    prop(v, 'transfer_scan_head', o + C2_HEAD, (-90.0, 0.0, 0.0), 'r11_sc_c2_head')
    prop(v, 'transfer_scan_cones', o + C2_HEAD, (-90.0, 0.0, 0.0), 'r11_sc_c2_cones')
    E.add_box(v, o + np.array([-30.0, -37.0, 88.0]), o + np.array([-12.0, 37.0, 110.0]), 'corehub_intro/r11_sc_grey_b', ent=det)
    shell(v, o + np.array([-700.0, -800.0, -800.0]), o + np.array([800.0, 800.0, 800.0]))


def shot_c2(v, d):
    tr = c2_track()
    cam = c_camera(tr, ftime(2430), ftime(2467, 'L'), C2_ORIGIN)
    d.override_camera(cam, fov=60.0)
    chamber_c2(v, C2_ORIGIN)


def apply(v, d):
    SM.textures(); SM.materials()
    shot_a(v, d)
    shot_c(v, d)
    shot_c2(v, d)
    shot_d(v, d)
    fades(d)
