#!/bin/zsh
# doctor: reports what this Mac has for the Corehub pipeline. Read-only.
emulate -R zsh
setopt null_glob
CX=/Applications/CrossOver.app
CXBIN=$CX/Contents/SharedSupport/CrossOver/bin
sec() { print; print "== $1" }
sec system
sw_vers 2>&1
print "arch $(uname -m)  cpu $(sysctl -n machdep.cpu.brand_string 2>/dev/null)  cores $(sysctl -n hw.ncpu)  mem $(( $(sysctl -n hw.memsize) / 1073741824 )) GB"
print "user $USER  home $HOME  shell $ZSH_VERSION"
sec rosetta
if /usr/bin/arch -x86_64 /usr/bin/true 2>/dev/null; then print "rosetta ok"; else print "rosetta MISSING"; fi
sec displays
system_profiler SPDisplaysDataType 2>/dev/null | grep -E 'Chipset|Metal|Display Type|Resolution|Main Display|UI Looks|Online' 
sec power
pmset -g batt 2>&1 | head -3
sec crossover
if [[ -d $CX ]]; then
  print "version $(defaults read $CX/Contents/Info CFBundleShortVersionString 2>&1)"
  ls $CXBIN 2>&1 | tr '\n' ' '; print
  print "bottles:"; ls -la "$HOME/Library/Application Support/CrossOver/Bottles" 2>&1
else print "CrossOver MISSING"; fi
sec gptk
ls -d "/Applications/Game Porting Toolkit.app" 2>&1
ls "/Applications/Game Porting Toolkit.app/Contents/Resources" 2>&1 | head -20
sec tools
for t in python3 ffmpeg ffprobe git gh brew wine wine64 7z unzip magick; do print -n "$t: "; command -v $t || print missing; done
python3 --version 2>&1
python3 -c "import sys; print(sys.executable)
for m in ('PIL','numpy','cv2','skimage'):
    try:
        mod=__import__(m); print(m, getattr(mod,'__version__','?'))
    except Exception as e: print(m,'MISSING')" 2>&1
if (( $+commands[ffmpeg] )); then
  ffmpeg -version 2>&1 | head -1
  print -n "bink decoder: "; ffmpeg -hide_banner -decoders 2>/dev/null | grep -c -i 'bink'
  print -n "x264/videotoolbox: "; ffmpeg -hide_banner -encoders 2>/dev/null | grep -E 'libx264 |h264_videotoolbox' | tr '\n' ' '; print
  print -n "drawtext filter: "; ffmpeg -hide_banner -filters 2>/dev/null | grep -c drawtext
fi
git --version 2>&1
print "git credential helper: $(git config --global credential.helper 2>/dev/null)"
sec disk
df -h $COREHUB_ROOT 2>&1
sec revision9
ls -la $COREHUB_ROOT 2>&1
ls $COREHUB_ROOT/runtime 2>&1 | head
print; print "doctor finished"
