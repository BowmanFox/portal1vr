// dllmain.cpp : Defines the entry point for the DLL application.
#include <Windows.h>
#include <winternl.h>
#include <iostream>
#include <cstdarg>
#include <cstring>
#include "game.h"
#include "hooks.h"
#include "vr.h"
#include "sdk.h"
#include "debuglog.h"

namespace
{
    using ExitProcessFn = VOID (WINAPI *)(UINT);
    using TerminateProcessFn = BOOL (WINAPI *)(HANDLE, UINT);
    using Tier0SpewFn = void (__cdecl *)(const char *, ...);
    using LoadLibraryAFn = HMODULE (WINAPI *)(LPCSTR);
    using LoadLibraryWFn = HMODULE (WINAPI *)(LPCWSTR);
    using LoadLibraryExAFn = HMODULE (WINAPI *)(LPCSTR, HANDLE, DWORD);
    using LoadLibraryExWFn = HMODULE (WINAPI *)(LPCWSTR, HANDLE, DWORD);
    using LdrLoadDllFn = NTSTATUS (NTAPI *)(PWSTR, PULONG, PUNICODE_STRING, PHANDLE);

    ExitProcessFn g_OriginalExitProcess = nullptr;
    TerminateProcessFn g_OriginalTerminateProcess = nullptr;
    bool g_ExitHooksInstalled = false;
    Tier0SpewFn g_OriginalTier0Error = nullptr;
    Tier0SpewFn g_OriginalTier0Warning = nullptr;
    Tier0SpewFn g_OriginalTier0ConWarning = nullptr;
    Tier0SpewFn g_OriginalTier0DevWarning = nullptr;
    bool g_Tier0HooksInstalled = false;
    PVOID g_VectoredExceptionHandle = nullptr;
    LoadLibraryAFn g_OriginalLoadLibraryA = nullptr;
    LoadLibraryWFn g_OriginalLoadLibraryW = nullptr;
    LoadLibraryExAFn g_OriginalLoadLibraryExA = nullptr;
    LoadLibraryExWFn g_OriginalLoadLibraryExW = nullptr;
    LdrLoadDllFn g_OriginalLdrLoadDll = nullptr;
    bool g_LoadLibraryHooksInstalled = false;

#ifndef STATUS_DLL_NOT_FOUND
#define STATUS_DLL_NOT_FOUND static_cast<NTSTATUS>(0xC0000135L)
#endif

    bool IsBlockedModuleName(const char *moduleName)
    {
        if (!moduleName)
            return false;

        const char *baseName = strrchr(moduleName, '\\');
        baseName = baseName ? baseName + 1 : moduleName;
        return _stricmp(baseName, "fastprox.dll") == 0;
    }

    bool IsBlockedModuleName(const wchar_t *moduleName)
    {
        if (!moduleName)
            return false;

        const wchar_t *baseName = wcsrchr(moduleName, L'\\');
        baseName = baseName ? baseName + 1 : moduleName;
        return _wcsicmp(baseName, L"fastprox.dll") == 0;
    }

    bool IsBlockedModuleName(const UNICODE_STRING *moduleName)
    {
        if (!moduleName || !moduleName->Buffer || moduleName->Length == 0)
            return false;

        wchar_t buffer[MAX_PATH] = {};
        const size_t requestedCharacters = static_cast<size_t>(moduleName->Length / sizeof(wchar_t));
        const size_t characters = requestedCharacters < (ARRAYSIZE(buffer) - 1) ? requestedCharacters : (ARRAYSIZE(buffer) - 1);
        wcsncpy_s(buffer, ARRAYSIZE(buffer), moduleName->Buffer, characters);
        return IsBlockedModuleName(buffer);
    }

    void LogAddressWithModule(const char *label, void *address)
    {
        MEMORY_BASIC_INFORMATION mbi = {};
        if (VirtualQuery(address, &mbi, sizeof(mbi)) == 0)
        {
            PortalVrLog("%s %p", label, address);
            return;
        }

        char modulePath[MAX_PATH] = {};
        HMODULE module = static_cast<HMODULE>(mbi.AllocationBase);
        if (module && GetModuleFileNameA(module, modulePath, MAX_PATH))
        {
            const char *moduleName = strrchr(modulePath, '\\');
            moduleName = moduleName ? moduleName + 1 : modulePath;
            PortalVrLog("%s %s+0x%IX", label, moduleName, reinterpret_cast<uintptr_t>(address) - reinterpret_cast<uintptr_t>(module));
        }
        else
        {
            PortalVrLog("%s %p", label, address);
        }
    }

    void FormatTier0Message(char *buffer, size_t bufferSize, const char *fmt, va_list args)
    {
        if (!fmt)
        {
            strcpy_s(buffer, bufferSize, "<null>");
            return;
        }

        vsnprintf_s(buffer, bufferSize, _TRUNCATE, fmt, args);
    }

    void LogExitStack(const char *label)
    {
        void *frames[24] = {};
        const USHORT frameCount = CaptureStackBackTrace(1, ARRAYSIZE(frames), frames, nullptr);
        PortalVrLog("%s", label);

        for (USHORT i = 0; i < frameCount; ++i)
        {
            MEMORY_BASIC_INFORMATION mbi = {};
            if (VirtualQuery(frames[i], &mbi, sizeof(mbi)) == 0)
            {
                PortalVrLog("  #%u %p", i, frames[i]);
                continue;
            }

            char modulePath[MAX_PATH] = {};
            HMODULE module = static_cast<HMODULE>(mbi.AllocationBase);
            if (module && GetModuleFileNameA(module, modulePath, MAX_PATH))
            {
                const char *moduleName = strrchr(modulePath, '\\');
                moduleName = moduleName ? moduleName + 1 : modulePath;
                PortalVrLog("  #%u %s+0x%IX", i, moduleName, reinterpret_cast<uintptr_t>(frames[i]) - reinterpret_cast<uintptr_t>(module));
            }
            else
            {
                PortalVrLog("  #%u %p", i, frames[i]);
            }
        }
    }

    void LogCurrentStack(const char *label, USHORT framesToSkip)
    {
        void *frames[24] = {};
        const USHORT frameCount = CaptureStackBackTrace(framesToSkip, ARRAYSIZE(frames), frames, nullptr);
        PortalVrLog("%s", label);

        for (USHORT i = 0; i < frameCount; ++i)
        {
            MEMORY_BASIC_INFORMATION mbi = {};
            if (VirtualQuery(frames[i], &mbi, sizeof(mbi)) == 0)
            {
                PortalVrLog("  #%u %p", i, frames[i]);
                continue;
            }

            char modulePath[MAX_PATH] = {};
            HMODULE module = static_cast<HMODULE>(mbi.AllocationBase);
            if (module && GetModuleFileNameA(module, modulePath, MAX_PATH))
            {
                const char *moduleName = strrchr(modulePath, '\\');
                moduleName = moduleName ? moduleName + 1 : modulePath;
                PortalVrLog("  #%u %s+0x%IX", i, moduleName, reinterpret_cast<uintptr_t>(frames[i]) - reinterpret_cast<uintptr_t>(module));
            }
            else
            {
                PortalVrLog("  #%u %p", i, frames[i]);
            }
        }
    }

    VOID WINAPI HookedExitProcess(UINT exitCode)
    {
        PortalVrLog("ExitProcess called exitCode=%u", exitCode);
        LogExitStack("ExitProcess stack");
        if (g_OriginalExitProcess)
            g_OriginalExitProcess(exitCode);
    }

    BOOL WINAPI HookedTerminateProcess(HANDLE process, UINT exitCode)
    {
        if (process == GetCurrentProcess() || process == reinterpret_cast<HANDLE>(-1))
        {
            PortalVrLog("TerminateProcess called exitCode=%u", exitCode);
            LogExitStack("TerminateProcess stack");
        }

        return g_OriginalTerminateProcess ? g_OriginalTerminateProcess(process, exitCode) : FALSE;
    }

    void InstallProcessExitHooks()
    {
        if (g_ExitHooksInstalled)
            return;

        const MH_STATUS initStatus = MH_Initialize();
        if (initStatus != MH_OK && initStatus != MH_ERROR_ALREADY_INITIALIZED)
        {
            PortalVrLog("MH_Initialize failed for exit hooks status=%d", initStatus);
            return;
        }

        const MH_STATUS exitHookStatus = MH_CreateHookApi(L"kernel32", "ExitProcess", &HookedExitProcess, reinterpret_cast<LPVOID *>(&g_OriginalExitProcess));
        const MH_STATUS terminateHookStatus = MH_CreateHookApi(L"kernel32", "TerminateProcess", &HookedTerminateProcess, reinterpret_cast<LPVOID *>(&g_OriginalTerminateProcess));
        if (exitHookStatus != MH_OK || terminateHookStatus != MH_OK)
        {
            PortalVrLog("Failed to create exit hooks exit=%d terminate=%d", exitHookStatus, terminateHookStatus);
            return;
        }

        const MH_STATUS enableStatus = MH_EnableHook(MH_ALL_HOOKS);
        if (enableStatus != MH_OK)
        {
            PortalVrLog("Failed to enable exit hooks status=%d", enableStatus);
            return;
        }

        g_ExitHooksInstalled = true;
        PortalVrLog("Process exit hooks installed");
    }

    HMODULE WINAPI HookedLoadLibraryA(LPCSTR libFileName)
    {
        if (IsBlockedModuleName(libFileName))
        {
            PortalVrLog("Blocked LoadLibraryA for %s", libFileName);
            SetLastError(ERROR_MOD_NOT_FOUND);
            return nullptr;
        }

        return g_OriginalLoadLibraryA ? g_OriginalLoadLibraryA(libFileName) : nullptr;
    }

    HMODULE WINAPI HookedLoadLibraryW(LPCWSTR libFileName)
    {
        if (IsBlockedModuleName(libFileName))
        {
            PortalVrLog("Blocked LoadLibraryW for fastprox.dll");
            SetLastError(ERROR_MOD_NOT_FOUND);
            return nullptr;
        }

        return g_OriginalLoadLibraryW ? g_OriginalLoadLibraryW(libFileName) : nullptr;
    }

    HMODULE WINAPI HookedLoadLibraryExA(LPCSTR libFileName, HANDLE file, DWORD flags)
    {
        if (IsBlockedModuleName(libFileName))
        {
            PortalVrLog("Blocked LoadLibraryExA for %s", libFileName);
            SetLastError(ERROR_MOD_NOT_FOUND);
            return nullptr;
        }

        return g_OriginalLoadLibraryExA ? g_OriginalLoadLibraryExA(libFileName, file, flags) : nullptr;
    }

    HMODULE WINAPI HookedLoadLibraryExW(LPCWSTR libFileName, HANDLE file, DWORD flags)
    {
        if (IsBlockedModuleName(libFileName))
        {
            PortalVrLog("Blocked LoadLibraryExW for fastprox.dll");
            SetLastError(ERROR_MOD_NOT_FOUND);
            return nullptr;
        }

        return g_OriginalLoadLibraryExW ? g_OriginalLoadLibraryExW(libFileName, file, flags) : nullptr;
    }

    NTSTATUS NTAPI HookedLdrLoadDll(PWSTR searchPath, PULONG loadFlags, PUNICODE_STRING moduleFileName, PHANDLE moduleHandle)
    {
        if (IsBlockedModuleName(moduleFileName))
        {
            PortalVrLog("Blocked LdrLoadDll for fastprox.dll");
            if (moduleHandle)
                *moduleHandle = nullptr;
            SetLastError(ERROR_MOD_NOT_FOUND);
            return STATUS_DLL_NOT_FOUND;
        }

        return g_OriginalLdrLoadDll
            ? g_OriginalLdrLoadDll(searchPath, loadFlags, moduleFileName, moduleHandle)
            : STATUS_DLL_NOT_FOUND;
    }

    void InstallLoadLibraryHooks()
    {
        if (g_LoadLibraryHooksInstalled)
            return;

        PortalVrLog("InstallLoadLibraryHooks start");

        const MH_STATUS initStatus = MH_Initialize();
        if (initStatus != MH_OK && initStatus != MH_ERROR_ALREADY_INITIALIZED)
        {
            PortalVrLog("MH_Initialize failed for LoadLibrary hooks status=%d", initStatus);
            return;
        }

        void *ldrLoadDllAddress = nullptr;
        if (HMODULE ntdll = GetModuleHandleW(L"ntdll.dll"))
            ldrLoadDllAddress = reinterpret_cast<void *>(GetProcAddress(ntdll, "LdrLoadDll"));

        const MH_STATUS hookAStatus = MH_CreateHookApi(L"kernel32", "LoadLibraryA", &HookedLoadLibraryA, reinterpret_cast<LPVOID *>(&g_OriginalLoadLibraryA));
        const MH_STATUS hookWStatus = MH_CreateHookApi(L"kernel32", "LoadLibraryW", &HookedLoadLibraryW, reinterpret_cast<LPVOID *>(&g_OriginalLoadLibraryW));
        const MH_STATUS hookExAStatus = MH_CreateHookApi(L"kernel32", "LoadLibraryExA", &HookedLoadLibraryExA, reinterpret_cast<LPVOID *>(&g_OriginalLoadLibraryExA));
        const MH_STATUS hookExWStatus = MH_CreateHookApi(L"kernel32", "LoadLibraryExW", &HookedLoadLibraryExW, reinterpret_cast<LPVOID *>(&g_OriginalLoadLibraryExW));
        const MH_STATUS ldrHookStatus = ldrLoadDllAddress
            ? MH_CreateHook(ldrLoadDllAddress, &HookedLdrLoadDll, reinterpret_cast<LPVOID *>(&g_OriginalLdrLoadDll))
            : MH_ERROR_NOT_EXECUTABLE;
        if (hookAStatus != MH_OK || hookWStatus != MH_OK || hookExAStatus != MH_OK || hookExWStatus != MH_OK || ldrHookStatus != MH_OK)
        {
            PortalVrLog(
                "Failed to create LoadLibrary hooks A=%d W=%d ExA=%d ExW=%d Ldr=%d addr=%p",
                hookAStatus,
                hookWStatus,
                hookExAStatus,
                hookExWStatus,
                ldrHookStatus,
                ldrLoadDllAddress);
            return;
        }

        const MH_STATUS enableStatus = MH_EnableHook(MH_ALL_HOOKS);
        if (enableStatus != MH_OK)
        {
            PortalVrLog("Failed to enable LoadLibrary hooks status=%d", enableStatus);
            return;
        }

        g_LoadLibraryHooksInstalled = true;
        PortalVrLog("LoadLibrary hooks installed ldr=%p fastproxLoaded=%p", ldrLoadDllAddress, GetModuleHandleA("fastprox.dll"));
    }

    LONG CALLBACK PortalVrVectoredExceptionHandler(EXCEPTION_POINTERS *exceptionInfo)
    {
        if (!exceptionInfo || !exceptionInfo->ExceptionRecord)
            return EXCEPTION_CONTINUE_SEARCH;

        const DWORD code = exceptionInfo->ExceptionRecord->ExceptionCode;
        if (code == EXCEPTION_BREAKPOINT || code == EXCEPTION_SINGLE_STEP || code == 0x406D1388 || code == 0xE06D7363 || code == 0x40010006 || code == 0x4001000A)
            return EXCEPTION_CONTINUE_SEARCH;

        PortalVrLog("SEH exception code=0x%08X flags=0x%08X", code, exceptionInfo->ExceptionRecord->ExceptionFlags);
        LogAddressWithModule("SEH address", exceptionInfo->ExceptionRecord->ExceptionAddress);
        LogCurrentStack("SEH stack", 1);

        if (code == EXCEPTION_ACCESS_VIOLATION && exceptionInfo->ExceptionRecord->NumberParameters >= 2)
        {
            const ULONG_PTR accessType = exceptionInfo->ExceptionRecord->ExceptionInformation[0];
            const void *targetAddress = reinterpret_cast<void *>(exceptionInfo->ExceptionRecord->ExceptionInformation[1]);
            PortalVrLog("SEH access violation type=%Iu address=%p", accessType, targetAddress);
        }

        return EXCEPTION_CONTINUE_SEARCH;
    }

    void InstallVectoredExceptionLogger()
    {
        if (g_VectoredExceptionHandle)
            return;

        g_VectoredExceptionHandle = AddVectoredExceptionHandler(1, &PortalVrVectoredExceptionHandler);
        if (g_VectoredExceptionHandle)
            PortalVrLog("Vectored exception logger installed");
        else
            PortalVrLog("Failed to install vectored exception logger");
    }

    void __cdecl HookedTier0Error(const char *fmt, ...)
    {
        char buffer[2048] = {};
        va_list args;
        va_start(args, fmt);
        FormatTier0Message(buffer, sizeof(buffer), fmt, args);
        va_end(args);

        PortalVrLog("tier0 Error: %s", buffer);
        if (g_OriginalTier0Error)
            g_OriginalTier0Error("%s", buffer);
    }

    void __cdecl HookedTier0Warning(const char *fmt, ...)
    {
        char buffer[2048] = {};
        va_list args;
        va_start(args, fmt);
        FormatTier0Message(buffer, sizeof(buffer), fmt, args);
        va_end(args);

        PortalVrLog("tier0 Warning: %s", buffer);
        if (g_OriginalTier0Warning)
            g_OriginalTier0Warning("%s", buffer);
    }

    void __cdecl HookedTier0ConWarning(const char *fmt, ...)
    {
        char buffer[2048] = {};
        va_list args;
        va_start(args, fmt);
        FormatTier0Message(buffer, sizeof(buffer), fmt, args);
        va_end(args);

        PortalVrLog("tier0 ConWarning: %s", buffer);
        if (g_OriginalTier0ConWarning)
            g_OriginalTier0ConWarning("%s", buffer);
    }

    void __cdecl HookedTier0DevWarning(const char *fmt, ...)
    {
        char buffer[2048] = {};
        va_list args;
        va_start(args, fmt);
        FormatTier0Message(buffer, sizeof(buffer), fmt, args);
        va_end(args);

        PortalVrLog("tier0 DevWarning: %s", buffer);
        if (g_OriginalTier0DevWarning)
            g_OriginalTier0DevWarning("%s", buffer);
    }

    void InstallTier0SpewHooks()
    {
        if (g_Tier0HooksInstalled)
            return;

        if (!GetModuleHandleA("tier0.dll"))
            return;

        const MH_STATUS errorHookStatus = MH_CreateHookApi(L"tier0.dll", "Error", &HookedTier0Error, reinterpret_cast<LPVOID *>(&g_OriginalTier0Error));
        const MH_STATUS warningHookStatus = MH_CreateHookApi(L"tier0.dll", "Warning", &HookedTier0Warning, reinterpret_cast<LPVOID *>(&g_OriginalTier0Warning));
        const MH_STATUS conWarningHookStatus = MH_CreateHookApi(L"tier0.dll", "ConWarning", &HookedTier0ConWarning, reinterpret_cast<LPVOID *>(&g_OriginalTier0ConWarning));
        const MH_STATUS devWarningHookStatus = MH_CreateHookApi(L"tier0.dll", "DevWarning", &HookedTier0DevWarning, reinterpret_cast<LPVOID *>(&g_OriginalTier0DevWarning));
        if (errorHookStatus != MH_OK || warningHookStatus != MH_OK || conWarningHookStatus != MH_OK || devWarningHookStatus != MH_OK)
        {
            PortalVrLog(
                "Failed to create tier0 hooks error=%d warning=%d conWarning=%d devWarning=%d",
                errorHookStatus,
                warningHookStatus,
                conWarningHookStatus,
                devWarningHookStatus);
            return;
        }

        const MH_STATUS enableStatus = MH_EnableHook(MH_ALL_HOOKS);
        if (enableStatus != MH_OK)
        {
            PortalVrLog("Failed to enable tier0 hooks status=%d", enableStatus);
            return;
        }

        g_Tier0HooksInstalled = true;
        PortalVrLog("Tier0 spew hooks installed");
    }
}

DWORD WINAPI InitL4D2VR(LPVOID)
{
    PortalVrResetLog();
    PortalVrLog("Init thread start");
    InstallVectoredExceptionLogger();
    InstallProcessExitHooks();
    InstallLoadLibraryHooks();

// Release if buggy, so we'll be releasing the debug binary
#ifdef _DEBUG
    if (AllocConsole())
    {
        FILE *fp = nullptr;
        freopen_s(&fp, "CONOUT$", "w", stdout);
        freopen_s(&fp, "CONOUT$", "w", stderr);
    }
#endif

    // Make sure -insecure is used
    int nArgs = 0;
    LPWSTR *szArglist = CommandLineToArgvW(GetCommandLineW(), &nArgs);
    if (!szArglist)
    {
        PortalVrLog("CommandLineToArgvW failed");
        MessageBoxA(nullptr,
            "Portal VR failed to read the launch arguments. Initialization was skipped.",
            "Portal VR",
            MB_ICONWARNING | MB_OK);
        return 0;
    }

    bool insecureEnabled = false;
    for (int i = 0; i < nArgs; ++i)
    {
        if (wcscmp(szArglist[i], L"-insecure") == 0)
            insecureEnabled = true;
    }
    LocalFree(szArglist);

    if (!insecureEnabled)
    {
        PortalVrLog("Missing -insecure, init skipped");
        MessageBoxA(nullptr,
            "Portal VR requires the -insecure launch option. Initialization was skipped.",
            "Portal VR",
            MB_ICONWARNING | MB_OK);
        return 0;
    }

    PortalVrLog("Launch arguments validated, constructing Game");
    g_Game = new Game();
    PortalVrLog("Game constructed successfully");
    InstallTier0SpewHooks();

    return 0;
}



BOOL APIENTRY DllMain( HMODULE hModule,
                       DWORD  ul_reason_for_call,
                       LPVOID lpReserved
                     )
{
    switch (ul_reason_for_call)
    {
    case DLL_PROCESS_ATTACH:
        {
            HANDLE initThread = CreateThread(NULL, 0, InitL4D2VR, hModule, 0, NULL);
            if (initThread)
                CloseHandle(initThread);
            break;
        }
    case DLL_THREAD_ATTACH:
    case DLL_THREAD_DETACH:
    case DLL_PROCESS_DETACH:
        break;
    }
    return TRUE;
}


