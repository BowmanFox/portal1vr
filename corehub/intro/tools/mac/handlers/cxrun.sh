#!/bin/zsh
# cxrun: runs one Windows program from Niko's Corehub build (or the bottle) in the Corehub bottle and logs its output.
# usage: cxrun [-Dir <native working dir>] [-Timeout <seconds>] [-Env "A=1 B=2"] -- <exe> [args...]
source ${0:A:h:h}/env.sh
dir=$GAME; tmo=1800; envs=()
while (( $# )); do
  case $1 in
    -Dir) shift; dir=$1 ;;
    -Timeout) shift; tmo=$1 ;;
    -Env) shift; envs=(${(z)1}) ;;
    --) shift; break ;;
  esac
  shift
done
[[ -d $dir ]] || { print "no such dir $dir"; exit 2 }
cd $dir
print "cwd $PWD"; print -r -- "run $@"
( env $envs $WINE --bottle $CX_BOTTLE --no-gui "$@" ) 2>&1 &
pid=$!
( sleep $tmo; print "TIMEOUT after $tmo s"; kill $pid 2>/dev/null; $CXBIN/wineserver -k 2>/dev/null ) &
killer=$!
wait $pid; rc=$?
kill $killer 2>/dev/null
print "program exit $rc"
exit $rc
