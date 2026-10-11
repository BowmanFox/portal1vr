"""Measure circular rings (tube collars, irises) in video frames or renders.
fit_ring(gray, c0, r_lo, r_hi, polarity) samples rays from a centre guess, takes the strongest radial brightness
step of the wanted polarity on each ray and fits a circle with outlier rejection.
    polarity +1: bright inside -> dark outside (outer edge of a light ring on a dark background)
             -1: dark inside -> bright outside (inner edge of a light ring)"""
import numpy as np, cv2


def gray_frame(n, frames='/home/claude/data/frames/f%04d.jpg'):
    return cv2.cvtColor(cv2.imread(frames % n), cv2.COLOR_BGR2GRAY).astype(np.float32)


def frame_of(t):
    return int(round(t * 30000 / 1001))


def circle_fit(P):
    A = np.c_[2 * P[:, 0], 2 * P[:, 1], np.ones(len(P))]; b = (P ** 2).sum(axis=1)
    (cx, cy, c), *_ = np.linalg.lstsq(A, b, rcond=None)
    return cx, cy, float(np.sqrt(max(c + cx * cx + cy * cy, 0)))


def fit_ring(g, c0, r_lo, r_hi, polarity=1, n_rays=180, min_step=12.0, iters=3, tol=3.0, blur=1.2):
    """-> dict(cx, cy, r, n, rms) or None"""
    g = cv2.GaussianBlur(g, (0, 0), blur)
    h, w = g.shape
    pts = []
    rs = np.arange(r_lo, r_hi, 0.5)
    for k in range(n_rays):
        a = 2 * np.pi * k / n_rays
        xs = c0[0] + rs * np.cos(a); ys = c0[1] + rs * np.sin(a)
        ok = (xs >= 1) & (xs < w - 2) & (ys >= 1) & (ys < h - 2)
        if ok.sum() < 8: continue
        v = cv2.remap(g, xs[ok].astype(np.float32)[None], ys[ok].astype(np.float32)[None], cv2.INTER_LINEAR)[0]
        d = (v[:-4] - v[4:]) * polarity            # brightness drop over 2 px going outward
        i = int(np.argmax(d))
        if d[i] < min_step: continue
        pts.append((xs[ok][i + 2], ys[ok][i + 2]))
    if len(pts) < 12: return None
    P = np.array(pts); keep = np.ones(len(P), bool)
    for _ in range(iters):
        cx, cy, r = circle_fit(P[keep])
        res = np.abs(np.hypot(P[:, 0] - cx, P[:, 1] - cy) - r)
        keep = res < max(tol, 2.5 * np.median(res[keep]))
        if keep.sum() < 10: return None
    cx, cy, r = circle_fit(P[keep])
    res = np.abs(np.hypot(P[keep, 0] - cx, P[keep, 1] - cy) - r)
    return dict(cx=float(cx), cy=float(cy), r=float(r), n=int(keep.sum()), rms=float(np.sqrt((res ** 2).mean())))


def radial_profile(g, cx, cy, R, rel=None, angles=None, blur=0.0):
    """median brightness along circles of radius rel*R about (cx, cy); angles in degrees (default: all, 3-degree steps)"""
    if blur: g = cv2.GaussianBlur(g, (0, 0), blur)
    rel = np.arange(0.30, 1.16, 0.02) if rel is None else np.asarray(rel)
    angles = np.arange(0, 360, 3) if angles is None else np.asarray(angles)
    h, w = g.shape; out = []
    for rr in rel:
        x = cx + rr * R * np.cos(np.radians(angles)); y = cy + rr * R * np.sin(np.radians(angles))
        ok = (x >= 0) & (x < w - 1) & (y >= 0) & (y < h - 1)
        out.append(float(np.median(g[np.round(y[ok]).astype(int), np.round(x[ok]).astype(int)])) if ok.sum() > 5 else -1.0)
    return rel, np.array(out)
