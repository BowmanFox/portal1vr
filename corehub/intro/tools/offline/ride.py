"""Reconstructing a shot of the tube ride: camera orientation, camera path and the surroundings.

What the film gives (found on the rust room, 32.7-36.1 s):
  * the rooms and tubes are built on three perpendicular axes; in a straight tube section the camera sits on the tube
    axis and looks exactly along a room axis (orient.py measures that from the lines in the picture, with no drift);
  * in a bend the view turns a quarter turn about the camera's own right or up axis; too few room lines are in view
    there, but matched image features give the turn from frame to frame (gyro.py);
  * with the orientation of every frame known, the camera positions and the 3D points of all matched features follow
    from one linear least-squares problem (no bas-relief ambiguity, no drift): solve_positions().
Units: positions come out in "steps" (mean camera advance per frame = 1) until scaled; axes are the room axes.

    S = Shot('rust2', 981, 1082)                    # COLMAP database name (features + matches of the blended frames), frame range
    S.solve_orientation(anchor=990, x='forward', z='up')    # room axes named by what the camera sees at the anchor frame
    S.report_orientation()                           # straights (plateaus) and bends
    S.solve_positions()                              # camera centres S.C[n], points S.X
    S.save('out/rust_a_ride.pkl')
"""
import math, pickle
import numpy as np, cv2
import orient as O
from gyro import Gyro, F_HD, _slerp

COLLAR_R = 61.06            # radius of the tube collars' light band in map units (measured in the opening room's ascent)
RAIL_RHO = 34.0             # distance of the four rails from the tube axis
AXES = {'+x': (1, 0, 0), '-x': (-1, 0, 0), '+y': (0, 1, 0), '-y': (0, -1, 0), '+z': (0, 0, 1), '-z': (0, 0, -1)}


def snap_rotation(R, tol_deg=2.0):
    """nearest of the 24 axis-aligned rotations, or None when R is further than tol_deg from it"""
    S = np.zeros((3, 3)); used = set()
    for i in np.argsort(-np.abs(R).max(axis=1)):
        j = max((j for j in range(3) if j not in used), key=lambda j: abs(R[i, j]))
        used.add(j); S[i, j] = 1.0 if R[i, j] > 0 else -1.0
    if np.linalg.det(S) < 0: return None
    return S if O.angle_between(R, S) <= tol_deg else None


def _robust_smooth(st):
    """smooth curve through per-frame steps that ignores wild values (the ends of a straight are often poorly measured)"""
    st = np.asarray(st, dtype=float); n = len(st); x = np.arange(n)
    if n < 4: return np.full(n, float(np.median(st)))
    med = np.median(st); mad = np.median(np.abs(st - med)) + 1e-6
    ok = np.abs(st - med) < max(4 * mad, 0.25 * abs(med))
    deg = 1 if n < 6 else (2 if n < 14 else 3)
    for _ in range(3):
        if ok.sum() <= deg + 1: return np.full(n, float(med))
        c = np.polyfit(x[ok], st[ok], deg); fit = np.polyval(c, x)
        r = st - fit; sd = np.median(np.abs(r[ok])) + 1e-6
        ok = np.abs(r) < max(4 * sd, 0.08 * abs(med))
    # do not let the polynomial run away outside the trusted samples
    lo, hi = x[ok].min(), x[ok].max()
    fit[:lo] = fit[lo]; fit[hi + 1:] = fit[hi]
    return np.maximum(fit, 0.05 * abs(med))


def nearest_axis_rotation(R):
    """(nearest of the 24 axis-aligned rotations, its distance in degrees, distance of the runner-up)"""
    import itertools
    best = []
    for perm in itertools.permutations(range(3)):
        for signs in itertools.product((1, -1), repeat=3):
            S = np.zeros((3, 3))
            for i in range(3): S[i, perm[i]] = signs[i]
            if np.linalg.det(S) < 0: continue
            best.append((O.angle_between(R, S), S))
    best.sort(key=lambda t: t[0])
    return best[0][1], best[0][0], best[1][0]


class Path:
    """a path of straight lines and circular arcs, addressed by arclength"""
    def __init__(self, p0):
        self.p0 = np.asarray(p0, dtype=float); self.pieces = []; self.end = self.p0.copy(); self.length = 0.0

    def line(self, length, d):
        d = np.asarray(d, dtype=float)
        if length <= 0: return self
        if self.pieces and self.pieces[-1]['kind'] == 'line' and np.allclose(self.pieces[-1]['dir'], d):
            self.pieces[-1]['length'] += length
        else: self.pieces.append(dict(kind='line', start=self.end.copy(), dir=d, length=float(length), s0=self.length))
        self.end = self.end + d * length; self.length += length
        return self

    def arc(self, radius, d0, d1):
        d0 = np.asarray(d0, dtype=float); d1 = np.asarray(d1, dtype=float)
        th = math.acos(max(-1.0, min(1.0, float(d0 @ d1))))
        n = (d1 - d0 * math.cos(th)) / math.sin(th)
        self.pieces.append(dict(kind='arc', start=self.end.copy(), dir=d0, normal=n, radius=float(radius), angle=th, length=float(radius * th), s0=self.length))
        self.end = self.end + radius * (math.sin(th) * d0 + (1 - math.cos(th)) * n); self.length += radius * th
        return self

    def point(self, s):
        """(position, unit tangent) at arclength s (clamped to the ends, continued straight beyond them)"""
        if not self.pieces: return self.p0.copy(), np.array([1.0, 0, 0])
        pc = self.pieces[0] if s < 0 else next((p for p in self.pieces if p['s0'] <= s <= p['s0'] + p['length'] + 1e-12), self.pieces[-1])
        u = s - pc['s0']
        if pc['kind'] == 'line': return pc['start'] + pc['dir'] * u, pc['dir'].copy()
        if u > pc['length']:                                   # beyond the end of a final arc: continue along its end tangent
            ph = pc['angle']; e = pc['start'] + pc['radius'] * (math.sin(ph) * pc['dir'] + (1 - math.cos(ph)) * pc['normal'])
            t = math.cos(ph) * pc['dir'] + math.sin(ph) * pc['normal']; return e + t * (u - pc['length']), t
        ph = u / pc['radius']
        return pc['start'] + pc['radius'] * (math.sin(ph) * pc['dir'] + (1 - math.cos(ph)) * pc['normal']), math.cos(ph) * pc['dir'] + math.sin(ph) * pc['normal']

    def to_json(self):
        out = []
        for p in self.pieces:
            d = dict(kind=p['kind'], start=[float(x) for x in p['start']], dir=[float(x) for x in p['dir']], length=p['length'], s0=p['s0'])
            if p['kind'] == 'arc': d.update(normal=[float(x) for x in p['normal']], radius=p['radius'], angle=p['angle'])
            out.append(d)
        return out



def make_path(sections, frames, v, R, bends=None, default_radius=None):
    """see Shot.build_path. sections: [(kind, first, last, forward, up)], frames: sorted frame numbers, v: {n: step n -> n+1},
    R: {n: Rcw}. -> (Path, {n: arclength}, bend_info, {n: step used})"""
    bends = bends or {}
    fr = list(frames); v = dict(v)
    straights = [x for x in sections if x[0] == 'straight']
    assert straights, 'no straight section in the shot'
    # bends with a given tail: the path length between the straights is set, so the speeds inside follow from it
    for k in range(len(straights) - 1):
        cur, nxt = straights[k], straights[k + 1]; a, b = cur[2], nxt[1]; prm = bends.get(a + 1, {})
        if 'tail' not in prm: continue
        fa = np.array(AXES[cur[3]], dtype=float); fb = np.array(AXES[nxt[3]], dtype=float)
        th = math.acos(max(-1.0, min(1.0, float(fa @ fb))))
        L = prm.get('lead', 0.0) + prm['radius'] * th + prm['tail']
        va = v[a - 1] if (a - 1) in v else v[a]; vb = v[b] if b in v else v[b - 1]
        N = b - a; x = (np.arange(N) + 0.5) / N
        bump = 4 * x * (1 - x); k_ = (L - N * (va + vb) / 2.0) / bump.sum()
        vv = va + (vb - va) * x + k_ * bump
        for i, n in enumerate(range(a, b)): v[n] = float(vv[i])
    s_of = {fr[0]: 0.0}
    for n0, n1 in zip(fr, fr[1:]): s_of[n1] = s_of[n0] + v[n0] * (n1 - n0)
    path = Path(np.zeros(3)); info = []
    first = straights[0]; f0 = np.array(AXES[first[3]], dtype=float)
    path.line(s_of[first[2]] - s_of[fr[0]], f0)                      # lead-in and first straight
    for k in range(len(straights)):
        cur = straights[k]; fa = np.array(AXES[cur[3]], dtype=float)
        nxt = straights[k + 1] if k + 1 < len(straights) else None
        if nxt is None:
            rest = s_of[fr[-1]] - s_of[cur[2]]
            if rest > 1e-9:
                # the shot ends after this straight: is the view turning (into a bend) at the end?
                fl = O.to_basis(R[fr[-1]])[0]; rem = fl - fa * (fl @ fa)
                bkey = cur[2] + 1; prm = bends.get(bkey, {})
                if np.linalg.norm(rem) > 0.2:
                    j = int(np.argmax(np.abs(rem))); fb = np.zeros(3); fb[j] = np.sign(rem[j])
                    rad = prm.get('radius', default_radius or rest / (math.pi / 2))
                    lead = prm.get('lead', 0.0)
                    path.line(lead, fa); path.arc(rad, fa, fb); path.line(max(0.0, rest - lead - rad * math.pi / 2) + 1e-6, fb)
                    info.append(dict(first=bkey, last=fr[-1], length=rest, radius=rad, lead=lead, open=True))
                else: path.line(rest, fa)
            break
        fb = np.array(AXES[nxt[3]], dtype=float)
        L = s_of[nxt[1]] - s_of[cur[2]]; bkey = cur[2] + 1; prm = bends.get(bkey, {})
        if abs(fa @ fb) > 0.99:                                     # no net turn (a jog is not modelled yet): straight on
            path.line(L, fa); info.append(dict(first=bkey, last=nxt[1] - 1, length=L, radius=None, lead=None))
        else:
            th = math.acos(max(-1.0, min(1.0, float(fa @ fb))))
            rmax = L / th
            rad = min(prm.get('radius', default_radius or rmax), rmax)
            lead = prm.get('lead', (L - rad * th) / 2.0); lead = max(0.0, min(lead, L - rad * th))
            path.line(lead, fa); path.arc(rad, fa, fb); path.line(L - lead - rad * th, fb)
            info.append(dict(first=bkey, last=nxt[1] - 1, length=L, radius=rad, lead=lead, tail=L - lead - rad * th))
        path.line(s_of[nxt[2]] - s_of[nxt[1]], fb)                  # the next straight
    return path, s_of, info, v


def path_moments(frames, R, v, s, path, RM=None):
    """[(time, frame, moment, position, Rcw, arclength)] at 60 per second (see Shot.moments)"""
    fr = list(frames); out = []
    for i, n in enumerate(fr):
        vprev = v[fr[i - 1]] if i > 0 else v[n]
        vnext = v[n] if n in v else vprev
        Rp = R[fr[i - 1]] if i > 0 else R[n]; Rn = R[fr[i + 1]] if i + 1 < len(fr) else R[n]
        for mo, ds, Ro in (('E', -0.25 * vprev, Rp), ('L', 0.25 * vnext, Rn)):
            Rm = RM[(n, mo)] if RM and (n, mo) in RM else O.orthonormal(_slerp(R[n], Ro, 0.25)); sm = s[n] + ds
            out.append((n * 1001 / 30000.0 + (1001 / 60000.0 if mo == 'L' else 0.0), n, mo, path.point(sm)[0], Rm, sm))
    return out



class Curve:
    """a smooth path given by closely spaced points, addressed by arclength (the camera path = the tube's centre line)"""
    def __init__(self, pts, t=None):
        self.P = np.asarray(pts, dtype=float)
        d = np.linalg.norm(np.diff(self.P, axis=0), axis=1)
        self.S = np.r_[0.0, np.cumsum(d)]; self.length = float(self.S[-1])
        self.t = None if t is None else np.asarray(t, dtype=float)          # film frame number at every point
        T = np.gradient(self.P, axis=0); self.T = T / (np.linalg.norm(T, axis=1, keepdims=True) + 1e-12)

    def point(self, s):
        """(position, unit tangent) at arclength s; beyond the ends the path continues straight"""
        if s <= 0: return self.P[0] + self.T[0] * s, self.T[0].copy()
        if s >= self.length: return self.P[-1] + self.T[-1] * (s - self.length), self.T[-1].copy()
        i = int(np.clip(np.searchsorted(self.S, s) - 1, 0, len(self.S) - 2)); u = (s - self.S[i]) / max(self.S[i + 1] - self.S[i], 1e-12)
        t = self.T[i] * (1 - u) + self.T[i + 1] * u
        return self.P[i] + (self.P[i + 1] - self.P[i]) * u, t / np.linalg.norm(t)

    def s_at_time(self, t):
        """arclength at a (fractional) film frame number"""
        return float(np.interp(t, self.t, self.S))

    def transport(self, u0):
        """unit vector u0 (perpendicular to the first tangent) carried along the path without twisting: [k,3]"""
        U = np.zeros_like(self.P); u = np.asarray(u0, dtype=float); u = u - self.T[0] * (u @ self.T[0]); U[0] = u / np.linalg.norm(u)
        for i in range(1, len(self.P)):
            u = U[i - 1] - self.T[i] * (U[i - 1] @ self.T[i]); U[i] = u / np.linalg.norm(u)
        return U

    def offset_curves(self, rho, u0):
        """the four rails: curves at distance rho from the path on the diagonals of the frame (u0, tangent x u0) -> [4][k,3]"""
        U = self.transport(u0); W = np.cross(self.T, U)
        return [self.P + (a * U + b * W) * rho / math.sqrt(2.0) for a in (1, -1) for b in (1, -1)]


class Shot:
    def __init__(self, db_name, first, last):
        self.name = db_name; self.first = first; self.last = last
        self.G = Gyro(db_name)
        self.frames = [n for n in range(first, last + 1) if n in self.G.ids]
        self.R = {}; self.RE = {}; self.RL = {}; self.status = {}; self.steps = {}
        self.C = {}; self.X = None

    # ------------------------------------------------------------------ orientation
    def gyro_step(self, n):
        """cached (R, inliers, t) for frames n -> n+1"""
        if n not in self.steps: self.steps[n] = self.G.step(n, n + 1)
        return self.steps[n]

    def clean_steps(self):
        """frame-to-frame rotations with the unreliable ones (few matches, or a turn rate that does not fit its
        neighbours) replaced by the average of the nearest good steps -> {n: (R, good)} for n -> n+1"""
        fr = self.frames; raw = {}
        for a, b in zip(fr, fr[1:]):
            if b != a + 1: continue
            R, k, t = self.gyro_step(a)
            raw[a] = (R, k)
        ang = {n: (O.angle_between(R, np.eye(3)) if R is not None else None) for n, (R, k) in raw.items()}
        good = {}
        for n, (R, k) in raw.items():
            if R is None or k < 25: good[n] = False; continue
            nb = [ang[m] for m in (n - 2, n - 1, n + 1, n + 2) if m in ang and ang[m] is not None and raw[m][1] >= 25]
            if len(nb) >= 2:
                med = float(np.median(nb))
                good[n] = abs(ang[n] - med) <= max(3.0, 0.6 * med)
            else: good[n] = True
        out = {}
        for n in raw:
            if good[n]: out[n] = (raw[n][0], True); continue
            prev = next((m for m in range(n - 1, n - 6, -1) if good.get(m)), None)
            nxt = next((m for m in range(n + 1, n + 6) if good.get(m)), None)
            if prev is not None and nxt is not None:
                f = (n - prev) / float(nxt - prev); out[n] = (_slerp(raw[prev][0], raw[nxt][0], f), False)
            elif prev is not None: out[n] = (raw[prev][0], False)
            elif nxt is not None: out[n] = (raw[nxt][0], False)
            else: out[n] = (np.eye(3), False)
        return out

    def _lines(self, n, pred, max_corr):
        """orientation of frame n from the lines of its two moments near the prediction -> (R, measured?, per-moment)"""
        res = {}
        for mo in 'EL':
            Rm, info = O.refine(O.segments_of(n, mo), pred, tol=3.0, prior=0.03)
            good = info['ok'] and O.angle_between(Rm, pred) <= max_corr
            res[mo] = (Rm if good else None, info)
        got = [res[m][0] for m in 'EL' if res[m][0] is not None]
        if len(got) == 2: return O.orthonormal(_slerp(got[0], got[1], 0.5)), True, res
        if len(got) == 1: return got[0], True, res
        return pred, False, res

    def solve_orientation(self, anchor, forward='+x', up='+z', verbose=False):
        """Orientation of every frame (self.R[n], rows = camera right, down, forward in room axes).
        anchor: a frame in a straight tube section; forward / up name the room axes the camera looks along and has
        overhead there (this is what defines the room axes; '+x' and '+z' unless the shot continues another one).
        self.status[n]: 'axis' (looking exactly along a room axis), 'lines' (measured from room lines), 'gyro'
        (carried over from the neighbouring frames by feature matching)."""
        f = np.array(AXES[forward], dtype=float); u = np.array(AXES[up], dtype=float)
        assert abs(f @ u) < 1e-9, 'forward and up must be different axes'
        s = np.array([np.cross(f, u), -u, f])
        ok = 0
        for mo in 'EL':
            Rm, info = O.refine(O.segments_of(anchor, mo), s, tol=2.5, prior=0.03)
            if info['ok'] and O.angle_between(Rm, s) <= 1.0: ok += 1
        assert ok >= 1, 'the lines of the anchor frame do not fit a camera looking along a room axis; pick a frame in a straight section'
        steps = self.clean_steps()
        self.R = {anchor: s}; self.status = {anchor: 'axis'}; self.RE = {}; self.RL = {}
        for d in (1, -1):
            n = anchor
            while (n + d) in self.G.ids and self.first <= n + d <= self.last:
                a = n if d > 0 else n + d
                if a in steps: pred = (steps[a][0] @ self.R[n]) if d > 0 else (steps[a][0].T @ self.R[n])
                else: pred = self.R[n]
                pred = O.orthonormal(pred); m = n + d
                # straight section? the nearest axis-aligned orientation must explain the lines of both moments
                cand, d1, d2 = nearest_axis_rotation(pred); st = None
                if d1 > 40.0 or d2 - d1 < 12.0: cand = None           # the prediction is between two axis-aligned poses: do not guess
                if cand is not None:
                    okc = 0
                    for mo in 'EL':
                        Rm, info = O.refine(O.segments_of(m, mo), cand, tol=2.0, prior=0.03)
                        if info['ok'] and O.angle_between(Rm, cand) <= 0.8 and info['used'] >= 12: okc += 1
                    if okc == 2: R = cand; st = 'axis'
                if st is None:
                    R, measured, res = self._lines(m, pred, 6.0)
                    st = 'lines' if measured else 'gyro'
                    self.RE[m] = res['E'][0]; self.RL[m] = res['L'][0]
                self.R[m] = R; self.status[m] = st
                if verbose:
                    f, r, u = O.to_basis(R); print(m, st, np.round(f, 2), np.round(u, 2))
                n = m
        return self

    # ------------------------------------------------------------------ bends: one turn angle per moment
    def _line_scores(self, n, mo, Ra, w, grid, sigma=0.8):
        """how well the lines of a moment fit the room axes for the orientations Ra turned by each angle of `grid`
        (degrees) about room axis w; lines along w itself fit every angle and are left out. -> scores [len(grid)]"""
        S = O.segments_of(n, mo)
        if len(S) < 3: return np.zeros(len(grid))
        nrm, ln = O._seg_dirs(S)
        k0 = int(np.argmax(np.abs(w))); k1, k2 = [k for k in range(3) if k != k0]
        m0 = np.degrees(np.arcsin(np.clip(np.abs(nrm @ Ra[:, k0]), 0, 1)))
        keep = m0 > 2.0
        if keep.sum() < 2: return np.zeros(len(grid))
        nrm = nrm[keep]; wt = np.sqrt(ln[keep] / 40.0)
        out = np.zeros(len(grid))
        for j, th in enumerate(grid):
            R = Ra @ O._rodrigues(np.asarray(w, dtype=float) * math.radians(th)).T
            m = np.degrees(np.arcsin(np.clip(np.abs(nrm @ R[:, [k1, k2]]), 0, 1)))
            out[j] = float((wt * np.exp(-(m.min(axis=1) / sigma) ** 2)).sum())
        return out

    def solve_bends(self, verbose=False, margin=15.0, dth=0.5):
        """Orientation inside the bends, moment by moment. Between two straights the camera turns about one room axis,
        so each moment has one unknown: the angle turned so far. For every moment the room lines in view score every
        candidate angle; the frame-to-frame rotation from the feature matches (gyro) says how much the angle changes;
        dynamic programming picks the best sequence between the fixed ends. An open bend at the start or the end of
        the shot is solved the same way with one end free.
        -> self.RM[(n, 'E'|'L')] for every moment of the shot, self.R[n] updated inside bends (status 'turn')."""
        steps = self.clean_steps(); sec = self.sections(); fr = sorted(self.R)
        self.RM = {(n, mo): self.R[n] for n in fr for mo in 'EL'}
        self.turn = {}; self.bend_axis = {}
        for i, (kind, a, b, fw, up) in enumerate(sec):
            if kind != 'bend': continue
            prev = sec[i - 1] if i > 0 and sec[i - 1][0] == 'straight' else None
            nxt = sec[i + 1] if i + 1 < len(sec) and sec[i + 1][0] == 'straight' else None
            if prev is None and nxt is None: continue
            if prev is not None and nxt is not None:
                Ra = self.R[prev[2]]; Rb = self.R[nxt[1]]; D = Rb.T @ Ra
                total = math.degrees(math.acos(max(-1.0, min(1.0, (np.trace(D) - 1) / 2))))
                if total < 1.0:                                   # same pose before and after: a wobble, keep the gyro result
                    continue
                w = np.array([D[2, 1] - D[1, 2], D[0, 2] - D[2, 0], D[1, 0] - D[0, 1]]) / (2 * math.sin(math.radians(total)))
                w = np.round(w); anchor = 'both'
            else:
                # open bend: turn axis = room axis nearest to the mean rotation axis of the gyro steps, measured from the fixed end
                Ra = self.R[prev[2]] if prev is not None else self.R[nxt[1]]
                acc = np.zeros(3)
                for n in range(a - 1, b + 1):
                    if n in steps:
                        rv = cv2.Rodrigues(steps[n][0])[0].ravel(); acc += -(Ra.T @ rv)      # world-axis rotation of the camera
                if np.linalg.norm(acc) < 1e-6: continue
                k = int(np.argmax(np.abs(acc))); w = np.zeros(3); w[k] = np.sign(acc[k])
                total = None; anchor = 'start' if prev is not None else 'end'
                if anchor == 'end': w = -w                      # angles are counted backwards from the fixed end
            self.bend_axis[a] = w.copy()
            # moments of the bend, with one fixed moment at each known end
            mom = [(n, mo) for n in range(a, b + 1) for mo in 'EL']
            lo = -margin; hi = (total if total is not None else 100.0) + margin
            grid = np.arange(lo, hi + 1e-9, dth); J = len(grid)
            sc = np.array([self._line_scores(n, mo, Ra, w, grid) for n, mo in mom])
            norm = np.median(sc.max(axis=1)) + 1e-6; sc = sc / norm
            # expected change of the angle from moment to moment (gyro: rotation of frame n -> n+1 about the turn axis)
            def g(n):
                if n not in steps: return None, False
                rv = cv2.Rodrigues(steps[n][0])[0].ravel()
                return -math.degrees(float(rv @ (Ra @ w))), steps[n][1]
            exp = []; sig = []
            for t in range(len(mom) + 1):
                # transition into moment t (from the fixed start for t = 0, into the fixed end for t = len)
                n = mom[min(t, len(mom) - 1)][0]; mo = mom[t][1] if t < len(mom) else 'E'
                if t == len(mom): n = b + 1
                if mo == 'L':
                    g0, ok0 = g(n - 1); g1, ok1 = g(n); vals = [x for x in (g0, g1) if x is not None]
                    e = (sum(vals) / len(vals)) / 2.0 if vals else 0.0; good = bool(vals) and (ok0 or ok1)
                else:
                    g0, ok0 = g(n - 1); e = g0 / 2.0 if g0 is not None else 0.0; good = g0 is not None and ok0
                if anchor == 'end': e = -e
                exp.append(e); sig.append(1.2 if good else 5.0)
            if anchor == 'end':                                  # run the chain from the fixed end backwards
                mom_r = mom[::-1]; sc = sc[::-1]
                exp = exp[::-1]; sig = sig[::-1]
            else: mom_r = mom
            T = len(mom_r)
            cost = np.full((T, J), np.inf); back = np.zeros((T, J), int)
            def trans(prev_cost, t):
                d = grid[None, :] - grid[:, None] - exp[t]            # [from, to]
                c = np.minimum((d / sig[t]) ** 2 / 2.0, 12.0)
                tot = prev_cost[:, None] + c
                return tot.min(axis=0), tot.argmin(axis=0)
            start = np.full(J, np.inf); start[int(round((0.0 - lo) / dth))] = 0.0
            c, bk = trans(start, 0); cost[0] = c - 3.0 * sc[0]; back[0] = bk
            for t in range(1, T):
                c, bk = trans(cost[t - 1], t); cost[t] = c - 3.0 * sc[t]; back[t] = bk
            if total is not None:
                jend = int(round((total - lo) / dth))
                d = grid[jend] - grid - exp[T]; fin = cost[T - 1] + np.minimum((d / sig[T]) ** 2 / 2.0, 12.0)
                j = int(np.argmin(fin))
            else: j = int(np.argmin(cost[T - 1]))
            th = np.zeros(T)
            for t in range(T - 1, -1, -1):
                th[t] = grid[j]; j = back[t, j]
            for (n, mo), x in zip(mom_r, th):
                self.RM[(n, mo)] = O.orthonormal(Ra @ O._rodrigues(w * math.radians(float(x))).T); self.turn[(n, mo)] = float(x)
            for n in range(a, b + 1):
                xe, xl = self.turn[(n, 'E')], self.turn[(n, 'L')]
                self.R[n] = O.orthonormal(Ra @ O._rodrigues(w * math.radians((xe + xl) / 2.0)).T); self.status[n] = 'turn'
            if verbose:
                print('bend %d-%d about %s (%s): %s' % (a, b, w.astype(int).tolist(), 'total %.0f' % total if total is not None else 'open, counted from the ' + anchor,
                      ' '.join('%d%s %.1f' % (n, mo, self.turn[(n, mo)]) for n, mo in mom)))
        return self

    def sections(self, min_straight=3):
        """[(kind, first, last, forward, up)] with kind 'straight' (frames looking along a room axis) or 'bend'"""
        out = []
        for n in sorted(self.R):
            if self.status[n] == 'axis':
                f, r, u = O.to_basis(self.R[n]); key = ('straight', O.axis_label(f, 0.5), O.axis_label(u, 0.5))
            else: key = ('bend', None, None)
            if out and out[-1][0] == key and out[-1][2] == n - 1: out[-1][2] = n
            else: out.append([key, n, n])
        merged = []
        for key, a, b in out:
            if key[0] == 'straight' and b - a + 1 < min_straight: key = ('bend', None, None)
            if merged and merged[-1][0] == key: merged[-1][2] = b
            else: merged.append([key, a, b])
        return [(k[0], a, b, k[1], k[2]) for k, a, b in merged]

    def report_orientation(self):
        sec = self.sections()
        for i, (kind, a, b, fw, up) in enumerate(sec):
            if kind == 'straight': print('straight %d-%d  forward %s up %s' % (a, b, fw, up)); continue
            Ra, Rb = self.R[max(a - 1, min(self.R))], self.R[min(b + 1, max(self.R))]
            fa, ra, ua = O.to_basis(Ra); fb, rb, ub = O.to_basis(Rb)
            ang = O.angle_between(Ra, Rb)
            turn = math.degrees(math.atan2(float(np.cross(fa, fb) @ ua), float(fa @ fb)))       # + = to the left (about the camera's up)
            pitch = math.degrees(math.asin(max(-1.0, min(1.0, float(fb @ ua)))))                 # + = upward (toward the camera's up)
            what = ('turns left' if turn > 0 else 'turns right') + ' %.0f' % abs(turn) if abs(turn) > abs(pitch) else ('pitches up' if pitch > 0 else 'pitches down') + ' %.0f' % abs(pitch)
            st = [self.status[n] for n in range(a, b + 1) if n in self.status]
            print('bend     %d-%d  %s deg (total rotation %.0f); lines in %d of %d frames' % (a, b, what, ang, sum(x != 'gyro' for x in st), len(st)))

    # ------------------------------------------------------------------ positions and structure
    def tracks(self, max_gap=10, min_len=3):
        """feature tracks from the stored pairwise matches: list of {frame: (x, y)} (1280x800 pixels)"""
        parent = {}
        def find(a):
            while parent.get(a, a) != a:
                parent[a] = parent.get(parent[a], parent[a]); a = parent[a]
            return a
        fr = self.frames
        for i, a in enumerate(fr):
            for b in fr[i + 1:i + 1 + max_gap]:
                try: tv = self.G.db.read_two_view_geometry(self.G.ids[a], self.G.ids[b])
                except Exception: continue
                m = np.asarray(tv.inlier_matches)
                if m.size == 0: continue
                for ka, kb in m:
                    ra, rb = find((a, int(ka))), find((b, int(kb)))
                    if ra != rb: parent[ra] = rb
        groups = {}
        for node in list(parent.keys()):
            groups.setdefault(find(node), []).append(node)
        out = []
        for g in groups.values():
            fs = {}
            ok = True
            for n, k in g:
                if n in fs: ok = False; break          # two different keypoints of one image in one track: inconsistent
                fs[n] = k
            if not ok or len(fs) < min_len: continue
            out.append({n: tuple(self.G.keypoints(n)[k]) for n, k in fs.items()})
        return out

    # ------------------------------------------------------------------ speed along the tube
    def straight_steps(self, a, b, axis, T=None, iters=40):
        """relative camera positions along a straight section from the feature tracks: for a point beside the tube axis
        the cotangent of its angle from the axis falls linearly as the camera advances. -> positions s[n] for frames
        a..b with s[a] = 0 and a mean step of 1, number of tracks used"""
        if T is None:
            if not hasattr(self, 'T') or self.T is None: self.T = self.tracks(10, 3)
            T = self.T
        fr = list(range(a, b + 1)); idx = {n: i for i, n in enumerate(fr)}; N = len(fr)
        rows = []
        for tr in T:
            obs = [(idx[n], p) for n, p in tr.items() if n in idx]
            if len(obs) < 3: continue
            cs = []
            for i, p in obs:
                d = self.R[fr[i]].T @ np.array([(p[0] - 640.0) / F_HD, (p[1] - 400.0) / F_HD, 1.0]); d /= np.linalg.norm(d)
                ca = float(d @ axis); sa = math.sqrt(max(1 - ca * ca, 1e-12))
                if ca <= 0.05 or sa < 0.02: cs = None; break
                cs.append((i, ca / sa))
            if cs: rows.append((np.array([i for i, c in cs]), np.array([c for i, c in cs])))
        s = np.arange(N, dtype=float)
        if len(rows) < 8: return s, len(rows)
        for it in range(iters):
            num = np.zeros(N); den = np.zeros(N)
            for ii, cc in rows:
                A = np.c_[np.ones(len(ii)), -s[ii]]
                sol = np.linalg.lstsq(A, cc, rcond=None)[0]
                if sol[1] <= 1e-6: continue
                r = cc - A @ sol
                wt = 1.0 / (1.0 + (np.abs(r).max() / (0.02 * np.abs(cc).mean() + 1e-9)) ** 2)
                wgt = wt * (sol[1] / np.maximum(cc, 1e-3)) ** 2
                num[ii] += wgt * (sol[0] - cc) / sol[1]; den[ii] += wgt
            s_new = np.where(den > 0, num / np.maximum(den, 1e-12), s)
            s_new = s_new - s_new[0]
            if s_new[-1] <= 1e-6: break
            s_new = s_new * (N - 1) / s_new[-1]
            done = np.abs(s_new - s).max() < 1e-6; s = s_new
            if done: break
        return s, len(rows)

    def colmap_steps(self, model=0):
        """camera advance per frame according to COLMAP's reconstruction of the shot (its own units): {n: step n -> n+1}.
        COLMAP places frames wrongly now and then in these repetitive rooms, but the size of its steps inside a
        straight run is sound and has one common scale for the whole shot."""
        from sfmtools import Recon
        R = Recon(self.name, model)
        out = {}
        for n in self.frames:
            if R.has(n) and R.has(n + 1): out[n] = float(np.linalg.norm(R.cams[(n + 1, 'E')][0] - R.cams[(n, 'E')][0]))
        return out

    def collar_ruler(self, a, b, s_rel, verbose=False):
        """The size of the collars as a ruler for a straight section: the outer edge of a collar's light band (radius
        COLLAR_R in the map) approaching the camera draws a straight line in f / r against the camera position.
        s_rel: positions of the frames a..b in any linear unit.
        -> (collar radius in units of s_rel or None, [(radius, support)] of all candidate edges)"""
        from ringscale import edge_lines
        fr = list(range(a, b + 1)); cand = []
        for mo in 'EL':
            for l in edge_lines(fr, np.asarray(s_rel, dtype=float), moment=mo):
                if l['polarity'] == 1 and l['n'] >= 4 and l['strength'] >= 8.0 and l['slope'] > 0 and -0.2 * s_rel[-1] < l['cross'] < 2.5 * s_rel[-1] + 4:
                    cand.append((1.0 / l['slope'], l['strength'] * l['n']))
        if not cand: return None, cand
        cand.sort(); best = None
        for r0, _ in cand:                                     # the group of similar radii (12 %) with the most support
            grp = [(r, w) for r, w in cand if r0 <= r <= r0 * 1.12]
            sup = sum(w for r, w in grp)
            if best is None or sup > best[0]: best = (sup, grp)
        sup, grp = best
        if len(grp) < 2: return None, cand
        rs = np.array([r for r, w in grp]); ws = np.array([w for r, w in grp]); o = np.argsort(rs); cw = np.cumsum(ws[o])
        return float(rs[o][np.searchsorted(cw, cw[-1] / 2.0)]), cand

    def solve_speeds(self, verbose=True, scales=None, model=0, unit=None):
        """Speed of the camera for every frame step in MAP UNITS: self.v[n] = distance travelled from frame n to n + 1.
        Inside a straight the feature tracks give the relative steps. Their size comes from
          1. the collars the camera passes there (their light band has radius COLLAR_R = 61.06: collar_ruler), or
          2. COLMAP's step sizes times self.unit, the map units per COLMAP unit (median over the straights with
             collars; give `unit` when a shot has no collars at all), or
          3. `scales` {first frame of a straight: speed in map units per frame}.
        Bends are interpolated."""
        cs = self.colmap_steps(model)
        sec = self.sections(); self.T = self.tracks(10, 3)
        self.v = {}; self.straight_info = []
        for kind, a, b, fw, up in sec:
            if kind != 'straight' or b - a < 3: continue
            axis = np.array(AXES[fw], dtype=float)
            s, nt = self.straight_steps(a, b, axis)
            st = np.diff(s); fit = _robust_smooth(st); s_fit = np.r_[0.0, np.cumsum(fit)]
            c = np.array([cs[n] for n in range(a, b) if n in cs]); col = None
            if len(c) >= 3:
                med = np.median(c); c = c[(c > med / 2.5) & (c < med * 2.5)]; col = float(np.median(c))
            Rrel, cand = self.collar_ruler(a, b, s_fit)
            ruler = COLLAR_R / Rrel * float(np.mean(fit)) if Rrel else None        # map units per frame (mean of the straight)
            self.straight_info.append(dict(a=a, b=b, forward=fw, up=up, steps=fit, raw_steps=st, tracks=nt, colmap=col, ruler=ruler, speed=None, src='none'))
        info = self.straight_info
        ratios = [d['ruler'] / d['colmap'] for d in info if d['ruler'] and d['colmap']]
        self.unit = float(unit) if unit else (float(np.median(ratios)) if ratios else None)
        for d in info:
            if scales and d['a'] in scales: d['speed'] = float(scales[d['a']]); d['src'] = 'given'
            elif d['ruler'] and (d['colmap'] is None or self.unit is None or abs(d['ruler'] / (d['colmap'] * self.unit) - 1) < 0.2):
                d['speed'] = d['ruler']; d['src'] = 'collars'
            elif d['colmap'] and self.unit: d['speed'] = d['colmap'] * self.unit; d['src'] = 'colmap'
        for i, d in enumerate(info):                        # no measurement: continue the neighbours' speed
            if d['speed'] is None:
                nb = [x['speed'] for x in info[max(0, i - 1):i + 2] if x['speed'] is not None]
                d['speed'] = float(np.mean(nb)) if nb else 60.0; d['src'] = 'neighbours' if nb else 'guess'
        for d in info:
            k = d['speed'] / float(np.mean(d['steps']))
            for i, n in enumerate(range(d['a'], d['b'])): self.v[n] = float(k * d['steps'][i])
            if verbose: print('straight %d-%d %s: %d tracks, speed %.1f..%.1f map units per frame (%s; collars say %s, COLMAP %s)' % (
                d['a'], d['b'], d['forward'], d['tracks'], k * d['steps'].min(), k * d['steps'].max(), d['src'],
                '-' if not d['ruler'] else '%.1f' % d['ruler'], '-' if not (d['colmap'] and self.unit) else '%.1f' % (d['colmap'] * self.unit)))
        fr = sorted(self.R); known = sorted(self.v)
        for n in fr[:-1]:
            if n in self.v: continue
            lo = max((k for k in known if k < n), default=None); hi = min((k for k in known if k > n), default=None)
            if lo is None: self.v[n] = self.v[hi]
            elif hi is None: self.v[n] = self.v[lo]
            else: self.v[n] = self.v[lo] + (self.v[hi] - self.v[lo]) * (n - lo) / float(hi - lo)
        return self

    # ------------------------------------------------------------------ path
    def build_path(self, bends=None, default_radius=None):
        """The camera path as straight lines and circular arcs, and the camera's place on it for every frame.
        Straights run along their room axis for the distance travelled in them. A bend between two straights is
          a line of length `lead` on the old axis, an arc of `radius`, and a line of length `tail` on the new axis.
        bends: {first frame of the bend (as report_orientation prints it): dict(radius=..., lead=..., tail=...)};
        without `tail` the three pieces together are as long as the distance travelled at the speeds interpolated
        between the two straights; with `tail` the speed inside the bend follows from the length (smooth bump).
        Defaults: radius = default_radius (or the largest that fits), the arc centred in the bend.
        -> self.path (Path), self.s[n] (arclength at frame n), self.P[n] (position); units as self.v."""
        self.path, self.s, self.bend_info, self.v_path = make_path(self.sections(), sorted(self.R), self.v, self.R, bends, default_radius)
        fr = sorted(self.R)
        self.P = {n: self.path.point(self.s[n])[0] for n in fr}
        self.tangent = {n: self.path.point(self.s[n])[1] for n in fr}
        return self

    def solve_paths(self, pre=5, post=5, verbose=True, adopt_rotation=1.5):
        """Camera position of every frame (self.Pn). Straights: along their axis with the steps of solve_speeds.
        Bends: bundle adjustment with the orientations held (bendba.adjust): the matched features show which way the
        camera moves from frame to frame while the speed stays near the value interpolated between the straights.
        Bend after bend, each starting from the end of the one before."""
        import bendba
        sec = self.sections(); st = [x for x in sec if x[0] == 'straight']; fr = sorted(self.R); v = self.v
        assert st, 'no straight section in the shot'
        if not hasattr(self, 'T') or self.T is None: self.T = self.tracks(10, 3)
        P = {}; self.ba = {}
        first = st[0]; ax = np.array(AXES[first[3]], dtype=float); P[first[1]] = np.zeros(3)
        for n in range(first[1], first[2]): P[n + 1] = P[n] + ax * v[n]
        for n in range(first[1] - 1, fr[0] - 1, -1): P[n] = P[n + 1] - ax * v[n]          # frames before the first straight: straight on
        def adopt(C, Rn, frames):
            for n in frames:
                P[n] = C[n]
                if adopt_rotation and angle_ok(self.R[n], Rn[n], adopt_rotation):
                    dR = Rn[n] @ self.R[n].T; self.R[n] = Rn[n]
                    for mo in 'EL':
                        if hasattr(self, 'RM') and (n, mo) in self.RM: self.RM[(n, mo)] = O.orthonormal(dR @ self.RM[(n, mo)])
        def angle_ok(Ra, Rb, lim): return O.angle_between(Ra, Rb) <= lim
        for k in range(len(st) - 1):
            cur, nxt = st[k], st[k + 1]
            fa = np.array(AXES[cur[3]], dtype=float); fb = np.array(AXES[nxt[3]], dtype=float)
            a0 = max(cur[1], cur[2] - pre + 1); b1 = min(nxt[2], nxt[1] + post - 1)
            frames = [n for n in range(a0, b1 + 1) if n in self.R]; fixed = [n for n in frames if n <= cur[2]]
            # start: a quarter turn spread over the whole bend (or straight on when the tube does not turn)
            C0 = {n: P[n] for n in fixed}; L = sum(v[n] for n in range(cur[2], nxt[1])); s = 0.0
            turn = abs(float(fa @ fb)) < 0.99
            if turn:
                th = math.acos(max(-1.0, min(1.0, float(fa @ fb)))); r = L / th
            for n in range(cur[2] + 1, b1 + 1):
                s += v[n - 1]
                if not turn: C0[n] = P[cur[2]] + fa * s
                elif s <= L: ph = s / r; C0[n] = P[cur[2]] + r * (math.sin(ph) * fa + (1 - math.cos(ph)) * fb)
                else: C0[n] = P[cur[2]] + r * (fa + fb) + fb * (s - L)
            basis = np.array([fa, fb]) if turn else None
            if verbose: print('bend %d-%d (%s -> %s)' % (cur[2] + 1, nxt[1] - 1, cur[3], nxt[3]))
            C, Rn, X, rep = bendba.adjust(frames, fixed, C0, {n: self.R[n] for n in frames}, self.T, v, straight=(nxt[1], b1, fb), basis=basis,
                                          verbose=verbose, rot_free=[n for n in frames if self.status.get(n) != 'axis'])
            self.ba[cur[2] + 1] = rep
            adopt(C, Rn, [n for n in frames if cur[2] < n < nxt[1]])
            # the straight after the bend: on one line; its place across the axis = mean of its adjusted frames
            Q = np.array([C[n] for n in range(nxt[1], b1 + 1)]); side = Q - np.outer(Q @ fb, fb)
            P[nxt[1]] = side.mean(axis=0) + fb * float(C[nxt[1]] @ fb)
            for n in range(nxt[1], nxt[2]): P[n + 1] = P[n] + fb * v[n]
        last = st[-1]
        if last[2] < fr[-1]:                                    # the shot ends in a bend (or just after the last straight)
            fa = np.array(AXES[last[3]], dtype=float); w = getattr(self, 'bend_axis', {}).get(last[2] + 1)
            a0 = max(last[1], last[2] - pre + 1); frames = [n for n in range(a0, fr[-1] + 1) if n in self.R]; fixed = [n for n in frames if n <= last[2]]
            C0 = {n: P[n] for n in fixed}; s = 0.0
            for n in range(last[2] + 1, fr[-1] + 1): s += v[n - 1]; C0[n] = P[last[2]] + fa * s
            if len(frames) - len(fixed) >= 2 and w is not None:
                if verbose: print('open bend %d-%d (from %s)' % (last[2] + 1, fr[-1], last[3]))
                C, Rn, X, rep = bendba.adjust(frames, fixed, C0, {n: self.R[n] for n in frames}, self.T, v, basis=np.array([fa, np.cross(w, fa)]),
                                              verbose=verbose, rot_free=[n for n in frames if self.status.get(n) != 'axis'])
                self.ba[last[2] + 1] = rep; adopt(C, Rn, [n for n in frames if n > last[2]])
            else:
                for n in range(last[2] + 1, fr[-1] + 1): P[n] = C0[n]
        p0 = P[fr[0]].copy()                                    # origin: the camera of the shot's first frame
        self.Pn = {n: p - p0 for n, p in P.items()}
        return self

    def build_curve(self, smooth=0.6, dt=0.05):
        """The path as one smooth curve through the frame positions of solve_paths. Straights stay exactly straight;
        in each bend the adjusted positions are kept between the two straights' lines (a quarter turn never goes back)
        and smoothed (`smooth` weighs the change of direction from frame to frame against the measured positions).
        -> self.curve (Curve with the film frame number at every point), self.s[n], self.P[n], self.tangent[n]"""
        fr = sorted(self.Pn); idx = {n: i for i, n in enumerate(fr)}
        Q = np.array([self.Pn[n] for n in fr], dtype=float)
        sec = self.sections(); st = [x for x in sec if x[0] == 'straight']
        for k in range(len(st)):
            cur = st[k]; nxt = st[k + 1] if k + 1 < len(st) else None
            a = cur[2]; b = nxt[1] if nxt else fr[-1] + 1
            inner = [n for n in range(a + 1, b) if n in idx]
            if not inner: continue
            fa = np.array(AXES[cur[3]], dtype=float)
            if nxt is not None:
                fb = np.array(AXES[nxt[3]], dtype=float)
                if abs(fa @ fb) < 0.1:                          # quarter turn: both bend-plane coordinates monotone, between the ends
                    from sklearn.isotonic import IsotonicRegression
                    ii = [idx[a]] + [idx[n] for n in inner] + [idx[b]]
                    for ax in (fa, fb):
                        u = Q[ii] @ ax; lo, hi = min(u[0], u[-1]), max(u[0], u[-1])
                        un = IsotonicRegression(y_min=lo, y_max=hi, increasing=bool(u[-1] >= u[0])).fit_transform(np.arange(len(u)), u)
                        Q[ii] += np.outer(un - u, ax)
            # smoothing with the frames around the bend held: data + smooth * second differences
            hold_lo = [n for n in (a - 1, a) if n in idx]; hold_hi = [n for n in ((b, b + 1) if nxt else ()) if n in idx]
            chain = hold_lo + inner + hold_hi; m = len(chain); free = [i for i, n in enumerate(chain) if n in inner]
            Afull = []; bfull = []
            for j, i in enumerate(free):
                row = np.zeros(len(free)); row[j] = 1.0; Afull.append(row); bfull.append(Q[idx[chain[i]]])
            for i in range(1, m - 1):
                row = np.zeros(len(free)); rhs = np.zeros(3)
                for off, c in ((-1, 1.0), (0, -2.0), (1, 1.0)):
                    n = chain[i + off]
                    if n in inner: row[free.index(i + off)] += c * smooth
                    else: rhs -= c * smooth * Q[idx[n]]
                Afull.append(row); bfull.append(rhs)
            sol = np.linalg.lstsq(np.array(Afull), np.array(bfull), rcond=None)[0]
            for j, i in enumerate(free): Q[idx[chain[i]]] = sol[j]
        # dense curve: cubic Hermite between the frames (tangents from neighbouring frames)
        t = np.array(fr, dtype=float); D = np.gradient(Q, t, axis=0)
        for kind, a, b, fw, up in sec:                           # inside straights the tangent is the axis exactly
            if kind != 'straight': continue
            ax = np.array(AXES[fw], dtype=float)
            for n in range(a, b + 1):
                if n in idx: D[idx[n]] = ax * float(D[idx[n]] @ ax)
        tt = np.arange(fr[0] - 0.5, fr[-1] + 0.5 + 1e-9, dt); pts = np.zeros((len(tt), 3))
        for j, x in enumerate(tt):
            if x <= t[0]: pts[j] = Q[0] + D[0] * (x - t[0]); continue
            if x >= t[-1]: pts[j] = Q[-1] + D[-1] * (x - t[-1]); continue
            i = int(np.searchsorted(t, x) - 1); h = t[i + 1] - t[i]; u = (x - t[i]) / h
            h00 = 2 * u ** 3 - 3 * u ** 2 + 1; h10 = u ** 3 - 2 * u ** 2 + u; h01 = -2 * u ** 3 + 3 * u ** 2; h11 = u ** 3 - u ** 2
            pts[j] = h00 * Q[i] + h10 * h * D[i] + h01 * Q[i + 1] + h11 * h * D[i + 1]
        self.Pq = {n: Q[idx[n]] for n in fr}
        self.curve = Curve(pts, tt)
        self.s = {n: self.curve.s_at_time(n) for n in fr}
        self.P = {n: self.curve.point(self.s[n])[0] for n in fr}
        self.tangent = {n: self.curve.point(self.s[n])[1] for n in fr}
        self.path = self.curve
        return self

    def moments(self):
        """[(time, frame, moment, position, Rcw, arclength)] at 60 per second: the earlier (E) and later (L) moment of
        every frame, a quarter of a frame before and after the frame's own place on the path"""
        fr = sorted(self.P); out = []; RM = getattr(self, 'RM', None); cv_ = getattr(self, 'curve', None)
        for i, n in enumerate(fr):
            V = getattr(self, 'v_path', None) or self.v
            vprev = V[fr[i - 1]] if i > 0 else V[n]
            vnext = V[n] if n in V else vprev
            Rp = self.R[fr[i - 1]] if i > 0 else self.R[n]; Rn = self.R[fr[i + 1]] if i + 1 < len(fr) else self.R[n]
            for mo, dq, ds, Ro in (('E', -0.25, -0.25 * vprev, Rp), ('L', 0.25, 0.25 * vnext, Rn)):
                Rm = RM[(n, mo)] if RM and (n, mo) in RM else O.orthonormal(_slerp(self.R[n], Ro, 0.25))
                sm = cv_.s_at_time(n + dq) if cv_ is not None and cv_.t is not None else self.s[n] + ds
                out.append((n * 1001 / 30000.0 + (1001 / 60000.0 if mo == 'L' else 0.0), n, mo, self.path.point(sm)[0], Rm, sm))
        return out

    def triangulate(self, max_err=2.0, min_views=3):
        """feature points from the tracks with the cameras of build_path(): (points [k,3], median error px [k], views [k])"""
        fr = set(self.P); pts = []; errs = []; nv = []
        for tr in self.T:
            obs = [(n, p) for n, p in tr.items() if n in fr]
            if len(obs) < min_views: continue
            A = np.zeros((3, 3)); bb = np.zeros(3); ds = []
            for n, p in obs:
                d = self.R[n].T @ np.array([(p[0] - 640.0) / F_HD, (p[1] - 400.0) / F_HD, 1.0]); d /= np.linalg.norm(d)
                M = np.eye(3) - np.outer(d, d); A += M; bb += M @ self.P[n]; ds.append(d)
            try: X = np.linalg.solve(A + 1e-12 * np.eye(3), bb)
            except np.linalg.LinAlgError: continue
            e = []; front = True
            for (n, p), d in zip(obs, ds):
                q = X - self.P[n]; dep = q @ d
                if dep <= 0: front = False; break
                e.append(np.linalg.norm(q - dep * d) / dep * F_HD)
            if not front: continue
            pts.append(X); errs.append(float(np.median(e))); nv.append(len(obs))
        pts = np.array(pts); errs = np.array(errs); nv = np.array(nv)
        ok = errs <= max_err
        return pts[ok], errs[ok], nv[ok]

    def save(self, path):
        cv_ = getattr(self, 'curve', None)
        d = dict(name=self.name, first=self.first, last=self.last, R=self.R, RE=self.RE, RL=self.RL, status=self.status,
                 RM=getattr(self, 'RM', None), turn=getattr(self, 'turn', None), bend_axis=getattr(self, 'bend_axis', None),
                 steps=self.steps, v=getattr(self, 'v', None), P=getattr(self, 'P', None), Pn=getattr(self, 'Pn', None), s=getattr(self, 's', None),
                 straights=getattr(self, 'straight_info', None), sections=self.sections(), ba=getattr(self, 'ba', None),
                 curve_P=None if cv_ is None else cv_.P, curve_t=None if cv_ is None else cv_.t,
                 moments=self.moments() if cv_ is not None else None)
        pickle.dump(d, open(path, 'wb'))
