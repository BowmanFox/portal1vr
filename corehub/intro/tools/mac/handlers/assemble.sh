#!/bin/zsh
# assemble: turns a recorded test run into videos and stills.
#   r10/videos/<Prefix>_map.mp4         full-size rebuild with in-game audio
#   r10/videos/<Prefix>_side.mp4        original video | rebuild, in-game audio
#   r10/videos/<Prefix>_side_small.mp4  small copy for sending
#   r10/stills/<Prefix>/a###.jpg, b###.jpg   frames at t = s and s + 0.5 for scoring
# usage: assemble -Prefix <name> [-Fps 60]
source ${0:A:h:h}/env.sh
prefix=""; fps=60
while (( $# )); do
  case $1 in
    -Prefix) shift; prefix=$1 ;;
    -Fps) shift; fps=$1 ;;
  esac
  shift
done
M=$MOD/movies/$prefix; O=$R10/videos; S=$R10/stills/$prefix
ref=$GAME/portal2/media/p2_intro.bik
A=$R/mac/assets
[[ -f $M/f0000.jpg ]] || { print "no frames in $M"; exit 2 }
mkdir -p $O $S
audio=(); amap=()
if [[ -f $M/f.wav ]]; then audio=(-i $M/f.wav); fi
n=$(ls $M | grep -c '\.jpg$')
print "frames $n"
ffmpeg -y -hide_banner -loglevel error -framerate $fps -i $M/f%04d.jpg $audio \
  -vf 'scale=1280:720:flags=lanczos,format=yuv420p' -c:v libx264 -preset medium -crf 19 ${audio:+-c:a} ${audio:+aac} ${audio:+-b:a} ${audio:+192k} -shortest $O/${prefix}_map.mp4 || print "map video FAILED"
# side by side: labels and the per-second clock are pre-rendered images (this ffmpeg has no drawtext)
fc="[0:v]setpts=N/(30000/1001)/TB,fps=$fps,scale=960:540[a0];[a0][3:v]overlay=12:10[a];[1:v]scale=960:540:flags=lanczos[b0];[b0][4:v]overlay=12:10[b1];[b1][5:v]overlay=W-w-12:10[b];[a][b]hstack=inputs=2,format=yuv420p[v]"
if [[ -n $audio ]]; then am=(-map 2:a -c:a aac -b:a 160k); else am=(); fi
if [[ -f $A/label_original.png && -f $A/clock/c000.png ]]; then
  if [[ -n $audio ]]; then
    ffmpeg -y -hide_banner -loglevel error -i $ref -framerate $fps -i $M/f%04d.jpg -i $M/f.wav -i $A/label_original.png -i $A/label_rebuild.png -framerate 1 -i $A/clock/c%03d.png \
      -filter_complex $fc -map '[v]' $am -c:v libx264 -preset medium -crf 21 -shortest $O/${prefix}_side.mp4 || print "side video FAILED"
  else
    fc2=${fc//\[3:v\]/[2:v]}; fc2=${fc2//\[4:v\]/[3:v]}; fc2=${fc2//\[5:v\]/[4:v]}
    ffmpeg -y -hide_banner -loglevel error -i $ref -framerate $fps -i $M/f%04d.jpg -i $A/label_original.png -i $A/label_rebuild.png -framerate 1 -i $A/clock/c%03d.png \
      -filter_complex $fc2 -map '[v]' -c:v libx264 -preset medium -crf 21 -shortest $O/${prefix}_side.mp4 || print "side video FAILED"
  fi
else
  print "label images missing, side video without labels"
  ffmpeg -y -hide_banner -loglevel error -i $ref -framerate $fps -i $M/f%04d.jpg $audio \
    -filter_complex "[0:v]setpts=N/(30000/1001)/TB,fps=$fps,scale=960:540[a];[1:v]scale=960:540:flags=lanczos[b];[a][b]hstack=inputs=2,format=yuv420p[v]" -map '[v]' ${audio:+-map} ${audio:+2:a} -c:v libx264 -preset medium -crf 21 -shortest $O/${prefix}_side.mp4 || print "side video FAILED"
fi
[[ -f $O/${prefix}_side.mp4 ]] && ffmpeg -y -hide_banner -loglevel error -i $O/${prefix}_side.mp4 -vf fps=30,scale=1600:450 -c:v libx264 -preset medium -crf 26 -c:a aac -b:a 96k $O/${prefix}_side_small.mp4
for (( s = 0; s <= 134; s++ )); do
  i=$(( s * fps )); (( i < n )) && cp $M/$(printf 'f%04d.jpg' $i) $S/$(printf 'a%03d.jpg' $s)
  i=$(( s * fps + fps / 2 )); (( i < n )) && cp $M/$(printf 'f%04d.jpg' $i) $S/$(printf 'b%03d.jpg' $s)
done
ls -la $O/${prefix}_*.mp4
print "assembled $prefix frames=$n"
