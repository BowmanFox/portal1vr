# Working on one scene of the Corehub intro rebuild

You are rebuilding one scene of a 134 s video (Portal 2's 2009 "Corehub" intro, a pre-rendered ride through a
pneumatic tube system) as a Source-engine map. The video is the only target: at every moment of your scene the
rebuild's frame should show the same composition, shapes and tones as the video's frame. You work entirely in this
Linux container with an offline preview renderer; the real game runs elsewhere and is not your concern.

Read `README.md` in this folder first (layout, conventions, the method that worked for the iris/ascent).

## Where things are

| What | Where |
|---|---|
| Video frames, 640x400, frame n at t = n * 1001 / 30000 s | `/home/claude/data/frames/f%04d.jpg` |
| Base map and director (never edit) | `/home/claude/work/gen/base/` |
| Model generators (one file per group) | `/home/claude/work/gen/models/` |
| Scene patches (one file per scene) | `/home/claude/work/gen/scenes/` |
| Offline tools | `/home/claude/offline/` (run scripts from that folder) |
| Worked example | `models/iris.py`, `scenes/iris.py`, `/home/claude/offline/solve_iris.py`, `camsolve.py`, `ringtrack.py` |
| Placement of every model in the base map | `/home/claude/work/lost_models.txt` (LOST = no model exists yet) |
| Scratch output (images, notes) | a folder of your own under `/home/claude/offline/out/<your tag>/` |

## Build and look

    cd /home/claude/work/gen
    python3 make.py <TAG> --models <your groups> --scenes iris,<your scene>     # ~25 s; --no-sim when only models changed
    cd /home/claude/offline
    python3 cmp.py <TAG> --cw 384 --cols 2 --rows 4 --out out/<tag>/cmp  t,t,t,...     # video | preview pairs
    python3 overlay.py <TAG> --out out/<tag>/ov  t,t,t      # video | preview | video with the preview's edges in yellow
    python3 zoom.py t x0 y0 x1 y1 --step 10 --scale 3 --out out/<tag>/z.jpg [--tag <TAG>]   # pixel grid for reading positions

`make.py` writes the test map/director and an offline run folder (`/home/claude/offline/run_<TAG>`); use a TAG of
your own (given in your task). In Python:

    import sys; sys.path.insert(0, '/home/claude/offline')
    from preview import Preview, ref_frame
    P = Preview('<TAG>')                      # prints materials / models that are still missing
    im = P.render(t)                          # PIL image 640x400 at director time t (same as video time)
    eye, ang, fov = P.cam(t)                  # camera: position, QAngle (pitch, yaw, roll), fov
    P.project(t, [x, y, z])                   # world point -> pixel (x, y, depth)
    P.unproject(t, px, py, 'z', 0.0)          # pixel -> world point on the plane z = 0 (or 'x' / 'y' planes)
    P.row(t)['ents']                          # state of the named entities the director moves (origin, angles, ...)

Look at images with the Read tool. Sheets wider than about 1550 px get downscaled, so keep them at or below that.

## Rules

- Edit only your own files (named in your task). Never edit `base/`, other scenes' modules or the shared libraries;
  if a library lacks something, add a helper inside your own module.
- New materials need your prefix (given in your task) so they cannot collide with anyone else's.
- Models are your own geometry: build them with `lib.mesh.Mesh`. Do not copy or convert meshes from Valve's
  models, and do not copy pixels of the video into textures (procedural textures made with `lib.gen.write_texture`
  are fine). Referring to a stock material by name as a base texture is fine.
- Materials are `UnlitGeneric` flat colours (`lib.gen.mat`); shading is baked with ramps (`ramp` + `Mesh.shade`).
  The video is mostly flat-shaded greys, so sample its colours (`"$color"` is roughly the sRGB value / 255 on a
  white base) instead of guessing.
- Keep the entity names and model names the director uses (see `P.row(t)['ents']` and the base director); if a
  model must move or change size, patch the map in your scene module (`lib.vmfedit`), do not rename it.
- Do not change the camera unless your task says so. When you do, use `Director.set_camera()` with samples at the
  video's frame times, as `scenes/iris.py` does.
- Measure with tools. Reading positions off a grid by eye is good to about 5 px; `ringtrack.fit_ring`,
  `camsolve.edge_points`, colour sampling with numpy and `P.unproject` are much better. Circles in the video are
  true circles in the 640x400 frames.
- Some video frames are blends of two moments during fast motion; prefer clean frames for measuring.
- Leave the container's other folders alone; no network, no git, nothing outside `/home/claude`.

## What to hand back

1. Your module files, building cleanly with the `make.py` line above.
2. Comparison sheets in `out/<tag>/` covering your whole time range at 0.5 s steps or finer (video | preview).
3. A short report as your final message: what you built, the measurements behind the main sizes, what still differs
   from the video (be specific and honest: list times and what is off), and a 1-10 score per the strict scale:
   9 = every half-second sample has the same composition (shapes within about 5 % of the frame), the same objects
   and similar tones, only small details differ; 7 = same shot content and rough framing but clear differences in
   many samples; 5 = same idea, many elements missing or misplaced.
