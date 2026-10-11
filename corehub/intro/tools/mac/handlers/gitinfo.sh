#!/bin/zsh
# gitinfo: read-only look at the git settings that affect cloning/pushing (no credentials are read or printed).
print "== url rewrites"; git config --show-origin --get-regexp '^url\.' 2>&1
print "== credential helpers"; git config --show-origin --get-all credential.helper 2>&1
print "== gh hosts protocol"; gh config get git_protocol 2>&1
print "== ssh keys present?"; ls ~/.ssh 2>/dev/null | grep -c -E '^id_' 
print "== test https ls-remote with gh helper (no rewrite)"
GIT_CONFIG_GLOBAL=/dev/null GIT_TERMINAL_PROMPT=0 git -c credential.helper= -c credential.helper='!/opt/homebrew/bin/gh auth git-credential' ls-remote --heads https://github.com/BowmanFox/portal1vr.git corehub-intro 2>&1 | head -3
print "== push permission (API)"; gh api repos/BowmanFox/portal1vr --jq '.permissions' 2>&1 | head -3
