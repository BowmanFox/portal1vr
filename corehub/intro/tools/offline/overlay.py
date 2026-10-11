"""alignment check: 2009 video | offline preview | video with the preview's edges drawn on it (yellow) and the
video's own edges (cyan) on the preview.   usage: overlay.py TAG [--cw 512] [--grid] [--out prefix] t,t,t  |  t0 t1 step"""
import sys, argparse
import numpy as np, cv2
from PIL import Image, ImageDraw
from preview import Preview, ref_frame
ap = argparse.ArgumentParser()
ap.add_argument('tag'); ap.add_argument('--cw', type=int, default=512); ap.add_argument('--out', default=None)
ap.add_argument('--grid', action='store_true'); ap.add_argument('--rows', type=int, default=3); ap.add_argument('times', nargs='+')
a = ap.parse_args()
if len(a.times) == 3 and ',' not in a.times[0]:
    t0, t1, st = (float(x) for x in a.times); ts = []; t = t0
    while t <= t1 + 1e-6: ts.append(round(t, 3)); t += st
else:
    ts = [float(x) for x in ','.join(a.times).split(',') if x]
P = Preview(a.tag, quiet=True)
cw = a.cw; ch = cw * 5 // 8
def edges(im):
    g = cv2.cvtColor(np.asarray(im), cv2.COLOR_RGB2GRAY); g = cv2.GaussianBlur(g, (0, 0), 1.0)
    return cv2.Canny(g, 25, 60) > 0
def grid(im):
    d = ImageDraw.Draw(im)
    for gx in range(0, 640, 80):
        x = gx * cw // 640; d.line((x, 0, x, ch), fill=(90, 90, 0)); d.text((x + 2, ch - 11), str(gx), fill=(255, 255, 0))
    for gy in range(0, 400, 80):
        y = gy * ch // 400; d.line((0, y, cw, y), fill=(90, 90, 0)); d.text((2, y + 1), str(gy), fill=(255, 255, 0))
    return im
for g in range(0, len(ts), a.rows):
    grp = ts[g:g + a.rows]
    im = Image.new('RGB', (3 * cw + 4, len(grp) * (ch + 2))); d = ImageDraw.Draw(im)
    for k, t in enumerate(grp):
        y = k * (ch + 2)
        v = ref_frame(t, (cw, ch)); o = P.render(t, cw, ch)
        ov = np.asarray(v).copy(); ov[edges(o)] = (255, 255, 0)
        ov = Image.fromarray(ov)
        if a.grid: v = grid(v.copy()); o = grid(o.copy())
        im.paste(v, (0, y)); im.paste(o, (cw + 2, y)); im.paste(ov, (2 * cw + 4, y))
        d.rectangle((0, y, 46, y + 11), fill=(0, 0, 0)); d.text((2, y), '%gs' % t, fill=(255, 255, 0))
    out = (a.out or 'out/ov_%s' % a.tag) + '_%06.2f.jpg' % grp[0]; im.save(out, quality=88); print(out)
