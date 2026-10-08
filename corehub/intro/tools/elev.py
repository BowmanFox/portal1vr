import sys,json
from srctools import VMF
from PIL import Image,ImageDraw
vmf_path,tl_path,out=sys.argv[1:4]
x0,x1,z0,z1=[float(a) for a in sys.argv[4].split(',')]
ylo,yhi=[float(a) for a in sys.argv[5].split(',')]
sc=float(sys.argv[6])
v=VMF.parse(vmf_path)
W,H=int((x1-x0)*sc),int((z1-z0)*sc)
im=Image.new('RGB',(W,H),(255,255,255));d=ImageDraw.Draw(im)
def P(x,z):return ((x-x0)*sc,(z1-z)*sc)
def draw(sol,col):
  lo,hi=sol.get_bbox()
  if hi.y<ylo or lo.y>yhi:return
  d.rectangle([P(lo.x,hi.z),P(hi.x,lo.z)],outline=col)
for s in v.brushes:draw(s,(0,0,0))
for e in v.entities:
  if e['classname'] in('func_detail','func_brush','func_door','func_movelinear','func_illusionary'):
    for s in e.solids:draw(s,(0,120,255))
tl=json.load(open(tl_path))
pts=[P(k['eye'][0],k['eye'][2]) for k in tl['positions']]
for a,b in zip(pts,pts[1:]):d.line([a,b],fill=(255,0,0),width=2)
for k in tl['positions']:
  t=k['time']
  if abs(t-round(t/5)*5)<0.02:
    p=P(k['eye'][0],k['eye'][2]);d.text((p[0]+3,p[1]+3),str(round(t)),fill=(200,0,0))
for x in range(int(x0//500*500),int(x1),500):
  p=P(x,z1);d.text((p[0]+2,2),str(x),fill=(0,140,0))
im.save(out)
