"""Adds/overrides camera reference-angle knots in the v50 director (writes a copy)."""
import re, sys, os
from pathlib import Path
src = Path(os.path.expanduser('~/mnt/revision9/r10/base/director_v50.nut'))   # untouched v50 director
dst = Path(sys.argv[1])
edits = {  # time: (pitch, yaw, roll)
    # "16" wall: aimed so the sign sits where the video has it (top centre at 72.5-73.25 s, frame centre at 73.5 s);
    # solved from the camera path and the sign's position (4976, -30, 1298)
    # r10an: the video holds back from the inlet (72.5-73 s): the sign at the top centre with the shaft's tube running
    # down below it; the camera then closes in and drops into the shaft at 74 s (positions in inlet_pos below)
    72.5: (-2.0, -6.0, 0.0), 72.75: (-2.0, -6.0, 0.0), 73.0: (-3.0, -6.0, 0.0), 73.25: (-10.0, -7.0, 0.0),
    73.5: (-40.0, -8.0, 0.0),  # then drops into the shaft at 74 s
    # sludge test room: the video looks almost straight down onto the chamber while the tube carries
    # the camera across it, with the copper collar ahead at the top of the frame
    # r10x: the video frames the whole chamber -- the north walkway band sits mid-frame -- so the camera looks
    # about 45 degrees down (60 hid the far walkway, 30 showed too much far wall); at 90 s it lifts to the black-tiled wall and up the copper exit tube.
    # r10al: the video rises out of the copper tube and drops down a short vertical copper funnel into the chamber
    # (86.2-87.2 s): looking straight down the funnel, then forward-down over the walkways
    86.0: (-10.0, 20.0, 0.0), 86.25: (40.0, 45.0, 0.0), 86.5: (80.0, 60.0, 0.0), 86.75: (88.0, 80.0, 0.0), 87.0: (85.0, 90.0, 0.0), 87.25: (60.0, 90.0, 0.0), 87.5: (45.0, 90.0, 0.0),
    88.0: (44.0, 90.0, 0.0), 89.0: (44.0, 90.0, 0.0), 89.5: (42.0, 90.0, 0.0),
    90.0: (38.0, 90.0, 0.0), 90.25: (5.0, 90.0, 0.0), 90.5: (-35.0, 60.0, 0.0), 91.0: (-20.0, 0.0, 0.0),
    # turret lift (64.5-67 s): look up at the collar, then down into the floor ring the turret rises from,
    # then level with the turret (the camera dips to its eye height, see pos_z below)
    # r10ah: the video comes over the top of the turret-lift collar and looks down on it (63.4-64.8 s: the dark
    # platform with tubes hanging under it, the "16" sign at the right), drops through it looking straight down at
    # the floor ring (65-65.6 s), and watches the turret rise toward the lens (66-67 s)
    63.25: (25.0, 10.0, 0.0), 63.5: (38.0, 5.0, 0.0), 63.75: (43.0, 4.0, 0.0), 64.0: (48.0, 3.0, 0.0), 64.25: (55.0, 2.0, 0.0), 64.5: (65.0, 0.0, 0.0),
    64.75: (75.0, 0.0, 0.0), 65.0: (85.0, 10.0, 0.0), 65.5: (88.0, 20.0, 0.0), 66.0: (85.0, 30.0, 0.0),
    66.25: (55.0, 40.0, 0.0), 66.5: (12.0, 46.0, 0.0), 67.0: (0.0, 46.0, 0.0),   # r10ay: level with the rising turret by 66.5 s (video)
    # r10af: the video holds the turret front-on and centred through the lens glare (69.5-71.2 s), the camera rising
    # only slightly; it leaves for the "16" inlet in the last 0.8 s (see pos_x/pos_z)
    70.5: (-9.0, 63.0, 0.0), 71.0: (-8.0, 62.0, 0.0), 71.25: (-7.0, 40.0, 0.0), 71.5: (-8.0, 12.0, 0.0),
    43.0: (-10.0, 60.0, 0.0), 43.5: (-18.0, -5.0, 0.0),   # pod rise: glance at the near wall, then down the tube
    # tower entrance: the video keeps the pale collar centred and looks slightly up, then tilts up the tower
    56.0: (-3.0, 2.0, 0.0), 56.5: (-4.0, 0.0, 0.0), 57.0: (-6.0, -2.0, 0.0), 57.5: (-12.0, 0.0, 0.0), 58.0: (-30.0, 22.0, 0.0),
    # lab: the video turns right toward the white test chamber and its hanging turrets
    102.5: (-4.0, -6.0, 0.0), 103.0: (2.0, -30.0, 0.0), 103.5: (6.0, -42.0, 0.0),
    104.0: (12.0, -55.0, 0.0), 104.5: (18.0, -75.0, 0.0), 105.0: (22.0, -100.0, 0.0),   # onto the turret wall, not past it
    # 107-109.5 s: the video looks steeply down into the white test chamber before the incinerator cut
    # r10af: along the tube until 106.6 s (concentric rings), down into the chamber by 107.5 s with the frame turned so the
    # receptacle is top-left and the purple strip runs down the right (video 107.5 s), the view spins as it does in the
    # video (strip along the top at 108 s) while the camera drops down a short copper tube onto the receptacle
    106.6: (3.0, 0.0, 0.0), 107.0: (50.0, -10.0, 0.0), 107.5: (88.0, -25.0, 0.0), 108.0: (89.0, -75.0, 0.0),
    108.5: (89.0, -115.0, 0.0), 109.0: (89.0, -150.0, 0.0), 109.3: (89.0, -170.0, 0.0), 109.70928: (89.0, -190.0, 0.0),
}
txt = src.read_text()
start = txt.index('knots <- [')
end = txt.index('];', start)
body = txt[start:end]
rows = re.findall(r'\{t=([0-9.]+),a=Vector\(([-0-9.]+),([-0-9.]+),([-0-9.]+)\)\}', body)
knots = {float(t): (float(a), float(b), float(c)) for t, a, b, c in rows}
knots.update(edits)
# r10as: pod-rise run (44-47 s) -- the video looks a little up and right down the tube (far end at ~43%, 70% of the frame),
# then swings right at the pale crossing tube (47-48 s), looks up through the crossing (48.25 s) and faces the pale
# wall that closes the tube (48.5-48.85 s) before the dark tube of the cube passage (49 s)
edits2 = {44.0: (-19.0, -11.0, 0.0), 45.0: (-15.0, -11.0, 0.0), 45.5: (-14.0, -10.0, 0.0), 46.0: (-17.0, -8.0, 0.0), 46.5: (-15.0, -6.0, 0.0),
          47.0: (-11.0, -26.0, 0.0), 47.25: (-4.0, -42.0, 0.0), 47.5: (-3.0, -55.0, 0.0), 47.75: (-2.0, -60.0, 0.0), 48.0: (-5.0, -45.0, 0.0),
          48.25: (-35.0, -20.0, 0.0), 48.5: (-5.0, 0.0, 0.0), 48.75: (0.0, 0.0, 0.0), 48.85: (0.0, 0.0, 0.0),
          # r10aw: gallery -- the video looks across the cream truss at the rust wall while the tube runs along it (91-92 s)
          # and sees the cream collar at the right of the frame at 95 s
          # r10bc: the video looks down at the dark room's end wall with ring A at the top (90.5-90.9 s), goes through it
          # and looks at the rust wall over ring B (91-92 s), then keeps facing the wall while the tube runs right to the
          # broken flange, which holds at ~78% of the frame width (92.25-93.75 s)
          90.25: (15.0, 40.0, 0.0), 90.5: (20.0, -2.0, 0.0), 90.75: (30.0, -2.0, 0.0), 91.0: (25.0, -6.0, 0.0), 91.25: (16.0, -6.0, 0.0),
          91.5: (12.0, -12.0, 0.0), 91.75: (8.0, -17.0, 0.0), 92.0: (6.0, -18.0, 0.0), 92.25: (4.0, -20.0, 0.0), 92.5: (6.0, -29.0, 0.0),
          92.75: (8.0, -48.0, 0.0), 93.0: (5.0, -53.0, 0.0), 93.25: (7.0, -58.0, 0.0), 93.5: (5.0, -56.0, 0.0), 93.75: (8.0, -56.0, 0.0),
          94.0: (2.0, -35.0, 0.0), 94.25: (2.0, -33.0, 0.0), 94.5: (0.0, 20.0, 0.0),
          63.25: (-16.0, 118.0, 0.0), 63.5: (-16.0, 118.0, 0.0), 63.75: (-15.0, 118.0, 0.0), 63.86: (-15.0, 118.0, 0.0), 63.87: (43.0, 4.0, 0.0),
          123.2: (-2.0, 40.0, 0.0), 123.35: (0.0, 88.0, 0.0), 123.4: (0.0, 89.0, 0.0), 123.5: (0.0, 90.0, 0.0), 123.6: (0.0, 92.0, 0.0), 123.65: (0.0, 94.0, 0.0),
          95.0: (0.0, 46.0, 0.0), 95.25: (0.0, 40.0, 0.0),   # r10bi: the cream collar sits at ~85% of the frame width (video)
          # r10ax: pod rise -- the video looks straight up the tube (far end at the frame centre)
          39.5: (-88.0, 0.0, -20.0), 40.5: (-89.0, 0.0, -24.0), 41.5: (-84.0, 0.0, -20.0),
          # tower entrance: two shots joined by quick dissolves (56.5 and 58.6 s). Shot A looks straight at the collar from
          # inside the tube; shot B starts further back, looking up and right at the collar, and tilts up the dark column
          # r10at: collar at (46%, 58%) of the frame in shot A and (45%, 68%) at 57 s in shot B (video)
          55.25: (-7.0, -5.0, 0.0), 55.5: (-7.0, -5.0, 0.0), 56.0: (-6.0, -5.0, 0.0), 56.25: (-5.0, -5.0, 0.0), 56.5: (-5.0, -5.0, 0.0), 56.51: (-5.0, -5.0, 0.0),
          56.52: (-10.0, -10.0, 0.0), 57.0: (-13.0, -10.0, 0.0), 57.5: (-22.0, -10.0, 0.0), 58.0: (-34.0, -9.0, 0.0), 58.25: (-40.0, -9.0, 0.0),
          58.5: (-44.0, -8.0, 0.0), 58.57: (-45.0, -8.0, 0.0), 58.58: (-16.0, 58.0, 0.0),
          # r10bu: the video cuts from the glare to a look straight down into the inlet iris (71.4-71.75 s) and tilts up to the 16 wall
          # r10bv: the camera sits 45 units from the turret (it was 66; the video's turret is ~1.5x larger) and is aimed so
          # the eye follows the video's track (measured: right/up of centre, degrees)
          67.5: (-1.7, 61.2, 0.0), 67.75: (1.6, 65.9, 0.0), 68.0: (1.6, 69.6, 0.0), 68.25: (1.6, 71.9, 0.0), 68.5: (1.1, 75.5, 0.0),
          68.75: (1.6, 78.1, 0.0), 69.0: (2.5, 77.2, 0.0), 69.25: (4.4, 76.8, 0.0), 69.5: (5.3, 74.15, 0.0), 69.75: (6.2, 71.5, 0.0),
          70.0: (2.0, 70.6, 0.0), 70.25: (-4.1, 70.1, 0.0), 70.5: (-8.4, 70.6, 0.0), 70.75: (-7.9, 69.2, 0.0), 71.0: (-5.1, 67.3, 0.0),
          71.2: (-5.1, 66.4, 0.0), 71.33: (-5.1, 66.4, 0.0),
          # r10by: under the turret-lift collar (63.87-67 s)
          63.87: (22.0, 82, 0.0), 64.0: (25.0, 81, 0.0), 64.25: (8.0, 79, 0.0), 64.5: (12.0, 77, 0.0), 64.75: (17.0, 75, 0.0), 65.0: (23.0, 73, 0.0), 65.25: (31.0, 71, 0.0), 65.5: (39.0, 69, 0.0), 65.75: (47.0, 67, 0.0), 66.0: (55.0, 65, 0.0), 66.25: (42.0, 63.5, 0.0), 66.5: (12.0, 62.5, 0.0), 67.0: (0.0, 55.0, 0.0),
          # r10cb: the inlet iris shot's first knots had slipped behind a comment, so 71.34-71.8 s swept from the turret yaw
          71.34: (89.0, 0.0, -8.0), 71.5: (89.0, 0.0, -4.0), 71.6: (88.0, 0.0, 2.0), 71.7: (84.0, 0.0, 8.0),
          71.8: (66.0, -2.0, 8.0), 71.9: (42.0, -4.0, 4.0), 72.0: (22.0, -5.0, 2.0), 72.1: (10.0, -6.0, 0.0), 72.25: (-1.0, -6.0, 0.0)}   # r10au: tilts up faster (collar at the bottom edge by 58.25 s)
for _t in [k for k in knots if 63.865 < k < 67.0 or 67.4 < k < 72.25]: del knots[_t]   # r10bu/bv: turret framing and the inlet iris shot replace these
knots.update(edits2)
# r10ca: the rust room's lower run (36.12-38.94 s) was shot upside down (pitch 180); upright it frames junction E like the
# video -- the panel behind it at mid height, the dark floor below, black above. (p, y) -> (180 - p, y - 180), cut at 36.12 s
# inside the video's dissolve
knots[36.12] = (180.0, 164.0, 0.0)
for _t in [k for k in knots if 36.12 < k <= 38.94]:
    _a, _b, _c = knots[_t]; knots[_t] = (180.0 - _a, _b - 180.0, _c)
knots[36.121] = (0.0, -16.0, 0.0)
# r10cb: the video stays level through the drop at x 2048 (37.8-38.4 s) with only a short nod into the bend; ours
# tilted straight down the branch (pitch 90) and saw nothing but tube
for _t in [k for k in knots if 37.8 < k < 38.4]: del knots[_t]
knots.update({37.88: (20.0, 0.0, 0.0), 37.95: (26.0, 0.0, 0.0), 38.02: (12.0, 0.0, 0.0), 38.1: (0.0, 0.0, 0.0)})
# r10cc: the video keeps looking straight down into the iris through 82.8 s and dives into it (the tube's rings
# concentric at 82.6-82.75 s); ours tilted up from 82 s and lost the iris off the bottom edge
for _t in [k for k in knots if 82.0 < k < 83.0]: del knots[_t]
knots.update({82.25: (88.0, 0.0, 0.0), 82.5: (89.0, 0.0, 0.0), 82.8: (89.0, 0.0, 0.0)})
# r10cv: tube ride after the pod rise (43.75-46.6 s) -- the video's tube runs off to the lower left: its rings' centre sits
# at (-0.21..-0.06, +0.46..+0.54)f, ours at (+0.34..+0.27) below the middle; looking 10 degrees higher puts it there
for _t in [k for k in knots if 43.6 < k < 46.65]:
    _a, _b, _c = knots[_t]; knots[_t] = (_a - 10.0, _b, _c)
# r10cy: vault doorway (124.25-125.5 s) -- the video's tube centre sits at y +0.13..+0.20f, ours +0.21..+0.28f: look 4.5 lower
for _t in [k for k in knots if 124.1 < k < 125.6]:
    _a, _b, _c = knots[_t]; knots[_t] = (_a + 4.5, _b, _c)
# r10ct: scanner shaft -- the video's vanishing point sits steadily at (-0.03, +0.10) of the focal length (measured
# 76.5-80.2 s); ours wandered (+0.02..+0.06, +0.03..+0.14). Pitch 84 and roll -13 put the nadir there; the yaw takes over
# the old roll so the rails and boards keep their image angles (yaw + roll is what turns the picture when looking down).
for _t in [k for k in knots if 75.6 < k < 80.3]:
    _a, _b, _c = knots[_t]; knots[_t] = (84.0, _b + _c + 13.0, -13.0)
new = 'knots <- [\n' + ',\n'.join('{t=%.8f,a=Vector(%.8f,%.8f,%.8f)}' % ((t,) + knots[t]) for t in sorted(knots)) + '\n'
txt = txt[:start] + new + txt[end:]
# Fades measured from the video's mean luminance around each cut (the cuts dissolve, they are not hard).
# camera height for the turret lift: dips from the tube (1152) to the turret's eye level, holds there until 71 s
# (r10af: the video stays on the turret through the glare) and climbs back to the tube by 72 s
pos_z = [(65.5, 1152.0), (66.0, 1125.0), (66.25, 1095.0), (66.5, 1060.0), (67.0, 1010.0), (67.5, 1000.0),
         (71.0, 1000.0), (71.25, 1040.0), (71.5, 1090.0), (71.75, 1128.0), (72.0, 1152.0)]
pos_x = [(70.0, 4544.0), (71.0, 4544.0), (71.25, 4566.0), (71.5, 4598.0), (71.75, 4634.0), (72.0, 4672.0)]
def lerp(tab, t):
    for (t0, z0), (t1, z1) in zip(tab, tab[1:]):
        if t0 <= t <= t1: return z0 + (z1 - z0) * (t - t0) / (t1 - t0)
    return None
# lab (108-109.7 s): the camera leaves the end of the tube and drops down a short copper tube onto the receptacle
lab_pos = {108.25: (8228.0, 0.0, 250.0), 108.5: (8252.0, 0.0, 238.0), 108.75: (8266.0, 0.0, 215.0), 109.0: (8270.0, 0.0, 185.0),
           109.25: (8270.0, 0.0, 150.0), 109.3: (8270.0, 0.0, 143.0), 109.5: (8270.0, 0.0, 115.0)}
# r10ah: scanner shaft (76-81 s) -- the video is still among the stacked rings at 78-79 s and reaches the scanner
# cones / iris only at 80.5-81.5 s; the v50 camera got there about 1.5 s early. z only, x/y unchanged.
inlet_pos = {72.25: (4676.0, 0.0, 1152.0), 72.5: (4680.0, 0.0, 1152.0), 72.75: (4684.0, 0.0, 1152.0), 73.0: (4690.0, 0.0, 1152.0),
             73.25: (4725.0, 0.0, 1148.0), 73.5: (4770.0, 0.0, 1120.0), 73.75: (4795.0, 0.0, 1070.0)}
funnel = {86.0: (5770.0, 0.0, 280.0), 86.25: (5880.0, 80.0, 505.0), 86.5: (5950.0, 145.0, 440.0), 86.75: (5952.0, 150.0, 380.0),
          87.0: (5952.0, 150.0, 320.0), 87.25: (5952.0, 180.0, 275.0), 87.5: (5952.0, 210.0, 256.0)}
copper_x = [(84.2, 5240.0), (84.55, 5260.0), (85.0, 5330.0), (85.5, 5450.0), (85.75, 5600.0), (86.0, 5770.0)]   # r10am: the room west of the towers is dark; start at them
pod_z = [(39.5, 640.0), (39.75, 660.0), (40.0, 680.0), (40.25, 700.0), (40.5, 720.0), (40.75, 745.0), (41.0, 770.0), (41.25, 810.0), (41.5, 880.0), (41.75, 1000.0)]
shaft_z = [(77.0, 835.0), (78.0, 790.0), (79.0, 720.0), (79.5, 685.0), (80.0, 655.0), (80.25, 650.0), (80.5, 645.0), (80.75, 618.0), (81.0, 570.0), (81.25, 552.0), (81.5, 545.0), (82.0, 545.0), (82.25, 520.0), (82.5, 400.0)]   # r10az: hover higher over the iris (video 81-82 s: the iris ~45% of the frame width)   # r10ao: hover over the iris until 82.2 s, then drop through it
# r10ah: sludge chamber (87-90 s) -- the video is lower and closer over the walkways than the tube (z 256)
sludge_z = {86.5: 246.0, 86.75: 226.0, 87.0: 206.0, 87.25: 192.0, 87.5: 186.0, 87.75: 186.0, 88.0: 186.0, 88.25: 186.0,
            88.5: 186.0, 88.75: 186.0, 89.0: 186.0, 89.25: 186.0, 89.5: 188.0, 89.75: 196.0, 90.0: 210.0, 90.25: 232.0, 90.5: 250.0}
descent = {63.25: (4180, 20, 1450), 63.5: (4330, 40, 1520), 63.75: (4390, 45, 1535), 64.0: (4420, 50, 1540), 64.25: (4480, 52, 1500), 64.5: (4510, 52, 1430),
           64.75: (4530, 40, 1380), 65.0: (4540, 30, 1290), 65.25: (4542, 20, 1220), 65.5: (4544, 10, 1150), 65.75: (4544, 5, 1110),
           66.0: (4544, 0, 1080), 66.25: (4544, 0, 1060), 66.5: (4544, 0, 1045), 66.75: (4544, 0, 1025), 67.0: (4544, 0, 1010),   # r10aq: lower, the floor ring big below (65.5 s)
           67.25: (4544, 0, 1005), 67.5: (4544, 0, 1000), 67.75: (4544, 0, 1000)}
ps = txt.index('positions <- ['); pe = txt.index('];', ps)
def repl(m):
    t = float(m.group(1)); x, y, z = (float(m.group(k)) for k in (2, 3, 4))
    for k, q in descent.items():
        if abs(t - k) < 1e-4: return '{t=%s,p=Vector(%.8f,%.8f,%.8f)}' % ((m.group(1),) + tuple(float(c) for c in q))
    if 65.5 < t < 72.0:
        nz = lerp(pos_z, t); nx = lerp(pos_x, t)
        return '{t=%s,p=Vector(%.8f,%s,%.8f)}' % (m.group(1), x if nx is None else nx, m.group(3), z if nz is None else nz)
    for k, q in lab_pos.items():
        if abs(t - k) < 1e-4: return '{t=%s,p=Vector(%.8f,%.8f,%.8f)}' % ((m.group(1),) + q)
    if abs(t - 109.709) < 0.002 and abs(x - 8240) < 1: return '{t=%s,p=Vector(8270.0,0.0,85.0)}' % m.group(1)
    for k, q in list(funnel.items()) + list(inlet_pos.items()):
        if abs(t - k) < 1e-4: return '{t=%s,p=Vector(%.8f,%.8f,%.8f)}' % ((m.group(1),) + q)
    if 84.2 < t <= 86.0:   # r10ak: the lattice towers stand ahead on both sides at 84.6-85.5 s in the video
        return '{t=%s,p=Vector(%.8f,%s,%s)}' % (m.group(1), lerp(copper_x, t), m.group(3), m.group(4))
    if 39.6 < t <= 41.75:   # r10aj: pod rise -- the video stays low in a long tube (small far opening) until ~41.3 s
        return '{t=%s,p=Vector(%s,%s,%.8f)}' % (m.group(1), m.group(2), m.group(3), lerp(pod_z, t))
    if 77.0 < t <= 82.5:
        return '{t=%s,p=Vector(%s,%s,%.8f)}' % (m.group(1), m.group(2), m.group(3), lerp(shaft_z, t))
    for tab in ():   # r10ai: the sludge dip (r10ah) framed the walkways too close; the video's scale matches z 256
        for k, nz in tab.items():
            if abs(t - k) < 1e-4: return '{t=%s,p=Vector(%s,%s,%.8f)}' % (m.group(1), m.group(2), m.group(3), nz)
    return m.group(0)
newpos = re.sub(r'\{t=([-\d.]+),p=Vector\(([-\d.]+),([-\d.]+),([-\d.]+)\)\}', repl, txt[ps:pe])
# r10as: tower entrance -- shot A (55.25-56.5 s) approaches slowly inside the tube, shot B (56.52-58.57 s) starts ~245 units
# from the collar and closes to ~150, then the 58.6 s dissolve goes to the climb inside the tower
pos_set = {55.0: (3435.0, 0.0, 1152.0), 55.25: (3445.0, 0.0, 1152.0), 55.5: (3458.0, 0.0, 1152.0), 55.75: (3472.0, 0.0, 1152.0),
           56.0: (3486.0, 0.0, 1152.0), 56.25: (3500.0, 0.0, 1152.0), 56.5: (3510.0, 0.0, 1152.0), 56.51: (3511.0, 0.0, 1152.0),
           56.52: (3455.0, 0.0, 1152.0), 56.75: (3467.0, 0.0, 1152.0), 57.0: (3480.0, 0.0, 1152.0), 57.25: (3495.0, 0.0, 1152.0),
           57.5: (3510.0, 0.0, 1152.0), 57.75: (3532.0, 0.0, 1152.0), 58.0: (3555.0, 0.0, 1152.0), 58.25: (3575.0, 0.0, 1152.0),
           58.5: (3590.0, 0.0, 1152.0), 58.57: (3595.0, 0.0, 1152.0), 58.58: (3754.0, 0.0, 1306.0),
           # r10bc: gallery -- ring A (x 6272) at 91.0 s and ring B (6426) at 92.0 s like the video; the run to the broken
           # flange (y 185) reaches it at ~94 s
           90.25: (6035.0, 500.0, 256.0), 90.5: (6140.0, 511.0, 256.0), 90.75: (6215.0, 512.0, 256.0), 91.0: (6276.0, 512.0, 256.0),
           91.25: (6318.0, 512.0, 256.0), 91.5: (6360.0, 512.0, 256.0), 91.75: (6395.0, 512.0, 256.0), 92.0: (6426.0, 512.0, 256.0),
           92.25: (6452.0, 512.0, 256.0), 92.5: (6478.0, 511.0, 256.0), 92.75: (6560.0, 500.0, 256.0), 93.0: (6592.0, 470.0, 256.0),
           93.25: (6592.0, 420.0, 256.0), 93.5: (6592.0, 360.0, 256.0), 93.75: (6592.0, 300.0, 256.0), 94.0: (6592.0, 245.0, 256.0),
           94.25: (6594.0, 175.0, 256.0), 94.5: (6625.0, 80.0, 256.0), 94.75: (6670.0, 20.0, 256.0), 95.0: (6700.0, 2.0, 256.0),
           # r10bf: capsule -- the video turns from the cracked pane to a close concrete wall and holds it (123.35-123.65 s)
           # before the dissolve to the vault doorway; the wall segment is x 11376-11492 at y 140
           123.2: (11410.0, 40.0, 148.0), 123.35: (11434.0, 92.0, 145.0), 123.4: (11433.0, 93.0, 145.0), 123.5: (11431.0, 94.0, 145.0),
           123.6: (11428.0, 95.0, 145.0), 123.65: (11424.0, 95.0, 145.0),
           # r10bn: the video stays in the tower on the scanning column (red laser, cube) until ~63.85 s, then goes to the
           # turret-lift collar from above; the descent now starts at its 63.75 s pose
           63.25: (4010.0, 0.0, 1320.0), 63.5: (4010.0, 0.0, 1295.0), 63.75: (4010.0, 0.0, 1270.0), 63.86: (4010.0, 0.0, 1262.0),
           63.87: (4390.0, 45.0, 1535.0),
           67.5: (4547.0, 6.0, 1004.0), 67.75: (4548.6, 8.7, 1008.0), 68.0: (4548.6, 8.7, 1008.0), 69.0: (4548.6, 8.7, 1008.0),
           70.0: (4548.6, 8.7, 1008.0), 71.0: (4548.6, 8.7, 1008.0),
           71.33: (4548.6, 8.7, 1008.0), 71.34: (4789.0, 55.0, 1105.0),
           48.5: (2786.0, 0.0, 1152.0), 48.75: (2796.0, 0.0, 1152.0),
           # r10bz: the video frames the sludge room ~1.3x wider than our z 256 pass: 40 higher and 40 further back
           87.25: (5952.0, 170.0, 290.0), 87.5: (5952.0, 170.0, 296.0), 87.75: (5952.0, 210.0, 296.0), 88.0: (5952.0, 260.0, 296.0),
           88.25: (5952.0, 281.0, 296.0), 88.5: (5952.0, 302.0, 296.0), 88.75: (5952.0, 323.0, 296.0), 89.0: (5952.0, 344.0, 296.0),
           89.25: (5954.0, 369.0, 296.0), 89.5: (5962.0, 394.0, 296.0), 89.75: (5974.0, 415.0, 290.0), 90.0: (5988.0, 440.0, 275.0),
           63.87: (4508.2, -417.3, 1470.0), 64.0: (4504.6, -386.5, 1430.0), 64.25: (4498.7, -334.7, 1300.0), 64.5: (4494.0, -292.8, 1245.0), 64.75: (4492.2, -251.1, 1195.0), 65.0: (4493.1, -209.8, 1160.0), 65.25: (4500.1, -159.5, 1130.0), 65.5: (4510.5, -110.0, 1105.0), 65.75: (4522.3, -66.3, 1088.0), 66.0: (4532.7, -32.6, 1075.0), 66.25: (4541.5, -9.1, 1060.0), 66.5: (4546.4, 3.0, 1045.0), 67.0: (4547.3, 5.9, 1015.0),   # r10by   # r10bx: the tube end fills the frame (48.5 s) 71.5: (4789.0, 55.0, 1103.0), 71.6: (4789.0, 52.0, 1102.0),
           71.7: (4785.0, 45.0, 1104.0), 71.8: (4772.0, 30.0, 1112.0), 71.9: (4748.0, 15.0, 1124.0), 72.0: (4722.0, 5.0, 1136.0),
           72.1: (4700.0, 0.0, 1145.0),
           # r10cd: the video passes through the opened iris by ~82.5 s; ours was still 115 above it at 82.75 s
           82.4: (4800.0, 0.0, 430.0), 82.5: (4800.0, 0.0, 345.0), 82.6: (4801.0, 0.0, 300.0), 82.75: (4812.0, 0.0, 272.0), 83.0: (4844.0, 0.0, 262.0)}
kn = [(float(a), (float(b), float(c), float(d))) for a, b, c, d in re.findall(r'\{t=([-\d.]+),p=Vector\(([-\d.]+),([-\d.]+),([-\d.]+)\)\}', newpos)]
kd = dict(kn)
for _t in [k for k in kd if 63.865 < k < 67.0 or 67.4 < k < 72.25]: del kd[_t]   # r10bu/bv: turret framing and the inlet iris shot
# r10cq: scanner shaft (75.75-80.25 s). The video's ring edges, tracked every 0.1 s, give its descent: still 75.9-76.4 s,
# a quick step at 76.45 s and 77.65 s, otherwise steady; scaled to the rebuilt ring stack (ring B top z 605 = 95 units)
for _t in [k for k in kd if 75.6 < k < 80.3]: del kd[_t]
pos_set.update({75.75: (4800.0, 0.0, 898.0), 76.0: (4800.0, 0.0, 894.8), 76.25: (4800.0, 0.0, 881.7), 76.5: (4800.0, 0.0, 867.4),
                76.75: (4800.0, 0.0, 848.2), 77.0: (4800.0, 0.0, 841.4), 77.25: (4800.0, 0.0, 826.7), 77.5: (4800.0, 0.0, 812.1),
                77.75: (4800.0, 0.0, 798.3), 78.0: (4800.0, 0.0, 779.5), 78.25: (4800.0, 0.0, 763.9), 78.5: (4800.0, 0.0, 749.9),
                78.75: (4800.0, 0.0, 733.9), 79.0: (4800.0, 0.0, 721.8), 79.25: (4800.0, 0.0, 707.9), 79.5: (4800.0, 0.0, 693.5),
                79.75: (4800.0, 0.0, 677.1), 80.0: (4800.0, 0.0, 662.2), 80.25: (4800.0, 0.0, 650.0)})   # r10cr: re-measured with the video's 16:10 stretch undone
for k, q in pos_set.items():
    for t0 in list(kd):
        if abs(t0 - k) < 1e-4: del kd[t0]
    kd[k] = q
newpos = 'positions <- [\n' + ',\n'.join('{t=%.8f,p=Vector(%.8f,%.8f,%.8f)}' % ((t,) + kd[t]) for t in sorted(kd)) + '\n'
txt = txt[:ps] + newpos + txt[pe:]
fades = [[62.9,63.05,0,235],[63.05,63.3,235,0],[52.45,52.55,0,110],[52.55,52.68,110,0],[38.70,38.9388,0,255],[39.2725,39.60,255,0],[53.83,54.1206,0,255],[54.8547,55.27,240,240],
         [55.27,55.47,240,0],[82.55,83.1829,40,255],[84.5510,84.97,255,0],[95.33,95.7288,0,255],
         [104.97,105.305,0,255],[56.37,56.52,0,75],[56.52,56.70,75,0],[58.42,58.58,0,100],[58.58,58.72,100,0],[109.40,109.7094,0,255],[109.8428,110.6,255,0],[123.60,123.70,0,150],[123.70,123.82,150,0],[102.72,102.80,0,110],[102.80,102.90,110,0],[63.78,63.865,0,150],[63.865,63.97,150,0],
         # r10cb: the video fades the rust room in from black (32.63-33.07 s, measured luma ratio)
         [32.60,32.70,255,228],[32.70,32.77,228,145],[32.77,32.83,145,100],[32.83,32.90,100,50],[32.90,33.04,50,15],[33.04,33.07,15,0],
         # r10cj: the lab tube opens darker than ours (106-107.25 s: video 17/28/57/64/78 vs our 34/51/73/82/99) and the video goes
         # dark inside the tube from 108.6 s (100 -> 55 at 109.0 -> 13 at 109.4) where ours kept the bright chamber to 109.4 s
         [105.9,106.0,200,200],[106.0,106.25,200,158],[106.25,106.5,158,72],[106.5,106.75,72,56],[106.75,107.0,56,50],[107.0,107.25,50,18],[107.25,107.5,18,0],
         [108.55,108.67,0,94],[108.67,108.8,94,59],[108.8,108.93,59,92],[108.93,109.07,92,150],[109.07,109.2,150,196],[109.2,109.4,196,224],[109.4,109.6,224,240],[109.6,109.71,240,255],
         # r10cj: the video passes through the inlet iris in the dark (74.7-75.5 s: 20-54 against our 62-82)
         [74.63,74.7,0,70],[74.7,74.83,70,120],[74.83,74.97,120,138],[74.97,75.03,138,175],[75.03,75.17,175,128],[75.17,75.3,128,71],[75.3,75.5,71,64],[75.5,75.57,64,0],
         # r10ck: where ours read brighter than the video (smoothed frame-mean ratio 0.5-0.8): the lower rust run past junction E,
         # the scanner iris approach, the gallery turn, the 98 s factory ring and the incinerator descent
         [36.82,36.95,0,75],[36.95,37.15,75,95],[37.15,37.35,95,65],[37.35,37.5,65,20],[37.5,37.75,20,30],[37.75,37.8,30,0],
         [80.68,80.78,0,100],[80.78,80.95,100,100],[80.95,81.05,100,60],[81.05,81.15,60,0],
         [91.82,91.92,0,55],[91.92,92.05,55,72],[92.05,92.2,72,40],[92.2,92.6,40,35],[92.6,92.8,35,0],
         [97.95,98.05,0,60],[98.05,98.12,60,123],[98.12,98.25,123,80],[98.25,98.45,80,20],[98.45,98.5,20,0],
         [111.35,111.5,0,60],[111.5,111.7,60,95],[111.7,111.85,95,115],[111.85,112.05,115,65],[112.05,112.95,65,50],[112.95,113.15,50,5],
         [113.15,113.35,5,20],[113.35,113.55,20,58],[113.55,113.95,58,38],[113.95,114.12,38,0],
         # r10cm: the lift descent beside the collar reads brighter than the video (63.97-65.4 s, ratio 0.52-0.8)
         [63.97,64.1,0,115],[64.1,64.6,115,105],[64.6,64.85,105,75],[64.85,65.1,75,35],[65.1,65.5,35,0]]
anchor = '    SetScreenBlack(fadeAlpha);'
assert txt.count(anchor) == 1
txt = txt.replace(anchor, '    foreach(f in r10Fades) if(t>=f[0] && t<f[1]){local k=(t-f[0])/(f[1]-f[0]);local a=(f[2]+(f[3]-f[2])*k).tointeger();if(a>fadeAlpha)fadeAlpha=a;}\n' + anchor)
txt = txt.replace('cutTab <- [', 'r10Fades <- ' + str(fades).replace(' ', '') + ';\ncutTab <- [', 1)
# the cube rides ahead in the lab tube (100-101.5 s) instead of sitting where the camera passes through it
txt = txt.replace('cutTab <- [', 'r10LabCube <- [[99.8,7565],[100,7575],[100.5,7600],[101,7625],[101.5,7640],[101.9,7900]];' + chr(10) + 'cutTab <- [', 1)
# cube passage (52-53.8 s): the video dissolves from the far cube to a close one at ~52.55 s; the cube jumps
# closer under a short dip instead of drifting slowly toward the camera
cube_old = 'for(local i=0;i<4;i++)MoveProp("intro_cube_"+i,t<55.5?Vector(3480+i*62-(cubeTime-52)*25,0,1152):Vector(0,0,-3000));'
cube_new = 'for(local i=0;i<4;i++)MoveProp("intro_cube_"+i,(t<54.9&&t>=51.5)?Vector(Lerp1(r10CubeX,t)+i*62,0,1152):Vector(0,0,-3000));'   # r10as: gone before the 55.3 s fade-in; r10ai: the video shows no cube before 51.6 s
assert txt.count(cube_old) == 1
txt = txt.replace(cube_old, cube_new)
txt = txt.replace('cutTab <- [', 'r10CubeX <- [[51,3420],[52,3394],[52.5,3437],[52.54,3437],[52.56,3295],[53.0,3339],[53.5,3386],[53.83,3418],[55.5,3480]];' + chr(10) + 'cutTab <- [', 1)
txt = txt.replace('cutTab <- [', 'r10TurretZ <- [[65.9,820],[66.45,1010]];r10GlowPath <- [[114.0,Vector(8425,61,900)],[114.5,Vector(8454,28,740)],[115.1,Vector(8448,0,600)],[116.4,Vector(8436,-24,640)]];' + chr(10) + 'cutTab <- [', 1)
# turret laser in the lens (69.3-71.3 s): the video washes the frame pink; a second env_fade tints the screen red
txt = txt.replace('cutTab <- [', 'r10Red <- [[69.2,0],[71.28,0],[71.33,150],[71.37,150],[71.46,0]];r10RedAlpha <- 0;' + chr(10) +
    'function SetRedHaze(t){local a=(t>=69.2&&t<71.5)?Lerp1(r10Red,t).tointeger():0;if(a==r10RedAlpha)return;' +
    'local f=Entities.FindByName(null,"r10_red_fade");if(f==null)return;f.__KeyValueFromString("renderamt",""+a);' +
    'EntFire("r10_red_fade","Fade","",0);r10RedAlpha=a;}' + chr(10) +
    'r10GlowOn <- false;function SetLensGlow(t){local g=(t>=69.4&&t<71.34);if(g==r10GlowOn)return;EntFire("r10_glare_ov",g?"StartOverlays":"StopOverlays","",0);r10GlowOn=g;}' + chr(10) + 'cutTab <- [', 1)
anchor2 = '    SetPursuitShaft(t);'
assert txt.count(anchor2) == 1
txt = txt.replace(anchor2, '    SetRedHaze(t);' + chr(10) + '    MoveProp("r10_scan_plate",(t>=80.75&&t<82.9)?Vector(0,0,0):Vector(0,0,-4000));MoveProp("r10_pod_sleeve",(t>=39.2&&t<41.8)?Vector(0,0,0):Vector(0,0,-4000));MoveProp("r10_inc_frame",(t>=108.0&&t<111.9)?Vector(0,0,0):Vector(0,0,-4000));MoveProp("r10_tw_bend",(t>=55.0&&t<57.3)?Vector(0,0,-3000):Vector(3754,0,1152));{local cp=(t>=52.0&&t<53.95);MoveProp("r10_cp_sleeve",cp?Vector(0,0,0):Vector(0,0,-4000));foreach(i,x in [3431,3509,3587,3665])MoveProp("r10_cp_ring_"+i,cp?Vector(x,0,1152):Vector(0,0,-3000));};MoveProp("r10_scan_grey",(t>=80.75&&t<82.3)?Vector(0,0,0):Vector(0,0,-4000));MoveProp("r10_exit_collar2",(t>=80.75&&t<82.9)?Vector(0,0,-3000):Vector(4968.7,0,256));' + chr(10) + '    if(t>=81.1&&t<82.5){foreach(nm in ["intro_transfer_scan_upper_0","intro_transfer_scan_fore_0","intro_transfer_scan_head_0","intro_transfer_scan_cone_0","intro_transfer_mount_0","intro_transfer_scan_upper_1","intro_transfer_scan_fore_1","intro_transfer_mount_1"])MoveProp(nm,Vector(0,0,-3000));}' + chr(10) + '    SetLensGlow(t);' + chr(10) + '    MoveProp("intro_turret",Vector(4575,58,Lerp1(r10TurretZ,t)));' + chr(10) + '    {local g=(t>=114.0&&t<116.4);local p=Vector(0,0,-3000);if(g){p=r10GlowPath[0][1];for(local i=0;i<r10GlowPath.len()-1;i++)if(t>=r10GlowPath[i][0]&&t<=r10GlowPath[i+1][0]){local f=(t-r10GlowPath[i][0])/(r10GlowPath[i+1][0]-r10GlowPath[i][0]);p=r10GlowPath[i][1]+(r10GlowPath[i+1][1]-r10GlowPath[i][1])*f;break;};};MoveProp("r10_core_glow",p);}' + chr(10) + '    MoveProp("intro_factory_cube",(t>=99.8 && t<101.9)?Vector(Lerp1(r10LabCube,t),0,256):Vector(0,0,-3000));' + chr(10) + anchor2)
exp_old = 'local exposure=P41_Lerp1([[0,0.58],[22.6,0.58],[23.1,1.0],[33,1.0]],t);'
# r10ce: measured on the top strip, the video's ceiling is 132/108/76/58/36 at 10.0-10.75 s and nearly black (8-15) at
# 10.9-11.1 s; ours read 173/120/66/42/40 and 32-46. The band above the far tile wall is that ceiling seen through the
# chamber glass, so it darkens with it (11.25-11.5 s: video 42-72, ours 79-105).
exp_new = 'local exposure=P41_Lerp1([[0,0.93],[9.6,0.93],[10.0,0.72],[10.3,0.56],[10.5,0.42],[10.6,0.30],[10.75,0.20],[10.9,0.08],[11.1,0.06],[11.6,0.10],[12.4,0.75],[21.2,0.75],[21.7,0.35],[22.05,0.35],[22.35,0.93],[33,0.93]],t);'   # r10bz: the video's ceiling stays lit to 10.3 s and is dark (39-45) at 10.75-11.25 s   # r10ar: bright again as the camera looks up at the iris (22.3 s)
assert txt.count(exp_old) == 1
txt = txt.replace(exp_old, exp_new)
tint_old = '"SetMaterialVar","["+exposure+" "+exposure+" "+exposure+"]"'
tint_new = '"SetMaterialVar","["+exposure+" "+(exposure*0.976)+" "+(exposure*1.01)+"]"'   # the tile texture reads green; the video is neutral
assert txt.count(tint_old) == 1
txt = txt.replace(tint_old, tint_new)
# r10ag: the video's glare is the turret's laser shining into the lens -- a red wedge from the eye down to the bottom of
# the frame, with the rest of the frame lifted to a neutral grey (r10_red_fade is now neutral). Aim the beam at a point
# just in front of and below the lens. The keys are in the v50 turret frame (turret at z 1159); the r10 turret stands
# at 1010, so a key is the wanted world point + 149 in z.
lk_old = """ {t=69.3,p=Vector(4516,-46,1122)},
 {t=69.5,p=Vector(4506,-64,1124)},
 {t=70.0,p=Vector(4498,-80,1146)},
 {t=71.35,p=Vector(4498,-80,1146)}"""
lk_new = """ {t=69.3,p=Vector(4667,13,1179)},
 {t=69.5,p=Vector(4667,13,1179)},
 {t=70.0,p=Vector(4667,13,1179)},
 {t=71.35,p=Vector(4667,13,1179)}"""
assert txt.count(lk_old) == 1
txt = txt.replace(lk_old, lk_new)
# r10as: chrome drop ahead of the camera in the pod-rise run, turning off into the pale crossing tube at 47.1 s
drop_old = 'MoveProp("intro_drop",(t>=44.0 && t<47.4)?Vector(Lerp1(dropTab,t),0,1150):Vector(0,0,-3000));'
drop_new = ('{local p=Vector(0,0,-3000);if(t>=44.0&&t<47.6){for(local i=0;i<r10DropPath.len()-1;i++)if(t>=r10DropPath[i][0]&&t<=r10DropPath[i+1][0])'
            '{local f=(t-r10DropPath[i][0])/(r10DropPath[i+1][0]-r10DropPath[i][0]);p=r10DropPath[i][1]+(r10DropPath[i+1][1]-r10DropPath[i][1])*f;break;};};'
            'MoveProp("intro_drop",p);MoveProp("r10_tube_end",(t<48.85)?Vector(2812,0,1152):Vector(0,0,-3000));'
            'MoveProp("r10_tw_column",(t<58.58)?Vector(3754,0,1272):Vector(0,0,-3000));MoveProp("r10_tw_backwall",(t<58.58)?Vector(0,0,0):Vector(0,0,-4000));'
            '{local cc=(t>=79.75&&t<81.05);local p=Vector(0,0,-3000);if(cc){local q=r10CloseCones[0][1];for(local i=0;i<r10CloseCones.len()-1;i++)if(t>=r10CloseCones[i][0]&&t<=r10CloseCones[i+1][0]){local f=(t-r10CloseCones[i][0])/(r10CloseCones[i+1][0]-r10CloseCones[i][0]);q=r10CloseCones[i][1]+(r10CloseCones[i+1][1]-r10CloseCones[i][1])*f;break;};p=Vector(q.x,q.y,PositionAt(t).z+q.z);};MoveProp("r10_close_cones",p);MoveProp("r10_close_head",p);local pb=(t<80.1)?p:Vector(0,0,-3000);if(t>=71.3&&t<72.35){p=Vector(4820,50,990);pb=p;MoveProp("r10_close_cones",p);MoveProp("r10_close_head",p);};MoveProp("r10_close_arm_a",(t<72.35)?Vector(0,0,-3000):p);MoveProp("r10_close_arm_b",pb);};'
            '{local twt=(t<58.58||t>=63.9);MoveProp("r10_tw_tube_0",twt?Vector(3754,0,1396):Vector(0,0,-3000));MoveProp("r10_tw_tube_1",twt?Vector(3754,0,1640):Vector(0,0,-3000));MoveProp("r10_tw_tube_2",twt?Vector(4010,0,1640):Vector(0,0,-3000));MoveProp("r10_tw_tube_3",twt?Vector(4010,0,1396):Vector(0,0,-3000));};'
            '{local ins=(t>=71.3&&t<72.35);local pet=(t>=71.3&&t<74.7);local pl=ins||(t>=73.4&&t<74.7);MoveProp("r10_inlet_plate",pl?Vector(0,0,0):Vector(0,0,-4000));MoveProp("r10_inlet_ring",ins?Vector(0,0,-3000):Vector(4800,0,984));local hid=Vector(0,0,-3000);local P1=[Vector(4761.8,38.2,950),Vector(4761.8,-38.2,950),Vector(4838.2,-38.2,950),Vector(4838.2,38.2,950)];local P2=[Vector(4838.2,38.2,950),Vector(4838.2,-38.2,950),Vector(4761.8,-38.2,950),Vector(4761.8,38.2,950)];if(pet){MoveProp("r10_inlet_frame_orig",hid);MoveProp("r10_inlet_frame2",Vector(4800,0,938));foreach(i,q in P2)MoveProp("r10_inlet_petal_"+i,q);foreach(i,q in P1)MoveProp("intro_cake_iris_"+i,hid);}else{MoveProp("r10_inlet_frame2",hid);foreach(i,q in P2)MoveProp("r10_inlet_petal_"+i,hid);if(t>=74.7&&t<74.85){MoveProp("r10_inlet_frame_orig",Vector(4800,0,950));foreach(i,q in P1)MoveProp("intro_cake_iris_"+i,q);};};};'
            'MoveProp("r10_cube_sleeve",(t>=48.86&&t<50.6)?Vector(0,0,0):Vector(0,0,-4000));'
            'MoveProp("r10_tu_tubes",(t<67.4)?Vector(4575,58,1340):Vector(0,0,-3000));'
            'MoveProp("r10_exit_collar",(t>=81.0&&t<82.4)?Vector(0,0,-3000):Vector(4967,0,256));'
            '{local tp=(t<67.4);MoveProp("r10_tu_posts",tp?Vector(0,0,0):Vector(0,0,-4000));local ts=(t>=63.87&&t<71.2);MoveProp("r10_tu_screen",ts?Vector(0,0,0):Vector(0,0,-4000));};'
            '{local lsc=(t<102.8);MoveProp("r10_lab_screen",lsc?Vector(0,0,0):Vector(0,0,-4000));MoveProp("r10_lab_pipe_0",lsc?Vector(7480,-134,272):Vector(0,0,-3000));MoveProp("r10_lab_pipe_1",lsc?Vector(7730,-134,272):Vector(0,0,-3000));};'
            '{local dbr=(t>=37.3);MoveProp("r10_rr_down_0",dbr?Vector(2048,-5748,0):Vector(0,0,-3000));MoveProp("r10_rr_down_128",dbr?Vector(2048,-5748,128):Vector(0,0,-3000));MoveProp("r10_rr_down_256",dbr?Vector(2048,-5748,256):Vector(0,0,-3000));};'
            '{local cr=(t>=119.0&&t<121.0);MoveProp("r10_cap_ring_0",cr?Vector(11312,0,128):Vector(0,0,-3000));MoveProp("r10_cap_ring_1",cr?Vector(11360,0,128):Vector(0,0,-3000));};'
            'MoveProp("r10_fac_collar",(t>=97.95&&t<98.08)?Vector(0,0,-3000):Vector(-5420,-6000,0));{local dk=(t>=97.92&&t<98.12);if(dk!=r10CollarDark){EntFire("r10_fac_collar","Color",dk?"70 66 62":"255 255 255",0);r10CollarDark=dk;}};MoveProp("r10_funnel_lo1",(t<86.95)?Vector(5952,150,255):Vector(0,0,-3000));MoveProp("r10_funnel_lo2",(t<86.95)?Vector(5952,150,170):Vector(0,0,-3000));'
            '{local h=(t>=102.8||t<99.0);MoveProp("r10_lab_tur_0",h?Vector(7774.4,-183.4,206.8):Vector(0,0,-3000));MoveProp("r10_lab_tur_1",h?Vector(7854.2,-162.0,206.8):Vector(0,0,-3000));MoveProp("r10_lab_tur_2",h?Vector(7909.8,-116.5,206.8):Vector(0,0,-3000));}}')
assert txt.count(drop_old) == 1
txt = txt.replace(drop_old, drop_new)
txt = txt.replace('cutTab <- [', 'r10CollarDark <- false;r10HazeA <- -1;r10RingDark <- false;' + chr(10) + 'cutTab <- [', 1)
txt = txt.replace('cutTab <- [', 'r10CloseCones <- [[79.75,Vector(4827,0,-150)],[80.0,Vector(4810,0,-95)],[80.25,Vector(4806,0,-56)],[80.5,Vector(4805,0,-52)],[80.75,Vector(4838,-9,-85)],[81.05,Vector(4845,0,-170)]];' + chr(10) + 'cutTab <- [', 1)
txt = txt.replace('cutTab <- [', 'r10DropPath <- [[44.0,Vector(2300,-12,1142)],[45.0,Vector(2470,-12,1142)],[46.0,Vector(2625,-12,1142)],[46.5,Vector(2695,-12,1142)],[47.0,Vector(2752,-12,1142)],[47.2,Vector(2760,-52,1146)],[47.6,Vector(2760,-270,1150)]];' + chr(10) + 'cutTab <- [', 1)
tl_old = '    local turretOn=(t>=67.2 && t<71.35)?1:0;'
assert txt.count(tl_old) == 1
txt = txt.replace(tl_old, '    local turretOn=(t>=67.2 && t<69.4)?1:0;')   # r10bs: the video shows only the glare from 69.5 s
sh_old = '    local shaftOn=t<79.9?1:0;'
assert txt.count(sh_old) == 1
txt = txt.replace(sh_old, '    local shaftOn=(t>=72.25 && t<79.6)?1:0;')   # r10bs: no scanner lasers in the turret room shot
cake_old = 'MoveProp("intro_cake",t<74.5?Vector(4814,14,956):Vector(0,0,-3000));'
assert txt.count(cake_old) == 1
txt = txt.replace(cake_old, 'MoveProp("intro_cake",(t<74.5&&!(t>=71.3&&t<72.35))?Vector(4814,14,956):Vector(0,0,-3000));')
# r10ce: the opening's light flicker (6.8-7.85 s) is a screen-overlay sequence (tools/make_flicker.py); the global fade
# now holds 92 until 6.8 s and the overlay does the rest
fl_old = 'if(t<6.8)fadeAlpha=92;else if(t<7.05)fadeAlpha=92*(7.05-t)/0.25;'
assert txt.count(fl_old) == 1
txt = txt.replace(fl_old, 'if(t<6.85)fadeAlpha=92;')   # r10cf: the video stays dark to 6.85 s
txt = txt.replace('cutTab <- [', 'r10FlickOn <- false;function SetFlicker(t){local g=(t>=6.85&&t<7.85);if(g==r10FlickOn)return;EntFire("r10_flicker_ov",g?"StartOverlays":"StopOverlays","",0);r10FlickOn=g;}' + chr(10) + 'cutTab <- [', 1)
txt = txt.replace('cutTab <- [', 'r10Veil <- [[77.3,0],[77.42,110],[77.5,186],[77.75,186],[77.8,125],[78.5,125],[78.6,150],[78.7,181],[79.3,181],[79.4,115],[79.7,115],[79.8,0]];r10VeilA <- 0;' + chr(10) +
    'function SetVeil(t){local a=(t>=77.3&&t<79.8)?Lerp1(r10Veil,t).tointeger():0;if(a==r10VeilA)return;' +
    'local f=Entities.FindByName(null,"r10_veil_fade");if(f==null)return;f.__KeyValueFromString("renderamt",""+a);' +
    'EntFire("r10_veil_fade","Fade","",0);r10VeilA=a;}' + chr(10) + 'cutTab <- [', 1)
sq_old = '    SetRedHaze(t);' + chr(10)
assert txt.count(sq_old) == 1
txt = txt.replace(sq_old, sq_old + '    MoveProp("r10_sl_shaft",(t>=86.21&&t<87.1)?Vector(0,0,0):Vector(0,0,-4000));' + chr(10) + '    {local rd=(t>=36.33&&t<36.7);if(rd!=r10RingDark){EntFire("r10_rr_ring_near","Color",rd?"62 62 64":"255 255 255",0);r10RingDark=rd;}};' + chr(10) + '    MoveProp("r10_lab_white",(t>=103.0&&t<105.31)?Vector(0,0,0):Vector(0,0,-4000));' + chr(10) + '    MoveProp("r10_inc_ring2",(t>=111.5&&t<113.5)?Vector(0,0,0):Vector(0,0,-4000));' + chr(10) + '    MoveProp("r10_pod_dark",(t>=43.3&&t<47.3)?Vector(0,0,0):Vector(0,0,-4000));MoveProp("r10_pod_rails",(t>=43.3&&t<48.6)?Vector(0,0,0):Vector(0,0,-4000));' + chr(10) + '    MoveProp("r10_rr_black",(t>=33.8&&t<35.4)?Vector(0,0,0):Vector(0,0,-4000));' + chr(10) + '    SetVeil(t);' + chr(10) + '    {local sq=(t>=75.4&&t<80.75);MoveProp("r10_sc_rings",sq?Vector(0,0,0):Vector(0,0,-4000));foreach(z in [584,664,744,824,904])MoveProp("r10_sh_ring_"+z,sq?Vector(0,0,-3000):Vector(4800,0,z));}' + chr(10))
sf_old = '    SetLensGlow(t);' + chr(10)
assert txt.count(sf_old) == 1
txt = txt.replace(sf_old, sf_old + '    SetFlicker(t);' + chr(10))
dst.write_text(txt)
print('knots', len(rows), '->', len(knots), 'written', dst)
