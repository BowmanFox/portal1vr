"""three-way sheets: 2009 video | published r10dj (review sheet cell) | a run fetched into /home/claude/data/runs/<name>
usage: tri.py RUN [cellw=256] [groups_per_row=2] [rows=7] [t...]"""
import sys, os
from PIL import Image, ImageDraw
from revsheet import cell
RUN = sys.argv[1]; cw = int(sys.argv[2]) if len(sys.argv) > 2 else 256; gpr = int(sys.argv[3]) if len(sys.argv) > 3 else 2
rows = int(sys.argv[4]) if len(sys.argv) > 4 else 7
times = [float(a) for a in sys.argv[5:]] or [1.5 + 3 * k for k in range(44)]
ch = cw * 5 // 8
def ref(t): return Image.open('/home/claude/data/frames/f%04d.jpg' % round(t * 30000 / 1001)).convert('RGB')
def run(t):
    p = '/home/claude/data/runs/%s/m%06d.jpg' % (RUN, round(t * 1000))
    return Image.open(p).convert('RGB') if os.path.exists(p) else Image.new('RGB', (cw, ch), (60, 0, 60))
per = gpr * rows
for g in range(0, len(times), per):
    grp = times[g:g + per]
    im = Image.new('RGB', (gpr * (3 * cw + 6), rows * (ch + 12)), (0, 0, 0)); d = ImageDraw.Draw(im)
    for k, t in enumerate(grp):
        x = (k % gpr) * (3 * cw + 6); y = (k // gpr) * (ch + 12)
        try: pub = cell(t)[1]
        except AssertionError: pub = Image.new('RGB', (cw, ch), (30, 30, 30))
        for j, c in enumerate((ref(t), pub, run(t))):
            im.paste(c.resize((cw, ch), Image.BILINEAR), (x + j * cw, y + 12))
        d.text((x + 2, y), '%gs  video | published dj | %s' % (t, RUN), fill=(255, 255, 0))
    out = 'out/tri_%s_%02d.jpg' % (RUN, g // per); im.save(out, quality=88); print(out)
