# usage: fetch_frames.py PREFIX t0 t1 step [width=640] [name] -> transfer/frames_<name>.tar with movies/PREFIX frames (60 fps) resized,
# stored as m<ms:06d>.jpg (ms = time in milliseconds). For looking at a run in the offline tooling.
import os as _os
_ROOT = next(p for p in (_os.environ.get('COREHUB_ROOT') or '', _os.path.expanduser('~/mnt/Games/revision9'), _os.path.expanduser('~/Games/revision9'), _os.path.expanduser('~/mnt/revision9')) if p and _os.path.isdir(p))   # PC, Mac VM or native Mac
import sys, os, io, tarfile
from PIL import Image
M = _ROOT + '/runtime/game/corehub_intro/movies'
P = sys.argv[1]; t0, t1, st = (float(a) for a in sys.argv[2:5])
w = int(sys.argv[5]) if len(sys.argv) > 5 else 640; name = sys.argv[6] if len(sys.argv) > 6 else P
out = f'{_ROOT}/transfer/frames_{name}.tar'; n = 0
with tarfile.open(out + '.tmp', 'w') as tar:
    t = t0
    while t <= t1 + 1e-6:
        f = f'{M}/{P}/f{round(t * 60):04d}.jpg'
        if os.path.exists(f):
            im = Image.open(f).convert('RGB')
            if w and im.width != w: im = im.resize((w, w * im.height // im.width), Image.LANCZOS)
            b = io.BytesIO(); im.save(b, 'JPEG', quality=90); b.seek(0)
            ti = tarfile.TarInfo(f'm{round(t * 1000):06d}.jpg'); ti.size = len(b.getvalue()); tar.addfile(ti, b); n += 1
        t += st
os.replace(out + '.tmp', out)
print(out, n, 'frames', os.path.getsize(out), 'bytes')
