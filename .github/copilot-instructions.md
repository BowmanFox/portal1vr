# Copilot / AI Developer Instructions — Portal VR (Portal 1)

Purpose
- Short: A Portal VR shim that hooks engine/game functions to render VR eyes, propagate controller state, and adapt HUD/input.
- Primary entry points: the injected DLL in `L4D2VR/dllmain.cpp` and the hook layer in `L4D2VR/hooks.cpp`.

Quick start (build & debug)
- Open the Visual Studio solution: `l4d2vr.sln`.
- Target: set Configuration=`Release` or `Debug`, Platform=`x64`. Build the solution.
- A project-level preprocessor macro `PORTAL_1` is added to all configurations when building for Portal 1.
- Result: the DLL is produced under the project `Release`/`Debug` output. The project has PostBuild copy steps that place the DLL into `H:\SteamLibrary\steamapps\common\Portal\bin` (edit path to match your library).
- Runtime: inject/copy the DLL into Portal (`portal.exe`) or run via your injector. To debug, build `Debug` and attach Visual Studio to the game process; set breakpoints in `Hooks::dCreateMove`, `Hooks::dRenderView`, or `Game::Init*`.

Key components & architecture
- Hooking layer: `L4D2VR/hooks.cpp`
  - Pattern: Hook objects named `hkXxx` and detours named `dXxx` (e.g., `hkWriteUsercmd` / `dWriteUsercmd`). Call originals with `.fOriginal(...)`.
- Core game glue: `L4D2VR/game.cpp` / `L4D2VR/game.h` — holds engine interfaces (material system, engine client, model info, etc.).
- VR runtime: `L4D2VR/vr.cpp` / `L4D2VR/vr.h` — `m_VR` is the central VR state: `m_VR->m_IsVREnabled`, `GetRightControllerAbsPos()`, `m_LeftEyeTexture`/`m_RightEyeTexture`.
- Offsets & scanning: `L4D2VR/offsets.h` and `sigscanner.h` — update offsets/signatures when engine version changes.
- SDK helpers: `L4D2VR/sdk/` contains engine data types used throughout (bitbuf, usercmd, vector, etc.).

Important integration / dependencies
- MinHook: `thirdparty/minhook` — runtime detours (initialized in `Hooks` constructor).
- OpenVR: `openvr` + Steam action manifest in `L4D2VR/SteamVRActionManifest/action_manifest.json`.
- Game specific: The code was adapted from Portal 2 originally; the project now builds with `PORTAL_1` defined to target Portal (1).

Project-specific patterns and conventions
- Hook naming: `hkXxx` = hook object; `dXxx` = detour function. Keep this consistent.
- Call originals: use `hkXxx.fOriginal(...)` to call the original engine function.
- Detour calling conventions: many functions use `__fastcall` capturing `ecx/edx`.
- Custom network extension: controller state is serialized into usercmds:
  - Writer: `dWriteUsercmd` writes a sentinel `WriteChar(-2)` then serializes `WriteBitVec3Coord(controllerPos)` and `WriteBitAngles(controllerAngles)`.
  - Reader: `dReadUsercmd` reads the sentinel via `ReadChar()` and then reads coordinates/angles when the sentinel is present. Keep the sentinel value consistent when changing serialization.
- Rendering order: `dRenderView` renders left/right eye into `m_LeftEyeTexture`/`m_RightEyeTexture`. HUD render-target override is in `dPushRenderTargetAndViewport` / `dPopRenderTargetAndViewport`. Be careful modifying alpha writes or render order.

Build & Debug tips
- Breakpoints: `Hooks::dRenderView`, `Hooks::dCreateMove`, `Hooks::dWriteUsercmd`, `Game::Init*`, `VR::CreateVRTextures`.
- Logging: `std::cout` debug prints are used; avoid heavy logging in hot paths.

When changing offsets or the signature scanner
- Update `L4D2VR/offsets.h` and `sigscanner.h` as needed and rebuild.

Files to inspect quickly
- Entry & startup: `L4D2VR/dllmain.cpp`
- Hooks & detours: `L4D2VR/hooks.cpp`
- VR logic: `L4D2VR/vr.cpp`
- Offsets/signatures: `L4D2VR/offsets.h`, `L4D2VR/sigscanner.h`
- Action manifest & bindings: `L4D2VR/SteamVRActionManifest/action_manifest.json`

Do not change
- The `hk`/`d` naming and `.fOriginal` pattern — many places assume this.
- The usercmd sentinel (`-2`) unless updating both writer and reader.

If unsure
- Grep for patterns in `L4D2VR/hooks.cpp` before adding hooks.
- For new serialized usercmd fields, ensure write/read order and sentinel are mirrored.
- Ask maintainers before adjusting render target or HUD alpha logic — it is timing-sensitive.

If anything here is unclear or you want me to make the file more concise/verbose or add more low-level examples (e.g., exact signature changes for Portal 1), tell me and I will iterate.