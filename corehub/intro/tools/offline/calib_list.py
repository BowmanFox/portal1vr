import pickle, numpy as np, collections, sys
D=pickle.load(open(sys.argv[1] if len(sys.argv)>1 else 'calib_dj.pkl','rb'))
names=D['names']; found=D['found']
acc=collections.defaultdict(list)
BAD={70.5,115.5}
for fr in D['frames']:
    if fr['black']>0 or fr['fades']['r10_veil_fade']>0 or fr['fades']['r10_red_fade']>0 or fr['t'] in BAD: continue
    m0=fr['L_mat'][0]; obs=fr['obs']; f0=fr['L_fac'][0]
    for mi in np.unique(m0[m0>=0]):
        if found[mi]: continue
        sel=(m0==mi)
        acc[mi].append((fr['t'],obs[sel],f0[sel]))
print(len(acc),'missing materials seen as first layer;', sum(1 for i,n in enumerate(names) if not found[i]),'missing in total')
rows=[]
for mi,lst in acc.items():
    o=np.concatenate([x[1] for x in lst]); n=len(o)
    med=np.median(o,axis=0)*255; sd=o.std(axis=0)*255
    rows.append((n,names[mi],med,sd,[x[0] for x in lst]))
for n,name,med,sd,ts in sorted(rows,key=lambda r:-r[0]):
    print(f'{n:7d} {name:58s} med {np.round(med).astype(int)} sd {np.round(sd).astype(int)} t={ts[:8]}')
seen=set(names[mi] for mi in acc)
print('NEVER first-layer:', sorted(n for i,n in enumerate(names) if not found[i] and n not in seen))
