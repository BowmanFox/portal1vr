"""sheets of the 2009 video alone.  usage: vidsheet.py t0 t1 step [cols=3] [cellw=512] [outprefix=out/vid]"""
import sys
from PIL import Image, ImageDraw
from preview import ref_frame
t0, t1, st = (float(a) for a in sys.argv[1:4])
cols = int(sys.argv[4]) if len(sys.argv) > 4 else 3; cw = int(sys.argv[5]) if len(sys.argv) > 5 else 512
pre = sys.argv[6] if len(sys.argv) > 6 else 'out/vid'
ch = cw * 5 // 8; rows = 4
ts = []; t = t0
while t <= t1 + 1e-6: ts.append(round(t, 3)); t += st
per = cols * rows
for g in range(0, len(ts), per):
    grp = ts[g:g + per]; nr = (len(grp) + cols - 1) // cols
    im = Image.new('RGB', (cols * cw, nr * ch)); d = ImageDraw.Draw(im)
    for k, t in enumerate(grp):
        x = (k % cols) * cw; y = (k // cols) * ch
        im.paste(ref_frame(t, (cw, ch)), (x, y))
        d.rectangle((x, y, x + 46, y + 11), fill=(0, 0, 0)); d.text((x + 2, y), '%gs' % t, fill=(255, 255, 0))
    out = '%s_%06.2f.jpg' % (pre, grp[0]); im.save(out, quality=88); print(out)
