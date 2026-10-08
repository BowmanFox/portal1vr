import sys,json,math,os
from srctools import VMF
from PIL import Image,ImageDraw
vmf_path,out=sys.argv[1:3]
x0,x1,y0,y1=[float(a) for a in sys.argv[3].split(',')]
zlo,zhi=[float(a) for a in sys.argv[4].split(',')]
sc=float(sys.argv[5])
cams=[float(a) for a in sys.argv[6].split(',')] if len(sys.argv)>6 else []
v=VMF.parse(vmf_path)
W,H=int((x1-x0)*sc),int((y1-y0)*sc)
im=Image.new('RGB',(W,H),(255,255,255));d=ImageDraw.Draw(im)
def P(x,y):return ((x-x0)*sc,(y1-y)*sc)
def draw(s,col):
  lo,hi=s.get_bbox()
  if hi.z<zlo or lo.z>zhi or hi.x<x0 or lo.x>x1 or hi.y<y0 or lo.y>y1:return
  # draw actual face polygons projected (top view outline of the solid's vertices)
  pts=set()
  for f in s.sides:
    for p in f.planes: pts.add((round(p.x,1),round(p.y,1)))
  d.rectangle([P(lo.x,hi.y),P(hi.x,lo.y)],outline=col)
for s in v.brushes:draw(s,(0,0,0))
for e in v.entities:
  for s in e.solids:draw(s,(0,110,255))
  if e['classname'].startswith('prop_') and 'origin' in e:
    o=[float(c) for c in e['origin'].split()]
    if x0<o[0]<x1 and y0<o[1]<y1 and zlo<o[2]<zhi:
      p=P(o[0],o[1]);d.ellipse([p[0]-3,p[1]-3,p[0]+3,p[1]+3],outline=(0,160,0))
tl=json.load(open(os.path.expanduser('~/mnt/outputs/Corehub-Intro/intro-timeline.json')))
wk=tl['wakeCameraOverride']['knots']
def at(t):
  for a,b in zip(wk,wk[1:]):
    if a['time']<=t<=b['time']:
      f=(t-a['time'])/(b['time']-a['time']);return [u+(w-u)*f for u,w in zip(a['eye'],b['eye'])],[u+(w-u)*f for u,w in zip(a['referenceAngles'],b['referenceAngles'])]
for t in cams:
  e,a=at(t);p=P(e[0],e[1]);yaw=math.radians(a[1])
  for dyaw in (-45,0,45):
    yy=yaw+math.radians(dyaw);q=P(e[0]+600*math.cos(yy),e[1]+600*math.sin(yy))
    d.line([p,q],fill=(255,0,0) if dyaw==0 else (255,160,160),width=1)
  d.text((p[0]+4,p[1]),f'{t:g}',fill=(200,0,0))
im.save(out)
print(W,H)
