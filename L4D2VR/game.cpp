#include "game.h"
#include <Windows.h>
#include <iostream>
#include "sdk.h"
#include "vr.h"
#include "hooks.h"
#include "offsets.h"
#include "portal1.h"
#include "sigscanner.h"
#include <Psapi.h>

namespace
{
    bool TryGetModuleInfo(const char *dllname, MODULEINFO &moduleInfo)
    {
        HMODULE hModule = GetModuleHandleA(dllname);
        if (!hModule)
            return false;

        return GetModuleInformation(GetCurrentProcess(), hModule, &moduleInfo, sizeof(moduleInfo)) != FALSE;
    }
}

Game* g_Game = nullptr;

Game::Game()
{
    while (!(m_BaseClient = (uintptr_t)GetModuleHandle("client.dll")))
        Sleep(50);
    while (!(m_BaseEngine = (uintptr_t)GetModuleHandle("engine.dll")))
        Sleep(50);
    while (!(m_BaseMaterialSystem = (uintptr_t)GetModuleHandle("materialsystem.dll")))
        Sleep(50);
    while (!(m_BaseServer = (uintptr_t)GetModuleHandle("server.dll")))
        Sleep(50);
    while (!(m_BaseVgui2 = (uintptr_t)GetModuleHandle("vgui2.dll")))
        Sleep(50);

    m_ClientEntityList = (IClientEntityList *)GetInterface("client.dll", Portal1::Interfaces::kClientEntityList);
    m_EngineTrace = (IEngineTrace *)GetInterface("engine.dll", Portal1::Interfaces::kEngineTrace);
    m_EngineClient = (IEngineClient *)GetInterface("engine.dll", Portal1::Interfaces::kEngineClient);
    m_MaterialSystem = (IMaterialSystem *)GetInterface("MaterialSystem.dll", Portal1::Interfaces::kMaterialSystem);
    m_ClientMode = (IClientMode *)GetModuleOffset("client.dll", Portal1::ClientGlobal::kClientModePortalNormal);
    m_ClientViewRender = (IViewRender *)GetModuleOffset("client.dll", Portal1::ClientGlobal::kViewRender);
    m_EngineViewRender = (IViewRender *)GetInterface("engine.dll", Portal1::Interfaces::kEngineRenderView, false);
    m_ModelInfo = (IModelInfo *)GetInterface("engine.dll", Portal1::Interfaces::kModelInfo);
    m_ModelRender = (IModelRender *)GetInterface("engine.dll", Portal1::Interfaces::kModelRender);
    m_VguiInput = (IInput *)GetInterface("vgui2.dll", Portal1::Interfaces::kVguiInput);
    m_VguiSurface = (ISurface *)GetInterface("vguimatsurface.dll", Portal1::Interfaces::kVguiSurface);

    m_Offsets = new Offsets();

    m_VR = new VR(this);
    m_Hooks = new Hooks(this);

    m_Initialized = true;
}

void *Game::GetInterface(const char *dllname, const char *interfacename, bool required)
{
    tCreateInterface CreateInterface = (tCreateInterface)GetProcAddress(GetModuleHandle(dllname), "CreateInterface");
    if (!CreateInterface)
    {
        if (required)
        {
            std::string error = "Missing CreateInterface in ";
            error += dllname;
            Game::errorMsg(error.c_str());
        }
        return nullptr;
    }

    int returnCode = 0;
    void *createdInterface = CreateInterface(interfacename, &returnCode);
    if (!createdInterface && required)
    {
        std::string error = "Failed to get interface ";
        error += interfacename;
        error += " from ";
        error += dllname;
        Game::errorMsg(error.c_str());
    }

    return createdInterface;
}

void *Game::GetModuleOffset(const char *dllname, uintptr_t offset, bool required)
{
    MODULEINFO moduleInfo = {};
    if (!TryGetModuleInfo(dllname, moduleInfo))
    {
        if (required)
        {
            std::string error = "Failed to query module info for ";
            error += dllname;
            Game::errorMsg(error.c_str());
        }
        return nullptr;
    }

    if (offset >= moduleInfo.SizeOfImage)
    {
        if (required)
        {
            char error[256];
            sprintf_s(error, "Offset 0x%zX is outside %s", static_cast<size_t>(offset), dllname);
            Game::errorMsg(error);
        }
        return nullptr;
    }

    return reinterpret_cast<void *>(reinterpret_cast<uintptr_t>(moduleInfo.lpBaseOfDll) + offset);
}

void Game::errorMsg(const char *msg)
{
    MessageBox(0, msg, "L4D2VR", MB_ICONERROR | MB_OK);
}

CBaseEntity *Game::GetClientEntity(int entityIndex)
{
    return (CBaseEntity *)(m_ClientEntityList->GetClientEntity(entityIndex));
}

char *Game::getNetworkName(uintptr_t *entity)
{
    uintptr_t *IClientNetworkableVtable = (uintptr_t *)*(entity + 0x8);
    uintptr_t *GetClientClassPtr = (uintptr_t *)*(IClientNetworkableVtable + 0x8);
    uintptr_t *ClientClassPtr = (uintptr_t *)*(GetClientClassPtr + 0x1);
    char *m_pNetworkName = (char *)*(ClientClassPtr + 0x8);
    int classID = (int)*(ClientClassPtr + 0x10);
    std::cout << "ClassID: " << classID << std::endl;
    return m_pNetworkName;
}

void Game::ClientCmd(const char *szCmdString)
{
    m_EngineClient->ClientCmd(szCmdString);
}

void Game::ClientCmd_Unrestricted(const char *szCmdString)
{
    m_EngineClient->ClientCmd_Unrestricted(szCmdString);
}


