"""Preview: the r10 scene (VMF + director state + models + materials) rendered offline at any time, next to the 2009 video.
    from preview import Preview, ref_frame, run_frame
    P = Preview('dm')                       # run_<tag>/ holds director.nut, state.jsonl (see make_sim_inputs.py) and map.vmf
    im = P.render(52.5)                      # PIL image 640x400
Scene preparation (VMF brushes) is cached in run_<tag>/scene.pkl; models and materials are re-read on every start."""
import json, os, pickle, sys, bisect
import numpy as np
from PIL import Image
from scene import Scene, SCENE_VERSION
from render import Renderer, MaterialLib, apply_fades, to_image, srgb_decode, srgb_encode, gamma_to_linear

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = '/home/claude/bowmanfox/portal1vr/corehub/intro'
WORK = '/home/claude/work'
MODEL_DIRS = [REPO + '/models', WORK + '/gen/out', WORK + '/mod-src/models-src']
MAT_ROOTS = [WORK + '/gen/out/materials', WORK + '/mod-src/materials', REPO + '/materials', '/home/claude/data/texpack/portal2',
             '/home/claude/data/texpack/portal2_tempcontent', '/home/claude/data/texpack/portal']
STOCK_ROOTS = ['/home/claude/data/stock/portal2', '/home/claude/data/stock/portal2_tempcontent', '/home/claude/data/stock/portal']
FRAMES = '/home/claude/data/frames'
RUNS = '/home/claude/data/runs'


def ref_frame(t, size=None):
    """2009 video frame nearest to time t (640x400)"""
    n = max(0, min(4015, round(t * 30000 / 1001)))
    im = Image.open('%s/f%04d.jpg' % (FRAMES, n)).convert('RGB')
    return im.resize(size, Image.BILINEAR) if size else im


def run_frame(run, t, size=None):
    """frame of a game run fetched with fetch_frames.py (None when that time was not fetched)"""
    p = '%s/%s/m%06d.jpg' % (RUNS, run, round(t * 1000))
    if not os.path.exists(p): return None
    im = Image.open(p).convert('RGB')
    return im.resize(size, Image.BILINEAR) if size else im


class Preview:
    def __init__(self, tag, overrides=None, model_dirs=None, mat_roots=None, extra_model_dirs=(), extra_mat_roots=(), quiet=False):
        self.dir = os.path.join(HERE, 'run_' + tag)
        vmf = os.path.join(self.dir, 'map.vmf')
        pk = os.path.join(self.dir, 'scene.pkl')
        self.scene = None
        if os.path.exists(pk) and os.path.getmtime(pk) >= os.path.getmtime(vmf):
            self.scene = pickle.load(open(pk, 'rb'))
            if getattr(self.scene, 'version', 0) != SCENE_VERSION: self.scene = None
        if self.scene is None:
            self.scene = Scene(vmf)
            pickle.dump(self.scene, open(pk, 'wb'))
        self.ml = MaterialLib(list(extra_mat_roots) + (mat_roots or MAT_ROOTS), overrides=overrides or {})
        self.scene.finalize(list(extra_model_dirs) + (model_dirs or MODEL_DIRS), stock_roots=STOCK_ROOTS,
                            mat_exists=lambda n: self.ml.idx.find(n + '.vmt') is not None)
        self.R = Renderer(self.scene, self.ml)
        self.rows = [json.loads(l) for l in open(os.path.join(self.dir, 'state.jsonl'))]
        if self.rows and self.rows[0].get('delta'):      # rows hold only the entities that changed: rebuild the full state per row
            cur = {}
            for r in self.rows:
                if r['ents']:
                    cur = dict(cur); cur.update(r['ents'])
                r['ents'] = cur
        self.times = [r['t'] for r in self.rows]
        # material_modify_control: timeline of SetMaterialVar inputs per controlled material
        self.matvar = {}
        for r in self.rows:
            for ft, target, action, value in r.get('fires', []):
                if action.lower() == 'setmaterialvar' and target in self.scene.mat_controls:
                    m, var = self.scene.mat_controls[target]
                    if var == '$color' and m in self.scene.mat_index:
                        try: c = [float(x) for x in value.strip('[]').split()]
                        except ValueError: continue
                        self.matvar.setdefault(m, []).append((ft, c))
        self._base_color = self.R.m_color.copy()
        if not quiet:
            miss = sorted(n for i, n in enumerate(self.scene.mat_names) if not self.R.m_found[i])
            if miss: print('materials not found:', miss)
            if self.scene.missing_models:
                print('models without sources:', {k: len(v) for k, v in sorted(self.scene.missing_models.items())})

    def row(self, t):
        i = bisect.bisect_left(self.times, t - 1e-6)
        if i >= len(self.times): i = len(self.times) - 1
        if i > 0 and abs(self.times[i - 1] - t) < abs(self.times[i] - t): i -= 1
        return self.rows[i]

    def render_lin(self, t, w=640, h=400, fades=True, cam=None, **kw):
        """cam: optional (eye, ang, fov) override; the entity state still comes from time t"""
        row = self.row(t)
        eye, ang, fov = cam if cam else (row['eye'], row['ang'], row['fov'])
        for m, tl in self.matvar.items():
            i = self.scene.mat_index[m]; c = None
            for ft, v in tl:
                if ft <= t + 1e-6: c = v
                else: break
            self.R.m_color[i] = gamma_to_linear(np.array((c + c[-1:] * 3)[:3])) if c else self._base_color[i]
        out = self.R.render(eye, ang, fov, row['ents'], w=w, h=h, **kw)
        if isinstance(out, tuple):
            return (apply_fades(out[0], row) if fades else out[0]), out[1]
        return apply_fades(out, row) if fades else out

    def render(self, t, w=640, h=400, fades=True, cam=None, blend=False):
        """blend=True: like the film, the average of the two moments t and t + 1/60 (each film frame is a blend of
        its two 60 Hz moments; in fast motion they differ)"""
        if blend and cam is None:
            a = self.render_lin(t, w, h, fades); b = self.render_lin(t + 1.0 / 60.0, w, h, fades)
            return to_image((a + b) * 0.5)
        return to_image(self.render_lin(t, w, h, fades, cam))


    def pick(self, t, px, py, w=640, h=400, cam=None):
        """what the preview shows at pixel (px, py) of the 640x400 frame: dict(material, depth, point) of the first
        visible surface (None when the ray leaves the map)"""
        row = self.row(t)
        eye, ang, fov = cam if cam else (row['eye'], row['ang'], row['fov'])
        img, aux = self.R.render(eye, ang, fov, row['ents'], w=w, h=h, return_aux=True)
        x = min(w - 1, max(0, int(px))); y = min(h - 1, max(0, int(py)))
        m = int(aux['mat'][y, x])
        if m < 0: return None
        o, d = self.ray(t, x + 0.5, y + 0.5, w, h, cam)
        dist = float(aux['depth'][y, x])
        return dict(material=self.scene.mat_names[m], depth=dist, point=(o + d * dist).tolist())

    def materials_in_view(self, t, w=320, h=200, cam=None):
        """{material: share of the frame} for the first visible surfaces at time t, largest first"""
        row = self.row(t)
        eye, ang, fov = cam if cam else (row['eye'], row['ang'], row['fov'])
        img, aux = self.R.render(eye, ang, fov, row['ents'], w=w, h=h, return_aux=True)
        ids, cnt = np.unique(aux['mat'], return_counts=True)
        out = {(self.scene.mat_names[i] if i >= 0 else '(nothing)'): c / float(w * h) for i, c in zip(ids, cnt)}
        return dict(sorted(out.items(), key=lambda kv: -kv[1]))

    # ------------------------------------------------------------------ camera geometry helpers (640x400 pixel grid by default)
    def cam(self, t):
        row = self.row(t); return row['eye'], row['ang'], row['fov']

    def project(self, t, P, w=640, h=400, cam=None):
        """world point(s) -> pixel (x, y) and depth along the view axis (depth <= 0: behind the camera)"""
        import math
        from scene import view_basis, DEG
        eye, ang, fov = cam if cam else self.cam(t)
        f, r, u = view_basis(*ang)
        th = math.tan(fov * DEG / 2.0) * (1.6 / (4.0 / 3.0)); tv = math.tan(fov * DEG / 2.0) * 0.75
        P = np.atleast_2d(np.asarray(P, dtype=np.float64)) - np.asarray(eye, dtype=np.float64)
        d = P @ f; x = (P @ r) / np.where(np.abs(d) < 1e-9, 1e-9, d) / th; y = (P @ u) / np.where(np.abs(d) < 1e-9, 1e-9, d) / tv
        return np.stack([(x + 1) * 0.5 * w, (1 - y) * 0.5 * h, d], axis=1)

    def ray(self, t, px, py, w=640, h=400, cam=None):
        """pixel -> (eye, unit direction)"""
        import math
        from scene import view_basis, DEG
        eye, ang, fov = cam if cam else self.cam(t)
        f, r, u = view_basis(*ang)
        th = math.tan(fov * DEG / 2.0) * (1.6 / (4.0 / 3.0)); tv = math.tan(fov * DEG / 2.0) * 0.75
        d = f + r * ((px / w) * 2 - 1) * th + u * (1 - (py / h) * 2) * tv
        return np.asarray(eye, dtype=np.float64), d / np.linalg.norm(d)

    def unproject(self, t, px, py, axis='z', value=0.0, w=640, h=400, cam=None):
        """pixel -> world point on the plane <axis> = value (None when the ray is parallel or the plane is behind)"""
        o, d = self.ray(t, px, py, w, h, cam); i = 'xyz'.index(axis)
        if abs(d[i]) < 1e-9: return None
        k = (value - o[i]) / d[i]
        return o + d * k if k > 0 else None
