"""Offline preview renderer for the Corehub intro map (ray casting with Embree).

Shading follows what the game does for the map's unlit materials: the texture is read as sRGB, "$color" (and the
entity tint) is converted with gamma 2.2, everything is multiplied and alpha-blended in linear light, and the result
is written as sRGB. Lit stock textures are only approximated. See scene.py for the geometry side."""
import math, os, re, json
import numpy as np
from PIL import Image
from embreex import rtcore_scene as rtcs
from embreex.mesh_construction import TriangleMesh
from scene import Scene, view_basis, parse_vec, DEG

try:
    from srctools.vtf import VTF
except Exception:      # pragma: no cover
    VTF = None


def srgb_decode(c):
    c = np.asarray(c, dtype=np.float64)
    return np.where(c <= 0.04045, c / 12.92, np.power((np.maximum(c, 0) + 0.055) / 1.055, 2.4))


def srgb_encode(l):
    l = np.clip(np.asarray(l, dtype=np.float64), 0, 1)
    return np.where(l <= 0.0031308, l * 12.92, 1.055 * np.power(np.maximum(l, 1e-12), 1 / 2.4) - 0.055)


def gamma_to_linear(c):
    return np.power(np.maximum(np.asarray(c, dtype=np.float64), 0), 2.2)


# ----------------------------------------------------------------------------- materials
class FileIndex:
    """case-insensitive lookup of files under several roots (first root wins)"""
    def __init__(self, roots):
        self.map = {}
        for r in roots:
            if not os.path.isdir(r): continue
            for d, _, fs in os.walk(r):
                rel = os.path.relpath(d, r).replace('\\', '/').lower()
                rel = '' if rel == '.' else rel + '/'
                for f in fs:
                    key = rel + f.lower()
                    self.map.setdefault(key, os.path.join(d, f))

    def find(self, rel):
        return self.map.get(rel.lower().replace('\\', '/'))


def parse_vmt(text):
    text = re.sub(r'//[^\n]*', '', text)
    m = re.match(r'\s*"?([\w]+)"?\s*\{', text)
    shader = m.group(1).lower() if m else 'unknown'
    kv = {}
    depth = 0
    for line in text.split('\n'):
        depth_before = depth
        depth += line.count('{') - line.count('}')
        if depth_before != 1: continue
        mm = re.match(r'\s*"?(\$?[%\w]+)"?\s+"?([^"]*?)"?\s*$', line.strip())
        if mm: kv[mm.group(1).lower()] = mm.group(2).strip()
    return shader, kv


def parse_color(s, default=(1.0, 1.0, 1.0)):
    if s is None: return np.array(default)
    s = s.strip()
    try:
        if s.startswith('['):
            v = [float(x) for x in s.strip('[]').split()]
        elif s.startswith('{'):
            v = [float(x) / 255.0 for x in s.strip('{}').split()]
        else:
            v = [float(x) for x in s.split()]
        if len(v) == 1: v = v * 3
        return np.array(v[:3])
    except ValueError:
        return np.array(default)


class Material:
    __slots__ = ('name', 'shader', 'kv', 'color', 'alpha', 'translucent', 'nocull', 'additive', 'unlit', 'tex', 'texsize',
                 'found', 'alphatest', 'selfillum', 'avg', 'basetexture')


class MaterialLib:
    def __init__(self, material_roots, overrides=None, mip_size=128):
        self.idx = FileIndex(material_roots)
        self.cache = {}
        self.tex_cache = {}
        self.overrides = overrides or {}       # name -> dict(color=(r,g,b), alpha=.., base=.., unlit=True, nocull=..)
        self.mip_size = mip_size
        self.missing = set()
        self.sizes = None
        for r in material_roots:
            sp = os.path.join(os.path.dirname(r.rstrip('/')), 'sizes.json')
            if os.path.exists(sp): self.sizes = json.load(open(sp)); break

    def texture(self, name):
        """-> (array[h,w,4] float32, rgb in LINEAR light, alpha as stored; (full_w, full_h)) or None.
        Reads real VTFs, or the reduced PNG pack (texpack/<game>/<path>.png, sizes.json holds the original dimensions)."""
        key = name.lower().replace('\\', '/')
        if key.endswith('.vtf'): key = key[:-4]
        if key in self.tex_cache: return self.tex_cache[key]
        res = None
        p = self.idx.find(key + '.vtf')
        if p and VTF is not None:
            try:
                with open(p, 'rb') as f:
                    vtf = VTF.read(f)
                    mip = 0
                    while max(vtf.width >> mip, vtf.height >> mip) > self.mip_size and mip < vtf.mipmap_count - 1: mip += 1
                    fr = vtf.get(mipmap=mip); fr.load()
                    img = fr.to_PIL().convert('RGBA')
                    res = (np.asarray(img, dtype=np.float32) / 255.0, (vtf.width, vtf.height))
            except Exception as ex:
                print('texture load failed', name, ex)
        if res is None:
            p = self.idx.find(key + '.png')
            if p:
                img = Image.open(p).convert('RGBA')
                full = img.size
                m = re.search(r'texpack/((?:portal2_tempcontent|portal2|portal)/.*)\.png$', p.replace('\\', '/'))
                if m and self.sizes is not None:
                    sz = self.sizes.get(m.group(1).lower() + '.vtf')
                    if sz: full = (sz[0], sz[1])
                res = (np.asarray(img, dtype=np.float32) / 255.0, full)
        if res is not None:
            arr = res[0].copy(); arr[..., :3] = srgb_decode(arr[..., :3]).astype(np.float32)
            res = (arr, res[1])
        self.tex_cache[key] = res
        return res

    def get(self, name):
        key = name.lower().replace('\\', '/')
        if key in self.cache: return self.cache[key]
        m = Material(); m.name = key; m.found = False
        m.shader = 'unknown'; m.kv = {}; m.color = np.ones(3); m.alpha = 1.0; m.translucent = False; m.nocull = False
        m.additive = False; m.unlit = True; m.tex = None; m.texsize = (64, 64); m.alphatest = False; m.selfillum = False
        m.basetexture = None
        p = self.idx.find(key + '.vmt')
        if p:
            m.found = True
            shader, kv = parse_vmt(open(p, errors='replace').read())
            m.shader = shader; m.kv = kv
            m.color = parse_color(kv.get('$color'))
            if '$color2' in kv: m.color = m.color * parse_color(kv.get('$color2'))
            try: m.alpha = float(kv.get('$alpha', '1'))
            except ValueError: m.alpha = 1.0
            m.translucent = kv.get('$translucent', '0') == '1' or m.alpha < 1.0
            m.alphatest = kv.get('$alphatest', '0') == '1'
            m.nocull = kv.get('$nocull', '0') == '1'
            m.additive = kv.get('$additive', '0') == '1'
            m.selfillum = kv.get('$selfillum', '0') == '1'
            m.unlit = shader in ('unlitgeneric', 'unlittwotexture', 'sprite', 'modulate', 'refract', 'water', 'cable', 'screenspace_general')
            bt = kv.get('$basetexture')
            if bt:
                m.basetexture = bt.lower().replace('\\', '/')
                t = self.texture(bt)
                if t is not None: m.tex, m.texsize = t
        else:
            self.missing.add(key)
        ov = self.overrides.get(key)
        if ov:
            if 'color' in ov: m.color = np.array(ov['color'], dtype=np.float64)
            if 'alpha' in ov: m.alpha = float(ov['alpha']); m.translucent = m.alpha < 1.0
            if 'unlit' in ov: m.unlit = bool(ov['unlit'])
            if 'nocull' in ov: m.nocull = bool(ov['nocull'])
            if 'additive' in ov: m.additive = bool(ov['additive'])
            if 'base' in ov:
                m.basetexture = ov['base']
                t = self.texture(ov['base'])
                if t is not None: m.tex, m.texsize = t
            m.found = True
        m.avg = m.tex[..., :3].reshape(-1, 3).mean(axis=0) if m.tex is not None else np.ones(3)
        self.cache[key] = m
        return m


# ----------------------------------------------------------------------------- renderer
MISSING_COLOR = np.array([1.0, 0.0, 1.0])


class Renderer:
    def __init__(self, scene, matlib, ambient=0.30, missing_color=MISSING_COLOR):
        self.scene = scene; self.ml = matlib; self.ambient = ambient; self.missing_color = np.asarray(missing_color)
        self.sV, self.sUV, self.sM, self.sN, self.sT, self.sC = scene.static_arrays()
        self.sC = gamma_to_linear(self.sC)
        self.sscene = rtcs.EmbreeScene()
        TriangleMesh(self.sscene, np.ascontiguousarray(self.sV))
        self._mat_tables()

    def _mat_tables(self):
        n = len(self.scene.mat_names)
        self.m_color = np.ones((n, 3)); self.m_alpha = np.ones(n); self.m_nocull = np.zeros(n, bool); self.m_add = np.zeros(n, bool)
        self.m_unlit = np.ones(n, bool); self.m_found = np.zeros(n, bool); self.m_hastex = np.zeros(n, bool)
        self.m_atest = np.zeros(n, bool); self.m_usetexalpha = np.zeros(n, bool)
        self.mats = []
        for i, name in enumerate(self.scene.mat_names):
            m = self.ml.get(name); self.mats.append(m)
            self.m_color[i] = gamma_to_linear(m.color if m.found else self.missing_color)     # LINEAR
            self.m_alpha[i] = m.alpha; self.m_nocull[i] = m.nocull; self.m_add[i] = m.additive; self.m_unlit[i] = m.unlit or not m.found
            self.m_found[i] = m.found; self.m_hastex[i] = m.tex is not None; self.m_atest[i] = m.alphatest
            self.m_usetexalpha[i] = (m.translucent and m.kv.get('$translucent', '0') == '1') or m.alphatest

    def refresh_materials(self, overrides=None):
        if overrides is not None: self.ml.overrides = overrides
        self.ml.cache.clear(); self._mat_tables()

    def _cast(self, scene, o, d):
        if scene is None:
            return np.full(len(o), np.inf, np.float32), np.full(len(o), -1, np.int64), None, None
        r = scene.run(np.ascontiguousarray(o, np.float32), np.ascontiguousarray(d, np.float32), output=1)
        prim = r['primID'].astype(np.int64); t = r['tfar'].astype(np.float32)
        miss = prim < 0
        t = np.where(miss, np.inf, t); prim = np.where(miss, -1, prim)
        return t, prim, r['u'], r['v']

    def render(self, eye, ang, fov, state=None, w=640, h=400, aspect=1.6, max_layers=16, return_aux=False, layers=0):
        """-> image in LINEAR light, float (h, w, 3). Use to_image() / srgb_encode for display."""
        state = state or {}
        dV, dUV, dM, dN, dT, dC = self.scene.dynamic_arrays(state)
        dC = gamma_to_linear(dC)
        dscene = None
        if len(dV):
            dscene = rtcs.EmbreeScene(); TriangleMesh(dscene, np.ascontiguousarray(dV))
        UV = [self.sUV, dUV]; M = [self.sM, dM]; N = [self.sN, dN]; TX = [self.sT, dT]; TC = [self.sC, dC]
        f, r, u = view_basis(*ang)
        th = math.tan(fov * DEG / 2.0) * (aspect / (4.0 / 3.0)); tv = math.tan(fov * DEG / 2.0) * 0.75
        xs = (np.arange(w) + 0.5) / w * 2 - 1; ys = 1 - (np.arange(h) + 0.5) / h * 2
        X, Y = np.meshgrid(xs, ys)
        D = f[None, None, :] + r[None, None, :] * (X[..., None] * th) + u[None, None, :] * (Y[..., None] * tv)
        D = D.reshape(-1, 3); D /= np.linalg.norm(D, axis=1, keepdims=True)
        O = np.tile(np.asarray(eye, np.float64), (w * h, 1))
        n = w * h
        C = np.zeros((n, 3)); T = np.ones(n)
        first_mat = np.full(n, -1, np.int64); first_depth = np.full(n, np.inf); first_set = np.zeros(n, bool)
        travelled = np.zeros(n)
        active = np.arange(n)
        if layers:
            L_mat = np.full((layers, n), -1, np.int32); L_alpha = np.zeros((layers, n), np.float32)
            L_fac = np.zeros((layers, n, 3), np.float32); L_cnt = np.zeros(n, np.int32)
            L_uv = np.zeros((layers, n, 2), np.float32)       # raw texture coordinates (texels for brush faces)
        for layer in range(max_layers):
            if len(active) == 0: break
            o = O[active]; d = D[active]
            t0, p0, u0, v0 = self._cast(self.sscene, o, d)
            t1, p1, u1, v1 = self._cast(dscene, o, d)
            use1 = t1 < t0
            t = np.where(use1, t1, t0)
            hit = np.isfinite(t)
            if not hit.any(): break
            ai = active[hit]; th_ = t[hit].astype(np.float64); u1h = use1[hit]
            col = np.zeros((len(ai), 3)); alpha = np.ones(len(ai)); back = np.zeros(len(ai), bool); mat = np.zeros(len(ai), np.int64)
            add = np.zeros(len(ai), bool); facs = np.ones((len(ai), 3)); uvs_all = np.zeros((len(ai), 2))
            dh = d[hit]
            for which, pr, uu, vv in ((0, p0, u0, v0), (1, p1, u1, v1)):
                sel = (u1h == bool(which))
                if not sel.any(): continue
                prim = pr[hit][sel]
                bu = uu[hit][sel].astype(np.float64); bv = vv[hit][sel].astype(np.float64)
                m = M[which][prim]; mat[sel] = m
                nrm = N[which][prim].astype(np.float64)
                dd = dh[sel]
                back[sel] = np.einsum('ij,ij->i', dd, nrm) > 0
                uvt = UV[which][prim].astype(np.float64)
                uv = uvt[:, 0] * (1 - bu - bv)[:, None] + uvt[:, 1] * bu[:, None] + uvt[:, 2] * bv[:, None]
                uvs_all[sel] = uv
                fac = np.array(TC[which][prim], dtype=np.float64)        # linear factor on the material colour
                a = self.m_alpha[m].copy()
                texel = TX[which][prim]
                for mi in np.unique(m):
                    mm = self.mats[mi]
                    if mm.tex is None: continue
                    s2 = (m == mi)
                    th2, tw2 = mm.tex.shape[:2]
                    uvs = uv[s2].copy(); tex_sel = texel[s2]
                    uvs[tex_sel, 0] /= mm.texsize[0]; uvs[tex_sel, 1] /= mm.texsize[1]
                    ix = np.floor((uvs[:, 0] % 1.0) * tw2).astype(int) % tw2; iy = np.floor((uvs[:, 1] % 1.0) * th2).astype(int) % th2
                    tx = mm.tex[iy, ix]
                    fac[s2] = fac[s2] * tx[:, :3]
                    if self.m_usetexalpha[mi]:
                        aa = a[s2] * tx[:, 3]
                        if mm.alphatest: aa = (aa > 0.5).astype(np.float64)
                        a[s2] = aa
                lit = ~self.m_unlit[m]
                if lit.any():      # lit stock materials: crude ambient + view-angle term (approximation only)
                    ndl = np.abs(np.einsum('ij,ij->i', dd[lit], nrm[lit]))
                    fac[lit] = fac[lit] * (self.ambient + (1 - self.ambient) * 0.5 * ndl)[:, None]
                facs[sel] = fac
                col[sel] = fac * self.m_color[m]; alpha[sel] = a; add[sel] = self.m_add[m]
            culled = back & ~self.m_nocull[mat]
            vis = ~culled
            idx = ai[vis]
            fs = ~first_set[idx]
            first_mat[idx[fs]] = mat[vis][fs]; first_depth[idx[fs]] = (travelled[idx] + th_[vis])[fs]; first_set[idx[fs]] = True
            a = np.clip(alpha[vis], 0, 1); c = np.maximum(col[vis], 0)
            if layers:
                k = L_cnt[idx]; ok = k < layers
                L_mat[k[ok], idx[ok]] = mat[vis][ok]; L_alpha[k[ok], idx[ok]] = a[ok]; L_fac[k[ok], idx[ok]] = facs[vis][ok]
                L_uv[k[ok], idx[ok]] = uvs_all[vis][ok]
                L_cnt[idx[ok]] += 1
            C[idx] += (T[idx] * a)[:, None] * c
            is_add = add[vis]
            T[idx] = np.where(is_add, T[idx], T[idx] * (1 - a))
            adv = th_ + 0.02
            O[ai] = O[ai] + D[ai] * adv[:, None]; travelled[ai] += adv
            keep = T[ai] > 0.004
            active = ai[keep]
        img = np.clip(C, 0, 1).reshape(h, w, 3)
        if return_aux:
            aux = dict(mat=first_mat.reshape(h, w), depth=first_depth.reshape(h, w), trans=T.reshape(h, w))
            if layers: aux.update(L_mat=L_mat, L_alpha=L_alpha, L_fac=L_fac, L_cnt=L_cnt, L_uv=L_uv)
            return img, aux
        return img


def apply_fades(img_lin, row):
    """screen fades recorded by the director simulation (blended in linear light like the rest):
    the scanner veil, the grey lens veil and black"""
    out = img_lin.copy()
    ents = row.get('ents', {})
    for name, default in (('r10_veil_fade', (95, 95, 95)), ('r10_red_fade', (137, 136, 136))):
        e = ents.get(name)
        if e and 'renderamt' in e:
            a = float(e['renderamt']) / 255.0
            if a > 0:
                c = gamma_to_linear(np.array(default) / 255.0)
                out = out * (1 - a) + c * a
    b = row.get('black', 0)
    if b and b > 0:
        out = out * (1 - b / 255.0)
    return out


def to_image(img_lin):
    return Image.fromarray((srgb_encode(img_lin) * 255 + 0.5).astype(np.uint8))
