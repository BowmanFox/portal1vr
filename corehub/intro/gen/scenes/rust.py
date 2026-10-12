"""Rust room (32.7-38.9 s), rebuilt at the film's scale from the measured ride (tools/offline/ride.py, ride_export.py).

Shot A (frames 981-1082, cell C2, true scale) and shot B (1083-1165, cell C1, scale 0.65) each get a cell of their own
north of the old map (y > 3000), sealed by a black shell. Everything is placed relative to the measured camera path
(ride coordinates = solver coordinates, origin = the camera of the shot's first frame, +x = first direction of travel):
  * the camera: the film's camera at 60 samples per second, fov 60 (Director.override_camera);
  * the tube: rails along a cleaned copy of the measured path (the bundle-adjusted bends do not join their straights
    exactly: the joins are blended), collars where the film's camera passes collars, the junction of shot A modelled
    (main tube on to the port, branch rails split off);
  * the room: lit rust panel areas where the film shows them (walls from the measured planes, extents from the film
    frames), dark tiled floors, black everywhere else.
Measurements (film frames, 640x400, focal 461.88; see models/rust.py for colours and panel sizes):
  shot A: big wall x 4623 lit for y -1570..980, z -352..655 (frames 990/994: edges 162/88 px left, 93/47 top,
          258/280 bottom, 580 right); floor z -352; wall y 3487 lit up to the ceiling z 2361 and to x 4623 on the
          right (1017: corner at x 385 px; 1063: top at 40 px); ceiling z 2361 lit for x 3386..4633;
  shot B: wall x 7470 lit for y -2150..1760, z -1328..482 (1108); upper floor z -396 up to x ~4700; lower floor
          z -1912 lit (seen from above 1121-1131, its corner with the dark wall x 4800 at 265 px in 1127)."""
import math
import numpy as np
from lib import vmfedit as E, tube
from lib.ride import Ride
from models import rust as RM

BLACK = 'corehub_intro/void_black'
ORIGIN_A = (-8350.0, 5050.0, 0.0)          # cell C2: x -9000..-2000, y 3200..9750
ORIGIN_B = (-15400.0, 6400.0, 1500.0)       # cell C1: x -16000..-9000, y 3200..9750 (shot B is built at 0.65 scale)
UNIT_B = 0.65
# texture scale (world units per texel): the rust texture holds 2 x 4 panels of 580 x 320 units in 512 x 512 texels
RUST_SU = RM.PANEL_W * RM.TEX_PANELS[0] / RM.TEX
RUST_SV = RM.PANEL_H * RM.TEX_PANELS[1] / RM.TEX
FLOOR_S = 640.0 / 256


def shell(v, lo, hi, mat=BLACK, t=32.0):
    """hollow box that seals a cell (inside faces `mat`)"""
    lo = np.asarray(lo, dtype=float); hi = np.asarray(hi, dtype=float)
    for ax in range(3):
        for side in (0, 1):
            a = lo.copy() - t; b = hi.copy() + t
            if side == 0: b[ax] = lo[ax]
            else: a[ax] = hi[ax]
            E.add_box(v, a, b, mat)


def tex_box(v, ent, lo, hi, mat, su=RUST_SU, sv=RUST_SV, off=(0.0, 0.0), rot=False):
    """axis-aligned brush with texture scale su x sv world units per texel on every side; rot: on the horizontal
    faces the texture's u runs along y (streaks along y)"""
    from srctools.vmf import UVAxis
    p = E.add_box(v, lo, hi, mat, ent=ent)
    for s in p.solid.sides:
        if rot and abs(s.normal().z) > 0.5:
            s.uaxis = UVAxis(0, 1, 0); s.vaxis = UVAxis(-1, 0, 0)
        s.uaxis.scale = su; s.vaxis.scale = sv; s.uaxis.offset = off[0]; s.vaxis.offset = off[1]
    return p


CELL_C2 = ((-9000.0, 3200.0, -3000.0), (-2000.0, 9750.0, 5000.0))
CELL_C1 = ((-16000.0, 3200.0, -3000.0), (-9000.0, 9750.0, 5000.0))


class Cell:
    """map placement of one shot: ride coordinates -> map (origin + unit scale); `bounds`: the cell's map box
    (the shell is clamped to it, so nothing reaches into the old map or the neighbour cells)"""
    def __init__(self, v, rd, origin, unit, bounds):
        self.v = v; self.rd = rd; self.o = np.asarray(origin, dtype=float); self.k = float(unit)
        self.bounds = (np.asarray(bounds[0], dtype=float) + 40, np.asarray(bounds[1], dtype=float) - 40)
        self.det = v.create_ent(classname='func_detail')
        self.lo = np.full(3, np.inf); self.hi = np.full(3, -np.inf)

    def m(self, p):
        return self.o + np.asarray(p, dtype=float) * self.k

    def box(self, lo, hi, mat, su=RUST_SU, sv=RUST_SV, off=(0.0, 0.0), grow=True, rot=False):
        a = self.m(np.minimum(lo, hi)); b = self.m(np.maximum(lo, hi))
        a = np.clip(a, self.bounds[0], self.bounds[1]); b = np.clip(b, self.bounds[0], self.bounds[1])
        if (b - a).min() < 1.0: return
        tex_box(self.v, self.det, a, b, mat, su * self.k, sv * self.k, off, rot)
        if grow: self.lo = np.minimum(self.lo, a); self.hi = np.maximum(self.hi, b)

    def slab(self, axis, coord, lo2, hi2, cam_side, mat, t=24.0, **kw):
        """a wall face at <axis> = coord (ride units) facing the camera side (cam_side +1: camera on the + side),
        lo2 / hi2: the extents on the other two axes (in xyz order, the slab axis ignored)"""
        i = 'xyz'.index(axis); a = np.array(lo2, dtype=float); b = np.array(hi2, dtype=float)
        a = np.insert(np.delete(a, i) if len(a) == 3 else a, i, 0.0); b = np.insert(np.delete(b, i) if len(b) == 3 else b, i, 0.0)
        if cam_side > 0: a[i] = coord - t; b[i] = coord
        else: a[i] = coord; b[i] = coord + t
        self.box(a, b, mat, **kw)

    def seal(self, margin=900.0):
        lo, hi = self.rd.bounds()
        lo = np.minimum(lo, self.lo) - margin * self.k; hi = np.maximum(hi, self.hi) + margin * self.k
        shell(self.v, np.maximum(lo, self.bounds[0]), np.minimum(hi, self.bounds[1]))


# ------------------------------------------------------------------------------------------------ path cleaning
FRAME_T = 1001.0 / 30000.0


def _bezier(A, a, B, b, n=80):
    """cubic Bezier from A (tangent a, a vector incl. handle length) to B (tangent b) -> points [n,3]"""
    u = np.linspace(0.0, 1.0, n)[:, None]
    P0, P1, P2, P3 = A, A + a, B - b, B
    return (1 - u) ** 3 * P0 + 3 * (1 - u) ** 2 * u * P1 + 3 * (1 - u) * u ** 2 * P2 + u ** 3 * P3


def _arclen(P):
    return np.r_[0.0, np.cumsum(np.linalg.norm(np.diff(P, axis=0), axis=1))]


def clean_ride(rd, end=None, flat_end=False, lead=None):
    """Replace the measured positions (rd.moments, rd.curve) by straight lines along the straights and cubic
    Beziers (fitted to the measured positions, tangent to the straights) in the bends; the camera keeps its measured
    orientation and its arclength profile. end: (end point, end tangent) for a path that ends in a bend (map coords);
    flat_end: the path ends on the last straight's line (the final bend is only begun).
    lead: {first frame of a bend: weight}: in that bend the path must not turn ahead of the camera (the film's view
    leads the path into a turn); a path tangent turned further than the camera's measured view costs weight * rad^2."""
    mo = rd.moments
    fr = np.array([m[1] + (0.0 if m[2] == 'E' else 0.4995) for m in mo]); P = np.array([m[3] for m in mo])
    secs = rd.sections; st = [d for d in secs if d['kind'] == 'straight']
    lines = []
    for d in st:
        ax = d['forward_vec']; sel = (fr >= d['first'] - 0.01) & (fr <= d['last'] + 0.6)
        c = P[sel].mean(axis=0); lines.append((c, ax, d))
    def proj(L, p): c, ax, _ = L; return c + ax * ((p - c) @ ax)
    newP = P.copy(); pieces = []          # dense curve pieces in order: list of arrays
    # assign every moment to a section
    for k, d in enumerate(secs):
        sel = np.where((fr >= d['first'] - 0.01) & (fr <= d['last'] + 0.6))[0]
        if not len(sel): continue
        if d['kind'] == 'straight':
            L = [l for l in lines if l[2] is d][0]
            for i in sel: newP[i] = proj(L, P[i])
            continue
        prev = [l for l in lines if l[2]['last'] < d['first']]; nxt = [l for l in lines if l[2]['first'] > d['last']]
        if not prev:                              # lead-in: on the first straight's line
            for i in sel: newP[i] = proj(nxt[0], P[i])
            continue
        L1 = prev[-1]
        if not nxt and (flat_end or end is None):
            for i in sel: newP[i] = proj(L1, P[i])
            continue
        i0 = sel[0] - 1; i1 = sel[-1] + 1
        A = proj(L1, P[i0])
        if nxt:
            L2 = nxt[0]; B = proj(L2, P[min(i1, len(P) - 1)]); dB = L2[1]; i1 = min(i1, len(P) - 1)
        else:
            B, dB = np.asarray(end[0], dtype=float), np.asarray(end[1], dtype=float) / np.linalg.norm(end[1]); i1 = len(P) - 1
        dA = L1[1]; meas = P[i0:i1 + 1]; best = None
        # corner of the two tangent lines: the handles stay on A..K and K..B (a tube bends monotonically)
        w0 = A - B; aa, bb, cc, dd_, ee = dA @ dA, dA @ dB, dB @ dB, dA @ w0, dB @ w0
        den = aa * cc - bb * bb
        if abs(den) < 1e-9: ha = hb = np.linalg.norm(B - A) / 2
        else:
            sA = (bb * ee - cc * dd_) / den; sB = (aa * ee - bb * dd_) / den
            ha = max(1.0, sA); hb = max(1.0, -sB)
        wl = (lead or {}).get(d['first'], 0.0)
        if wl:
            Fw = np.array([mo[i][4] for i in range(i0, i1 + 1)]); cam_turn = np.arccos(np.clip(Fw @ dA, -1, 1))
            fm = _arclen(meas) / max(_arclen(meas)[-1], 1e-9)
        for fa in np.linspace(0.05, 1.0, 24):
            for fb in np.linspace(0.05, 1.0, 24):
                C = _bezier(A, dA * fa * ha, B, dB * fb * hb, 120)
                dd = np.sqrt(((meas[:, None, :] - C[None, :, :]) ** 2).sum(-1)).min(axis=1)
                e = float((dd ** 2).mean())
                if wl:
                    sc_ = _arclen(C); q = np.interp(fm * sc_[-1], sc_, np.arange(len(C)))
                    Tc = np.gradient(C, axis=0); Tc /= np.linalg.norm(Tc, axis=1, keepdims=True)
                    Tq = Tc[np.clip(np.round(q).astype(int), 0, len(C) - 1)]
                    path_turn = np.arccos(np.clip(Tq @ dA, -1, 1))
                    if wl > 0: e += wl * rd.unit ** 2 * float((np.maximum(0.0, path_turn - cam_turn) ** 2).mean())
                    else: e += -wl * rd.unit ** 2 * float(((path_turn - cam_turn) ** 2).mean())     # < 0: follow the view
                if best is None or e < best[0]: best = (e, fa, fb, C)
        e, fa, fb, C = best
        # place the moments on the curve by their measured arclength fraction
        sm = _arclen(meas); sc = _arclen(C)
        for j, i in enumerate(range(i0, i1 + 1)):
            f = sm[j] / sm[-1]; q = np.interp(f * sc[-1], sc, np.arange(len(C)))
            a = int(min(len(C) - 2, q)); w = q - a; newP[i] = C[a] * (1 - w) + C[a + 1] * w
        print('clean_ride %s bend %d-%d: rms %.1f handles %.2f %.2f' % (rd.name, d['first'], d['last'], math.sqrt(e), fa, fb))
    # write back: moments, and a dense curve through the cleaned positions
    rd.moments = [(m[0], m[1], m[2], newP[i], m[4], m[5]) for i, m in enumerate(mo)]
    dense = [newP[0]]; dt = [fr[0]]
    for i in range(1, len(newP)):
        for w in (0.25, 0.5, 0.75, 1.0):
            dense.append(newP[i - 1] * (1 - w) + newP[i] * w); dt.append(fr[i - 1] * (1 - w) + fr[i] * w)
    dense = np.array(dense); dt = np.array(dt)
    keep = np.r_[True, np.linalg.norm(np.diff(dense, axis=0), axis=1) > 1e-6]
    rd.curve = dense[keep]; rd.t = dt[keep]
    rd.S = _arclen(rd.curve); rd.length = float(rd.S[-1])
    T = np.gradient(rd.curve, axis=0); rd.T = T / (np.linalg.norm(T, axis=1, keepdims=True) + 1e-12)
    for d in rd.sections: d['s0'] = rd.s_at(d['first']); d['s1'] = rd.s_at(d['last'])
    rd.rings = [dict(r, s=rd.s_at(r['frame']), pos=rd.pos(r['frame']), axis=rd.direction(r['frame'])) for r in rd.raw['rings']]
    return rd


# ------------------------------------------------------------------------------------------------ shot A
def hole_wall(c, axis, coord, lo2, hi2, cam_side, mat, centre2, h, **kw):
    """a slab with a square hole (half size h) around centre2 (the two other axes)"""
    (a0, b0), (a1, b1) = lo2, hi2; cu, cv = centre2
    for lo, hi in (((a0, b0), (cu - h, b1)), ((cu + h, b0), (a1, b1)), ((cu - h, b0), (cu + h, cv - h)), ((cu - h, cv + h), (cu + h, b1))):
        if hi[0] - lo[0] > 1 and hi[1] - lo[1] > 1: c.slab(axis, coord, lo, hi, cam_side, mat, **kw)


def prop(c, model, p, ang=(0, 0, 0), name=None):
    E.add_prop(c.v, 'models/corehub_intro/%s.mdl' % model, c.m(p), ang, name=name)


FLOOR_A = -352.0
X_WALL_A = 4623.0
Y_PORT_A = 980.0                 # dividing wall with the port the camera passes through (frames 1013-1016)
X_TUBE_A = 4253.5                # the +y run (measured straight)


def room_a(c):
    W, D, F = RM.WALL_MAT, RM.WALL_DIM, RM.FLOOR_MAT
    # big wall ahead of the first straight: lit panel rectangle (the rest of the wall is dark)
    c.slab('x', X_WALL_A, (-1570, FLOOR_A), (Y_PORT_A, 655), -1, W)
    c.slab('x', X_WALL_A + 17, (-1850, FLOOR_A), (Y_PORT_A + 30, 2361), -1, BLACK)
    # dividing wall y 980 (seen edge-on from the first straight, frontal in 1004-1013): lit near the corner, a port
    hole_wall(c, 'y', Y_PORT_A, (4100, FLOOR_A), (X_WALL_A, 655), -1, W, (X_TUBE_A, 0.0), 75.0)
    c.slab('y', Y_PORT_A, (3880, FLOOR_A), (4100, 655), -1, D)
    c.slab('y', Y_PORT_A, (3800, FLOOR_A), (3880, 655), -1, BLACK)
    c.slab('y', Y_PORT_A, (-650, FLOOR_A), (3800, 2361), -1, BLACK)
    c.slab('y', Y_PORT_A, (3800, 655), (X_WALL_A, 2361), -1, BLACK)
    # floor (dark tiles), both sides of the dividing wall
    c.slab('z', FLOOR_A, (-650, -1850), (X_WALL_A, 3487), +1, F, su=FLOOR_S, sv=FLOOR_S)
    # beyond the port: far wall y 3487 (frontal in 1011-1070) up to the ceiling, ending at the corner x 4623
    c.slab('y', 3487.0, (3300, FLOOR_A), (X_WALL_A, 2361), -1, W)
    c.slab('z', 2361.0, (3386, 1004), (4633, 2150), -1, D)                 # ceiling: lit above the climb (1044)
    c.slab('z', 2361.0, (3386, 2150), (4633, 3572), -1, RM.WALL_DARK)      # darker further on (1055-1062: top dark)
    c.slab('x', 3548.0, (1004, FLOOR_A), (3487, 2361), +1, D)              # left wall of the +y run
    # end of the shot: the camera turns right (+x) into a dark tube; a lit wall far ahead (1081)
    c.slab('x', 5200.0, (2650, 1500), (3400, 2300), -1, D)
    # round 3: 35.75-36.1 the film shows rust panels all round the tube mouth (frames 1071-1082), where at 35.5 it is
    # black right of the run (the same place seen from the run): the far wall y 3487 goes on past x 4623 to the corner
    # with the wall x 5200 as a model shown only from 35.7 s (ru_show; parked under the floor before)
    c.slab('x', 5200.0, (3400, 1300), (3487, 2500), -1, D)
    E.add_prop(c.v, 'models/corehub_intro/r11_rux_endwall.mdl', c.m(ENDWALL_PARK), (0, 0, 0), name='r11_rust_a_endwall')
    SHOW.append(('r11_rust_a_endwall', 35.70, 36.20, c.m(ENDWALL_AT), c.m(ENDWALL_PARK)))
    E.add_prop(c.v, 'models/corehub_intro/r11_rux_mouthwall.mdl', c.m(MOUTH_PARK), (0, 0, 0), name='r11_rust_a_mouthwall')
    SHOW.append(('r11_rust_a_mouthwall', 35.85, 36.20, c.m(MOUTH_AT), c.m(MOUTH_PARK)))
    # devices
    prop(c, 'r11_ru_port', (X_WALL_A, 0.0, 0.0), (0, 0, 0), 'r11_rust_a_port0')
    prop(c, 'r11_ru_support', (X_WALL_A - 90.0, 0.0, -62.0), (0, 0, 0), 'r11_rust_a_support0')
    prop(c, 'r11_ru_port_open', (X_TUBE_A, Y_PORT_A, 0.0), (0, 90, 0), 'r11_rust_a_port1')
    prop(c, 'r11_ru_glass_t', (X_TUBE_A, 820.0, 0.0), (0, 90, 0), 'r11_rust_a_glass')
    prop(c, 'r11_ru_elbow', (2283.0, -228.0, 30.0), (0, 0, 0), 'r11_rust_a_elbow')
    # ribbed dark tube the camera enters at the cut (1063-1082); round 3: moving its mouth to y 2910, z 1852 (where
    # the film's dark ring points at 36.0 s) and a collar on its face both scored lower at 36.0: kept at y 2950
    prop(c, 'r11_ru_endtube', (4540.0, MOUTH_AT[1], MOUTH_AT[2]), (0, 0, 0), 'r11_rust_a_endtube')


# collars the export did not list (the fade-in hides their edges) and two of its rings moved: ride x of the first
# straight from the light band's outer edge (radial profiles of the E moments 982, 984, 988, 990/991, 993/994, 995).
# (A series of rings of radius ~110 every 550 units also fits the kymograph, but scored worse in the preview.)
EXTRA_COLLARS_A = [258.0, 822.0, 1607.0, 3000.0]
MOVE_RINGS_A = {991.9: 2163.0, 995.6: 2711.0}
# rings that could be placed from their image radius instead of the export's passing frame (tried, all scored lower
# once the preview averaged t and t+1/60 like the film: ring 1042.6 at z 870, a ring at y 620 for 1010, ring 1073.3
# at y 2500); the export's positions are kept
# round 3: the collar at the start of the second +y run, seen at the bottom of the frame at 35.25 s (frame 1056: centre
# 22.6 deg below the view, radius 125 px -> 226 units along that ray: on the path at y 1952)
# (tried in round 3 and dropped: a collar at y 630 after the junction bend and the ring of 1025.0 at y 1363, from the
# light-band edges of the moments 1010-1020: edge +0.03 but ssim -0.12 over 33.5-34.25)
PLACED_RINGS_A = [((4253.5, 1952.0, 1863.0), (0.0, 1.0, 0.0))]
REPLACE_RINGS_A = {}
# junction rings one frame later than exported (998: ring radius ~136 px ahead -> x ~3565; 1003: radius ~136 px
# -> passed at ~1004.2): placed on the path at these frames
REFRAME_RINGS_A = {999.0: 1000.1, 1003.0: 1004.2}
END_TANGENT_A = (0.945, 0.328, 0.0)          # direction of the path at the cut (1082E -> 1082L)
PORT_A = 4538.0                              # the main tube ends at the port in the wall (x of the port's face)


ENDWALL_AT = (X_WALL_A, 3487.0, 1300.0)       # model r11_rux_endwall: x 0..577, face at y 0 (facing -y), z 0..1200
ENDWALL_PARK = (4000.0, 3000.0, -900.0)       # under the floor slab, inside the shell
MOUTH_AT = (4538.0, 2950.0, 1863.0)           # model r11_rux_mouthwall: the wall round the end tube's mouth (x 4540)
MOUTH_PARK = (3000.0, 3000.0, -900.0)
SHOW = []


def show_props(d):
    """director hook: props in SHOW sit at their place only between t0 and t1 (else parked); acts only in 32.6-38.95 s"""
    rows = ','.join('["%s",%.4f,%.4f,%.1f,%.1f,%.1f,%.1f,%.1f,%.1f]' % ((n, t0, t1) + tuple(p) + tuple(q)) for n, t0, t1, p, q in SHOW)
    d.append('ruShow <- [' + rows + '];\n' + '''function Ru_Show(t) {
    if(t<32.6||t>38.95) return;
    foreach(r in ruShow){local e=Entities.FindByName(null,r[0]);if(e==null)continue;
        if(t>=r[1]&&t<r[2])e.SetOrigin(Vector(r[3],r[4],r[5]));else e.SetOrigin(Vector(r[6],r[7],r[8]));}
}
''')
    d.hook('Ru_Show(t);')


def lead_in(cam, t_from):
    """camera samples extended back to t_from along the first straight (the film fades in on the same ride)"""
    (t0, p0, a0), (t1, p1, a1) = cam[0], cam[2]
    v = (np.asarray(p1) - np.asarray(p0)) / (t1 - t0); out = []; t = t0 - 1 / 60.0
    while t >= t_from - 1e-6:
        out.append((t, tuple(float(x) for x in np.asarray(p0) + v * (t - t0)), a0)); t -= 1 / 60.0
    return out[::-1] + list(cam)


def fades(d):
    """screen black for the fade-in of shot A and the fade-out of shot B, from the film's brightness (see report)"""
    d.append('''ruFadeIn <- [%s];
ruFadeOut <- [%s];
function Ru_Fade(t) {
    if(t>=FADE_IN_T0 && t<FADE_IN_T1) SetScreenBlack(Lerp1(ruFadeIn,t));
    if(t>=FADE_OUT_T0 && t<FADE_OUT_T1) SetScreenBlack(Lerp1(ruFadeOut,t));
}'''.replace('FADE_IN_T0', '%.4f' % FADE_IN[0][0]).replace('FADE_IN_T1', '%.4f' % FADE_IN[-1][0])
       .replace('FADE_OUT_T0', '%.4f' % FADE_OUT[0][0]).replace('FADE_OUT_T1', '%.4f' % FADE_OUT[-1][0])
       % (','.join('[%.4f,%.1f]' % r for r in FADE_IN), ','.join('[%.4f,%.1f]' % r for r in FADE_OUT)))
    d.hook('Ru_Fade(t);', late=True)


# round 3: the game (and now the preview) draws SetScreenBlack in gamma space: the round-2 alphas (fitted as
# 1 - film / unfaded in linear light, frames 979-985 and 1150-1166) converted to 255 * (1 - (1 - a/255) ^ (1/2.2))
# fade-in re-fitted on the gamma-space preview (film 979-986: 1.9 4.7 7.0 10.2 10.1 13.6 16.3 20.5; the unfaded
# preview 14-33 with the collar passes): 32.75 s needs ~0.35 of the unfaded 29 -> alpha ~165
FADE_IN = [(32.60, 255.0), (32.674, 225.0), (32.741, 168.0), (32.775, 150.0), (32.808, 110.0), (32.874, 30.0), (32.92, 0.0), (33.16, 0.0)]
# fade-out re-fitted on the gamma-space preview: alpha = 255 * (1 - film / unfaded preview) at 38.5 (film 23.2,
# unfaded 54.2 -> 146) and 38.75 (13.8 / 34.2 -> 152)
FADE_OUT = [(38.38, 0.0), (38.447, 60.0), (38.513, 146.0), (38.58, 148.0), (38.647, 150.0), (38.714, 151.0), (38.78, 156.0),
            (38.847, 180.0), (38.914, 215.0), (38.94, 255.0)]


def straight_rails(c, a, b, rho=34.0, width=1.8):
    """four rails between ride points a and b (axis-aligned piece), scaled into the cell"""
    a = c.m(a); b = c.m(b); d = (b - a) / np.linalg.norm(b - a)
    tube.add_straight_rails(c.v, None, rho=rho * c.k, width=width * c.k, ent=c.det, pieces=[(a, b, d)])


def collars(c, pts, prefix, model=None):
    """collar props at ride points with axis directions [(p, axis)]"""
    for k, (p, ax) in enumerate(pts):
        E.add_prop(c.v, model or tube.COLLAR_MDL, c.m(p), tube.axis_angles(ax), name='%s_collar%d' % (prefix, k))


# ------------------------------------------------------------------------------------------------ sample timing
# The quarter-second samples (game runs, score.py) compare the game at t (two 60 Hz moments t, t + 1/60) with the
# film frame n = round(t / FRAME_T), whose moments are n * FRAME_T and + 1/60: at x.25 / x.75 s the game is 0.4 frame
# AHEAD of the film frame it is compared with, at x.0 / x.5 s 0.1 frame behind. A collar passing at 150 units per
# frame then shows 60 units nearer than in the film. sample_shift() moves a collar along the path by the camera's
# travel over that offset at the samples where the collar is in view (weighted by its size there), so the samples
# show it as the film frames do; at most 0.4 frame of travel, invisible in motion.
SAMPLES = [32.75 + 0.25 * i for i in range(25)]
# Oct 12: the scorers now compare film frame n with the game / preview at the frame's own time n * FRAME_T
# (offline/preview.film_time; the Mac's fetch_run.py fetches the game frames the same way), so the offset above is
# gone and the shift is off.
SAMPLE_SHIFT = False


def _s_time(rd, t):
    """camera arclength at film time t (fractional frames: E moment of frame n at n)"""
    return rd.s_at(t / FRAME_T)


def sample_shift(rd, s_c, R=61.06, f=461.88):
    if not SAMPLE_SHIFT:
        return 0.0
    num = 0.0; den = 0.0
    t_lo = rd.raw['first'] * FRAME_T; t_hi = (rd.raw['last'] + 1) * FRAME_T
    for t in SAMPLES:
        n = int(round(t / FRAME_T)); tn = n * FRAME_T
        if not (t_lo <= t <= t_hi and t_lo <= tn <= t_hi): continue
        D = s_c - _s_time(rd, tn)
        if not (-150.0 < D < R * f / 15.0): continue          # in view, or just passed (the shift may bring it back)
        w = R * f / max(abs(D), 30.0)                          # near passes dominate
        num += w * (_s_time(rd, t) - _s_time(rd, tn)); den += w
    return num / den if den > 0 else 0.0


def shift_points(rd, pts, unit=1.0, origin=None):
    """[(ride point, axis)] -> the same moved along the path by sample_shift (ride coordinates of a Ride built with
    origin 0, unit 1: rd here is such a ride, cleaned as the scene's)"""
    out = []
    for p, ax in pts:
        p = np.asarray(p, dtype=float)
        i = int(np.argmin(np.linalg.norm(rd.curve - p, axis=1))); s = float(rd.S[i])
        ds = sample_shift(rd, s)
        q, tg = rd.at(s + ds)
        # keep the point's offset from the path (collars sit on it; this is for safety)
        out.append((q + (p - rd.curve[i]), tg if np.linalg.norm(np.cross(tg, ax)) > 1e-3 else np.asarray(ax, dtype=float)))
        print('  collar s %7.1f shift %+6.1f' % (s, ds))
    return out


def build_a(v, d):
    rd = Ride('rust_a', origin=ORIGIN_A)
    clean_ride(rd, end=(rd.moments[-1][3], np.array(END_TANGENT_A)))
    d.override_camera(lead_in(rd.camera(), 32.60), fov=60.0)
    c = Cell(v, rd, ORIGIN_A, 1.0, CELL_C2)
    room_a(c)
    tube.add_straight_rails(v, rd, ent=c.det)
    tube.add_bend_rails(v, rd, 'r11_rust_a')
    # junction: the main tube goes on along +x to the port (the camera's branch leaves it at frame ~998)
    straight_rails(c, (3200.0, 0, 0), (PORT_A, 0, 0))
    o = np.asarray(ORIGIN_A)
    pts = [(np.array([x, 0.0, 0.0]), np.array([1.0, 0, 0])) for x in EXTRA_COLLARS_A]
    for r in rd.rings:
        mv = [x for f, x in MOVE_RINGS_A.items() if abs(r['frame'] - f) < 0.2]
        rp = [q for f, q in REPLACE_RINGS_A.items() if abs(r['frame'] - f) < 0.2]
        rf = [q for f, q in REFRAME_RINGS_A.items() if abs(r['frame'] - f) < 0.2]
        if rf: pts.append((rd.pos(rf[0]) - o, rd.direction(rf[0])))
        elif mv: pts.append((np.array([mv[0], 0.0, 0.0]), np.array([1.0, 0, 0])))
        elif rp: pts.append((np.array(rp[0]), r['axis']))
        else: pts.append(((r['pos'] - o), r['axis']))
    pts += [(np.array(p), np.array(a)) for p, a in PLACED_RINGS_A]
    rr = Ride('rust_a'); clean_ride(rr, end=(rr.moments[-1][3], np.array(END_TANGENT_A)))
    pts = shift_points(rr, pts)
    collars(c, pts, 'r11_rust_a', model='models/corehub_intro/r11_ru_collar.mdl')
    c.seal()
    return rd


# ------------------------------------------------------------------------------------------------ shot B
def room_b(c):
    W, D, F = RM.WALL_MAT, RM.WALL_DIM, RM.FLOOR_MAT
    # wall ahead of the upper run: lit panel rectangle (frames 1086-1109: y 1619..1758 / -2117..-2121,
    # z 484..491 top; the upper floor's edge hides its lower part until ~1105). It goes down to the lower floor,
    # where the lower tube passes it through a port (1145-1155: port in the middle of a frontal wall)
    c.slab('x', 7470.0, (-2150, -396), (1720, 486), -1, W)
    hole_wall(c, 'x', 7470.0, (-2150, -1912), (1720, -396), -1, 'corehub_intro/r11_ru_wall_low', (0.0, -1519.0), 75.0)
    c.slab('x', 7490.0, (-3200, -1328), (2600, 2000), -1, BLACK)
    # second lit wall on the right (36.25: x 457-548 px, 36.75: 555-640 px -> x 5262, edge at y -1435)
    c.slab('x', 5262.0, (-2425, -613), (-1435, 363), -1, D)
    c.slab('z', -396.0, (-600, -3000), (4700, 2600), +1, F, su=FLOOR_S, sv=FLOOR_S)     # upper floor
    # lower floor: lit rust from the foot of the vertical tube (seen from above 1121-1131, streaks across the
    # view) to x 6900, dark tiles further on (1145: dark at the bottom of the frame)
    c.slab('z', -1912.0, (4700, -2600), (6900, 2600), +1, D, rot=True)
    c.slab('z', -1912.0, (6900, -2600), (9400, 2600), +1, F, su=FLOOR_S, sv=FLOOR_S)
    c.slab('x', 4800.0, (-2600, -1912), (2600, -396), +1, F, su=FLOOR_S, sv=FLOOR_S)    # dark wall behind the drop
    prop(c, 'r11_ru_port_small_s065', (7470.0, 0.0, -1519.0), (0, 0, 0), 'r11_rust_b_port1')
    prop(c, 'r11_ru_support_s065', (7380.0, 0.0, -1581.0), (0, 0, 0), 'r11_rust_b_support1')
    c.slab('x', 9300.0, (-2600, -1912), (2600, 500), -1, 'corehub_intro/r11_ru_wall_low')     # end wall of the lower run


PORT_B = 7470.0
# round 3: the second bend's fitted path turned ahead of the camera (horizontal at 1139 where the measured view still
# looks 16 deg down and the film's rails meet at the frame centre, 38.0 s): the path may not turn ahead of the view
LEAD_B = {1134: 2.0e5}                   # (1116: -1e5, a path following the view in the first bend, changed nothing)
# collars of shot B (ride coordinates of the cleaned path), round 3: from the film's light-band edges, s_c = s_cam +
# 61.06 * 461.88 / r over every E / L moment of a straight (clusters of 5-18 moments agreeing within 10-40 units):
#   upper run (1083-1115): x 94 (1083: r 292 px), 652, 1414, 2168, 2718, 3269, 4026, 4562
#   the drop (1124-1133):  z -779, -1301          lower run (1142-1152): x 5879, 6261, 6658
COLLARS_B = ([((x, 0.0, 0.0), (1.0, 0.0, 0.0)) for x in (94.0, 652.0, 1414.0, 2168.0, 2718.0, 3269.0, 4026.0, 4562.0)] +
             [((4976.9, 0.0, z), (0.0, 0.0, -1.0)) for z in (-779.0, -1301.0)] +
             [((x, 0.0, -1519.0), (1.0, 0.0, 0.0)) for x in (5879.0, 6261.0, 6658.0)])
DARK_RINGS_B = (1153.8,)                # dark ring in the film there (1154: dark ring around); 1120.5 dropped (37.25: rails only)


def build_b(v, d):
    rd = Ride('rust_b', origin=ORIGIN_B, unit=UNIT_B)
    clean_ride(rd, flat_end=True, lead=LEAD_B)
    d.override_camera(rd.camera(), fov=60.0)
    c = Cell(v, rd, ORIGIN_B, UNIT_B, CELL_C1)
    room_b(c)
    k = UNIT_B
    tube.add_straight_rails(v, rd, rho=34.0 * k, width=1.8 * k, ent=c.det)
    tube.add_bend_rails(v, rd, 'r11_rust_b', rho=34.0 * k, width=1.8 * k)
    straight_rails(c, (4500.0, 0, 0), (PORT_B, 0, 0))          # main tube on to the port of the far wall
    from models.tubekit import build_collar
    o = np.asarray(ORIGIN_B)
    rr = Ride('rust_b'); clean_ride(rr, flat_end=True, lead=LEAD_B)    # ride coordinates (origin 0, unit 1), as built
    pts = shift_points(rr, [(np.array(p), np.array(a)) for p, a in COLLARS_B]); dark = []
    for r in rd.rings:
        if any(abs(r['frame'] - f) < 0.3 for f in DARK_RINGS_B):
            dark.append(((r['pos'] - o) / k, r['axis']))
    collars(c, pts, 'r11_rust_b', model='models/corehub_intro/r11_ru_collar_s065.mdl')
    for kk, (p, ax) in enumerate(dark):          # clamps are built about model +X
        ax = np.asarray(ax, dtype=float); left = np.cross([0, 0, 1.0], ax) if abs(ax[2]) < 0.9 else np.array([0, 1.0, 0])
        E.add_prop(c.v, 'models/corehub_intro/r11_ru_clamp_s065.mdl', c.m(p), tube.frame_angles(ax, left), name='r11_rust_b_clamp%d' % kk)
    prop(c, 'r11_ru_port_s065', (PORT_B, 0.0, 0.0), (0, 0, 0), 'r11_rust_b_port0')
    prop(c, 'r11_ru_support_s065', (PORT_B - 90.0, 0.0, -62.0), (0, 0, 0), 'r11_rust_b_support0')
    c.seal()
    return rd


STATIC_PREFIXES = ('models/corehub_intro/r11_ru_', 'models/corehub_intro/r11_rust_')


def make_static(v):
    """every model of this scene is still: prop_static without a targetname (entity limit of the 2009 engine)"""
    n = 0
    for e in v.entities:
        if e['classname'] in ('prop_dynamic_override', 'prop_dynamic') and e['model', ''].lower().startswith(STATIC_PREFIXES):
            e['classname'] = 'prop_static'
            for k in ('targetname', 'solid', 'disableshadows'):
                if k in e: del e[k]
            e['solid'] = '0'; e['disableshadows'] = '1'
            n += 1
    return n


def apply(v, d):
    RM.brush_materials()
    del SHOW[:]
    build_a(v, d)
    build_b(v, d)
    fades(d)
    show_props(d)
    make_static(v)
