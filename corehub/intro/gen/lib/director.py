"""Editing the intro director (director.nut) from Python.

The camera of the automatic reference ride is two tables in the script: `positions` ({t, p=Vector}) and `knots`
({t, a=Vector(pitch, yaw, roll)}), linearly interpolated by PositionAt() / ReferenceAngles() (outside the opening,
t < 21.7 s, and the factory, 96.6-99.8 s, which have their own functions). Director parses both tables so a scene
module can replace the camera for a time range with a densely sampled track, and offers checked text replacement
for everything else."""
import re


class Director:
    def __init__(self, text):
        self.text = text
        self.tables = {}
        for name, key in (('knots', 'a'), ('positions', 'p')):
            m = re.search(r'^%s <- \[\n(.*?)\n\];' % name, self.text, re.S | re.M)
            assert m, name
            rows = []
            for line in m.group(1).split('\n'):
                line = line.strip()
                if not line: continue
                mm = re.match(r'\{t=([-\d.eE]+),%s=Vector\(([-\d.eE]+),([-\d.eE]+),([-\d.eE]+)\)\},?$' % key, line)
                assert mm, (name, line)
                rows.append((float(mm.group(1)), (float(mm.group(2)), float(mm.group(3)), float(mm.group(4)))))
            self.tables[name] = dict(key=key, rows=rows, marker='@@TABLE_%s@@' % name)
            self.text = self.text[:m.start(1)] + '@@TABLE_%s@@' % name + self.text[m.end(1):]

    # ------------------------------------------------------------------ camera
    def value(self, name, t):
        rows = self.tables[name]['rows']
        i = 0
        while i < len(rows) - 2 and t >= rows[i + 1][0]: i += 1
        (ta, a), (tb, b) = rows[i], rows[i + 1]
        f = min(1.0, max(0.0, (t - ta) / (tb - ta))) if tb > ta else 0.0
        return tuple(x + (y - x) * f for x, y in zip(a, b))

    def set_range(self, name, t0, t1, rows, pin=(True, True)):
        """replace the rows with t0 <= t <= t1 by `rows` [(t, (x, y, z)), ...]. pin = (start, end): pin the old value
        just outside that end of the range, so the track before / after it is unchanged."""
        tab = self.tables[name]; old = tab['rows']
        eps = 1e-4
        new = [r for r in old if r[0] < t0 - eps]
        if pin[0] and old and old[0][0] < t0 - eps: new.append((t0 - eps, self.value(name, t0 - eps)))
        new += [(float(t), tuple(float(x) for x in v)) for t, v in rows]
        if pin[1] and old and old[-1][0] > t1 + eps: new.append((t1 + eps, self.value(name, t1 + eps)))
        new += [r for r in old if r[0] > t1 + eps]
        ts = [r[0] for r in new]
        assert all(b > a for a, b in zip(ts, ts[1:])), 'times must increase'
        tab['rows'] = new

    def set_camera(self, t0, t1, samples, pin=(True, True)):
        """samples: [(t, (x, y, z), (pitch, yaw, roll)), ...] inside [t0, t1]"""
        self.set_range('positions', t0, t1, [(t, p) for t, p, a in samples], pin)
        self.set_range('knots', t0, t1, [(t, a) for t, p, a in samples], pin)

    # ------------------------------------------------------------------ text
    def replace(self, old, new, count=1):
        n = self.text.count(old)
        assert n == count, 'expected %d occurrence(s) of %r, found %d' % (count, old[:80], n)
        self.text = self.text.replace(old, new)

    def sub(self, pattern, repl, count=1, flags=0):
        self.text, n = re.subn(pattern, repl, self.text, flags=flags)
        assert n == count, 'expected %d match(es) of %r, found %d' % (count, pattern[:80], n)

    def append(self, code):
        """extra globals / functions, added at the end of the script"""
        self.text = self.text.rstrip('\n') + '\n' + code.strip('\n') + '\n'

    def render(self):
        out = self.text
        for name, tab in self.tables.items():
            k = tab['key']
            body = ',\n'.join('{t=%.8f,%s=Vector(%.8f,%.8f,%.8f)}' % (t, k, v[0], v[1], v[2]) for t, v in tab['rows'])
            out = out.replace(tab['marker'], body)
        return out


def lint(text):
    """the old sqlint check: a statement right after '}' on one line without ';' is a Squirrel compile error"""
    bad = []
    for n, line in enumerate(text.split('\n'), 1):
        code = re.sub(r'"(\\.|[^"\\])*"', '""', line.split('//')[0])
        for m in re.finditer(r'\}\s*([A-Za-z_]\w*)', code):
            if m.group(1) in ('else', 'catch'): continue
            bad.append((n, code.strip()[:160]))
    return bad
