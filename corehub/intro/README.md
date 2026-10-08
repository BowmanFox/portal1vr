# Corehub intro rebuild: r10 status

r10 is built on top of the newest pursuit9 map (capsule-follow v50: walkable opening, measured factory passage, capsule follow).
`patch_r10.py` patches the v50 editable VMF, and `patch_director.py` patches the v50 director. The v50 files themselves are never edited.

## What r10 changes

- **Separate rooms.** The old shared middle hall is split by full-height partition walls at x = 1528, 2840 (dark tunnel), 3400 (cube passage | tower), 4364 (tower | turret room), 4980 ("16" wall), 6000, 6780, 7300 and 7960.
  - Each wall only opens where the tube (or a side tube) passes through.
  - The openings are computed from the tube's own ring props and the camera path. A collar ring frames each opening.
  - A clearance check confirms the camera never enters a wall.
- **Walls at the video's angles.** The turret backdrop was rebuilt to face the camera squarely, as in the 66–71 s shots. Partitions are frontal to the tube.
- **WIP / unfinished content.**
  - Pale `dev_measuregeneric` panels on the cube-passage wall (50–53 s), on an upper corner of the "16" wall, and on the back of the lab partition.
  - A hazard-striped bulkhead edge, and an unfinished floor patch under the pod rise.
- **Materials matched to the video.**
  - Copper collars on the low tube (84–110 s).
  - Cream-white lattice towers and gallery truss (85–93 s).
  - Dark-tile sludge test room (87–90 s), black-tile lab walls (100–104 s), and a white tiled wall behind the hanging turrets (104–105 s).
  - Dimmed pod-room skylights (41–43 s).
- **Cuts dissolve like the video** at 38.7, 53.8, 82.6, 84.6, 95.3, 105.0 and 109.4 s. The timings were measured from the video's frame luminance.
- **"16" wall framing.** Camera knots at 73–73.5 s keep the "16" wall framed like the video.
- **Opening iris cover.** The closed iris now uses the ceiling's own material and texture alignment, so it disappears into the ceiling until it opens (5–11 s), as in the video.
- **Custom scanner model.** `models/corehub_intro/scanner_board.mdl` (built by `models/build_board.py`, compiled with studiomdl) replaces the round scanner heads in the transfer shaft (74–80 s) with flat boards on arms.
- **Tower entrance (55.5–58 s).** A centred collar ring, horizontal pipes and a pale concrete block frame the tube entrance; the camera knots at 56–58 s keep it centred.
- **Lab (100–109.5 s).** A cube rides ahead in the tube (100–101.9 s), the camera turns right at 103 s and looks down into the opened test chamber at 107–109.5 s.
- **Director patches are tested by packing them.** A controlled run (r10m_v: r10u BSP + loose r10v director) matched r10u frame for frame, so the director packed in the BSP is what runs. Every test BSP is packed with the director under test; `-Director` additionally keeps the loose copy in step.

## Test runs

- The watcher handles `requests\movie-<name>.req`, for example:
  ```
  -Prefix r10m_x -Fps 60 -Quality 90 -Bsp <path to bsp> -Director <path to director.nut>
  ```
  - It runs `r10\record_movie.ps1`: the game records a 60 fps fixed-step movie with the automatic reference camera (no input needed) and the in-game soundtrack.
  - It then runs `r10\assemble_movie.ps1`, which writes `r10\videos\<name>_map.mp4` (rebuild) and `<name>_side.mp4` (original | rebuild), plus 1 s stills for scoring sheets (`r10\tools\sheets.py`).
- The normal Play.cmd setup (`mapspawn.nut` / `autoexec.cfg`) is restored after every run.

## Scores (1–10, against the 2009 video; ending blink/black not scored)

Published build: `corehub_r10ax` + `director_r10ax` (outputs/Corehub-Intro). Test run: `videos/r10m_ax2_side.mp4`.

| # | Scene | Time (s) | v50 base | r10 now | Main remaining differences |
|---|---|---|---|---|---|
| 1 | Opening room | 0–22 | 7.5 | 8.5 | ceiling bright/neutral looking up and dark at grazing angles; far wall and chamber glass toned to the video; rubble shapes |
| 2 | Iris and ascent | 22–32.5 | 7.5 | 9 | matches shot for shot; iris petal edge shading, small falling debris at 26 s |
| 3 | Rust room | 32.5–39 | 4 | 7.5 | far wall cut to the lit panel, dark C-bend, post under the ring (33 s); 34–36 s framings still off |
| 4 | Pod rise | 39.5–49 | 4 | 8 | dark walls and rings; white chrome drop ahead; the run ends at a pale crossing tube and a pale wall (46.5–48.9 s) like the video; pods still read as round blobs |
| 5 | Cube passage | 48–55 | 4.5 | 8.5 | cube hidden until 51.5 s like the video; 48.5 s pale tube interior |
| 6 | Processing tower | 55.3–65 | 4.5 | 8 | entrance now two shots with the video's dissolves (56.5, 58.6 s): rails only, pale collar, dark column with flange, rust back wall; collar framed a little large |
| 7 | Turret and "16" inlet | 65–74 | 5 | 8 | turret rises in the ring and holds front-on through the glare; dark bars round it; sign framed top-centre at 72.5–73 s; 71.5 s dissolve missing |
| 8 | Transfer and scanners | 74–83 | 5 | 8 | light-grey shaft rings; cones/iris re-timed; 81.5 s iris framed closer than the video |
| 9 | Copper tube, sludge room, gallery | 84.5–95.7 | 4 | 8 | sludge chamber rebuilt to the video's proportions (r10au/av: floor at z 0, far wall at y 608) with the white wall foot, rod and claw, raised plate, round door, signs and laser; gallery (91–95 s) still differs: the video climbs out over a white truss to a broken pipe opening |
| 10 | Factory passage | 96.6–99.8 | 6 | 7.5 | warmer, brighter factory materials; one-frame black arm silhouette at 98 s |
| 11 | Lab and test chamber | 100–109.5 | 4 | 8.5 | chamber view matches (receptacle, checker, button, strip, black tiles); copper drop onto the receptacle |
| 12 | Incinerator and final probes | 110–118.4 | 5.5 | 8 | yellow glowing ball drops with the discarded parts; the video's ball passes closer (115 s); 116.75 s view |
| 13 | Capsule and ending | 118.4–134 | 6 | 8 | capsule frost/cracks, 123.4 s flat grey patch |

## Objective check

`tools/similarity.py <run>` scores every half second against the video (SSIM on blurred 128x80 greyscale; 1 = identical) and
prints per-scene means and the worst moments. It is a regression guard, not the score: the factory looks close but scores
low because its fine detail never lines up. r10m_q 0.453 -> r10m_z 0.471 mean.

## Not at 9 yet (next work, in order)

1. **Gallery (90.5–95.7 s).** The video climbs out of the chamber up a copper tube, runs above a white truss along a rust
   wall to a broken pipe opening (93–94.25 s) and passes a white collar (94.75–95.25 s); the rebuild runs straight through rings.
2. **Tower and turret lift (62.8–66 s).** In test (r10ah/ai): the camera crosses over the turret-lift collar, looks down on
   it with the tubes hanging under it, drops through it to the floor ring and watches the turret rise. Still to match: the
   dark collar overhead at 62.8 s, the tower interior with lasers and the "16" sign at 63.4–64 s.
3. **Rust room (33.5–36.5 s).** 33.5 s turn along the wall, 35–36 s ring/bend views.
4. **Pod rise (39.5–42 s).** The video's pod walls are dim vertical panels; the rebuild's read as bright round pods.
5. **Incinerator (114–116.75 s).** Glowing ball in test (r10ai); 116.75 s view.
6. **Lab (106–106.6 s).** The chamber floor shows at the bottom of the tube view; the video is dark there.
7. **Factory (98 s).** The camera passes the white collar's inside during a fast turn (97.93–98.07 s); its inside is now dark copper instead of black (r10av).
8. **Turret (71.5 s).** The video dissolves through a top view of a ring with the turret before the "16" wall.
