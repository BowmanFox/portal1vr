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

Published build: `corehub_r10u` + `director_r10u` (outputs/Corehub-Intro). Test run: `videos/r10m_u_side.mp4`.

| # | Scene | Time (s) | v50 base | r10 now | Main remaining differences |
|---|---|---|---|---|---|
| 1 | Opening room | 0–22 | 7.5 | 8 | tiles read greener/lighter than the video's neutral grey; rubble shapes |
| 2 | Iris and ascent | 22–32.5 | 7.5 | 8.5 | iris petal edge shading |
| 3 | Rust room | 32.5–39 | 4 | 7 | far-wall pipe layout, 36–38 s framing |
| 4 | Pod rise | 39.5–47.5 | 4 | 6.5 | video stays inside a glass tube (40–42 s) with lit panel walls; rebuild shows bright pods and the rust floor |
| 5 | Cube passage | 48–55 | 4.5 | 8 | cube jumps close under a short dip (the video's dissolve), lit and tumbling; 49–50 s surroundings too bright |
| 6 | Processing tower | 55.5–65 | 4.5 | 6.5 | 64–66 s look-up at the tower base |
| 7 | Turret and "16" inlet | 65–74 | 5 | 7 | turret now lit white; 64–66.5 s should look down into the turret lift (pistons) and the turret should rise from a floor hole; backdrop greys |
| 8 | Transfer and scanners | 74–83 | 5 | 7 | boards should be brighter white; video's rings are lighter grey |
| 9 | Copper tube, sludge room, gallery | 84.5–95.7 | 4 | 6.5 | video drops down a vertical copper tube into the sludge chamber (86.2–87 s) and climbs another (90.6 s); rebuild crosses it horizontally; chamber walls should be white below black tiles |
| 10 | Factory passage | 96.6–99.8 | 6 | 7 | floor/conveyor details, lighting |
| 11 | Lab and test chamber | 100–109.5 | 4 | 7.5 | white wall with three hanging turrets now framed like the video (103–105 s); low light-blue ceiling (r10w); 107–109 s chamber floor view |
| 12 | Incinerator and final probes | 110–118.4 | 5.5 | 7 | centre glow at 110–111 s, falling debris |
| 13 | Capsule and ending | 118.4–134 | 6 | 7.5 | capsule frost/cracks, hatch lamp colour |

## Not at 9 yet (next work, in order)

1. **Turret lift (64–67 s).** The video exits under the tower's base platform, looks down at a pale floor ring with three dark rods
   running into it, and the turret rises out of that ring (66–67 s) to stand on the floor. Needs: the ring + rods + a rising
   `intro_turret` (MoveProp, and the laser start `laser_turret_a`), the camera ~250 units above the ring at 65.4 s descending to
   the turret's eye level by 67 s, tube rings re-laid along that path, and an extra hole in the x=4364 partition.
2. **Sludge chamber (86–90.5 s).** The video drops down a vertical copper tube into the chamber (86.2–87 s) and climbs another
   (90.6 s); beyond the north walkway there is a black-tiled raised floor with a floor button and signs, not a wall. Camera pitch
   45 is in test (r10x); geometry still to do.
3. **Rust room (32.5–39 s).** Camera is inside a tube ring at 32.75 s where the video is in open space; post under the tube,
   C-bend at the right; 34.25 s and 36.5 s framings.
4. **Pod rise (42–43.5 s).** Video sees frosted skylights then a dark rust wall up close at 43 s.
5. **Tower (58–63 s).** Collars read as black slabs (edge-on tower_ring props); the video sees them as rings from below.
6. **Lab (106–109.5 s).** Looking down at the test chamber: white floor, purple light strip, copper receptacle, checker patch.
7. **Opening.** Tile tint is greener/lighter than the video's neutral grey.
8. **"16" inlet (72.9–73.6 s).** Video sees the vertical tube running down below the sign from outside; rebuild is in the bend.
9. **82.5 s, 94.5 s, 106.5 s** single-view mismatches (see the r10m_q overview sheets).
