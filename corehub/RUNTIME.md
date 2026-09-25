# Corehub 3916 VR runtime

This branch contains a separate, experimental runtime for the native 2009
Corehub build. It verifies client, server, engine, material-system and shader-API
DLL hashes before enabling hooks. Other builds are rejected. Portal 1 retains
its existing runtime path.

Build with the repository's `build.ps1`, close Corehub, then run:

```powershell
.\corehub\Install-Runtime.ps1 -GameRoot "C:\path\to\Portal 2 2009 Corehub Overwatch Build"
```

The installer backs up replaced runtime files and checks their installed SHA256
hashes. Launch `hl2.wrap.exe` with `-corehubvr -tempcontent -insecure
+mat_queue_mode 0`. Use `-game bowman_singleplayer` for the original-colour Bowman
profile, or `-game bowman_coop` for the co-op model profile. Install the separate
Bowman asset package before using either profile.

Corehub now requires `-corehubvr` explicitly. A desktop launch skips VR so a
copied runtime used by Hammer cannot claim SteamVR's scene application. Already
running copies with an older DLL still need to be closed before a VR test.
The installer updates both Bowman launchers to include the flag and backs up
their previous versions.

## Hands and menu update, 2026-09-24

Bare hands use native v49 assets, server precaching and a separate left
viewmodel. Corehub suppresses weaponless viewmodels in its normal draw path;
the runtime renders them and the portal gun explicitly in the world pass with
controller-aligned bone palettes and the Portal 1 finger/grip code. Additional
hand and body draws use the invalid instance handle `0xffff`; `0` is an actual
renderer instance that these independent draws do not own.

The desktop menu is captured before any diagnostic mirror, uploaded to a
separate D3D11 texture and shown as an HMD-relative panel. Game-UI visibility
comes from `VEngineVGui001`, rather than cursor visibility. This lets the panel
hide and gameplay input resume when entering a map. Menu pointer events use
Corehub's native VGUI input queue. The overlay laser is enabled only while a
controller intersects the panel, allowing action buttons to work otherwise.

The inherited Pico/Touch bindings assign A to Jump, MenuSelect and ActivateVR.
Corehub no longer consumes ActivateVR: choosing a menu item or jumping must
not disable stereo rendering. Pause remains on the inherited left Y binding.

Local verification includes visible bare hands in both eye renders, native
menu pointer selection, D3D11 overlay acceptance and regression suites. Actual
Pico hand tracking and menu placement await the user's next headset test.
Back/Escape did not close the stock Options dialog in the local test; use its
Cancel button. Do not report that interaction as fixed.
The opening bed scene can place opaque scene geometry across the forced HMD
view before the scripted camera transition; that cutscene case is unresolved.

## Stereo rendering fix, 2026-09-24

Corehub's shader API overwrites primary render-target bookkeeping when unused
MRT slots 1–3 are unbound. The eye color and depth buffers were both 2352 square,
but the renderer treated them as the desktop and clamped its pending viewport to
1280×720. Shadow passes could temporarily restore the state, producing changing
coverage between frames. Setting the D3D9 viewport directly did not fix the
cached state applied at the next draw.

During VR rendering, secondary target changes now preserve RT0's texture flag
and size. Internal 2D views also use eye dimensions. Completed eyes are copied
to separate submission surfaces before the next native render pass.

Both full-sized eye captures and SteamVR compositor captures were verified.
The Pico user confirmed both eyes stable, with the flashing and black regions
gone. The final build was checked again after temporary tracing was removed: 1,800
stereo frames, successful submits for both eyes, and full-sized source and
compositor captures. See `validation/runtime-stereo-20260924.json`.

## Current limits and diagnostics

- The conservative D3D11 submission path uses CPU readback and upload; it may
  limit frame rate. `-corehubvr-vulkan` remains an experimental alternative and
  has not been confirmed in-headset with this fix.
- `-corehubvr-mirror` displays submitted eyes side by side on the desktop.
- `-corehubvr-debug-textures` saves eye BMPs at frame 60 and every 600 frames;
  leave it off during normal play because captures can briefly stall rendering.
- HMD stereo view, controller-oriented command input, tracked hand/gun bone
  palettes, HMD-driven head animation and an additive first-person body are
  implemented. The body follows horizontal camera motion, moves back eight
  units and hides its head/arms in the first-person copy. It needs headset QA.
- Controller-origin server pickup, contact retry, grip-height correction,
  server-side portal rebasing and camera collision are still pending. Shared
  Portal 1 regression tests passing does not prove these are ported to Corehub.
- Full co-op gameplay, save/load and portal traversal cases still need
  validation. This is not a completed compatibility port.
- Developer fixtures: `-corehubvr-test-hands` uses fixed poses instead of live
  tracking. With it, `-corehubvr-test-gun` gives a portal gun after 120 frames
  and opens the pause menu after 650. `-corehubvr-test-menu` clicks Options and
  sends Escape at the main menu. Leave all test flags off for normal play.
