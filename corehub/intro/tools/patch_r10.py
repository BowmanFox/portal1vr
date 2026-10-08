"""r10 patch on top of the newest pursuit9 map (capsule-follow v50).

Splits the old shared middle hall into separate rooms with full-height
partition walls that only open where the tube passes (holes are derived from
the tube's own ring props and the camera path), turns the turret backdrop to
face the camera the way the video frames it, and adds a few unfinished/WIP
dev-textured surfaces. Writes r10/build/<name>.vmf; the input is never changed.
"""
import json, math, os, sys
from pathlib import Path
from srctools import VMF, Vec

HOME = Path(os.path.expanduser('~'))
OUT = HOME / 'mnt/outputs/Corehub-Intro'
R10 = HOME / 'mnt/revision9/r10'
# Always patch the untouched v50 VMF (outputs/ holds the published r10 build once publish_r10.py has run);
# argv[1] is kept for compatibility and ignored.
BASE = R10 / 'base' / 'corehub_intro_v50.vmf'
NAME = sys.argv[2] if len(sys.argv) > 2 else 'corehub_r10a'
MOD = HOME / 'mnt/revision9/runtime/game/corehub_intro'
v = VMF.parse(str(BASE))
tl = json.loads((OUT / 'intro-timeline.json').read_text())

# ---------- materials ----------
def unlit(name, base, color, extra=''):
    txt = f'"UnlitGeneric"\n{{\n"$basetexture" "{base}"\n"$color" "[{color}]"\n{extra}}}\n'
    for d in ('materials/corehub_intro/r10',):
        p = MOD / d / (name + '.vmt'); p.parent.mkdir(parents=True, exist_ok=True); p.write_text(txt)
    return 'corehub_intro/r10/' + name
RUST = unlit('rust', 'metal/metalwall_bts_001b', '0.86 0.84 0.82')
RUST_DARK = unlit('rust_dark', 'metal/metalwall_bts_001b', '0.40 0.39 0.38')
TUNNEL = unlit('tunnel', 'metal/black_wall_metal_001a', '0.22 0.22 0.22')
BAND = unlit('band', 'lights/white002', '0.45 0.45 0.44')
WIP_GRID = unlit('wip_grid', 'Dev/dev_measuregeneric01b', '0.92 0.92 0.92')   # unlit so the unfinished panels read pale like the video's grey rooms
WIP_WALL = 'dev/dev_measurewall01a'
LABDARK = unlit('labdark', 'metal/black_wall_metal_002a', '0.55 0.55 0.56')
WIP_STRIPE = 'dev/dev_hazzardstripe01a'
NODRAW = 'tools/toolsnodraw'

added = []
def box(lo, hi, mat, world=True, side_mat=None, x_mat=None):
    lo, hi = Vec(*lo), Vec(*hi)
    s = v.make_prism(lo, hi, mat).solid
    for f in s.sides:
        n = f.normal()
        if side_mat and abs(n.x) < 0.5: f.mat = side_mat
        if x_mat and abs(n.x) > 0.5: f.mat = x_mat
        f.lightmap = 32
    if world: v.add_brush(s)
    else: v.create_ent('func_detail').solids.append(s)
    added.append((lo, hi))
    return s

# ---------- camera path (eye positions) ----------
P = tl['positions']
def eye(t):
    for a, b in zip(P, P[1:]):
        if a['time'] <= t <= b['time']:
            f = 0 if b['time'] == a['time'] else (t - a['time']) / (b['time'] - a['time'])
            if (32.5 <= a['time'] < 32.51) or (38.9388 <= a['time'] < 39.10) or (118.3512 <= a['time'] < 118.3847): f = 0
            return [u + (w - u) * f for u, w in zip(a['eye'], b['eye'])]
    return P[-1]['eye']
path = [(t / 100, eye(t / 100)) for t in range(3260, 11840)]
path = [(t, p) for t, p in path if not (96.596307 <= t < 99.7995006)]

from srctools import Angle
rings = []   # (center, x half-extent of the ring)
for e in v.entities:
    if e['classname'].startswith('prop_') and ('ring' in e['model'] or 'collar' in e['model']):
        ax = Vec(1, 0, 0) @ Angle.from_str(e['angles'] if 'angles' in e else '0 0 0')
        R, w = 76.0, 24.0
        rings.append((Vec.from_str(e['origin']), R * math.sqrt(max(0.0, 1 - ax.x ** 2)) + w / 2 * abs(ax.x)))

collars = []
def _wb(lo, hi, mat, side, west, east):
    so = box(lo, hi, mat, side_mat=side)
    for f in so.sides:
        nx = f.normal().x   # srctools face normals point into the solid
        if west and nx > 0.5: f.mat = west
        if east and nx < -0.5: f.mat = east
    return so
def wall_x(x0, x1, y0=-1024, y1=1152, z0=-768, z1=2900, mat=RUST, side=None, extra_holes=(), hole=52, wip=None, collar=True, west=None, east=None):
    holes = list(extra_holes)
    for r, ext in rings:
        if x0 - ext < r.x < x1 + ext and y0 < r.y < y1 and z0 < r.z < z1:
            if abs(r.y) < 1 and abs(r.z - 1152) < 1 or abs(r.y) < 1 and abs(r.z - 256) < 1:
                holes.append((r.y - hole, r.y + hole, r.z - hole, r.z + hole))   # main tube: tight hole + collar
            else:
                holes.append((r.y - 96, r.y + 96, r.z - 96, r.z + 96))        # other (diagonal) tubes: generous
    crossings = []
    for t, p in path:
        if x0 - 40 < p[0] < x1 + 40 and y0 < p[1] < y1 and z0 < p[2] < z1:
            holes.append((p[1] - hole, p[1] + hole, p[2] - hole, p[2] + hole))
            if x0 <= p[0] <= x1: crossings.append(p)
    if collar and crossings:
        c = crossings[len(crossings) // 2]
        collars.append((x0 - 13, c[1], c[2]))   # on the approach face so the collar frames the hole instead of hiding inside it
    # merge overlapping holes
    merged = True
    while merged:
        merged = False
        out = []
        for h in holes:
            for i, g in enumerate(out):
                if h[0] <= g[1] + 80 and g[0] <= h[1] + 80 and h[2] <= g[3] + 80 and g[2] <= h[3] + 80:
                    out[i] = (min(h[0], g[0]), max(h[1], g[1]), min(h[2], g[2]), max(h[3], g[3])); merged = True; break
            else:
                out.append(h)
        holes = out
    holes = [(max(y0, a), min(y1, b), max(z0, c), min(z1, d)) for a, b, c, d in holes]
    ys = sorted({y0, y1} | {c for h in holes for c in h[:2]})
    zs = sorted({z0, z1} | {c for h in holes for c in h[2:]})
    n = 0
    for ya, yb in zip(ys, ys[1:]):
        run = None
        for za, zb in zip(zs, zs[1:]):
            inside = any(h[0] <= ya and yb <= h[1] and h[2] <= za and zb <= h[3] for h in holes)
            if inside:
                if run: _wb((x0, ya, run), (x1, yb, za), mat, side, west, east); n += 1
                run = None
            elif run is None:
                run = za
        if run is not None: _wb((x0, ya, run), (x1, yb, z1), mat, side, west, east); n += 1
    print(f'wall x {x0}..{x1}: {len(holes)} holes, {n} brushes', [tuple(round(c) for c in h) for h in holes])
    return holes

# ---------- room partitions (west to east) ----------
wall_x(1528, 1560)                       # west end of the pod-lined rise
wall_x(2840, 2960, mat=RUST, side=TUNNEL, hole=84)   # dark tunnel 49-50 s between rooms
wall_x(3400, 3432, hole=84)              # cube passage | tower base: crossed during the 54.1-54.9 s cut; opening clears the rings
wall_x(4364, 4396)                       # tower | turret room (collar in a frontal wall at 65-66 s)
wall_x(4980, 5012)                       # the "16" wall behind the inlet sign (72-73 s)
wall_x(6000, 6032, y1=60)                # far end of the copper-tube room (84-86 s); the gallery turns off to +y before it
wall_x(6780, 6812, west=TUNNEL)           # gallery | old factory remains: reads as darkness ahead at 95-95.5 s, crossed in the 95.7 s cut
wall_x(7300, 7332, east=LABDARK)         # old factory remains | laboratory (crossed in the 99.8 s cut)
wall_x(7960, 7992, mat=LABDARK)          # laboratory | dark room (106 s): black tiles both sides like the video

for cx, cy, cz in collars:
    mdl = 'transport_ring_orange' if cz < 600 and abs(cx - 6767) > 5 else 'transport_ring'   # copper in the low rooms (84-109 s); the 95 s collar is pale
    v.create_ent('prop_dynamic_override', model=f'models/corehub_intro/{mdl}.mdl', origin=f'{cx} {cy} {cz}',
                 angles='0 0 0', modelscale='1.5', solid='0', disableshadows='1', targetname='r10_wall_collar')
print('wall collars', collars)
swapped = 0
for e in v.entities:
    if e['classname'].startswith('prop_') and e['model'] == 'models/corehub_intro/transport_ring.mdl':
        o = Vec.from_str(e['origin'])
        if 4840 < o.x < 8400 and abs(o.y) < 5 and 150 < o.z < 400:
            e['model'] = 'models/corehub_intro/transport_ring_orange.mdl'; swapped += 1
    if e['classname'].startswith('prop_') and e['model'] == 'models/corehub_intro/transport_ring_bend.mdl':
        o = Vec.from_str(e['origin'])
        if 4840 < o.x < 8400 and 150 < o.z < 400:
            e['model'] = 'models/corehub_intro/transport_ring_bend_orange.mdl'; swapped += 1
print('copper collars', swapped)
# pod-room skylights read as dim frosted panels in the video (41-43 s), not glowing white
SKY = unlit('skylight_dim', 'lights/white002', '0.58 0.60 0.60')
dim = 0
for e in v.entities:
    for so in e.solids:
        lo, hi = so.get_bbox()
        if hi.x > 1500 and lo.x < 2500 and lo.z > 1250:
            for f in so.sides:
                if f.mat.lower() == 'corehub_intro/shaft_lamp': f.mat = SKY; dim += 1
print('skylight faces dimmed', dim)
# ---------- turret backdrop facing the camera (67.5-70.5 s) ----------
cam = Vec(4544, 0, 1152); yaw = math.radians(65)
f = Vec(math.cos(yaw), math.sin(yaw), 0); u = Vec(-math.sin(yaw), math.cos(yaw), 0)
for e in list(v.entities):
    if e['classname'] == 'func_detail':
        for s in list(e.solids):
            if any('turret_backing_u' in sd.mat.lower() for sd in s.sides):
                e.solids.remove(s); print('removed old oblique turret backing')
        if not e.solids: v.remove_ent(e)
def rotated_box(center, half_u, half_f, z0, z1, mat):
    s = v.make_prism(Vec(-half_f, -half_u, z0), Vec(half_f, half_u, z1), mat).solid
    s.localise(Vec(center.x, center.y, 0), Vec(0, 65, 0).to_angle() if False else __import__('srctools').Angle(0, 65, 0))
    for sd in s.sides: sd.lightmap = 32
    v.create_ent('func_detail').solids.append(s)
    return s
c_band = cam + f * 172; c_band.z = 0
c_wall = cam + f * 214; c_wall.z = 0
rotated_box(c_band + u * 90, 240, 4, 1104, 1165, BAND)
# keep the rotated rust wall clear of the descending shaft at x=4800 (radius ~90)
rotated_box(c_wall + u * 45, 255, 12, 860, 1700, RUST)   # extends further left (toward the tower wall) than right (the shaft/inlet drum)

box((7340, 300, -200), (7950, 316, 900), LABDARK, world=False)
# sludge test room (87-90 s): dark tiles with light seams like the video instead of flat black
n = 0
for e in v.entities:
    if e['classname'] != 'func_detail': continue
    for so in e.solids:
        lo, hi = so.get_bbox()
        if lo.x >= 5560 and hi.x <= 6340 and lo.y >= 60 and hi.y <= 980 and lo.z >= -230 and hi.z <= 175:
            for f in so.sides:
                if f.mat.lower() == 'corehub_intro/black_u': f.mat = LABDARK; n += 1
print('sludge room faces retextured', n)
# white lattice towers and the gallery truss read bright cream in the video (85-86 s, 91-93 s)
TRUSS = unlit('truss', 'lights/white002', '0.84 0.81 0.75')
tr = 0
for e in v.entities:
    if e['classname'] != 'func_detail': continue
    for so in e.solids:
        lo, hi = so.get_bbox(); d = hi - lo
        towers = lo.x >= 5280 and hi.x <= 5680 and 150 <= min(abs(lo.y), abs(hi.y)) and max(abs(lo.y), abs(hi.y)) <= 230
        gallery = lo.x >= 5960 and hi.x <= 6800 and hi.z < 260
        if (towers or gallery) and min(d.x, d.y, d.z) < 30:
            for f in so.sides:
                if f.mat.lower() == 'corehub_intro/white_u': f.mat = TRUSS; tr += 1
print('truss faces', tr)
# lab (104-109 s): open the test chamber like the video. The old solid black block filled the chamber;
# the video looks across it at a white tiled far wall (104-105 s) and down onto its white floor and
# blue light strip (107-109 s).
removed = 0
for e in list(v.entities):
    if e['classname'] != 'func_detail': continue
    for so in list(e.solids):
        lo, hi = so.get_bbox()
        if abs(lo.x - 7693) < 2 and abs(hi.x - 8127) < 2 and abs(lo.y + 611) < 2 and abs(hi.y + 132) < 2 and (abs(hi.z - 352) < 2 or abs(hi.z - 560) < 2):
            e.solids.remove(so); removed += 1
    if not e.solids: v.remove_ent(e)
wt = 0
for e in v.entities:
    if e['classname'] != 'func_detail': continue
    for so in e.solids:
        lo, hi = so.get_bbox()
        far = abs(lo.y + 896) < 2 and abs(hi.y + 880) < 2 and lo.x > 7790   # chamber south wall
        west = abs(lo.x - 7792) < 2 and abs(hi.x - 7808) < 2 and hi.y < -400  # chamber west wall
        if far or west:
            for f in so.sides:
                n = f.normal()
                if (far and n.y < -0.5) or (west and n.x < -0.5):   # faces toward the chamber (normals point into the solid)
                    f.mat = 'corehub_intro/wfloor_u'; wt += 1
print('lab chamber opened', removed, 'white wall faces', wt)
# tower entrance (55.5-57.5 s): the video frames a pale collar on the tube where it enters the tower room,
# with horizontal pipes running left and right at collar height, pale concrete below, and the lit grey room.
PALE = unlit('pale_concrete', 'concrete/concrete_modular_wall001a', '0.74 0.74 0.73')
v.create_ent('prop_dynamic_override', model='models/corehub_intro/transport_ring.mdl', origin='3700 0 1152',
             angles='0 0 0', modelscale='1.35', solid='0', disableshadows='1')
for y0, y1 in ((-1000, -96), (96, 1000)):
    box((3696, y0, 1144), (3712, y1, 1160), 'metal/metalpipe007a', world=False)
    for fy in range(y0 + 60, y1, 220):           # pipe flanges
        box((3693, fy, 1138), (3715, fy + 10, 1166), 'metal/metalpipe007a', world=False)
box((3640, -150, 760), (3720, 760, 1074), PALE, world=False)    # pale block under the collar (bottom of the 56 s frame)
v.create_ent('light', origin='3560 0 1320', _light='224 226 228 210', _lightHDR='-1 -1 -1 1', _constant_attn='0',
             _linear_attn='0', _quadratic_attn='1', _fifty_percent_distance='0', _zero_percent_distance='0')
# lab tube (100-101.5 s): the cube ahead is brightly lit in the video
v.create_ent('light', origin='7610 0 340', _light='236 238 240 170', _lightHDR='-1 -1 -1 1', _constant_attn='0',
             _linear_attn='0', _quadratic_attn='1', _fifty_percent_distance='0', _zero_percent_distance='0')
# transfer shaft (74-80 s): the video's scanners are flat white boards on arms, not round heads (custom model r10/models)
boards = 0
for e in v.entities:
    if e['classname'].startswith('prop_') and e['model'] == 'models/corehub_intro/scanner_arm.mdl':
        o = Vec.from_str(e['origin'])
        if 4600 < o.x < 5000 and abs(o.y) < 200:
            e['model'] = 'models/corehub_intro/scanner_board.mdl'; e['modelscale'] = '0.8'; boards += 1
print('scanner boards', boards)
# opening (5-11 s): the ceiling iris cover read as a darker, differently tiled square; give its visible face the
# ceiling's own material and texture alignment so the closed iris is invisible like in the video
ref_face = None
for e in v.entities:
    if e['targetname'] == 'p41_preview_ceiling_exposure':
        for so in e.solids:
            for f in so.sides:
                if f.normal().z > 0.5 and 'nodraw' not in f.mat.lower(): ref_face = f; break
            if ref_face: break
    if ref_face: break
cov = 0
for e in v.entities:
    if e['targetname'] == 'p41_intro_iris_cover':
        for so in e.solids:
            for f in so.sides:
                if f.normal().z > 0.5 and 'nodraw' not in f.mat.lower():
                    f.mat = ref_face.mat; f.uaxis = ref_face.uaxis.copy(); f.vaxis = ref_face.vaxis.copy(); cov += 1
print('iris cover faces matched to ceiling', cov)
# the cubes waiting in the tube (52-54 s) are brightly lit in the video; the rebuild had them in the dark
for lx in (3250, 3330, 3470, 3600):
    v.create_ent('light', origin=f'{lx} 0 1236', _light='228 230 232 520', _lightHDR='-1 -1 -1 1', _constant_attn='0', _linear_attn='0', _quadratic_attn='1', _fifty_percent_distance='0', _zero_percent_distance='0')
# pod rise (39.5-41.5 s): the video shows pod walls on both sides of the vertical tube -- lit grey pods on the
# north (left of frame) and dark ones on the south. Pod materials were lightened (x0.55 of the original), so the
# south pods are darkened with rendercolor and two lit pod walls go on the north wall (y = 10, facing -y).
pods = 0
for e in v.entities:
    if e['classname'].startswith('prop_') and e['model'] == 'models/corehub_intro/pod_wall.mdl':
        e['rendercolor'] = '98 98 99'; pods += 1
for pz in (850, 1170):
    v.create_ent('prop_static', model='models/corehub_intro/pod_wall.mdl', origin=f'1856 3 {pz}', angles='0 270 0',
                 solid='0', disableshadows='1', rendercolor='255 255 255', skin='0')
print('pod walls darkened', pods, '+ 2 lit north pod walls')
# turret (67-70.5 s): the video's turret is bright white; the rebuild's read almost black. Front fill light from the
# camera side (the camera holds at 4544,0,1152 looking at the turret at 4575,58,1159).
v.create_ent('light', origin='4520 -10 1185', _light='236 238 240 650', _lightHDR='-1 -1 -1 1', _constant_attn='0',
             _linear_attn='0', _quadratic_attn='1', _fifty_percent_distance='0', _zero_percent_distance='0')
# lab (103-105 s): the video turns right onto a white tiled wall with three turrets hanging on red cables in front
# of it, framed by black tiles. Placed from the camera (7768,0,256 looking -65 yaw, 15 down at 104.25 s) so the
# panel fills the middle of the frame and stays west of the lab partition at x=7960; the old cable bar is replaced.
import srctools as _st
def oriented_box(center, half_u, half_f, z0, z1, mat, yaw):
    sol = v.make_prism(Vec(-half_f, -half_u, z0), Vec(half_f, half_u, z1), mat).solid
    sol.localise(Vec(center[0], center[1], 0), _st.Angle(0, yaw, 0))
    v.create_ent('func_detail').solids.append(sol)
    return sol
CABLE = unlit('cable_red', 'lights/white002', '0.42 0.16 0.12')
gone = 0
for e in list(v.entities):
    if e['classname'] != 'func_detail': continue
    keep = []
    for so in e.solids:
        lo, hi = so.get_bbox()
        if lo.x >= 7880 and hi.x <= 8070 and lo.y >= -300 and hi.y <= -90 and lo.z >= 195 and hi.z <= 410 and \
                any(f.mat.lower() == 'metal/metalwall_bts_006b' for f in so.sides):
            gone += 1; continue
        keep.append(so)
    e.solids[:] = keep
cam104 = (7768.0, 0.0, 256.0)
spots = [(-39.4, 190), (-62.0, 190), (-88.0, 190)]   # azimuth from the camera, distance
hov = [e for e in v.entities if e['classname'].startswith('prop_') and e['model'] == 'models/props_backstage/vacum_hover.mdl'
       and 7850 < Vec.from_str(e['origin']).x < 8100 and Vec.from_str(e['origin']).z > 100]
hov.sort(key=lambda e: Vec.from_str(e['origin']).x, reverse=True)
for e, (az, d) in zip(hov, spots):
    a = math.radians(az); hd = d * math.cos(math.radians(15))
    x, y, z = cam104[0] + hd * math.cos(a), cam104[1] + hd * math.sin(a), cam104[2] - d * math.sin(math.radians(15))
    e['origin'] = f'{x:.1f} {y:.1f} {z:.1f}'; e['angles'] = f'347 {az + 180:.1f} 0'
    box((x - 1, y - 1, z + 14), (x + 1, y + 1, 430), CABLE, world=False)
oriented_box((7858, -203), 110, 2, 120, 272, 'corehub_intro/wfloor_u', -66)
oriented_box((7858, -203), 110, 2, -150, 120, 'corehub_intro/black_u', -66)   # black tiles under it (hides the receptacle until 107 s)
print('lab turret wall: cable bars removed', gone, 'turrets moved', len(hov))
# the lead cube in the passage (52.6-53.8 s) is seen tumbling, tipped about 30 degrees, not square-on
for e in v.entities:
    if e['targetname'] == 'intro_cube_0': e['angles'] = '24 62 28'
# ---------- WIP / unfinished surfaces ----------
# Room G (cube passage) east partition, lower part: grey measuring panels.
# (r10s: the pale measuring panels behind the cube were removed -- the video shows only the tube and grey walls there)
# Unfinished floor patch under the pod-lined rise.
box((1600, -700, -512), (2200, 960, -500), WIP_GRID, world=False)
# Hazard-striped temporary bulkhead edge on the lab partition and a bare panel.
box((7296, -1000, 700), (7300, 1100, 732), WIP_STRIPE, world=False)
box((7992, 300, -760), (7996, 980, 500), WIP_GRID, world=False)   # east side of the lab partition, seen only after 106 s
# Missing-panel framing on the "16" wall's far side (upper corner, never finished).
box((5012, 600, 1600), (5016, 1100, 2400), WIP_GRID, world=False)

dst = R10 / 'build' / (NAME + '.vmf')
v.export(dst.open('w'), inc_version=False)
print('wrote', dst, len(added), 'boxes')

# ---------- verify the camera never enters a new solid ----------
bad = []
for t, p in path:
    for lo, hi in added:
        if lo.x - 10 < p[0] < hi.x + 10 and lo.y - 10 < p[1] < hi.y + 10 and lo.z - 10 < p[2] < hi.z + 10:
            bad.append((t, [round(c) for c in p], (tuple(lo), tuple(hi)))); break
print('camera collisions:', len(bad), bad[:5])
