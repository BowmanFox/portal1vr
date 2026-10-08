"""Adds/overrides camera reference-angle knots in the v50 director (writes a copy)."""
import re, sys, os
from pathlib import Path
src = Path(os.path.expanduser('~/mnt/revision9/r10/base/director_v50.nut'))   # untouched v50 director
dst = Path(sys.argv[1])
edits = {  # time: (pitch, yaw, roll)
    # "16" wall: aimed so the sign sits where the video has it (top centre at 72.5-73.25 s, frame centre at 73.5 s);
    # solved from the camera path and the sign's position (4976, -30, 1298)
    72.5: (3.0, 8.0, 0.0), 72.75: (-4.0, 10.0, 0.0), 73.0: (-12.0, 11.0, 0.0), 73.25: (-20.0, 11.0, 0.0),
    73.5: (-54.0, 15.0, 0.0),  # then drops into the shaft at 74 s
    # sludge test room: the video looks almost straight down onto the chamber while the tube carries
    # the camera across it, with the copper collar ahead at the top of the frame
    # r10x: the video frames the whole chamber -- the north walkway band sits mid-frame -- so the camera looks
    # about 45 degrees down (60 hid the far walkway, 30 showed too much far wall); at 90 s it lifts to the black-tiled wall and up the copper exit tube.
    86.5: (50.0, 70.0, 0.0), 87.0: (48.0, 85.0, 0.0), 87.5: (45.0, 90.0, 0.0),
    88.0: (44.0, 90.0, 0.0), 89.0: (44.0, 90.0, 0.0), 89.5: (42.0, 90.0, 0.0),
    90.0: (38.0, 90.0, 0.0), 90.25: (5.0, 90.0, 0.0), 90.5: (-35.0, 60.0, 0.0), 91.0: (-20.0, 0.0, 0.0),
    # turret lift (64.5-67 s): look up at the collar, then down into the floor ring the turret rises from,
    # then level with the turret (the camera dips to its eye height, see pos_z below)
    # r10ah: the video comes over the top of the turret-lift collar and looks down on it (63.4-64.8 s: the dark
    # platform with tubes hanging under it, the "16" sign at the right), drops through it looking straight down at
    # the floor ring (65-65.6 s), and watches the turret rise toward the lens (66-67 s)
    63.5: (10.0, 20.0, 0.0), 63.75: (40.0, 5.0, 0.0), 64.0: (48.0, 3.0, 0.0), 64.25: (55.0, 2.0, 0.0), 64.5: (65.0, 0.0, 0.0),
    64.75: (75.0, 0.0, 0.0), 65.0: (85.0, 10.0, 0.0), 65.5: (88.0, 20.0, 0.0), 66.0: (85.0, 30.0, 0.0),
    66.5: (45.0, 45.0, 0.0), 67.0: (0.0, 46.0, 0.0),
    # r10af: the video holds the turret front-on and centred through the lens glare (69.5-71.2 s), the camera rising
    # only slightly; it leaves for the "16" inlet in the last 0.8 s (see pos_x/pos_z)
    70.5: (-9.0, 63.0, 0.0), 71.0: (-8.0, 62.0, 0.0), 71.25: (-7.0, 50.0, 0.0), 71.5: (-8.0, 25.0, 0.0),
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
shaft_z = [(77.0, 835.0), (78.0, 790.0), (79.0, 720.0), (79.5, 660.0), (80.0, 600.0), (80.5, 540.0), (81.0, 515.0)]
# r10ah: sludge chamber (87-90 s) -- the video is lower and closer over the walkways than the tube (z 256)
sludge_z = {86.5: 246.0, 86.75: 226.0, 87.0: 206.0, 87.25: 192.0, 87.5: 186.0, 87.75: 186.0, 88.0: 186.0, 88.25: 186.0,
            88.5: 186.0, 88.75: 186.0, 89.0: 186.0, 89.25: 186.0, 89.5: 188.0, 89.75: 196.0, 90.0: 210.0, 90.25: 232.0, 90.5: 250.0}
descent = {63.5: (4150, 20, 1420), 63.75: (4300, 40, 1510), 64.0: (4420, 50, 1540), 64.25: (4480, 52, 1500), 64.5: (4510, 52, 1430),
           64.75: (4530, 40, 1380), 65.0: (4540, 30, 1320), 65.25: (4542, 20, 1280), 65.5: (4544, 10, 1240), 65.75: (4544, 5, 1195),
           66.0: (4544, 0, 1150), 66.25: (4544, 0, 1105), 66.5: (4544, 0, 1060), 66.75: (4544, 0, 1035), 67.0: (4544, 0, 1010),
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
    if 77.0 < t <= 81.0:
        return '{t=%s,p=Vector(%s,%s,%.8f)}' % (m.group(1), m.group(2), m.group(3), lerp(shaft_z, t))
    for tab in (sludge_z,):
        for k, nz in tab.items():
            if abs(t - k) < 1e-4: return '{t=%s,p=Vector(%s,%s,%.8f)}' % (m.group(1), m.group(2), m.group(3), nz)
    return m.group(0)
newpos = re.sub(r'\{t=([-\d.]+),p=Vector\(([-\d.]+),([-\d.]+),([-\d.]+)\)\}', repl, txt[ps:pe])
txt = txt[:ps] + newpos + txt[pe:]
fades = [[63.2,63.35,0,170],[63.35,63.6,170,0],[52.45,52.55,0,110],[52.55,52.68,110,0],[38.70,38.9388,0,255],[39.2725,39.60,255,0],[53.83,54.1206,0,255],[54.8547,55.27,240,240],
         [55.27,55.47,240,0],[82.55,83.1829,40,255],[84.5510,84.97,255,0],[95.33,95.7288,0,255],
         [104.97,105.305,0,255],[109.40,109.7094,0,255],[109.8428,110.6,255,0]]
anchor = '    SetScreenBlack(fadeAlpha);'
assert txt.count(anchor) == 1
txt = txt.replace(anchor, '    foreach(f in r10Fades) if(t>=f[0] && t<f[1]){local k=(t-f[0])/(f[1]-f[0]);local a=(f[2]+(f[3]-f[2])*k).tointeger();if(a>fadeAlpha)fadeAlpha=a;}\n' + anchor)
txt = txt.replace('cutTab <- [', 'r10Fades <- ' + str(fades).replace(' ', '') + ';\ncutTab <- [', 1)
# the cube rides ahead in the lab tube (100-101.5 s) instead of sitting where the camera passes through it
txt = txt.replace('cutTab <- [', 'r10LabCube <- [[99.8,7565],[100,7575],[100.5,7600],[101,7625],[101.5,7640],[101.9,7900]];' + chr(10) + 'cutTab <- [', 1)
# cube passage (52-53.8 s): the video dissolves from the far cube to a close one at ~52.55 s; the cube jumps
# closer under a short dip instead of drifting slowly toward the camera
cube_old = 'for(local i=0;i<4;i++)MoveProp("intro_cube_"+i,t<55.5?Vector(3480+i*62-(cubeTime-52)*25,0,1152):Vector(0,0,-3000));'
cube_new = 'for(local i=0;i<4;i++)MoveProp("intro_cube_"+i,t<55.5?Vector(Lerp1(r10CubeX,t)+i*62,0,1152):Vector(0,0,-3000));'
assert txt.count(cube_old) == 1
txt = txt.replace(cube_old, cube_new)
txt = txt.replace('cutTab <- [', 'r10CubeX <- [[51,3420],[52,3394],[52.5,3437],[52.54,3437],[52.56,3295],[53.0,3339],[53.5,3386],[53.83,3418],[55.5,3480]];' + chr(10) + 'cutTab <- [', 1)
txt = txt.replace('cutTab <- [', 'r10TurretZ <- [[66.15,820],[66.9,1010]];' + chr(10) + 'cutTab <- [', 1)
# turret laser in the lens (69.3-71.3 s): the video washes the frame pink; a second env_fade tints the screen red
txt = txt.replace('cutTab <- [', 'r10Red <- [[69.2,0],[69.5,80],[70.2,104],[70.9,104],[71.3,0]];r10RedAlpha <- 0;' + chr(10) +
    'function SetRedHaze(t){local a=(t>=69.2&&t<71.3)?Lerp1(r10Red,t).tointeger():0;if(a==r10RedAlpha)return;' +
    'local f=Entities.FindByName(null,"r10_red_fade");if(f==null)return;f.__KeyValueFromString("renderamt",""+a);' +
    'EntFire("r10_red_fade","Fade","",0);r10RedAlpha=a;}' + chr(10) + 'cutTab <- [', 1)
anchor2 = '    SetPursuitShaft(t);'
assert txt.count(anchor2) == 1
txt = txt.replace(anchor2, '    SetRedHaze(t);' + chr(10) + '    MoveProp("intro_turret",Vector(4575,58,Lerp1(r10TurretZ,t)));' + chr(10) + '    MoveProp("intro_factory_cube",(t>=99.8 && t<101.9)?Vector(Lerp1(r10LabCube,t),0,256):Vector(0,0,-3000));' + chr(10) + anchor2)
exp_old = 'local exposure=P41_Lerp1([[0,0.58],[22.6,0.58],[23.1,1.0],[33,1.0]],t);'
exp_new = 'local exposure=P41_Lerp1([[0,0.93],[9.6,0.93],[10.3,0.40],[11.6,0.40],[12.4,0.75],[21.2,0.75],[21.9,0.30],[22.6,0.30],[23.1,0.93],[33,0.93]],t);'
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
dst.write_text(txt)
print('knots', len(rows), '->', len(knots), 'written', dst)
