# usage: cmpsheet.py PREFIX t0 t1 step [pairs_per_row=2] [rows=5] [cell_w=384] -> r10/sheets/PREFIX/cmp_NN_<t0>-<t1>.jpg
# Pairs (2009 video | rebuild run) straight from the movie frames (movies/PREFIX/fNNNN.jpg at 60 fps) and r10/ref/frames (29.97 fps).
import os as _os
_ROOT = next(p for p in (_os.environ.get('COREHUB_ROOT') or '', _os.path.expanduser('~/mnt/Games/revision9'), _os.path.expanduser('~/Games/revision9'), _os.path.expanduser('~/mnt/revision9')) if p and _os.path.isdir(p))   # PC, Mac VM or native Mac
import sys, os
from PIL import Image, ImageDraw
R = _ROOT + '/r10'; M = _ROOT + '/runtime/game/corehub_intro/movies'
P = sys.argv[1]; t0, t1, st = (float(a) for a in sys.argv[2:5])
cols = int(sys.argv[5]) if len(sys.argv) > 5 else 2; rows = int(sys.argv[6]) if len(sys.argv) > 6 else 5
w = int(sys.argv[7]) if len(sys.argv) > 7 else 384; h = w * 5 // 8
out = f'{R}/sheets/{P}'; os.makedirs(out, exist_ok=True)
times = []; t = t0
while t <= t1 + 1e-6: times.append(round(t, 3)); t += st
per = cols * rows; made = []
for g in range(0, len(times), per):
    grp = times[g:g + per]; im = Image.new('RGB', (cols * (2 * w + 6), rows * (h + 14)), (0, 0, 0)); d = ImageDraw.Draw(im)
    for k, t in enumerate(grp):
        x = (k % cols) * (2 * w + 6); y = (k // cols) * (h + 14)
        r = f'{R}/ref/frames/f{round(t * 30000 / 1001):04d}.jpg'; m = f'{M}/{P}/f{round(t * 60):04d}.jpg'
        for j, f in enumerate((r, m)):
            if os.path.exists(f): im.paste(Image.open(f).convert('RGB').resize((w, h), Image.BILINEAR), (x + j * w, y + 14))
        d.text((x + 3, y + 1), f'{t:g}s   2009 video | {P}', fill=(255, 255, 0))
    name = f'{out}/cmp_{g // per:02d}_{grp[0]:g}-{grp[-1]:g}.jpg'; im.save(name, quality=85); made.append(name)
print('\n'.join(made))
