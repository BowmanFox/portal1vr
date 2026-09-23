#include "hooks.h"
#include "game.h"
#include "texture.h"
#include "sdk.h"
#include "sdk_server.h"
#include "trace.h"
#include "vr.h"
#include "offsets.h"
#include "portal1.h"
#include "debuglog.h"
#include "handpose.h"
#include "optionalgungrip.h"
#include "gunattachments.h"
#include "firstpersonbody.h"
#include "cameracollision.h"
#include "portalpose.h"
#include "pickuptrace.h"
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
Hook<tGetAttachmentMatrix> Hooks::hkGetAttachmentMatrix = {};
Hook<tGetAttachmentAngles> Hooks::hkGetAttachmentAngles = {};
static void *s_RightViewmodelRenderable = nullptr;
static void *s_GunAttachmentRenderable = nullptr;
static const void *s_GunAttachmentModel = nullptr;
static GunAttachments::Model s_GunAttachments;
static void *s_LeftArmRenderable = nullptr;
static void *s_LocalPlayerEntity = nullptr;
static void *s_LocalPlayerRenderable = nullptr;
static bool s_DrawingLocalPlayerBodyDirect = false;
static bool s_ActiveFirstPersonBodyPass = false;
static bool s_InlineBodyDrawEligible = false;
static bool s_BodyDrawTriggered = false;
static bool s_HasLocalPlayerBodyTransform = false;
static Vector s_LocalPlayerBodyOrigin = {0, 0, 0};
static QAngle s_LocalPlayerBodyAngles = {0, 0, 0};
static Vector s_LocalPlayerBodyDrawOffset = {0, 0, 0};
static struct { Vector origin, angles; float zNear, fov; } s_BodyExpectedView{};
static Vector s_BodyCameraCenter = {0, 0, 0};
static std::vector<bool> s_BodyViewStack;

static void ExpectBodyView(const CViewSetup &view)
{
    s_BodyExpectedView.origin = view.origin;
    s_BodyExpectedView.angles = view.angles;
    s_BodyExpectedView.zNear = view.zNear;
    s_BodyExpectedView.fov = view.fov;
}

static bool IsBodyWorldView(const CViewSetup &view, ITexture *target, ITexture *depth)
{
    return s_InlineBodyDrawEligible && !depth
        && (!target || target == Hooks::m_ActiveEyeTexture)
        && !view.m_bOrtho
        && (view.origin - s_BodyExpectedView.origin).LengthSqr() < 0.0001f
        && (view.angles - s_BodyExpectedView.angles).LengthSqr() < 0.0001f
        && fabsf(view.zNear - s_BodyExpectedView.zNear) < 0.001f
        && fabsf(view.fov - s_BodyExpectedView.fov) < 0.001f;
}
Hook<tProcessUsercmds> Hooks::hkProcessUsercmds = {};
Hook<tReadUsercmd> Hooks::hkReadUsercmd = {};
Hook<tWriteUsercmdDeltaToBuffer> Hooks::hkWriteUsercmdDeltaToBuffer = {};
Hook<tWriteUsercmd> Hooks::hkWriteUsercmd = {};
Hook<tAdjustEngineViewport> Hooks::hkAdjustEngineViewport = {};
Hook<tViewport> Hooks::hkViewport = {};
Hook<tGetViewport> Hooks::hkGetViewport = {};
Hook<tGetPrimaryAttackActivity> Hooks::hkGetPrimaryAttackActivity = {};
Hook<tDrawModelExecute> Hooks::hkDrawModelExecute = {};
Hook<tPushRenderTargetAndViewport> Hooks::hkPushRenderTargetAndViewport = {};
Hook<tPopRenderTargetAndViewport> Hooks::hkPopRenderTargetAndViewport = {};
Hook<tVgui_Paint> Hooks::hkVgui_Paint = {};
Hook<tIsSplitScreen> Hooks::hkIsSplitScreen = {};
Hook<tPrePushRenderTarget> Hooks::hkPrePushRenderTarget = {};
Hook<tGetFullScreenTexture> Hooks::hkGetFullScreenTexture = {};
Hook<tEyePosition> Hooks::hkEyePosition = {};
Hook<tWeapon_ShootPosition> Hooks::hkWeapon_ShootPosition = {};
Hook<tTraceFirePortal> Hooks::hkTraceFirePortal = {};

Hook<tGetModeHeight> Hooks::hkGetModeHeight = {};
Hook<tDrawSelf> Hooks::hkDrawSelf = {};
Hook<tClipTransform> Hooks::hkClipTransform = {};
Hook<tPlayerPortalled> Hooks::hkPlayerPortalled = {};
Hook<tPlayerUse> Hooks::hkPlayerUse = {};
Hook<tFindUseEntity> Hooks::hkFindUseEntity = {};
Hook<tVGui_GetHudBounds> Hooks::hkVGui_GetHudBounds = {};
Hook<tVGui_GetPanelBounds> Hooks::hkVGui_GetPanelBounds = {};
Hook<tVGUI_UpdateScreenSpaceBounds> Hooks::hkVGUI_UpdateScreenSpaceBounds = {};
Hook<tVGui_GetTrueScreenSize> Hooks::hkVGui_GetTrueScreenSize = {};
Hook<tSetBounds> Hooks::hkSetBounds = {};
Hook<tGetScreenSize> Hooks::hkGetScreenSize = {};
Hook<tPush2DView> Hooks::hkPush2DView = {};
Hook<tPopView> Hooks::hkPopView = {};
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
tGetOwner Hooks::GetOwner = nullptr;
tGetFullScreenTexture Hooks::GetFullScreenTexture = nullptr;

namespace
{
	struct PickupQueryPose { void* player; Vector origin; QAngle angles; };
	thread_local PickupQueryPose* s_PickupQuery = nullptr;
	struct ScopedPickupQuery {
		PickupQueryPose* previous;
		explicit ScopedPickupQuery(PickupQueryPose& query) : previous(s_PickupQuery) { s_PickupQuery = &query; }
		~ScopedPickupQuery() { s_PickupQuery = previous; }
	};

	bool ServerHandPose(void *player, Vector &position, QAngle &angles)
	{
		auto *vr = Hooks::m_VR;
		if (!vr || !vr->m_GrabPoseValid || !Hooks::hkEyePosition.isCreated()
			|| !Hooks::hkEyeAngles.isCreated()) return false;
		Vector eye;
		const Vector *actualEye = Hooks::hkEyePosition.fOriginal(player, &eye);
		if (!actualEye) return false;
		const auto hand = PortalPose::WorldHand(vr->m_GrabHandRelative,
			*actualEye, Hooks::hkEyeAngles.fOriginal(player));
		position = PortalPose::Position(hand);
		angles = PortalPose::Angles(hand);
		return true;
	}

	int ServerEntityIndex(void *entity)
	{
		const uintptr_t target = SigScanner::GetVirtualFunction(entity,
			Portal1::VTableIndex::kServerEntity_GetRefEHandle);
		if (!target) return -1;
		using GetHandleFn = const unsigned int &(__thiscall *)(void *);
		const unsigned int handle = reinterpret_cast<GetHandleFn>(target)(entity);
		return handle == 0xffffffffu ? -1 : static_cast<int>(handle & 0xfffu);
	}

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

	uintptr_t FindPortalPlayerFunction(size_t index)
	{
		// CPortal_Player owns the complete object vtable in Portal 1, but the
		// two accessors used by the pickup code are inherited from CBasePlayer.
		// Try the derived table first and retain the base-table fallback for
		// builds whose RTTI is stripped or laid out differently.
		for (const char *typeName : { ".?AVCPortal_Player@@", ".?AVCBasePlayer@@" })
		{
			const uintptr_t function = SigScanner::FindRttiVtableFunction(
				"server.dll", typeName, index);
			if (function)
				return function;
		}
		return 0;
	}

	struct StudioBodyView
	{
		const unsigned char *header = nullptr;
		int count = 0;
		int boneOffset = 0;
		int modelLength = 0;
	};

	bool GetStudioBodyView(void *state, StudioBodyView &view)
	{
		if (!state || !SigScanner::IsReadable(reinterpret_cast<uintptr_t>(state), sizeof(void *)))
			return false;

		const auto *header = *reinterpret_cast<const unsigned char * const *>(state);
		if (!header || !SigScanner::IsReadable(reinterpret_cast<uintptr_t>(header), 164))
			return false;

		const int modelLength = *reinterpret_cast<const int *>(header + 76);
		const int count = *reinterpret_cast<const int *>(header + 156);
		const int boneOffset = *reinterpret_cast<const int *>(header + 160);
		if (modelLength <= 0 || count <= 0 || count > FirstPersonBody::MaxBones
			|| boneOffset < 164 || boneOffset > modelLength
			|| modelLength - boneOffset < count * 216
			|| !SigScanner::IsReadable(reinterpret_cast<uintptr_t>(header + boneOffset), count * 216))
			return false;

		view.header = header;
		view.count = count;
		view.boneOffset = boneOffset;
		view.modelLength = modelLength;
		return true;
	}

	const char *GetStudioBoneName(const StudioBodyView &view, int index)
	{
		if (index < 0 || index >= view.count)
			return nullptr;

		const auto *bone = view.header + view.boneOffset + index * 216;
		const int nameOffset = *reinterpret_cast<const int *>(bone);
		if (nameOffset <= 0 || nameOffset >= view.modelLength - (bone - view.header))
			return nullptr;

		const auto *name = bone + nameOffset;
		return SigScanner::IsReadable(reinterpret_cast<uintptr_t>(name), 1)
			? reinterpret_cast<const char *>(name) : nullptr;
	}

	int FindStudioBone(const StudioBodyView &view, const char *wanted)
	{
		if (!wanted)
			return -1;

		for (int i = 0; i < view.count; ++i)
		{
			const char *name = GetStudioBoneName(view, i);
			if (name && !_stricmp(name, wanted))
				return i;
		}

		return -1;
	}

	bool IsPlayerModelName(const char *name)
	{
		if (!name)
			return false;

		if (!_strnicmp(name, "models/", 7))
			name += 7;

		// This intentionally accepts any player model, including the custom
		// Chell model supplied by the VPK.  It does not replace or rewrite the
		// model; it only identifies the local player's normal draw call.
		return !_strnicmp(name, "player/", 7);
	}

	bool IsLocalPlayerBody(const ModelRenderInfo_t &info)
	{
		if (!Hooks::m_Game || !Hooks::m_VR || !s_ActiveFirstPersonBodyPass
			|| !Hooks::m_VR->m_IsVREnabled || !Hooks::m_VR->m_FirstPersonBody
			|| !s_DrawingLocalPlayerBodyDirect || !info.pModel)
			return false;

		IModelInfo *modelInfo = Hooks::m_Game->GetModelInfo();
		const char *modelName = modelInfo ? modelInfo->GetModelName(info.pModel) : nullptr;
		if (!IsPlayerModelName(modelName))
			return false;

		const int localIndex = Hooks::m_Game->GetLocalPlayerIndex();
		return (localIndex > 0 && info.entity_index == localIndex)
			|| info.pRenderable == s_LocalPlayerRenderable
			|| info.pRenderable == s_LocalPlayerEntity;
	}

	bool TranslateFirstPersonBodyBones(void *state, const matrix3x4_t *source,
		matrix3x4_t *result)
	{
		StudioBodyView view;
		if (!source || !result || !GetStudioBodyView(state, view)
			|| !SigScanner::IsReadable(reinterpret_cast<uintptr_t>(source), view.count * sizeof(matrix3x4_t)))
			return false;

		memcpy(result, source, view.count * sizeof(matrix3x4_t));
		if (!s_DrawingLocalPlayerBodyDirect) return true;
		// Align the model's eye midpoint under the center camera, never one
		// stereo eye. Horizontal correction preserves the animated foot height.
		Vector offset = s_LocalPlayerBodyDrawOffset;
		bool hasEyeAttachment = false;
		// Procedural QC eyes are skinned to the head, so optional eye bones
		// may no longer be evaluated. Use the model's authored eyes attachment.
		if (view.modelLength >= 248 && SigScanner::IsReadable(
			reinterpret_cast<uintptr_t>(view.header), view.modelLength)) {
			const int attachmentCount = *reinterpret_cast<const int *>(view.header + 240);
			const int attachmentOffset = *reinterpret_cast<const int *>(view.header + 244);
			if (attachmentCount > 0 && attachmentCount <= 256 && attachmentOffset >= 248
				&& attachmentOffset <= view.modelLength - attachmentCount * 92) {
				for (int i = 0; i < attachmentCount; ++i) {
					const int at = attachmentOffset + i * 92;
					const auto *attachment = view.header + at;
					const int nameOffset = *reinterpret_cast<const int *>(attachment);
					const int bone = *reinterpret_cast<const int *>(attachment + 8);
					if (nameOffset <= 0 || nameOffset > view.modelLength - at - 5
						|| bone < 0 || bone >= view.count
						|| memcmp(attachment + nameOffset, "eyes", 5)) continue;
					const auto &local = *reinterpret_cast<const matrix3x4_t *>(attachment + 12);
					const auto world = HandPose::Concat(source[bone], local);
					const Vector eyes(world[0][3], world[1][3], world[2][3]);
					if (std::isfinite(eyes.x) && std::isfinite(eyes.y) && std::isfinite(eyes.z)) {
						offset = FirstPersonBody::HorizontalCameraOffset(eyes, s_BodyCameraCenter);
						hasEyeAttachment = true;
					}
					break;
				}
			}
		}
		const int leftEye = FindStudioBone(view, "LeftEye");
		const int rightEye = FindStudioBone(view, "RightEye");
		if (!hasEyeAttachment && leftEye >= 0 && rightEye >= 0) {
			const Vector eyes((source[leftEye][0][3] + source[rightEye][0][3]) * 0.5f,
				(source[leftEye][1][3] + source[rightEye][1][3]) * 0.5f,
				(source[leftEye][2][3] + source[rightEye][2][3]) * 0.5f);
			offset = FirstPersonBody::HorizontalCameraOffset(eyes, s_BodyCameraCenter);
		}
		// Set the first-person torso behind the camera without moving hands,
		// collision, or the complete player model seen through portals.
		offset += FirstPersonBody::BackwardOffset(s_BodyExpectedView.angles.y,
			Hooks::m_VR->m_FirstPersonBodyBackOffset);
		for (int i = 0; i < view.count; ++i) {
			result[i][0][3] += offset.x;
			result[i][1][3] += offset.y;
		}

		return true;
	}

	bool BuildFirstPersonBodyBones(void *state, const matrix3x4_t *source,
		matrix3x4_t *result, const ModelRenderInfo_t &)
	{
		StudioBodyView view;
		if (!source || !result || !GetStudioBodyView(state, view)
			|| !TranslateFirstPersonBodyBones(state, source, result))
			return false;

		int parents[FirstPersonBody::MaxBones]{};
		for (int i = 0; i < view.count; ++i)
		{
			const auto *bone = view.header + view.boneOffset + i * 216;
			parents[i] = *reinterpret_cast<const int *>(bone + 4);
		}

		int hiddenRoots[3]{};
		int hiddenRootCount = 0;
		// Keep the chest and upper torso visible when looking down. Hide only
		// the head and untracked arms, closing each at its own attachment.
		for (const char *candidate : {"neck", "clavicle_L", "clavicle_R"})
		{
			const int root = FindStudioBone(view, candidate);
			if (root >= 0 && hiddenRootCount < 3)
				hiddenRoots[hiddenRootCount++] = root;
		}

		if (hiddenRootCount == 0)
			return s_DrawingLocalPlayerBodyDirect
				&& s_LocalPlayerBodyDrawOffset.LengthSqr() > 0.0001f;

		FirstPersonBody::CollapseBranchesAtRoots(result, parents, view.count,
			hiddenRoots, hiddenRootCount);
		return true;
	}

	bool GetRenderableTransform(void *renderable, Vector &origin, QAngle &angles)
	{
		if (!renderable)
			return false;

		const uintptr_t originTarget = SigScanner::GetVirtualFunction(
			renderable, Portal1::VTableIndex::kClientRenderable_GetRenderOrigin);
		const uintptr_t anglesTarget = SigScanner::GetVirtualFunction(
			renderable, Portal1::VTableIndex::kClientRenderable_GetRenderAngles);
		if (!originTarget || !anglesTarget)
			return false;

		using GetVectorFn = const Vector &(__thiscall *)(void *);
		using GetAnglesFn = const QAngle &(__thiscall *)(void *);
		const Vector &renderOrigin = reinterpret_cast<GetVectorFn>(originTarget)(renderable);
		const QAngle &renderAngles = reinterpret_cast<GetAnglesFn>(anglesTarget)(renderable);
		if (!std::isfinite(renderOrigin.x) || !std::isfinite(renderOrigin.y)
			|| !std::isfinite(renderOrigin.z) || !std::isfinite(renderAngles.x)
			|| !std::isfinite(renderAngles.y) || !std::isfinite(renderAngles.z))
			return false;

		origin = renderOrigin;
		angles = renderAngles;
		return true;
	}

	int DrawLocalPlayerBodyDirect()
	{
		if (!Hooks::m_Game || !Hooks::m_VR || !s_ActiveFirstPersonBodyPass
			|| !Hooks::m_VR->m_IsVREnabled || !Hooks::m_VR->m_FirstPersonBody)
			return 0;
		// The first-person copy is useful below the headset, but must never
		// obscure forward aim. Portal/mirror world models keep their usual draw.
		if (!FirstPersonBody::LookingDown(s_BodyExpectedView.angles.x))
			return 0;

		void *player = Hooks::m_Game->GetLocalPortalPlayer();
		if (!player)
			return 0;

		// Portal keeps the renderable interface in the secondary subobject used
		// by the existing viewmodel path. GetModel is safe to call here, but its
		// DrawModel method still applies the first-person visibility rejection.
		// Use the engine model-render interface for the actual submission so the
		// normal model, animation, materials, and lighting remain engine-owned.
		void *renderable = static_cast<unsigned char *>(player) + 4;
		const uintptr_t getModelTarget = SigScanner::GetVirtualFunction(
			renderable, Portal1::VTableIndex::kClientRenderable_GetModel);
		if (!getModelTarget)
			return 0;

		using GetModelFn = model_t *(__thiscall *)(void *);
		model_t *model = reinterpret_cast<GetModelFn>(getModelTarget)(renderable);
		if (!model)
			return 0;

		IModelRender *modelRender = Hooks::m_Game->GetModelRender();
		if (!modelRender)
			return 0;

		// Read the renderable's live transform first. This remains valid even
		// when Source suppresses the normal first-person player draw, and follows
		// crouching, portals, and elevators without a guessed eye-height offset.
		// The ModelRenderInfo transform is the safe fallback for engines that do
		// not expose these renderable accessors.
		Vector origin = Hooks::m_VR->m_SetupOrigin - Vector(0, 0, 64.0f);
		QAngle angles = Hooks::m_VR->m_HmdAngAbs;
		QAngle renderAngles;
		if (GetRenderableTransform(renderable, origin, renderAngles))
		{
			// Keep the model transform paired with the live bone palette. The HMD
			// can look independently of the player's body; rotating the model to
			// HMD yaw while retaining Source's bones makes the mesh shear/drift.
			angles = renderAngles;
		}
		else if (s_HasLocalPlayerBodyTransform)
		{
			origin = s_LocalPlayerBodyOrigin;
			angles = s_LocalPlayerBodyAngles;
		}

		// The camera moves by the tracked HMD displacement while Source's player
		// entity remains at its locomotion origin. Apply the same horizontal
		// displacement to the temporary bone palette so room-scale movement cannot
		// leave the body behind. Include the collision correction because the eye
		// view can be pushed away from the desired tracked position near a wall.
		// Do not apply Z: leaning/crouching must not lift the feet off the floor.
		// The desktop mirror uses the ordinary world view, so it receives no
		// tracked offset.
		Vector trackingOffset = {0, 0, 0};
		if (Hooks::m_ActiveEyeTexture && Hooks::m_VR->m_6DOF)
		{
			trackingOffset = Hooks::m_VR->m_HmdPosRelative;
			trackingOffset += Hooks::m_VR->m_CameraCollisionOffset;
			trackingOffset.z = 0.0f;
		}
		const int entityIndex = Hooks::m_Game->GetLocalPlayerIndex();
		if (entityIndex <= 0)
			return 0;

		s_LocalPlayerEntity = player;
		s_LocalPlayerRenderable = renderable;
		const bool wasDrawingDirect = s_DrawingLocalPlayerBodyDirect;
		const Vector previousDrawOffset = s_LocalPlayerBodyDrawOffset;
		s_LocalPlayerBodyDrawOffset = trackingOffset;
		s_DrawingLocalPlayerBodyDirect = true;
		const int result = modelRender->DrawModel(
			1, renderable, 0, entityIndex, model, origin, angles, 0, 0, 0);
		s_DrawingLocalPlayerBodyDirect = wasDrawingDirect;
		s_LocalPlayerBodyDrawOffset = previousDrawOffset;
		static int diagnosticDraws = 0;
		if (diagnosticDraws++ < 8)
		{
			const char *modelName = Hooks::m_Game->GetModelInfo()
				? Hooks::m_Game->GetModelInfo()->GetModelName(model) : nullptr;
			PortalVrLog("First-person direct draw pass=%d eye=%p model=%s player=%p renderable=%p result=%d origin=%f,%f,%f offset=%f,%f,%f angles=%f,%f,%f",
				s_ActiveFirstPersonBodyPass,
				Hooks::m_ActiveEyeTexture, modelName ? modelName : "<unknown>",
				player, renderable, result,
				origin.x, origin.y, origin.z,
				trackingOffset.x, trackingOffset.y, trackingOffset.z,
				angles.x, angles.y, angles.z);
		}
		return result;
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
	EnableIfCreated(hkPush2DView);
	EnableIfCreated(hkPopView);
	EnableIfCreated(hkPush3DViewDepth);
	EnableIfCreated(hkTraceFirePortal);
	EnableIfCreated(hkCWeaponPortalgun_FirePortal);
	EnableIfCreated(hkEyePosition);
	EnableIfCreated(hkWeapon_ShootPosition);
	EnableIfCreated(hkComputeError);
	EnableIfCreated(hkUpdateObject);
	EnableIfCreated(hkUpdateObjectVM);
	EnableIfCreated(hkRotateObject);
	EnableIfCreated(hkEyeAngles);
	EnableIfCreated(hkGetViewModelFOV);
	EnableIfCreated(hkCreateViewModel);
	EnableIfCreated(hkGetAttachmentMatrix);
	EnableIfCreated(hkGetAttachmentAngles);
	EnableIfCreated(hkDrawModelExecute);
	EnableIfCreated(hkPlayerPortalled);
	EnableIfCreated(hkPlayerUse);
	EnableIfCreated(hkFindUseEntity);
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
	if (hasOffsets) {
		CreateHookAt(hkGetAttachmentMatrix, m_Game->m_Offsets->GetAttachmentMatrix.address,
			reinterpret_cast<LPVOID>(&dGetAttachmentMatrix), "Portal1::GetAttachment(matrix)", false);
		CreateHookAt(hkGetAttachmentAngles, m_Game->m_Offsets->GetAttachmentAngles.address,
			reinterpret_cast<LPVOID>(&dGetAttachmentAngles), "Portal1::GetAttachment(angles)", false);
	}
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
	CreateHookAt(hkPush2DView, SigScanner::GetVirtualFunction(engineRenderView, 39),
		reinterpret_cast<LPVOID>(&dPush2DView), "IVRenderView::Push2DView", true);
	CreateHookAt(hkPopView, SigScanner::GetVirtualFunction(engineRenderView, 40),
		reinterpret_cast<LPVOID>(&dPopView), "IVRenderView::PopView", true);
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
		CreateHookAt(hkPlayerUse, SigScanner::FindRttiVtableFunction("server.dll",
			".?AVCPortal_Player@@", Portal1::VTableIndex::kPortalPlayer_PlayerUse),
			reinterpret_cast<LPVOID>(&dPlayerUse), "Portal1::PlayerUse", false);
		CreateHookAt(hkFindUseEntity, SigScanner::FindRttiVtableFunction("server.dll",
			".?AVCPortal_Player@@", Portal1::VTableIndex::kPortalPlayer_FindUseEntity),
			reinterpret_cast<LPVOID>(&dFindUseEntity), "Portal1::FindUseEntity", false);
		PortalVrLog("Near-contact pickup hook target=%p", hkFindUseEntity.pTarget);
		const uintptr_t eyePositionTarget = FindPortalPlayerFunction(
			Portal1::VTableIndex::kPortalPlayer_EyePosition);
		const uintptr_t shootPositionTarget = FindPortalPlayerFunction(
			Portal1::VTableIndex::kPortalPlayer_WeaponShootPosition);
		const uintptr_t eyeAnglesTarget = FindPortalPlayerFunction(
			Portal1::VTableIndex::kPortalPlayer_EyeAngles);
		CreateHookAt(hkEyePosition,
			eyePositionTarget,
			reinterpret_cast<LPVOID>(&dEyePosition), "Portal1::EyePosition", false);
		CreateHookAt(hkWeapon_ShootPosition,
			shootPositionTarget ? shootPositionTarget : m_Game->m_Offsets->Weapon_ShootPosition.address,
			reinterpret_cast<LPVOID>(&dWeapon_ShootPosition), "Portal1::WeaponShootPosition", false);
		CreateHookAt(hkComputeError, m_Game->m_Offsets->ComputeError.address,
			reinterpret_cast<LPVOID>(&dComputeError), "Portal1::ComputeGrabError", false);
		CreateHookAt(hkUpdateObject, m_Game->m_Offsets->UpdateObject.address,
			reinterpret_cast<LPVOID>(&dUpdateObject), "Portal1::UpdateGrabObject", false);
		CreateHookAt(hkUpdateObjectVM, m_Game->m_Offsets->UpdateObjectVM.address,
			reinterpret_cast<LPVOID>(&dUpdateObjectVM), "Portal1::UpdateGrabObjectVM", false);
		CreateHookAt(hkRotateObject, m_Game->m_Offsets->RotateObject.address,
			reinterpret_cast<LPVOID>(&dRotateObject), "Portal1::RotateGrabObject", false);
		CreateHookAt(hkEyeAngles,
			eyeAnglesTarget ? eyeAnglesTarget : m_Game->m_Offsets->EyeAngles.address,
			reinterpret_cast<LPVOID>(&dEyeAngles), "Portal1::EyeAngles", false);
	}

	// The inherited FirePortal detour has Portal 2's ABI. Portal 1 aiming is
	// handled by the verified eight-argument TraceFirePortal hook above.

	CreatePingPointer = (hasOffsets ? reinterpret_cast<tCreatePingPointer>(m_Game->m_Offsets->CreatePingPointer.address) : nullptr);
	PrecacheParticleSystem = hasOffsets && m_Game->m_Offsets->PrecacheParticleSystem.valid ? (tPrecacheParticleSystem)m_Game->m_Offsets->PrecacheParticleSystem.address : nullptr;
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
		"initSourceHooks targets render=%p createMove=%p getViewModelFov=%p calcViewModel=%p traceFirePortal=%p eyePosition=%p shoot=%p computeError=%p update=%p eyeAngles=%p playerPortalled=%p crosshair=%p playerUse=%p",
		hkRenderView.pTarget,
		hkCreateMove.pTarget,
		hkGetViewModelFOV.pTarget,
		hkCalcViewModelView.pTarget,
		hkTraceFirePortal.pTarget,
		hkEyePosition.pTarget,
		hkWeapon_ShootPosition.pTarget,
		hkComputeError.pTarget,
		hkUpdateObject.pTarget,
		hkEyeAngles.pTarget,
		hkPlayerPortalled.pTarget,
		hkCHudCrosshair_ShouldDraw.pTarget,
		hkPlayerUse.pTarget);
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
    s_BodyViewStack.push_back(IsBodyWorldView(view, target, nullptr));
}

void __fastcall Hooks::dPush3DViewDepth(void *ecx, void *edx, const CViewSetup &view, int flags, ITexture *target, void *frustum, ITexture *depth)
{
    if (!target && m_ActiveEyeTexture) target = m_ActiveEyeTexture;
    hkPush3DViewDepth.fOriginal(ecx, view, flags, target, frustum, depth);
    s_BodyViewStack.push_back(IsBodyWorldView(view, target, depth));
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

	m_VR->m_SetupOrigin = position;
	m_VR->UpdateCameraCollision(position);

	Vector hmdAngle = m_VR->GetViewAngle();
	static int renderPoseLogCounter = 0;
	if ((++renderPoseLogCounter % 120) == 0)
	{
		PortalVrLog("Render view pose hmd=%f,%f,%f setup=%f,%f,%f",
			hmdAngle.x, hmdAngle.y, hmdAngle.z,
			setup.angles.x, setup.angles.y, setup.angles.z);
	}
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
	s_HasLocalPlayerBodyTransform = false;
	s_BodyDrawTriggered = false;
	s_InlineBodyDrawEligible = true;
	s_ActiveFirstPersonBodyPass = true;
		ExpectBodyView(leftEyeView);
		s_BodyCameraCenter = m_VR->GetViewOrigin(position);
		hkRenderView.fOriginal(ecx, leftEyeView, nClearFlags, whatToDraw & ~RENDERVIEW_DRAWHUD);
	s_ActiveFirstPersonBodyPass = false;
	s_InlineBodyDrawEligible = false;
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
	s_HasLocalPlayerBodyTransform = false;
	s_BodyDrawTriggered = false;
	s_InlineBodyDrawEligible = true;
	s_ActiveFirstPersonBodyPass = true;
		ExpectBodyView(rightEyeView);
		s_BodyCameraCenter = m_VR->GetViewOrigin(position);
		hkRenderView.fOriginal(ecx, rightEyeView, nClearFlags, whatToDraw & ~RENDERVIEW_DRAWHUD);
	s_ActiveFirstPersonBodyPass = false;
	s_InlineBodyDrawEligible = false;
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
		s_HasLocalPlayerBodyTransform = false;
		s_BodyDrawTriggered = false;
		s_InlineBodyDrawEligible = true;
		s_ActiveFirstPersonBodyPass = true;
		ExpectBodyView(desktopView);
		s_BodyCameraCenter = desktopView.origin;
		hkRenderView.fOriginal(ecx, desktopView, nClearFlags, whatToDraw);
		s_ActiveFirstPersonBodyPass = false;
		s_InlineBodyDrawEligible = false;
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
		// Keep IN_USE and the sampled hand on the same tick. PlayerUse and the
		// grab solver scope the hand override; portal physics must keep seeing
		// the real player eye pose. Command view angles remain HMD-driven.
		const bool useHeld = m_VR->PressedDigitalAction(m_VR->m_ActionUse);
		m_VR->SnapshotGrabPose();
		cmd->buttons = useHeld ? (cmd->buttons | IN_USE) : (cmd->buttons & ~IN_USE);
		cmd->viewangles = m_VR->m_HmdAngAbs;
		static bool lastUseHeld = false;
		if (useHeld != lastUseHeld) {
			PortalVrLog("Controller use state=%d origin=%f,%f,%f angle=%f,%f,%f cmdButtons=0x%X",
				useHeld, m_VR->m_GrabControllerPos.x, m_VR->m_GrabControllerPos.y,
				m_VR->m_GrabControllerPos.z, cmd->viewangles.x, cmd->viewangles.y,
				cmd->viewangles.z, cmd->buttons);
			lastUseHeld = useHeld;
		}

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

namespace {
    bool TrackedGunAttachment(void *renderable, int number, matrix3x4_t& output) {
        auto *vr = Hooks::m_VR;
        if (!vr || !vr->m_IsVREnabled || !vr->m_RightControllerPose.isValid
            || !renderable || renderable != s_RightViewmodelRenderable
            || renderable != s_GunAttachmentRenderable || number < 1
            || number > s_GunAttachments.count) return false;
        const auto getModel = SigScanner::GetVirtualFunction(renderable,Portal1::VTableIndex::kClientRenderable_GetModel);
        const auto setupBones = SigScanner::GetVirtualFunction(renderable,Portal1::VTableIndex::kClientRenderable_SetupBones);
        using GetModelFn = const void *(__thiscall *)(void *);
        using SetupBonesFn = bool (__thiscall *)(void *,matrix3x4_t *,int,int,float);
        if (!getModel || !setupBones
            || reinterpret_cast<GetModelFn>(getModel)(renderable) != s_GunAttachmentModel) return false;
        // The original successful attachment query just computed these native
        // bones. Copy them; never write transformed matrices into Source's cache.
        static thread_local bool resolving = false;
        if (resolving) return false;
        struct Guard { bool& value; Guard(bool& v):value(v) { value=true; } ~Guard() { value=false; } } guard(resolving);
        matrix3x4_t nativeBones[128];
        constexpr int usedByAttachment = 0x200;
        if (!reinterpret_cast<SetupBonesFn>(setupBones)(renderable,nativeBones,128,usedByAttachment,0.0f)) return false;
        const auto controller = HandPose::Frame(-vr->m_RightControllerRight,
            vr->m_RightControllerUp,vr->m_RightControllerForward,vr->GetRightHandAbsPos());
        if (!s_GunAttachments.Resolve(number,controller,nativeBones,output)) return false;
        static int logged = 0;
        if (number == 1 && logged++ < 12)
            PortalVrLog("VR muzzle attachment aligned origin=%f,%f,%f",output[0][3],output[1][3],output[2][3]);
        return true;
    }
}

bool __fastcall Hooks::dGetAttachmentMatrix(void *ecx, void *edx, int number, matrix3x4_t& matrix) {
    const bool result = hkGetAttachmentMatrix.fOriginal(ecx,number,matrix);
    if (result) TrackedGunAttachment(ecx,number,matrix);
    return result;
}

bool __fastcall Hooks::dGetAttachmentAngles(void *ecx, void *edx, int number, Vector& origin, QAngle& angles) {
    const bool result = hkGetAttachmentAngles.fOriginal(ecx,number,origin,angles);
    matrix3x4_t matrix;
    if (result && TrackedGunAttachment(ecx,number,matrix)) {
        origin = PortalPose::Position(matrix);
        angles = PortalPose::Angles(HandPose::RigidOrientation(matrix));
    }
    return result;
}

void __fastcall Hooks::dCalcViewModelView(void *ecx, void *edx, const Vector &eyePosition, const QAngle &eyeAngles)
{
	s_LeftArmRenderable = nullptr;
	s_RightViewmodelRenderable = nullptr;
	if (m_VR->m_IsVREnabled && m_Game->m_Offsets->GetViewModel.valid) {
		using GetViewModelFn = void *(__thiscall *)(void *, int, bool);
		for (int index = 0; index < 2; ++index) {
			void *vm = reinterpret_cast<GetViewModelFn>(m_Game->m_Offsets->GetViewModel.address)(ecx, index, false);
			if (vm) {
				if (index == 0) s_RightViewmodelRenderable = static_cast<unsigned char *>(vm) + 4;
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
					const auto getModel = SigScanner::GetVirtualFunction(
						renderable, Portal1::VTableIndex::kClientRenderable_GetModel);
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

	if (pPlayer)
	{
		int index = ServerEntityIndex(pPlayer);
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

void Hooks::dDrawModelExecute(void *ecx, void *edx, void *state, const ModelRenderInfo_t &info, void *pCustomBoneToWorld)
{
	// Work on a copy: Source shares its cached matrices with attachments and
	// other eyes. Rewriting that cache would accumulate the controller transform.
    const auto *bones = static_cast<const matrix3x4_t *>(pCustomBoneToWorld);
	const bool localPlayerBody = IsLocalPlayerBody(info);
	if (localPlayerBody && !s_DrawingLocalPlayerBodyDirect)
	{
		s_LocalPlayerBodyOrigin = info.origin;
		s_LocalPlayerBodyAngles = info.angles;
		s_HasLocalPlayerBodyTransform = true;
	}


	if (localPlayerBody && s_DrawingLocalPlayerBodyDirect)
	{
		static int directDrawExecuteLogCounter = 0;
		if (directDrawExecuteLogCounter++ < 16)
		{
			IModelInfo *modelInfo = m_Game ? m_Game->GetModelInfo() : nullptr;
			const char *modelName = modelInfo && info.pModel
				? modelInfo->GetModelName(info.pModel) : nullptr;
			PortalVrLog("First-person direct DrawModelExecute eye=%p model=%s customBones=%p",
				m_ActiveEyeTexture, modelName ? modelName : "<unknown>",
				pCustomBoneToWorld);
		}
	}

	if (localPlayerBody && m_VR->m_FirstPersonBodyHideUpper)
	{
		matrix3x4_t bodyBones[FirstPersonBody::MaxBones];
		const bool built = BuildFirstPersonBodyBones(state, bones, bodyBones, info);
		static int diagnosticBodyDraws = 0;
		if (diagnosticBodyDraws++ < 8)
		{
			IModelInfo *modelInfo = m_Game ? m_Game->GetModelInfo() : nullptr;
			const char *modelName = modelInfo && info.pModel
				? modelInfo->GetModelName(info.pModel) : nullptr;
			PortalVrLog("First-person body candidate eye=%p model=%s entity=%d renderable=%p origin=%f,%f,%f built=%d",
				m_ActiveEyeTexture, modelName ? modelName : "<unknown>",
				info.entity_index, info.pRenderable,
				info.origin.x, info.origin.y, info.origin.z, built);
		}
		if (built)
			return hkDrawModelExecute.fOriginal(ecx, state, info, bodyBones);
	}

	if (localPlayerBody && s_DrawingLocalPlayerBodyDirect)
	{
		matrix3x4_t bodyBones[FirstPersonBody::MaxBones];
		if (TranslateFirstPersonBodyBones(state, bones, bodyBones))
			return hkDrawModelExecute.fOriginal(ecx, state, info, bodyBones);
	}

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
                const auto rightTarget = HandPose::ControllerHandFrame(
                    m_VR->m_RightHandForward, m_VR->m_RightControllerRight,
                    m_VR->m_RightHandUp, rightPosition, false);
                if (gun) {
                    // The gun's local +Z is its barrel, +Y is up. Align its
                    // grip with the controller and retain animated gun parts.
                    matrix3x4_t source = reference[24];
                    for (int row = 0; row < 3; ++row) source[row][3] = reference[8][row][3];
                    const auto target = HandPose::Frame(-m_VR->m_RightControllerRight,
                        m_VR->m_RightControllerUp, m_VR->m_RightControllerForward, rightPosition);
                    // The gun model now contains an anatomical wrist frame
                    // fitted to Portal's authored grip, independently of bare hands.
                    for (int i = 0; i < 24; ++i) tracked[i] = HandPose::Reanchor(reference[i], source, target);
                    const auto fittedGun = HandPose::FitGunToPalm(reference[24]);
                    const auto gunTarget = HandPose::Reanchor(fittedGun, source, target);
                    if (info.pRenderable == s_RightViewmodelRenderable) {
                        s_GunAttachmentRenderable = nullptr;
                        m_VR->m_PortalAimLastSeen = 0;
                        if (modelLength >= 248 && modelLength <= 64 * 1024 * 1024
                            && SigScanner::IsReadable(reinterpret_cast<uintptr_t>(hdr), modelLength)
                            && s_GunAttachments.Read(hdr,modelLength,reference)) {
                            s_GunAttachmentRenderable = info.pRenderable;
                            s_GunAttachmentModel = info.pModel;
                            if (s_GunAttachments.hasBarrel) {
                                m_VR->m_PortalAimFromController = s_GunAttachments.barrelFromController;
                                m_VR->m_PortalAimLastSeen = GetTickCount64();
                            } else m_VR->m_PortalAimLastSeen = 0;
                        }
                    }
                    for (int i = 24; i < count; ++i) tracked[i] = HandPose::Reanchor(bones[i], bones[24], gunTarget);
                    HandPose::ApplyGunGrip(reference, tracked, m_VR->m_RightFingerCurl);
                    matrix3x4_t socket;
                    if (modelLength >= 248 && modelLength <= 64 * 1024 * 1024
                        && SigScanner::IsReadable(reinterpret_cast<uintptr_t>(hdr), modelLength)
                        && OptionalGunGrip::ReadSocket(hdr, modelLength, socket)) {
                        // Keep the socket relative to the gun controller, so
                        // either eye and either draw order use today's tracking.
                        m_VR->m_SupportFromController = HandPose::Concat(HandPose::InverseRigid(source),
                            HandPose::Concat(fittedGun, socket));
                        m_VR->m_SupportLastSeen = GetTickCount64();
                    } else {
                        m_VR->m_SupportLastSeen = 0;
                        m_VR->m_OptionalGripState.active = false;
                        m_VR->m_OptionalSupportActive = false;
                    }
                } else {
                    auto leftTarget = HandPose::ControllerHandFrame(
                        m_VR->m_LeftHandForward, m_VR->m_LeftControllerRight,
                        m_VR->m_LeftHandUp, m_VR->GetLeftHandAbsPos(), true);
                    const bool supporting = s_LeftArmRenderable && m_VR->UpdateOptionalGunSupport(&leftTarget);
                    HandPose::AlignBareArms(reference, tracked, leftTarget, rightTarget);
                    static const float supportCurl[5] = {0.30f, 0.40f, 0.45f, 0.45f, 0.45f};
                    HandPose::ApplyFingerCurl(reference, tracked,
                        supporting ? supportCurl : m_VR->m_LeftFingerCurl, m_VR->m_RightFingerCurl);
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

Vector* Hooks::dWeapon_ShootPosition(void* ecx, void* edx, Vector* shootPos)
{
	Vector* result = hkWeapon_ShootPosition.fOriginal(ecx, shootPos);

	if (!result || !m_Game || !m_VR)
		return result;

	const int localIndex = m_Game->GetLocalPlayerIndex();
	const int index = ServerEntityIndex(ecx);
	if (index < 0 || index >= static_cast<int>(m_Game->m_PlayersVRInfo.size()))
		return result;

	const auto &vrPlayer = m_Game->m_PlayersVRInfo[index];

	if (m_VR->m_IsVREnabled && localIndex > 0 && localIndex == index
		&& m_VR->m_RightControllerPose.isValid) {
		Vector hand;
		QAngle angles;
		if (ServerHandPose(ecx, hand, angles)) *result = hand;
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
    Vector aimStart, aimDirection;
    if (placedBy == 2 && m_VR->GetPortalAimRay(aimStart,aimDirection)) {
        shotStart = aimStart;
        shotDirection = aimDirection;
        static int logged = 0;
        if (!test && logged++ < 20)
            PortalVrLog("Controller portal shot secondary=%d hand=%f,%f,%f direction=%f,%f,%f headDirection=%f,%f,%f",
                secondary,shotStart.x,shotStart.y,shotStart.z,
                shotDirection.x,shotDirection.y,shotDirection.z,direction.x,direction.y,direction.z);
    }
    return hkTraceFirePortal.fOriginal(ecx, secondary, shotStart, shotDirection, trace,
        finalPosition, finalAngles, placedBy, test);
}

void __fastcall Hooks::dPlayerPortalled(void* ecx, void* edx, void* portal)
{
	// The verified Portal 1 function copies the portal's VMatrix at +0x864.
	// Copy before calling the original; only the local player owns our tracking.
	matrix3x4_t transform;
	const auto matrixAddress = reinterpret_cast<uintptr_t>(portal) + 0x864;
	const bool apply = portal && m_VR && m_Game && m_VR->m_IsVREnabled
		&& ecx == m_Game->GetLocalPortalPlayer()
		&& SigScanner::IsReadable(matrixAddress, sizeof(transform));
	if (apply) memcpy(&transform, reinterpret_cast<const void *>(matrixAddress), sizeof(transform));
	hkPlayerPortalled.fOriginal(ecx, portal);
	if (!apply) return;

	const float yaw = PortalPose::UprightYawDelta(transform, m_VR->m_HmdAngAbs);
	m_VR->m_RotationOffset.y = std::remainder(m_VR->m_RotationOffset.y + yaw, 360.0f);
	m_VR->m_SetupOrigin = PortalPose::Position(HandPose::Concat(transform,
		PortalPose::Frame(m_VR->m_SetupOrigin, {0,0,0})));
	m_VR->m_CameraCollisionOffset = {0,0,0};
	m_VR->m_CameraBlocked = false;
	// Update both hands and the roomscale offset in this callback, before a
	// render or pickup update can consume an entry-side pose. No distance gate.
	m_VR->UpdateTracking();
	m_VR->SnapshotGrabPose();
	PortalVrLog("Player portalled: tracking yaw delta=%f origin=%f,%f,%f", yaw,
		m_VR->m_SetupOrigin.x, m_VR->m_SetupOrigin.y, m_VR->m_SetupOrigin.z);
}

void __fastcall Hooks::dPlayerUse(void* ecx, void* edx)
{
	const bool previous = m_VR->m_OverrideEyeAngles;
	m_VR->m_OverrideEyeAngles = true;
	hkPlayerUse.fOriginal(ecx);
	m_VR->m_OverrideEyeAngles = previous;
}

void* __fastcall Hooks::dFindUseEntity(void* ecx, void* edx)
{
	void* entity = hkFindUseEntity.fOriginal(ecx);
	if (entity || !m_Game || !m_VR || !m_VR->m_IsVREnabled
		|| !m_VR->m_OverrideEyeAngles || !m_VR->m_RightControllerPose.isValid
		|| m_Game->GetLocalPlayerIndex() <= 0
		|| ServerEntityIndex(ecx) != m_Game->GetLocalPlayerIndex()) return entity;

	Vector hand, eye;
	QAngle handAngles;
	if (!ServerHandPose(ecx, hand, handAngles)) return nullptr;
	const Vector* actualEye = hkEyePosition.fOriginal(ecx, &eye);
	auto* traceEngine = m_Game->GetServerEngineTrace();
	if (!actualEye || !traceEngine) return nullptr;
	eye = *actualEye;
	Ray_t sweep;
	sweep.Init(eye, hand, {-2,-2,-2}, {2,2,2});
	CGameTrace trace;
	CTraceFilterSkipEntity filter(reinterpret_cast<IHandleEntity*>(ecx), 0);
	// Same contents as Portal 1 FindUseEntity, with server entities throughout.
	traceEngine->TraceRay(sweep, 0x0601400b, &filter, &trace);
	PickupQueryPose query{ecx};
	if (!trace.m_pEnt || ServerEntityIndex(trace.m_pEnt) <= 0
		|| !PickupTrace::ContactQuery(eye, hand, trace.fraction,
			trace.startsolid, trace.allsolid, query.origin, query.angles)) return nullptr;

	// Only the second selection query sees this temporary origin. Attachment,
	// held-object physics and portal traversal keep using the real controller.
	{
		ScopedPickupQuery scope(query);
		entity = hkFindUseEntity.fOriginal(ecx);
	}
	const bool matched = entity == trace.m_pEnt;
	static unsigned int reports = 0;
	if (reports++ < 32)
		PortalVrLog("Near-contact pickup entity=%p matched=%d handDistance=%f",
			trace.m_pEnt, matched, sqrtf((hand-trace.endpos).LengthSqr()));
	return matched ? entity : nullptr;
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

void __fastcall Hooks::dPush2DView(void* ecx, void* edx, const CViewSetup& view, int nFlags, ITexture* pRenderTarget, void* frustumPlanes) {
	hkPush2DView.fOriginal(ecx, view, nFlags, pRenderTarget, frustumPlanes);
	s_BodyViewStack.push_back(false);
}

void __fastcall Hooks::dPopView(void* ecx, void* edx, void* frustumPlanes) {
	if (!s_BodyViewStack.empty()) {
		const bool mainWorldView = s_BodyViewStack.back();
		if (mainWorldView && s_InlineBodyDrawEligible && !s_BodyDrawTriggered) {
			s_BodyDrawTriggered = true;
			s_ActiveFirstPersonBodyPass = true;
			DrawLocalPlayerBodyDirect();
			s_ActiveFirstPersonBodyPass = false;
		}
		s_BodyViewStack.pop_back();
	}
	hkPopView.fOriginal(ecx, frustumPlanes);
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

Vector* __fastcall Hooks::dEyePosition(void* ecx, void* edx, Vector* eyePos)
{
	Vector* result = hkEyePosition.fOriginal(ecx, eyePos);

	if (!result || !m_Game || !m_VR)
		return result;
	if (s_PickupQuery && s_PickupQuery->player == ecx) {
		*result = s_PickupQuery->origin;
		return result;
	}

	const int localIndex = m_Game->GetLocalPlayerIndex();
	const int index = ServerEntityIndex(ecx);
	const bool isLocalPlayer = localIndex > 0 && localIndex == index;
	if (m_VR->m_IsVREnabled && isLocalPlayer
		&& m_VR->m_RightControllerPose.isValid
		&& m_VR->m_OverrideEyeAngles)
	{
		Vector hand;
		QAngle angles;
		if (ServerHandPose(ecx, hand, angles)) *result = hand;
		static bool logged = false;
		if (!logged)
		{
			PortalVrLog("Scoped controller EyePosition override origin=%f,%f,%f",
				result->x, result->y, result->z);
			logged = true;
		}
	}

	return result;
}

float __fastcall Hooks::dComputeError(void* ecx, void* edx) {
	const bool wasTrue = m_VR->m_OverrideEyeAngles;
	m_VR->m_OverrideEyeAngles = true;
	const float value = hkComputeError.fOriginal(ecx);
	m_VR->m_OverrideEyeAngles = wasTrue;
	return value;
}

bool __fastcall Hooks::dUpdateObject(void* ecx, void* edx, void* pPlayer, float flError) {
	const bool wasTrue = m_VR->m_OverrideEyeAngles;

	m_VR->m_OverrideEyeAngles = true;

	const bool value = hkUpdateObject.fOriginal(ecx, pPlayer, flError);

	m_VR->m_OverrideEyeAngles = wasTrue;

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
	if (s_PickupQuery && s_PickupQuery->player == ecx) return s_PickupQuery->angles;
	if (m_VR && m_Game) {
		const int localIndex = m_Game->GetLocalPlayerIndex();
		const int index = ServerEntityIndex(ecx);
		if (index >= 0 && index < static_cast<int>(m_Game->m_PlayersVRInfo.size()))
		{
			auto &vrPlayer = m_Game->m_PlayersVRInfo[index];
			if (m_VR->m_OverrideEyeAngles
				&& m_VR->m_IsVREnabled && localIndex > 0 && localIndex == index
				&& m_VR->m_RightControllerPose.isValid)
			{
				static bool logged = false;
				if (!logged)
				{
					const QAngle &controller = m_VR->m_GrabControllerAng;
					PortalVrLog("Controller EyeAngles override angle=%f,%f,%f",
						controller.x, controller.y, controller.z);
					logged = true;
				}
				Vector hand;
				if (ServerHandPose(ecx, hand, m_VR->m_ServerGrabAngles))
					return m_VR->m_ServerGrabAngles;
				return hkEyeAngles.fOriginal(ecx);
			}
			if (m_VR->m_OverrideEyeAngles && vrPlayer.isUsingVR)
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
