#!/bin/zsh
# bottle: creates the CrossOver bottle "Corehub" for the compilers and the game if it does not exist yet,
# then reports its status and runs a trivial console command in it. Other bottles are not touched.
source ${0:A:h:h}/env.sh
if [[ ! -d $BOTTLE_DIR ]]; then
  print "creating bottle $CX_BOTTLE (win10_64)"
  $CXBIN/cxbottle --bottle $CX_BOTTLE --create --template win10_64 --description "Corehub intro rebuild (Source 2009 build)" 2>&1 | tail -20
  print "create exit $?"
else
  print "bottle $CX_BOTTLE exists"
fi
$CXBIN/cxbottle --bottle $CX_BOTTLE --status 2>&1 | head -20
ls -la $BOTTLE_DIR 2>&1 | head -20
print "== console test"
( cd $R && $WINE --bottle $CX_BOTTLE --no-gui cmd /c "ver & echo hello from wine & cd" ) 2>&1 | tail -8
print "console test exit $?"
print "== dosdevices"; ls -la $BOTTLE_DIR/dosdevices 2>&1
