"""Scores of a game test run (or the preview) against the 2009 video, per scene.
usage: runscore.py RUN [--step 0.25] [--preview TAG]      RUN = folder /home/claude/data/runs/RUN (m<ms>.jpg, fetched
       with the Mac's fetch_run.py: blends of the run's two 60 fps frames at t and t + 1/60, like the film)
Prints ssim / edge / tone means per scene (see score.py) and writes /home/claude/offline/out/runs/RUN_scores.json."""
import argparse, json, os, math
import numpy as np
from score import scores
from preview import ref_frame, run_frame, film_time

SCENES = [('Opening room', 5.0, 21.7), ('Iris and ascent', 21.75, 32.65), ('Rust room', 32.75, 38.85),
          ('Pod', 39.35, 47.95), ('Cube', 48.0, 54.05), ('Tower', 54.9, 63.95), ('Turret and 16', 64.0, 73.95),
          ('Scanners', 74.0, 83.1), ('Sludge and gallery', 84.6, 95.65), ('Factory', 96.65, 99.75),
          ('Lab', 100.0, 109.6), ('Incinerator', 109.9, 118.35), ('Capsule', 119.3, 132.3)]

if __name__ == '__main__':
    ap = argparse.ArgumentParser(); ap.add_argument('run'); ap.add_argument('--step', type=float, default=0.25); ap.add_argument('--preview')
    a = ap.parse_args()
    P = None
    if a.preview:
        from preview import Preview
        P = Preview(a.preview, quiet=True)
    out = {}; rows = []
    for name, t0, t1 in SCENES:
        vals = []; t = round(math.ceil(t0 / a.step - 1e-9) * a.step, 4)        # on the run's sample grid
        while t <= t1 + 1e-6:
            im = P.render(film_time(t), blend=True) if P else run_frame(a.run, t)
            if im is not None:
                s = scores(ref_frame(t), im); vals.append((t,) + s)
            t = round(t + a.step, 4)
        M = np.array([v[1:] for v in vals]) if vals else np.zeros((0, 3))
        out[name] = dict(t0=t0, t1=t1, n=len(vals), ssim=float(M[:, 0].mean()) if len(M) else None, edge=float(M[:, 1].mean()) if len(M) else None,
                         tone=float(M[:, 2].mean()) if len(M) else None, samples=vals)
        if len(M): print('%-20s %6.2f-%6.2f  n=%3d  ssim %.3f  edge %.3f  tone %.3f' % (name, t0, t1, len(M), M[:, 0].mean(), M[:, 1].mean(), M[:, 2].mean()), flush=True)
        else: print('%-20s no frames' % name)
    allv = np.array([v[1:] for d in out.values() for v in d['samples']])
    print('%-20s %15s  n=%3d  ssim %.3f  edge %.3f  tone %.3f' % ('ALL', '', len(allv), allv[:, 0].mean(), allv[:, 1].mean(), allv[:, 2].mean()))
    os.makedirs('/home/claude/offline/out/runs', exist_ok=True)
    json.dump(out, open('/home/claude/offline/out/runs/%s_scores.json' % (a.preview or a.run), 'w'))
