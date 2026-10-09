"""r10ce: the opening's light flicker (6.8-7.85 s) as a screen-overlay sequence.

Measured from the bik (column means against the lit frame at 8.0 s): the room lights come on in a central band first
(6.85-6.95 s and again 7.2-7.6 s: x 0.36-0.78 lit, the sides at ~0.65), and in between and after they are on except
for dim edges (7.0-7.15 s and 7.7 s: x < 0.23 and x > 0.89 at ~0.85). Each overlay is black with a per-column alpha.
"""
import os
from pathlib import Path
import numpy as np
from srctools.vtf import VTF, ImageFormats, VTFFlags

MOD = Path(os.path.expanduser('~/mnt/revision9/runtime/game/corehub_intro'))
W, H = 64, 4
def smooth(e0, e1, x):
    x = np.clip((x - e0) / (e1 - e0), 0, 1); return x * x * (3 - 2 * x)
def band(lo, hi, a, soft=0.02):     # dark outside [lo, hi]
    x = (np.arange(W) + 0.5) / W
    inside = smooth(lo - soft, lo + soft, x) * (1 - smooth(hi - soft, hi + soft, x))
    return a * (1 - inside)
def edges(lo, hi, a, soft=0.03):    # dark below lo and above hi
    x = (np.arange(W) + 0.5) / W
    return a * np.maximum(1 - smooth(lo - soft, lo + soft, x), smooth(hi - soft, hi + soft, x))
# (duration, alpha per column)
# r10cf: in game an overlay darkens about half as much as its texture alpha says (r10ce measured 0.155 for 0.34), so the
# alphas are twice the wanted darkening; the darkenings come from the video's global means against the lit frame (8 s)
SEQ = [(0.12, band(0.39, 0.75, 0.76)), (0.20, edges(0.23, 0.89, 0.56)), (0.45, band(0.36, 0.78, 0.82)),
       (0.08, edges(0.23, 0.89, 0.72)), (0.07, edges(0.23, 0.89, 0.40)), (0.08, edges(0.06, 1.2, 0.20))]
def main():
    out = []
    for k, (d, al) in enumerate(SEQ):
        img = np.zeros((H, W, 4)); img[..., 3] = np.tile(al * 255, (H, 1))
        vtf = VTF(W, H, (7, 2), fmt=ImageFormats.RGBA8888,
                  flags=VTFFlags.CLAMP_S | VTFFlags.CLAMP_T | VTFFlags.NO_MIP | VTFFlags.NO_LOD | VTFFlags.EIGHTBITALPHA)
        vtf.get().copy_from(np.clip(img, 0, 255).astype(np.uint8).tobytes())
        nm = f'flick_{k:02d}'
        p = MOD / 'materials/corehub_intro/r10' / (nm + '.vtf')
        with p.open('wb') as f: vtf.save(f, asw_or_later=False)
        (MOD / 'materials/corehub_intro/r10' / (nm + '.vmt')).write_text(
            f'"UnlitGeneric"\n{{\n"$basetexture" "corehub_intro/r10/{nm}"\n"$translucent" "1"\n"$nocull" "1"\n"$ignorez" "1"\n"$nofog" "1"\n}}\n')
        out.append(('corehub_intro/r10/' + nm, d))
    return out
if __name__ == '__main__':
    print(main())
