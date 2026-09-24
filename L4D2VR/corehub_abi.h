#pragma once
#include <cstddef>
#include <cstdint>
#include <cmath>
#include <algorithm>

// Corehub build 3916, x86. These layouts are deliberately independent of the
// Portal 1 SDK: Corehub RenderView takes TWO views and its viewport has four ints.
namespace Corehub {
struct Vec3 { float x=0, y=0, z=0; };
inline Vec3 operator+(Vec3 a,Vec3 b) { return {a.x+b.x,a.y+b.y,a.z+b.z}; }
inline Vec3 operator-(Vec3 a,Vec3 b) { return {a.x-b.x,a.y-b.y,a.z-b.z}; }
inline Vec3 operator*(Vec3 a,float s) { return {a.x*s,a.y*s,a.z*s}; }
inline float Wrap(float a) { return std::remainder(a,360.0f); }
inline Vec3 RotateYaw(Vec3 a,float degrees) {
 const float r=degrees*0.0174532925199433f,c=std::cos(r),s=std::sin(r);
 return {a.x*c-a.y*s,a.x*s+a.y*c,a.z};
}
struct View {
 int x,y,width,height;
 bool ortho; std::uint8_t orthoPadding[3];
 float orthoLeft,orthoTop,orthoRight,orthoBottom;
 float fov,viewmodelFov;
 Vec3 origin,angles;
 float nearZ,farZ,viewmodelNearZ,viewmodelFarZ,aspect;
 std::uint8_t remaining[104];
};
static_assert(sizeof(View)==192);
static_assert(offsetof(View,fov)==36 && offsetof(View,origin)==44);
static_assert(offsetof(View,angles)==56 && offsetof(View,aspect)==84);
struct EyeViews { View world,overlay; };
inline EyeViews PrepareEyeViews(const View& world,const View& overlay,int width,int height,
 float fov,float aspect,Vec3 position,Vec3 angles) {
 EyeViews result{world,overlay};
 for(View* view:{&result.world,&result.overlay}) {
  view->x=view->y=0;view->width=width;view->height=height;view->aspect=aspect;
 }
 result.world.fov=result.world.viewmodelFov=fov;
 result.world.origin=position;result.world.angles=angles;
 result.world.nearZ=result.world.viewmodelNearZ=1.0f;
 result.world.remaining[100]&=static_cast<std::uint8_t>(~4u);
 return result;
}
// Only the verified shared prefix. Corehub appends portal-use entity handles;
// never copy or zero the whole command using Portal 1's sizeof(CUserCmd).
struct Command {
 std::uint32_t vtable;
 int number,tick;
 Vec3 angles;
 float forward,side,up;
 int buttons;
};
static_assert(sizeof(Command)==40 && offsetof(Command,buttons)==36);
constexpr float UnitsPerMetre=39.37007874f;
namespace Slot {
 constexpr int EngineCommand=7,LocalPlayer=12,GetAngles=19,SetAngles=20,InGame=26;
 constexpr int BeginTargets=82,EndTargets=83,CreateTarget=85,RenderContext=98;
 constexpr int BeginRender=2,EndRender=3,Release=1,GetTarget=7;
 constexpr int PushTarget=106,PopTarget=108; // Corehub; Portal 1 uses 107/109.
}
}
