"""Opening room (0-21.7 s): the relaxation chamber as the r10dm base has it, with the base director's camera
(fov 60, checked against the film: the room's edges, the window frame and the floor tiles fall on the film's
within a few pixels at 12-21 s). The models it places were lost with the old PC; models/opening.py rebuilds them
under their old names, so most of this scene lives there. Here only what the map / director needs besides:

- the hanging cable (p41_intro_ceiling_wire) falls at 6.8-7.15 s; after that the film never shows it again, but the
  rigid fallen model would float across the pod (its length turns horizontal): parked out of sight after 7.2 s.
- tones the film shows and the base map's stock materials do not (sampled on the film, flat unlit materials):
  the glazing frame and bars of the chamber are light (film 186-220, frame_steel / rail_light rendered 50-63), its
  frosted stripes faint (alpha 0.45 -> 0.2); the south side (seen only from below at 5-9 s) is dark in the film:
  its bars dark, its nearly clear glass (alpha 0.08) a dark veil (0.3, alpha 0.85) over the bright outer ceiling;
  the debris heaps by the north and east glass are light grey planks (black_wall_metal_001a rendered 30-35); the
  tops of the south / west walls over the pod, seen from below at 5-9 s, are mid grey (film 96-99; 'border' and
  black_wall_metal rendered 31-34).
- the room east of the chamber (seen square-on through the glass at 16.5-21.7 s): its dust floor and rubble are
  lighter south of y 40 (north of it the film shows that glass dark at 14-16 s, seen obliquely).
- the round door under the exit signs (11-15.5 s) is the own model r11_op_door instead of the stock one (see door()).
- the ceiling housing (p41_preview_housing_mesh, 10-11.3 s) is tinted with the ceiling's exposure curve.
"""
import numpy as np
from lib import vmfedit as E
from lib.gen import mat

F = 'corehub_intro/r11_op/'


def bmat(name, color):
    """brush material (UnlitGeneric flat colour) -> path"""
    mat(name, color, folder='corehub_intro/r11_op', model=False)
    return F + name


OP_CODE = r'''
opHousingTint <- -1;
function Op_Update(t) {
    if(t>=32.5)return;
    if(t>=7.2){local w=Entities.FindByName(null,"p41_intro_ceiling_wire");if(w!=null)w.SetOrigin(Vector(-12791.4,-201.4,-3000));}
    // the ceiling housing darkens with the ceiling's exposure (same curve as P41_Update)
    local ex=P41_Lerp1([[0,0.93],[9.6,0.93],[10.0,0.72],[10.3,0.56],[10.5,0.42],[10.6,0.30],[10.75,0.20],[10.9,0.08],[11.1,0.06],[11.6,0.10],[12.4,0.75],[21.2,0.75],[21.7,0.35],[22.05,0.35],[22.35,0.93],[33,0.93]],t);
    local c=(255.0*ex/0.93).tointeger(); if(c>255)c=255; if(c<0)c=0;
    if(c!=opHousingTint){opHousingTint=c;local h=Entities.FindByName(null,"p41_preview_housing_mesh");if(h!=null)h.__KeyValueFromString("rendercolor",c+" "+c+" "+c);}
}
'''

AREA = ((-13600.0, -500.0, -60.0), (-12400.0, 400.0, 300.0))
FLOOR_Y1 = 40.0          # only the part seen square-on through the east glass at 16.5-21.7 s (north of it the film
                         # shows the glass dark at 14-16 s, seen obliquely)


def in_area(lo, hi):
    return all(hi[i] >= AREA[0][i] and lo[i] <= AREA[1][i] for i in range(3))


def side_normal(side):
    n = side.normal(); return np.array([n.x, n.y, n.z])


def retexture(v):
    frame = bmat('r11_op_frame', (0.80, 0.80, 0.79))
    frame_d = bmat('r11_op_frame_d', (0.22, 0.22, 0.22))         # the south side, seen from below in shadow at 5-9 s
    side = 'corehub_intro/r11_op/r11_op_sideglass'
    mat('r11_op_sideglass', (0.30, 0.30, 0.30), folder='corehub_intro/r11_op', model=False, alpha=0.85, translucent=True, nocull=True)
    frost = 'corehub_intro/r11_op/r11_op_frost'
    mat('r11_op_frost', (0.62, 0.63, 0.63), folder='corehub_intro/r11_op', model=False, alpha=0.2, translucent=True, nocull=True)
    deb = [bmat('r11_op_deb%d' % k, c) for k, c in enumerate([(0.38, 0.38, 0.37), (0.52, 0.52, 0.51), (0.63, 0.63, 0.62), (0.73, 0.73, 0.72)])]
    walltop = bmat('r11_op_walltop', (0.38, 0.38, 0.38))
    trim = bmat('r11_op_trim', (0.58, 0.58, 0.57))
    light = np.array([0.35, -0.45, 0.82]); light /= np.linalg.norm(light)
    n_frame = n_deb = n_wall = 0
    for e in [v.spawn] + list(v.entities):
        for s in e.solids:
            lo, hi = E.solid_bounds(s)
            if not in_area(lo, hi): continue
            mats = {x.mat.lower() for x in s.sides}
            if mats == {'corehub_intro/p9_room_metric_v13/rail_light'}:          # glazing bars (light in the film)
                south = hi[1] < -230
                for x in s.sides:          # their undersides are what the camera sees at 5-9 s (dark in the film)
                    x.mat = frame_d if (south or side_normal(x)[2] < -0.5) else frame
                n_frame += 1
            elif 'corehub_intro/p9_room_metric_v13/room_side_clear' in mats:     # south glass: the film is dark beyond it
                for x in s.sides:
                    if x.mat.lower() == 'corehub_intro/p9_room_metric_v13/room_side_clear': x.mat = side
            elif 'corehub_intro/p9_room_metric_v13/room_frosted_engraving' in mats:   # frosted stripes: faint in the film
                for x in s.sides:
                    if x.mat.lower() == 'corehub_intro/p9_room_metric_v13/room_frosted_engraving': x.mat = frost
            elif e['targetname', ''] == 'p41_p9_exterior_glazing_seal':
                south = hi[1] < -230
                for x in s.sides:
                    if 'frame_steel' in x.mat.lower(): x.mat = frame_d if south else frame
                n_frame += 1
            elif mats == {'metal/black_wall_metal_001a'} or (mats == {'concrete/concrete_modular_floor001a'} and max(hi[i] - lo[i] for i in range(3)) < 160):
                # debris heaps by the glass: light grey planks in the film (125-135 lit, 65-75 in shadow)
                for x in s.sides:
                    d = float(side_normal(x) @ light) * 0.5 + 0.5
                    x.mat = deb[min(3, int(d * 4))]
                n_deb += 1
            elif 'metal/black_wall_metal_001a' in mats and 'tools/toolsnodraw' in mats:   # wall tops round the pod
                for x in s.sides:
                    if 'black_wall_metal' in x.mat.lower(): x.mat = trim
                n_wall += 1
            elif any(m.endswith('/border') for m in mats) and 'tools/toolsnodraw' in mats:
                for x in s.sides:
                    if x.mat.lower().endswith('/border'): x.mat = walltop
                n_wall += 1
    assert n_frame == 8 + 15 and n_deb >= 60 and n_wall >= 8, (n_frame, n_deb, n_wall)
    # the room east of the chamber, seen through the glass at 16.5-21.7 s: its floor is light grey in the film (128-140
    # through the glass, i.e. about 0.55 behind it; the dust_* floor rendered 70-90), its rubble light too
    floor = bmat('r11_op_outfloor', (0.52, 0.52, 0.51))
    n_floor = 0
    for e in v.entities:
        if e['classname'] != 'func_detail': continue
        for s in e.solids:
            lo, hi = E.solid_bounds(s)
            if lo[0] < -12790 or lo[0] > -11000 or hi[1] < -1100 or lo[1] > FLOOR_Y1 or hi[2] > 60: continue
            changed = False
            for x in s.sides:
                m = x.mat.lower()
                if '/p9_exterior_v2/dust_' in m: x.mat = floor; changed = True
                elif '/rubble_u' in m:
                    dd = float(side_normal(x) @ light) * 0.5 + 0.5
                    x.mat = deb[min(3, int(dd * 4))]; changed = True
            n_floor += changed
    assert n_floor > 100, n_floor


def door(v):
    """the stock round door (drawn lying under the floor by the preview) becomes the own model r11_op_door, centred
    where the film shows it: 46 px under the exit signs at 12.5 s -> world (-13079, 1075, 2), radius 80, on the wall
    through the signs (normal yaw -53)"""
    e = E.one(v, model='models/props/portaldoor.mdl')
    e['model'] = 'models/corehub_intro/r11_op_door.mdl'
    e['origin'] = E.fmt((-13080.0, 1074.5, 4.0))
    e['angles'] = '0 -53 0'
    e['modelscale'] = '1'


def apply(v, d):
    retexture(v)
    door(v)
    d.append(OP_CODE)
    d.hook('Op_Update(t);', late=True)
