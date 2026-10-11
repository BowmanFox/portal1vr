#!/bin/zsh
# compile: builds r10/build/<name>.vmf into <name>.bsp with the Corehub build's own vbsp, vvis and vrad (in CrossOver).
# usage: compile <name> [-NoVis] [-NoRad] [-Full] [-OnlyEnts]
# The full output goes to r10/build/<name>.log; each tool's "seconds elapsed" line shows it finished.
source ${0:A:h:h}/env.sh
name=$1; shift
novis=0; norad=0; fast=(-fast); onlyents=0
while (( $# )); do
  case $1 in
    -NoVis) novis=1 ;;
    -NoRad) norad=1 ;;
    -Full) fast=() ;;
    -OnlyEnts) onlyents=1 ;;
  esac
  shift
done
vmf=$R10/build/$name.vmf
[[ -f $vmf ]] || { print "missing $vmf"; exit 2 }
log=$R10/build/$name.log
: > $log
cd $GAME/bin || exit 2
export VPROJECT=$(winpath $MOD)
wbase=$(winpath $R10/build/$name)
tool() {
  local label=$1; shift
  print "== $label $(stamp)" | tee -a $log
  local t0=$SECONDS
  $WINE --bottle $CX_BOTTLE --no-gui --no-convert "$@" 2>&1 | tr -d '\r' >> $log
  local rc=${pipestatus[1]}
  print "== $label exit $rc after $(( SECONDS - t0 )) s" | tee -a $log
  return $rc
}
rm -f $R10/build/$name.bsp.tmp
if (( onlyents )); then
  tool vbsp vbsp.exe -onlyents -game "$VPROJECT" "$wbase" || exit 3
else
  tool vbsp vbsp.exe -game "$VPROJECT" "$wbase" || exit 3
  [[ -f $R10/build/$name.bsp ]] || { print "vbsp wrote no BSP"; tail -30 $log; exit 3 }
  (( novis )) || tool vvis vvis.exe $fast -game "$VPROJECT" "$wbase" || exit 4
  (( norad )) || tool vrad vrad.exe $fast -game "$VPROJECT" "$wbase" || exit 5
fi
print "== summary"
grep -n -i -E "seconds elapsed|^Error|error:|fatal|leaked|\*\*\*\* leaked|material not found|can.t find|could not|missing" $log | head -60
grep -c -i "material not found" $log | sed 's/^/material-not-found lines: /'
ls -la $R10/build/$name.bsp 2>&1
