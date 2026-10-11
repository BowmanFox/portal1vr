"""Render the 44 review-sheet moments offline with a set of material overrides and build comparison sheets:
2009 video | published rebuild (in game) | offline preview.   usage: render_review.py overrides.json outprefix [t ...]"""
import json, pickle, sys, os, numpy as np
from PIL import Image, ImageDraw
from scene import Scene
from render import Renderer, MaterialLib, apply_fades, to_image
from revsheet import cell
REPO='/home/claude/bowmanfox/portal1vr/corehub/intro'
MATROOTS=['/home/claude/work/mod-src/materials',REPO+'/materials','/home/claude/data/texpack/portal2','/home/claude/data/texpack/portal2_tempcontent','/home/claude/data/texpack/portal']
sc=pickle.load(open('scene_dj.pkl','rb'))
OV=json.load(open(sys.argv[1])) if os.path.exists(sys.argv[1]) else {}
R=Renderer(sc,MaterialLib(MATROOTS,overrides=OV))
print('still missing:',sorted(n for i,n in enumerate(sc.mat_names) if not R.m_found[i]))
rows={round(json.loads(l)['t'],2):json.loads(l) for l in open('run_dj/state.jsonl')}
ts=[float(a) for a in sys.argv[3:]] or [1.5+3*k for k in range(2,44)]
W,H=320,200; per=4
for g in range(0,len(ts),per):
    grp=ts[g:g+per]
    im=Image.new('RGB',(3*W+8,len(grp)*(H+14)),(0,0,0)); d=ImageDraw.Draw(im)
    for k,t in enumerate(grp):
        row=rows[round(t,2)]; y=k*(H+14)
        img=R.render(row['eye'],row['ang'],row['fov'],row['ents'],w=W,h=H)
        off=to_image(apply_fades(img,row))
        ref,reb=cell(t)
        im.paste(ref,(0,y+14)); im.paste(reb,(W+4,y+14)); im.paste(off,(2*W+8,y+14))
        d.text((3,y+1),f'{t:g}s   2009 video | published rebuild (in game) | offline preview',fill=(255,255,0))
    im.save(f'{sys.argv[2]}_{g//per:02d}.jpg',quality=90)
print('sheets',(len(ts)+per-1)//per)
