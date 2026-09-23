"""Package a built x86 runtime and the compiled Bowman avatar for installation."""
from pathlib import Path
import argparse,hashlib,json,zipfile

repo=Path(__file__).resolve().parent
parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--output',type=Path,required=True)
args=parser.parse_args();args.output.parent.mkdir(parents=True,exist_ok=True)
files={}
for name in ['Release/d3d9.dll','Launch Portal VR.cmd','L4D2VR/copy-to-portal.ps1',
             'L4D2VR/config.txt','L4D2VR/manifest.vrmanifest',
             'L4D2VR/portal1vr_capsule_main.png','L4D2VR/portal1vr_portrait_main.png',
             'L4D2VR/custom/bowman_portal1.zip','thirdparty/openvr/bin/win32/openvr_api.dll',
             'thirdparty/openvr/LICENSE','thirdparty/minhook/LICENSE.txt','dxvk/LICENSE']:
    files[name]=(repo/name).read_bytes()
for folder in ['L4D2VR/SteamVRActionManifest','L4D2VR/materials','L4D2VR/resource']:
    for path in (repo/folder).rglob('*'):
        if path.is_file():files[path.relative_to(repo).as_posix()]=path.read_bytes()
files['Install.ps1']=b'''param([string]$PortalDirectory)
$ErrorActionPreference = 'Stop'
if (Get-Process hl2 -ErrorAction SilentlyContinue) {
    throw 'Close Portal before installing this update.'
}
$options = @{ SourceDll = (Join-Path $PSScriptRoot 'Release/d3d9.dll') }
if ($PortalDirectory) { $options.PortalDirectory = $PortalDirectory }
& (Join-Path $PSScriptRoot 'L4D2VR/copy-to-portal.ps1') @options
'''
files['Install.cmd']=b'@echo off\r\npowershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0Install.ps1" %*\r\npause\r\n'
files['README.txt']=b'''Portal1VR - compiled Windows x86 release

Requires the Steam version of Portal and a working SteamVR headset setup.
No compiler or Blender installation is required.

1. Close Portal and extract this entire ZIP to a folder.
2. Run Install.cmd. The installer finds the Steam Portal installation.
   For a custom location, run PowerShell in this folder:
   .\\Install.ps1 -PortalDirectory "D:\\SteamLibrary\\steamapps\\common\\Portal"
3. Start SteamVR, then run Launch Portal VR.cmd from the Portal game folder.

The installer copies the x86 runtime, OpenVR DLL, controller bindings,
materials, and compiled Bowman body/arms/portal-gun models. Existing config
values and comments are retained; missing settings receive shipped defaults.
Back up an existing custom avatar or runtime before replacement.

The gun housing has inward thickness, two-sided rendering, and a relieved
rear opening for the wrist. The gun is uniformly scaled to 1.2 for the paw.
Left-hand support is optional; release grip to resume independent tracking.
The body retains 136 expression targets, QC eyes, and 12 jiggle bones.

Held objects now follow the corrected carry direction from the visible wrist.
Prop selection uses the barrel centerline separately from the wrist carry pose;
native reach, visibility and contact-pickup checks remain enabled.
Portal shots and the aim marker use the compiled barrel centerline and the
current controller pose. The user confirmed angled/ceiling aiming now lines up.
The gun render pass uses the current eye camera. The travelling PortalBlast
shot effect now starts and points along the actual muzzle; its native target,
timing and portal color are retained. Angled aiming passed the user headset test.
Wrist roll rotates props without triggering the native downward carry shift.

Choose "VR: use left-handed controls" or "VR: use right-handed controls" in
Portal's main/pause menu. The choice is saved. Left-handed mode mirrors gun,
buttons and sticks; manual recenter is on the movement-stick click (right stick
in left-handed mode), or use "VR: recenter headset" in the menu. Saved custom
SteamVR bindings may need the new left-handed action set configured.

AutoCalibration=true preserves position, height and heading after explicit
SteamVR tracking-origin changes, including slow accumulated changes. It uses
stable tracking samples and checks for a blocked player-body route with a clear
route at the visible headset before gently correcting horizontal alignment.
It pauses during unreliable tracking, crouching, aiming, carrying and portals.
AutoCalibration=false disables automatic recovery. Use manual recenter for
an incorrect initial setup.

This is a prerelease: compiled geometry, attachment, and regression checks
passed. Wrist-twist carry stability was confirmed in an earlier headset test.
Pickup accuracy, left-handed controller use and calibration need headset tests.

The included instrumental radio is derived from thecybercat's
The Device has Been Modified v2 - HD Remaster:
https://www.youtube.com/watch?v=wRj-29ceRvU
It uses Portal's radio effects with no dialogue-triggered mute.

Source and project credits: https://github.com/BowmanFox/portal1vr
Dependency licenses are included under thirdparty and dxvk.
'''
files['SHA256SUMS.txt']=''.join(f'{hashlib.sha256(v).hexdigest()}  {k}\n' for k,v in sorted(files.items())).encode()
with zipfile.ZipFile(args.output,'w',zipfile.ZIP_DEFLATED,6) as z:
    for name,data in sorted(files.items()):z.writestr(name,data)
with zipfile.ZipFile(args.output) as z:
    assert z.testzip() is None
    for name,data in files.items():assert z.read(name)==data
print(json.dumps({'path':str(args.output),'files':len(files),'bytes':args.output.stat().st_size,'sha256':hashlib.sha256(args.output.read_bytes()).hexdigest()}))
