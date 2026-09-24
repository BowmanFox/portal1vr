#pragma once
#include "sdk/vector.h"

namespace GunEffects {
// GetEffectParameters calls GetAttachment, then FormatViewModelAttachment.
// A tracked attachment is already in the same world space as the rendered gun;
// retain that position across the native flat-screen FOV conversion.
class PositionScope {
    inline static thread_local PositionScope *active = nullptr;
    PositionScope *previous;
    Vector *output;
    Vector tracked;
    bool captured = false;
public:
    PositionScope(Vector& position, bool enabled)
        : previous(active), output(enabled ? &position : nullptr) { active = this; }
    ~PositionScope() { active = previous; }
    PositionScope(const PositionScope&) = delete;
    PositionScope& operator=(const PositionScope&) = delete;

    static void Capture(const Vector& position) {
        if (active && active->output == &position) {
            active->tracked = position;
            active->captured = true;
        }
    }
    bool Restore(Vector *nativePosition = nullptr) const {
        if (!captured) return false;
        if (nativePosition) *nativePosition = *output;
        *output = tracked;
        return true;
    }
};
}
