"""texcmp.py t material base:color [base:color ...] : render one review moment with alternative textures for a material"""
import json, pickle, sys, os, numpy as np
from PIL import Image, ImageDraw
from render import Renderer, MaterialLib, apply_fades, to_image
from revsheet import cell
REPO='/home/claude/bowmanfox/portal1vr/corehub/intro'
MATROOTS=['/home/claude/work/mod-src/materials',REPO+'/materials','/home/claude/data/texpack/portal2','/home/claude/data/texpack/portal2_tempcontent','/home/claude/data/texpack/portal']
sc=pickle.load(open('scene_dj.pkl','rb'))
rows={round(json.loads(l)['t'],2):json.loads(l) for l in open('run_dj/state.jsonl')}
t=float(sys.argv[1]); mat=sys.argv[2]; alts=sys.argv[3:]
W,H=480,300
row=rows[round(t,2)]
ref,reb=cell(t)
ims=[('2009 video',Image.open(f'/home/claude/data/frames/f{round(t*30000/1001):04d}.jpg').resize((W,H))),('published rebuild',reb.resize((W,H),Image.LANCZOS))]
ml=MaterialLib(MATROOTS); R=Renderer(sc,ml)
for a in alts:
    base,col=a.split(':'); col=[float(x) for x in col.split(',')]
    R.refresh_materials({mat:{'base':base,'color':col if len(col)==3 else col*3}})
    img=R.render(row['eye'],row['ang'],row['fov'],row['ents'],w=W,h=H)
    ims.append((base.split('/')[-1],to_image(apply_fades(img,row))))
cols=2; rws=(len(ims)+1)//2
out=Image.new('RGB',(cols*(W+4),rws*(H+14))); d=ImageDraw.Draw(out)
for k,(lab,im) in enumerate(ims):
    x=(k%cols)*(W+4); y=(k//cols)*(H+14); out.paste(im,(x,y+14)); d.text((x+3,y+1),lab,fill=(255,255,0))
out.save('/tmp/texcmp.jpg',quality=90); print(out.size)
