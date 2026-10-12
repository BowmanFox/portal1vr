"""Regular elbows of the tube: where the tube turns, how tightly, and when the camera is where in it - from the rails.

A plain elbow is a straight tube, a quarter circle and a straight tube again. The four rails follow it, so they show
it in the picture: from the straight before the bend the elbow is seen ahead, and inside the bend the rails sweep past
the camera. For a trial elbow (distance of the corner along the old axis, radius) the camera is tracked along the
trial path frame by frame (dynamic programming: the rails must lie on dark lines of the film, the speed must stay near
the speed interpolated between the straights); the best trial is the elbow.

    import elbow
    res = elbow.fit(S, 1019)        # S: ride.Shot after solve_bends() and solve_speeds(); key = first frame of the bend
    res: dict(corner, radius, lead, s={frame: arclength from the last straight frame}, score, path)
All lengths in map units (rails 34 from the axis)."""
import math
import numpy as np
import ride as RD, railfit as RF


def elbow_path(Pa, fa, fb, lead, radius, tail=6000.0):
    p = RD.Path(np.asarray(Pa, dtype=float)); p.line(lead, fa); p.arc(radius, fa, fb); p.line(tail, fb)
    return p


def _rail_points(path, rho, s0, s1, ds):
    P = []
    for pts, tan in RF.rail_curves(path, rho, s0, s1, ds): P.append(pts)
    return np.concatenate(P, axis=0)


def emission(rmap, pts, C, R, rho, zmax=2500.0):
    """mean ridge strength along the rails as seen from each camera position C [J,3] with orientation R -> [J]"""
    q = (pts[None, :, :] - C[:, None, :]) @ R.T                                  # [J, M, 3]
    z = q[:, :, 2]; zz = np.where(z > 1e-6, z, 1e-6)
    x = RF.F * q[:, :, 0] / zz + RF.CX; y = RF.F * q[:, :, 1] / zz + RF.CY
    ok = (z > 0.4 * rho) & (z < zmax) & (x > 2) & (x < 637) & (y > 2) & (y < 397)
    xi = np.clip(x, 0, 638.999); yi = np.clip(y, 0, 398.999)
    x0 = xi.astype(int); y0 = yi.astype(int); fx = xi - x0; fy = yi - y0
    v = (rmap[y0, x0] * (1 - fx) * (1 - fy) + rmap[y0, x0 + 1] * fx * (1 - fy) + rmap[y0 + 1, x0] * (1 - fx) * fy + rmap[y0 + 1, x0 + 1] * fx * fy)
    w = np.where(ok, np.minimum(1.0 / zz, 1.0 / (2.0 * rho)), 0.0).astype(np.float32)      # a sample stands for more picture when it is near
    sw = w.sum(axis=1)
    return np.where(sw > 0.15 / rho, (v * w).sum(axis=1) / np.maximum(sw, 1e-12), 0.0)


def _rails_for(path, rho, s0, s1):
    """rail sample points: close together near the start, wider apart far ahead"""
    near = _rail_points(path, rho, s0, min(s1, s0 + 1400.0), rho * 0.7)
    if s1 > s0 + 1400.0: return np.concatenate([near, _rail_points(path, rho, s0 + 1400.0, s1, rho * 1.6)], axis=0).astype(np.float32)
    return near.astype(np.float32)


def _em(S, path, pts, n, svals, vv, rho):
    RM = getattr(S, 'RM', None) or {}
    tot = np.zeros(len(svals))
    for mo, dq in (('E', -0.25), ('L', 0.25)):
        R = RM.get((n, mo), S.R[n]).astype(np.float32)
        C = np.array([path.point(s + dq * vv)[0] for s in svals], dtype=np.float32)
        tot += emission(RF.ridge_map(n, mo), pts, C, R, rho)
    return tot / 2.0


def approach_score(S, path, fixed, s_known, v, rho=RD.RAIL_RHO):
    """how well the rails of a trial path fit the frames whose place is known (the straight before the bend)"""
    pts = _rails_for(path, rho, 0.0, max(s_known.values()) + 3200.0)
    return float(sum(_em(S, path, pts, n, np.array([s_known[n]]), v[n], rho)[0] for n in fixed))


def track(S, path, frames, s_start, vprior, rho=RD.RAIL_RHO, fixed=(), s_known=None, w_e=0.1, sigma=0.35, verbose=False):
    """the camera's arclength on `path` for every frame of `frames` (in order), starting at s_start for frames[0].
    fixed: frames whose arclength is known (s_known[n]). vprior[n]: expected step n -> n+1.
    -> ({n: s}, total score, per-frame emissions)"""
    vmin = min(vprior[n] for n in frames[:-1])
    L = sum(vprior[n] for n in frames[:-1])
    g = vmin / 3.0
    grid = np.arange(s_start - 2 * vmin, s_start + 1.5 * L + 4 * vmin, g); J = len(grid)
    pts = _rails_for(path, rho, max(0.0, grid[0] - 4 * rho), grid[-1] + 2600.0)
    fixed = set(fixed); cost = None; back = []; total_fixed = 0.0; ems = {}
    prev_n = None; s_exp = s_start
    for n in frames:
        if n in fixed:
            e = _em(S, path, pts, n, np.array([s_known[n]]), vprior[n], rho); total_fixed += w_e * float(e[0]); ems[n] = float(e[0])
            cost = np.full(J, np.inf); cost[int(np.clip(round((s_known[n] - grid[0]) / g), 0, J - 1))] = 0.0
            back.append(None); prev_n = n; s_exp = s_known[n]; continue
        vv = vprior[prev_n]; s_exp += vv
        # only the states the camera can have reached by now
        reach = np.isfinite(cost); lo = grid[reach].min() + 0.25 * vv; hi = grid[reach].max() + 3.0 * vv
        m = (grid >= lo - 1e-9) & (grid <= hi + 1e-9); idx = np.where(m)[0]
        e = np.zeros(J); e[idx] = _em(S, path, pts, n, grid[idx], vprior.get(n, vmin), rho)
        d = grid[None, idx] - grid[:, None]                                 # [from, to]
        c = ((d - vv) / (sigma * vv)) ** 2 / 2.0
        c[(d < 0.25 * vv) | (d > 3.0 * vv)] = np.inf
        tot = cost[:, None] + c
        bk = np.zeros(J, int); newc = np.full(J, np.inf)
        bk[idx] = tot.argmin(axis=0); newc[idx] = tot.min(axis=0) - w_e * e[idx]
        cost = newc; back.append((bk, e)); prev_n = n
    j = int(np.argmin(cost)); best = float(cost[j]); out = {}
    for n, b in zip(frames[::-1], back[::-1]):
        if b is None: out[n] = float(s_known[n]); continue
        bk, e = b; out[n] = float(grid[j]); ems[n] = float(e[j]); j = int(bk[j])
    return out, -(best) + total_fixed, ems


def fit(S, key, rho=RD.RAIL_RHO, pre=7, post=3, verbose=True, corners=None, radii=None, P_start=None, keep=8):
    """the elbow of the bend that starts at frame `key`. P_start: position of the last frame of the straight before
    (default origin; only the result's path depends on it). -> dict (see module text)"""
    sec = S.sections(); st = [x for x in sec if x[0] == 'straight']
    cur = next(x for x in st if x[2] + 1 == key); nxt = st[st.index(cur) + 1]
    fa = np.array(RD.AXES[cur[3]], dtype=float); fb = np.array(RD.AXES[nxt[3]], dtype=float)
    assert abs(fa @ fb) < 0.1, 'not a quarter turn'
    a = cur[2]; b = nxt[1]; v = S.v
    n0 = max(cur[1], a - pre); n1 = min(nxt[2], b + post)
    frames = list(range(n0, n1 + 1)); fixed = [n for n in frames if n <= a]
    L0 = sum(v[n] for n in range(a, b))
    Pa = np.zeros(3) if P_start is None else np.asarray(P_start, dtype=float)
    back = sum(v[n] for n in range(n0, a))                    # the fixed frames lie on the old axis before Pa
    s_known = {}; s = 0.0
    for n in fixed: s_known[n] = s; s += v[n]
    def mk(D, r): return elbow_path(Pa - fa * back, fa, fb, D - r + back, r)
    def trial(D, r):
        path = mk(D, r); sn, score, ems = track(S, path, frames, 0.0, v, rho, fixed, s_known)
        return score, sn, path, ems
    corners = corners if corners is not None else [L0 * f for f in np.arange(0.08, 0.96, 0.04)]
    radii = radii if radii is not None else [45.0, 60.0, 80.0, 105.0, 140.0, 185.0, 245.0, 320.0]
    pre_s = sorted(((approach_score(S, mk(D, r), fixed, s_known, v, rho), D, r) for D in corners for r in radii if r <= D), reverse=True)
    if verbose:
        print('  elbow search (distance travelled between the straights at the interpolated speed: %.0f)' % L0)
        print('     seen from the straight before: ' + ', '.join('corner %.0f r %.0f (%.1f)' % (D, r, sc) for sc, D, r in pre_s[:6]))
    # the best radius for each of the best corner distances, then track the camera through those
    cand = []; seen = set()
    for sc, D, r in pre_s:
        if D in seen: continue
        seen.add(D); cand.append((D, r))
        if len(cand) >= keep: break
    res = sorted(((trial(D, r)[0], D, r) for D, r in cand), reverse=True)
    if verbose:
        for sc, D, r in res[:5]: print('     score %.2f  corner %.0f past the last straight frame, radius %.0f' % (sc, D, r))
    sc, D, r = res[0]
    stepD = (corners[1] - corners[0]) / 2.0 if len(corners) > 1 else 0.04 * L0; stepR = 0.25 * r
    for it in range(6):                                        # refine
        improved = False
        for dD, dr in ((stepD, 0), (-stepD, 0), (0, stepR), (0, -stepR)):
            D2, r2 = D + dD, r + dr
            if r2 < 30 or r2 > D2: continue
            s2 = trial(D2, r2)[0]
            if s2 > sc: sc, D, r = s2, D2, r2; improved = True
        if not improved:
            stepD /= 2; stepR /= 2
            if stepD < 8: break
    score, sn, path, ems = trial(D, r)
    # arclengths counted from the last straight frame
    s_rel = {n: sn[n] - back for n in frames}
    if verbose:
        print('  elbow: corner %.0f past the last straight frame, radius %.0f (lead %.0f); score %.2f' % (D, r, D - r, score))
        print('     frame: arclength past the last straight frame / rail strength:  ' + '  '.join('%d: %.0f/%.1f' % (n, s_rel[n], ems[n]) for n in frames))
    return dict(corner=float(D), radius=float(r), lead=float(D - r), s=s_rel, score=float(score), em=ems,
                path=elbow_path(Pa, fa, fb, D - r, r), frames=frames, a=a, b=b, fa=fa, fb=fb, mean_em=float(np.mean([ems[n] for n in frames if n > a])))


if __name__ == '__main__':
    import sys, pickle, os
    from ride import Shot
    db, first, last, name = sys.argv[1], int(sys.argv[2]), int(sys.argv[3]), sys.argv[4]
    S = Shot(db, first, last)
    stf = '/home/claude/offline/out/%s_state.pkl' % name
    if os.path.exists(stf):
        for k, v in pickle.load(open(stf, 'rb')).items(): setattr(S, k, v)
    else:
        d = pickle.load(open('/home/claude/offline/out/%s_orient.pkl' % name, 'rb')); S.R = d['R']; S.status = d['status']; S.steps = d['steps']; S.RE = d['RE']; S.RL = d['RL']
        S.solve_bends(); S.solve_speeds(verbose=False)
    st = [x for x in S.sections() if x[0] == 'straight']
    keys = [int(k) for k in sys.argv[5].split(',')] if len(sys.argv) > 5 else [x[2] + 1 for x in st[:-1]]
    for k in keys:
        print('bend', k); fit(S, k)
