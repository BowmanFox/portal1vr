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
#include "trace.h"
#include "../dxvk/src/d3d9/d3d9_vr.h"
#include <Psapi.h>

namespace
{
    constexpr bool kEnableVrBootstrap = false;
    constexpr bool kResolveInterfaces = true;
    constexpr bool kConstructOffsets = true;
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

    template <typename T>
    T *ResolveInterfaceOnDemand(Game *game, T *&slot, const char *dllname, const char *interfacename, uint32_t &lastResolveTick, bool force = false)
    {
        if (slot)
            return slot;

        const DWORD now = GetTickCount();
        if (!force && lastResolveTick != 0 && (now - lastResolveTick) < 1000)
            return nullptr;

        lastResolveTick = now;
        slot = static_cast<T *>(game->GetInterface(dllname, interfacename, false));
        PortalVrLog("ResolveInterfaceOnDemand %s from %s => %p", interfacename, dllname, slot);
        return slot;
    }

    template <typename T>
    T *ResolveGlobalOnDemand(Game *game, T *&slot, const char *dllname, uintptr_t offset, uint32_t &lastResolveTick, const char *name, bool force = false)
    {
        if (slot)
            return slot;

        const DWORD now = GetTickCount();
        if (!force && lastResolveTick != 0 && (now - lastResolveTick) < 1000)
            return nullptr;

        lastResolveTick = now;
        slot = reinterpret_cast<T *>(game->GetModuleOffset(dllname, offset, false));
        PortalVrLog("ResolveGlobalOnDemand %s from %s+0x%zX => %p", name, dllname, static_cast<size_t>(offset), slot);
        return slot;
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
            m_ClientMode = GetClientMode(true);
            m_ClientViewRender = GetClientViewRender(true);
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
        m_ClientMode = GetClientMode(force);
    if (!m_ClientViewRender)
        m_ClientViewRender = GetClientViewRender(force);

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

IClientMode *Game::GetClientMode(bool force)
{
    return ResolveGlobalOnDemand(this, m_ClientMode, "client.dll", Portal1::ClientGlobal::kClientModePortalNormal, m_LastClientModeResolveTick, "ClientModePortalNormal", force);
}

IViewRender *Game::GetClientViewRender(bool force)
{
    return ResolveGlobalOnDemand(this, m_ClientViewRender, "client.dll", Portal1::ClientGlobal::kViewRender, m_LastClientViewRenderResolveTick, "CViewRender", force);
}

IClientEntityList *Game::GetClientEntityList(bool force)
{
    return ResolveInterfaceOnDemand(this, m_ClientEntityList, "client.dll", Portal1::Interfaces::kClientEntityList, m_LastClientEntityListResolveTick, force);
}

IEngineTrace *Game::GetEngineTrace(bool force)
{
    return ResolveInterfaceOnDemand(this, m_EngineTrace, "engine.dll", Portal1::Interfaces::kEngineTrace, m_LastEngineTraceResolveTick, force);
}

IEngineClient *Game::GetEngineClient(bool force)
{
    return ResolveInterfaceOnDemand(this, m_EngineClient, "engine.dll", Portal1::Interfaces::kEngineClient, m_LastEngineClientResolveTick, force);
}

IMaterialSystem *Game::GetMaterialSystem(bool force)
{
    return ResolveInterfaceOnDemand(this, m_MaterialSystem, "materialsystem.dll", Portal1::Interfaces::kMaterialSystem, m_LastRuntimeInterfaceResolveTick, force);
}

IModelInfo *Game::GetModelInfo(bool force)
{
    return ResolveInterfaceOnDemand(this, m_ModelInfo, "engine.dll", Portal1::Interfaces::kModelInfo, m_LastModelInfoResolveTick, force);
}

IModelRender *Game::GetModelRender(bool force)
{
    return ResolveInterfaceOnDemand(this, m_ModelRender, "engine.dll", Portal1::Interfaces::kModelRender, m_LastModelRenderResolveTick, force);
}

IInput *Game::GetVguiInput(bool force)
{
    return ResolveInterfaceOnDemand(this, m_VguiInput, "vgui2.dll", Portal1::Interfaces::kVguiInput, m_LastVguiInputResolveTick, force);
}

ISurface *Game::GetVguiSurface(bool force)
{
    return ResolveInterfaceOnDemand(this, m_VguiSurface, "vguimatsurface.dll", Portal1::Interfaces::kVguiSurface, m_LastVguiSurfaceResolveTick, force);
}

C_Portal_Player *Game::GetPortalPlayer(int index)
{
    IClientEntityList *entityList = GetClientEntityList();
    if (!entityList)
        return nullptr;

    int playerIndex = index;
    if (playerIndex < 0)
    {
        if (IEngineClient *engineClient = GetEngineClient())
            playerIndex = engineClient->GetLocalPlayer();

        if (playerIndex < 1)
            playerIndex = Portal1::Constants::kSinglePlayerLocalIndex;
    }

    return reinterpret_cast<C_Portal_Player *>(entityList->GetClientEntity(playerIndex));
}

C_Portal_Player *Game::GetLocalPortalPlayer()
{
    return GetPortalPlayer(-1);
}

int Game::GetLocalPlayerIndex()
{
    if (IEngineClient *engineClient = GetEngineClient())
    {
        const int localIndex = engineClient->GetLocalPlayer();
        if (localIndex > 0)
            return localIndex;
    }

    return GetLocalPortalPlayer() ? Portal1::Constants::kSinglePlayerLocalIndex : -1;
}

bool Game::IsInGame()
{
    if (IEngineClient *engineClient = GetEngineClient())
        return engineClient->IsInGame();

    return GetLocalPortalPlayer() != nullptr;
}

bool Game::GetViewAngles(QAngle &angle)
{
    C_Portal_Player *localPlayer = GetLocalPortalPlayer();
    if (!localPlayer)
        return false;

    angle = localPlayer->GetEyeAngles();
    return true;
}

bool Game::SetViewAngles(const QAngle &angle)
{
    C_Portal_Player *localPlayer = GetLocalPortalPlayer();
    if (!localPlayer)
        return false;

    localPlayer->SetEyeAngles(angle);
    return true;
}

bool Game::IsCursorVisible()
{
    ISurface *surface = GetVguiSurface();
    return surface != nullptr && surface->IsCursorVisible();
}

bool Game::IsScreenSizeOverrideActive()
{
    ISurface *surface = GetVguiSurface();
    return surface != nullptr && surface->IsScreenSizeOverrideActive();
}

bool Game::GetScreenSize(int &wide, int &tall)
{
    ISurface *surface = GetVguiSurface();
    if (!surface)
        return false;

    surface->GetScreenSize(wide, tall);
    return true;
}

bool Game::ForceScreenSizeOverride(bool state, int wide, int tall)
{
    ISurface *surface = GetVguiSurface();
    return surface != nullptr && surface->ForceScreenSizeOverride(state, wide, tall);
}

void Game::OnScreenSizeChanged(int oldWidth, int oldHeight)
{
    ISurface *surface = GetVguiSurface();
    if (surface)
        surface->OnScreenSizeChanged(oldWidth, oldHeight);
}

bool Game::SetCursorPos(int x, int y)
{
    IInput *input = GetVguiInput();
    if (!input)
        return false;

    input->SetCursorPos(x, y);
    return true;
}

bool Game::InternalMouseWheeled(int delta)
{
    IInput *input = GetVguiInput();
    if (!input)
        return false;

    input->InternalMouseWheeled(delta);
    return true;
}

bool Game::TraceRay(const Ray_t &ray, unsigned int mask, CTraceFilter *traceFilter, CGameTrace *trace)
{
    IEngineTrace *engineTrace = GetEngineTrace();
    if (!engineTrace)
        return false;

    engineTrace->TraceRay(ray, mask, traceFilter, trace);
    return true;
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
    IClientEntityList *entityList = GetClientEntityList();
    return entityList ? reinterpret_cast<CBaseEntity *>(entityList->GetClientEntity(entityIndex)) : nullptr;
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
    if (IEngineClient *engineClient = GetEngineClient())
        engineClient->ClientCmd(szCmdString);
}

void Game::ClientCmd_Unrestricted(const char *szCmdString)
{
    if (IEngineClient *engineClient = GetEngineClient())
        engineClient->ClientCmd_Unrestricted(szCmdString);
}


