#include "game.h"
#include <Windows.h>
#include <iostream>
#include "sdk.h"
#include "vr.h"
#include "hooks.h"
#include "offsets.h"
#include "portal1.h"
#include "sigscanner.h"
#include "debuglog.h"
#include "../dxvk/src/d3d9/d3d9_vr.h"
#include <Psapi.h>

namespace
{
    constexpr bool kEnableVrBootstrap = false;
    constexpr bool kResolveInterfaces = true;
    constexpr bool kConstructOffsets = false;
    constexpr bool kResolveClientGlobals = true;
    constexpr bool kResolveCreateInterfaces = false;

    bool TryGetModuleInfo(const char *dllname, MODULEINFO &moduleInfo)
    {
        HMODULE hModule = GetModuleHandleA(dllname);
        if (!hModule)
            return false;

        return GetModuleInformation(GetCurrentProcess(), hModule, &moduleInfo, sizeof(moduleInfo)) != FALSE;
    }

    template <typename T>
    bool ResolveInterfaceSlot(Game *game, T *&slot, const char *dllname, const char *interfacename)
    {
        if (slot)
            return true;

        PortalVrLog("Resolving interface %s from %s", interfacename, dllname);
        slot = static_cast<T *>(game->GetInterface(dllname, interfacename, false));
        PortalVrLog("Resolved interface %s from %s => %p", interfacename, dllname, slot);
        return slot != nullptr;
    }
}

Game* g_Game = nullptr;

Game::Game()
{
    PortalVrLog("Game::Game start");

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

    PortalVrLog(
        "Modules ready client=%p engine=%p materialsystem=%p server=%p vgui2=%p",
        reinterpret_cast<void *>(m_BaseClient),
        reinterpret_cast<void *>(m_BaseEngine),
        reinterpret_cast<void *>(m_BaseMaterialSystem),
        reinterpret_cast<void *>(m_BaseServer),
        reinterpret_cast<void *>(m_BaseVgui2));

    if (kResolveInterfaces)
    {
        if (kResolveClientGlobals)
        {
            m_ClientMode = (IClientMode *)GetModuleOffset("client.dll", Portal1::ClientGlobal::kClientModePortalNormal);
            m_ClientViewRender = (IViewRender *)GetModuleOffset("client.dll", Portal1::ClientGlobal::kViewRender);
        }
        else
        {
            PortalVrLog("Client globals disabled for diagnostic run");
        }

        if (kResolveCreateInterfaces)
        {
            TryResolveVrInterfaces(true);
        }
        else
        {
            PortalVrLog("CreateInterface resolution deferred until runtime");
        }

        PortalVrLog(
            "Interfaces ready clientMode=%p clientViewRender=%p engineViewRender=%p materialSystem=%p",
            m_ClientMode,
            m_ClientViewRender,
            m_EngineViewRender,
            m_MaterialSystem);
    }
    else
    {
        PortalVrLog("Interface resolution disabled for diagnostic run");
    }

    if (kConstructOffsets)
    {
        m_Offsets = new Offsets();
        PortalVrLog("Offsets constructed");
    }
    else
    {
        PortalVrLog("Offsets construction disabled for diagnostic run");
    }

    if (kEnableVrBootstrap)
    {
        EnsureVrBootstrap();
    }
    else
    {
        PortalVrLog("VR bootstrap deferred until runtime");
    }

    m_Initialized = true;
    PortalVrLog("Game::Game complete");
}

void Game::EnsureVrBootstrap()
{
    if (m_VrBootstrapAttempted || m_VR != nullptr)
        return;

    if (!g_D3DVR9)
    {
        PortalVrLog("EnsureVrBootstrap deferred: D3D9 VR interop not ready");
        return;
    }

    m_VrBootstrapAttempted = true;
    PortalVrLog("EnsureVrBootstrap start");

    m_VR = new VR(this);
    PortalVrLog("VR constructed");

    if (!m_VR || !m_VR->m_IsInitialized)
    {
        PortalVrLog("EnsureVrBootstrap aborted: VR did not initialize");
        return;
    }

    m_Hooks = new Hooks(this);
    PortalVrLog("Hooks constructed");
}

bool Game::TryResolveVrInterfaces(bool force)
{
    if (HasVrRuntimeInterfaces())
    {
        if (!m_LoggedVrInterfaceReady)
        {
            PortalVrLog(
                "VR render interfaces ready clientViewRender=%p materialSystem=%p",
                m_ClientViewRender,
                m_MaterialSystem);
            m_LoggedVrInterfaceReady = true;
        }

        return true;
    }

    const DWORD now = GetTickCount();
    if (!force && m_LastRuntimeInterfaceResolveTick != 0 && (now - m_LastRuntimeInterfaceResolveTick) < 1000)
        return false;

    m_LastRuntimeInterfaceResolveTick = now;
    PortalVrLog("TryResolveVrInterfaces attempt");

    if (!m_ClientMode)
        m_ClientMode = (IClientMode *)GetModuleOffset("client.dll", Portal1::ClientGlobal::kClientModePortalNormal, false);
    if (!m_ClientViewRender)
        m_ClientViewRender = (IViewRender *)GetModuleOffset("client.dll", Portal1::ClientGlobal::kViewRender, false);

    ResolveInterfaceSlot(this, m_MaterialSystem, "materialsystem.dll", Portal1::Interfaces::kMaterialSystem);

    if (HasVrRuntimeInterfaces())
    {
        PortalVrLog(
            "VR render interfaces ready clientViewRender=%p materialSystem=%p",
            m_ClientViewRender,
            m_MaterialSystem);
        m_LoggedVrInterfaceReady = true;
        return true;
    }

    PortalVrLog(
        "VR render interfaces pending clientViewRender=%p materialSystem=%p",
        m_ClientViewRender,
        m_MaterialSystem);
    return false;
}

bool Game::HasVrRuntimeInterfaces() const
{
    return m_ClientViewRender != nullptr
        && m_MaterialSystem != nullptr;
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


