#!/bin/zsh
# Starts the Corehub intro request watcher in this Terminal window.
# Usage:  zsh ~/Games/revision9/mac/start.sh
# Also starts the 30-minute push loop (it only queues push requests for the watcher; see handlers/autopush.sh).
zsh ${0:A:h}/handlers/autopush.sh start
exec zsh ${0:A:h}/watcher.sh
