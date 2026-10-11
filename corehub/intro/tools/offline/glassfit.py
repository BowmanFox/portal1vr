"""Fit colour and opacity of a translucent material from pixels where a known opaque surface shows through exactly
one layer of it (linear light): obs = a*G + (1-a)*B.   usage: glassfit.py data.pkl material [flat]"""
import pickle, numpy as np, sys
from render import srgb_encode
D=pickle.load(open(sys.argv[1],'rb'))
names=D['names']; found=D['found']; unlit=D['unlit']; color=D['color']; alpha=D['alpha']; hastex=D['hastex']
gname=sys.argv[2]; gi=names.index(gname); flat=len(sys.argv)>3
E=lambda x: np.round(srgb_encode(x)*255).astype(int)
X=[];Y=[];info=[];Mid=[]
BAD={70.5,115.5}
known=found&unlit
if flat: known&=~hastex
for fr in D['frames']:
    if fr['black']>0 or fr['fades']['r10_veil_fade']>0 or fr['fades']['r10_red_fade']>0 or fr['t'] in BAD: continue
    m0,m1=fr['L_mat'][0],fr['L_mat'][1]; a1=fr['L_alpha'][1]; f1=fr['L_fac'][1]; obs=fr['obs']
    ok=(m0==gi)&(m1>=0)&(a1>=0.999)&known[np.clip(m1,0,None)]
    if ok.sum()<20: continue
    pred=np.clip(color[m1[ok]]*f1[ok],0,1)
    X.append(pred); Y.append(obs[ok]); Mid.append(m1[ok]); info.append((fr['t'],int(ok.sum())))
X=np.concatenate(X); Y=np.concatenate(Y); Mid=np.concatenate(Mid)
print(gname,'pixels',len(X),info)
for c in range(3):
    A=np.stack([X[:,c],np.ones(len(X))],1); sol,res,_,_=np.linalg.lstsq(A,Y[:,c],rcond=None)
    s,k=sol; a=1-s; G=k/a if a>1e-3 else float('nan')
    print(f' ch{c}: slope {s:.3f} intercept(lin) {k:.4f} -> alpha {a:.3f}, glass colour sRGB {float(srgb_encode(max(G,0)))*255:.0f} ($color {max(G,0)**(1/2.2):.3f})')
for mi in np.unique(Mid):
    s=Mid==mi
    if s.sum()>40: print(f'  behind {names[mi]:44s} n={s.sum():6d} pred {E(np.median(X[s],0))} obs {E(np.median(Y[s],0))}')
