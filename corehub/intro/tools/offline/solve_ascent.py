"""Bundle solve of the ascent (31.2-32.5 s): camera on a straight vertical line + collar heights, from ring fits.
World frame: tube axis = vertical line through AX; rings are horizontal circles of radius R on the axis."""
import sys, numpy as np, json
from scipy.optimize import least_squares
sys.path.insert(0, '/home/claude/offline')
from ringtrack import *
from scene import view_basis, DEG
import math
AX = np.array([-12894.977855, -47.117998])
R_COLLAR = 61.06
F = 55.0
TH = math.tan(F * DEG / 2) * 1.2; TV = math.tan(F * DEG / 2) * 0.75
K0 = 14.6
T_PASS = dict(A=31.5511, B=31.8184, C=32.2372, D=32.6563)


def project_circle(eye, ang, c, R, n=72):
    f, r, u = view_basis(*ang)
    a = np.linspace(0, 2 * np.pi, n, endpoint=False)
    P = np.c_[c[0] + R * np.cos(a), c[1] + R * np.sin(a), np.full(n, c[2])] - eye
    d = P @ f
    ok = d > 1.0
    x = (P @ r) / d / TH; y = (P @ u) / d / TV
    px = (x + 1) * 320; py = (1 - y) * 200
    ok &= (px > 2) & (px < 637) & (py > 2) & (py < 397)
    if ok.sum() < 8: return None
    return circle_fit(np.c_[px[ok], py[ok]])


def collect():
    obs = []
    for name, T0 in T_PASS.items():
        for n in range(936, 975):
            t = n * 1001 / 30000
            if T0 - t < 0.03: continue
            rp = K0 / (T0 - t)
            if rp < 16 or rp > 300: continue
            g = gray_frame(n)
            a = fit_ring(g, (322, 146), rp * 0.80, rp * 1.25, +1, min_step=6)
            if a and a['rms'] < 1.0 and a['n'] >= 70: obs.append((name, n, t, a['cx'], a['cy'], a['r']))
    return obs


def main():
    obs = collect()
    names = sorted(T_PASS)
    frames = sorted({o[1] for o in obs})
    fi = {n: i for i, n in enumerate(frames)}
    print(len(obs), 'ring observations in', len(frames), 'frames')
    # unknowns: dx, dy (camera offset from the axis), pitch, yaw, v, z_ref (camera height at t_ref), ring heights (A fixed), per-frame dz for the first frames
    t_ref = 31.40
    nfree = sum(1 for n in frames if n * 1001 / 30000 < 31.31)        # frames before the speed settles get their own height
    def unpack(p):
        dx, dy, pitch, yaw, v, zref = p[:6]
        zr = dict(A=933.4, B=p[6], C=p[7], D=p[8])
        dz = p[9:9 + nfree]
        return dx, dy, pitch, yaw, v, zref, zr, dz
    def cam_z(p, n):
        dx, dy, pitch, yaw, v, zref, zr, dz = unpack(p)
        t = n * 1001 / 30000
        z = zref + v * (t - t_ref)
        i = fi[n]
        if i < nfree: z += dz[i]
        return z
    def resid(p):
        dx, dy, pitch, yaw, v, zref, zr, dz = unpack(p)
        out = []
        for name, n, t, cx, cy, r in obs:
            eye = np.array([AX[0] + dx, AX[1] + dy, cam_z(p, n)])
            c = project_circle(eye, (pitch, yaw, 0.0), (AX[0], AX[1], zr[name]), R_COLLAR)
            if c is None: out += [30.0, 30.0, 30.0]; continue
            w = 1.0
            out += [(c[0] - cx) * w, (c[1] - cy) * w, (c[2] - r) * w * 2.0]
        out += list(dz * 0.02)          # weak prior: early frames near the constant-speed line
        return np.array(out)
    p0 = np.array([-5.0, 1.9, -83.2, 0.0, 2185.0, 933.4 - 2185 * (31.5511 - t_ref), 1517.5, 2432.6, 3348.3] + [0.0] * nfree)
    sol = least_squares(resid, p0, loss='soft_l1', f_scale=1.5, x_scale=[1, 1, 0.2, 0.2, 50, 10, 20, 20, 20] + [20] * nfree)
    p = sol.x
    dx, dy, pitch, yaw, v, zref, zr, dz = unpack(p)
    r = resid(p)[:len(obs) * 3].reshape(-1, 3)
    print('camera offset from axis (%.2f, %.2f)  pitch %.3f yaw %.3f  speed %.1f u/s  z(%.2f)=%.1f' % (dx, dy, pitch, yaw, v, t_ref, zref))
    print('ring heights', {k: round(x, 1) for k, x in zr.items()})
    print('rms residual px: cx %.2f cy %.2f r %.2f' % (np.sqrt((r[:, 0] ** 2).mean()), np.sqrt((r[:, 1] ** 2).mean()), np.sqrt(((r[:, 2] / 2) ** 2).mean())))
    print('early frames:', [(n, round(cam_z(p, n), 1)) for n in frames[:nfree + 2]])
    json.dump(dict(dx=dx, dy=dy, pitch=pitch, yaw=yaw, v=v, t_ref=t_ref, zref=zref, rings=zr, early={int(n): cam_z(p, n) for n in frames[:nfree]}),
              open('/home/claude/offline/out/ascent_solution.json', 'w'), indent=1)


if __name__ == '__main__':
    main()
