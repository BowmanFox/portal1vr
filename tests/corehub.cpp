#include "corehub_abi.h"
#include <cassert>
#include <cstring>
#include <cstdio>
using namespace Corehub;
int main() {
 // The native function consumes two views. Both must use the eye extent;
 // desktop dimensions must not leak into the overlay's viewport stack entry.
 View desktop{},overlay{};desktop.width=overlay.width=1280;desktop.height=overlay.height=720;
 desktop.fov=73.7f;desktop.farZ=4096;overlay.ortho=true;
 desktop.remaining[100]=0x24;desktop.remaining[103]=0x73;
 const auto saved=desktop,savedOverlay=overlay;
 auto left=PrepareEyeViews(desktop,overlay,2352,2352,104,1,{0,1.25f,64},{2,30,0});
 auto right=PrepareEyeViews(desktop,overlay,2352,2352,104,1,{0,-1.25f,64},{2,30,0});
 for(auto* eye:{&left,&right}) {
  assert(eye->world.width==2352 && eye->world.height==2352);
  assert(eye->overlay.width==2352 && eye->overlay.height==2352);
  assert(eye->world.x==0 && eye->overlay.y==0 && eye->overlay.ortho);
  assert(eye->world.farZ==4096 && eye->world.remaining[100]==0x20 && eye->world.remaining[103]==0x73);
 }
 assert(left.world.origin.y-right.world.origin.y==2.5f);
 // Native writes to one eye must not alter the other eye or desktop snapshots.
 left.world.width=320;left.overlay.height=240;
 assert(right.world.width==2352 && right.overlay.height==2352);
 assert(!memcmp(&desktop,&saved,sizeof(View)) && !memcmp(&overlay,&savedOverlay,sizeof(View)));
 auto wide=PrepareEyeViews(desktop,overlay,1800,1600,100,1.125f,{},{ });
 assert(wide.world.width==1800 && wide.overlay.height==1600 && wide.overlay.aspect==1.125f);
 puts("Corehub stereo viewport and independent-view regression checks passed.");
}
