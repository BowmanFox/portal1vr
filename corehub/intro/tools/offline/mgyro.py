"""Visual gyroscope on the separated moments of the film (60 per second).

gyro.py works on the blended video frames; in a fast turn those are double images and its steps go wrong. Here the
features are taken from the two moments of every frame separately (640x400, the line noise of the separation averaged
away), and the rotation is chained moment to moment: E(n) -> L(n) -> E(n+1) ...

    import mgyro
    R, k = mgyro.step((1000, 'E'), (1000, 'L'))       # rotation cam_b <- cam_a (camera axes right, down, forward), inliers
    seq = mgyro.sequence(998, 1010)                    # [(n, 'E'), (n, 'L'), ...]
"""
import math
import numpy as np, cv2

F = 320.0 / (1.2 * math.tan(math.radians(30.0))); CX, CY = 319.5, 199.5
K = np.array([[F, 0, CX], [0, F, CY], [0, 0, 1.0]])
_feat = {}
_sift = None


def image(n, mo):
    g = cv2.imread('/home/claude/data/moments/%s/f%04d.jpg' % (mo, n), cv2.IMREAD_GRAYSCALE)
    g = cv2.resize(g, (640, 400), interpolation=cv2.INTER_AREA)
    return g


def features(key):
    global _sift
    if key not in _feat:
        if _sift is None: _sift = cv2.SIFT_create(nfeatures=3000, contrastThreshold=0.012, edgeThreshold=12, sigma=1.2)
        g = image(*key)
        g2 = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8)).apply(g)
        kp, des = _sift.detectAndCompute(g2, None)
        pts = np.array([k.pt for k in kp], dtype=np.float64).reshape(-1, 2)
        _feat[key] = (pts, des)
        if len(_feat) > 600: _feat.pop(next(iter(_feat)))
    return _feat[key]


def matches(a, b, ratio=0.8):
    pa, da = features(a); pb, db = features(b)
    if da is None or db is None or len(pa) < 8 or len(pb) < 8: return np.zeros((0, 2)), np.zeros((0, 2))
    bf = cv2.BFMatcher(cv2.NORM_L2)
    m1 = bf.knnMatch(da, db, k=2); m2 = bf.knnMatch(db, da, k=2)
    back = {m.queryIdx: m.trainIdx for m, n in (x for x in m2 if len(x) == 2) if m.distance < ratio * n.distance}
    ia = []; ib = []
    for x in m1:
        if len(x) < 2: continue
        m, n = x
        if m.distance < ratio * n.distance and back.get(m.trainIdx) == m.queryIdx: ia.append(m.queryIdx); ib.append(m.trainIdx)
    return pa[ia], pb[ib]


def step(a, b, thresh=0.8):
    """-> (R cam_b <- cam_a, inliers, matches)"""
    pa, pb = matches(a, b)
    if len(pa) < 12: return None, 0, len(pa)
    E, mask = cv2.findEssentialMat(pa, pb, K, method=cv2.RANSAC, prob=0.9999, threshold=thresh)
    if E is None or E.shape != (3, 3): return None, 0, len(pa)
    n, R, t, mask2 = cv2.recoverPose(E, pa, pb, K, mask=mask)
    return R, int(n), len(pa)


def sequence(first, last):
    return [(n, mo) for n in range(first, last + 1) for mo in 'EL']


if __name__ == '__main__':
    import sys
    a, b = int(sys.argv[1]), int(sys.argv[2])
    seq = sequence(a, b); Rc = np.eye(3)
    for x, y in zip(seq, seq[1:]):
        R, k, m = step(x, y)
        if R is None: print(x, y, 'failed', m); continue
        Rc = R @ Rc
        ang = math.degrees(math.acos(max(-1, min(1, (np.trace(R) - 1) / 2))))
        tot = math.degrees(math.acos(max(-1, min(1, (np.trace(Rc) - 1) / 2))))
        print('%d%s -> %d%s  matches %4d inliers %4d  step %.2f deg  total %.1f  forward now %s' % (x[0], x[1], y[0], y[1], m, k, ang, tot, np.round(Rc[2], 3)))
