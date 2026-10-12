"""Tower (film frames 1644-1917, 54.85-63.96 s), rebuilt in cell C9 (x 12000..16300, y 3200..9750, z -3000..5000),
sealed by a black shell. One continuous shot (moments/ncc.npy: no cut; the drop at 1655 is the iris opening):
  1644-1654  the camera in front of a closed iris (the whole frame flat grey 10)
  1655-1663  the iris opens as a cross (4 panels sliding apart diagonally, dark corners until 1663); the camera
             passes its plane at 1664.5 (1/H of the cross arms falls linearly to 0 there)
  1664-1700  slow straight tube (8.5 units per frame) toward the tower base: collars every 370 (first at 319)
  1700-1856  the camera bends up and rises beside the glass tower (up to 23 units per frame) looking at it
  1856-1917  it sinks again, past the dark ring band at 1886-1890
Camera: COLMAP run of out/tw/sfm (frames 1656-1930, 275 images, 0.86 px), aligned to the room lines at 1664-1690
(27 frames, spread 0.6 deg), scaled by the collars (offline/out/tw/tools/twsolve.py, twcam.py), mis-registered
frames dropped and interpolated; 1644-1655 extrapolated. COLMAP's world drifts in depth between the rising and
the sinking part: the rust walls are a height field of COLMAP's points
(each band where the camera of that time saw it), the tower's poles / bands are placed from the film's image
positions (out/tw/tools/poles.py, band traces). Ride coordinates: origin = camera 1664, room axes."""
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
    E.add_prop(c.v, 'models/corehub_intro/%s_iris_frame.mdl' % PFX, ctr, tube.frame_angles(F, L), name=PFX + '_iris_frame')
    for k in range(4):
        a = math.radians(90 * k); Lk = L * math.cos(a) + U * math.sin(a); Uk = np.cross(F, Lk)
        ang = tube.frame_angles(F, Lk); name = '%s_iris%d' % (PFX, k)
        E.add_prop(c.v, 'models/corehub_intro/%s_iris_panel.mdl' % PFX, ctr, ang, name=name)
        keys = [(t, ctr + (Lk + Uk) * g * IRIS_H, None) for t, g in IRIS_G]
        tracks.append(dict(name=name, keys=keys, t_on=54.0, t_off=ft(IRIS_FRAME) + 0.05))
    TM.save_iris(IRIS_H, IRIS_OUTER)


# ------------------------------------------------------------------------------------------------ tube
def rails_along(v, P, name, up0=(0, 0, 1.0), rho=34.0, width=1.8, step=6.0):
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
    E.add_prop(v, 'models/corehub_intro/%s.mdl' % name, org, (0, 0, 0), name=name)


# ------------------------------------------------------------------------------------------------ the room
TUBE_DIR = np.array([0.9894, 0.0969, -0.1082])     # the first tube's axis (camera 1660-1688, room coordinates)
TUBE_PT = np.array([81.7, 8.1, -9.0])
COLLARS_AX = [319.0, 689.0, 1059.0, 1429.0]         # collars along the tube (axial, from the cloud: first collar's
                                                    # inner rings at 319, the film's inner circles at 1664: 681, 1060, 1376)
TUBE_END_AX = 1900.0
TINTS = [0.55, 0.65, 0.75, 0.85, 0.95, 1.05, 1.15, 1.25]


def tube_axis(a): return TUBE_PT + TUBE_DIR * (a - TUBE_PT @ TUBE_DIR)


def backdrop(c, rd):
    """rust walls as a height field from the cloud (see offline/out/tw/tools/twsolve.py: backdrop)"""
    B = rd.raw['backdrop']; ys, zs = B['ystep'], B['zstep']
    mats = [TM.bmat('%s_rust%d' % (PFX, i), (t, t, t), base='corehub_intro/%s_rust' % PFX) for i, t in enumerate(TINTS)]
    su = TM.PANEL_W * TM.TEX_PANELS[0] / TM.TEX
    for y0, z0, x, g in B['cells']:
        t = (g / 85.0) ** 0.6; i = int(np.argmin([abs(math.log(max(t, 0.05) / q)) for q in TINTS]))
        c.box((x, y0, z0), (x + 60.0, y0 + ys, z0 + zs), mats[i], su=su, sv=su)          # (deeper boxes to fill the gaps scored lower)


# the glass tower (rising part, z > 600): axis, poles and bands from the film's images at the camera of that time
# (poles at 195 / 395 px, band A at the horizon 1844-1856 = camera z 2160, band B 22.6 deg above it at 1856, band
# spans 330 px at 1820); band heights fitted to the film's dark-row traces with the front edge at x 1500 (A 2055 /
# 2189, B 2568 / 2610 rising / sinking; a band at the horizon at 1812-1820 -> 1650); the bands the camera passes
# close by while sinking (1886-1890, 1912-1917) reach close to its path (COLMAP's sinking path drifts ~450 away
# from the tower relative to the rising one), shown only while it sinks
TOWER = dict(x=1800.0, y=200.0, pole_r=254.0, pole_w=60.0, pole_z0=900.0, pole_z1=3400.0,
             band_ri=270.0, band_t=70.0, bands=[(1650.0, 330.0), (2120.0, 330.0), (2590.0, 330.0), (3060.0, 330.0), (1800.0, 630.0), (1180.0, 820.0)],
             col_r=150.0, col_z0=900.0, col_z1=3400.0, col_tint=0.75, disc_r0=0.0, disc_r1=310.0, disc_t=30.0, disc_z=330.0)
BASE = dict(x=2060.0, y=230.0)            # the tower's base (1664-1730: column x ~1984, platform rim z ~300 at x ~2170)


DESCENT_T = 62.15          # frame 1863: the camera has turned from rising to sinking


def tower(c, tracks):
    """the glass tower: rust column, two black poles at its sides (as seen from the camera), dark octagonal ring
    bands, the base disc"""
    T = TOWER; M = TM.brush_materials(); o = np.asarray(ORIGIN)
    TM.save_tower(T)
    ax = np.array([T['x'], T['y'], 0.0])
    E.add_prop(c.v, 'models/corehub_intro/%s_column.mdl' % PFX, o + ax, (0, 0, 0), name=PFX + '_column')
    for k, (z, ro) in enumerate(T['bands']):
        name = '%s_band%d' % (PFX, k)
        E.add_prop(c.v, 'models/corehub_intro/%s_band%d.mdl' % (PFX, k), o + ax + (0, 0, z), (0, 22.5, 0), name=name)
        if ro > 600:          # the bands the sinking camera passes close by (1884-1917): only while it sinks
            tracks.append(dict(name=name, keys=[(62.0, o + ax + (0, 0, z), None)], t_on=DESCENT_T, t_off=70.0))
    w = T['pole_w'] / 2
    for dy in (T['pole_r'], -T['pole_r']):
        c.box((T['x'] - w, T['y'] + dy - w, T['pole_z0']), (T['x'] + w, T['y'] + dy + w, T['pole_z1']), M['black'])
    # the base (seen 1655-1760 from the tube): platform disc, column, two poles (1664: 250 / 352 px -> y 418 / -28)
    E.add_prop(c.v, 'models/corehub_intro/%s_disc.mdl' % PFX, o + (2100.0, 150.0, T['disc_z']), (0, 0, 0), name=PFX + '_disc')
    E.add_prop(c.v, 'models/corehub_intro/%s_column.mdl' % PFX, o + (BASE['x'], BASE['y'], 330.0 - T['col_z0']), (0, 0, 0), name=PFX + '_column_base')
    for y in (418.0, -28.0):
        c.box((1990.0, y - 30.0, 330.0), (2050.0, y + 30.0, 905.0), M['black'])
    # horizontal pipes across the view (1664: rows 222 / 245 px), with the flanges' darker rings left out
    for z in (-89.0, -163.0):
        E.add_prop(c.v, 'models/corehub_intro/%s_pipe.mdl' % PFX, o + (1500.0, 0.0, z), (0, 90, 0), name='%s_pipe%d' % (PFX, int(-z)))
    TM.save_pipe(2600.0, 7.0)


def room(c, rd):
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
    c.box((1300.0, 380.0, 1250.0), (1340.0, 1400.0, 3400.0), M['grey_dim'])
    c.box((1300.0, 380.0, 1000.0), (1340.0, 1400.0, 1250.0), M['wall_dim'], su=1.0)


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
    rails_along(v, P, PFX + '_rails')
    for k, a in enumerate(COLLARS_AX):
        E.add_prop(v, 'models/corehub_intro/%s_collar.mdl' % PFX, o + tube_axis(a), tube.axis_angles(TUBE_DIR), name='%s_collar%d' % (PFX, k))
    # the tube the camera rises in: bends up from the first tube at ~1700 (the film's rails converge below the
    # frame 1736-1800: the vertical tube's rails under the camera), a collar passed at ~1752
    fr = np.arange(1696.0, 1857.0, 1.0)
    Pr = np.array([rd.pos(n) for n in fr])
    Pr = np.vstack([o + tube_axis(float((Pr[0] - o) @ TUBE_DIR) - 300.0), Pr])
    # rails_along(v, Pr, PFX + '_rails_up', up0=(-1.0, 0.0, 0.0))   # tried: scores lower (orientation unmeasured)
    for k, n in enumerate(()):          # (a collar passed at 1757 did not score better)
        E.add_prop(v, 'models/corehub_intro/%s_collar.mdl' % PFX, rd.pos(n), (0, 0, 0), name='%s_collar_up%d' % (PFX, k))
    backdrop(c, rd)
    room(c, rd)
    tower(c, tracks)
    d.append(tracks_code(tracks))
    d.hook('Tw_Update(t);')
    # the base director's old fades in this range (iris, collar passes) are replaced by geometry: no screen black
    d.append('''function Tw_Fade(t) {
    if(t>=%.4f && t<%.4f) SetScreenBlack(0);
}''' % (ft(1644) - 0.001, ft(1917) + 1 / 60.0 + 0.002))
    d.hook('Tw_Fade(t);', late=True)
    shell(v, np.array(CELL[0]) + 40, np.array(CELL[1]) - 40)
