import struct
import sys
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
from ragdoll_bones import bone_repairs, repair, validate_avatar_zip


def fixture():
    mdl = bytearray(408 + 216 * 3 + 24)
    mdl[:4] = b'IDST'
    struct.pack_into('<2I', mdl, 4, 48, 123)
    struct.pack_into('<I', mdl, 76, len(mdl))
    struct.pack_into('<2I', mdl, 156, 3, 408)
    for i, (name, parent, flags) in enumerate([(b'root', -1, 0), (b'spring', 0, 4), (b'unused', 0, 0)]):
        entry, name_position = 408 + 216 * i, 408 + 216 * 3 + i * 8
        struct.pack_into('<2i', mdl, entry, name_position - entry, parent)
        struct.pack_into('<I', mdl, entry + 160, flags)
        mdl[name_position:name_position + len(name)] = name
    phy = struct.pack('<5I', 16, 0, 1, 123, 4) + b'TESTsolid {\n"name" "spring"\n}\0'
    return bytes(mdl), phy


class RagdollBones(unittest.TestCase):
    def test_repairs_collision_ancestors_preserves_other_bytes(self):
        mdl, phy = fixture()
        fixed, report = repair(mdl, phy)
        self.assertEqual([c['bone'] for c in report['changes']], ['root', 'spring'])
        allowed = {c['offset'] + 2 for c in report['changes']}
        self.assertEqual({i for i, (a, b) in enumerate(zip(mdl, fixed)) if a != b}, allowed)
        self.assertEqual(repair(fixed, phy)[0], fixed)
        self.assertEqual(bone_repairs(fixed, phy)['changes'], [])

    def test_rejects_mismatched_physics(self):
        mdl, phy = fixture()
        bad = bytearray(phy)
        struct.pack_into('<I', bad, 12, 456)
        with self.assertRaisesRegex(ValueError, 'checksum'):
            repair(mdl, bad)

    def test_rejects_missing_bone_and_cycle(self):
        mdl, phy = fixture()
        with self.assertRaisesRegex(ValueError, 'missing bone'):
            repair(mdl, phy.replace(b'spring', b'absent'))
        bad = bytearray(mdl)
        struct.pack_into('<i', bad, 412, 1)
        with self.assertRaisesRegex(ValueError, 'Cyclic'):
            repair(bad, phy)

    def test_shipped_avatar(self):
        report = validate_avatar_zip(Path(__file__).resolve().parents[1] / 'L4D2VR/custom/bowman_portal1.zip')
        self.assertEqual(report['solids'], 23)
        self.assertEqual(report['changes'], [])


if __name__ == '__main__':
    unittest.main()
