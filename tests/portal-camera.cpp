#include <Windows.h>
#include <cassert>
#include <cstdio>
#include "sdk/sdk.h"
#include "portalcamera.h"

static void Near(const Vector& a,const Vector& b,float tolerance=.003f) {
    assert((a-b).LengthSqr()<tolerance*tolerance);
}
int main(int argc,char** argv) {
    unsigned cases=0;float previousError=0;
    for(const auto& turn : {QAngle(0,180,0),QAngle(90,0,0),QAngle(-90,83,0),QAngle(0,12,180)}) {
        PortalCamera::Frame camera;
        camera.transformed=true;
        camera.toLinked=PortalPose::Frame({-1200,600,2000},turn);
        for(float pitch:{-89.f,-40.f,0.f,40.f,89.f})
        for(float yaw:{-179.f,-80.f,0.f,80.f,179.f})
        for(float roll:{-90.f,0.f,90.f})
        for(float eye:{-1.4f,1.4f}) {
            const Vector bodyEye(512,120,48),roomscale(12,6,-8);
            const QAngle head(pitch,yaw,roll);
            const auto headFrame=PortalPose::Frame(bodyEye+roomscale,head);
            const Vector side(headFrame[0][1],headFrame[1][1],headFrame[2][1]);
            const Vector entryEye=bodyEye+roomscale+side*eye;
            const Vector nativeEye=camera.Map(bodyEye);
            Near(camera.Unmap(nativeEye),bodyEye);
            const auto entryView=PortalPose::Frame(entryEye,head);
            const auto exitView=PortalPose::Frame(camera.Map(entryEye),camera.Map(head));
            const Vector point=bodyEye+roomscale+Vector(60,-8,-5);
            matrix3x4_t gun=PortalPose::Frame(point,QAngle(15,70,-33));
            const auto reference=HandPose::Concat(HandPose::InverseRigid(entryView),gun);
            camera.Map(&gun,1);
            const auto actual=HandPose::Concat(HandPose::InverseRigid(exitView),gun);
            Near(PortalPose::Position(actual),PortalPose::Position(reference));
            for(int r=0;r<3;++r) for(int c=0;c<3;++c)
                assert(fabsf(actual[r][c]-reference[r][c])<.0001f);
            const auto oldView=PortalPose::Frame(nativeEye+roomscale+side*eye,head);
            const auto old=HandPose::Concat(HandPose::InverseRigid(oldView),gun);
            previousError=std::fmax(previousError,sqrtf((PortalPose::Position(old)-PortalPose::Position(reference)).LengthSqr()));
            // A light/attachment and the gun use the same transform, preserving
            // their relative placement across either eye and every portal axis.
            auto light=PortalPose::Frame(point+Vector(2,3,4),{0,0,0});
            const Vector before=camera.Unmap(PortalPose::Position(gun));
            camera.Map(&light,1);
            Near(camera.Unmap(PortalPose::Position(light))-before,{2,3,4});
            ++cases;
        }
        PortalCamera::Frame current;
        { PortalCamera::Scope outer(current,camera);
          assert(current.transformed);
          {PortalCamera::Scope nested(current,PortalCamera::Frame{});assert(!current.transformed);}
          assert(current.transformed);
        }
        assert(!current.transformed);
    }
    PortalCamera::Frame off;
    Near(off.Map(Vector(1,2,3)),{1,2,3});
    Near(off.Unmap(Vector(1,2,3)),{1,2,3});
    assert(!PortalCamera::Read(nullptr,{},false).transformed);
    assert(previousError>50);
    // Exercise the actual native-state reader with valid handles and the
    // same transformed-eye flag observed during the installed play session.
    unsigned char player[0x1660]{},portal[0xabc]{},simulator=1,flags[2]{};
    uint32_t entities[8]{};
    uintptr_t list=reinterpret_cast<uintptr_t>(entities);
    entities[5]=reinterpret_cast<uintptr_t>(portal);entities[6]=1;
    const uint32_t handle=0x1001;
    memcpy(player+0x1658,&handle,4);player[0x1654]=1;portal[0xab4]=1;
    const uintptr_t simulatorAddress=reinterpret_cast<uintptr_t>(&simulator);
    memcpy(portal+0xab8,&simulatorAddress,4);
    const auto transition=PortalPose::Frame({100,200,300},{90,12,180});
    memcpy(portal+0x864,&transition,sizeof(transition));
    PortalTrace::Binding binding{reinterpret_cast<PortalTrace::TraceFn>(1),&list,flags};
    const auto read=PortalCamera::Read(player,binding,true);
    assert(read.transformed);Near(read.Map(Vector(0,0,0)),{100,200,300});
    player[0x1654]=0;assert(!PortalCamera::Read(player,binding,true).transformed);
    player[0x1654]=1;assert(!PortalCamera::Read(player,binding,false).transformed);
    entities[6]=2;assert(!PortalCamera::Read(player,binding,true).transformed);
    entities[6]=1;portal[0xab4]=0;assert(!PortalCamera::Read(player,binding,true).transformed);
    portal[0xab4]=1;
    const float invalid=NAN;memcpy(portal+0x864,&invalid,4);
    assert(!PortalCamera::Read(player,binding,true).transformed);
    if(argc==2) {
        const auto client=LoadLibraryExA(argv[1],nullptr,DONT_RESOLVE_DLL_REFERENCES);
        assert(client && PortalCamera::Supported(reinterpret_cast<uintptr_t>(client)));
        assert(PortalTrace::Binding::Resolve(reinterpret_cast<uintptr_t>(client)).function);
        FreeLibrary(client);
    }
    printf("PASS: %u portal stereo camera/model/light cases; old mixed-space error=%f; native ABI=%s\n",
        cases,previousError,argc==2?"verified":"not supplied");
}
