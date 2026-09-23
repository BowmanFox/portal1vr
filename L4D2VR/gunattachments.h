#pragma once
#include "handpose.h"
#include <cstddef>
#include <cstdint>

namespace GunAttachments {
// Store model-local attachment metadata, never a previous eye's world positions.
// Queries use current tracking and the native animation bones, just like drawing.
struct Model {
    struct Attachment { int bone = -1; matrix3x4_t local; } attachments[256];
    int count = 0;
    matrix3x4_t gunFromController;

    bool Read(const unsigned char *hdr, size_t size, const matrix3x4_t *reference) {
        count = 0;
        if (!hdr || !reference || size < 248) return false;
        auto integer = [&](size_t offset) { int v; std::memcpy(&v,hdr+offset,4); return v; };
        if (integer(4) != 48 || integer(156) != 45
            || std::memcmp(hdr+12,"weapons/v_portalgun.mdl",sizeof("weapons/v_portalgun.mdl"))) return false;
        const int n = integer(240), offset = integer(244);
        if (n < 1 || n > 256 || offset < 248 || size_t(offset) > size
            || size_t(n) > (size-size_t(offset))/92) return false;
        for (int i=0; i<n; ++i) {
            const size_t record = size_t(offset)+size_t(i)*92;
            attachments[i].bone = integer(record+8);
            if (attachments[i].bone < 24 || attachments[i].bone >= 45) return false;
            std::memcpy(&attachments[i].local,hdr+record+12,sizeof(matrix3x4_t));
            for (int r=0;r<3;++r) for (int c=0;c<4;++c)
                if (!std::isfinite(attachments[i].local[r][c])) return false;
        }
        auto source = reference[24];
        for (int r=0;r<3;++r) source[r][3] = reference[8][r][3];
        gunFromController = HandPose::Concat(HandPose::InverseRigid(source),
            HandPose::FitGunToPalm(reference[24]));
        count = n;
        return true;
    }

    bool Resolve(int number, const matrix3x4_t& controller,
                 const matrix3x4_t *nativeBones, matrix3x4_t& output) const {
        if (number < 1 || number > count || !nativeBones) return false;
        const auto& attachment = attachments[number-1];
        const auto gun = HandPose::Concat(controller,gunFromController);
        const auto animated = HandPose::Concat(nativeBones[attachment.bone],attachment.local);
        output = HandPose::Reanchor(animated,nativeBones[24],gun);
        return true;
    }
};
}
