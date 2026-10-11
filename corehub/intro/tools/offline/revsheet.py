"""helpers to cut the original|rebuild pairs out of the published review sheets (every 3 s from 1.5 s)"""
from PIL import Image
import os
REV='/home/claude/bowmanfox/portal1vr/corehub/intro/review'
W,H=320,200
_sheets={}
def cell(t):
    k=round((t-1.5)/3); assert abs(1.5+3*k-t)<1e-6, t
    g=k//16; j=k%16
    if g not in _sheets: _sheets[g]=Image.open(f'{REV}/overview_{g+1}.jpg').convert('RGB')
    im=_sheets[g]; x=(j%4)*(2*W+4); y=(j//4)*(H+12)+12
    return im.crop((x,y,x+W,y+H)), im.crop((x+W,y,x+2*W,y+H))
