"""Estimate colours of missing opaque materials from the published review frames.
For each pixel the surface stack is walked through known layers (blending in linear light); the first unknown
layer is taken as opaque and its colour solved from the observed pixel.
usage: calib_fit.py data.pkl [min_count]  -> prints estimates and writes fit_<data>.json"""
import pickle, numpy as np, sys, json, collections
from render import srgb_encode
D=pickle.load(open(sys.argv[1],'rb'))
MINC=int(sys.argv[2]) if len(sys.argv)>2 else 40
names=D['names']; found=D['found']; unlit=D['unlit']; color=D['color']; alpha=D['alpha']
W,H=320,200
BAD={70.5,115.5}
samples=collections.defaultdict(list); frames_of=collections.defaultdict(set)
for fr in D['frames']:
    if fr['black']>0 or fr['fades']['r10_veil_fade']>0 or fr['fades']['r10_red_fade']>0 or fr['t'] in BAD: continue
    LM=fr['L_mat']; LA=fr['L_alpha']; LF=fr['L_fac']; obs=fr['obs'].astype(np.float64)
    n=obs.shape[0]
    T=np.ones(n); acc=np.zeros((n,3)); alive=np.ones(n,bool); target=np.full(n,-1); tfac=np.zeros((n,3)); tT=np.zeros(n)
    for k in range(LM.shape[0]):
        m=LM[k]; has=(m>=0)&alive
        kn=has&found[np.clip(m,0,None)]&unlit[np.clip(m,0,None)]
        un=has&~found[np.clip(m,0,None)]
        lit=has&found[np.clip(m,0,None)]&~unlit[np.clip(m,0,None)]
        # unknown layer: record as target, stop
        target[un]=m[un]; tfac[un]=LF[k][un]; tT[un]=T[un]; alive[un]=False
        alive[lit]=False
        a=LA[k].astype(np.float64)
        c=color[np.clip(m,0,None)]*LF[k]
        acc[kn]+=(T[kn]*a[kn])[:,None]*c[kn]; T[kn]*=(1-a[kn])
        alive&=~(kn&(a>=0.999))
        alive&=has|~alive
    tg=target.reshape(H,W)
    same=np.ones((H,W),bool)
    same[1:,:]&=tg[1:,:]==tg[:-1,:]; same[:-1,:]&=tg[:-1,:]==tg[1:,:]; same[:,1:]&=tg[:,1:]==tg[:,:-1]; same[:,:-1]&=tg[:,:-1]==tg[:,1:]
    ok=(target>=0)&same.reshape(-1)&(tT>0.25)&(tfac.min(axis=1)>0.02)
    est=(obs-acc)/(tT[:,None]*tfac+1e-9)
    for mi in np.unique(target[ok]):
        s=ok&(target==mi)
        samples[mi].append(est[s]); frames_of[mi].add(fr['t'])
out={}
rows=[]
for mi,lst in samples.items():
    e=np.concatenate(lst); n=len(e)
    med=np.median(e,axis=0); mad=np.median(np.abs(e-med),axis=0)
    rows.append((n,names[mi],med,mad,sorted(frames_of[mi])))
    if n>=MINC:
        col=np.power(np.clip(med,0,4),1/2.2)
        out[names[mi]]={'color':[round(float(x),4) for x in col],'n':int(n),'mad':[round(float(x),4) for x in mad],'frames':sorted(frames_of[mi])}
E=lambda x: np.round(srgb_encode(np.clip(x,0,1))*255).astype(int)
for n,name,med,mad,fs in sorted(rows,key=lambda r:-r[0]):
    flag='' if n>=MINC else '  (too few)'
    print(f'{n:7d} {name:56s} sRGB {E(med)} +-{E(np.clip(med+mad,0,1))-E(med)} color {np.round(np.power(np.clip(med,0,4),1/2.2),3)} t={fs[:6]}{flag}')
json.dump(out,open('fit_'+sys.argv[1].replace('.pkl','.json'),'w'),indent=0)
unk=[n for i,n in enumerate(names) if not found[i]]
print(len(out),'estimated of',len(unk),'missing; never sampled:',len([n for n in unk if n not in {r[1] for r in rows}]))
