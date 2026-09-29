# Bowman models for the 2009 Corehub prototype

Two co-op coats recolor Bowman's existing grey markings blue or warm orange,
with distinct iris colors. Single-player uses Portal 1 Bowman's original coat
and eyes with the current mesh improvements. Foot soles have
continuous UV projections and neutral dark pads, separate from the coat atlas.
The center pad follows the supplied broad paw-print reference. The latest blue
foot sculpt is the base for regular mesh edits that soften the outer corners
and round the middle toe undersides. The middle pair is longer and fuller for
the requested toony canine proportions, and the two smaller side toes have
matching reach. Local toe subdivision adds 1,652 vertices with interpolated
weights. The user's latest saved blue upper-body sculpt is merged into all
three variants while the finished feet and their UVs stay unchanged.
The original 137 shape-key entries and their expression offsets are retained;
no cleanup shape key is added.

This package contains the character assets only. The Corehub VR runtime is
installed separately; see `../RUNTIME.md`. Its `-corehubvr` launchers use these
profiles.

## Install and launch

`Bowman_Corehub_Models.zip` and `package-manifest.json` contain the compiled
character assets and their checksums. This is an installable asset preview.

Run `Install.ps1 -GameRoot "C:\path\to\Portal 2 2009 Corehub Overwatch Build"`.
It verifies the package hashes, backs up overwritten package files, and writes
only `bowman_coop/`, `bowman_singleplayer/`, and their two launchers under that installation.

Use **Launch Bowman Co-op.cmd** for the co-op character profile. It starts
`mp_coop_start` with two player slots. The normal game launch and its original
`portal2/models/player.*` remain unchanged. All maps deliberately opened inside
the co-op profile use these models; this is launch-profile isolation, not an
automatic multiplayer-only model switch in the game DLL.

Use **Launch Bowman Single-player.cmd** for the original-colour character.
Choose New Game or Load Game from the native menu. This profile includes the
Portal 1 Bowman portal-gun hands rebuilt with Corehub's native compiler.

## Model and physics

- Native version-49 model; 97 bones including all 66 prototype animation bones.
- Uses the installation's original `models/player_animations.mdl`; no Valve
  animation binaries are redistributed.
- Five skin roles: blue, orange, silhouette, blue first-person, orange first-person.
  First-person roles hide head materials while retaining the torso.
- Measured Source QC eyeballs, eye attachments, gaze controls, and iris skin swaps.
- Ragdoll collision mesh and joint constraints compile to `player.phy`.
- Twelve Source jiggle bones: four tail segments and four per ear, with bounded
  flex and damping. Compiled procedural records are verified in both Corehub
  profiles. Portal 1's installed Bowman already has the same twelve records.
  The main head and neck bones remain animated, not spring driven.

The animation proportion layer changes translations only. Applying the fitting
rotation again on top of native animations twisted the arms. Blender edit bones
are now created with explicit heads/tails/roll and checked against exported axes.
The original matching vertices verify symmetric skeleton weights. The user's
latest sculpt has small left/right foot differences, which are preserved. Both
co-op variants use the same mesh, shape keys and UVs.

## Source and validation

`source/Bowman_Corehub_Models.blend` contains all three saved character scenes. Back it up
before editing. The QC and SMD files are the exact inputs used for this package.
The native model was rebuilt with the prototype's own compiler. A portable build
entry point is still pending. Python 3 and the x86 Windows SDK debugger (`cdb.exe`)
were used. The compiler's
old CPU-count limit is adjusted in its own process after signature verification;
no game binary is patched on disk.

`package.py --compiled-models PATH --materials PATH --skin-audit PATH` rebuilds
the ZIP from compiled `player.*` components, the custom material directory, and
the skin-family audit. It checks component compatibility and includes only the
materials and textures referenced by those skin families.

The editable bodies contain 137 original shape-key entries, including Basis.
These were recovered from the Portal 1 authoring avatar using its original UV
correspondences, interpolated symmetry-cut vertices and mirrored expressions.
Their offsets are added to the current sculpt. Shape keys are retained in the
Blender source; facial VTA/DMX flex animation is **not yet exported to Source**.
The compiled model retains the QC eyeballs and native skeletal animations.

The Blender previews are in `previews/`. Geometry/weight and skin audits are in
`validation/`; `torso-merge-audit.json` identifies the final merged source,
and `sculpt-export-audit.json` links that source to the QC/SMD build inputs.
Earlier intermediate checks are retained under `validation/previous/`.
Compilation and previews do not establish live Pico compatibility,
two-player behavior, or correct behavior of every co-op taunt.
