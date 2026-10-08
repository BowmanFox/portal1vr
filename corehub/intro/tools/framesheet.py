# usage: framesheet.py PREFIX OUTNAME t1 t2 ... -> r10/sheets/OUTNAME.jpg (original | rebuild pairs from raw movie frames)
import sys, os
from PIL import Image, ImageDraw
R = os.path.expanduser('~/mnt/revision9/r10'); M = os.path.expanduser('~/mnt/revision9/runtime/game/corehub_intro/movies')
P, name = sys.argv[1], sys.argv[2]; times = [float(a) for a in sys.argv[3:]]
w, h = 480, 300; cols = 2; rows = (len(times) + 1) // 2
im = Image.new('RGB', (cols * (2 * w + 6), rows * (h + 14)), (0, 0, 0)); d = ImageDraw.Draw(im)
for k, t in enumerate(times):
    m = f'{M}/{P}/f{round(t * 60):04d}.jpg'; r = f'{R}/ref/stills2/r{round(t * 2):04d}.jpg'
    x = (k % cols) * (2 * w + 6); y = (k // cols) * (h + 14)
    for j, f in enumerate((r, m)):
        if os.path.exists(f): im.paste(Image.open(f).convert('RGB').resize((w, h)), (x + j * w, y + 14))
    d.text((x + 3, y + 1), f'{t:g}s   original | rebuild', fill=(255, 255, 0))
os.makedirs(f'{R}/sheets', exist_ok=True); im.save(f'{R}/sheets/{name}.jpg', quality=85); print('ok', len(times))
