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
          58.5: (-44.0, -8.0, 0.0), 58.57: (-45.0, -8.0, 0.0), 58.58: (-16.0, 58.0, 0.0)}   # r10au: tilts up faster (collar at the bottom edge by 58.25 s)
knots.update(edits2)
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
shaft_z = [(77.0, 835.0), (78.0, 790.0), (79.0, 720.0), (79.5, 660.0), (80.0, 610.0), (80.5, 590.0), (81.0, 580.0), (81.5, 580.0), (82.0, 580.0), (82.25, 540.0), (82.5, 400.0)]   # r10az: hover higher over the iris (video 81-82 s: the iris ~45% of the frame width)   # r10ao: hover over the iris until 82.2 s, then drop through it
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
           63.87: (4390.0, 45.0, 1535.0)}
kn = [(float(a), (float(b), float(c), float(d))) for a, b, c, d in re.findall(r'\{t=([-\d.]+),p=Vector\(([-\d.]+),([-\d.]+),([-\d.]+)\)\}', newpos)]
kd = dict(kn)
for k, q in pos_set.items():
    for t0 in list(kd):
        if abs(t0 - k) < 1e-4: del kd[t0]
    kd[k] = q
newpos = 'positions <- [\n' + ',\n'.join('{t=%.8f,p=Vector(%.8f,%.8f,%.8f)}' % ((t,) + kd[t]) for t in sorted(kd)) + '\n'
txt = txt[:ps] + newpos + txt[pe:]
fades = [[62.9,63.05,0,235],[63.05,63.3,235,0],[52.45,52.55,0,110],[52.55,52.68,110,0],[38.70,38.9388,0,255],[39.2725,39.60,255,0],[53.83,54.1206,0,255],[54.8547,55.27,240,240],
         [55.27,55.47,240,0],[82.55,83.1829,40,255],[84.5510,84.97,255,0],[95.33,95.7288,0,255],
         [104.97,105.305,0,255],[56.37,56.52,0,75],[56.52,56.70,75,0],[58.42,58.58,0,100],[58.58,58.72,100,0],[109.40,109.7094,0,255],[109.8428,110.6,255,0],[123.60,123.70,0,150],[123.70,123.82,150,0],[102.72,102.80,0,110],[102.80,102.90,110,0],[63.78,63.865,0,150],[63.865,63.97,150,0]]
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
txt = txt.replace('cutTab <- [', 'r10Red <- [[69.2,0],[69.5,80],[70.2,104],[70.9,104],[71.3,0]];r10RedAlpha <- 0;' + chr(10) +
    'function SetRedHaze(t){local a=(t>=69.2&&t<71.3)?Lerp1(r10Red,t).tointeger():0;if(a==r10RedAlpha)return;' +
    'local f=Entities.FindByName(null,"r10_red_fade");if(f==null)return;f.__KeyValueFromString("renderamt",""+a);' +
    'EntFire("r10_red_fade","Fade","",0);r10RedAlpha=a;}' + chr(10) +
    'r10GlowOn <- false;function SetLensGlow(t){local g=(t>=69.4&&t<71.3);if(g==r10GlowOn)return;EntFire("laser_turret_glow",g?"TurnOn":"TurnOff","",0);r10GlowOn=g;}' + chr(10) + 'cutTab <- [', 1)
anchor2 = '    SetPursuitShaft(t);'
assert txt.count(anchor2) == 1
txt = txt.replace(anchor2, '    SetRedHaze(t);' + chr(10) + '    SetLensGlow(t);' + chr(10) + '    MoveProp("intro_turret",Vector(4575,58,Lerp1(r10TurretZ,t)));' + chr(10) + '    {local g=(t>=114.0&&t<116.4);local p=Vector(0,0,-3000);if(g){p=r10GlowPath[0][1];for(local i=0;i<r10GlowPath.len()-1;i++)if(t>=r10GlowPath[i][0]&&t<=r10GlowPath[i+1][0]){local f=(t-r10GlowPath[i][0])/(r10GlowPath[i+1][0]-r10GlowPath[i][0]);p=r10GlowPath[i][1]+(r10GlowPath[i+1][1]-r10GlowPath[i][1])*f;break;};};MoveProp("r10_core_glow",p);}' + chr(10) + '    MoveProp("intro_factory_cube",(t>=99.8 && t<101.9)?Vector(Lerp1(r10LabCube,t),0,256):Vector(0,0,-3000));' + chr(10) + anchor2)
exp_old = 'local exposure=P41_Lerp1([[0,0.58],[22.6,0.58],[23.1,1.0],[33,1.0]],t);'
exp_new = 'local exposure=P41_Lerp1([[0,0.93],[9.6,0.93],[10.3,0.40],[11.6,0.40],[12.4,0.75],[21.2,0.75],[21.7,0.35],[22.05,0.35],[22.35,0.93],[33,0.93]],t);'   # r10ar: bright again as the camera looks up at the iris (22.3 s)
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
lk_new = """ {t=69.3,p=Vector(4549,9,1142)},
 {t=69.5,p=Vector(4549,9,1142)},
 {t=70.0,p=Vector(4549,9,1142)},
 {t=71.35,p=Vector(4549,9,1142)}"""
assert txt.count(lk_old) == 1
txt = txt.replace(lk_old, lk_new)
# r10as: chrome drop ahead of the camera in the pod-rise run, turning off into the pale crossing tube at 47.1 s
drop_old = 'MoveProp("intro_drop",(t>=44.0 && t<47.4)?Vector(Lerp1(dropTab,t),0,1150):Vector(0,0,-3000));'
drop_new = ('{local p=Vector(0,0,-3000);if(t>=44.0&&t<47.6){for(local i=0;i<r10DropPath.len()-1;i++)if(t>=r10DropPath[i][0]&&t<=r10DropPath[i+1][0])'
            '{local f=(t-r10DropPath[i][0])/(r10DropPath[i+1][0]-r10DropPath[i][0]);p=r10DropPath[i][1]+(r10DropPath[i+1][1]-r10DropPath[i][1])*f;break;};};'
            'MoveProp("intro_drop",p);MoveProp("r10_tube_end",(t<48.85)?Vector(2812,0,1152):Vector(0,0,-3000));'
            'MoveProp("r10_tw_column",(t<58.58)?Vector(3754,0,1272):Vector(0,0,-3000));MoveProp("r10_tw_backwall",(t<58.58)?Vector(0,0,0):Vector(0,0,-4000));'
            '{local twt=(t<58.58||t>=63.9);MoveProp("r10_tw_tube_0",twt?Vector(3754,0,1396):Vector(0,0,-3000));MoveProp("r10_tw_tube_1",twt?Vector(3754,0,1640):Vector(0,0,-3000));MoveProp("r10_tw_tube_2",twt?Vector(4010,0,1640):Vector(0,0,-3000));MoveProp("r10_tw_tube_3",twt?Vector(4010,0,1396):Vector(0,0,-3000));};'
            '{local lsc=(t<102.8);MoveProp("r10_lab_screen",lsc?Vector(0,0,0):Vector(0,0,-4000));MoveProp("r10_lab_pipe_0",lsc?Vector(7480,-134,272):Vector(0,0,-3000));MoveProp("r10_lab_pipe_1",lsc?Vector(7730,-134,272):Vector(0,0,-3000));};'
            '{local dbr=(t>=37.3);MoveProp("r10_rr_down_0",dbr?Vector(2048,-5748,0):Vector(0,0,-3000));MoveProp("r10_rr_down_128",dbr?Vector(2048,-5748,128):Vector(0,0,-3000));MoveProp("r10_rr_down_256",dbr?Vector(2048,-5748,256):Vector(0,0,-3000));};'
            '{local cr=(t>=119.0&&t<121.0);MoveProp("r10_cap_ring_0",cr?Vector(11312,0,128):Vector(0,0,-3000));MoveProp("r10_cap_ring_1",cr?Vector(11360,0,128):Vector(0,0,-3000));};'
            '{local dk=(t>=97.92&&t<98.12);if(dk!=r10CollarDark){EntFire("r10_fac_collar","Color",dk?"70 66 62":"255 255 255",0);r10CollarDark=dk;}};MoveProp("r10_funnel_lo1",(t<86.95)?Vector(5952,150,255):Vector(0,0,-3000));MoveProp("r10_funnel_lo2",(t<86.95)?Vector(5952,150,170):Vector(0,0,-3000));'
            '{local h=(t>=102.8||t<99.0);MoveProp("r10_lab_tur_0",h?Vector(7774.4,-183.4,206.8):Vector(0,0,-3000));MoveProp("r10_lab_tur_1",h?Vector(7854.2,-162.0,206.8):Vector(0,0,-3000));MoveProp("r10_lab_tur_2",h?Vector(7909.8,-116.5,206.8):Vector(0,0,-3000));}}')
assert txt.count(drop_old) == 1
txt = txt.replace(drop_old, drop_new)
txt = txt.replace('cutTab <- [', 'r10CollarDark <- false;' + chr(10) + 'cutTab <- [', 1)
txt = txt.replace('cutTab <- [', 'r10DropPath <- [[44.0,Vector(2300,-12,1142)],[45.0,Vector(2470,-12,1142)],[46.0,Vector(2625,-12,1142)],[46.5,Vector(2695,-12,1142)],[47.0,Vector(2752,-12,1142)],[47.2,Vector(2760,-52,1146)],[47.6,Vector(2760,-270,1150)]];' + chr(10) + 'cutTab <- [', 1)
dst.write_text(txt)
print('knots', len(rows), '->', len(knots), 'written', dst)
