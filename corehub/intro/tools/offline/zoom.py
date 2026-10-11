"""zoom into a region of the video frame (and optionally the offline preview) with a pixel grid in 640x400 coordinates.
usage: zoom.py t [x0 y0 x1 y1] [--tag dm] [--step 20] [--scale 3] [--out file]
   --tag adds the offline preview of that run beside the video"""
import sys, argparse
from PIL import Image, ImageDraw
from preview import ref_frame
ap = argparse.ArgumentParser()
ap.add_argument('t', type=float); ap.add_argument('box', nargs='*', type=float)
ap.add_argument('--tag'); ap.add_argument('--step', type=int, default=20); ap.add_argument('--scale', type=float, default=0)
ap.add_argument('--out'); ap.add_argument('--nogrid', action='store_true')
a = ap.parse_args()
x0, y0, x1, y1 = a.box if len(a.box) == 4 else (0, 0, 640, 400)
sc = a.scale or min(4.0, 760.0 / (x1 - x0))
def crop(im):
    c = im.crop((int(x0), int(y0), int(x1), int(y1))).resize((int((x1 - x0) * sc), int((y1 - y0) * sc)), Image.LANCZOS)
    if a.nogrid: return c
    d = ImageDraw.Draw(c)
    gx = (int(x0) // a.step + 1) * a.step
    while gx < x1:
        X = (gx - x0) * sc; d.line((X, 0, X, c.height), fill=(255, 255, 0) if gx % (a.step * 5) == 0 else (120, 120, 0)); d.text((X + 2, 2), str(gx), fill=(255, 255, 0)); gx += a.step
    gy = (int(y0) // a.step + 1) * a.step
    while gy < y1:
        Y = (gy - y0) * sc; d.line((0, Y, c.width, Y), fill=(255, 255, 0) if gy % (a.step * 5) == 0 else (120, 120, 0)); d.text((2, Y + 2), str(gy), fill=(255, 255, 0)); gy += a.step
    return c
cells = [crop(ref_frame(a.t))]
if a.tag:
    from preview import Preview
    cells.append(crop(Preview(a.tag, quiet=True).render(a.t)))
im = Image.new('RGB', (sum(c.width for c in cells) + 4 * (len(cells) - 1), cells[0].height)); x = 0
for c in cells: im.paste(c, (x, 0)); x += c.width + 4
out = a.out or 'out/zoom_%g.jpg' % a.t; im.save(out, quality=90); print(out, im.size)
