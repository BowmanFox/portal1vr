"""Radial edges about the tube axis in a straight section, and the scale they give.

In a straight tube the camera is on the axis and looks along it, so every ring of the tube is a circle about the
picture centre. An edge of true radius R on a ring at distance d appears at radius r = f R / d, so f / r falls
linearly as the camera advances; the rate of that fall for the collars' outer edge gives the camera's advance in
units of the collar radius.
    edges = radial_edges(n, 'E')                    # [(r, strength, polarity)] 640x400 pixel units, polarity +1 = brighter inside
"""
import numpy as np, cv2
from orient import F, CX, CY

_RS = np.arange(3.0, 330.0, 0.25)
_ANG = np.linspace(0, 2 * np.pi, 720, endpoint=False)


def radial_profile(n, moment='E', cx=CX, cy=CY, sector=None):
    """mean brightness on circles about (cx, cy): (radii, profile, coverage). sector=(a0, a1) degrees limits the angles."""
    g = cv2.imread('/home/claude/data/moments/%s/f%04d.jpg' % (moment, n), cv2.IMREAD_GRAYSCALE).astype(np.float32)
    g = cv2.GaussianBlur(g, (0, 0), 1.0)
    ang = _ANG if sector is None else np.radians(np.arange(sector[0], sector[1], 0.5))
    xs = (cx + _RS[None, :] * np.cos(ang)[:, None]) * 2 + 0.5; ys = (cy + _RS[None, :] * np.sin(ang)[:, None]) * 2 + 0.5
    v = cv2.remap(g, xs.astype(np.float32), ys.astype(np.float32), cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT, borderValue=-1)
    ok = v >= 0
    return _RS, np.where(ok, v, 0).sum(axis=0) / np.maximum(ok.sum(axis=0), 1), ok.mean(axis=0)


def radial_edges(n, moment='E', min_strength=1.2, min_cover=0.35, **kw):
    """radial brightness steps: list of (r, strength, polarity), polarity +1 when the inside is brighter"""
    rs, p, cov = radial_profile(n, moment, **kw)
    k = 6                                                   # derivative over 1.5 px either side
    d = np.zeros_like(p); d[k:-k] = (p[:-2 * k] - p[2 * k:])          # inside minus outside
    out = []
    a = np.abs(d)
    for i in range(k + 1, len(p) - k - 1):
        if a[i] >= min_strength and a[i] >= a[i - 1] and a[i] > a[i + 1] and a[i] == a[max(0, i - 8):i + 9].max() and cov[i] >= min_cover:
            # sub-sample peak
            den = a[i - 1] - 2 * a[i] + a[i + 1]; off = 0.5 * (a[i - 1] - a[i + 1]) / den if abs(den) > 1e-9 else 0.0
            out.append((float(rs[i] + off * (rs[1] - rs[0])), float(a[i]), 1 if d[i] > 0 else -1))
    return out


def edge_classes(frames, s, moment='E', min_strength=4.0, slope_range=(0.2, 8.0)):
    """Groups the radial edges of a straight section by how fast f / r falls with the camera position.
    frames: frame numbers; s: camera position along the axis for each (any linear unit).
    -> list of dict(slope, polarity, support, rings=[intercepts]) sorted by support. For an edge of true radius R:
       slope = (camera advance per unit of s) / R, so two edge classes have slopes in the inverse ratio of their radii."""
    obs = []                                # (frame index, y = f / r, strength, polarity)
    for i, n in enumerate(frames):
        for r, st, pol in radial_edges(n, moment, min_strength=min(2.0, min_strength)):
            if st >= min_strength and r > 6: obs.append((i, F / r, st, pol))
    obs = np.array(obs)
    out = []
    for pol in (1, -1):
        o = obs[obs[:, 3] == pol]
        if len(o) < 4: continue
        votes = []
        for a in o:
            for b in o:
                di = int(b[0] - a[0])
                if di < 1 or di > 2: continue
                ds = s[int(b[0])] - s[int(a[0])]
                if ds <= 0 or b[1] >= a[1]: continue
                sl = (a[1] - b[1]) / ds
                if slope_range[0] <= sl <= slope_range[1]: votes.append((sl, min(a[2], b[2])))
        if not votes: continue
        v = np.array(votes); lg = np.log(v[:, 0])
        bins = np.arange(np.log(slope_range[0]), np.log(slope_range[1]), 0.04)
        h = np.zeros(len(bins))
        for x, wgt in zip(lg, v[:, 1]):
            k = int((x - bins[0]) / 0.04)
            if 0 <= k < len(h): h[k] += wgt
        hs = np.convolve(h, [0.25, 0.5, 0.25], 'same')
        for k in np.argsort(hs)[::-1][:6]:
            if hs[k] < 0.25 * hs.max() or (0 < k < len(hs) - 1 and (hs[k] < hs[k - 1] or hs[k] < hs[k + 1])): continue
            sl = float(np.exp(bins[k] + 0.02))
            # collect the edges on lines of this slope: intercept A = y + slope * s
            A = o[:, 1] + sl * s[o[:, 0].astype(int)]
            order = np.argsort(A); rings = []; cur = [order[0]]
            for q in order[1:]:
                if A[q] - A[cur[-1]] < 0.035 * max(A[q], 3.0): cur.append(q)
                else:
                    if len({int(o[c, 0]) for c in cur}) >= 3: rings.append(cur)
                    cur = [q]
            if len({int(o[c, 0]) for c in cur}) >= 3: rings.append(cur)
            if not rings: continue
            # refine the slope with all the rings' edges (common slope, one intercept per ring)
            rows = []; ys = []
            for j, rg in enumerate(rings):
                for c in rg:
                    row = np.zeros(len(rings) + 1); row[j] = 1.0; row[-1] = -s[int(o[c, 0])]; rows.append(row); ys.append(o[c, 1])
            sol = np.linalg.lstsq(np.array(rows), np.array(ys), rcond=None)[0]
            res = np.array(rows) @ sol - np.array(ys)
            out.append(dict(slope=float(sol[-1]), polarity=pol, support=float(sum(o[c, 2] for rg in rings for c in rg)), rings=[float(x) for x in sol[:-1]],
                            n=len(ys), rms=float(np.sqrt(np.mean(res ** 2)))))
    # merge duplicates
    out.sort(key=lambda d: -d['support']); keep = []
    for d in out:
        if all(not (abs(np.log(d['slope'] / k['slope'])) < 0.06 and d['polarity'] == k['polarity']) for k in keep): keep.append(d)
    return keep


GROOVE = 0.735          # radius of the collars' strongest dark-inside edge relative to the outer edge of the light band


def ring_fit(frames, s, moment='E', min_strength=4.0, kappa_range=(0.25, 7.0), verbose=False):
    """Scale of a straight section in collar radii: finds kappa (camera advance in collar radii per unit of s) for which
    the collars' two characteristic edges (light band outer edge, brighter inside, at radius 1; groove edge, darker
    inside, at GROOVE) of all frames fall on the same ring positions.
    -> dict(kappa, rings=[position along s where the camera passes each ring], score, second) or None"""
    obs = []
    for i, n in enumerate(frames):
        for r, st, pol in radial_edges(n, moment, min_strength=2.0):
            if st >= min_strength and r > 8: obs.append((s[i], F / r, st, pol))
    if len(obs) < 8: return None
    o = np.array(obs); rho = np.where(o[:, 3] > 0, 1.0, GROOVE)
    y = o[:, 1] * rho                              # distance of the ring ahead in collar radii if the edge is what we think
    bw = 0.12
    def score(k, detail=False):
        S = y + k * o[:, 0]
        lo = S.min() - 1; nb = int((S.max() + 1 - lo) / bw) + 2
        hp = np.zeros(nb); hm = np.zeros(nb)
        idx = ((S - lo) / bw).astype(int)
        np.add.at(hp, idx[o[:, 3] > 0], 1.0); np.add.at(hm, idx[o[:, 3] < 0], 1.0)
        ker = np.array([0.5, 1.0, 1.0, 1.0, 0.5])
        hp = np.convolve(hp, ker, 'same'); hm = np.convolve(hm, ker, 'same')
        both = np.sqrt(hp * hm)                    # a ring needs both of its edges, each seen in several frames
        if not detail: return float((both ** 2).sum())
        peaks = [i for i in range(2, nb - 2) if both[i] >= 2.0 and both[i] == both[i - 2:i + 3].max()]
        return [(lo + (i + 0.5) * bw, float(both[i])) for i in peaks]
    ks = np.exp(np.arange(np.log(kappa_range[0]), np.log(kappa_range[1]), 0.01))
    sc = np.array([score(k) for k in ks])
    i = int(np.argmax(sc)); k0 = ks[i]
    fine = np.linspace(k0 * 0.98, k0 * 1.02, 41); sf = np.array([score(k) for k in fine]); k0 = float(fine[int(np.argmax(sf))])
    # second best away from the peak, to judge how clear the answer is
    far = np.abs(np.log(ks / k0)) > 0.08
    second = float(sc[far].max()) if far.any() else 0.0
    rings = score(k0, detail=True)
    # least-squares refinement of kappa and the ring positions on the edges that belong to the found rings
    S = y + k0 * o[:, 0]; rows = []; ys = []; centers = [p for p, h in rings]
    if centers:
        for e in range(len(o)):
            j = int(np.argmin([abs(S[e] - c) for c in centers]))
            if abs(S[e] - centers[j]) < 0.25:
                row = np.zeros(len(centers) + 1); row[j] = 1.0; row[-1] = -o[e, 0]; rows.append(row); ys.append(y[e])
        if len(ys) >= len(centers) + 3:
            sol = np.linalg.lstsq(np.array(rows), np.array(ys), rcond=None)[0]
            if abs(sol[-1] / k0 - 1) < 0.05: k0 = float(sol[-1]); centers = [float(c) for c in sol[:-1]]
    out = dict(kappa=k0, rings=[c / k0 for c in centers], ring_S=centers, score=float(sc.max()), second=second, n_edges=len(o))
    if verbose: print('   kappa %.3f R per unit, score %.0f (next best %.0f), rings pass at s = %s' % (k0, out['score'], second, np.round(out['rings'], 2).tolist()))
    return out


def edge_lines(frames, s, moment='E', min_strength=3.0, min_frames=3, tol=0.03):
    """Tracks of radial edges through a straight section: edges of consecutive frames whose f / r falls in a straight
    line against the camera position s. -> list of dict(slope, intercept, polarity, strength, n, frames, rms),
    strongest first. slope = (camera advance per unit s) / (true radius of the edge); the camera passes the edge's
    ring at s = intercept / slope."""
    per = []
    for i, n in enumerate(frames):
        per.append([(F / r, st, pol) for r, st, pol in radial_edges(n, moment, min_strength=2.0) if st >= min_strength and r > 6])
    used = [set() for _ in per]; out = []
    order = sorted(((st, i, k) for i, es in enumerate(per) for k, (y, st, pol) in enumerate(es)), reverse=True)
    for st0, i0, k0 in order:
        if k0 in used[i0]: continue
        y0, _, pol = per[i0][k0]
        best = None
        # try every partner in the next two frames to define a line, keep the line with the most support
        for di in (1, 2):
            if i0 + di >= len(per): continue
            for k1, (y1, st1, p1) in enumerate(per[i0 + di]):
                if p1 != pol or y1 >= y0 or k1 in used[i0 + di]: continue
                sl = (y0 - y1) / (s[i0 + di] - s[i0])
                if sl <= 0: continue
                mem = []
                for j, es in enumerate(per):
                    yp = y0 - sl * (s[j] - s[i0])
                    if yp <= 0.8: continue
                    cand = [(abs(y - yp), k) for k, (y, stj, pj) in enumerate(es) if pj == pol and k not in used[j] and abs(y - yp) < tol * max(yp, 2.0) + 0.05]
                    if cand: mem.append((j, min(cand)[1]))
                if len(mem) >= min_frames and (best is None or len(mem) > len(best[1])): best = (sl, mem)
        if best is None: continue
        sl, mem = best
        xs = np.array([s[j] for j, k in mem]); ys = np.array([per[j][k][0] for j, k in mem])
        A = np.c_[np.ones(len(xs)), -xs]; sol = np.linalg.lstsq(A, ys, rcond=None)[0]
        res = ys - A @ sol
        if sol[1] <= 0: continue
        for j, k in mem: used[j].add(k)
        out.append(dict(slope=float(sol[1]), intercept=float(sol[0]), polarity=pol, strength=float(np.mean([per[j][k][1] for j, k in mem])), n=len(mem),
                        frames=[frames[j] for j, k in mem], rms=float(np.sqrt(np.mean(res ** 2))), cross=float(sol[0] / sol[1])))
    out.sort(key=lambda d: -d['strength'] * d['n'])
    return out


def collar_scale(frames, s, moment='E', verbose=False):
    """camera advance in collar radii per unit of s, from pairs of edge tracks that belong to one collar face: the
    light band's outer edge (brighter inside, radius 1) and the groove edge (darker inside, radius GROOVE), which
    pass the camera at the same position. -> (kappa, [positions s where collars pass], pairs) or (None, [], lines)"""
    L = edge_lines(frames, s, moment)
    pairs = []
    for p in L:
        if p['polarity'] != 1: continue
        for m in L:
            if m['polarity'] != -1: continue
            if abs(m['slope'] * GROOVE / p['slope'] - 1) < 0.05 and abs(m['cross'] - p['cross']) < 0.6:
                pairs.append((p['strength'] * p['n'] + m['strength'] * m['n'], p, m))
    if verbose:
        for l in L[:12]: print('     edge %+d slope %.3f passes at s=%.2f  strength %.0f  frames %d  rms %.3f' % (l['polarity'], l['slope'], l['cross'], l['strength'], l['n'], l['rms']))
    if not pairs: return None, [], L
    pairs.sort(key=lambda x: -x[0])
    w = np.array([x[0] for x in pairs]); k = np.array([x[1]['slope'] for x in pairs])
    kappa = float(np.sum(w * k) / np.sum(w))
    return kappa, sorted({round(x[1]['cross'], 2) for x in pairs}), pairs
