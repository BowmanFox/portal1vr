#!/usr/bin/env python3
"""usage: make_sim_inputs.py map.vmf director.nut workdir t0 t1 step  -> writes sim_ents.nut, sim_times.nut, copies director"""
import re, sys, os, shutil
vmf, nut, wd = sys.argv[1:4]; t0, t1, st = (float(a) for a in sys.argv[4:7])
os.makedirs(wd, exist_ok=True)
s = open(vmf, encoding='utf-8', errors='replace').read()
ents = re.split(r'\nentity\n\{', s)[1:]
lines = []; seen = set()
for e in ents:
    head = e.split('\n\tsolid\n')[0]
    kv = dict(re.findall(r'^\t"([^"]+)"\s+"([^"]*)"', head, re.M))
    name = kv.get('targetname')
    if not name or name in seen: continue
    seen.add(name)
    o = kv.get('origin', '0 0 0').split()
    lines.append('simEnts["%s"] <- SimEnt("%s","%s",Vector(%s,%s,%s));' % (name, name, kv.get('classname', ''), o[0], o[1], o[2]))
open(os.path.join(wd, 'sim_ents.nut'), 'w').write('\n'.join(lines) + '\n')
ts = []; t = t0
while t <= t1 + 1e-9: ts.append(round(t, 5)); t += st
open(os.path.join(wd, 'sim_times.nut'), 'w').write('simDumpTimes <- [' + ','.join('%.5f' % x for x in ts) + '];\nsimStep <- %.8f;\n' % (1 / 60))
shutil.copyfile(nut, os.path.join(wd, 'director.nut'))
here = os.path.dirname(os.path.abspath(__file__))
for f in ('sim_prelude.nut', 'sim_run.nut'): shutil.copyfile(os.path.join(here, f), os.path.join(wd, f))
print(len(lines), 'named entities;', len(ts), 'dump times')
