#pragma once
#include "portalpose.h"
#include <cstddef>

namespace PortalShotFx {
// Installed Portal 1 CEffectData layout. The remaining fields include color,
// endpoint timing and entity identity; preserve them byte for byte.
struct Data {
    Vector origin, start, normal;
    QAngle angles;
    unsigned char remaining[0x58];
};
static_assert(sizeof(Data)==0x88);
static_assert(offsetof(Data,angles)==0x24);
inline bool Align(Data& effect,const matrix3x4_t& muzzle) {
    for(int r=0;r<3;++r) for(int c=0;c<4;++c)
        if(!std::isfinite(muzzle[r][c])) return false;
    const Vector forward(muzzle[0][0],muzzle[1][0],muzzle[2][0]);
    if(forward.LengthSqr()<1e-8f) return false;
    effect.origin=PortalPose::Position(muzzle);
    effect.angles=PortalPose::Angles(HandPose::RigidOrientation(muzzle));
    return true;
}
}
