#pragma once
#include "vector.h"
#include <cmath>

namespace PickupTrace {
// Only recover a missed use query when the hand is touching/inside the first
// reachable surface. The head-to-hand sweep must still reject walls and solids.
inline bool ContactQuery(const Vector& eye, const Vector& hand, float fraction,
    bool startSolid, bool allSolid, Vector& origin, QAngle& angles)
{
    const Vector delta = hand - eye;
    const float length = sqrtf(delta.LengthSqr());
    if (startSolid || allSolid || !std::isfinite(length) || length < 1.0f
        || !std::isfinite(fraction) || fraction <= 0.0f || fraction >= 1.0f
        || length * (1.0f - fraction) > 24.0f)
        return false;
    const Vector direction = delta / length;
    const float beforeContact = fmaxf(0.0f, length * fraction - 2.0f);
    origin = eye + direction * beforeContact;
    angles = {RAD2DEG(atan2f(-direction.z, sqrtf(direction.x*direction.x + direction.y*direction.y))),
        RAD2DEG(atan2f(direction.y, direction.x)), 0};
    return true;
}
}
