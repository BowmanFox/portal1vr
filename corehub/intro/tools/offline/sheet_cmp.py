import sys
from PIL import Image, ImageDraw
from revsheet import cell
ts=[float(a) for a in sys.argv[2:]]
W,H=320,200
im=Image.new('RGB',(3*W+8,len(ts)*(H+14)),(0,0,0)); d=ImageDraw.Draw(im)
for k,t in enumerate(ts):
    ref,reb=cell(t); y=k*(H+14)
    im.paste(ref,(0,y+14)); im.paste(reb,(W+4,y+14))
    off=Image.open(f'/tmp/off_{t:g}.png').resize((W,H),Image.LANCZOS); im.paste(off,(2*W+8,y+14))
    d.text((3,y+1),f'{t:g}s   2009 video | published rebuild (r10dj, in game) | offline preview of r10dm',fill=(255,255,0))
im.save(sys.argv[1],quality=90); print('ok',im.size)
