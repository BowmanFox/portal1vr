"""objective scores of the offline preview (or a fetched game run) against the 2009 video, per sample and as a mean.
usage: score.py TAG t0 t1 [step=0.5] [--run NAME] [--quiet] [--single]
  The preview is rendered as the film is: the average of the moments t and t + 1/60 (--single: only t).
  ssim   the similarity.py metric of the game runs (SSIM on blurred 128x80 greyscale; 1 = identical)
  edge   how well the outlines agree: F-score of Canny edges matched within 6 px on the 640x400 frame (1 = all outlines
         of both pictures coincide). Sensitive to composition (camera, shapes), blind to tones.
  tone   1 - mean absolute difference of the blurred greyscale pictures / 64 (clipped at 0): overall brightness layout.
Neither replaces looking at the pictures, but a change that lowers all three is a step back."""
import argparse
import numpy as np, cv2
from PIL import Image, ImageFilter
from scipy.ndimage import uniform_filter, distance_transform_edt


def _small(im):
    im = im.convert('L').resize((128, 80), Image.BILINEAR).filter(ImageFilter.GaussianBlur(1.2))
    return np.asarray(im, dtype=np.float64) / 255.0


def ssim(a, b):
    a, b = _small(a), _small(b)
    c1, c2 = 0.01 ** 2, 0.03 ** 2
    ma, mb = uniform_filter(a, 7), uniform_filter(b, 7)
    va = uniform_filter(a * a, 7) - ma * ma; vb = uniform_filter(b * b, 7) - mb * mb; cov = uniform_filter(a * b, 7) - ma * mb
    s = ((2 * ma * mb + c1) * (2 * cov + c2)) / ((ma * ma + mb * mb + c1) * (va + vb + c2))
    return float(s.mean())


def _edges(im):
    g = cv2.cvtColor(np.asarray(im.convert('RGB').resize((640, 400), Image.BILINEAR)), cv2.COLOR_RGB2GRAY)
    g = cv2.GaussianBlur(g, (0, 0), 1.6)
    return cv2.Canny(g, 20, 50) > 0


def edge(a, b, tol=6.0):
    ea, eb = _edges(a), _edges(b)
    if ea.sum() < 50 and eb.sum() < 50: return 1.0
    if ea.sum() < 50 or eb.sum() < 50: return 0.0
    da = distance_transform_edt(~ea); db = distance_transform_edt(~eb)
    p = float((da[eb] <= tol).mean()); r = float((db[ea] <= tol).mean())      # preview edges near video edges / video edges found
    return 2 * p * r / (p + r) if p + r > 0 else 0.0


def tone(a, b):
    ga = cv2.GaussianBlur(np.asarray(a.convert('L').resize((160, 100), Image.BILINEAR), dtype=np.float32), (0, 0), 3)
    gb = cv2.GaussianBlur(np.asarray(b.convert('L').resize((160, 100), Image.BILINEAR), dtype=np.float32), (0, 0), 3)
    return float(max(0.0, 1.0 - np.abs(ga - gb).mean() / 64.0))


def scores(a, b):
    return ssim(a, b), edge(a, b), tone(a, b)


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('tag'); ap.add_argument('t0', type=float); ap.add_argument('t1', type=float); ap.add_argument('step', type=float, nargs='?', default=0.5)
    ap.add_argument('--run'); ap.add_argument('--quiet', action='store_true')
    ap.add_argument('--single', action='store_true', help='compare a single moment instead of the blend of the two moments of a film frame')
    a = ap.parse_args()
    from preview import Preview, ref_frame, run_frame
    P = None if a.run else Preview(a.tag, quiet=True)
    rows = []; t = a.t0
    while t <= a.t1 + 1e-6:
        ref = ref_frame(t)
        im = run_frame(a.run, t) if a.run else P.render(t, blend=not a.single)
        if im is not None:
            rows.append((t,) + scores(ref, im))
        t = round(t + a.step, 4)
    if not a.quiet:
        for t, s, e, o in rows: print('%7.2f  ssim %.3f  edge %.3f  tone %.3f' % (t, s, e, o))
    M = np.array([r[1:] for r in rows])
    print('%s %g-%g s (%d samples): ssim %.3f  edge %.3f  tone %.3f' % (a.run or a.tag, a.t0, a.t1, len(rows), M[:, 0].mean(), M[:, 1].mean(), M[:, 2].mean()))
    worst = sorted(rows, key=lambda r: r[1] + r[2])[:6]
    print('weakest:', ', '.join('%gs (ssim %.2f edge %.2f)' % (r[0], r[1], r[2]) for r in worst))
