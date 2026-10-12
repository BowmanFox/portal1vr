"""Camera positions through a bend by bundle adjustment with the orientations held fixed.

ride.py knows every frame's orientation (lines + turn angles) and the speed inside the straights; what the tube does
between two straights is measured here: the matched features of the frames around the bend are triangulated and the
camera positions adjusted until every feature falls on its pixels in every frame it is seen in. The positions of the
straight before the bend are held (they set the origin and the scale); the frames of the bend and of the straight after
it are free.

    import bendba
    res = bendba.solve(S, 998)            # S: ride.Shot with orientation, speeds and path; bend key = first frame of the bend
    res['C']                              # {frame: position}, solver units, same axes as S.P
    res['fit']                            # line-arc-line through them: dict(radius, lead, tail, rms)
"""
import math
import numpy as np
from scipy.optimize import least_squares
from scipy.sparse import lil_matrix
import ride as RD
from gyro import F_HD


def _proj(X, C, R):
    q = (X - C) @ R.T
    z = np.where(np.abs(q[:, 2]) < 1e-9, 1e-9, q[:, 2])
    return np.stack([F_HD * q[:, 0] / z + 640.0, F_HD * q[:, 1] / z + 400.0], 1), q[:, 2]


def _triangulate(obs, C, R):
    A = np.zeros((3, 3)); b = np.zeros(3)
    for n, p in obs:
        d = R[n].T @ np.array([(p[0] - 640.0) / F_HD, (p[1] - 400.0) / F_HD, 1.0]); d /= np.linalg.norm(d)
        M = np.eye(3) - np.outer(d, d); A += M; b += M @ C[n]
    try: return np.linalg.solve(A + 1e-10 * np.eye(3), b)
    except np.linalg.LinAlgError: return None


def _skew_rows(w):
    """[k,3] small rotation vectors -> [k,3,3] matrices I + [w]x"""
    k = len(w); M = np.zeros((k, 3, 3))
    M[:, 0, 0] = 1; M[:, 1, 1] = 1; M[:, 2, 2] = 1
    M[:, 0, 1] = -w[:, 2]; M[:, 0, 2] = w[:, 1]; M[:, 1, 0] = w[:, 2]; M[:, 1, 2] = -w[:, 0]; M[:, 2, 0] = -w[:, 1]; M[:, 2, 1] = w[:, 0]
    return M


def adjust(frames, fixed, C0, R, tracks, v, straight=None, basis=None, rounds=3, step_prior=0.12, acc_sigma=0.35, verbose=True, max_tracks=900,
           min_len=3, rot_sigma=0.4, rot_free=None, huber=2.0):
    """Bundle adjustment with (nearly) fixed orientations.
    frames: frame numbers in order; fixed: those whose position is held; C0: {n: start position}; R: {n: Rcw};
    tracks: [{frame: (x, y)}] in 1280x800 pixels; v: {n: expected step n -> n+1} (sets the size of the smoothness and
    step priors); straight: (first, last, axis) of frames that must lie on one line along `axis` with the steps v;
    basis: rows spanning the plane the free cameras may move in (None = free in space);
    rot_free: frames whose orientation may be corrected by about rot_sigma degrees (default: none).
    -> (C {n: position}, R {n: Rcw}, points [k,3], report dict)"""
    fs = set(frames); free = [n for n in frames if n not in set(fixed)]
    rfree = [n for n in frames if rot_free and n in set(rot_free)]
    obs_all = []
    for tr in tracks:
        obs = [(n, p) for n, p in tr.items() if n in fs]
        if len(obs) >= min_len: obs_all.append(obs)
    if len(obs_all) > max_tracks:
        # keep every frame supplied: long tracks first, but only while one of their frames still has few observations
        cnt = {n: 0 for n in frames}; sel = []; per = max(40, 3 * max_tracks // max(len(frames), 1))
        for o in sorted(obs_all, key=lambda o: -len(o)):
            if any(cnt[n] < per for n, p in o):
                sel.append(o)
                for n, p in o: cnt[n] += 1
        obs_all = sel
    C = {n: np.array(C0[n], dtype=float) for n in frames}; R = {n: np.array(R[n], dtype=float) for n in frames}
    fi = {n: i for i, n in enumerate(free)}; ri = {n: i for i, n in enumerate(rfree)}
    B = np.eye(3) if basis is None else np.asarray(basis, dtype=float); dof = len(B)
    base = np.array([C0[n] for n in free], dtype=float)
    rep = {}; XX = None; nc = len(free) * dof; nr = len(rfree) * 3
    for rnd in range(rounds):
        pts = []; keep = []
        for obs in obs_all:
            X = _triangulate(obs, C, R)
            if X is None: continue
            ok = True; errs = []
            for n, p in obs:
                xy, z = _proj(X[None, :], C[n], R[n])
                if z[0] <= 1e-6: ok = False; break
                errs.append(float(np.hypot(*(xy[0] - p))))
            if ok and np.median(errs) < (80.0 if rnd == 0 else 12.0): pts.append(X); keep.append(obs)
        if len(pts) < 20:
            rep['failed'] = 'too few points (%d)' % len(pts); break
        X = np.array(pts); M = len(X)
        nobs = sum(len(o) for o in keep)
        oi = np.zeros(nobs, int); oj = np.zeros(nobs, int); op = np.zeros((nobs, 2)); Rm = np.zeros((nobs, 3, 3)); fixedC = np.zeros((nobs, 3)); isfree = np.zeros(nobs, bool)
        orr = np.full(nobs, -1)
        k = 0
        for j, obs in enumerate(keep):
            for n, p in obs:
                oj[k] = j; op[k] = p; Rm[k] = R[n]
                if n in fi: oi[k] = fi[n]; isfree[k] = True
                else: fixedC[k] = C[n]
                if n in ri: orr[k] = ri[n]
                k += 1
        hasr = orr >= 0
        triples = [(a, b, c) for a, b, c in zip(frames, frames[1:], frames[2:]) if (a in fi or b in fi or c in fi) and c - a == 2]
        sline = [(n, n + 1) for n in range(straight[0], straight[1])] if straight else []
        sline = [(a, b) for a, b in sline if a in fs and b in fs and (a in fi or b in fi)]
        ax = np.asarray(straight[2], dtype=float) if straight else None
        pairs = [(a, b) for a, b in zip(frames, frames[1:]) if b - a == 1 and (a in fi or b in fi) and a in v and (a, b) not in set(sline)]
        def cam(cc, n): return cc[fi[n]] if n in fi else C[n]
        def unpack(x):
            return x[:nc].reshape(len(free), dof) @ B + base, x[nc:nc + nr].reshape(len(rfree), 3), x[nc + nr:].reshape(M, 3)
        def resid(x):
            cc, ww, Xp = unpack(x)
            Cs = np.where(isfree[:, None], cc[oi], fixedC)
            q = np.einsum('kij,kj->ki', Rm, Xp[oj] - Cs)
            if nr:
                W = _skew_rows(ww)
                q = np.where(hasr[:, None], np.einsum('kij,kj->ki', W[np.maximum(orr, 0)], q), q)
            z = np.where(q[:, 2] > 1e-6, q[:, 2], 1e-6)
            r = np.stack([F_HD * q[:, 0] / z + 640.0 - op[:, 0], F_HD * q[:, 1] / z + 400.0 - op[:, 1]], 1).ravel()
            r = np.sign(r) * huber * np.sqrt(2.0 * (np.sqrt(1.0 + (r / huber) ** 2) - 1.0))          # pseudo-Huber: large errors count linearly
            pr = []
            for a, b, c in triples:
                acc = cam(cc, c) - 2 * cam(cc, b) + cam(cc, a); sg = acc_sigma * 0.5 * (v.get(a, 0.1) + v.get(b, 0.1))
                pr.extend((acc / sg * 2.0).tolist())
            for a, b in sline:
                d = cam(cc, b) - cam(cc, a); vv = v[a]
                pr.append((d @ ax - vv) / (step_prior * vv) * 3.0)
                side = d - ax * (d @ ax); pr.extend((side / (0.03 * vv) * 3.0).tolist())
            for a, b in pairs:                                   # step sizes: the speed changes smoothly between the straights
                d = cam(cc, b) - cam(cc, a); vv = v[a]
                pr.append((math.sqrt(float(d @ d) + 1e-12) - vv) / (step_prior * vv) * 3.0)
            out = [r, np.array(pr)] if pr else [r]
            if nr: out.append((ww / math.radians(rot_sigma) * 3.0).ravel())
            return np.concatenate(out)
        c0 = (np.array([C[n] for n in free]) - base) @ np.linalg.pinv(B)
        x0 = np.concatenate([c0.ravel(), np.zeros(nr), X.ravel()])
        nres = len(resid(x0))
        J = lil_matrix((nres, len(x0)), dtype=int)
        for k in range(nobs):
            if isfree[k]: J[2 * k:2 * k + 2, oi[k] * dof:oi[k] * dof + dof] = 1
            if hasr[k]: J[2 * k:2 * k + 2, nc + orr[k] * 3:nc + orr[k] * 3 + 3] = 1
            c = nc + nr + oj[k] * 3; J[2 * k:2 * k + 2, c:c + 3] = 1
        row = 2 * nobs
        for tr3 in triples:
            for m in tr3:
                if m in fi: J[row:row + 3, fi[m] * dof:fi[m] * dof + dof] = 1
            row += 3
        for pair in sline:
            for m in pair:
                if m in fi: J[row:row + 4, fi[m] * dof:fi[m] * dof + dof] = 1
            row += 4
        for pair in pairs:
            for m in pair:
                if m in fi: J[row, fi[m] * dof:fi[m] * dof + dof] = 1
            row += 1
        for i in range(nr): J[row + i, nc + i] = 1
        sol = least_squares(resid, x0, jac_sparsity=J, loss='linear', x_scale='jac', max_nfev=50, method='trf')
        cc, ww, XX = unpack(sol.x)
        for n in free: C[n] = cc[fi[n]]
        for n in rfree:
            w = ww[ri[n]]; th = np.linalg.norm(w)
            if th > 1e-12:
                kx = w / th; K = np.array([[0, -kx[2], kx[1]], [kx[2], 0, -kx[0]], [-kx[1], kx[0], 0]])
                R[n] = (np.eye(3) + math.sin(th) * K + (1 - math.cos(th)) * K @ K) @ R[n]
        # true reprojection errors
        e = []; per = {}
        for obs, Xp in zip(keep, XX):
            for n, p in obs:
                xy, z = _proj(Xp[None, :], C[n], R[n]); e.append(float(np.hypot(*(xy[0] - p))))
                if n in fi: per[n] = per.get(n, 0) + 1
        e = np.array(e)
        rep = dict(points=M, observations=nobs, median=float(np.median(e)), p90=float(np.percentile(e, 90)), per_frame=per,
                   rot=float(np.degrees(np.abs(ww).max())) if nr else 0.0)
        if verbose: print('  round %d: %d points, %d observations, reprojection median %.2f px, 90%% %.2f px; fewest observations in a free frame: %d; largest rotation correction %.2f deg' % (
            rnd, M, nobs, np.median(e), np.percentile(e, 90), min(per.get(n, 0) for n in free), rep['rot']))
    return C, R, XX, rep


def solve(S, key, pre=5, post=5, verbose=True, plane=True, P=None, **kw):
    """bundle adjustment of the frames around the bend that starts at frame `key` (between two straights).
    P: positions to start from / to hold for the straight before the bend (default S.P).
    plane: keep the cameras in the plane of the bend (the two tube axes)."""
    sec = S.sections(); st = [x for x in sec if x[0] == 'straight']
    cur = next(x for x in st if x[2] + 1 == key); nxt = st[st.index(cur) + 1]
    fa = np.array(RD.AXES[cur[3]], dtype=float); fb = np.array(RD.AXES[nxt[3]], dtype=float)
    a0 = max(cur[1], cur[2] - pre + 1); b1 = min(nxt[2], nxt[1] + post - 1)
    frames = [n for n in range(a0, b1 + 1) if n in S.R]
    fixed = [n for n in frames if n <= cur[2]]
    P = P if P is not None else S.P
    if not hasattr(S, 'T') or S.T is None: S.T = S.tracks(10, 3)
    C, Rn, X, rep = adjust(frames, fixed, {n: P[n] for n in frames}, {n: S.R[n] for n in frames}, S.T, S.v, straight=(nxt[1], b1, fb),
                           basis=np.array([fa, fb]) if plane else None, verbose=verbose, rot_free=[n for n in frames if S.status.get(n) != 'axis'], **kw)
    out = dict(C=C, R=Rn, frames=frames, fixed=fixed, free=[n for n in frames if n not in fixed], axes=(fa, fb), points=X, report=rep)
    return out


def fit_arc(S, key, C, verbose=True):
    """line - arc - line that best follows the adjusted camera positions of a bend -> dict(radius, lead, tail, rms)"""
    sec = S.sections(); st = [x for x in sec if x[0] == 'straight']
    cur = next(x for x in st if x[2] + 1 == key); nxt = st[st.index(cur) + 1]
    fa = np.array(RD.AXES[cur[3]], dtype=float); fb = np.array(RD.AXES[nxt[3]], dtype=float)
    Pa = np.array(S.P[cur[2]], dtype=float)                       # end of the straight before (fixed)
    fr = [n for n in sorted(C) if n > cur[2]]
    Q = np.array([[(C[n] - Pa) @ fa, (C[n] - Pa) @ fb] for n in fr])        # coordinates in the bend plane
    # the straight after the bend lies on the line u = lead + radius (u along the old axis)
    after = np.array([Q[i] for i, n in enumerate(fr) if n >= nxt[1]])
    u_line = float(np.median(after[:, 0])) if len(after) else float(Q[-1, 0])
    best = None
    for r in np.linspace(0.02, 1.0, 99) * max(u_line, 1e-6):
        lead = u_line - r
        # distance of every bend camera to the path (line u<lead on v=0; arc centre (lead, r); line u = u_line for v > r)
        d = []
        for u, v in Q:
            if u <= lead and v < r: d.append(abs(v))
            elif v >= r and u > lead: d.append(abs(u - u_line))
            else: d.append(abs(math.hypot(u - lead, v - r) - r))
        rms = float(np.sqrt(np.mean(np.square(d))))
        if best is None or rms < best[0]: best = (rms, r, lead)
    rms, r, lead = best
    # tail: how far along the new axis the first frame of the next straight is past the arc's end
    v_first = float(((C[nxt[1]] - Pa) @ fb)) if nxt[1] in C else r
    tail = max(0.0, v_first - r)
    if verbose: print('  line-arc-line: radius %.3f lead %.3f tail %.3f (rms distance %.3f); new straight at %.3f along the old axis' % (r, lead, tail, rms, u_line))
    return dict(radius=float(r), lead=float(lead), tail=float(tail), rms=rms)


if __name__ == '__main__':
    import sys, pickle
    from ride import Shot
    db, first, last, name = sys.argv[1], int(sys.argv[2]), int(sys.argv[3]), sys.argv[4]
    S = Shot(db, first, last)
    d = pickle.load(open('/home/claude/offline/out/%s_orient.pkl' % name, 'rb')); S.R = d['R']; S.status = d['status']; S.steps = d['steps']; S.RE = d['RE']; S.RL = d['RL']
    S.solve_bends(); S.solve_speeds(verbose=False); S.build_path()
    for b in S.bend_info:
        if b.get('open') or b['radius'] is None: continue
        print('bend', b['first'])
        res = solve(S, b['first'])
        for n in res['frames']: print('   %d  %s' % (n, np.round(res['C'][n], 3)))
