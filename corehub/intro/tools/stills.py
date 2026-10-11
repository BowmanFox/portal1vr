# usage: stills.py PREFIX  -> rebuild a/b stills (t=s and s+0.5) from the movie frames
import os as _os
_ROOT = next(p for p in (_os.environ.get('COREHUB_ROOT') or '', _os.path.expanduser('~/mnt/Games/revision9'), _os.path.expanduser('~/Games/revision9'), _os.path.expanduser('~/mnt/revision9')) if p and _os.path.isdir(p))   # PC, Mac VM or native Mac
import os,sys,shutil
R=_ROOT;P=sys.argv[1]
m=f'{R}/runtime/game/corehub_intro/movies/{P}';o=f'{R}/r10/stills/{P}';os.makedirs(o,exist_ok=True)
n=len([f for f in os.listdir(m) if f.endswith('.jpg')])
for s in range(135):
  for tag,t in (('a',s),('b',s+0.5)):
    i=round(t*60)
    if i<n:shutil.copyfile(f'{m}/f{i:04d}.jpg',f'{o}/{tag}{s:03d}.jpg')
print(P,n)
