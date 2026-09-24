#pragma once
#include "portalpose.h"
#include "portaltrace.h"

namespace PortalCamera {
// CalcPortalView can move the eye through a portal before PlayerPortalled.
// The eye origin and orientation must stay in the same space. Tracked offsets
// belong in the player's space until the complete frame is transformed.
struct Frame {
    bool transformed = false;
    matrix3x4_t toLinked=PortalPose::Frame({0,0,0},{0,0,0});

    Vector Unmap(const Vector& point) const {
        return transformed ? PortalPose::Position(HandPose::Concat(
            HandPose::InverseRigid(toLinked),PortalPose::Frame(point,{0,0,0}))) : point;
    }
    Vector Map(const Vector& point) const {
        return transformed ? PortalPose::Position(HandPose::Concat(
            toLinked,PortalPose::Frame(point,{0,0,0}))) : point;
    }
    QAngle Map(const QAngle& angles) const {
        return transformed ? PortalPose::Angles(HandPose::Concat(
            toLinked,PortalPose::Frame({0,0,0},angles))) : angles;
    }
    QAngle Unmap(const QAngle& angles) const {
        return transformed ? PortalPose::Angles(HandPose::Concat(
            HandPose::InverseRigid(toLinked),PortalPose::Frame({0,0,0},angles))) : angles;
    }
    void Map(matrix3x4_t* bones, int count) const {
        if(transformed) for(int i=0;i<count;++i) bones[i]=HandPose::Concat(toLinked,bones[i]);
    }
};

inline bool Supported(uintptr_t client) {
    // Verify CalcView's call and CalcPortalView's transform flag/matrix reads.
    const unsigned char call[]={0xff,0x75,0x0c,0x8a,0x45,0xff,0x8b,0xcf,0xff,0x75,0x08,
        0x88,0x87,0x54,0x16,0,0,0xe8,0x1a,0xf8,0xff,0xff};
    const unsigned char transform[]={0x8d,0x87,0x64,0x08,0,0,0xc6,0x83,0x54,0x16,0,0,1,
        0x8b,0xf0,0x8d,0x7d,0x84,0xb9,0x10,0,0,0,0xf3,0xa5};
    return client && SigScanner::IsReadable(client+0x228eb0,sizeof(call))
        && SigScanner::IsReadable(client+0x2289c8,sizeof(transform))
        && !memcmp(reinterpret_cast<void*>(client+0x228eb0),call,sizeof(call))
        && !memcmp(reinterpret_cast<void*>(client+0x2289c8),transform,sizeof(transform));
}

inline Frame Read(void* player, const PortalTrace::Binding& binding, bool supported) {
    Frame result;
    if(!supported || !player
        || !SigScanner::IsReadable(reinterpret_cast<uintptr_t>(player)+0x1654,1)
        || !*(static_cast<const unsigned char*>(player)+0x1654)) return result;
    const auto portal=reinterpret_cast<uintptr_t>(binding.Environment(player));
    if(!portal || !SigScanner::IsReadable(portal+0x864,sizeof(result.toLinked))) return result;
    memcpy(&result.toLinked,reinterpret_cast<void*>(portal+0x864),sizeof(result.toLinked));
    for(int r=0;r<3;++r) for(int c=0;c<4;++c)
        if(!std::isfinite(result.toLinked[r][c])) return result;
    for(int r=0;r<3;++r) for(int c=0;c<3;++c) {
        float dot=0;
        for(int k=0;k<3;++k) dot+=result.toLinked[k][r]*result.toLinked[k][c];
        if(fabsf(dot-(r==c ? 1.f : 0.f))>.001f) return result;
    }
    result.transformed=true;
    return result;
}

class Scope {
    Frame& current;
    Frame saved;
public:
    Scope(Frame& current,const Frame& next):current(current),saved(current) {current=next;}
    ~Scope() {current=saved;}
    Scope(const Scope&)=delete;
    Scope& operator=(const Scope&)=delete;
};
}
