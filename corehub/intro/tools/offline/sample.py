"""colour of a small box in the video frame (and in the offline preview), as sRGB 0-255 and as the "$color" to use
on a white base texture.   usage: sample.py t x y [half=3] [--tag TAG]      (640x400 pixel coordinates)"""
import argparse
import numpy as np
from preview import ref_frame
ap = argparse.ArgumentParser()
ap.add_argument('t', type=float); ap.add_argument('x', type=float); ap.add_argument('y', type=float); ap.add_argument('half', type=int, nargs='?', default=3)
ap.add_argument('--tag')
a = ap.parse_args()
def box(im):
    A = np.asarray(im.convert('RGB'), dtype=np.float64)
    x0, x1 = max(0, int(a.x) - a.half), min(640, int(a.x) + a.half + 1); y0, y1 = max(0, int(a.y) - a.half), min(400, int(a.y) + a.half + 1)
    c = A[y0:y1, x0:x1].reshape(-1, 3)
    return c.mean(axis=0), c.std(axis=0).max()
c, sd = box(ref_frame(a.t))
print('video   t %.3f (%d, %d) +-%d: sRGB %s  spread %.1f   "$color" "[%s]"' % (a.t, a.x, a.y, a.half, np.round(c).astype(int).tolist(), sd, ' '.join('%.3f' % (v / 255.0) for v in c)))
if a.tag:
    from preview import Preview
    P = Preview(a.tag, quiet=True)
    c2, sd2 = box(P.render(a.t))
    pk = P.pick(a.t, a.x, a.y)
    print('preview %s: sRGB %s  spread %.1f   %s' % (a.tag, np.round(c2).astype(int).tolist(), sd2, ('material %s, depth %.1f, point (%.1f, %.1f, %.1f)' % ((pk['material'], pk['depth']) + tuple(pk['point']))) if pk else 'nothing hit'))
