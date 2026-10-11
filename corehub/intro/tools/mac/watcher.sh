#!/bin/zsh
# Corehub intro request watcher (macOS).
#
# Niko starts it once in Terminal and leaves the window open:
#     zsh ~/Games/revision9/mac/start.sh
#
# Claude queues work by writing a small request file
#     revision9/requests/<type>-<name>.req      (contents = arguments)
# and this loop runs the matching pipeline script
#     revision9/mac/handlers/<type>.sh <arguments>
# natively on the Mac (CrossOver/Wine compilers, the game, ffmpeg, git).
# Output goes to revision9/requests/<type>-<name>.log, ending in a DONE line.
#
# It only runs scripts from revision9/mac/handlers, one at a time.
# Stop it with Ctrl+C, by closing the window, or by creating requests/STOP.
emulate -R zsh
setopt null_glob extended_glob
ROOT=${0:A:h:h}
REQ=$ROOT/requests
HANDLERS=$ROOT/mac/handlers
mkdir -p $REQ
export COREHUB_ROOT=$ROOT
export PATH="$HOME/.homebrew/bin:/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin:$PATH"

LOCK=$REQ/.watcher.pid
if [[ -f $LOCK ]] && kill -0 "$(<$LOCK)" 2>/dev/null; then
  print "The Corehub watcher is already running (pid $(<$LOCK)). Nothing to do."
  exit 0
fi
print $$ > $LOCK
rm -f $REQ/STOP $REQ/.busy
cleanup() { rm -f $LOCK $REQ/.busy }
trap 'cleanup; exit 0' INT TERM HUP
# Keep the Mac and its display awake while the watcher runs.
if (( $+commands[caffeinate] )); then caffeinate -dims -w $$ &! ; fi

print "Corehub watcher started $(date). Watching $REQ"
print "Leave this window open. Ctrl+C or closing it stops the watcher."
while true; do
  if [[ -e $REQ/STOP ]]; then print "STOP file found - watcher stopped."; break; fi
  date -u +%Y-%m-%dT%H:%M:%SZ > $REQ/.heartbeat
  for f in $REQ/*.req(Om); do
    name=${f:t:r}
    type=${name%%-*}
    args="$(<$f)"
    rm -f $f
    log=$REQ/$name.log
    print -r -- "START $(date -u +%Y-%m-%dT%H:%M:%SZ) $args" > $log
    print -r -- "$(date +%H:%M:%S) $name $args"
    if [[ $type != [a-z][a-z0-9_]# ]]; then
      print "REJECTED request type" >> $log
    elif [[ ! -f $HANDLERS/$type.sh ]]; then
      print "UNKNOWN request type $type" >> $log
    else
      print -r -- $name > $REQ/.busy
      ( cd $ROOT && REQ_NAME=$name REQ_ARGS=$args zsh $HANDLERS/$type.sh ${(Q)${(z)args}} ) >> $log 2>&1
      print "EXIT $?" >> $log
      rm -f $REQ/.busy
    fi
    print "DONE $(date -u +%Y-%m-%dT%H:%M:%SZ)" >> $log
    print -r -- "$(date +%H:%M:%S) $name done"
    date -u +%Y-%m-%dT%H:%M:%SZ > $REQ/.heartbeat
  done
  sleep 2
done
cleanup
