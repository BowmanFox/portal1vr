#include "vr.h"
#include <Windows.h>
#include "sdk.h"
#include "game.h"
#include "hooks.h"
#include "trace.h"
#include <iostream>
#include <fstream>
#include <sstream>
#include <unordered_map>
#include <string>
#include <filesystem>
#include <thread>
#include <type_traits>
#include <algorithm>
#include <cstring>
#include "../dxvk/src/d3d9/d3d9_vr.h"
#include "debuglog.h"
#include "cameracollision.h"

namespace
{
    constexpr bool kEnableVrMenuSubmission = true;
    constexpr bool kEnableVrMenuInput = true;
    constexpr bool kEnableConfigWatcher = false;
    constexpr bool kEnableMaterialSystemEyeTargets = true;

    bool GetRuntimeBaseDirectory(char *buffer, size_t bufferSize)
    {
        if (!buffer || bufferSize == 0)
            return false;

        HMODULE module = GetModuleHandleA("d3d9.dll");
        if (!module)
            return false;

        const DWORD length = GetModuleFileNameA(module, buffer, static_cast<DWORD>(bufferSize));
        if (length == 0 || length >= bufferSize)
            return false;

        char *lastSlash = strrchr(buffer, '\\');
        if (!lastSlash)
            return false;

        *lastSlash = '\0';
        return true;
    }

    void GetOverlayWindowSize(const VR &vr, int &width, int &height)
    {
        width = static_cast<int>(vr.m_VKBackBuffer.m_VulkanData.m_nWidth);
        height = static_cast<int>(vr.m_VKBackBuffer.m_VulkanData.m_nHeight);

        if (width <= 0)
            width = static_cast<int>(vr.m_RenderWidth);
        if (height <= 0)
            height = static_cast<int>(vr.m_RenderHeight);
    }
}

VR::VR(Game *game) 
{
    m_Game = game;
    PortalVrLog("VR::VR start");

    vr::HmdError error = vr::VRInitError_None;
    m_System = vr::VR_Init(&error, vr::VRApplication_Scene);

    if (error != vr::VRInitError_None) 
    {
        PortalVrLog("VR_Init failed error=%d (%s); retrying when SteamVR is ready", error, vr::VR_GetVRInitErrorAsEnglishDescription(error));
        return;
    }
    PortalVrLog("VR_Init succeeded");

    if (!vr::VRCompositor())
    {
        PortalVrLog("VRCompositor init failed");
        vr::VR_Shutdown();
        return;
    }
    PortalVrLog("VRCompositor ready");

    m_Input = vr::VRInput();
    m_System = vr::OpenVRInternal_ModuleContext().VRSystem();
    if (!m_Input || !m_System)
    {
        PortalVrLog("OpenVR system or input interface unavailable");
        vr::VR_Shutdown();
        return;
    }

    m_System->GetRecommendedRenderTargetSize(&m_RenderWidth, &m_RenderHeight);
    m_AntiAliasing = 0;
    PortalVrLog("Recommended render target %u x %u", m_RenderWidth, m_RenderHeight);

    float l_left = 0.0f, l_right = 0.0f, l_top = 0.0f, l_bottom = 0.0f;
    m_System->GetProjectionRaw(vr::EVREye::Eye_Left, &l_left, &l_right, &l_top, &l_bottom);

    float r_left = 0.0f, r_right = 0.0f, r_top = 0.0f, r_bottom = 0.0f;
    m_System->GetProjectionRaw(vr::EVREye::Eye_Right, &r_left, &r_right, &r_top, &r_bottom);

    float tanHalfFov[2];

    tanHalfFov[0] = std::max({ -l_left, l_right, -r_left, r_right });
    tanHalfFov[1] = std::max({ -l_top, l_bottom, -r_top, r_bottom });

    // Each eye is rendered into its own complete symmetric Source target.
    // Submitting asymmetric raw-projection bounds here double-applies the
    // lens shift and makes the left eye appear cropped/warped in the headset.
    m_TextureBounds[0] = { 0, 0, 1, 1 };
    m_TextureBounds[1] = { 0, 0, 1, 1 };

    m_Aspect = tanHalfFov[0] / tanHalfFov[1];
    m_Fov = 2.0f * atan(tanHalfFov[0]) * 360 / (3.14159265358979323846 * 2);

    InstallApplicationManifest("manifest.vrmanifest");
    if (SetActionManifest("action_manifest.json") != 0)
    {
        PortalVrLog("VR initialization stopped: action manifest unavailable");
        vr::VR_Shutdown();
        return;
    }
    ParseConfigFile();

    if (kEnableConfigWatcher)
    {
        std::thread configParser(&VR::WaitForConfigUpdate, this);
        configParser.detach();
        PortalVrLog("Config watcher started");
    }
    else
    {
        PortalVrLog("Config watcher disabled");
    }

    if (!g_D3DVR9)
    {
        PortalVrLog("VR::VR aborted: D3D9 VR interop not ready");
        vr::VR_Shutdown();
        return;
    }
    PortalVrLog("g_D3DVR9 ready");

    g_D3DVR9->GetBackBufferData(&m_VKBackBuffer);
    PortalVrLog(
        "Backbuffer ready width=%u height=%u",
        m_VKBackBuffer.m_VulkanData.m_nWidth,
        m_VKBackBuffer.m_VulkanData.m_nHeight);
    if (kEnableVrMenuSubmission || kEnableVrMenuInput)
    {
        m_Overlay = vr::VROverlay();
        if (m_Overlay)
        {
            m_Overlay->CreateOverlay("MenuOverlayKey", "MenuOverlay", &m_MainMenuHandle);
            m_Overlay->SetOverlayInputMethod(m_MainMenuHandle, vr::VROverlayInputMethod_Mouse);
            m_Overlay->SetOverlayFlag(m_MainMenuHandle, vr::VROverlayFlags_SendVRDiscreteScrollEvents, true);

            const vr::HmdVector2_t mouseScaleMenu = {
                static_cast<float>(m_RenderWidth),
                static_cast<float>(m_RenderHeight)
            };
            m_Overlay->SetOverlayCurvature(m_MainMenuHandle, 0.15f);
            m_Overlay->SetOverlayMouseScale(m_MainMenuHandle, &mouseScaleMenu);
        }
    }
    else
    {
        PortalVrLog("VR menu overlay initialization skipped");
    }

    UpdatePosesAndActions();
    GetPoses();
    ResetPosition();
    PortalVrLog("UpdatePosesAndActions complete");

    if (!kEnableMaterialSystemEyeTargets)
        PortalVrLog("Using backbuffer VR submit path; materialsystem eye targets disabled");

    m_IsInitialized = true;
    m_IsVREnabled = true;
    PortalVrLog("VR::VR complete");
}

int VR::SetActionManifest(const char *fileName) 
{
    char currentDir[MAX_STR_LEN];
    if (!GetRuntimeBaseDirectory(currentDir, ARRAYSIZE(currentDir)))
    {
        PortalVrLog("SetActionManifest failed: runtime base directory unavailable");
        Game::errorMsg("Failed to resolve runtime directory for action manifest");
        return 1;
    }

    char path[MAX_STR_LEN];
    sprintf_s(path, MAX_STR_LEN, "%s\\VR\\SteamVRActionManifest\\%s", currentDir, fileName);
    PortalVrLog("SetActionManifest path=%s", path);

    if (m_Input->SetActionManifestPath(path) != vr::VRInputError_None) 
    {
        Game::errorMsg("SetActionManifestPath failed");
        return 1;
    }

    m_Input->GetActionHandle("/actions/main/in/ActivateVR", &m_ActionActivateVR);
    m_Input->GetActionHandle("/actions/main/in/Jump", &m_ActionJump);
    m_Input->GetActionHandle("/actions/main/in/PrimaryAttack", &m_ActionPrimaryAttack);
    m_Input->GetActionHandle("/actions/main/in/Reload", &m_ActionReload);
    m_Input->GetActionHandle("/actions/main/in/Use", &m_ActionUse);
    m_Input->GetActionHandle("/actions/main/in/Walk", &m_ActionWalk);
    m_Input->GetActionHandle("/actions/main/in/Turn", &m_ActionTurn);
    m_Input->GetActionHandle("/actions/main/in/SecondaryAttack", &m_ActionSecondaryAttack);
    m_Input->GetActionHandle("/actions/main/in/NextItem", &m_ActionNextItem);
    m_Input->GetActionHandle("/actions/main/in/PrevItem", &m_ActionPrevItem);
    m_Input->GetActionHandle("/actions/main/in/ResetPosition", &m_ActionResetPosition);
    m_Input->GetActionHandle("/actions/main/in/Crouch", &m_ActionCrouch);
    m_Input->GetActionHandle("/actions/main/in/Flashlight", &m_ActionFlashlight);
    m_Input->GetActionHandle("/actions/main/in/MenuSelect", &m_MenuSelect);
    m_Input->GetActionHandle("/actions/main/in/MenuBack", &m_MenuBack);
    m_Input->GetActionHandle("/actions/main/in/MenuUp", &m_MenuUp);
    m_Input->GetActionHandle("/actions/main/in/MenuDown", &m_MenuDown);
    m_Input->GetActionHandle("/actions/main/in/MenuLeft", &m_MenuLeft);
    m_Input->GetActionHandle("/actions/main/in/MenuRight", &m_MenuRight);
    m_Input->GetActionHandle("/actions/main/in/Spray", &m_Spray);
    m_Input->GetActionHandle("/actions/main/in/Scoreboard", &m_Scoreboard);
    m_Input->GetActionHandle("/actions/main/in/ShowHUD", &m_ShowHUD);
    m_Input->GetActionHandle("/actions/main/in/Pause", &m_Pause);
	if (m_Input->GetActionHandle("/actions/base/in/skeleton_lefthand", &m_ActionSkeletonLeft) != vr::VRInputError_None)
		m_ActionSkeletonLeft = 0;
	if (m_Input->GetActionHandle("/actions/base/in/skeleton_righthand", &m_ActionSkeletonRight) != vr::VRInputError_None)
		m_ActionSkeletonRight = 0;

    m_Input->GetActionSetHandle("/actions/main", &m_ActionSet);
    m_Input->GetActionSetHandle("/actions/base", &m_BaseActionSet);
    m_ActiveActionSet = {};
    m_ActiveActionSet.ulActionSet = m_ActionSet;

    return 0;
}

void VR::InstallApplicationManifest(const char *fileName)
{
    char currentDir[MAX_STR_LEN];
    if (!GetRuntimeBaseDirectory(currentDir, ARRAYSIZE(currentDir)))
    {
        PortalVrLog("InstallApplicationManifest failed: runtime base directory unavailable");
        return;
    }

    char path[MAX_STR_LEN];
    sprintf_s(path, MAX_STR_LEN, "%s\\VR\\%s", currentDir, fileName);
    PortalVrLog("InstallApplicationManifest path=%s", path);

    vr::VRApplications()->AddApplicationManifest(path);
}

void VR::SetScreenSizeOverride(bool bState) {
    bool isOverriding = m_Game->IsScreenSizeOverrideActive();

    if (bState && !isOverriding || !bState && isOverriding) {
        int iOldWidth, iOldHeight;
        if (!m_Game->GetScreenSize(iOldWidth, iOldHeight))
            return;

        m_Game->ForceScreenSizeOverride(bState, m_RenderWidth, m_RenderHeight);
       /*int x = 0, y = 0, w = m_RenderWidth, h = m_RenderHeight;

        if (m_Game->m_ClientMode->GetViewport())
            m_Game->m_ClientMode->AdjustEngineViewport(x, y, w, h);*/

        if (bState) {
            /*IMatRenderContext* renderContext = m_Game->m_MaterialSystem->GetRenderContext();
            renderContext->Viewport(0, 0, m_RenderWidth, m_RenderHeight);
            renderContext->Release();*/
        }
        m_Game->OnScreenSizeChanged(iOldWidth, iOldHeight);
    }
}

void VR::Update()
{
    if (!m_IsInitialized || !m_Game->m_Initialized)
        return;

    const bool hasGameplayInterfaces = m_Game->GetLocalPortalPlayer() != nullptr
        && m_Game->GetEngineTrace() != nullptr;
    const bool cursorVisible = m_Game->IsCursorVisible();
    const bool inGame = m_Game->IsInGame();
    static bool loggedUpdateEntry = false;
    static bool loggedAfterSubmit = false;
    static bool loggedAfterPoses = false;
    static bool loggedAfterTracking = false;
    static bool loggedSkippedMenuInput = false;
    static bool loggedAfterInput = false;
    static bool loggedSkippedGameplayInput = false;
    static bool wasInGame = false;

    if (!loggedUpdateEntry)
    {
        PortalVrLog("VR::Update first entry cursorVisible=%d inGame=%d gameplayInterfaces=%d", cursorVisible, inGame, hasGameplayInterfaces);
        loggedUpdateEntry = true;
    }

    if (m_IsVREnabled && g_D3DVR9)
    {
        //SetScreenSizeOverride(inGame);

        // Only force a texture rebuild when transitioning out of gameplay.
        if (!inGame)
        {
            m_CameraCollisionOffset = { 0, 0, 0 };
            m_CameraBlocked = false;
            m_Game->m_CachedArmsModel = false;
            if (wasInGame)
                m_CreatedVRTextures = false;
        } 

        if (kEnableMaterialSystemEyeTargets && !m_CreatedVRTextures)
        {
            PortalVrLog("VR::Update creating VR textures outside RenderView");
            CreateVRTextures();
        }
    }

    wasInGame = inGame;

    SubmitVRTextures();
    if (!loggedAfterSubmit)
    {
        PortalVrLog("VR::Update completed SubmitVRTextures");
        loggedAfterSubmit = true;
    }

    UpdatePosesAndActions();
    if (!loggedAfterPoses)
    {
        PortalVrLog("VR::Update completed UpdatePosesAndActions");
        loggedAfterPoses = true;
    }

    UpdateTracking();
    if (!loggedAfterTracking)
    {
        PortalVrLog("VR::Update completed UpdateTracking");
        loggedAfterTracking = true;
    }

    if (cursorVisible) {
        if (!kEnableVrMenuInput)
        {
            if (!loggedSkippedMenuInput)
            {
                PortalVrLog("VR::Update skipped VR menu input");
                loggedSkippedMenuInput = true;
            }
            return;
        }

        ProcessMenuInput();
    } else if (hasGameplayInterfaces) {
        ProcessInput();
        if (!loggedAfterInput)
        {
            PortalVrLog("VR::Update completed ProcessInput");
            loggedAfterInput = true;
        }
    } else if (!loggedSkippedGameplayInput) {
        PortalVrLog("VR::Update skipped gameplay input because gameplay interfaces are unavailable");
        loggedSkippedGameplayInput = true;
    }
}

void VR::CreateVRTextures()
{
    if (m_CreatedVRTextures)
        return;

    IMaterialSystem *materialSystem = m_Game->GetMaterialSystem();
    if (!materialSystem)
    {
        PortalVrLog("CreateVRTextures skipped: material system unavailable");
        return;
    }

    PortalVrLog("CreateVRTextures start width=%u height=%u", m_RenderWidth, m_RenderHeight);

    materialSystem->BeginRenderTargetAllocation();

    m_CreatingTextureID = Texture_LeftEye;
    m_LeftEyeTexture = materialSystem->CreateNamedRenderTargetTextureEx("leftEye0", m_RenderWidth, m_RenderHeight, RT_SIZE_LITERAL, materialSystem->GetBackBufferFormat(), MATERIAL_RT_DEPTH_SEPARATE, TEXTUREFLAGS_NOMIP);
    
    m_CreatingTextureID = Texture_RightEye;
    m_RightEyeTexture = materialSystem->CreateNamedRenderTargetTextureEx("rightEye0", m_RenderWidth, m_RenderHeight, RT_SIZE_LITERAL, materialSystem->GetBackBufferFormat(), MATERIAL_RT_DEPTH_SEPARATE, TEXTUREFLAGS_NOMIP);
    m_CreatingTextureID = Texture_None;

    materialSystem->EndRenderTargetAllocation();

    m_CreatedVRTextures = m_LeftEyeTexture && m_RightEyeTexture
        && m_D9LeftEyeSurface && m_D9RightEyeSurface
        && m_VKLeftEye.m_VulkanData.m_nImage && m_VKRightEye.m_VulkanData.m_nImage;
    PortalVrLog(
        "CreateVRTextures complete this=%p left=%p right=%p created=%d",
        this,
        m_LeftEyeTexture,
        m_RightEyeTexture,
        m_CreatedVRTextures);
}

void VR::SubmitVRTextures()
{
    if (!g_D3DVR9 || FAILED(g_D3DVR9->GetBackBufferData(&m_VKBackBuffer)))
        return;
    auto *compositor = vr::VRCompositor();
    if (!compositor)
        return;

    const bool eyeFrame = m_RenderedNewFrame && m_CreatedVRTextures;
    if (m_Overlay)
    {
        if ((!eyeFrame || m_Game->IsCursorVisible()) && kEnableVrMenuSubmission)
        {
            if (!m_Overlay->IsOverlayVisible(m_MainMenuHandle))
                RepositionOverlays();
            vr::VRTextureBounds_t bounds{0, 0, 1, 1};
            const vr::HmdVector2_t mouseScale = {
                static_cast<float>(m_VKBackBuffer.m_VulkanData.m_nWidth),
                static_cast<float>(m_VKBackBuffer.m_VulkanData.m_nHeight) };
            m_Overlay->SetOverlayMouseScale(m_MainMenuHandle, &mouseScale);
            m_Overlay->SetOverlayTexelAspect(m_MainMenuHandle, 1.0f);
            m_Overlay->SetOverlayTextureBounds(m_MainMenuHandle, &bounds);
            auto error = m_Overlay->SetOverlayTexture(m_MainMenuHandle, &m_VKBackBuffer.m_VRTexture);
            static int lastOverlayError = -1;
            if (lastOverlayError != error)
            {
                PortalVrLog("Menu texture submission result=%d", error);
                lastOverlayError = error;
            }
            m_Overlay->ShowOverlay(m_MainMenuHandle);
        }
        else
            m_Overlay->HideOverlay(m_MainMenuHandle);
    }

    auto left = compositor->Submit(vr::Eye_Left,
        eyeFrame ? &m_VKLeftEye.m_VRTexture : &m_VKBackBuffer.m_VRTexture,
        eyeFrame ? &m_TextureBounds[0] : nullptr);
    auto right = compositor->Submit(vr::Eye_Right,
        eyeFrame ? &m_VKRightEye.m_VRTexture : &m_VKBackBuffer.m_VRTexture,
        eyeFrame ? &m_TextureBounds[1] : nullptr);
    static int lastLeft = -1, lastRight = -1;
    static unsigned frames = 0;
    static bool lastEyeFrame = false;
    if ((++frames % 600) == 0 || lastEyeFrame != eyeFrame || lastLeft != left || lastRight != right)
    {
        PortalVrLog("VR frame=%u eyes=%d submitLeft=%d submitRight=%d inGame=%d hmdTracked=%d cursor=%d", frames, eyeFrame, left, right,
            m_Game->IsInGame(), m_Poses[vr::k_unTrackedDeviceIndex_Hmd].bPoseIsValid, m_Game->IsCursorVisible());
        lastLeft = left;
        lastRight = right;
        lastEyeFrame = eyeFrame;
        vr::InputAnalogActionData_t walk{};
        auto inputError = m_Input->GetAnalogActionData(m_ActionWalk, &walk, sizeof(walk), vr::k_ulInvalidInputValueHandle);
        PortalVrLog("Tracking yaw=%f walkError=%d active=%d axes=%f,%f", m_HmdAngAbs.y, inputError, walk.bActive, walk.x, walk.y);
    }
    m_RenderedNewFrame = false;
}

void VR::GetPoseData(vr::TrackedDevicePose_t &poseRaw, TrackedDevicePoseData &poseOut)
{
    if (poseRaw.bPoseIsValid) 
    {
        vr::HmdMatrix34_t mat = poseRaw.mDeviceToAbsoluteTracking;
        Vector pos;
        Vector vel;
        QAngle ang;
        QAngle angvel;
        pos.x = -mat.m[2][3];
        pos.y = -mat.m[0][3];
        pos.z = mat.m[1][3];
        ang.x = asin(mat.m[1][2]) * (180.0 / 3.141592654);
        ang.y = atan2f(mat.m[0][2], mat.m[2][2]) * (180.0 / 3.141592654);
        ang.z = atan2f(-mat.m[1][0], mat.m[1][1]) * (180.0 / 3.141592654);
        vel.x = -poseRaw.vVelocity.v[2];
        vel.y = -poseRaw.vVelocity.v[0];
        vel.z = poseRaw.vVelocity.v[1];
        angvel.x = -poseRaw.vAngularVelocity.v[2] * (180.0 / 3.141592654);
        angvel.y = -poseRaw.vAngularVelocity.v[0] * (180.0 / 3.141592654);
        angvel.z = poseRaw.vAngularVelocity.v[1] * (180.0 / 3.141592654);

        poseOut.TrackedDevicePos = pos;
        poseOut.TrackedDeviceVel = vel;
        poseOut.TrackedDeviceAng = ang;
        poseOut.TrackedDeviceAngVel = angvel;
    }
}

void VR::RepositionOverlays()
{
    vr::TrackedDevicePose_t hmdPose = m_Poses[vr::k_unTrackedDeviceIndex_Hmd];
    vr::HmdMatrix34_t hmdMat = hmdPose.mDeviceToAbsoluteTracking;
    Vector hmdPosition = { hmdMat.m[0][3], hmdMat.m[1][3], hmdMat.m[2][3] };
    Vector hmdForward = { -hmdMat.m[0][2], 0, -hmdMat.m[2][2] };

    int windowWidth, windowHeight;
    GetOverlayWindowSize(*this, windowWidth, windowHeight);

    vr::HmdMatrix34_t menuTransform = 
    {
        1.0f, 0.0f, 0.0f, 0.0f,
        0.0f, 1.0f, 0.0f, 1.0f,
        0.0f, 0.0f, 1.0f, 1.0f
    };

    vr::ETrackingUniverseOrigin trackingOrigin = vr::VRCompositor()->GetTrackingSpace();

    // Reposition main menu overlay
    float renderWidth = m_VKBackBuffer.m_VulkanData.m_nWidth;
    float renderHeight = m_VKBackBuffer.m_VulkanData.m_nHeight;

    float widthRatio = windowWidth / renderWidth;
    float heightRatio = windowHeight / renderHeight;
    menuTransform.m[0][0] *= widthRatio;
    menuTransform.m[1][1] *= heightRatio;

    hmdForward[1] = 0;
    VectorNormalize(hmdForward);

    Vector menuDistance = hmdForward * 3;
    Vector menuNewPos = menuDistance + hmdPosition;

    menuTransform.m[0][3] = menuNewPos.x;
    menuTransform.m[1][3] = menuNewPos.y - 0.25;
    menuTransform.m[2][3] = menuNewPos.z;

    float xScale = menuTransform.m[0][0];
    float hmdRotationDegrees = atan2f(hmdMat.m[0][2], hmdMat.m[2][2]);

    menuTransform.m[0][0] *= cos(hmdRotationDegrees);
    menuTransform.m[0][2] = sin(hmdRotationDegrees);
    menuTransform.m[2][0] = -sin(hmdRotationDegrees) * xScale;
    menuTransform.m[2][2] *= cos(hmdRotationDegrees);

    vr::VROverlay()->SetOverlayTransformAbsolute(m_MainMenuHandle, trackingOrigin, &menuTransform);
    vr::VROverlay()->SetOverlayWidthInMeters(m_MainMenuHandle, 1.5 * (1.0 / heightRatio));

    // Reposition HUD overlay
    /*vr::HmdMatrix34_t hudTransform =
    {
        1.0f, 0.0f, 0.0f, 0.0f,
        0.0f, 1.0f, 0.0f, 0.0f,
        0.0f, 0.0f, 1.0f, 0.0f
    };

    Vector hudDistance = hmdForward * m_HudDistance;
    Vector hudNewPos = hudDistance + hmdPosition;

    hudTransform.m[0][3] = hudNewPos.x;
    hudTransform.m[1][3] = hudNewPos.y - 0.25;
    hudTransform.m[2][3] = hudNewPos.z;

    hudTransform.m[0][0] *= cos(hmdRotationDegrees);
    hudTransform.m[0][2] = sin(hmdRotationDegrees);
    hudTransform.m[2][0] = -sin(hmdRotationDegrees);
    hudTransform.m[2][2] *= cos(hmdRotationDegrees);

    vr::VROverlay()->SetOverlayTransformAbsolute(m_HUDHandle, trackingOrigin, &hudTransform);
    vr::VROverlay()->SetOverlayWidthInMeters(m_HUDHandle, m_HudSize);*/
}

void VR::GetPoses() 
{
    vr::TrackedDevicePose_t hmdPose = m_Poses[vr::k_unTrackedDeviceIndex_Hmd];

    vr::TrackedDeviceIndex_t leftControllerIndex = m_System->GetTrackedDeviceIndexForControllerRole(vr::TrackedControllerRole_LeftHand);
    vr::TrackedDeviceIndex_t rightControllerIndex = m_System->GetTrackedDeviceIndexForControllerRole(vr::TrackedControllerRole_RightHand);

    if (m_LeftHanded)
        std::swap(leftControllerIndex, rightControllerIndex);

    vr::TrackedDevicePose_t leftControllerPose{};
    vr::TrackedDevicePose_t rightControllerPose{};
    if (leftControllerIndex < vr::k_unMaxTrackedDeviceCount)
        leftControllerPose = m_Poses[leftControllerIndex];
    if (rightControllerIndex < vr::k_unMaxTrackedDeviceCount)
        rightControllerPose = m_Poses[rightControllerIndex];

    GetPoseData(hmdPose, m_HmdPose);
    GetPoseData(leftControllerPose, m_LeftControllerPose);
    GetPoseData(rightControllerPose, m_RightControllerPose);
}

void VR::UpdatePosesAndActions() 
{
    static unsigned int loggedPoses = 0;
    if (loggedPoses++ < 3)
        PortalVrLog("Pose update this=%p poses=%p compositor=%p input=%p", this, m_Poses, vr::VRCompositor(), m_Input);
    vr::VRCompositor()->WaitGetPoses(m_Poses, vr::k_unMaxTrackedDeviceCount, NULL, 0);
    vr::VRActiveActionSet_t actionSets[2] = { m_ActiveActionSet, {} };
    actionSets[1].ulActionSet = m_BaseActionSet;
    m_Input->UpdateActionState(actionSets, sizeof(vr::VRActiveActionSet_t), m_BaseActionSet ? 2 : 1);

	// SteamVR can provide finger curl even when the controller has no full
	// skeletal tracking. Keep the last good pose and use a relaxed fallback so
	// custom hands never render as board-flat fists on runtimes without it.
	auto updateFingerSummary = [this](vr::VRActionHandle_t action, float *curl, bool &valid) {
		static bool reportedMissing = false;
		if (!action) { valid = false; if (!reportedMissing) { PortalVrLog("Finger skeleton action unavailable; using relaxed pose"); reportedMissing = true; } return; }
		vr::VRSkeletalSummaryData_t summary{};
		const auto error = m_Input->GetSkeletalSummaryData(action, vr::VRSummaryType_FromDevice, &summary);
		if (error != vr::VRInputError_None) { valid = false; if (!reportedMissing) { PortalVrLog("Finger skeleton data unavailable error=%d; using relaxed pose", error); reportedMissing = true; } return; }
		float sampledCurl[5]{};
		bool anyCurl = false;
		for (int i = 0; i < 5; ++i)
		{
			sampledCurl[i] = std::clamp(summary.flFingerCurl[i], 0.0f, 1.0f);
			anyCurl = anyCurl || sampledCurl[i] > 0.02f;
		}
		// Pico's compatibility layer can return a successful all-zero summary
		// even though it has no skeletal stream. Keep the relaxed fallback in
		// that case instead of turning every finger into a board-flat pose.
		if (!anyCurl) {
			valid = false;
			if (!reportedMissing) { PortalVrLog("Finger skeleton returned zero curl; using relaxed pose"); reportedMissing = true; }
			return;
		}
		for (int i = 0; i < 5; ++i) curl[i] = sampledCurl[i];
		valid = true;
		if (!reportedMissing) { PortalVrLog("Finger skeleton curl=%.2f,%.2f,%.2f,%.2f,%.2f", curl[0], curl[1], curl[2], curl[3], curl[4]); reportedMissing = true; }
	};
	updateFingerSummary(m_ActionSkeletonLeft, m_LeftFingerCurl, m_LeftSkeletonValid);
	updateFingerSummary(m_ActionSkeletonRight, m_RightFingerCurl, m_RightSkeletonValid);
}

void VR::GetViewParameters() 
{
    vr::HmdMatrix34_t eyeToHeadLeft = m_System->GetEyeToHeadTransform(vr::Eye_Left);
    vr::HmdMatrix34_t eyeToHeadRight = m_System->GetEyeToHeadTransform(vr::Eye_Right);
    m_EyeToHeadTransformPosLeft.x = eyeToHeadLeft.m[0][3];
    m_EyeToHeadTransformPosLeft.y = eyeToHeadLeft.m[1][3];
    m_EyeToHeadTransformPosLeft.z = eyeToHeadLeft.m[2][3];

    m_EyeToHeadTransformPosRight.x = eyeToHeadRight.m[0][3];
    m_EyeToHeadTransformPosRight.y = eyeToHeadRight.m[1][3];
    m_EyeToHeadTransformPosRight.z = eyeToHeadRight.m[2][3];
}

bool VR::PressedDigitalAction(vr::VRActionHandle_t &actionHandle, bool checkIfActionChanged)
{
    vr::InputDigitalActionData_t digitalActionData;
    vr::EVRInputError result = m_Input->GetDigitalActionData(actionHandle, &digitalActionData, sizeof(digitalActionData), vr::k_ulInvalidInputValueHandle);
    
    if (result == vr::VRInputError_None)
    {
        if (checkIfActionChanged)
            return digitalActionData.bState && digitalActionData.bChanged;
        else
            return digitalActionData.bState;
    }

    return false;
}

bool VR::GetAnalogActionData(vr::VRActionHandle_t &actionHandle, vr::InputAnalogActionData_t &analogDataOut)
{
    vr::EVRInputError result = m_Input->GetAnalogActionData(actionHandle, &analogDataOut, sizeof(analogDataOut), vr::k_ulInvalidInputValueHandle);

    if (result == vr::VRInputError_None)
        return true;

    return false;
}

void VR::ProcessMenuInput()
{
    //vr::VROverlayHandle_t currentOverlay = m_Game->m_EngineClient->IsInGame() ? m_HUDHandle : m_MainMenuHandle;
    vr::VROverlayHandle_t currentOverlay = m_MainMenuHandle;

    // Check if left or right hand controller is pointing at the overlay
    const bool isHoveringOverlay = CheckOverlayIntersectionForController(currentOverlay, vr::TrackedControllerRole_LeftHand) ||
                                   CheckOverlayIntersectionForController(currentOverlay, vr::TrackedControllerRole_RightHand);

    // Overlays can't process action inputs if the laser is active, so
    // only activate laser if a controller is pointing at the overlay
    if (isHoveringOverlay)
    {
        vr::VROverlay()->SetOverlayFlag(currentOverlay, vr::VROverlayFlags_MakeOverlaysInteractiveIfVisible, true);

        int windowWidth, windowHeight;
        GetOverlayWindowSize(*this, windowWidth, windowHeight);

        vr::VREvent_t vrEvent;
        while (vr::VROverlay()->PollNextOverlayEvent(currentOverlay, &vrEvent, sizeof(vrEvent)))
        {
            INPUT input{};
            switch (vrEvent.eventType)
            {
            case vr::VREvent_MouseMove:
            {
                float laserX = vrEvent.data.mouse.x;
                float laserY = vrEvent.data.mouse.y;

                laserY = windowHeight - laserY;

                m_Game->SetCursorPos(static_cast<int>(laserX), static_cast<int>(laserY));
                break;
            }

            case vr::VREvent_MouseButtonDown:
                // Don't allow holding down the mouse down in the pause menu. The resume button can be clicked before
                // the MouseButtonUp event is polled, which causes issues with the overlay.
                if (currentOverlay == m_MainMenuHandle)
                {
                    input.type = INPUT_MOUSE;
                    input.mi.dwFlags = MOUSEEVENTF_LEFTDOWN;
                    SendInput(1, &input, sizeof(INPUT));
                }
                break;

            case vr::VREvent_MouseButtonUp:
                /*if (currentOverlay == m_HUDHandle)
                {
                    input.type = INPUT_MOUSE;
                    input.mi.dwFlags = MOUSEEVENTF_LEFTDOWN;
                    SendInput(1, &input, sizeof(INPUT));
                }*/
                input.type = INPUT_MOUSE;
                input.mi.dwFlags = MOUSEEVENTF_LEFTUP;
                SendInput(1, &input, sizeof(INPUT));
                break;

            case vr::VREvent_ScrollDiscrete:
                m_Game->InternalMouseWheeled((int)vrEvent.data.scroll.ydelta);
                break;
            }
        }
    }
    else
    {
        vr::VROverlay()->SetOverlayFlag(currentOverlay, vr::VROverlayFlags_MakeOverlaysInteractiveIfVisible, false);
        
        if (PressedDigitalAction(m_MenuSelect, true))
        {
            INPUT input {};
            input.type = INPUT_KEYBOARD;
            input.ki.wVk = VK_RETURN;
            SendInput(1, &input, sizeof(INPUT));
            input.ki.dwFlags = KEYEVENTF_KEYUP;
            SendInput(1, &input, sizeof(INPUT));
        }
        if (PressedDigitalAction(m_MenuBack, true) || PressedDigitalAction(m_Pause, true))
        {
            INPUT input {};
            input.type = INPUT_KEYBOARD;
            input.ki.wVk = VK_ESCAPE;
            SendInput(1, &input, sizeof(INPUT));
            input.ki.dwFlags = KEYEVENTF_KEYUP;
            SendInput(1, &input, sizeof(INPUT));
        }
        if (PressedDigitalAction(m_MenuUp, true))
        {
            INPUT input {};
            input.type = INPUT_KEYBOARD;
            input.ki.wVk = VK_UP;
            SendInput(1, &input, sizeof(INPUT));
            input.ki.dwFlags = KEYEVENTF_KEYUP;
            SendInput(1, &input, sizeof(INPUT));
        }
        if (PressedDigitalAction(m_MenuDown, true))
        {
            INPUT input {};
            input.type = INPUT_KEYBOARD;
            input.ki.wVk = VK_DOWN;
            SendInput(1, &input, sizeof(INPUT));
            input.ki.dwFlags = KEYEVENTF_KEYUP;
            SendInput(1, &input, sizeof(INPUT));
        }
        if (PressedDigitalAction(m_MenuLeft, true))
        {
            INPUT input {};
            input.type = INPUT_KEYBOARD;
            input.ki.wVk = VK_LEFT;
            SendInput(1, &input, sizeof(INPUT));
            input.ki.dwFlags = KEYEVENTF_KEYUP;
            SendInput(1, &input, sizeof(INPUT));
        }
        if (PressedDigitalAction(m_MenuRight, true))
        {
            INPUT input {};
            input.type = INPUT_KEYBOARD;
            input.ki.wVk = VK_RIGHT;
            SendInput(1, &input, sizeof(INPUT));
            input.ki.dwFlags = KEYEVENTF_KEYUP;
            SendInput(1, &input, sizeof(INPUT));
        }
    }
}

void VR::ProcessInput()
{
    if (!m_IsVREnabled)
        return;

    //vr::VROverlay()->SetOverlayFlag(m_HUDHandle, vr::VROverlayFlags_MakeOverlaysInteractiveIfVisible, false);

    typedef std::chrono::duration<float, std::milli> duration;
    auto currentTime = std::chrono::steady_clock::now();
    duration elapsed = currentTime - m_PrevFrameTime;
    float deltaTime = elapsed.count();
    m_PrevFrameTime = currentTime;

    vr::InputAnalogActionData_t analogActionData;

    if (GetAnalogActionData(m_ActionTurn, analogActionData))
    {
        if (m_SnapTurning)
        {
            if (!m_PressedTurn && analogActionData.x > 0.5)
            {
                m_RotationOffset.y -= m_SnapTurnAngle;
                m_PressedTurn = true;
            }
            else if (!m_PressedTurn && analogActionData.x < -0.5)
            {
                m_RotationOffset.y += m_SnapTurnAngle;
                m_PressedTurn = true;
            }
            else if (analogActionData.x < 0.3 && analogActionData.x > -0.3)
                m_PressedTurn = false;
        }
        // Smooth turning
        else
        {
            float deadzone = 0.2;
            // smoother turning
            float xNormalized = (abs(analogActionData.x) - deadzone) / (1 - deadzone);
            if (analogActionData.x > deadzone)
            {
                m_RotationOffset.y -= m_TurnSpeed * deltaTime * xNormalized;
            }
            if (analogActionData.x < -deadzone)
            {
                m_RotationOffset.y += m_TurnSpeed * deltaTime * xNormalized;
            }
        }

        // Wrap from 0 to 360
        m_RotationOffset.y -= 360 * std::floor(m_RotationOffset.y / 360);
    }

    if (PressedDigitalAction(m_ActionPrimaryAttack))
    {
        m_Game->ClientCmd_Unrestricted("+attack");
    }
    else
    {
        m_Game->ClientCmd_Unrestricted("-attack");
    }

    if (PressedDigitalAction(m_ActionSecondaryAttack))
    {
        m_Game->ClientCmd_Unrestricted("+attack2");
    }
    else
    {
        m_Game->ClientCmd_Unrestricted("-attack2");
    }

    if (PressedDigitalAction(m_ActionJump))
    {
        m_Game->ClientCmd_Unrestricted("+jump");
    }
    else
    {
        m_Game->ClientCmd_Unrestricted("-jump");
    }

    if (PressedDigitalAction(m_ActionCrouch))
    {
        m_Game->ClientCmd_Unrestricted("+duck");
    }
    else
    {
        m_Game->ClientCmd_Unrestricted("-duck");
    }

    if (PressedDigitalAction(m_ActionUse))
    {
        m_Game->ClientCmd_Unrestricted("+use");
    }
    else
    {
        m_Game->ClientCmd_Unrestricted("-use");
    }

    if (PressedDigitalAction(m_ActionReload))
    {
        m_Game->ClientCmd_Unrestricted("+reload");
    }
    else
    {
        m_Game->ClientCmd_Unrestricted("-reload");
    }

    if (PressedDigitalAction(m_ActionPrevItem, true))
    {
        m_Game->ClientCmd_Unrestricted("invprev");
    }
    else if (PressedDigitalAction(m_ActionNextItem, true))
    {
        m_Game->ClientCmd_Unrestricted("invnext");
    }

    if (PressedDigitalAction(m_ActionResetPosition, true))
    {
        ResetPosition();
    }

    if (PressedDigitalAction(m_ActionFlashlight, true))
    {
        m_Game->ClientCmd_Unrestricted("impulse 100");
    }

    if (PressedDigitalAction(m_Spray, true))
    {
        m_Game->ClientCmd_Unrestricted("impulse 201");
    }
    
    /*bool isControllerVertical = m_RightControllerAngAbs.x > 60 || m_RightControllerAngAbs.x < -45;
    if ((PressedDigitalAction(m_ShowHUD) || PressedDigitalAction(m_Scoreboard) || isControllerVertical || m_HudAlwaysVisible)
        && m_RenderedHud)
    {
        if (!vr::VROverlay()->IsOverlayVisible(m_HUDHandle) || m_HudAlwaysVisible)
            RepositionOverlays();

        if (PressedDigitalAction(m_Scoreboard))
            m_Game->ClientCmd_Unrestricted("+showscores");
        else
            m_Game->ClientCmd_Unrestricted("-showscores");

        vr::VROverlay()->ShowOverlay(m_HUDHandle);
    }
    else
    {
        vr::VROverlay()->HideOverlay(m_HUDHandle);
    }*/

    m_RenderedHud = false;

    if (PressedDigitalAction(m_Pause, true))
    {
        m_Game->ClientCmd_Unrestricted("gameui_activate");
        RepositionOverlays();
    }
}

VMatrix VR::VMatrixFromHmdMatrix(const vr::HmdMatrix34_t &hmdMat)
{
    // VMatrix has a different implicit coordinate system than HmdMatrix34_t, but this function does not convert between them
    VMatrix vMat(
        hmdMat.m[0][0], hmdMat.m[1][0], hmdMat.m[2][0], 0.0f,
        hmdMat.m[0][1], hmdMat.m[1][1], hmdMat.m[2][1], 0.0f,
        hmdMat.m[0][2], hmdMat.m[1][2], hmdMat.m[2][2], 0.0f,
        hmdMat.m[0][3], hmdMat.m[1][3], hmdMat.m[2][3], 1.0f
    );

    return vMat;
}

vr::HmdMatrix34_t VR::VMatrixToHmdMatrix(const VMatrix &vMat)
{
    vr::HmdMatrix34_t hmdMat = {0};

    hmdMat.m[0][0] = vMat.m[0][0];
    hmdMat.m[1][0] = vMat.m[0][1];
    hmdMat.m[2][0] = vMat.m[0][2];

    hmdMat.m[0][1] = vMat.m[1][0];
    hmdMat.m[1][1] = vMat.m[1][1];
    hmdMat.m[2][1] = vMat.m[1][2];

    hmdMat.m[0][2] = vMat.m[2][0];
    hmdMat.m[1][2] = vMat.m[2][1];
    hmdMat.m[2][2] = vMat.m[2][2];

    hmdMat.m[0][3] = vMat.m[3][0];
    hmdMat.m[1][3] = vMat.m[3][1];
    hmdMat.m[2][3] = vMat.m[3][2];

    return hmdMat;
}

vr::HmdMatrix34_t VR::GetControllerTipMatrix(vr::ETrackedControllerRole controllerRole)
{
    vr::VRInputValueHandle_t inputValue = vr::k_ulInvalidInputValueHandle;

    if (controllerRole == vr::TrackedControllerRole_RightHand)
    {
        m_Input->GetInputSourceHandle("/user/hand/right", &inputValue);
    }
    else if (controllerRole == vr::TrackedControllerRole_LeftHand)
    {
        m_Input->GetInputSourceHandle("/user/hand/left", &inputValue);
    }

    if (inputValue != vr::k_ulInvalidInputValueHandle)
    {
        char buffer[vr::k_unMaxPropertyStringSize];

        m_System->GetStringTrackedDeviceProperty(vr::VRSystem()->GetTrackedDeviceIndexForControllerRole(controllerRole), vr::Prop_RenderModelName_String, 
                                                 buffer, vr::k_unMaxPropertyStringSize);

        vr::RenderModel_ControllerMode_State_t controllerState = {0};
        vr::RenderModel_ComponentState_t componentState = {0};

        if (vr::VRRenderModels()->GetComponentStateForDevicePath(buffer, vr::k_pch_Controller_Component_Tip, inputValue, &controllerState, &componentState))
        {
            return componentState.mTrackingToComponentLocal;
        }
    }

    // Not a hand controller role or tip lookup failed, return identity
    const vr::HmdMatrix34_t identity = 
    {
        1.0f, 0.0f, 0.0f, 0.0f,
        0.0f, 1.0f, 0.0f, 0.0f,
        0.0f, 0.0f, 1.0f, 0.0f
    };

    return identity;
}

bool VR::CheckOverlayIntersectionForController(vr::VROverlayHandle_t overlayHandle, vr::ETrackedControllerRole controllerRole)
{
    vr::TrackedDeviceIndex_t deviceIndex = m_System->GetTrackedDeviceIndexForControllerRole(controllerRole);

    if (deviceIndex == vr::k_unTrackedDeviceIndexInvalid)
        return false;

    vr::TrackedDevicePose_t &controllerPose = m_Poses[deviceIndex];

    if (!controllerPose.bPoseIsValid)
        return false;

    VMatrix controllerVMatrix = VMatrixFromHmdMatrix(controllerPose.mDeviceToAbsoluteTracking);
    VMatrix tipVMatrix        = VMatrixFromHmdMatrix(GetControllerTipMatrix(controllerRole));
    tipVMatrix.MatrixMul(controllerVMatrix, controllerVMatrix);

    vr::VROverlayIntersectionParams_t  params  = {0};
    vr::VROverlayIntersectionResults_t results = {0};

    params.eOrigin    = vr::VRCompositor()->GetTrackingSpace();
    params.vSource    = { controllerVMatrix.m[3][0],  controllerVMatrix.m[3][1],  controllerVMatrix.m[3][2]};
    params.vDirection = {-controllerVMatrix.m[2][0], -controllerVMatrix.m[2][1], -controllerVMatrix.m[2][2]};

    return m_Overlay->ComputeOverlayIntersection(overlayHandle, &params, &results);
}

QAngle VR::GetRightControllerAbsAngle()
{
    return m_RightControllerAngAbs;
}

QAngle& VR::GetRightControllerAbsAngleConst()
{
    return m_RightControllerAngAbs;
}

Vector VR::GetRightControllerAbsPos(Vector eyePosition)
{
    Vector offset = eyePosition;

    if (offset.x == 0 && offset.y == 0 && offset.z == 0) {
        /*int playerIndex = m_Game->m_EngineClient->GetLocalPlayer();
        C_BasePlayer* localPlayer = (C_BasePlayer*)m_Game->GetClientEntity(playerIndex);
        if (!localPlayer)
            return {0, 0, 0};

        offset = localPlayer->EyePosition();*/

        offset = m_SetupOrigin;
    }

    Vector position = offset + m_RightControllerPosRel;

    if (m_6DOF)
        position += m_HmdPosRelative;

    return position + m_CameraCollisionOffset;
}

Vector VR::GetRecommendedViewmodelAbsPos(Vector eyePosition)
{
    Vector viewmodelPos = GetRightControllerAbsPos(eyePosition);
    viewmodelPos -= m_ViewmodelForward * m_ViewmodelPosOffset.x;
    viewmodelPos -= m_ViewmodelRight * m_ViewmodelPosOffset.y;
    viewmodelPos -= m_ViewmodelUp * m_ViewmodelPosOffset.z;

    return viewmodelPos;
}

QAngle VR::GetRecommendedViewmodelAbsAngle()
{
    QAngle result{};

    QAngle::VectorAngles(m_ViewmodelForward, m_ViewmodelUp, result);

    return result;
}

void VR::UpdateHMDAngles() {
    QAngle hmdAngLocal = m_HmdPose.TrackedDeviceAng;

    //hmdAngLocal += m_RotationOffset;
    hmdAngLocal.x += m_RotationOffset.x;
    hmdAngLocal.y += m_RotationOffset.y;
    hmdAngLocal.z += m_RotationOffset.z;

    //hmdAngLocal.Normalize();

    QAngle::AngleVectors(hmdAngLocal, &m_HmdForward, &m_HmdRight, &m_HmdUp);

    //hmdAngLocal.x = (hmdAngLocal.x > 180 ? 180)
    hmdAngLocal.Normalize();

    m_HmdAngAbs = hmdAngLocal;
}

void VR::ResetPosition()
{
    m_Center = m_HmdPose.TrackedDevicePos;
}

void VR::UpdateTracking()
{
    GetPoses();

    // HMD tracking
    Vector hmdPosLocal = m_HmdPose.TrackedDevicePos;
    Vector hmdPosCentered = hmdPosLocal - m_Center;

    m_HmdPosRelativeRaw = hmdPosCentered;

    //std::cout << "HMD - X: " << hmdWorldPos.x << ", Y: " << hmdWorldPos.y << ", Z: " << hmdWorldPos.z << "\n";

    Vector hmdPosCorrected = hmdPosCentered;
    VectorPivotXY(hmdPosCorrected, { 0, 0, 0 }, m_RotationOffset.y);
    
    UpdateHMDAngles();

    m_HmdPosRelative = hmdPosCorrected * m_VRScale;

    C_BasePlayer* localPlayer = reinterpret_cast<C_BasePlayer *>(m_Game->GetLocalPortalPlayer());
    if (!localPlayer)
        return;

    // Roomscale setup
    /*Vector cameraMovingDirection = m_Center - m_SetupOriginPrev;
    Vector cameraToPlayer = m_HmdPosAbsPrev - m_SetupOriginPrev;
    cameraMovingDirection.z = 0;
    cameraToPlayer.z = 0;
    float cameraFollowing = DotProduct(cameraMovingDirection, cameraToPlayer);
    float cameraDistance = VectorLength(cameraToPlayer);

    if (localPlayer->m_hGroundEntity != -1 && localPlayer->m_vecVelocity.IsZero())
        m_RoomscaleActive = true;

    // TODO: Get roomscale to work while using thumbstick
    if ((cameraFollowing < 0 && cameraDistance > 1) || (m_PushingThumbstick))
        m_RoomscaleActive = false;*/

    m_AimPos = Trace((uint32_t*)localPlayer);

    if (m_AimMode == 2 && m_Game->m_Hooks->CreatePingPointer &&
        m_Game->m_Offsets->SetControlPoint.address && m_Game->m_Offsets->StopEmission.address) {
        C_Portal_Player* portalPlayer = (C_Portal_Player*)localPlayer;

        auto activeWeaponAddr = (*(int(__thiscall**)(void*))(*(uintptr_t*)portalPlayer + 968))(portalPlayer);
        //auto activeWeaponAddr = (*(int(__thiscall**)(void*))(*(uintptr_t*)m_Game->m_Offsets->GetActivePortalWeapon.address))(portalPlayer);

        if (activeWeaponAddr && m_DrawCrosshair) {
            CWeaponPortalBase* activeWeapon = (CWeaponPortalBase*)activeWeaponAddr;

            if (portalPlayer->m_PointLaser) {
                portalPlayer->m_PointLaser->SetControlPoint(1, m_AimPos);
                portalPlayer->m_PointLaser->SetControlPoint(2, m_Game->m_singlePlayerPortalColors[activeWeapon->m_iLastFiredPortal] * 0.5f);
            }
            else if (m_Game->m_Hooks->CreatePingPointer) {
                std::cout << "Creating Point Laser Beam Sight Thingy" << "\n";
                m_Game->m_Hooks->CreatePingPointer(localPlayer, m_AimPos);
            }
        }
        else if (portalPlayer->m_PointLaser){
            portalPlayer->m_PointLaser->StopEmission(false, true, false);
            portalPlayer->m_PointLaser = NULL;
        }
    }

    // Check if camera is clipping inside wall
    /*CGameTrace trace;
    Ray_t ray;
    CTraceFilterSkipEntity tracefilter((IHandleEntity*)localPlayer, 0);

    Vector extendedHmdPos = m_HmdPosAbs - m_SetupOrigin;
    VectorNormalize(extendedHmdPos);
    extendedHmdPos = m_HmdPosAbs + (extendedHmdPos * 10);
    ray.Init(m_SetupOrigin, extendedHmdPos);

    if (!m_Game->TraceRay(ray, STANDARD_TRACE_MASK, &tracefilter, &trace))
        return vecEnd;
    if (trace.fraction < 1 && trace.fraction > 0)
    {
        Vector distanceInsideWall = trace.endpos - extendedHmdPos;
        m_CameraAnchor += distanceInsideWall;
        m_HmdPosAbs = m_CameraAnchor - Vector(0, 0, 64) + m_HmdPosLocalInWorld;
    }

    // Reset camera if it somehow gets too far
    m_SetupOriginToHMD = m_HmdPosAbs - m_SetupOrigin;
    if (VectorLength(m_SetupOriginToHMD) > 150)
        ResetPosition();

    m_HmdPosAbsPrev = m_HmdPosAbs;
    m_SetupOriginPrev = m_SetupOrigin;*/

    GetViewParameters();
    m_Ipd = m_EyeToHeadTransformPosRight.x * 2;
    m_EyeZ = m_EyeToHeadTransformPosRight.z;

    // Hand tracking
    Vector leftControllerPosLocal = m_LeftControllerPose.TrackedDevicePos;
    QAngle leftControllerAngLocal = m_LeftControllerPose.TrackedDeviceAng;

    Vector rightControllerPosLocal = m_RightControllerPose.TrackedDevicePos;
    QAngle rightControllerAngLocal = m_RightControllerPose.TrackedDeviceAng;

    //std::cout << "Right Controller - X: " << rightControllerPosLocal.x << "Y: " << rightControllerPosLocal.y << "Z: " << rightControllerPosLocal.z << "\n";

    Vector hmdToController = rightControllerPosLocal - hmdPosLocal;
    //Vector rightControllerPosCorrected = hmdPosCorrected + hmdToController;

    // When using stick turning, pivot the controllers around the HMD
    VectorPivotXY(hmdToController, { 0, 0, 0 }, m_RotationOffset.y);

    m_RightControllerPosRel = hmdToController * m_VRScale;
    Vector hmdToLeftController = leftControllerPosLocal - hmdPosLocal;
    VectorPivotXY(hmdToLeftController, { 0, 0, 0 }, m_RotationOffset.y);
    m_LeftControllerPosRel = hmdToLeftController * m_VRScale;
    leftControllerAngLocal.x += m_RotationOffset.x;
    leftControllerAngLocal.y += m_RotationOffset.y;
    leftControllerAngLocal.z += m_RotationOffset.z;

    //rightControllerAngLocal += m_RotationOffset;
    rightControllerAngLocal.x += m_RotationOffset.x;
    rightControllerAngLocal.y += m_RotationOffset.y;
    rightControllerAngLocal.z += m_RotationOffset.z;

    // Wrap angle from -180 to 180
    //rightControllerAngLocal.Normalize();

    QAngle::AngleVectors(leftControllerAngLocal, &m_LeftControllerForward, &m_LeftControllerRight, &m_LeftControllerUp);
    QAngle::AngleVectors(rightControllerAngLocal, &m_RightControllerForward, &m_RightControllerRight, &m_RightControllerUp);

    // Bare wrists use the tracked grip orientation, without the gun aim tilt.
    m_RightHandForward = m_RightControllerForward;
    m_RightHandUp = m_RightControllerUp;
    m_LeftHandForward = m_LeftControllerForward;
    m_LeftHandUp = m_LeftControllerUp;

    const float offset = -30;

    // Adjust controller angle downward
    m_LeftControllerForward = VectorRotate(m_LeftControllerForward, m_LeftControllerRight, offset);
    m_LeftControllerUp = VectorRotate(m_LeftControllerUp, m_LeftControllerRight, offset);

    m_RightControllerForward = VectorRotate(m_RightControllerForward, m_RightControllerRight, offset);
    m_RightControllerUp = VectorRotate(m_RightControllerUp, m_RightControllerRight, offset);

    // controller angles
    QAngle::VectorAngles(m_LeftControllerForward, m_LeftControllerUp, m_LeftControllerAngAbs);
    QAngle::VectorAngles(m_RightControllerForward, m_RightControllerUp, m_RightControllerAngAbs);
    m_RightControllerAngAbs.Normalize();

    PositionAngle viewmodelOffset = PositionAngle{ {4.5, -1, 1.5}, {0,0,0} };

    // Apply both hardcoded and custom (from config) viewmodel offsets here:
    m_ViewmodelPosOffset = viewmodelOffset.position + m_ViewmodelPosCustomOffset;
    m_ViewmodelAngOffset = viewmodelOffset.angle + m_ViewmodelAngCustomOffset;

    m_ViewmodelForward = m_RightControllerForward;
    m_ViewmodelUp = m_RightControllerUp;
    m_ViewmodelRight = m_RightControllerRight;

    // Viewmodel yaw offset
    m_ViewmodelForward = VectorRotate(m_ViewmodelForward, m_ViewmodelUp, m_ViewmodelAngOffset.y);
    m_ViewmodelRight = VectorRotate(m_ViewmodelRight, m_ViewmodelUp, m_ViewmodelAngOffset.y);

    // Viewmodel pitch offset
    m_ViewmodelForward = VectorRotate(m_ViewmodelForward, m_ViewmodelRight, m_ViewmodelAngOffset.x);
    m_ViewmodelUp = VectorRotate(m_ViewmodelUp, m_ViewmodelRight, m_ViewmodelAngOffset.x);

    // Viewmodel roll offset
    m_ViewmodelRight = VectorRotate(m_ViewmodelRight, m_ViewmodelForward, m_ViewmodelAngOffset.z);
    m_ViewmodelUp = VectorRotate(m_ViewmodelUp, m_ViewmodelForward, m_ViewmodelAngOffset.z);
}

Vector VR::GetViewAngle()
{
    return Vector( m_HmdAngAbs.x, m_HmdAngAbs.y, m_HmdAngAbs.z );
}

Vector VR::GetViewOrigin(Vector setupOrigin)
{
    Vector center = setupOrigin;

    if (m_6DOF)
        center += m_HmdPosRelative;

    return center + (m_HmdForward * -(m_EyeZ * m_VRScale)) + m_CameraCollisionOffset;
}

void VR::UpdateCameraCollision(Vector setupOrigin)
{
    // Always solve from the engine's current player eye position. Never move
    // the tracking origin: leaning back, respawning, or portalling must recover.
    m_CameraCollisionOffset = { 0, 0, 0 };
    auto* player = m_Game->GetLocalPortalPlayer();
    if (!player)
    {
        m_CameraBlocked = false;
        return;
    }

    const Vector desired = GetViewOrigin(setupOrigin);
    const float radius = CameraCollision::HullRadius(m_Ipd * m_IpdScale * m_VRScale, m_Fov, m_Aspect);
    const Vector extent(radius, radius, radius);
    Ray_t ray{};
    ray.Init(setupOrigin, desired, extent * -1.0f, extent);
    CGameTrace trace;
    trace.fraction = 1.0f;
    trace.startsolid = trace.allsolid = false;
    CTraceFilterSkipEntity filter(reinterpret_cast<IHandleEntity*>(player), 0);
    constexpr unsigned mask = CONTENTS_SOLID | CONTENTS_WINDOW | CONTENTS_GRATE | CONTENTS_MOVEABLE;
    if (!m_Game->TraceRay(ray, mask, &filter, &trace))
    {
        m_CameraBlocked = false;
        return;
    }

    // An actual engine trace catches ABI errors that pure geometry tests cannot.
    static const bool debugCollision = strstr(GetCommandLineA(), "-portalvr-debug-collision") != nullptr;
    static bool loggedProbe = false;
    if (debugCollision && !loggedProbe)
    {
        Ray_t floorRay{};
        floorRay.Init(setupOrigin, setupOrigin - Vector(0, 0, 4096), extent * -1.0f, extent);
        CGameTrace floorTrace;
        if (m_Game->TraceRay(floorRay, mask, &filter, &floorTrace))
        {
            PortalVrLog("Collision engine probe fraction=%f startsolid=%d allsolid=%d start=%f,%f,%f end=%f,%f,%f rayFlags=%d,%d",
                floorTrace.fraction, floorTrace.startsolid, floorTrace.allsolid,
                setupOrigin.x, setupOrigin.y, setupOrigin.z,
                floorTrace.endpos.x, floorTrace.endpos.y, floorTrace.endpos.z,
                floorRay.m_IsRay, floorRay.m_IsSwept);
            loggedProbe = true;
        }
    }

    const Vector safe = CameraCollision::Constrain(setupOrigin, desired, trace.fraction, trace.startsolid, trace.allsolid);
    m_CameraCollisionOffset = safe - desired;
    const bool blocked = m_CameraCollisionOffset.LengthSqr() > 0.0001f;
    if (blocked != m_CameraBlocked)
        PortalVrLog("Head collision blocked=%d fraction=%f radius=%f correction=%f,%f,%f startsolid=%d allsolid=%d",
            blocked, trace.fraction, radius, m_CameraCollisionOffset.x, m_CameraCollisionOffset.y,
            m_CameraCollisionOffset.z, trace.startsolid, trace.allsolid);
    m_CameraBlocked = blocked;
}

Vector VR::GetViewOriginLeft(Vector setupOrigin)
{
    Vector viewOriginLeft = GetViewOrigin(setupOrigin);
    viewOriginLeft -= m_HmdRight * ((m_Ipd * m_IpdScale * m_VRScale) / 2);

    return viewOriginLeft;
}

Vector VR::GetViewOriginRight(Vector setupOrigin)
{
    Vector viewOriginRight = GetViewOrigin(setupOrigin);
    viewOriginRight += m_HmdRight * ((m_Ipd * m_IpdScale * m_VRScale) / 2);

    return viewOriginRight;
}

Vector VR::Trace(uint32_t* localPlayer) {
    Vector vecStart = GetRightControllerAbsPos();
    Vector vecEnd = vecStart + m_RightControllerForward * MAX_TRACE_LENGTH;

    CGameTrace trace;
    Ray_t ray;
    CTraceFilterSkipEntity tracefilter((IHandleEntity*)localPlayer, 0);

    ray.Init(vecStart, vecEnd);

    if (!m_Game->TraceRay(ray, MASK_SHOT | MASK_SHOT_HULL, &tracefilter, &trace))
        return vecEnd;

    return trace.endpos;
}

void AngleMatrix(const QAngle& angles, matrix3x4_t& matrix)
{
    float sr, sp, sy, cr, cp, cy;

    SinCos(DEG2RAD(angles[YAW]), &sy, &cy);
    SinCos(DEG2RAD(angles[PITCH]), &sp, &cp);
    SinCos(DEG2RAD(angles[ROLL]), &sr, &cr);

    // matrix = (YAW * PITCH) * ROLL
    matrix[0][0] = cp * cy;
    matrix[1][0] = cp * sy;
    matrix[2][0] = -sp;

    // NOTE: Do not optimize this to reduce multiplies! optimizer bug will screw this up.
    matrix[0][1] = sr * sp * cy + cr * -sy;
    matrix[1][1] = sr * sp * sy + cr * cy;
    matrix[2][1] = sr * cp;
    matrix[0][2] = (cr * sp * cy + -sr * -sy);
    matrix[1][2] = (cr * sp * sy + -sr * cy);
    matrix[2][2] = cr * cp;

    matrix[0][3] = 0.0f;
    matrix[1][3] = 0.0f;
    matrix[2][3] = 0.0f;
}

void MatrixCopy(const matrix3x4_t& in, matrix3x4_t& out)
{
    memcpy(out.Base(), in.Base(), sizeof(float) * 3 * 4);
}


/*
================
R_ConcatTransforms
================
*/

void ConcatTransforms(const matrix3x4_t& in1, const matrix3x4_t& in2, matrix3x4_t& out)
{
    if (&in1 == &out)
    {
        matrix3x4_t in1b;
        MatrixCopy(in1, in1b);
        ConcatTransforms(in1b, in2, out);
        return;
    }
    if (&in2 == &out)
    {
        matrix3x4_t in2b;
        MatrixCopy(in2, in2b);
        ConcatTransforms(in1, in2b, out);
        return;
    }
    out[0][0] = in1[0][0] * in2[0][0] + in1[0][1] * in2[1][0] +
        in1[0][2] * in2[2][0];
    out[0][1] = in1[0][0] * in2[0][1] + in1[0][1] * in2[1][1] +
        in1[0][2] * in2[2][1];
    out[0][2] = in1[0][0] * in2[0][2] + in1[0][1] * in2[1][2] +
        in1[0][2] * in2[2][2];
    out[0][3] = in1[0][0] * in2[0][3] + in1[0][1] * in2[1][3] +
        in1[0][2] * in2[2][3] + in1[0][3];
    out[1][0] = in1[1][0] * in2[0][0] + in1[1][1] * in2[1][0] +
        in1[1][2] * in2[2][0];
    out[1][1] = in1[1][0] * in2[0][1] + in1[1][1] * in2[1][1] +
        in1[1][2] * in2[2][1];
    out[1][2] = in1[1][0] * in2[0][2] + in1[1][1] * in2[1][2] +
        in1[1][2] * in2[2][2];
    out[1][3] = in1[1][0] * in2[0][3] + in1[1][1] * in2[1][3] +
        in1[1][2] * in2[2][3] + in1[1][3];
    out[2][0] = in1[2][0] * in2[0][0] + in1[2][1] * in2[1][0] +
        in1[2][2] * in2[2][0];
    out[2][1] = in1[2][0] * in2[0][1] + in1[2][1] * in2[1][1] +
        in1[2][2] * in2[2][1];
    out[2][2] = in1[2][0] * in2[0][2] + in1[2][1] * in2[1][2] +
        in1[2][2] * in2[2][2];
    out[2][3] = in1[2][0] * in2[0][3] + in1[2][1] * in2[1][3] +
        in1[2][2] * in2[2][3] + in1[2][3];
}

void MatrixAngles(const matrix3x4_t& matrix, float* angles)
{
    float forward[3];
    float left[3];
    float up[3];

    //
    // Extract the basis vectors from the matrix. Since we only need the Z
    // component of the up vector, we don't get X and Y.
    //
    forward[0] = matrix[0][0];
    forward[1] = matrix[1][0];
    forward[2] = matrix[2][0];
    left[0] = matrix[0][1];
    left[1] = matrix[1][1];
    left[2] = matrix[2][1];
    up[2] = matrix[2][2];

    float xyDist = sqrtf(forward[0] * forward[0] + forward[1] * forward[1]);

    // enough here to get angles?
    if (xyDist > 0.001f)
    {
        // (yaw)	y = ATAN( forward.y, forward.x );		-- in our space, forward is the X axis
        angles[1] = RAD2DEG(atan2f(forward[1], forward[0]));

        // (pitch)	x = ATAN( -forward.z, sqrt(forward.x*forward.x+forward.y*forward.y) );
        angles[0] = RAD2DEG(atan2f(-forward[2], xyDist));

        // (roll)	z = ATAN( left.z, up.z );
        angles[2] = RAD2DEG(atan2f(left[2], up[2]));
    }
    else	// forward is mostly Z, gimbal lock-
    {
        // (yaw)	y = ATAN( -left.x, left.y );			-- forward is mostly z, so use right for yaw
        angles[1] = RAD2DEG(atan2f(-left[0], left[1]));

        // (pitch)	x = ATAN( -forward.z, sqrt(forward.x*forward.x+forward.y*forward.y) );
        angles[0] = RAD2DEG(atan2f(-forward[2], xyDist));

        // Assume no roll in this case as one degree of freedom has been lost (i.e. yaw == roll)
        angles[2] = 0;
    }
}

inline void MatrixAngles(const matrix3x4_t& matrix, QAngle& angles)
{
    MatrixAngles(matrix, &angles.x);
}



// transform a set of angles in the input space of parentMatrix to the output space
QAngle TransformAnglesToWorldSpace(const QAngle& angles, const matrix3x4_t& parentMatrix)
{
    matrix3x4_t angToParent, angToWorld;
    AngleMatrix(angles, angToParent);
    ConcatTransforms(parentMatrix, angToParent, angToWorld);
    QAngle out;
    MatrixAngles(angToWorld, out);
    return out;
}


Vector VR::TraceEye(uint32_t* localPlayer, Vector cameraPos, Vector eyePos, QAngle& eyeAngle) {
    CGameTrace trTestObstructionsNearPortals;
    Ray_t ray;
    CTraceFilterSkipEntity tracefilter((IHandleEntity*)localPlayer, 0);

    ray.Init(cameraPos, eyePos);
    if (!m_Game->TraceRay(ray, MASK_SHOT | MASK_SHOT_HULL, &tracefilter, &trTestObstructionsNearPortals))
        return eyePos;

    float flWallHitFraction = trTestObstructionsNearPortals.fraction + 0.01f;
    CPortal_Base2D* pPortal = (CPortal_Base2D*)m_Game->m_Hooks->UTIL_Portal_FirstAlongRay(ray, flWallHitFraction);

    if (trTestObstructionsNearPortals.DidHit() && pPortal) {
        float flRayHitFraction = m_Game->m_Hooks->UTIL_IntersectRayWithPortal(ray, pPortal);
        //Vector vNewEye;
        Vector vHitPoint = ray.m_Start + ray.m_Delta * flRayHitFraction;
        //vNewEye = m_Game->m_Hooks->UTIL_Portal_PointTransform(pPortal->MatrixThisToLinked(), vHitPoint, vNewEye);

        //VMatrix matrix = *(VMatrix*)((uintptr_t)pPortal + 0x4C4);
        VMatrix matrix = pPortal->MatrixThisToLinked();

   
        /*QAngle newAngle;
        m_Game->m_Hooks->UTIL_Portal_AngleTransform(matrix, eyeAngle, newAngle);*/
        eyeAngle = TransformAnglesToWorldSpace(eyeAngle, matrix.As3x4());

        return matrix * vHitPoint;

        //return pPortal->MatrixThisToLinked() * vHitPoint;
    }

    return eyePos;
}

// [CONFIG PARSING UTILITY FUNCTION]
// Generates an error message by stringifying and concatenating 'args...'.
template <typename... Ts>
static void concatErrorMsg(Game& game, const Ts&... args)
{
    std::ostringstream oss;
    (oss << ... << args);
    game.errorMsg(oss.str().c_str());
}

// [CONFIG PARSING UTILITY FUNCTION]
// Attempts to parse an entry with key 'key' from the provided 'userConfig'. If the key is
// missing or if the parsing fails, 'defaultValue' is returned and an error message is
// generated.
template <typename T>
static T parseConfigEntry(
    const std::unordered_map<std::string, std::string>& userConfig, Game& game,
    const char* key, const T& defaultValue)
try
{
    const auto itr = userConfig.find(key);

    if (itr == userConfig.end())
    {
        concatErrorMsg(game, "Config entry with key '", key,
            "' missing -- reverting to default value of '", defaultValue, "'");

        return defaultValue;
    }

    const std::string& configValue = itr->second;

    if constexpr (std::is_same_v<T, bool>)
    {
        return configValue == "true";
    }
    else if constexpr(std::is_floating_point_v<T>)
    {
        return std::stof(configValue);
    }
    else if constexpr(std::is_integral_v<T>)
    {
        return std::stol(configValue);
    }
    else
    {
        // Just a way of generating a compilation failure in case this branch is taken.
        struct invalid_type;
        return invalid_type{};
    }
}
catch (const std::logic_error& e)
{
    concatErrorMsg(game, "Error parsing config entry with key '", key,
        "' -- reverting to default value of '", defaultValue, "' -- error: (", e.what(), ")");

    throw;
}

void VR::ParseConfigFile()
{
    char runtimeDirectory[MAX_PATH] = {};
    if (!GetRuntimeBaseDirectory(runtimeDirectory, sizeof(runtimeDirectory)))
        return;
    std::ifstream configStream(std::filesystem::path(runtimeDirectory) / "VR" / "config.txt");
    std::unordered_map<std::string, std::string> userConfig;

    std::string line;
    while (std::getline(configStream, line))
    {
        std::istringstream sLine(line);
        std::string key;
        if (std::getline(sLine, key, '='))
        {
            std::string value;
            if (std::getline(sLine, value, '#'))
                userConfig[key] = value;
            else if (std::getline(sLine, value))
                userConfig[key] = value;
        }
    }

    if (userConfig.empty())
        return;

    // Parse a single entry with key 'key' from the config into 'target'.
    // If the entry does not exist, or if the parsing fails, sets 'target' to
    // 'defaultValue'.
    const auto parseOrDefault = [&](const char* key, auto& target,
                                    const auto& defaultValue) 
    { 
        target = parseConfigEntry(userConfig, *m_Game, key, defaultValue);
        std::cout << "Setting '" << key << "' to '" << target << "'\n";
    };

    // Parses a vector or angle from the config into 'target'. The XYZ coordinates
    // are read from three separate config entries with key 'keyPrefix' + 'X'/'Y'/'Z'.
    // If any entry does not exist, or if the parsing fails, sets the corresponding
    // coordinate in 'target' to zero.
    const auto parseXYZOrDefaultZero = [&](std::string keyPrefix, auto& target)
    {
        parseOrDefault((keyPrefix + "X").c_str(), target.x, 0.f);
        parseOrDefault((keyPrefix + "Y").c_str(), target.y, 0.f);
        parseOrDefault((keyPrefix + "Z").c_str(), target.z, 0.f);
    };

    parseOrDefault("SnapTurning", m_SnapTurning, false);
    parseOrDefault("SnapTurnAngle", m_SnapTurnAngle, 45.0f);
    parseOrDefault("TurnSpeed", m_TurnSpeed, 0.15f);
    parseOrDefault("LeftHanded", m_LeftHanded, false);
    parseOrDefault("VRScale", m_VRScale, 43.2f);
    parseOrDefault("IPDScale", m_IpdScale, 1.0f);
    parseOrDefault("6DOF", m_6DOF, true);
    /*parseOrDefault("HudDistance", m_HudDistance, 1.3f);
    parseOrDefault("HudSize", m_HudSize, 4.0f);
    parseOrDefault("HudAlwaysVisible", m_HudAlwaysVisible, false);*/
    parseOrDefault("AimMode", m_AimMode, 2);
    parseOrDefault("AntiAliasing", m_AntiAliasing, 0);
    parseOrDefault("RenderWindow", m_RenderWindow, 0);
    parseXYZOrDefaultZero("ViewmodelPosCustomOffset", m_ViewmodelPosCustomOffset);
    parseXYZOrDefaultZero("ViewmodelAngCustomOffset", m_ViewmodelAngCustomOffset);
}

void VR::WaitForConfigUpdate()
{
    char currentDir[MAX_STR_LEN];
    GetCurrentDirectory(MAX_STR_LEN, currentDir);
    char configDir[MAX_STR_LEN];
    sprintf_s(configDir, MAX_STR_LEN, "%s\\VR\\", currentDir);
    HANDLE fileChangeHandle = FindFirstChangeNotificationA(configDir, false, FILE_NOTIFY_CHANGE_LAST_WRITE);

    std::filesystem::file_time_type configLastModified;
    while (1)
    {
        try 
        {
            // Windows only notifies of change within a directory, so extra check here for just config.txt
            auto configModifiedTime = std::filesystem::last_write_time("VR\\config.txt");
            if (configModifiedTime != configLastModified)
            {
                configLastModified = configModifiedTime;
                ParseConfigFile();
                
                std::cout << "Successfully reloaded 'config.txt'\n";
            }
        }
        catch (const std::invalid_argument &e)
        {
            concatErrorMsg(
                *m_Game, "Failed to parse 'config.txt' (", e.what(), ")");
        }
        catch (const std::filesystem::filesystem_error &e)
        {
            concatErrorMsg(
                *m_Game, "'config.txt' not found. (", e.what(), ")");
            
            return;
        }
        
        FindNextChangeNotification(fileChangeHandle);
        WaitForSingleObject(fileChangeHandle, INFINITE);
        Sleep(100); // Sometimes the thread tries to read config.txt before it's finished writing
    }
}
