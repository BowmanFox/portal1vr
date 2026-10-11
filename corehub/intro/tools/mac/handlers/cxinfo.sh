#!/bin/zsh
# cxinfo: read-only details about CrossOver's command-line tools and git/gh setup.
emulate -R zsh
setopt null_glob
CX=/Applications/CrossOver.app/Contents/SharedSupport/CrossOver
print "== wine --help"; $CX/bin/wine --help 2>&1 | head -80
print; print "== wine --version"; $CX/bin/wine --version 2>&1 | head -3
print; print "== cxbottle --help"; $CX/bin/cxbottle --help 2>&1 | head -70
print; print "== cxstart --help"; $CX/bin/cxstart --help 2>&1 | head -60
print; print "== templates"; ls $CX/share/crossover/bottle_templates 2>&1
print; print "== AnthroHeat bottle"; ls -la "$HOME/Library/Application Support/CrossOver/Bottles/AnthroHeat" 2>&1; grep -v -i -E 'serial|license|key' "$HOME/Library/Application Support/CrossOver/Bottles/AnthroHeat/cxbottle.conf" 2>&1 | head -60
print; print "== crossover prefs (names only)"; defaults read com.codeweavers.CrossOver 2>/dev/null | grep -v -i -E 'serial|license|key|token|password|email' | head -40
print; print "== lib dirs"; ls $CX/lib 2>&1 | head; ls $CX/lib/wine 2>&1 | head -20
print; print "== homebrew wine64"; ls -la /opt/homebrew/bin/wine64 2>&1; /opt/homebrew/bin/wine64 --version 2>&1 | head -2
print; print "== git"; git config --show-origin --get-all credential.helper 2>&1; git config --global user.name 2>&1
print "== gh"; gh --version 2>&1 | head -1; gh auth status 2>&1 | grep -v -i token
print; print "== fonts"; ls /System/Library/Fonts/Supplemental 2>/dev/null | grep -i -E 'arial' | head
print "== python"; ls /opt/homebrew/bin | grep -i -E '^python3|^pip3' | tr '\n' ' '; print; /usr/bin/python3 --version 2>&1; /usr/bin/python3 -c "import PIL, numpy; print('system python has PIL, numpy')" 2>&1 | tail -1
print "== screen"; system_profiler SPDisplaysDataType 2>/dev/null | grep -E 'Resolution|UI Looks like|Mirror|Refresh'
