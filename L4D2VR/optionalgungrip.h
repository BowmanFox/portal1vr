#pragma once
#include "handpose.h"
#include <cstddef>
#include <cstdint>
#include <cstring>

namespace OptionalGunGrip {
// A fresh squeeze near the socket is intentional; merely moving a closed hand
// past the weapon must not capture it. Pulling away always releases the hand.
struct State {
    bool active = false;
    bool wasPressed = false;
    bool Update(bool enabled, bool tracked, bool fresh, bool pressed,
                float distance, float radius) {
        const bool rising = pressed && !wasPressed;
        wasPressed = pressed;
        if (!enabled || !tracked || !fresh || !pressed || !std::isfinite(distance)
            || !std::isfinite(radius) || radius <= 0 || distance > radius * 2.5f)
            active = false;
        else if (!active && rising && distance <= radius)
            active = true;
        return active;
    }
};

inline bool Squeeze(bool button, bool skeletonValid, const float *curl, bool previous) {
    if (button) return true;
    if (!skeletonValid) return false;
    float amount = 0;
    for (int i = 2; i < 5; ++i) {
        if (!std::isfinite(curl[i])) return false;
        amount += curl[i] / 3.0f;
    }
    return amount >= (previous ? 0.45f : 0.75f);
}

inline bool Finite(const matrix3x4_t& frame) {
    for (int i = 0; i < 3; ++i)
        for (int j = 0; j < 4; ++j)
            if (!std::isfinite(frame[i][j])) return false;
    return true;
}

// Source v48 attachment records are 92 bytes. Accept only our named socket on
// the weapon root, and check every range before reading this optional metadata.
inline bool ReadSocket(const unsigned char *hdr, size_t size, matrix3x4_t& local) {
    if (!hdr || size < 248) return false;
    auto integer = [&](size_t offset) { int v; std::memcpy(&v, hdr + offset, 4); return v; };
    if (integer(4) != 48 || integer(156) != 45) return false;
    const int count = integer(240), offset = integer(244);
    if (count < 1 || count > 256 || offset < 248 || size_t(offset) > size
        || size_t(count) > (size - size_t(offset)) / 92) return false;
    static const char wanted[] = "lefthand_grip";
    for (int i = 0; i < count; ++i) {
        const size_t record = size_t(offset) + size_t(i) * 92;
        const int nameOffset = integer(record);
        if (nameOffset <= 0 || size_t(nameOffset) > size - record) continue;
        const size_t name = record + size_t(nameOffset);
        if (sizeof(wanted) > size - name || std::memcmp(hdr + name, wanted, sizeof(wanted))) continue;
        if (integer(record + 8) != 24) return false;
        std::memcpy(&local, hdr + record + 12, sizeof(local));
        if (!Finite(local)) return false;
        for (int axis = 0; axis < 3; ++axis) {
            float norm = 0;
            for (int r = 0; r < 3; ++r) norm += local[r][axis] * local[r][axis];
            if (std::fabs(norm - 1.0f) > 0.01f || std::fabs(local[axis][3]) > 64) return false;
        }
        return true;
    }
    return false;
}
}
