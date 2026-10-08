# usage: review_sheets.py PREFIX -> r10/review/overview_N.jpg: original | rebuild pairs every 3 s (for the repo README)
import os, sys
from PIL import Image, ImageDraw
R = os.path.expanduser('~/mnt/revision9/r10'); M = os.path.expanduser('~/mnt/revision9/runtime/game/corehub_intro/movies')
P = sys.argv[1]; os.makedirs(f'{R}/review', exist_ok=True)
ts = [1.5 + 3 * k for k in range(44)]; w, h = 320, 200; cols = 4; per = 16
for g in range(0, len(ts), per):
    grp = ts[g:g + per]; rows = (len(grp) + cols - 1) // cols
    im = Image.new('RGB', (cols * (2 * w + 4), rows * (h + 12))); d = ImageDraw.Draw(im)
    for k, t in enumerate(grp):
        x = (k % cols) * (2 * w + 4); y = (k // cols) * (h + 12)
        for j, f in enumerate([f'{R}/ref/stills2/r{round(t * 2):04d}.jpg', f'{M}/{P}/f{round(t * 60):04d}.jpg']):
            if os.path.exists(f): im.paste(Image.open(f).convert('RGB').resize((w, h)), (x + j * w, y + 12))
        d.text((x + 2, y), f'{t:g}s  2009 video | rebuild {P}', fill=(255, 255, 0))
    im.save(f'{R}/review/overview_{g // per + 1}.jpg', quality=80)
print('review sheets for', P)
