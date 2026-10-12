"""Turret / "16" part (film frames 1918-2217, 63.997-73.974 s), rebuilt in cell C10 (x 12000..16300, y 9850..16300).

Two shots (a hard cut between 2082L and 2083E; frame 2082 is already greyed by the haze of shot B):
  A 1918-2082  the camera descends in a tube past the bottom of the turret tower (dark 12-sided flange, tube stubs,
               the grey front of the upper floor slab), collar 1 slides toward it, the camera rides on to a small
               collar (ring 2) out of which a turret is lifted on wires; the camera follows the turret up through a
               floor slab (2015-2017) and on up past grey floor slabs while the turret's laser sight sweeps.
  B 2083-2217  under a grey haze (2083-2141) the camera rises with a turret whose side panels open, in front of a
               rust wall; a second set-up from 2142 (haze off): an iris on the wall moving down with a robot arm in
               it, a scanner head passing the camera, the "16" sign and a small tube of collars, a floor slab
               passing the camera (2165-2181), then a fast rise along the tube.
Cameras: my own COLMAP mappings of the shared tower database (out/tu/sfm: s1a 1918-1966, s1c 1950-1990, s1d
1984-2030, s1b 1960-2082 (frames >= 2025 used), s2 2083-2217), aligned to the room axes (walls vertical, line
families), joined through common frames, scaled by objects of known size (out/tu/tools/build_cam_a.py, build_cam_b.py,
data/tu_a_ride.json, data/tu_b_ride.json). Shot A uses two rooms (a1 until 2016, a5 from 2017: s1b and s1d do not
agree after the slab pass). Moving parts (collar 1, the turrets, the iris, the scanner head, slabs) are keyed from the
film's images with the measured cameras (out/tu/tools/props_a.py, eye.py: the red eye; the iris' cyan lights)."""
import math, json, os
import numpy as np
from lib import vmfedit as E, tube
from models import turret as TM

CELL = ((12000.0, 9850.0, -3000.0), (16300.0, 16300.0, 5000.0))
FRAME_T = 1001.0 / 30000.0
T0 = 1918 * FRAME_T                          # earlier moment of the first frame
T1 = 2217 * FRAME_T + 1001.0 / 60000.0       # later moment of the last frame
HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RUST_S = TM.PANEL_W * TM.TEX_PANELS[0] / TM.TEX       # world units per texel of the rust texture


def shell(v, lo, hi, mat=TM.BLACK, t=32.0):
    """hollow box that seals a region (inside faces `mat`)"""
    lo = np.asarray(lo, dtype=float); hi = np.asarray(hi, dtype=float)
    for ax in range(3):
        for side in (0, 1):
            a = lo.copy() - t; b = hi.copy() + t
            if side == 0: b[ax] = lo[ax]
            else: a[ax] = hi[ax]
            E.add_box(v, a, b, mat)


class Room:
    """placement of one shot's geometry: room coordinates (world units, axes = map axes) + origin -> map; boxes are
    clamped to the cell"""
    def __init__(self, v, origin, name, tex=RUST_S):
        self.v = v; self.o = np.asarray(origin, dtype=float); self.name = name; self.tex = tex
        self.det = v.create_ent(classname='func_detail')
        self.bounds = (np.asarray(CELL[0]) + 40, np.asarray(CELL[1]) - 40)
        self.lo = np.full(3, np.inf); self.hi = np.full(3, -np.inf); self.nprop = 0

    def m(self, p):
        return self.o + np.asarray(p, dtype=float)

    def box(self, lo, hi, mat, su=None, sv=None, off=(0.0, 0.0), grow=True):
        su = self.tex if su is None else su; sv = self.tex if sv is None else sv
        a = self.m(np.minimum(lo, hi)); b = self.m(np.maximum(lo, hi))
        a = np.clip(a, *self.bounds); b = np.clip(b, *self.bounds)
        if (b - a).min() < 0.5: return
        p = E.add_box(self.v, a, b, mat, ent=self.det)
        for s in p.solid.sides:
            s.uaxis.scale = su; s.vaxis.scale = sv; s.uaxis.offset = off[0]; s.vaxis.offset = off[1]
        if grow: self.lo = np.minimum(self.lo, a); self.hi = np.maximum(self.hi, b)
        return p

    def slab(self, axis, coord, lo2, hi2, cam_side, mat, t=16.0, **kw):
        """a face at <axis> = coord facing the camera side (cam_side +1: camera on the + side); lo2 / hi2: extents on the
        two other axes (xyz order)"""
        i = 'xyz'.index(axis); a = np.insert(np.array(lo2, dtype=float), i, 0.0); b = np.insert(np.array(hi2, dtype=float), i, 0.0)
        if cam_side > 0: a[i] = coord - t; b[i] = coord
        else: a[i] = coord; b[i] = coord + t
        return self.box(a, b, mat, **kw)

    def prop(self, model, p, ang=(0, 0, 0), name=None, **kv):
        self.nprop += 1
        mdl = model if model.startswith('models/') else 'models/corehub_intro/%s.mdl' % model
        return E.add_prop(self.v, mdl, self.m(p), ang, name=name or 'r11_tu_%s_%d' % (self.name, self.nprop), **kv)

    def static(self, model, p, ang=(0, 0, 0)):
        """a model that never moves: prop_static, no name (entity limit)"""
        mdl = model if model.startswith('models/') else 'models/corehub_intro/%s.mdl' % model
        return E.add_prop(self.v, mdl, self.m(p), ang, cls='prop_static')

    def seal(self, lo, hi):
        lo = np.maximum(self.m(lo), self.bounds[0]); hi = np.minimum(self.m(hi), self.bounds[1])
        shell(self.v, lo, hi)


def load_cam(name):
    """moments [t, n, mo, x, y, z, fx, fy, fz, ux, uy, uz] (room coordinates) of data/<name>_ride.json"""
    return json.load(open(os.path.join(HERE, 'data', name + '_ride.json')))


def qangle(f, u):
    from lib.ride import qangle as q
    return q(f, u)


def cam_samples(J, origin):
    o = np.asarray(origin, dtype=float); out = []
    for m in J['moments']:
        out.append((m[0], tuple(float(x) for x in o + np.array(m[3:6])), qangle(m[6:9], m[9:12])))
    return sharp_cuts(out)


def sharp_cuts(cam, jump=40.0, lead=0.0045):
    """where the camera jumps (a cut, or the switch between two rooms), hold the old pose until just before the new
    one, so that no 60 Hz tick interpolates across the jump; the first sample is also repeated `lead` s earlier (the
    sim's tick before the film's first moment then already shows the shot)"""
    out = [(cam[0][0] - lead, cam[0][1], cam[0][2])]
    for a, b in zip(cam, cam[1:]):
        out.append(a)
        if np.linalg.norm(np.array(b[1]) - np.array(a[1])) > jump:
            out.append((b[0] - 0.0002, a[1], a[2]))
    out.append(cam[-1])
    return out


HIDE = (14150.0, 16150.0, -2900.0)          # parking place for hidden props (inside the cell, below everything)


def squirrel_tracks(tracks, fades):
    """Squirrel: keyed props (linear between keys, angles when given, parked outside [on, off]) and the screen fades
    of the range (black alpha table; grey haze alpha table for r10_red_fade) -> code for Tu_Update(t)"""
    rows = []
    for tr in tracks:
        ks = []
        for t, p, a in tr['keys']:
            aa = a if a is not None else (0, 0, 0)
            ks.append('[%.4f,Vector(%.2f,%.2f,%.2f),Vector(%.3f,%.3f,%.3f),%d]' % (t, p[0], p[1], p[2], aa[0], aa[1], aa[2], 0 if a is None else 1))
        rows.append('{name="%s",on=%.4f,off=%.4f,k=[%s]}' % (tr['name'], tr.get('on', -1.0), tr.get('off', 1e6), ','.join(ks)))
    black = ','.join('[%.4f,%.1f]' % r for r in fades['black']); grey = ','.join('[%.4f,%.1f]' % r for r in fades['grey'])
    return ('tuTracks <- [\n' + ',\n'.join(rows) + '];\ntuBlack <- [%s];\ntuGrey <- [%s];\n' % (black, grey) + TU_CODE
            .replace('T_LO', '%.4f' % (T0 - 0.002)).replace('T_HI', '%.4f' % (T1 + 0.008))
            .replace('HIDE', 'Vector(%.1f,%.1f,%.1f)' % HIDE))


TU_CODE = '''function Tu_Update(t) {
    if(t<T_LO||t>T_HI)return;
    foreach(tr in tuTracks){
        local e=Entities.FindByName(null,tr.name); if(e==null)continue;
        if(t<tr.on||t>tr.off){e.SetOrigin(HIDE);continue;}
        local k=tr.k; local n=k.len(); local a=k[0]; local b=k[0]; local f=0.0;
        if(t>=k[n-1][0]){a=k[n-1];b=k[n-1];}
        else if(t>k[0][0]){for(local i=0;i<n-1;i++)if(t>=k[i][0]&&t<=k[i+1][0]){a=k[i];b=k[i+1];f=(t-a[0])/(b[0]-a[0]);break;}}
        e.SetOrigin(a[1]+(b[1]-a[1])*f);
        if(a[3]==1){local g=a[2]+(b[2]-a[2])*f;e.__KeyValueFromString("angles",g.x+" "+g.y+" "+g.z);}
    }
    SetScreenBlack(Lerp1(tuBlack,t));
    local ga=Lerp1(tuGrey,t).tointeger();
    if(ga!=r10RedAlpha){local fe=Entities.FindByName(null,"r10_red_fade");if(fe!=null){fe.__KeyValueFromString("renderamt",""+ga);EntFire("r10_red_fade","Fade","",0);r10RedAlpha=ga;}}
}
'''


ORIGIN_A1 = (12900.0, 11000.0, 3600.0)    # shot A, room a1 (s1a frame: origin = camera of frame 1918)
ORIGIN_A5 = (14500.0, 11000.0, 1200.0)    # shot A, room a5 (s1b frame: origin = camera of frame 2026)
A1_LIT_Y = 28.0                            # a1: the wall is lit right of this (y < 28), dark left of it
A_WALL_X = 243.0                           # a1: the rust wall behind the tower (s1a cloud, planes x 238-247)
TOWER = dict(x=float(os.environ.get('TU_TX', 151.0)), y=-5.0, z=-50.0)     # a1: tower axis and flange top (flange r 92 spans the film's 1925-1940 width; wall constraint)
WALL_BAND = [float(x) for x in os.environ.get('TU_WBAND', 'off').split(',')] if os.environ.get('TU_WBAND', 'off') != 'off' else None      # (a stripe at 228,-110,-62 scored lower)
BAND_DROP = float(os.environ.get('TU_BDROP', -12.5))
TOWER_Z = [(1916, -37.0 + float(os.environ.get('TU_TZ', 8))), (1933, -50.0 + float(os.environ.get('TU_TZ', 8))), (1960, -62.0 + float(os.environ.get('TU_TZ', 8)))]
# a1: light grey band behind the tubes. Its left-edge rows in 1929-1955 (290-361 ... 10-91) fit a static stripe on the
# wall: front face x 240, z -146.8 .. -111.4 (drift -0.01 per frame; at x 160 it would have to sink 1.6 per frame)
BAND = dict(x=float(os.environ.get('TU_BANDX', 240.0)), z0=float(os.environ.get('TU_BAND0', -146.8)))
BAND['z1'] = BAND['z0'] + float(os.environ.get('TU_BANDH', 35.4))
A5_WALL_X = 410.0                          # a5: rust wall (s1b cloud, scale 21)
A5_SLAB = dict(x=258.0, z0=-5.0, z1=94.0)  # a5: grey floor slab front face (band edges 2024-2080)
LIFT = (195.0, float(os.environ.get('TU_LIFTY', -26.5)), float(os.environ.get('TU_LIFTO', 23.5)))                # a1: axis (x, y) and rail offset of the vertical lift tube
RING2 = (180.0, -4.0, -255.0)
USE_WEDGE = os.environ.get('TU_WEDGE', '0') == '1'       # tried: the score drops a little with it
WEDGE = (13.0, 3.0, 110.0)                 # a1: top of the near dark rail relative to the camera (the film's central wedge)             # a1: the small collar the turret is lifted out of (1980-1996)
BEAM_DIR = [(2021, 1.0, 0.35), (2028, 1.0, 0.55), (2032, 0.6, 1.0), (2036, 0.3, 1.0), (2040, -0.4, 1.0), (2046, -0.75, 1.0),
            (2050, -0.3, 1.0), (2054, 1.0, 0.15), (2058, 1.0, -0.05), (2066, 1.0, -0.15), (2074, 1.0, -0.18), (2082, 1.0, -0.2)]
TURRET2 = [(1994, (178.0, -20.0, -256.0)), (2001, (179.0, -27.0, -250.0)), (2008, (182.0, -25.0, -234.0)), (2017, (184.0, -24.0, -214.0))]
TURRET_MDL = 'r11_tu_turret_w'             # own unlit turret (models/turret.py): +Z up, eye toward -X, origin = the eye
TURRET_ANG = (0.0, 0.0, 0.0)
EYE_OFF = np.array([0.0, 0.0, 0.0])        # eye relative to the prop origin


def cam_tube(r, J, org, tracks, name='r11_tu_a_camtube', rho=34.0, width=2.6, f0=1918, f1=1975, x_end=232.0, off=1982):
    """the tube the camera rides down (film 1918-1975: its near rails are the big dark wedges converging toward
    collar 1): four rails swept along the smoothed camera path, then on along +x to the collar's start"""
    from lib.gen import save
    from models.tubekit import rail_sweep, materials
    materials()
    P = np.array([m[3:6] for m in J['moments'] if f0 <= m[1] <= f1 and m[2] == 'E'])
    k = 7; Ps = np.array([P[max(0, i - k):i + k + 1].mean(axis=0) for i in range(len(P))])
    Ps = np.vstack([Ps[:1] + [0, 0, 120.0], Ps])
    last = Ps[-1]; ext = [last + np.array([dx, 0, 0]) for dx in np.arange(8.0, x_end - last[0], 8.0)]
    Ps = np.vstack([Ps] + ([np.array(ext)] if ext else []))
    T = np.gradient(Ps, axis=0); T /= np.linalg.norm(T, axis=1, keepdims=True)
    Wv = np.tile([0, 1.0, 0], (len(Ps), 1)); U = np.cross(T, Wv); U /= np.linalg.norm(U, axis=1, keepdims=True); Wv = np.cross(U, T)
    org0 = Ps[0].copy()
    save(rail_sweep(Ps - org0, U, Wv, rho, width), name)
    r.prop(name, org0, (0, 0, 0), name=name)
    # the camera leaves this tube upward after ~1990 (the film shows no rails below it then)
    tracks.append(dict(name=name, keys=[(T0 - 0.1, r.m(org0), None)], on=T0 - 0.1, off=off * FRAME_T))


def shot_a(v, d, tracks):
    J = load_cam('tu_a')
    org = {'a1': np.asarray(ORIGIN_A1), 'a5': np.asarray(ORIGIN_A5)}
    cam = [(m[0], tuple(float(x) for x in org[m[12]] + np.array(m[3:6])), qangle(m[6:9], m[9:12])) for m in J['moments']]
    d.override_camera(sharp_cuts(cam, lead=0.002), fov=60.0)
    # ---------------- room a1: tower base, grey band, wall, the moving tube end
    r = Room(v, ORIGIN_A1, 'a1', tex=0.35)
    cam_tube(r, J, org, tracks)
    r.slab('x', A_WALL_X, (-700, -1500), (A1_LIT_Y, 500), -1, TM.WALL)             # lit right part (1986: boundary 200 px)
    r.slab('x', A_WALL_X, (A1_LIT_Y, -1500), (700, 500), -1, TM.WALL_A1)           # dark left part (1960 / 1990: p50 31-33)
    r.prop('r11_tu_tower', (TOWER['x'], TOWER['y'], TOWER['z']), (0, 0, 0), name='r11_tu_a_tower')
    # the flange sits lower in the film's later frames than the measured descent puts it: keyed height (1918 / 1933)
    tracks.append(dict(name='r11_tu_a_tower', keys=[(n * FRAME_T, org['a1'] + np.array([TOWER['x'], TOWER['y'], z]), None) for n, z in TOWER_Z],
                       on=T0 - 0.1, off=1964 * FRAME_T))         # below the tower from ~1964 the film shows none of its tubes
    # floor slab of the upper level (front face = the grey band 1934-1950); seen again from below as the camera rises
    # through it (2015-2016) about 12 units lower than the descent puts it: a model, keyed
    r.prop('r11_tu_bandslab', (BAND['x'], 0.0, BAND['z0']), (0, 0, 0), name='r11_tu_a_bandslab')
    tracks.append(dict(name='r11_tu_a_bandslab', keys=[(1962 * FRAME_T, org['a1'] + np.array([BAND['x'], 0.0, BAND['z0']]), None),
                                                        (1996 * FRAME_T, org['a1'] + np.array([BAND['x'], 0.0, BAND['z0'] + BAND_DROP]), None)],
                       on=(T0 - 0.1) if not WALL_BAND else 1990 * FRAME_T))
    if WALL_BAND:       # the grey band of 1934-1950 moves across the picture like something near the wall: a grey stripe there
        r.box((WALL_BAND[0], -700, WALL_BAND[1]), (A_WALL_X, 700, WALL_BAND[2]), TM.GREY)
        r.box((WALL_BAND[0] + 3.0, -700, WALL_BAND[1] - 14.0), (A_WALL_X, 700, WALL_BAND[1]), TM.GREY_DARK)
    if os.environ.get('TU_STRIP', '0') == '1':
        r.slab('x', BAND['x'], (-700, BAND['z0'] - 12.0), (700, BAND['z0']), -1, TM.GREY_DARK, t=6.0)  # dark strip under it (1934-1950)
    if os.environ.get('TU_BEAM', '0') == '1':      # (tried, scores drop) the dark beam above the lifted turret (film 2008: y ~64 px; 2016: slab bottom)
        r.box((BAND['x'] - 2.0, -700, -163.0), (BAND['x'] + 40.0, 700, -155.0), TM.GREY_DARK)
    r.slab('z', -300.0, (-200, -700), (A_WALL_X, 700), +1, TM.FLOOR)            # floor (1980-1992: dark floor)
    P = J['props']
    ring_keys = [(t, org['a1'] + np.array(p), (0.0, 0.0, 0.0)) for t, p in P['ring']]
    if os.environ.get('TU_RINGX', '0') == '1':      # (scored lower: held is better) past the last fit (65.94) the ring keeps coming: at 66.0 its inner edge
        lp = np.array(P['ring'][-1][1])               # frames the picture (d ~ 88), by 66.1 it has passed the camera
        rx = [float(v) for v in os.environ.get('TU_RINGXS', '144,130,110').split(',')]
        ring_keys += [(tt, org['a1'] + np.array([xx, lp[1], lp[2]]), (0.0, 0.0, 0.0)) for tt, xx in zip((66.0, 66.1, 66.2), rx)]
    tracks.append(dict(name='r11_tu_a_ringtube', keys=ring_keys, on=T0 - 0.01, off=2000 * FRAME_T))
    r.prop('r11_tu_ringtube', P['ring'][0][1], (0, 0, 0), name='r11_tu_a_ringtube')
    r.static('r11_tu_ring2', RING2)
    # the near dark rail in front of the descending camera keeps its place in the picture (1918-1962): it moves with it
    if USE_WEDGE:
        wk = [(m[0], org['a1'] + np.array(m[3:6]) + np.array(WEDGE), None) for m in J['moments'] if m[2] == 'E' and m[1] % 3 == 1 and m[1] <= 1964]
        tracks.append(dict(name='r11_tu_a_wedge', keys=wk, on=T0 - 0.01, off=1962 * FRAME_T))
        r.prop('r11_tu_wedge', np.array(J['moments'][0][3:6]) + np.array(WEDGE), (0, 0, 0), name='r11_tu_a_wedge')
    # the vertical tube the turret is lifted in (film 1996-2016: two thick dark rails left and right of the turret)
    for sy in (-1, 1):
        for sx in (-1,):
            cx, cy = LIFT[0] + sx * LIFT[2], LIFT[1] + sy * LIFT[2]
            r.box((cx - 3.5, cy - 3.5, -262.0), (cx + 3.5, cy + 3.5, -40.0), TM.BLACK)
    r.seal((-600, -800, -1700), (800, 800, 700))
    # ---------------- room a5: wall, slab, the rising turret
    r5 = Room(v, ORIGIN_A5, 'a5', tex=0.35)
    r5.slab('x', A5_WALL_X, (-900, -800), (900, 1200), -1, TM.WALL)
    r5.box((A5_SLAB['x'], -900, A5_SLAB['z0']), (A5_WALL_X, 900, A5_SLAB['z1']), TM.GREY)
    r5.slab('z', A5_SLAB['z1'], (A5_SLAB['x'], -900), (A5_WALL_X, 900), +1, TM.GREY_DARK, t=2.0)
    # the platform the turret is lifted out of (film 2018-2024: grey front, dark top edge at ~292 px in 2023)
    r5.box((150.0, -900, -80.0), (A5_SLAB['x'], 900, -45.0), TM.GREY_MID)
    r5.slab('z', -45.0, (150.0, -900), (A5_SLAB['x'], 900), +1, TM.GREY_DARK, t=2.0)
    # before 1998 the turret sits in ring 2 (film 1990-1997: its head in the collar), then it is lifted
    tk = [(1986 * FRAME_T, org['a1'] + np.array(RING2) + [26.0, 0.0, 2.0] - EYE_OFF, TURRET_ANG, 'a1'),
          (1993 * FRAME_T, org['a1'] + np.array(RING2) + [14.0, -3.0, 8.0] - EYE_OFF, TURRET_ANG, 'a1')]
    for t, rm, p in P['turret']:
        if tk and rm == 'a5' and tk[-1][3] == 'a1':
            tk.append((2016.95 * FRAME_T, tk[-1][1], TURRET_ANG, 'a1')); tk.append((2016.96 * FRAME_T, org[rm] + np.array(p) - EYE_OFF, TURRET_ANG, rm))
        tk.append((t, org[rm] + np.array(p) - EYE_OFF, TURRET_ANG, rm))
    tk = [k[:3] for k in tk]
    tracks.append(dict(name='r11_tu_a_turret', keys=tk, on=1985 * FRAME_T, off=2083 * FRAME_T))
    r5.prop(TURRET_MDL, np.array(P['turret'][0][2]) - EYE_OFF, TURRET_ANG, name='r11_tu_a_turret')
    # the next turret, below the lifted one, its back to the camera (film 1996-2016: white dome low in the frame)
    k2 = [(n * FRAME_T, org['a1'] + np.array(p), (0.0, 180.0, 0.0)) for n, p in TURRET2]
    tracks.append(dict(name='r11_tu_a_turret2', keys=k2, on=1994 * FRAME_T, off=2016.9 * FRAME_T))
    r.prop('r11_tu_turret', TURRET2[0][1], (0.0, 180.0, 0.0), name='r11_tu_a_turret2')
    # the laser sight: a thin beam from the eye, its image direction read from the film (2024-2080)
    bk = []
    for t, pos, ang in tk:
        n = t / FRAME_T
        if n < 2021: continue
        dx, dy = np.interp(n, [k[0] for k in BEAM_DIR], [k[1] for k in BEAM_DIR]), np.interp(n, [k[0] for k in BEAM_DIR], [k[2] for k in BEAM_DIR])
        dv = np.array([0.35, -dx, -dy]); dv /= np.linalg.norm(dv)
        bk.append((t, pos + EYE_OFF + dv * 1.5, (-math.degrees(math.asin(dv[2])), math.degrees(math.atan2(dv[1], dv[0])), 0.0)))
    tracks.append(dict(name='r11_tu_a_beam', keys=bk, on=bk[0][0], off=2082.5 * FRAME_T))
    r5.prop('r11_tu_beam', np.array(P['turret'][0][2]), (0, 0, 0), name='r11_tu_a_beam')
    r5.seal((-700, -1000, -900), (A5_WALL_X + 200, 1000, 1400))


ORIGIN_B = (14600.0, 14600.0, 1500.0)     # shot B room (s2 frame: origin = camera of frame 2083E)
B_WALL_X = 150.0                           # the rust wall (s2 cloud, scale 13.8)
B_WALL_END = -150.0                        # the wall ends here on the right (black beyond: 2171, 2188)
B_IRIS = (112.0, -62.0, 76.0)              # iris centre (moves down, B_IRIS_KEYS)
B_IRIS_R = 59.0                            # petal radius (196 px at 139 units)
B_SIGN = (148.5, -101.6, 97.0)             # the "16" sign's centre (2176-2200: consistent to 0.1)
B_EYE = {2083: (90.6, -3.6, 11.3), 2086: (90.7, -4.2, 14.0), 2089: (90.8, -5.7, 15.7), 2092: (90.7, -4.4, 20.6), 2095: (90.8, -4.9, 22.0), 2098: (90.8, -5.5, 22.4),
         2101: (90.9, -6.7, 22.0), 2104: (90.9, -6.6, 23.4), 2107: (91.1, -8.7, 26.4), 2110: (91.1, -8.9, 28.3),
         2113: (91.3, -10.7, 30.5), 2116: (91.5, -12.4, 33.1), 2119: (91.6, -12.2, 36.0), 2122: (91.9, -14.4, 42.5),
         2128: (92.3, -17.3, 53.4), 2131: (92.4, -17.2, 57.7), 2134: (92.7, -19.6, 62.1), 2137: (93.1, -22.5, 67.0)}
# the iris moves down (cyan lights 2138-2148: -6.4 units per frame on the wall plane); it hangs in front of the small
# tube (the film's petals hide the tube in 2143-2150), so it is placed at x 112 (the wall-plane track scaled to there)
B_IRIS_KEYS = [(2120, -58.0, 233.0), (2138, -59.0, 118.5), (2141.95, -59.0, 96.0), (2142, -57.9, 90.5), (2145, -62.3, 74.8), (2148, -62.6, 61.7), (2160, -69.8, 3.9), (2217, -70.3, -209.4)]
T_CUT_B = 2142 * FRAME_T
B_HEAD = [(2150, (96.0, -48.0, 150.0)), (2156, (98.0, -50.0, 128.0)), (2160, (100.0, -58.0, 114.0)), (2163, (101.0, -57.0, 104.0)),
          (2166, (102.0, -56.0, 90.0)), (2172, (104.0, -55.0, 62.0))]
# film 2161/2163/2165: the head's white cylinder (r 13.6) is 156/187/244 px wide, top edge at rows 4/50/141: it comes
# toward the camera while it goes down (cylinder top centre (91.5,-63.6,106.9), (78.9,-63.5,93.7), (63.9,-67.3,77.6))
# (z of 2161/2163 then lowered by 6: the silhouette top is the cylinder's near rim; checked: rows 57/56 at 2163)
B_HEAD2 = [(2150, (100.0, -58.0, 168.0)), (2155, (100.0, -62.0, 150.0)), (2161, (91.5, -63.6, 100.9)), (2163, (78.9, -63.5, 87.7)),
           (2165, (63.9, -67.3, 78.6)), (2169, (36.3, -70.0, 49.4))]   # (2165 at 74.6 / 82.6 scored lower)


def shot_b(v, d, tracks):
    J = load_cam('tu_b')
    o = np.asarray(ORIGIN_B)
    d.override_camera(cam_samples(J, ORIGIN_B), fov=60.0)
    r = Room(v, ORIGIN_B, 'b', tex=0.2)
    r.slab('x', B_WALL_X, (B_WALL_END, -300), (500, 700), -1, TM.WALL_B)
    r.slab('x', B_WALL_X + 400, (-900, -500), (B_WALL_END, 900), -1, TM.BLACK)
    r.slab('z', -41.0, (-200, -400), (B_WALL_X, 300), +1, TM.FLOOR)                 # floor (2084-2100: dark strip at the bottom)
    # sign and the small tube below / above it
    r.static('r11_tu_sign16', B_SIGN)
    r.static('r11_tu_smalltube', (128.0, -100.0, float(os.environ.get('TU_STZ', 67.0))), tuple(float(v) for v in os.environ.get('TU_STA', '0,0,0').split(',')))
    r.static('r11_tu_htube', (100.0, -84.0, 278.0))           # the end: rings at x 100-102, z 277-280 (2214/2215 fits)
    if os.environ.get('TU_HT2', '118,-84,246') != 'off':        # a second camera-facing tube end lower down (2211: ring r 105 px at row 90)
        r.static('r11_tu_htube', tuple(float(v) for v in os.environ.get('TU_HT2', '118,-84,246').split(',')))
    # the scanner head descends past the camera (2156-2168: cylinder top 2160 y 5 -> 2163 y 60, x ~215 px, ~70 away)
    if os.environ.get('TU_HEAD2', '1') == '1':
        hk = [(n * FRAME_T + 1 / 120.0, o + np.array(p), None) for n, p in B_HEAD2]
        tracks.append(dict(name='r11_tu_b_head', keys=hk, on=2152 * FRAME_T, off=2170 * FRAME_T))
    else:
        hk = [(n * FRAME_T, o + np.array(p), None) for n, p in B_HEAD]
        tracks.append(dict(name='r11_tu_b_head', keys=hk, on=2152 * FRAME_T, off=2172 * FRAME_T))
    r.prop('r11_tu_scanhead', B_HEAD[0][1], (0, 0, 0), name='r11_tu_b_head')
    # the turret it holds, hanging head-down left of it (2156-2166)
    if os.environ.get('TU_HELD', '1') == '1':      # grey, left of and below the head (with the measured head track it scores higher)
        ho = np.array([float(v) for v in os.environ.get('TU_HELDO', '-4,27,-43').split(',')])   # film 2159/2161: egg left of and below the head
        tk2 = [(t, p + ho, None) for t, p, a in hk]
        tracks.append(dict(name='r11_tu_b_heldturret', keys=tk2, on=2153 * FRAME_T, off=2166 * FRAME_T))
        r.prop('r11_tu_turret_inv', np.array(B_HEAD[0][1]) + ho, (0, 0, 0), name='r11_tu_b_heldturret')
    # the white arm reaching into the iris (2148-2158), moving with the iris
    ao = [float(v) for v in os.environ.get('TU_ARMO', '-19,-11,79').split(',')]
    ak = [(n * FRAME_T, o + np.array([B_IRIS[0] + ao[0], y + ao[1], z + ao[2]]), None) for n, y, z in B_IRIS_KEYS]
    tracks.append(dict(name='r11_tu_b_arm', keys=ak, on=2142 * FRAME_T, off=2160 * FRAME_T))
    r.prop('r11_tu_arm', (B_IRIS[0] - 25.0, B_IRIS[1] - 15.0, 180.0), (0, 0, 0), name='r11_tu_b_arm')
    # a grey panel passes the camera downward (2166-2182: its lower edge top -> bottom of the frame, then its top edge):
    # a vertical plate at x 60, lower edge z 67.6 at frame 2171, -3.96 per frame (fit of both edges, rms 0.6)
    if os.environ.get('TU_VPLATE', '1') == '1':
        zl = lambda n: 67.6 - 3.96 * (n - 2171)
        r.prop('r11_tu_vplate', (60.0, -71.0, zl(2160)), (0, 0, 0), name='r11_tu_b_slab')
        tracks.append(dict(name='r11_tu_b_slab', keys=[(n * FRAME_T + 1 / 120.0, o + np.array([60.0, -71.0, zl(n)]), None) for n in (2160, 2186)],
                           on=2160 * FRAME_T, off=2186 * FRAME_T))
    else:                          # (the earlier horizontal slab)
        r.prop('r11_tu_slab', (40.0, -80.0, 150.0), (0, 0, 0), name='r11_tu_b_slab')
        tracks.append(dict(name='r11_tu_b_slab', keys=[(2165 * FRAME_T, o + np.array([40.0, -80.0, 131.0]), None), (2181 * FRAME_T, o + np.array([40.0, -80.0, 21.0]), None)],
                           on=2165 * FRAME_T, off=2184 * FRAME_T))
    # iris on the wall: four petals (retracted by g), frame ring, throat
    from lib.tube import frame_angles
    g = 17.0                       # petals retracted: their cyan corners at +-95 px around the centre (2145)
    for k in range(4):
        th = math.radians(90 * k); th2 = th + math.pi / 2
        X = (0, math.cos(th2), math.sin(th2)); Y = (0, math.cos(th), math.sin(th))
        off = np.array([-1.0, g * (math.cos(th) + math.cos(th2)), g * (math.sin(th) + math.sin(th2))])
        ang = frame_angles(X, Y); nm = 'r11_tu_b_petal%d' % k
        r.prop('r11_tu_petal', np.array(B_IRIS) + off, ang, name=nm)
        tracks.append(dict(name=nm, keys=[(n * FRAME_T, o + np.array([B_IRIS[0], y, z]) + off, None) for n, y, z in B_IRIS_KEYS]))
    r.prop('r11_tu_irisframe', np.array(B_IRIS) + [0.5, 0, 0], frame_angles((0, 1, 0), (0, 0, -1)), name='r11_tu_b_irisframe')
    tracks.append(dict(name='r11_tu_b_irisframe', keys=[(n * FRAME_T, o + np.array([B_IRIS[0] + 0.5, y, z]), None) for n, y, z in B_IRIS_KEYS]))
    # turret rising in front of the wall (eye track at 117.6: stock shell 42 units = 165 px), wings from 2095
    ks = sorted(B_EYE)
    tk = [(T0 + 0.0, o + np.array(B_EYE[ks[0]]) - EYE_OFF, TURRET_ANG)] + [(n * FRAME_T + 1001 / 120000.0, o + np.array(B_EYE[n]) - EYE_OFF, TURRET_ANG) for n in ks]
    tk[0] = (2083 * FRAME_T - 0.01, tk[1][1], TURRET_ANG)
    tracks.append(dict(name='r11_tu_b_turret', keys=tk, on=2083 * FRAME_T - 0.005, off=T_CUT_B - 0.001))
    r.prop('r11_tu_turret', np.array(B_EYE[ks[0]]) - EYE_OFF, TURRET_ANG, name='r11_tu_b_turret')
    # the side panels open (2093-2100): the open turret replaces the closed one from 2096
    tracks[-1]['off'] = 2096 * FRAME_T
    tracks.append(dict(name='r11_tu_b_turret_open', keys=[(t, p, a) for t, p, a in tk], on=2096 * FRAME_T, off=T_CUT_B - 0.001))
    r.prop('r11_tu_turret_open', np.array(B_EYE[ks[0]]) - EYE_OFF, TURRET_ANG, name='r11_tu_b_turret_open')
    # red glow over the lower body: a soft sprite just in front of the turret
    gk = [(t, p + EYE_OFF + np.array([-14.0, 0.0, -30.0]), None) for t, p, a in tk]
    tracks.append(dict(name='r11_tu_b_glow', keys=gk, on=2083 * FRAME_T - 0.005, off=T_CUT_B - 0.001))
    r.prop('r11_tu_glow2', np.array(B_EYE[ks[0]]) + [-14.0, 0.0, -30.0], (0, 0, 0), name='r11_tu_b_glow')
    # haze: a grey veil just in front of the camera until the cut at 2142
    tracks.append(dict(name='r11_tu_b_haze', keys=[(2083 * FRAME_T - 0.01, o + np.array([22.0, -30.0, 40.0]), None)], on=2083 * FRAME_T - 0.005, off=T_CUT_B - 0.001))
    r.prop('r11_tu_haze', (22.0, -30.0, 40.0), (0, 0, 0), name='r11_tu_b_haze')
    r.seal((-300, -600, -500), (B_WALL_X + 420, 400, 900))


def apply(v, d):
    TM.brush_materials()
    tracks = []
    shot_a(v, d, tracks)
    shot_b(v, d, tracks)
    e82 = 2082 * FRAME_T          # the film's last frame of shot A (both moments) is already greyed (p50 86 for 68)
    fades = dict(black=[(T0 - 0.01, 0.0), (T1 + 0.01, 0.0)],
                 grey=[(T0 - 0.01, 0.0), (e82 - 0.013, 0.0), (e82 - 0.012, 46.0), (e82 + 0.026, 46.0), (e82 + 0.027, 0.0), (T1 + 0.01, 0.0)])
    d.append(squirrel_tracks(tracks, fades))
    d.hook('Tu_Update(t);', late=True)
