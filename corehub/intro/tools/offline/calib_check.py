import pickle, numpy as np, collections, sys
from render import srgb_encode
D=pickle.load(open(sys.argv[1],'rb'))
names=D['names']; found=D['found']; unlit=D['unlit']; color=D['color']; alpha=D['alpha']
E=lambda x: np.round(srgb_encode(x)*255).astype(int)
acc=collections.defaultdict(list)
BAD={70.5,115.5}
for fr in D['frames']:
    if fr['black']>0 or fr['fades']['r10_veil_fade']>0 or fr['fades']['r10_red_fade']>0 or fr['t'] in BAD: continue
    m0=fr['L_mat'][0]; a0=fr['L_alpha'][0]; f0=fr['L_fac'][0]; obs=fr['obs']
    ok=(m0>=0)&(a0>=0.999)
    for mi in np.unique(m0[ok]):
        if not (found[mi] and unlit[mi]): continue
        sel=ok&(m0==mi)
        if sel.sum()<30: continue
        pred=np.clip(color[mi]*f0[sel],0,1)
        acc[mi].append((fr['t'],int(sel.sum()),np.median(pred,axis=0),np.median(obs[sel],axis=0)))
print('known unlit opaque first-layer materials: predicted vs observed (sRGB 0-255)')
for mi,lst in sorted(acc.items(), key=lambda kv:-sum(x[1] for x in kv[1])):
    for t,n,p,o in lst:
        print(f'{names[mi]:48s} t={t:6.1f} n={n:6d}  pred {E(p)}  obs {E(o)}')
