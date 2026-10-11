"""inventory.py x0 x1 [y0 y1] : materials used by brush faces whose polygons fall in a region of the r10dj map, with areas"""
import pickle, sys, json, numpy as np, collections
sc=pickle.load(open('scene_dj.pkl','rb'))
V,UV,M,N,T,C=sc.static_arrays()
x0,x1=float(sys.argv[1]),float(sys.argv[2])
y0,y1=(float(sys.argv[3]),float(sys.argv[4])) if len(sys.argv)>4 else (-1e9,1e9)
cen=V.mean(axis=1)
sel=(cen[:,0]>=x0)&(cen[:,0]<=x1)&(cen[:,1]>=y0)&(cen[:,1]<=y1)
area=0.5*np.linalg.norm(np.cross(V[:,1]-V[:,0],V[:,2]-V[:,0]),axis=1)
fit=json.load(open('fit_calib_ov1.json'))
acc=collections.Counter(); cnt=collections.Counter(); zr={}
for m,a,c in zip(M[sel],area[sel],cen[sel]):
    acc[m]+=a; cnt[m]+=1
    z=zr.setdefault(m,[1e9,-1e9]); z[0]=min(z[0],c[2]); z[1]=max(z[1],c[2])
for m,a in acc.most_common():
    n=sc.mat_names[m]; f=fit.get(n)
    print(f'{a:12.0f} u2  {cnt[m]:6d} tris  z {zr[m][0]:7.0f}..{zr[m][1]:7.0f}  {n:52s}', ('fit %s n=%d'%(f['color'],f['n'])) if f else '')
