# usage: sheets.py PREFIX [t0 t1 step] -> r10/sheets/PREFIX/NN.jpg  (ref | map pairs, 2 cols x 4 rows)
import sys,os
from PIL import Image,ImageDraw
R=os.path.expanduser('~/mnt/revision9/r10')
P=sys.argv[1]
t0,t1,st=(float(a) for a in sys.argv[2:5]) if len(sys.argv)>4 else (0,134,1)
out=f'{R}/sheets/'+(sys.argv[5] if len(sys.argv)>5 else P);os.makedirs(out,exist_ok=True)
times=[];t=t0
while t<=t1+1e-6:times.append(round(t,2));t+=st
w,h=480,270;cols=2;rows=4;per=cols*rows
def still(t):
    s=int(t);tag='a' if abs(t-s)<0.25 else 'b'
    return f'{R}/stills/{P}/{tag}{s:03d}.jpg', f'{R}/ref/stills2/r{round(t*2):04d}.jpg'
for g in range(0,len(times),per):
    grp=times[g:g+per];im=Image.new('RGB',(cols*(2*w+6),rows*(h+14)),(0,0,0));d=ImageDraw.Draw(im)
    for k,t in enumerate(grp):
        m,r=still(t);x=(k%cols)*(2*w+6);y=(k//cols)*(h+14)
        for j,f in enumerate((r,m)):
            if os.path.exists(f):im.paste(Image.open(f).convert('RGB').resize((w,h)),(x+j*w,y+14))
        d.text((x+3,y+1),f'{t:g}s   original | rebuild',fill=(255,255,0))
    im.save(f'{out}/{g//per:02d}_{grp[0]:g}-{grp[-1]:g}.jpg',quality=86)
print(len(times),'pairs')
