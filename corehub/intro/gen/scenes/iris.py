"""Iris and ascent (22-32.5 s) at the scale solved from the video.

The tube is full size: mouth radius 45.84 at 116.8 above the frame ring, collars of radius 61.06 at 933.4, 1488.0,
2351.9 and 3216.7, camera 2087 u/s. (r10dm had a 0.6-scale tube with collars at 617-1895 and a 1250 u/s camera: the
rings passed at the right times but the mouth, the frame and the room did not fit together.) The shaft is widened so
the collars fit; its rust wall sits 76.3 from the axis, where the video's wall edges put it."""
import math, re
from lib import vmfedit as E

AX = (-12894.977855, -47.117998)
CAP_ABOVE = 46.0          # the cap sits on top of the last collar
RAIL_RHO = 34.0
# Camera track solved from the video (tools/offline/solve_iris.py -> gen/data/iris_track.json): constant orientation,
# position per video frame from the ring edges (hold: frame ring, tube mouth, first collar; climb: the collars).
CAM_ANG = (-83.17, -7.18, 0.30)
# frames the ring tracker could not follow (the dip before the launch); heights from the mouth ring and collar A
Z_FIX = {933: 106.6, 934: 88.3, 935: 160.5, 936: 220.0, 937: 302.0}


def camera_track():
    import json, os
    tr = json.load(open(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'data', 'iris_track.json')))
    asc = {r[0]: r for r in tr['ascent']}
    pts = {}
    for n, t, x, y, z, rms, k in tr['hold']:
        n = int(n)
        if rms <= 2.0 and n <= 932: pts[n] = (x, y, z)
    for n, r in asc.items():
        if n >= 938: pts[n] = (r[2], r[3], r[4])
    ax, ay = tr['ascent'][0][2], tr['ascent'][0][3]
    last = pts[max(k for k in pts if k <= 932)]
    for n, z in Z_FIX.items():
        f = (n - 932) / 6.0
        pts[n] = (last[0] + (ax - last[0]) * f, last[1] + (ay - last[1]) * f, z)
    lo, hi = min(pts), max(pts)
    # fill the few missing frames by interpolation, then continue the climb at its fitted speed up to the black frame
    out = []
    keys = sorted(pts)
    for n in range(lo, hi + 1):
        if n in pts: p = pts[n]
        else:
            a = max(k for k in keys if k < n); b = min(k for k in keys if k > n); f = (n - a) / (b - a)
            p = tuple(pa + (pb - pa) * f for pa, pb in zip(pts[a], pts[b]))
        out.append((n * 1001 / 30000.0, p))
    v, z0 = tr['speed']
    n = hi + 1
    while n * 1001 / 30000.0 < 32.4995:
        t = n * 1001 / 30000.0; out.append((t, (ax, ay, v * t + z0))); n += 1
    return out, tr['rings']


# The cube that overtakes the camera (30.53 s) and flies up the tube ahead of it. Image position and apparent width
# (640x400 pixels) read from the video's frames; its depth follows from the 36-unit cube.
CUBE_IMG = [(915, (353, 100), 250), (916, (322, 147), 158), (917, (325, 158), 117), (918, (315, 142), 87), (919, (312, 130), 67),
            (920, (313, 130), 55), (921, (320, 122), 45), (922, (318, 122), 37), (923, (320, 122), 33), (924, (317, 133), 30)]
CUBE_AXIS = [(31.098, 1230.0), (31.398, 1750.0), (32.0, 3008.0), (32.15, 3150.0)]      # then on the tube axis (time, height)


def cube_keys(track):
    import numpy as np
    sys_path = '/home/claude/offline'
    from lib.camera import ray
    cam = {round(t, 4): p for t, p in track}
    keys = []
    for n, (px, py), w in CUBE_IMG:
        t = n * 1001 / 30000.0
        eye = cam[min(cam, key=lambda k: abs(k - t))]
        o, d = ray(eye, CAM_ANG, 55.0, px, py)
        depth = 36.0 * 512.2 / w
        f = np.array(d) / np.dot(d, ray(eye, CAM_ANG, 55.0, 320, 200)[1])        # scale the ray to unit depth along the view axis
        keys.append((t, tuple(float(x) for x in (np.array(o) + f * depth))))
    for t, z in CUBE_AXIS: keys.append((t, (AX[0], AX[1], z)))
    return keys


def rel(s):
    lo, hi = E.solid_bounds(s)
    return (lo[0] - AX[0], lo[1] - AX[1], lo[2]), (hi[0] - AX[0], hi[1] - AX[1], hi[2])


def near(a, b, tol=0.6):
    return all(abs(x - y) <= tol for x, y in zip(a, b))


def rebox(v, ent, old, lo, hi):
    """replace an axis-aligned solid by a box lo..hi (relative to the axis in x, y), keeping each face's material"""
    mats = {}
    for side in old.sides:
        n = side.normal()
        key = ('+' if max(n.x, n.y, n.z) > 0.5 else '-') + 'xyz'[[abs(n.x), abs(n.y), abs(n.z)].index(max(abs(n.x), abs(n.y), abs(n.z)))]
        mats[key] = side.mat
    ent.solids.remove(old)
    E.add_box(v, (AX[0] + lo[0], AX[1] + lo[1], lo[2]), (AX[0] + hi[0], AX[1] + hi[1], hi[2]), mats.get('+z', 'tools/toolsnodraw'), ent=ent, mats=mats)


def apply(v, d):
    track, rings = camera_track()
    collars = [rings[k] for k in 'ABCD']
    cap_z = collars[-1] + CAP_ABOVE
    # ---- collars and cap
    for k, z in enumerate(collars):
        e = E.one(v, name='p41_preview_ascent_collar_%d' % k)
        e['origin'] = E.fmt((AX[0], AX[1], z))
    E.one(v, name='p41_preview_tube_end_cap')['origin'] = E.fmt((AX[0], AX[1], cap_z))
    # ---- shaft: drop the old small-tube pieces, widen the walls
    removed = 0
    walls = {}
    for e in list(v.entities):
        if e['classname'] != 'func_detail': continue
        for s in list(e.solids):
            lo, hi = rel(s)
            m = {x.mat.lower() for x in s.sides}
            if abs(lo[2] - 347.1) < 0.2 and abs(hi[2] - 349.6) < 0.2 and 'corehub_intro/void_black' in m and max(abs(lo[0]), abs(hi[0]), abs(lo[1]), abs(hi[1])) < 100:
                e.solids.remove(s); removed += 1          # black plate round the old tube
            elif 'corehub_intro/iris_dark_u' in m and near((lo[2], hi[2]), (318.7, 455.4)) and max(abs(lo[0]), abs(hi[0])) < 25:
                e.solids.remove(s); removed += 1          # old rail stubs
            elif 'corehub_intro/p9_ascent_rail_v2' in m and near((lo[2], hi[2]), (400.0, 1907.0)):
                walls.setdefault('rails', []).append((e, s))
            elif near((lo[2], hi[2]), (297.9, 6000.0)) and ('corehub_intro/p9_ascent_wall_v1' in m or 'corehub_intro/p9_stock_shaft_006b_v3' in m):
                key = '+x' if lo[0] > 50 else '-x' if hi[0] < -50 else '+y' if lo[1] > 40 else '-y'
                walls[key] = (e, s)
        if not e.solids: e.remove()
    assert removed == 28 and len(walls) == 5 and len(walls['rails']) == 4, (removed, {k: (len(x) if isinstance(x, list) else 1) for k, x in walls.items()})
    X0, X1, Y0, Y1 = -76.0, 76.3, -72.0, 73.9
    rebox(v, *walls['+x'], (X1, Y0, 297.9), (X1 + 28, Y1, 6000.0))
    rebox(v, *walls['-x'], (X0 - 28, Y0, 297.9), (X0, Y1, 6000.0))
    rebox(v, *walls['+y'], (X0 - 28, Y1, 297.9), (X1 + 28, Y1 + 28, 6000.0))
    rebox(v, *walls['-y'], (X0 - 28, Y0 - 28, 297.9), (X1 + 28, Y0, 6000.0))
    for k, (e, s) in enumerate(walls['rails']):
        a = math.radians(45 + 90 * k); x, y = RAIL_RHO * math.cos(a), RAIL_RHO * math.sin(a)
        rebox(v, e, s, (x - 0.9, y - 0.9, 410.0), (x + 0.9, y + 0.9, cap_z))
    # ---- camera: the hold under the iris and the climb (23.5-32.5 s), blended in from the old track over 0.25 s
    t0 = track[0][0]
    samples = []
    for t, p in track:
        f = min(1.0, (t - t0) / 0.25); f = f * f * (3 - 2 * f)
        po = d.value('positions', t); ao = d.value('knots', t)
        samples.append((t, tuple(a + (b - a) * f for a, b in zip(po, p)), tuple(a + (b - a) * f for a, b in zip(ao, CAM_ANG))))
    d.set_camera(t0 - 0.001, 32.4995, samples, pin=(True, False))

    # ---- the cube: world-space keys replace the old rig-space path
    keys = cube_keys(track)
    rows = []
    for t, p in keys:
        k = t - 30.53
        rows.append('[%.4f,%.2f,%.2f,%.2f,%.1f,%.1f,%.1f]' % (t, p[0], p[1], p[2], 18.0 * math.sin(k * 9.0), 90.0 + 210.0 * k, -260.0 * k))
    code = 'r11CubeKeys <- [' + ','.join(rows) + '];\n' + '''function P41_SetEarlyShaftCube(t) {
    local e=Entities.FindByName(null,"p41_intro_early_cube");if(e==null)return;
    local n=r11CubeKeys.len();
    if(t<r11CubeKeys[0][0] || t>=r11CubeKeys[n-1][0]){e.SetOrigin(Vector(-13056.3,-47.1,-1757.1));return;}
    e.__KeyValueFromString("rendercolor","255 255 255");
    for(local i=0;i<n-1;i++){
        local a=r11CubeKeys[i],b=r11CubeKeys[i+1];if(t>b[0])continue;
        local f=(t-a[0])/(b[0]-a[0]);if(f<0)f=0;
        e.SetOrigin(Vector(a[1]+(b[1]-a[1])*f,a[2]+(b[2]-a[2])*f,a[3]+(b[3]-a[3])*f));
        e.__KeyValueFromString("angles",(a[4]+(b[4]-a[4])*f)+" "+(a[5]+(b[5]-a[5])*f)+" "+(a[6]+(b[6]-a[6])*f));
        return;
    }
}
'''
    d.sub(r'function P41_SetEarlyShaftCube\(t\) \{.*?\n\}\n(?=function P41_MoveEarly)', lambda m: code, flags=re.S)
