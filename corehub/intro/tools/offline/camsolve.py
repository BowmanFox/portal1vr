"""Camera pose from known 3D circles (tube collars, iris rings) seen in a video frame.

edge_points() finds the points of a ring's edge in the image; solve_pose() moves the camera so the projected 3D
circles pass through those points (point-to-curve distances, robust least squares). Angles are Source QAngles."""
import math
import numpy as np, cv2
from scipy.optimize import least_squares
from scene import view_basis, DEG
from ringtrack import circle_fit

W, H = 640, 400


def cam_scale(fov):
    return math.tan(fov * DEG / 2) * 1.2, math.tan(fov * DEG / 2) * 0.75


def project(eye, ang, fov, P):
    f, r, u = view_basis(*ang); th, tv = cam_scale(fov)
    Q = np.atleast_2d(np.asarray(P, dtype=np.float64)) - np.asarray(eye, dtype=np.float64)
    d = Q @ f
    dd = np.where(np.abs(d) < 1e-6, 1e-6, d)
    return np.c_[((Q @ r) / dd / th + 1) * W / 2, (1 - (Q @ u) / dd / tv) * H / 2, d]


def ring_points(center, R, normal=(0, 0, 1), n=360):
    nrm = np.asarray(normal, dtype=np.float64); nrm /= np.linalg.norm(nrm)
    a = np.array([1.0, 0, 0]) if abs(nrm[0]) < 0.9 else np.array([0, 1.0, 0])
    u = np.cross(nrm, a); u /= np.linalg.norm(u); v = np.cross(nrm, u)
    t = np.linspace(0, 2 * np.pi, n, endpoint=False)
    return np.asarray(center, dtype=np.float64) + R * (np.cos(t)[:, None] * u + np.sin(t)[:, None] * v)


def edge_points(g, c0, r_lo, r_hi, polarity=1, n_rays=180, min_step=10.0, tol=2.5, blur=1.2):
    """points on a ring edge (strongest radial step of the wanted polarity per ray, kept when they agree with a circle).
    -> (points[k,2], fitted (cx, cy, r)) or (None, None)"""
    g = cv2.GaussianBlur(g, (0, 0), blur)
    h, w = g.shape; pts = []
    rs = np.arange(r_lo, r_hi, 0.5)
    for k in range(n_rays):
        a = 2 * np.pi * k / n_rays
        xs = c0[0] + rs * np.cos(a); ys = c0[1] + rs * np.sin(a)
        ok = (xs >= 1) & (xs < w - 2) & (ys >= 1) & (ys < h - 2)
        if ok.sum() < 8: continue
        v = cv2.remap(g, xs[ok].astype(np.float32)[None], ys[ok].astype(np.float32)[None], cv2.INTER_LINEAR)[0]
        d = (v[:-4] - v[4:]) * polarity
        i = int(np.argmax(d))
        if d[i] < min_step: continue
        pts.append((xs[ok][i + 2], ys[ok][i + 2]))
    if len(pts) < 12: return None, None
    P = np.array(pts); keep = np.ones(len(P), bool)
    for _ in range(3):
        cx, cy, r = circle_fit(P[keep])
        res = np.abs(np.hypot(P[:, 0] - cx, P[:, 1] - cy) - r)
        keep = res < max(tol, 2.5 * np.median(res[keep]))
        if keep.sum() < 10: return None, None
    return P[keep], circle_fit(P[keep])


def curve_dist(pts, curve):
    """distance of each point to a closed polyline (n x 2)"""
    a = curve; b = np.roll(curve, -1, axis=0)
    ab = b - a; L2 = (ab ** 2).sum(axis=1) + 1e-12
    out = np.empty(len(pts))
    for i, p in enumerate(pts):
        t = np.clip(((p - a) * ab).sum(axis=1) / L2, 0, 1)
        q = a + ab * t[:, None]
        out[i] = np.sqrt(((q - p) ** 2).sum(axis=1).min())
    return out


def signed_radial(pts, curve, c):
    """signed distance along the ray from c: positive when the point is outside the curve (curve assumed star-shaped about c)"""
    ang_c = np.arctan2(curve[:, 1] - c[1], curve[:, 0] - c[0]); r_c = np.hypot(curve[:, 0] - c[0], curve[:, 1] - c[1])
    o = np.argsort(ang_c); ang_c = ang_c[o]; r_c = r_c[o]
    ang_p = np.arctan2(pts[:, 1] - c[1], pts[:, 0] - c[0]); r_p = np.hypot(pts[:, 0] - c[0], pts[:, 1] - c[1])
    r_i = np.interp(ang_p, np.r_[ang_c[-1] - 2 * np.pi, ang_c, ang_c[0] + 2 * np.pi], np.r_[r_c[-1], r_c, r_c[0]])
    return r_p - r_i


def solve_pose(obs, eye0, ang0, fov, free=('x', 'y', 'z', 'pitch', 'yaw'), prior=None, loss_scale=1.5):
    """obs: [(ring3d points [n,3], image points [k,2]), ...]; start pose eye0 / ang0; -> eye, ang, rms px
    prior: optional dict name -> weight pulling that parameter back to its start value (px per unit)"""
    names = ['x', 'y', 'z', 'pitch', 'yaw', 'roll']
    p_full = np.array(list(eye0) + list(ang0), dtype=np.float64)
    idx = [names.index(k) for k in free]
    def unpack(q):
        p = p_full.copy(); p[idx] = q; return p[:3], p[3:]
    def resid(q):
        eye, ang = unpack(q); out = []
        for ring, pts in obs:
            pr = project(eye, ang, fov, ring)
            if (pr[:, 2] <= 1).any(): out.append(np.full(len(pts), 50.0)); continue
            c = pr[:, :2].mean(axis=0)
            out.append(signed_radial(pts, pr[:, :2], c))
        if prior:
            for k, wgt in prior.items():
                if k in free: out.append(np.array([(q[free.index(k)] - p_full[names.index(k)]) * wgt]))
        return np.concatenate(out)
    sol = least_squares(resid, p_full[idx], loss='soft_l1', f_scale=loss_scale, x_scale=[{'x': 1, 'y': 1, 'z': 2, 'pitch': 0.2, 'yaw': 0.5, 'roll': 0.5}[k] for k in free])
    eye, ang = unpack(sol.x)
    n = sum(len(p) for _, p in obs)
    r = resid(sol.x)[:n]
    return eye, ang, float(np.sqrt((r ** 2).mean()))
