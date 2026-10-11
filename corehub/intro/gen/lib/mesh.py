"""Small mesh builder for the corehub_intro custom models (SMD + QC for the Corehub build's studiomdl).

Rewritten on the Mac in Oct 2026 (the original helper was lost with the old PC). Models are flat-shaded and
unlit in game, so shading is baked by giving each face one of several materials of a ramp ("name0".."nameN")
according to its normal; see Mesh.shade().

Conventions: Source units, +Z up. With "$origin 0 0 0 -90" in the QC the SMD coordinates are the model's own
coordinates in game (entity angles "pitch yaw roll" then rotate it as usual).
"""
import math, os
import numpy as np


def V(*a):
    if len(a) == 1:
        a = a[0]
        if hasattr(a, 'x') and hasattr(a, 'y') and hasattr(a, 'z'): return np.array([a.x, a.y, a.z], dtype=float)
    return np.array(a, dtype=float)


def rot_x(d):
    c, s = math.cos(math.radians(d)), math.sin(math.radians(d)); return np.array([[1, 0, 0], [0, c, -s], [0, s, c]])


def rot_y(d):
    c, s = math.cos(math.radians(d)), math.sin(math.radians(d)); return np.array([[c, 0, s], [0, 1, 0], [-s, 0, c]])


def rot_z(d):
    c, s = math.cos(math.radians(d)), math.sin(math.radians(d)); return np.array([[c, -s, 0], [s, c, 0], [0, 0, 1]])


def angle_matrix(pitch, yaw, roll):
    """Source QAngle -> rotation matrix (same as the engine's AngleMatrix)."""
    sp, cp = math.sin(math.radians(pitch)), math.cos(math.radians(pitch))
    sy, cy = math.sin(math.radians(yaw)), math.cos(math.radians(yaw))
    sr, cr = math.sin(math.radians(roll)), math.cos(math.radians(roll))
    return np.array([[cp * cy, sr * sp * cy - cr * sy, cr * sp * cy + sr * sy],
                     [cp * sy, sr * sp * sy + cr * cy, cr * sp * sy - sr * cy],
                     [-sp, sr * cp, cr * cp]])


class Tri:
    __slots__ = ('mat', 'p', 'n', 'uv')

    def __init__(self, mat, p, n=None, uv=None):
        self.mat = mat; self.p = [V(q) for q in p]
        if n is None:
            nn = np.cross(self.p[1] - self.p[0], self.p[2] - self.p[0]); ln = np.linalg.norm(nn)
            nn = nn / ln if ln > 1e-12 else np.array([0, 0, 1.0])
            n = [nn, nn, nn]
        self.n = [V(q) for q in n]; self.uv = uv

    def face_normal(self):
        nn = np.cross(self.p[1] - self.p[0], self.p[2] - self.p[0]); ln = np.linalg.norm(nn)
        return nn / ln if ln > 1e-12 else np.array([0, 0, 1.0])

    # compatibility with the old generators, which unpacked (material, points, normals)
    def __iter__(self):
        return iter((self.mat, self.p, self.n))


class Mesh:
    def __init__(self):
        self.tris = []

    # ------------------------------------------------------------------ primitives
    def tri(self, mat, a, b, c, n=None, uv=None):
        """counter-clockwise seen from outside"""
        self.tris.append(Tri(mat, (a, b, c), n, uv)); return self

    def quad(self, mat, a, b, c, d):
        self.tri(mat, a, b, c); self.tri(mat, a, c, d); return self

    def poly(self, mat, pts):
        pts = [V(p) for p in pts]
        for k in range(1, len(pts) - 1): self.tri(mat, pts[0], pts[k], pts[k + 1])
        return self

    def box(self, lo, hi, mat, mats=None):
        """axis-aligned box. mats may override single faces: keys '+x','-x','+y','-y','+z','-z' (None skips a face)."""
        lo, hi = V(lo), V(hi)
        x0, y0, z0 = np.minimum(lo, hi); x1, y1, z1 = np.maximum(lo, hi)
        faces = {'+x': [(x1, y0, z0), (x1, y1, z0), (x1, y1, z1), (x1, y0, z1)], '-x': [(x0, y1, z0), (x0, y0, z0), (x0, y0, z1), (x0, y1, z1)],
                 '+y': [(x1, y1, z0), (x0, y1, z0), (x0, y1, z1), (x1, y1, z1)], '-y': [(x0, y0, z0), (x1, y0, z0), (x1, y0, z1), (x0, y0, z1)],
                 '+z': [(x0, y0, z1), (x1, y0, z1), (x1, y1, z1), (x0, y1, z1)], '-z': [(x0, y1, z0), (x1, y1, z0), (x1, y0, z0), (x0, y0, z0)]}
        for key, q in faces.items():
            m = mat if not mats or key not in mats else mats[key]
            if m is None: continue
            self.quad(m, *q)
        return self

    def obox(self, center, half, R, mat, mats=None):
        """box with half-extents 'half' rotated by matrix R about its centre"""
        b = Mesh().box(-V(half), V(half), mat, mats)
        return self.add(b, R=R, offset=center)

    def lathe(self, profile, mat, n=16, axis='z', phase=0.0, arc=360.0, smooth=False, caps=True):
        """solid of revolution. profile: [(pos along axis, radius), ...] walked so that the outside is on the left when the
        axis points up (i.e. for an outer surface give ascending positions with the solid toward the axis... simply:
        the face normal follows (dr, -dpos) rotated out of the profile; reverse the profile if faces come out inverted).
        arc < 360 makes a partial sweep (open ends are not capped)."""
        prof = [(float(a), float(r)) for a, r in profile]
        steps = n if arc >= 360 else max(1, int(round(n * arc / 360.0)))
        da = math.radians(arc) / steps
        def pt(a, r, ang):
            c, s = math.cos(ang), math.sin(ang)
            if axis == 'z': return V(r * c, r * s, a)
            if axis == 'x': return V(a, r * c, r * s)
            return V(r * s, a, r * c)
        for k in range(steps):
            a0 = math.radians(phase) + k * da; a1 = a0 + da
            for (p0, r0), (p1, r1) in zip(prof, prof[1:]):
                if abs(p0 - p1) < 1e-9 and abs(r0 - r1) < 1e-9: continue
                q00, q01, q10, q11 = pt(p0, r0, a0), pt(p0, r0, a1), pt(p1, r1, a0), pt(p1, r1, a1)
                if r0 < 1e-9: self.tri(mat, q00, q11, q10)
                elif r1 < 1e-9: self.tri(mat, q00, q01, q10)
                else: self.quad(mat, q00, q01, q11, q10)
        if smooth: self.smooth_about_axis(axis)
        return self

    def tube(self, a, b, radius, mat, n=8, caps=True, radius2=None):
        """cylinder (or cone when radius2 is given) from point a to point b"""
        a, b = V(a), V(b); d = b - a; L = np.linalg.norm(d)
        if L < 1e-9: return self
        d = d / L
        u = np.cross(d, [0, 0, 1.0]) if abs(d[2]) < 0.99 else np.cross(d, [1.0, 0, 0]); u /= np.linalg.norm(u); w = np.cross(d, u)
        r1 = radius if radius2 is None else radius2
        ring0 = [a + radius * (math.cos(2 * math.pi * k / n) * u + math.sin(2 * math.pi * k / n) * w) for k in range(n)]
        ring1 = [b + r1 * (math.cos(2 * math.pi * k / n) * u + math.sin(2 * math.pi * k / n) * w) for k in range(n)]
        for k in range(n):
            k2 = (k + 1) % n
            self.quad(mat, ring0[k], ring0[k2], ring1[k2], ring1[k])
        if caps:
            self.poly(mat, ring0[::-1]); self.poly(mat, ring1)
        return self

    def prism(self, outline, z0, z1, mat, top=None, bottom=None, side=None):
        """extrude a convex 2D outline [(x, y), ...] (counter-clockwise seen from +z) from z0 to z1"""
        o = [(float(x), float(y)) for x, y in outline]
        for k in range(len(o)):
            (xa, ya), (xb, yb) = o[k], o[(k + 1) % len(o)]
            self.quad(side or mat, (xa, ya, z0), (xb, yb, z0), (xb, yb, z1), (xa, ya, z1))
        self.poly(top or mat, [(x, y, z1) for x, y in o]); self.poly(bottom or mat, [(x, y, z0) for x, y in o][::-1])
        return self

    def sphere(self, center, radius, mat, n=12, m=8, squash=(1, 1, 1)):
        c = V(center)
        def pt(i, j):
            th = math.pi * j / m; ph = 2 * math.pi * i / n
            return c + radius * np.array([squash[0] * math.sin(th) * math.cos(ph), squash[1] * math.sin(th) * math.sin(ph), squash[2] * math.cos(th)])
        for i in range(n):
            for j in range(m):
                a, b, cc, d = pt(i, j), pt(i + 1, j), pt(i + 1, j + 1), pt(i, j + 1)
                if j == 0: self.tri(mat, a, d, cc)
                elif j == m - 1: self.tri(mat, a, d, b)
                else: self.quad(mat, a, d, cc, b)
        return self

    # ------------------------------------------------------------------ combining and editing
    def add(self, other, R=None, offset=(0, 0, 0), scale=1.0, mat=None):
        off = V(offset)
        flip = R is not None and np.linalg.det(R) < 0
        for t in other.tris:
            p = [(q * scale) for q in t.p]; n = t.n
            if R is not None:
                p = [R @ q for q in p]; n = [R @ q for q in n]
            p = [q + off for q in p]
            if flip: p = p[::-1]; n = n[::-1]
            self.tris.append(Tri(mat or t.mat, p, n, t.uv))
        return self

    def transform(self, R=None, offset=(0, 0, 0), scale=1.0):
        m = Mesh().add(self, R, offset, scale); self.tris = m.tris; return self

    def flip(self):
        for t in self.tris: t.p = t.p[::-1]; t.n = [-q for q in t.n[::-1]]
        return self

    def flat(self):
        for t in self.tris:
            n = t.face_normal(); t.n = [n, n, n]
        return self

    def smooth_about_axis(self, axis='z'):
        """vertex normals pointing radially away from an axis through the origin (for lathed parts)"""
        i = 'xyz'.index(axis)
        for t in self.tris:
            fn = t.face_normal(); ns = []
            for q in t.p:
                r = q.copy(); r[i] = 0; ln = np.linalg.norm(r)
                if ln < 1e-6: ns.append(fn); continue
                r /= ln; n = r * math.sqrt(max(0.0, 1 - fn[i] ** 2)) * (1 if np.dot(r, fn) >= 0 else -1); n[i] = fn[i]
                ln = np.linalg.norm(n); ns.append(n / ln if ln > 1e-9 else fn)
            t.n = ns
        return self

    def shade(self, base, levels=4, light=(0.35, -0.25, 0.9), only=None, ambient=0.0):
        """Bake flat shading: every triangle whose material is `only` (default: `base`) gets material base+str(k),
        k = 0 (darkest) .. levels-1 (brightest), from the angle between its normal and the light direction."""
        L = V(light); L = L / np.linalg.norm(L); src = only or base
        for t in self.tris:
            if t.mat != src: continue
            d = float(np.dot(t.face_normal(), L)) * 0.5 + 0.5          # 0 .. 1
            d = ambient + (1 - ambient) * d
            t.mat = f'{base}{min(levels - 1, int(d * levels))}'
        return self

    def bounds(self):
        P = np.array([q for t in self.tris for q in t.p]); return P.min(axis=0), P.max(axis=0)

    def materials(self):
        return sorted({t.mat for t in self.tris})

    # ------------------------------------------------------------------ output
    def uv_box(self, scale=128.0, only=None):
        """box-projected texture coordinates (for textured materials), `scale` units per texture repeat"""
        for t in self.tris:
            if only and t.mat not in only: continue
            n = np.abs(t.face_normal()); ax = int(np.argmax(n))
            ia, ib = [(1, 2), (0, 2), (0, 1)][ax]
            t.uv = [(q[ia] / scale, q[ib] / scale) for q in t.p]
        return self

    def save(self, name, outdir, cdmaterials='models/corehub_intro', staticprop=True, skins=None, renames=None,
             modelname=None, surfaceprop='metal', extra_qc=''):
        """writes <outdir>/<name>.smd and <name>.qc and returns the QC path"""
        os.makedirs(outdir, exist_ok=True)
        smd = ['version 1', 'nodes', '0 "root" -1', 'end', 'skeleton', 'time 0', '0 0 0 0 0 0 0', 'end', 'triangles']
        for t in self.tris:
            smd.append(t.mat)
            uv = t.uv or [(0.0, 0.0), (1.0, 0.0), (0.0, 1.0)]
            for q, n, (uu, vv) in zip(t.p, t.n, uv):
                smd.append('0 %.5f %.5f %.5f %.5f %.5f %.5f %.4f %.4f' % (q[0], q[1], q[2], n[0], n[1], n[2], uu, vv))
        smd.append('end')
        open(os.path.join(outdir, name + '.smd'), 'w').write('\n'.join(smd) + '\n')
        qc = ['$modelname "%s"' % (modelname or f'corehub_intro/{name}.mdl'), '$origin 0 0 0 -90', '$body body "%s.smd"' % name,
              '$cdmaterials "%s"' % cdmaterials, '$surfaceprop "%s"' % surfaceprop]
        if staticprop: qc.append('$staticprop')
        for a, b in (renames or {}).items(): qc.append('$renamematerial "%s" "%s"' % (a, b))
        if skins:
            qc += ['$texturegroup skinfamilies', '{'] + ['{ ' + ' '.join('"%s"' % m for m in fam) + ' }' for fam in skins] + ['}']
        if extra_qc: qc.append(extra_qc.strip())
        qc.append('$sequence idle "%s.smd" fps 1' % name)
        p = os.path.join(outdir, name + '.qc')
        open(p, 'w').write('\n'.join(qc) + '\n')
        return p
