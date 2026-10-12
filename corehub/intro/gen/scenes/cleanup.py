"""Clean-up of the r10dm base map's middle hall (applied after all other scenes).

All scenes after the iris/ascent (32.6 s on) are rebuilt in their own cells north of the old map (y > 3000), so the
old hall's decorative brushes (func_detail with x > -10000 in the old map's area) are never seen any more. The 2009 vbsp
runs out of brush sides (MAX_MAP_BRUSHSIDES) with them and the new cells together, so they are removed here. The
hall's world brushes (its sealed hull) and every named entity (func_brush, props, lights the director may still
address) stay, so the map stays sealed and the director finds what it looks for."""
import numpy as np

X_MIN = -10000.0          # the opening room, iris and ascent are at x < -11800 and stay untouched
Y_MAX = 3000.0            # the new cells start at y 3200


def _bounds(solid):
    pts = np.array([(p.x, p.y, p.z) for side in solid.sides for p in side.planes])
    return pts.min(axis=0), pts.max(axis=0)


def apply(v, d):
    removed = 0; ents_dropped = 0
    for e in list(v.by_class['func_detail']):
        keep = []
        for s in e.solids:
            lo, hi = _bounds(s)
            if lo[0] > X_MIN and hi[1] < Y_MAX: removed += 1
            else: keep.append(s)
        if len(keep) != len(e.solids):
            e.solids[:] = keep
            if not keep: e.remove(); ents_dropped += 1
    print('cleanup: removed %d old func_detail brushes of the middle hall (%d entities emptied)' % (removed, ents_dropped))
