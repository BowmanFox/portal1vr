#!/usr/bin/env python3
"""Runs every model generator in gen/models (or the ones named on the command line) and writes gen/out/.
usage: build.py [group ...]      e.g.  build.py iris opening"""
import importlib, os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from lib import gen
groups = sys.argv[1:] or sorted(f[:-3] for f in os.listdir(os.path.join(HERE, 'models')) if f.endswith('.py') and not f.startswith('_'))
for g in groups:
    n0 = len(gen._models)
    importlib.import_module('models.' + g).build()
    print('%-14s %d models' % (g, len(gen._models) - n0))
print('materials', gen.write_materials(), '->', gen.MATS_OUT)
