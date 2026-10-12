"""look at one custom model on its own: six views (four from around and above, from below, from the top) on a grey
background, drawn with the model's own materials exactly as the preview draws them (unlit, back faces culled unless
$nocull).   usage: modelview.py MODELNAME [--out file.jpg] [--size 320] [--angles "p y r"]
   MODELNAME = name of a QC under gen/out/models-src (or any other model source folder), without extension."""
import argparse, math, os, tempfile
import numpy as np
from PIL import Image, ImageDraw
from scene import Scene, angle_matrix
from render import Renderer, MaterialLib, to_image, gamma_to_linear
import preview as PV

ap = argparse.ArgumentParser()
ap.add_argument('name'); ap.add_argument('--out'); ap.add_argument('--size', type=int, default=320); ap.add_argument('--angles', default='0 0 0')
a = ap.parse_args()
vmf = 'world\n{\n\t"id" "1"\n\t"classname" "worldspawn"\n}\nentity\n{\n\t"id" "2"\n\t"classname" "prop_dynamic"\n\t"targetname" "m"\n\t"model" "models/corehub_intro/%s.mdl"\n\t"origin" "0 0 0"\n\t"angles" "%s"\n}\n' % (a.name, a.angles)
tmp = tempfile.NamedTemporaryFile('w', suffix='.vmf', delete=False); tmp.write(vmf); tmp.close()
sc = Scene(tmp.name); os.unlink(tmp.name)
ml = MaterialLib(PV.MAT_ROOTS)
sc.finalize(PV.MODEL_DIRS, stock_roots=PV.STOCK_ROOTS, mat_exists=lambda n: ml.idx.find(n + '.vmt') is not None)
assert not sc.missing_models, 'no source for model %s' % a.name
R = Renderer(sc, ml)
V = np.concatenate([p['tris'].arrays()[0].reshape(-1, 3) for p in sc.dynamic['m']]).astype(np.float64) @ angle_matrix(*[float(x) for x in a.angles.split()]).T
lo, hi = V.min(axis=0), V.max(axis=0); c = (lo + hi) / 2; rad = float(np.linalg.norm(hi - lo)) / 2 + 1e-3
ntri = sum(len(p['tris'].arrays()[0]) for p in sc.dynamic['m'])
miss = sorted(n for i, n in enumerate(sc.mat_names) if not R.m_found[i])
print('%s: %d triangles, bounds (%.1f %.1f %.1f) .. (%.1f %.1f %.1f), %d materials%s' % (a.name, ntri, *lo, *hi, len(sc.mat_names), ('; MISSING materials: %s' % miss) if miss else ''))
views = [('from +X +Y above', (20, 225, 0)), ('from -X +Y above', (20, 315, 0)), ('from -X -Y above', (20, 45, 0)), ('from +X -Y above', (20, 135, 0)),
         ('from below (+X up in picture)', (-89, 0, 0)), ('from the top (+X up in picture)', (89, 0, 0))]
s = a.size; sheet = Image.new('RGB', (3 * s, 2 * (s * 5 // 8 + 14)), (0, 0, 0)); d = ImageDraw.Draw(sheet)
bg = gamma_to_linear(np.array([0.36, 0.40, 0.46]))
fov = 40.0
for k, (label, ang) in enumerate(views):
    f = angle_matrix(*ang)[:, 0]
    dist = rad / math.tan(math.radians(fov) / 2 * 0.75) * 1.15
    img, aux = R.render(c - f * dist, ang, fov, {}, w=s, h=s * 5 // 8, return_aux=True)
    T = aux['trans'][..., None]
    img = img + T * bg * (aux['mat'][..., None] < 0)
    x = (k % 3) * s; y = (k // 3) * (s * 5 // 8 + 14)
    sheet.paste(to_image(np.clip(img, 0, 1)), (x, y + 14)); d.text((x + 3, y + 1), label, fill=(255, 255, 0))
out = a.out or 'out/model_%s.jpg' % a.name
sheet.save(out, quality=90); print(out)
