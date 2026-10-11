"""sheets of (2009 video | game run) pairs.  usage: pairs.py RUN t0 t1 step [pairs_per_row=3] [cellw=256] [rows=8]"""
import sys
from PIL import Image, ImageDraw
from preview import ref_frame, run_frame
RUN = sys.argv[1]; t0, t1, st = (float(a) for a in sys.argv[2:5])
ppr = int(sys.argv[5]) if len(sys.argv) > 5 else 3; cw = int(sys.argv[6]) if len(sys.argv) > 6 else 256
rows = int(sys.argv[7]) if len(sys.argv) > 7 else 8
ch = cw * 5 // 8
ts = []; t = t0
while t <= t1 + 1e-6: ts.append(round(t, 3)); t += st
per = ppr * rows
for g in range(0, len(ts), per):
    grp = ts[g:g + per]; nr = (len(grp) + ppr - 1) // ppr
    im = Image.new('RGB', (ppr * (2 * cw + 4), nr * ch)); d = ImageDraw.Draw(im)
    for k, t in enumerate(grp):
        x = (k % ppr) * (2 * cw + 4); y = (k // ppr) * ch
        im.paste(ref_frame(t, (cw, ch)), (x, y))
        r = run_frame(RUN, t, (cw, ch))
        if r: im.paste(r, (x + cw, y))
        d.rectangle((x, y, x + 40, y + 10), fill=(0, 0, 0)); d.text((x + 2, y - 1), '%g' % t, fill=(255, 255, 0))
    out = 'out/pairs_%s_%06.2f.jpg' % (RUN, grp[0]); im.save(out, quality=86); print(out)
