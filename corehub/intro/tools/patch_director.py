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
    86.5: (45.0, 70.0, 0.0), 87.0: (58.0, 85.0, 0.0), 87.5: (60.0, 90.0, 0.0),
    88.0: (60.0, 90.0, 0.0), 89.0: (60.0, 90.0, 0.0), 89.5: (57.0, 90.0, 0.0),
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
anchor2 = '    SetPursuitShaft(t);'
assert txt.count(anchor2) == 1
txt = txt.replace(anchor2, '    MoveProp("intro_factory_cube",(t>=99.8 && t<101.9)?Vector(Lerp1(r10LabCube,t),0,256):Vector(0,0,-3000));' + chr(10) + anchor2)
dst.write_text(txt)
print('knots', len(rows), '->', len(knots), 'written', dst)
