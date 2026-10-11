"""Camera track of the iris hold and the ascent (23.5-32.5 s) with a constant orientation, from ring edges.
Writes out/iris_track.json: [[frame, t, x, y, z, rms], ...] and the collar heights."""
import sys, json, numpy as np
from scipy.optimize import least_squares
sys.path.insert(0, '/home/claude/offline')
from camsolve import *
from ringtrack import gray_frame
AX = np.array([-12894.977855, -47.117998])
ANG = (-83.17, -7.18, 0.30); FOV = 55.0
RF, ZF = 53.7, 262.1; RM, ZM = 45.84, 378.9; RC = 61.06
K0 = 14.6; T_PASS = dict(A=31.5511, B=31.8184, C=32.2372, D=32.6563)


def hold():
    rings = dict(frame=ring_points((AX[0], AX[1], ZF), RF), mouth=ring_points((AX[0], AX[1], ZM), RM), A=ring_points((AX[0], AX[1], 933.4), RC))
    out = []; prev = dict(frame=204.0, mouth=94.0, A=39.0); eye = np.array([-12905.0, -44.5, 126.4])
    for n in range(706, 938):
        t = n * 1001 / 30000; g = gray_frame(n); obs = []
        for name, c0, lo, hi in (('frame', (322, 165), 0.85, 1.25), ('mouth', (322, 152), 0.85, 1.3), ('A', (320, 143), 0.8, 1.25)):
            pts, fit = edge_points(g, c0, prev[name] * lo, prev[name] * hi, +1)
            if pts is not None and len(pts) >= 40 and (name != 'frame' or prev[name] < 300):
                obs.append((rings[name], pts)); prev[name] = fit[2]
        if len(obs) < 2: continue
        e2, a2, rms = solve_pose(obs, eye, ANG, FOV, free=('x', 'y', 'z'))
        if rms < 2.5: eye = e2
        out.append([n, t, float(e2[0]), float(e2[1]), float(e2[2]), rms, len(obs)])
    return out


def ascent():
    obs = []
    for name, T0 in T_PASS.items():
        for n in range(936, 975):
            t = n * 1001 / 30000
            if T0 - t < 0.03: continue
            rp = K0 / (T0 - t)
            if rp < 16 or rp > 300: continue
            pts, fit = edge_points(gray_frame(n), (322, 146), rp * 0.80, rp * 1.25, +1, min_step=6)
            if pts is not None and len(pts) >= 70: obs.append((name, n, pts))
    frames = sorted({o[1] for o in obs}); fi = {n: i for i, n in enumerate(frames)}
    nf = len(frames)
    def unpack(p):
        return p[0], p[1], dict(A=933.4, B=p[2], C=p[3], D=p[4]), p[5:5 + nf]
    def resid(p):
        dx, dy, zr, zc = unpack(p); out = []
        for name, n, pts in obs:
            eye = (AX[0] + dx, AX[1] + dy, zc[fi[n]])
            pr = project(eye, ANG, FOV, ring_points((AX[0], AX[1], zr[name]), RC, n=180))
            if (pr[:, 2] <= 1).any(): out.append(np.full(len(pts), 50.0)); continue
            out.append(signed_radial(pts, pr[:, :2], pr[:, :2].mean(axis=0)))
        zs = zc; out.append(np.diff(zs, 2) * 0.01)        # weak smoothness of the climb
        return np.concatenate(out)
    z0 = [607.8 + 2086.6 * (n * 1001 / 30000 - 31.40) for n in frames]
    p0 = np.array([-8.6, 4.26, 1488.0, 2351.9, 3216.7] + z0)
    sol = least_squares(resid, p0, loss='soft_l1', f_scale=1.5)
    dx, dy, zr, zc = unpack(sol.x)
    r = resid(sol.x)[:sum(len(o[2]) for o in obs)]
    print('ascent: offset (%.2f, %.2f) rings %s rms %.2f px' % (dx, dy, {k: round(float(v), 1) for k, v in zr.items()}, np.sqrt((r ** 2).mean())))
    zs = np.array(zc); ts = np.array([n * 1001 / 30000 for n in frames])
    v = np.polyfit(ts[5:], zs[5:], 1); print('speed after 31.4 s: %.1f u/s; z(31.40) = %.1f; max deviation from the line %.1f' % (v[0], np.polyval(v, 31.40), np.abs(zs[5:] - np.polyval(v, ts[5:])).max()))
    return [[int(n), float(t), float(AX[0] + dx), float(AX[1] + dy), float(z)] for n, t, z in zip(frames, ts, zs)], {k: float(x) for k, x in zr.items()}, v


if __name__ == '__main__':
    h = hold()
    a, rings, v = ascent()
    H = np.array(h)
    print('hold: %d frames, rms median %.2f; x %.1f..%.1f y %.1f..%.1f z %.1f..%.1f' % (len(H), np.median(H[:, 5]), H[:, 2].min(), H[:, 2].max(), H[:, 3].min(), H[:, 3].max(), H[:, 4].min(), H[:, 4].max()))
    print('hold frames with rms > 2:', [(int(r[0]), round(r[5], 1)) for r in h if r[5] > 2])
    print('last hold frames:', [(int(r[0]), round(r[4], 1), round(r[5], 1)) for r in h[-8:]])
    print('first ascent frames:', [(r[0], round(r[4], 1)) for r in a[:8]])
    json.dump(dict(hold=h, ascent=a, rings=rings, speed=[float(x) for x in v], ang=ANG), open('/home/claude/offline/out/iris_track.json', 'w'))
