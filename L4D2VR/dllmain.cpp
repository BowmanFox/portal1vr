// dllmain.cpp : Defines the entry point for the DLL application.
#include <Windows.h>
#include <iostream>
#include "game.h"
#include "hooks.h"
#include "vr.h"
#include "sdk.h"
#include "debuglog.h"

DWORD WINAPI InitL4D2VR(LPVOID)
{
    PortalVrResetLog();
    PortalVrLog("Init thread start");

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


