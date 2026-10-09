"""r10bv: procedural lens-glare overlays for the turret glare (69.4-71.34 s).

The video's glare frame is a flat grey veil (wall sd 3-5, mean ~107) with a red glow round the turret's lower body
(R +46 at the legs, +30 in the bottom corners, +14 mid-sides) that follows the turret as the camera tilts. A screen
overlay sequence (env_screenoverlay, ten 0.2 s steps) draws a translucent grey veil with a soft red glow centred below
the turret's eye; the eye track is the one the camera is aimed by (see patch_director.py, r10bv).
"""
import math, os, sys
from pathlib import Path
import numpy as np
from srctools.vtf import VTF, ImageFormats, VTFFlags

MOD = Path(os.path.expanduser('~/mnt/revision9/runtime/game/corehub_intro'))
# turret eye in the video, degrees (right of centre, above centre), measured from the bik
EYE = [(69.25, 18.0, 10.9), (69.75, 12.7, 12.7), (70.0, 11.8, 8.5), (70.25, 11.3, 2.4), (70.5, 11.8, -1.9),
       (70.75, 10.4, -1.4), (71.0, 8.5, 1.4), (71.2, 7.6, 1.4), (71.4, 7.6, 1.4)]
def eye_at(t):
    for (t0, a0, b0), (t1, a1, b1) in zip(EYE, EYE[1:]):
        if t0 <= t <= t1:
            f = (t - t0) / (t1 - t0); return a0 + (a1 - a0) * f, b0 + (b1 - b0) * f
    return EYE[-1][1:] if t > EYE[-1][0] else EYE[0][1:]
TIMES = [69.5 + 0.2 * k for k in range(10)]
W = H = 256
A_VEIL = 0.82
BASE = np.array([112.0, 111.0, 111.0])
def smooth(e0, e1, x):
    x = np.clip((x - e0) / (e1 - e0), 0, 1); return x * x * (3 - 2 * x)
def overlay(t):
    r, u = eye_at(t)
    ue = 0.5 + math.tan(math.radians(r)) / 1.2 * 0.5      # our frame: horizontal half-FOV tan 1.2
    ve = 0.5 - math.tan(math.radians(u)) / 0.75 * 0.5     # vertical tan 0.75
    yy, xx = np.mgrid[0:H, 0:W]
    x = (xx + 0.5) / W; y = (yy + 0.5) / H
    cx, cy = ue, min(ve + 0.24, 0.92)
    g1 = np.exp(-(((x - cx) / 0.17) ** 2 + ((y - cy) / 0.24) ** 2) / 2)
    g2 = smooth(0.55, 1.0, y) * (0.55 + 0.45 * np.exp(-((x - cx) / 0.45) ** 2 / 2))
    g3 = np.exp(-(((x - cx) / 0.32) ** 2 + ((y - cy) / 0.30) ** 2) / 2)
    dr = 52 * g1 + 34 * g2 + 14 * g3
    dg = -4 * g1
    img = np.zeros((H, W, 4))
    img[..., 0] = BASE[0] + dr; img[..., 1] = BASE[1] + dg; img[..., 2] = BASE[2] + dg * 0.6
    img[..., 3] = A_VEIL * 255
    return np.clip(img, 0, 255).astype(np.uint8)
def main():
    names = []
    for k, t in enumerate(TIMES):
        img = overlay(t)
        vtf = VTF(W, H, (7, 2), fmt=ImageFormats.RGBA8888,
                  flags=VTFFlags.CLAMP_S | VTFFlags.CLAMP_T | VTFFlags.NO_MIP | VTFFlags.NO_LOD | VTFFlags.EIGHTBITALPHA)
        vtf.get().copy_from(img.tobytes())
        nm = f'glare_{k:02d}'
        p = MOD / 'materials/corehub_intro/r10' / (nm + '.vtf')
        with p.open('wb') as f: vtf.save(f, asw_or_later=False)
        (MOD / 'materials/corehub_intro/r10' / (nm + '.vmt')).write_text(
            f'"UnlitGeneric"\n{{\n"$basetexture" "corehub_intro/r10/{nm}"\n"$translucent" "1"\n"$nocull" "1"\n"$ignorez" "1"\n"$nofog" "1"\n}}\n')
        names.append('corehub_intro/r10/' + nm)
    return names
if __name__ == '__main__':
    print(main())
