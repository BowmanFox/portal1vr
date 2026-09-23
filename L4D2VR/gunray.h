#pragma once
#include "handpose.h"

namespace GunRay {
// Use the muzzle's centerline, beginning at wrist depth. Starting at the muzzle
// itself could put the trace beyond a nearby wall penetrated by the viewmodel.
inline bool FromBarrel(const matrix3x4_t& barrel, const Vector& wrist,
                       Vector& origin, Vector& direction) {
    for (int r=0;r<3;++r) {
        if (!std::isfinite(wrist[r])) return false;
        for (int c=0;c<4;++c) if (!std::isfinite(barrel[r][c])) return false;
    }
    direction = {barrel[0][0],barrel[1][0],barrel[2][0]};
    const float length = sqrtf(direction.LengthSqr());
    if (!std::isfinite(length) || length < 1e-6f) return false;
    direction *= 1.0f/length;
    const Vector muzzle(barrel[0][3],barrel[1][3],barrel[2][3]);
    const Vector delta = muzzle-wrist;
    const float depth = delta.x*direction.x+delta.y*direction.y+delta.z*direction.z;
    origin = muzzle-direction*depth;
    return true;
}
}
