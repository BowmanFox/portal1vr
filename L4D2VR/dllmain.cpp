// dllmain.cpp : Defines the entry point for the DLL application.
#include <Windows.h>
#include <iostream>
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

    ExitProcessFn g_OriginalExitProcess = nullptr;
    TerminateProcessFn g_OriginalTerminateProcess = nullptr;
    bool g_ExitHooksInstalled = false;

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
}

DWORD WINAPI InitL4D2VR(LPVOID)
{
    PortalVrResetLog();
    PortalVrLog("Init thread start");
    InstallProcessExitHooks();

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


