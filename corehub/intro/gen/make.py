#!/usr/bin/env python3
"""Builds a test version of the intro from the r10dm base plus the scene modules in gen/scenes.
usage: make.py NAME [--scenes a,b] [--models a,b] [--no-models] [--no-sim] [--range t0,t1]
  --scenes: only these scene modules (default: all in gen/scenes); --models: only these generators (default: all)
  --range: simulate the director only for these seconds of the film (faster; the preview then knows no other times)
  -> out/models-src, out/materials (all model generators)
     out/build/corehub_r10NAME.vmf, out/build/director_r10NAME.nut   (test run prefix r10m_NAME)
     offline run folder /home/claude/offline/run_NAME (map.vmf, director.nut, state.jsonl) for the preview tools"""
import argparse, importlib, os, shutil, subprocess, sys, time
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from lib import gen, vmfedit
from lib.director import Director, lint
ap = argparse.ArgumentParser()
ap.add_argument('name'); ap.add_argument('--scenes'); ap.add_argument('--models'); ap.add_argument('--no-models', action='store_true'); ap.add_argument('--no-sim', action='store_true'); ap.add_argument('--range')
a = ap.parse_args()
ORDER = ['opening', 'iris', 'rust', 'pod', 'cube', 'tower', 'turret', 'scanners', 'sludge', 'factory', 'lab', 'incinerator', 'capsule']
have = sorted(f[:-3] for f in os.listdir(os.path.join(HERE, 'scenes')) if f.endswith('.py') and not f.startswith('_'))
scenes = a.scenes.split(',') if a.scenes else [s for s in ORDER if s in have] + [s for s in have if s not in ORDER]
t0 = time.time()
if not a.no_models:
    groups = a.models.split(',') if a.models else sorted(f[:-3] for f in os.listdir(os.path.join(HERE, 'models')) if f.endswith('.py') and not f.startswith('_'))
    for g in groups:
        importlib.import_module('models.' + g).build()
    print('models', len(gen._models), 'materials', gen.write_materials())
v = vmfedit.load(os.path.join(HERE, 'base', 'corehub_r10dm.vmf'))
d = Director(open(os.path.join(HERE, 'base', 'director_r10dm.nut')).read())
for s in scenes:
    importlib.import_module('scenes.' + s).apply(v, d)
    print('scene', s, 'applied')
gen.write_materials()             # scenes may build models of their own (e.g. rail bends along a measured path)
out = os.path.join(HERE, 'out', 'build'); os.makedirs(out, exist_ok=True)
vmf_path = os.path.join(out, 'corehub_r10%s.vmf' % a.name); nut_path = os.path.join(out, 'director_r10%s.nut' % a.name)
vmfedit.save(v, vmf_path)
text = d.render()
bad = lint(text)
assert not bad, bad[:5]
open(nut_path, 'w').write(text)
print('wrote', vmf_path, os.path.getsize(vmf_path), nut_path, len(text), 'lint ok  %.1fs' % (time.time() - t0))
if not a.no_sim:
    run = '/home/claude/offline/run_' + a.name
    os.makedirs(run, exist_ok=True)
    subprocess.run([sys.executable, '/home/claude/offline/make_sim_inputs.py', vmf_path, nut_path, run] + ([x for x in a.range.split(',')] if a.range else ['0', '134.4']) + ['0.0166666666667'], check=True, stdout=subprocess.DEVNULL)
    mv = os.path.join(run, 'map.vmf')          # keep the old file (and the preview's scene cache) when the map did not change
    if not os.path.exists(mv) or open(mv, 'rb').read() != open(vmf_path, 'rb').read(): shutil.copyfile(vmf_path, mv)
    with open(os.path.join(run, 'state.jsonl.tmp'), 'w') as f:
        r = subprocess.run(['/home/claude/squirrel/bin/sq', 'sim_run.nut'], cwd=run, stdout=f, stderr=subprocess.PIPE, text=True)
    if r.returncode != 0 or os.path.getsize(os.path.join(run, 'state.jsonl.tmp')) < 1000:
        print('SIM FAILED', r.stderr[-800:]); sys.exit(2)
    os.replace(os.path.join(run, 'state.jsonl.tmp'), os.path.join(run, 'state.jsonl'))
    print('sim ok ->', run, ' %.1fs' % (time.time() - t0))
