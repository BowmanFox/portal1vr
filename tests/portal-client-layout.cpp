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
    const bool matched = binding.function && binding.entityList && binding.traceFlags;
    FreeLibrary(client);
    puts(matched ? "Installed Portal 1 portal-trace ABI guards match" : "Unsupported Portal client; ordinary trace fallback required");
    return matched ? 0 : 4;
}
