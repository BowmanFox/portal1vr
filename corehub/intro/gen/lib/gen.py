"""Shared helpers for the model generators (gen/models/*.py).

Every generator builds meshes with lib.mesh.Mesh, registers the materials they use with mat()/ramp() and saves
SMD + QC with save(). build.py runs them all and writes gen/out/:
    out/models-src/<name>.smd|qc          sources for studiomdl (compiled on the Mac by the 'model' request)
    out/materials/models/corehub_intro/   the models' materials (UnlitGeneric, flat colours on a white base)
All colours are the "$color" values the game uses (gamma space, 0..1); shading is baked with ramps of materials.
"""
import os
import numpy as np
from .mesh import Mesh, V, rot_x, rot_y, rot_z, angle_matrix   # noqa: F401  (re-exported)

GEN = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(GEN, 'out')
MODELS_OUT = os.path.join(OUT, 'models-src')
MATS_OUT = os.path.join(OUT, 'materials')
WHITE = 'lights/white002'
F4 = (0.265, 0.43, 0.68, 1.0)          # shade factors of a 4-step ramp (darkest .. brightest), as the old tube skins used

_mats = {}        # path under materials/ (no extension) -> vmt text
_models = []      # names saved in this run


def _fmt(c):
    if isinstance(c, (int, float)): c = (c, c, c)
    return '[%s]' % ' '.join(('%.4f' % float(x)).rstrip('0').rstrip('.') for x in c)


def mat(name, color=(1, 1, 1), base=WHITE, alpha=None, nocull=False, additive=False, translucent=False, extra=None,
        folder='models/corehub_intro', model=True):
    """register an UnlitGeneric material; returns the bare name to use on triangles"""
    lines = ['"UnlitGeneric"', '{', '"$basetexture" "%s"' % base, '"$color" "%s"' % _fmt(color)]
    if model: lines.append('"$model" "1"')
    if alpha is not None: lines.append('"$alpha" "%s"' % ('%.3f' % alpha).rstrip('0').rstrip('.'))
    if translucent: lines.append('"$translucent" "1"')
    if nocull: lines.append('"$nocull" "1"')
    if additive: lines.append('"$additive" "1"')
    for k, v in (extra or {}).items(): lines.append('"%s" "%s"' % (k, v))
    lines.append('}')
    _mats[folder.strip('/') + '/' + name] = '\n'.join(lines) + '\n'
    return name


def ramp(prefix, top, factors=F4, **kw):
    """materials prefix0..prefixN (dark .. bright) for Mesh.shade(prefix, levels=len(factors))"""
    top = (top,) * 3 if isinstance(top, (int, float)) else top
    for i, f in enumerate(factors):
        mat('%s%d' % (prefix, i), tuple(c * f for c in top), **kw)
    return prefix


def save(mesh, name, **kw):
    _models.append(name)
    return mesh.save(name, MODELS_OUT, **kw)


def write_materials():
    for path, text in sorted(_mats.items()):
        p = os.path.join(MATS_OUT, path + '.vmt')
        os.makedirs(os.path.dirname(p), exist_ok=True)
        if not os.path.exists(p) or open(p).read() != text: open(p, 'w').write(text)
    return len(_mats)


def write_texture(path, rgba, mips=True, clamp=False):
    """write an own texture (numpy uint8 array h x w x 3|4) as materials/<path>.vtf (VTF 7.2, readable by the 2009 engine)"""
    from srctools.vtf import VTF, ImageFormats, VTFFlags
    a = np.asarray(rgba, dtype=np.uint8)
    if a.shape[2] == 3: a = np.concatenate([a, np.full(a.shape[:2] + (1,), 255, np.uint8)], axis=2)
    h, w = a.shape[:2]
    flags = VTFFlags.EIGHTBITALPHA if (a[..., 3] < 255).any() else VTFFlags(0)
    if clamp: flags |= VTFFlags.CLAMP_S | VTFFlags.CLAMP_T
    if not mips: flags |= VTFFlags.NO_MIP | VTFFlags.NO_LOD
    vtf = VTF(w, h, (7, 2), fmt=ImageFormats.RGBA8888, flags=flags)
    vtf.get().copy_from(a.tobytes())
    if mips: vtf.compute_mipmaps()
    p = os.path.join(MATS_OUT, path + '.vtf')
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p, 'wb') as f: vtf.save(f, asw_or_later=False)
    return path
