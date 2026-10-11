"""Collects, for every pixel of the 44 published review-sheet frames (r10m_dj, every 3 s from 1.5 s), the stack of
surfaces the offline renderer sees there, next to the colour the game actually showed (both in linear light).
usage: calib_data.py [overrides.json] [out.pkl]"""
import json, pickle, time, sys, os, numpy as np
from scene import Scene
from render import Renderer, MaterialLib, srgb_decode
from revsheet import cell
REPO='/home/claude/bowmanfox/portal1vr/corehub/intro'
MATROOTS=[REPO+'/materials','/home/claude/data/texpack/portal2','/home/claude/data/texpack/portal2_tempcontent','/home/claude/data/texpack/portal']
if os.path.exists('scene_dj.pkl'): sc=pickle.load(open('scene_dj.pkl','rb'))
else:
    sc=Scene(REPO+'/map/corehub_intro.vmf',[REPO+'/models']); sc.vmf=None; pickle.dump(sc,open('scene_dj.pkl','wb'))
OV=json.load(open(sys.argv[1])) if len(sys.argv)>1 and os.path.exists(sys.argv[1]) else {}
ml=MaterialLib(MATROOTS,overrides=OV)
R=Renderer(sc,ml)
rows={round(json.loads(l)['t'],2):json.loads(l) for l in open('run_dj/state.jsonl')}
W,H,K=320,200,6
out=dict(names=sc.mat_names,found=R.m_found.copy(),unlit=R.m_unlit.copy(),color=R.m_color.copy(),alpha=R.m_alpha.copy(),
         hastex=R.m_hastex.copy(),nocull=R.m_nocull.copy(),frames=[])
for k in range(44):
    t=1.5+3*k; row=rows[round(t,2)]
    img,aux=R.render(row['eye'],row['ang'],row['fov'],row['ents'],w=W,h=H,return_aux=True,layers=K)
    ref,reb=cell(t)
    obs=srgb_decode(np.asarray(reb,dtype=np.float32).reshape(-1,3)/255.0).astype(np.float32)
    fades={n:float(row['ents'].get(n,{}).get('renderamt',0) or 0) for n in ('r10_veil_fade','r10_red_fade')}
    out['frames'].append(dict(t=t,obs=obs,L_mat=aux['L_mat'],L_alpha=aux['L_alpha'],L_fac=aux['L_fac'],L_cnt=aux['L_cnt'],L_uv=aux['L_uv'],black=row['black'],fades=fades,
                              pred=img.reshape(-1,3).astype(np.float32),trans=aux['trans'].reshape(-1).astype(np.float32)))
pickle.dump(out,open(sys.argv[2] if len(sys.argv)>2 else 'calib_dj.pkl','wb'))
print('saved')
