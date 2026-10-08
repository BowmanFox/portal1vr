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
    64.5: (-15.0, 95.0, 0.0), 65.0: (15.0, 10.0, 0.0), 65.5: (34.0, 11.0, 0.0), 66.0: (38.0, 12.0, 0.0),
    66.5: (40.0, 28.0, 0.0), 67.0: (0.0, 46.0, 0.0),
    # tower entrance: the video keeps the pale collar centred and looks slightly up, then tilts up the tower
    56.0: (-3.0, 2.0, 0.0), 56.5: (-4.0, 0.0, 0.0), 57.0: (-6.0, -2.0, 0.0), 57.5: (-12.0, 0.0, 0.0), 58.0: (-30.0, 22.0, 0.0),
    # lab: the video turns right toward the white test chamber and its hanging turrets
    102.5: (-4.0, -6.0, 0.0), 103.0: (2.0, -30.0, 0.0), 103.5: (6.0, -42.0, 0.0),
    104.0: (12.0, -55.0, 0.0), 104.5: (18.0, -75.0, 0.0), 105.0: (22.0, -100.0, 0.0),   # onto the turret wall, not past it
    # 107-109.5 s: the video looks steeply down into the white test chamber before the incinerator cut
    107.0: (30.0, -65.0, 10.0), 107.5: (55.0, -85.0, 15.0), 108.0: (65.0, -100.0, 20.0),
    108.5: (75.0, -100.0, 20.0), 109.0: (80.0, -100.0, 20.0), 109.3: (82.0, -100.0, 20.0), 109.70928: (85.0, -100.0, 20.0),
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
# camera height for the turret lift: dips from the tube (1152) to the turret's eye level and climbs back by 72 s
pos_z = [(65.5, 1152.0), (66.0, 1125.0), (66.25, 1095.0), (66.5, 1060.0), (67.0, 1010.0), (67.5, 1000.0),
         (70.0, 1000.0), (70.5, 1040.0), (71.0, 1090.0), (71.5, 1130.0), (72.0, 1152.0)]
def zat(t):
    for (t0, z0), (t1, z1) in zip(pos_z, pos_z[1:]):
        if t0 <= t <= t1: return z0 + (z1 - z0) * (t - t0) / (t1 - t0)
    return None
ps = txt.index('positions <- ['); pe = txt.index('];', ps)
def repl(m):
    t = float(m.group(1)); z = zat(t)
    if z is None or not (65.5 < t < 72.0): return m.group(0)
    return '{t=%s,p=Vector(%s,%s,%.8f)}' % (m.group(1), m.group(2), m.group(3), z)
newpos = re.sub(r'\{t=([-\d.]+),p=Vector\(([-\d.]+),([-\d.]+),([-\d.]+)\)\}', repl, txt[ps:pe])
txt = txt[:ps] + newpos + txt[pe:]
fades = [[52.45,52.55,0,110],[52.55,52.68,110,0],[38.70,38.9388,0,255],[39.2725,39.60,255,0],[53.83,54.1206,0,255],[54.8547,55.27,240,240],
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
txt = txt.replace('cutTab <- [', 'r10Red <- [[69.2,0],[69.5,60],[70.2,110],[70.9,110],[71.3,0]];r10RedAlpha <- -1;' + chr(10) +
    'function SetRedHaze(t){local a=(t>=69.2&&t<71.3)?Lerp1(r10Red,t).tointeger():0;if(a==r10RedAlpha)return;' +
    'local f=Entities.FindByName(null,"r10_red_fade");if(f==null)return;f.__KeyValueFromString("renderamt",""+a);' +
    'EntFire("r10_red_fade","Fade","",0);r10RedAlpha=a;}' + chr(10) + 'cutTab <- [', 1)
anchor2 = '    SetPursuitShaft(t);'
assert txt.count(anchor2) == 1
txt = txt.replace(anchor2, '    SetRedHaze(t);' + chr(10) + '    MoveProp("intro_turret",Vector(4575,58,Lerp1(r10TurretZ,t)));' + chr(10) + '    MoveProp("intro_factory_cube",(t>=99.8 && t<101.9)?Vector(Lerp1(r10LabCube,t),0,256):Vector(0,0,-3000));' + chr(10) + anchor2)
dst.write_text(txt)
print('knots', len(rows), '->', len(knots), 'written', dst)
