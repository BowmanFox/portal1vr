"""Working with structure-from-motion results of the film (pycolmap reconstructions made by /home/claude/sfm/run_sfm.py).

A reconstruction gives, for every registered image, the camera of that moment of the film, and a sparse cloud of
3D points (wall textures, edges). Coordinates are arbitrary (any scale, any orientation) until align() maps them to
map coordinates with a similarity transform. Image names: f1234E.jpg / f1234L.jpg = the earlier / later of the two
moments blended into video frame 1234 (see fieldsplit.py); video frame n is at t = n * 1001 / 30000 s, its later
moment 1/59.94 s after that.

    from sfmtools import Recon
    R = Recon('rustm', 0)                 # /home/claude/sfm/rustm/sparse/0
    R.keys                                 # sorted [(frame, 'E'|'L'), ...] of the registered images
    eye, (f, r, u) = R.pose(1000, 'E')     # camera centre and forward / right / up unit vectors (SfM or map coordinates)
    R.project(P, 1000, 'E')                # points -> pixels of the 640x400 frame (x, y, depth)
    R.triangulate([(1000, 'E', 331.5, 120.0), (1010, 'L', 352.0, 97.5)])   # same feature seen in several images -> 3D
    R.points, R.colors                     # the cloud (good points only)
    R.set_transform(scale, A, T)           # from here on everything is in map coordinates: X_map = scale * A @ X + T
    R.qangle(1000, 'E')                    # Source QAngle (pitch, yaw, roll) of the camera (after set_transform)
"""
import math, os
import numpy as np

F640 = 320.0 / (1.2 * math.tan(math.radians(60.0) / 2))       # focal length in pixels of the 640x400 frame at fov 60


def frame_time(n, moment='E'):
    return n * 1001 / 30000.0 + (1001 / 60000.0 if moment == 'L' else 0.0)


def qangle_from_basis(f, r, u):
    """Source QAngle (pitch, yaw, roll) of a camera with forward f, right r, up u"""
    pitch = -math.degrees(math.asin(max(-1.0, min(1.0, f[2]))))
    yaw = math.degrees(math.atan2(f[1], f[0]))
    roll = math.degrees(math.atan2(-r[2], u[2]))
    if abs(f[2]) > 0.99999:                     # looking straight up / down: yaw and roll share one freedom; use roll 0
        roll = 0.0
        yaw = math.degrees(math.atan2(-u[1], -u[0])) if f[2] > 0 else math.degrees(math.atan2(u[1], u[0]))
    return pitch, yaw, roll


def basis_from_qangle(pitch, yaw, roll):
    sp, cp = math.sin(math.radians(pitch)), math.cos(math.radians(pitch))
    sy, cy = math.sin(math.radians(yaw)), math.cos(math.radians(yaw))
    sr, cr = math.sin(math.radians(roll)), math.cos(math.radians(roll))
    f = np.array([cp * cy, cp * sy, -sp])
    r = np.array([-sr * sp * cy + cr * sy, -sr * sp * sy - cr * cy, -sr * cp])
    u = np.array([cr * sp * cy + sr * sy, cr * sp * sy - sr * cy, cr * cp])
    return f, r, u


class Recon:
    def __init__(self, name, model=0, min_track=3, max_error=2.0, root='/home/claude/sfm'):
        import pycolmap
        self.path = os.path.join(root, name, 'sparse', str(model))
        rec = pycolmap.Reconstruction(self.path)
        self.rec = rec
        self.cams = {}
        for im in rec.images.values():
            if hasattr(im, 'has_pose') and not im.has_pose: continue
            nm = im.name; n = int(nm[1:5]); mo = nm[5] if nm[5] in 'EL' else 'E'
            M = im.cam_from_world().matrix() if callable(getattr(im, 'cam_from_world', None)) else im.cam_from_world.matrix()
            Rm = np.array(M)[:3, :3]; t = np.array(M)[:3, 3]
            self.cams[(n, mo)] = (-Rm.T @ t, Rm[2].copy(), Rm[0].copy(), -Rm[1].copy())       # centre, forward, right, up
        self.keys = sorted(self.cams)
        cam = next(iter(rec.cameras.values()))
        self.f = float(cam.params[0]) * 640.0 / cam.width          # focal length on the 640x400 frame
        P, C, E, T = [], [], [], []
        for p in rec.points3D.values():
            P.append(p.xyz); C.append(p.color); E.append(p.error); T.append(p.track.length())
        P = np.array(P); T = np.array(T); E = np.array(E)
        good = (T >= min_track) & (E <= max_error)
        self.points = P[good]; self.colors = np.array(C)[good] / 255.0; self.track_len = T[good]
        self.scale, self.A, self.T = 1.0, np.eye(3), np.zeros(3)

    # ------------------------------------------------------------------ coordinates
    def set_transform(self, scale, A, T):
        """switch to map coordinates: X_map = scale * A @ X_sfm + T (A: rotation matrix, det +1)"""
        A = np.asarray(A, dtype=float); T = np.asarray(T, dtype=float)
        assert abs(np.linalg.det(A) - 1) < 1e-6 and np.allclose(A @ A.T, np.eye(3), atol=1e-6), 'A must be a rotation'
        inv = lambda X: ((np.atleast_2d(X) - self.T) @ self.A) / self.scale        # back to raw SfM coordinates
        raw_pts = inv(self.points)
        raw = {k: (inv(c)[0], self.A.T @ f, self.A.T @ r, self.A.T @ u) for k, (c, f, r, u) in self.cams.items()}
        self.scale, self.A, self.T = float(scale), A, T
        fw = lambda X: self.scale * (np.atleast_2d(X) @ A.T) + T
        self.points = fw(raw_pts)
        self.cams = {k: (fw(c)[0], A @ f, A @ r, A @ u) for k, (c, f, r, u) in raw.items()}

    def pose(self, n, moment='E'):
        c, f, r, u = self.cams[(n, moment)]
        return c, (f, r, u)

    def qangle(self, n, moment='E'):
        c, f, r, u = self.cams[(n, moment)]
        return qangle_from_basis(f, r, u)

    def has(self, n, moment='E'):
        return (n, moment) in self.cams

    # ------------------------------------------------------------------ geometry
    def project(self, P, n, moment='E'):
        """points [k,3] -> [k,3] (x, y on the 640x400 frame, depth along the view axis)"""
        c, f, r, u = self.cams[(n, moment)]
        Q = np.atleast_2d(np.asarray(P, dtype=float)) - c
        d = Q @ f; dd = np.where(np.abs(d) < 1e-9, 1e-9, d)
        return np.c_[320.0 + self.f * (Q @ r) / dd, 200.0 - self.f * (Q @ u) / dd, d]

    def ray(self, n, moment, px, py):
        """pixel of the 640x400 frame -> (camera centre, unit direction)"""
        c, f, r, u = self.cams[(n, moment)]
        d = f + r * ((px - 320.0) / self.f) + u * ((200.0 - py) / self.f)
        return c, d / np.linalg.norm(d)

    def triangulate(self, obs):
        """obs: [(frame, moment, px, py), ...] (640x400 pixels) of one feature in two or more images -> (point, rms px)"""
        A = np.zeros((3, 3)); b = np.zeros(3)
        for n, mo, px, py in obs:
            c, d = self.ray(n, mo, px, py)
            M = np.eye(3) - np.outer(d, d); A += M; b += M @ c
        X = np.linalg.solve(A, b)
        err = [np.hypot(*(self.project(X, n, mo)[0, :2] - (px, py))) for n, mo, px, py in obs]
        return X, float(np.sqrt(np.mean(np.square(err))))

    def visible_points(self, n, moment='E', margin=0):
        """cloud points in front of the camera inside the frame: (pixels [k,3], indices)"""
        pr = self.project(self.points, n, moment)
        ok = (pr[:, 2] > 0) & (pr[:, 0] >= -margin) & (pr[:, 0] < 640 + margin) & (pr[:, 1] >= -margin) & (pr[:, 1] < 400 + margin)
        return pr[ok], np.where(ok)[0]

    def depth_near(self, n, moment, px, py, radius=12.0):
        """median depth and 3D position of the cloud points that project within `radius` pixels of (px, py); None if none"""
        pr, idx = self.visible_points(n, moment)
        d = np.hypot(pr[:, 0] - px, pr[:, 1] - py); m = d <= radius
        if m.sum() == 0: return None
        return float(np.median(pr[m, 2])), np.median(self.points[idx[m]], axis=0), int(m.sum())

    # ------------------------------------------------------------------ planes
    def planes(self, max_planes=8, tol=None, min_points=150, seed=0, iters=600):
        """dominant planes of the cloud by RANSAC -> [dict(normal, d, n, centre, extent, color, idx)], n.x = d"""
        rng = np.random.default_rng(seed)
        P = self.points; left = np.ones(len(P), bool); out = []
        if tol is None:
            ext = np.percentile(P, 95, axis=0) - np.percentile(P, 5, axis=0); tol = 0.006 * float(np.linalg.norm(ext))
        for _ in range(max_planes):
            idx = np.where(left)[0]
            if len(idx) < min_points: break
            best = None
            for _ in range(iters):
                a, b, c = P[rng.choice(idx, 3, replace=False)]
                nrm = np.cross(b - a, c - a); ln = np.linalg.norm(nrm)
                if ln < 1e-9: continue
                nrm /= ln; d = nrm @ a
                inl = idx[np.abs(P[idx] @ nrm - d) < tol]
                if best is None or len(inl) > len(best[0]): best = (inl, nrm, d)
            inl, nrm, d = best
            if len(inl) < min_points: break
            for _ in range(2):                                   # refine by least squares
                c0 = P[inl].mean(axis=0); _, _, vt = np.linalg.svd(P[inl] - c0); nrm = vt[-1]; d = nrm @ c0
                inl = idx[np.abs(P[idx] @ nrm - d) < tol]
            Q = P[inl]
            out.append(dict(normal=nrm, d=float(d), n=len(inl), centre=Q.mean(axis=0), lo=np.percentile(Q, 2, axis=0), hi=np.percentile(Q, 98, axis=0),
                            color=self.colors[inl].mean(axis=0), idx=inl, rms=float(np.sqrt(np.mean((Q @ nrm - d) ** 2)))))
            left[inl] = False
        return out

    # ------------------------------------------------------------------ pictures
    def overlay(self, n, moment='E', size=(640, 400), radius=1):
        """the moment's image with the cloud points drawn on it (green dots): do the cameras and the cloud agree?"""
        from PIL import Image, ImageDraw
        p = '/home/claude/data/moments/%s/f%04d.jpg' % (moment, n)
        im = Image.open(p).convert('RGB').resize(size)
        d = ImageDraw.Draw(im); sx, sy = size[0] / 640.0, size[1] / 400.0
        pr, idx = self.visible_points(n, moment)
        for x, y, z in pr: d.ellipse((x * sx - radius, y * sy - radius, x * sx + radius, y * sy + radius), fill=(0, 255, 0))
        return im

    def track(self):
        """[(t, frame, moment, eye, (pitch, yaw, roll)), ...] of every registered moment, in time order"""
        out = []
        for (n, mo) in sorted(self.cams, key=lambda k: frame_time(*k)):
            c, f, r, u = self.cams[(n, mo)]
            out.append((frame_time(n, mo), n, mo, c.copy(), qangle_from_basis(f, r, u)))
        return out


def rotation_from_axes(x_axis=None, y_axis=None, z_axis=None):
    """rotation matrix A (rows = the SfM-space directions that become map +X, +Y, +Z); give two of the three,
    the second one is made perpendicular to the first, the third follows (right-handed)"""
    ax = {'x': x_axis, 'y': y_axis, 'z': z_axis}
    given = [k for k in 'xyz' if ax[k] is not None]
    assert len(given) == 2, 'give exactly two axes'
    a = np.asarray(ax[given[0]], dtype=float); a /= np.linalg.norm(a)
    b = np.asarray(ax[given[1]], dtype=float); b = b - a * (a @ b); b /= np.linalg.norm(b)
    v = {given[0]: a, given[1]: b}
    third = [k for k in 'xyz' if k not in given][0]
    if third == 'z': v['z'] = np.cross(v['x'], v['y'])
    elif third == 'x': v['x'] = np.cross(v['y'], v['z'])
    else: v['y'] = np.cross(v['z'], v['x'])
    A = np.array([v['x'], v['y'], v['z']])
    assert abs(np.linalg.det(A) - 1) < 1e-6
    return A
