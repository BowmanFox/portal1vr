"""Check/repair Source MDL v48 bone usage required by the matching PHY.

Portal initializes death ragdolls from a BONE_USED_BY_ANYTHING bone array.
Collision-only bones with zero usage flags otherwise receive stack garbage.
Use the compiler's $bonemerge flag for those bones and their unused ancestors;
do not modify geometry, bind poses, animations, hulls, or the model checksum.
"""
import argparse
import json
from pathlib import Path
import re
import struct
import zipfile
import zlib

BONE_USED_BY_ANYTHING = 0x0007FF00
BONE_USED_BY_BONE_MERGE = 0x00040000


def bone_repairs(mdl, phy):
    if len(mdl) < 408 or mdl[:4] != b'IDST':
        raise ValueError('Not a Source studio model')
    version, checksum = struct.unpack_from('<2I', mdl, 4)
    if version != 48 or struct.unpack_from('<I', mdl, 76)[0] != len(mdl):
        raise ValueError('Unsupported or truncated MDL')
    if len(phy) < 16:
        raise ValueError('Truncated PHY')
    header, _, solids, phy_checksum = struct.unpack_from('<4I', phy)
    if header != 16 or phy_checksum != checksum or not 0 < solids <= 128:
        raise ValueError('PHY header/checksum does not match MDL')
    cursor = header
    for _ in range(solids):
        if cursor + 4 > len(phy):
            raise ValueError('Truncated PHY solid')
        size = struct.unpack_from('<I', phy, cursor)[0]
        cursor += 4 + size
        if size == 0 or cursor > len(phy):
            raise ValueError('Invalid PHY solid size')
    text = phy[cursor:].rstrip(b'\0').decode('ascii')
    blocks = re.findall(r'(?m)^solid\s*\{([^{}]*)\}', text)
    if len(blocks) != solids:
        raise ValueError('PHY solid metadata count mismatch')
    collision_names = []
    for block in blocks:
        names = re.findall(r'"name"\s+"([^"]+)"', block)
        if len(names) != 1:
            raise ValueError('Missing or ambiguous collision bone')
        collision_names.append(names[0])
    count, offset = struct.unpack_from('<2I', mdl, 156)
    if not 0 < count <= 128 or offset < 408 or offset + count * 216 > len(mdl):
        raise ValueError('Invalid MDL bone table')
    bones = []
    for index in range(count):
        entry = offset + index * 216
        name_offset, parent = struct.unpack_from('<2i', mdl, entry)
        start = entry + name_offset
        if not 0 <= start < len(mdl) or not -1 <= parent < count:
            raise ValueError('Invalid bone name/parent')
        name = mdl[start:mdl.index(0, start)].decode('ascii')
        bones.append((name, parent, entry + 160))
    by_name = {name.lower(): i for i, (name, _, _) in enumerate(bones)}
    if len(by_name) != count:
        raise ValueError('Duplicate bone names')
    required = set()
    for name in collision_names:
        if name.lower() not in by_name:
            raise ValueError('PHY references missing bone: ' + name)
        index = by_name[name.lower()]
        chain = set()
        while index != -1:
            if index in chain:
                raise ValueError('Cyclic bone parents')
            chain.add(index)
            required.add(index)
            index = bones[index][1]
    changes = []
    for index in sorted(required):
        name, _, position = bones[index]
        flags = struct.unpack_from('<I', mdl, position)[0]
        if not flags & BONE_USED_BY_ANYTHING:
            changes.append(dict(bone=name, index=index, offset=position,
                                before=flags, after=flags | BONE_USED_BY_BONE_MERGE))
    return dict(solids=solids, bones=count, required_bones=len(required), changes=changes)


def repair(mdl, phy):
    report = bone_repairs(mdl, phy)
    result = bytearray(mdl)
    for change in report['changes']:
        struct.pack_into('<I', result, change['offset'], change['after'])
    assert not bone_repairs(result, phy)['changes']
    return bytes(result), report


def vpk_model_files(data):
    """Read the two model entries from a self-contained VPK, checking their CRCs."""
    signature, version, tree_size = struct.unpack_from('<3I', data)
    if signature != 0x55AA1234 or version not in (1, 2):
        raise ValueError('Invalid VPK')
    position = header = 12 if version == 1 else 28
    tree_end = header + tree_size
    if tree_end > len(data):
        raise ValueError('Truncated VPK tree')

    def string():
        nonlocal position
        end = data.index(0, position, tree_end)
        result = data[position:end].decode('ascii')
        position = end + 1
        return result

    found = {}
    while extension := string():
        while directory := string():
            while name := string():
                crc, preload, archive, offset, size, end = struct.unpack_from('<IHHIIH', data, position)
                position += 18
                if end != 0xFFFF or position + preload > tree_end:
                    raise ValueError('Invalid VPK entry')
                prefix = data[position:position + preload]
                position += preload
                path = ('' if directory == ' ' else directory + '/') + name + '.' + extension
                if path not in ('models/player/chell.mdl', 'models/player/chell.phy'):
                    continue
                if archive != 0x7FFF or tree_end + offset + size > len(data) or path in found:
                    raise ValueError('Unsupported model VPK entry')
                payload = prefix + data[tree_end + offset:tree_end + offset + size]
                if zlib.crc32(payload) != crc:
                    raise ValueError('Model CRC mismatch')
                found[path] = payload
    if len(found) != 2:
        raise ValueError('VPK must contain Chell MDL and PHY')
    return found['models/player/chell.mdl'], found['models/player/chell.phy']


def validate_avatar_zip(path):
    with zipfile.ZipFile(path) as archive:
        if archive.namelist() != ['bowman_portal1.vpk'] or archive.testzip() is not None:
            raise ValueError('Invalid avatar archive')
        report = bone_repairs(*vpk_model_files(archive.read('bowman_portal1.vpk')))
    if report['changes']:
        raise ValueError('Unevaluated ragdoll bones: ' + ', '.join(c['bone'] for c in report['changes']))
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('model', type=Path)
    parser.add_argument('--repair', action='store_true', help='Back up the MDL and repair only missing usage flags')
    args = parser.parse_args()
    original = args.model.read_bytes()
    fixed, report = repair(original, args.model.with_suffix('.phy').read_bytes())
    if args.repair and fixed != original:
        backup = args.model.with_suffix('.mdl.before-ragdoll-fix')
        with backup.open('xb') as file:
            file.write(original)
        args.model.write_bytes(fixed)
    print(json.dumps(report, indent=2))
    if report['changes'] and not args.repair:
        raise SystemExit(1)
