#!/bin/zsh
# stage: puts a generated test build in place for compiling.
#   - copies r10/gen/out/build/corehub_<name>.vmf and director_<name>.nut to r10/build/
#   - copies the generated materials (r10/gen/out/materials, r10/mod-src/materials) into the corehub_intro mod folder
#   - compiles the generated model sources (r10/gen/out/models-src/*.qc) that are newer than their compiled model
# usage: stage <build name> <director name> [-AllModels]
source ${0:A:h:h}/env.sh
build=$1; dirn=$2; all=0
[[ $3 == -AllModels ]] && all=1
G=$R10/gen/out
for f in $G/build/$build.vmf $G/build/$dirn.nut; do
  [[ -f $f ]] || { print "missing $f"; exit 2 }
  cp $f $R10/build/ && print "staged ${f:t}"
done
n=0
for src in $R10/mod-src/materials $G/materials; do
  [[ -d $src ]] || continue
  /usr/bin/rsync -a $src/ $MOD/materials/ && n=$(( n + $(find $src -type f | wc -l) ))
done
print "materials copied: $n files"
qcs=()
for qc in $G/models-src/*.qc; do
  mdl=$MOD/models/corehub_intro/${qc:t:r}.mdl
  smd=${qc:r}.smd
  if (( all )) || [[ ! -f $mdl || $qc -nt $mdl || $smd -nt $mdl ]]; then qcs+=($qc); fi
done
if (( $#qcs )); then
  print "compiling $#qcs models"
  zsh ${0:A:h}/model.sh $qcs || exit 3
else
  print "models up to date"
fi
