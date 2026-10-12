"""A measured shot of the tube ride in map coordinates (tools/offline/ride.py + ride_export.py measure it).

    rd = Ride('rust_a', origin=(-6000, 9000, 0))         # gen/data/rust_a_ride.json; map units throughout
    d.override_camera(rd.camera(), fov=60)               # the film's camera for this shot (60 samples per second)
    rd.pos(1000.5), rd.direction(1000.5)                 # camera position / direction of travel at a (fractional) frame
    rd.at(s)                                             # (position, tangent) at arclength s along the path
    rd.curve, rd.S, rd.t                                 # the path as closely spaced points, their arclength and film frame
    rd.sections                                          # straights and bends: frame range, arclength range, axes
    rd.straights()                                       # [(start, end, axis vector)] of the straight tube pieces
    rd.rails(rho=34)                                     # the four rails as polylines along the whole path
    rd.rings, rd.planes                                  # collars the camera passes; wall planes found in the film

origin: map position of the measured origin (the camera of the shot's first frame); axes: where the room's +x, +y, +z
point in the map, e.g. ('+x', '+y', '+z') (must keep right-handedness)."""
import json, math, os
import numpy as np

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
AX = {'+x': (1, 0, 0), '-x': (-1, 0, 0), '+y': (0, 1, 0), '-y': (0, -1, 0), '+z': (0, 0, 1), '-z': (0, 0, -1)}
RAIL_RHO = 34.0
COLLAR_R = 61.06


def qangle(f, u):
    """Source QAngle (pitch, yaw, roll) of a camera with forward f and up u"""
    f = np.asarray(f, dtype=float); u = np.asarray(u, dtype=float)
    r = np.cross(f, u)
    pitch = -math.degrees(math.asin(max(-1.0, min(1.0, f[2]))))
    if abs(f[2]) > 0.99999:
        roll = 0.0
        yaw = math.degrees(math.atan2(-u[1], -u[0])) if f[2] > 0 else math.degrees(math.atan2(u[1], u[0]))
    else:
        yaw = math.degrees(math.atan2(f[1], f[0])); roll = math.degrees(math.atan2(-r[2], u[2]))
    return pitch, yaw, roll


class Ride:
    def __init__(self, name, origin=(0, 0, 0), unit=1.0, axes=('+x', '+y', '+z')):
        self.name = name
        self.raw = json.load(open(os.path.join(HERE, 'data', name + '_ride.json')))
        self.M = np.array([AX[a] for a in axes], dtype=float).T          # columns: where the room axes go
        assert abs(np.linalg.det(self.M) - 1) < 1e-9, 'axes must be right-handed'
        self.origin = np.asarray(origin, dtype=float); self.unit = float(unit)
        self.moments = [(m[0], m[1], m[2], self.to_map(m[3:6]), self.M @ np.array(m[6:9]), self.M @ np.array(m[9:12])) for m in self.raw['moments']]
        self.frames = {int(k): self.to_map(v) for k, v in self.raw['frames'].items()}
        cv = np.array(self.raw['curve'], dtype=float)
        self.t = cv[:, 0]; self.curve = np.array([self.to_map(p) for p in cv[:, 1:4]])
        self.S = np.r_[0.0, np.cumsum(np.linalg.norm(np.diff(self.curve, axis=0), axis=1))]; self.length = float(self.S[-1])
        T = np.gradient(self.curve, axis=0); self.T = T / (np.linalg.norm(T, axis=1, keepdims=True) + 1e-12)
        self.sections = []
        for s in self.raw['sections']:
            d = dict(s); d['s0'] = self.s_at(s['first']); d['s1'] = self.s_at(s['last'])
            if s['forward']: d['forward_vec'] = self.M @ np.array(AX[s['forward']], dtype=float); d['up_vec'] = self.M @ np.array(AX[s['up']], dtype=float)
            self.sections.append(d)
        self.rings = [dict(r, s=self.s_at(r['frame']), pos=self.pos(r['frame']), axis=self.direction(r['frame'])) for r in self.raw['rings']]
        self.planes = []
        for p in self.raw['planes']:
            n = self.M @ np.array(AX['+' + p['axis']], dtype=float); i = int(np.argmax(np.abs(n)))
            lo = self.to_map(p['lo']); hi = self.to_map(p['hi'])
            c = p['coord'] * self.unit * n[i] + self.origin[i]
            self.planes.append(dict(axis='xyz'[i], coord=float(c), n=p['n'], lo=np.minimum(lo, hi), hi=np.maximum(lo, hi)))

    def to_map(self, p):
        return self.M @ (np.asarray(p, dtype=float) * self.unit) + self.origin

    # ------------------------------------------------------------------ along the path
    def at(self, s):
        """(position, unit tangent) at arclength s; beyond the ends the path continues straight"""
        if s <= 0: return self.curve[0] + self.T[0] * s, self.T[0].copy()
        if s >= self.length: return self.curve[-1] + self.T[-1] * (s - self.length), self.T[-1].copy()
        i = int(np.clip(np.searchsorted(self.S, s) - 1, 0, len(self.S) - 2)); u = (s - self.S[i]) / max(self.S[i + 1] - self.S[i], 1e-12)
        t = self.T[i] * (1 - u) + self.T[i + 1] * u
        return self.curve[i] + (self.curve[i + 1] - self.curve[i]) * u, t / np.linalg.norm(t)

    def s_at(self, frame):
        """arclength of the camera at a (fractional) film frame"""
        return float(np.interp(frame, self.t, self.S))

    def pos(self, frame): return self.at(self.s_at(frame))[0]

    def direction(self, frame): return self.at(self.s_at(frame))[1]

    def straights(self, extend=0.0):
        """[(start, end, axis)] of the straight pieces of the path (the lead-in before the first straight and the
        run-out after the last are included in them)"""
        out = []; st = [d for d in self.sections if d['kind'] == 'straight']
        for k, d in enumerate(st):
            s0 = 0.0 if k == 0 else d['s0']; s1 = self.length if (k == len(st) - 1 and self.sections[-1] is d) else d['s1']
            a = self.at(s0)[0]; b = self.at(s1)[0]; ax = d['forward_vec']
            out.append((a - ax * extend, b + ax * extend, ax))
        return out

    def transport(self, u0):
        """unit vector u0 (perpendicular to the first tangent) carried along the path without twisting: [k,3]"""
        U = np.zeros_like(self.curve); u = np.asarray(u0, dtype=float); u = u - self.T[0] * (u @ self.T[0]); U[0] = u / np.linalg.norm(u)
        for i in range(1, len(self.curve)):
            u = U[i - 1] - self.T[i] * (U[i - 1] @ self.T[i]); U[i] = u / np.linalg.norm(u)
        return U

    def rails(self, rho=RAIL_RHO, s0=None, s1=None):
        """the four rails (on the diagonals of the tube cross-section) as polylines [k,3] between arclengths s0 and s1"""
        st = [d for d in self.sections if d['kind'] == 'straight']
        U = self.transport(st[0]['up_vec'] if st else np.array([0, 0, 1.0])); W = np.cross(self.T, U)
        m = np.ones(len(self.S), bool)
        if s0 is not None: m &= self.S >= s0
        if s1 is not None: m &= self.S <= s1
        return [(self.curve + (a * U + b * W) * rho / math.sqrt(2.0))[m] for a in (1, -1) for b in (1, -1)]

    def frame_at(self, s):
        """(tangent, u, w): the tube's cross-section axes at arclength s (u, w point at the rail diagonals' sides)"""
        st = [d for d in self.sections if d['kind'] == 'straight']
        U = self.transport(st[0]['up_vec'] if st else np.array([0, 0, 1.0]))
        i = int(np.clip(np.searchsorted(self.S, s), 0, len(self.S) - 1)); T = self.T[i]; u = U[i] - T * (U[i] @ T); u /= np.linalg.norm(u)
        return T, u, np.cross(T, u)

    # ------------------------------------------------------------------ camera
    def camera(self):
        """[(t, (x, y, z), (pitch, yaw, roll)), ...] for Director.override_camera"""
        return [(t, tuple(float(x) for x in p), qangle(f, u)) for t, n, mo, p, f, u in self.moments]

    def bounds(self, margin=0.0):
        P = np.array([p for _, _, _, p, _, _ in self.moments]); return P.min(axis=0) - margin, P.max(axis=0) + margin
