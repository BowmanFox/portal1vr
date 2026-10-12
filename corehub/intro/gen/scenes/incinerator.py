"""Incinerator (film frames 3293-3547, 109.88-118.35 s), rebuilt in cell C7 at the measured camera.

ONE continuous shot (no hard cut; the similarity drop at 3518 is the camera passing the wall iris):
  3293-3333  straight tube along +x toward a rust wall (iris in it), white disc + turret far beyond   (ride ic_a)
  3333-3360  the camera passes the wall iris and pitches down 90 deg over the incinerator              (ic_a + COLMAP 1)
  3360-3486  down the shaft: collars, rails, orange bowl, burnt funnel and fire; camera rolls and bobs (COLMAP 1)
  3486-3516  pitch back up, approach the iris in the orange wall                                        (interpolated)
  3516-3547  straight tube along +x to a rust end wall with a black mouth                                (COLMAP 0)
The camera track is data/ic_cam_ride.json, written by offline/out/ic/tools/build_cam.py from the measurements (ride
ic_a = ride_export of 3293-3351; COLMAP models 0 and 1 of sfm/incin rotated to the room axes; model 1 scaled by
S1 = 139 (free: the picture does not depend on it; the shaft rails, 0.25-0.35 from the axis in model 1, come out near
34), model 0 by S0 = 148.5 (ic_a's collar-measured speed against model 0's steps).
Geometry is placed relative to it. Cell C7: x -2000..5000, y 9850..16300, z -3000..5000, sealed by a black shell.
Animated props (iris petals, the falling turret, debris, glow, laser beams, scan cones, the optical head) are moved by
my own Squirrel function IC_Update(t) (Director.append + hook); the old incinerator's entities stay unused.
Round 3: own unlit turret / open turret / cubes / cans / dark debris (the stock ones render black in the game), every
model that does not move is a prop_static, hidden props are parked inside the shell at (-1900, 13000, 0), the base
fades of this range are re-fitted for the game's gamma-space fades (FADE_KEYS, FADE_IN_KEYS)."""
import json, math, os
import numpy as np
from lib import vmfedit as E
from lib.gen import Mesh, V, save, rot_x, rot_y, rot_z
from lib.mesh import angle_matrix
from models import incinerator as M
from models.tubekit import materials as tk_materials

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
O = np.array([-1700.0, 13000.0, 2500.0])          # cell origin = camera at frame 3293 (+ the ride's lead-in)
RUST = 'corehub_intro/r11_ic_rust'
BLACK = 'corehub_intro/void_black'
DARK = 'corehub_intro/r11_ic_dark'
ORANGE_DK = 'corehub_intro/r11_ic_orange_dk'
ORANGE = 'corehub_intro/r11_ic_orange'
RAIL_MAT = 'corehub_intro/p9_ascent_rail_v2'
COLLAR_MDL = 'models/corehub_intro/r11_ic_tcollar.mdl'          # own 12-sided collar, axis model +X
PFX = 'r11_ic'
RAIL_TURN = 45.0                                   # shaft rails: measured cluster angles + this (checked on the film)
RIM_DX = float(os.environ.get('IC_RIMDX', 75.0))     # the opening's rim behind the rust wall: radial profiles of 110.75 / 110.85
                                                     # agree only with it 75 beyond x 1474 (light band R 109-126, dark 88-109)
PD_SHIFT = float(os.environ.get('IC_PDSHIFT', 60.0))  # exit iris + its wall moved along +x: the film's camera passes it at 3517-3518,
                                                     # the track at 117.32 (and the iris looked 1.4 x too big at 117.15)
RUST_K = float(os.environ.get('IC_RUSTK', 1.0))    # rust walls: map units per texel of the rust texture
FAN_A = float(os.environ.get('IC_FANA', 0.0))
RED_R = float(os.environ.get('IC_REDR', 0.09))       # red laser cones: end radius / S1 (was 0.09: too narrow)
FAN_R = float(os.environ.get('IC_FANR', 0.55))      # pale scan fans: end radius / S1, length / S1, outward lean, alpha
FAN_L = float(os.environ.get('IC_FANL', 1.9))
FAN_OUT = float(os.environ.get('IC_FANO', 0.9))
FAN_T = (111.85, 113.75)
TOP_POS = np.array([-40.0, 0.0, 320.0])            # own turret held above the white disc (relative to the disc centre;
TOP_ANG = (0.0, 180.0, 0.0)                        # film 3330: white body z 198-366, 70 wide at x 2460)
# base darkening fades 111.35-114.12 (black screen fade, alpha 0-255). The old alphas were tuned on the linear-light
# preview; the game draws fades in gamma space: a_gamma = 255 (1 - (1 - a_lin / 255) ** (1 / 2.2)), then re-fitted
# against the film's mean brightness (alpha = 255 (1 - film / unfaded)).
OLD_FADES = ('[111.35,111.5,0,60],[111.5,111.7,60,95],[111.7,111.85,95,115],[111.85,112.05,115,65],[112.05,112.95,65,50],'
             '[112.95,113.15,50,5],[113.15,113.35,5,20],[113.35,113.55,20,58],[113.55,113.95,58,38],[113.95,114.12,38,0]')
# re-fitted by score on the gamma-space preview (offline/out/ic/r3/fadefit.py: the unfaded picture x (1 - a / 255) against
# the film, best ssim + tone per time; 111.4-111.9 the film is darker than ours where our turret / walls are lit)
FADE_KEYS = [(111.35, 0), (111.5, 50), (111.6, 80), (111.7, 100), (111.85, 115), (112.0, 80), (112.15, 55), (112.3, 50),
             (112.5, 45), (112.7, 55), (112.9, 30), (113.1, 10), (113.3, 20), (113.5, 25), (113.7, 12), (113.9, 15),
             (114.05, 8), (114.12, 0)]
OLD_FADE_IN = '[109.8428,110.6,255,0]'
# the fade-in from black: alpha = 255 (1 - film / unfaded) from the mean brightness (film 7.5 / 16.6 / 27.1 / 35.4 / 49.6
# at 109.9 / 110.0 / 110.1 / 110.25 / 110.4 against unfaded 55-74; the old ramp to 110.6 left the game 4-7 levels dark)
FADE_IN_KEYS = [(109.8428, 255), (109.9, 238), (110.0, 186), (110.1, 160), (110.25, 90), (110.4, 25), (110.47, 0)]


def fade_table(keys):
    return ','.join('[%.4f,%.4f,%d,%d]' % (ta, tb, aa, ab) for (ta, aa), (tb, ab) in zip(keys, keys[1:]))


def frame_time(n): return n * 1001 / 30000.0


def shell(v, lo, hi, mat=BLACK, t=32.0):
    lo = np.asarray(lo, dtype=float); hi = np.asarray(hi, dtype=float)
    for ax in range(3):
        for side in (0, 1):
            a = lo.copy() - t; b = hi.copy() + t
            if side == 0: b[ax] = lo[ax]
            else: a[ax] = hi[ax]
            E.add_box(v, a, b, mat)


def _scale(prism, k):
    for side in (prism.east, prism.west, prism.north, prism.south, prism.top, prism.bottom):
        side.uaxis.scale = k; side.vaxis.scale = k


def box(v, lo, hi, mat, ent=None, k=None):
    """E.add_box with the texture scale k (map units per texel) on every face (the rust tiles are 512 texels)"""
    p = E.add_box(v, lo, hi, mat, ent=ent)
    if k is not None: _scale(p, k)
    return p


def wall_with_hole(v, ent, x, cam_side, c, half, hole, mat, t=32.0, hole_c=None, hole_r=None):
    """plane x = x (faces toward cam_side), centred at c (y, z), half extents (hy, hz), square hole of half size `hole`
    (or an octagonal hole of inradius hole_r centred at hole_c)"""
    y0, z0 = c; hy, hz = half
    xa, xb = (x - t, x) if cam_side > 0 else (x, x + t)
    if hole_r:
        yc, zc = hole_c; h = hole_r; q = h * math.tan(math.radians(22.5))
        box(v, (xa, y0 - hy, z0 - hz), (xb, y0 + hy, zc - h), mat, ent=ent, k=RUST_K)
        box(v, (xa, y0 - hy, zc + h), (xb, y0 + hy, z0 + hz), mat, ent=ent, k=RUST_K)
        box(v, (xa, y0 - hy, zc - h), (xb, yc - h, zc + h), mat, ent=ent, k=RUST_K)
        box(v, (xa, yc + h, zc - h), (xb, y0 + hy, zc + h), mat, ent=ent, k=RUST_K)
        return
    if hole <= 0:
        box(v, (xa, y0 - hy, z0 - hz), (xb, y0 + hy, z0 + hz), mat, ent=ent, k=RUST_K); return
    box(v, (xa, y0 - hy, z0 - hz), (xb, y0 - hole, z0 + hz), mat, ent=ent, k=RUST_K)
    box(v, (xa, y0 + hole, z0 - hz), (xb, y0 + hy, z0 + hz), mat, ent=ent, k=RUST_K)
    box(v, (xa, y0 - hole, z0 - hz), (xb, y0 + hole, z0 - hole), mat, ent=ent, k=RUST_K)
    box(v, (xa, y0 - hole, z0 + hole), (xb, y0 + hole, z0 + hz), mat, ent=ent, k=RUST_K)


def _qangle_x(d):
    """prop angles that point a model's +X along d"""
    d = np.asarray(d, float); d = d / np.linalg.norm(d)
    return (-math.degrees(math.asin(max(-1, min(1, d[2])))), math.degrees(math.atan2(d[1], d[0])), 0.0)


def _frame_to(d):
    """rotation matrix taking +X to direction d"""
    d = np.asarray(d, float); d = d / np.linalg.norm(d)
    a = np.array([0, 0, 1.0]) if abs(d[2]) < 0.9 else np.array([1.0, 0, 0])
    y = np.cross(a, d); y /= np.linalg.norm(y); z = np.cross(d, y)
    return np.array([d, y, z]).T


def squirrel_tracks(tracks):
    """Squirrel: a table of keyed props and IC_Update(t) that moves them (linear between keys; angles if given;
    hidden below the cell outside [t_on, t_off])"""
    rows = []
    for tr in tracks:
        ks = []
        for t, p, a in tr['keys']:
            a = a if a is not None else (0, 0, 0)
            ks.append('[%.4f,Vector(%.2f,%.2f,%.2f),Vector(%.2f,%.2f,%.2f),%d]' % (t, p[0], p[1], p[2], a[0], a[1], a[2], 0 if tr['keys'][0][2] is None else 1))
        rows.append('{name="%s",on=%.3f,off=%.3f,sm=%d,k=[%s]}' % (tr['name'], tr.get('t_on', -1.0), tr.get('t_off', 1e6), 1 if tr.get('smooth') else 0, ','.join(ks)))
    return ('icTracks <- [\n' + ',\n'.join(rows) + '];\n' + IC_CODE)


IC_CODE = '''function IC_Update(t) {
    if(t<109.5||t>118.6)return;
    foreach(tr in icTracks){
        local e=Entities.FindByName(null,tr.name); if(e==null)continue;
        if(t<tr.on||t>tr.off){e.SetOrigin(Vector(-1900,13000,0));continue;}
        local k=tr.k; local n=k.len(); local a=k[0]; local b=k[0]; local f=0.0;
        if(t<=k[0][0]){a=k[0];b=k[0];}
        else if(t>=k[n-1][0]){a=k[n-1];b=k[n-1];}
        else {for(local i=0;i<n-1;i++)if(t>=k[i][0]&&t<=k[i+1][0]){a=k[i];b=k[i+1];f=(t-a[0])/(b[0]-a[0]);break;}}
        if(tr.sm==1)f=f*f*(3-2*f);
        e.SetOrigin(a[1]+(b[1]-a[1])*f);
        if(a[3]==1){local g=a[2]+(b[2]-a[2])*f;e.__KeyValueFromString("angles",g.x+" "+g.y+" "+g.z);}
    }
}
'''


def unwrap_keys(keys):
    """keep keyed angles continuous (no 360 jumps between keys: IC_Update interpolates them linearly)"""
    out = []; prev = None
    for t, p, a in keys:
        a = [float(x) for x in a]
        if prev is not None:
            for k in range(3):
                while a[k] - prev[k] > 180: a[k] -= 360
                while a[k] - prev[k] < -180: a[k] += 360
        prev = a; out.append((t, p, tuple(a)))
    return out


def rails_x(v, ent, x0, x1, y, z, rho=34.0, w=1.8):
    for sy in (1, -1):
        for sz in (1, -1):
            cy = y + sy * rho / math.sqrt(2); cz = z + sz * rho / math.sqrt(2)
            E.add_box(v, (x0, cy - w / 2, cz - w / 2), (x1, cy + w / 2, cz + w / 2), RAIL_MAT, ent=ent)


def apply(v, d):
    cam = json.load(open(os.path.join(HERE, 'data', 'ic_cam_ride.json')))
    S1 = cam['S1']; K = {k: np.array(p) for k, p in cam['keys'].items()}
    K['PD'] = K['PD'] + np.array([PD_SHIFT, 0.0, 0.0])
    samples = []
    for m in cam['moments']:
        t = m[0]; p = np.array(m[3:6]) + O; f = np.array(m[6:9]); u = np.array(m[9:12])
        from lib.ride import qangle
        samples.append((t, tuple(float(x) for x in p), qangle(f, u)))
    d.override_camera(samples, fov=60.0)
    d.replace(OLD_FADES, fade_table(FADE_KEYS))
    d.replace(OLD_FADE_IN, fade_table(FADE_IN_KEYS))
    # (the base director's screen fades in this range stay: the film's shaft is darker and greyer than its orange walls
    #  where the pale scan fans cross it, and those fades bring the luminance to the film's: checked with the mean colours)
    M.materials(); tk_materials()
    det = v.create_ent(classname='func_detail')
    P = np.array([m[3:6] for m in cam['moments']]) + O

    # ------------------------------------------------------------ seg 1: tube along +x through the rust wall
    XW = 1474.0                                   # rust wall with an opening (ride ic_a plane x = 1474; ride points start at r ~120)
    XP = 1850.0                                   # iris petals (film: closed disc at 3324, open 3326-3330, out of view from 3338)
    XDISC = 2500.0                                # white disc (radius 74) with the turret above it
    XF = 3300.0                                   # far rust wall (ride ic_a points beyond the opening, median 3278)
    rails_x(v, det, O[0] - 250, O[0] + XP, O[1], O[2])
    for k, x in enumerate((455.0, 1216.0)):          # collars: passed at 3303 (film) and Hough of the film (x 1216, R 74)
        E.add_prop(v, COLLAR_MDL.replace('tcollar', 'tcollar_b'), (O[0] + x, O[1], O[2]), (0, 0, 0), cls='prop_static')
    wall_with_hole(v, det, O[0] + XW, -1, (O[1], O[2] - 600), (2600, 2200), 0.0, RUST, hole_c=(O[1], O[2]), hole_r=118.0)
    E.add_prop(v, 'models/corehub_intro/r11_ic_rim.mdl', (O[0] + XW + RIM_DX, O[1], O[2]), (0, 0, 0), cls='prop_static')
    wall_with_hole(v, det, O[0] + XF, -1, (O[1], O[2] + 300), (2600, 1200), 0, RUST)
    E.add_prop(v, 'models/corehub_intro/r11_ic_disc.mdl', (O[0] + XDISC - 2, O[1], O[2]), (0, 0, 0), cls='prop_static')
    box(v, (O[0] + XDISC, O[1] - 90, O[2] - 90), (O[0] + XF, O[1] + 90, O[2] + 90), RUST, ent=det, k=RUST_K)
    E.add_prop(v, 'models/corehub_intro/r11_ic_turret_top.mdl', TOP_POS + np.array([O[0] + XDISC, O[1], O[2]]), TOP_ANG, cls='prop_static')
    for sy in (-1, 1):                            # dark pillars in front of the far wall (film 3332: bands at +-173 px, 51 px wide)
        box(v, (O[0] + XDISC - 60, O[1] + sy * 320 - 48, O[2] - 890), (O[0] + XDISC, O[1] + sy * 320 + 48, O[2] + 1500), DARK, ent=det)

    # ------------------------------------------------------------ shaft
    sh = cam['shaft']; axy = np.array(sh['axis_xy']) + O[:2]; z0 = sh['z0'] + O[2]
    zmap = lambda zz: z0 - S1 * zz
    parts = Mesh(); beams = Mesh(); fans = Mesh()
    # rings measured on the film (radial brightness about the shaft's vanishing point over 127 frames, Hough over depth
    # Z and radius R in COLMAP model-1 units, x S1 = map units; tools in offline/out/ic/tools/ringhough.py):
    #   collars: light band 0.69-0.86 (the top one 0.76-0.86), dark edge, at Z -3.80 / -0.82 / 1.92 (down the shaft)
    #   scanner stations (white probe points of the COLMAP cloud, 0.37-0.76 from the axis) at Z -4.90 / -2.45 / -0.10
    #   funnel mouth: light band 0.77-0.86 at Z 4.66, the burnt funnel below it (cloud: 0.69 -> 0.31 from Z 4.6 to 5.2)
    parts.add(M.band_ring(0.76 * S1, 0.86 * S1, edge=0.72 * S1), offset=(0, 0, zmap(-3.80) - z0))     # Hough: light 0.76-0.85, dark 0.73
    parts.add(M.band_ring(0.62 * S1, 0.72 * S1, mat_band='r11_ic_midgrey'), offset=(0, 0, zmap(-3.80) - z0 - 1))
    parts.add(M.band_ring(0.69 * S1, 0.86 * S1, edge=0.65 * S1), offset=(0, 0, zmap(-0.82) - z0))
    low = M.band_ring(0.69 * S1, 0.86 * S1, edge=0.65 * S1)          # the lowest collar (Z 1.92) is its own prop: the film
    save(low, '%s_lowcollar' % PFX)                                   # does not show it once the camera looks up (116.45+)
    E.add_prop(v, 'models/corehub_intro/%s_lowcollar.mdl' % PFX, (axy[0], axy[1], zmap(1.92)), (0, 0, 0), name='%s_lowcollar' % PFX)
    for zz in (-4.90, -2.45, -0.10):
        parts.add(M.band_ring(0.50 * S1, 0.55 * S1, mat_band='r11_ic_darkgrey'), offset=(0, 0, zmap(zz) - z0))   # thin mount ring (the film shows no light band here)
        for k in range(4):
            cs, sn = math.cos(math.radians(90 * k)), math.sin(math.radians(90 * k)); zl = zmap(zz) - z0 + 12
            parts.add(M.probe(0.39 * S1, 0.045 * S1), R=rot_z(90 * k + 180), offset=(cs * 0.76 * S1, sn * 0.76 * S1, zl))
            parts.tube((cs * 0.86 * S1, sn * 0.86 * S1, zl), (cs * 2.6 * S1, sn * 2.6 * S1, zl), 0.028 * S1, 'r11_ic_pipe', n=8, caps=False)
            # red scan beam from the probe tip up toward the camera (film 3355-3392), slightly outward
            tip = np.array([cs * 0.37 * S1, sn * 0.37 * S1, zl]); top = tip + np.array([cs * 0.25 * S1, sn * 0.25 * S1, 1.7 * S1])
            beams.add(M.cone(float(np.linalg.norm(top - tip)), 1.0, RED_R * S1, 'r11_ic_red'), R=_frame_to(top - tip), offset=tip)
            # pale scan fans from every probe tip, up toward the camera and outward (film 3354-3410: wide grey wedges
            # from near the centre to the frame edges)
            dfan = np.array([cs * FAN_OUT, sn * FAN_OUT, 1.0]); dfan = dfan / np.linalg.norm(dfan)
            fans.add(M.cone(FAN_L * S1, 2.0, FAN_R * S1, 'r11_ic_fan'), R=_frame_to(dfan), offset=tip)
    parts.add(M.band_ring(0.77 * S1, 0.86 * S1, edge=0.69 * S1), offset=(0, 0, zmap(4.66) - z0 + 2))
    parts.add(M.funnel(0.69 * S1, 0.31 * S1, 0.6 * S1), offset=(0, 0, zmap(4.66) - z0))
    parts.add(M.bowl([(zmap(4.66) - z0, 0.86 * S1), (zmap(3.75) - z0, 2.4 * S1), (zmap(1.0) - z0, 3.6 * S1), (zmap(-1.5) - z0, 6.0 * S1)]))
    parts.add(M.bowl([(zmap(-1.5) - z0, 6.0 * S1), (O[2] - 890 - z0, 6.0 * S1)]), mat='r11_ic_darkwall')
    PDm = K['PD'] + O
    xcut = PDm[0] - axy[0] + 2.0                     # nothing of the shaft beyond the wall of the exit iris
    parts.tris = [t for t in parts.tris if (t.p[0][0] + t.p[1][0] + t.p[2][0]) / 3.0 < xcut]
    save(parts, '%s_shaft' % PFX)
    save(beams, '%s_beams' % PFX)
    if FAN_A > 0:          # (pale fans at alpha 0.2 from every probe scored lower in 111.9-113.65: ssim 0.40 / tone 0.59 against 0.44 / 0.68)
        save(fans, '%s_fans' % PFX)
        E.add_prop(v, 'models/corehub_intro/%s_fans.mdl' % PFX, (axy[0], axy[1], z0), (0, 0, 0), name='%s_fans' % PFX)
    E.add_prop(v, 'models/corehub_intro/%s_beams.mdl' % PFX, (axy[0], axy[1], z0), (0, 0, 0), name='%s_beams' % PFX)
    E.add_prop(v, 'models/corehub_intro/%s_shaft.mdl' % PFX, (axy[0], axy[1], z0), (0, 0, 0), cls='prop_static')
    # shaft rails (measured angles, not on the map diagonals)
    rm = Mesh(); top = zmap(-7.5) - z0; bot = zmap(4.5) - z0
    for ang in sh['rails_deg']:
        a = math.radians(ang + RAIL_TURN); c = np.array([math.cos(a), math.sin(a), 0.0]) * 34.0
        w = 0.9; tdir = np.array([-math.sin(a), math.cos(a), 0.0])
        rm.obox((c[0], c[1], (top + bot) / 2), (w, w, (top - bot) / 2), np.array([c / 34.0, tdir, [0, 0, 1.0]]).T, 'r11_rail')
    save(rm, '%s_shaft_rails' % PFX)
    E.add_prop(v, 'models/corehub_intro/%s_shaft_rails.mdl' % PFX, (axy[0], axy[1], z0), (0, 0, 0), cls='prop_static')
    # the incinerator room: orange walls round the bowl, a dark ceiling above
    R_room = 1600.0
    PD = K['PD'] + O
    zr0 = zmap(5.6); zr1 = zmap(-1.5)
    x_lo = O[0] + XW; x_hi = PD[0]
    E.add_box(v, (x_lo, axy[1] - R_room, zr0 - 32), (x_hi, axy[1] + R_room, zr0), ORANGE, ent=det)        # floor
    for sy in (-1, 1):
        ya = axy[1] + sy * R_room
        E.add_box(v, (x_lo, min(ya, ya + sy * 32), zr0), (O[0] + XF, max(ya, ya + sy * 32), zr1), ORANGE, ent=det)
    # the side of the bowl the camera exits through (iris at PD), up to the bowl's rim
    wall_with_hole(v, det, PD[0], -1, (PD[1], (zr0 + zr1) / 2), (R_room, (zr1 - zr0) / 2), 0.0, ORANGE_DK, hole_c=(PD[1], PD[2]), hole_r=70.0)   # film 3500: (97 52 39)
    # far wall continues down past the bowl rim (111.5-111.8 the camera looked under it into the black shell; the film shows
    # the rust wall continuing below the shaft's dark rim)
    # (with an opening of half size 400 round the final tube, which passes x XF at the height of the exit iris: its edges
    #  stay outside the picture once the camera is within ~580 of it)
    xa, xb = O[0] + XF, O[0] + XF + 32; hw = 400.0
    box(v, (xa, O[1] - 2600, PD[2] + hw), (xb, O[1] + 2600, O[2] - 900), RUST, ent=det, k=RUST_K)
    box(v, (xa, O[1] - 2600, zr0 - 560), (xb, O[1] + 2600, PD[2] - hw), RUST, ent=det, k=RUST_K)
    box(v, (xa, O[1] - 2600, PD[2] - hw), (xb, PD[1] - hw, PD[2] + hw), RUST, ent=det, k=RUST_K)
    box(v, (xa, PD[1] + hw, PD[2] - hw), (xb, O[1] + 2600, PD[2] + hw), RUST, ent=det, k=RUST_K)

    # ------------------------------------------------------------ seg 4-5: the wall iris and the final tube
    t5 = [m[0] for m in cam['moments']]
    XE = float(np.interp(frame_time(3547.5), t5, P[:, 0]))                 # end wall: the film's black mouth (r 60) is 478 ahead at 3541
    rails_x(v, det, PD[0] - 10, XE, PD[1], PD[2])
    for k, x in enumerate((2762.0, 3027.0, 3347.0, 3592.0)):    # collars (Hough of the film, frames 3517-3546; none visible at 3541 but the mouth)
        E.add_prop(v, COLLAR_MDL, (O[0] + x, PD[1], PD[2]), (0, 0, 0), cls='prop_static')
    wall_with_hole(v, det, XE, -1, (PD[1], PD[2]), (2200, 1500), 0.0, RUST, hole_c=(PD[1], PD[2]), hole_r=60.0)
    E.add_prop(v, COLLAR_MDL.replace('tcollar', 'tcollar_m'), (XE - 1, PD[1], PD[2]), (0, 0, 0), cls='prop_static')   # black mouth r ~58 (film 3541-3546)
    E.add_box(v, (XE + 32, PD[1] - 160, PD[2] - 160), (XE + 400, PD[1] + 160, PD[2] + 160), BLACK, ent=det)

    # ------------------------------------------------------------ animated props (own hook: IC_Update)
    tracks = []

    def petals(tag, mdl, c, t0, t1, dmax):
        for i in range(4):
            Mr = angle_matrix(0, 0, i * 90); dirv = Mr @ np.array([0.0, math.cos(math.radians(45)), math.sin(math.radians(45))])
            nm = '%s_%s_petal%d' % (PFX, tag, i)
            E.add_prop(v, 'models/corehub_intro/%s.mdl' % mdl, c, (0, 0, i * 90), name=nm)
            tracks.append(dict(name=nm, keys=[(t0, c, None), (t1, c + dirv * dmax, None)], smooth=True))
    petals('w1', 'r11_ic_petal_s', np.array([O[0] + XP, O[1], O[2]]), 110.90, 111.06, 27.0)
    E.add_prop(v, 'models/corehub_intro/r11_ic_frame_s.mdl', (O[0] + XP - 3, O[1], O[2]), (0, 0, 0), cls='prop_static')
    petals('w2', 'r11_ic_petal', np.array([PD[0] - 4, PD[1], PD[2]]), 117.10, 117.38, 46.0)     # (film: 3511 starts, 3515 ~55 %, 3517 open)
    E.add_prop(v, 'models/corehub_intro/ending_iris_frame.mdl', (PD[0] - 7, PD[1], PD[2]), (0, 0, 0), cls='prop_static')

    from lib.ride import qangle
    tm = np.array([m[0] for m in cam['moments']]); Fw = np.array([m[6:9] for m in cam['moments']]); Up = np.array([m[9:12] for m in cam['moments']])

    def rel(t, dist, up=0.0, right=0.0):
        """a point `dist` ahead of the film camera at time t, shifted up / right in the picture"""
        i = int(np.clip(np.searchsorted(tm, t), 0, len(tm) - 1))
        f = Fw[i]; u = Up[i]; r = np.cross(f, u)
        return P[i] + f * dist + u * up * dist + r * right * dist

    # the turret the camera follows out of the tube and down the shaft (film 3340-3420): ahead of the camera, tumbling
    # film-measured picture position (x, y of 640 x 400) and size of the falling turret (3339-3368): distance = f * L / size
    # for the own model (L = 71.5 * TURRET_K); pose: its back to the camera, its top toward the picture's top, tumbling
    tk = [(111.38, 412, 360, 50, 0), (111.48, 110, 307, 112, 25), (111.58, 70, 312, 260, 10), (111.68, 120, 297, 330, 0),
          (111.78, 150, 282, 320, -8), (111.88, 270, 285, 230, -20), (112.13, 330, 300, 160, -40), (112.30, 380, 315, 200, -55)]
    keys = []
    for t, dd, x, y, roll in tk:
        i = int(np.clip(np.searchsorted(tm, t), 0, len(tm) - 1)); pa = qangle(-Fw[i], Up[i])
        # (sizes measured on the own model at k 0.5 came out 2.7 x too small in the picture: distances / 2.7 at k 1;
        #  the model's visual centre lies 15 k below its origin: lift the origin by that along the picture's up)
        keys.append((t, rel(t, dd * M.TURRET_K / 0.5 / 2.7, (200.0 - y) / 461.88, (x - 320.0) / 461.88) + Up[i] * 15.0 * M.TURRET_K,
                     (pa[0], pa[1], pa[2] + roll)))
    keys.append((113.6, np.array([axy[0] + 10, axy[1] + 12, zmap(4.4)]), (keys[-1][2][0] + 40, keys[-1][2][1] + 60, keys[-1][2][2] - 80)))
    keys = unwrap_keys(keys)
    E.add_prop(v, 'models/corehub_intro/r11_ic_turret_open.mdl', keys[0][1], keys[0][2], name='%s_turret' % PFX)   # (film: panels spread)
    tracks.append(dict(name='%s_turret' % PFX, keys=keys, t_on=111.38, t_off=113.6))
    # the turret again, wings spread, tumbling near the camera in the funnel (film 3432-3462: picture x, y, size of the
    # longest extent; own model ~60 long -> distance = f * 60 / size)
    tk2 = [(114.45, 300, 333, 215, 0), (114.53, 277, 333, 208, 10), (114.66, 208, 360, 192, 25), (114.79, 166, 370, 183, 45),
           (114.93, 151, 347, 142, 70), (115.06, 119, 300, 142, 95), (115.19, 151, 268, 142, 120), (115.32, 370, 295, 192, 150),
           (115.52, 520, 330, 230, 180), (115.70, 700, 340, 250, 200)]
    keys2 = []
    for t, dd, x, y, roll in tk2:
        i = int(np.clip(np.searchsorted(tm, t), 0, len(tm) - 1)); pa = qangle(-Fw[i], Up[i])
        keys2.append((t, rel(t, dd, (200.0 - y) / 461.88, (x - 320.0) / 461.88) + Up[i] * 12.0, (pa[0] + 30, pa[1], pa[2] + roll)))
    keys2 = unwrap_keys(keys2)
    E.add_prop(v, 'models/corehub_intro/r11_ic_turret_open.mdl', keys2[0][1], keys2[0][2], name='%s_turret2' % PFX)
    tracks.append(dict(name='%s_turret2' % PFX, keys=keys2, t_on=114.45, t_off=115.70))
    # the three yellow fans converging on it (film 3452-3490: apex fixed in the picture at (320, 142)): camera-attached
    fk = []
    for t in np.arange(115.30, 116.46, 0.05):
        i = int(np.clip(np.searchsorted(tm, t), 0, len(tm) - 1)); pa = qangle(Fw[i], Up[i])
        fk.append((float(t), rel(float(t), 80.0, (200.0 - 142.0) / 461.88, 0.0), pa))      # (at 300 the funnel walls clipped them)
    fk = unwrap_keys(fk)
    E.add_prop(v, 'models/corehub_intro/r11_ic_yfans.mdl', fk[0][1], fk[0][2], name='%s_yfans' % PFX)
    tracks.append(dict(name='%s_yfans' % PFX, keys=fk, t_on=115.33, t_off=116.42))
    # dark boxes and cans falling just ahead of the camera at the top of the shaft (film 3354-3384: picture x, y, size)
    def screen_track(name, mdl, L, samples, spin):
        ks = []
        for t, x, y, size in samples:
            ks.append((t, rel(t, 461.88 * L / size, (200.0 - y) / 461.88, (x - 320.0) / 461.88),
                       (t * spin[0] % 360, t * spin[1] % 360, t * spin[2] % 360)))
        ks = unwrap_keys(ks)
        E.add_prop(v, 'models/corehub_intro/%s.mdl' % mdl, ks[0][1], ks[0][2], name='%s_%s' % (PFX, name))
        tracks.append(dict(name='%s_%s' % (PFX, name), keys=ks, t_on=samples[0][0], t_off=samples[-1][0]))
    screen_track('dboxa', 'r11_ic_dbox', 44.0, [(111.86, 90, 175, 160), (111.90, 110, 160, 140), (112.13, 195, 115, 90),
                 (112.40, 195, 125, 75), (112.63, 160, 112, 85), (112.75, 150, 100, 90)], (40, 25, 15))
    screen_track('dcanb', 'r11_ic_dcan', 32.0, [(111.86, 550, 240, 100), (111.90, 535, 225, 90), (112.13, 460, 137, 50),
                 (112.40, 452, 172, 45), (112.63, 505, 115, 50), (112.75, 515, 105, 55)], (-30, 45, 20))
    screen_track('dballc', 'r11_ic_dcan', 32.0, [(112.30, 335, 140, 22), (112.40, 330, 145, 25), (112.63, 350, 140, 30),
                 (112.90, 340, 130, 40), (113.05, 345, 120, 45)], (20, 60, 35))
    # debris falling into the funnel ahead of the camera (film 3380-3480: cube, cans, a dark carton)
    deb = [('models/corehub_intro/r11_ic_cube_s.mdl', 112.3, 114.6, (-40, 25), 0.6),
           ('models/corehub_intro/r11_ic_can.mdl', 112.8, 115.4, (30, -20), 0.3),
           ('models/corehub_intro/r11_ic_can.mdl', 113.4, 116.2, (-15, -35), 0.2),
           ('models/corehub_intro/r11_ic_cube_s.mdl', 114.8, 116.6, (20, 10), 0.5)]
    for k, (mdl, ta, tb, (dx, dy), lead) in enumerate(deb):
        za = float(rel(ta, 400)[2]); zb = zmap(4.9)
        ka = (ta, np.array([axy[0] + dx, axy[1] + dy, za]), (ta * 61 % 360, ta * 47 % 360, 0)); kb = (tb, np.array([axy[0] + dx * 0.6, axy[1] + dy * 0.6, zb]), (tb * 61 % 360, tb * 47 % 360, 90))
        nm = '%s_debris%d' % (PFX, k)
        E.add_prop(v, mdl, ka[1], ka[2], name=nm)
        tracks.append(dict(name=nm, keys=[ka, kb], t_on=ta, t_off=tb))
    # the yellow glow (core light) that drops past the camera (film 3440-3475)
    gk = [(114.70, rel(114.70, 330, 0.05, -0.05), None), (115.00, rel(115.00, 170, -0.20, -0.12), None), (115.15, rel(115.15, 150, -0.45, -0.25), None)]
    E.add_prop(v, 'models/corehub_intro/r11_ic_glow.mdl', gk[0][1], (0, 0, 0), name='%s_glow' % PFX)
    tracks.append(dict(name='%s_glow' % PFX, keys=gk, t_on=114.70, t_off=115.15))
    tracks.append(dict(name='%s_beams' % PFX, keys=[(111.7, np.array([axy[0], axy[1], z0]), None)], t_on=111.70, t_off=113.35))
    if FAN_A > 0: tracks.append(dict(name='%s_fans' % PFX, keys=[(111.7, np.array([axy[0], axy[1], z0]), None)], t_on=FAN_T[0], t_off=FAN_T[1]))
    # the storage cube tumbling close to the camera, low right in the picture (film 3366-3392)
    ck = [(112.25, rel(112.25, 260, -0.281, 0.433), (10, 20, 30)), (112.40, rel(112.40, 200, -0.29, 0.346), (18, 30, 40)),
          (112.60, rel(112.60, 150, -0.368, 0.574), (28, 45, 55)), (112.90, rel(112.90, 140, -0.41, 0.52), (42, 64, 72)),
          (113.05, rel(113.05, 170, -0.48, 0.65), (55, 80, 90))]
    E.add_prop(v, 'models/corehub_intro/r11_ic_cube.mdl', ck[0][1], ck[0][2], name='%s_nearcube' % PFX)
    tracks.append(dict(name='%s_nearcube' % PFX, keys=ck, t_on=112.25, t_off=113.05))
    # (the three long yellow cones from beside the wall iris of round 2 are replaced by the camera-attached fans above)
    tracks.append(dict(name='%s_lowcollar' % PFX, keys=[(109.5, np.array([axy[0], axy[1], zmap(1.92)]), None)], t_on=109.5, t_off=116.45))
    # the lit head in front of the exit iris with its three yellow light lobes (film 3496-3516): it hangs in front of the
    # closed iris, then backs into the opening iris and rises out of the picture (3513: small in the centre, 3515: only
    # the lobes at the top edge, 3517 gone)
    # (film head width 140 / 110 / 80 px at 117.05 / 117.15 / 117.25 -> 257 / 330 / 450 from the camera; it comes down
    #  from above at 3500, hangs at the iris centre at 3504, then backs away through the opening and up)
    hk = [(116.72, (-35.0, 0.0, 160.0)), (116.85, (-35.0, 0.0, 8.0)), (117.05, (-10.0, 0.0, 40.0)), (117.15, (140.0, 0.0, 57.0)),
          (117.25, (350.0, 0.0, 136.0)), (117.33, (450.0, 0.0, 250.0))]
    hkeys = [(t, PD + np.array(p), None) for t, p in hk]
    for nm in ('head', 'lobes'):
        E.add_prop(v, 'models/corehub_intro/r11_ic_%s.mdl' % nm, hkeys[0][1], (0, 0, 0), name='%s_%s' % (PFX, nm))
        tracks.append(dict(name='%s_%s' % (PFX, nm), keys=hkeys, t_on=116.72, t_off=117.33, smooth=True))
    d.append(squirrel_tracks(tracks))
    d.hook('IC_Update(t);')

    # ------------------------------------------------------------ black shell round everything
    lo_all = np.minimum(P.min(axis=0), [O[0] - 600, axy[1] - R_room, zr0]) - 600
    hi_all = np.maximum(P.max(axis=0), [XE + 500, axy[1] + R_room, O[2] + 1200]) + 600
    lo_all = np.maximum(lo_all, [-2000 + 32, 9850 + 32, -3000 + 32]); hi_all = np.minimum(hi_all, [5000 - 32, 16300 - 32, 5000 - 32])   # shell inside C7
    shell(v, lo_all, hi_all)
