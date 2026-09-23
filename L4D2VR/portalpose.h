#pragma once
#include "handpose.h"

namespace PortalPose {
inline matrix3x4_t Frame(const Vector& position, const QAngle& angles)
{
    Vector forward, right, up;
    QAngle::AngleVectors(angles, &forward, &right, &up);
    return HandPose::Frame(forward, -right, up, position);
}

inline Vector Position(const matrix3x4_t& frame)
{
    return {frame[0][3], frame[1][3], frame[2][3]};
}

inline QAngle Angles(const matrix3x4_t& frame)
{
    QAngle result;
    QAngle::VectorAngles({frame[0][0], frame[1][0], frame[2][0]},
        {frame[0][2], frame[1][2], frame[2][2]}, result);
    result.Normalize();
    return result;
}

// Store the hand in the sampled head frame. Rebuild it from the server's real
// eye pose, which may already be through a portal before the client is notified.
inline matrix3x4_t RelativeHand(const Vector& offset, const QAngle& hand,
    const QAngle& head)
{
    return HandPose::Concat(HandPose::InverseRigid(Frame({0,0,0}, head)), Frame(offset, hand));
}

inline matrix3x4_t WorldHand(const matrix3x4_t& relativeHand,
    const Vector& eye, const QAngle& head)
{
    return HandPose::Concat(Frame(eye, head), relativeHand);
}

inline float UprightYawDelta(const matrix3x4_t& portal, const QAngle& head)
{
    const auto before = Frame({0,0,0}, head);
    const auto after = HandPose::Concat(portal, before);
    // When forward becomes vertical (floor/ceiling portals), use the lateral
    // axis to preserve a finite heading while keeping the VR camera upright.
    const int axis = after[0][0]*after[0][0] + after[1][0]*after[1][0] > 0.0001f
        && before[0][0]*before[0][0] + before[1][0]*before[1][0] > 0.0001f ? 0 : 1;
    const float delta = RAD2DEG(atan2f(after[1][axis], after[0][axis])
        - atan2f(before[1][axis], before[0][axis]));
    return std::remainder(delta, 360.0f);
}
}
