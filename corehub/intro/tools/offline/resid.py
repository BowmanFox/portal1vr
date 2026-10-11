"""Offline render vs the published review frames: where do they differ? Per frame mean error and, per first-hit
material, the mean signed difference (sRGB).   usage: resid.py [t ...]"""
import json, pickle, sys, os, numpy as np, collections
from scene import Scene
from render import Renderer, MaterialLib, apply_fades, srgb_encode
from revsheet import cell
REPO='/home/claude/bowmanfox/portal1vr/corehub/intro'
MATROOTS=['/home/claude/work/mod-src/materials',REPO+'/materials','/home/claude/data/texpack/portal2','/home/claude/data/texpack/portal2_tempcontent','/home/claude/data/texpack/portal']
sc=pickle.load(open('scene_dj.pkl','rb'))
R=Renderer(sc,MaterialLib(MATROOTS))
rows={round(json.loads(l)['t'],2):json.loads(l) for l in open('run_dj/state.jsonl')}
ts=[float(a) for a in sys.argv[1:]] or [1.5+3*k for k in range(2,44)]
W,H=320,200
tot=collections.defaultdict(lambda:[0,np.zeros(3),np.zeros(3)])
for t in ts:
    row=rows[round(t,2)]
    img,aux=R.render(row['eye'],row['ang'],row['fov'],row['ents'],w=W,h=H,return_aux=True)
    pred=srgb_encode(apply_fades(img,row)).reshape(-1,3)*255
    obs=np.asarray(cell(t)[1],dtype=np.float64).reshape(-1,3)
    d=pred-obs; m=aux['mat'].reshape(-1)
    line=f'{t:6.1f}s mean|d| {np.abs(d).mean():5.1f}  bias {d.mean():+6.1f} |'
    parts=[]
    for mi in np.unique(m[m>=0]):
        s=m==mi
        if s.sum()<600: continue
        parts.append((s.sum(),sc.mat_names[mi].replace('corehub_intro/','').replace('models/',''),d[s].mean(axis=0),pred[s].mean(),obs[s].mean()))
        e=tot[mi]; e[0]+=s.sum(); e[1]+=d[s].sum(axis=0); e[2]+=obs[s].sum(axis=0)
    parts.sort(key=lambda p:-p[0]*abs(p[2].mean()))
    print(line,'; '.join(f'{n} {name} {pm:.0f}->{om:.0f}' for n,name,dd,pm,om in parts[:6]))
if len(ts)>3:
    print('--- overall per material (count, mean signed diff rgb, mean observed)')
    for mi,(n,dsum,osum) in sorted(tot.items(),key=lambda kv:-kv[1][0]*abs(kv[1][1].mean()/max(kv[1][0],1)))[:45]:
        print(f'{n:8d} {sc.mat_names[mi]:52s} diff {np.round(dsum/n).astype(int)} obs {np.round(osum/n).astype(int)}')
