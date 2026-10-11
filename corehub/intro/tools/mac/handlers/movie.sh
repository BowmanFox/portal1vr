#!/bin/zsh
# movie: records a continuous test run of a build with the automatic reference camera (no input needed), using the
# game's own startmovie at a fixed frame rate plus the in-game soundtrack, then assembles the videos (assemble.sh).
# usage: movie -Prefix <name> [-Fps 60] [-Width 1280] [-Height 800] [-End 134.4] [-Quality 90] [-Bsp <bsp>] [-Director <nut>]
#              [-NoAssemble] [-Map <mapname>] [-Extra "<more launch args>"]
# The normal mapspawn/autoexec/director are restored afterwards.
source ${0:A:h:h}/env.sh
prefix=""; fps=60; width=1280; height=800; endt=134.4; quality=90; bsp=""; director=""; assemble=1; map=corehub_intro; extra=()
while (( $# )); do
  case $1 in
    -Prefix) shift; prefix=$1 ;;
    -Fps) shift; fps=$1 ;;
    -Width) shift; width=$1 ;;
    -Height) shift; height=$1 ;;
    -End) shift; endt=$1 ;;
    -Quality) shift; quality=$1 ;;
    -Bsp) shift; bsp=$1 ;;
    -Director) shift; director=$1 ;;
    -Map) shift; map=$1 ;;
    -Extra) shift; extra=(${(z)1}) ;;
    -NoAssemble) assemble=0 ;;
  esac
  shift
done
[[ -n $prefix ]] || { print "need -Prefix"; exit 2 }
[[ $prefix == [A-Za-z0-9_]## ]] || { print "bad prefix"; exit 2 }
[[ -z $bsp ]] && bsp=$OUTPUTS/corehub_intro.bsp
[[ $bsp == /* ]] || bsp=$R/$bsp
[[ -n $director && $director != /* ]] && director=$R/$director
[[ -f $bsp ]] || { print "missing bsp $bsp"; exit 2 }
normal=$R10/normal-runtime
log=$MOD/console.log
moviedir=$MOD/movies/$prefix
loose=$MOD/scripts/vscripts/p9_walkable_v47c/director.nut
mkdir -p $MOD/maps $MOD/cfg $MOD/scripts/vscripts/p9_walkable_v47c $normal

$CXBIN/wineserver -k 2>/dev/null; sleep 1
cp $bsp $MOD/maps/$map.bsp
# The engine loads the loose director ahead of the copy packed in the BSP, so a test run puts its own there.
[[ ! -f $normal/director.loose.nut && -f $loose ]] && cp $loose $normal/director.loose.nut
if [[ -n $director ]]; then cp $director $loose; print "director $director"; fi
[[ -d $moviedir ]] && rm -rf $moviedir
mkdir -p $moviedir
rm -f $log

cat > $MOD/scripts/vscripts/mapspawn.nut <<NUT
// Movie test run: automatic reference camera, fixed-step recording. Private workspace only.
movD<-null;movStarted<-false;movPrefix<-"$prefix";
EntFire("intro_director","RunScriptCode","qaReferenceOpening=true;qaMouseLock=true",0.2);
function MovieTick(){
 if(movD==null){local d=Entities.FindByName(null,"intro_director");if(d!=null){d.ValidateScriptScope();movD=d.GetScriptScope();movD.qaReferenceOpening=true;movD.qaMouseLock=true;}}
 if(movD==null||!movD.started){EntFire("worldspawn","RunScriptCode","MovieTick()",0.01);return;}
 local p=movD.player;
 if(!movStarted){
  movStarted=true;
  EntFire("intro_client","Command","cl_mouseenable 0;cl_drawhud 0;r_drawviewmodel 0;con_notifytime 0;developer 0;hud_saytext_time 0;startmovie movies/$prefix/f jpg wav jpeg_quality $quality $quality $quality $quality",0,p);
  printl("MOVIE_BEGIN "+movPrefix+" world="+Time()+" start="+movD.startTime);
 }
 local t=Time()-movD.startTime;
 if(t>=$endt){
  printl("MOVIE_COMPLETE "+movPrefix+" t="+t);
  EntFire("intro_client","Command","endmovie",0,p);
  EntFire("intro_client","Command","quit",2.0,p);
  return;
 }
 EntFire("worldspawn","RunScriptCode","MovieTick()",0.05);
}
EntFire("worldspawn","RunScriptCode","MovieTick()",0.3);
NUT
print -l "con_enable 1" "cl_forcepreload 1" "mat_queue_mode 0" "cl_mouseenable 0" "sv_cheats 1" "host_framerate $fps" "jpeg_quality $quality" "snd_mute_losefocus 0" "mat_motion_blur_enabled 0" "engine_no_focus_sleep 0" > $MOD/cfg/autoexec.cfg

restore() {
  $CXBIN/wineserver -k 2>/dev/null
  [[ -f $normal/mapspawn.nut ]] && cp $normal/mapspawn.nut $MOD/scripts/vscripts/mapspawn.nut || rm -f $MOD/scripts/vscripts/mapspawn.nut
  [[ -f $normal/autoexec.cfg ]] && cp $normal/autoexec.cfg $MOD/cfg/autoexec.cfg || rm -f $MOD/cfg/autoexec.cfg
  [[ -n $director && -f $normal/director.loose.nut ]] && cp $normal/director.loose.nut $loose
  [[ -f $log ]] && cp $log $moviedir/console.log
  print "normal runtime restored"
}
trap 'restore; exit 9' INT TERM

cd $GAME
export SteamAppId=380 SteamGameId=380
print "launch $(stamp)"
$WINE --bottle $CX_BOTTLE --no-gui --no-convert --no-wait --cx-log $moviedir/wine.log hl2.exe -game corehub_intro -tempcontent -insecure -windowed -noborder -w $width -h $height -x 0 -y 0 -novid -condebug -conclearlog -ip 127.0.0.1 -port 27029 +mat_queue_mode 0 +maxplayers 1 +host_framerate $fps +engine_no_focus_sleep 0 $extra +map $map > $moviedir/launch.out 2>&1
t0=$SECONDS; seen=0; last=-1; stall=0; done=0; failed=0; begun=0
while true; do
  sleep 5
  [[ -f $log ]] && grep -q "MOVIE_COMPLETE $prefix" $log && done=1
  [[ -f $log ]] && grep -q "FAILED to compile and execute script" $log && failed=1
  [[ -f $log && $begun == 0 ]] && grep -q "MOVIE_BEGIN" $log && { begun=1; print "recording began after $(( SECONDS - t0 )) s" }
  alive=0; pgrep -f 'hl2\.exe' > /dev/null && alive=1
  (( alive )) && seen=1
  count=$(ls $moviedir 2>/dev/null | grep -c '\.jpg$')
  if (( count != last )); then last=$count; stall=0; else (( stall += 5 )); fi
  (( done || failed )) && break
  (( seen && ! alive )) && { print "game exited"; break }
  (( ! seen && SECONDS - t0 > 180 )) && { print "game never started"; break }
  (( stall > 600 )) && { print "stalled at $count frames"; break }
  (( SECONDS - t0 > 14400 )) && { print "deadline"; break }
done
sleep 6
count=$(ls $moviedir 2>/dev/null | grep -c '\.jpg$')
print "frames $count after $(( SECONDS - t0 )) s"
restore
trap - INT TERM
if (( failed )); then print "A map script failed to compile; see console.log."; grep -n -B2 -A6 "FAILED to compile" $moviedir/console.log | head -40; exit 3; fi
if (( ! done )); then print "Movie did not complete."; tail -40 $moviedir/console.log 2>/dev/null; print "--- wine log tail"; tail -30 $moviedir/wine.log 2>/dev/null; exit 4; fi
(( assemble )) && zsh ${0:A:h}/assemble.sh -Prefix $prefix -Fps $fps
