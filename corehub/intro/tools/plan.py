import sys,json
from srctools import VMF
from PIL import Image,ImageDraw
vmf_path,tl_path,out=sys.argv[1:4]
x0,x1,y0,y1=[float(a) for a in sys.argv[4].split(',')] if len(sys.argv)>4 else (-1200,9600,-1600,1600)
zlo,zhi=[float(a) for a in sys.argv[5].split(',')] if len(sys.argv)>5 else (-99999,99999)
v=VMF.parse(vmf_path)
sc=float(sys.argv[6]) if len(sys.argv)>6 else 0.12
W,H=int((x1-x0)*sc),int((y1-y0)*sc)
im=Image.new('RGB',(W,H),(255,255,255));d=ImageDraw.Draw(im)
def P(x,y):return ((x-x0)*sc,(y1-y)*sc)
cnt=0
def draw(sol,col):
  global cnt
  bb=sol.get_bbox();lo,hi=bb
  if hi.z<zlo or lo.z>zhi:return
  if hi.x<x0 or lo.x>x1 or hi.y<y0 or lo.y>y1:return
  a=P(lo.x,hi.y);b=P(hi.x,lo.y)
  d.rectangle([a,b],outline=col);cnt+=1
for s in v.brushes:draw(s,(0,0,0))
for e in v.entities:
  if e['classname'] in('func_detail','func_brush','func_door','func_movelinear','func_illusionary'):
    for s in e.solids:draw(s,(0,120,255))
tl=json.load(open(tl_path))
pts=[P(k['eye'][0],k['eye'][1]) for k in tl['positions']]
for a,b in zip(pts,pts[1:]):d.line([a,b],fill=(255,0,0),width=2)
for k in tl['positions']:
  t=k['time']
  if abs(t-round(t/5)*5)<0.02:
    p=P(k['eye'][0],k['eye'][1]);d.text((p[0]+3,p[1]+3),str(round(t)),fill=(200,0,0))
for x in range(int(x0//500*500),int(x1),500):
  p=P(x,y1);d.text((p[0]+2,2),str(x),fill=(0,140,0));d.line([P(x,y0),P(x,y1)],fill=(220,255,220))
im.save(out);print(cnt,'brushes drawn',W,H)
