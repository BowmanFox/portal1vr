"""Small helpers for patching the map (srctools VMF) from scene modules."""
from srctools import VMF, Vec, Angle, Entity


def load(path):
    with open(path, encoding='utf-8', errors='replace') as f:
        from srctools import Keyvalues
        return VMF.parse(Keyvalues.parse(f))


def save(v, path):
    with open(path, 'w', encoding='utf-8') as f:
        v.export(f)


def vec(s):
    return [float(x) for x in str(s).split()]


def fmt(v):
    return ' '.join(('%.6f' % float(x)).rstrip('0').rstrip('.') for x in v)


def ents(v, name=None, model=None, cls=None):
    """entities matching all given filters (model: substring of the model path)"""
    out = []
    for e in v.entities:
        if name is not None and e['targetname'] != name: continue
        if cls is not None and e['classname'] != cls: continue
        if model is not None and model not in e['model', '']: continue
        out.append(e)
    return out


def one(v, **kw):
    r = ents(v, **kw)
    assert len(r) == 1, (kw, len(r))
    return r[0]


def add_prop(v, model, origin, angles=(0, 0, 0), name=None, cls='prop_dynamic_override', **kv):
    e = v.create_ent(classname=cls, model=model, origin=fmt(origin), angles=fmt(angles), solid='0', disableshadows='1', **{k: str(x) for k, x in kv.items()})
    if name: e['targetname'] = name
    return e


def add_box(v, lo, hi, mat, ent=None, mats=None):
    """axis-aligned brush; ent None -> world, 'detail' -> a new func_detail, or an existing Entity to add to.
    mats may override the material per side by outward normal: {'+x': .., '-z': ..}"""
    prism = v.make_prism(Vec(*lo), Vec(*hi), mat)
    if mats:
        for key, side in (('+x', prism.east), ('-x', prism.west), ('+y', prism.north), ('-y', prism.south), ('+z', prism.top), ('-z', prism.bottom)):
            if key in mats: side.mat = mats[key]
    if ent is None: v.add_brush(prism.solid)
    else:
        if ent == 'detail': ent = v.create_ent(classname='func_detail')
        ent.solids.append(prism.solid)
    return prism


def solid_bounds(solid):
    xs = [p for side in solid.sides for p in side.planes]
    return (min(p.x for p in xs), min(p.y for p in xs), min(p.z for p in xs)), (max(p.x for p in xs), max(p.y for p in xs), max(p.z for p in xs))
