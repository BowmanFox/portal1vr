#include <Windows.h>
#include <cassert>
#include <cstring>
#include "sdk/sdk.h"
#include "sdk/trace.h"
#include "sigscanner.h"
#include "handpose.h"
#include "cameracollision.h"
#include <limits>

static void CheckCameraCollision() {
    static_assert(sizeof(Ray_t) == 80);
    static_assert(offsetof(Ray_t, m_IsRay) == 64);
    static_assert(offsetof(Ray_t, m_IsSwept) == 65);
    static_assert(sizeof(CGameTrace) == 84);
    static_assert(offsetof(CGameTrace, fraction) == 44);
    static_assert(offsetof(CGameTrace, startsolid) == 55);
    Ray_t hull;
    memset(&hull, 0xcc, sizeof(hull));
    hull.Init({0,0,0},{20,0,0},{-3,-3,-3},{3,3,3});
    // Read the exact bytes consumed by Portal's engine.dll, not just our fields.
    const auto* engineRayBytes = reinterpret_cast<const unsigned char*>(&hull);
    assert(engineRayBytes[64] == 0 && engineRayBytes[65] == 1);
    assert(hull.m_Extents.x == 3 && hull.m_StartOffset.LengthSqr() == 0);
    hull.Init({0,0,0},{20,0,0});
    assert(engineRayBytes[64] == 1 && engineRayBytes[65] == 1);
    hull.Init({0,0,0},{0,0,0},{-3,-3,-3},{3,3,3});
    assert(engineRayBytes[64] == 0 && engineRayBytes[65] == 0);

    const Vector start(0,0,0), desired(20,0,0);
    const float radius = CameraCollision::HullRadius(2.8f,104.0f,1.0f);
    assert(radius > 3.0f && radius < 5.0f);
    // A solid wall at x=10 must stop both eyes and all near-plane corners.
    const float hitFraction = (10.0f-radius)/20.0f;
    const auto safe = CameraCollision::Constrain(start,desired,hitFraction,false,false);
    assert(safe.x > 0 && safe.x + radius < 10.0f && safe.y == 0 && safe.z == 0);
    const auto repeated = CameraCollision::Constrain(start,desired,hitFraction,false,false);
    assert((safe-repeated).LengthSqr() == 0);
    // Leaning back and engine teleports must recover immediately without drift.
    assert((CameraCollision::Constrain(start,{2,0,0},1,false,false)-Vector(2,0,0)).LengthSqr() == 0);
    assert((CameraCollision::Constrain({100,0,0},{105,0,0},1,false,false)-Vector(105,0,0)).LengthSqr() == 0);
    assert(CameraCollision::Constrain(start,desired,0.5f,true,false).LengthSqr() == 0);
    assert(CameraCollision::Constrain(start,desired,0.5f,false,true).LengthSqr() == 0);
    assert(CameraCollision::Constrain(start,desired,std::numeric_limits<float>::quiet_NaN(),false,false).LengthSqr() == 0);
    assert(CameraCollision::Constrain(start,start,0,false,false).LengthSqr() == 0);
    const auto floor = CameraCollision::Constrain(start,{0,0,-20},0.25f,false,false);
    assert(floor.z > -5.0f && floor.z < 0.0f);
    // Wider IPD and near-plane corners require a correspondingly larger hull.
    assert(CameraCollision::HullRadius(6.0f,104.0f,1.0f) > radius + 1.5f);
}

static void CheckHandAttachment() {
    assert(HandPose::Identify("weapons/V_hands.mdl",43) == HandPose::Model::Hands);
    assert(HandPose::Identify("weapons/v_hands.mdl",43) == HandPose::Model::Hands);
    assert(HandPose::Identify("weapons/v_hands.mdl",45) == HandPose::Model::Other);
    // A wrist at (10,20,30), with a barrel 23 units ahead. Move and rotate
    // it 90 degrees; the attachment must land on the new hand and retain length.
    const auto source = HandPose::Frame({1,0,0},{0,1,0},{0,0,1},{10,20,30});
    const auto target = HandPose::Frame({0,1,0},{-1,0,0},{0,0,1},{-5,7,9});
    auto muzzle = source;
    muzzle[0][3] += 23;
    const auto inverse = HandPose::InverseRigid(target);
    const auto doubleInverse = HandPose::InverseRigid(inverse);
    for (int r=0;r<3;++r) for (int c=0;c<4;++c) assert(fabs(doubleInverse[r][c]-target[r][c])<0.0001f);
    const auto wrist = HandPose::Reanchor(source, source, target);
    const auto moved = HandPose::Reanchor(muzzle, source, target);
    for (int r=0;r<3;++r) for (int c=0;c<4;++c) assert(fabs(wrist[r][c]-target[r][c])<0.0001f);
    assert(fabs(moved[0][3]+5)<0.0001f && fabs(moved[1][3]-30)<0.0001f && fabs(moved[2][3]-9)<0.0001f);
    // Repeated stereo passes must read the unchanged source, not compound motion.
    const auto secondEye = HandPose::Reanchor(muzzle, source, target);
    assert(!memcmp(&moved, &secondEye, sizeof(moved)));
    const auto restored = HandPose::Reanchor(moved, target, source);
    for (int r=0;r<3;++r) for (int c=0;c<4;++c) assert(fabs(restored[r][c]-muzzle[r][c])<0.0001f);

    matrix3x4_t original[43], first[43]{}, rightMoved[43]{}, leftMoved[43]{};
    for (int i=0;i<43;++i) original[i] = HandPose::Frame({1,0,0},{0,1,0},{0,0,1},{float(i),0,0});
    HandPose::AlignBareArms(original, first, source, source);
    HandPose::AlignBareArms(original, rightMoved, source, target);
    HandPose::AlignBareArms(original, leftMoved, target, source);
    // Moving either controller cannot move the other arm, including its fingers.
    for (int i=5;i<24;++i) assert(!memcmp(&first[i],&rightMoved[i],sizeof(matrix3x4_t)));
    for (int i=24;i<43;++i) assert(!memcmp(&first[i],&leftMoved[i],sizeof(matrix3x4_t)));
    assert(!memcmp(&rightMoved[27],&target,sizeof(target)));
    assert(!memcmp(&leftMoved[8],&target,sizeof(target)));

    // Controller hand frames keep the Source left-handed controller basis
    // rigid while mirroring the lateral axis.  This prevents edge-on palms
    // and keeps each hand's fingers aligned with its own controller.
    const auto rightFrame = HandPose::ControllerHandFrame(
        {1,0,0}, {0,-1,0}, {0,0,1}, {2,3,4}, false);
    const auto leftFrame = HandPose::ControllerHandFrame(
        {1,0,0}, {0,-1,0}, {0,0,1}, {5,6,7}, true);
    assert(rightFrame[0][0] == 1 && rightFrame[1][1] == -1 && rightFrame[2][2] == -1);
    assert(leftFrame[0][0] == 1 && leftFrame[1][1] == 1 && leftFrame[2][2] == 1);
    assert(rightFrame[0][3] == 2 && leftFrame[1][3] == 6);

    // Custom VPK fingers extend along +X and hinge around local +Y, so curl
    // must rotate in the local X/Z plane toward the palm.
    const auto curlFrame = HandPose::FingerBend(0.5f);
    assert(fabs(curlFrame[0][1]) < 0.0001f && fabs(curlFrame[2][1]) < 0.0001f);
    assert(fabs(curlFrame[1][1] - 1.0f) < 0.0001f);
    assert(fabs(curlFrame[0][2]) > 0.1f && fabs(curlFrame[2][0]) > 0.1f);

    matrix3x4_t gun[45];
    for (auto &bone:gun) bone = source;
    gun[8] = HandPose::Frame({1,0,0},{0,1,0},{0,0,1},{1,10,3});
    gun[7] = HandPose::Frame({0,1,0},{-1,0,0},{0,0,1},{1,-1.48f,3});
    const auto heldHand = gun[8], heldGun = gun[24];
    HandPose::StraightenGunWrist(gun);
    assert(!memcmp(&heldHand,&gun[8],sizeof(heldHand)));
    assert(!memcmp(&heldGun,&gun[24],sizeof(heldGun)));
    for (int r=0;r<3;++r) {
        assert(fabs(gun[7][r][0]-gun[8][r][0])<0.0001f);
        assert(fabs(gun[7][r][3]+11.48f*gun[7][r][0]-gun[8][r][3])<0.0001f);
    }
}

static void *expectedThis;
static bool __fastcall InGame(void *self, void *) { assert(self == expectedThis); return true; }
static void __fastcall GetAngles(void *self, void *, QAngle &out) { assert(self == expectedThis); out = {1,2,3}; }
static void __fastcall Command(void *self, void *, const char *text) { assert(self == expectedThis); assert(!strcmp(text,"test")); }
static void __fastcall Screen(void *self, void *, int &w, int &h) { assert(self == expectedThis); w=1280; h=720; }
static void __fastcall PushTarget(void *self, void *, ITexture *target, int x, int y, int w, int h) {
    assert(self == expectedThis && target == reinterpret_cast<ITexture *>(0x1234));
    assert(x == 0 && y == 0 && w == 2352 && h == 2352);
}
static void __fastcall PopTarget(void *self, void *) { assert(self == expectedThis); }
int main() {
    CheckHandAttachment();
    CheckCameraCollision();
    static_assert(sizeof(void *) == 4);
    static_assert(sizeof(CViewSetup) == 0xc8);
    static_assert(offsetof(CViewSetup, fov) == 0x38);
    static_assert(offsetof(CViewSetup, origin) == 0x40);
    static_assert(offsetof(CViewSetup, m_flAspectRatio) == 0x6c);
    void *table[194]{};
    void **object = table;
    expectedThis = &object;
    table[19] = reinterpret_cast<void *>(&GetAngles);
    table[26] = reinterpret_cast<void *>(&InGame);
    table[106] = reinterpret_cast<void *>(&Command);
    auto engine = reinterpret_cast<IEngineClient *>(&object);
    QAngle angle;
    assert(engine->IsInGame()); engine->GetViewAngles(angle);
    assert(angle.x == 1 && angle.y == 2 && angle.z == 3);
    engine->ClientCmd_Unrestricted("test");
    table[38] = reinterpret_cast<void *>(&Screen);
    table[53] = reinterpret_cast<void *>(&InGame);
    auto surface = reinterpret_cast<ISurface *>(&object);
    int w=0,h=0; surface->GetScreenSize(w,h);
    assert(w==1280 && h==720 && surface->IsCursorVisible());
    table[106] = reinterpret_cast<void *>(&PushTarget);
    table[109] = reinterpret_cast<void *>(&PopTarget);
    auto context = reinterpret_cast<IMatRenderContext *>(&object);
    context->PushRenderTargetAndViewport(reinterpret_cast<ITexture *>(0x1234),0,0,2352,2352);
    context->PopRenderTargetAndViewport();
    CTraceFilterSkipEntity filter(reinterpret_cast<IHandleEntity *>(0x1234),0);
    assert(!filter.ShouldHitEntity(reinterpret_cast<IHandleEntity *>(0x1234),0));
    assert(filter.ShouldHitEntity(reinterpret_cast<IHandleEntity *>(0x5678),0));
    assert(!SigScanner::GetVirtualFunction(nullptr, 0));
    void *guard = VirtualAlloc(nullptr,4096,MEM_COMMIT|MEM_RESERVE,PAGE_NOACCESS);
    assert(guard && !SigScanner::GetVirtualFunction(guard,0));
    VirtualFree(guard,0,MEM_RELEASE);
    puts("Portal ABI, trace, hand attachment, and camera collision regression checks passed");
}
