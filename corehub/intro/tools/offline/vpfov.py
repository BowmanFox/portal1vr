"""Field of view of the film camera from vanishing points: line segments of a frame are grouped into three mutually
orthogonal directions (a tiled room), which fixes the focal length when the principal point is the frame centre.
usage: vpfov.py t [t ...] [--show] [--mask x0,y0,x1,y1]
For a camera with QAngle fov F (horizontal at 4:3): f_px = 320 / (1.2 * tan(F / 2)) on the 640x400 frame."""
import sys, math, argparse, itertools
import numpy as np, cv2
from ringtrack import gray_frame, frame_of

C = np.array([320.0, 200.0])


def segments(g, min_len=28):
    lsd = cv2.createLineSegmentDetector(0)
    L = lsd.detect(cv2.GaussianBlur(g, (0, 0), 0.8).astype(np.uint8))[0]
    if L is None: return np.zeros((0, 4))
    L = L.reshape(-1, 4)
    ln = np.hypot(L[:, 2] - L[:, 0], L[:, 3] - L[:, 1])
    return L[ln >= min_len]


def line_h(seg):
    p = np.array([seg[0], seg[1], 1.0]); q = np.array([seg[2], seg[3], 1.0])
    l = np.cross(p, q); return l / np.hypot(l[0], l[1])


def vp_of(lines, w):
    """least-squares intersection of homogeneous lines (rows), weights w"""
    A = lines * w[:, None]
    _, _, vt = np.linalg.svd(A)
    return vt[-1]


def seg_err(seg, v):
    """angle (deg) between a segment and the line from its midpoint to vanishing point v (homogeneous)"""
    m = np.array([(seg[0] + seg[2]) / 2, (seg[1] + seg[3]) / 2]); d = np.array([seg[2] - seg[0], seg[3] - seg[1]])
    if abs(v[2]) > 1e-9 * max(abs(v[0]), abs(v[1]), 1): e = v[:2] / v[2] - m
    else: e = v[:2]
    c = abs(d @ e) / (np.linalg.norm(d) * np.linalg.norm(e) + 1e-12)
    return math.degrees(math.acos(min(1.0, c)))


def errs(S, v):
    """angle (deg) between each segment and the line from its midpoint to the vanishing point v (homogeneous), vectorised"""
    m = np.c_[(S[:, 0] + S[:, 2]) / 2, (S[:, 1] + S[:, 3]) / 2]; d = np.c_[S[:, 2] - S[:, 0], S[:, 3] - S[:, 1]]
    if abs(v[2]) > 1e-9 * max(abs(v[0]), abs(v[1]), 1): e = v[:2] / v[2] - m
    else: e = np.tile(v[:2], (len(S), 1))
    c = np.abs((d * e).sum(axis=1)) / (np.linalg.norm(d, axis=1) * np.linalg.norm(e, axis=1) + 1e-12)
    return np.degrees(np.arccos(np.minimum(1.0, c)))


def groups(S, iters=1500, tol=1.5, seed=1, n=3):
    """RANSAC: up to n vanishing points with many supporting segments; -> [(vp, inlier idx)]"""
    rng = np.random.default_rng(seed)
    Lh = np.array([line_h(s) for s in S]); ln = np.hypot(S[:, 2] - S[:, 0], S[:, 3] - S[:, 1])
    left = np.ones(len(S), bool); out = []
    for _ in range(n):
        idx = np.where(left)[0]
        if len(idx) < 6: break
        best = None
        for _ in range(iters):
            i, j = rng.choice(idx, 2, replace=False)
            v = np.cross(Lh[i], Lh[j])
            if np.linalg.norm(v) < 1e-9: continue
            inl = idx[errs(S[idx], v) < tol]; score = ln[inl].sum()
            if best is None or score > best[0]: best = (score, inl)
        inl = best[1]
        for _ in range(3):
            if len(inl) < 2: break
            v = vp_of(Lh[inl], ln[inl])
            cand = np.where(left)[0]
            inl = cand[errs(S[cand], v) < tol]
        if len(inl) < 4: break
        out.append((v, inl)); left[inl] = False
    return out


def focal(v1, v2):
    """f from two vanishing points of orthogonal directions (None when not consistent)"""
    a = v1[:2] / v1[2] - C; b = v2[:2] / v2[2] - C
    f2 = -(a @ b)
    return math.sqrt(f2) if f2 > 0 else None


if __name__ == '__main__':
    ap = argparse.ArgumentParser(); ap.add_argument('times', nargs='+', type=float); ap.add_argument('--show', action='store_true'); ap.add_argument('--mask')
    ap.add_argument('--tol', type=float, default=1.5); ap.add_argument('--minlen', type=float, default=28)
    a = ap.parse_args()
    for t in a.times:
        g = gray_frame(frame_of(t))
        S = segments(g, a.minlen)
        if a.mask:
            x0, y0, x1, y1 = (float(x) for x in a.mask.split(','))
            mx = (S[:, 0] + S[:, 2]) / 2; my = (S[:, 1] + S[:, 3]) / 2
            S = S[(mx >= x0) & (mx <= x1) & (my >= y0) & (my <= y1)]
        G = groups(S, tol=a.tol)
        print('t %.3f: %d segments' % (t, len(S)))
        for v, inl in G:
            pv = v[:2] / v[2] if abs(v[2]) > 1e-12 else (float('inf'), float('inf'))
            print('   vanishing point (%.0f, %.0f)  %d segments' % (pv[0], pv[1], len(inl)))
        for (v1, i1), (v2, i2) in itertools.combinations(G, 2):
            f = focal(v1, v2)
            if f: print('   f = %.1f px  -> fov %.1f' % (f, 2 * math.degrees(math.atan(320 / 1.2 / f))))
        if a.show:
            im = cv2.cvtColor(g.astype(np.uint8), cv2.COLOR_GRAY2BGR)
            for k, (v, inl) in enumerate(G):
                col = [(0, 0, 255), (0, 255, 0), (255, 128, 0)][k]
                for i in inl: cv2.line(im, (int(S[i, 0]), int(S[i, 1])), (int(S[i, 2]), int(S[i, 3])), col, 1)
            cv2.imwrite('out/vp_%07.3f.jpg' % t, cv2.resize(im, (1280, 800), interpolation=cv2.INTER_LANCZOS4)); print('   out/vp_%07.3f.jpg' % t)
