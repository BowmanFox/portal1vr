#!/bin/zsh
# pack: packs the files in mac/packlist.txt (the director under test and the overlay materials) into a compiled BSP
# with the build's own bspzip.
# usage: pack <build name> <director name>      e.g. pack corehub_r10dm director_r10dm
source ${0:A:h:h}/env.sh
name=$1; dirname=$2
bsp=$R10/build/$name.bsp; nut=$R10/build/$dirname.nut
[[ -f $bsp ]] || { print "missing $bsp"; exit 2 }
[[ -f $nut ]] || { print "missing $nut"; exit 2 }
list=$R10/build/$name.packlist.txt
: > $list
n=0
while IFS=$'\t' read -r internal src; do
  [[ -z $internal || $internal == \#* ]] && continue
  if [[ $src == @DIRECTOR@ ]]; then f=$nut; else f=$MOD/$src; fi
  [[ -f $f ]] || { print "pack source missing: $f"; exit 3 }
  print -r -- "$internal" >> $list
  print -r -- "$(winpath $f)" >> $list
  (( n++ ))
done < $R/mac/packlist.txt
cd $GAME/bin || exit 2
export VPROJECT=$(winpath $MOD)
tmp=$R10/build/$name.packed.bsp
rm -f $tmp
$WINE --bottle $CX_BOTTLE --no-gui --no-convert bspzip.exe -addlist "$(winpath $bsp)" "$(winpath $list)" "$(winpath $tmp)" 2>&1 | tr -d '\r' | tail -8
[[ -s $tmp ]] || { print "bspzip wrote nothing"; exit 4 }
mv -f $tmp $bsp
print "packed $n files into $bsp ($(stat -f %z $bsp) bytes)"
$WINE --bottle $CX_BOTTLE --no-gui --no-convert bspzip.exe -dir "$(winpath $bsp)" 2>&1 | tr -d '\r' | grep -c -i -E 'director|glare|flick' | sed 's/^/pak entries listed: /'
