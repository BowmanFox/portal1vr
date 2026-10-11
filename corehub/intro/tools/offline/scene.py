"""Offline scene model for the Corehub intro map: VMF brushes + prop models (from SMD/QC sources) + materials.

Used to preview frames from the director's camera without the game, and to recover material colours
from published review sheets. Geometry conventions follow the Source engine (units, QAngle order).
"""
import math, os, re, json
import numpy as np
from srctools import VMF, Vec

DEG = math.pi / 180.0


# ----------------------------------------------------------------------------- math
def angle_matrix(pitch, yaw, roll):
    """Source AngleMatrix: columns are forward, left, up for a QAngle (degrees)."""
    sp, cp = math.sin(pitch * DEG), math.cos(pitch * DEG)
    sy, cy = math.sin(yaw * DEG), math.cos(yaw * DEG)
    sr, cr = math.sin(roll * DEG), math.cos(roll * DEG)
    return np.array([
        [cp * cy, sr * sp * cy - cr * sy, cr * sp * cy + sr * sy],
        [cp * sy, sr * sp * sy + cr * cy, cr * sp * sy - sr * cy],
        [-sp, sr * cp, cr * cp]], dtype=np.float64)


def view_basis(pitch, yaw, roll):
    """forward, right, up vectors for a view QAngle (Source AngleVectors)."""
    m = angle_matrix(pitch, yaw, roll)
    return m[:, 0], -m[:, 1], m[:, 2]


def parse_vec(s, n=3, default=0.0):
    try:
        v = [float(x) for x in str(s).split()]
    except ValueError:
        v = []
    return np.array((v + [default] * n)[:n], dtype=np.float64)


# ----------------------------------------------------------------------------- brushes
def solid_polygons(solid):
    """-> list of (side, verts[k,3]) with verts counter-clockwise seen from outside."""
    planes = []
    for side in solid.sides:
        p = [np.array([q.x, q.y, q.z], dtype=np.float64) for q in side.planes]
        # VMF convention: the three plane points run clockwise seen from outside, so (p2-p0)x(p1-p0) points outward.
        # (The points need not lie inside the face, so the solid's inside cannot be guessed from them.)
        n = np.cross(p[2] - p[0], p[1] - p[0])
        ln = np.linalg.norm(n)
        if ln < 1e-9:
            planes.append(None); continue
        n /= ln
        planes.append([n, float(n @ p[0])])
    if not any(pl is not None for pl in planes):
        return []
    out = []
    for i, side in enumerate(solid.sides):
        pl = planes[i]
        if pl is None: continue
        n, d = pl
        # big quad on plane i
        a = np.array([1.0, 0, 0]) if abs(n[0]) < 0.9 else np.array([0, 1.0, 0])
        u = np.cross(n, a); u /= np.linalg.norm(u); v = np.cross(n, u)
        o = n * d; S = 2.0e5
        poly = [o - u * S - v * S, o + u * S - v * S, o + u * S + v * S, o - u * S + v * S]
        for j, pj in enumerate(planes):
            if j == i or pj is None: continue
            nj, dj = pj
            dist = [float(nj @ q - dj) for q in poly]
            if all(x <= 1e-4 for x in dist): continue
            new = []
            for k in range(len(poly)):
                q0, q1 = poly[k], poly[(k + 1) % len(poly)]; d0, d1 = dist[k], dist[(k + 1) % len(poly)]
                if d0 <= 1e-4: new.append(q0)
                if (d0 > 1e-4) != (d1 > 1e-4) and abs(d0 - d1) > 1e-12:
                    t = d0 / (d0 - d1); new.append(q0 + (q1 - q0) * t)
            poly = new
            if len(poly) < 3: break
        if len(poly) < 3: continue
        # drop near-duplicate points
        cl = []
        for q in poly:
            if not cl or np.linalg.norm(q - cl[-1]) > 1e-3: cl.append(q)
        if len(cl) > 1 and np.linalg.norm(cl[0] - cl[-1]) <= 1e-3: cl.pop()
        if len(cl) < 3: continue
        V = np.array(cl)
        # make winding counter-clockwise seen from outside (normal n)
        nn = np.zeros(3)
        for k in range(1, len(V) - 1): nn += np.cross(V[k] - V[0], V[k + 1] - V[0])
        if nn @ n < 0: V = V[::-1]
        out.append((side, V, n))
    return out


class TriSet:
    """A bag of triangles with per-triangle material ids and uvs."""
    def __init__(self):
        self.v = []; self.uv = []; self.mat = []; self.n = []; self.texel = []; self.tint = []

    def add(self, verts, uvs, mat, normal, texel, tint=(1.0, 1.0, 1.0)):
        for k in range(1, len(verts) - 1):
            self.v.append((verts[0], verts[k], verts[k + 1]))
            self.uv.append((uvs[0], uvs[k], uvs[k + 1]))
            self.mat.append(mat); self.n.append(normal); self.texel.append(texel); self.tint.append(tint)

    def arrays(self):
        if not self.v:
            return (np.zeros((0, 3, 3), np.float32), np.zeros((0, 3, 2), np.float32), np.zeros(0, np.int32),
                    np.zeros((0, 3), np.float32), np.zeros(0, bool), np.zeros((0, 3), np.float32))
        return (np.asarray(self.v, np.float32), np.asarray(self.uv, np.float32), np.asarray(self.mat, np.int32),
                np.asarray(self.n, np.float32), np.asarray(self.texel, bool), np.asarray(self.tint, np.float32))


# ----------------------------------------------------------------------------- models
def parse_smd(path):
    """-> list of (material, [(pos, normal, uv) x3])"""
    tris = []
    with open(path, errors='replace') as f:
        lines = f.read().split('\n')
    try:
        i = lines.index('triangles') + 1
    except ValueError:
        return tris
    while i + 3 < len(lines):
        mat = lines[i].strip()
        if mat == 'end' or not mat: break
        vs = []
        for k in range(1, 4):
            p = lines[i + k].split()
            vs.append((np.array([float(p[1]), float(p[2]), float(p[3])]), np.array([float(p[4]), float(p[5]), float(p[6])]),
                       np.array([float(p[7]), float(p[8])])))
        tris.append((mat.lower(), vs)); i += 4
    return tris


def parse_qc(path):
    txt = open(path, errors='replace').read()
    q = {'path': path, 'renames': {}, 'skins': [], 'scale': 1.0, 'origin': (0.0, 0.0, 0.0, 0.0), 'bodies': []}
    m = re.search(r'\$modelname\s+"?([^"\s]+)"?', txt)
    q['modelname'] = ('models/' + m.group(1)).lower().replace('\\', '/') if m else ''
    for a, b in re.findall(r'\$renamematerial\s+"?([^"\s]+)"?\s+"?([^"\s]+)"?', txt): q['renames'][a.lower()] = b.lower()
    m = re.search(r'\$scale\s+([-\d.]+)', txt)
    if m: q['scale'] = float(m.group(1))
    m = re.search(r'\$origin\s+([-\d.]+)\s+([-\d.]+)\s+([-\d.]+)(?:\s+([-\d.]+))?', txt)
    if m: q['origin'] = tuple(float(x) if x else 0.0 for x in m.groups())
    for b in re.findall(r'\$(?:body|model)\s+"?\w+"?\s+"?([^"\s]+)"?', txt): q['bodies'].append(b)
    m = re.search(r'\$texturegroup\s+"?\w+"?\s*\{(.*?)\n\}', txt, re.S)
    if m:
        for grp in re.findall(r'\{([^{}]*)\}', m.group(1)):
            q['skins'].append([s.lower() for s in re.findall(r'"([^"]+)"', grp)])
    m = re.search(r'\$cdmaterials\s+"?([^"\n]+)"?', txt)
    q['cdmaterials'] = (m.group(1).strip().strip('"').lower().replace('\\', '/').strip('/') if m else 'models')
    q['staticprop'] = '$staticprop' in txt
    return q


class ModelLib:
    def __init__(self, dirs):
        self.models = {}
        for d in dirs:
            for root, _, files in os.walk(d):
                for f in files:
                    if f.lower().endswith('.qc'):
                        q = parse_qc(os.path.join(root, f))
                        if q['modelname']: self.models[q['modelname']] = q
        self._cache = {}

    def tris(self, modelname, skin=0):
        """-> list of (material path, verts[3,3], uvs[3,2], normal[3]) in model space, or None when unknown"""
        key = (modelname, skin)
        if key in self._cache: return self._cache[key]
        q = self.models.get(modelname)
        if q is None:
            self._cache[key] = None; return None
        out = []
        # studiomdl rotates SMD data +90 degrees about Z by default; "$origin x y z r" adds r degrees and an offset.
        rot = 90.0 + q['origin'][3]
        R = angle_matrix(0, rot, 0)
        off = np.array(q['origin'][:3])
        sub = {}
        if q['skins'] and 0 < skin < len(q['skins']):
            for a, b in zip(q['skins'][0], q['skins'][skin]): sub[a] = b
        for body in q['bodies']:
            p = os.path.join(os.path.dirname(q['path']), body)
            if not p.lower().endswith('.smd'): p += '.smd'
            if not os.path.exists(p): continue
            for mat, vs in parse_smd(p):
                mat = q['renames'].get(mat, mat)
                mat = sub.get(mat, mat)
                P = np.array([(R @ (v[0] - off)) * q['scale'] for v in vs])
                nrm = np.cross(P[1] - P[0], P[2] - P[0]); ln = np.linalg.norm(nrm)
                nrm = nrm / ln if ln > 1e-12 else np.array([0, 0, 1.0])
                UV = np.array([[v[2][0], 1.0 - v[2][1]] for v in vs])
                out.append((q['cdmaterials'] + '/' + mat, P, UV, nrm))
        self._cache[key] = out
        return out


# ----------------------------------------------------------------------------- scene
SKIP_MATERIALS = ('tools/toolsnodraw', 'tools/toolsskip', 'tools/toolshint', 'tools/toolsclip', 'tools/toolsplayerclip',
                  'tools/toolstrigger', 'tools/toolsinvisible', 'tools/toolsareaportal', 'tools/toolsorigin',
                  'tools/toolsblocklight', 'tools/toolsoccluder', 'tools/toolsnpcclip', 'tools/toolsblockbullets')
BRUSH_CLASSES = ('func_detail', 'func_brush', 'func_illusionary', 'func_wall', 'func_door', 'func_movelinear',
                 'func_tracktrain', 'func_physbox', 'func_rotating', 'func_door_rotating', 'func_lod')


class Scene:
    """VMF brushes are converted once (slow, cacheable with pickle after prepare()); props are instanced from the
    model sources in finalize(), so models can be changed and reloaded quickly."""
    def __init__(self, vmf_path, model_dirs=None):
        self.vmf_path = vmf_path
        self.mat_names = []          # index -> material path (lower case, forward slashes)
        self.mat_index = {}
        self.brush_static = TriSet()
        self.brush_dynamic = {}      # targetname -> list of dict(kind='brush', ...)
        self.props = []              # every prop_* placement
        self.lights = []
        self.beams = []
        self.static = None
        self.dynamic = {}
        self.missing_models = {}
        self.models = None
        self._prepare(VMF.parse(vmf_path))
        if model_dirs is not None: self.finalize(model_dirs)

    def mat(self, name):
        name = name.lower().replace('\\', '/')
        if name not in self.mat_index:
            self.mat_index[name] = len(self.mat_names); self.mat_names.append(name)
        return self.mat_index[name]

    def _add_solid(self, ts, solid, offset=None, tint=(1.0, 1.0, 1.0)):
        for side, V, n in solid_polygons(solid):
            m = side.mat.lower().replace('\\', '/')
            if m in SKIP_MATERIALS or m.startswith('tools/'): continue
            ua, va = side.uaxis, side.vaxis
            U = (V @ np.array([ua.x, ua.y, ua.z])) / (ua.scale or 0.25) + ua.offset
            W = (V @ np.array([va.x, va.y, va.z])) / (va.scale or 0.25) + va.offset
            P = V if offset is None else V - offset
            ts.add(P, np.stack([U, W], axis=1), self.mat(m), n, True, tint)

    def _prepare(self, v):
        for solid in v.brushes:
            self._add_solid(self.brush_static, solid)
        for e in v.entities:
            cls = e['classname']; name = e['targetname']
            if cls in ('light', 'light_spot', 'light_dynamic'):
                L = parse_vec(e['_light', '255 255 255 200'], 4, 200.0)
                self.lights.append(dict(cls=cls, origin=parse_vec(e['origin']), color=L[:3] / 255.0, brightness=L[3], name=name,
                                        kv={k: e[k] for k in e.keys()}))
                continue
            if cls == 'env_beam':
                self.beams.append({k: e[k] for k in e.keys()}); continue
            tint = (1.0, 1.0, 1.0)
            rc = e['rendercolor', '']
            if rc:
                c = parse_vec(rc, 3, 255.0) / 255.0; tint = (float(c[0]), float(c[1]), float(c[2]))
            if e.solids and (cls in BRUSH_CLASSES or cls.startswith('func_')):
                if cls == 'func_detail' or not name:
                    for s in e.solids: self._add_solid(self.brush_static, s, tint=tint if cls != 'func_detail' else (1.0, 1.0, 1.0))
                else:
                    org = parse_vec(e['origin', '0 0 0'])
                    ts = TriSet()
                    for s in e.solids: self._add_solid(ts, s, offset=org, tint=tint)
                    self.brush_dynamic.setdefault(name, []).append(dict(kind='brush', tris=ts, origin=org, angles=np.zeros(3), cls=cls,
                                                                        renderamt=float(e['renderamt', '255'] or 255), rendermode=e['rendermode', '0']))
                continue
            if cls.startswith('prop_') and e['model']:
                self.props.append(dict(cls=cls, name=name, model=e['model'].lower().replace('\\', '/'), skin=int(float(e['skin', '0'] or 0)),
                                       origin=parse_vec(e['origin', '0 0 0']), angles=parse_vec(e['angles', '0 0 0']),
                                       scale=float(e['modelscale', '1'] or 1), tint=tint, parent=e['parentname', '']))

    def finalize(self, model_dirs):
        """(re)instance every prop from the model sources found under model_dirs"""
        self.models = ModelLib(model_dirs)
        self.static = TriSet()
        st = self.brush_static
        self.static.v = list(st.v); self.static.uv = list(st.uv); self.static.mat = list(st.mat); self.static.n = list(st.n)
        self.static.texel = list(st.texel); self.static.tint = list(st.tint)
        self.dynamic = {k: list(v) for k, v in self.brush_dynamic.items()}
        self.missing_models = {}
        for pr in self.props:
            cls = pr['cls']; name = pr['name']; mdl = pr['model']
            tris = self.models.tris(mdl, pr['skin'])
            scale_used = 1.0 if cls == 'prop_static' else pr['scale']     # the 2009 engine has no static-prop scale
            if tris is None:
                self.missing_models.setdefault(mdl, []).append(pr)
                continue
            ts = TriSet()
            for mat, P, UV, nrm in tris:
                ts.add(P * scale_used, UV, self.mat(mat), nrm, False, pr['tint'])
            if name and cls != 'prop_static':
                self.dynamic.setdefault(name, []).append(dict(kind='prop', tris=ts, origin=pr['origin'], angles=pr['angles'], cls=cls, model=mdl,
                                                              scale=scale_used, tint=pr['tint']))
            else:
                R = angle_matrix(*pr['angles'])
                V, UVa, M, N, T, C = ts.arrays()
                Vw = (V.reshape(-1, 3).astype(np.float64) @ R.T + pr['origin']).reshape(-1, 3, 3)
                Nw = N.astype(np.float64) @ R.T
                self.static.v.extend(Vw); self.static.uv.extend(UVa); self.static.mat.extend(int(x) for x in M)
                self.static.n.extend(Nw); self.static.texel.extend([False] * len(Vw)); self.static.tint.extend(C)
        return self

    def static_arrays(self):
        return self.static.arrays()

    def dynamic_arrays(self, state):
        """state: dict name -> {'o':[x,y,z], 'angles': 'p y r', 'rendercolor': 'r g b', ...} from the director simulation."""
        Vs, UVs, Ms, Ns, Ts, Cs = [], [], [], [], [], []
        for name, parts in self.dynamic.items():
            st = state.get(name, {})
            for part in parts:
                V, UVa, M, N, T, C = part['tris'].arrays()
                if len(V) == 0: continue
                org = np.array(st['o'], dtype=np.float64) if 'o' in st else part['origin']
                if org[2] < -2500: continue                       # parked out of sight by the director
                ang = parse_vec(st['angles']) if 'angles' in st else part['angles']
                if part['kind'] == 'brush':
                    Vw = V.astype(np.float64) + org; Nw = N
                else:
                    R = angle_matrix(*ang)
                    Vw = (V.reshape(-1, 3).astype(np.float64) @ R.T + org).reshape(-1, 3, 3); Nw = N.astype(np.float64) @ R.T
                tint = C
                if 'rendercolor' in st:
                    c = parse_vec(st['rendercolor'], 3, 255.0) / 255.0; tint = np.tile(c.astype(np.float32), (len(V), 1))
                Vs.append(Vw.astype(np.float32)); UVs.append(UVa); Ms.append(M); Ns.append(np.asarray(Nw, np.float32)); Ts.append(T); Cs.append(tint)
        if not Vs:
            return (np.zeros((0, 3, 3), np.float32), np.zeros((0, 3, 2), np.float32), np.zeros(0, np.int32),
                    np.zeros((0, 3), np.float32), np.zeros(0, bool), np.zeros((0, 3), np.float32))
        return (np.concatenate(Vs), np.concatenate(UVs), np.concatenate(Ms), np.concatenate(Ns), np.concatenate(Ts), np.concatenate(Cs))
