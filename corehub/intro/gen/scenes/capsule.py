"""Capsule / ending (film frames 3575-3965, 119.29-132.30 s), rebuilt in cell C8 (x 5000..12000, y 9850..16300,
z -3000..5000) round HUB (8500, 13000, 1000), sealed by a black shell.

Shots (moments/ncc.npy: one hard cut, 3751 | 3752; the dips at 3625-3633 and 3693-3707 are fast motion, not cuts):
  A1 3575-3631  down the vertical delivery tube (rails, dark collars, dim rust shaft) to the vault floor and the pod
  A2 3631-3690  close above the pod's cracked glass lid
  A3 3690-3716  the camera turns about the picture's up axis, past a concrete wall, up to the ceiling
  A4 3716-3751  under the open ceiling iris (cross-shaped gap between four square petals); the radio drops down the
                tube at the camera
  B  3752-3965  (cut) red light: the radio flies off to the left, the iris closes (3758-3770), the camera pulls back
                (3771-3840) while a tiled shutter slides over the recess (3822-3846), then holds and turns slowly with
                a round lamp on the shutter; fade to black 131.2-132.3
The camera is data/cp_cam_ride.json, written by offline/out/cp/tools/build_cam.py (see there for the measurements).
The parts of the set that the film shows from inconsistent places (the shaft seen from above in A1, the ceiling seen
from below in B) are models switched on and off in time, so that each shot sees only its own surroundings.
Everything that moves (petals, shutter + lamp, radio, the light object at the right of the picture in B, the
red tint of the ceiling props, screen black) is driven by my own Squirrel function CP_Update(t) (Director.append +
hook), limited to 119.2-132.4 s. The base director's SetEnding moves the old ending props intro_pod, intro_pod_body,
intro_pod_crack and intro_pod_shell relative to the camera, which would bring them into this cell: CP_Update hides
them (in this cell, outside the shell) during that range. The two LOST capsule models (p9_end_capsule_glazing /
intro_pod, p9_end_v4_capsule_fracture / intro_pod_crack) are rebuilt as r11_cp_pod and r11_cp_crack here."""
import json, math, os
import numpy as np
from lib import vmfedit as E, tube
from lib.ride import qangle
from models import capsule as M

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CELL = ((5000.0, 9850.0, -3000.0), (12000.0, 16300.0, 5000.0))
BLACK = 'corehub_intro/r11_cp_black'
HUB = np.array([8500.0, 13000.0, 1000.0])
Z_FLOOR = 650.0             # vault floor (A1: the lit tile square's edge, 3600 / 3612: half-width 204 at z 652)
Z_CEIL = 970.0              # vault ceiling tiles
Z_PANEL = 1012.0            # back of the recess (dark panel round the tube hole)
Z_PETAL = 1004.0
REC = 185.0                 # recess half-width (3830: 470 px at depth ~364)
Z_SHUT = 900.0              # shutter plane (its tiles 1.25 x the ceiling's in 3840)
POD_AT = np.array([8473.0, 13020.0, Z_FLOOR])     # film 3616-3624: pod centre ~20 units to the picture's left; A2: the
                                                  # head cushion's lower edge just above the picture centre
T0, T1 = 119.20, 132.40


def frame_time(n): return n * 1001 / 30000.0


def shell(v, lo, hi, mat=BLACK, t=32.0):
    lo = np.asarray(lo, dtype=float); hi = np.asarray(hi, dtype=float)
    for ax in range(3):
        for side in (0, 1):
            a = lo.copy() - t; b = hi.copy() + t
            if side == 0: b[ax] = lo[ax]
            else: a[ax] = hi[ax]
            E.add_box(v, a, b, mat)


def prop(v, model, p, ang=(0, 0, 0), name=None):
    mdl = model if model.startswith('models/') else 'models/corehub_intro/%s.mdl' % model
    E.add_prop(v, mdl, tuple(float(x) for x in p), tuple(float(x) for x in ang), name=name)


# ------------------------------------------------------------------------------------------------ camera
def load_cam():
    cam = json.load(open(os.path.join(HERE, 'data', 'cp_cam_ride.json')))
    tm = np.array([m[0] for m in cam['moments']]); P = np.array([m[3:6] for m in cam['moments']])
    Fw = np.array([m[6:9] for m in cam['moments']]); Up = np.array([m[9:12] for m in cam['moments']])
    return cam, tm, P, Fw, Up


def cam_at(C, t):
    cam, tm, P, Fw, Up = C
    i = int(np.clip(np.searchsorted(tm, t) - 1, 0, len(tm) - 2)); a = (t - tm[i]) / (tm[i + 1] - tm[i]); a = min(1, max(0, a))
    p = P[i] * (1 - a) + P[i + 1] * a; f = Fw[i] * (1 - a) + Fw[i + 1] * a; u = Up[i] * (1 - a) + Up[i + 1] * a
    f /= np.linalg.norm(f); u = u - f * (u @ f); u /= np.linalg.norm(u)
    return p, f, u, np.cross(f, u)          # right = f x u


def screen_point(C, t, px, py, depth):
    """world point at pixel (px, py) of the 640x400 frame, `depth` along the view axis"""
    p, f, u, r = cam_at(C, t); F = 461.88
    return p + f * depth + r * (px - 319.5) / F * depth + u * (199.5 - py) / F * depth


def unproject_z(C, t, px, py, z):
    p, f, u, r = cam_at(C, t); F = 461.88
    d = f + r * (px - 319.5) / F + u * (199.5 - py) / F
    k = (z - p[2]) / d[2]
    return p + d * k


# ------------------------------------------------------------------------------------------------ animation tables
def petal_g(t):
    """opening per axis (film: the cross-shaped gap is 2g wide: 205 px at depth 234 in 3738 -> g 52; 3762: 80 px,
    3766: 40 px, closed at 3770)"""
    tab = [(119.0, 52.0), (125.38, 52.0), (125.46, 28.0), (125.53, 17.0), (125.63, 9.0), (125.72, 3.0), (125.79, 0.0)]
    return float(np.interp(t, [a for a, b in tab], [b for a, b in tab]))


# shutter: leading edge (map x on z = Z_SHUT) from the film (3822-3844: edge pixel rows 400, 312, 255, 223, 138, 112)
SHUT_EDGE_PX = [(3822, 400.0), (3826, 312.0), (3830, 255.0), (3832, 223.0), (3838, 138.0), (3840, 112.0), (3846, -60.0)]
LAMP_PX = [(3860, 130.0, 312.0), (3875, 70.0, 275.0), (3890, 50.0, 262.0), (3905, 60.0, 250.0), (3920, 87.0, 257.0), (3935, 137.0, 262.0), (3950, 192.0, 262.0)]


# red light on the ceiling after the cut (film 3756-3880: r/g 1.62 -> 1.27): rendercolor tint of the ceiling props
RED = [(125.18, (180, 105, 105)), (126.0, (185, 115, 110)), (126.5, (215, 170, 160)), (127.0, (245, 230, 225)),
       (127.3, (255, 255, 255))]


def squirrel_tracks(tracks, hide, red=()):
    rows = []
    for tr in tracks:
        ks = []
        for t, p, a in tr['keys']:
            a2 = a if a is not None else (0, 0, 0)
            ks.append('[%.4f,Vector(%.2f,%.2f,%.2f),Vector(%.2f,%.2f,%.2f),%d]' % (t, p[0], p[1], p[2], a2[0], a2[1], a2[2], 0 if tr['keys'][0][2] is None else 1))
        rows.append('{name="%s",on=%.3f,off=%.3f,k=[%s]}' % (tr['name'], tr.get('t_on', -1.0), tr.get('t_off', 1e6), ','.join(ks)))
    code = 'cpTracks <- [\n' + ',\n'.join(rows) + '];\n'
    code += 'cpHide <- [%s];\n' % ','.join('"%s"' % h for h in hide)
    code += 'cpRedEnts <- [%s];\n' % ','.join('"%s"' % h for h in red)
    code += 'cpRed <- [%s];\n' % ','.join('[%.3f,Vector(%d,%d,%d)]' % (t, c[0], c[1], c[2]) for t, c in RED)
    code += 'cpRedLast <- "";\n'
    code += '''function CP_Update(t) {
    if(t<%.3f||t>%.3f)return;
    foreach(nm in cpHide){local e=Entities.FindByName(null,nm); if(e!=null)e.SetOrigin(Vector(5100,9900,-2950));}
    foreach(tr in cpTracks){
        local e=Entities.FindByName(null,tr.name); if(e==null)continue;
        if(t<tr.on||t>tr.off){e.SetOrigin(Vector(5100,9900,-2950));continue;}
        local k=tr.k; local n=k.len(); local a=k[0]; local b=k[0]; local f=0.0;
        if(t<=k[0][0]){a=k[0];b=k[0];}
        else if(t>=k[n-1][0]){a=k[n-1];b=k[n-1];}
        else {for(local i=0;i<n-1;i++)if(t>=k[i][0]&&t<=k[i+1][0]){a=k[i];b=k[i+1];f=(t-a[0])/(b[0]-a[0]);break;}}
        e.SetOrigin(a[1]+(b[1]-a[1])*f);
        if(a[3]==1){local g=a[2]+(b[2]-a[2])*f;e.__KeyValueFromString("angles",g.x+" "+g.y+" "+g.z);}
    }
    SetScreenBlack(Lerp1(cpFade,t));
    local c=Vector(255,255,255);
    if(t>=cpRed[0][0]){c=cpRed[cpRed.len()-1][1];for(local i=0;i<cpRed.len()-1;i++)if(t>=cpRed[i][0]&&t<=cpRed[i+1][0]){local f=(t-cpRed[i][0])/(cpRed[i+1][0]-cpRed[i][0]);c=cpRed[i][1]+(cpRed[i+1][1]-cpRed[i][1])*f;break;}}
    local cs=(c.x.tointeger())+" "+(c.y.tointeger())+" "+(c.z.tointeger());
    if(cs!=cpRedLast){cpRedLast=cs;foreach(nm in cpRedEnts){local e=Entities.FindByName(null,nm); if(e!=null)e.__KeyValueFromString("rendercolor",cs);}}
}
''' % (T0, T1)
    code += 'cpFade <- [%s];\n' % ','.join('[%.4f,%.1f]' % r for r in FADE)
    code = code.replace('FADE_T0', '%.4f' % FADE[0][0]).replace('FADE_T1', '%.4f' % FADE[-1][0])
    return code


# film brightness 3928-3962 (sRGB mean 71 -> 66, 47, 25, 10): black alpha = 255 * (1 - (film/71)^2.2)
FADE = [(119.20, 255.0), (119.30, 219.0), (119.50, 165.0), (119.70, 10.0), (119.75, 0.0),
        (131.20, 0.0), (131.33, 38.0), (131.60, 153.0), (131.86, 229.0), (132.13, 252.0), (132.40, 255.0)]


Z_A1_END = 874.0                          # A1: end ring (inner R 51, outer 90): 170 / 300 px at 3621 -> 139 below the camera


def apply(v, d):
    M.materials()
    C = load_cam(); cam, tm, P, Fw, Up = C
    samples = [(m[0], tuple(m[3:6]), qangle(np.array(m[6:9]), np.array(m[9:12]))) for m in cam['moments']]
    d.override_camera(samples, fov=60.0)
    tracks = []

    def static(nm, model, pos, ang, t_on, t_off):
        prop(v, model, pos, ang, nm)
        tracks.append(dict(name=nm, keys=[(T0, np.asarray(pos, float), None)], t_on=t_on, t_off=t_off))

    # ---- A1 / A2: shaft, tube, floor, the pod
    static('r11_cp_ashaft', 'r11_cp_ashaft', (HUB[0], HUB[1], Z_FLOOR), (0, 0, 0), T0, 123.75)
    static('r11_cp_atube', 'r11_cp_atube', (HUB[0], HUB[1], Z_A1_END), (0, 0, 0), T0, 121.10)
    static('r11_cp_pod', 'r11_cp_pod', POD_AT, (0, 0, 0), T0, 123.30)
    static('r11_cp_crack', 'r11_cp_crack', (HUB[0] - 1.0, HUB[1] + 19.0, cam['Z_A2'] - 7.0), (0, 0, 0), 121.05, 123.45)
    # ---- A3: the concrete wall
    static('r11_cp_concrete', 'r11_cp_concrete', (HUB[0], HUB[1] + 140.0, Z_FLOOR), (0, 0, 0), 121.30, 124.10)
    # ---- B: ceiling, recess, iris, tube above it, the light curved object
    static('r11_cp_ceiling', 'r11_cp_ceiling', (HUB[0], HUB[1], Z_CEIL), (0, 0, 0), 122.90, T1)
    static('r11_cp_strip', 'r11_cp_strip', (HUB[0], HUB[1], Z_CEIL), (0, 0, 0), 122.90, 128.20)     # orange light strip: not seen in the hold
    static('r11_cp_frame', 'r11_cp_frame', (HUB[0], HUB[1], Z_PETAL + 5), (0, 0, 0), 122.90, T1)
    static('r11_cp_frameout', 'r11_cp_frameout', (HUB[0], HUB[1], Z_PETAL + 5), (0, 0, 0), 122.90, 125.80)
    static('r11_cp_btube', 'r11_cp_btube', (HUB[0], HUB[1], Z_PANEL - 1), tube.axis_angles(np.array(cam['D_TUBE'])), 122.90, 125.90)
    # before the pull-back the object's left edge is measured in the picture (3744-3750: x 600, 3754: 520, 3757-3770:
    # 470): there the same cylinder is carried with the camera (axis along the picture's up, 132 ahead)
    # (film: it keeps its place in the picture while the camera turns in the hold, so it is carried all through B)
    rk2 = [(124.55, 610.0), (125.10, 600.0), (125.22, 540.0), (125.32, 470.0), (125.95, 465.0), (126.45, 560.0),
           (126.80, 613.0), (127.47, 600.0), (128.13, 540.0), (128.80, 520.0), (129.46, 513.0), (130.30, 535.0),
           (131.10, 558.0), (T1, 560.0)]
    kk = []
    for t in np.arange(124.55, T1 + 1e-6, 0.025):
        p, f, u, r = cam_at(C, t); px = float(np.interp(t, [a for a, b in rk2], [b for a, b in rk2]))
        X0 = 62.0 + (px - 319.5) * 132.0 / 461.88
        kk.append((float(t), p + f * 132.0 + r * X0, tube.frame_angles(u, -r)))
    prop(v, 'r11_cp_rim2', kk[0][1], kk[0][2], 'r11_cp_rim2')
    tracks.append(dict(name='r11_cp_rim2', keys=kk, t_on=124.55))
    ts = np.arange(T0, T1 + 1e-6, 0.05)
    for k in range(4):
        a = math.radians(45 + 90 * k); dv = np.array([math.cos(a), math.sin(a), 0.0]) * math.sqrt(2)
        keys = [(float(t), HUB + np.array([0, 0, Z_PETAL - HUB[2]]) + dv * petal_g(t), None) for t in ts if 123.3 <= t <= 125.9]
        keys = [(T0, keys[0][1], None)] + keys + [(T1, keys[-1][1], None)]
        for var, ton, toff in (('r11_cp_petal_dk', 122.90, 125.19), ('r11_cp_petal', 125.19, T1)):
            nm = '%s%d' % (var, k)
            prop(v, var, keys[0][1], (0, 90 * k, 0), nm)
            tracks.append(dict(name=nm, keys=keys, t_on=ton, t_off=toff))
    # ---- shutter + lamp: the leading edge from the film rows, the lamp from its pixel track
    ex = []
    for n, py in SHUT_EDGE_PX:
        q = unproject_z(C, frame_time(n) + 1 / 120.0, 320.0, py, Z_SHUT); ex.append((frame_time(n) + 1 / 120.0, float(q[0])))
    lam = []
    for n, px, py in LAMP_PX:
        q = unproject_z(C, frame_time(n) + 1 / 120.0, px, py, Z_SHUT); lam.append((frame_time(n) + 1 / 120.0, q))
    print('capsule: shutter edge x', [(round(t, 2), round(x)) for t, x in ex])
    print('capsule: lamp', [(round(t, 2), np.round(q[:2]).tolist()) for t, q in lam])
    SH_L = M.SH_L; y0 = 13110.0 - M.SH_W
    shk = [(t, np.array([x - SH_L, y0, Z_SHUT]), None) for t, x in ex]
    (ta, xa), (tb, xb) = ex[-2], ex[-1]
    xe = xb + (xb - xa) / (tb - ta) * (lam[0][0] - tb) * 0.25          # edge at the lamp's first sample (slowing down)
    off = xe - lam[0][1][0]
    for t, q in lam: shk.append((t, np.array([q[0] + off - SH_L, y0, Z_SHUT]), None))
    shk = [(T0, shk[0][1] + np.array([-900.0, 0, 0]), None), (ex[0][0] - 0.3, shk[0][1] + np.array([-400.0, 0, 0]), None)] + shk + [(T1, shk[-1][1], None)]
    # placed inside the sealed shell at first (a prop outside it makes the map leak); the hook moves it along its keys
    prop(v, 'r11_cp_shutter', np.array([HUB[0], HUB[1], Z_SHUT]), (0, 0, 0), 'r11_cp_shutter')
    tracks.append(dict(name='r11_cp_shutter', keys=shk, t_on=127.0))
    i0 = [i for i, k in enumerate(shk) if abs(k[0] - lam[0][0]) < 1e-6][0]
    rel = lam[0][1] - shk[i0][1]
    lamp_keys = [(t, p + rel - np.array([0, 0, 0.5]), None) for t, p, _ in shk]
    prop(v, 'r11_cp_lamp', lamp_keys[0][1], (0, 0, 0), 'r11_cp_lamp')
    tracks.append(dict(name='r11_cp_lamp', keys=lamp_keys, t_on=127.0))
    # ---- the radio: drops down the tube at the camera (film 3738: a dot at the vanishing point, 3746: 60 px,
    #      3751: fills the right of the picture, front with the display toward the camera), after the cut its back
    #      (black, logo) faces the camera and it flies off to the left (3752 top-left, 3754 220/150, 3762 left edge)
    rk = [(3736, 298, 266, 700, 0), (3742, 288, 252, 220, 0), (3746, 290, 240, 95, 0), (3748, 325, 240, 58, 0),
          (3750, 400, 236, 36, 0), (3751.5, 470, 230, 25, 0),
          (3752.0, 130, 70, 18, 1), (3754, 220, 150, 48, 1), (3757, 150, 215, 95, 1), (3762, 20, 230, 130, 1), (3767, -70, 235, 155, 1)]
    keys = []
    for n, px, py, dd, side in rk:
        t = frame_time(n) + 1 / 120.0; p, f, u, r = cam_at(C, t)
        tilt = math.radians(25.0 * (n - 3740) / 12.0)
        uu = u * math.cos(tilt) + r * math.sin(tilt); rr = np.cross(f, uu)
        ang = tube.frame_angles(-rr, -f) if side == 0 else tube.frame_angles(rr, f)      # preview: model front = +Y
        c = screen_point(C, t, px, py, dd) - uu * 15.0
        keys.append((t, c, ang))
    for i in range(1, len(keys)):                       # keep the angles continuous for the interpolation
        a = list(keys[i][2]); b = keys[i - 1][2]
        for j in range(3):
            while a[j] - b[j] > 180: a[j] -= 360
            while a[j] - b[j] < -180: a[j] += 360
        keys[i] = (keys[i][0], keys[i][1], tuple(a))
    prop(v, 'models/props/radio_reference.mdl', keys[0][1], keys[0][2], 'r11_cp_radio')
    tracks.append(dict(name='r11_cp_radio', keys=keys, t_on=keys[0][0], t_off=keys[-1][0]))
    # ---- red light (B): the ceiling props are tinted (the film's light object at the right is not)
    red = ['r11_cp_ceiling', 'r11_cp_frame', 'r11_cp_frameout', 'r11_cp_btube', 'r11_cp_shutter', 'r11_cp_lamp'] + ['r11_cp_petal%d' % k for k in range(4)]
    hide = ['intro_pod', 'intro_pod_body', 'intro_pod_crack', 'intro_pod_shell']
    d.append(squirrel_tracks(tracks, hide, red))
    d.hook('CP_Update(t);')
    # ---- black shell round everything (inside C8)
    lo = np.array([HUB[0] - 1400, HUB[1] - 1400, Z_FLOOR - 400]); hi = np.array([HUB[0] + 1400, HUB[1] + 1400, 2900.0])
    lo = np.maximum(lo, np.array(CELL[0]) + 40); hi = np.minimum(hi, np.array(CELL[1]) - 40)
    shell(v, lo, hi)
