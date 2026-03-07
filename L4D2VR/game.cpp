#include "game.h"
#include <Windows.h>
#include <iostream>
#include "sdk.h"
#include "vr.h"
#include "hooks.h"
#include "offsets.h"
#include "sigscanner.h"

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

    m_ClientEntityList = (IClientEntityList *)GetInterface("client.dll", "VClientEntityList003");
    m_EngineTrace = (IEngineTrace *)GetInterface("engine.dll", "EngineTraceClient003");
    m_EngineClient = (IEngineClient *)GetInterface("engine.dll", "VEngineClient014");
    m_MaterialSystem = (IMaterialSystem *)GetInterface("MaterialSystem.dll", "VMaterialSystem080");
    m_ClientViewRender = (IViewRender *)GetInterface("client.dll", "VEngineRenderView014");
    m_EngineViewRender = (IViewRender *)GetInterface("engine.dll", "VEngineRenderView014");
    m_ModelInfo = (IModelInfo *)GetInterface("engine.dll", "VModelInfoClient006");
    m_ModelRender = (IModelRender *)GetInterface("engine.dll", "VEngineModel016");
    m_VguiInput = (IInput *)GetInterface("vgui2.dll", "VGUI_InputInternal001");
    m_VguiSurface = (ISurface *)GetInterface("vguimatsurface.dll", "VGUI_Surface030");

    m_Offsets = new Offsets();

    m_VR = new VR(this);
    m_Hooks = new Hooks(this);

    m_Initialized = true;
}

void *Game::GetInterface(const char *dllname, const char *interfacename)
{
    tCreateInterface CreateInterface = (tCreateInterface)GetProcAddress(GetModuleHandle(dllname), "CreateInterface");
    if (!CreateInterface)
    {
        std::string error = "Missing CreateInterface in ";
        error += dllname;
        Game::errorMsg(error.c_str());
        return nullptr;
    }

    int returnCode = 0;
    void *createdInterface = CreateInterface(interfacename, &returnCode);
    if (!createdInterface)
    {
        std::string error = "Failed to get interface ";
        error += interfacename;
        error += " from ";
        error += dllname;
        Game::errorMsg(error.c_str());
    }

    return createdInterface;
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


