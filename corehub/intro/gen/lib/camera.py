"""Camera maths shared by the scene modules (Source QAngles, the film's 16:10 frame at 640x400 pixels)."""
import math
import numpy as np


def basis(pitch, yaw, roll):
    """forward, right, up"""
    sp, cp = math.sin(math.radians(pitch)), math.cos(math.radians(pitch))
    sy, cy = math.sin(math.radians(yaw)), math.cos(math.radians(yaw))
    sr, cr = math.sin(math.radians(roll)), math.cos(math.radians(roll))
    f = np.array([cp * cy, cp * sy, -sp])
    left = np.array([sr * sp * cy - cr * sy, sr * sp * sy + cr * cy, sr * cp])
    up = np.array([cr * sp * cy + sr * sy, cr * sp * sy - sr * cy, cr * cp])
    return f, -left, up


def scales(fov):
    t = math.tan(math.radians(fov) / 2.0)
    return t * 1.2, t * 0.75           # tan of the half angles (horizontal, vertical) of the 16:10 frame


def ray(eye, ang, fov, px, py, w=640, h=400):
    f, r, u = basis(*ang); th, tv = scales(fov)
    d = f + r * ((px / w) * 2 - 1) * th + u * (1 - (py / h) * 2) * tv
    return np.asarray(eye, dtype=float), d / np.linalg.norm(d)


def project(eye, ang, fov, P, w=640, h=400):
    f, r, u = basis(*ang); th, tv = scales(fov)
    Q = np.atleast_2d(np.asarray(P, dtype=float)) - np.asarray(eye, dtype=float)
    d = Q @ f
    return np.c_[((Q @ r) / d / th + 1) * w / 2, (1 - (Q @ u) / d / tv) * h / 2, d]
