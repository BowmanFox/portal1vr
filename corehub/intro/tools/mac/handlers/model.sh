#!/bin/zsh
# model: compiles model sources (QC + SMD) with the build's own studiomdl into the corehub_intro mod folder.
# usage: model <qc file or folder> [more ...]     paths relative to revision9/ (e.g. transport-models r10/models/scanner_board.qc)
source ${0:A:h:h}/env.sh
export VPROJECT=$(winpath $MOD)
qcs=()
for a in "$@"; do
  [[ $a == /* ]] || a=$R/$a
  if [[ -d $a ]]; then qcs+=($a/*.qc); else qcs+=($a); fi
done
ok=0; bad=0
mkdir -p $R10/build/modellogs
for qc in $qcs; do
  [[ -f $qc ]] || { print "missing $qc"; (( bad++ )); continue }
  log=$R10/build/modellogs/${qc:t:r}.log
  ( cd ${qc:h} && $WINE --bottle $CX_BOTTLE --no-gui --no-convert "$(winpath $GAME/bin/studiomdl.exe)" -game "$VPROJECT" -nop4 -nox360 "${qc:t}" ) 2>&1 | tr -d '\r' > $log
  mdl=$(grep -i -m1 '^\$modelname' $qc | sed -E 's/^\$modelname[[:space:]]+"?([^"]+)"?.*/\1/' | tr '\\' '/')
  if [[ -n $mdl && -f $MOD/models/$mdl && $MOD/models/$mdl -nt $qc ]] || grep -q -i "Completed" $log; then
    (( ok++ ))
  else
    (( bad++ )); print "FAILED ${qc:t}:"; tail -6 $log
  fi
done
print "models compiled $ok, failed $bad"
ls $MOD/models/corehub_intro 2>/dev/null | grep -c '\.mdl$' | sed 's/^/mdl files in mod: /'
