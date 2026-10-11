"""Incinerator shaft and final probes (110-118.4 s).

STARTER (first versions, to be refined against the video by this scene's pass): the two shaft irises and the wall
iris' frame, in the opening iris' design."""
import math
from lib.gen import Mesh, V, mat, ramp, save, rot_x, rot_y, rot_z
from models import iris as I
from models import scanners as S


def build():
    I.materials()
    # the shaft irises lie flat: axis +Z, petal in the +X+Y quadrant, decorated side up (seen by the descending camera).
    # rot_y(90): (x, y, z) -> (z, y, -x), so the +Y+Z sector becomes +X+Y and the -X side faces +Z
    save(S.quarter_x().transform(R=rot_y(90)), 'p9_end_shaft_iris_quarter')
    save(S.ring_frame(), 'ending_iris_frame')
