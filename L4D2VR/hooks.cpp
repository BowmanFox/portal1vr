#include "hooks.h"
#include "game.h"
#include "texture.h"
#include "sdk.h"
#include "sdk_server.h"
#include "vr.h"
#include "offsets.h"
#include "portal1.h"
#include "debuglog.h"
#include "handpose.h"
#include "cameracollision.h"
#include <iostream>

Game *Hooks::m_Game = nullptr;
VR *Hooks::m_VR = nullptr;

Hook<tGetRenderTarget> Hooks::hkGetRenderTarget = {};
Hook<tRenderView> Hooks::hkRenderView = {};
Hook<tPush3DView> Hooks::hkPush3DView = {};
Hook<tPush3DViewDepth> Hooks::hkPush3DViewDepth = {};
ITexture *Hooks::m_ActiveEyeTexture = nullptr;
Hook<tCreateMove> Hooks::hkCreateMove = {};
Hook<tEndFrame> Hooks::hkEndFrame = {};
Hook<tCalcViewModelView> Hooks::hkCalcViewModelView = {};
Hook<tCreateViewModel> Hooks::hkCreateViewModel = {};
static void *s_LeftArmRenderable = nullptr;
Hook<tProcessUsercmds> Hooks::hkProcessUsercmds = {};
Hook<tReadUsercmd> Hooks::hkReadUsercmd = {};
Hook<tWriteUsercmdDeltaToBuffer> Hooks::hkWriteUsercmdDeltaToBuffer = {};
Hook<tWriteUsercmd> Hooks::hkWriteUsercmd = {};
Hook<tAdjustEngineViewport> Hooks::hkAdjustEngineViewport = {};
Hook<tViewport> Hooks::hkViewport = {};
Hook<tGetViewport> Hooks::hkGetViewport = {};
Hook<tGetPrimaryAttackActivity> Hooks::hkGetPrimaryAttackActivity = {};
Hook<tEyePosition> Hooks::hkEyePosition = {};
Hook<tDrawModelExecute> Hooks::hkDrawModelExecute = {};
Hook<tPushRenderTargetAndViewport> Hooks::hkPushRenderTargetAndViewport = {};
Hook<tPopRenderTargetAndViewport> Hooks::hkPopRenderTargetAndViewport = {};
Hook<tVgui_Paint> Hooks::hkVgui_Paint = {};
Hook<tIsSplitScreen> Hooks::hkIsSplitScreen = {};
Hook<tPrePushRenderTarget> Hooks::hkPrePushRenderTarget = {};
Hook<tGetFullScreenTexture> Hooks::hkGetFullScreenTexture = {};
Hook<tWeapon_ShootPosition> Hooks::hkWeapon_ShootPosition = {};
Hook<tTraceFirePortal> Hooks::hkTraceFirePortal = {};

Hook<tGetModeHeight> Hooks::hkGetModeHeight = {};
Hook<tDrawSelf> Hooks::hkDrawSelf = {};
Hook<tClipTransform> Hooks::hkClipTransform = {};
Hook<tPlayerPortalled> Hooks::hkPlayerPortalled = {};
Hook<tVGui_GetHudBounds> Hooks::hkVGui_GetHudBounds = {};
Hook<tVGui_GetPanelBounds> Hooks::hkVGui_GetPanelBounds = {};
Hook<tVGUI_UpdateScreenSpaceBounds> Hooks::hkVGUI_UpdateScreenSpaceBounds = {};
Hook<tVGui_GetTrueScreenSize> Hooks::hkVGui_GetTrueScreenSize = {};
Hook<tSetBounds> Hooks::hkSetBounds = {};
Hook<tGetScreenSize> Hooks::hkGetScreenSize = {};
Hook<tPush2DView> Hooks::hkPush2DView = {};
Hook<tRender> Hooks::hkRender = {};
Hook<tGetClipRect> Hooks::hkGetClipRect = {};
Hook<tGetHudSize> Hooks::hkGetHudSize = {};
Hook<tSetSize> Hooks::hkSetSize = {};

Hook<tComputeError> Hooks::hkComputeError = {};
Hook<tUpdateObject> Hooks::hkUpdateObject = {};
Hook<tUpdateObjectVM> Hooks::hkUpdateObjectVM = {};
Hook<tRotateObject> Hooks::hkRotateObject = {};
Hook<tEyeAngles> Hooks::hkEyeAngles = {};

Hook<tMatrixBuildPerspectiveX> Hooks::hkMatrixBuildPerspectiveX = {};
Hook<tGetDefaultFOV> Hooks::hkGetDefaultFOV = {};
Hook<tGetFOV> Hooks::hkGetFOV = {};
Hook<tGetViewModelFOV> Hooks::hkGetViewModelFOV = {};

Hook<tSetDrawOnlyForSplitScreenUser> Hooks::hkSetDrawOnlyForSplitScreenUser = {};
Hook<tClientThink> Hooks::hkClientThink = {};
Hook<tPrecache> Hooks::hkPrecache = {};
Hook<tCHudCrosshair_ShouldDraw> Hooks::hkCHudCrosshair_ShouldDraw = {};
Hook<tCWeaponPortalgun_FirePortal> Hooks::hkCWeaponPortalgun_FirePortal = {};

int Hooks::m_PushHUDStep = 0;
bool Hooks::m_PushedHud = false;

tCreatePingPointer Hooks::CreatePingPointer = nullptr;
tPrecacheParticleSystem Hooks::PrecacheParticleSystem = nullptr;

tUTIL_Portal_FirstAlongRay Hooks::UTIL_Portal_FirstAlongRay = nullptr;
tUTIL_IntersectRayWithPortal Hooks::UTIL_IntersectRayWithPortal = nullptr;
tUTIL_Portal_AngleTransform Hooks::UTIL_Portal_AngleTransform = nullptr;
tEntindex Hooks::EntityIndex = nullptr;
tGetOwner Hooks::GetOwner = nullptr;
tGetFullScreenTexture Hooks::GetFullScreenTexture = nullptr;

namespace
{
	constexpr bool kEnableAllHooks = true;
	constexpr bool kEnableClientModeHooks = true;

	template <typename T>
	bool CreateHookAt(Hook<T> &hook, uintptr_t address, LPVOID detour, const char *name, bool required)
	{
		if (!address)
		{
			if (required)
			{
				std::string error = "Required hook target not found: ";
				error += name;
				Game::errorMsg(error.c_str());
			}
			return false;
		}

		return hook.createHook(reinterpret_cast<LPVOID>(address), detour) == 0;
	}

	template <typename T>
	void EnableIfCreated(Hook<T> &hook)
	{
		if (hook.isCreated())
			hook.enableHook();
	}
}

Hooks::Hooks(Game *game)
{
	PortalVrLog("Hooks::Hooks start");

	const MH_STATUS initStatus = MH_Initialize();
	if (initStatus != MH_OK && initStatus != MH_ERROR_ALREADY_INITIALIZED)
	{
		Game::errorMsg("Failed to init MinHook");
	}
	PortalVrLog("MinHook initialized");

	m_Game = game;
	m_VR = m_Game->m_VR;

	m_PushHUDStep = -999;
	m_PushedHud = true;

	if (!kEnableAllHooks)
	{
		PortalVrLog("All hooks disabled for diagnostic run");
		return;
	}

	initSourceHooks();
	PortalVrLog("initSourceHooks complete render=%d createMove=%d getViewModelFov=%d", hkRenderView.isCreated(), hkCreateMove.isCreated(), hkGetViewModelFOV.isCreated());

	EnableIfCreated(hkCalcViewModelView);
	EnableIfCreated(hkCreateMove);
	EnableIfCreated(hkRenderView);
	EnableIfCreated(hkPush3DView);
	EnableIfCreated(hkPush3DViewDepth);
	EnableIfCreated(hkTraceFirePortal);
	EnableIfCreated(hkCWeaponPortalgun_FirePortal);
	EnableIfCreated(hkWeapon_ShootPosition);
	EnableIfCreated(hkComputeError);
	EnableIfCreated(hkUpdateObject);
	EnableIfCreated(hkUpdateObjectVM);
	EnableIfCreated(hkRotateObject);
	EnableIfCreated(hkEyeAngles);
	EnableIfCreated(hkGetViewModelFOV);
	EnableIfCreated(hkCreateViewModel);
	EnableIfCreated(hkDrawModelExecute);
	EnableIfCreated(hkPlayerPortalled);
	EnableIfCreated(hkCHudCrosshair_ShouldDraw);
	PortalVrLog("Hooks enabled");
}

Hooks::~Hooks()
{
	if (MH_Uninitialize() != MH_OK)
	{
		Game::errorMsg("Failed to uninitialize MinHook");
	}
}


int Hooks::initSourceHooks()
{
	const bool hasOffsets = m_Game->m_Offsets != nullptr;
	CreateHookAt(hkCreateViewModel,
		SigScanner::FindRttiVtableFunction("server.dll", ".?AVCBasePlayer@@", 323),
		reinterpret_cast<LPVOID>(&dCreateViewModel), "Portal1::CreateViewModel", false);
	void *modelRender = m_Game->GetInterface("engine.dll", Portal1::Interfaces::kModelRender, false);
	CreateHookAt(hkDrawModelExecute, SigScanner::GetVirtualFunction(modelRender, 19),
		reinterpret_cast<LPVOID>(&dDrawModelExecute), "IVModelRender::DrawModelExecute", false);
	void *engineRenderView = m_Game->GetInterface("engine.dll", Portal1::Interfaces::kEngineRenderView);
	CreateHookAt(hkPush3DViewDepth, SigScanner::GetVirtualFunction(engineRenderView, 37),
		reinterpret_cast<LPVOID>(&dPush3DViewDepth), "IVRenderView::Push3DView(depth)", true);
	CreateHookAt(hkPush3DView, SigScanner::GetVirtualFunction(engineRenderView, 38),
		reinterpret_cast<LPVOID>(&dPush3DView), "IVRenderView::Push3DView", true);
	IViewRender *clientViewRender = m_Game->GetClientViewRender();
	IClientMode *clientMode = m_Game->GetClientMode();

	PortalVrLog(
		"initSourceHooks objects clientMode=%p clientViewRender=%p",
		clientMode,
		clientViewRender);

	const uintptr_t renderViewTarget = clientViewRender
		? SigScanner::GetVirtualFunction(clientViewRender, Portal1::VTableIndex::kViewRender_RenderView)
		: 0;
	CreateHookAt(
		hkRenderView,
		renderViewTarget,
		reinterpret_cast<LPVOID>(&dRenderView),
		"Portal1::CViewRender::RenderView",
		true);

	if (!hasOffsets)
		PortalVrLog("Offsets unavailable, enabling minimal hook set only");

	CreateHookAt(
		hkCalcViewModelView,
		SigScanner::FindRttiVtableFunction("client.dll", ".?AVC_Portal_Player@@", 224),
		reinterpret_cast<LPVOID>(&dCalcViewModelView),
		"Portal1::CalcViewModelView",
		false);

	if (kEnableClientModeHooks)
	{
		const uintptr_t createMoveTarget = clientMode
			? SigScanner::GetVirtualFunction(clientMode, Portal1::VTableIndex::kClientMode_CreateMove)
			: 0;
		const uintptr_t getViewModelFovTarget = clientMode
			? SigScanner::GetVirtualFunction(clientMode, Portal1::VTableIndex::kClientMode_GetViewModelFOV)
			: 0;
		CreateHookAt(
			hkCreateMove,
			createMoveTarget,
			reinterpret_cast<LPVOID>(&dCreateMove),
			"Portal1::ClientModePortalNormal::CreateMove",
			true);
		CreateHookAt(
			hkGetViewModelFOV,
			getViewModelFovTarget,
			reinterpret_cast<LPVOID>(&dGetViewModelFOV),
			"Portal1::ClientModePortalNormal::GetViewModelFOV",
			false);
	}
	else
	{
		PortalVrLog("ClientMode hooks disabled for diagnostic run");
	}

	if (hasOffsets && m_Game->m_Offsets->TraceFirePortalServer.valid)
		CreateHookAt(hkTraceFirePortal, m_Game->m_Offsets->TraceFirePortalServer.address, reinterpret_cast<LPVOID>(&dTraceFirePortal), "TraceFirePortalServer", false);
	if (hasOffsets) {
		CreateHookAt(hkWeapon_ShootPosition, m_Game->m_Offsets->Weapon_ShootPosition.address,
			reinterpret_cast<LPVOID>(&dWeapon_ShootPosition), "Portal1::WeaponShootPosition", false);
		CreateHookAt(hkComputeError, m_Game->m_Offsets->ComputeError.address,
			reinterpret_cast<LPVOID>(&dComputeError), "Portal1::ComputeGrabError", false);
		CreateHookAt(hkUpdateObject, m_Game->m_Offsets->UpdateObject.address,
			reinterpret_cast<LPVOID>(&dUpdateObject), "Portal1::UpdateGrabObject", false);
		CreateHookAt(hkUpdateObjectVM, m_Game->m_Offsets->UpdateObjectVM.address,
			reinterpret_cast<LPVOID>(&dUpdateObjectVM), "Portal1::UpdateGrabObjectVM", false);
		CreateHookAt(hkRotateObject, m_Game->m_Offsets->RotateObject.address,
			reinterpret_cast<LPVOID>(&dRotateObject), "Portal1::RotateGrabObject", false);
		CreateHookAt(hkEyeAngles, m_Game->m_Offsets->EyeAngles.address,
			reinterpret_cast<LPVOID>(&dEyeAngles), "Portal1::EyeAngles", false);
	}

	// The inherited FirePortal detour has Portal 2's ABI. Portal 1 aiming is
	// handled by the verified eight-argument TraceFirePortal hook above.

	CreatePingPointer = (hasOffsets ? reinterpret_cast<tCreatePingPointer>(m_Game->m_Offsets->CreatePingPointer.address) : nullptr);
	PrecacheParticleSystem = hasOffsets && m_Game->m_Offsets->PrecacheParticleSystem.valid ? (tPrecacheParticleSystem)m_Game->m_Offsets->PrecacheParticleSystem.address : nullptr;
	EntityIndex = hasOffsets && m_Game->m_Offsets->CBaseEntity_entindex.valid ? (tEntindex)m_Game->m_Offsets->CBaseEntity_entindex.address : nullptr;
	GetOwner = hasOffsets && m_Game->m_Offsets->GetOwner.valid ? (tGetOwner)m_Game->m_Offsets->GetOwner.address : nullptr;
	GetFullScreenTexture = hasOffsets && m_Game->m_Offsets->GetFullScreenTexture.valid ? (tGetFullScreenTexture)m_Game->m_Offsets->GetFullScreenTexture.address : nullptr;
	CreateHookAt(
		hkPlayerPortalled,
		(hasOffsets ? m_Game->m_Offsets->PlayerPortalled.address : 0),
		reinterpret_cast<LPVOID>(&dPlayerPortalled),
		"Portal1::C_Portal_Player::PlayerPortalled",
		false);
	CreateHookAt(
		hkCHudCrosshair_ShouldDraw,
		(hasOffsets ? m_Game->m_Offsets->CHudCrosshair_ShouldDraw.address : 0),
		reinterpret_cast<LPVOID>(&dCHudCrosshair_ShouldDraw),
		"Portal1::CHudCrosshair::ShouldDraw",
		false);
	PortalVrLog(
		"initSourceHooks targets render=%p createMove=%p getViewModelFov=%p calcViewModel=%p traceFirePortal=%p shoot=%p update=%p eyeAngles=%p playerPortalled=%p crosshair=%p",
		hkRenderView.pTarget,
		hkCreateMove.pTarget,
		hkGetViewModelFOV.pTarget,
		hkCalcViewModelView.pTarget,
		hkTraceFirePortal.pTarget,
		hkWeapon_ShootPosition.pTarget,
		hkUpdateObject.pTarget,
		hkEyeAngles.pTarget,
		hkPlayerPortalled.pTarget,
		hkCHudCrosshair_ShouldDraw.pTarget);
	return 1;
} 

bool __fastcall Hooks::dCHudCrosshair_ShouldDraw(void* ecx, void* edx) {
	bool shouldDraw = hkCHudCrosshair_ShouldDraw.fOriginal(ecx);

	m_VR->m_DrawCrosshair = shouldDraw;

	return ((m_VR->m_AimMode == 1) ? shouldDraw : false);
}

void __fastcall Hooks::dPrecache(void* ecx, void* edx) {
	hkPrecache.fOriginal(ecx);
	if (PrecacheParticleSystem)
		PrecacheParticleSystem("robot_point_beam");
}

void __fastcall Hooks::dClientThink(void* ecx, void* edx) {
	hkClientThink.fOriginal(ecx);
}

void __fastcall Hooks::dSetDrawOnlyForSplitScreenUser(void* ecx, void* edx, int nSlot) {
	hkSetDrawOnlyForSplitScreenUser.fOriginal(ecx, -1);
}

ITexture *__fastcall Hooks::dGetFullScreenTexture()
{
	ITexture *result = hkGetFullScreenTexture.fOriginal();
	return result;
}

ITexture* __fastcall Hooks::dGetRenderTarget(void* ecx, void* edx)
{
	ITexture* result = hkGetRenderTarget.fOriginal(ecx);
	return result;
}


void __fastcall Hooks::dPush3DView(void *ecx, void *edx, const CViewSetup &view, int flags, ITexture *target, void *frustum)
{
    if (!target && m_ActiveEyeTexture) target = m_ActiveEyeTexture;
    hkPush3DView.fOriginal(ecx, view, flags, target, frustum);
}

void __fastcall Hooks::dPush3DViewDepth(void *ecx, void *edx, const CViewSetup &view, int flags, ITexture *target, void *frustum, ITexture *depth)
{
    if (!target && m_ActiveEyeTexture) target = m_ActiveEyeTexture;
    hkPush3DViewDepth.fOriginal(ecx, view, flags, target, frustum, depth);
}

void __fastcall Hooks::dRenderView(void *ecx, void *edx, CViewSetup &originalSetup, int nClearFlags, int whatToDraw)
{
    CViewSetup setup = originalSetup;
	static bool loggedRenderViewEntry = false;
	if (!m_Game->TryResolveVrInterfaces())
		return hkRenderView.fOriginal(ecx, setup, nClearFlags, whatToDraw);

	if (!loggedRenderViewEntry)
	{
		PortalVrLog("dRenderView first entry ecx=%p flags=%d draw=%d view=%dx%d fov=%f origin=%f,%f,%f", ecx, nClearFlags, whatToDraw, setup.width, setup.height, setup.fov, setup.origin.x, setup.origin.y, setup.origin.z);
		loggedRenderViewEntry = true;
	}

	if (!m_VR->m_CreatedVRTextures)
		return hkRenderView.fOriginal(ecx, setup, nClearFlags, whatToDraw);

	//VPanel* g_pFullscreenRootPanel = *(VPanel**)(m_Game->m_Offsets->g_pFullscreenRootPanel.address);

	IMaterialSystem* matSystem = m_Game->GetMaterialSystem();
	if (!matSystem)
		return hkRenderView.fOriginal(ecx, setup, nClearFlags, whatToDraw);

	CViewSetup desktopView = setup;
	Vector position = setup.origin;

	if (m_VR->m_ApplyPortalRotationOffset) {
		Vector vec = position - m_VR->m_SetupOrigin;
		float distance = sqrt(vec.x * vec.x + vec.y * vec.y + vec.z * vec.z);

		// Rudimentary portalling detection
		if (distance > 35) {
			//m_VR->m_RotationOffset.x += m_VR->m_PortalRotationOffset.x;
			m_VR->m_RotationOffset.y += m_VR->m_PortalRotationOffset.y;
			//m_VR->m_RotationOffset.z += m_VR->m_PortalRotationOffset.z;

			m_VR->UpdateHMDAngles();

			m_VR->m_ApplyPortalRotationOffset = false;
		}
	}

	m_VR->m_SetupOrigin = position;
	m_VR->UpdateCameraCollision(position);

	Vector hmdAngle = m_VR->GetViewAngle();
	m_Game->SetViewAngles(QAngle(hmdAngle.x, hmdAngle.y, hmdAngle.z));

	float aspect = setup.m_flAspectRatio;

	setup.x = 0;
	setup.y = 0;
	setup.width = m_VR->m_RenderWidth;
	setup.height = m_VR->m_RenderHeight;
	setup.m_nUnscaledWidth = m_VR->m_RenderWidth;
	setup.m_nUnscaledHeight = m_VR->m_RenderHeight;
	setup.fov = m_VR->m_Fov;
	setup.fovViewmodel = m_VR->m_Fov;
	setup.m_flAspectRatio = m_VR->m_Aspect;
	setup.zNear = CameraCollision::NearClip;
	setup.zNearViewmodel = 2;
	setup.angles = hmdAngle;

	if (!m_VR->m_CreatedVRTextures)
	{
		setup.origin = m_VR->GetViewOrigin(position);
		hkRenderView.fOriginal(ecx, setup, nClearFlags, whatToDraw);
		m_PushedHud = false;
		m_VR->m_RenderedNewFrame = true;
		return;
	}

	CViewSetup leftEyeView = setup;
	CViewSetup rightEyeView = setup;

	// Left eye CViewSetup
	leftEyeView.origin = m_VR->GetViewOriginLeft(position);
    static int loggedEye = 0;
    if (++loggedEye == 120) PortalVrLog("Eye view fov=%f aspect=%f pos=%f,%f,%f angle=%f,%f,%f near=%f far=%f ortho=%d projectionOverride=%d",
        leftEyeView.fov,leftEyeView.m_flAspectRatio,leftEyeView.origin.x,leftEyeView.origin.y,leftEyeView.origin.z,
        leftEyeView.angles.x,leftEyeView.angles.y,leftEyeView.angles.z,leftEyeView.zNear,leftEyeView.zFar,leftEyeView.m_bOrtho,leftEyeView.m_bViewToProjectionOverride);

	IMatRenderContext* rndrContext = matSystem->GetRenderContext();
	if (!rndrContext)
		return hkRenderView.fOriginal(ecx, setup, nClearFlags, whatToDraw);

	m_VR->m_BindingEyeTexture = VR::Texture_LeftEye;
	rndrContext->PushRenderTargetAndViewport(
		m_VR->m_LeftEyeTexture,
		0,
		0,
		static_cast<int>(m_VR->m_RenderWidth),
		static_cast<int>(m_VR->m_RenderHeight));
	m_VR->m_BindingEyeTexture = VR::Texture_None;
	m_ActiveEyeTexture = m_VR->m_LeftEyeTexture;
	hkRenderView.fOriginal(ecx, leftEyeView, nClearFlags, whatToDraw & ~RENDERVIEW_DRAWHUD);
	m_ActiveEyeTexture = nullptr;
	rndrContext->PopRenderTargetAndViewport();
	
	// Right eye CViewSetup
	rightEyeView.origin = m_VR->GetViewOriginRight(position);

	m_VR->m_BindingEyeTexture = VR::Texture_RightEye;
	rndrContext->PushRenderTargetAndViewport(
		m_VR->m_RightEyeTexture,
		0,
		0,
		static_cast<int>(m_VR->m_RenderWidth),
		static_cast<int>(m_VR->m_RenderHeight));
	m_VR->m_BindingEyeTexture = VR::Texture_None;
	m_ActiveEyeTexture = m_VR->m_RightEyeTexture;
	hkRenderView.fOriginal(ecx, rightEyeView, nClearFlags, whatToDraw & ~RENDERVIEW_DRAWHUD);
	m_ActiveEyeTexture = nullptr;
	rndrContext->PopRenderTargetAndViewport();

	m_PushedHud = false;
	rndrContext->Release();

	/*rndrContext = matSystem->GetRenderContext();

	ITexture* fullscreenTxt = rndrContext->GetRenderTarget();

	Rect_t srcRect;
	srcRect.x = setup.x;
	srcRect.y = setup.y;
	srcRect.width = 1920;
	srcRect.height = 1080;

	rndrContext->SetRenderTarget(m_VR->m_RightEyeTexture);
	rndrContext->CopyRenderTargetToTextureEx(fullscreenTxt, 0, &srcRect, &srcRect);

	rndrContext->SetRenderTarget(NULL);
	rndrContext->Release();*/

	if (m_VR->m_RenderWindow) {
        hkRenderView.fOriginal(ecx, desktopView, nClearFlags, whatToDraw);
	}


	m_VR->m_RenderedNewFrame = true;
}

bool __fastcall Hooks::dCreateMove(void *ecx, void *edx, float flInputSampleTime, CUserCmd *cmd)
{
	if (!cmd)
		return hkCreateMove.fOriginal(ecx, flInputSampleTime, cmd);

	if (!cmd->command_number)
		return hkCreateMove.fOriginal(ecx, flInputSampleTime, cmd);

    const bool originalResult = hkCreateMove.fOriginal(ecx, flInputSampleTime, cmd);
    if (!m_VR->m_IsVREnabled)
        return originalResult;
	if (m_VR->m_IsVREnabled)
	{
		// Portal's object pickup code reads the server eye angles while +use is
		// held. Feed it the portal-gun controller for that interval so the use
		// trace and the held-object orientation follow the hand instead of the
		// HMD. The VR renderer still uses the headset pose for the camera.
		cmd->viewangles = m_VR->PressedDigitalAction(m_VR->m_ActionUse)
			? m_VR->m_RightControllerAngAbs
			: m_VR->m_HmdAngAbs;

		vr::InputAnalogActionData_t analogActionData;
		if (m_VR->GetAnalogActionData(m_VR->m_ActionWalk, analogActionData)) {
			// Run toward other guy
			cmd->buttons &= ~(IN_FORWARD | IN_BACK | IN_MOVELEFT | IN_MOVERIGHT);

			cmd->forwardmove += analogActionData.y * MAX_LINEAR_SPEED;
			cmd->sidemove += analogActionData.x * MAX_LINEAR_SPEED;

			// We'll only be moving fwd or sideways
			cmd->upmove = 0.0f;

			if (cmd->forwardmove > 0.0f)
			{
				cmd->buttons |= IN_FORWARD;
			}
			else if (cmd->forwardmove < 0.0f)
			{
				cmd->buttons |= IN_BACK;
			}

			if (cmd->sidemove > 0.0f)
			{
				cmd->buttons |= IN_MOVELEFT;
			}
			else if (cmd->sidemove < 0.0f)
			{
				cmd->buttons |= IN_MOVERIGHT;
			}

		}

		if (m_VR->m_RoomscaleActive)
		{
			// How much have we moved since last CreateMove?
			Vector setupOriginToHMD = (m_VR->m_HmdPosRelativeRaw - m_VR->m_HmdPosRelativeRawPrev) * m_VR->m_VRScale; //m_VR->m_HmdPosRelative - m_VR->m_HmdPosRelativePrev;
			m_VR->m_HmdPosRelativeRawPrev = m_VR->m_HmdPosRelativeRaw;

			setupOriginToHMD.z = 0;
			float distance = VectorLength(setupOriginToHMD);
			if (distance > 0)
			{
				float forwardSpeed = DotProduct2D(setupOriginToHMD, m_VR->m_HmdForward);
				float sideSpeed = DotProduct2D(setupOriginToHMD, m_VR->m_HmdRight);
				cmd->forwardmove += distance * forwardSpeed;
				cmd->sidemove += distance * sideSpeed;

				// Let's update the position and the previous too
				/*m_VR->m_HmdPosRelative -= setupOriginToHMD;
				m_VR->m_HmdPosRelativePrev = m_VR->m_HmdPosRelative;*/

				/*m_VR->m_Center += m_VR->m_HmdPosRelativeRaw - m_VR->m_HmdPosRelativeRawPrev;
				m_VR->m_HmdPosRelativeRawPrev = m_VR->m_HmdPosRelativeRaw;*/

				//m_VR->ResetPosition();
			}
		}
	}

	return false;
}

void __fastcall Hooks::dEndFrame(void *ecx, void *edx)
{
	return hkEndFrame.fOriginal(ecx);
}

void __fastcall Hooks::dCreateViewModel(void *ecx, void *edx, int index)
{
    hkCreateViewModel.fOriginal(ecx, index);
    if (index == 0 && m_VR->m_IsVREnabled) {
        // Use Source's second owned viewmodel. The game manages its lifetime,
        // networking and save data, and gun pickup can keep the left arm visible.
        hkCreateViewModel.fOriginal(ecx, 1);
        PortalVrLog("Created independent left-arm viewmodel");
    }
}

void __fastcall Hooks::dCalcViewModelView(void *ecx, void *edx, const Vector &eyePosition, const QAngle &eyeAngles)
{
	s_LeftArmRenderable = nullptr;
	if (m_VR->m_IsVREnabled && m_Game->m_Offsets->GetViewModel.valid) {
		using GetViewModelFn = void *(__thiscall *)(void *, int, bool);
		for (int index = 0; index < 2; ++index) {
			void *vm = reinterpret_cast<GetViewModelFn>(m_Game->m_Offsets->GetViewModel.address)(ecx, index, false);
			if (vm) {
				if (index == 1) s_LeftArmRenderable = static_cast<unsigned char *>(vm) + 4;
				using GetWeaponFn = void *(__thiscall *)(void *);
				const auto getWeapon = SigScanner::GetVirtualFunction(vm, 209);
				void *weapon = getWeapon ? reinterpret_cast<GetWeaponFn>(getWeapon)(vm) : nullptr;
				if (getWeapon && !weapon) {
					using SetWeaponModelFn = void (__thiscall *)(void *, const char *, void *);
					using RemoveEffectsFn = void (__thiscall *)(void *, int);
					const auto setModel = SigScanner::GetVirtualFunction(vm, 202);
					const auto removeEffects = SigScanner::GetVirtualFunction(vm, 208);
					if (setModel && removeEffects) {
						void *renderable = static_cast<unsigned char *>(vm) + 4;
						const auto getModel = SigScanner::GetVirtualFunction(renderable, 9);
						using GetModelFn = model_t *(__thiscall *)(void *);
						model_t *model = getModel ? reinterpret_cast<GetModelFn>(getModel)(renderable) : nullptr;
						const char *name = model && m_Game->GetModelInfo() ? m_Game->GetModelInfo()->GetModelName(model) : nullptr;
						if (!name || _stricmp(name, "models/weapons/v_hands.mdl"))
							reinterpret_cast<SetWeaponModelFn>(setModel)(vm, "models/weapons/v_hands.mdl", nullptr);
						// Keep custom hands independent of the world-player skeleton.
						// Reference-pose rendering also avoids the legacy idle animation.
						reinterpret_cast<RemoveEffectsFn>(removeEffects)(vm, 1 | 32);
					}
				}
				static int loggedModel = 0;
				if (loggedModel++ < 3) PortalVrLog("Viewmodel entity=%p weapon=%p", vm, weapon);
			}
		}
	}
	static int logged = 0;
	if (logged++ < 3) PortalVrLog("Controller viewmodel update player=%p hand=%f,%f,%f", ecx,
		m_VR->m_RightControllerPosRel.x,m_VR->m_RightControllerPosRel.y,m_VR->m_RightControllerPosRel.z);
	Vector vecNewOrigin = eyePosition;
	QAngle vecNewAngles = eyeAngles;

	//std::cout << "dCalcViewModelView: (" << m_VR->m_IsVREnabled << ")\n";

	if (m_VR->m_IsVREnabled)
	{
		vecNewOrigin = m_VR->GetRecommendedViewmodelAbsPos(eyePosition);
		vecNewAngles = m_VR->GetRecommendedViewmodelAbsAngle();
	}


	return hkCalcViewModelView.fOriginal(ecx, vecNewOrigin, vecNewAngles);
}

float __fastcall Hooks::dProcessUsercmds(void *ecx, void *edx, edict_t *player, void *buf, int numcmds, int totalcmds, int dropped_packets, bool ignore, bool paused)
{
	Server_BaseEntity *pPlayer = (Server_BaseEntity*)player->m_pUnk->GetBaseEntity();

	if (EntityIndex)
	{
		int index = EntityIndex(pPlayer);
		m_Game->m_CurrentUsercmdID = index;
	}

	return hkProcessUsercmds.fOriginal(ecx, player, buf, numcmds, totalcmds, dropped_packets, ignore, paused);
}

int Hooks::dWriteUsercmd(bf_write *buf, CUserCmd *to, CUserCmd *from)
{
	auto result =  hkWriteUsercmd.fOriginal(buf, to, from);

	// Let's write our stuff into the buffer
	if (m_VR->m_IsVREnabled)
	{
		Vector controllerPos = m_VR->GetRightControllerAbsPos();
		QAngle controllerAngles = m_VR->GetRightControllerAbsAngle();

		buf->WriteChar(-2);
		buf->WriteBitVec3Coord(controllerPos);
		buf->WriteBitAngles(controllerAngles);
	}

	return result;
}

int Hooks::dReadUsercmd(bf_read *buf, CUserCmd* move, CUserCmd* from)
{
	auto result = hkReadUsercmd.fOriginal(buf, move, from);

	int i = m_Game->m_CurrentUsercmdID;
	auto& vrPlayer = m_Game->m_PlayersVRInfo[i];

	auto pos = buf->Tell();
	int res = buf->ReadChar();

	// This means we got a VR player on the other side
	if (res == -2)
	{
		vrPlayer.isUsingVR = true;
		buf->ReadBitVec3Coord(vrPlayer.controllerPos);
		buf->ReadBitAngles(vrPlayer.controllerAngle);
	}
	else {
		vrPlayer.isUsingVR = false;
		buf->Seek(pos);
	}

	return result;
}


void Hooks::dAdjustEngineViewport(int &x, int &y, int &width, int &height)
{
	width = m_VR->m_RenderWidth;
	height = m_VR->m_RenderHeight;

	hkAdjustEngineViewport.fOriginal(x, y, width, height);
}

void Hooks::dGetViewport(void *ecx, void *edx, int &x, int &y, int &width, int &height)
{
	hkGetViewport.fOriginal(ecx, x, y, width, height);

	width = m_VR->m_RenderWidth;
	height = m_VR->m_RenderHeight;
}

int Hooks::dGetPrimaryAttackActivity(void *ecx, void *edx, void *meleeInfo)
{
	return hkGetPrimaryAttackActivity.fOriginal(ecx, meleeInfo);
}

Vector *Hooks::dEyePosition(void *ecx, void *edx, Vector *eyePos)
{
	Vector *result = hkEyePosition.fOriginal(ecx, eyePos);
	return result;
}

void Hooks::dDrawModelExecute(void *ecx, void *edx, void *state, const ModelRenderInfo_t &info, void *pCustomBoneToWorld)
{
    // Work on a copy: Source shares its cached matrices with attachments and
    // other eyes. Rewriting that cache would accumulate the controller transform.
    const auto *bones = static_cast<const matrix3x4_t *>(pCustomBoneToWorld);
    if (m_VR->m_IsVREnabled && state && bones) {
        const auto *hdr = *reinterpret_cast<const unsigned char **>(state);
        if (hdr && SigScanner::IsReadable(reinterpret_cast<uintptr_t>(hdr), 164)) {
            const char *name = reinterpret_cast<const char *>(hdr + 12);
            const int count = *reinterpret_cast<const int *>(hdr + 156);
            const auto kind = HandPose::Identify(name, count);
            const bool gun = kind == HandPose::Model::Gun;
            const bool hands = kind == HandPose::Model::Hands;
            if ((gun || hands) && SigScanner::IsReadable(reinterpret_cast<uintptr_t>(bones), count * sizeof(matrix3x4_t))
                && m_VR->m_RightControllerForward.LengthSqr() > 0.9f) {
                matrix3x4_t tracked[128];
                memcpy(tracked, bones, count * sizeof(matrix3x4_t));
                // Use the model's actual bind skeleton for skinning the arms.
                // The inherited player/viewmodel animation can displace wrists
                // relative to these meshes. Gun parts retain their animation below.
                matrix3x4_t reference[128];
                const int boneOffset = *reinterpret_cast<const int *>(hdr + 160);
                const int modelLength = *reinterpret_cast<const int *>(hdr + 76);
                if (boneOffset < 164 || modelLength < boneOffset || modelLength - boneOffset < count * 216
                    || !SigScanner::IsReadable(reinterpret_cast<uintptr_t>(hdr + boneOffset), count * 216))
                    return hkDrawModelExecute.fOriginal(ecx, state, info, pCustomBoneToWorld);
                for (int i = 0; i < count; ++i) {
                    const auto &poseToBone = *reinterpret_cast<const matrix3x4_t *>(hdr + boneOffset + i * 216 + 96);
                    reference[i] = HandPose::InverseRigid(poseToBone);
                }

                const Vector rightPosition = m_VR->GetRightHandAbsPos();
                if (gun) {
                    // The gun's local +Z is its barrel, +Y is up. Align its
                    // grip with the controller and retain animated gun parts.
                    matrix3x4_t source = reference[24];
                    for (int row = 0; row < 3; ++row) source[row][3] = reference[8][row][3];
                    const auto target = HandPose::Frame(-m_VR->m_RightControllerRight,
                        m_VR->m_RightControllerUp, m_VR->m_RightControllerForward, rightPosition);
                    for (int i = 0; i < 24; ++i) tracked[i] = HandPose::Reanchor(reference[i], source, target);
                    const auto gunTarget = HandPose::Reanchor(reference[24], source, target);
                    for (int i = 24; i < count; ++i) tracked[i] = HandPose::Reanchor(bones[i], bones[24], gunTarget);
                    HandPose::ApplyFingerCurlChain(reference, tracked, m_VR->m_RightFingerCurl, 0, 8);
                    HandPose::StraightenGunWrist(tracked);
                } else {
                    const auto rightTarget = HandPose::ControllerHandFrame(
                        m_VR->m_RightHandForward, m_VR->m_RightControllerRight,
                        m_VR->m_RightHandUp, rightPosition, false);
                    const auto leftTarget = HandPose::ControllerHandFrame(
                        m_VR->m_LeftHandForward, m_VR->m_LeftControllerRight,
                        m_VR->m_LeftHandUp, m_VR->GetLeftHandAbsPos(), true);
                    HandPose::AlignBareArms(reference, tracked, leftTarget, rightTarget);
                    HandPose::ApplyFingerCurl(reference, tracked,
                        m_VR->m_LeftFingerCurl, m_VR->m_RightFingerCurl);
                    if (s_LeftArmRenderable) {
                        const bool leftOnly = info.pRenderable == s_LeftArmRenderable;
                        const Vector hiddenAt = leftOnly ? m_VR->GetLeftHandAbsPos() : rightPosition;
                        const auto collapsed = HandPose::Frame({0,0,0},{0,0,0},{0,0,0},hiddenAt);
                        for (int i = 0; i < count; ++i)
                            if (i < 5 || (leftOnly ? i >= 24 : i < 24)) tracked[i] = collapsed;
                    }

                }
                static int logged = 0;
                if (logged++ < 6) PortalVrLog("Hand-anchored model=%s wrist=%f,%f,%f", name,
                    tracked[gun ? 8 : 27][0][3],tracked[gun ? 8 : 27][1][3],tracked[gun ? 8 : 27][2][3]);
                return hkDrawModelExecute.fOriginal(ecx, state, info, tracked);
            }
        }
    }
    return hkDrawModelExecute.fOriginal(ecx, state, info, pCustomBoneToWorld);
}

void Hooks::dPushRenderTargetAndViewport(void *ecx, void *edx, ITexture *pTexture, ITexture *pDepthTexture, int nViewX, int nViewY, int nViewW, int nViewH)
{
	if (m_VR->m_CreatedVRTextures && !m_PushedHud)
	{
		auto *materialSystem = m_Game->GetMaterialSystem();
		if (!materialSystem)
			return hkPushRenderTargetAndViewport.fOriginal(ecx, pTexture, pDepthTexture, nViewX, nViewY, nViewW, nViewH);

		pTexture = m_VR->m_HUDTexture;

		//pTexture = m_VR->m_RightEyeTexture;

		IMatRenderContext *renderContext = materialSystem->GetRenderContext();
		renderContext->ClearBuffers(false, true, true);
		renderContext->Release();

		hkPushRenderTargetAndViewport.fOriginal(ecx, pTexture, pDepthTexture, nViewX, nViewY, nViewW, nViewH);

		renderContext = materialSystem->GetRenderContext();
		renderContext->OverrideAlphaWriteEnable(true, true);
		renderContext->ClearColor4ub(0, 0, 0, 0);
		renderContext->ClearBuffers(true, false);
		renderContext->Release();

		m_VR->m_RenderedHud = true;
		m_PushedHud = true;
	}
	else
	{
		hkPushRenderTargetAndViewport.fOriginal(ecx, pTexture, pDepthTexture, nViewX, nViewY, nViewW, nViewH);
	}
}

void Hooks::dPopRenderTargetAndViewport(void *ecx, void *edx)
{
	if (!m_VR->m_CreatedVRTextures)
		return hkPopRenderTargetAndViewport.fOriginal(ecx);

	//std::cout << "dPopRenderTargetAndViewport: " << m_PushHUDStep << "\n";

	m_PushHUDStep = 0;

	if (m_PushedHud)
	{
		if (IMaterialSystem *materialSystem = m_Game->GetMaterialSystem())
		{
			IMatRenderContext* renderContext = materialSystem->GetRenderContext();
			renderContext->OverrideAlphaWriteEnable(false, true);
			renderContext->ClearColor4ub(0, 0, 0, 255);
			renderContext->Release();
		}
	}

	hkPopRenderTargetAndViewport.fOriginal(ecx);
}

void Hooks::dVGui_Paint(void *ecx, void *edx, int mode)
{
	if (!m_VR->m_CreatedVRTextures || m_Game->IsCursorVisible())
		return hkVgui_Paint.fOriginal(ecx, mode);

	//std::cout << "dVGui_Paint\n";

	if (m_PushedHud)
		mode = PAINT_UIPANELS | PAINT_INGAMEPANELS;

	hkVgui_Paint.fOriginal(ecx, mode);
}

int Hooks::dIsSplitScreen()
{
	//std::cout << "dIsSplitScreen: " << m_PushHUDStep << "\n";

	if (m_PushHUDStep == 0)
		++m_PushHUDStep;
	else
		m_PushHUDStep = -999;

	return hkIsSplitScreen.fOriginal();
}

DWORD *Hooks::dPrePushRenderTarget(void *ecx, void *edx, int a2)
{
	//std::cout << "dPrePushRenderTarget: " << m_PushHUDStep << "\n";

	if (m_PushHUDStep == 1)
		++m_PushHUDStep;
	else
		m_PushHUDStep = -999;

	return hkPrePushRenderTarget.fOriginal(ecx, a2);
}

Vector* Hooks::dWeapon_ShootPosition(void* ecx, void* edx, Vector* eyePos)
{
	Vector* result = hkWeapon_ShootPosition.fOriginal(ecx, eyePos);

	if (!EntityIndex)
		return result;

	int localIndex = m_Game->GetLocalPlayerIndex();
	int index = EntityIndex(ecx);

	auto vrPlayer = m_Game->m_PlayersVRInfo[index];

	if (m_VR->m_IsVREnabled && localIndex == index) {
		*result = m_VR->GetRightControllerAbsPos();	
	}
	else if (vrPlayer.isUsingVR)
	{
		*result = vrPlayer.controllerPos;
	}

	return result;
}

void* Hooks::dCWeaponPortalgun_FirePortal(void* ecx, void* edx, bool isSecondaryPortal, Vector* pVector) {
	auto result = hkCWeaponPortalgun_FirePortal.fOriginal(ecx, isSecondaryPortal, pVector);

	return result;
}

float __fastcall Hooks::dTraceFirePortal(void* ecx, void* edx, bool secondary,
    const Vector& start, const Vector& direction, void* trace,
    Vector& finalPosition, QAngle& finalAngles, int placedBy, bool test)
{
    Vector shotStart = start;
    Vector shotDirection = direction;
    if (placedBy == 2 && m_VR->m_IsVREnabled) {
        shotStart = m_VR->GetRightHandAbsPos();
        shotDirection = m_VR->m_RightControllerForward;
        static int logged = 0;
        if (!test && logged++ < 20)
            PortalVrLog("Controller portal shot secondary=%d hand=%f,%f,%f direction=%f,%f,%f headDirection=%f,%f,%f",
                secondary,shotStart.x,shotStart.y,shotStart.z,
                shotDirection.x,shotDirection.y,shotDirection.z,direction.x,direction.y,direction.z);
    }
    return hkTraceFirePortal.fOriginal(ecx, secondary, shotStart, shotDirection, trace,
        finalPosition, finalAngles, placedBy, test);
}

void __fastcall Hooks::dPlayerPortalled(void* ecx, void* edx, void* a2, __int64 a3)
{
	CBaseEntity* pBaseEntity = (CBaseEntity*)ecx;

	QAngle angAbsRotationBefore;
	m_Game->GetViewAngles(angAbsRotationBefore);

	hkPlayerPortalled.fOriginal(ecx, a2, a3);

	QAngle angAbsRotationAfter;
	m_Game->GetViewAngles(angAbsRotationAfter);

	if (angAbsRotationBefore != angAbsRotationAfter) {
		m_VR->m_PortalRotationOffset = angAbsRotationAfter - angAbsRotationBefore;
		m_VR->m_ApplyPortalRotationOffset = true;
	}

	return;
}

int Hooks::dGetModeHeight(void* ecx, void* edx) {
	//std::cout << "dGetModeHeight\n";
	return m_VR->m_RenderHeight;
}

bool Hooks::dClipTransform(const Vector& point, Vector* pScreen)
{
	return hkClipTransform.fOriginal(point, pScreen);
}

bool Hooks::ScreenTransform(const Vector& point, Vector* pScreen, int width, int height)
{
	bool retval = hkClipTransform.fOriginal(point, pScreen);

	pScreen->x = 0.5f * (pScreen->x + 1.0f) * width;
	pScreen->y = 0.5f * (-pScreen->y + 1.0f) * height;

	return retval;
}

int __fastcall Hooks::dDrawSelf(void* ecx, void* edx, int x, int y, int w, int h, const void* clr, float flApparentZ) {
	//std::cout << "dDrawSelf - X: " << x << ", Y: " << y << ", W: " << w << ", H: " << h << ", Z: " << flApparentZ << "\n";

	//int playerIndex = m_Game->m_EngineClient->GetLocalPlayer();

	//auto viewport = m_Game->m_ClientMode->GetViewport();

	int newX = x;
	int	newY = y;

	if (m_VR->m_IsVREnabled)
	{
		int windowWidth, windowHeight;
		if (IMaterialSystem *materialSystem = m_Game->GetMaterialSystem())
		{
			IMatRenderContext *renderContext = materialSystem->GetRenderContext();
			renderContext->GetWindowSize(windowWidth, windowHeight);
			renderContext->Release();
		}
		else
		{
			windowWidth = m_VR->m_RenderWidth;
			windowHeight = m_VR->m_RenderHeight;
		}

		Vector screen = { 0, 0, 0 };

		//Vector vec = m_VR->m_AimPos - m_VR->GetRightControllerAbsPos();

		//newZ = 1.0 / sqrt(vec.x * vec.x + vec.y * vec.y + vec.z * vec.z);

		ScreenTransform(m_VR->m_AimPos, &screen, m_VR->m_RenderWidth, m_VR->m_RenderHeight);

		int offsetX = x - (windowWidth * 0.5f);
		int offsetY = y - (windowHeight * 0.5f);

		newX = screen.x + offsetX;
		newY = screen.y + offsetY;
	}

	return hkDrawSelf.fOriginal(ecx, newX, newY, w, h, clr, flApparentZ);
}

void __cdecl Hooks::dVGui_GetHudBounds(int slot, int& x, int& y, int& w, int& h) {
	if (m_VR->m_IsVREnabled && !m_Game->IsCursorVisible())
	{
		x = y = 0;
		w = m_VR->m_RenderWidth;
		h = m_VR->m_RenderHeight;
	} else {
		hkVGui_GetHudBounds.fOriginal(slot, x, y, w, h);
	}

	//std::cout << "dVGui_GetHudBounds - X: " << x << ", Y: " << y << ", W: " << w << ", H: " << h << "\n";
}

void __cdecl Hooks::dVGui_GetPanelBounds(int slot, int& x, int& y, int& w, int& h) {
	if (m_VR->m_IsVREnabled && !m_Game->IsCursorVisible())
	{
		x = y = 0;
		w = m_VR->m_RenderWidth;
		h = m_VR->m_RenderHeight;
	}
	else {
		hkVGui_GetPanelBounds.fOriginal(slot, x, y, w, h);
	}

	//std::cout << "dVGui_GetPanelBounds - X: " << x << ", Y: " << y << ", W: " << w << ", H: " << h << "\n";
}

void __cdecl Hooks::dVGUI_UpdateScreenSpaceBounds(int nNumSplits, int sx, int sy, int sw, int sh) {
	hkVGUI_UpdateScreenSpaceBounds.fOriginal(nNumSplits, sx, sy, m_VR->m_RenderWidth, m_VR->m_RenderHeight);
}

void __cdecl Hooks::dVGui_GetTrueScreenSize(int &w, int &h) {
	w = m_VR->m_RenderWidth;
	h = m_VR->m_RenderHeight;
}

void __fastcall Hooks::dGetScreenSize(void* ecx, void* edx, int& wide, int& tall) {
	//hkGetScreenSize.fOriginal(ecx, wide, tall);
	wide = m_VR->m_RenderWidth;
	tall = m_VR->m_RenderHeight;
}

void __cdecl Hooks::dGetHudSize(int& w, int& h) {
	w = m_VR->m_RenderWidth;
	h = m_VR->m_RenderHeight;
}

void __fastcall Hooks::dPush2DView(void* ecx, void* edx, IMatRenderContext* pRenderContext, const CViewSetup& view, int nFlags, ITexture* pRenderTarget, void* frustumPlanes) {
	m_PushedHud = false;

	return hkPush2DView.fOriginal(ecx, pRenderContext, view, nFlags, pRenderTarget, frustumPlanes);
}

void __fastcall Hooks::dRender(void* ecx, void* edx, vrect_t* rect) {
	//std::cout << "dRender - X: " << rect->x << ", Y: " << rect->y << ", W: " << rect->width << ", H: " << rect->height  << "\n";

	return hkRender.fOriginal(ecx, rect);
}

void __fastcall Hooks::dSetBounds(void* ecx, void* edx, int x, int y, int w, int h) {
	std::cout << "dSetBounds - X: " << x << ", Y: " << y << ", W: " << w << ", H: " << h << "\n";

	hkSetBounds.fOriginal(ecx, x, y, m_VR->m_RenderWidth, m_VR->m_RenderHeight);
}

void __fastcall Hooks::dSetSize(void* ecx, void* edx, int wide, int tall) {
	hkSetSize.fOriginal(ecx, wide, tall);

	//std::cout << "dSetSize - Wide: " << wide << ", Tall: " << tall  << "\n";
}

void __fastcall Hooks::dGetClipRect(void* ecx, void* edx, int& x0, int& y0, int& x1, int& y1) {
	hkGetClipRect.fOriginal(ecx, x0, y0, x1, y1);

	//std::cout << "dGetClipRect - X: " << x0 << ", Y: " << y0 << ", W: " << x1 << ", H: " << y1  << "\n";
}

double __fastcall Hooks::dComputeError(void* ecx, void* edx) {
	bool wasTrue = m_VR->m_OverrideEyeAngles;

	m_VR->m_OverrideEyeAngles = true;

	double computedError = hkComputeError.fOriginal(ecx);

	if (!wasTrue)
		m_VR->m_OverrideEyeAngles = false;

	return computedError;
}

bool __fastcall Hooks::dUpdateObject(void* ecx, void* edx, void* pPlayer, float flError, bool bIsTeleport) {
	bool wasTrue = m_VR->m_OverrideEyeAngles;

	m_VR->m_OverrideEyeAngles = true;

	bool value = hkUpdateObject.fOriginal(ecx, pPlayer, flError, bIsTeleport);

	if (!wasTrue)
		m_VR->m_OverrideEyeAngles = false;

	return value;
}

bool __fastcall Hooks::dUpdateObjectVM(void* ecx, void* edx, void* pPlayer, float flError) {
	bool wasTrue = m_VR->m_OverrideEyeAngles;

	m_VR->m_OverrideEyeAngles = true;

	bool value = hkUpdateObjectVM.fOriginal(ecx, pPlayer, flError);

	if (!wasTrue)
		m_VR->m_OverrideEyeAngles = false;

	return value;
}

// This function is apparently not used by Portal 2, remove?
void __fastcall Hooks::dRotateObject(void* ecx, void* edx, void* pPlayer, float fRotAboutUp, float fRotAboutRight, bool bUseWorldUpInsteadOfPlayerUp) {
	bool wasTrue = m_VR->m_OverrideEyeAngles;

	m_VR->m_OverrideEyeAngles = true;

	hkRotateObject.fOriginal(ecx, pPlayer, fRotAboutUp, fRotAboutRight, bUseWorldUpInsteadOfPlayerUp);

	if (!wasTrue)
		m_VR->m_OverrideEyeAngles = false;
}

// This is CPlayerBase, do we also need to hook CPortalPlayer? can the same function be used by both?
// This works for release, but why was it crashing before??? TODO: buy a c++ book...
QAngle& __fastcall Hooks::dEyeAngles(void* ecx, void* edx) {
	if (m_VR->m_OverrideEyeAngles && EntityIndex) {
		int localIndex = m_Game->GetLocalPlayerIndex();
		int index = EntityIndex(ecx);

		auto& vrPlayer = m_Game->m_PlayersVRInfo[index];

		if (m_VR->m_IsVREnabled && localIndex == index) {
			return m_VR->GetRightControllerAbsAngleConst();
		}
		else if (vrPlayer.isUsingVR)
		{
			return vrPlayer.controllerAngle;
		}
	}

	return hkEyeAngles.fOriginal(ecx);
}

int __fastcall Hooks::dGetDefaultFOV(void* ecx, void* edx) {
	return m_VR->m_Fov;
}

double __fastcall Hooks::dGetFOV(void* ecx, void* edx) {
	return m_VR->m_Fov;
}

float __fastcall Hooks::dGetViewModelFOV(void* ecx, void* edx) {
	return m_VR->m_Fov;
}
