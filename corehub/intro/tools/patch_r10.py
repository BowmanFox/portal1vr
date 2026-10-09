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
LABWALL = unlit('labwall', 'tile/white_floor_tile001a', '1.0 0.95 1.0')   # bright neutral white tiles like the video
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
wall_x(4364, 4396, hole=84, extra_holes=((-20, 110, 1430, 1620),))   # tower | turret room; r10ah: the camera crosses high (64 s) to come over the turret-lift collar
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
# scanner shaft (74-80 s): the video's stacked rings read light grey, not dark; transport_ring_white is the same ring
# compiled with the brighter tube_w materials ($renamematerial, transport-models/transport_ring_white.qc)
white = 0
for e in v.entities:
    if e['classname'].startswith('prop_') and e['model'] == 'models/corehub_intro/transport_ring.mdl':
        o = Vec.from_str(e['origin'])
        if abs(o.x - 4800) < 5 and abs(o.y) < 5 and 560 < o.z < 1000:
            e['model'] = 'models/corehub_intro/transport_ring_white.mdl'; e['skin'] = '0'; white += 1
print('white shaft rings', white)
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
rotated_box(c_band + u * 90, 240, 4, 950, 1011, BAND)   # r10y: grey band at the lowered turret's legs, like the video
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
for pz in (850,):   # r10ag: the upper one (1170) stood across the tube's turn at 42.5-43.2 s (grey pods filled the frame)
    v.create_ent('prop_static', model='models/corehub_intro/pod_wall.mdl', origin=f'1856 3 {pz}', angles='0 270 0',
                 solid='0', disableshadows='1', rendercolor='255 255 255', skin='0')
print('pod walls darkened', pods, '+ 2 lit north pod walls')
# pod rise turn (42.5-43.5 s): the video swings past a dark rust wall close on the north side of the tube
box((1700, 70, 1010), (2200, 86, 1400), RUST_DARK, world=False)
# rust room (32.6-33.3 s): the video looks down the tube at a lit rust panel in a dark room -- the ring at its centre,
# a post under the ring, a black C-bend to its right. The far wall (x=896) is cut down to that panel with black,
# the decorative tube (y=-5740) is dark, and a post stands under the bend.
box((878, -5125, 2400), (884, -4600, 3000), 'corehub_intro/black_u', world=False)
box((878, -6500, 2400), (884, -6039, 3000), 'corehub_intro/black_u', world=False)
box((878, -6039, 2844), (884, -5125, 3000), 'corehub_intro/black_u', world=False)
box((878, -6039, 2400), (884, -5125, 2578), 'corehub_intro/black_u', world=False)
box((756, -5512, 2440), (780, -5488, 2622), 'corehub_intro/steel_u', world=False)
dk = 0
for e in v.entities:
    if e['classname'].startswith('prop_') and e['model'] == 'models/corehub_intro/p9_entry_ring.mdl':
        o = Vec.from_str(e['origin'])
        if abs(o.y + 5740) < 2 and o.z > 2400: e['rendercolor'] = '34 34 34'; dk += 1
print('rust room: dark C-bend rings', dk)
# second look at the panel (36.6-37.3 s, camera at z 512 heading +x): the video's panel is wide and low
# (about y -6189..-5422, z 210..641); v50's was narrow and tall
box((2272, -6189, 210), (2280, -5422, 641), 'corehub_intro/steel_u', world=False)
box((2272, -6100, -100), (2280, -5380, 210), 'corehub_intro/black_u', world=False)
box((2272, -6100, 641), (2280, -5380, 1100), 'corehub_intro/black_u', world=False)
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
oriented_box((7858, -203), 110, 2, 120, 272, LABWALL, -66)
# the video's lab has a low light-blue ceiling just above the tube (top third of the frame at 101-104 s)
box((7400, -700, 340), (7955, 300, 356), 'corehub_intro/labblue_u', world=False)
# the low ceiling shades the hanging turrets; the video's are bright white -- fill light under the ceiling
v.create_ent('light', origin='7800 -80 320', _light='236 238 240 420', _lightHDR='-1 -1 -1 1', _constant_attn='0',
             _linear_attn='0', _quadratic_attn='1', _fifty_percent_distance='0', _zero_percent_distance='0')
oriented_box((7858, -203), 110, 2, -150, 120, 'corehub_intro/black_u', -66)   # black tiles under it (hides the receptacle until 107 s)
print('lab turret wall: cable bars removed', gone, 'turrets moved', len(hov))
# the lead cube in the passage (52.6-53.8 s) is seen tumbling, tipped about 30 degrees, not square-on
for e in v.entities:
    if e['targetname'] == 'intro_cube_0': e['angles'] = '24 62 28'
# turret lift (64-67 s): in the video the camera passes under a dark collar platform, looks down at a pale floor
# ring with three dark rods running into it, and the turret rises out of that ring to stand on the floor (the
# director lowers the camera to the turret's eye level and raises intro_turret from z 760 to 950).
LX, LY, LZ = 4575, 58, 950
v.create_ent('prop_static', model='models/corehub_intro/tower_ring.mdl', origin=f'{LX} {LY} 1355', angles='-90 0 0',
             solid='0', disableshadows='1')
for a in (40, 100, 150):   # r10an: on the collar's inner edge, clear of the drop (64.5-67 s) and the climb to the "16" inlet (71-72 s)
    rx, ry = LX + 100 * math.cos(math.radians(a)), LY + 100 * math.sin(math.radians(a))
    box((rx - 6, ry - 6, LZ), (rx + 6, ry + 6, 1345), 'metal/black_wall_metal_001a', world=False)   # r10ap: dark, like the black bars round the turret (67-71 s)
FLOOR = RUST_DARK   # r10ag: the video never shows a pale floor round the turret (66-71 s); it reads as the dark wall
for lo, hi in [((4420, -100), (4730, LY - 70)), ((4420, LY + 70), (4730, 220)), ((4420, LY - 70), (LX - 70, LY + 70)), ((LX + 70, LY - 70), (4730, LY + 70))]:
    box((lo[0], lo[1], LZ - 20), (hi[0], hi[1], LZ), FLOOR, world=False)
v.create_ent('prop_static', model='models/corehub_intro/transport_ring.mdl', origin=f'{LX} {LY} {LZ - 6}', angles='90 0 0',
             modelscale='1.3', solid='0', disableshadows='1', skin='2')   # pale ring like the video
# three dark rods hang from the tower's base collar (seen when the camera looks back at it, 64-64.5 s)
for a in (30, 150, 270):
    rx, ry = 3882 + 110 * math.cos(math.radians(a)), 240 + 110 * math.sin(math.radians(a))
    box((rx - 5, ry - 5, 1000), (rx + 5, ry + 5, 1242), 'corehub_intro/steel_u', world=False)
# tower collars (58-64 s): the video sees dark grey rings with open centres from above and below; the v50 collars
# were black and 32 thick, so beside the camera's height they read as solid slabs. tower_ring_thin is half as
# thick with a wider hole and grey shading (towerg_* materials); the stack moves up 50 so the camera, which rises
# to 1640 and comes back down, spends less time level with a collar.
tw = 0
for e in v.entities:
    if e['classname'].startswith('prop_') and e['model'] == 'models/corehub_intro/tower_ring.mdl':
        o = Vec.from_str(e['origin'])
        if abs(o.x - 3882) < 2 and abs(o.y - 240) < 2:
            e['model'] = 'models/corehub_intro/tower_ring_thin.mdl'; e['origin'] = f'{o.x:g} {o.y:g} {o.z + 50:g}'; tw += 1
print('tower collars thinned', tw)
# r10ah: the camera now drops through the turret-lift collar at x 4530-4544 (64.5-65.3 s); v50's steel slab over the
# turret (x 4520-4536, from z 1250 up) stood in that shaft, so it now starts above the camera's way in (z 1480)
raised = 0
for e in list(v.entities):
    if e['classname'] != 'func_detail': continue
    for so in list(e.solids):
        lo, hi = so.get_bbox()
        if abs(lo.x - 4520) < 1 and abs(hi.x - 4536) < 1 and abs(lo.z - 1250) < 1 and abs(hi.z - 2868) < 1:
            e.solids.remove(so); raised += 1
    if not e.solids: v.remove_ent(e)
if raised: box((4520, -700, 1480), (4536, 700, 2868), 'corehub_intro/steel_u', world=False)
print('turret slab raised', raised)
# r10aq: copper room (84.6-86 s) -- above the gallery opening the x=6000 partition stopped at y=60, so the top of the view
# ran out to the far gallery wall (dark); the video sees the rust wall there
box((6000, 60, 700), (6032, 1152, 2900), RUST, world=False)
# r10al: sludge funnel (86.2-87.2 s) -- the camera leaves the copper tube through a gap (the 5783 ring is dropped)
# and comes down a short vertical copper funnel into the tube over the chamber
for e in list(v.entities):
    if e['classname'].startswith('prop_') and 'transport_ring' in e['model']:
        o = Vec.from_str(e['origin'])
        if abs(o.x - 5783.27) < 2 and abs(o.y) < 2 and abs(o.z - 256) < 2: v.remove_ent(e); print('removed copper ring 5783')
for z, sc in ((88, '1'), (172, '1'), (340, '1'), (425, '1.4')):   # r10an: a longer copper tube below, seen end-on from the top (86.5-87 s)
    v.create_ent('prop_static', model='models/corehub_intro/transport_ring_orange.mdl', origin=f'5952 150 {z}', angles='90 0 0',
                 modelscale=sc, solid='0', disableshadows='1')
# r10aj: pod rise (40-42 s) -- through the top of the tube the video sees grey ceiling structure round the skylights;
# the rebuild's was rust metal
pc = 0
for e in v.entities:
    if e['classname'] != 'func_detail': continue
    for so in e.solids:
        lo, hi = so.get_bbox()
        if lo.x >= 1600 and hi.x <= 2300 and lo.y >= -700 and hi.y <= 150 and lo.z >= 1230:
            for f in so.sides:
                if f.mat.lower() in ('metal/metalwall_bts_001b', 'corehub_intro/steel_u', 'corehub_intro/steel_ud'):
                    f.mat = TUNNEL; pc += 1
print('pod ceiling faces greyed', pc)
# r10ai: the single tube ring left in the turret room (x 4538) sat on the camera's way down to the turret (65-66 s)
for e in list(v.entities):
    if e['classname'].startswith('prop_') and e['model'] == 'models/corehub_intro/transport_ring.mdl':
        o = Vec.from_str(e['origin'])
        if abs(o.x - 4538.5) < 2 and abs(o.y) < 2 and abs(o.z - 1152) < 2: v.remove_ent(e); print('removed turret-room tube ring')
# r10ai: incinerator (114-116.3 s) -- the video shows a glowing yellow ball dropping with the discarded parts
v.create_ent('prop_dynamic_override', targetname='r10_core_glow', model='models/corehub_intro/r10_ball.mdl', origin='8448 0 900', modelscale='1.45',
             solid='0', disableshadows='1', DefaultAnim='idle')   # r10ap: an unlit no-fog yellow ball (sprites never drew through the incinerator haze)
print('turret lift: collar, rods, floor and ring at', (LX, LY, LZ))
# sludge chamber (87-90 s): the video's walkways are solid white blocks rising out of the sludge (a white border
# round the pit); the rebuild's were thin slabs over a black pit wall
box((5588, 80, -194), (5762, 800, -60), LABWALL, world=False)
box((5588, 800, -194), (6316, 960, -60), LABWALL, world=False)
for e in v.entities:   # walkway tops in bright neutral white too
    if e['classname'] != 'func_detail': continue
    for so in e.solids:
        lo, hi = so.get_bbox()
        if lo.x >= 5580 and hi.x <= 6320 and lo.y >= 70 and hi.y <= 970 and lo.z >= -70 and hi.z <= 45:
            for f in so.sides:
                if f.mat.lower() == 'corehub_intro/wfloor_u': f.mat = LABWALL
# the light-brown square panel resting in the sludge by the far walkway (right of the laser)
PANEL = unlit('panel_brown', 'lights/white002', '0.62 0.52 0.40')
box((6070, 650, -186), (6210, 790, -176), PANEL, world=False)
box((6066, 646, -192), (6214, 794, -186), 'corehub_intro/black_u', world=False)
v.create_ent('env_fade', targetname='r10_red_fade', origin='4544 0 1000', rendercolor='172 170 170', renderamt='0', duration='0.001', holdtime='0', spawnflags='8')
# lab test chamber seen from above (107.5-109.5 s): the video looks straight down onto a bright white floor with a
# purple-blue light strip, a copper-rimmed receptacle and a grey checker patch; v50 had black blocks under the tube there
gone = 0
for e in list(v.entities):
    if e['classname'] != 'func_detail': continue
    keep = []
    for so in e.solids:
        lo, hi = so.get_bbox()
        if lo.x >= 7890 and hi.x <= 8140 and lo.y >= -145 and hi.y <= 82 and lo.z >= -162 and hi.z <= 354 and \
                all(f.mat.lower() in ('corehub_intro/black_u', 'tools/toolsnodraw') for f in so.sides):
            gone += 1; continue
        keep.append(so)
    e.solids[:] = keep
LABFLOOR = unlit('labfloor', 'tile/white_floor_tile001a', '1.3 1.24 1.3')   # the video's chamber floor is near-white
# r10af: laid out from the video's 107.5 s view (camera 8134,0,256 looking straight down, frame turned 25 degrees):
# receptacle top-left under a short copper tube, grey checker patch centre-left, an orange button below it, the purple
# light strip running down the right with black tiles beyond it, and a pale pink wall along the left
box((8000, -94, -80), (8336, 260, -60), LABFLOOR, world=False)
box((8000, -300, -80), (8336, -134, -60), LABDARK, world=False)
box((7996, -300, -80), (8000, 260, 120), LABWALL, world=False)
box((7996, -304, -80), (8336, -300, 120), LABDARK, world=False)
box((7996, 260, -80), (8336, 264, 120), LABWALL, world=False)
box((8336, -72, -80), (8338, 264, 120), LABWALL, world=False)
STRIP = unlit('lab_strip', 'lights/white002', '0.46 0.42 0.95')
box((8000, -134, -80), (8336, -94, -57), STRIP, world=False)
CHECK = unlit('lab_check', 'lights/white002', '0.50 0.50 0.50')
for i in range(6):
    for j in range(6):
        if (i + j) % 2: box((8160 + 10 * i, 50 + 10 * j, -60), (8170 + 10 * i, 60 + 10 * j, -59), CHECK, world=False)
BUTTON = unlit('lab_button', 'lights/white002', '0.85 0.45 0.20')
box((8099, 68, -60), (8115, 84, -52), BUTTON, world=False)
box((8235, -35, -60), (8305, 35, -58), 'corehub_intro/black_u', world=False)
v.create_ent('prop_static', model='models/corehub_intro/transport_ring_orange.mdl', origin='8270 0 -46', angles='90 0 0',
             modelscale='1.35', solid='0', disableshadows='1')
for z in (30, 114):   # the short copper tube the video drops down onto the receptacle (108.5-109.7 s)
    v.create_ent('prop_static', model='models/corehub_intro/transport_ring_orange.mdl', origin=f'8270 0 {z}', angles='90 0 0',
                 solid='0', disableshadows='1')
# the last ring of the lab tube (8278,0,256) sat where the camera now turns down; the tube ends at the 8194 ring
for e in list(v.entities):
    if e['classname'].startswith('prop_') and 'transport_ring' in e['model']:
        o = Vec.from_str(e['origin'])
        if abs(o.x - 8278) < 2 and abs(o.y) < 2 and abs(o.z - 256) < 2: v.remove_ent(e); print('removed lab tube end ring')
print('lab chamber floor view: removed black blocks', gone)
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

# ---------- r10as: pod rise (39.5-49 s) ----------
# the video's pod-rise tube is dark grey; skin 2 read pale teal. The vertical rise and the run to the crossing use skin 1.
dk2 = 0
for e in v.entities:
    if e['classname'].startswith('prop_') and e['model'] == 'models/corehub_intro/transport_ring.mdl':
        o = Vec.from_str(e['origin'])
        if (abs(o.x - 1856) < 2 and abs(o.y + 256) < 2 and 600 < o.z < 1000) or (2000 < o.x < 2740 and abs(o.y) < 2 and abs(o.z - 1152) < 2):
            e['skin'] = '1'; dk2 += 1
print('pod rise rings darkened', dk2)
# the run ends at a pale tube crossing at tube height (video 46.5-48 s): the side tube at x 2760 (z 1010) is raised to the
# tube and made pale; its ring on the camera's path is dropped
side = 0
for e in list(v.entities):
    if e['classname'].startswith('prop_') and e['model'] == 'models/corehub_intro/transport_ring.mdl':
        o = Vec.from_str(e['origin'])
        if abs(o.x - 2760) < 2 and abs(o.z - 1010) < 2 and abs(o.y) <= 401:
            if o.y > -2: v.remove_ent(e); continue   # r10au: right-hand half only (y < 0), like the video
            e['origin'] = f'{o.x:g} {o.y:g} 1152'; e['model'] = 'models/corehub_intro/transport_ring_pale.mdl'; e['skin'] = '0'; side += 1
print('pale crossing tube rings', side)
# the pale wall closing the tube beyond the crossing: the white far end at 44-47 s and the white frame at 48.3-48.85 s;
# the director moves it away before the camera reaches it
v.create_ent('prop_dynamic_override', targetname='r10_tube_end', model='models/corehub_intro/r10_tube_end.mdl', origin='2812 0 1152',
             angles='0 0 0', solid='0', disableshadows='1')
# the chrome drop reads as a white ball a few rings ahead in the video
for e in v.entities:
    if e['targetname'] == 'intro_drop': e['modelscale'] = '1.8'; print('drop scaled')
# the walls round the vertical rise were white tiles; the video sees dark walls between the pods
POD_BG = unlit('pod_bg', 'metal/black_wall_metal_001a', '0.34 0.34 0.34')
pw = 0
for e in v.entities:
    if e['classname'] != 'func_detail': continue
    for so in e.solids:
        lo, hi = so.get_bbox()
        if hi.x > 1680 and lo.x < 2140 and hi.y > -420 and lo.y < 30 and lo.z >= 630 and hi.z <= 1345:
            for f in so.sides:
                if f.mat.lower() == 'corehub_intro/white_u': f.mat = POD_BG; pw += 1
print('pod shaft wall faces darkened', pw)
# r10ax: the video's pods are lit grey capsules packed on every side of the rise (39.5-41.75 s)
for e in v.entities:
    if e['classname'].startswith('prop_') and e['model'] == 'models/corehub_intro/pod_wall.mdl':
        e['rendercolor'] = '215 215 218'
for org, ang in (('2118 -256 850', '0 180 0'), ('1762 -256 1170', '0 0 0'), ('1762 -256 530', '0 0 0'), ('2118 -256 530', '0 180 0')):
    v.create_ent('prop_static', model='models/corehub_intro/pod_wall.mdl', origin=org, angles=ang, solid='0', disableshadows='1', rendercolor='215 215 218', skin='0')
# skylights over the pod room: dimmer still (the video shows thin light strips in a dark truss at 42 s)
SKY2 = unlit('skylight_dim', 'lights/white002', '0.40 0.41 0.41')
# ---------- r10at: tower entrance (55.3-58.6 s) ----------
# the video's camera rides only the tube's rails toward the collar (no ring flanges round the frame): the three rings
# between the cube-passage wall and the collar become rails-only props
rails = 0
for e in v.entities:
    if e['classname'].startswith('prop_') and e['model'] == 'models/corehub_intro/transport_ring.mdl':
        o = Vec.from_str(e['origin'])
        if 3420 < o.x < 3600 and abs(o.y) < 2 and abs(o.z - 1152) < 2:
            e['model'] = 'models/corehub_intro/transport_rails.mdl'; e['skin'] = '0'; rails += 1
    if e['classname'] == 'prop_dynamic_override' and e['model'] == 'models/corehub_intro/transport_ring.mdl' and e['origin'] == '3700 0 1152':
        e['model'] = 'models/corehub_intro/transport_ring_white.mdl'; e['skin'] = '0'; e['modelscale'] = '1.1'; print('pale tower collar')
print('tower entrance rings -> rails', rails)
# the dark column rising from the collar, with its flange plate (hidden by the director at the 58.6 s dissolve)
v.create_ent('prop_dynamic_override', targetname='r10_tw_column', model='models/corehub_intro/r10_column.mdl', origin='3754 0 1272',
             angles='0 0 0', solid='0', disableshadows='1')
# rusty back wall behind the collar (the video shows rust panels there, not the lit tower interior); a func_brush the
# director moves away at the 58.6 s dissolve, before the camera climbs through
bw = v.make_prism(Vec(3830, -420, 900), Vec(3846, 420, 2400), unlit('rust_tw', 'metal/metalwall_bts_006a', '0.85 0.85 0.88')).solid   # r10cn: wider and lit like the video's rust behind the junction (55.5-58.25 s)
for f in bw.sides: f.lightmap = 32
v.create_ent('func_brush', targetname='r10_tw_backwall', Solidity='1', spawnflags='2', rendermode='0', renderamt='255',
             rendercolor='255 255 255', disablereceiveshadows='1', disableshadows='1', vrad_brush_cast_shadows='0').solids.append(bw)
# ---------- r10au: sludge test chamber (87-90 s) rebuilt to the video's proportions ----------
# Solved from the video frames (88.5 s: far wall foot at mid-frame spanning ~82% of the width; 89.75 s: at ~66%) with the
# camera's own path (x 5952, y 342 -> 455, z 256, looking 44 deg down): sludge at z 0, far wall at y 608, width 728.
# The old deep chamber (floor -194, walkways, far wall at 960) is removed.
def in_box(lo, hi, a, b):
    return a[0] <= lo.x and hi.x <= b[0] and a[1] <= lo.y and hi.y <= b[1] and a[2] <= lo.z and hi.z <= b[2]
gone = 0
for e in list(v.entities):
    if e['classname'] not in ('func_detail', 'func_brush'): continue
    keep = []
    for so in e.solids:
        lo, hi = so.get_bbox()
        if in_box(lo, hi, (5570, 60, -230), (6334, 978, 172)): gone += 1; continue
        keep.append(so)
    if len(keep) != len(e.solids):
        e.solids[:] = keep
        if not keep: v.remove_ent(e)
for so in list(v.spawn.solids):
    lo, hi = so.get_bbox()
    if in_box(lo, hi, (5580, 70, -215), (6320, 970, -190)) and any('toxicslime' in f.mat.lower() for f in so.sides):
        v.remove_brush(so); gone += 1
print('old sludge chamber solids removed', gone)
SLUDGE = 'nature/toxicslime002a'
sl = v.make_prism(Vec(5588, 80, -14), Vec(6316, 608, 0), NODRAW).solid
for f in sl.sides:
    if f.normal().z < -0.5: f.mat = SLUDGE
v.add_brush(sl)
box((5572, 64, -30), (6332, 624, -14), LABDARK, world=False)          # floor slab under the sludge
box((5572, 64, -14), (5588, 624, 520), LABDARK, world=False)          # west wall
box((6316, 64, -14), (6332, 442, 520), LABDARK, world=False)          # east wall, round the exit tube (y 512, z 256)
box((6316, 582, -14), (6332, 624, 520), LABDARK, world=False)
box((6316, 442, -14), (6332, 582, 186), LABDARK, world=False)
box((6316, 442, 326), (6332, 582, 520), LABDARK, world=False)
box((5588, 608, -14), (6316, 624, 520), LABDARK, world=False)         # far wall
box((5588, 64, -14), (6316, 80, 170), LABDARK, world=False)           # near wall (low: the camera comes in over it)
# white tiled foot of the walls (the video's white band)
box((5588, 600, 0), (6316, 608, 90), LABWALL, world=False)
box((5588, 80, 0), (5596, 600, 90), LABWALL, world=False)
box((6308, 80, 0), (6316, 600, 90), LABWALL, world=False)
# r10av: top/side materials set per face (box()'s side_mat also caught the tops)
def box_top(lo, hi, top, side):
    so = box(lo, hi, side, world=False)
    for f in so.sides:
        if f.normal().z < -0.5: f.mat = top      # normals point into the solid: the top face's normal is -z
    return so
# far-left: a small dark landing with a white pedestal on the far wall (video top-left)
box_top((5690, 548, 0), (5830, 600, 66), 'corehub_intro/black_u', LABWALL)
box((5742, 570, 66), (5762, 590, 96), LABWALL, world=False)
# far-right: black ledge under the round door, with a floor button; the door and its signs on the far wall
box((5990, 556, 120), (6150, 600, 128), 'corehub_intro/black_u', world=False)
SIGNW = unlit('sign_white', 'lights/white002', '0.80 0.80 0.78')
SIGNB = unlit('sign_blue', 'lights/white002', '0.10 0.45 0.62')
box((6030, 602, 214), (6070, 606, 230), SIGNW, world=False)
box((6084, 602, 192), (6098, 606, 206), SIGNB, world=False)
moved = 0
for e in v.entities:
    if e['classname'].startswith('prop_') and e['model'] in ('models/props/portaldoor_circle.mdl', 'models/corehub_intro/white_disc.mdl'):
        o = Vec.from_str(e['origin'])
        if abs(o.x - 6182) < 2 and abs(o.y - 951) < 2: e['origin'] = '6050 604 180'; e['modelscale'] = '0.4'; moved += 1
        if abs(o.x - 6132) < 2 and abs(o.y - 955) < 2: e['origin'] = '6066 586 130'; e['angles'] = '-90 0 0'; e['modelscale'] = '1.3'; moved += 1
print('door/button moved', moved)
# the large plate at the right (grey-beige top, copper rim)
PLATE = unlit('sludge_plate', 'concrete/concrete_modular_floor001a', '0.70 0.66 0.58')
COPPER = unlit('sludge_copper', 'lights/white002', '0.55 0.30 0.17')
box((6028, 494, 74), (6266, 600, 82), COPPER, world=False)          # r10av: raised against the far wall (video 37-60% of the frame)
box_top((6034, 500, 82), (6260, 600, 90), PLATE, COPPER)
box((6060, 510, 0), (6070, 520, 74), 'corehub_intro/black_u', world=False)
box((6224, 510, 0), (6234, 520, 74), 'corehub_intro/black_u', world=False)
# the laser across the chamber with its emitters on the side walls
for yy in (540, 550):
    lb = v.make_prism(Vec(5596, yy, 40), Vec(6308, yy + 2, 42), 'corehub_intro/bridge_light').solid
    v.create_ent('func_brush', Solidity='1', origin='0 0 0').solids.append(lb)
EMIT = unlit('sludge_emitter', 'lights/white002', '0.75 0.75 0.74')
box((5596, 531, 28), (5622, 561, 54), EMIT, world=False)
box((6282, 531, 28), (6308, 561, 54), EMIT, world=False)
# the copper rod reaching from the near side up to its claw on the far wall
v.create_ent('prop_static', model='models/corehub_intro/r10_rod.mdl', origin='5946 110 26', angles='-14 90 0', solid='0', disableshadows='1')
# the funnel ends above the chamber now (its two lowest rings would stand in the sludge)
for e in list(v.entities):
    if e['classname'].startswith('prop_') and 'transport_ring_orange' in e['model']:
        o = Vec.from_str(e['origin'])
        if abs(o.x - 5952) < 2 and abs(o.y - 150) < 2 and o.z < 200: v.remove_ent(e); print('funnel ring removed', o.z)
# r10av: the video looks down a long copper funnel (86.5-86.75 s): two lower rings the director removes as the camera
# comes out of the funnel (86.95 s)
for k, z in ((1, 255), (2, 170)):
    v.create_ent('prop_dynamic_override', targetname=f'r10_funnel_lo{k}', model='models/corehub_intro/transport_ring_orange.mdl',
                 origin=f'5952 150 {z}', angles='90 0 0', solid='0', disableshadows='1')
# ---------- r10aw: gallery (90.5-95.7 s) ----------
# The video runs through copper rings above a cream truss in a rust-walled hall, through a broken dark tube section
# (93.5-94.25 s), then past rust walls to a cream collar (95 s).
from srctools import Angle
gw = 0
for e in [v.spawn] + list(v.entities):
    for so in e.solids:
        lo, hi = so.get_bbox()
        gallery_wall = (lo.x >= 6330 and hi.x <= 6790 and lo.y >= -410 and hi.y <= 740 and hi.z >= 600)
        partition = (abs(lo.x - 6780) < 1 and abs(hi.x - 6812) < 1)
        for f in so.sides:
            m = f.mat.lower()
            if (gallery_wall and m == 'corehub_intro/steel_u') or (partition and m == 'corehub_intro/r10/tunnel'):
                f.mat = RUST; gw += 1
                f.uaxis.scale = 0.5; f.vaxis.scale = 0.5   # r10ax: the steel faces were stretched; rust streaks at the video's size
print('gallery walls rusted', gw)
def truss_run(a0, a1, axis, c, z0, z1, w=56, step=60):
    """cream lattice along x or y from a0 to a1, centred on the other horizontal coordinate c, between z0 and z1"""
    n = 0
    def pr(lo, hi):
        so = v.make_prism(Vec(*lo), Vec(*hi), TRUSS).solid
        v.create_ent('func_detail').solids.append(so)
    def P(a, o, z):   # a along the run, o across it
        return (a, c + o, z) if axis == 'x' else (c + o, a, z)
    for o in (-w / 2, w / 2):
        for z in (z0, z1):
            lo = P(min(a0, a1), o - 2, z - 2); hi = P(max(a0, a1), o + 2, z + 2)
            pr(tuple(min(lo[i], hi[i]) for i in range(3)), tuple(max(lo[i], hi[i]) for i in range(3))); n += 1
    a = min(a0, a1); h = z1 - z0; L = (step ** 2 + h ** 2) ** 0.5; ang = math.degrees(math.atan2(h, step))
    k = 0
    while a <= max(a0, a1) - step + 1:
        for o in (-w / 2, w / 2):
            lo = P(a - 1.5, o - 1.5, z0); hi = P(a + 1.5, o + 1.5, z1)
            pr(tuple(min(lo[i], hi[i]) for i in range(3)), tuple(max(lo[i], hi[i]) for i in range(3)))
            # diagonal in the side plane, alternating
            so = v.make_prism(Vec(-L / 2, -1.2, -1.2), Vec(L / 2, 1.2, 1.2), TRUSS).solid
            sign = 1 if k % 2 == 0 else -1
            if axis == 'x':
                so.localise(Vec(a + step / 2, c + o, (z0 + z1) / 2), Angle(-sign * ang, 0, 0))
            else:
                so.localise(Vec(c + o, a + step / 2, (z0 + z1) / 2), Angle(-sign * ang, 90, 0))
            v.create_ent('func_detail').solids.append(so); n += 2
        lo = P(a - 1.5, -w / 2, z1 - 1.5); hi = P(a + 1.5, w / 2, z1 + 1.5)
        pr(tuple(min(lo[i], hi[i]) for i in range(3)), tuple(max(lo[i], hi[i]) for i in range(3))); n += 1
        a += step; k += 1
    return n
# r10bd: the video's truss runs across the view under ring B and the flange (91-93 s); the old run along x north of the
# dark room showed as a diagonal lattice at the left of the frame. Drop it and carry the cross truss on to y 700.
ot = 0
for e in list(v.entities):
    if e['classname'] != 'func_detail': continue
    keep = []
    for so in e.solids:
        lo, hi = so.get_bbox()
        if (lo.y >= 618 and hi.y <= 706 and lo.x >= 6000 and hi.x <= 6700 and lo.z >= 140 and hi.z <= 215
                and all(f.mat.lower() == TRUSS.lower() for f in so.sides)):
            ot += 1; continue
        keep.append(so)
    if len(keep) != len(e.solids):
        e.solids[:] = keep
        if not keep: e.remove()
print('old gallery truss pieces removed', ot)
tn = truss_run(140, 700, 'y', 6592, 120, 195, w=72, step=70)   # r10bz: taller and closer under the tube -- the video's lattice fills the lower third (91.25-93.75 s)
tn += truss_run(6600, 6740, 'x', 0, 140, 190)            # under the tube before the cream collar (94.5-95.3 s)
print('gallery truss pieces', tn)
# copper rings on the run, and the broken dark section the camera passes through (93.5-94.25 s)
cr = 0
for e in v.entities:
    if e['classname'].startswith('prop_') and e['model'] == 'models/corehub_intro/transport_ring.mdl':
        o = Vec.from_str(e['origin'])
        if abs(o.x - 6592) < 2 and 150 < o.y < 360 and abs(o.z - 256) < 2:
            e['model'] = 'models/corehub_intro/transport_ring_orange.mdl'; e['skin'] = '0'; cr += 1
print('run rings coppered', cr)
v.create_ent('prop_static', model='models/corehub_intro/r10_broken.mdl', origin='6592 185 256', angles='0 90 0', solid='0', disableshadows='1')
# the cream collar at the end of the gallery (video 95 s): collar ring, its frame in the partition and the next ring
CREAM = unlit('collar_cream', 'lights/white002', '0.86 0.80 0.72')
cf = 0
for e in v.entities:
    if e['classname'] == 'func_detail':
        for so in e.solids:
            lo, hi = so.get_bbox()
            if lo.x >= 6783 and hi.x <= 6881 and lo.y >= -221 and hi.y <= 221 and lo.z >= 35 and hi.z <= 477:
                for f in so.sides:
                    if f.mat.lower() == 'corehub_intro/black_u': f.mat = RUST; cf += 1   # r10ax: the round white rings are the collar; the frame blends into the wall
    if e['classname'].startswith('prop_') and 'transport_ring' in e['model']:
        o = Vec.from_str(e['origin'])
        if (abs(o.x - 6767) < 2 or abs(o.x - 6818.3) < 2) and abs(o.y) < 2 and abs(o.z - 256) < 2:
            e['model'] = 'models/corehub_intro/transport_ring_white.mdl'; e['skin'] = '0'; cf += 1
print('cream collar faces/props', cf)
# ---------- r10ay: turret glare and warm rust walls ----------
# the video's lens glare (69.5-71.2 s) is a wide soft pink glow from the turret's eye down to the bottom of the frame:
# a second, wide and faint beam on the laser's own endpoints, switched on by the director for the glare only
v.create_ent('env_beam', targetname='laser_turret_glow', LightningStart='laser_turret_a', LightningEnd='laser_turret_b',
             BoltWidth='70', NoiseAmplitude='0', renderamt='16', rendercolor='255 90 100', texture='sprites/laserbeam.spr',
             spawnflags='0', life='0', damage='0', origin='4576 54 1159', TextureScroll='0', framerate='0', framestart='0', HDRColorScale='1.0')
# the "16" wall and the gallery read warm brown rust in the video; the same texture showed its grey panels there
RUST_WARM = unlit('rust_warm', 'metal/metalwall_bts_001b', '1.25 0.95 0.70')
rw = 0
for e in [v.spawn] + list(v.entities):
    for so in e.solids:
        lo, hi = so.get_bbox()
        wall16 = abs(lo.x - 4980) < 1 and abs(hi.x - 5012) < 1
        gal = lo.x >= 6330 and hi.x <= 6815 and lo.y >= -1030 and hi.y <= 1160
        for f in so.sides:
            if f.mat.lower() == 'corehub_intro/r10/rust' and ((wall16 and f.normal().x > 0.5) or gal):
                f.mat = RUST_WARM; rw += 1
print('warm rust faces', rw)
# ---------- r10az: lab (100-103 s) ----------
# the video's tube view of the lab shows black tiles and a pipe on the right until the camera turns at 103 s; the three
# hanging turrets only come into view then. They get names so the director can bring them in at 102.8 s.
ht = 0
for e in v.entities:
    if e['classname'] == 'prop_dynamic_override' and e['model'] == 'models/props_backstage/vacum_hover.mdl':
        o = Vec.from_str(e['origin'])
        if 7700 < o.x < 7950 and -200 < o.y < -100 and abs(o.z - 206.8) < 1:
            e['targetname'] = f'r10_lab_tur_{ht}'; ht += 1
print('lab hanging turrets named', ht)
# ---------- r10ba: incinerator approach (110-114 s) ----------
# the video looks down the shaft at a white iris with dark rings round it; the furnace's orange top showed round the
# iris from 110 s. A dark frame just above it (open in the middle for the camera and the falling parts) hides it until
# the camera drops through at 114.25 s.
# r10ch: the frame is a brush entity the director shows only until 111.9 s -- from 112 s the video is inside the orange
# shaft and sees no black round the light tubes (112.75-113.25 s)
_fr = [v.make_prism(Vec(*lo), Vec(*hi), TUNNEL).solid for lo, hi in (
    ((8188, -260, 1300), (8708, -75, 1306)), ((8188, 75, 1300), (8708, 260, 1306)),
    ((8188, -75, 1300), (8373, 75, 1306)), ((8523, -75, 1300), (8708, 75, 1306)))]
v.create_ent('func_brush', targetname='r10_inc_frame', Solidity='1', spawnflags='2', rendermode='0', renderamt='255',
             rendercolor='255 255 255', disablereceiveshadows='1', disableshadows='1', vrad_brush_cast_shadows='0').solids.extend(_fr)
# ---------- r10bb: shaft lids and the factory collar ----------
# the video looks down on a flat rust floor round the top collar and dark rings round the iris; the chamber's lower
# orange wall showed as a bright annulus from 110 s. Two thin plates (holes inside the collars) close the shaft
# round each collar; the camera and the falling parts pass through the holes.
v.create_ent('prop_dynamic_override', targetname='r10_inc_lid_a', model='models/corehub_intro/r10_lid_rust.mdl', origin='8448 0 1830',
             angles='0 0 0', solid='0', disableshadows='1')
v.create_ent('prop_dynamic_override', targetname='r10_inc_lid_b', model='models/corehub_intro/r10_lid_dark.mdl', origin='8448 0 1640',
             angles='0 0 0', solid='0', disableshadows='1')
fc = 0
for e in v.entities:
    if e['classname'] == 'prop_dynamic_override' and e['model'] == 'models/corehub_intro/p9_factory_collar_v4.mdl':
        o = Vec.from_str(e['origin'])
        if abs(o.x + 5420) < 1 and abs(o.y + 6000) < 1:
            e['targetname'] = 'r10_fac_collar'; fc += 1
print('factory collar named', fc)
# ---------- r10bc: gallery wall and tunnel rings ----------
# the video's gallery wall is dark grey metal with horizontal rust bands (metalwall_bts_006a, measured mean 71-92 / 64-81 /
# 60-73 against the texture's 73 / 64 / 60), panel rows about 100 units tall; the warm 001b read olive and riveted
RUST_GAL = unlit('rust_gal', 'metal/metalwall_bts_006a', '1.10 1.10 1.10')
rg = 0
for e in [v.spawn] + list(v.entities):
    for so in e.solids:
        lo, hi = so.get_bbox()
        if not (lo.x >= 6330 and hi.x <= 6815 and lo.y >= -1030 and hi.y <= 1160): continue
        for f in so.sides:
            if f.mat.lower() == RUST_WARM.lower():
                f.mat = RUST_GAL; f.uaxis.scale = 0.75; f.vaxis.scale = 0.75; rg += 1
print('gallery wall faces -> 006a', rg)
# the video passes one ring at the dark room's wall (ring A, 91 s) and one in the gallery (ring B, 92 s); the long
# tunnel of rings inside the dark room is not there
rr = 0
for e in list(v.entities):
    if e['classname'].startswith('prop_') and e['model'] == 'models/corehub_intro/transport_ring_orange.mdl':
        o = Vec.from_str(e['origin'])
        if abs(o.y - 512) < 1 and abs(o.z - 256) < 1 and any(abs(o.x - xx) < 1 for xx in (6118.4, 6195.2, 6348.8)):
            e.remove(); rr += 1
print('gallery tunnel rings removed', rr)
# ---------- r10bd: gallery rings ----------
# the video shows two pale copper rings (A at the dark room's wall, B in the gallery) and then only the broken flange;
# no ring at the bend and none on the run before the flange
gb = 0
for e in list(v.entities):
    if not e['classname'].startswith('prop_'): continue
    o = Vec.from_str(e['origin']) if e['origin'] else None
    if o is None: continue
    if e['model'] == 'models/corehub_intro/transport_ring_orange.mdl' and abs(o.y - 512) < 1 and abs(o.z - 256) < 1 and (abs(o.x - 6272) < 1 or abs(o.x - 6425.6) < 1):
        e['model'] = 'models/corehub_intro/transport_ring_pink.mdl'; gb += 1
    elif e['model'] == 'models/corehub_intro/transport_ring_bend_orange.mdl' and abs(o.x - 6592) < 1 and abs(o.y - 512) < 1:
        e.remove(); gb += 1
    elif e['model'] == 'models/corehub_intro/transport_ring_orange.mdl' and abs(o.x - 6592) < 1 and abs(o.y - 341.3) < 1:
        e.remove(); gb += 1
print('gallery rings A/B pink, bend and run ring removed', gb)
# ---------- r10be: broken flange and the last gallery ring ----------
# the video's broken section shows a jagged black hole in rust, ahead and to the right, that slides to the left as the
# camera passes (94-94.4 s): the hole faces the rust wall (east) and a black plate closes it from behind; the flange
# ring reads smaller/further in the video (93-93.75 s); a pale copper ring stands before the cream collar (94.75 s)
be = 0
for e in v.entities:
    if not e['classname'].startswith('prop_'): continue
    o = Vec.from_str(e['origin'])
    if e['model'] == 'models/corehub_intro/r10_broken.mdl' and abs(o.x - 6592) < 1 and abs(o.y - 185) < 1:
        e['model'] = 'models/corehub_intro/r10_wallhole.mdl'; e['origin'] = '6679 150 255'; e['angles'] = '0 0 0'; be += 1   # r10bf
        e['classname'] = 'prop_dynamic_override'; e['modelscale'] = '1.6'; e['solid'] = '0'   # r10bg: the video's hole is ~0.35 of the frame
    elif e['model'] == 'models/corehub_intro/transport_ring_orange.mdl' and abs(o.x - 6592) < 1 and abs(o.y - 256) < 1:
        e['classname'] = 'prop_dynamic_override'; e['modelscale'] = '0.75'; e['solid'] = '0'; be += 1
# r10bf: the video passes a jagged black hole in a rust panel close to the right of the rails (94-94.4 s), not a closed
# broken tube: a rust panel parallel to the run carries the hole (wall-hole model with two cream boxes)
pan = box((6680, 60, 150), (6690, 320, 380), RUST_GAL, world=False)
for f in pan.sides: f.uaxis.scale = 0.75; f.vaxis.scale = 0.75
v.create_ent('prop_dynamic_override', model='models/corehub_intro/transport_ring_pink.mdl', origin='6700 0 256', angles='0 0 0',
             solid='0', disableshadows='1')
print('broken flange / hole / last ring', be)
# ---------- r10bf: capsule approach rings ----------
# the video is still inside the ring tube with the capsule framed by concentric rings until ~120.9 s; two more grey rings
# past the mouth (the director shows them only 119-121 s, before the camera turns round in the vault)
for i, x in enumerate((11312, 11360)):
    v.create_ent('prop_dynamic_override', targetname=f'r10_cap_ring_{i}', model='models/corehub_intro/transport_ring.mdl',
                 origin=f'{x} 0 128', angles='0 0 0', modelscale='0.9', solid='0', disableshadows='1')
# ---------- r10bg: black beyond the cream collar ----------
# the video's cream collar (95 s) shows a black centre; the factory-tube rings behind it read as a lit tunnel
BLACK = unlit('black', 'lights/white002', '0 0 0')
_bk = v.make_prism(Vec(7300, -120, 136), Vec(7304, 120, 376), BLACK).solid   # r10bh: far end of the tube, so the rings show   # non-solid: the camera passes it in the 95.7 s black
v.create_ent('func_illusionary', rendermode='0').solids.append(_bk)
wr = 0
for e in v.entities:   # the video's tunnel beyond the collar is white rings narrowing to black
    if e['classname'].startswith('prop_') and e['model'] == 'models/corehub_intro/transport_ring_orange.mdl':
        o = Vec.from_str(e['origin'])
        if abs(o.y) < 1 and abs(o.z - 256) < 1 and (abs(o.x - 7015) < 2 or abs(o.x - 7212) < 2):
            e['model'] = 'models/corehub_intro/transport_ring_white.mdl'; wr += 1
print('collar tunnel rings white', wr)
# ---------- r10bi: rust room posts and side pipes ----------
# the video's junction rings stand on thick grey posts and carry side pipes ending in flanges (32.75-33.25 s left/right,
# 33.75 s, the shaft rings 34.5-35 s, and the lower run 36.25-37 s where the camera rides upside down: its "post below"
# is a pipe going up in the world and its "pipe left" runs to -y). A dark plane over the lower run reads as the video's
# floor there.
posts = [((-32, -5500, 2628), '90 0 0'), ((-32, -5560, 2688), '0 -90 0'),
         ((416, -5500, 2628), '90 0 0'), ((416, -5440, 2688), '0 90 0'), ((416, -5560, 2688), '0 -90 0'),
         ((768, -5162, 2628), '90 0 0'),
         ((768, -5012, 2176), '0 90 0'), ((768, -5132, 1664), '0 -90 0'), ((768, -5132, 1152), '0 -90 0'),
         ((1560, -5688, 512), '0 90 0'), ((1560, -5748, 452), '90 0 0')]   # r10ca: the lower run is shot upright now (pipe left, lit pipe down)
for (x, y, z), ang in posts:
    v.create_ent('prop_static', model='models/corehub_intro/r10_post.mdl', origin=f'{x} {y} {z}', angles=ang, solid='0', disableshadows='1')
# r10ca put a floor under the upright lower run at z 256; r10cb raises it to z 340 and runs it to the end wall (below)
print('rust room posts', len(posts))
# the lower run's down-branch at x 2048 reads as a tube going up behind the 36.25-37 s junction; the video shows it only
# from 37.5 s. Named so the director can bring it in then.
db = 0
for e in v.entities:
    if e['classname'].startswith('prop_') and e['model'] == 'models/corehub_intro/p9_entry_ring.mdl':
        o = Vec.from_str(e['origin'])
        if abs(o.x - 2048) < 1 and abs(o.y + 5748) < 1 and o.z in (0.0, 128.0, 256.0):
            e['classname'] = 'prop_dynamic_override'; e['targetname'] = f'r10_rr_down_{int(o.z)}'; db += 1
print('down-branch rings named', db)
# ---------- r10bj: factory floor beyond the walkway ----------
# the video's walkway is mid grey (measured 93/91/88) but the floor beyond its railings is near black-brown (28/20/15);
# the one floor slab under both read 52/47/39 there. Split it: the walkway strip keeps the floor material.
FAC_FLOOR_DARK = unlit('fac_floor_dark', 'metal/metalfloor_bts_001a', '0.60 0.60 0.60')
ff = 0
for e in [v.spawn] + list(v.entities):
    keep = []
    for so in e.solids:
        lo, hi = so.get_bbox()
        if (abs(lo.z - 140) < 1 and abs(hi.z - 156) < 1 and abs(lo.y + 6744) < 1 and abs(hi.y + 5904) < 1
                and any(f.mat.lower() == 'corehub_intro/p9_factory_v4_floor' for f in so.sides)):
            ff += 1; continue
        keep.append(so)
    if len(keep) != len(e.solids):
        e.solids[:] = keep
if ff:
    box((-6600, -6744, 140), (-3500, -6090, 156), FAC_FLOOR_DARK, world=False)
    box((-6600, -6090, 140), (-3500, -5904, 156), 'corehub_intro/p9_factory_v4_floor', world=False)
print('factory floor split', ff)
# the grey benches beyond the walkway read as pale slabs; the video shows dark machinery there
FAC_BENCH_DARK = unlit('fac_bench_dark', 'lights/white002', '0.20 0.17 0.14')
fb = 0
for e in v.entities:
    if e['classname'] != 'func_detail': continue
    for so in e.solids:
        lo, hi = so.get_bbox()
        if hi.y <= -6090 and lo.x >= -6600 and hi.x <= -3500 and lo.z >= 140 and hi.z <= 260:
            for f in so.sides:
                if f.mat.lower() == 'corehub_intro/p9_factory_v4_grey': f.mat = FAC_BENCH_DARK; fb += 1
print('factory benches darkened', fb)
# ---------- r10bl: lab tube view (100-102.8 s) ----------
# from the lab tube the video sees black tiles on the right with a grey pipe and a small white sign; our white test
# chamber and its turret cables showed there. A black-tiled screen (func_brush) and the pipe stand between the tube and
# the chamber until the camera turns at 102.8 s, when the director moves them away.
ls_wall = v.make_prism(Vec(7480, -156, 60), Vec(7990, -148, 480), LABDARK).solid
ls_sign = v.make_prism(Vec(7600, -148, 196), Vec(7636, -146, 232), SIGNW).solid
v.create_ent('func_brush', targetname='r10_lab_screen', Solidity='1', spawnflags='2', rendermode='0', renderamt='255',
             rendercolor='255 255 255', disablereceiveshadows='1', disableshadows='1', vrad_brush_cast_shadows='0').solids.extend([ls_wall, ls_sign])
for i, x in enumerate((7480, 7730)):
    v.create_ent('prop_dynamic_override', targetname=f'r10_lab_pipe_{i}', model='models/corehub_intro/r10_post.mdl',
                 origin=f'{x} -134 272', angles='0 0 0', solid='0', disableshadows='1')
# ---------- r10bn: tower climb tube ----------
# the video's tube rings in the tower are dark and clear; the light skin and the glass haze greyed the whole climb
tt = 0
for e in v.entities:
    if e['classname'].startswith('prop_') and e['model'] in ('models/corehub_intro/transport_ring.mdl', 'models/corehub_intro/transport_ring_bend.mdl'):
        o = Vec.from_str(e['origin'])
        if 3650 < o.x < 4100 and abs(o.y) < 150 and 1250 < o.z < 1750:
            e['model'] = e['model'].replace('.mdl', '_ng.mdl'); e['skin'] = '0'
            e['classname'] = 'prop_dynamic_override'; e['targetname'] = f'r10_tw_tube_{tt}'; e['solid'] = '0'; tt += 1   # r10bp: hidden during the climb
print('tower tube rings dark/clear', tt)
# ---------- r10bo: pod walls ----------
# the video's pod walls are shelves of small oval pods in rows with thin cables hanging in front (40-42 s); the old
# panels carried a few large round blobs
pw = 0
for e in v.entities:
    if e['classname'].startswith('prop_') and e['model'] == 'models/corehub_intro/pod_wall.mdl':
        e['model'] = 'models/corehub_intro/pod_wall2.mdl'; pw += 1
print('pod walls -> shelves', pw)
# ---------- r10br: scanner close-up ----------
# the video brings a scanner head with its three yellow light cones right up to the lens (80-80.75 s) before it settles
# above the iris; a copy pointing up at the camera is moved by the director
for nm, mdl in (('r10_close_cones', 'transfer_scan_cones'), ('r10_close_head', 'transfer_scan_head')):
    v.create_ent('prop_dynamic_override', targetname=nm, model=f'models/corehub_intro/{mdl}.mdl', origin='4800 0 700',
                 angles='90 0 0', solid='0', disableshadows='1')
# ---------- r10bs: turret room backdrop and glare, scanner close-up arm, rust room panel ----------
# the video's wall behind the turret is the rust-patched tile (68-69.25 s: mean 80/76/76, textured); the grey-seamed
# tile read as a dark grooved wall (50/49/50)
RUST_TU = unlit('rust_tu', 'metal/metalwall_bts_006a', '1.22 1.30 1.36')
tu = 0
for e in v.entities:
    if e['classname'] != 'func_detail': continue
    for so in e.solids:
        lo, hi = so.get_bbox()
        if lo.x >= 4350 and hi.x <= 4840 and lo.y >= 90 and hi.y <= 340 and lo.z >= 850 and hi.z <= 1710:
            for f in so.sides:
                if f.mat.lower() == RUST.lower(): f.mat = RUST_TU; tu += 1
print('turret backdrop faces -> 006a', tu)
# the three thin cage posts stay in front of the grey band in our shot; the video's bars leave the frame by 67.5 s
posts_tu = []
for e in list(v.entities):
    if e['classname'] != 'func_detail': continue
    keep = []
    for so in e.solids:
        lo, hi = so.get_bbox()
        if (4470 <= lo.x and hi.x <= 4670 and 95 <= lo.y and hi.y <= 170 and abs(lo.z - 950) < 1 and abs(hi.z - 1345) < 1
                and hi.x - lo.x < 20):
            posts_tu.append(so); continue
        keep.append(so)
    if len(keep) != len(e.solids):
        e.solids[:] = keep
        if not e.solids: v.remove_ent(e)
if posts_tu:
    v.create_ent('func_brush', targetname='r10_tu_posts', Solidity='1', spawnflags='2', rendermode='0', renderamt='255',
                 rendercolor='255 255 255', disablereceiveshadows='1', disableshadows='1', vrad_brush_cast_shadows='0').solids.extend(posts_tu)
print('turret cage posts -> func_brush', len(posts_tu))
# the scanner shaft's rings and boards showed at the right of the turret shot; the video has the rust wall and band there
scr_wall = v.make_prism(Vec(4716, -260, 850), Vec(4724, 420, 1500), RUST_TU).solid   # r10bz: wider -- the lift descent (64-66 s) looks past it too
scr_band = v.make_prism(Vec(4712, -260, 950), Vec(4716, 420, 1011), BAND).solid
v.create_ent('func_brush', targetname='r10_tu_screen', Solidity='1', spawnflags='2', rendermode='0', renderamt='255',
             rendercolor='255 255 255', disablereceiveshadows='1', disableshadows='1', vrad_brush_cast_shadows='0').solids.extend([scr_wall, scr_band])
# glare (69.4-71.3 s): the video's red is a soft wedge from the eye down to the bottom of the frame (legs R-G ~50, corners
# ~30); the wide beam ended at the lens and washed the whole lower half pink. Its own end point now sits just inside the
# bottom of the frame (moved by the director) and the thin laser is off during the glare.
v.create_ent('info_target', targetname='r10_glow_b', origin='4555 20 987', spawnflags='1')
for e in v.entities:
    if e['targetname'] == 'laser_turret_glow':
        e['LightningEnd'] = 'r10_glow_b'; e['BoltWidth'] = '34'; e['renderamt'] = '12'; e['rendercolor'] = '255 50 60'
# the shaft scanners' lasers read as a bright starburst; the video's are thin and dim
sb = 0
for e in v.entities:
    if e['classname'] == 'env_beam' and e['targetname'].startswith('shaft_') and e['targetname'].endswith('_beam'):
        e['renderamt'] = '38'; sb += 1
print('shaft beams dimmed', sb)
# scanner close-up (79.75-81 s): the head rides on a long white arm crossing the frame (top-left to bottom-right)
for nm, yaw in (('r10_close_arm_a', 195), ('r10_close_arm_b', 15)):
    v.create_ent('prop_dynamic_override', targetname=nm, model='models/corehub_intro/transfer_scan_link.mdl', origin='4800 0 700',
                 angles=f'0 {yaw} 0', solid='0', disableshadows='1')
# rust room: junction A carries only the left side pipe in the video (33-33.25 s)
for e in list(v.entities):
    if e['classname'] == 'prop_static' and e['model'] == 'models/corehub_intro/r10_post.mdl' and e['origin'] == '416 -5560 2688':
        v.remove_ent(e); print('junction A right pipe removed')
# rust room: the video's panel behind junction A is taller and wider (33.0-33.2 s: top at 25 -> 10 %, left edge 26 -> 15 %);
# open the black frame to y -6320..-4977, z 2510..ceiling and carry the rust wall up to the ceiling
RUST_RR = unlit('rust_rr', 'metal/metalwall_bts_006a', '0.80 0.83 0.88')   # r10cb: rust pixels read 20 % brighter and redder than the video (33.25-36 s: warm median 76 vs 61)
win = 0
for e in v.entities:
    if e['classname'] != 'func_detail': continue
    keep = []
    for so in e.solids:
        lo, hi = so.get_bbox()
        if abs(lo.x - 878) < 1 and abs(hi.x - 884) < 1 and lo.z >= 2399 and hi.z <= 3001 and lo.y >= -6501 and hi.y <= -4599:
            win += 1; continue
        keep.append(so)
    if len(keep) != len(e.solids): e.solids[:] = keep
if win:
    box((878, -6500, 2400), (884, -6320, 3000), 'corehub_intro/black_u', world=False)
    box((878, -6320, 2400), (884, -4977, 2510), 'corehub_intro/black_u', world=False)
    box((878, -4977, 2400), (884, -4600, 3000), 'corehub_intro/black_u', world=False)
    box((896, -6320, 2848), (912, -4800, 2976), RUST_RR, world=False)
print('rust room window frame pieces replaced', win)
# rust room walls read 25 % darker and redder than the video (33-37 s: 47-55 vs 59-71)
rr = 0
for e in [v.spawn] + list(v.entities):
    for so in e.solids:
        lo, hi = so.get_bbox()
        if lo.x >= -2340 and hi.x <= 3270 and lo.y >= -6700 and hi.y <= -3460 and lo.z >= -560 and hi.z <= 3010:
            for f in so.sides:
                if f.mat.lower() == 'corehub_intro/steel_u': f.mat = RUST_RR; rr += 1
print('rust room faces -> rust_rr', rr)
# ---------- r10bu: glare tuning, the inlet iris shot (71.34-72.3 s) ----------
# glare: a stronger, darker veil flattens the wall like the video (sd 3-5); the glow beam is half as wide and fainter
for e in v.entities:
    if e['targetname'] == 'r10_red_fade': e['rendercolor'] = '137 136 136'
    if e['targetname'] == 'laser_turret_glow':
        e['BoltWidth'] = '18'; e['renderamt'] = '8'; e['rendercolor'] = '255 40 50'
    if e['classname'] == 'env_beam' and e['targetname'].startswith('shaft_') and e['targetname'].endswith('_beam'):
        e['renderamt'] = '22'
# the video cuts (a quick dissolve) from the glare to a look straight down into the inlet iris, a scanner arm with its
# yellow cones reaching in and the rust floor around it (71.4-71.75 s), then tilts up to the "16" wall. A rust plate
# with a square hole under the petals stands in for that floor while the shot lasts; the tube ring above the petals and
# the cake are moved away.
pl = []
for lo, hi in (((4560, -320, 940), (4715, 320, 946)), ((4885, -320, 940), (4980, 320, 946)),
               ((4715, -320, 940), (4885, -85, 946)), ((4715, 85, 940), (4885, 320, 946))):
    pl.append(v.make_prism(Vec(*lo), Vec(*hi), RUST_TU).solid)
# r10cc: the video's iris sits on a grey square (71.5-71.75 s), not over the open tube; a grey floor under the petals
pl.append(v.make_prism(Vec(4715, -85, 922), Vec(4885, 85, 928), unlit('scan_grey', 'lights/white002', '0.48 0.48 0.48')).solid)
v.create_ent('func_brush', targetname='r10_inlet_plate', Solidity='1', spawnflags='2', rendermode='0', renderamt='255',
             rendercolor='255 255 255', disablereceiveshadows='1', disableshadows='1', vrad_brush_cast_shadows='0').solids.extend(pl)
ir = 0
for e in v.entities:
    if e['classname'] == 'prop_static' and e['model'] == 'models/corehub_intro/transport_ring_white.mdl' and e['origin'] in ('4800 0 984', '4800.0 0.0 984.0'):
        e['classname'] = 'prop_dynamic_override'; e['targetname'] = 'r10_inlet_ring'; e['solid'] = '0'; ir += 1
print('inlet ring named', ir)
# ---------- r10bv: lens glare as a screen overlay sequence (69.4-71.34 s) ----------
# the screen fade dimmed the red glow with everything else; a translucent overlay sequence carries both the grey veil
# and the red glow round the turret's lower body, stepping every 0.2 s with the turret as the camera tilts
sys.path.insert(0, str(R10 / 'tools'))
import make_glare
gl = make_glare.main()
kv = {'targetname': 'r10_glare_ov', 'origin': '4544 0 1000'}
for i, (nm, d) in enumerate(zip(gl, [0.2] * 9 + [0.14]), 1):
    kv[f'OverlayName{i}'] = nm; kv[f'OverlayTime{i}'] = str(d)
v.create_ent('env_screenoverlay', **kv)
for e in v.entities:
    if e['targetname'] == 'laser_turret_glow': e['renderamt'] = '0'
print('glare overlays', len(gl))
# ---------- r10bx: pod walls and the pale tube end ----------
# the video's pod shelves read lighter and with more contrast (40-41 s right side 63-78, sd 15-27; ours 43-48, sd 10-13)
for k, c in ((2, 0.0793), (3, 0.1249), (4, 0.1819), (5, 0.2508), (6, 0.3320), (7, 0.4256)):
    c2 = round(c * 1.5, 4)
    (MOD / 'materials/models/corehub_intro' / f'podwall_s{k}.vmt').write_text(
        f'"UnlitGeneric"\n{{\n"$basetexture" "lights/white002"\n"$color" "[{c2} {c2} {round(c2 * 1.02, 4)}]"\n}}\n')
# the pale wall closing the tube fills the frame at 48.5 s in the video (140-160); the cap read 112
(MOD / 'materials/models/corehub_intro/r10_tube_end.vmt').write_text(
    '"UnlitGeneric"\n{\n"$basetexture" "concrete/concrete_modular_wall001a"\n"$color" "[0.88 0.89 0.88]"\n"$nocull" "1"\n"$model" "1"\n}\n')
# ---------- r10bx: dark run before the cube room (49-50.6 s) ----------
# the video rides a dark tube from the pale wall to the cube room (49.25-50.5 s: dark rings, nothing of the room); our
# clear tube showed the room's pale walls the whole way. A dark sleeve round the tube hides them until 50.6 s.
sl = []
for lo, hi in (((2790, -96, 1056), (3400, -90, 1248)), ((2790, 90, 1056), (3400, 96, 1248)),
               ((2790, -96, 1056), (3400, 96, 1062)), ((2790, -96, 1242), (3400, 96, 1248))):
    sl.append(v.make_prism(Vec(*lo), Vec(*hi), TUNNEL).solid)
v.create_ent('func_brush', targetname='r10_cube_sleeve', Solidity='1', spawnflags='2', rendermode='0', renderamt='255',
             rendercolor='255 255 255', disablereceiveshadows='1', disableshadows='1', vrad_brush_cast_shadows='0').solids.extend(sl)
# ---------- r10by: turret lift seen from below the collar (63.87-67 s) ----------
# the video comes in beside the dark collar, drops under it and looks down past the tubes that hang from it into the
# floor ring the turret rises from; the tubes (and a pale skirt under the collar) leave once the turret is level
v.create_ent('prop_dynamic_override', targetname='r10_tu_tubes', model='models/corehub_intro/r10_tu_tubes.mdl', origin='4575 58 1340',
             angles='0 0 0', solid='0', disableshadows='1')
# ---------- r10bz: scanner iris view (81-82.4 s) ----------
# the exit collar showed at the top of the iris view; the video has the arm's dark beam there
for e in v.entities:
    if (e['classname'].startswith('prop_') and e['model'] == 'models/corehub_intro/transport_ring_orange.mdl' and e['targetname'] == 'r10_wall_collar'
            and abs(Vec.from_str(e['origin']).x - 4967) < 2):
        e['targetname'] = 'r10_exit_collar'; print('exit collar renamed', e['origin'])
# ---------- r10cb: rust room lower run (36.2-38.94 s) ----------
# the video's lower run passes a rust panel at junction E (x ~1690: 36.25-37.4 s its top edge and sides fit a panel
# ~515 wide reaching z ~624, the tube through a hole), then looks at a wall that fills the frame above a pale band and a
# dark floor (37.5-38.3 s: band at ~62 %, floor below). Ours showed the small end panel far off inside black.
RUST_BAND = unlit('rust_band', 'metal/metalwall_bts_006a', '1.30 1.22 1.12')
for lo, hi in (((1688, -6028, 300), (1696, -5800, 624)), ((1688, -5696, 300), (1696, -5514, 624)),
               ((1688, -5800, 300), (1696, -5696, 460)), ((1688, -5800, 564), (1696, -5696, 624))):
    box(lo, hi, RUST_RR, world=False)
ew = 0
for e in v.entities:
    if e['classname'] != 'func_detail': continue
    keep = []
    for so in e.solids:
        lo, hi = so.get_bbox()
        if abs(lo.x - 2272) < 1 and abs(hi.x - 2280) < 1 and lo.y > -6200 and hi.y < -5370 and lo.z > -101 and hi.z < 1101:
            ew += 1; continue
        keep.append(so)
    if len(keep) != len(e.solids): e.solids[:] = keep
box((2272, -6460, -100), (2280, -5040, 1150), RUST_RR, world=False)     # end wall: floor to above the frame, full width
box((2268, -6460, 348), (2272, -5040, 364), RUST_BAND, world=False)      # the pale band above the floor
for lo, hi in (((860, -6460, 340), (2272, -5798, 348)), ((860, -5698, 340), (2272, -5040, 348)),
               ((860, -5798, 340), (1998, -5698, 348)), ((2098, -5798, 340), (2272, -5698, 348))):
    box(lo, hi, RUST_DARK, world=False)                                  # floor at z 340 with a hole for the down-branch
for e in v.entities:   # the lower corridor's black ceiling slab reads as the video's dark rust (38.25-38.9 s)
    if e['classname'] != 'func_detail': continue
    for so in e.solids:
        lo, hi = so.get_bbox()
        if abs(lo.x - 2176) < 1 and abs(hi.x - 3008) < 1 and abs(lo.z + 128) < 1 and abs(hi.z + 112) < 1:
            for f in so.sides: f.mat = RUST_DARK
print('r10cb lower run: end wall pieces replaced', ew)
# ---------- r10cc: scanner iris view (80.75-82.9 s) ----------
# the video looks straight down at the iris set in a flat rust floor: a grey square behind the petals, black beams left
# and right, a darker panel on the right, black at the top and bottom edges (81.5 s: floor 85/74/69, grey 123, panel
# 65/61/62). Ours looked down into the open room, its walls and the floor far below. A func_brush floor stands in while
# the shot lasts; the static orange ring in the front wall's tube opening becomes dynamic so the director can move it out.
SCAN_FLOOR = unlit('scan_floor', 'metal/metalwall_bts_006a', '1.00 1.00 1.03')
SCAN_PANEL = unlit('scan_panel', 'metal/metalwall_bts_006a', '0.78 0.80 0.86')
SCAN_GREY = unlit('scan_grey', 'lights/white002', '0.48 0.48 0.48')
sp = []
for lo, hi, m in (
        ((4635, 125, 278), (4950, 250, 284), SCAN_FLOOR), ((4635, -175, 278), (4950, -125, 284), SCAN_FLOOR),
        ((4635, -125, 278), (4650, 125, 284), SCAN_FLOOR), ((4920, -125, 278), (4950, 125, 284), SCAN_FLOOR),
        ((4650, -125, 114), (4920, 125, 120), RUST_DARK),    # r10cd/cf: dark rust seen through the opened iris (82.3-82.6 s)
        ((4560, 250, 278), (4980, 440, 286), 'corehub_intro/black_u'), ((4560, -194, 278), (4980, -175, 286), 'corehub_intro/black_u'),
        ((4560, -440, 278), (4980, -194, 284), SCAN_PANEL),
        ((4950, -175, 278), (4980, 250, 290), 'corehub_intro/black_u'), ((4560, -175, 278), (4635, 250, 286), 'corehub_intro/black_u'),
        ((4976, -440, 290), (4980, 440, 360), 'corehub_intro/black_u')):
    sp.append(v.make_prism(Vec(*lo), Vec(*hi), m).solid)
v.create_ent('func_brush', targetname='r10_scan_plate', Solidity='1', spawnflags='2', rendermode='0', renderamt='255',
             rendercolor='255 255 255', disablereceiveshadows='1', disableshadows='1', vrad_brush_cast_shadows='0').solids.extend(sp)
# r10cd: the grey shutter under the petals is its own brush -- the video's iris opens at ~82.3 s
v.create_ent('func_brush', targetname='r10_scan_grey', Solidity='1', spawnflags='2', rendermode='0', renderamt='255',
             rendercolor='255 255 255', disablereceiveshadows='1', disableshadows='1', vrad_brush_cast_shadows='0').solids.append(
    v.make_prism(Vec(4650, -125, 250), Vec(4920, 125, 256), SCAN_GREY).solid)
for e in v.entities:
    if (e['classname'] == 'prop_static' and e['model'] == 'models/corehub_intro/transport_ring_orange.mdl'
            and abs(Vec.from_str(e['origin']).x - 4968.7) < 0.5 and abs(Vec.from_str(e['origin']).z - 256) < 1):
        e['classname'] = 'prop_dynamic_override'; e['targetname'] = 'r10_exit_collar2'; print('static exit collar named', e['origin'])
# ---------- r10cd: inlet iris look (71.3-72.35 s) ----------
# the video's inlet iris from above is the transfer iris: flat white petals in a square round a grey frame with cyan
# lights. Ours (the cake iris, petals pointing up, the plain frame) read as a black disc with angled petals. While the
# shot lasts the director swaps in a copy of the transfer iris (petals 12 above the refined frame, as at 274/286).
for e in v.entities:
    if e['classname'].startswith('prop_') and e['model'] == 'models/corehub_intro/iris_frame.mdl':
        o = Vec.from_str(e['origin'])
        if abs(o.x - 4800) < 1 and abs(o.y) < 1 and abs(o.z - 950) < 1:
            e['classname'] = 'prop_dynamic_override'; e['targetname'] = 'r10_inlet_frame_orig'; print('inlet frame named')
v.create_ent('prop_dynamic_override', targetname='r10_inlet_frame2', model='models/corehub_intro/transfer_refined_iris_frame.mdl',
             origin='4800 0 938', angles='90 0 0', solid='0', disableshadows='1')
for k, (x, y, yaw) in enumerate(((4838.2, 38.2, 0), (4838.2, -38.2, 270), (4761.8, -38.2, 180), (4761.8, 38.2, 90))):
    v.create_ent('prop_dynamic_override', targetname=f'r10_inlet_petal_{k}', model='models/corehub_intro/iris_quarter.mdl',
                 origin=f'{x} {y} 950', angles=f'90 {yaw} 0', solid='0', disableshadows='1')
# ---------- r10ce: the opening's light flicker (6.8-7.85 s) ----------
import make_flicker
fl = make_flicker.main()
kv = {'targetname': 'r10_flicker_ov', 'origin': '-12825 -191 100'}
for i, (nm, d) in enumerate(fl, 1):
    kv[f'OverlayName{i}'] = nm; kv[f'OverlayTime{i}'] = str(d)
v.create_ent('env_screenoverlay', **kv)
print('flicker overlays', len(fl))
# ---------- r10cf: opening chamber glass, capsule glass ----------
# the opening's chamber glass is a 2-unit brush drawn from both sides (nocull), so its upper panel reads as a flat grey band
# (98) where the video's is darker (69-73 at 11-11.5 s)
(MOD / 'materials/corehub_intro/p9_exterior_v2/chamber_glass.vmt').write_text(
    '"UnlitGeneric"\n{\n"$basetexture" "lights/white002"\n"$color" "[0.47 0.47 0.47]"\n"$alpha" "0.34"\n"$surfaceprop" "glass"\n"$translucent" "1"\n"$nocull" "1"\n}\n')
# the capsule's frosted glass read teal (G/B +10-12 over R) where the video's is neutral grey (121-122.5 s: 123/125/126)
(MOD / 'materials/models/corehub_intro/p9_end_capsule_frost.vmt').write_text(
    '"UnlitGeneric"\n{\n"$basetexture" "lights/white002"\n"$model" "1"\n"$translucent" "1"\n"$nocull" "1"\n"$alpha" "0.35"\n"$color" "[0.53 0.54 0.55]"\n}\n')
# ---------- r10cg: capsule approach frames (119.4-120.8 s) ----------
# the video sees salmon-red strips round the tube on the way to the capsule (120.1-120.4 s: 4.7-7.3 % of the frame at
# 166-174/123-128/109-113); they are the vertical sides of the square frames every 128 units, ours dark rust
CAP_FRAME = unlit('cap_frame', 'lights/white002', '0.66 0.48 0.42')
cf = 0
for e in v.entities:
    if e['classname'] != 'func_detail': continue
    for so in e.solids:
        lo, hi = so.get_bbox()
        if 10290 <= lo.x and hi.x <= 11210 and hi.x - lo.x < 10 and (abs(lo.y + 180) < 1 or abs(lo.y - 164) < 1) and hi.y - lo.y < 20 and lo.z < -40 and hi.z > 300:
            for f in so.sides:
                if f.mat.lower() == 'metal/metalwall_bts_006b': f.mat = CAP_FRAME; cf += 1
print('capsule frame sides salmon', cf)
# ---------- r10ch: pod rise tube veil (39.2-41.8 s) ----------
# the video's pod-rise tube reads as grey frosted walls with the shelves washed out behind them; our tube glass is nearly
# clear (alpha 0.15). A translucent 16-sided sleeve inside the rings (radius 40, inner faces only) veils everything but
# the far opening while the rise lasts.
# r10ci: the veil is lighter where the video's tube is (frame top and right) and near black where it is dark (left and
# bottom): measured 82/72/42/33 against our 56/64/57/57; looking up with roll -20 the frame's top, right, bottom and left
# are the tube's azimuths 160, 250, 340 and 70 degrees
import math as _m
_anch = [(70, 0.03), (160, 0.55), (250, 0.36), (340, 0.0), (430, 0.03)]
def _veil_c(az):
    az = az % 360
    if az < 70: az += 360
    for (a0, c0), (a1, c1) in zip(_anch, _anch[1:]):
        if a0 <= az <= a1: return c0 + (c1 - c0) * (az - a0) / (a1 - a0)
    return 0.2
pv = []
for k in range(16):
    yaw = k * 22.5; rr = 60.0   # r10cp: outside the rails (the video's rails read black, unveiled)
    c = round(_veil_c(yaw), 3)
    POD_VEIL = unlit(f'pod_veil_{k:02d}', 'lights/white002', f'{c} {c} {round(c * 1.02, 3)}', '"$translucent" "1"\n"$alpha" "0.36"\n"$nocull" "1"\n')
    cx, cy = 1856 + rr * _m.cos(_m.radians(yaw)), -256 + rr * _m.sin(_m.radians(yaw))
    sol = v.make_prism(Vec(-1, -12.5, 560), Vec(1, 12.5, 1120), POD_VEIL).solid
    sol.localise(Vec(cx, cy, 0), _st.Angle(0, yaw, 0))
    rx, ry = _m.cos(_m.radians(yaw)), _m.sin(_m.radians(yaw))
    for f in sol.sides:   # side normals point into the solid: the face nearest the axis has its normal along +radial
        n = f.normal()
        if n.x * rx + n.y * ry < 0.9: f.mat = NODRAW
    pv.append(sol)
v.create_ent('func_brush', targetname='r10_pod_sleeve', Solidity='1', spawnflags='2', rendermode='0', renderamt='255',
             rendercolor='255 255 255', disablereceiveshadows='1', disableshadows='1', vrad_brush_cast_shadows='0').solids.extend(pv)
print('pod sleeve', len(pv), sum(1 for so in pv for f in so.sides if 'pod_veil' in f.mat))
# ---------- r10cl: factory walkway (96.6-99.8 s) ----------
# the video's walkway under the tube reads lighter and warmer than ours (97-97.25 s: 75/74/72 vs 60/58/54; 99.25-99.5 s:
# 83-113/65-83/52-59 vs 68-72/66-68/60-61)
(MOD / 'materials/corehub_intro/p9_factory_v4_floor.vmt').write_text(
    '"UnlitGeneric"\n{\n"$basetexture" "metal/black_wall_metal_002a"\n"$color" "[0.66 0.59 0.49]"\n"$model" "1"\n}\n')
(MOD / 'materials/corehub_intro/p9_factory_v7_plate.vmt').write_text(
    '"UnlitGeneric"\n{\n"$basetexture" "lights/white002"\n"$color" "[0.48 0.48 0.46]"\n"$surfaceprop" "metal"\n}\n')
# ---------- r10cm: the lift's hanging tubes ----------
# the video's tubes under the lift collar read dark grey, ours near black (65.6-66.3 s our frames 35-46 vs the video's 50-64)
(MOD / 'materials/models/corehub_intro/r10_tu_tube.vmt').write_text(
    '"UnlitGeneric"\n{\n"$basetexture" "lights/white002"\n"$color" "[0.16 0.16 0.165]"\n"$model" "1"\n}\n')
# ---------- r10cn: tower entrance junction (55.5-58.55 s) ----------
# the bend at the junction read as a big glossy dome in front of the collar; the video sees the collar ring with the tube's
# far end small inside it and rust behind. The bend becomes dynamic so the director can take it out for the approach.
for e in v.entities:
    if e['classname'] == 'prop_static' and e['model'] == 'models/corehub_intro/transport_ring_bend.mdl':
        o = Vec.from_str(e['origin'])
        if abs(o.x - 3754) < 1 and abs(o.y) < 1 and abs(o.z - 1152) < 1:
            e['classname'] = 'prop_dynamic_override'; e['targetname'] = 'r10_tw_bend'; print('tower bend named')
# ---------- r10co: cube passage tube end (52.5-53.9 s) ----------
# the video is still deep in the tube when it fades (53.0-53.8 s: rings nested far ahead, the cube among them); ours
# reached the wall collar and looked out at the lit tower room. Rings stand in beyond the collar until the fade.
for k, x in enumerate((3431, 3509, 3587, 3665)):
    v.create_ent('prop_dynamic_override', targetname=f'r10_cp_ring_{k}', model='models/corehub_intro/transport_ring.mdl',
                 origin=f'{x} 0 1152', angles='0 0 0', skin='2', solid='0', disableshadows='1')
# and the tube walls read as frosted grey there (53.0-53.8 s), not clear: a translucent sleeve along the tube (x axis)
CP_VEIL = unlit('cp_veil', 'lights/white002', '0.46 0.46 0.47', '"$translucent" "1"\n"$alpha" "0.42"\n"$nocull" "1"\n')
cpv = []
for k in range(16):
    ang = k * 22.5; rr = 60.0   # r10cp: outside the rails
    cy, cz = rr * _m.cos(_m.radians(ang)), 1152 + rr * _m.sin(_m.radians(ang))
    sol = v.make_prism(Vec(2950, -12.5, -1), Vec(3720, 12.5, 1), CP_VEIL).solid
    sol.localise(Vec(0, cy, cz), _st.Angle(0, 0, ang - 90))
    ry, rz = _m.cos(_m.radians(ang)), _m.sin(_m.radians(ang))
    for f in sol.sides:
        n = f.normal()
        if n.y * ry + n.z * rz < 0.9: f.mat = NODRAW
    cpv.append(sol)
v.create_ent('func_brush', targetname='r10_cp_sleeve', Solidity='1', spawnflags='2', rendermode='0', renderamt='255',
             rendercolor='255 255 255', disablereceiveshadows='1', disableshadows='1', vrad_brush_cast_shadows='0').solids.extend(cpv)
print('cube passage sleeve', len(cpv), sum(1 for so in cpv for f in so.sides if f.mat == CP_VEIL))
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
