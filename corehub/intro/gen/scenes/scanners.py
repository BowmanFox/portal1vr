"""Scanners (74.0-83.1 s, film frames 2218-2491), rebuilt at film fov 60 in the space above cells C2 and C3
(x -9000..5000, y 3200..9750, z 6000..15500), sealed by black shells. Shots (cuts from moments/ncc.npy):
  A 2218-2249  the cake and the scanner arm, split picture: two half worlds on either side of the plane through the
               eye (see shot_a)
  B 2250-2261  the cube passing close below the camera (own unlit model, positions measured per frame)
  C 2262-2467  down the scanner shaft (12-sided rust shaft, ring bands fitted to the film's radial edges, scanner boards,
               eyes, a red beam), past the scan head, a pitch toward the wall, then the open iris (COLMAP run 'sc')
  D 2468-2491  through the iris into the tube, collars in the dark, fade to black
Round 3 (engine rules): only own unlit models (the stock cake and cube rendered black in the game), everything that does
not move is prop_static without a name, hidden parts wait inside the shells.
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


def prop(v, mdl, origin, angles=(0, 0, 0), name=None, static=False):
    """props that never move are prop_static without a name (engine rule); the others keep their names for the hooks"""
    mdl = mdl if mdl.startswith('models/') else 'models/corehub_intro/%s.mdl' % mdl
    if static: return E.add_prop(v, mdl, origin, angles, cls='prop_static')
    return E.add_prop(v, mdl, origin, angles, name=name)


# ------------------------------------------------------------------------------------------------ screen black
# re-fitted in round 3 for the gamma-space fades (alpha = 255 * (1 - film / unfaded preview), mean grey of the blended
# samples): 74.75 film 45.6 / unfaded 52.9 -> 35, 74.9 38.8 / 52.9 -> 68, 75.0 25.9 / 52.9 -> 130, 75.1 26.5 / 38.8 -> 81;
# 82.75 10.2 / 22.0 -> 136, 82.85 7.6 / 21.8 -> 166, 82.95 7.4 / 21.4 -> 166, 83.05 3.1 / 20.6 -> 216
FADE = [(73.9, 0.0), (74.62, 0.0), (74.75, 35.0), (74.9, 68.0), (75.0, 130.0), (75.05, 120.0), (75.1, 81.0), (75.15, 40.0), (75.25, 0.0),
        (82.62, 0.0), (82.75, 136.0), (82.85, 166.0), (82.95, 168.0), (83.05, 216.0), (83.1, 235.0), (83.15, 255.0), (83.2, 255.0)]


def fades(d):
    d.append('''scFade <- [%s];
function Sc_Fade(t) {
    if(t>=73.95 && t<83.2) SetScreenBlack(Lerp1(scFade,t));
}''' % ','.join('[%.4f,%.1f]' % r for r in FADE))
    d.hook('Sc_Fade(t);', late=True)


# ------------------------------------------------------------------------------------------------ shot A
# 2218-2249: frames 2218-2233 show two pictures side by side. The seam is the straight edge of an iris petal right at
# the camera: it stays at x 651-637 (of 1280) in 2219-2230 and then runs left with the petal's edge (633, 621, 598, 567
# in 2231-2234), where the right half's petal joins the left half's picture (2233-2237 are one picture: the arm on the
# left, the petal on the right). Both halves scroll down at the same speed (64, 54, 46, 40 px per frame in 2219-2222,
# phase correlation of the moments); the film's E and L moments are identical here (held frames). Built as one static
# camera looking along +x (up +z) with two half worlds split by the plane y = 0 through the eye (the left picture's
# parts clipped to y >= 0, the right picture's to y <= 0), the parts moved per film frame by Sc_ShotA:
#   left: the tube rails and ring (2218), the grey ring band (2219-2228), the cake (210 px wide at (185, 95) in 2225),
#         the scan head on its white arm (2225-2236)
#   right: a lower-right petal (corner (365, 170), R 323 px in 2225), the grey band with two dark posts above it,
#         the upper-right petal (corner (298, 340), R 280 px in 2233) with the hub ring and its cyan lights
#   2236-2249: dark posts over rust (screen darkening, film mean 46 -> 21)
A_ORIGIN = np.array([-7000.0, 4200.0, 9000.0])
F_PX = 461.88


def img_pt(px, py, d):
    """camera at the origin looking +x, up +z: the point at depth d seen at pixel (px, py) of the 640x400 frame"""
    return np.array([d, -(px - 319.5) * d / F_PX, -(py - 199.5) * d / F_PX])


def clip_half(m, keep):
    """the part of a mesh with keep * y >= 0 (Sutherland-Hodgman on every triangle)"""
    from lib.mesh import Tri
    out = Mesh()
    for t in m.tris:
        P = list(t.p); UV = list(t.uv) if t.uv else [None] * 3
        poly = list(zip(P, UV)); res = []
        for i in range(len(poly)):
            (a, ua), (b, ub) = poly[i], poly[(i + 1) % len(poly)]
            da, db = keep * a[1], keep * b[1]
            if da >= 0: res.append((a, ua))
            if (da >= 0) != (db >= 0):
                s = da / (da - db); p = a + (b - a) * s
                u = None if ua is None else (ua[0] + (ub[0] - ua[0]) * s, ua[1] + (ub[1] - ua[1]) * s)
                res.append((p, u))
        if len(res) < 3: continue
        fn = t.face_normal()
        for k in range(1, len(res) - 1):
            tri = [res[0], res[k], res[k + 1]]
            uv = None if tri[0][1] is None else [q[1] for q in tri]
            out.tris.append(Tri(t.mat, [q[0] for q in tri], [fn, fn, fn], uv))
    return out


def card(pts_px, d, material, m=None):
    """flat polygon at depth d through the given pixel corners (facing the camera)"""
    m = m or Mesh()
    P = [img_pt(px, py, d) for px, py in pts_px]
    if np.dot(np.cross(P[1] - P[0], P[2] - P[0]), [-1.0, 0, 0]) < 0: P = P[::-1]
    m.poly(material, P)
    return m


def bar_px(m, a, b, w, d0, d1, material):
    """dark bar between two pixel points at depths d0 / d1, w units thick"""
    pa = img_pt(a[0], a[1], d0); pb = img_pt(b[0], b[1], d1)
    dd = pb - pa; L = np.linalg.norm(dd); dd /= L
    s = np.cross([1.0, 0, 0], dd); s = s / np.linalg.norm(s) if np.linalg.norm(s) > 1e-6 else np.array([0, 1.0, 0])
    R3 = np.c_[dd, s, np.cross(dd, s)]
    m.obox((pa + pb) / 2, V(L / 2, w / 2, w / 2), R3, material)
    return m


# film frame -> (px, py, depth) of each moving part's reference point (held per film frame like the film). Clipped
# parts move only along z: py is the screen height of their reference line at their own depth. The game's moment
# at 74.5 s falls on film frame 2232.77 (the film shows 2233 there): p2 and the head take 2233's pose from 2232 on.
A_KEYS = {
    'tube':  (None, [(2217, 0), (2218.9, 0), (2219, 9000)]),
    'bandL': (150.0, [(2218, -200), (2219, 0), (2220, 34), (2222, 85), (2223, 232), (2225, 262), (2228, 330), (2230, 420)]),
    'cake':  (0, [(2221, 210, -150, 88.0), (2223, 200, 12, 85.0), (2224, 192, 55, 83.0), (2225, 185, 95, 81.0), (2226, 180, 150, 79.0), (2227, 175, 200, 77.0), (2228, 168, 250, 76.0), (2229, 160, 300, 74.0), (2230, 150, 360, 73.0), (2231, 145, 420, 72.0), (2232, 140, 480, 72.0)]),
    'head':  (0, [(2225, 185, -70, 70.0), (2226, 180, -10, 69.0), (2227, 172, 60, 68.0), (2228, 162, 140, 67.0), (2229, 152, 215, 66.0), (2230, 142, 262, 66.0), (2231, 132, 302, 66.0), (2232, 155, 375, 66.0), (2233, 160, 380, 66.0), (2234, 150, 430, 66.0), (2236, 150, 560, 66.0)]),
    'p1':    (0, [(2217, 330, -330, 62.3), (2218, 330, -270, 62.3), (2219, 335, -180, 62.3), (2220, 338, -90, 62.3), (2222, 345, 20, 62.3), (2225, 365, 170, 62.3), (2228, 375, 330, 62.3), (2230, 380, 450, 62.3)]),
    'rectR': (180.0, [(2218, -10), (2222, 60), (2225, 165), (2229, 300), (2233, 430)]),
    'p2':    (0, [(2226, 335, -160, 72.0), (2228, 332, 20, 72.0), (2229, 330, 100, 72.0), (2230, 328, 170, 72.0), (2231, 322, 230, 72.0), (2232, 300, 335, 72.0), (2233, 298, 340, 72.0), (2234, 285, 385, 72.0), (2235, 262, 425, 72.0), (2236, 240, 470, 72.0), (2238, 200, 560, 72.0)]),
    'dark':  (None, [(2235.9, 9000), (2236, 0), (2250, 0)]),
}


def shot_a(v, d):
    o = A_ORIGIN
    cam = [(ftime(2218), tuple(o), (0.0, 0.0, 0.0)), (ftime(2249, 'L') + 0.001, tuple(o), (0.0, 0.0, 0.0))]   # from 2218E
    d.override_camera(cam, fov=60.0)
    det = v.create_ent(classname='func_detail')
    # rust background behind both halves (static brush)
    E.add_box(v, o + np.array([700.0, -900.0, -700.0]), o + np.array([720.0, 900.0, 700.0]), 'corehub_intro/r11_sc_rust_b', ent=det)
    parts = {}
    # left 2218: the tube from the turret shot (dark rails converging to the grey ring at (316, 237))
    t = Mesh()
    for a, b in (((40.0, 0.0), (250.0, 240.0)), ((140.0, 0.0), (300.0, 232.0))):
        bar_px(t, a, b, 9.0, 60.0, 420.0, 'r11_sc_mech')
    ring = Mesh(); SM.annulus_z(ring, 0.0, 52.0, 76.0, 'r11_sc_grey', 12, True); SM.annulus_z(ring, 0.0, 48.0, 52.0, 'r11_sc_line', 12, True)
    t.add(ring.transform(R=rot_y(-90)), offset=img_pt(316, 237, 420.0))
    parts['tube'] = clip_half(t, 1.0)
    # left: the grey ring band (top edge a flat 12-gon arc, dark rim below it), reference = its top edge at screen y 0
    b = Mesh()
    card([(0, 0), (160, -8), (330, 30), (330, 160), (0, 160)], 150.0, 'r11_sc_ring_lip', b)        # film 2225: grey 85-100
    card([(0, 160), (330, 160), (330, 175), (0, 175)], 149.0, 'r11_sc_line', b)
    parts['bandL'] = clip_half(b.transform(offset=-img_pt(0, 0, 150.0) * np.array([0, 0, 1.0])), 1.0)
    # left: the cake, top facing the camera (reference = centre of its top)
    ck = SM.cake(); ck.transform(offset=(0, 0, -14.0)); ck.transform(R=rot_y(-90))
    parts['cake'] = ck
    # left: the scan head on its arm (three translucent yellow cones round a grey hub, white arm up out of the frame)
    # film 2233: cones 110-220 px wide at the bottom, the arm's segments 35-60 px wide coming down at x 40-130 (left of
    # the head), joints at y ~150 and ~330
    hd = Mesh()
    for k in range(3):
        a = math.radians(90 + 120 * k)
        hd.sphere(V(4.0, 4.6 * math.cos(a), 4.6 * math.sin(a)), 4.0, 'r11_sc_yellow', n=10, m=6)
    hd.sphere(V(-2.0, 0, 0), 3.2, 'r11_sc_grey', n=10, m=6)
    hd.box((-6.0, 1.5, 2.0), (-2.0, 7.0, 6.0), 'r11_sc_white')
    hd.box((-8.0, 5.0, 2.0), (-3.0, 11.0, 22.0), 'r11_sc_white')
    hd.box((-9.0, 4.0, 22.0), (-2.0, 13.0, 29.0), 'r11_sc_white')
    hd.box((-8.0, 4.5, 29.0), (-3.0, 10.5, 47.0), 'r11_sc_white')
    hd.box((-9.0, 3.5, 47.0), (-2.0, 12.5, 54.0), 'r11_sc_white')
    hd.box((-8.0, 5.0, 54.0), (-3.0, 10.0, 200.0), 'r11_sc_white')
    parts['head'] = hd
    # right: the lower-right petal and the upper-right petal with the hub ring and two cyan lights (corner = reference)
    q = SM.I.quarter()
    parts['p1'] = Mesh().add(q, R=rot_x(180))
    p2 = Mesh().add(q, R=rot_x(90))
    hub = Mesh(); SM.annulus_z(hub, 0.0, 10.0, 15.0, 'r11_sc_mech', 16, True)
    for k in range(2):
        a = math.radians(135 + 90 * k)
        hub.sphere(V(15.0 * math.cos(a), 15.0 * math.sin(a), 0.5), 2.2, 'r11_sc_cyan', n=8, m=5)
    p2.add(hub.transform(R=rot_y(-90)), offset=(-1.0, 0, 0))
    fr = Mesh(); SM.annulus_z(fr, 0.0, 44.5, 53.0, 'r11_sc_mech', 24, True)       # the iris frame's dark ring (film 2233: arc from (0, 280) to (300, 330))
    p2.add(clip_half(fr.transform(R=rot_y(-90)), 1.0), offset=(2.0, 0, 0))          # (its left half only: the film shows rust right of the petal)
    parts['p2'] = p2
    # right: the grey band and two dark posts above it (reference: its bottom edge at screen y 0)
    r = Mesh()
    card([(320, -230), (500, -230), (500, 0), (320, 0)], 180.0, 'r11_sc_ring_top', r)
    bar_px(r, (342, -230), (342, 0), 9.0, 170.0, 170.0, 'r11_sc_mech'); bar_px(r, (368, -230), (368, 0), 9.0, 170.0, 170.0, 'r11_sc_mech')
    parts['rectR'] = clip_half(r.transform(offset=-img_pt(0, 0, 180.0) * np.array([0, 0, 1.0])), -1.0)
    # 2236-2249: dark posts and a beam over the rust
    gd = Mesh()
    for px in (150.0, 470.0):
        c = img_pt(px, 200.0, 300.0); gd.box(c + np.array([-10.0, -18.0, -400.0]), c + np.array([10.0, 18.0, 400.0]), 'r11_sc_mech')
    c = img_pt(320.0, 120.0, 300.0); gd.box(c + np.array([-10.0, -500.0, -14.0]), c + np.array([10.0, 500.0, 14.0]), 'r11_sc_mech')
    parts['dark'] = gd
    hid = o + np.array([0.0, 0.0, -700.0])         # parked inside the shell
    tabs = []
    for nm, mesh in parts.items():
        prop(v, model('r11_sc_a_' + nm, mesh), hid, (0, 0, 0), 'r11_sc_a_' + nm)
        dep0, keys = A_KEYS[nm]; rows = []
        for k in keys:
            if dep0 is None: p = o + np.array([0.0, 0.0, -float(k[1])])
            elif dep0 > 0: p = o + np.array([0.0, 0.0, -(float(k[1]) - 199.5) * dep0 / F_PX])
            else: p = o + img_pt(k[1], k[2], k[3])
            rows.append('[%.2f,Vector(%.2f,%.2f,%.2f)]' % ((k[0], ) + tuple(p)))
        tabs.append('["r11_sc_a_%s",[%s]]' % (nm, ','.join(rows)))
    d.append('''scA <- [%s];
function Sc_ShotA(t) {
    if(t<73.9 || t>75.25) return;
    local n=floor(t*29.97002997+0.02);
    foreach(it in scA) {
        local tab=it[1], p=Vector(%.2f,%.2f,%.2f);
        if(n>=tab[0][0] && n<=tab[tab.len()-1][0]) {
            for(local i=0;i<tab.len()-1;i++) if(n<=tab[i+1][0]) { local a=tab[i],b=tab[i+1],f=(n-a[0])/(b[0]-a[0]); p=a[1]+(b[1]-a[1])*f; break; }
        }
        MoveProp(it[0],p);
    }
}''' % (','.join(tabs), hid[0], hid[1], hid[2]))
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
        prop(v, pet, o + np.array([0.0, off * math.cos(a), off * math.sin(a)]), (0.0, 0.0, -90.0 + 90 * k + 90), static=True)
    # the wall around the iris (rust) and the wall with the port further on
    rust = Mesh()
    for x0, hole in ((-6.0, 1.25 * D_PETAL_R + 18.0), (D_PORT_X, 62.0)):
        # square slab with a square hole, facing -x (toward the camera)
        H = 1600.0
        for (y0, y1, z0, z1) in ((-H, -hole, -H, H), (hole, H, -H, H), (-hole, hole, -H, -hole), (-hole, hole, hole, H)):
            q = [V(x0, y0, z0), V(x0, y0, z1), V(x0, y1, z1), V(x0, y1, z0)]
            uv = [(y0 / 768.0, z0 / 768.0), (y0 / 768.0, z1 / 768.0), (y1 / 768.0, z1 / 768.0), (y1 / 768.0, z0 / 768.0)]
            rust.tri('r11_sc_rust', q[0], q[1], q[2], uv=[uv[0], uv[1], uv[2]]); rust.tri('r11_sc_rust', q[0], q[2], q[3], uv=[uv[0], uv[2], uv[3]])
    prop(v, model('r11_sc_d_walls', rust), o, static=True)
    # grey iris frame behind the petals (seen in the gaps), the tube's mouth: dark 12-gon line, grey ring
    fr = Mesh()
    SM.annulus_z(fr, 0.0, 37.0, 1.25 * D_PETAL_R + 18.0, 'r11_sc_grey', 12, True)
    SM.annulus_z(fr, 0.0, 35.0, 37.0, 'r11_sc_line', 12, True)
    SM.annulus_z(fr, -30.0, 14.0, 22.0, 'r11_sc_grey', 12, True)
    prop(v, model('r11_sc_d_frame', fr.transform(R=rot_y(-90))), o + np.array([3.0, 0.0, 0.0]), static=True)
    # rails along the tube (from the iris to the end)
    for k in range(4):
        a = math.radians(45 + 90 * k); c = np.array([0.0, 34.0 * math.cos(a), 34.0 * math.sin(a)])
        E.add_box(v, o + c + np.array([-10.0, -0.9, -0.9]), o + c + np.array([D_FLOOR_END + 400.0, 0.9, 0.9]), 'corehub_intro/r11_sc_rail_b', ent=det)
    # port ring in the second wall and the collars beyond it (12-gon collars, axis +x)
    col = model('r11_sc_collar', SM.collar_wide().transform(R=rot_y(90)))
    # film: the nearest collar at r 88 px (320 ahead) in 2480 and 2483, r 138 (205 ahead) in 2488: the collar after
    # 1670 sits at 2170 (round 2's 2030 passed right at the camera at 83.0)
    xs = [D_PORT_X] + [D_COLLAR0 + D_COLLAR_STEP * k for k in range(3)] + [2170.0, 2530.0, 2890.0]
    for k, x in enumerate(xs):
        prop(v, col, o + np.array([x, 0.0, 0.0]), (0, 0, 0), static=True)
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
# ring bands (round 3): edges tracked through the film's angular-mean radial profiles 2266-2400 (out/sc/r3/tools/
# kymo2.py, ringtrack2.py) and fitted r = F*R/(zc - z) with the ride's camera heights (median error <= 1.7 px):
#   A  light from (R 140, z -38.6) to (R 173, z -56.5) (a cone: the outer edge lies lower)
#   B  dark 128-143 at z -216 with its lip down to -233 (R 129.7), light 143-170.5 (2306: light 186-212 px)
#   C  light 125-155 at -279 (2292: light 116-136 px, 2340: light to 254 px);  D  light 109-150 at -322;  E  light 131 (-397) to 168 (-420)
#   ring -460: 64-105.5 with the thin dark line at 67-71
# the round-2 plates at +50, -50, -110 and -165 (R 125-163) are not in the film: it is dark there (2278: 260-320 px,
# 2292: 195-250 px, 2306: 220-290 px)
C_BANDS = [(140.0, -38.6, 173.0, -56.5, 'light', 0.0), (128.0, -216.0, 143.0, -216.0, 'dark', 17.0), (143.0, -216.0, 170.5, -217.6, 'light', 0.0),
           (125.0, -279.0, 155.0, -279.0, 'light', 6.0), (109.0, -322.0, 150.0, -322.0, 'light', 6.0), (131.0, -397.0, 168.0, -420.0, 'light', 8.0)]
C_RING = (-460.0, 64.0, 105.5)
C_FLOOR = -715.0
C_BOARDS = [(50.0, 44.0), (50.0, 223.0), (-128.0, 130.0), (-128.0, 318.0), (-318.0, 43.0), (-318.0, 223.0)]
C_WALL_R = 330.0
C_HEAD = dict(z=-372.0, arm_angle=225.0)
C_CUBE = dict(n0=2255.0, z0=302.0, vz=-9.6, size=35.6)     # film 2255 / 2290 / 2306: cube 45 / 235 / 330 below the camera
# red beams (eye, direction, length, end radius, visible t0-t1)
C_RED = [((-128.0, 318.0), (-0.45, 0.35, -1.0), 420.0, 10.0, 74.0, 80.0)]     # (cones from the top boards' eyes toward the bottom made a red disc at the centre, not the film's wedges: left out)


def shaft_c(v, o):
    det = v.create_ent(classname='func_detail')
    # ring bands (static, one model)
    bm = Mesh()
    for r0, z0, r1, z1, kind, lip in C_BANDS:
        b = SM.band(r0, z0, r1, z1, lip=lip, phase=math.radians(15))
        if kind == 'dark':
            for t in b.tris:
                if t.mat.startswith('r11_sc_band') and t.mat not in ('r11_sc_band_under', 'r11_sc_band_lip'): t.mat = 'r11_sc_band_mid'
        bm.add(b)
    prop(v, model('r11_sc_bands', bm), o, (0, 0, 0), static=True)
    z, a0, a1 = C_RING
    m = Mesh(); SM.annulus_z(m, 0.0, a0 + 7.0, a1, 'r11_sc_ring_top', 12, True); SM.annulus_z(m, 0.0, a0 + 3.0, a0 + 7.0, 'r11_sc_line', 12, True)
    SM.annulus_z(m, 0.0, a0, a0 + 3.0, 'r11_sc_ring_top', 12, True)
    SM.wall_z(m, -14.0, 0.0, a1, 'r11_sc_ring_lip', 12, inward=False)
    prop(v, model('r11_sc_ring460', m), o + np.array([0.0, 0.0, z]), (0, 0, 0), 'r11_sc_c_ring')
    # posts
    P = C_POSTS
    for k, ang in enumerate(P['angles']):
        c = o + np.array([P['r'] * math.cos(math.radians(ang)), P['r'] * math.sin(math.radians(ang)), 0.0])
        E.add_box(v, c + np.array([-P['w'] / 2, -P['w'] / 2, P['z0']]), c + np.array([P['w'] / 2, P['w'] / 2, P['z1']]), 'corehub_intro/r11_sc_rail_b', ent=det)
    # boards (film 2293: white plates about 2/3 of the round-2 size with black mechanism, outer ends at R ~118)
    bmdl = model('r11_sc_board2', SM.board2(48.0, 16.0))
    for k, (z, ang) in enumerate(C_BOARDS):
        a = math.radians(ang); r0 = 118.0
        prop(v, bmdl, o + np.array([r0 * math.cos(a), r0 * math.sin(a), z]), (0.0, ang, 0.0), static=True)
    # floor (rust) and the white target
    fl = Mesh(); q = [V(-900, -900, 0), V(900, -900, 0), V(900, 900, 0), V(-900, 900, 0)]
    uv = [(-900 / 600.0, -900 / 600.0), (900 / 600.0, -900 / 600.0), (900 / 600.0, 900 / 600.0), (-900 / 600.0, 900 / 600.0)]
    fl.tri('r11_sc_rust', q[0], q[1], q[2], uv=[uv[0], uv[1], uv[2]]); fl.tri('r11_sc_rust', q[0], q[2], q[3], uv=[uv[0], uv[2], uv[3]])
    SM.annulus_z(fl, 2.0, 0.0, 23.0, 'r11_sc_target', 24, True)
    SM.annulus_z(fl, 2.0, 23.0, 38.0, 'r11_sc_grey', 12, True)
    prop(v, model('r11_sc_floor_c', fl), o + np.array([0.0, 0.0, C_FLOOR]), (0, 0, 0), static=True)
    # shaft wall beyond the bands (dim rust, 12-gon)
    prop(v, model('r11_sc_wall_c', SM.shaft_wall(C_WALL_R, C_FLOOR, 1200.0, material='r11_sc_rust_dark', uv=(600.0, 400.0))), o, (0, 0, 0), static=True)
    # eyes at the boards' inner ends (lens toward the shaft axis), red beams from some of them
    em = model('r11_sc_eye2', SM.eye(6.0))
    for k, (z, ang) in enumerate(C_BOARDS):
        a = math.radians(ang); r0 = 62.0
        prop(v, em, o + np.array([r0 * math.cos(a), r0 * math.sin(a), z - 6.0]), (0.0, ang + 180.0, 0.0), static=True)
    red = []
    for k, ((z, ang), dvec, ln, rad, _, _) in enumerate(C_RED):
        a = math.radians(ang); p0 = o + np.array([62.0 * math.cos(a), 62.0 * math.sin(a), z - 6.0]); red.append(p0)
        dv = np.array(dvec, dtype=float); dv /= np.linalg.norm(dv)
        from lib.tube import frame_angles
        left = np.cross([0, 0, 1.0], dv) if abs(dv[2]) < 0.95 else np.array([0, 1.0, 0])
        prop(v, model('r11_sc_red%d' % k, SM.cone(ln, rad)), p0, frame_angles(dv, left), 'r11_sc_c_red%d' % k)
    # scan head on its arm, yellow cones pointing up (toward the descending camera)
    hz = C_HEAD['z']; aa = math.radians(C_HEAD['arm_angle'])
    prop(v, 'transfer_scan_head', o + np.array([0.0, 0.0, hz]), (90.0, 0.0, 0.0), 'r11_sc_c_head')
    prop(v, 'transfer_scan_cones', o + np.array([0.0, 0.0, hz]), (90.0, 0.0, 0.0), 'r11_sc_c_cones')
    arm = Mesh().box((0.0, -10.0, -9.0), (C_WALL_R, 10.0, 9.0), 'r11_sc_white')     # film 2405: one arm, ~40 px wide
    prop(v, model('r11_sc_arm', arm), o + np.array([0.0, 0.0, hz - 30.0]), (0.0, C_HEAD['arm_angle'], 0.0), 'r11_sc_c_arm')
    # the cube falling ahead of the camera (own unlit model, moved and turned by Sc_Cube)
    prop(v, model('r11_sc_cube', SM.cube(36.0)), o + np.array([0.0, 0.0, C_CUBE['z0']]), (20, 30, 10), 'r11_sc_c_cube')
    shell(v, o + np.array([-1000.0, -1000.0, C_FLOOR - 300.0]), o + np.array([1000.0, 1000.0, 1300.0]))
    return red


# cube below the camera. Round 3, measured on the film frames (dome = the face's round plate, 15.6 units across):
#   2253 dome at (290, 45) 185 px, 2255 (265, 205) 190 px, 2258 (140, 120) 210 px, 2259 (120, 176) 224 px,
#   2261 (112, 328) 240 px, 2263 leaving at the lower left -> face 40 .. 30 units ahead (centre 58 .. 47)
#   from 2266 on the axis below the camera (round 2: 2270 ~220 below at the upper left, 2290 ~330, 2306 ~420)
C_CUBE_S = [(2250.0, 58.0, 300.0, -90.0), (2253.0, 54.0, 290.0, 45.0), (2255.0, 52.0, 265.0, 205.0), (2258.0, 49.0, 140.0, 120.0),
            (2259.0, 48.0, 120.0, 176.0), (2261.0, 47.0, 112.0, 328.0), (2263.0, 46.0, 40.0, 430.0), (2264.0, 46.0, -60.0, 520.0)]   # face (dz - 18) 40 .. 28: the face ~540 px wide in 2255
C_CUBE_D = [(2266.0, 190.0), (2270.0, 220.0), (2290.0, 330.0), (2306.0, 420.0), (2330.0, 560.0), (2345.0, 750.0)]


def head_hook(d, o, red):
    """the scan head rises to meet the camera on its arm (film: small at the centre 79.75 s (cones ~60 px, ~540 below
    the camera), big 80.25 s (cones ~300 px, ~110 below)), then drops away after 80.53 s (2416-2428: it shrinks)"""
    hz = C_HEAD['z']
    d.append('scRed <- [%s];' % ','.join('Vector(%.2f,%.2f,%.2f)' % tuple(p) for p in red))
    d.append('scRedT <- [%s];' % ','.join('[%.2f,%.2f]' % (r[4], r[5]) for r in C_RED))
    d.append('scPark <- Vector(%.1f,%.1f,%.1f);' % (o[0], o[1], o[2] - 900.0))     # hidden parts wait below the floor, inside the shell
    d.append('''scHeadZ <- [[78.9,-900.0],[79.75,-745.0],[80.25,%.1f],[80.53,%.1f],[81.2,%.1f]];
function Sc_Head(t) {
    if(t<74.0 || t>81.2) return;
    foreach(i,w in scRedT) MoveProp("r11_sc_c_red"+i,(t<w[0] || t>w[1])?scPark:scRed[i]);
    local f=(t-78.9)/1.1; if(f>1)f=1; if(f<0)f=0;
    local z=Lerp1(scHeadZ,t);
    local p=(t<78.9)?scPark:Vector(%.2f+(%.2f)*f, %.2f+(%.2f)*f, %.2f+z);
    foreach(nm in ["r11_sc_c_head","r11_sc_c_cones"]) MoveProp(nm,p);
    MoveProp("r11_sc_c_arm",(t<78.9)?scPark:p+Vector(0,0,-30));
    MoveProp("r11_sc_c_ring",(t>80.62)?scPark:Vector(%.2f,%.2f,%.2f));
}''' % (hz, hz, hz - 650.0 * (81.2 - 80.53), o[0] + 40.0, -50.0, o[1] + 40.0, -40.0, o[2], o[0], o[1], o[2] + C_RING[0]))
    d.hook('Sc_Head(t);', late=True)


def cube_hook(d, o, cam):
    ts = np.array([c[0] for c in cam]); zs = np.array([c[1][2] for c in cam]); xs = np.array([c[1][0] for c in cam]); ys = np.array([c[1][1] for c in cam])
    from lib.mesh import angle_matrix
    rows = []
    for row in C_CUBE_S + C_CUBE_D:
        n, dz = row[0], row[1]
        t = ftime(n) + FT / 4
        p = np.array([float(np.interp(t, ts, xs)), float(np.interp(t, ts, ys)), float(np.interp(t, ts, zs))])
        k = int(np.argmin(np.abs(ts - t))); M = angle_matrix(*cam[k][2]); f, left, up = M[:, 0], M[:, 1], M[:, 2]
        if len(row) == 4:           # seen at a screen position (px, py), its face dz - 18 ahead
            dd = dz - 18.0
            q = p + f * dz - left * (row[2] - 319.5) * dd / 461.88 - up * (row[3] - 199.5) * dd / 461.88
        else:                       # on the axis below once the camera looks down the shaft
            side = max(0.0, min(1.0, (2290.0 - n) / 25.0)) * np.array([45.0, 45.0, 0.0])     # film 2270: upper left
            q = np.array([o[0], o[1], p[2] - dz]) + side
        rows.append((t, q[0], q[1], q[2]))
    d.append('''scCube <- [%s];
function Sc_Cube(t) {
    if(t<74.9 || t>78.4) return;
    local e=Entities.FindByName(null,"r11_sc_c_cube"); if(e==null) return;
    if(t>=scCube[scCube.len()-1][0]){e.SetOrigin(Vector(%.1f,%.1f,%.1f));return;}
    local i=0; while(i<scCube.len()-2 && t>=scCube[i+1][0]) i++;
    local a=scCube[i], b=scCube[i+1], f=(t-a[0])/(b[0]-a[0]); if(f<0)f=0;
    e.SetOrigin(Vector(a[1]+(b[1]-a[1])*f, a[2]+(b[2]-a[2])*f, a[3]+(b[3]-a[3])*f));
    local n=t*29.97002997-2255.0;
    e.__KeyValueFromString("angles",(18+1.1*n)+" "+(12+2.2*n)+" "+(8+0.7*n));
}''' % (','.join('[%.4f,%.2f,%.2f,%.2f]' % r for r in rows), o[0], o[1], o[2] - 900.0))
    d.hook('Sc_Cube(t);', late=True)


C_TURN = 32.0      # degrees by 2430 (smoothstep from 2414); 50 lost the scan head above the frame at 81.0, a slow ramp kept it too central


def shot_c(v, d):
    tr = c_track()
    tr = [x for x in tr if 2264 <= int(round((x[0] - FT / 4) / FT)) <= 2412]
    cam = c_camera(tr, ftime(2250), ftime(2412, 'L'), C_ORIGIN)
    # 2413-2429 (COLMAP lost the camera): it goes on down slowly and pitches toward the picture's bottom (film: the
    # ring at -460 slides up out of the frame 2416-2421, the scan head moves to the top centre, the wall's dark bands
    # cross the frame 2422-2429), C_TURN degrees by 2430 where shot C2 takes over
    from lib.mesh import angle_matrix
    last = cam[-1]; p0 = np.array(last[1]); t0 = last[0]
    M0 = angle_matrix(*last[2]); f0, u0 = M0[:, 0], M0[:, 2]
    for n in range(2413, 2430):
        for mo in 'EL':
            t = ftime(n, mo); fr = n + (0.5 if mo == 'L' else 0.0)
            a = min(1.0, max(0.0, (fr - 2414.0) / (2430.0 - 2414.0))); th = math.radians(C_TURN * a * a * (3 - 2 * a))
            f = math.cos(th) * f0 - math.sin(th) * u0; u = math.cos(th) * u0 + math.sin(th) * f0
            cam.append((t, tuple(p0 + np.array([0.0, 0.0, -4.0 * (t - t0) / FT])), qangle(f, u)))
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
    prop(v, model('r11_sc_c2_wall', rust), o, static=True)
    # the iris (same parts as shot D), the tube behind it
    pet = model('r11_sc_petal_d', SM.I.quarter().transform(scale=D_PETAL_R / SM.I.PETAL_R))
    off = 25.5
    for k in range(4):
        a = math.radians(45 + 90 * k)
        prop(v, pet, o + np.array([-1.0, off * math.cos(a), off * math.sin(a)]), (0.0, 0.0, 90.0 * k), static=True)
    prop(v, 'r11_sc_d_frame', o + np.array([2.0, 0.0, 0.0]), static=True)
    for k in range(4):
        a = math.radians(45 + 90 * k); c = np.array([0.0, 34.0 * math.cos(a), 34.0 * math.sin(a)])
        E.add_box(v, o + c + np.array([0.0, -0.9, -0.9]), o + c + np.array([900.0, 0.9, 0.9]), 'corehub_intro/r11_sc_rail_b', ent=det)
    E.add_box(v, o + np.array([700.0, -300.0, -300.0]), o + np.array([720.0, 300.0, 300.0]), 'corehub_intro/r11_sc_rust_b', ent=det)
    # dark posts and beams in front of the wall
    for (x, y), w in C2_POSTS:
        E.add_box(v, o + np.array([x - w / 2, y - w / 2, -500.0]), o + np.array([x + w / 2, y + w / 2, 500.0]), 'corehub_intro/r11_sc_rail_b', ent=det)
    for x, z, h in C2_BEAMS:
        E.add_box(v, o + np.array([x - 8.0, -500.0, z - h / 2]), o + np.array([x + 8.0, 500.0, z + h / 2]), 'corehub_intro/r11_sc_rail_b', ent=det)
    # scan head hanging on its white arm, three translucent yellow cones down toward the iris (own model; film 2458:
    # cones x 280-370 / y 20-115 px at ~184 ahead -> 36 units wide, 38 tall; the stock-size head was twice as wide)
    hd = Mesh()
    for k, (dy, dx) in enumerate(((-9.0, 2.0), (9.0, 2.0), (0.0, -6.0))):
        hd.sphere(V(dx, dy, -14.0), 8.0, 'r11_sc_yellow', n=12, m=8, squash=(1.0, 1.0, 1.9))
    hd.sphere(V(0.0, 0.0, 2.0), 6.0, 'r11_sc_grey', n=10, m=6)
    hd.box((-5.0, -6.0, 6.0), (5.0, 6.0, 16.0), 'r11_sc_white')
    hd.box((-3.0, -3.0, 16.0), (3.0, 3.0, 140.0), 'r11_sc_white')
    prop(v, model('r11_sc_c2_head', hd), o + C2_HEAD + np.array([0.0, 0.0, 14.0]), (0, 0, 0), static=True)
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
