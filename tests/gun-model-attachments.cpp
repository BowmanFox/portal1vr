#include <Windows.h>
#include <cassert>
#include <fstream>
#include <vector>
#include <iterator>
#include "portalpose.h"
#include "gunattachments.h"
#include "gunray.h"
#include "portalshotfx.h"

// Optional regression using the actual compiled custom v_portalgun.mdl.
int main(int argc,char **argv) {
    if(argc!=2)return 2;
    std::ifstream file(argv[1],std::ios::binary);
    std::vector<unsigned char> data((std::istreambuf_iterator<char>(file)),{});
    assert(data.size()>=248);
    int count,offset;
    memcpy(&count,data.data()+156,4);memcpy(&offset,data.data()+160,4);
    assert(count==45 && offset>=248 && size_t(offset)+45*216<=data.size());
    matrix3x4_t bind[45],native[45];
    for(int i=0;i<45;++i) {
        matrix3x4_t inverse;memcpy(&inverse,data.data()+offset+i*216+96,sizeof(inverse));
        bind[i]=HandPose::InverseRigid(inverse);
    }
    GunAttachments::Model model;assert(model.Read(data.data(),data.size(),bind));
    assert(model.count==18);
    assert(model.hasBarrel);
    auto source=bind[24];for(int r=0;r<3;++r)source[r][3]=bind[8][r][3];
    float maxError=0,maxRayError=0,maxPickupError=0;int cases=0,rangeCases=0,pickupCases=0;
    for(float pitch:{-90.f,-75.f,-30.f,0.f,45.f,80.f,90.f})
    for(float yaw:{-150.f,-45.f,0.f,90.f})
    for(float roll:{-180.f,-90.f,-60.f,0.f,60.f,90.f,180.f}) {
        const auto engine=PortalPose::Frame({120,70,40},{12,35,-8});
        for(int i=0;i<45;++i)native[i]=HandPose::Concat(engine,bind[i]);
        native[25]=HandPose::Concat(native[25],PortalPose::Frame({0,0,-.8f},{3,0,0}));
        Vector forward,right,up;QAngle::AngleVectors({pitch,yaw,roll},&forward,&right,&up);
        const auto controller=HandPose::Frame(-right,up,forward,{-30,10,60});
        const auto gun=HandPose::Reanchor(HandPose::FitGunToPalm(bind[24]),source,controller);
        const auto barrel=HandPose::Concat(controller,model.barrelFromController);
        const auto& muzzle=model.attachments[0];
        const auto authored=HandPose::Concat(HandPose::Reanchor(bind[muzzle.bone],bind[24],gun),muzzle.local);
        const auto rigid=HandPose::RigidOrientation(authored);
        const Vector barrelForward(rigid[0][0],rigid[1][0],rigid[2][0]);
        const Vector wrist=PortalPose::Position(controller);
        PortalShotFx::Data effect;
        memset(&effect,0xa5,sizeof(effect));
        effect.origin={500,90,12};effect.start={200,-300,40};effect.angles={10,40,25};
        const auto oldEffect=effect;
        assert(PortalShotFx::Align(effect,authored));
        Vector effectDirection;QAngle::AngleVectors(effect.angles,&effectDirection,nullptr,nullptr);
        assert((effect.origin-PortalPose::Position(authored)).LengthSqr()<1e-8f);
        assert((effectDirection-barrelForward).LengthSqr()<1e-8f);
        assert(!memcmp(&effect.start,&oldEffect.start,2*sizeof(Vector)));
        assert(!memcmp(effect.remaining,oldEffect.remaining,sizeof(effect.remaining)));
        Vector rayStart,rayDirection;
        assert(GunRay::FromBarrel(barrel,wrist,rayStart,rayDirection));
        assert((rayStart-wrist).LengthSqr()>.5f); // reproduces the old wrist-ray parallax
        // Use the same barrel ray for native prop selection, independently of
        // the wrist used for carrying. Rebase both position and direction if
        // the server crosses a portal before the next controller sample.
        const auto head=PortalPose::Frame({17,-40,64},{37,120,13});
        QAngle pickupAngles;QAngle::VectorAngles(rayDirection,up,pickupAngles);
        const auto relative=PortalPose::RelativeHand(rayStart-PortalPose::Position(head),
            pickupAngles,PortalPose::Angles(head));
        for(const auto& crossing:{PortalPose::Frame({0,0,0},{0,0,0}),
            PortalPose::Frame({300,-100,20},{0,180,0}),PortalPose::Frame({0,80,400},{90,0,0})}) {
            const auto serverHead=HandPose::Concat(crossing,head);
            const auto selection=PortalPose::WorldHand(relative,PortalPose::Position(serverHead),PortalPose::Angles(serverHead));
            const auto expectedSelection=HandPose::Concat(crossing,PortalPose::Frame(rayStart,pickupAngles));
            Vector selectionDirection;QAngle::AngleVectors(PortalPose::Angles(selection),&selectionDirection,nullptr,nullptr);
            const Vector expectedDirection(expectedSelection[0][0],expectedSelection[1][0],expectedSelection[2][0]);
            const auto originError=PortalPose::Position(selection)-PortalPose::Position(expectedSelection);
            assert(originError.LengthSqr()<.00001f);
            assert((selectionDirection-expectedDirection).LengthSqr()<.000001f);
            const auto distanceError=originError+(selectionDirection-expectedDirection)*1024;
            maxPickupError=std::fmax(maxPickupError,sqrtf(distanceError.LengthSqr()));
            ++pickupCases;
        }
        // Recoil slides the front cover down the same barrel line. Check near
        // walls and distant targets without converging at an arbitrary range.
        for(float recoil:{0.f,-3.f,1.f})
        for(float distance:{8.f,32.f,128.f,512.f,2048.f}) {
            const Vector target=PortalPose::Position(authored)+barrelForward*(distance+recoil);
            const Vector toTarget=target-rayStart;
            const float along=toTarget.x*rayDirection.x+toTarget.y*rayDirection.y+toTarget.z*rayDirection.z;
            const Vector error=toTarget-rayDirection*along;
            maxRayError=std::fmax(maxRayError,sqrtf(error.LengthSqr()));
            ++rangeCases;
        }
        for(int n=1;n<=model.count;++n) {
            const auto& a=model.attachments[n-1];
            const auto drawn=HandPose::Concat(HandPose::Reanchor(native[a.bone],native[24],gun),a.local);
            matrix3x4_t queried,otherEye;
            assert(model.Resolve(n,controller,native,queried));
            assert(model.Resolve(n,controller,native,otherEye));
            assert(!memcmp(&queried,&otherEye,sizeof(queried)));
            const auto rigid=HandPose::RigidOrientation(queried);
            const auto angleFrame=PortalPose::Frame(PortalPose::Position(rigid),PortalPose::Angles(rigid));
            for(int r=0;r<3;++r)for(int c=0;c<3;++c)
                assert(std::fabs(angleFrame[r][c]-rigid[r][c])<.001f);
            for(int r=0;r<3;++r)for(int c=0;c<4;++c)
                maxError=std::fmax(maxError,std::fabs(queried[r][c]-drawn[r][c]));
            ++cases;
        }
    }
    assert(maxError<.001f);
    assert(maxRayError<.002f);
    // Float matrix/Euler round trips stay below 0.25 mm even at 24 m,
    // far beyond native pickup reach, including exactly vertical poses.
    assert(maxPickupError<.01f);
    printf("{\"attachments\":%d,\"angle_poses\":%d,\"queries\":%d,\"maximum_matrix_error\":%.9f,\"range_checks\":%d,\"maximum_barrel_ray_error\":%.9f,\"pickup_barrel_checks\":%d,\"maximum_pickup_error_at_1024\":%.9f,\"blast_pose_checks\":%d,\"passed\":true}\n",model.count,cases/model.count,cases,maxError,rangeCases,maxRayError,pickupCases,maxPickupError,cases/model.count);
}
