# usage: refsheet.py t0 t1 step cols out.jpg [w]
import sys,os
from PIL import Image,ImageDraw
R=os.path.expanduser('~/mnt/revision9/r10/ref/stills')
t0,t1,st=float(sys.argv[1]),float(sys.argv[2]),float(sys.argv[3]);cols=int(sys.argv[4]);out=sys.argv[5]
w=int(sys.argv[6]) if len(sys.argv)>6 else 320;h=w*9//16
ts=[];t=t0
while t<=t1+1e-6:ts.append(round(t,2));t+=st
rows=(len(ts)+cols-1)//cols
im=Image.new('RGB',(cols*(w+2),rows*(h+2)));d=ImageDraw.Draw(im)
for k,t in enumerate(ts):
    f=f'{R}/r{round(t*2):04d}.jpg'
    x=(k%cols)*(w+2);y=(k//cols)*(h+2)
    if os.path.exists(f):im.paste(Image.open(f).resize((w,h)),(x,y))
    d.text((x+3,y+2),f'{t:g}',fill=(255,255,0))
im.save(out,quality=85)
