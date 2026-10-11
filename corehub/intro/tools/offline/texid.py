"""Which stock texture did a lost brush material use? Compares the pattern seen in the published review frames
(by texture coordinate) with every candidate stock texture.   usage: texid.py data.pkl material [topN]"""
import pickle, numpy as np, sys, json, os, glob, collections
from PIL import Image
from render import srgb_decode, srgb_encode
D=pickle.load(open(sys.argv[1],'rb'))
target=sys.argv[2]; TOP=int(sys.argv[3]) if len(sys.argv)>3 else 6
names=D['names']; found=D['found']; unlit=D['unlit']; color=D['color']
ti=names.index(target)
BAD={70.5,115.5}
E=[];U=[]
for fr in D['frames']:
    if fr['black']>0 or fr['fades']['r10_veil_fade']>0 or fr['fades']['r10_red_fade']>0 or fr['t'] in BAD: continue
    LM=fr['L_mat']; LA=fr['L_alpha']; LF=fr['L_fac']; LU=fr['L_uv']; obs=fr['obs'].astype(np.float64)
    n=obs.shape[0]; T=np.ones(n); acc=np.zeros((n,3)); alive=np.ones(n,bool)
    for k in range(LM.shape[0]):
        m=LM[k]; has=(m>=0)&alive; mc=np.clip(m,0,None)
        hit=has&(m==ti)
        if hit.any():
            ok=hit&(T>0.3)
            E.append(((obs-acc)/(T[:,None]*LF[k]+1e-9))[ok]); U.append(LU[k][ok])
        kn=has&found[mc]&unlit[mc]
        a=LA[k].astype(np.float64); c=color[mc]*LF[k]
        acc[kn]+=(T[kn]*a[kn])[:,None]*c[kn]; T[kn]*=(1-a[kn])
        alive&=kn&(a<0.999)
if not E: print('no samples'); sys.exit()
E=np.concatenate(E); U=np.concatenate(U)
Y=E@np.array([0.2126,0.7152,0.0722])
print(target,'samples',len(E),'mean sRGB',np.round(srgb_encode(np.clip(np.median(E,0),0,1))*255).astype(int),'luma cv %.3f'%(Y.std()/max(Y.mean(),1e-6)))
PACK='/home/claude/data/texpack'; sizes=json.load(open(PACK+'/sizes.json'))
res=[]
for game in ('portal2','portal2_tempcontent','portal'):
    for d in ('tile','concrete','plaster','metal','wood','glass','nature','dev','lights','plastic','brick','stone','building_template','props','signage'):
        for f in glob.glob(f'{PACK}/{game}/{d}/*.png'):
            b=os.path.basename(f)
            if any(s in b for s in ('_normal','height','ssbump','_ref','_exp','_mask','_bump','_spec','reflect','_n.')): continue
            key=f'{game}/{d}/{b[:-4]}.vtf'; sz=sizes.get(key)
            if not sz: continue
            im=np.asarray(Image.open(f).convert('RGB'),dtype=np.float64)/255.0; im=srgb_decode(im)
            h,w=im.shape[:2]
            ix=np.floor((U[:,0]/sz[0]%1.0)*w).astype(int)%w; iy=np.floor((U[:,1]/sz[1]%1.0)*h).astype(int)%h
            c=im[iy,ix]; yc=c@np.array([0.2126,0.7152,0.0722])
            if yc.std()<1e-6 or Y.std()<1e-6: corr=0.0
            else: corr=float(np.corrcoef(yc,Y)[0,1])
            ratio=np.median(E/(c+1e-4),axis=0)
            resid=np.median(np.abs(E-c*ratio))/max(np.median(Y),1e-6)
            res.append((corr,resid,f'{d}/{b[:-4]}',game,ratio))
res.sort(key=lambda r:-r[0])
for corr,resid,name,game,ratio in res[:TOP]:
    print(f'  corr {corr:+.3f} resid {resid:.3f}  {name:44s} ({game}) $color {np.round(np.power(np.clip(ratio,0,8),1/2.2),3)}')
flat=np.median(np.abs(E-np.median(E,0)))/max(np.median(Y),1e-6)
print(f'  flat-colour residual {flat:.3f} (lights/white002 $color {np.round(np.power(np.clip(np.median(E,0),0,8),1/2.2),3)})')
