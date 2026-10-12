"""Sludge / gallery (84.58-95.69 s, film frames 2535-2868), rebuilt from the film's measurements in cell C4.

ONE continuous ride (no hard cut: the similarity drop at 2706 is a collar sliding past the lens):
  * 2536-2569 shaft: the camera rises up a tall rust shaft looking up (image up = -X), measured with ride_export
    (sludge 2536 2603 anchor 2552 -> data/sg_a_ride.json: speed from the collars 98-110 u/frame, true scale); a copper
    ring travels ahead of the camera (constant apparent size in the film), moved by the director (SgRing);
  * 2570-2601 quarter bend: the view pitches 90 deg from up (+Z) to +X (lines + gyro chain of the export, smoothed);
    the path tangent lags the view by up to 9 deg (the view leads into the turn) and reaches +X at 2602;
  * 2602-2758 gallery: the tube runs straight along +X high above a test chamber (sludge pit, white ledge, upper floor
    with door / signs / vat / plate, light bridge, leaning panel, a turret with a long pole); the camera pitches down to
    61 deg and back up; it leaves through a collar in a bulkhead into the rust room;
  * 2759-2827 right turn (+X -> -Y) along the rust room's plank wall (white truss catwalk, a wall hole);
  * 2828-2867 straight along -Y toward lit collars; film fades measured from the frames' brightness (SgFade).
The camera of 2602-2867 is the COLMAP model of the frames (one model, 2536-2867; its shaft part is flipped and unused),
rotated to the room axes with the line-measured orientations (they agree to 1.4 deg over 2600-2752), positions after
2832 continued at the measured speed (COLMAP's positions jump there). Scale S = 545 map units per COLMAP unit: the
gallery collars then match the film's apparent sizes and the shaft-side wall plane of the export (X 2060) lands on the
COLMAP entrance wall (X 1906..2085); an earlier guess of 1240 (equal collar spacing) made every gallery collar 2.3x
too small. The whole scene is built at unit K = 0.6 (the ride is 8000 long at true scale; rails rho 34K, collars K).
Build the camera data with:  python3 -c "import sys; sys.path.insert(0,'.'); from scenes import sludge; sludge.build_camera()"
"""
import json, math, os
import numpy as np
from lib import vmfedit as E, tube
from lib.ride import Ride

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
NAME = 'sg'                                   # data/sg_ride.json (camera + tube centre line, map axes, true scale)
K = 0.6                                       # build scale (cell C4 is too small for true scale)
ORIGIN = (5950.0, 7300.0, -1700.0)            # map position of the camera at frame 2536 (shaft bottom)
S_COLMAP = 545.0                              # map units per COLMAP unit (gallery and later)
BLACK = 'corehub_intro/void_black'
F0, F1 = 2536, 2867


def T(n):
    return n * 1001 / 30000.0


# ---------------------------------------------------------------------------------------------- camera measurement
def build_camera():
    """measure -> data/sg_ride.json (run: python3 scenes/sludge.py camera; needs the offline tools)"""
    import sys, pickle
    sys.path.insert(0, '/home/claude/offline')
    import orient as O
    from sfmtools import Recon
    ex = json.load(open(os.path.join(HERE, 'data', 'sg_a_ride.json')))
    orr = pickle.load(open('/home/claude/offline/out/sg_a_orient.pkl', 'rb'))
    toM = lambda v: np.array([-v[2], v[1], v[0]], dtype=float)          # export room axes -> map axes
    # --- COLMAP aligned to map axes (rotation from the line-measured orientations of 2600-2750)
    C = Recon('sludge', 0)
    allr = pickle.load(open('/home/claude/offline/out/sg_all_orient.pkl', 'rb'))['R']
    Qs = []
    for n in range(2600, 2751):
        if n in allr and C.has(n, 'E'):
            f, r, u = O.to_basis(allr[n]); c, (cf, cr, cu) = C.pose(n, 'E')
            Qs.append(np.array([f, r, u]).T @ np.array([cf, cr, cu]))
    U_, S_, Vt = np.linalg.svd(sum(Qs)); Q = U_ @ Vt
    Mx = np.array([[0, 0, -1], [0, 1, 0], [1, 0, 0]], float)
    A = Mx @ Q
    cpos = {n: A @ C.pose(n, 'E')[0] for n in range(2598, F1 + 1)}
    cdir = {n: (A @ C.pose(n, 'E')[1][0], A @ C.pose(n, 'E')[1][2]) for n in range(2598, F1 + 1)}
    # COLMAP breaks after 2832 (positions jump by the wall's pattern): keep its orientation, continue the position
    for n in range(2833, F1 + 1):
        cpos[n] = cpos[n - 1] + np.array([0.0, -(0.093 + 0.0003 * (n - 2833)), 0.0])
    # gallery line (y, z) and final line (x) in COLMAP units
    gl = np.array([cpos[n] for n in range(2600, 2756)]); yg, zg = float(np.median(gl[:, 1])), float(np.median(gl[:, 2]))
    xf = float(np.median([cpos[n][0] for n in range(2822, 2833)]))
    # --- shaft: export positions (map Z = room x), speeds; bend: smoothed pitch, speed profile
    mom = {(r[1], r[2]): r for r in ex['moments']}
    th = {}
    for n in range(2566, 2611):
        if n in orr['R']:
            f = toM(O.to_basis(orr['R'][n])[0]); th[n] = math.degrees(math.atan2(f[0], f[2]))
    ns = np.array(sorted(th)); tv = np.array([th[n] for n in ns])
    ok = np.ones(len(ns), bool)
    for _ in range(3):
        c = np.polyfit(ns[ok] - 2585.0, tv[ok], 5); res = tv - np.polyval(c, ns - 2585.0); ok = np.abs(res) < 3.0
    theta = lambda x: float(np.clip(np.polyval(c, x - 2585.0), 0.0, 180.0)) if x >= 2569.5 else 0.0
    # speed per frame: export straight speeds, then 108 through the bend, easing to the gallery's speed at 2599
    sx = {n: mom[(n, 'E')][3] for n in range(2536, 2569)}
    J = 2602                                          # the gallery line starts here (end of the bend)
    v_g = S_COLMAP * float(np.linalg.norm(cpos[J + 5] - cpos[J])) / 5.0
    def speed(x):
        if x < 2567: return sx[int(math.floor(x)) + 1] - sx[int(math.floor(x))]
        if x < 2591: return 108.0
        if x < J: return 108.0 + (v_g - 108.0) * (x - 2591) / float(J - 2591)
        return v_g
    # path tangent in the bend: the view leads into the turn (about 9 deg in the middle), the tangent reaches 90 at J
    thJ = theta(float(J))
    def phi(x):
        u = min(1.0, theta(x) / thJ)
        return 90.0 * (u - 0.09 * math.sin(math.pi * u))
    # integrate the shaft + bend centre line from the first frame (fine steps in frames)
    dt = 0.02; x = 2536.0; p = np.zeros(3); s = 0.0
    curve = [(x, p.copy())]; sof = {2536: 0.0}
    p = np.array([0.0, 0.0, mom[(2536, 'E')][3]]); curve = [(2536.0, p.copy())]
    while x < J - 1e-9:
        a = math.radians(phi(x + dt / 2)); v = speed(x + dt / 2)
        p = p + v * dt * np.array([math.sin(a), 0.0, math.cos(a)]); s += v * dt; x += dt
        curve.append((x, p.copy()))
        if abs(x - round(x)) < 1e-6: sof[int(round(x))] = s
    G0 = curve[-1][1].copy()                          # start of the gallery line (map, true scale, shaft origin)
    sG = s
    # --- gallery, turn and final line: COLMAP positions (scaled), snapped onto the straight lines, smoothed in the turn
    to_map = lambda q: G0 + S_COLMAP * np.array([q[0] - cpos[J][0], q[1] - yg, q[2] - zg])
    Xf = to_map(np.array([xf, yg, zg]))[0]
    fr = np.arange(J, F1 + 1)
    raw = np.array([to_map(cpos[n]) for n in fr])
    from scipy.ndimage import median_filter
    raw0 = raw.copy()
    raw = np.stack([median_filter(raw[:, k], size=5, mode='nearest') for k in range(3)], axis=1)       # drop single-frame outliers
    raw[-3:] = raw0[-3:]                                 # (the last frames are the extrapolated straight: keep them)
    sm = raw.copy()
    for i in range(len(fr) - 4):                        # light smoothing (gaussian, sigma 1.5 frames); the ends stay
        w = np.exp(-0.5 * ((fr - fr[i]) / 1.5) ** 2); sm[i] = (raw * w[:, None]).sum(0) / w.sum()
    sm[:, 2] = G0[2]
    t_in, t_out = 2758, 2828                            # the turn (the path leaves the gallery line / joins the final line)
    for i, n in enumerate(fr):
        if n <= t_in: sm[i, 1] = G0[1]
        elif n < t_in + 8: b = (n - t_in) / 8.0; sm[i, 1] = G0[1] * (1 - b) + sm[i, 1] * b
        if n >= t_out: sm[i, 0] = Xf
        elif n > t_out - 8: b = (t_out - n) / 8.0; sm[i, 0] = Xf * (1 - b) + sm[i, 0] * b
    sm[0] = G0
    # the per-frame points are the camera at fractional frame n + 0.25 (blended frames); extend the final line
    pfr = fr + 0.25; pfr[0] = float(J)
    def pos_x(x):
        if x <= J:
            return np.array([np.interp(x, ct, cp[:, k]) for k in range(3)])
        return np.array([np.interp(x, pfr, sm[:, k]) for k in range(3)]) if x <= pfr[-1] else sm[-1] + (sm[-1] - sm[-2]) / (pfr[-1] - pfr[-2]) * (x - pfr[-1])
    ct = np.array([t for t, _ in curve]); cp = np.array([q for _, q in curve])
    L1 = float(sm[fr.tolist().index(t_in)][0] - G0[0])
    rt = float(Xf - sm[fr.tolist().index(t_in)][0])
    def orient(x):
        """(forward, up) at fractional frame x (x = n for E, n + 0.5 for L)"""
        if x < 2569.5: return np.array([0, 0, 1.0]), np.array([-1.0, 0, 0])
        a = math.radians(theta(x)); fb = np.array([math.sin(a), 0, math.cos(a)]); ub = np.array([-math.cos(a), 0, math.sin(a)])
        if x <= 2600.0: return fb, ub
        y = x - 0.25; n0 = int(math.floor(y)); w = y - n0          # COLMAP pose of blended frame n at n + 0.25
        n0 = max(2598, min(F1 - 1, n0))
        f = cdir[n0][0] * (1 - w) + cdir[n0 + 1][0] * w; u = cdir[n0][1] * (1 - w) + cdir[n0 + 1][1] * w
        if x < 2606.0:                                  # blend the bend's pitch into the COLMAP pose
            b = (x - 2600.0) / 6.0; f = fb * (1 - b) + f * b; u = ub * (1 - b) + u * b
        f = f / np.linalg.norm(f); u = u - f * (u @ f); u = u / np.linalg.norm(u)
        return f, u
    moments = []; frames = {}
    for n in range(F0, F1 + 1):
        for mo, x in (('E', float(n)), ('L', n + 0.5)):
            t = T(n) + (1001 / 60000.0 if mo == 'L' else 0.0)
            p = pos_x(x); f, u = orient(x)
            moments.append([round(t, 6), n, mo] + [round(float(q), 3) for q in p] + [round(float(q), 6) for q in f] + [round(float(q), 6) for q in u])
            if mo == 'E': frames[str(n)] = [float(q) for q in p]
    # centre line with film frame numbers: the camera path (the camera rides on the tube axis), continued at both ends
    xs = np.arange(F0, F1 + 0.5001, 0.25); P = np.array([pos_x(x) for x in xs])
    pre = [P[0] - np.array([0, 0, 1.0]) * u for u in (1000, 600, 300)]
    post = [P[-1] + (P[-1] - P[-2]) / np.linalg.norm(P[-1] - P[-2]) * u for u in (1000, 2000, 3000)]
    curve_out = [[F0 - 1 - 0.1 * (3 - i)] + [round(float(q), 3) for q in p] for i, p in enumerate(pre)]
    curve_out += [[round(float(x), 3)] + [round(float(q), 3) for q in p] for x, p in zip(xs, P)]
    v_end = float(np.linalg.norm(P[-1] - P[-2])) / 0.25
    curve_out += [[round(float(xs[-1] + u / v_end), 3)] + [round(float(q), 3) for q in p] for u, p in zip((1000, 2000, 3000), post)]
    sections = [dict(kind='straight', first=2536, last=2569, forward='+z', up='-x'),
                dict(kind='bend', first=2570, last=J - 1, forward=None, up=None),
                dict(kind='straight', first=J, last=t_in, forward='+x', up='+z'),
                dict(kind='bend', first=t_in + 1, last=t_out - 1, forward=None, up=None),
                dict(kind='straight', first=t_out, last=F1, forward='-y', up='+z')]
    rings = [dict(frame=2557.05, edges=4), dict(frame=2573.27, edges=2)]
    out = dict(db='sludge', first=F0, last=F1, unit=1.0, moments=moments, sections=sections, planes=[], rings=rings, frames=frames,
               curve=curve_out, s={}, speed={}, info=dict(S=S_COLMAP, G0=G0.tolist(), Xf=float(Xf), turn_radius=float(rt), gallery_len=float(L1),
                                                          v_g=v_g, theta_fit=c.tolist(), colmap_ref=cpos[J].tolist(), yg=yg, zg=zg, xf=xf,
                                                          A=A.tolist()))
    json.dump(out, open(os.path.join(HERE, 'data', NAME + '_ride.json'), 'w'))
    print('gallery line from', np.round(G0, 1), 'length %.0f, turn radius %.0f at X %.0f, v_g %.1f' % (L1, rt, Xf, v_g))
    for row in moments[::40]: print(row[:6], np.round(row[6:9], 2))


def colmap_to_map(q, info, origin=ORIGIN, unit=K):
    """COLMAP-aligned point (as in align: A @ X) -> map position"""
    G0 = np.array(info['G0']); c = info['colmap_ref']
    p = G0 + info['S'] * np.array([q[0] - c[0], q[1] - info['yg'], q[2] - info['zg']])
    return np.asarray(origin) + unit * p


# ---------------------------------------------------------------------------------------------- map
def shell(v, lo, hi, mat=BLACK, t=32.0):
    lo = np.asarray(lo, dtype=float); hi = np.asarray(hi, dtype=float)
    for ax in range(3):
        for side in (0, 1):
            a = lo.copy() - t; b = hi.copy() + t
            if side == 0: b[ax] = lo[ax]
            else: a[ax] = hi[ax]
            E.add_box(v, a, b, mat)


def tbox(v, ent, lo, hi, mat, tex=128.0, px=128, mats=None):
    """textured brush box: the texture (px pixels) spans `tex` map units"""
    lo, hi = np.minimum(lo, hi), np.maximum(lo, hi)
    if np.any(np.asarray(hi) - np.asarray(lo) < 1.0): return None
    pr = E.add_box(v, lo, hi, mat, ent=ent, mats=mats)
    for s in pr.solid.sides:
        s.uaxis.scale = tex / px; s.vaxis.scale = tex / px
    return pr


class Geo:
    """placement helpers: q = COLMAP-aligned units (gallery and later), t = true-scale frame of the camera json"""
    def __init__(self, v, info):
        self.v = v; self.info = info; self.det = v.create_ent(classname='func_detail')
        self.lo = np.full(3, 1e9); self.hi = np.full(3, -1e9)

    def q(self, p): return colmap_to_map(p, self.info)

    def t(self, p): return np.asarray(ORIGIN) + K * np.asarray(p, dtype=float)

    def box(self, a, b, mat, tex=128.0, px=128, space='q', mats=None):
        f = self.q if space == 'q' else self.t
        A = f(a); B = f(b); lo = np.minimum(A, B); hi = np.maximum(A, B)
        self.lo = np.minimum(self.lo, lo); self.hi = np.maximum(self.hi, hi)
        return tbox(self.v, self.det, lo, hi, mat, tex, px, mats)

    def wall_with_hole(self, axis, c0, c1, lo, hi, centre, half, mat, tex=128.0, space='q'):
        """slab c0..c1 on `axis` covering lo..hi on the other two axes, with a square hole of half-size `half`
        around `centre` (other two axes)"""
        i = 'xyz'.index(axis); j, k = [a for a in range(3) if a != i]
        def mk(jl, jh, kl, kh):
            a = np.zeros(3); b = np.zeros(3); a[i], b[i] = c0, c1; a[j], b[j] = jl, jh; a[k], b[k] = kl, kh
            self.box(a, b, mat, tex, space=space)
        cj, ck = centre
        mk(lo[0], cj - half, lo[1], hi[1]); mk(cj + half, hi[0], lo[1], hi[1])
        mk(cj - half, cj + half, lo[1], ck - half); mk(cj - half, cj + half, ck + half, hi[1])


TILE = 'corehub_intro/r11_sg_tile'
SLUDGE = 'corehub_intro/r11_sg_sludge'
WHITE = 'corehub_intro/r11_sg_white'
BROWN = 'corehub_intro/r11_sg_brown'
GREY = 'corehub_intro/r11_sg_grey'
PLANK = 'corehub_intro/r11_sg_plank'
FLAT = 'corehub_intro/r11_sg_flat_black'


def gallery(g, yg, zg):
    """the observation gallery and the test chamber below it (COLMAP-aligned units; tube at y = yg, z = zg).
    Measured (COLMAP points, film pixels unprojected): sludge z -3.73; white ledge face x 1.40 (z -3.73..-2.95);
    upper floor z -2.95 to the back wall x 2.5 (door, sign); side ledges inside y 2.5 / -2.1; light bridge x 0.65,
    z -3.27; collars the camera passes at x -4.04, -2.70, 1.14 (spacing 1.33)."""
    T = 0.03; tile = 150.0
    # wall between the shaft and the gallery (brown rust, hole for the tube)
    g.wall_with_hole('x', -3.87, -3.83, (-3.4, -4.0), (3.6, 0.65), (yg, zg), 0.13, BROWN, 220.0)
    # gallery side walls and ceiling (black tiles / dark)
    g.box((-3.85, 3.5, -4.0), (2.55, 3.5 + T, 0.65), TILE, tile)
    g.box((-3.85, -3.3 - T, -4.0), (2.55, -3.3, 0.65), TILE, tile)
    g.box((-3.85, -3.3, 0.6), (1.14, 3.5, 0.6 + T), FLAT)
    # sludge pit
    g.box((-3.85, -3.3, -3.73 - T), (1.40, 3.5, -3.73), SLUDGE, 260.0, 256)
    # upper level: white face toward the pit, black floor
    g.box((1.40, -3.3, -3.73), (2.5, 3.5, -2.95), WHITE, 120.0, mats={'+z': TILE})
    # side ledges
    g.box((-1.2, 2.55, -3.73), (1.40, 2.95, -2.95), WHITE, 120.0)
    g.box((-1.2, -2.5, -3.73), (1.40, -2.1, -2.95), WHITE, 120.0)
    g.box((-1.2, 2.95, -3.73), (1.40, 3.5, -2.0), TILE, 150.0)
    g.box((-1.2, -3.3, -3.73), (1.40, -2.5, -2.0), TILE, 150.0)
    # white walkway to the vat on the upper floor
    g.box((1.40, 1.45, -2.95), (2.3, 1.98, -2.93), WHITE, 120.0)
    g.box((1.40, 0.95, -2.95), (1.75, 2.6, -2.93), WHITE, 120.0)
    # back wall of the chamber (door, signs) up to the bulkhead floor
    g.box((2.5, -3.3, -2.95), (2.55, 3.5, -0.75), TILE, tile)
    g.box((1.14, -3.3, -0.78), (2.55, 3.5, -0.75), TILE, tile)
    # bulkhead with the tube's collar (the camera leaves the gallery through it)
    g.wall_with_hole('x', 1.10, 1.14, (-3.3, -0.78), (3.5, 0.65), (yg, zg), 0.11, TILE, tile)


def chamber_props(v, info):
    """objects of the test chamber as one model (built in map units around the chamber's centre)"""
    from lib.gen import save, Mesh, V
    from models import sludge as M
    q = lambda p: colmap_to_map(p, info)
    org = q((1.4, 0.3, -2.95)); m = Mesh(); s = info['S'] * K
    L = lambda p: q(p) - org
    # the pole (horizontal, toward the camera) and the turret on its end
    m.tube(L((1.38, 0.56, -2.42)), L((-3.0, 0.56, -2.42)), 0.03 * s, 'r11_sg_pole3', n=8)
    tur = L((1.38, 0.56, -2.42))
    m.box(tur + V(-0.02, -0.03, -0.06) * s, tur + V(0.03, 0.03, 0.05) * s, 'r11_sg_whiteobj3')
    m.box(tur + V(-0.01, -0.08, -0.01) * s, tur + V(0.02, 0.08, 0.015) * s, 'r11_sg_whiteobj2')
    # vat (metal cylinder) on the upper floor
    c = L((1.72, 1.85, -2.95))
    m.tube(c, c + V(0, 0, 0.42) * s, 0.12 * s, 'r11_sg_metal2', n=14)
    M.disc(m, c + V(0, 0, 0.421) * s, 0.12 * s, (0, 0, 1), 'r11_sg_dark', n=14)
    # plate (white ring + copper disc) lying on the upper floor
    c = L((1.9, -1.45, -2.94))
    M.disc(m, c, 0.17 * s, (0, 0, 1), 'r11_sg_whiteobj3', n=20, r0=0.12 * s)
    M.disc(m, c + V(0, 0, 0.002) * s, 0.12 * s, (0, 0, 1), 'r11_sg_cupl2', n=20)
    # exit door (white disc on the back wall) and the signs
    M.disc(m, L((2.49, -0.93, -2.66)), 0.21 * s, (-1, 0, 0), 'r11_sg_whiteobj3', n=20)
    m.box(L((2.485, -1.03, -2.36)), L((2.49, -0.83, -2.26)), 'r11_sg_whiteobj2')
    m.box(L((2.485, -1.61, -2.52)), L((2.49, -1.49, -2.40)), 'r11_sg_sign')
    # square panel leaning against the ledge, on a wooden frame
    P = [L(p) for p in ((1.32, -0.62, -2.93), (1.32, -2.05, -2.93), (0.32, -2.05, -3.5), (0.32, -0.62, -3.5))]
    m.quad('r11_sg_panel3', *P)
    dn = np.cross(P[1] - P[0], P[3] - P[0]); dn = dn / np.linalg.norm(dn) * 0.02 * s
    if dn[2] > 0: dn = -dn
    Q = [p + dn + (p - sum(P) / 4) * 0.05 for p in P]
    m.quad('r11_sg_wood1', *Q)
    # light bridge between two emitters on the side ledges
    a = L((0.65, 2.5, -3.27)); b = L((0.65, -2.1, -3.27))
    m.box(np.minimum(a, b) + V(-0.006, 0, -0.002) * s, np.maximum(a, b) + V(0.006, 0, 0.002) * s, 'r11_sg_bridge')
    for e in (a, b):
        m.box(e + V(-0.05, -0.06, -0.04) * s, e + V(0.05, 0.06, 0.05) * s, 'r11_sg_metal1')
    save(m, 'r11_sg_chamber')
    E.add_prop(v, 'models/corehub_intro/r11_sg_chamber.mdl', org, (0, 0, 0), name='r11_sg_chamber')


def rust_room(g, yg, zg, xf):
    """the room after the gallery: plank wall at x 4.5 (COLMAP plane, 11000 points) with a white truss catwalk in
    front (x 4.33-4.45, top at the camera's height), a hole in the wall at y -1.96; the final tube runs along -y at x 3.90"""
    T = 0.03
    g.box((4.50, -12.0, -1.5), (4.50 + T, 1.6, 1.5), PLANK, 330.0, 256)
    g.box((1.14, 1.6, -1.5), (4.53, 1.6 + T, 1.5), PLANK, 330.0, 256)
    g.box((1.14, -12.0, 1.5), (4.53, 1.6, 1.5 + T), FLAT)
    g.box((1.14, -12.0, -1.5 - T), (4.53, 1.6, -1.5), FLAT)
    g.box((1.14 - T, -12.0, -1.5), (1.14, -3.3, 1.5), PLANK, 330.0, 256)
    g.box((1.14, -12.0 - T, -1.5), (4.53, -12.0, 1.5), PLANK, 330.0, 256)
    # wall hole (dark ragged opening) and a block of debris in it
    for dy, dz, h in ((0.0, 0.0, 0.17), (0.12, -0.06, 0.10), (-0.13, 0.05, 0.09), (0.05, 0.15, 0.08), (-0.04, -0.16, 0.09)):
        g.box((4.485, -1.96 + dy - h, zg + dz - h), (4.50, -1.96 + dy + h, zg + dz + h), FLAT)
    g.box((4.40, -1.98, zg - 0.05), (4.49, -1.86, zg + 0.02), 'corehub_intro/r11_sg_debris')


def truss_props(v, info, yg, zg):
    """white truss catwalk along the plank wall (models, one per bay group)"""
    from lib.gen import save
    from models import sludge as M
    s = info['S'] * K
    L = 1.2; H = 0.5; D = 0.14
    mesh = M.truss(L * s, H * s, D * s, 0.02 * s, bays=2)
    save(mesh, 'r11_sg_truss')
    mdl = 'models/corehub_intro/r11_sg_truss.mdl'
    k = 0
    for row_top in (zg - 0.36, zg - 0.36 - H):
        for y0 in np.arange(1.5, -11.9, -L):
            p = colmap_to_map((4.33, y0, row_top - H), info)
            E.add_prop(v, mdl, p, (0, -90, 0), name='r11_sg_truss%d' % k); k += 1


def shaft(g):
    """the shaft the camera rises in (true-scale frame of the camera json: tube axis x = y = 0, up +z)"""
    T = 40.0
    g.box((-1500, -840, -1500), (1900, -840 - T, 5900), GREY, 300.0, 256, space='t')       # right wall (white truss side)
    g.box((-1500, 840, -1500), (1900, 840 + T, 5900), GREY, 300.0, 256, space='t')         # left wall
    g.box((-1500 - T, -840, -1500), (-1500, 840, 5900), FLAT, space='t')                   # dark side (image top)
    g.box((-1500, -840, 5900), (1900, 840, 5900 + T), GREY, 300.0, 256, space='t')         # ceiling
    g.box((900, -840, -1500), (900 + T, 840, 3600), GREY, 300.0, 256, space='t')           # +x wall below the bend


def shaft_trusses(v):
    """truss towers in the shaft (true-scale frame): a white truss frame on the -y wall (image right).
    (The film's copper towers on the +y side are still missing: truss models placed there did not show in the
    offline preview, so they are left out until that is understood.)"""
    from lib.gen import save
    from models import sludge as M
    k = K
    save(M.truss(6900 * k, 160 * k, 80 * k, 22 * k, bays=36, flat=True), 'r11_sg_tw_white')
    save(M.truss(1000 * k, 140 * k, 80 * k, 20 * k, bays=6, flat=True), 'r11_sg_tw_whiteh')
    t = lambda p: np.asarray(ORIGIN) + k * np.asarray(p, dtype=float)
    n = 0
    for x0 in (-500.0, 640.0):
        E.add_prop(v, 'models/corehub_intro/r11_sg_tw_white.mdl', t((x0, -690.0, -1500.0)), (-90, 0, 0), name='r11_sg_tw%d' % n); n += 1
    for z0 in np.arange(-1200.0, 5000.0, 1100.0):
        E.add_prop(v, 'models/corehub_intro/r11_sg_tw_whiteh.mdl', t((-500.0, -690.0, z0)), (0, 0, 0), name='r11_sg_tw%d' % n); n += 1


def moving_ring(v, d, rd):
    """the copper ring that travels up the shaft ahead of the camera (2536-2568: it keeps an outer radius of about
    185 px, centre near (310, 195), while the walls stream past): a collar prop moved by the director"""
    from models import sludge as M
    from lib.gen import save
    R = 100.0 * K; D = 461.88 * R / 152.0
    save(M.ring(R, 0.6 * R), 'r11_sg_ring')
    rows = []
    for t, n, mo, p, f, u in rd.moments:
        if not (84.5 <= t <= 85.75): continue
        r = np.cross(f, u)
        c = p + f * D + r * (-10.0 / 461.88 * D) + u * (5.0 / 461.88 * D)
        a = tube.axis_angles(f)
        rows.append('[%.4f,%.2f,%.2f,%.2f,%.2f,%.2f,%.2f]' % ((t,) + tuple(c) + tuple(a)))
    E.add_prop(v, 'models/corehub_intro/r11_sg_ring.mdl', (11800, 9600, 4800), (0, 0, 0), name='r11_sg_ring')     # parked in an empty corner of the sealed cell (a prop in the void makes the map leak)
    d.append('SgRingTab <- [' + ','.join(rows) + '];\n' + '''
function SgRing(t) {
    local e=Entities.FindByName(null,"r11_sg_ring"); if(e==null) return;
    local T=SgRingTab;
    if(t<T[0][0] || t>T[T.len()-1][0]) { e.SetOrigin(Vector(11800,9600,4800)); return; }
    local i=0; while(i<T.len()-2 && t>=T[i+1][0]) i++;
    local a=T[i]; local b=T[i+1]; local f=(t-a[0])/(b[0]-a[0]); if(f<0)f=0; if(f>1)f=1;
    e.SetOrigin(Vector(a[1]+(b[1]-a[1])*f, a[2]+(b[2]-a[2])*f, a[3]+(b[3]-a[3])*f));
    e.__KeyValueFromString("angles",(a[4]+(b[4]-a[4])*f)+" "+(a[5]+(b[5]-a[5])*f)+" "+(a[6]+(b[6]-a[6])*f));
}
''')
    d.hook('SgRing(t);')


def apply(v, d):
    from models import sludge as M
    M.textures(); M.materials()
    rd = Ride(NAME, origin=ORIGIN, unit=K)
    info = rd.raw['info']
    d.override_camera(rd.camera(), fov=60.0)
    # fade in / out as the film's brightness (frames 2534-2547, 2860-2868), in the preview's linear-light blend
    d.append('''
SgFadeIn <- [[84.50,255],[84.585,254],[84.651,249],[84.718,217],[84.785,184],[84.851,166],[84.918,59],[84.951,28],[84.99,0]];
SgFadeOut <- [[95.40,0],[95.462,66],[95.495,107],[95.529,145],[95.562,178],[95.595,209],[95.629,233],[95.662,248],[95.696,254],[95.74,255]];
function SgFade(t) {
    if(t>=84.50 && t<84.99) SetScreenBlack(Lerp1(SgFadeIn,t));
    else if(t>=95.40 && t<95.74) SetScreenBlack(Lerp1(SgFadeOut,t));
}
''')
    d.hook('SgFade(t);')
    g = Geo(v, info)
    yg, zg = info['yg'], info['zg']
    gallery(g, yg, zg); rust_room(g, yg, zg, info['xf']); shaft(g); chamber_props(v, info); truss_props(v, info, yg, zg); shaft_trusses(v)
    tube.add_straight_rails(v, rd, rho=34.0 * K, width=1.8 * K, ent=g.det)
    tube.add_bend_rails(v, rd, 'r11_sg', rho=34.0 * K, width=1.8 * K)
    # collars: shaft (export ring times), gallery (COLMAP clusters at x -4.04, -2.7, 1.14), final straight
    from lib.gen import save
    save(M.collar(K), 'r11_sg_collar')
    save(M.sleeve(K), 'r11_sg_sleeve')
    save(M.collar(K, band='r11_sg_lit'), 'r11_sg_collar_lit')
    lit = 'models/corehub_intro/r11_sg_collar_lit.mdl'
    mdl = 'models/corehub_intro/r11_sg_collar.mdl'
    cu = 'models/corehub_intro/r11_sg_sleeve.mdl'
    moving_ring(v, d, rd)
    for k, x in enumerate((-3.87, -2.53, -1.20, 0.13, 1.12, 2.10)):
        p = colmap_to_map((x, yg, zg), info)
        E.add_prop(v, cu if x < 1.0 else mdl, p, tube.axis_angles((1, 0, 0)), name='r11_sg_gal_collar%d' % k)
    tube.add_collars(v, rd, model=cu, frames=[2812.0], prefix='r11_sg_turn')
    tube.add_collars(v, rd, model=lit, frames=[2841.0, 2855.0, 2869.0], prefix='r11_sg_fin')
    lo = np.array([5000.0, 3200.0, -3000.0]); hi = np.array([12000.0, 9750.0, 5000.0])
    shell(v, lo + 40, hi - 40)
    return rd


if __name__ == '__main__':
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == 'camera': build_camera()
