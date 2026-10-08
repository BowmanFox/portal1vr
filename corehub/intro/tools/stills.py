# usage: stills.py PREFIX  -> rebuild a/b stills (t=s and s+0.5) from the movie frames
import os,sys,shutil
R=os.path.expanduser('~/mnt/revision9');P=sys.argv[1]
m=f'{R}/runtime/game/corehub_intro/movies/{P}';o=f'{R}/r10/stills/{P}';os.makedirs(o,exist_ok=True)
n=len([f for f in os.listdir(m) if f.endswith('.jpg')])
for s in range(135):
  for tag,t in (('a',s),('b',s+0.5)):
    i=round(t*60)
    if i<n:shutil.copyfile(f'{m}/f{i:04d}.jpg',f'{o}/{tag}{s:03d}.jpg')
print(P,n)
