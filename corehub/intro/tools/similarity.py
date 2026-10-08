# usage: similarity.py PREFIX [PREFIX2 ...] -> per-0.5s structural similarity (SSIM on blurred 128x80 greyscale) between
# the 2009 video and each run, plus per-scene means; worst moments first. Higher is better (1 = identical).
import os, sys, json
import numpy as np
from PIL import Image, ImageFilter
from scipy.ndimage import uniform_filter
R = os.path.expanduser('~/mnt/revision9/r10'); M = os.path.expanduser('~/mnt/revision9/runtime/game/corehub_intro/movies')
SCENES = [('Opening', 3, 22), ('Iris+ascent', 22, 32.5), ('Rust room', 32.5, 39), ('Pod rise', 39.5, 47.5), ('Cube passage', 48, 53.8),
          ('Tower', 55.5, 65), ('Turret/16', 65, 74), ('Scanners', 74, 82.5), ('Copper/sludge', 84.5, 95.3), ('Factory', 96.6, 99.8),
          ('Lab', 100, 109.4), ('Incinerator', 110.6, 118.3), ('Capsule', 118.5, 131)]
def load(path):
    im = Image.open(path).convert('L').resize((128, 80), Image.BILINEAR).filter(ImageFilter.GaussianBlur(1.2))
    return np.asarray(im, dtype=np.float64) / 255.0
def ssim(a, b):
    c1, c2 = 0.01 ** 2, 0.03 ** 2
    ma, mb = uniform_filter(a, 7), uniform_filter(b, 7)
    va = uniform_filter(a * a, 7) - ma * ma; vb = uniform_filter(b * b, 7) - mb * mb; cov = uniform_filter(a * b, 7) - ma * mb
    s = ((2 * ma * mb + c1) * (2 * cov + c2)) / ((ma * ma + mb * mb + c1) * (va + vb + c2))
    return float(s.mean())
out = {}
for P in sys.argv[1:]:
    res = {}
    for k in range(0, 269):
        t = k * 0.5; r = f'{R}/ref/stills2/r{k:04d}.jpg'; f = f'{M}/{P}/f{round(t * 60):04d}.jpg'
        if os.path.exists(r) and os.path.exists(f): res[t] = ssim(load(r), load(f))
    out[P] = res
    print(f'== {P}: mean {np.mean(list(res.values())):.3f}')
    for name, a, b in SCENES:
        v = [s for t, s in res.items() if a <= t <= b]
        print(f'  {name:14s} {np.mean(v):.3f}')
    worst = sorted(res.items(), key=lambda kv: kv[1])[:12]
    print('  worst:', ', '.join(f'{t:g}s={s:.2f}' for t, s in worst))
json.dump({p: {str(t): s for t, s in r.items()} for p, r in out.items()}, open(f'{R}/sheets/similarity.json', 'w'))
