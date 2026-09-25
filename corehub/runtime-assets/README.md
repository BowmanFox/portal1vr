# Corehub bare hands

The five files in `models/weapons` are the native build 3916/v49 compilation of
the Portal 1 Bowman hand source in `source/v_hands`. They retain its 43-bone
layout, skin weights and three sequences. The material search path is changed
to `models/bowman_corehub`, supplied by the separate Bowman model package.

`Install-Runtime.ps1` installs these into each existing Bowman profile, with
backup and hash verification. The runtime precaches the model on the server,
creates the second viewmodel and explicitly draws each unarmed hand. Compile
the QC with Corehub's own `bin/studiomdl.exe`; a Portal 1 v48 model is not a
replacement for this v49 compilation. The editable Blender scenes are unchanged.
