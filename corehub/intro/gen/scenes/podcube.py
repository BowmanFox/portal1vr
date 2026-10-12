"""Pod + cube (film frames 1178-1621, 39.3-54.1 s), rebuilt at film scale in cell C3 (x -2000..5000, y 3200..9750,
z -3000..5000). No hard cut in the range (moments/ncc.npy never below 0.6): one ride whose fast turns split the
COLMAP run 'pod'. The camera wobbles 1-7 degrees off the room axes everywhere, so ride_export's anchor check fails;
the cameras come from the COLMAP poses aligned to the room lines and scaled by the collars (offline/out/pc/pcsolve.py,
pcalign.py; measurements in its docstrings and in the report):
  shot A (1178-1462, data/pc_a_ride.json, origin ORIGIN_A): the glass tube along +x (collars every 350, camera 22.6
     units per frame; COLMAP block 1179-1311, room lines 26 samples, spread 0.9 deg), the tube's end ring and the bend
     through the room with the lit wall (COLMAP's frame-to-frame turn kept, its 22.6 deg drift spread over the bend),
     the ringed tube along +y (rings every ~120, 9.9 units per frame; COLMAP block 1314-1436 aligned on its own by
     35 line samples, spread 0.4 deg) to the junction with the white pod; 1437-1462 carried on with the feature-match
     gyro into the pale vertical tube (the film's flat pale view at 48.6-48.9 s);
  shot B (1463-1511, data/pc_b_ride.json, C's coordinates): from the pale sleeve down the dark ringed tube (synthesised:
     pitch from the gyro / the tube's vanishing point, speed assumed) and the fast bend into
  shot C (1512-1621, data/pc_c_ride.json, origin ORIGIN_C): the light ringed tube along +x (rings every ~112, 16.6
     units per frame; COLMAP model 1, aliased steps replaced by the median) where the cube comes toward the camera.
The tube axis is offset from the camera path where the film's rails say so (railfit_pc.py). Everything is placed
relative to the measured camera paths; each shot is sealed by its own shell."""
import math
import numpy as np
from lib import vmfedit as E, tube
from lib.gen import mat, save, V
from lib.ride import Ride

ORIGIN_A = (-1500.0, 3900.0, 0.0)
ORIGIN_C = (-1500.0, 8600.0, 2500.0)
BLACK = 'corehub_intro/void_black'
PFX = 'r11_pc'


def bmat(name, color):
    """brush material (UnlitGeneric flat colour) -> path"""
    mat(name, color, folder='corehub_intro', model=False)
    return 'corehub_intro/' + name


def shell(v, lo, hi, material=BLACK, t=32.0, mats=None):
    """hollow box sealing a shot (inside faces `material`; mats: {'+x': material of the face at hi.x, ...})"""
    lo = np.asarray(lo, dtype=float); hi = np.asarray(hi, dtype=float)
    for ax in range(3):
        for side in (0, 1):
            a = lo.copy() - t; b = hi.copy() + t
            if side == 0: b[ax] = lo[ax]
            else: a[ax] = hi[ax]
            key = ('+' if side else '-') + 'xyz'[ax]
            E.add_box(v, a, b, (mats or {}).get(key, material))


def cam_until(rd, t_end):
    """the shot's camera samples, the last pose held until t_end (so that consecutive shots leave no gap in which
    the old director camera would show)"""
    cam = rd.camera()
    if t_end is not None and t_end > cam[-1][0]: cam = cam + [(t_end, cam[-1][1], cam[-1][2])]
    return cam


def tnext(n): return n * 1001 / 30000.0 - 0.0004


def frames_uw(P, up0):
    """tangents and a twist-free cross-section frame (U, W) along a polyline"""
    T = np.gradient(P, axis=0); T /= np.linalg.norm(T, axis=1, keepdims=True) + 1e-12
    U = np.zeros_like(P); u = np.asarray(up0, dtype=float)
    for i in range(len(P)):
        u = u - T[i] * (u @ T[i]); u /= np.linalg.norm(u); U[i] = u
    return T, U, np.cross(T, U)


def rails_along(v, P, name, up0=(0, 0, 1.0), rho=34.0, width=1.8, step=6.0, roll=None):
    """the four rails swept along polyline P (map coordinates) as one model; roll: degrees per point (the rails'
    turn about the axis from the diagonals of up0)"""
    from models.tubekit import rail_sweep
    keep = [0]; s = 0.0
    for i in range(1, len(P)):
        s += np.linalg.norm(P[i] - P[i - 1])
        if s >= step or i == len(P) - 1: keep.append(i); s = 0.0
    P = np.asarray(P, dtype=float)[keep]
    T, U, W = frames_uw(P, up0)
    if roll is not None:
        r = np.radians(np.asarray(roll, dtype=float)[keep])[:, None]
        U, W = U * np.cos(r) + W * np.sin(r), W * np.cos(r) - U * np.sin(r)
    org = P[0].copy()
    save(rail_sweep(P - org, U, W, rho, width, material='r11_pc_rail'), name)
    E.add_prop(v, 'models/corehub_intro/%s.mdl' % name, org, (0, 0, 0), name=name)


def rings_at(v, kind, pts, axis, prefix):
    ang = tube.axis_angles(axis)
    for k, p in enumerate(pts):
        E.add_prop(v, 'models/corehub_intro/r11_pc_ring_%s.mdl' % kind, p, ang, name='%s_%s_%d' % (prefix, kind, k))


def line(a, b, n=40):
    a = np.asarray(a, dtype=float); b = np.asarray(b, dtype=float)
    return np.array([a + (b - a) * k / (n - 1) for k in range(n)])


# ---------------------------------------------------------------------------------------------------------- shot A
A1_COLLARS = [220.0, 570.0, 920.0, 1270.0, 1620.0, 1700.0]   # x of the collars' faces (bands in the film's frames; 1700: the tube's end ring)
A2_RINGS = [680.0, 800.0, 912.0, 1025.0, 1143.0, 1257.0, 1369.0, 1520.0, 1660.0]   # y (the junction follows)


# the tube axis relative to the camera path (the camera rides off the axis here): fitted to the film's dark rails
# (out/pc/railfit_pc.py, near rails 25-300 ahead): A1 (39.55-41.6 s) mean rail brightness 8.8 with the axis at
# y +11.8, z -14 from the camera, rails on the diagonals; A2 (44.3-46.4 s) axis at x +4.9, z -10, rails turned -14.8
A1_OFF, A2_OFF = np.array([0.0, 11.8, -14.0]), np.array([4.9, 0.0, -10.0])
A1_ROLL, A2_ROLL = 0.0, -14.8
A_BEND = (1255.0, 1314.0)


def a_offset(frame):
    w = float(np.clip((frame - A_BEND[0]) / (A_BEND[1] - A_BEND[0]), 0, 1)); w = w * w * (3 - 2 * w)
    return A1_OFF * (1 - w) + A2_OFF * w, A1_ROLL * (1 - w) + A2_ROLL * w


def shot_a(v, d):
    rd = Ride('pc_a', origin=ORIGIN_A)
    d.override_camera(cam_until(rd, tnext(1463)), fov=60.0)
    o = np.asarray(ORIGIN_A)
    keep = rd.t <= 1436.0
    cv = rd.curve[keep]; ft = rd.t[keep]
    offs = [a_offset(f) for f in ft]
    cvo = cv + np.array([x for x, r in offs]); rolls = [r for x, r in offs]
    # rails: lead-in along -x, the measured path, run-out along +y
    lead = line(cvo[0] - np.array([900.0, 0, 0]), cvo[0], 20)[:-1]; run = line(cvo[-1], cvo[-1] + np.array([0, 20.0, 0]), 3)[1:]
    P = np.vstack([lead, cvo, run]); R = [rolls[0]] * len(lead) + rolls + [rolls[-1]] * len(run)
    rails_along(v, P, PFX + '_a_rails', roll=R)
    rings_at(v, 'a1', [o + (x, 0.0, 0.0) + A1_OFF for x in A1_COLLARS], (1, 0, 0), PFX + '_a')
    xa2 = float(rd.pos(1400)[0])
    rings_at(v, 'a2', [np.array([xa2, y + o[1], o[2]]) + A2_OFF for y in A2_RINGS], (0, 1, 0), PFX + '_a')
    junction(v, np.array([xa2, o[1], o[2]]) + A2_OFF)
    room_a(v, o)
    lo, hi = rd.bounds()
    lo = np.minimum(lo, o + (-900, -900, -900)); hi = np.maximum(hi, np.array([xa2, o[1] + 2400, o[2]]) + 900)
    bg = bmat('r11_pc_bg_a', (0.225, 0.225, 0.225)); bg2 = bmat('r11_pc_bg_a2', (0.145, 0.145, 0.145))
    shell(v, lo - 600, hi + 600, bg, mats={'+y': bg2, '-z': bg2})
    return rd


JUNCTION_Y, CROSS_R, WALL_Y = 1825.0, 92.0, 1985.0
LIGHT_X = 2650.0


def room_a(v, o):
    """the room around the tube's end (41.7-43.0 s): a far wall ahead with rows of lit panels (seen through the end
    ring at eye height, 4-11 degrees above the view at 42.05 s), the rusty walls (the shell)"""
    wall = bmat('r11_pc_ceil', (0.20, 0.20, 0.20)); lamp = bmat('r11_pc_lamp', (0.70, 0.70, 0.68))
    E.add_box(v, o + (LIGHT_X, -160.0, -200.0), o + (LIGHT_X + 40.0, 450.0, 110.0), wall)
    for z0 in (-135.0, -60.0, 15.0):
        for y in np.arange(-130.0, 300.0, 190.0):
            E.add_box(v, o + (LIGHT_X - 6.0, y, z0), o + (LIGHT_X, y + 160.0, z0 + 50.0), lamp)


WALL_SHOW = []


def show_props(d):
    """director hook: props listed in WALL_SHOW sit at their place only between t0 and t1"""
    if not WALL_SHOW: return
    rows = ','.join('["%s",%.4f,%.4f,%.1f,%.1f,%.1f,%.1f,%.1f,%.1f]' % ((n, t0, t1) + tuple(p) + tuple(q)) for n, t0, t1, p, q in WALL_SHOW)
    d.append('r11pcShow <- [' + rows + '];\n' + '''function R11PC_Show(t) {
    foreach(r in r11pcShow){local e=Entities.FindByName(null,r[0]);if(e==null)continue;
        if(t>=r[1]&&t<r[2])e.SetOrigin(Vector(r[3],r[4],r[5]));else e.SetOrigin(Vector(r[6],r[7],r[8]));}
}
''')
    d.hook('R11PC_Show(t);')


def junction(v, base):
    """the end of the ringed tube (46.9-48.8 s): it meets a vertical tube (axis z) with a pale inside and dark collars;
    the camera turns down into it and faces its pale wall at close range (the film's flat pale view 48.6-48.9 s).
    base: the ringed tube's axis at y = 0"""
    from lib.mesh import Mesh
    m = Mesh(); c = base + (0.0, JUNCTION_Y, 0.0)
    n = 12
    for rr, mt in ((CROSS_R - 2.0, 'r11_pc_cross_in'), (CROSS_R + 2.0, 'r11_pc_cross_out')):     # pale inside, dark outside
        for k in range(n):
            a0 = 2 * math.pi * k / n; a1 = 2 * math.pi * (k + 1) / n
            p = [(rr * math.cos(a), rr * math.sin(a)) for a in (a0, a1)]
            q = [c + (p[0][0], p[0][1], -900.0), c + (p[0][0], p[0][1], 260.0), c + (p[1][0], p[1][1], 260.0), c + (p[1][0], p[1][1], -900.0)]
            m.quad(mt, *q)
    save(m.transform(offset=-c), PFX + '_cross')
    E.add_prop(v, 'models/corehub_intro/%s_cross.mdl' % PFX, c, (0, 0, 0), name=PFX + '_cross')
    for k, z in enumerate((230.0, 120.0, -330.0, -470.0, -610.0, -750.0)):
        E.add_prop(v, 'models/corehub_intro/r11_pc_ring_xl.mdl', c + (0.0, 0.0, z), tube.axis_angles((0, 0, -1)), name='%s_xring%d' % (PFX, k))
    # the white pod at the ringed tube's end, in front of the vertical tube (the film's bright blob at the vanishing point)
    pp = base + (0.0, JUNCTION_Y - CROSS_R - 40.0, 0.0)
    E.add_prop(v, 'models/corehub_intro/r11_pc_pod.mdl', pp, tube.axis_angles((0, 1, 0)), name=PFX + '_pod')
    WALL_SHOW.append((PFX + '_pod', 39.0, 47.15, pp, pp + (0.0, 0.0, -2500.0)))      # gone once the camera reaches it


# ---------------------------------------------------------------------------------------------------------- shot B
B_RING_STEP = 62.0


def shot_b(v, d, rc):
    """the dark vertical tube above shot C's start (C's coordinates), the pale wall at its top"""
    rd = Ride('pc_b', origin=ORIGIN_C)
    d.override_camera(cam_until(rd, tnext(1512)), fov=60.0)
    o = np.asarray(ORIGIN_C)
    top = rd.pos(1463)
    rings_at(v, 'b', [o + (0.0, 0.0, z) for z in np.arange(top[2] - o[2] - 60.0, 160.0, -B_RING_STEP)], (0, 0, -1), PFX + '_b')
    # the pale sleeve the camera is in while it faces the wall (48.8-49.2 s), above the dark rings
    from lib.mesh import Mesh
    m = Mesh(); n = 12
    for rr, mt in ((CROSS_R - 2.0, 'r11_pc_cross_in'), (CROSS_R + 2.0, 'r11_pc_cross_out')):
        for k in range(n):
            a0 = 2 * math.pi * k / n; a1 = 2 * math.pi * (k + 1) / n
            p = [(rr * math.cos(a), rr * math.sin(a)) for a in (a0, a1)]
            m.quad(mt, V(p[0][0], p[0][1], -40.0), V(p[0][0], p[0][1], 600.0), V(p[1][0], p[1][1], 600.0), V(p[1][0], p[1][1], -40.0))
    save(m, PFX + '_bsleeve')
    E.add_prop(v, 'models/corehub_intro/%s_bsleeve.mdl' % PFX, top, (0, 0, 0), name=PFX + '_bsleeve')
    return rd


# ---------------------------------------------------------------------------------------------------------- shot C
C_RING0, C_RING_STEP = 572.0, 111.8


def shot_c(v, d):
    rd = Ride('pc_c', origin=ORIGIN_C)
    d.override_camera(cam_until(rd, None), fov=60.0)
    rb = shot_b(v, d, rd)
    o = np.asarray(ORIGIN_C); ax = np.asarray(rd.raw['axis'], dtype=float)
    # rails: down the vertical tube, through the bend (shot B's path) and along C's tube
    tb = [f for f in rb.t if f >= 1476.0]; ib = [i for i, f in enumerate(rb.t) if f >= 1476.0]
    Pb = rb.curve[ib]
    P = np.vstack([line(Pb[0] + (0, 0, 400.0), Pb[0], 10)[:-1], Pb, line(Pb[-1], o + ax * 2600.0, 60)[1:]])
    rails_along(v, P, PFX + '_c_rails', up0=(1.0, 0.0, 0.0))
    rings_at(v, 'c', [o + ax * (C_RING0 + C_RING_STEP * k) for k in range(-4, 19)], ax, PFX + '_c')
    lo, hi = rd.bounds(); lb, hb = rb.bounds()
    lo = np.minimum(np.minimum(lo, lb), o - ax * 600); hi = np.maximum(np.maximum(hi, hb + (0, 0, 900.0)), o + ax * 2600)
    bg = bmat('r11_pc_bg_c', (0.255, 0.257, 0.257))
    shell(v, lo - 700, hi + 700, bg)
    return rd


# the cube (50.4-54.1 s): measured in the film's moments (out/pc/cubetrack.py: bright blob size and centre):
# about 890 units ahead of the camera at 1546, 450 at 1555, 210 at 1576, 160-190 from 1590 on (cube edge 44)
CUBE_D = (160.0, 728.0, 1546.0, 11.0)


def cube(v, d, rd):
    o = np.asarray(ORIGIN_C); ax = np.asarray(rd.raw['axis'], dtype=float)
    E.add_prop(v, 'models/corehub_intro/r11_pc_cube.mdl', o + ax * 3000.0, (0, 0, 0), name=PFX + '_cube')
    rows = []
    d0, A, n0, tau = CUBE_D
    for n in range(1512, 1623):
        cam = rd.pos(n) if n <= 1621 else rd.pos(1621)
        dist = d0 + A * math.exp(-(n - n0) / tau)
        p = cam + ax * dist + np.array([0.0, 0.0, 0.0])
        k = n - 1512
        rows.append('[%.4f,%.1f,%.1f,%.1f,%.1f,%.1f,%.1f]' % (n * 1001 / 30000.0, p[0], p[1], p[2], 25.0 + 0.55 * k, 40.0 + 1.2 * k, 10.0 + 0.8 * k))
    park = o + np.array([-500.0, -500.0, -500.0])
    code = 'r11pcCube <- [' + ','.join(rows) + '];\n' + '''function R11PC_Cube(t) {
    local e=Entities.FindByName(null,"r11_pc_cube");if(e==null)return;
    local n=r11pcCube.len();
    if(t<r11pcCube[0][0] || t>=r11pcCube[n-1][0]){e.SetOrigin(Vector(%.1f,%.1f,%.1f));return;}
    for(local i=0;i<n-1;i++){
        local a=r11pcCube[i],b=r11pcCube[i+1];if(t>b[0])continue;
        local f=(t-a[0])/(b[0]-a[0]);if(f<0)f=0;
        e.SetOrigin(Vector(a[1]+(b[1]-a[1])*f,a[2]+(b[2]-a[2])*f,a[3]+(b[3]-a[3])*f));
        e.__KeyValueFromString("angles",(a[4]+(b[4]-a[4])*f)+" "+(a[5]+(b[5]-a[5])*f)+" "+(a[6]+(b[6]-a[6])*f));
        return;
    }
}
''' % tuple(park)
    d.append(code)
    d.hook('R11PC_Cube(t);')


def apply(v, d):
    del WALL_SHOW[:]
    shot_a(v, d)
    rc = shot_c(v, d)
    cube(v, d, rc)
    show_props(d)
    # the old build dipped the screen to 110/255 black at 52.45-52.68 s; the film has no dip there (frames 1572-1580
    # keep their brightness), so that fade goes
    d.replace('[52.45,52.55,0,110],[52.55,52.68,110,0],', '')
