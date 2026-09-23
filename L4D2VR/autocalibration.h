#pragma once
#include "portalpose.h"
#include <algorithm>

namespace AutoCalibration {
inline Vector TransformPoint(const matrix3x4_t& frame,const Vector& point) {
    return {frame[0][0]*point.x+frame[0][1]*point.y+frame[0][2]*point.z+frame[0][3],
        frame[1][0]*point.x+frame[1][1]*point.y+frame[1][2]*point.z+frame[1][3],
        frame[2][0]*point.x+frame[2][1]*point.y+frame[2][2]*point.z+frame[2][3]};
}
// Convert a transform (not a device orientation) from OpenVR to Source axes.
inline matrix3x4_t SourceSpace(const float (&m)[3][4]) {
    const int axis[]={2,0,1}; const float sign[]={-1,-1,1};
    matrix3x4_t out;
    for(int r=0;r<3;++r) {
        for(int c=0;c<3;++c) out[r][c]=sign[r]*sign[c]*m[axis[r]][axis[c]];
        out[r][3]=sign[r]*m[axis[r]][3];
    }
    return out;
}
struct Origin {
    matrix3x4_t previous{};
    bool ready=false;
    bool Update(const matrix3x4_t& frame,bool enabled,Vector& center,float& yaw) {
        for(int r=0;r<3;++r) for(int c=0;c<4;++c)
            if(!std::isfinite(frame[r][c])) return false;
        for(int c=0;c<3;++c) {
            const Vector axis(frame[0][c],frame[1][c],frame[2][c]);
            if(fabsf(axis.LengthSqr()-1)>1e-3f) return false;
            for(int other=0;other<c;++other)
                if(fabsf(axis.x*frame[0][other]+axis.y*frame[1][other]+axis.z*frame[2][other])>1e-3f) return false;
        }
        const auto delta=ready ? HandPose::Concat(frame,HandPose::InverseRigid(previous)) : PortalPose::Frame({0,0,0},{0,0,0});
        // Reflections and tilted tracking spaces cannot be represented by the
        // game's yaw-only room transform. Never accept them as a new baseline.
        const float determinant=frame[0][0]*(frame[1][1]*frame[2][2]-frame[1][2]*frame[2][1])
            -frame[0][1]*(frame[1][0]*frame[2][2]-frame[1][2]*frame[2][0])
            +frame[0][2]*(frame[1][0]*frame[2][1]-frame[1][1]*frame[2][0]);
        if(determinant<.999f || frame[2][2]<.9999f) return false;
        const bool apply=ready && enabled;
        if(!apply) { previous=frame;ready=true;return false; }
        // Calibrated tracking origins are upright yaw/translation transforms.
        if(!apply || delta[2][2]<.9999f) return false;
        const float turn=RAD2DEG(atan2f(delta[1][0],delta[0][0]));
        const auto translation=PortalPose::Position(delta);
        if(fabsf(turn)<.001f && translation.LengthSqr()<1e-8f) return false;
        // Keep sub-threshold changes in the baseline until they accumulate;
        // otherwise slow origin drift is silently discarded every frame.
        previous=frame;
        center=TransformPoint(delta,center);
        yaw=std::remainder(yaw-turn,360.0f);
        return true;
    }
};
struct Stability {
    Vector anchor{}, mean{}, previous{};
    QAngle angles{};
    float elapsed=0;
    bool ready=false;
    void Reset() { ready=false;elapsed=0; }
    bool Step(float dt,const Vector& position,const QAngle& orientation,bool valid) {
        if(!valid || !std::isfinite(position.LengthSqr()) || !std::isfinite(orientation.x)
            || !std::isfinite(orientation.y) || !std::isfinite(orientation.z)
            || dt<=0 || dt>.1f || !std::isfinite(dt)) { Reset();return false; }
        const bool moved=!ready || (position-anchor).LengthSqr()>.012f*.012f
            || (position-previous).LengthSqr()>(.04f*dt+.002f)*(.04f*dt+.002f)
            || fabsf(std::remainder(orientation.x-angles.x,360.f))>2.f
            || fabsf(std::remainder(orientation.y-angles.y,360.f))>2.f
            || fabsf(std::remainder(orientation.z-angles.z,360.f))>2.f;
        if(moved) { anchor=mean=position;angles=orientation;elapsed=0;ready=true; }
        previous=position;
        elapsed+=dt;
        mean+=(position-mean)*(1.f-expf(-dt/.15f));
        return elapsed>=.75f;
    }
};
// A blocked physical body with a clear route at the visible head is evidence
// of a roomscale mismatch. An ordinary wall in front of both is not.
inline bool NeedsBodyAlignment(float bodyFraction,bool bodySolid,float headFraction,bool headSolid) {
    return std::isfinite(bodyFraction) && std::isfinite(headFraction)
        && !bodySolid && !headSolid && bodyFraction>=0 && bodyFraction<.5f && headFraction>.95f;
}
struct Drift {
    float dwell=0;
    float speed=0;
    bool active=false;
    void Reset() { dwell=0;speed=0;active=false; }
    // Require stick movement against a stationary player, a still upright
    // headset, and a large horizontal offset. No height/yaw guessing here.
    Vector Step(float dt,const Vector& offset,bool eligible) {
        if(!std::isfinite(dt) || dt<=0 || dt>.1f || !eligible
            || !std::isfinite(offset.LengthSqr()) || fabsf(offset.z)>.12f) {
            Reset();return {0,0,0};
        }
        const float distance=sqrtf(offset.x*offset.x+offset.y*offset.y);
        if(distance<(active ? .015f : .25f)) { Reset();return {0,0,0}; }
        dwell+=dt;
        if(dwell<1.0f) return {0,0,0};
        active=true;
        // Ease into the correction, slow near the target, and never overshoot.
        speed=std::min(speed+.25f*dt,std::min(.12f,distance*2.f));
        const float step=std::min(distance,speed*dt);
        return {offset.x*step/distance,offset.y*step/distance,0};
    }
};
}
