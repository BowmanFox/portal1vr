"""comparison sheets: 2009 video | offline preview (+ optional game run).
usage: cmp.py TAG [--run NAME] [--cw 512] [--cols 1] [--edges] t0 t1 step | t,t,t...
   TAG = run_<TAG> folder (map.vmf + state.jsonl)."""
import sys, argparse
import numpy as np
from PIL import Image, ImageDraw
from preview import Preview, ref_frame, run_frame
ap = argparse.ArgumentParser()
ap.add_argument('tag'); ap.add_argument('--run'); ap.add_argument('--cw', type=int, default=512); ap.add_argument('--cols', type=int, default=1)
ap.add_argument('--out', default=None); ap.add_argument('--rows', type=int, default=4); ap.add_argument('times', nargs='+')
a = ap.parse_args()
if len(a.times) == 3 and ',' not in a.times[0]:
    t0, t1, st = (float(x) for x in a.times); ts = []; t = t0
    while t <= t1 + 1e-6: ts.append(round(t, 3)); t += st
else:
    ts = [float(x) for x in ','.join(a.times).split(',') if x]
P = Preview(a.tag, quiet=True)
cw = a.cw; ch = cw * 5 // 8; n = 3 if a.run else 2
per = a.cols * a.rows
for g in range(0, len(ts), per):
    grp = ts[g:g + per]; nr = (len(grp) + a.cols - 1) // a.cols
    im = Image.new('RGB', (a.cols * (n * cw + 6), nr * (ch + 2))); d = ImageDraw.Draw(im)
    for k, t in enumerate(grp):
        x = (k % a.cols) * (n * cw + 6); y = (k // a.cols) * (ch + 2)
        cells = [ref_frame(t, (cw, ch))]
        if a.run:
            r = run_frame(a.run, t, (cw, ch)); cells.append(r if r else Image.new('RGB', (cw, ch), (40, 0, 40)))
        cells.append(P.render(t, cw, ch))
        for j, c in enumerate(cells): im.paste(c, (x + j * cw, y))
        d.rectangle((x, y, x + 46, y + 11), fill=(0, 0, 0)); d.text((x + 2, y), '%gs' % t, fill=(255, 255, 0))
    out = (a.out or 'out/cmp_%s' % a.tag) + '_%06.2f.jpg' % grp[0]; im.save(out, quality=88); print(out)
