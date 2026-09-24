# Gun light and portal crossing camera

The blue/orange gun light was displaced after its attachment had already been
aligned to the tracked gun. In the installed Portal client,
`GetEffectParameters` (`0x24B5B0`) calls the attachment reader, then applies
`FormatViewModelAttachment` (`0xC7A80`) to the returned position. That second
operation applies the desktop/viewmodel FOV ratio to a VR world-space point.
The guarded hook retains the exact tracked output position for this effect
query. Color, size, material, world-model effects and unrelated attachment
queries continue through the native path.

The headset-only crossing report exposed a separate coordinate-space defect.
Read-only sampling during the installed play session observed
`C_Portal_Player::CalcPortalView` setting its transformed-eye flag while the
eye was behind the active portal plane. The existing VR renderer used that
already-transformed origin, added untransformed roomscale/stereo offsets, and
replaced the native angles with the untransformed HMD angles. The desktop
camera retained the complete native transform.

The renderer now checks the native transformed-eye flag and linked matrix,
returns the native eye to player space, adds tracked offsets there, and maps
the complete eye frame through the portal. Temporary first-person body/hand/
gun bones and gun attachments use that same mapping. Bone caches, physics,
native teleport timing, portal recursion and desktop camera are preserved.
This handles the confirmed native transformed-camera state; it does not
introduce a second teleport decision or change portal opening collision.

Validation:

- Release x86 build succeeded with no errors or warnings on the final build.
- The installed client passes native camera, glow-effect, attachment and trace
  signature/layout guards.
- 600 stereo camera/model/light regressions cover wall, floor, ceiling and
  inverted portal transforms with varied head pitch, yaw and roll. They check
  camera-relative model positions and orientations, attachment alignment,
  nested scope restoration and disabled/invalid native state.
- 21,168 glow-position checks cover both eyes, FOV ratios and 196 controller
  poses against the compiled gun. World-model and unrelated-query behavior
  remain unchanged.
- Existing compiled-model, both-color shot, wrist carry, support-hand,
  calibration, collision and ragdoll-bone regressions passed.
- Background OpenVR timing sampling recorded successful submissions and no
  compositor fade around the captured portal-crossing interval. A separate
  loading pause caused a grid fade; the timing evidence does not independently
  prove the reported headset flash is eliminated.

Headset confirmation of the new light and crossing changes is pending.
The compiled package was installed on September 24 after fresh-install,
upgrade-preservation and repeated-install tests passed. The installed DLL hash
matches the tested package; the existing configuration and model VPK are
byte-for-byte unchanged. Package hashes and installation checks are recorded
in the adjacent JSON report.
The compiled avatar is unchanged from the death-crash hotfix, retaining its
blendshapes, eyes, jiggle bones, physics and corrected ragdoll evaluation flags.
