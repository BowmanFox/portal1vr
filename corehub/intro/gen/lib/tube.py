"""Tube parts along a measured ride (lib.ride.Ride): rails, rail bends and collars.

The film's tubes: four thin square rails (1.8 thick) on the diagonals of the cross-section, 34 from the axis; along
them translucent collars (light band of radius 61.06) where the camera's rings are seen passing. The camera rides on
the tube axis, so the measured camera path IS the tube's centre line.

    from lib import tube
    tube.add_straight_rails(v, rd)                         # brushes along the straight pieces
    tube.add_bend_rails(v, rd, 'r11_rust_a')               # one model per bend (rails swept along the measured path)
    tube.add_collars(v, rd)                                 # collar props where the film's camera passes collars
    tube.axis_angles(d), tube.frame_angles(forward, left)   # prop angles helpers
"""
import math
import numpy as np
from . import vmfedit as E
from .ride import RAIL_RHO

RAIL_W = 1.8
RAIL_MAT = 'corehub_intro/p9_ascent_rail_v2'
COLLAR_MDL = 'models/corehub_intro/p9_ascent_collar_plain_v4.mdl'


def frame_angles(forward, left):
    """Source QAngle (pitch, yaw, roll) that rotates a model so its +X points along `forward` and its +Y along `left`"""
    F = np.asarray(forward, dtype=float); F = F / np.linalg.norm(F)
    L = np.asarray(left, dtype=float); L = L - F * (L @ F); L = L / np.linalg.norm(L)
    U = np.cross(F, L)
    pitch = -math.degrees(math.asin(max(-1.0, min(1.0, F[2]))))
    if abs(F[2]) > 0.99999:
        yaw = math.degrees(math.atan2(-L[0], L[1])); roll = 0.0
    else:
        yaw = math.degrees(math.atan2(F[1], F[0])); roll = math.degrees(math.atan2(L[2], U[2]))
    return pitch, yaw, roll


def axis_angles(d):
    """prop angles that point a model's +Z axis along direction d (for parts made around +Z, like the collars)"""
    d = np.asarray(d, dtype=float); d = d / np.linalg.norm(d)
    if abs(d[2]) > 0.999: return (0.0, 0.0, 0.0) if d[2] > 0 else (180.0, 0.0, 0.0)
    return (90.0 - math.degrees(math.asin(d[2])), math.degrees(math.atan2(d[1], d[0])), 0.0)


def _perp_axes(d):
    i = int(np.argmax(np.abs(d))); j, k = [a for a in range(3) if a != i]
    u = np.zeros(3); w = np.zeros(3); u[j] = 1.0; w[k] = 1.0
    return u, w


def add_straight_rails(v, rd, rho=RAIL_RHO, width=RAIL_W, material=RAIL_MAT, ent='detail', extend=0.0, pieces=None):
    """four rail strips along every straight piece of the ride's path (axis-aligned boxes). -> number of brushes"""
    n = 0
    if ent == 'detail': ent = v.create_ent(classname='func_detail')
    for a, b, d in (pieces if pieces is not None else rd.straights(extend)):
        if np.linalg.norm(b - a) < 1.0: continue
        assert abs(np.abs(d).max() - 1) < 1e-6, 'straight pieces must run along a map axis'
        u, w = _perp_axes(d)
        for su in (1, -1):
            for sw in (1, -1):
                c = (su * u + sw * w) * (rho / math.sqrt(2.0))
                lo = np.minimum(a, b) + c - (u + w) * width / 2; hi = np.maximum(a, b) + c + (u + w) * width / 2
                E.add_box(v, lo, hi, material, ent=ent); n += 1
    return n


def bend_ranges(rd, overlap=3.0):
    """arclength ranges of the path that are not straight (bends, and a final turn) -> [(s0, s1, section)]"""
    out = []
    for d in rd.sections:
        if d['kind'] == 'straight': continue
        s0 = max(0.0, d['s0'] - overlap); s1 = min(rd.length, d['s1'] + overlap)
        # a bend runs from the end of the straight before to the start of the straight after
        i = rd.sections.index(d)
        if i > 0 and rd.sections[i - 1]['kind'] == 'straight': s0 = rd.sections[i - 1]['s1'] - overlap
        else: s0 = 0.0
        if i + 1 < len(rd.sections) and rd.sections[i + 1]['kind'] == 'straight': s1 = rd.sections[i + 1]['s0'] + overlap
        else: s1 = rd.length
        if s1 - s0 > 2 * overlap + 1: out.append((s0, s1, d))
    return out


def add_bend_rails(v, rd, prefix, rho=RAIL_RHO, width=RAIL_W, step=6.0, ranges=None):
    """rails of the bends as models <prefix>_bend<k> (built here, origin at the bend's first point, map axes) and
    props for them. -> [(model name, origin)]"""
    from lib.gen import save
    from models.tubekit import rail_sweep, materials
    materials(); out = []
    st = [d for d in rd.sections if d['kind'] == 'straight']
    U = rd.transport(st[0]['up_vec'] if st else np.array([0, 0, 1.0])); W = np.cross(rd.T, U)
    for k, (s0, s1, d) in enumerate(ranges if ranges is not None else bend_ranges(rd)):
        m = (rd.S >= s0) & (rd.S <= s1); idx = np.where(m)[0]
        if len(idx) < 3: continue
        # thin the points to about `step` apart
        keep = [idx[0]]
        for i in idx[1:]:
            if rd.S[i] - rd.S[keep[-1]] >= step: keep.append(i)
        if keep[-1] != idx[-1]: keep.append(idx[-1])
        keep = np.array(keep); org = rd.curve[keep[0]].copy()
        mesh = rail_sweep(rd.curve[keep] - org, U[keep], W[keep], rho, width)
        name = '%s_bend%d' % (prefix, k)
        save(mesh, name)
        E.add_prop(v, 'models/corehub_intro/%s.mdl' % name, org, (0, 0, 0), name=name)
        out.append((name, org))
    return out


def add_collars(v, rd, model=COLLAR_MDL, frames=None, prefix=None, skip_near=None):
    """collar props where the film's camera passes collars (rd.rings, or the given frames). -> [(position, axis)]"""
    out = []
    pts = [(rd.pos(f), rd.direction(f)) for f in frames] if frames is not None else [(r['pos'], r['axis']) for r in rd.rings]
    for k, (p, a) in enumerate(pts):
        E.add_prop(v, model, p, axis_angles(a), name='%s_collar%d' % (prefix or 'r11_' + rd.name, k)); out.append((p, a))
    return out
