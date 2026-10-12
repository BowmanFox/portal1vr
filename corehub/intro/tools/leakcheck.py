"""Rough leak check of a VMF: every point entity must be boxed in by brushes in all six axis directions
(brush bounding boxes; exact for the axis-aligned shells of the rebuilt cells). usage: leakcheck.py map.vmf"""
import re, sys
import numpy as np
txt = open(sys.argv[1]).read()
# brush AABBs
boxes = []
for m in re.finditer(r'solid\s*\{(.*?)\n\t\}', txt, re.S):
    pts = re.findall(r'"plane" "\(([-\d.e]+) ([-\d.e]+) ([-\d.e]+)\) \(([-\d.e]+) ([-\d.e]+) ([-\d.e]+)\) \(([-\d.e]+) ([-\d.e]+) ([-\d.e]+)\)"', m.group(1))
    if not pts: continue
    P = np.array(pts, dtype=float).reshape(-1, 3)
    boxes.append((P.min(axis=0), P.max(axis=0)))
LO = np.array([b[0] for b in boxes]); HI = np.array([b[1] for b in boxes])
bad = []
for e in txt.split('\nentity\n')[1:]:
    m = re.search(r'"origin" "([-\d.e]+) ([-\d.e]+) ([-\d.e]+)"', e)
    if not m or '\tsolid\n' in e: continue
    p = np.array([float(x) for x in m.groups()])
    esc = []
    for ax in range(3):
        o = [a for a in range(3) if a != ax]
        inline = (LO[:, o[0]] <= p[o[0]]) & (HI[:, o[0]] >= p[o[0]]) & (LO[:, o[1]] <= p[o[1]]) & (HI[:, o[1]] >= p[o[1]])
        if not (inline & (HI[:, ax] >= p[ax])).any(): esc.append('+' + 'xyz'[ax])
        if not (inline & (LO[:, ax] <= p[ax])).any(): esc.append('-' + 'xyz'[ax])
    if esc:
        cls = re.search(r'"classname" "([^"]*)"', e).group(1); nm = re.search(r'"targetname" "([^"]*)"', e)
        bad.append((cls, nm.group(1) if nm else '', p.tolist(), esc))
print(len(boxes), 'brushes;', len(bad), 'point entities not boxed in')
for b in bad[:40]: print('  ', b)
