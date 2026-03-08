#pragma once
#include <cstdint>
#include <array>
#include "vector.h"

class IClientEntityList;
class IEngineTrace;
class IEngineClient;
class IMaterialSystem;
class IBaseClientDLL;
class IViewRender;
class IViewRender;
class CBaseEntity;
class IModelInfo;
class IModelRender;
class IMaterial;
class IInput;
class ISurface;
class IClientMode;
class C_BasePlayer;
class C_Portal_Player;
class CTraceFilter;
struct model_t;
struct Ray_t;
class CGameTrace;

class Game;
class Offsets;
class VR;
class Hooks;

extern Game *g_Game;

struct Player
{
    C_BasePlayer *pPlayer;
    bool isUsingVR;
    QAngle controllerAngle;
    Vector controllerPos;
    QAngle prevControllerAngle;

    Player()
        : isUsingVR(false),
        controllerAngle({ 0,0,0 }),
        controllerPos({ 0,0,0 }),
        prevControllerAngle({ 0,0,0 })
    {}
};

class Game
{
public:
    IClientEntityList* m_ClientEntityList = nullptr;
    IEngineTrace* m_EngineTrace = nullptr;
    IEngineClient* m_EngineClient = nullptr;
    IMaterialSystem* m_MaterialSystem = nullptr;
    IBaseClientDLL* m_BaseClientDll = nullptr;
    IViewRender* m_ClientViewRender = nullptr;
    IViewRender* m_EngineViewRender = nullptr;
    IModelInfo* m_ModelInfo = nullptr;
    IModelRender* m_ModelRender = nullptr;
    IInput* m_VguiInput = nullptr;
    ISurface* m_VguiSurface = nullptr;
    IClientMode* m_ClientMode = nullptr;

    uintptr_t m_BaseEngine;
    uintptr_t m_BaseClient;
    uintptr_t m_BaseServer;
    uintptr_t m_BaseMaterialSystem;
    uintptr_t m_BaseVgui2;

    Vector m_singlePlayerPortalColors[3] = { Vector(255.0f, 255.0f, 255.0f), Vector(64.0f, 160.0f, 255.0f), Vector(255.0f, 160.0f, 32.0f) };

    Offsets *m_Offsets = nullptr;
    VR *m_VR = nullptr;
    Hooks *m_Hooks = nullptr;

    bool m_Initialized = false;
    bool m_VrBootstrapAttempted = false;
    uint32_t m_LastRuntimeInterfaceResolveTick = 0;
    bool m_LoggedVrInterfaceReady = false;
    uint32_t m_LastClientModeResolveTick = 0;
    uint32_t m_LastClientViewRenderResolveTick = 0;
    uint32_t m_LastClientEntityListResolveTick = 0;
    uint32_t m_LastEngineTraceResolveTick = 0;
    uint32_t m_LastEngineClientResolveTick = 0;
    uint32_t m_LastModelInfoResolveTick = 0;
    uint32_t m_LastModelRenderResolveTick = 0;
    uint32_t m_LastVguiInputResolveTick = 0;
    uint32_t m_LastVguiSurfaceResolveTick = 0;
    std::array<Player, 24> m_PlayersVRInfo;
    int m_CurrentUsercmdID = -1;

    model_t *m_ArmsModel = nullptr;
    IMaterial *m_ArmsMaterial = nullptr;
    bool m_CachedArmsModel = false;

    Game();
    void EnsureVrBootstrap();
    bool TryResolveVrInterfaces(bool force = false);
    bool HasVrRuntimeInterfaces() const;
    IClientMode *GetClientMode(bool force = false);
    IViewRender *GetClientViewRender(bool force = false);
    IClientEntityList *GetClientEntityList(bool force = false);
    IEngineTrace *GetEngineTrace(bool force = false);
    IEngineClient *GetEngineClient(bool force = false);
    IMaterialSystem *GetMaterialSystem(bool force = false);
    IModelInfo *GetModelInfo(bool force = false);
    IModelRender *GetModelRender(bool force = false);
    IInput *GetVguiInput(bool force = false);
    ISurface *GetVguiSurface(bool force = false);
    C_Portal_Player *GetPortalPlayer(int index = -1);
    C_Portal_Player *GetLocalPortalPlayer();
    int GetLocalPlayerIndex();
    bool IsInGame();
    bool GetViewAngles(QAngle &angle);
    bool SetViewAngles(const QAngle &angle);
    bool IsCursorVisible();
    bool IsScreenSizeOverrideActive();
    bool GetScreenSize(int &wide, int &tall);
    bool ForceScreenSizeOverride(bool state, int wide, int tall);
    void OnScreenSizeChanged(int oldWidth, int oldHeight);
    bool SetCursorPos(int x, int y);
    bool InternalMouseWheeled(int delta);
    bool TraceRay(const Ray_t &ray, unsigned int mask, CTraceFilter *traceFilter, CGameTrace *trace);

    void *GetInterface(const char *dllname, const char *interfacename, bool required = true);
    void *GetModuleOffset(const char *dllname, uintptr_t offset, bool required = true);

    static void errorMsg(const char *msg);

    CBaseEntity *GetClientEntity(int entityIndex);
    char *getNetworkName(uintptr_t *entity);
    void ClientCmd(const char *szCmdString);
    void ClientCmd_Unrestricted(const char *szCmdString);

    typedef void *(__cdecl *tCreateInterface)(const char *name, int *returnCode);
};

