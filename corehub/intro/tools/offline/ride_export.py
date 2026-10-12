"""Measures one shot of the tube ride and writes it as JSON for the map generators (gen/data/<name>_ride.json).

usage: ride_export.py DB first last anchor NAME [forward=+x] [up=+z] [--unit U] [--scales '{"986": 0.33}'] [--verbose]
  DB       name of the COLMAP run of the shot (/home/claude/sfm/DB, made by run_sfm.py)
  anchor   a frame in a straight tube section; forward / up: the room axes the camera looks along / has overhead there
  --unit   map units per solver unit (default 1 = write solver units; see AGENT_GUIDE on finding it from the collars)
  --scales speed per frame of single straights (solver units, key = first frame of the straight) to overrule COLMAP's
The JSON holds, in solver units times --unit, room axes:
  moments   [[time, frame, 'E'|'L', x, y, z, fx, fy, fz, ux, uy, uz], ...]   camera at 60 per second (position, forward, up)
  curve     [[frame number, x, y, z], ...]   the path as closely spaced points (the tube's centre line)
  sections  straights (with forward / up axes) and bends, as frame ranges
  frames    {frame: [x, y, z]}, s {frame: arclength}, speed {frame: step to the next frame}
  planes    axis-aligned surfaces found in the triangulated feature points
  rings     places where the camera passes a tube collar (from the radial edges in the straights)
The orientation is solved once and kept in out/NAME_orient.pkl (delete it to solve again)."""
import sys, json, math, pickle
import numpy as np
sys.path.insert(0, '/home/claude/offline')
from ride import Shot, AXES
import orient as O
from ringscale import edge_lines


def planes_of(X, min_frac=0.04, bw=None):
    """axis-aligned planes of a point cloud: peaks of the coordinate histograms -> [dict(axis, coord, n, lo, hi)]"""
    out = []
    ext = np.percentile(X, 98, axis=0) - np.percentile(X, 2, axis=0)
    bw = bw or max(float(ext.max()) / 400.0, 1e-3)
    for ax in range(3):
        v = X[:, ax]; edges = np.arange(v.min() - bw, v.max() + 2 * bw, bw)
        h, _ = np.histogram(v, bins=edges); hs = np.convolve(h, [1, 1, 1], 'same')
        for i in np.argsort(hs)[::-1][:12]:
            if hs[i] < min_frac * len(X) or hs[i] < hs[max(0, i - 3):i + 4].max(): continue
            c = edges[i] + bw / 2; m = np.abs(v - c) < 1.5 * bw
            c = float(np.median(v[m])); m = np.abs(v - c) < 2.0 * bw
            P = X[m]
            out.append(dict(axis='xyz'[ax], coord=c, n=int(m.sum()), lo=[float(x) for x in np.percentile(P, 2, axis=0)], hi=[float(x) for x in np.percentile(P, 98, axis=0)],
                            thickness=float(np.std(v[m]))))
    out.sort(key=lambda d: -d['n'])
    return out


def export(S, X, path, unit=1.0):
    mom = []
    for t, n, mo, p, R, sm in S.moments():
        f, r, u = O.to_basis(R)
        mom.append([round(t, 6), n, mo] + [round(float(x) * unit, 4) for x in p] + [round(float(x), 6) for x in f] + [round(float(x), 6) for x in u])
    sec = [dict(kind=k, first=a, last=b, forward=fw, up=up) for k, a, b, fw, up in S.sections()]
    rings = []
    for d in S.straight_info:
        fr = list(range(d['a'], d['b'] + 1)); s = np.arange(len(fr), dtype=float)
        L = edge_lines(fr, s)
        cr = sorted(l['cross'] for l in L if l['n'] >= 4 and l['strength'] >= 8 and -2 < l['cross'] < len(fr) + 8)
        groups = []
        for c in cr:
            if groups and c - groups[-1][-1] < 1.2: groups[-1].append(c)
            else: groups.append([c])
        for g in groups:
            if len(g) >= 2: rings.append(dict(straight=d['a'], frame=float(d['a'] + np.median(g)), edges=len(g)))
    cv = S.curve
    pl = planes_of(X) if len(X) > 50 else []
    for p in pl:
        p['coord'] *= unit; p['lo'] = [x * unit for x in p['lo']]; p['hi'] = [x * unit for x in p['hi']]; p['thickness'] *= unit
    out = dict(db=S.name, first=S.first, last=S.last, unit=unit, moments=mom, sections=sec, planes=pl, rings=rings,
               frames={str(n): [float(x) * unit for x in S.P[n]] for n in sorted(S.P)}, speed={str(n): float(v) * unit for n, v in S.v.items()},
               curve=[[round(float(t), 3)] + [round(float(x) * unit, 3) for x in p] for t, p in zip(cv.t, cv.P)],
               s={str(n): float(x) * unit for n, x in S.s.items()},
               bend_axis={str(k): [float(x) for x in w] for k, w in getattr(S, 'bend_axis', {}).items()},
               ba={str(k): dict(points=r.get('points'), median=r.get('median'), weakest=min(r.get('per_frame', {0: 0}).values())) for k, r in getattr(S, 'ba', {}).items()})
    json.dump(out, open(path, 'w'))
    return out


def measure(db, first, last, anchor, name, forward='+x', up='+z', scales=None, verbose=False, model=0):
    """the whole measurement -> Shot (orientation, speeds, positions, curve)"""
    import os
    S = Shot(db, first, last)
    cache = '/home/claude/offline/out/%s_orient.pkl' % name
    if os.path.exists(cache):
        d = pickle.load(open(cache, 'rb')); S.R = d['R']; S.status = d['status']; S.steps = d['steps']; S.RE = d['RE']; S.RL = d['RL']
    else:
        S.solve_orientation(anchor=anchor, forward=forward, up=up)
        pickle.dump(dict(R=S.R, status=S.status, steps=S.steps, RE=S.RE, RL=S.RL), open(cache, 'wb'))
    S.solve_bends(verbose=verbose)
    S.report_orientation()
    S.solve_speeds(scales=scales, model=model)
    S.solve_paths(verbose=True)
    S.build_curve()
    return S


if __name__ == '__main__':
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument('db'); ap.add_argument('first', type=int); ap.add_argument('last', type=int); ap.add_argument('anchor', type=int); ap.add_argument('name')
    ap.add_argument('forward', nargs='?', default='+x'); ap.add_argument('up', nargs='?', default='+z')
    ap.add_argument('--scales', default='{}'); ap.add_argument('--model', type=int, default=0)
    ap.add_argument('--verbose', action='store_true'); ap.add_argument('--unit', type=float, default=1.0, help='map units per solver unit: everything is written in map units then')
    a = ap.parse_args()
    S = measure(a.db, a.first, a.last, a.anchor, a.name, a.forward, a.up, {int(k): v for k, v in json.loads(a.scales).items()} or None, a.verbose, a.model)
    X, e, nv = S.triangulate()
    S.save('/home/claude/offline/out/%s_ride.pkl' % a.name); np.save('/home/claude/offline/out/%s_points.npy' % a.name, X)
    o = export(S, X, '/home/claude/work/gen/data/%s_ride.json' % a.name, a.unit)
    print('%d moments, %d points, path length %.2f' % (len(o['moments']), len(X), S.curve.length * a.unit))
    for p in o['planes'][:10]: print('  plane %s = %.3f  (%d points)  extent %s .. %s' % (p['axis'], p['coord'], p['n'], np.round(p['lo'], 2).tolist(), np.round(p['hi'], 2).tolist()))
    for r in o['rings']: print('  collar passed at frame %.2f (%d edges)' % (r['frame'], r['edges']))
