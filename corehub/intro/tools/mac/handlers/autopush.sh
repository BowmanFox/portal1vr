#!/bin/zsh
# autopush: background loop that queues a push request every 30 minutes (the handoff's push rule).
# It only drops requests/push-auto-HHMM.req files; the watcher runs them one at a time like any other request.
# The loop ends when the watcher is gone, or after the first push queued once r10/FINALIZED exists (the last push).
# usage: autopush [start|stop|status] [-Every seconds]
source ${0:A:h:h}/env.sh
PIDF=$R/requests/.autopush.pid
cmd=start; every=1800
while (( $# )); do
  case $1 in
    start|stop|status) cmd=$1 ;;
    -Every) shift; every=$1 ;;
  esac
  shift
done
running() { [[ -f $PIDF ]] && kill -0 "$(<$PIDF)" 2>/dev/null }
case $cmd in
  status)
    if running; then print "autopush running (pid $(<$PIDF))"; else print "autopush not running"; fi
    [[ -f $R10/LAST_PUSH.txt ]] && print "last push $(<$R10/LAST_PUSH.txt)"
    ;;
  stop)
    if running; then kill "$(<$PIDF)"; rm -f $PIDF; print "autopush stopped"; else print "autopush was not running"; fi
    ;;
  start)
    if running; then print "autopush already running (pid $(<$PIDF))"; exit 0; fi
    COREHUB_ROOT=$R EVERY=$every nohup zsh -c '
      R=$COREHUB_ROOT
      while true; do
        sleep $EVERY
        [[ -f $R/requests/.watcher.pid ]] && kill -0 "$(<$R/requests/.watcher.pid)" 2>/dev/null || break
        : > $R/requests/push-auto-$(date -u +%H%M).req
        [[ -e $R/r10/FINALIZED ]] && break
      done
      rm -f $R/requests/.autopush.pid' >/dev/null 2>&1 &!
    print $! > $PIDF
    print "autopush started (pid $(<$PIDF)), every $every s"
    ;;
esac
