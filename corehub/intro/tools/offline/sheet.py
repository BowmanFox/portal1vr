"""contact sheet of video frames: sheet.py out.jpg n,n,n | first last step  [--cols 3] [--w 512] [--src hd|E|L] [--crop x0,y0,x1,y1 (HD px)]"""
import sys, argparse, cv2, numpy as np
ap = argparse.ArgumentParser(); ap.add_argument('out'); ap.add_argument('frames', nargs='+'); ap.add_argument('--cols', type=int, default=3); ap.add_argument('--w', type=int, default=512)
ap.add_argument('--src', default='hd'); ap.add_argument('--crop', default=None); ap.add_argument('--gain', type=float, default=1.0)
a = ap.parse_args()
if len(a.frames) == 3 and ',' not in a.frames[0]: ns = list(range(int(a.frames[0]), int(a.frames[1]) + 1, int(a.frames[2])))
else: ns = [int(x) for x in ','.join(a.frames).split(',') if x]
cells = []
for n in ns:
    p = '/home/claude/data/frames_hd/f%04d.jpg' % n if a.src == 'hd' else '/home/claude/data/moments/%s/f%04d.jpg' % (a.src, n)
    im = cv2.imread(p)
    if a.crop:
        x0, y0, x1, y1 = (int(v) for v in a.crop.split(',')); im = im[y0:y1, x0:x1]
    h = int(round(im.shape[0] * a.w / im.shape[1])); im = cv2.resize(im, (a.w, h), interpolation=cv2.INTER_AREA if a.w < im.shape[1] else cv2.INTER_CUBIC)
    if a.gain != 1.0: im = np.clip(im.astype(np.float32) * a.gain, 0, 255).astype(np.uint8)
    cv2.putText(im, str(n), (4, 14), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 255, 255), 1); cells.append(im)
rows = []
for i in range(0, len(cells), a.cols):
    r = cells[i:i + a.cols]
    while len(r) < a.cols: r.append(np.zeros_like(cells[0]))
    rows.append(np.hstack(r))
cv2.imwrite(a.out, np.vstack(rows), [cv2.IMWRITE_JPEG_QUALITY, 88]); print(a.out, np.vstack(rows).shape)
