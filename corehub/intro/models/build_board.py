"""r10 custom model: the flat white scanner boards seen on the transfer-shaft arms (75.5-79.5 s).

Same mount frame as scanner_arm (mount at x=0, head toward -x), so it is a drop-in model swap.
"""
import sys, os, math
sys.path.insert(0, os.path.expanduser('~/mnt/revision9'))
from mesh_source import Mesh
from srctools import Vec
m = Mesh()
m.box((-23, -7, -4), (0, 7, 4), 'shell')                 # mount block (as scanner_arm)
m.box((-70, -12, -2.2), (-14, 12, 2.2), 'shell')          # the flat board
for x0 in (-64, -52, -40, -28):                           # grey circuit details on the face
    m.box((x0, -7, 2.2), (x0 + 6, 7, 2.6), 'metal')
m.box((-68, -10.5, -2.8), (-16, -9.5, -2.2), 'dark')
m.box((-68, 9.5, -2.8), (-16, 10.5, -2.2), 'dark')
m.box((-80, -6, -7), (-70, 6, 3), 'metal')                # camera block at the tip
def lathe_part(profile, material, off):
    p = Mesh(); p.lathe(profile, material, 32)
    for mat, pts, ns in p.tris:
        m.tri(mat, *(Vec(v.z, v.y, -v.x) + Vec(*off) for v in pts))
lathe_part([(-4, 0), (-4, 3.4), (2, 3.4), (2, 0)], 'dark', (-82, 0, -2))
lathe_part([(2.1, 0), (2.1, 2.2), (2.3, 2.2), (2.3, 0)], 'red', (-82, 0, -2))
qc = m.save('scanner_board', os.path.dirname(os.path.abspath(__file__)))
print(qc, len(m.tris))
