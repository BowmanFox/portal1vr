#include <Windows.h>
#include <cassert>
#include <fstream>
#include <vector>
#include <iterator>
#include "portalpose.h"
#include "gunattachments.h"

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
    auto source=bind[24];for(int r=0;r<3;++r)source[r][3]=bind[8][r][3];
    float maxError=0;int cases=0;
    for(float pitch:{-75.f,-30.f,0.f,45.f,80.f})
    for(float yaw:{-150.f,-45.f,0.f,90.f})
    for(float roll:{-60.f,0.f,60.f}) {
        const auto engine=PortalPose::Frame({120,70,40},{12,35,-8});
        for(int i=0;i<45;++i)native[i]=HandPose::Concat(engine,bind[i]);
        native[25]=HandPose::Concat(native[25],PortalPose::Frame({0,0,-.8f},{3,0,0}));
        Vector forward,right,up;QAngle::AngleVectors({pitch,yaw,roll},&forward,&right,&up);
        const auto controller=HandPose::Frame(-right,up,forward,{-30,10,60});
        const auto gun=HandPose::Reanchor(HandPose::FitGunToPalm(bind[24]),source,controller);
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
    printf("{\"attachments\":%d,\"angle_poses\":60,\"queries\":%d,\"maximum_matrix_error\":%.9f,\"passed\":true}\n",model.count,cases,maxError);
}
