# usage: sheet3.py OUTNAME PREFIX_A PREFIX_B t1 t2 ... -> r10/sheets/OUTNAME.jpg  (original | A | B per row)
import os as _os
_ROOT = next(p for p in (_os.environ.get('COREHUB_ROOT') or '', _os.path.expanduser('~/mnt/Games/revision9'), _os.path.expanduser('~/Games/revision9'), _os.path.expanduser('~/mnt/revision9')) if p and _os.path.isdir(p))   # PC, Mac VM or native Mac
import sys, os
from PIL import Image, ImageDraw
R = (_ROOT + '/r10'); M = (_ROOT + '/runtime/game/corehub_intro/movies')
name, A, B = sys.argv[1:4]; times = [float(a) for a in sys.argv[4:]]
w, h = 400, 250
im = Image.new('RGB', (3 * w + 8, len(times) * (h + 14)), (0, 0, 0)); d = ImageDraw.Draw(im)
for k, t in enumerate(times):
    y = k * (h + 14)
    for j, f in enumerate((f'{R}/ref/stills2/r{round(t * 2):04d}.jpg', f'{M}/{A}/f{round(t * 60):04d}.jpg', f'{M}/{B}/f{round(t * 60):04d}.jpg')):
        if os.path.exists(f): im.paste(Image.open(f).convert('RGB').resize((w, h)), (j * (w + 4), y + 14))
    d.text((3, y + 1), f'{t:g}s   original | {A} | {B}', fill=(255, 255, 0))
im.save(f'{R}/sheets/{name}.jpg', quality=85); print('ok')
