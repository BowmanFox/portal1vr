#pragma once
#include "portalpose.h"
#include <cstddef>
#include <cstdint>

namespace PortalShotFx {
// Installed Portal 1 CEffectData layout. The remaining fields include color,
// endpoint timing and entity identity; preserve them byte for byte.
struct Data {
    Vector origin, start, normal;
    QAngle angles;
    unsigned char remaining[0x58];
};
static_assert(sizeof(Data)==0x88);
static_assert(offsetof(Data,angles)==0x24);
// The verified client callback reads only this prefix (through color at 0x58).
// Its allocation need not share the server CEffectData tail.
constexpr size_t ClientPayloadSize=0x5c;
inline unsigned Color(const Data& data) {
    return reinterpret_cast<const unsigned char*>(&data)[0x58];
}
inline bool Align(Data& effect,const matrix3x4_t& muzzle) {
    for(int r=0;r<3;++r) for(int c=0;c<4;++c)
        if(!std::isfinite(muzzle[r][c])) return false;
    const Vector forward(muzzle[0][0],muzzle[1][0],muzzle[2][0]);
    if(forward.LengthSqr()<1e-8f) return false;
    effect.origin=PortalPose::Position(muzzle);
    effect.angles=PortalPose::Angles(HandPose::RigidOrientation(muzzle));
    return true;
}

// Source's effect replication rounded a measured 15.60/41.64-degree launch to
// 17.01/42.52 degrees. Retain shot-time precision for local loopback effects.
// Match color AND both positions; never aim an old projectile using a new pose.
// The caller serializes access between server emission and client callbacks.
struct LaunchHistory {
    struct Entry {
        Vector origin,target;
        QAngle angles;
        uint64_t time=0;
        unsigned color=0;
        bool valid=false;
    } entries[16];
    size_t next=0;
    void Record(const Data& effect,uint64_t now) {
        if(Color(effect)<1 || Color(effect)>2) return;
        const float values[]={effect.origin.x,effect.origin.y,effect.origin.z,
            effect.start.x,effect.start.y,effect.start.z,effect.angles.x,effect.angles.y,effect.angles.z};
        for(float value:values) if(!std::isfinite(value))return;
        auto& e=entries[next++%16];
        e.origin=effect.origin;e.target=effect.start;e.angles=effect.angles;
        e.time=now;e.color=Color(effect);e.valid=true;
    }
    bool Restore(Data& effect,uint64_t now) {
        Entry* match=nullptr;
        float best=2.f;
        for(auto& e:entries) {
            if(e.valid && (now<e.time || now-e.time>2000))e.valid=false;
            if(!e.valid || e.color!=Color(effect))continue;
            const float originError=(e.origin-effect.origin).LengthSqr();
            const float targetError=(e.target-effect.start).LengthSqr();
            if(!std::isfinite(originError) || !std::isfinite(targetError)
                || originError>1.f || targetError>1.f)continue;
            const float score=originError+targetError;
            if(!match || score<best || (score==best && e.time<match->time)) {
                match=&e;best=score;
            }
        }
        if(!match)return false;
        effect.origin=match->origin;effect.angles=match->angles;
        match->valid=false;
        return true;
    }
};
}
