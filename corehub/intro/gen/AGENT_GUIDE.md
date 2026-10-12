# Rebuilding one shot of the Corehub intro (film-scale method, Oct 11 2026)

You rebuild one part of a 134 s video (Portal 2's 2009 "Corehub" intro: a pre-rendered ride through pneumatic tubes and
huge rooms) as a Source-engine map. The video is the only target: at every moment of your range the rebuild's frame
must show the same composition, shapes and tones as the video's frame. You work in this Linux container with an
offline preview renderer; the real game runs elsewhere and is not your concern.

## What the film is (measured, trust these)

- Frame n of the video is at t = n * 1001 / 30000 s. Reference frames: `/home/claude/data/frames/f%04d.jpg` (640x400),
  `/home/claude/data/frames_hd/f%04d.jpg` (1280x800 colour). Square pixels at these sizes.
- **Field of view 60** (Source fov, horizontal at 4:3) everywhere in the ride: focal length 461.88 px on the 640x400
  frame (923.76 on 1280x800), principal point at the centre (319.5, 199.5). The old r10 build used 90 in most scenes:
  that is why its ride scenes never matched. Use `fov=60.0` in `Director.override_camera`.
- **Every video frame is a blend of two moments** 1/60 s apart (E = earlier at t_n, L = later at t_n + 1/60): in fast
  motion you see double images. The separated moments are `/home/claude/data/moments/E|L/f%04d.jpg` (1280x800 grey,
  some line noise): measure on those; look at the blended frames. The game run records 60 fps, so your camera
  samples come at 60 per second (the ride tools write them that way).
- **Scale is true film scale, map units**: the tubes' collars have a light band of radius 61.06, the four rails are
  1.8 thick square bars 34 from the tube axis on the diagonals. The camera rides exactly on the tube axis (a few units
  of shake) and moves 1500 - 6000 units per second, so the rooms are thousands of units across.
- The rooms and tubes are built on three perpendicular axes. In a straight tube the camera looks exactly along the
  axis; in a bend the view turns about one room axis and leads the path (looks into the turn).

## The ride tools (`/home/claude/offline`, run from there)

    python3 ride_export.py DB first last anchor NAME [forward] [up]          # ~2 min
      DB      a COLMAP run of your frames: /home/claude/sfm/<DB> (made by run_sfm.py; see your task for which)
      anchor  a frame in a straight tube section; forward / up: room axes the camera looks along / has overhead there
              (+x / +z unless you continue another shot's axes)
      -> /home/claude/work/gen/data/NAME_ride.json   for the map side (lib/ride.py)
         out/NAME_ride.pkl, out/NAME_points.npy        for checking (triangulated feature points = the room's surfaces)
      prints: straights / bends, the speed of every straight (from the collars it passes, else COLMAP), the bundle
      adjustment of every bend (reprojection < 1 px median is good; "fewest observations 0-5" = that bend leans on its
      priors), wall planes (axis, coordinate, extent), frames where the camera passes a collar.

What it does: orientation from the room lines (exact in straights), turn angle per moment in bends (lines + feature
gyro, dynamic programming); speed per straight from the collars (true scale); positions in bends by bundle
adjustment with the orientations held; the path = straight lines + smoothed bends (monotone quarter turns).

Check it before you build on it:

    import railfit as RF
    rd = RF.load(NAME)                                   # out/NAME_ride.pkl
    RF.overlay_curve(rd, range(a, b, 2), 'out/<tag>/rails.jpg', 34.0, cols=4)   # film moments + the path's rails (yellow)

The yellow rails must lie on the film's dark rails, in the straights and in the bends. Where they do not, the bend
is off (or the shot is not a plain tube ride there: junctions, rooms). Known limits: a junction where a branch leaves
a main tube is measured right for the camera, but the rails of a junction are not offset curves of the path (model
them yourself). Hard cuts end a shot: one export per shot (find cuts with the frames; `moments/ncc.npy` holds the
frame-to-frame similarity, low = cut).

Other tools: `cmp.py`, `overlay.py`, `zoom.py`, `score.py` (preview vs film, see below), `kymo.py` (radius-versus-frame
diagram of rings in a straight), `sheet.py out.jpg first last step [--src hd|E|L] [--crop x0,y0,x1,y1] [--w 512]`
(contact sheets of film frames), `modelview.py NAME` (six views of one of your models), `sfmtools.Recon(DB)`
(the COLMAP model itself), `ringscale.edge_lines` (ring edges against camera position).

## The map side (`/home/claude/work/gen`)

    from lib.ride import Ride
    from lib import tube, vmfedit as E
    rd = Ride(NAME, origin=(x, y, z), unit=1.0)       # your cell's origin; unit = scale (see Cells)
    d.override_camera(rd.camera(), fov=60.0)         # the film's camera for the whole shot
    tube.add_straight_rails(v, rd)                    # brushes
    tube.add_bend_rails(v, rd, '<prefix>_<shot>')    # models swept along the measured bends (built by make.py)
    tube.add_collars(v, rd, prefix='<prefix>_<shot>') # p9_ascent_collar_plain_v4 where the film passes collars
    rd.planes                                         # measured wall planes (map coordinates)
    rd.pos(frame), rd.direction(frame), rd.at(s), rd.rails(), rd.sections, rd.straights()

`scenes/rust.py` is the worked example (shot A of the rust room: camera, tube, main walls, sealed shell).

Build and look:

    cd /home/claude/work/gen
    python3 make.py <TAG> --scenes iris,<your scene> --models tubekit,iris,<your groups> --range t0,t1    # ~10 s
    cd /home/claude/offline
    python3 cmp.py <TAG> --cw 384 --cols 2 --rows 5 --out out/<tag>/cmp  t,t,t,...     # film | preview
    python3 score.py <TAG> t0 t1 0.25 --quiet                                          # ssim / edge / tone

    from preview import Preview, ref_frame
    P = Preview('<TAG>'); im = P.render(t); P.cam(t); P.project(t, xyz); P.unproject(t, px, py, 'z', z0); P.pick(t, px, py)

Look at images with the Read tool; keep sheets at or below about 1550 px wide.

## Cells (where your geometry goes) and scale

The old map occupies x -13832..11800, y -6982..2591, z -800..6037. New geometry goes into your own cell (given in your
task), sealed by a black shell (`scenes/rust.py: shell`). A shot that does not fit its cell at true scale is built at a
smaller scale: `Ride(NAME, origin, unit=k)` with k < 1 scales the camera path, and you scale everything else by k too
(rails: `tube.add_*` take rho / width; collars: build a scaled collar model, see `models/iris.py: collar(R=...)`).
The picture does not change with scale (keep k >= 0.4 so the near rails stay farther than the engine's near plane).

## What the game does differently from the preview (learned from the full test runs)

- **Stock models with lit materials render BLACK** in the new cells (no light there): build your own unlit models (as
  the turret agent did), or place `light` entities near the stock model and check the brightness in a game run.
- **The 2009 engine has no SetAngles / GetAngles**: a call stops the whole director (the screen stayed black from 84 s
  in the first run). Turn props with `e.__KeyValueFromString("angles", "p y r")`. The preview now fails on them too.
- **Map limits**: the 2009 vbsp is close to its brush-side limit (the whole map has room for about 1300 more brushes):
  large plain surfaces as brushes, everything else as models. Models that do not move are `prop_static`
  (`E.add_prop(..., cls='prop_static')`, no targetname): prop_dynamic only for animated parts (entity limit).
- **Leaks**: every point entity (props included, also where a hook parks them at first) must be inside a sealed shell,
  or the whole map leaks and does not compile: `python3 /home/claude/work/tools/leakcheck.py <your vmf>` must report 0.
- **Screen fades** (SetScreenBlack and the other env_fade veils) are drawn over the finished frame in GAMMA space in
  the game: a black fade of alpha a scales the frame's 0-255 values by (1 - a/255). The preview did this in linear light
  until Oct 12 (fades looked weaker there: 106 instead of the game's 84 at 5.5 s); it now matches the game, so fade
  tables tuned on the old preview are too dark now: re-fit them against the film (alpha = 255 * (1 - film/unfaded)).
- **Screen overlays** (env_screenoverlay) are drawn by the game but NOT by the preview: the old director's
  r10_flicker_ov (6.85-7.85 s, the opening's cable flash) and r10_glare_ov (69.4-71.34 s, a grey veil with a wide red
  glow that hid the turret in the game; the turret scene now stops it).
- **Sample timing**: the video frame for a sample time t is n = round(t x 29.97); it blends the moments
  n x 1001/30000 and + 1/60. The scorers (score.py, cmp.py, runscore.py) and the Mac's fetch_run.py compare the
  game / preview at that frame's own time (`preview.film_time(t)`), not at t (until Oct 12 13:30 they used t: half a
  film frame late at x.25 / x.75 s; do not compensate for that offset in your scene any more). When you render
  yourself to compare with `ref_frame(t)`, use `P.render(film_time(t), blend=True)`.
- Otherwise the game matches the preview closely (geometry, unlit materials, world translucency).
- Game runs: frames of the newest run are in `/home/claude/data/runs/<run>/m<milliseconds>.jpg` every 0.25 s (blends of
  the game's two 60 fps frames at t and t + 1/60, like the film); `cmp.py TAG --run <run>` shows film | game | preview,
  `score.py TAG t0 t1 0.25 --run <run>` scores the game frames, `runscore.py <run>` all scenes.

## Rules

- Edit only your own files (named in your task): your scene module, your model module(s), your data/<NAME>_ride.json.
  Never edit `base/`, `lib/`, other scenes or the offline tools; if a library lacks something, add a helper in your
  own module (and say so in your report).
- New materials and models need your prefix (given in your task).
- Models are your own geometry (`lib.mesh.Mesh`, `lib.gen.mat` / `ramp`): no copying or converting Valve meshes, no
  video pixels in textures (procedural textures with `lib.gen.write_texture` are fine; sample the film's colours and
  panel sizes with numpy). Stock material names as base textures are fine.
- Materials are `UnlitGeneric` (flat colours, shading baked with `ramp` + `Mesh.shade`): the film is mostly flat.
- Keep the director's entity names; when your shot is rebuilt in a new cell, the old scene's entities simply stay
  unused (do not delete them unless your task says so).
- Measure with tools, not by eye: by eye is good to about 5 px; the tools to a fraction of that.
- Leave other folders alone; no network, no git, nothing outside /home/claude. CPU is shared with other agents:
  render sheets of ~10-20 frames, not hundreds; do not run several ride exports at once.

## What to hand back

1. Your files, building cleanly with your `make.py` line.
2. Comparison sheets in `out/<tag>/` covering your whole range at 0.25 s steps (film | preview).
3. A short final report: what you built, the measurements behind it, `score.py` means for your range, what still
   differs from the film (specific: times and what), and a 1-10 score on the strict scale:
   10 = indistinguishable; 9 = every half-second sample has the same composition (shapes within about 5 % of the
   frame), the same objects and similar tones, only small details differ; 7 = same shot content and rough framing
   with clear differences in many samples; 5 = same idea, many elements missing or misplaced.
