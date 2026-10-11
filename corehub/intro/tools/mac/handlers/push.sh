#!/bin/zsh
# push: commits the current Corehub intro work to branch corehub-intro of BowmanFox/portal1vr and pushes it.
# Works in its own clone (r10/p1vr-intro); Niko's main portal1vr checkout is never touched.
# Never pushed: the BSP, videos, the reference video, the soundtrack, anything from the Valve build.
# usage: push [-NoPush] [-Message "text"]
source ${0:A:h:h}/env.sh
BRANCH=corehub-intro
REPO=https://github.com/BowmanFox/portal1vr.git
WT=$R10/p1vr-intro
nopush=0; msg=""
while (( $# )); do
  case $1 in
    -NoPush) nopush=1 ;;
    -Message) shift; msg=$1 ;;
  esac
  shift
done
export GIT_TERMINAL_PROMPT=0
# Niko's global git config rewrites https://github.com/ to SSH, and this Mac has no SSH key. For this clone only,
# git runs without the global config and gets its credential from the gh CLI Niko is already logged in with
# (the token never leaves gh/git; nothing here reads or stores it). His global config is not changed.
g() { GIT_CONFIG_GLOBAL=/dev/null git -c credential.helper= -c credential.helper='!/opt/homebrew/bin/gh auth git-credential' "$@" }
if [[ ! -d $WT/.git ]]; then
  print "cloning $BRANCH into $WT"
  g clone --quiet --branch $BRANCH --single-branch --depth 50 $REPO $WT || { print "clone FAILED"; exit 2 }
fi
cd $WT || exit 2
cur=$(g rev-parse --abbrev-ref HEAD)
[[ $cur == $BRANCH ]] || { print "clone is on $cur, expected $BRANCH"; exit 2 }
url=$(g remote get-url origin)
[[ ${url:l} == *bowmanfox/portal1vr* ]] || { print "unexpected remote $url"; exit 2 }
g pull --quiet --ff-only origin $BRANCH || print "pull skipped (not fast-forward)"

D=$WT/corehub/intro
mkdir -p $D/{map,wip,tools/mac/handlers,models/transport,materials/corehub_intro/r10,review,mod}
pub=(); wip=()
[[ -f $R10/PUBLISHED.txt ]] && pub=($(cat $R10/PUBLISHED.txt))   # build director movie
[[ -f $R10/WIP.txt ]] && wip=($(cat $R10/WIP.txt))               # build director
[[ -n $pub[1] && -f $R10/build/$pub[1].vmf ]] && cp $R10/build/$pub[1].vmf $D/map/corehub_intro.vmf
[[ -n $pub[2] && -f $R10/build/$pub[2].nut ]] && cp $R10/build/$pub[2].nut $D/map/director.nut
if [[ -n $wip[1] && -f $R10/build/$wip[1].vmf ]]; then
  cp $R10/build/$wip[1].vmf $D/wip/corehub_intro_wip.vmf
  [[ -f $R10/build/$wip[2].nut ]] && cp $R10/build/$wip[2].nut $D/wip/director_wip.nut
  print "Newest test build: $wip[1] + $wip[2]. Published build (map\\): $pub[1] + $pub[2]." > $D/wip/BUILD.txt
fi
for f in $R10/*.py $R10/tools/*.py; do cp $f $D/tools/; done
for f in $R/mac/*.sh $R/mac/*.py $R/mac/*.json $R/mac/*.md; do cp $f $D/tools/mac/; done
for f in $R/mac/handlers/*.sh; do cp $f $D/tools/mac/handlers/; done
for f in $R10/models/*.(qc|smd|py); do cp $f $D/models/; done
for f in $R/transport-models/*.(qc|smd|py); do cp $f $D/models/transport/; done
for f in $MOD/materials/corehub_intro/r10/*.(vmt|vtf); do cp $f $D/materials/corehub_intro/r10/; done
[[ -f $R10/STATUS.md ]] && cp $R10/STATUS.md $D/README.md
for f in $R10/review/*.jpg; do cp $f $D/review/; done
# The rebuilt (non-Valve) mod content: our own materials, model sources' compiled output and scripts.
if [[ -d $R10/mod-src ]]; then
  /usr/bin/rsync -a --exclude '*.bsp' --exclude '*.bik' --exclude '*.wav' --exclude '*.mp3' --exclude '*.mp4' --exclude '*.vpk' --exclude 'sound/' --exclude 'movies/' --exclude 'maps/' $R10/mod-src/ $D/mod/
fi
# Safety net: nothing from the Valve build or the reference video may be staged.
bad=$(cd $D && find . \( -name '*.bsp' -o -name '*.bik' -o -name '*.wav' -o -name '*.mp3' -o -name '*.mp4' -o -name '*.vpk' -o -name '*.exe' -o -name '*.dll' \) | head -5)
if [[ -n $bad ]]; then print "REFUSING to commit, found:\n$bad"; exit 3; fi
big=$(cd $D && find . -type f -size +40M | head -5)
if [[ -n $big ]]; then print "REFUSING to commit, file over 40 MB:\n$big"; exit 3; fi

g add -A -- corehub/intro
if g diff --cached --quiet; then
  print "no changes since the last commit"
else
  [[ -z $msg ]] && msg="Corehub intro rebuild ($pub[1] + $pub[2]; newest test ${wip[1]#corehub_})"
  g -c user.name='Niko (via Claude)' -c user.email='awesomeguy3612@gmail.com' commit -q -m "$msg" \
    -m "Mac pipeline; see corehub/intro/README.md for per-scene scores." \
    -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_016YSCvamikJTTDXFothpCe2" || { print "commit FAILED"; exit 4 }
  g log --oneline -1
  g show --stat --format= HEAD | tail -15
fi
if (( nopush )); then print "COMMITTED (no push requested)"; exit 0; fi
if g push --quiet origin HEAD:refs/heads/$BRANCH 2>&1; then
  print "PUSHED $BRANCH to $url at $(stamp)"
  stamp > $R10/LAST_PUSH.txt
else
  print "git push FAILED"; exit 5
fi
