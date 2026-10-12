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
        self.cam_overrides = []; self.hooks_early = []; self.hooks_late = []

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

    def override_camera(self, samples, fov=None):
        """The camera follows `samples` [(t, (x, y, z), (pitch, yaw, roll)), ...] (linear interpolation, times strictly
        increasing) from the first to the last sample time; outside that range nothing changes. Works everywhere,
        including the opening (t < 21.7) and the factory, which do not use the camera tables. fov: optional constant
        field of view for the range (FilmFov otherwise). Several overrides may be added; they must not overlap."""
        rows = []
        prev = None
        for t, p, a in samples:
            a = [float(x) for x in a]
            if prev is not None:                      # keep the angles continuous (no jumps of 360 between samples)
                for k in range(3):
                    while a[k] - prev[k] > 180: a[k] -= 360
                    while a[k] - prev[k] < -180: a[k] += 360
            prev = a
            rows.append((float(t), tuple(float(x) for x in p), tuple(a)))
        ts = [r[0] for r in rows]
        assert len(rows) >= 2 and all(b > a for a, b in zip(ts, ts[1:])), 'need two or more samples with increasing times'
        for o in self.cam_overrides:
            assert ts[-1] < o['rows'][0][0] or ts[0] > o['rows'][-1][0], 'camera overrides overlap'
        self.cam_overrides.append(dict(rows=rows, fov=fov))

    def hook(self, call, late=True):
        """run a Squirrel statement on every tick with the film time `t` in scope, e.g. hook('Rust_Update(t);').
        late=True: after all of the base director's scene code (so it has the last word on an entity);
        late=False: before it. Define the function itself with append()."""
        (self.hooks_late if late else self.hooks_early).append(call.strip())

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
        if self.cam_overrides:
            def once(text, old, new):
                assert text.count(old) == 1, old
                return text.replace(old, new)
            tabs = []
            ovs = sorted(self.cam_overrides, key=lambda o: o['rows'][0][0])
            for j, o in enumerate(ovs):
                body = ',\n'.join('[%.6f,%.4f,%.4f,%.4f,%.5f,%.5f,%.5f]' % ((t,) + p + a) for t, p, a in o['rows'])
                # hold the last sample for one more 60 Hz tick (a shot's last sample is a frame's later moment; the next
                # shot starts with the next frame's earlier moment, 1/60 s later), but never into the next override
                t1 = o['rows'][-1][0] + 0.0175
                if j + 1 < len(ovs): t1 = min(t1, ovs[j + 1]['rows'][0][0] - 1e-6)
                tabs.append('{t0=%.6f,t1=%.6f,fov=%s,i=0,rows=[\n%s]}' % (o['rows'][0][0], t1, 'null' if o['fov'] is None else '%.4f' % o['fov'], body))
            code = 'camOv <- [\n' + ',\n'.join(tabs) + '];\n' + CAM_OV_CODE
            out = once(out, 'function PositionAt(t) {\n', 'function PositionAt(t) {\n    local ov=CamOvFind(t); if(ov!=null)return CamOvValue(ov,t,1);\n')
            out = once(out, 'function ReferenceAngles(t) {\n', 'function ReferenceAngles(t) {\n    local ov=CamOvFind(t); if(ov!=null)return CamOvValue(ov,t,4);\n')
            out = once(out, 'function FilmFov(t) { ', 'function FilmFov(t) { local ov=CamOvFind(t); if(ov!=null && ov.fov!=null)return ov.fov; ')
            out = once(out, 'function FilmFov(t) {', code + 'function FilmFov(t) {')
        if self.hooks_early:
            a = 'function SetSceneTime(t) {\n    P41_Update(t);\n'
            assert out.count(a) == 1
            out = out.replace(a, a + ''.join('    %s\n' % h for h in self.hooks_early))
        if self.hooks_late:
            a = ' SetSceneTime(t);\n local report='
            assert out.count(a) == 1
            out = out.replace(a, ' SetSceneTime(t);\n' + ''.join(' %s\n' % h for h in self.hooks_late) + ' local report=')
        return out


CAM_OV_CODE = '''function CamOvFind(t) {
    foreach(o in camOv) if(t>=o.t0 && t<=o.t1) return o;
    return null;
}
function CamOvValue(o,t,k) {
    local r=o.rows, n=r.len(), i=o.i;
    if(i>n-2)i=n-2;
    while(i>0 && t<r[i][0])i--;
    while(i<n-2 && t>=r[i+1][0])i++;
    o.i=i;
    local a=r[i], b=r[i+1], f=(t-a[0])/(b[0]-a[0]);
    if(f<0)f=0; if(f>1)f=1;
    return Vector(a[k]+(b[k]-a[k])*f, a[k+1]+(b[k+1]-a[k+1])*f, a[k+2]+(b[k+2]-a[k+2])*f);
}
'''


def lint(text):
    """the old sqlint check: a statement right after '}' on one line without ';' is a Squirrel compile error"""
    bad = []
    for n, line in enumerate(text.split('\n'), 1):
        code = re.sub(r'"(\\.|[^"\\])*"', '""', line.split('//')[0])
        for m in re.finditer(r'\}\s*([A-Za-z_]\w*)', code):
            if m.group(1) in ('else', 'catch'): continue
            bad.append((n, code.strip()[:160]))
    return bad
