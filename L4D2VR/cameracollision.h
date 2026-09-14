#pragma once
#include "vector.h"
#include <algorithm>
#include <cmath>

namespace CameraCollision {
    constexpr float NearClip = 1.0f;
    constexpr float SurfaceMargin = 0.25f;

    inline float HullRadius(float eyeSeparation, float horizontalFov, float aspect) {
        // Enclose both eyes AND their near-plane corners, at any head rotation.
        const float tangent = std::tan(DEG2RAD(std::clamp(horizontalFov, 30.0f, 170.0f)) * 0.5f);
        const float vertical = tangent / std::max(aspect, 0.25f);
        return std::abs(eyeSeparation) * 0.5f
            + NearClip * std::sqrt(1.0f + tangent * tangent + vertical * vertical)
            + SurfaceMargin;
    }

    inline Vector Constrain(const Vector& start, const Vector& desired,
                            float fraction, bool startSolid, bool allSolid) {
        if (startSolid || allSolid || !std::isfinite(fraction))
            return start;
        if (fraction >= 1.0f)
            return desired;
        const Vector delta = desired - start;
        const float length = std::sqrt(delta.LengthSqr());
        if (length < 0.0001f)
            return start;
        const float safeFraction = std::clamp(fraction - SurfaceMargin / length, 0.0f, 1.0f);
        return start + delta * safeFraction;
    }
}
