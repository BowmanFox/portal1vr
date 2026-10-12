"""Fitting the bends of a ride to the tube rails in the picture.

In a straight the four rails are lines through the vanishing point whatever the camera's place on the axis, but in a
bend their curves show exactly where the tube turns. For a trial bend (lead, radius, tail; see ride.make_path) the
rails are projected into every moment of the frames around the bend and scored by how dark the picture is along them
compared to both sides. The best trial is where the film's rails are.

    import railfit as RF
    rd = RF.load('rust_a')                                   # out/rust_a_ride.pkl written by ride_export.py
    best = RF.fit(rd, 998, rho=34 / 623.0)                   # bend that starts at frame 998 (key as ride_export prints)
    RF.overlay(rd, {998: best}, range(996, 1012), 'out/x.jpg', rho=34 / 623.0)     # the film with the fitted rails drawn in
All lengths are in the ride's solver units (rho = rail distance from the tube axis, 34 map units at true scale; width
= rail thickness, 2 map units)."""
import math, pickle, itertools
import numpy as np, cv2
import ride as RD

F = 320.0 / (1.2 * math.tan(math.radians(30.0)))       # 461.88 px on the 640x400 grid
CX, CY = 319.5, 199.5
_img = {}


def moment_image(n, mo):
    """one moment of video frame n as float32 640x400 (grey)"""
    k = (n, mo)
    if k not in _img:
        g = cv2.imread('/home/claude/data/moments/%s/f%04d.jpg' % (mo, n), cv2.IMREAD_GRAYSCALE)
        _img[k] = cv2.resize(g, (640, 400), interpolation=cv2.INTER_AREA).astype(np.float32)
        if len(_img) > 400: _img.pop(next(iter(_img)))
    return _img[k]


def load(name):
    d = pickle.load(open('/home/claude/offline/out/%s_ride.pkl' % name, 'rb'))
    d['frames'] = sorted(d['R'])
    return d


def _perp(d):
    i = int(np.argmax(np.abs(d))); j, k = [a for a in range(3) if a != i]
    u = np.zeros(3); w = np.zeros(3); u[j] = 1.0; w[k] = 1.0
    return u, w


def rail_curves(path, rho, s0=None, s1=None, ds=None):
    """the four rails along the path between arclengths s0 and s1: list of (points [k,3], tangents [k,3]) per rail piece"""
    ds = ds or rho * 0.5
    out = []
    for pc in path.pieces:
        a = pc['s0']; b = a + pc['length']
        lo = a if s0 is None else max(a, s0); hi = b if s1 is None else min(b, s1)
        if hi - lo < 1e-9: continue
        n = max(2, int(math.ceil((hi - lo) / ds)) + 1); u = np.linspace(lo, hi, n) - a
        if pc['kind'] == 'line':
            C = pc['start'][None, :] + u[:, None] * pc['dir'][None, :]; T = np.repeat(pc['dir'][None, :], n, 0)
            e1, e2 = _perp(pc['dir'])
            for s1_, s2_ in itertools.product((1, -1), repeat=2):
                out.append((C + (s1_ * e1 + s2_ * e2)[None, :] * rho / math.sqrt(2.0), T))
        else:
            ph = u / pc['radius']; d0 = pc['dir']; nn = pc['normal']; bn = np.cross(d0, nn)
            C = pc['start'][None, :] + pc['radius'] * (np.sin(ph)[:, None] * d0[None, :] + (1 - np.cos(ph))[:, None] * nn[None, :])
            T = np.cos(ph)[:, None] * d0[None, :] + np.sin(ph)[:, None] * nn[None, :]
            N = -np.sin(ph)[:, None] * d0[None, :] + np.cos(ph)[:, None] * nn[None, :]
            for s1_, s2_ in itertools.product((1, -1), repeat=2):
                P = C + (s1_ * N + s2_ * bn[None, :]) * rho / math.sqrt(2.0)
                # the rail's own tangent: the inner rails are shorter, but the direction is the tube's tangent
                out.append((P, T))
    return out


def project(X, C, Rcw):
    q = (X - C[None, :]) @ Rcw.T
    z = q[:, 2]; zz = np.where(z > 1e-9, z, 1e-9)
    return np.stack([F * q[:, 0] / zz + CX, F * q[:, 1] / zz + CY], 1), z


def _sample(img, xy):
    x = np.clip(xy[:, 0], 0, 638.999); y = np.clip(xy[:, 1], 0, 398.999)
    x0 = x.astype(int); y0 = y.astype(int); fx = x - x0; fy = y - y0
    return (img[y0, x0] * (1 - fx) * (1 - fy) + img[y0, x0 + 1] * fx * (1 - fy) + img[y0 + 1, x0] * (1 - fx) * fy + img[y0 + 1, x0 + 1] * fx * fy)


_ridge = {}


def ridge_map(n, mo, size=33, blur=5.0):
    """how much darker a pixel is than its surroundings on the scale of `size` pixels (thin dark things: the rails),
    spread out by `blur` pixels so that a rail a few pixels off still counts"""
    k = (n, mo, size, blur)
    if k not in _ridge:
        img = moment_image(n, mo)
        ker = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (size, size))
        th = cv2.morphologyEx(img, cv2.MORPH_CLOSE, ker) - img
        _ridge[k] = cv2.GaussianBlur(np.clip(th, 0, 60.0), (0, 0), blur)
        if len(_ridge) > 400: _ridge.pop(next(iter(_ridge)))
    return _ridge[k]


def ridge_response(rmap, curves, C, Rcw, width, zmin, zmax=None):
    """(sum of weighted ridge strength, sum of weights) along the projected rails"""
    tot = 0.0; wsum = 0.0
    for P, T in curves:
        xy, z = project(P, C, Rcw)
        ok = (z > zmin) & (xy[:, 0] > 2) & (xy[:, 0] < 637) & (xy[:, 1] > 2) & (xy[:, 1] < 397)
        if zmax is not None: ok &= z < zmax
        if ok.sum() < 2: continue
        v = _sample(rmap, xy)
        seg = np.zeros(len(P)); d = np.linalg.norm(np.diff(xy, axis=0), axis=1); d = np.minimum(d, 40.0)
        seg[:-1] += d / 2; seg[1:] += d / 2
        tot += float((v * seg)[ok].sum()); wsum += float(seg[ok].sum())
    return tot, wsum


def rail_response(img, curves, C, Rcw, width, zmin):
    """(sum of weighted contrast, sum of weights) of the rails in one picture"""
    tot = 0.0; wsum = 0.0
    for P, T in curves:
        xy, z = project(P, C, Rcw)
        xy2, z2 = project(P + T * (width * 0.5), C, Rcw)
        ok = (z > zmin) & (z2 > zmin) & (xy[:, 0] > 2) & (xy[:, 0] < 637) & (xy[:, 1] > 2) & (xy[:, 1] < 397)
        if ok.sum() < 2: continue
        t2 = xy2 - xy; ln = np.linalg.norm(t2, axis=1) + 1e-9; t2 = t2 / ln[:, None]
        n2 = np.stack([-t2[:, 1], t2[:, 0]], 1)
        hw = F * (width * 0.5) / np.maximum(z, 1e-9)
        ok &= hw > 0.3
        off = hw + np.maximum(1.5, 0.9 * hw)
        c = _sample(img, xy); a = _sample(img, xy + n2 * off[:, None]); b = _sample(img, xy - n2 * off[:, None])
        inb = lambda q: (q[:, 0] > 0) & (q[:, 0] < 639) & (q[:, 1] > 0) & (q[:, 1] < 399)
        ok &= inb(xy + n2 * off[:, None]) & inb(xy - n2 * off[:, None])
        con = np.clip(np.minimum(a, b) - c, 0, 50.0)
        # weight: length of the rail on the picture that a sample stands for
        seg = np.zeros(len(P)); d = np.linalg.norm(np.diff(xy, axis=0), axis=1); d = np.minimum(d, 40.0)
        seg[:-1] += d / 2; seg[1:] += d / 2
        tot += float((con * seg)[ok].sum()); wsum += float(seg[ok].sum())
    return tot, wsum


def cameras(rd, bends, frames=None, default_radius=None):
    """path and camera moments of a ride for the given bend settings -> (Path, s_of, [(frame, moment, C, Rcw, s)])"""
    path, s_of, info, v = RD.make_path(rd['sections'], rd['frames'], rd['v'], rd['R'], bends, default_radius)
    mom = RD.path_moments(rd['frames'], rd['R'], v, s_of, path, rd.get('RM'))
    fs = set(frames) if frames is not None else None
    return path, s_of, [(n, mo, p, R, s) for t, n, mo, p, R, s in mom if fs is None or n in fs], info


def score(rd, bends, frames, rho, width, s_range=None, default_radius=None, moments='EL', measure='ridge', zmax=None):
    """mean rail contrast over the frames (higher = the projected rails lie on dark lines of the film)"""
    path, s_of, cams, info = cameras(rd, bends, frames, default_radius)
    if s_range is None: lo, hi = None, None
    else: lo, hi = s_of[s_range[0]], s_of[s_range[1]]
    curves = rail_curves(path, rho, lo, hi)
    tot = 0.0; w = 0.0
    for n, mo, C, R, s in cams:
        if mo not in moments: continue
        if measure == 'ridge': a, b = ridge_response(ridge_map(n, mo), curves, C, R, width, zmin=0.3 * rho, zmax=zmax)
        else: a, b = rail_response(moment_image(n, mo), curves, C, R, width, zmin=0.3 * rho)
        tot += a; w += b
    return (tot / w if w > 0 else 0.0), w


def _bend_frames(rd, key):
    """(last frame of the straight before the bend, first frame of the straight after, first frame of the next bend or the end)"""
    st = [x for x in rd['sections'] if x[0] == 'straight']
    for k, x in enumerate(st):
        if x[2] + 1 == key:
            nxt = st[k + 1] if k + 1 < len(st) else None
            return x[1], x[2], (nxt[1] if nxt else rd['frames'][-1]), (nxt[2] if nxt else rd['frames'][-1])
    raise KeyError('no bend starts at frame %d' % key)


def fit(rd, key, rho, width=None, bends=None, pre=4, post=3, radii=None, leads=None, tails=None, verbose=True, refine=2):
    """grid search of (lead, radius, tail) for the bend that starts at frame `key`; the other bends as in `bends`.
    -> dict(radius, lead, tail, score)"""
    width = width or rho * 2.0 / 34.0
    a0, a, b, b1 = _bend_frames(rd, key)
    frames = list(range(max(a0, a - pre), min(b1, b + post) + 1))
    base = dict(bends or {})
    L0 = sum(rd['v'][n] for n in range(a, b))             # distance at the interpolated speeds
    radii = radii if radii is not None else [L0 * f for f in (0.08, 0.14, 0.2, 0.27, 0.35, 0.45, 0.55, 0.63)]
    leads = leads if leads is not None else [L0 * f for f in (0.0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.75, 0.9)]
    tails = tails if tails is not None else [L0 * f for f in (0.0, 0.05, 0.12, 0.2, 0.3, 0.4, 0.55)]
    best = None; res = []
    def ev(r, l, t):
        bd = dict(base); bd[key] = dict(radius=r, lead=l, tail=t)
        try: sc, w = score(rd, bd, frames, rho, width, s_range=(frames[0], b1))
        except Exception as e: return None
        return sc
    for r in radii:
        for l in leads:
            for t in tails:
                sc = ev(r, l, t)
                if sc is None: continue
                res.append((sc, r, l, t))
    res.sort(reverse=True)
    if verbose:
        print('bend %d (frames %d..%d, scored on %d..%d), distance at interpolated speed %.3f' % (key, a + 1, b - 1, frames[0], frames[-1], L0))
        for sc, r, l, t in res[:8]: print('   score %.2f  radius %.3f lead %.3f tail %.3f  (length %.3f)' % (sc, r, l, t, l + r * math.pi / 2 + t))
    sc, r, l, t = res[0]
    step = [L0 * 0.05, L0 * 0.05, L0 * 0.05]
    for it in range(refine * 12):                              # coordinate descent refinement
        improved = False
        for i in range(3):
            for sg in (1, -1):
                p = [r, l, t]; p[i] += sg * step[i]
                if p[0] <= 0.02 * L0 or p[1] < 0 or p[2] < 0: continue
                s2 = ev(*p)
                if s2 is not None and s2 > sc: sc, (r, l, t) = s2, p; improved = True
        if not improved:
            step = [x / 2 for x in step]
            if step[0] < L0 * 0.004: break
    if verbose: print('   refined: score %.2f  radius %.3f lead %.3f tail %.3f (length %.3f)' % (sc, r, l, t, l + r * math.pi / 2 + t))
    return dict(radius=float(r), lead=float(l), tail=float(t), score=float(sc))


def overlay(rd, bends, frames, out, rho, width=None, moments='E', cols=3, scale=1.0, rings=None, ring_r=None, default_radius=None, gain=1.6):
    """sheet of film moments with the rails of the path drawn in (yellow) and, optionally, collars: rings = arclengths,
    ring_r = their radius"""
    width = width or rho * 2.0 / 34.0
    path, s_of, cams, info = cameras(rd, bends, frames, default_radius)
    curves = rail_curves(path, rho, None, None)
    cells = []
    for n, mo, C, R, s in cams:
        if mo not in moments: continue
        g = np.clip(moment_image(n, mo) * gain, 0, 255).astype(np.uint8); im = cv2.cvtColor(g, cv2.COLOR_GRAY2BGR)
        if scale != 1.0: im = cv2.resize(im, None, fx=scale, fy=scale, interpolation=cv2.INTER_LINEAR)
        for P, T in curves:
            xy, z = project(P, C, R)
            for i in range(len(P) - 1):
                if z[i] > 0.3 * rho and z[i + 1] > 0.3 * rho and max(abs(xy[i]).max(), abs(xy[i + 1]).max()) < 4000:
                    cv2.line(im, (int(round(xy[i, 0] * scale)), int(round(xy[i, 1] * scale))), (int(round(xy[i + 1, 0] * scale)), int(round(xy[i + 1, 1] * scale))), (0, 255, 255), 1, cv2.LINE_AA)
        if rings is not None and ring_r:
            for sr in rings:
                c, t = path.point(sr); e1 = np.cross(t, [0, 0, 1.0])
                if np.linalg.norm(e1) < 0.1: e1 = np.cross(t, [0, 1.0, 0])
                e1 /= np.linalg.norm(e1); e2 = np.cross(t, e1)
                ang = np.linspace(0, 2 * np.pi, 49)
                Pr = c[None, :] + ring_r * (np.cos(ang)[:, None] * e1[None, :] + np.sin(ang)[:, None] * e2[None, :])
                xy, z = project(Pr, C, R)
                if (z > 0.3 * rho).all():
                    cv2.polylines(im, [np.round(xy * scale).astype(np.int32).reshape(-1, 1, 2)], False, (0, 160, 255), 1, cv2.LINE_AA)
        cv2.putText(im, '%d%s' % (n, mo), (4, 14), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 255, 0), 1)
        cells.append(im)
    rows = []
    for i in range(0, len(cells), cols):
        r = cells[i:i + cols]
        while len(r) < cols: r.append(np.zeros_like(cells[0]))
        rows.append(np.hstack(r))
    cv2.imwrite(out, np.vstack(rows), [cv2.IMWRITE_JPEG_QUALITY, 88]); return out


def curve_of(rd):
    return RD.Curve(rd['curve_P'], rd['curve_t'])


def first_up(rd):
    st = [x for x in rd['sections'] if x[0] == 'straight']
    return np.array(RD.AXES[st[0][4]], dtype=float)


def overlay_curve(rd, frames, out, rho, moments='E', cols=4, scale=0.6, rings=None, ring_r=None, gain=1.6, extra=None):
    """sheet of film moments with the four rails of the measured path (rd = load(name) after ride_export.py) drawn in
    yellow; rings: arclengths of collars to draw as circles of radius ring_r; extra: [(points [k,3], colour)] more
    polylines in solver coordinates"""
    cv_ = curve_of(rd); rails = cv_.offset_curves(rho, first_up(rd))
    fs = set(frames); cells = []
    for t, n, mo, C, R, s in rd['moments']:
        if n not in fs or mo not in moments: continue
        g = np.clip(moment_image(n, mo) * gain, 0, 255).astype(np.uint8); im = cv2.cvtColor(g, cv2.COLOR_GRAY2BGR)
        if scale != 1.0: im = cv2.resize(im, None, fx=scale, fy=scale, interpolation=cv2.INTER_LINEAR)
        def draw(P, col, closed=False):
            xy, z = project(P, C, R)
            for i in range(len(P) - 1):
                if z[i] > 0.3 * rho and z[i + 1] > 0.3 * rho and max(abs(xy[i]).max(), abs(xy[i + 1]).max()) < 4000:
                    cv2.line(im, (int(round(xy[i, 0] * scale)), int(round(xy[i, 1] * scale))), (int(round(xy[i + 1, 0] * scale)), int(round(xy[i + 1, 1] * scale))), col, 1, cv2.LINE_AA)
        for P in rails: draw(P, (0, 255, 255))
        if rings is not None and ring_r:
            for sr in rings:
                c, tn = cv_.point(sr); e1 = np.cross(tn, [0, 0, 1.0])
                if np.linalg.norm(e1) < 0.1: e1 = np.cross(tn, [0, 1.0, 0])
                e1 /= np.linalg.norm(e1); e2 = np.cross(tn, e1); ang = np.linspace(0, 2 * np.pi, 49)
                draw(c[None, :] + ring_r * (np.cos(ang)[:, None] * e1[None, :] + np.sin(ang)[:, None] * e2[None, :]), (0, 160, 255))
        for P, col in (extra or []): draw(np.asarray(P, dtype=float), col)
        cv2.putText(im, '%d%s' % (n, mo), (4, 14), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 255, 0), 1)
        cells.append(im)
    rows = []
    for i in range(0, len(cells), cols):
        r = cells[i:i + cols]
        while len(r) < cols: r.append(np.zeros_like(cells[0]))
        rows.append(np.hstack(r))
    cv2.imwrite(out, np.vstack(rows), [cv2.IMWRITE_JPEG_QUALITY, 88]); return out


if __name__ == '__main__':
    import argparse, json
    ap = argparse.ArgumentParser(description='fit the bends of a ride to the rails (ride_export.py must have run)')
    ap.add_argument('name'); ap.add_argument('--unit', type=float, required=True, help='map units per solver unit (rails are 34 map units from the axis)')
    ap.add_argument('--bends', default='{}', help='settings to keep, as for ride_export.py'); ap.add_argument('--only', default=None, help='bend keys to fit, comma separated')
    ap.add_argument('--sheet', default=None)
    a = ap.parse_args()
    rd = load(a.name); rho = 34.0 / a.unit
    bends = {int(k): v for k, v in json.loads(a.bends).items()}
    st = [x for x in rd['sections'] if x[0] == 'straight']
    keys = [x[2] + 1 for x in st[:-1]]
    if a.only: keys = [int(k) for k in a.only.split(',')]
    for k in keys:
        b = fit(rd, k, rho, bends=bends); bends[k] = dict(radius=round(b['radius'], 4), lead=round(b['lead'], 4), tail=round(b['tail'], 4))
    print(json.dumps({str(k): v for k, v in bends.items()}))
    if a.sheet:
        fr = [n for n in rd['frames']]
        overlay(rd, bends, fr[::2], a.sheet, rho, cols=4, scale=0.6)
