"""Shared tube parts for the rebuilt ride (true film scale; see lib/tube.py and tools/offline/ride.py).

rail_sweep(): the four square rails swept along a measured path (used by lib.tube.add_bend_rails, which saves one
model per bend). Collars: models/iris.py's p9_ascent_collar_* (light band radius 61.06, axis = model +Z)."""
import math
import numpy as np
from lib.gen import Mesh, V, mat, save

RAIL = 'r11_rail'


def materials():
    mat(RAIL, (0.035, 0.035, 0.04))


def rail_sweep(P, U, W, rho=34.0, width=1.8, material=RAIL):
    """four square rails (sides `width`, faces along U and W) at distance rho from the polyline P on the diagonals of
    the frame (U, W); P, U, W: [k,3] (model coordinates)"""
    m = Mesh(); h = width / 2.0
    P = np.asarray(P, dtype=float); U = np.asarray(U, dtype=float); W = np.asarray(W, dtype=float)
    for a in (1, -1):
        for b in (1, -1):
            C = P + (a * U + b * W) * rho / math.sqrt(2.0)
            ring = [C - h * U - h * W, C + h * U - h * W, C + h * U + h * W, C - h * U + h * W]      # 4 corners per point
            for i in range(len(P) - 1):
                for j in range(4):
                    k = (j + 1) % 4
                    q = [ring[j][i], ring[j][i + 1], ring[k][i + 1], ring[k][i]]
                    out = (q[0] + q[1] + q[2] + q[3]) / 4.0 - (C[i] + C[i + 1]) / 2.0      # faces point away from the rail's centre
                    nrm = np.cross(q[1] - q[0], q[3] - q[0])
                    if nrm @ out < 0: q = q[::-1]
                    m.quad(material, *[V(*p) for p in q])
    return m


def build_collar(scale=1.0, name=None):
    """the ascent collar (models/iris.py, light band radius 61.06, axis = model +Z) at another scale, for shots built
    smaller than the film (Ride(..., unit=scale)). -> model path for lib.tube.add_collars(model=...)"""
    from models import iris
    from lib.gen import rot_y
    iris.materials()
    name = name or 'r11_collar_s%03d' % int(round(scale * 100))
    save(iris.collar(Mesh(), 0.0).transform(R=rot_y(-90), scale=scale), name)
    return 'models/corehub_intro/%s.mdl' % name


def build():
    materials()
