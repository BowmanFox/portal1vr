"""Factory and lab (96.6-109.6 s): own models for the rebuilt shots (prefix r11_fl; scenes/factorylab.py places them).

The factory's collars, arms, beams, forklifts and panels of the old build (p9_factory_collar_v4, p9f5_*) are lost;
these are new generator models made to what the film shows (colours sampled from the frames, gamma space):
  r11_fl_fcollar    factory tube collar: 16-sided, white light band (r 40..61.06) on the front (z = 0, facing -Z),
                    orange-brown housing r 82, 30 deep, open behind; axis = model +Z
  r11_fl_arm / _arm_l / _arm_g   hanging robot arm (yellow-orange; 1.5x; grey 1.3x), hangs down from z = 0
  r11_fl_floorarm   robot arm lying on the conveyor
  r11_fl_box / _box_l   white carton on the +y conveyor shelf (1.6x)
  r11_fl_lcollar    lab tube collar: dark ring r 70..88 with an orange band r 61..70, 30 deep, axis +Z
  r11_fl_cube       the cube riding ahead of the camera in lab 1 (40 across)
  r11_fl_pedestal   lab 1 cube pedestal: grey cylinder, eight orange petals r 28..150
  r11_fl_sphere     lab 1 hanging sphere (about 170 across, red eye looking +X)
  r11_fl_ringstack  lab 2 glass tube stub: brown collars inside every 80, orange ring at the top (z 470..520), legs
  r11_fl_turret     small turret (kept for reference, not placed)"""
import math
import numpy as np
from lib.gen import Mesh, V, mat, ramp, save, rot_x, rot_y, rot_z

N16 = 16


def materials():
    mat('r11_fl_cwhite', (0.80, 0.78, 0.75))
    mat('r11_fl_cgrey', (0.36, 0.35, 0.34))
    mat('r11_fl_cinner', (0.22, 0.21, 0.20))
    ramp('r11_fl_corange', (0.62, 0.36, 0.17), factors=(0.35, 0.55, 0.78, 1.0))
    ramp('r11_fl_arm', (0.70, 0.50, 0.16), factors=(0.25, 0.45, 0.7, 1.0))
    ramp('r11_fl_armg', (0.58, 0.56, 0.53), factors=(0.25, 0.45, 0.7, 1.0))
    ramp('r11_fl_mach', (0.52, 0.51, 0.49), factors=(0.3, 0.5, 0.75, 1.0))
    mat('r11_fl_armdark', (0.10, 0.07, 0.03))
    ramp('r11_fl_box', (0.82, 0.82, 0.80), factors=(0.45, 0.65, 0.85, 1.0))
    # lab
    mat('r11_fl_lring', (0.10, 0.10, 0.10))
    mat('r11_fl_lglass', (0.09, 0.09, 0.10), alpha=0.6, translucent=True)
    mat('r11_fl_lband', (0.42, 0.28, 0.20), alpha=0.8, translucent=True)
    mat('r11_fl_glass2', (0.22, 0.22, 0.23))
    ramp('r11_fl_lorange', (0.75, 0.45, 0.30), factors=(0.45, 0.65, 0.85, 1.0))
    ramp('r11_fl_lgrey', (0.55, 0.55, 0.56), factors=(0.30, 0.5, 0.75, 1.0))
    ramp('r11_fl_lbrown', (0.55, 0.32, 0.18), factors=(0.30, 0.5, 0.75, 1.0))
    ramp('r11_fl_cube', (0.92, 0.92, 0.92), factors=(0.45, 0.65, 0.85, 1.0))
    mat('r11_fl_cubeseam', (0.55, 0.55, 0.57))
    ramp('r11_fl_tur', (0.90, 0.90, 0.90), factors=(0.45, 0.65, 0.85, 1.0))
    mat('r11_fl_turside', (0.30, 0.30, 0.31))
    mat('r11_fl_red', (0.85, 0.10, 0.08))


def ring_z(m, z, r0, r1, material, n=N16, face=-1, phase=0.0):
    """flat annulus in the plane Z = z between radii r0 < r1 (n-gon), facing -Z (face=-1) or +Z"""
    for k in range(n):
        t0 = math.radians(phase) + 2 * math.pi * k / n; t1 = math.radians(phase) + 2 * math.pi * (k + 1) / n
        p = [(r0 * math.cos(t0), r0 * math.sin(t0), z), (r1 * math.cos(t0), r1 * math.sin(t0), z),
             (r1 * math.cos(t1), r1 * math.sin(t1), z), (r0 * math.cos(t1), r0 * math.sin(t1), z)]
        if face > 0: m.poly(material, p)
        else: m.poly(material, p[::-1])
    return m


def wall_z(m, z0, z1, r, material, n=N16, inward=True, phase=0.0):
    """n-gon cylinder wall about Z from z0 to z1 at radius r, visible from inside (inward) or outside"""
    for k in range(n):
        t0 = math.radians(phase) + 2 * math.pi * k / n; t1 = math.radians(phase) + 2 * math.pi * (k + 1) / n
        p = [(r * math.cos(t0), r * math.sin(t0), z0), (r * math.cos(t1), r * math.sin(t1), z0),
             (r * math.cos(t1), r * math.sin(t1), z1), (r * math.cos(t0), r * math.sin(t0), z1)]
        if inward: p = p[::-1]
        m.poly(material, p)
    return m


def fcollar(s=1.0):
    """factory collar, axis +Z, front (white band, a thin plate r 40..61) at z = 0 facing -Z; housing 60 deep, outer
    radius 82, 30 deep, open behind (radius 61)"""
    m = Mesh(); ph = 360.0 / 32
    ring_z(m, 0.0, 40 * s, 61.06 * s, 'r11_fl_cwhite', phase=ph)
    ring_z(m, 1.0 * s, 40 * s, 61.06 * s, 'r11_fl_cinner', face=+1, phase=ph)
    h = Mesh()
    wall_z(h, 0.0, 30 * s, 82 * s, 'r11_fl_corange', inward=False, phase=ph)
    ring_z(h, 0.0, 61.06 * s, 82 * s, 'r11_fl_corange', phase=ph)
    wall_z(h, 0.0, 30 * s, 61.06 * s, 'r11_fl_cgrey', inward=True, phase=ph)
    ring_z(h, 30 * s, 61.06 * s, 82 * s, 'r11_fl_corange', face=+1, phase=ph)
    h.shade('r11_fl_corange', light=(0.3, 0.5, -0.8))
    m.add(h)
    return m


def arm(mt='r11_fl_arm'):
    """hanging robot arm: mount plate at z = 0, hangs down about 90 (model x = reach direction)"""
    m = Mesh()
    m.box((-10, -10, -8), (10, 10, 0), mt)                      # mount
    m.tube((0, 0, -8), (0, 0, -22), 9, mt, n=10)                # turntable
    m.sphere((0, 0, -28), 11, mt, n=10, m=6)                    # shoulder
    m.tube((0, 0, -28), (22, 0, -52), 6, mt, n=8)               # upper arm
    m.sphere((22, 0, -52), 8, mt, n=10, m=6)                    # elbow
    m.tube((22, 0, -52), (8, 0, -80), 5, mt, n=8)               # fore arm
    m.box((2, -6, -92), (14, 6, -80), mt)                       # tool
    m.shade(mt, light=(0.2, 0.3, 0.9))
    return m


def mach():
    """grey machinery hanging under the ceiling on the +y side (film 96.7-97.5: grey housings, motor drums, hoses)"""
    m = Mesh()
    m.box((-45, -30, -28), (45, 30, 0), 'r11_fl_mach')                    # housing under its rail
    m.tube((-30, 0, -40), (30, 0, -40), 16, 'r11_fl_mach', n=10)          # motor drum
    m.box((-12, -12, -90), (12, 12, -40), 'r11_fl_mach')                  # drop arm
    m.box((-22, -18, -112), (22, 18, -90), 'r11_fl_mach')                 # tool head
    m.shade('r11_fl_mach', light=(-0.3, -0.4, 0.85))
    return m


def floorarm():
    """robot arm lying on the conveyor (long axis +X)"""
    m = Mesh()
    m.box((-12, -12, 0), (12, 12, 10), 'r11_fl_arm')
    m.sphere((0, 0, 18), 12, 'r11_fl_arm', n=10, m=6)
    m.tube((0, 0, 18), (40, 0, 30), 6, 'r11_fl_arm', n=8)
    m.sphere((40, 0, 30), 8, 'r11_fl_arm', n=10, m=6)
    m.tube((40, 0, 30), (75, 0, 14), 5, 'r11_fl_arm', n=8)
    m.shade('r11_fl_arm', light=(0.2, 0.3, 0.9))
    return m


def box():
    m = Mesh().box((-14, -10, 0), (14, 10, 14), 'r11_fl_box')
    m.shade('r11_fl_box', light=(-0.3, 0.4, 0.85))
    return m


def lcollar(s=1.0):
    """lab collar: dark 16-gon ring, orange inner band; axis +Z, centred at z = 0 (depth 30)"""
    m = Mesh(); ph = 360.0 / 32
    o = Mesh()
    # film (100-106 s): dark translucent glass rings, a thin brownish-orange inner band
    ring_z(o, -15 * s, 66 * s, 88 * s, 'r11_fl_lglass', phase=ph)
    ring_z(o, -15 * s, 61.06 * s, 66 * s, 'r11_fl_lband', phase=ph)
    ring_z(o, 15 * s, 61.06 * s, 88 * s, 'r11_fl_lglass', face=+1, phase=ph)
    wall_z(o, -15 * s, 15 * s, 88 * s, 'r11_fl_lglass', inward=False, phase=ph)
    wall_z(o, -15 * s, 15 * s, 61.06 * s, 'r11_fl_lband', inward=True, phase=ph)
    m.add(o)
    return m


def cube(s=1.0):
    m = Mesh(); h = 20 * s
    m.box((-h, -h, -h), (h, h, h), 'r11_fl_cube')
    m.shade('r11_fl_cube', light=(-0.3, 0.4, 0.85))
    for ax in range(3):
        for sg in (-1, 1):
            c = np.zeros(3); c[ax] = sg * (h + 0.3)
            half = np.full(3, h * 0.3); half[ax] = 0.3
            m.box(c - half, c + half, 'r11_fl_cubeseam')
    return m


def turret(s=1.0):
    """turret: egg body (axis +Z), grey side panels, red eye looking +X"""
    m = Mesh()
    m.sphere((0, 0, 0), 22 * s, 'r11_fl_tur', n=14, m=10, squash=(0.85, 0.85, 1.25))
    m.shade('r11_fl_tur', light=(0.4, 0.3, 0.85))
    for sg in (-1, 1):
        m.box((-14 * s, sg * 19 * s - 3 * s, -18 * s), (14 * s, sg * 19 * s + 3 * s, 18 * s), 'r11_fl_turside')
    m.sphere((18.5 * s, 0, 4 * s), 4.5 * s, 'r11_fl_red', n=8, m=6)
    return m


def pedestal():
    """cube pedestal under the tube: grey cylinder, orange petals around its top (z = 0 at the top)"""
    m = Mesh()
    m.lathe([(-260, 26), (0, 26)], 'r11_fl_lgrey', n=16, axis='z')
    m.shade('r11_fl_lgrey', light=(0.5, 0.3, 0.6))
    p = Mesh()
    for k in range(8):
        a = 360.0 * (k + 0.5) / 8
        p.add(Mesh().box((28, -40, -28), (110, 40, -25), 'r11_fl_lorange'), R=rot_z(a))
    p.shade('r11_fl_lorange', light=(0.0, 0.3, 0.95))
    m.add(p)
    return m


def sphere():
    """the hanging sphere of the lab (white shell, grey handles, red eye looking +X), about 170 across"""
    m = Mesh()
    m.sphere((0, 0, 0), 80, 'r11_fl_tur', n=16, m=12)
    m.shade('r11_fl_tur', light=(0.5, 0.3, 0.8))
    m.sphere((74, 0, 0), 24, 'r11_fl_red', n=10, m=8, squash=(0.5, 1, 1))
    for sg in (-1, 1):
        m.box((-40, sg * 84 - 6, -50), (40, sg * 84 + 6, 50), 'r11_fl_turside')
    return m


def ringstack():
    """the chamber's glass tube stub (lab 2): dark glass body r 110 standing on legs (floor z = 0) to z 500, brown
    collars inside it every 80 (seen as concentric rings from above), an orange ring around its top"""
    m = Mesh()
    wall_z(m, 60.0, 100.0, 110.0, 'r11_fl_glass2', inward=False)
    for z in np.arange(100.0, 500.0, 80.0):
        r = Mesh()
        ring_z(r, z + 10, 72.0, 108.0, 'r11_fl_lbrown', face=+1)
        wall_z(r, z - 10, z + 10, 72.0, 'r11_fl_lbrown', inward=True)
        r.shade('r11_fl_lbrown', light=(0.4, 0.3, 0.8))
        m.add(r)
    t = Mesh()
    wall_z(t, 470.0, 520.0, 128.0, 'r11_fl_lorange', inward=False)
    ring_z(t, 520.0, 96.0, 128.0, 'r11_fl_lorange', face=+1)
    wall_z(t, 470.0, 520.0, 96.0, 'r11_fl_lorange', inward=True)
    t.shade('r11_fl_lorange', light=(0.4, 0.3, 0.8))
    m.add(t)
    for k in range(4):                                                   # legs
        a = math.radians(45 + 90 * k)
        m.tube((105 * math.cos(a), 105 * math.sin(a), 60), (150 * math.cos(a), 150 * math.sin(a), 0), 5, 'r11_fl_lring', n=6)
    return m


def build():
    materials()
    save(fcollar(), 'r11_fl_fcollar')
    save(arm(), 'r11_fl_arm')
    save(arm().transform(scale=1.5), 'r11_fl_arm_l')
    save(arm('r11_fl_armg').transform(scale=1.3), 'r11_fl_arm_g')
    save(floorarm(), 'r11_fl_floorarm')
    save(mach(), 'r11_fl_mach')
    save(box(), 'r11_fl_box')
    save(box().transform(scale=1.6), 'r11_fl_box_l')
    save(lcollar(), 'r11_fl_lcollar')
    save(cube(), 'r11_fl_cube')
    save(turret(), 'r11_fl_turret')
    save(pedestal(), 'r11_fl_pedestal')
    save(ringstack(), 'r11_fl_ringstack')
    save(sphere(), 'r11_fl_sphere')
