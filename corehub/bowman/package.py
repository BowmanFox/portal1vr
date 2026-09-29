"""Package an existing native Corehub model build and its custom materials."""
import argparse
import hashlib
import json
import re
import struct
import zipfile
from pathlib import Path

HERE = Path(__file__).resolve().parent


def digest(data):
    return hashlib.sha256(data).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--compiled-models', type=Path, required=True)
    parser.add_argument('--materials', type=Path, required=True,
                        help='Directory containing the custom VMT and VTF files')
    parser.add_argument('--skin-audit', type=Path, required=True)
    args = parser.parse_args()
    files = {}
    checksums = set()
    for suffix, offset in [('mdl', 8), ('vvd', 8), ('dx80.vtx', 16),
                           ('dx90.vtx', 16), ('sw.vtx', 16), ('phy', 12)]:
        data = (args.compiled_models / f'player.{suffix}').read_bytes()
        checksums.add(struct.unpack_from('<I', data, offset)[0])
        if suffix == 'mdl':
            assert data[:4] == b'IDST' and struct.unpack_from('<I', data, 4)[0] == 49
        files[f'bowman_coop/models/player.{suffix}'] = data
    assert len(checksums) == 1, 'Model component checksums differ'

    audit = json.loads(args.skin_audit.read_text(encoding='utf-8-sig'))
    names = sorted({name for family in audit['families'] for name in family})
    textures = set()
    for name in names:
        assert re.fullmatch(r'[a-zA-Z0-9_]+', name), name
        data = (args.materials / f'{name}.vmt').read_bytes()
        files[f'bowman_coop/materials/models/bowman_corehub/{name}.vmt'] = data
        for texture in re.findall(r'"\$(?:basetexture|iris|bumpmap|detail|envmapmask)"\s+"([^"]+)"',
                                  data.decode('utf-8-sig'), flags=re.I):
            assert re.fullmatch(r'models/bowman_corehub/[a-zA-Z0-9_]+', texture), texture
            textures.add(texture.rsplit('/', 1)[1])
    for name in sorted(textures):
        files[f'bowman_coop/materials/models/bowman_corehub/{name}.vtf'] = (args.materials / f'{name}.vtf').read_bytes()

    # Single-player uses Portal 1 Bowman's original coat and iris, with the same
    # repaired geometry, native skeleton, QC eyeballs, and collision model.
    for name, data in list(files.items()):
        if name.endswith('.vtf') and '_markings' in name:
            continue
        if name.endswith('.vmt'):
            text = data.decode('utf-8-sig')
            for variant in ('blue', 'orange'):
                text = text.replace(f'fur_{variant}_markings', 'fur')
                text = text.replace(f'iris_{variant}_markings', 'eyes')
            data = text.encode('utf-8')
        files[name.replace('bowman_coop/', 'bowman_singleplayer/', 1)] = data
    files['bowman_singleplayer/materials/models/bowman_corehub/eyes.vtf'] = (args.materials / 'eyes.vtf').read_bytes()
    files['bowman_singleplayer/materials/models/bowman_corehub/fur.vmt'] = (args.materials / 'fur.vmt').read_bytes()
    weapon_checksums=set()
    for suffix,offset in [('mdl',8),('vvd',8),('dx80.vtx',16),('dx90.vtx',16),('sw.vtx',16)]:
        data=(args.compiled_models/'weapons'/f'v_portalgun.{suffix}').read_bytes()
        weapon_checksums.add(struct.unpack_from('<I',data,offset)[0])
        if suffix=='mdl':
            assert data[:4]==b'IDST' and struct.unpack_from('<I',data,4)[0]==49
        files[f'bowman_singleplayer/models/weapons/v_portalgun.{suffix}']=data
    assert len(weapon_checksums)==1,'Portal-gun model component checksums differ'

    gameinfo = '''"GameInfo"
{
 game "Bowman Corehub Co-op"
 title "BOWMAN CO-OP"
 GameData "portal2.fgd"
 FileSystem
 {
  SteamAppId 380
  ToolsAppId 211
  SearchPaths
  {
   Game |gameinfo_path|.
   Game portal2_tempcontent
   Game portal2
   Game portal
   Game hl2
   PLATFORM platform
  }
 }
}
'''
    launcher = '''@echo off
cd /d "%~dp0"
start "" "%~dp0hl2.wrap.exe" -game bowman_coop -tempcontent -insecure -windowed -w 1280 -h 720 -novid -condebug +mat_queue_mode 0 +maxplayers 2 +map mp_coop_start
'''
    files['bowman_coop/gameinfo.txt'] = gameinfo.replace('\n', '\r\n').encode()
    files['Launch Bowman Co-op.cmd'] = launcher.replace('\n', '\r\n').encode()
    files['bowman_singleplayer/gameinfo.txt'] = gameinfo.replace('Bowman Corehub Co-op', 'Bowman Corehub Single-player').replace('BOWMAN CO-OP', 'BOWMAN').replace('\n', '\r\n').encode()
    single_launcher = launcher.replace('bowman_coop', 'bowman_singleplayer').replace('+maxplayers 2 +map mp_coop_start', '+maxplayers 1')
    files['Launch Bowman Single-player.cmd'] = single_launcher.replace('\n', '\r\n').encode()
    files['bowman_coop/README.txt'] = (
        'Bowman character assets for the native 2009 Corehub prototype.\r\n'
        'This package does not include a VR runtime: Corehub VR support is unfinished.\r\n'
        'Launch Bowman Co-op.cmd starts the separate model profile on mp_coop_start.\r\n'
        'All maps opened in this profile use these models. The normal launch stays separate.\r\n'
        'The original player_animations.mdl is loaded from your existing installation.\r\n'
        'Blender facial shape keys are preserved in the source but not exported as Source flexes.\r\n'
    ).encode()
    files['bowman_singleplayer/README.txt'] = (
        'Portal 1 Bowman appearance with the updated mesh, adapted for native Corehub.\r\n'
        'Launch Bowman Single-player.cmd, then choose New Game or load a save.\r\n'
        'This character package does not include VR support or Source facial flexes.\r\n'
        'Co-op colors are available in the separate co-op launch profile.\r\n'
    ).encode()
    package = HERE / 'Bowman_Corehub_Models.zip'
    with zipfile.ZipFile(package, 'w', compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for name, data in sorted(files.items()):
            info = zipfile.ZipInfo(name, date_time=(2026, 9, 24, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o100644 << 16
            archive.writestr(info, data)
    manifest = {
        'kind': 'corehub-native-character-assets', 'vr_runtime_included': False,
        'model_checksum': checksums.pop(), 'singleplayer_weapon_checksum':weapon_checksums.pop(),
        'package_sha256': digest(package.read_bytes()),
        'files': [{'path': name, 'sha256': digest(data), 'bytes': len(data)}
                  for name, data in sorted(files.items())],
    }
    (HERE / 'package-manifest.json').write_text(json.dumps(manifest, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({'package': str(package), 'files': len(files),
                      'bytes': package.stat().st_size, 'sha256': manifest['package_sha256']}))


if __name__ == '__main__':
    main()
