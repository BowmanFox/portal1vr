"""Tower (film frames 1644-1917, 54.85-63.96 s), rebuilt in cell C9 (x 12000..16300, y 3200..9750, z -3000..5000),
sealed by a black shell. One continuous shot (moments/ncc.npy: no cut; the drop at 1655 is the iris opening):
  1644-1654  the camera in front of a closed iris (the whole frame flat grey 10)
  1655-1663  the iris opens as a cross (4 panels sliding apart diagonally); the camera passes its plane at 1664.5
  1664-1702  slow straight tube (8.5 units per frame) toward the tower base: collars every 370 (first at 319)
  1702-1763  the film keeps the tube around the camera (rails converging below the centre, the second collar
             centred and passed at ~1760) while COLMAP's camera rises: that tube is carried with the camera
  1763-1856  the camera rises beside the glass tower (poles, octagonal bands, turrets, arms, white discs, red beams,
             diagonal tubes with dark collars), then sinks again past the bands (1856-1917)
Camera: COLMAP run of out/tw/sfm (frames 1656-1930, 275 images, 0.86 px), aligned to the room lines at 1664-1690,
scaled by the collars, kept on the first tube's axis until 1702 (offline/out/tw/tools/twsolve.py, twcam.py).
COLMAP's world drifts (its rise is too fast for the tower's bands to stay put): the rust walls are a height field
of COLMAP's points (one static model), and the tower's poles, bands, discs and beams follow the film's own image
measurements (dark-row traces, pole runs, disc / beam tracks: out/tw/tools/dtrack.py, ltrack.py), as keyed props
moved by the director hook Tw_Update (angles through __KeyValueFromString). Ride coordinates: origin = camera 1664,
room axes. Engine budget: 15 brushes in the cell (large plain surfaces + the shell), 24 static props, 47 dynamic.
Round 3: the platform (disc + hanging pipes) placed per moment from the film's image of it (PLAT_*: centre row and
width 1664-1764, tilted to the film's shallow ~5 deg view); the glass tower's poles reach down to the platform
(POLE_Z0); the camera-carried collar stays until 1757.5 with a dark inside (the film's wide dark arc at 1755-1758);
from 1852 the keyed bands are tilted per moment into open rings (BAND_TILT, from below / above); left wall 54.
Tried and dropped (scored lower): bands placed from the film's top arcs as open rings over the whole rise (BAND_FILM,
higher edge, lower ssim), tilting from 1790, a 75-grey panel instead of the base column, the right walls 1.45x,
a brighter glass interior, a lower left wall from 58.7 s."""
import math, json, os
import numpy as np
from lib import vmfedit as E, tube
from lib.gen import mat, save, V
from lib.ride import Ride
from models import tower as TM

PFX = 'r11_tw'
CELL = ((12000.0, 3200.0, -3000.0), (16300.0, 9750.0, 5000.0))
ORIGIN = (12600.0, 6400.0, 0.0)
BLACK = 'corehub_intro/void_black'
FRAME_T = 1001.0 / 30000.0


def ft(n): return n * FRAME_T


def shell(v, lo, hi, material=BLACK, t=32.0):
    lo = np.asarray(lo, dtype=float); hi = np.asarray(hi, dtype=float)
    for ax in range(3):
        for side in (0, 1):
            a = lo.copy() - t; b = hi.copy() + t
            if side == 0: b[ax] = lo[ax]
            else: a[ax] = hi[ax]
            E.add_box(v, a, b, material)


class Cell:
    """ride coordinates -> map (origin + unit); boxes clamped to the cell"""
    def __init__(self, v, origin, unit=1.0, bounds=CELL):
        self.v = v; self.o = np.asarray(origin, dtype=float); self.k = float(unit)
        self.bounds = (np.asarray(bounds[0], dtype=float) + 40, np.asarray(bounds[1], dtype=float) - 40)
        self.det = v.create_ent(classname='func_detail')
        self.lo = np.full(3, np.inf); self.hi = np.full(3, -np.inf)

    def m(self, p):
        return self.o + np.asarray(p, dtype=float) * self.k

    def box(self, lo, hi, material, su=None, sv=None, grow=True, rot=False):
        from srctools.vmf import UVAxis
        a = self.m(np.minimum(lo, hi)); b = self.m(np.maximum(lo, hi))
        a = np.clip(a, self.bounds[0], self.bounds[1]); b = np.clip(b, self.bounds[0], self.bounds[1])
        if (b - a).min() < 1.0: return
        p = E.add_box(self.v, a, b, material, ent=self.det)
        if su is not None:
            for s in p.solid.sides:
                if rot and abs(s.normal().z) > 0.5:
                    s.uaxis = UVAxis(0, 1, 0); s.vaxis = UVAxis(-1, 0, 0)
                s.uaxis.scale = su * self.k; s.vaxis.scale = (sv or su) * self.k
        if grow: self.lo = np.minimum(self.lo, a); self.hi = np.maximum(self.hi, b)

    def prop(self, model, p, ang=(0, 0, 0), name=None):
        return E.add_prop(self.v, 'models/corehub_intro/%s.mdl' % model, self.m(p), ang, name=name)

    def seal(self, lo, hi):
        shell(self.v, np.maximum(self.m(lo), self.bounds[0]), np.minimum(self.m(hi), self.bounds[1]))


# ------------------------------------------------------------------------------------------------ iris
IRIS_FRAME = 1664.5          # the camera passes the iris plane (1/H of the cross arms falls linearly to 0 there)
IRIS_H = 40.0                # opening half-size (arm length 240 px at 1655L at 77 units)
IRIS_OUTER = 420.0
# gap half-width / IRIS_H against time (cross arms 1655E-1660L, then the panels stay: dark corners 1661-1663)
IRIS_G = [(ft(1655) - 0.004, 0.0), (ft(1655) + 0.017, 0.04), (ft(1656) + 0.008, 0.08), (ft(1657) + 0.008, 0.15),
          (ft(1658) + 0.008, 0.20), (ft(1659) + 0.008, 0.27), (ft(1660), 0.31), (ft(1661), 0.33), (ft(1666), 0.33)]


def tracks_code(tracks, fname='Tw_Update', tab='twTracks', t0=54.6, t1=64.2):
    """Squirrel: keyed props moved linearly between keys (position + optional angles), hidden outside [on, off]"""
    rows = []
    for tr in tracks:
        ks = []
        for t, p, a in tr['keys']:
            a = a if a is not None else (0, 0, 0)
            ks.append('[%.4f,Vector(%.2f,%.2f,%.2f),Vector(%.2f,%.2f,%.2f),%d]' % (t, p[0], p[1], p[2], a[0], a[1], a[2], 0 if tr['keys'][0][2] is None else 1))
        rows.append('{name="%s",on=%.3f,off=%.3f,k=[%s]}' % (tr['name'], tr.get('t_on', -1.0), tr.get('t_off', 1e6), ','.join(ks)))
    return (tab + ' <- [\n' + ',\n'.join(rows) + '];\n' + TRACK_CODE.replace('FNAME', fname).replace('TAB', tab)
            .replace('T0', '%.3f' % t0).replace('T1', '%.3f' % t1))


TRACK_CODE = '''function FNAME(t) {
    if(t<T0||t>T1)return;
    foreach(tr in TAB){
        local e=Entities.FindByName(null,tr.name); if(e==null)continue;
        if(t<tr.on||t>tr.off){e.SetOrigin(Vector(14000,9000,-2900));continue;}
        local k=tr.k; local n=k.len(); local a=k[0]; local b=k[0]; local f=0.0;
        if(t<=k[0][0]){a=k[0];b=k[0];}
        else if(t>=k[n-1][0]){a=k[n-1];b=k[n-1];}
        else {for(local i=0;i<n-1;i++)if(t>=k[i][0]&&t<=k[i+1][0]){a=k[i];b=k[i+1];f=(t-a[0])/(b[0]-a[0]);break;}}
        e.SetOrigin(a[1]+(b[1]-a[1])*f);
        if(a[3]==1){local g=a[2]+(b[2]-a[2])*f;e.__KeyValueFromString("angles",g.x+" "+g.y+" "+g.z);}
    }
}
'''


def iris(c, rd, tracks):
    """four grey-10 panels sliding apart diagonally in a grey-10 housing, perpendicular to the tube at IRIS_FRAME"""
    ctr = rd.pos(IRIS_FRAME); F = rd.direction(IRIS_FRAME)
    up = np.array([0, 0, 1.0]); L = np.cross(up, F); L /= np.linalg.norm(L); U = np.cross(F, L)
    c.v_prop = None
    sprop(c.v, PFX + '_iris_frame', ctr, tube.frame_angles(F, L))
    for k in range(4):
        a = math.radians(90 * k); Lk = L * math.cos(a) + U * math.sin(a); Uk = np.cross(F, Lk)
        ang = tube.frame_angles(F, Lk); name = '%s_iris%d' % (PFX, k)
        E.add_prop(c.v, 'models/corehub_intro/%s_iris_panel.mdl' % PFX, ctr, ang, name=name)
        keys = [(t, ctr + (Lk + Uk) * g * IRIS_H, None) for t, g in IRIS_G]
        tracks.append(dict(name=name, keys=keys, t_on=54.0, t_off=ft(IRIS_FRAME) + 0.05))
    TM.save_iris(IRIS_H, IRIS_OUTER)


# ------------------------------------------------------------------------------------------------ tube
def rails_along(v, P, name, up0=(0, 0, 1.0), rho=34.0, width=1.8, step=6.0, dynamic=False):
    """the four rails (on the diagonals of up0 / left) swept along polyline P (map coordinates) as one model"""
    from models.tubekit import rail_sweep
    P = np.asarray(P, dtype=float)
    keep = [0]; s = 0.0
    for i in range(1, len(P)):
        s += np.linalg.norm(P[i] - P[i - 1])
        if s >= step or i == len(P) - 1: keep.append(i); s = 0.0
    P = P[keep]
    T = np.gradient(P, axis=0); T /= np.linalg.norm(T, axis=1, keepdims=True) + 1e-12
    U = np.zeros_like(P); u = np.asarray(up0, dtype=float)
    for i in range(len(P)):
        u = u - T[i] * (u @ T[i]); u /= np.linalg.norm(u); U[i] = u
    W = np.cross(T, U)
    org = P[0].copy()
    save(rail_sweep(P - org, U, W, rho, width, material=PFX + '_rail'), name)
    if dynamic: E.add_prop(v, 'models/corehub_intro/%s.mdl' % name, org, (0, 0, 0), name=name)
    else: sprop(v, name, org)
    return org


# ------------------------------------------------------------------------------------------------ the room
TUBE_DIR = np.array([0.9894, 0.0969, -0.1082])     # the first tube's axis (camera 1660-1688, room coordinates)
TUBE_PT = np.array([81.7, 8.1, -9.0])
COLLARS_AX = [319.0, 689.0, 1059.0, 1429.0]         # collars along the tube (axial, from the cloud: first collar's
                                                    # inner rings at 319, the film's inner circles at 1664: 681, 1060, 1376)
TUBE_END_AX = 1900.0
TINTS = [0.55, 0.65, 0.75, 0.85, 0.95, 1.05, 1.15, 1.25, 1.4, 1.55, 1.75, 2.0]
BASE_DIM = 1.0            # (0.8 for the walls behind the tower base scored the same or lower)
RISE_LIFT = 1.1           # film 60.8-62.4 s: the walls around the tower 37-63, the cells gave 31-52
GLASS_LIFT = 1.35          # film 59-63 s: between the poles 55-72, the rust cells alone gave 41-56
RIGHT_LIFT = 1.0           # (film 1810-1870: the right third 50-58, the cells give 36-39; lifting them 1.45x scored lower)
RIGHT_Z0 = 1400.0


def tube_axis(a): return TUBE_PT + TUBE_DIR * (a - TUBE_PT @ TUBE_DIR)


def sprop(v, model, origin, angles=(0, 0, 0)):
    """static prop (no name: the 2009 engine's entity limit; prop_static for everything that does not move)"""
    return E.add_prop(v, 'models/corehub_intro/%s.mdl' % model, origin, angles, cls='prop_static')


def backdrop(c, rd):
    """rust walls as a height field from the cloud (offline/out/tw/tools/twsolve.py: backdrop), one static model
    (cells: front face + sides; tint levels from the points' median grey)"""
    from lib.gen import Mesh, mat
    B = rd.raw['backdrop']; ys, zs = B['ystep'], B['zstep']
    names = []
    for i, t in enumerate(TINTS):
        names.append(mat('%s_rustm%d' % (PFX, i), (t, t, t), base='corehub_intro/%s_rust' % PFX))
    m = Mesh()
    for y0, z0, x, g in B['cells']:
        if y0 + ys <= -378.0 + 1e-6 and x < 1650.0: continue      # in front of the concrete pillar (it shows in the film)
        t = (g / 85.0) ** 0.6
        if z0 >= 900.0: t *= RISE_LIFT
        else: t *= BASE_DIM
        if z0 >= 900.0 and -10.0 <= y0 + ys / 2 <= 355.0: t *= GLASS_LIFT     # seen through the tower's glass: lighter
        if z0 >= RIGHT_Z0 and y0 + ys / 2 < -10.0: t *= RIGHT_LIFT       # right of the tower
        i = int(np.argmin([abs(math.log(max(t, 0.05) / q)) for q in TINTS]))
        m.box((x, y0, z0), (x + 60.0, y0 + ys, z0 + zs), names[i], mats={'+x': None})
    m.uv_box(scale=512.0)
    save(m, PFX + '_backdrop')
    sprop(c.v, PFX + '_backdrop', np.asarray(ORIGIN))


# the glass tower (rising part, z > 900): axis, poles and bands from the film's images at the camera of that time
# (poles at 195 / 395 px, band spans 330 px at 1820); band heights fitted to the film's dark-row traces with the
# front edge at x 1500 (A 2055 / 2189, B 2568 / 2610 rising / sinking; a band at the horizon at 1812-1820 -> 1650);
# the bands the camera passes close by while sinking (1886-1890, 1912-1917) reach close to its path (COLMAP's
# sinking path drifts ~450 away from the tower relative to the rising one) and show only while it sinks
POLE_Z0 = 330.0            # the glass tower's poles reach down to the platform (film 1756-1770; they started at 900)
TOWER = dict(x=1550.0, y=172.0, poles=[(1450.0, 355.0, 100.0), (1450.0, -10.0, 65.0)], pole_descent=[(1450.0, 355.0), (1450.0, -10.0)],    # (moved nearer while sinking: scored lower)
             # the poles follow the film (dark run centres at row 200, 1760-1916, on the plane x 1450)
             pole_keys=[[(1760, 337.0), (1780, 346.0), (1800, 370.0), (1830, 361.0), (1845, 384.0), (1860, 387.0), (1870, 366.0), (1880, 410.0),
                         (1895, 380.0), (1904, 377.0), (1910, 313.0), (1916, 263.0)],
                        [(1760, 11.0), (1780, 6.0), (1800, 6.0), (1820, -8.0), (1840, -20.0), (1860, -29.0), (1870, -27.0), (1880, -65.0),
                         (1895, -33.0), (1904, -42.0), (1916, -54.0)]],
             pole_z0=POLE_Z0, pole_z1=3400.0, column=False,
             key_dz=0.0,               # (moving them -100 / +50 scored the same or lower)
             band_ri=200.0, band_t=70.0, bands=[(1707.0, 330.0), (2102.0, 330.0), (2504.0, 330.0), (2900.0, 330.0), (1800.0, 630.0), (1180.0, 820.0)],
             # bands A, B, C follow the film's dark-row traces (heights for a front edge at x 1220 from each frame's
             # camera: COLMAP's rise is too fast for one static height, A would drift 1716 -> 2184 -> 1967)
             keyed={1: [(1800, 1716), (1808, 1831), (1816, 1918), (1824, 1989), (1832, 2063), (1840, 2105), (1848, 2160), (1856, 2184), (1864, 2175), (1872, 2155), (1880, 2098), (1888, 1967)],
                    2: [(1824, 2313), (1832, 2387), (1840, 2426), (1848, 2462), (1856, 2489), (1864, 2470), (1872, 2432)],
                    0: [(1812, 1694), (1816, 1714), (1820, 1766)]},
             col_r=150.0, col_z0=900.0, col_z1=3400.0, col_tint=0.52, disc_r0=0.0, disc_r1=310.0, disc_t=30.0, disc_z=330.0)
BASE = dict(x=2060.0, y=230.0, r=150.0)            # the tower's base (1664-1730: column x ~1984, platform rim z ~300 at x ~2170)
GLASS_BASE = False         # (a grey 75 panel between the base poles instead of the column scored lower)
BASE_COLUMN = True         # (removing the grey column above the platform scored lower at 57.85-59.35 s)
# the platform in the film (E moments, 640x400): centre x ~292, centre row and width against n - 1700 (rows: 1664 125,
# 1688 130, 1712 147, 1728 191, 1752 295, 1760 343; widths 175 at 1664 .. 221 at 1728 .. ~295 at 1760); placed per
# moment along the ray through that centre at the distance that gives that width (radius disc_r1)
PLAT_CY = (-7.20151287e-06, 4.81057484e-04, 3.98339134e-02, 7.66206587e-01, 1.34342468e+02)
PLAT_W = (1.26635545e-02, 7.92161804e-01, 1.90951296e+02)
PLAT_CX = 292.0
PLAT_N = (1650.0, 1778.0)
PLAT_OFF = 1780.0
PLAT_ELEV = 5.0


def cam_at(rd, fn):
    """camera (position, forward, up) at fractional film frame fn (moments: n = E, n + 0.5 = L)"""
    M = rd.moments
    fs = np.array([m[1] + (0.5 if m[2] == 'L' else 0.0) for m in M])
    i = int(np.clip(np.searchsorted(fs, fn) - 1, 0, len(M) - 2)); a = (fn - fs[i]) / max(fs[i + 1] - fs[i], 1e-9); a = min(max(a, 0.0), 1.0)
    p = M[i][3] * (1 - a) + M[i + 1][3] * a; f = M[i][4] * (1 - a) + M[i + 1][4] * a; u = M[i][5] * (1 - a) + M[i + 1][5] * a
    f = f / np.linalg.norm(f); u = u - f * (u @ f); u /= np.linalg.norm(u)
    return p, f, u


def img_ray(rd, fn, px, py, F=461.88):
    p, f, u = cam_at(rd, fn); r = np.cross(f, u)
    d = f * F + r * (px - 319.5) - u * (py - 199.5); return p, d / np.linalg.norm(d)


def plat_keys(rd, R, T):
    """[(t, origin)] of the platform disc (top at the origin) from the film's platform centre / width"""
    out = []
    for t, n, mo, p, f, u in rd.moments:
        fn = n + (0.5 if mo == 'L' else 0.0)
        if fn < PLAT_N[0] or fn > PLAT_N[1] or (int(round(fn * 2)) % 2): continue
        x = min(max(fn, 1664.0), 1776.0) - 1700.0
        cy = float(np.polyval(PLAT_CY, x)) + (0.0 if fn >= 1664 else 0.0); w = float(np.polyval(PLAT_W, x))
        c, d = img_ray(rd, fn, PLAT_CX, cy)
        s = 461.88 * R / (w / 2.0)
        pos = c + d * s + np.array([0, 0, T / 2.0])
        # the film's platform is seen nearly edge-on (1744-1770: ~25 px of top face for ~290 px width, ~5 deg):
        # tilted so it never shows steeper than PLAT_ELEV
        phi = math.degrees(math.asin(d[2])); tgt = math.copysign(min(abs(phi), PLAT_ELEV), phi)
        out.append((t, pos, (-(phi - tgt), math.degrees(math.atan2(d[1], d[0])), 0.0)))
    return out
LWALL_LOW_T = None         # (a lower part from 58.7 s, z 300-1000, scored lower at 59.1 s)
LWALL_LOW_Z = 300.0
LWALL_OFF = 63.0           # the film's left side turns dark after the near band (1888)
DESCENT_T = 62.15          # frame 1863: the camera has turned from rising to sinking


# the film's bands look like open rings at every height in the frame (1790-1890: the outer outline ~150-175 px tall
# for ~340 px wide, seen from below in the upper part of the frame and from above in the lower part), more open than
# a level ring at COLMAP's camera pitch can look: each keyed band is tilted per moment about the horizontal axis
# across the view so it shows at BAND_ELEV from below / above (switching at row BAND_ROW)
BAND_TILT = True
TILT_FROM = 1852.0        # (tilting from 1800 scored lower at 59.1-61.4 s, higher at 62.35-62.6 s): level before,
TILT_RAMP = 8.0           # ramped in over 8 frames
BAND_ELEV = 22.0
BAND_ROW = 250.0


BAND_DY = 70.0            # the keyed heights put a level band on the film's top arc (dark rows at the centre column);
                          # the open ring's centre lies ~70 px lower (outline ~160 px tall from that arc)


# the film's bands from their top arcs (dark run centres at the centre column x 270-330 of the E moments, 640x400):
# the open ring's centre lies BAND_DY below, at x BAND_CX, at the distance that gives its ~340 px width (radius 330)
BAND_RUNS = {1: [(1792, 9.5), (1796, 36.5), (1800, 63.0), (1804, 91.5), (1808, 119.0), (1812, 147.0), (1816, 174.5), (1820, 200.0),
                 (1824, 225.5), (1828, 247.5), (1832, 268.0), (1836, 287.0), (1840, 303.5), (1844, 315.0), (1848, 321.0), (1852, 323.0),
                 (1856, 319.5), (1860, 311.0), (1864, 291.0), (1868, 263.5), (1872, 229.0), (1876, 190.5), (1880, 141.5)],
             2: [(1820, 2.0), (1824, 22.5), (1828, 48.5), (1832, 67.5), (1836, 87.0), (1840, 103.0), (1844, 117.0), (1848, 124.5),
                 (1852, 128.0), (1856, 126.0), (1860, 117.5), (1864, 99.5), (1868, 76.5), (1872, 43.0), (1876, 11.0)]}
BAND_CX = 295.0
BAND_DIST = 897.0
BAND_DY_BELOW = 106.0     # top arc -> ring centre, seen from below (the near wall is the top)
BAND_DY_ABOVE = 40.0      # seen from above (the far side is the top)
BAND_FILM = False         # bands 1 / 2 placed from BAND_RUNS (else from the old keyed heights)
BAND_FILM_DIMS = (250.0, 40.0)   # inner radius, thickness of those bands


def band_film_keys(rd, runs, step=2):
    ns = [n for n, _ in runs]; ys = [y for _, y in runs]
    out = []; prev = None
    for fn in np.arange(ns[0] - 4, ns[-1] + 4.01, step):
        yr = float(np.interp(fn, ns, ys, left=ys[0] - (ys[1] - ys[0]), right=ys[-1] + (ys[-1] - ys[-2])))
        below = yr + BAND_DY < BAND_ROW
        yc = yr + (BAND_DY_BELOW if below else BAND_DY_ABOVE)     # (the near side projects farther from the centre)
        cp, d = img_ray(rd, fn, BAND_CX, yc)
        pos = cp + d * BAND_DIST
        phi_c = math.degrees(math.asin(d[2]))
        tgt = BAND_ELEV if below else -BAND_ELEV
        ang = np.array([-(phi_c - tgt), math.degrees(math.atan2(d[1], d[0])), 0.0])
        if prev is not None: ang = prev + (ang - prev + 180.0) % 360.0 - 180.0
        prev = ang
        out.append((ft(fn), pos, tuple(ang)))
    return out


def band_tilt_keys(rd, axis_pt, keyed, dz=0.0, step=2):
    ns = [n for n, _ in keyed]; zs = [z + dz for _, z in keyed]
    out = []; prev = None
    for fn in np.arange(ns[0], ns[-1] + 0.01, step):
        z = float(np.interp(fn, ns, zs)); p0 = np.asarray(axis_pt, float) + (0, 0, z)
        cp, f, u = cam_at(rd, fn); r0 = p0 - cp; rr = np.cross(f, u)
        x0 = 319.5 + 461.88 * (r0 @ rr) / (r0 @ f); y0 = 199.5 - 461.88 * (r0 @ u) / (r0 @ f)
        wt = min(max((fn - TILT_FROM) / TILT_RAMP, 0.0), 1.0)
        _, d = img_ray(rd, fn, x0, y0 + BAND_DY * wt)
        pos = cp + d * np.linalg.norm(r0)
        r = pos - cp; dist = np.linalg.norm(r)
        phi_c = math.degrees(math.asin(r[2] / dist))
        row = y0 + BAND_DY
        tgt = BAND_ELEV if row < BAND_ROW else -BAND_ELEV
        delta = (phi_c - tgt) * wt
        ang = np.array([-delta, math.degrees(math.atan2(r[1], r[0])), 0.0])
        if prev is not None: ang = prev + (ang - prev + 180.0) % 360.0 - 180.0
        prev = ang
        out.append((ft(fn), pos, tuple(ang)))
    return out


def tower(c, rd, tracks):
    """the glass tower: rust column, two black poles at its sides (as seen from the camera), dark octagonal ring
    bands, the base disc"""
    T = dict(TOWER); M = TM.brush_materials(); o = np.asarray(ORIGIN)
    if BAND_TILT or BAND_FILM:       # (the octagon's 22.5 deg yaw baked into the tilted bands)
        T['band_rot'] = {k: 0.0 for k in T['keyed'] if k != 0 or BAND_FILM or TILT_FROM < 1820}
    if BAND_FILM: T['band_dims'] = {k: BAND_FILM_DIMS for k in BAND_RUNS}
    TM.save_tower(T)
    ax = np.array([T['x'], T['y'], 0.0])
    if T.get('column', True): sprop(c.v, PFX + '_column', o + ax)
    for k, (z, ro) in enumerate(T['bands']):
        name = '%s_band%d' % (PFX, k)
        if k in T.get('keyed', {}):
            if (BAND_FILM or (BAND_TILT and TILT_FROM < 1820)) and k == 0: continue   # (1812-1820: the bottom arc of band 1's open ring)
            if BAND_FILM and k in BAND_RUNS:
                ks = band_film_keys(rd, BAND_RUNS[k])
                E.add_prop(c.v, 'models/corehub_intro/%s_band%d.mdl' % (PFX, k), ks[0][1], ks[0][2], name=name)
                tracks.append(dict(name=name, keys=ks, t_on=ks[0][0] - 0.01, t_off=ks[-1][0] + 0.01)); continue
            if BAND_TILT and (k != 0 or TILT_FROM < 1820):
                ks = band_tilt_keys(rd, o + ax, T['keyed'][k], T.get('key_dz', 0.0))
                E.add_prop(c.v, 'models/corehub_intro/%s_band%d.mdl' % (PFX, k), ks[0][1], ks[0][2], name=name)
            else:
                ks = [(ft(n), o + ax + (0, 0, zz + T.get('key_dz', 0.0)), None) for n, zz in T['keyed'][k]]
                E.add_prop(c.v, 'models/corehub_intro/%s_band%d.mdl' % (PFX, k), ks[0][1], (0, 22.5, 0), name=name)
            tracks.append(dict(name=name, keys=ks, t_on=54.0, t_off=70.0)); continue
        if ro <= 600: sprop(c.v, name, o + ax + (0, 0, z), (0, 22.5, 0)); continue
        E.add_prop(c.v, 'models/corehub_intro/%s_band%d.mdl' % (PFX, k), o + ax + (0, 0, z), (0, 22.5, 0), name=name)
        if ro > 600:          # the bands the sinking camera passes close by (1884-1917): only while it sinks
            tracks.append(dict(name=name, keys=[(62.0, o + ax + (0, 0, z), None)], t_on=DESCENT_T, t_off=70.0))
    # the poles are models: while the camera sinks (1856-1885) they come ~250 nearer (film 1898: poles at 120-220 /
    # 520-570 px, 1.7 times wider apart than while rising; COLMAP's sinking path drifts away from the tower)
    from lib.gen import Mesh
    for k, ((px, py, pw), (dx, dy)) in enumerate(zip(T['poles'], T['pole_descent'])):
        m = Mesh(); w = pw / 2; m.box((-w, -w, 0.0), (w, w, T['pole_z1'] - T['pole_z0']), PFX + '_pole')
        save(m, '%s_pole%d' % (PFX, k))
        nm = '%s_pole%d' % (PFX, k); a = o + (px, py, T['pole_z0']); b = o + (dx, dy, T['pole_z0'])
        E.add_prop(c.v, 'models/corehub_intro/%s.mdl' % nm, a, (0, 0, 0), name=nm)
        ks = [(ft(n), o + (px, yy, T['pole_z0']), None) for n, yy in T['pole_keys'][k]]
        tracks.append(dict(name=nm, keys=ks, t_on=54.0, t_off=70.0))
    # the base (seen 1655-1776 from the tube): platform disc and its hanging pipes placed per moment on the film's
    # image of the platform (PLAT_IMG: centre and width, 1664-1764), two poles (1664: 250 / 352 px -> y 418 / -28)
    TM.save_hangers()
    pk = plat_keys(rd, T['disc_r1'], T['disc_t'])
    for nm, dz in ((PFX + '_disc', 0.0), (PFX + '_hangers', -T['disc_t'])):
        ks = [(t, p + (0, 0, dz), a) for t, p, a in pk]
        E.add_prop(c.v, 'models/corehub_intro/%s.mdl' % nm, ks[0][1], ks[0][2], name=nm + 'k')
        tracks.append(dict(name=nm + 'k', keys=ks, t_on=54.0, t_off=ft(PLAT_OFF)))
    if BASE_COLUMN:
        TM.save_column(BASE['r'], T['col_z0'], T['col_z1'], PFX + '_column_base')
        sprop(c.v, PFX + '_column_base', o + (BASE['x'], BASE['y'], 330.0 - T['col_z0']))
    for y in (418.0, -28.0):
        c.box((1990.0, y - 30.0, 330.0), (2050.0, y + 30.0, 905.0), M['black'])
    if GLASS_BASE:      # the glass tower's interior between the base poles (film 1696-1735: 75 grey with streaks)
        c.box((2055.0, 2.0, 330.0), (2075.0, 388.0, 905.0), M['glassbase'], su=1.0, sv=2.0)
    # the light grey ledge behind the platform (1664: rows 105-145, x 155-415 px on the plane x 2150; film 94)
    c.box((2150.0, -321.0, 230.0), (2190.0, 904.0, 414.0), M['ledge'])
    # horizontal pipes across the view (1664: rows 222 / 245 px), with the flanges' darker rings left out
    for z in (-89.0, -163.0):
        sprop(c.v, PFX + '_pipe', o + (1500.0, 0.0, z), (0, 90, 0))
    TM.save_pipe(2600.0, 7.0)


# inside the glass tower: positions of the film's objects on the plane x 1700 (film pixels of the frame named, ray
# from that frame's camera; out/tw/tools/blobs.py): white discs 1790 (232,102) / (337,197), 1850 (250,140),
# 1848 (371,99), 1760-1776 (334,30-100); red beams 1760 (252,0-84), 1790 (315,165)-(370,400), 1904 (290,0)-(330,320)
# and (360,0)-(374,319); turrets / arms 1850 (190,190), (210,250), (400,250); diagonal tubes 1800 (560,40)-(640,300)
# right, 1850 (0,50)-(200,170) left
INT_K = 0.68                              # objects on the plane x 1350 instead of ~1700: sizes scaled by depth
DISCS = [(1350.0, 269.0, 1472.0), (1350.0, 105.0, 1317.0), (1350.0, 251.0, 2476.0), (1350.0, 32.0, 2544.0), (1350.0, 100.0, 1087.0)]
BEAMS = [((1350.0, 238.0, 1080.0), (1350.0, 236.0, 900.0)), ((1350.0, 138.0, 1368.0), (1350.0, 61.0, 1018.0)),
         ((1350.0, 207.0, 1733.0), (1350.0, 162.0, 1323.0)), ((1350.0, 115.0, 1734.0), (1350.0, 109.0, 1323.0))]
TURRETS = [(1350.0, 352.0, 2385.0), (1350.0, -5.0, 2276.0), (1350.0, 275.0, 2272.0), (1350.0, 121.0, 2326.0), (1350.0, 83.0, 2421.0),
           # white objects of frames 1806 / 1840 / 1866 (bright blobs, plane x 1350)
           (1350.0, 100.0, 2000.0), (1350.0, 245.0, 1700.0), (1350.0, 40.0, 2500.0), (1350.0, 245.0, 2465.0), (1350.0, 95.0, 2250.0)]
ARMS = [(1350.0, 283.0, 2254.0), (1350.0, 44.0, 2373.0), (1350.0, 245.0, 2380.0), (1350.0, 100.0, 1900.0)]          # frame 1830: arms (220,65)-(230,145), (370,25)-(368,80)
CUBES = [(1350.0, 182.0, 2200.0)]                                 # frame 1830: the black cube at (290,175)
DIAGS = [((1150.0, 536.0, 2245.0), (1150.0, 323.0, 2021.0), 1.0), ((1680.0, -244.0, 2351.0), (1680.0, -416.0, 1928.0), 1.0),
         ((1350.0, 99.0, 2200.0), (1350.0, -59.0, 1841.0), INT_K)]     # frame 1830: left / right tubes, the disc's tube


GLASS = dict(x=1330.0, y0=27.0, y1=333.0, z0=900.0, z1=3400.0)   # between the poles as seen from the rising camera


def interior(c, rd, tracks):
    o = np.asarray(ORIGIN)
    # the glass front: the film's tower interior is lighter than its walls (55-72 against 41-56 here, 59-63 s)
    TM.save_glass(GLASS['y1'] - GLASS['y0'], GLASS['z1'] - GLASS['z0'])
    # sprop(c.v, PFX + '_glassfront', o + (GLASS['x'], GLASS['y0'], GLASS['z0']))   # tried: edges and ssim lower
    BT = rd.raw.get('beams', [])
    lens = [float(np.median([np.linalg.norm(np.subtract(b, a)) for n, a, b in tr])) for tr in BT]
    TM.save_interior(lens, INT_K)
    # the white discs follow their film tracks (offline/out/tw/tools/dtrack.py: the discs' segments grouped and
    # linked over frames, put on the plane x 1350 from each frame's camera)
    for k, tr in enumerate(rd.raw.get('discs', [])):
        nm = '%s_disc%d' % (PFX, k); ks = [(ft(n), o + (x, y, z), None) for n, x, y, z in tr]
        E.add_prop(c.v, 'models/corehub_intro/%s_wdisc.mdl' % PFX, ks[0][1], (0, 0, 0), name=nm)
        tracks.append(dict(name=nm, keys=ks, t_on=ks[0][0] - 0.035, t_off=ks[-1][0] + 0.035))
    # red beams (and the turret each hangs from) follow their film tracks (offline/out/tw/tools/ltrack.py)
    for k, tr in enumerate(BT):
        ks = []; kt = []; prev = None
        for n, a, b in tr:
            ang = np.array(tube.axis_angles(np.subtract(b, a)))
            if prev is not None: ang = prev + (ang - prev + 180.0) % 360.0 - 180.0
            prev = ang; ks.append((ft(n), o + a, tuple(ang))); kt.append((ft(n), o + a + (0, 0, 14.0), None))
        nm = '%s_beam%d' % (PFX, k)
        E.add_prop(c.v, 'models/corehub_intro/%s_laser%d.mdl' % (PFX, k), ks[0][1], ks[0][2], name=nm)
        tracks.append(dict(name=nm, keys=ks, t_on=ks[0][0] - 0.035, t_off=ks[-1][0] + 0.035))
        nm = '%s_bturret%d' % (PFX, k)
        E.add_prop(c.v, 'models/corehub_intro/%s_turret.mdl' % PFX, kt[0][1], (0, 0, 0), name=nm)
        tracks.append(dict(name=nm, keys=kt, t_on=kt[0][0] - 0.035, t_off=kt[-1][0] + 0.035))
    for p in TURRETS: sprop(c.v, PFX + '_turret', o + p)
    for p in CUBES: sprop(c.v, PFX + '_cube', o + p, (10, 30, 20))
    for p in ARMS: sprop(c.v, PFX + '_arm', o + p)
    for a, b, kk in DIAGS:
        a = np.asarray(a); b = np.asarray(b); dv = (a - b) / np.linalg.norm(a - b)
        L = np.cross(dv, [1.0, 0, 0]); L /= np.linalg.norm(L)
        ctr = (a + b) / 2; sprop(c.v, PFX + ('_diag' if kk != 1.0 else '_diag1'), o + ctr - dv * 900.0 * kk, tube.frame_angles(dv, L))


def room(c, rd, lw_tracks):
    """the big surfaces seen from the tube (1664: film edges -> rays from the camera, depths from the cloud)"""
    M = TM.brush_materials()
    # right concrete pillar: front face x 1650 (cloud), left edge at 453 px in 1664 -> y -378
    c.box((1650.0, -1150.0, -700.0), (1950.0, -378.0, 1400.0), M['concrete'], su=1.0, sv=4.0)
    c.box((1650.0, -1150.0, 1400.0), (1950.0, -378.0, 3400.0), M['wall_dim'], su=1.0)      # darker above (film 60-63 s: right side 45-55)
    # left flat grey wall facing the camera: x 1500, right edge at 132 px in 1664 -> y 710
    c.box((1500.0, 710.0, -260.0), (1560.0, 1400.0, 3400.0), M['grey'])
    # floor block (light concrete) bottom left: top z -283, right edge 192 px -> y 505
    c.box((1500.0, 505.0, -700.0), (1700.0, 1400.0, -283.0), M['block'], su=1.0)
    # plinth below the tower base (grey 64): top z -254, y -343..495
    c.box((1500.0, -343.0, -700.0), (2150.0, 495.0, -254.0), M['slab'])
    # floor
    c.box((-400.0, -1200.0, -760.0), (2400.0, 1400.0, -700.0), M['floor'])
    # the left wall beside the tower, seen during the rise (1790: light grey 87 above, dark panels 30 below eye level)
    # (a model, hidden while the camera sinks: the film's left side is dark then, 16-29)
    from lib.gen import Mesh
    m = Mesh(); m.box((0.0, 0.0, 0.0), (40.0, 1020.0, 2400.0), PFX + '_lwall'); save(m, PFX + '_lwall')
    E.add_prop(c.v, 'models/corehub_intro/%s_lwall.mdl' % PFX, np.asarray(ORIGIN) + (1300.0, 380.0, 1000.0), (0, 0, 0), name=PFX + '_lwall')
    lw_tracks.append(dict(name=PFX + '_lwall', keys=[(54.0, np.asarray(ORIGIN) + (1300.0, 380.0, 1000.0), None)], t_on=54.0, t_off=LWALL_OFF))
    if LWALL_LOW_T is not None:      # its lower part once the camera has risen out of the tube (film 1764-1790: the
        m = Mesh(); m.box((0.0, 0.0, 0.0), (40.0, 1020.0, 1000.0 - LWALL_LOW_Z), PFX + '_lwall'); save(m, PFX + '_lwall2')   # left third grey to the bottom)
        p2 = np.asarray(ORIGIN) + (1300.0, 380.0, LWALL_LOW_Z)
        E.add_prop(c.v, 'models/corehub_intro/%s_lwall2.mdl' % PFX, p2, (0, 0, 0), name=PFX + '_lwall2')
        lw_tracks.append(dict(name=PFX + '_lwall2', keys=[(54.0, p2, None)], t_on=LWALL_LOW_T, t_off=LWALL_OFF))


# ------------------------------------------------------------------------------------------------ the tube 1702-1795
# COLMAP's camera rises from ~1700 (its scene points fit that), but the film keeps showing the tube around the camera:
# the rails converge on a vanishing point that moves down steadily (x ~297 px; angle below the view axis, film rails:
# 8.9 deg at 1700 .. 25.6 at 1742 .. 53.5 at 1790, cubic fit rms 0.5 deg) and the second collar stays centred on it,
# approached at 6.1 slowing to 5.4 units per frame (its light band's outer edge: f/r 5.70 at 1700 .. 2.22 at 1736,
# quadratic fit) and passed at 1763. Neither fits a static tube in COLMAP's world, so this tube is carried with the camera: rails and
# collar placed per moment from these film measurements.
TUBE_LEAVE = 1702.0
CT_POLY = (-2.4e-05, 2.316e-03, 0.521349, 24.577738)       # angle below the view axis (deg) of the rails, n - 1740
CT_VPX = 297.0
CT_FR = (2.59e-04, -0.106884, 5.722989)                       # collar f/r (outer band edge) against n - 1700 (rms 0.02,
                                                             # 1700-1736; a cubic through 1749 / 1757 as well scored lower)
CT_PASS = 1763.2
CT_HIDE = 1757.5           # the collars are hidden from here (their wide light band at 1757 scored lower than nothing)
CT_DK = 1.0                # (distance factor on the fitted collar distances: 1.0 scored best of 0.85 / 1.0 / 1.2)
CT_END = 1795.0


def cam_tube(v, rd, tracks):
    from models.tubekit import rail_sweep
    L0, L1 = -120.0, 1100.0
    P = np.array([[L0, 0, 0], [L1, 0, 0]], float); U = np.array([[0, 0, 1.0]] * 2); W = np.array([[0, 1.0, 0]] * 2)
    save(rail_sweep(P, U, W, 34.0, 1.8, material=PFX + '_rail'), PFX + '_camtube')
    keys_r = []; keys_c = []; prev_r = None; prev_c = None
    F = 461.88
    for t, n, mo, p, f, u in rd.moments:
        fn = n + (0.5 if mo == 'L' else 0.0)
        if fn < TUBE_LEAVE - 1 or fn > CT_END + 1: continue
        th = math.radians(np.polyval(CT_POLY, fn - 1740.0))
        r = np.cross(f, u)
        dvec = f + r * (CT_VPX - 319.5) / F - u * math.tan(th); dvec /= np.linalg.norm(dvec)
        left = np.cross(u, dvec); left /= np.linalg.norm(left)
        ang = np.array(tube.frame_angles(dvec, left))
        if prev_r is not None: ang = prev_r + (ang - prev_r + 180.0) % 360.0 - 180.0
        prev_r = ang
        keys_r.append((t, np.asarray(p), tuple(ang)))
        dist = CT_DK * 61.06 * max(float(np.polyval(CT_FR, fn - 1700.0)), 0.0) if fn < CT_PASS else 0.0
        ca = np.array(tube.axis_angles(dvec))
        if prev_c is not None: ca = prev_c + (ca - prev_c + 180.0) % 360.0 - 180.0
        prev_c = ca
        keys_c.append((t, np.asarray(p) + dvec * dist, tuple(ca)))
    E.add_prop(v, 'models/corehub_intro/%s_camtube.mdl' % PFX, keys_r[0][1], keys_r[0][2], name=PFX + '_camtube')
    # carried until the collar passes (1763), then left where it is: the camera rises out of it (1764-1795: the
    # film's rails only below the camera, on the right and bottom left)
    tracks.append(dict(name=PFX + '_camtube', keys=[k for k in keys_r if k[0] <= ft(CT_PASS) + 0.01], t_on=ft(TUBE_LEAVE), t_off=ft(CT_END)))
    t_pass = ft(CT_HIDE)
    for j, extra in enumerate((0.0, 370.0, 740.0)):           # the collar and the next two beyond it (inner rings)
        ks = [(t, pc + (pc - keys_r[i][1]) / max(np.linalg.norm(pc - keys_r[i][1]), 1e-6) * extra, a) for i, (t, pc, a) in enumerate(keys_c)]
        nm = '%s_camcollar%d' % (PFX, j)
        E.add_prop(v, 'models/corehub_intro/%s_collar.mdl' % PFX, ks[0][1], ks[0][2], name=nm)
        tracks.append(dict(name=nm, keys=[k for k in ks if k[0] <= t_pass + 0.02], t_on=ft(TUBE_LEAVE), t_off=t_pass))


def apply(v, d):
    TM.brush_materials()
    rd = Ride('tw', origin=ORIGIN)
    cam = rd.camera()
    d.override_camera(cam, fov=60.0)
    c = Cell(v, ORIGIN)
    tracks = []
    iris(c, rd, tracks)
    o = np.asarray(ORIGIN)
    # the tube: straight from the iris plane along its axis
    a0 = float((rd.pos(IRIS_FRAME) - o) @ TUBE_DIR)
    P = np.array([o + tube_axis(a) for a in np.linspace(a0, TUBE_END_AX, 40)])
    org = rails_along(v, P, PFX + '_rails', dynamic=True)
    t_leave = ft(TUBE_LEAVE)
    tracks.append(dict(name=PFX + '_rails', keys=[(54.0, org, None)], t_on=54.0, t_off=t_leave))
    for k, a in enumerate(COLLARS_AX):
        nm = '%s_collar%d' % (PFX, k)
        E.add_prop(v, 'models/corehub_intro/%s_collar.mdl' % PFX, o + tube_axis(a), tube.axis_angles(TUBE_DIR), name=nm)
        tracks.append(dict(name=nm, keys=[(54.0, o + tube_axis(a), tube.axis_angles(TUBE_DIR))], t_on=54.0, t_off=t_leave))
    cam_tube(v, rd, tracks)
    backdrop(c, rd)
    room(c, rd, tracks)
    tower(c, rd, tracks)
    interior(c, rd, tracks)
    d.append(tracks_code(tracks))
    d.hook('Tw_Update(t);')
    # the base director's old fades in this range (iris, collar passes) are replaced by geometry: no screen black
    d.append('''function Tw_Fade(t) {
    if(t>=%.4f && t<%.4f) SetScreenBlack(0);
}''' % (ft(1644) - 0.001, ft(1917) + 1 / 60.0 + 0.002))
    d.hook('Tw_Fade(t);', late=True)
    shell(v, np.array(CELL[0]) + 40, np.array(CELL[1]) - 40)
