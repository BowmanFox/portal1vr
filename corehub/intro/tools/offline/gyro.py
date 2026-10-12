"""Frame-to-frame camera rotation of the film from matched image features (a "visual gyroscope").

Uses the keypoints and verified matches that COLMAP stored for a shot (/home/claude/sfm/<name>/db.db, blended frames):
for two frames the essential matrix gives the relative rotation, which is reliable even where the translation is not.
Chaining the steps follows the camera through bends where too few room lines are visible for orient.py; the drift
of the chain is removed again at every straight section, where orient.py measures the orientation absolutely.

    G = Gyro('rust2')
    R, n, t = G.step(1000, 1001)            # rotation cam(1001) <- cam(1000) (camera axes: right, down, forward), inliers, direction of motion
    Rs = G.chain(998, 1010, R_start)        # {frame: Rcw} carried on from R_start at frame 998 (Rcw: x_cam = Rcw @ x_room)
"""
import math
import numpy as np, cv2

F_HD = 640.0 / (1.2 * math.tan(math.radians(60.0) / 2))       # 923.76 px on the 1280x800 frames


class Gyro:
    def __init__(self, name, root='/home/claude/sfm'):
        import pycolmap
        self.db = pycolmap.Database.open('%s/%s/db.db' % (root, name))
        self.ids = {}
        for im in self.db.read_all_images():
            self.ids[int(im.name[1:5])] = im.image_id
        self._kp = {}

    def keypoints(self, n):
        if n not in self._kp:
            k = self.db.read_keypoints(self.ids[n]); self._kp[n] = np.asarray(k)[:, :2].astype(np.float64)
        return self._kp[n]

    def matches(self, a, b):
        """matched pixel coordinates (1280x800) of frames a and b: (pa [k,2], pb [k,2]); empty when the pair was not matched"""
        ia, ib = self.ids[a], self.ids[b]
        try: tv = self.db.read_two_view_geometry(ia, ib)
        except Exception: return np.zeros((0, 2)), np.zeros((0, 2))
        m = np.asarray(tv.inlier_matches)
        if m.size == 0: return np.zeros((0, 2)), np.zeros((0, 2))
        return self.keypoints(a)[m[:, 0]], self.keypoints(b)[m[:, 1]]

    def step(self, a, b, thresh=1.0):
        """-> (R [3,3] cam_b <- cam_a, number of inliers, unit translation direction in cam_b axes) or (None, 0, None)"""
        pa, pb = self.matches(a, b)
        if len(pa) < 12: return None, len(pa), None
        K = np.array([[F_HD, 0, 640.0], [0, F_HD, 400.0], [0, 0, 1.0]])
        E, mask = cv2.findEssentialMat(pa, pb, K, method=cv2.RANSAC, prob=0.9999, threshold=thresh)
        if E is None or E.shape != (3, 3): return None, 0, None
        n, R, t, mask2 = cv2.recoverPose(E, pa, pb, K, mask=mask)
        return R, int(n), t.ravel()

    def chain(self, first, last, R_start, max_gap=3):
        """orientations Rcw for frames first..last, starting from R_start at `first` (forward when last > first,
        backward otherwise). A frame whose step fails is bridged with a step over 2 or 3 frames when possible."""
        out = {first: R_start.copy()}; d = 1 if last >= first else -1
        n = first
        while n != last:
            done = False
            for gap in range(1, max_gap + 1):
                m = n + d * gap
                if (d > 0 and m > last) or (d < 0 and m < last) or m not in self.ids: continue
                a, b = (n, m) if d > 0 else (m, n)
                R, k, t = self.step(a, b)
                if R is None or k < 15: continue
                Rn = (R @ out[n]) if d > 0 else (R.T @ out[n])
                for j in range(1, gap + 1):            # spread the turn evenly over skipped frames
                    out[n + d * j] = _slerp(out[n], Rn, j / gap)
                n = m; done = True; break
            if not done:
                out[n + d] = out[n].copy(); n += d
        return out


def _slerp(Ra, Rb, f):
    d = Rb @ Ra.T
    ang = math.acos(max(-1.0, min(1.0, (np.trace(d) - 1) / 2)))
    if ang < 1e-9: return Ra.copy()
    ax = np.array([d[2, 1] - d[1, 2], d[0, 2] - d[2, 0], d[1, 0] - d[0, 1]]) / (2 * math.sin(ang))
    K = np.array([[0, -ax[2], ax[1]], [ax[2], 0, -ax[0]], [-ax[1], ax[0], 0]])
    Rf = np.eye(3) + math.sin(ang * f) * K + (1 - math.cos(ang * f)) * K @ K
    return Rf @ Ra
