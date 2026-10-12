"""Camera orientation of film frames from the straight lines of the rooms (walls, panels, tiles, tube rails).

The rooms are built on three perpendicular axes, so every straight edge that runs along one of them points at one of
three vanishing points; where those are in the picture gives the camera's rotation directly, frame by frame, with no
drift. World axes here are the ROOM axes (labelled X, Y, Z by the caller); a rotation is the matrix Rcw whose rows are
the camera's right, down and forward directions in room coordinates (x_cam = Rcw @ x_world).

    from orient import segments_of, init_rotation, refine, track, to_basis
    S = segments_of(n, 'E')                       # line segments of a moment image (640x400 pixel units)
    R0 = init_rotation(S)                          # from three vanishing points (labels arbitrary) -> relabel as needed
    R, info = refine(S, R0)                        # snap to the lines; info: counts per axis, rms angle (deg)
    T = track(first, last, R0)                     # [(n, moment, R, info), ...] following the camera through the frames
"""
import math
import numpy as np, cv2
from scipy.optimize import least_squares

F = 320.0 / (1.2 * math.tan(math.radians(60.0) / 2))       # 461.9 px on the 640x400 frame
CX, CY = 319.5, 199.5
_lsd = None


def load_gray(n, moment='E'):
    """moment image as float32 640x400 ('E' / 'L' = earlier / later moment, 'B' = the blended frame)"""
    if moment == 'B':
        g = cv2.imread('/home/claude/data/frames_hd/f%04d.jpg' % n, cv2.IMREAD_GRAYSCALE)
    else:
        g = cv2.imread('/home/claude/data/moments/%s/f%04d.jpg' % (moment, n), cv2.IMREAD_GRAYSCALE)
    return g


def segments_of(n, moment='E', min_len=22.0, img=None):
    """LSD line segments [k,4] (x1, y1, x2, y2) in 640x400 pixel units (detected on the 1280x800 image)"""
    global _lsd
    if _lsd is None: _lsd = cv2.createLineSegmentDetector(0)
    g = load_gray(n, moment) if img is None else img
    g = cv2.GaussianBlur(g, (0, 0), 1.0)
    L = _lsd.detect(g)[0]
    if L is None: return np.zeros((0, 4))
    L = L.reshape(-1, 4).astype(np.float64) * (640.0 / g.shape[1])
    ln = np.hypot(L[:, 2] - L[:, 0], L[:, 3] - L[:, 1])
    return L[ln >= min_len]


def _seg_dirs(S):
    """unit normals of the planes through the camera centre and each segment (camera coordinates), lengths"""
    a = np.c_[(S[:, 0] - CX) / F, (S[:, 1] - CY) / F, np.ones(len(S))]
    b = np.c_[(S[:, 2] - CX) / F, (S[:, 3] - CY) / F, np.ones(len(S))]
    nrm = np.cross(a, b); nrm /= np.linalg.norm(nrm, axis=1, keepdims=True)
    return nrm, np.hypot(S[:, 2] - S[:, 0], S[:, 3] - S[:, 1])


def _rodrigues(w):
    th = np.linalg.norm(w)
    if th < 1e-12: return np.eye(3)
    k = w / th; K = np.array([[0, -k[2], k[1]], [k[2], 0, -k[0]], [-k[1], k[0], 0]])
    return np.eye(3) + math.sin(th) * K + (1 - math.cos(th)) * K @ K


def orthonormal(R):
    """nearest rotation matrix"""
    U, _, Vt = np.linalg.svd(R)
    M = U @ Vt
    if np.linalg.det(M) < 0: M = U @ np.diag([1, 1, -1]) @ Vt
    return M


def misalign(S, R):
    """[k,3] angle in degrees between each segment and each room axis' direction as seen by rotation R
    (0 = the segment lies exactly on a line through that axis' vanishing point)"""
    nrm, ln = _seg_dirs(S)
    # a segment is consistent with world direction d when its interpretation-plane normal is perpendicular to R d
    return np.degrees(np.arcsin(np.clip(np.abs(nrm @ R), 0, 1)))        # columns of R = room axes in camera coordinates


def refine(S, R0, tol=3.0, iters=4, min_per_axis=3, prior=0.0):
    """rotation near R0 that lines the segments up with the three axes; -> (R, info).
    prior > 0 pulls the result back to R0 (residual units per degree), which keeps the part of the rotation that the
    visible lines cannot determine (only one axis family in view) at the prediction.
    info: n = lines used per axis, used, rms (deg), ok (two or more axis families seen), families"""
    R = orthonormal(R0); nrm, ln = _seg_dirs(S)
    info = dict(n=[0, 0, 0], rms=float('nan'), ok=False, used=0, families=0)
    if len(S) < 4: return R, info
    Rstart = R.copy()
    for it in range(iters):
        M = misalign(S, R); best = M.argmin(axis=1); val = M.min(axis=1)
        second = np.sort(M, axis=1)[:, 1]
        t = tol * (1.0 if it < 2 else 0.6)
        sel = (val < t) & (second > 1.5 * val + 1.0)
        if sel.sum() < 4: break
        n_sel = nrm[sel]; b_sel = best[sel]; w = np.sqrt(ln[sel] / 40.0)
        def resid(wv):
            Rn = _rodrigues(wv) @ R
            r = np.einsum('ij,ij->i', n_sel, Rn[:, b_sel].T) * w * 57.3
            if prior > 0:
                dR = Rn @ Rstart.T
                rv = np.array([dR[2, 1] - dR[1, 2], dR[0, 2] - dR[2, 0], dR[1, 0] - dR[0, 1]]) * 0.5 * 57.3
                r = np.concatenate([r, rv * prior])
            return r
        sol = least_squares(resid, np.zeros(3), loss='soft_l1', f_scale=1.0)
        R = orthonormal(_rodrigues(sol.x) @ R)
        M = misalign(S, R); val = M[np.arange(len(S)), best]
        cnt = [int(((best == a) & sel).sum()) for a in range(3)]
        fam = sum(c >= min_per_axis for c in cnt)
        info = dict(n=cnt, rms=float(np.sqrt(np.mean(val[sel] ** 2))), used=int(sel.sum()), ok=fam >= 2, families=fam)
    return R, info


def angle_between(Ra, Rb):
    """rotation angle in degrees between two orientations"""
    return float(np.degrees(np.arccos(np.clip((np.trace(Ra @ Rb.T) - 1) / 2, -1, 1))))


def init_rotation(S, seed=1):
    """rotation from the three strongest mutually perpendicular vanishing points (axis labels and signs arbitrary:
    column 0 = strongest group). Use relabel() to name the axes."""
    from vpfov import groups
    G = groups(S, tol=1.5, n=3, seed=seed)
    assert len(G) >= 2, 'need two vanishing points'
    dirs = []
    for v, inl in G:
        d = np.array([(v[0] - CX * v[2]) / F, (v[1] - CY * v[2]) / F, v[2]]) if abs(v[2]) > 1e-12 else np.array([v[0] / F, v[1] / F, 0.0])
        dirs.append(d / np.linalg.norm(d))
    a = dirs[0]; b = dirs[1] - a * (a @ dirs[1]); b /= np.linalg.norm(b); c = np.cross(a, b)
    R = np.c_[a, b, c]
    return refine(S, R, tol=4.0)[0]


def relabel(R, x=None, y=None, z=None):
    """rename / flip the room axes: give for two of x, y, z a camera-space direction hint among 'right', 'left',
    'up', 'down', 'forward', 'back' (the axis whose image direction is closest gets that label, pointing that way)"""
    hints = {'right': (1, 0, 0), 'left': (-1, 0, 0), 'down': (0, 1, 0), 'up': (0, -1, 0), 'forward': (0, 0, 1), 'back': (0, 0, -1)}
    cols = [R[:, k] for k in range(3)]; out = {}; used = set()
    for name, h in (('x', x), ('y', y), ('z', z)):
        if h is None: continue
        hv = np.array(hints[h], dtype=float)
        k = max((k for k in range(3) if k not in used), key=lambda k: abs(cols[k] @ hv))
        used.add(k); out[name] = cols[k] * (1 if cols[k] @ hv > 0 else -1)
    assert len(out) == 2, 'give two hints'
    if 'x' in out and 'y' in out: out['z'] = np.cross(out['x'], out['y'])
    elif 'y' in out and 'z' in out: out['x'] = np.cross(out['y'], out['z'])
    else: out['y'] = np.cross(out['z'], out['x'])
    return np.c_[out['x'], out['y'], out['z']]


def to_basis(R):
    """(forward, right, up) of the camera in room coordinates"""
    return R[2].copy(), R[0].copy(), -R[1].copy()


def track(first, last, R0, moments='EL', tol=3.0, max_step=9.0, verbose=False):
    """follow the orientation through frames first..last starting from R0 at the first moment.
    -> list of (frame, moment, R, info). info['ok']: two or more axis families were in view (a full measurement);
    otherwise the rotation is the prediction (the last turn rate continued), corrected by whatever lines were seen.
    max_step: largest believable turn between two consecutive moments in degrees (a jump beyond it is refused)."""
    out = []; R = orthonormal(R0); Rprev = None
    for n in range(first, last + 1):
        for mo in moments:
            S = segments_of(n, mo)
            pred = R
            if Rprev is not None:
                d = R @ Rprev.T
                if angle_between(R, Rprev) < max_step: pred = orthonormal(d @ R)        # bends turn at a steady rate
            best = None
            for Rc in ([R, pred] if pred is not R else [R]):
                Rn, info = refine(S, Rc, tol=tol, prior=0.03)
                step = angle_between(Rn, R)
                score = (info['families'] >= 2, info['used']) if step <= max_step else (False, -1)
                if best is None or score > best[0]: best = (score, Rn, info)
            score, Rn, info = best
            if score[1] < 0:                                   # nothing believable: keep the prediction
                Rn = pred; info = dict(info, ok=False, families=0)
            out.append((n, mo, Rn, info))
            if verbose:
                f, r, u = to_basis(Rn); print(n, mo, np.round(f, 3), np.round(u, 2), info)
            Rprev, R = R, Rn
    return out


def axis_label(v, tol_deg=1.5):
    """'+x', '-z', ... when v is within tol_deg of a room axis, else None"""
    i = int(np.argmax(np.abs(v)))
    if abs(v[i]) < math.cos(math.radians(tol_deg)): return None
    return ('+' if v[i] > 0 else '-') + 'xyz'[i]


def plateaus(T, tol_deg=1.5, min_len=4):
    """runs of moments in which the camera looks exactly along a room axis (the straight tube sections):
    -> [dict(a=(frame, moment), b=(frame, moment), forward='+x', up='+z', i0, i1)]"""
    runs = []; cur = None
    for i, (n, mo, R, info) in enumerate(T):
        f, r, u = to_basis(R); key = (axis_label(f, tol_deg), axis_label(u, tol_deg)) if info['ok'] else (None, None)
        if key[0] is None or key[1] is None: key = None
        if cur is not None and key == cur['key']: cur['i1'] = i
        else:
            if cur is not None and cur['key'] is not None and cur['i1'] - cur['i0'] + 1 >= min_len: runs.append(cur)
            cur = dict(key=key, i0=i, i1=i)
    if cur is not None and cur['key'] is not None and cur['i1'] - cur['i0'] + 1 >= min_len: runs.append(cur)
    return [dict(a=T[r['i0']][:2], b=T[r['i1']][:2], forward=r['key'][0], up=r['key'][1], i0=r['i0'], i1=r['i1']) for r in runs]
