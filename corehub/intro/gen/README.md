# Corehub intro: generators and scene patches (Mac era, Oct 2026)

Everything here builds on the last PC build, **r10dm** (`base/corehub_r10dm.vmf`, `base/director_r10dm.nut`; the same
files as `corehub/intro/wip/`). Nothing in `base/` is edited. `make.py NAME` produces a test build:

    out/models-src/*.smd|qc              model sources (compiled on the Mac by the `stage` request)
    out/materials/models/corehub_intro/  the models' materials (UnlitGeneric; flat colours, baked shade ramps)
    out/build/corehub_r10NAME.vmf        base map + scene patches
    out/build/director_r10NAME.nut       base director + scene patches
    (container only) /home/claude/offline/run_NAME/   map.vmf + director + state.jsonl for the offline preview

Test builds are named in the r10 series (`corehub_r10ea`, `director_r10ea`, test run `r10m_ea`).

## Layout

- `lib/mesh.py`      Mesh builder (tri/quad/box/lathe/tube/prism/sphere, `shade()` bakes flat shading into ramp materials,
                     `save()` writes SMD + QC with `$origin 0 0 0 -90`, so SMD coordinates = model coordinates in game).
- `lib/gen.py`       `mat()`, `ramp()`, `save()`, `write_texture()` (own VTFs, version 7.2).
- `lib/director.py`  `Director`: parses the camera tables (`positions`, `knots`), `set_camera(t0, t1, samples)`,
                     checked `replace()` / `sub()` / `append()`, `lint()` (the old sqlint rule).
- `lib/vmfedit.py`   srctools helpers: `ents()`, `one()`, `add_prop()`, `add_box()`, `solid_bounds()`.
- `lib/camera.py`    `ray()`, `project()` for the film frame (640x400 pixels, 16:10; `fov` is horizontal at 4:3).
- `models/*.py`      one generator per group; each has `build()`.
- `scenes/*.py`      one module per scene; each has `apply(v, d)` (VMF, Director).
- `data/`            tracks solved from the video (camera positions per video frame, ring heights).
- `build.py`         models and materials only; `make.py` everything.

## Method (what made the iris/ascent frame-accurate)

1. **Measure the video with tools, not by eye.** `tools/offline/ringtrack.py` fits circles to ring edges
   (sub-pixel; reading pixel grids by eye was off by 5-7 %). `ringcmp.py` runs the same fit on the offline preview
   and prints the differences.
2. **Solve sizes from parallax.** While the camera bobs, `1/r_far = a + b * (1/r_near)` over many frames gives a far
   ring's radius and distance from a near ring of known size (regression over the 23.5-31.2 s hold: tube mouth
   R 45.84 at 116.8 above the frame ring, first collar R 61.06 at z 933).
3. **Solve the camera per frame** from the ring edges (`camsolve.py`: point-to-projected-circle distances, robust
   least squares). Orientation that the rings cannot see (rotation about the view axis) stays fixed.
4. **Bundle solve along the tube** (`solve_iris.py`): per-frame camera height + collar heights from all visible
   collars; rings pass the camera at the video's frame times (residual below 1 px).
5. Write the track into the director with `Director.set_camera()` and the geometry into the map; check in the
   offline preview, then in a real test run.

Facts found on the way:
- The video is rendered 16:10 and stored 16:9; the 640x400 reference frames have square pixels (rings fit as circles).
- Some video frames are blends of two moments (ghost images during fast moves, e.g. 31.20-31.27 s); measurements
  on those frames are less reliable.
- The opening-room iris and ascent were at about 0.6 of the true scale in r10dm (collars R 37 at z 617-1895, camera
  1250 u/s). True: collars R 61.06 at 933 / 1489 / 2355 / 3226, camera 2096 u/s, constant orientation
  (-83.17, -7.18, 0.30) with only the position shaking.
- `material_modify_control` only works when the material has the `MaterialModify` proxy (the ceiling "exposure").
- prop_dynamic angles `270 y 0` point model +X up; ascent collars and the cap are placed with `0 0 0` (axis = model +Z).

## Offline preview (container, `tools/offline/`)

    python3 cmp.py NAME t,t,t           video | preview sheets          (--run RUN adds a fetched game run)
    python3 overlay.py NAME t,t         video | preview | video with the preview's edges
    python3 zoom.py t x0 y0 x1 y1       zoomed video frame with a pixel grid (--tag NAME adds the preview)
    python3 pairs.py RUN t0 t1 step     video | game run sheets;  tri.py RUN: video | published r10dj | run
    from preview import Preview; P = Preview('NAME'); P.render(t); P.cam(t); P.project(t, xyz); P.unproject(t, px, py, 'z', z0)

The preview executes the real director in a standalone Squirrel interpreter (`sim_run.nut`, 60 Hz, delta-coded
states) and ray-casts the map's brushes plus the models' SMD sources (stock models from their compiled files).
Unlit materials are exact (texture sRGB, `$color` gamma 2.2, blending in linear light); lit stock materials are
only approximated, and screen overlays (glare, flicker) are not drawn.
