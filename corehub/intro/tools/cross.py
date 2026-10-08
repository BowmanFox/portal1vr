import os,sys
from srctools import VMF,Vec
v=VMF.parse(os.path.expanduser('~/mnt/outputs/Corehub-Intro/corehub_intro.vmf'))
xs=[float(a) for a in sys.argv[1:]]
items=[]
for s in v.brushes: items.append(('W',s,None))
for e in v.entities:
    for s in e.solids: items.append((e['classname'][:10],s,e))
props=[e for e in v.entities if e['classname'].startswith('prop_')]
for X in xs:
    print('==== x=',X)
    for kind,s,e in items:
        lo,hi=s.get_bbox()
        if lo.x<X<hi.x and lo.y>-1000 and hi.y<1130 and lo.z>-760 and hi.z<2890:
            print(' %-10s y %6.0f..%6.0f z %6.0f..%6.0f x %6.0f..%6.0f %s %s'%(kind,lo.y,hi.y,lo.z,hi.z,lo.x,hi.x,sorted({f.mat.lower() for f in s.sides})[:2],(e['targetname'] if e else '')))
    for e in props:
        o=Vec.from_str(e['origin'])
        if abs(o.x-X)<120: print('  prop',e['model'].split('/')[-1],o,e['angles'] if 'angles' in e else '')
