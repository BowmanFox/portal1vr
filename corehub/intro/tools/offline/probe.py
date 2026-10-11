"""probe.py t [px py] : what does the offline renderer hit along a pixel's ray at time t (r10dj scene)?"""
import json, pickle, sys, numpy as np
from render import Renderer, MaterialLib
REPO='/home/claude/bowmanfox/portal1vr/corehub/intro'
MATROOTS=['/home/claude/work/mod-src/materials',REPO+'/materials','/home/claude/data/texpack/portal2','/home/claude/data/texpack/portal2_tempcontent','/home/claude/data/texpack/portal']
sc=pickle.load(open('scene_dj.pkl','rb'))
R=Renderer(sc,MaterialLib(MATROOTS,overrides={}))
rows={round(json.loads(l)['t'],2):json.loads(l) for l in open('run_dj/state.jsonl')}
t=float(sys.argv[1]); row=rows[round(t,2)]
W,H=320,200
img,aux=R.render(row['eye'],row['ang'],row['fov'],row['ents'],w=W,h=H,return_aux=True,layers=8)
pts=[(int(sys.argv[2]),int(sys.argv[3]))] if len(sys.argv)>3 else [(160,100),(80,50),(240,50),(80,150),(240,150)]
print('eye',row['eye'],'ang',row['ang'],'fov',row['fov'])
for px,py in pts:
    i=py*W+px
    print(f'pixel {px},{py}: depth {aux["depth"].reshape(-1)[i]:.1f}')
    for k in range(aux['L_cnt'][i]):
        m=aux['L_mat'][k][i]; print(f'    layer {k}: {sc.mat_names[m]:50s} alpha {aux["L_alpha"][k][i]:.2f} found {R.m_found[m]}')
