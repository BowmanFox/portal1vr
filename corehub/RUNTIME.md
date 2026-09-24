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
- HMD stereo view, controller-oriented command input and gun placement, and
  HMD-driven local head animation are implemented. Controller-origin server
  pickup and the full Portal 1 first-person-body behavior are not fully ported.
- D3D11 headset menu presentation, full co-op gameplay, save/load and all portal
  traversal cases still need validation. This is not a completed compatibility port.
