import json, time, sys, numpy as np
from scene import Scene
from render import Renderer, MaterialLib, apply_fades, to_image
REPO='/home/claude/bowmanfox/portal1vr/corehub/intro'
t0=time.time()
sc=Scene(REPO+'/wip/corehub_intro_wip.vmf',[REPO+'/models'])
V=sc.static_arrays()[0]
print('scene built %.1fs: static tris %d, materials %d, dynamic ents %d, missing models %d' % (time.time()-t0,len(V),len(sc.mat_names),len(sc.dynamic),len(sc.missing_models)))
ml=MaterialLib([REPO+'/materials'])
t0=time.time(); R=Renderer(sc,ml); print('renderer init %.1fs'%(time.time()-t0))
rows={round(json.loads(l)['t'],2):json.loads(l) for l in open('run_dm/state.jsonl')}
for t in [float(a) for a in sys.argv[1:]]:
    row=rows[t]; t0=time.time()
    img=R.render(row['eye'],row['ang'],row['fov'],row['ents'])
    to_image(apply_fades(img,row)).save(f'/tmp/off_{t:g}.png'); print(t,row['eye'],row['ang'],row['fov'],'%.1fs'%(time.time()-t0))
