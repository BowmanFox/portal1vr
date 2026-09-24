#include <Windows.h>
#include <cassert>
#include <cstdio>
#include "sdk/sdk.h"
#include "nativepose.h"
#include "pickuptrace.h"
#include "autocalibration.h"
#include "vrsettings.h"

static float NativeCarryDrop(QAngle angles) {
    angles.x=std::clamp(angles.x,-75.f,75.f);
    Vector f,r,u;QAngle::AngleVectors(angles,&f,&r,&u);
    // Verified Portal 1 UpdateObject: negative up.z and right.z multiply the
    // player's view offset and are added to the carry origin.
    return 64.f*(std::min(u.z,0.f)+std::min(r.z,0.f));
}
int main(int argc,char** argv) {
    int cases=0;
    assert(NativeCarryDrop({0,0,90}) < -63.9f);
    for(float pitch:{-89.9f,-60.f,0.f,60.f,89.9f})
    for(float yaw:{-170.f,0.f,135.f})
    for(int roll=-180;roll<=180;roll+=5) {
        const QAngle hand(pitch,yaw,float(roll));
        const auto carry=PickupTrace::CarryDirectionAngles(hand);
        Vector before,after;QAngle::AngleVectors(hand,&before,nullptr,nullptr);
        QAngle::AngleVectors(carry,&after,nullptr,nullptr);
        assert((before-after).LengthSqr()<1e-10f);
        assert(fabsf(NativeCarryDrop(carry))<1e-5f);
        assert(hand.z==roll); // orientation remains available to later solver reads
        ++cases;
    }
    // Viewmodel and world rays must project identically at steep elevation.
    const float eyeAspect=1.f,fov=104.f,tanHalf=tanf(DEG2RAD(fov*.5f));
    for(float desktop:{4.f/3,16.f/9,21.f/9})
    for(float elevation:{-65.f,-30.f,0.f,30.f,65.f}) {
        const float y=tanf(DEG2RAD(elevation));
        const float world=y*eyeAspect/tanHalf;
        const float oldGun=y*desktop/tanHalf;
        const float correctedGun=y*eyeAspect/tanHalf;
        assert(fabsf(correctedGun-world)<1e-6f);
        if(elevation!=0) assert(fabsf(oldGun-world)>.1f);
    }
    const auto identity=PortalPose::Frame({0,0,0},{0,0,0});
    AutoCalibration::Origin invalidOrigin;Vector invalidCenter(1,2,3);float invalidYaw=45;
    matrix3x4_t zero{};
    assert(!invalidOrigin.Update(zero,true,invalidCenter,invalidYaw) && !invalidOrigin.ready);
    auto reflection=identity;reflection[0][0]=-1;
    assert(!invalidOrigin.Update(reflection,true,invalidCenter,invalidYaw) && !invalidOrigin.ready);
    assert(!invalidOrigin.Update(PortalPose::Frame({0,0,0},{10,0,0}),true,invalidCenter,invalidYaw));
    AutoCalibration::Origin slowOrigin;Vector slowCenter(0,0,0);float slowYaw=0;
    slowOrigin.Update(identity,true,slowCenter,slowYaw);
    for(int i=1;i<=10000;++i)
        slowOrigin.Update(PortalPose::Frame({i*.00001f,0,0},{0,i*.0001f,0}),true,slowCenter,slowYaw);
    assert(fabsf(slowCenter.x-.1f)<.00015f && fabsf(slowYaw+1.f)<.002f);
    AutoCalibration::Stability stability;
    for(int i=0;i<60;++i) assert(!stability.Step(.01f,{.5f,0,1.7f},{0,179.5f,0},true));
    for(int i=0;i<40;++i) stability.Step(.01f,{.501f,0,1.7f},{0,-179.5f,0},true);
    assert(stability.elapsed>.9f); // yaw wrap does not look like a spin
    assert(!stability.Step(.01f,{.5f,0,1.4f},{0,0,0},true)); // crouch
    assert(!stability.Step(.01f,{.5f,0,1.7f},{0,0,0},false)); // loss
    assert(!stability.Step(.2f,{.5f,0,1.7f},{0,0,0},true)); // resume
    for(int i=0;i<200;++i)
        assert(!stability.Step(.01f,{i*.002f,0,1.7f},{0,0,0},true)); // slow actual walking
    assert(AutoCalibration::NeedsBodyAlignment(.1f,false,1.f,false));
    assert(!AutoCalibration::NeedsBodyAlignment(.1f,false,.1f,false)); // ordinary wall
    assert(!AutoCalibration::NeedsBodyAlignment(1.f,false,1.f,false)); // clear both
    assert(!AutoCalibration::NeedsBodyAlignment(.1f,true,1.f,false)); // embedded
    assert(!AutoCalibration::NeedsBodyAlignment(.1f,false,1.f,true));
    // Explicit OpenVR origin change: +1 meter right, +2 up, +3 back.
    const float openvr[3][4]={{1,0,0,1},{0,1,0,2},{0,0,1,3}};
    const auto source=AutoCalibration::SourceSpace(openvr);
    assert((PortalPose::Position(source)-Vector(-3,-1,2)).LengthSqr()==0);
    for(float turn:{-170.f,-45.f,0.f,110.f}) {
        AutoCalibration::Origin origin;
        Vector center(.3f,-.6f,1.7f);float yaw=35;
        assert(!origin.Update(identity,true,center,yaw));
        const Vector beforeCenter=center,head(.55f,-.45f,1.6f);
        const auto change=PortalPose::Frame({2,-4,.8f},{0,turn,0});
        const auto movedHead=AutoCalibration::TransformPoint(change,head);
        assert(origin.Update(change,true,center,yaw));
        const Vector before=AutoCalibration::TransformPoint(PortalPose::Frame({0,0,0},{0,35,0}),head-beforeCenter);
        const Vector after=AutoCalibration::TransformPoint(PortalPose::Frame({0,0,0},{0,yaw,0}),movedHead-center);
        assert((before-after).LengthSqr()<1e-10f);
        const Vector hand(.75f,-.3f,1.1f);
        const Vector beforeHand=AutoCalibration::TransformPoint(PortalPose::Frame({0,0,0},{0,35,0}),hand-beforeCenter);
        const Vector afterHand=AutoCalibration::TransformPoint(PortalPose::Frame({0,0,0},{0,yaw,0}),AutoCalibration::TransformPoint(change,hand)-center);
        assert((beforeHand-afterHand).LengthSqr()<1e-10f);
        assert(fabsf(std::remainder(yaw+turn-35,360.f))<1e-4f);
        assert(!origin.Update(change,true,center,yaw)); // no accumulated drift
        auto saved=center;const float savedYaw=yaw;
        assert(!origin.Update(identity,false,center,yaw));
        assert((center-saved).LengthSqr()==0 && yaw==savedYaw);
    }
    AutoCalibration::Drift drift;
    for(int i=0;i<200;++i) assert(drift.Step(.01f,{.5f,0,0},false).LengthSqr()==0);
    for(int i=0;i<200;++i) assert(drift.Step(.01f,{.5f,0,-.3f},true).LengthSqr()==0); // crouch
    for(int i=0;i<200;++i) assert(drift.Step(.01f,{.1f,0,0},true).LengthSqr()==0); // normal lean
    for(int i=0;i<90;++i) assert(drift.Step(.01f,{.5f,0,0},true).LengthSqr()==0);
    Vector offset(.5f,0,0);int steps=0;
    for(int i=0;i<800;++i) {
        const auto correction=drift.Step(.01f,offset,true);
        assert(correction.LengthSqr()<=.00201f*.00201f && correction.z==0);
        offset-=correction;if(correction.LengthSqr()>0) ++steps;
    }
    assert(offset.x<.0151f && steps>200);
    assert(drift.Step(.5f,{.5f,0,0},true).LengthSqr()==0); // paused/late frame
    for(float hz:{72.f,90.f,120.f,144.f}) {
        AutoCalibration::Drift rate;Vector remaining(.5f,.2f,0);float previousSpeed=0;
        for(int i=0;i<int(hz*10);++i) {
            const auto step=rate.Step(1.f/hz,remaining,true);
            const float speed=sqrtf(step.LengthSqr())*hz;
            assert(speed<=.1201f && speed-previousSpeed<=.25f/hz+.0001f);
            assert(step.LengthSqr()<=remaining.LengthSqr());
            remaining-=step;previousSpeed=speed;
        }
        assert(remaining.LengthSqr()<.0151f*.0151f);
    }
    assert(VrSettings::Parse(" portal1vr_hand_left\n")==VrSettings::Command::Left);
    assert(VrSettings::Parse("portal1vr_hand_left;quit")==VrSettings::Command::None);
    assert(VrSettings::Parse("portal1vr_hand_right")==VrSettings::Command::Right);
    assert(VrSettings::Parse("portal1vr_recenter")==VrSettings::Command::Recenter);
    const std::string config="# keep\r\nLeftHanded=false # note\r\nCustom=yes\r\nLeftHanded=false";
    const auto saved=VrSettings::SetBool(config,"LeftHanded",true);
    assert(saved=="# keep\r\nLeftHanded=true# note\r\nCustom=yes\r\nLeftHanded=true");
    assert(VrSettings::SetBool(saved,"LeftHanded",true)==saved);
    assert(VrSettings::SetBool("Custom=yes","LeftHanded",false)=="Custom=yes\nLeftHanded=false\n");
    if(argc==3) {
        HMODULE client=LoadLibraryExA(argv[1],nullptr,DONT_RESOLVE_DLL_REFERENCES);
        HMODULE server=LoadLibraryExA(argv[2],nullptr,DONT_RESOLVE_DLL_REFERENCES);
        assert(client && server);
        assert(NativePose::ViewmodelProjectionReturn(reinterpret_cast<uintptr_t>(client)));
        assert(NativePose::CarryDirectionReturn(reinterpret_cast<uintptr_t>(server)+0x468300));
        assert(NativePose::PortalBlastDispatch(reinterpret_cast<uintptr_t>(server)));
        assert(NativePose::PortalBlastCallback(reinterpret_cast<uintptr_t>(client)));
        assert(NativePose::PortalGunEffectParameters(reinterpret_cast<uintptr_t>(client)));
        FreeLibrary(server);FreeLibrary(client);
    }
    printf("{\"wrist_roll_cases\":%d,\"old_maximum_drop_source_units\":64,\"corrected_drop\":0,\"projection_checks\":15,\"calibration_checks_passed\":true,\"installed_binary_guards\":%s,\"passed\":true}\n",cases,argc==3?"true":"false");
}
