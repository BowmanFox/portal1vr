#pragma once
#include "sigscanner.h"
#include "sdk/trace.h"
#include <cmath>

namespace PortalTrace {
// Portal 1 client.dll, PE timestamp 0x68362d89. CPortalGameMovement::
// TracePlayerBBox calls this six-argument cdecl helper with the player's
// portal environment. Its swept-hull trace retains exit-side obstacles while
// removing the wall inside the linked portal. A normal engine trace cannot.
using TraceFn = void (__cdecl *)(void *, const Ray_t&, unsigned, CTraceFilter *, CGameTrace *, bool);

struct Binding {
    TraceFn function = nullptr;
    uintptr_t *entityList = nullptr;
    unsigned char *traceFlags = nullptr;

    static Binding Resolve(uintptr_t base) {
        Binding result;
        if (!SigScanner::IsReadable(base, sizeof(IMAGE_DOS_HEADER))) return result;
        const auto *dos = reinterpret_cast<const IMAGE_DOS_HEADER *>(base);
        if (dos->e_magic != IMAGE_DOS_SIGNATURE || dos->e_lfanew < 0
            || dos->e_lfanew > 0x1000) return result;
        const uintptr_t ntAddress = base + dos->e_lfanew;
        if (!SigScanner::IsReadable(ntAddress, sizeof(IMAGE_NT_HEADERS32))) return result;
        const auto *nt = reinterpret_cast<const IMAGE_NT_HEADERS32 *>(ntAddress);
        if (nt->Signature != IMAGE_NT_SIGNATURE || nt->FileHeader.Machine != IMAGE_FILE_MACHINE_I386
            || nt->FileHeader.TimeDateStamp != 0x68362d89
            || nt->OptionalHeader.SizeOfImage != 0x5d6000) return result;
        const uintptr_t helper = base + 0x23b980;
        const uintptr_t caller = base + 0x237851;
        const unsigned char prologue[] = {0x55,0x8b,0xec,0x81,0xec,0x1c,1,0,0,0x57,0x8b,0x7d,8,0x85,0xff};
        const unsigned char handleLoad[] = {0x8b,0x8f,0x58,0x16,0,0,0x83,0xf9,0xff,0x74,0x1e,0x8b,0x15};
        if (!SigScanner::IsExecutable(helper) || !SigScanner::IsReadable(helper, 0xc0)
            || !SigScanner::IsReadable(caller, 0x45)
            || memcmp(reinterpret_cast<void *>(helper), prologue, sizeof(prologue))
            || memcmp(reinterpret_cast<void *>(caller), handleLoad, sizeof(handleLoad))) return result;
        // Check both relocated globals and the actual native caller, rather
        // than assuming a matching entry prologue implies a matching layout.
        if (*reinterpret_cast<const uintptr_t *>(caller + 13) != base + 0x4ab590
            || *reinterpret_cast<const unsigned char *>(caller + 0x40) != 0xe8
            || caller + 0x45 + *reinterpret_cast<const int32_t *>(caller + 0x41) != helper
            || *reinterpret_cast<const unsigned char *>(helper + 0x6a) != 0xa0
            || *reinterpret_cast<const uintptr_t *>(helper + 0x6b) != base + 0x51c0ad
            || *reinterpret_cast<const uint16_t *>(helper + 0xa1) != 0x3d80
            || *reinterpret_cast<const uintptr_t *>(helper + 0xa3) != base + 0x51c0ac
            || !SigScanner::IsReadable(base + 0x4ab590, sizeof(uintptr_t))
            || !SigScanner::IsReadable(base + 0x51c0ac, 2)) return result;
        result.function = reinterpret_cast<TraceFn>(helper);
        result.entityList = reinterpret_cast<uintptr_t *>(base + 0x4ab590);
        result.traceFlags = reinterpret_cast<unsigned char *>(base + 0x51c0ac);
        return result;
    }

    void *Environment(void *player) const {
        if (!function || !entityList || !traceFlags || !player
            || !SigScanner::IsReadable(reinterpret_cast<uintptr_t>(player) + 0x1658, 4)) return nullptr;
        const uint32_t handle = *reinterpret_cast<const uint32_t *>(static_cast<const char *>(player) + 0x1658);
        if (handle == 0xffffffff || !SigScanner::IsReadable(*entityList, 16)) return nullptr;
        const uintptr_t entry = *entityList + (handle & 0xfff) * 16;
        if (!SigScanner::IsReadable(entry, 12)
            || *reinterpret_cast<const uint32_t *>(entry + 8) != handle >> 12) return nullptr;
        const uintptr_t portal = *reinterpret_cast<const uintptr_t *>(entry + 4);
        if (!SigScanner::IsReadable(portal, 0xabc)
            || !*reinterpret_cast<const unsigned char *>(portal + 0xab4)) return nullptr;
        const uintptr_t linked = *reinterpret_cast<const uintptr_t *>(portal + 0xab8);
        if (!SigScanner::IsReadable(linked, 1) || !*reinterpret_cast<const unsigned char *>(linked)) return nullptr;
        return reinterpret_cast<void *>(portal);
    }

    bool Trace(void *player, const Ray_t& ray, unsigned mask, CTraceFilter *filter, CGameTrace *out) const {
        void *portal = Environment(player);
        if (!portal) return false;
        // Native movement owns these scratch flags. Rendering must not leave
        // them changed for the following prediction or movement tick.
        const unsigned char saved[2] = {traceFlags[0], traceFlags[1]};
        function(portal, ray, mask, filter, out, true);
        traceFlags[0] = saved[0];
        traceFlags[1] = saved[1];
        return std::isfinite(out->fraction) && out->fraction >= 0 && out->fraction <= 1;
    }
};
}
