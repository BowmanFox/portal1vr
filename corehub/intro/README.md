# Corehub intro rebuild: status (film-scale rebuild, Oct 12 2026)

Published build: **corehub_r10ga + director_r10ga**, test run **r10m_ga2** (60 fps, automatic camera, the Mac
pipeline). It replaces the r10 series (last published r10dj). Not every scene is at 9/10 yet; work continues.

## What changed: the film measured, every ride scene rebuilt at the film's scale

- **The film's camera is fov 60 everywhere** (vanishing points of tiles and panels: f = 457-468 px at 640 wide). The r10
  series used fov 90 for 32.5-118 s, which is why its ride scenes never lined up.
- **The reference is 1280x720 at 29.97 fps, rendered 16:10, and every video frame blends two moments 1/60 s apart.**
  The two moments are separated (tools/offline/fieldsplit.py) and used for measuring; the scorers compare the game's
  60 fps frames blended the same way.
- **True scale.** The tube collars' light band has radius 61.06 and the four rails sit 34 from the tube axis; the camera
  moves 1500-6000 units per second, so the rooms are thousands of units across.
- **Measured rides** (tools/offline): COLMAP structure-from-motion per shot (`run_sfm.py`); orientation from the room
  lines plus a feature gyro with one turn angle per moment in bends (`orient.py`, `gyro.py`, `ride.py`); speeds from the
  collars passing the camera; bends by bundle adjustment with the orientations held (`bendba.py`); the path as a curve
  (`ride_export.py` -> `gen/data/*_ride.json`); rail overlays on the film to check it (`railfit.py`).
- **Every scene from 32.6 s on is rebuilt in its own sealed cell** north of the old map (y > 3000) with the film's camera
  at 60 samples per second (`Director.override_camera`, fov 60). The opening keeps its room with 17 rebuilt models; the
  iris/ascent is unchanged. The old middle hall's detail brushes are removed (the 2009 vbsp ran out of brush sides).
- **Generators** (`gen/`): one module per scene (`scenes/*.py`) and per model group (`models/*.py`), shared libraries
  (`lib/ride.py`, `lib/tube.py`, `lib/director.py`, `lib/vmfedit.py`, `lib/mesh.py`); `make.py NAME` builds the map,
  the director and the offline preview. `gen/AGENT_GUIDE.md` explains the method.

## Scores (1-10, strict, against the 2009 video; ending blink and black not scored)

Objective columns: score.py means over 0.25 s samples (ssim = the similarity.py metric; edge = outline agreement; tone =
brightness layout; 1 = identical). "Before" is the r10-era test run r10m_ea measured the same way (0.5 s samples).

| # | Scene | Time (s) | Before ssim/edge/tone | r10m_ga2 ssim/edge/tone | Score | Main remaining differences |
|---|---|---|---|---|---|---|
| 1 | Opening room | 5-21.7 | 0.45 / 0.54 / 0.53 | 0.63 / 0.64 / 0.76 | 6.5 | tones of the far room and wall tops, slab face, dome shape, cable flash |
| 2 | Iris and ascent | 21.7-32.6 | 0.68 / 0.67 / 0.78 | 0.74 / 0.72 / 0.81 | 9 | petal shading, small debris |
| 3 | Rust room | 32.7-38.9 | 0.35 / 0.51 / 0.61 | 0.46 / 0.49 / 0.76 | 5 | collar translucency and passing, junction rails, panels round the tube mouth, shot B devices |
| 4 | Pod | 39.3-48 | 0.41 / 0.41 / 0.67 | 0.47 / 0.37 / 0.69 | 5 | room backgrounds (tanks, scaffolds, textures), the cross tube at 46.8-48.3 |
| 5 | Cube | 48-54 | 0.42 / 0.34 / 0.63 | 0.47 / 0.32 / 0.67 | 5 | pale collar structures, the whip at 50 s, structures outside the rings |
| 6 | Tower | 54.9-64 | 0.33 / 0.53 / 0.60 | 0.47 / 0.54 / 0.71 | 4 | the glass tower interior (turrets, arms, discs, lasers, diagonal tubes) |
| 7 | Turret and "16" | 64-74 | 0.44 / 0.37 / 0.61 | 0.51 / 0.47 / 0.73 | 4 | the stock turret renders black in the unlit cell; second turret, scanner head, final rise |
| 8 | Scanners | 74-83.1 | 0.37 / 0.47 / 0.61 | 0.43 / 0.54 / 0.64 | 5 | the split cake picture at 74 s, ring density, the turn to the iris (80-81 s) |
| 9 | Sludge and gallery | 84.6-95.7 | 0.32 / 0.46 / 0.54 | 0.40 / 0.51 / 0.57 | 5.5 | copper truss towers, the gallery's dark glass, window grid, plank wall details |
| 10 | Factory | 96.6-99.8 | 0.19 / 0.34 / 0.37 | 0.28 / 0.63 / 0.68 | 6 | grey machinery on the +y side, conveyor machinery, collar insides |
| 11 | Lab | 100-109.6 | 0.35 / 0.40 / 0.34 | 0.39 / 0.41 / 0.43 | 4.5 | translucent glass collars, the sphere room walls, lab 2's fast move (107-109.5 s) |
| 12 | Incinerator | 109.9-118.4 | 0.36 / 0.43 / 0.54 | 0.49 / 0.43 / 0.69 | 5.5 | stock turret black and too small, scanner fans, iris checker pattern |
| 13 | Capsule | 119.3-132.3 | 0.45 / 0.32 / 0.56 | 0.52 / 0.33 / 0.65 | 6 | collar bands, pod lid glass, lamp shading |

All scenes together: before 0.41 / 0.46 / 0.58, now 0.51 / 0.50 / 0.68.

## Test runs on the Mac

Requests are files in `revision9/requests/` (see `tools/mac/watcher.sh`): `stage <build> <director>` copies a generated
build and compiles its models, `cycle <build> <director> <movie prefix>` compiles the map, packs the director, records
the 60 fps run and assembles `r10/videos/<prefix>_side.mp4` (original | rebuild). Film frames never go to GitHub.
