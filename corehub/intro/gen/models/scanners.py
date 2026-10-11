"""Transfer shaft and inlet (71.3-75.5 s and 74-84 s): the irises at (4800, 0, 950) and (4800, 0, 286).

STARTER (first versions, to be refined against the video by this scene's pass): the opening iris' petal and ring
design at the size the director's petal travel implies (54 units along the diagonal)."""
import math
from lib.gen import Mesh, V, mat, ramp, save, rot_x, rot_y, rot_z
from models import iris as I

PETAL_SCALE = 64.0 / I.PETAL_R        # petal radius 64


def quarter_x(scale=PETAL_SCALE):
    """axis +X, petal in the +Y+Z quadrant, decorated side toward -X (as the opening iris' petal)"""
    return I.quarter().transform(scale=scale)


def ring_frame(r0=66.0, r1=78.0, depth=10.0, both=True):
    """grey ring round an iris, axis X, faces at X = 0 (toward -X) and X = depth (toward +X)"""
    m = Mesh()
    I.ring_x(m, 0.0, r0, r1, 'irisf_ring')
    I.ring_x(m, 0.0, r0 - 2.4, r0, 'irisf_ring_in')
    I.wall_x(m, 0.0, r0 - 2.4, depth, r0 - 2.4, 'irisf_ring_in', inward=True)
    I.wall_x(m, 0.0, r1, depth, r1, 'irisf_black', inward=False)
    if both:
        I.ring_x(m, depth, r0 - 2.4, r1, 'irisf_ring', down=False)
    return m


def build():
    I.materials()
    save(quarter_x(), 'iris_quarter')
    save(ring_frame(), 'iris_frame')
    save(ring_frame(), 'transfer_refined_iris_frame')
