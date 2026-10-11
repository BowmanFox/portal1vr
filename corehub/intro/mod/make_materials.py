#!/usr/bin/env python3
"""Generator for the corehub_intro mod's own materials (rebuilt on the Mac, Oct 2026).

The original VMTs were lost with the old PC. Colours here were recovered from the published review sheets
(r10m_dj) by rendering each surface with the director's camera and solving its colour, then checked in test runs
against the 2009 video. Every material is UnlitGeneric: "$color" on a stock base texture.

usage: make_materials.py OUTDIR   -> writes OUTDIR/materials/corehub_intro/... and OUTDIR/materials/models/corehub_intro/...
The r10 materials (materials/corehub_intro/r10) are written by the r10 patch scripts and are not touched here.
"""
import os, sys

W = 'lights/white002'
MAP = {}      # name (under materials/corehub_intro) -> dict(base, color, extra)
MODEL = {}    # name (under materials/models/corehub_intro) -> dict


def u(table, name, color, base=W, alpha=None, nocull=False, extra=None, model=False):
    if isinstance(color, (int, float)): color = (color, color, color)
    d = dict(base=base, color=tuple(round(float(c), 4) for c in color), alpha=alpha, nocull=nocull, extra=dict(extra or {}))
    if model: d['extra'].setdefault('$model', '1')
    table[name] = d


def ramp(table, prefix, top, factors, **kw):
    for i, f in enumerate(factors):
        u(table, f'{prefix}{i}', tuple(c * f for c in (top if not isinstance(top, (int, float)) else (top,) * 3)), **kw)


# ----------------------------------------------------------------------------------------------- map materials
# opening room (the chamber, its glass, the service area and dust outside)
u(MAP, 'p9_room_metric_v13/opening_floor', (0.53, 0.543, 0.546), base='tile/white_floor_tile002b')
u(MAP, 'p9_joined_v12/far_wall', (0.655, 0.655, 0.652), base='tile/white_wall_tile003a')
u(MAP, 'p9_joined_v12/plaster', (1.0, 1.0, 1.02), base='concrete/concrete_bts_wall001a')
# The director drives this material's $color through the map's material_modify_control (the ceiling "exposure"),
# which only works when the material carries the MaterialModify proxy.
u(MAP, 'p9_ceiling_exposure_v2', (0.93, 0.91, 0.94), base='tile/white_ceiling_tile001a', extra={'__raw__': '"Proxies"\n{\n"MaterialModify"\n{\n}\n}'})
u(MAP, 'p9_joined_v14/border', (0.142, 0.149, 0.139))
u(MAP, 'p9_joined_v14/ceiling', (0.60, 0.60, 0.59))
u(MAP, 'p9_exterior_v2/service_panel', (0.225, 0.262, 0.292), base='tile/white_wall_tile003a')
u(MAP, 'p9_exterior_v2/service_concrete', (0.264, 0.28, 0.272))
u(MAP, 'p9_exterior_v2/exposed_concrete', (0.35, 0.363, 0.357))
for k, c in enumerate(((0.30, 0.312, 0.315), (0.315, 0.328, 0.331), (0.329, 0.343, 0.347), (0.343, 0.357, 0.35), (0.343, 0.357, 0.357), (0.376, 0.389, 0.389))):
    u(MAP, f'p9_exterior_v2/dust_{k}', c)
u(MAP, 'p9_exterior_v2/frame_steel', (0.20, 0.21, 0.215))
u(MAP, 'p9_exterior_v2/chamber_glass', (0.47, 0.47, 0.47), alpha=0.34, nocull=True, extra={'$surfaceprop': 'glass'})
u(MAP, 'p9_exterior_v1/frame_steel', (0.254, 0.266, 0.274))
u(MAP, 'p9_exterior_v1/painted_steel', (0.287, 0.295, 0.287))
u(MAP, 'p9_exterior_v1/panel_edge', (0.337, 0.343, 0.323))
u(MAP, 'p9_room_metric_v13/mound_concrete', (0.344, 0.351, 0.351))
u(MAP, 'p9_room_metric_v13/rail_light', (0.195, 0.198, 0.203))
u(MAP, 'p9_room_metric_v13/raised_panel_top', (0.272, 0.28, 0.272))
u(MAP, 'p9_room_metric_v13/rubble_u0', (0.363, 0.363, 0.35))
u(MAP, 'p9_room_metric_v13/rubble_u1', (0.425, 0.431, 0.413))
u(MAP, 'p9_room_metric_v13/rubble_u2', (0.466, 0.466, 0.455))
u(MAP, 'p9_room_metric_v13/slab_concrete', (0.285, 0.292, 0.287))
u(MAP, 'p9_room_metric_v13/room_frosted_engraving', (0.62, 0.63, 0.63), alpha=0.45, nocull=True)
u(MAP, 'p9_room_metric_v13/room_side_clear', (0.47, 0.47, 0.47), alpha=0.08)
# iris and ascent shaft
u(MAP, 'p9_stock_shaft_006b_v3', (0.50, 0.49, 0.50), base='metal/metalwall_bts_006b')
u(MAP, 'p9_ascent_wall_v1', (0.0415, 0.0415, 0.0415))
u(MAP, 'p9_ascent_rail_v2', (0.0717, 0.0717, 0.0717))
u(MAP, 'shaft_far_u', (0.153, 0.156, 0.146))
u(MAP, 'shaft_side_u', (0.025, 0.025, 0.025))
u(MAP, 'shaft_near_u', (0.09, 0.09, 0.09))
u(MAP, 'shaft_lip_u', (0.30, 0.30, 0.30))
u(MAP, 'void_black', (0.0, 0.0, 0.0))
u(MAP, 'iris_dark_u', (0.12, 0.125, 0.13))
u(MAP, 'service_orange_u', (0.62, 0.30, 0.12))
u(MAP, 'box_ceiling', (0.60, 0.60, 0.59))
u(MAP, 'ruin_dark_u', (0.08, 0.08, 0.085))
# shared wall colours of the middle rooms
u(MAP, 'black_u', (0.0815, 0.0848, 0.0914))
u(MAP, 'white_u', (0.385, 0.396, 0.388))
u(MAP, 'grey_u', (0.135, 0.146, 0.146))
u(MAP, 'steel_u', (0.68, 0.70, 0.72), base='metal/metalwall_bts_006b')
u(MAP, 'steel_ud', (0.36, 0.37, 0.38), base='metal/metalwall_bts_006b')
u(MAP, 'clear_glass', (0.41, 0.43, 0.435), alpha=0.15)
u(MAP, 'lamp', (0.284, 0.256, 0.187))
u(MAP, 'sign_ink', (0.05, 0.05, 0.05))
u(MAP, 'drum_s', (0.503, 0.509, 0.504))
u(MAP, 'drum_u', (0.59, 0.596, 0.565))
u(MAP, 'bridge_light', (0.45, 0.85, 0.95))
u(MAP, 'hall_u', (0.95, 0.80, 0.70), base='metal/metalwall_bts_006a')
# lab
u(MAP, 'labblue_u', (0.475, 0.637, 0.684))
u(MAP, 'wfloor_u', (0.548, 0.567, 0.529))
u(MAP, 'field_u', (0.20, 0.35, 0.60), alpha=0.5, nocull=True)
u(MAP, 'incinerator_panel', (0.20, 0.20, 0.21))
# factory passage
u(MAP, 'p9_factory_v4_dark', (0.0815, 0.0629, 0.0523))
u(MAP, 'p9_factory_v4_floor', (0.66, 0.59, 0.49), base='metal/black_wall_metal_002a', extra={'$model': '1'})
u(MAP, 'p9_factory_v4_grey', (0.17, 0.153, 0.129))
u(MAP, 'p9_factory_v4_orange', (0.441, 0.314, 0.167))
u(MAP, 'p9_factory_v4_wall', (0.285, 0.227, 0.181))
u(MAP, 'p9_factory_v4_white', (0.60, 0.58, 0.54))
u(MAP, 'p9_factory_v7_plate', (0.48, 0.48, 0.46), extra={'$surfaceprop': 'metal'})
# incinerator
u(MAP, 'p9_end_exit_oxide', (0.62, 0.27, 0.13))
u(MAP, 'incin_outlet_void', (0.0, 0.0, 0.0))
# capsule and vault (ending)
u(MAP, 'ending_gold_u', (0.321, 0.227, 0.112))
u(MAP, 'ending_floor_u', (0.487, 0.498, 0.502))
u(MAP, 'ending_white_u', (0.6335, 0.6413, 0.6296))
u(MAP, 'ending_recess_u', (0.108, 0.057, 0.041))
u(MAP, 'ending_recess_top_u', (0.318, 0.227, 0.108))
u(MAP, 'ending_collar_u', (0.202, 0.205, 0.209))
u(MAP, 'ending_flange_u', (0.263, 0.281, 0.296))
u(MAP, 'ending_flangehi_u', (0.42, 0.44, 0.46))
u(MAP, 'ending_flangetop_u', (0.33, 0.35, 0.37))
u(MAP, 'ending_redwall_u', (0.475, 0.234, 0.163))
u(MAP, 'ending_petalb_u', (0.475, 0.303, 0.163))
u(MAP, 'ending_ring_u', (0.25, 0.19, 0.13))
u(MAP, 'ending_ringb_u', (0.362, 0.27, 0.184))
u(MAP, 'ending_ringhi_u', (0.637, 0.583, 0.548))
u(MAP, 'ending_hub_u', (0.23, 0.132, 0.085))
u(MAP, 'ending_hubring_u', (0.34, 0.321, 0.248))
u(MAP, 'ending_strut_u', (0.181, 0.112, 0.075))
u(MAP, 'ending_mouth_u', (0.212, 0.209, 0.22))
u(MAP, 'ending_green_u', (0.239, 0.325, 0.205))
u(MAP, 'ending_border_u', (0.479, 0.403, 0.292))
u(MAP, 'ending_bulb_u', (0.663, 0.564, 0.426))
u(MAP, 'ending_lampring_u', (0.072, 0.052, 0.035))
u(MAP, 'ending_black_u', (0.061, 0.0415, 0.047))
u(MAP, 'ending_concrete_u', (0.42, 0.43, 0.43))
u(MAP, 'ending_tubeglass_u', (0.41, 0.43, 0.435), alpha=0.15, nocull=True)
u(MAP, 'ending_podshade_u', (0.0, 0.0, 0.0), alpha=0.35, nocull=True)
u(MAP, 'ending_flash_u', (1.0, 1.0, 1.0), alpha=0.0, nocull=True)
u(MAP, 'ending_redmod', (0.9, 0.25, 0.2), alpha=0.25, nocull=True)
u(MAP, 'ending_shattermod', (0.8, 0.82, 0.85), alpha=0.3, nocull=True)

# ----------------------------------------------------------------------------------------------- model materials
M = dict(model=True)
F4 = (0.265, 0.43, 0.68, 1.0)            # the four baked shade levels of the lathed rings
# transport tube rings: flange (0-3), chamfer (h0-h3), inner lip; one family per skin
def tube(tag, s3, h3, lip):
    ramp(MODEL, f'tube_{tag}', s3, F4, **M); ramp(MODEL, f'tube_{tag}h', h3, F4, **M); u(MODEL, f'tube_{tag}lip', lip, **M)
tube('d', (0.11, 0.115, 0.115), (0.15, 0.155, 0.155), (0.174, 0.181, 0.177))      # dark skin
tube('m', (0.20, 0.21, 0.21), (0.26, 0.27, 0.27), (0.208, 0.217, 0.216))          # mid skin
tube('b', (0.32, 0.344, 0.343), (0.42, 0.45, 0.45), (0.174, 0.181, 0.177))        # pale teal skin (v50 look)
tube('w', (0.54, 0.54, 0.54), (0.74, 0.745, 0.74), (0.177, 0.177, 0.174))         # light grey (scanner shaft, collars)
tube('o', (0.44, 0.30, 0.17), (0.50, 0.34, 0.22), (0.245, 0.248, 0.248))          # copper
tube('k', (0.62, 0.47, 0.40), (0.60, 0.45, 0.38), (0.216, 0.205, 0.198))          # pale copper / pink (gallery)
tube('p', (0.70, 0.72, 0.72), (0.82, 0.84, 0.84), (0.50, 0.51, 0.51))             # pale crossing tube
u(MODEL, 'tube_glass', (0.41, 0.43, 0.435), alpha=0.15, nocull=True, **M)
u(MODEL, 'tube_pglass', (0.80, 0.82, 0.83), alpha=0.35, nocull=True, **M)
u(MODEL, 'tube_glass_none', (0.0, 0.0, 0.0), alpha=0.0, nocull=True, **M)
u(MODEL, 'glass', (0.41, 0.43, 0.435), alpha=0.15, nocull=True, **M)
u(MODEL, 'tube_rail2', (0.05, 0.047, 0.047), **M)
ramp(MODEL, 'early_tube', (0.36, 0.37, 0.37), F4, **M); ramp(MODEL, 'early_tubeh', (0.48, 0.49, 0.49), F4, **M)
u(MODEL, 'early_tube_lip', (0.20, 0.205, 0.205), **M)
ramp(MODEL, 'p9_entry_c', (0.40, 0.40, 0.39), F4, **M); ramp(MODEL, 'p9_entry_ch', (0.50, 0.50, 0.49), F4, **M)
u(MODEL, 'p9_entry_clip', (0.28, 0.28, 0.28), **M)
# pod shelves (values from patch_r10.py r10bx)
for k, c in ((2, 0.0793), (3, 0.1249), (4, 0.1819), (5, 0.2508), (6, 0.3320), (7, 0.4256)):
    c2 = round(c * 1.5, 4); u(MODEL, f'podwall_s{k}', (c2, c2, round(c2 * 1.02, 4)), **M)
u(MODEL, 'podwall_back', (0.10, 0.105, 0.11), **M)
# tower collars
for k, c in enumerate(((0.03, 0.03, 0.03), (0.04, 0.04, 0.04), (0.055, 0.055, 0.055), (0.075, 0.075, 0.075))): u(MODEL, f'tower_s{k}', c, **M)
for k, c in enumerate(((0.035, 0.035, 0.035), (0.05, 0.05, 0.05), (0.07, 0.07, 0.07), (0.09, 0.09, 0.09))): u(MODEL, f'tower_h{k}', c, **M)
u(MODEL, 'tower_lip', (0.05, 0.05, 0.05), **M)
for k, c in enumerate(((0.108, 0.108, 0.108), (0.125, 0.129, 0.125), (0.153, 0.153, 0.149), (0.184, 0.188, 0.184))): u(MODEL, f'towerg_s{k}', c, **M)
for k, c in enumerate(((0.108, 0.112, 0.108), (0.142, 0.146, 0.144), (0.22, 0.22, 0.212), (0.256, 0.274, 0.263))): u(MODEL, f'towerg_h{k}', c, **M)
u(MODEL, 'towerg_lip', (0.125, 0.125, 0.122), **M)
# scanners
u(MODEL, 'transfer_black', (0.06, 0.06, 0.06), **M); u(MODEL, 'transfer_grey', (0.36, 0.36, 0.36), **M)
u(MODEL, 'transfer_white', (0.78, 0.78, 0.77), **M); u(MODEL, 'transfer_lens', (0.10, 0.08, 0.06), **M)
u(MODEL, 'transfer_yellow', (0.95, 0.85, 0.35), alpha=0.35, nocull=True, **M)
u(MODEL, 'dark', (0.10, 0.10, 0.10), **M); u(MODEL, 'metal', (0.30, 0.30, 0.30), **M); u(MODEL, 'red', (0.75, 0.15, 0.12), **M)
u(MODEL, 'shell', (0.72, 0.72, 0.71), **M)
u(MODEL, 'board_white', (0.749, 0.74, 0.742), **M); u(MODEL, 'board_grey', (0.494, 0.49, 0.49), **M)
u(MODEL, 'disc_white', (0.80, 0.80, 0.79), **M); u(MODEL, 'disc_dark', (0.10, 0.10, 0.10), **M)
for k, c in enumerate((0.07, 0.20, 0.03, 0.04, 0.22, 0.31, 0.58, 0.81)): u(MODEL, f'drop_s{k}', (c, c, c * 1.01), **M)
# r10 models
u(MODEL, 'r10_ball', (1.0, 0.92, 0.35), extra={'$nofog': '1'}, **M)
u(MODEL, 'r10_broken', (0.10, 0.09, 0.085), nocull=True, **M)
u(MODEL, 'r10_debris', (0.05, 0.05, 0.05), **M); u(MODEL, 'r10_debris_pale', (0.60, 0.56, 0.50), **M)
u(MODEL, 'r10_column', (0.068, 0.072, 0.078), **M); u(MODEL, 'r10_flange', (0.035, 0.035, 0.035), **M)
u(MODEL, 'r10_hole_black', (0.0, 0.0, 0.0), **M); u(MODEL, 'r10_hole_box', (0.86, 0.80, 0.72), **M)
u(MODEL, 'r10_lid_dark', (0.09, 0.09, 0.095), **M)
u(MODEL, 'r10_lid_rust', (0.86, 0.84, 0.82), base='metal/metalwall_bts_001b', **M)
u(MODEL, 'r10_post_dark', (0.16, 0.16, 0.174), **M); u(MODEL, 'r10_post_grey', (0.396, 0.411, 0.422), **M)
u(MODEL, 'r10_rod', (0.55, 0.30, 0.17), **M); u(MODEL, 'r10_rod_dark', (0.10, 0.08, 0.07), **M)
u(MODEL, 'r10_tu_skirt', (0.60, 0.61, 0.60), **M)
u(MODEL, 'r10_tu_tube', (0.16, 0.16, 0.165), **M)
u(MODEL, 'r10_tube_end', (0.88, 0.89, 0.88), base='concrete/concrete_modular_wall001a', nocull=True, **M)
# factory arm
u(MODEL, 'robot_dark', (0.06, 0.055, 0.05), **M); u(MODEL, 'robot_grey', (0.22, 0.21, 0.20), **M)
ramp(MODEL, 'robot_o', (0.70, 0.42, 0.14), F4, **M)
# old frame/bend collars
u(MODEL, 'collar_bevel', (0.30, 0.30, 0.30), **M); u(MODEL, 'collar_dark', (0.08, 0.08, 0.08), **M)
u(MODEL, 'collar_gray', (0.40, 0.40, 0.40), **M); u(MODEL, 'collar_orange', (0.50, 0.32, 0.18), **M)


def vmt(d):
    lines = ['"UnlitGeneric"', '{', f'"$basetexture" "{d["base"]}"', '"$color" "[%s]"' % ' '.join('%g' % c for c in d['color'])]
    if d['alpha'] is not None:
        lines += ['"$translucent" "1"', '"$alpha" "%g"' % d['alpha']]
    if d['nocull']: lines.append('"$nocull" "1"')
    for k, v in d['extra'].items():
        if k == '__raw__': lines.append(v)
        else: lines.append(f'"{k}" "{v}"')
    lines.append('}')
    return '\n'.join(lines) + '\n'


def write_all(out):
    n = 0
    for table, sub in ((MAP, 'materials/corehub_intro'), (MODEL, 'materials/models/corehub_intro')):
        for name, d in table.items():
            p = os.path.join(out, sub, name + '.vmt'); os.makedirs(os.path.dirname(p), exist_ok=True)
            open(p, 'w').write(vmt(d)); n += 1
    return n


if __name__ == '__main__':
    out = sys.argv[1] if len(sys.argv) > 1 else '.'
    print('wrote', write_all(out), 'materials to', out)
