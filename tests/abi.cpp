#include <Windows.h>
#include <cassert>
#include <cstring>
#include "sdk/sdk.h"
#include "sdk/trace.h"
#include "sigscanner.h"
#include "handpose.h"
#include "firstpersonbody.h"
#include "cameracollision.h"
#include "portalpose.h"
#include "pickuptrace.h"
#include "optionalgungrip.h"
#include "portaltrace.h"
#include "gunattachments.h"
#include <limits>

static void CheckGunAttachments() {
    unsigned char mdl[248+92]{};
    auto put=[&](int offset,int value){std::memcpy(mdl+offset,&value,4);};
    put(4,48); put(156,45); put(240,1); put(244,248); put(256,25);
    std::memcpy(mdl+12,"weapons/v_portalgun.mdl",sizeof("weapons/v_portalgun.mdl"));
    const auto local=PortalPose::Frame({0,2.2f,2.8f},{0,0,0});
    std::memcpy(mdl+260,&local,sizeof(local));
    matrix3x4_t bind[45], native[45];
    for(auto& b:bind)b=PortalPose::Frame({0,0,0},{0,0,0});
    bind[8]=PortalPose::Frame({-8,-16,-14},{20,35,10});
    bind[24]=PortalPose::Frame({-7,-15,-17},{40,15,-10});
    bind[25]=HandPose::Concat(bind[24],PortalPose::Frame({0,0,20},{0,0,0}));
    GunAttachments::Model model;
    assert(model.Read(mdl,sizeof(mdl),bind));
    auto source=bind[24];for(int r=0;r<3;++r)source[r][3]=bind[8][r][3];
    for (const QAngle& angle: {QAngle{0,0,0},QAngle{60,135,20},QAngle{-75,-120,-65},QAngle{89,45,90}}) {
        const auto engine=PortalPose::Frame({100,40,-20},{5,-10,0});
        for(int i=0;i<45;++i)native[i]=HandPose::Concat(engine,bind[i]);
        native[25]=HandPose::Concat(native[25],PortalPose::Frame({0,0,-1},{2,0,0}));
        const auto controller=PortalPose::Frame({-20,30,60},angle);
        const auto renderedGun=HandPose::Reanchor(HandPose::FitGunToPalm(bind[24]),source,controller);
        const auto renderedBone=HandPose::Reanchor(native[25],native[24],renderedGun);
        const auto expected=HandPose::Concat(renderedBone,local);
        const auto before=native[25];matrix3x4_t first,second;
        assert(model.Resolve(1,controller,native,first));
        assert(model.Resolve(1,controller,native,second));
        for(int r=0;r<3;++r)for(int c=0;c<4;++c)assert(fabs(first[r][c]-expected[r][c])<.0001f);
        assert(!std::memcmp(&first,&second,sizeof(first)));
        assert(!std::memcmp(&before,&native[25],sizeof(before)));
        assert((PortalPose::Position(first)-PortalPose::Position(HandPose::Concat(native[25],local))).LengthSqr()>100);
        assert(!model.Resolve(0,controller,native,second));
        assert(!model.Resolve(2,controller,native,second));
    }
    assert(!model.Read(mdl,sizeof(mdl)-1,bind));
    put(256,45);assert(!model.Read(mdl,sizeof(mdl),bind));
    put(256,25);put(244,2147483647);assert(!model.Read(mdl,sizeof(mdl),bind));
    put(244,248);mdl[12]='X';assert(!model.Read(mdl,sizeof(mdl),bind));
}

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

    // Controller hand frames preserve the custom V_hands wrist frame while
    // mirroring the lateral axis for the opposite hand.
    const auto rightFrame = HandPose::ControllerHandFrame(
        {1,0,0}, {0,-1,0}, {0,0,1}, {2,3,4}, false);
    const auto leftFrame = HandPose::ControllerHandFrame(
        {1,0,0}, {0,-1,0}, {0,0,1}, {5,6,7}, true);
    assert(rightFrame[0][0] == 1 && rightFrame[1][1] == 1 && rightFrame[2][2] == 1);
    assert(leftFrame[0][0] == 1 && leftFrame[1][1] == -1 && leftFrame[2][2] == -1);
    assert(rightFrame[0][3] == 2 && leftFrame[1][3] == 6);
    assert(!FirstPersonBody::LookingDown(0));
    assert(!FirstPersonBody::LookingDown(-45));
    assert(!FirstPersonBody::LookingDown(29));
    assert(FirstPersonBody::LookingDown(45));
    assert(FirstPersonBody::LookingDown(90));

    // Custom VPK fingers extend along +X and hinge around local +Y, so curl
    // must rotate in the local X/Z plane toward the palm.
    const auto curlFrame = HandPose::FingerBend(0.5f);
    assert(fabs(curlFrame[0][1]) < 0.0001f && fabs(curlFrame[2][1]) < 0.0001f);
    assert(fabs(curlFrame[1][1] - 1.0f) < 0.0001f);
    assert(curlFrame[0][2] > 0.1f && curlFrame[2][0] < -0.1f);

    // The arbitrary-axis path must preserve its hinge axis.  This catches a
    // column/row transpose that would make a valid thumb axis bend sideways.
    const auto zHinge = HandPose::RotateAroundAxis({0,0,3}, 0.5f);
    assert(fabs(zHinge[0][2]) < 0.0001f && fabs(zHinge[1][2]) < 0.0001f);
    assert(fabs(zHinge[2][2] - 1.0f) < 0.0001f);
    assert(fabs(zHinge[0][0]) > 0.1f && fabs(zHinge[1][0]) > 0.1f);

    // Anatomical joints keep their base and lengths, regardless of bone roll.
    matrix3x4_t bind[43], posed[43];
    for (auto &bone : bind)
        bone = HandPose::Frame({1,0,0}, {0,1,0}, {0,0,1}, {0,0,0});
    for (int side=0;side<2;++side) {
        const int offset=side*19;
        for(int root : {9,12,15,18,21}) {
            for(int joint=0;joint<3;++joint) {
                bind[root+joint+offset]=HandPose::RotateAroundAxis({1,0,0},0.8f);
                bind[root+joint+offset][0][3]=float(2+joint);
                bind[root+joint+offset][1][3]=float(root-15)*0.3f;
            }
        }
    }
    memcpy(posed,bind,sizeof(bind));
    const float open[5]={0,0,0,0,0},closed[5]={1,1,1,1,1};
    HandPose::ApplyFingerCurl(bind,posed,open,open);
    for(int i=0;i<43;++i)for(int r=0;r<3;++r)for(int c=0;c<4;++c)
        assert(fabs(posed[i][r][c]-bind[i][r][c])<0.00001f);
    HandPose::ApplyFingerCurl(bind,posed,closed,closed);
    for(int side=0;side<2;++side)for(int root : {9,12,15,18,21}) {
        const int offset=side*19;
        for(int r=0;r<3;++r)assert(fabs(posed[root+offset][r][3]-bind[root+offset][r][3])<0.0001f);
        for(int j=1;j<3;++j) {
            Vector distance(posed[root+j+offset][0][3]-posed[root+j-1+offset][0][3],
                posed[root+j+offset][1][3]-posed[root+j-1+offset][1][3],
                posed[root+j+offset][2][3]-posed[root+j-1+offset][2][3]);
            assert(fabs(distance.LengthSqr()-1)<0.0001f);
        }
    }
    assert(posed[19][2][3]>0.5f && posed[38][2][3]<-0.5f);
    const float invalid[5]={NAN,0,0,0,0};
    memcpy(posed,bind,sizeof(bind));
    HandPose::ApplyFingerCurl(bind,posed,invalid,invalid);
    for(int i=0;i<43;++i)for(int r=0;r<3;++r)for(int c=0;c<4;++c)
        assert(std::isfinite(posed[i][r][c]));

    // A resting gun grip must keep contact, while the trigger changes only
    // the index chain. Neither input can displace the wrist or gun mechanism.
    matrix3x4_t gunBind[45], resting[45], triggered[45];
    for (int i=0;i<45;++i) gunBind[i] = bind[i < 43 ? i : 0];
    memcpy(resting,gunBind,sizeof(gunBind));
    memcpy(triggered,gunBind,sizeof(gunBind));
    HandPose::ApplyGunGrip(gunBind,resting,open);
    const float triggerOnly[5]={0,1,0,0,0};
    HandPose::ApplyGunGrip(gunBind,triggered,triggerOnly);
    assert(fabs(resting[16][2][3]-gunBind[16][2][3]) > 0.1f);
    assert(fabs(triggered[19][2][3]-resting[19][2][3]) > 0.01f);
    for (int i=0;i<45;++i) {
        if (i < 18 || i > 20) assert(!memcmp(&resting[i],&triggered[i],sizeof(matrix3x4_t)));
        if (i >= 24) assert(!memcmp(&resting[i],&gunBind[i],sizeof(matrix3x4_t)));
    }
    for(int r=0;r<3;++r) assert(fabsf(resting[8][r][3]-gunBind[8][r][3])<.001f);
    float beforeLength=0, afterLength=0;
    for(int r=0;r<3;++r) {
        beforeLength+=powf(gunBind[8][r][3]-gunBind[7][r][3],2);
        afterLength+=powf(resting[8][r][3]-resting[7][r][3],2);
    }
    assert(fabsf(beforeLength-afterLength)<.001f);

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

static void CheckFirstPersonBody() {
    static_assert(FirstPersonBody::MaxBones >= 95);
    const auto shift=FirstPersonBody::HorizontalCameraOffset({10,20,62},{15,18,45});
    assert(shift.x==5 && shift.y==-2 && shift.z==0); // crouch never lifts the floor
    const auto secondEye=FirstPersonBody::HorizontalCameraOffset({10,20,62},{15,18,45});
    assert((shift-secondEye).LengthSqr()==0);

    // Setback follows heading, with no vertical movement, including after a
    // portal turns the player. Zero keeps the previous camera alignment.
    assert((FirstPersonBody::BackwardOffset(0,8)-Vector(-8,0,0)).LengthSqr()<0.0001f);
    assert((FirstPersonBody::BackwardOffset(90,8)-Vector(0,-8,0)).LengthSqr()<0.0001f);
    assert((FirstPersonBody::BackwardOffset(180,8)-Vector(8,0,0)).LengthSqr()<0.0001f);
    assert(FirstPersonBody::BackwardOffset(35,0).LengthSqr()==0);

    // root -> hips -> upper body -> upper child, with a separate leg branch.
    const int parents[6] = {-1, 0, 1, 2, 1, 4};
    matrix3x4_t bones[6];
    for (int i=0; i<6; ++i)
        bones[i] = HandPose::Frame({1,0,0}, {0,1,0}, {0,0,1}, {float(i), 2, 3});
    const auto hips = bones[1];
    const auto leg = bones[4];

    FirstPersonBody::CollapseUpperBody(bones, parents, 6, 2, 1, {10,20,30});
    assert(FirstPersonBody::IsDescendant(parents, 6, 2, 2));
    assert(FirstPersonBody::IsDescendant(parents, 6, 3, 2));
    assert(!FirstPersonBody::IsDescendant(parents, 6, 4, 2));
    assert(!memcmp(&bones[1], &hips, sizeof(hips)));
    assert(!memcmp(&bones[4], &leg, sizeof(leg)));
    assert(bones[2][0][0] == 0 && bones[2][1][1] == 0 && bones[2][2][2] == 0);
    assert(bones[2][0][3] == 10 && bones[2][1][3] == 20 && bones[2][2][3] == 30);
    assert(!memcmp(&bones[2], &bones[3], sizeof(bones[2])));

    matrix3x4_t branches[6];
    for (int i=0; i<6; ++i)
        branches[i] = HandPose::Frame({1,0,0}, {0,1,0}, {0,0,1}, {float(i), 4, 5});
    const auto branchesHips = branches[1];
    const int hiddenRoots[2] = {2, 4};
    matrix3x4_t atRoots[6]; memcpy(atRoots, branches, sizeof(atRoots));
    FirstPersonBody::CollapseBranchesAtRoots(atRoots, parents, 6, hiddenRoots, 2);
    for(int root : hiddenRoots)for(int r=0;r<3;++r)
        assert(atRoots[root][r][3]==branches[root][r][3]);
    FirstPersonBody::CollapseBranches(branches, parents, 6, hiddenRoots, 2, 1, {7,8,9});
    assert(!memcmp(&branches[1], &branchesHips, sizeof(branchesHips)));
    assert(!memcmp(&branches[2], &branches[3], sizeof(branches[2])));
    assert(!memcmp(&branches[4], &branches[5], sizeof(branches[4])));
    assert(branches[2][0][3] == 7 && branches[2][1][3] == 8 && branches[2][2][3] == 9);
    assert(branches[2][0][0] == 0 && branches[4][1][1] == 0);
}

static void CheckPortalPickup()
{
    const Vector eye(32, -120, 64), offset(24, -12, -18);
    const QAngle head(12, 173, 5), hand(35, -160, -20);
    const auto relative = PortalPose::RelativeHand(offset, hand, head);
    const auto initial = PortalPose::WorldHand(relative, eye, head);
    const auto expected = PortalPose::Frame(eye + offset, hand);
    const auto nearFrame = [](const matrix3x4_t& a, const matrix3x4_t& b) {
        for (int r=0; r<3; ++r) for (int c=0; c<4; ++c)
            assert(fabsf(a[r][c]-b[r][c]) < 0.002f);
    };
    nearFrame(initial, expected);
    // Server has crossed but the client still holds its entry-side sample.
    // Translation, yaw reversal, and floor/ceiling rotations must all carry
    // the entire hand pose, including orientation, to the exit side.
    for (const QAngle turn : {QAngle(0,0,0), QAngle(0,180,0),
        QAngle(0,90,0), QAngle(90,0,0), QAngle(-90,0,0), QAngle(0,0,90)}) {
        const auto portal = PortalPose::Frame({640,-450,300}, turn);
        const auto exitHead = HandPose::Concat(portal, PortalPose::Frame(eye, head));
        const auto exitHand = PortalPose::WorldHand(relative,
            PortalPose::Position(exitHead), PortalPose::Angles(exitHead));
        nearFrame(exitHand, HandPose::Concat(portal, initial));
        nearFrame(HandPose::Concat(HandPose::InverseRigid(portal), exitHand), initial);
        assert(std::isfinite(PortalPose::UprightYawDelta(portal, head)));
    }
    const auto quarterTurn = PortalPose::Frame({1,2,3}, {0,90,0});
    assert(fabsf(PortalPose::UprightYawDelta(quarterTurn, {0,179,0}) - 90) < 0.001f);
    // A short portal displacement must still turn tracking. Looking straight
    // into a floor portal uses the lateral axis instead of an undefined yaw.
    const auto floor = PortalPose::Frame({0,0,0}, {90,0,0});
    assert(std::isfinite(PortalPose::UprightYawDelta(floor, {0,0,0})));
    assert(std::isfinite(PortalPose::UprightYawDelta(floor, {90,0,0})));
}

static void *expectedThis;
static void CheckContactPickup()
{
    Vector origin;
    QAngle angles;
    // Hand inside a cube whose first surface is x=40; query starts outside.
    assert(PickupTrace::ContactQuery({0,0,64}, {50,0,64}, 0.8f, false, false, origin, angles));
    assert((origin-Vector(38,0,64)).LengthSqr()<0.001f);
    Vector forward;
    QAngle::AngleVectors(angles, &forward, nullptr, nullptr);
    assert((forward-Vector(1,0,0)).LengthSqr()<0.001f);
    // A portal rotation/translation must preserve the same surface margin.
    assert(PickupTrace::ContactQuery({100,200,20}, {100,250,20}, 0.8f, false, false, origin, angles));
    assert((origin-Vector(100,238,20)).LengthSqr()<0.001f);
    assert(PickupTrace::ContactQuery({0,0,100}, {0,0,50}, 0.8f, false, false, origin, angles));
    assert((origin-Vector(0,0,62)).LengthSqr()<0.001f);
    QAngle::AngleVectors(angles, &forward, nullptr, nullptr);
    assert((forward-Vector(0,0,-1)).LengthSqr()<0.001f);
    // No hit, occlusion far from the hand, or an embedded start cannot retry.
    for (float fraction : {0.0f, 1.0f, -0.1f, 1.1f, 0.2f, std::numeric_limits<float>::quiet_NaN()})
        assert(!PickupTrace::ContactQuery({0,0,64}, {50,0,64}, fraction, false, false, origin, angles));
    assert(!PickupTrace::ContactQuery({0,0,64}, {50,0,64}, 0.8f, true, false, origin, angles));
    assert(!PickupTrace::ContactQuery({0,0,64}, {50,0,64}, 0.8f, false, true, origin, angles));
    assert(!PickupTrace::ContactQuery({0,0,64}, {0,0,64}, 0.8f, false, false, origin, angles));
    assert(!PickupTrace::ContactQuery({0,0,64}, {std::numeric_limits<float>::infinity(),0,64}, 0.8f, false, false, origin, angles));

    // Level grip must remain level when rebased onto the server head, including
    // when the player is looking down. Do not use the separately tilted gun ray.
    QAngle grip;
    QAngle::VectorAngles({1,0,0}, {0,0,1}, grip);
    const auto relative = PortalPose::RelativeHand({20,-12,-18}, grip, {45,90,0});
    const auto world = PortalPose::WorldHand(relative, {0,0,64}, {45,90,0});
    assert(fabsf(world[2][0])<0.001f);
    assert(fabsf(PortalPose::Angles(world).x)<0.001f);
}

static bool __fastcall InGame(void *self, void *) { assert(self == expectedThis); return true; }
static void __fastcall GetAngles(void *self, void *, QAngle &out) { assert(self == expectedThis); out = {1,2,3}; }
static void __fastcall Command(void *self, void *, const char *text) { assert(self == expectedThis); assert(!strcmp(text,"test")); }
static void __fastcall Screen(void *self, void *, int &w, int &h) { assert(self == expectedThis); w=1280; h=720; }
static void __fastcall PushTarget(void *self, void *, ITexture *target, int x, int y, int w, int h) {
    assert(self == expectedThis && target == reinterpret_cast<ITexture *>(0x1234));
    assert(x == 0 && y == 0 && w == 2352 && h == 2352);
}
static void __fastcall PopTarget(void *self, void *) { assert(self == expectedThis); }
static void CheckOptionalGunGrip() {
    OptionalGunGrip::State grip;
    assert(!grip.Update(true,true,true,false,3,6));
    assert(grip.Update(true,true,true,true,3,6));
    assert(grip.Update(true,true,true,true,10,6));
    assert(!grip.Update(true,true,true,false,3,6));
    assert(!grip.Update(true,true,true,true,20,6));
    assert(!grip.Update(true,true,true,true,3,6)); // Held before entering.
    grip.Update(true,true,true,false,3,6);
    assert(grip.Update(true,true,true,true,3,6));
    assert(!grip.Update(true,true,true,true,16,6)); // Pull-away release.
    for (int failure=0; failure<4; ++failure) {
        grip.Update(true,true,true,false,3,6);
        assert(grip.Update(true,true,true,true,3,6));
        assert(!grip.Update(failure!=0, failure!=1, failure!=2, true,
            failure==3 ? std::numeric_limits<float>::quiet_NaN() : 3.0f,6));
    }
    const float open[5]={0,0,0,0,0}, closed[5]={1,1,1,1,1}, mid[5]={.6f,.6f,.6f,.6f,.6f};
    assert(!OptionalGunGrip::Squeeze(false,false,closed,false));
    assert(OptionalGunGrip::Squeeze(true,false,open,false));
    assert(OptionalGunGrip::Squeeze(false,true,closed,false));
    assert(!OptionalGunGrip::Squeeze(false,true,mid,false));
    assert(OptionalGunGrip::Squeeze(false,true,mid,true));
    assert(!OptionalGunGrip::Squeeze(false,true,open,true));
    unsigned char mdl[512]{};
    auto put=[&](int off,int value){memcpy(mdl+off,&value,4);};
    put(4,48); put(156,45); put(240,1); put(244,256);
    put(256,92); put(264,24); memcpy(mdl+348,"lefthand_grip",13);
    const auto expected=HandPose::Frame({-1,0,0},{0,0,1},{0,1,0},{3,-2,10});
    memcpy(mdl+268,&expected,sizeof(expected));
    matrix3x4_t socket;
    assert(OptionalGunGrip::ReadSocket(mdl,sizeof(mdl),socket));
    assert(!memcmp(&socket,&expected,sizeof(socket)));
    assert(!OptionalGunGrip::ReadSocket(mdl,347,socket));
    put(256,2147483647); assert(!OptionalGunGrip::ReadSocket(mdl,sizeof(mdl),socket));
    put(256,92); put(264,8); assert(!OptionalGunGrip::ReadSocket(mdl,sizeof(mdl),socket));
    put(264,24); put(240,-1); assert(!OptionalGunGrip::ReadSocket(mdl,sizeof(mdl),socket));
    // Cached controller-relative sockets must follow both translation and rotation.
    const auto controller=HandPose::Frame({0,1,0},{-1,0,0},{0,0,1},{100,200,300});
    const auto world=HandPose::Concat(controller,expected);
    const auto restored=HandPose::Concat(HandPose::InverseRigid(controller),world);
    for(int r=0;r<3;++r) for(int c=0;c<4;++c) assert(fabsf(restored[r][c]-expected[r][c])<.001f);
    const auto fitted = HandPose::FitGunToPalm(controller);
    const auto fitLocal = HandPose::Concat(HandPose::InverseRigid(controller), fitted);
    assert(fabsf(fitLocal[0][3]-.218f)<.001f && fabsf(fitLocal[1][3]+7.66f)<.001f);
    assert(fabsf(fitLocal[2][3]+3.3f)<.001f);
    for(int r=0;r<3;++r) for(int c=0;c<3;++c) assert(fabsf(fitted[r][c]-1.2f*controller[r][c])<.001f);
    const auto supportWorld = HandPose::Concat(fitted, expected);
    const auto support = HandPose::RigidOrientation(supportWorld);
    for(int r=0;r<3;++r) assert(support[r][3]==supportWorld[r][3]);
    for(int c=0;c<3;++c) {
        float norm=0;for(int r=0;r<3;++r) norm+=support[r][c]*support[r][c];
        assert(fabsf(norm-1)<.001f);
    }
}
static unsigned char portalTraceFlags[2];
static bool invalidPortalTrace = false;
static void *expectedPortal = nullptr;
static void __cdecl PortalTraceStub(void *portal, const Ray_t& ray, unsigned mask,
    CTraceFilter *filter, CGameTrace *out, bool throughPortal) {
    assert(portal == expectedPortal && mask == 0x400b && filter && throughPortal);
    assert(!ray.m_IsRay && ray.m_IsSwept && ray.m_Extents.x == 3);
    portalTraceFlags[0] = portalTraceFlags[1] = 1;
    out->fraction = invalidPortalTrace ? std::numeric_limits<float>::quiet_NaN() : .75f;
    out->startsolid = out->allsolid = false;
}
static void CheckPortalTrace() {
    assert(!PortalTrace::Binding::Resolve(0).function);
    unsigned char player[0x1660]{}, portal[0xabc]{};
    uintptr_t entries[8]{}, list = reinterpret_cast<uintptr_t>(entries);
    const uint32_t handle = (7u << 12) | 1;
    memcpy(player + 0x1658, &handle, 4);
    entries[5] = reinterpret_cast<uintptr_t>(portal); entries[6] = 7;
    portal[0xab4] = 1;
    unsigned char linked = 1;
    const uintptr_t link = reinterpret_cast<uintptr_t>(&linked);
    memcpy(portal + 0xab8, &link, 4);
    PortalTrace::Binding binding{PortalTraceStub, &list, portalTraceFlags};
    expectedPortal = portal;
    assert(binding.Environment(player) == portal);
    entries[6] = 8; assert(!binding.Environment(player)); entries[6] = 7;
    linked = 0; assert(!binding.Environment(player)); linked = 1;
    portal[0xab4] = 0; assert(!binding.Environment(player)); portal[0xab4] = 1;
    entries[5] = 0; assert(!binding.Environment(player)); entries[5] = reinterpret_cast<uintptr_t>(portal);
    Ray_t ray{}; ray.Init({0,0,0},{20,0,0},{-3,-3,-3},{3,3,3});
    CGameTrace trace;
    CTraceFilterSkipEntity filter(reinterpret_cast<IHandleEntity *>(player),0);
    for (int first = 0; first <= 1; ++first) for (int second = 0; second <= 1; ++second) {
        portalTraceFlags[0] = first; portalTraceFlags[1] = second;
        assert(binding.Trace(player, ray, 0x400b, &filter, &trace));
        assert(trace.fraction == .75f && !trace.startsolid);
        assert(portalTraceFlags[0] == first && portalTraceFlags[1] == second);
        invalidPortalTrace = true;
        assert(!binding.Trace(player, ray, 0x400b, &filter, &trace));
        assert(portalTraceFlags[0] == first && portalTraceFlags[1] == second);
        invalidPortalTrace = false;
    }
}
int main() {
    CheckPortalTrace();
    CheckOptionalGunGrip();
    CheckGunAttachments();
    CheckHandAttachment();
    CheckFirstPersonBody();
    CheckCameraCollision();
    CheckPortalPickup();
    CheckContactPickup();
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
    puts("Portal ABI, trace, hand attachment, optional gun support, body, collision, portal pickup, and contact pickup regression checks passed");
}
