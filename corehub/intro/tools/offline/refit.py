"""refit.py data.pkl material base [base2 ...] : $color that makes <base> match the published frames for a lost brush material"""
import pickle, numpy as np, sys, json
from render import MaterialLib, srgb_encode
D=pickle.load(open(sys.argv[1],'rb')); target=sys.argv[2]
names=D['names']; found=D['found']; unlit=D['unlit']; color=D['color']
ti=names.index(target)
ml=MaterialLib(['/home/claude/data/texpack/portal2','/home/claude/data/texpack/portal2_tempcontent','/home/claude/data/texpack/portal'])
BAD={70.5,115.5,112.5}
E=[];U=[];TT=[]
for fr in D['frames']:
    if fr['black']>0 or fr['fades']['r10_veil_fade']>0 or fr['fades']['r10_red_fade']>0 or fr['t'] in BAD: continue
    LM=fr['L_mat']; LA=fr['L_alpha']; LF=fr['L_fac']; LU=fr['L_uv']; obs=fr['obs'].astype(np.float64)
    n=obs.shape[0]; T=np.ones(n); acc=np.zeros((n,3)); alive=np.ones(n,bool)
    for k in range(LM.shape[0]):
        m=LM[k]; has=(m>=0)&alive; mc=np.clip(m,0,None)
        hit=has&(m==ti)&(T>0.3)
        if hit.any():
            E.append(((obs-acc)/(T[:,None]+1e-9))[hit]); U.append(LU[k][hit]); TT.append(np.full(hit.sum(),fr['t']))
        kn=has&found[mc]&unlit[mc]
        a=LA[k].astype(np.float64); c=color[mc]*LF[k]
        acc[kn]+=(T[kn]*a[kn])[:,None]*c[kn]; T[kn]*=(1-a[kn])
        alive&=kn&(a<0.999)
E=np.concatenate(E); U=np.concatenate(U); TT=np.concatenate(TT)
print(target,'samples',len(E),'by frame',{float(t):int((TT==t).sum()) for t in np.unique(TT)})
for base in sys.argv[3:]:
    t=ml.texture(base)
    if t is None: print('  no texture',base); continue
    tex,(fw,fh)=t; h,w=tex.shape[:2]
    ix=np.floor((U[:,0]/fw%1.0)*w).astype(int)%w; iy=np.floor((U[:,1]/fh%1.0)*h).astype(int)%h
    c=tex[iy,ix,:3].astype(np.float64)
    ratio=np.median(E,axis=0)/np.median(c,axis=0)       # robust: ratio of medians
    ratio2=E.mean(axis=0)/c.mean(axis=0)
    print(f'  {base:40s} $color (ratio of medians) {np.round(np.power(np.clip(ratio,0,9),1/2.2),3)}  (ratio of means) {np.round(np.power(np.clip(ratio2,0,9),1/2.2),3)}  tex avg sRGB {np.round(srgb_encode(c.mean(0))*255).astype(int)} obs avg sRGB {np.round(srgb_encode(np.clip(E.mean(0),0,1))*255).astype(int)}')
