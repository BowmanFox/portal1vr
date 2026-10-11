#!/bin/zsh
# cycle: one full build cycle for a test build: compile, pack, record the 60 fps test run and assemble the videos.
# usage: cycle <build name> <director name> <movie prefix> [-NoCompile] [-End <seconds>] [-Full]
#   e.g. cycle corehub_r10dq director_r10dq r10m_dq
source ${0:A:h:h}/env.sh
build=$1; dirn=$2; prefix=$3; shift 3
nocompile=0; endarg=(); full=()
while (( $# )); do
  case $1 in
    -NoCompile) nocompile=1 ;;
    -End) shift; endarg=(-End $1) ;;
    -Full) full=(-Full) ;;
  esac
  shift
done
H=${0:A:h}
if (( ! nocompile )); then
  zsh $H/compile.sh $build $full || { print "CYCLE stopped: compile failed"; exit 3 }
  grep -q "seconds elapsed" $R10/build/$build.log || { print "CYCLE stopped: no 'seconds elapsed' in the compile log"; exit 3 }
  zsh $H/pack.sh $build $dirn || { print "CYCLE stopped: pack failed"; exit 4 }
fi
zsh $H/movie.sh -Prefix $prefix -Fps 60 -Quality 90 -Bsp $R10/build/$build.bsp -Director $R10/build/$dirn.nut $endarg || { print "CYCLE stopped: movie failed"; exit 5 }
print "CYCLE complete $build $dirn $prefix $(stamp)"
