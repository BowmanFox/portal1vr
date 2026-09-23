#include <Windows.h>
#include <cassert>
#include "sdk/sdk.h"
#include "portaltrace.h"
// Optional installed-binary check: map code/relocations without running the
// game's DLL initializer or any game function outside its engine context.
int main(int argc, char **argv) {
    if (argc != 2) return 2;
    HMODULE client = LoadLibraryExA(argv[1], nullptr, DONT_RESOLVE_DLL_REFERENCES);
    if (!client) return 3;
    const auto binding = PortalTrace::Binding::Resolve(reinterpret_cast<uintptr_t>(client));
    const auto *base = reinterpret_cast<const unsigned char *>(client);
    const unsigned char matrixPrologue[]={0x55,0x8b,0xec,0x56,0x8b,0x75,8,0x57,0x8b,0xf9,0x83,0xfe,1,0x7c,0x38};
    const unsigned char anglesPrologue[]={0x55,0x8b,0xec,0x56,0x57,0x8b,0x7d,8,0x8b,0xf1,0x83,0xff,1,0x7c,0x6f};
    const unsigned char retMatrix[]={0xc2,8,0}, retAngles[]={0xc2,12,0};
    const bool attachments = binding.function
        && !memcmp(base+0xa5c50,matrixPrologue,sizeof(matrixPrologue))
        && !memcmp(base+0xa5d00,anglesPrologue,sizeof(anglesPrologue))
        && !memcmp(base+0xa5c94,retMatrix,sizeof(retMatrix))
        && !memcmp(base+0xa5d7b,retAngles,sizeof(retAngles));
    const bool matched = binding.function && binding.entityList && binding.traceFlags && attachments;
    FreeLibrary(client);
    puts(matched ? "Installed Portal 1 trace and attachment ABI guards match" : "Installed client ABI mismatch");
    return matched ? 0 : 4;
}
