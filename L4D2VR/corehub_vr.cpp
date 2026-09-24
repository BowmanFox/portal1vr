#include "corehub_vr.h"
#include "corehub_abi.h"
#include <Windows.h>
#include <bcrypt.h>
#include <d3d9.h>
#include <d3d11.h>
#include <wrl/client.h>
#include <string>
#include <fstream>
#include <array>
#include <vector>
#include <cstring>
#include "openvr.h"
#include "MinHook.h"
#include "vr.h"
#include "debuglog.h"
#include "../dxvk/src/d3d9/d3d9_vr.h"
#pragma comment(lib,"bcrypt.lib")
#pragma comment(lib,"d3d11.lib")
#pragma comment(lib,"dxgi.lib")

namespace CorehubVR {
namespace {
using namespace Corehub;
using Microsoft::WRL::ComPtr;
template<class R,class... A> R Call(void* p,int slot,A... a) {
 return reinterpret_cast<R(__thiscall*)(void*,A...)>((*static_cast<void***>(p))[slot])(p,a...);
}
struct Fingerprint { const char* module; unsigned timestamp,size; const char* sha; };
constexpr Fingerprint builds[]={
 {"client.dll",0x4a6f77ae,0x64f000,"329b788ff0c5e744403086eea7e455c2c113344371f072a0829dbd4f731a3d4b"},
 {"engine.dll",0x4a6f766d,0x6a3000,"f2b2b02abdf9504ec77708e0205a02f33e7ef8e3e6fd2e81423adfa4533ad228"},
 {"server.dll",0x4a6f96c4,0x72c000,"1dc9c9ac0e12511b21beac4c183462df53b504920421e52e66e96e926659c948"},
 {"materialsystem.dll",0x4a6f7794,0x135000,"a7d83e3549a93f8918b4a92d41dc6124f018b2785a8a70f9c2ed12fcd66ae276"},
 {"shaderapidx9.dll",0x4a6a316e,0x1a6000,"7b86f32602fe813b0ee03debbc45c4b184ed01c92f2e2b5667f4ca9d76f67ffc"}
};
std::string DiskHash(HMODULE module) {
 wchar_t path[32768]{}; if(!GetModuleFileNameW(module,path,32768))return {};
 std::ifstream file(path,std::ios::binary); if(!file)return {};
 BCRYPT_ALG_HANDLE algorithm=nullptr; BCRYPT_HASH_HANDLE hash=nullptr;
 if(BCryptOpenAlgorithmProvider(&algorithm,BCRYPT_SHA256_ALGORITHM,nullptr,0)<0)return {};
 DWORD count=0,objectSize=0;
 BCryptGetProperty(algorithm,BCRYPT_OBJECT_LENGTH,reinterpret_cast<PUCHAR>(&objectSize),sizeof(objectSize),&count,0);
 std::vector<UCHAR> object(objectSize); std::array<UCHAR,32> digest{}; bool ok=true;
 if(BCryptCreateHash(algorithm,&hash,object.data(),objectSize,nullptr,0,0)<0)ok=false;
 std::array<char,65536> buffer{};
 while(ok && file) {
  file.read(buffer.data(),buffer.size());
  if(file.gcount() && BCryptHashData(hash,reinterpret_cast<PUCHAR>(buffer.data()),static_cast<ULONG>(file.gcount()),0)<0)ok=false;
 }
 if(ok && BCryptFinishHash(hash,digest.data(),digest.size(),0)<0)ok=false;
 if(hash)BCryptDestroyHash(hash); BCryptCloseAlgorithmProvider(algorithm,0);
 if(!ok)return {};
 std::string result; for(auto b:digest){result+="0123456789abcdef"[b>>4];result+="0123456789abcdef"[b&15];} return result;
}
IMAGE_NT_HEADERS* Header(HMODULE m) {
 auto* p=reinterpret_cast<unsigned char*>(m); auto* dos=reinterpret_cast<IMAGE_DOS_HEADER*>(p);
 if(!m || dos->e_magic!=IMAGE_DOS_SIGNATURE)return nullptr;
 return reinterpret_cast<IMAGE_NT_HEADERS*>(p+dos->e_lfanew);
}
void* Address(const char* module,unsigned rva) { return reinterpret_cast<unsigned char*>(GetModuleHandleA(module))+rva; }
bool Verified() {
 for(const auto& b:builds) {
  HMODULE m=GetModuleHandleA(b.module);auto* h=Header(m);
  if(!h || h->Signature!=IMAGE_NT_SIGNATURE || h->FileHeader.Machine!=IMAGE_FILE_MACHINE_I386 ||
     h->FileHeader.TimeDateStamp!=b.timestamp || h->OptionalHeader.SizeOfImage!=b.size || DiskHash(m)!=b.sha) {
   PortalVrLog("Corehub: unsupported %s; all Corehub hooks disabled",b.module);return false;
  }
 }
 PortalVrLog("Corehub: all five native build 3916 DLL fingerprints verified");return true;
}
struct Pose { Vec3 position,angles; bool valid=false; };
Pose Convert(const vr::TrackedDevicePose_t& p) {
 Pose out;out.valid=p.bPoseIsValid && p.bDeviceIsConnected;
 if(!out.valid)return out;
 const auto& m=p.mDeviceToAbsoluteTracking.m;
 out.position={-m[2][3],-m[0][3],m[1][3]};
 constexpr float deg=57.2957795131f;
 out.angles={std::asin(std::clamp(m[1][2],-1.0f,1.0f))*deg,std::atan2(m[0][2],m[2][2])*deg,std::atan2(-m[1][0],m[1][1])*deg};
 return out;
}
struct State {
 vr::IVRSystem* system=nullptr;vr::IVRInput* input=nullptr;
 void* engine=nullptr;void* materials=nullptr;
 unsigned width=0,height=0;float fov=90,aspect=1,yaw=0;
 bool installed=false,calibrated=false,rendered=false,enabled=true,inGame=false,turnHeld=false,ownAngles=false;
 bool insideRender=false,insideMove=false;unsigned long retry=0;unsigned long long frames=0;
 Vec3 trackingOrigin,nativeOrigin;Pose hmd,left,right;
 std::array<vr::TrackedDevicePose_t,vr::k_unMaxTrackedDeviceCount> poses{};
 std::array<void*,2> textures{};std::array<IDirect3DSurface9*,2> surfaces{};
 // Engine targets may be multisampled or reused later in the frame. Only
 // dedicated, explicitly resolved single-sample textures reach the compositor.
 std::array<IDirect3DSurface9*,2> submitted{};
 std::array<SharedTextureHolder,2> shared;SharedTextureHolder backbuffer;
 bool submissionReady=false;
 std::array<bool,2> resolved{};
 bool directX=true;
 ComPtr<ID3D11Device> submitDevice;
 ComPtr<ID3D11DeviceContext> submitContext;
 std::array<ComPtr<ID3D11Texture2D>,2> directEyes;
 std::array<ComPtr<IDirect3DSurface9>,2> readback;
 std::array<vr::VRTextureBounds_t,2> bounds{};
 int bindingEye=-1;void* activeTarget=nullptr;
 vr::VROverlayHandle_t menu=vr::k_ulOverlayHandleInvalid;
 vr::VRActionSetHandle_t mainSet=0,baseSet=0;
 vr::VRActionHandle_t walk=0,turn=0,reset=0,activate=0,leftPose=0,rightPose=0,pause=0;
 std::array<vr::VRActionHandle_t,6> buttons{};
 std::array<bool,6> pressed{};
 Vec3 walkAxis;bool snapReady=true;
} s;
using RenderFn=void(__thiscall*)(void*,View&,View&,int,int);
using MoveFn=bool(__thiscall*)(void*,float,Command*);
using AnglesFn=void(__thiscall*)(void*,Vec3*);
using AnimUpdateFn=void(__thiscall*)(void*,float,float);
AnimUpdateFn originalAnimUpdate=nullptr;
using ViewmodelFn=void(__thiscall*)(void*,Vec3&,Vec3&);
ViewmodelFn originalViewmodel=nullptr;
using PushViewFn=void(__thiscall*)(void*,View&,int,void*,void*);
using PushViewDepthFn=void(__thiscall*)(void*,View&,int,void*,void*,void*);
PushViewFn originalPushView=nullptr;PushViewDepthFn originalPushViewDepth=nullptr;
PushViewFn originalPush2D=nullptr;
using ShaderTargetFn=void(__thiscall*)(void*,int,int,int);
ShaderTargetFn originalShaderTarget=nullptr;
void __fastcall ShaderTarget(void* self,void*,int index,int color,int depth) {
 // This build changes the PRIMARY render-target flag and size even when it
 // unbinds MRT slots 1..3. A subsequent SetViewports then clamps the eye to
 // desktop dimensions. Only RT0 owns those primary-target bookkeeping fields.
 auto* bytes=static_cast<unsigned char*>(self);
 const auto primaryFlag=bytes[0x2ae4]&8;
 const auto width=*reinterpret_cast<unsigned*>(bytes+0x2ae8);
 const auto height=*reinterpret_cast<unsigned*>(bytes+0x2aec);
 originalShaderTarget(self,index,color,depth);
 if(s.activeTarget && index>0) {
  bytes[0x2ae4]=(bytes[0x2ae4]&~8u)|primaryFlag;
  *reinterpret_cast<unsigned*>(bytes+0x2ae8)=width;
  *reinterpret_cast<unsigned*>(bytes+0x2aec)=height;
 }
}
RenderFn originalRender=nullptr;MoveFn originalMove=nullptr;AnglesFn originalAngles=nullptr;
Vec3 HeadAngles(){auto a=s.hmd.angles;a.y=Wrap(a.y+s.yaw);return a;}
Vec3 HandAngles(){auto a=s.right.valid?s.right.angles:s.hmd.angles;a.y=Wrap(a.y+s.yaw);return a;}
Vec3 WorldPosition(Vec3 local){return s.nativeOrigin+RotateYaw(local-s.trackingOrigin,s.yaw)*UnitsPerMetre;}
void __fastcall ViewmodelView(void* self,void*,Vec3& origin,Vec3& angles) {
 auto local=reinterpret_cast<void*(__cdecl*)(int)>(Address("client.dll",0x44d30))(-1);
 if(s.enabled && s.calibrated && s.right.valid && s.inGame && self==local) {
  auto hand=WorldPosition(s.right.position),aim=HandAngles();
  originalViewmodel(self,hand,aim);return;
 }
 originalViewmodel(self,origin,angles);
}
void __fastcall UpdatePlayerAnimation(void* self,void*,float yaw,float pitch) {
 // Command angles still aim the portal gun. Feed headset angles separately
 // to the local avatar so moving the controller does not rock its head.
 auto local=reinterpret_cast<void*(__cdecl*)(int)>(Address("client.dll",0x44d30))(-1);
 if(s.enabled && s.calibrated && s.hmd.valid && s.inGame && local &&
    *reinterpret_cast<void**>(static_cast<unsigned char*>(self)+224)==local) {
  const auto head=HeadAngles();yaw=head.y;pitch=head.x;
  static bool first=true;if(first){first=false;PortalVrLog("Corehub: local avatar head animation follows HMD");}
 }
 originalAnimUpdate(self,yaw,pitch);
}
void __fastcall PushView(void* self,void*,View& view,int flags,void* texture,void* frustum) {
 if(s.activeTarget && s.frames<2)PortalVrLog("Corehub: native 3D view rect=%d,%d %dx%d target=%p redirected=%p",view.x,view.y,view.width,view.height,texture,s.activeTarget);
 // Corehub explicitly pushes a null desktop target inside RenderView.
 // Redirect default-target views while retaining shadow/reflection targets.
 originalPushView(self,view,flags,texture?texture:s.activeTarget,frustum);

}
void __fastcall PushViewDepth(void* self,void*,View& view,int flags,void* texture,void* frustum,void* depth) {
 originalPushViewDepth(self,view,flags,texture?texture:s.activeTarget,frustum,depth);
}
void __fastcall Push2D(void* self,void*,View& view,int flags,void* texture,void* frustum) {
 // Corehub creates an additional desktop-sized 2D view internally before
 // the world pass. Size this stack entry for the eye as well as the public HUD.
 if(s.activeTarget && (!texture || texture==s.activeTarget)) {
  View eye=view;eye.x=eye.y=0;eye.width=s.width;eye.height=s.height;eye.aspect=s.aspect;
  originalPush2D(self,eye,flags,s.activeTarget,frustum);
 } else originalPush2D(self,view,flags,texture,frustum);
}
void CommandText(const char* text){Call<void>(s.engine,Slot::EngineCommand,text);}
bool Digital(vr::VRActionHandle_t action,bool edge=false) {
 vr::InputDigitalActionData_t d{};
 return action && s.input->GetDigitalActionData(action,&d,sizeof(d),vr::k_ulInvalidInputValueHandle)==vr::VRInputError_None && d.bActive && d.bState && (!edge || d.bChanged);
}
void Recenter() {
 if(!s.hmd.valid)return;
 Vec3 angles{};Call<void>(s.engine,Slot::GetAngles,&angles);
 s.yaw=Wrap(angles.y-s.hmd.angles.y);s.trackingOrigin=s.hmd.position;s.calibrated=true;
 PortalVrLog("Corehub: tracking recentered yaw=%.2f height=%.3fm",s.yaw,s.trackingOrigin.z);
}
void __fastcall SetAngles(void* self,void*,Vec3* value) {
 // Portal transitions rotate the engine view. Retain that rotation in the
 // tracking frame without interpreting our own HMD update as a teleport.
 if(s.calibrated && s.enabled && !s.ownAngles && !s.insideMove && value) {
  Vec3 previous{};Call<void>(s.engine,Slot::GetAngles,&previous);
  s.yaw=Wrap(s.yaw+Wrap(value->y-previous.y));
 }
 originalAngles(self,value);
}
bool __fastcall CreateMove(void* self,void*,float sample,Command* cmd) {
 s.insideMove=true;const bool result=originalMove(self,sample,cmd);s.insideMove=false;
 if(!cmd || !cmd->number || !s.enabled || !s.hmd.valid || !s.calibrated || !s.inGame)return result;
 const Vec3 head=HeadAngles(),aim=HandAngles();
 // Keep locomotion aligned with the HMD even though the command's aim follows
 // the right controller. Preserve ordinary keyboard movement when no stick is used.
 const float f=cmd->forward+s.walkAxis.y*250.0f,side=cmd->side+s.walkAxis.x*250.0f;
 const float radians=Wrap(head.y-aim.y)*0.0174532925199433f;
 cmd->forward=std::cos(radians)*f+std::sin(radians)*side;
 cmd->side=-std::sin(radians)*f+std::cos(radians)*side;
 cmd->angles=aim;
 constexpr int masks[]={1,2048,2,32,4,8192};
 for(int i=0;i<6;++i)if(s.pressed[i])cmd->buttons|=masks[i];
 auto camera=head;s.ownAngles=true;originalAngles(s.engine,&camera);s.ownAngles=false;
 return false;
}
bool CreateTargets() {
 if(s.textures[0] && s.textures[1])return true;
 // IMAGE_FORMAT_BGRA8888, the native D3D9 render-target format. Corehub's
 // material-system slot 32 is not Portal 1's GetBackBufferFormat.
 constexpr int format=12;
 // Native Begin/End refuses late allocations after GameInit. Temporarily
 // reopen the verified build's allocation gate; restore it before any draw.
 auto* gameStarted=static_cast<unsigned char*>(s.materials)+0x2a88;
 const auto savedGameStarted=*gameStarted;*gameStarted=0;
 Call<void>(s.materials,Slot::BeginTargets);
 for(int eye=0;eye<2;++eye) {
  if(s.textures[eye])continue;
  // CreateNamedRenderTargetTextureEx: literal dimensions, separate depth,
  // no mipmaps. Corehub's native material system owns the ITexture lifetime.
  s.textures[eye]=Call<void*>(s.materials,Slot::CreateTarget,eye?"_rt_CorehubVR_Right":"_rt_CorehubVR_Left",s.width,s.height,8,format,1,0x100u,0u);
 }
 Call<void>(s.materials,Slot::EndTargets);
 *gameStarted=savedGameStarted;
 const bool ok=s.textures[0] && s.textures[1];
 PortalVrLog("Corehub: eye targets %ux%u ready=%d left=%p right=%p",s.width,s.height,ok,s.textures[0],s.textures[1]);return ok;
}
Vec3 EyePosition(int eye) {
 const auto e=s.system->GetEyeToHeadTransform(static_cast<vr::EVREye>(eye));
 const auto& h=s.poses[vr::k_unTrackedDeviceIndex_Hmd].mDeviceToAbsoluteTracking.m;
 float p[3]{};for(int row=0;row<3;++row)p[row]=h[row][3]+h[row][0]*e.m[0][3]+h[row][1]*e.m[1][3]+h[row][2]*e.m[2][3];
 return WorldPosition({-p[2],-p[0],p[1]});
}
bool ResolveEye(int eye);
void __fastcall RenderView(void* self,void*,View& main,View& hud,int flags,int draw) {
 static bool first=true;if(first){first=false;PortalVrLog("Corehub: RenderView self=%p view=%p hud=%p rect=%d,%d %dx%d fov=%.1f flags=%x draw=%x original=%p",self,&main,&hud,main.x,main.y,main.width,main.height,main.fov,flags,draw,originalRender);}
 if(s.insideRender || !s.enabled || !s.hmd.valid || !Call<bool>(s.engine,Slot::InGame)) {originalRender(self,main,hud,flags,draw);return;}
 s.nativeOrigin=main.origin;s.inGame=true;if(!s.calibrated)Recenter();
 if(!s.textures[0] || !s.textures[1]){originalRender(self,main,hud,flags,draw);return;}
 const View desktopView=main,desktopHud=hud;
 s.insideRender=true;s.resolved.fill(false);
 void* context=Call<void*>(s.materials,Slot::RenderContext);
 if(!context){s.insideRender=false;originalRender(self,main,hud,flags,draw);return;}
 Call<void>(context,Slot::BeginRender);
 for(int eye=0;eye<2;++eye) {
  auto eyeViews=PrepareEyeViews(desktopView,desktopHud,s.width,s.height,s.fov,s.aspect,EyePosition(eye),HeadAngles());
  s.bindingEye=eye;s.activeTarget=s.textures[eye];Call<void>(context,Slot::PushTarget,s.activeTarget);
  originalRender(self,eyeViews.world,eyeViews.overlay,flags|3,draw&~2);
  s.bindingEye=-1;
  // Preserve this eye BEFORE any later engine pass can clear/reuse its target.
  s.resolved[eye]=ResolveEye(eye);
  Call<void>(context,Slot::PopTarget);s.activeTarget=nullptr;
 }
 Call<void>(context,Slot::EndRender);Call<void>(context,Slot::Release);
 s.rendered=s.surfaces[0] && s.surfaces[1] && s.surfaces[0]!=s.surfaces[1];s.insideRender=false;
 // Preserve the regular desktop/menu rendering and native render bookkeeping.
 View desktop=desktopView,desktopOverlay=desktopHud;
 originalRender(self,desktop,desktopOverlay,flags,draw);
 if(++s.frames==1 || s.frames%600==0)PortalVrLog("Corehub: stereo frame=%llu native=(%.1f %.1f %.1f) HMD=(%.1f %.1f %.1f)",s.frames,main.origin.x,main.origin.y,main.origin.z,HeadAngles().x,HeadAngles().y,HeadAngles().z);
}
struct Hook { const char* module;unsigned rva;void* detour;void** original; };
bool InstallHooks() {
 Hook hooks[]={
  {"client.dll",0x181120,reinterpret_cast<void*>(&RenderView),reinterpret_cast<void**>(&originalRender)},
  {"client.dll",0x95940,reinterpret_cast<void*>(&CreateMove),reinterpret_cast<void**>(&originalMove)},
  {"client.dll",0x1e9aa0,reinterpret_cast<void*>(&UpdatePlayerAnimation),reinterpret_cast<void**>(&originalAnimUpdate)},
  {"client.dll",0x1d6f00,reinterpret_cast<void*>(&ViewmodelView),reinterpret_cast<void**>(&originalViewmodel)},
  {"engine.dll",0xd5fc0,reinterpret_cast<void*>(&SetAngles),reinterpret_cast<void**>(&originalAngles)},
  {"engine.dll",0x175da0,reinterpret_cast<void*>(&PushView),reinterpret_cast<void**>(&originalPushView)},
  {"engine.dll",0x175dd0,reinterpret_cast<void*>(&Push2D),reinterpret_cast<void**>(&originalPush2D)},
  {"shaderapidx9.dll",0x21070,reinterpret_cast<void*>(&ShaderTarget),reinterpret_cast<void**>(&originalShaderTarget)},
  {"engine.dll",0x175e60,reinterpret_cast<void*>(&PushViewDepth),reinterpret_cast<void**>(&originalPushViewDepth)}
 };
 auto init=MH_Initialize();if(init!=MH_OK && init!=MH_ERROR_ALREADY_INITIALIZED)return false;
 std::vector<void*> created;
 for(const auto& h:hooks) {
  void* target=Address(h.module,h.rva);const auto result=MH_CreateHook(target,h.detour,h.original);
  if(result!=MH_OK){PortalVrLog("Corehub: hook %s+%x failed: %s",h.module,h.rva,MH_StatusToString(result));for(auto p:created)MH_RemoveHook(p);return false;}
  created.push_back(target);
 }
 for(auto target:created)if(MH_EnableHook(target)!=MH_OK){for(auto p:created){MH_DisableHook(p);MH_RemoveHook(p);}return false;}
 PortalVrLog("Corehub: camera, input and portal view rotation hooks installed");return true;
}
bool Start() {
 vr::EVRInitError error=vr::VRInitError_None;s.system=vr::VR_Init(&error,vr::VRApplication_Scene);
 if(error!=vr::VRInitError_None){s.system=nullptr;PortalVrLog("Corehub: OpenVR unavailable: %s (retry in 5s)",vr::VR_GetVRInitErrorAsEnglishDescription(error));return false;}
 if(!vr::VRCompositor() || !(s.input=vr::VRInput())){vr::VR_Shutdown();s.system=nullptr;return false;}
 vr::VRCompositor()->SetTrackingSpace(vr::TrackingUniverseStanding);
 s.directX=strstr(GetCommandLineA(),"-corehubvr-vulkan")==nullptr;
 if(s.directX && !s.submitDevice) {
  // Match the headset's LUID rather than the legacy adapter index: on hybrid
  // systems DXGI and Vulkan enumerate the Intel/NVIDIA adapters differently.
  uint64_t headsetLuid=0;s.system->GetOutputDevice(&headsetLuid,vr::TextureType_DirectX);
  ComPtr<IDXGIFactory1> factory;ComPtr<IDXGIAdapter1> adapter;
  HRESULT hr=CreateDXGIFactory1(IID_PPV_ARGS(&factory));
  if(SUCCEEDED(hr))for(UINT i=0;;++i) {
   ComPtr<IDXGIAdapter1> candidate;if(FAILED(factory->EnumAdapters1(i,&candidate)))break;
   DXGI_ADAPTER_DESC1 desc{};candidate->GetDesc1(&desc);
   uint64_t luid=0;memcpy(&luid,&desc.AdapterLuid,sizeof(luid));
   if(luid==headsetLuid){adapter=candidate;break;}
  }
  if(adapter)hr=D3D11CreateDevice(adapter.Get(),D3D_DRIVER_TYPE_UNKNOWN,nullptr,D3D11_CREATE_DEVICE_BGRA_SUPPORT,nullptr,0,D3D11_SDK_VERSION,&s.submitDevice,nullptr,&s.submitContext);
  else hr=DXGI_ERROR_NOT_FOUND;
  if(FAILED(hr)) {
   PortalVrLog("Corehub: D3D11 compositor device failed hr=%08x LUID=%llu",hr,headsetLuid);
   vr::VR_Shutdown();s.system=nullptr;return false;
  }
  PortalVrLog("Corehub: D3D11 compositor device ready LUID=%llu",headsetLuid);
 }
 s.system->GetRecommendedRenderTargetSize(&s.width,&s.height);
 float raw[2][4]{},tanX=0,tanY=0;
 for(int eye=0;eye<2;++eye) {
  s.system->GetProjectionRaw(static_cast<vr::EVREye>(eye),&raw[eye][0],&raw[eye][1],&raw[eye][2],&raw[eye][3]);
  tanX=std::max({tanX,std::abs(raw[eye][0]),std::abs(raw[eye][1])});tanY=std::max({tanY,std::abs(raw[eye][2]),std::abs(raw[eye][3])});
 }
 if(!s.width || !s.height || tanX<=0 || tanY<=0){vr::VR_Shutdown();s.system=nullptr;return false;}
 s.fov=2*std::atan(tanX)*57.2957795131f;s.aspect=tanX/tanY;
 for(int eye=0;eye<2;++eye)s.bounds[eye]={.5f+.5f*raw[eye][0]/tanX,.5f+.5f*raw[eye][2]/tanY,.5f+.5f*raw[eye][1]/tanX,.5f+.5f*raw[eye][3]/tanY};
 char path[MAX_PATH]{};GetModuleFileNameA(GetModuleHandleA("d3d9.dll"),path,MAX_PATH);
 std::string directory=path;directory.resize(directory.find_last_of("/\\")+1);
 const std::string manifest=directory+"VR\\SteamVRActionManifest\\action_manifest.json";
 const auto manifestError=s.input->SetActionManifestPath(manifest.c_str());
 if(manifestError!=vr::VRInputError_None){PortalVrLog("Corehub: action manifest failed (%d) at %s",manifestError,manifest.c_str());vr::VR_Shutdown();s.system=nullptr;return false;}
 s.input->GetActionSetHandle("/actions/main",&s.mainSet);s.input->GetActionSetHandle("/actions/base",&s.baseSet);
 auto action=[](const char* name,vr::VRActionHandle_t& a){s.input->GetActionHandle(name,&a);};
 const char* names[]={"PrimaryAttack","SecondaryAttack","Jump","Use","Crouch","Reload"};
 for(int i=0;i<6;++i)action((std::string("/actions/main/in/")+names[i]).c_str(),s.buttons[i]);
 action("/actions/main/in/Walk",s.walk);action("/actions/main/in/Turn",s.turn);action("/actions/main/in/ResetPosition",s.reset);action("/actions/main/in/ActivateVR",s.activate);action("/actions/main/in/Pause",s.pause);
 action("/actions/base/in/pose_lefthand",s.leftPose);action("/actions/base/in/pose_righthand",s.rightPose);
 if(auto overlay=vr::VROverlay()) {
  overlay->CreateOverlay("corehub.vr.desktop","Corehub",&s.menu);
  if(s.menu!=vr::k_ulOverlayHandleInvalid){vr::HmdMatrix34_t transform{{{1,0,0,0},{0,1,0,0},{0,0,1,-2}}};overlay->SetOverlayWidthInMeters(s.menu,2.5f);overlay->SetOverlayTransformTrackedDeviceRelative(s.menu,vr::k_unTrackedDeviceIndex_Hmd,&transform);}
 }
 if(!CreateTargets()){PortalVrLog("Corehub: render-target allocation failed; stereo disabled");vr::VR_Shutdown();s.system=nullptr;return false;}
 if(!s.installed && !(s.installed=InstallHooks())){vr::VR_Shutdown();s.system=nullptr;return false;}
 CommandText("mat_queue_mode 0; mat_motion_blur_enabled 0; mat_depth_of_field_enabled 0");
 PortalVrLog("Corehub: OpenVR started, eye target=%ux%u FOV=%.2f aspect=%.3f",s.width,s.height,s.fov,s.aspect);return true;
}
void Update() {
 if(s.submissionReady) {
  // SteamVR requires TRANSFER_SRC_OPTIMAL even when Submit reports success.
  // Finish DXVK work before external queue access, then restore its layout.
  if(!s.directX) {
   g_D3DVR9->TransferSurface(s.submitted[0],FALSE);
   g_D3DVR9->TransferSurface(s.submitted[1],FALSE);
   g_D3DVR9->WaitDeviceIdle();
  }
  const auto a=vr::VRCompositor()->Submit(vr::Eye_Left,&s.shared[0].m_VRTexture,&s.bounds[0]);
  const auto b=vr::VRCompositor()->Submit(vr::Eye_Right,&s.shared[1].m_VRTexture,&s.bounds[1]);
  if(s.frames==1 || s.frames%600==0)PortalVrLog("Corehub: compositor left=%d right=%d",a,b);
  vr::VRCompositor()->PostPresentHandoff();
  if(!s.directX) {
   g_D3DVR9->WaitDeviceIdle();
   g_D3DVR9->RestoreSurface(s.submitted[0]);
   g_D3DVR9->RestoreSurface(s.submitted[1]);
   g_D3DVR9->WaitDeviceIdle();
  }
  if(s.menu!=vr::k_ulOverlayHandleInvalid)vr::VROverlay()->HideOverlay(s.menu);
 } else if(!s.directX && !s.inGame && s.menu!=vr::k_ulOverlayHandleInvalid && SUCCEEDED(g_D3DVR9->GetBackBufferData(&s.backbuffer))) {
  g_D3DVR9->WaitDeviceIdle();vr::VROverlay()->SetOverlayTexture(s.menu,&s.backbuffer.m_VRTexture);vr::VROverlay()->ShowOverlay(s.menu);
 }
 s.rendered=false;s.submissionReady=false;
 const auto poseError=vr::VRCompositor()->WaitGetPoses(s.poses.data(),s.poses.size(),nullptr,0);
 s.hmd=poseError==vr::VRCompositorError_None?Convert(s.poses[0]):Pose{};
 vr::VRActiveActionSet_t sets[2]{};sets[0].ulActionSet=s.mainSet;sets[1].ulActionSet=s.baseSet;
 s.input->UpdateActionState(sets,sizeof(sets[0]),2);
 auto hand=[](vr::VRActionHandle_t action,vr::ETrackedControllerRole role) {
  vr::InputPoseActionData_t pose{};
  if(s.input->GetPoseActionDataForNextFrame(action,vr::TrackingUniverseStanding,&pose,sizeof(pose),vr::k_ulInvalidInputValueHandle)==vr::VRInputError_None && pose.bActive && pose.pose.bPoseIsValid)return Convert(pose.pose);
  const auto index=s.system->GetTrackedDeviceIndexForControllerRole(role);
  return index<s.poses.size()?Convert(s.poses[index]):Pose{};
 };
 s.left=hand(s.leftPose,vr::TrackedControllerRole_LeftHand);s.right=hand(s.rightPose,vr::TrackedControllerRole_RightHand);
 const bool game=Call<bool>(s.engine,Slot::InGame);if(game!=s.inGame){s.calibrated=false;s.inGame=game;}
 if(Digital(s.activate,true)){s.enabled=!s.enabled;s.calibrated=false;}
 if(Digital(s.reset,true))Recenter();
 if(Digital(s.pause,true))CommandText("gameui_activate");
 for(int i=0;i<6;++i)s.pressed[i]=s.hmd.valid && Digital(s.buttons[i]);
 vr::InputAnalogActionData_t walk{},turn{};s.walkAxis={};
 s.input->GetAnalogActionData(s.walk,&walk,sizeof(walk),vr::k_ulInvalidInputValueHandle);
 s.input->GetAnalogActionData(s.turn,&turn,sizeof(turn),vr::k_ulInvalidInputValueHandle);
 if(walk.bActive && s.hmd.valid)s.walkAxis={walk.x,walk.y,0};
 if(!turn.bActive || std::abs(turn.x)<.3f)s.snapReady=true;
 else if(s.snapReady && std::abs(turn.x)>.7f && s.enabled && s.hmd.valid){s.yaw=Wrap(s.yaw-(turn.x>0?30.0f:-30.0f));s.snapReady=false;}
 vr::VREvent_t event{};while(s.system->PollNextEvent(&event,sizeof(event))) {
  if(event.eventType==vr::VREvent_Quit){s.enabled=false;s.hmd.valid=false;s.pressed.fill(false);s.system->AcknowledgeQuit_Exiting();}
 }
}
}
namespace {
HRESULT UploadDirectEye(IDirect3DDevice9* device,int eye,const D3DSURFACE_DESC& desc) {
 if(desc.Format!=D3DFMT_A8R8G8B8 && desc.Format!=D3DFMT_X8R8G8B8)return D3DERR_INVALIDCALL;
 if(s.readback[eye]) {
  D3DSURFACE_DESC old{};s.readback[eye]->GetDesc(&old);
  if(old.Width!=desc.Width || old.Height!=desc.Height || old.Format!=desc.Format){s.readback[eye].Reset();s.directEyes[eye].Reset();}
 }
 HRESULT hr=S_OK;
 if(!s.readback[eye]) {
  hr=device->CreateOffscreenPlainSurface(desc.Width,desc.Height,desc.Format,D3DPOOL_SYSTEMMEM,&s.readback[eye],nullptr);
  if(FAILED(hr))return hr;
 }
 if(!s.directEyes[eye]) {
  D3D11_TEXTURE2D_DESC texture{};texture.Width=desc.Width;texture.Height=desc.Height;
  texture.MipLevels=texture.ArraySize=1;texture.Format=DXGI_FORMAT_B8G8R8A8_UNORM;texture.SampleDesc.Count=1;
  texture.Usage=D3D11_USAGE_DEFAULT;texture.BindFlags=D3D11_BIND_SHADER_RESOURCE|D3D11_BIND_RENDER_TARGET;
  hr=s.submitDevice->CreateTexture2D(&texture,nullptr,&s.directEyes[eye]);if(FAILED(hr))return hr;
 }
 hr=device->GetRenderTargetData(s.submitted[eye],s.readback[eye].Get());if(FAILED(hr))return hr;
 D3DLOCKED_RECT map{};hr=s.readback[eye]->LockRect(&map,nullptr,D3DLOCK_READONLY);if(FAILED(hr))return hr;
 if((s.frames==60 || s.frames%600==0) && strstr(GetCommandLineA(),"-corehubvr-debug-textures")) {
  BITMAPFILEHEADER header{};BITMAPINFOHEADER info{};
  header.bfType=0x4d42;header.bfOffBits=sizeof(header)+sizeof(info);header.bfSize=header.bfOffBits+desc.Width*desc.Height*4;
  info.biSize=sizeof(info);info.biWidth=desc.Width;info.biHeight=-LONG(desc.Height);info.biPlanes=1;info.biBitCount=32;
  FILE* file=nullptr;fopen_s(&file,eye?"corehubvr-right.bmp":"corehubvr-left.bmp","wb");
  if(file){fwrite(&header,sizeof(header),1,file);fwrite(&info,sizeof(info),1,file);for(UINT row=0;row<desc.Height;++row)fwrite(static_cast<char*>(map.pBits)+row*map.Pitch,desc.Width*4,1,file);fclose(file);}
 }
 s.submitContext->UpdateSubresource(s.directEyes[eye].Get(),0,nullptr,map.pBits,map.Pitch,0);
 s.readback[eye]->UnlockRect();
 s.shared[eye].m_VRTexture={s.directEyes[eye].Get(),vr::TextureType_DirectX,vr::ColorSpace_Auto};
 return S_OK;
}
}
namespace {
bool ResolveEye(int eye) {
 if(!s.surfaces[eye])return false;
 IDirect3DDevice9* device=nullptr;
 if(FAILED(s.surfaces[eye]->GetDevice(&device)))return false;
 bool ready=true;
  D3DSURFACE_DESC source{},destination{};
  HRESULT result=s.surfaces[eye]->GetDesc(&source);
  if(s.submitted[eye]) {
   s.submitted[eye]->GetDesc(&destination);
   if(destination.Width!=source.Width || destination.Height!=source.Height || destination.Format!=source.Format) {
    s.submitted[eye]->Release();s.submitted[eye]=nullptr;
   }
  }
  if(SUCCEEDED(result) && !s.submitted[eye]) {
   result=device->CreateRenderTarget(source.Width,source.Height,source.Format,D3DMULTISAMPLE_NONE,0,FALSE,&s.submitted[eye],nullptr);
   PortalVrLog("Corehub: submission target eye=%d sourceMSAA=%u size=%ux%u create=%08x",eye,source.MultiSampleType,source.Width,source.Height,result);
  }
  // D3DTEXF_NONE and equal extents are required for a multisample resolve.
  if(SUCCEEDED(result))result=device->StretchRect(s.surfaces[eye],nullptr,s.submitted[eye],nullptr,D3DTEXF_NONE);
  D3D9_TEXTURE_VR_DESC desc{};
  if(SUCCEEDED(result))result=g_D3DVR9->GetVRDesc(s.submitted[eye],&desc);
  ready=SUCCEEDED(result) && desc.SampleCount==1;
  if(ready) {
   auto& holder=s.shared[eye];memcpy(&holder.m_VulkanData,&desc,sizeof(desc));
   holder.m_VRTexture={&holder.m_VulkanData,vr::TextureType_Vulkan,vr::ColorSpace_Auto};
  }
  if(!ready) {
   static unsigned errors=0;
   if(++errors<=8)PortalVrLog("Corehub: eye resolve failed eye=%d hr=%08x samples=%u; frame not submitted",eye,result,desc.SampleCount);
  }
 device->Release();
 return ready;
}
}
void BeforePresent() {
 s.submissionReady=false;
 if(!s.rendered || !s.resolved[0] || !s.resolved[1])return;
 bool ready=true;
 if(s.directX) {
  IDirect3DDevice9* device=nullptr;if(FAILED(s.submitted[0]->GetDevice(&device)))return;
  for(int eye=0;eye<2 && ready;++eye) {
   D3DSURFACE_DESC desc{};s.submitted[eye]->GetDesc(&desc);
   ready=SUCCEEDED(UploadDirectEye(device,eye,desc));
  }
  if(ready)s.submitContext->Flush();
  device->Release();
 }
 s.submissionReady=ready;
 if(!ready)return;
  // Optional diagnostic mirror shows the exact submitted images, side by side.
  // It does not rely on another engine camera pass to verify eye coverage.
  if(strstr(GetCommandLineA(),"-corehubvr-mirror")) {
   IDirect3DDevice9* device=nullptr;IDirect3DSurface9* back=nullptr;
   if(SUCCEEDED(s.surfaces[0]->GetDevice(&device))) {
    if(SUCCEEDED(device->GetBackBuffer(0,0,D3DBACKBUFFER_TYPE_MONO,&back))) {
     D3DSURFACE_DESC desc{};back->GetDesc(&desc);
     for(int eye=0;eye<2;++eye) {
      RECT rect{static_cast<LONG>(eye*desc.Width/2),0,static_cast<LONG>((eye+1)*desc.Width/2),static_cast<LONG>(desc.Height)};
      device->StretchRect(s.submitted[eye],nullptr,back,&rect,D3DTEXF_LINEAR);
     }
     back->Release();
    }
    device->Release();
   }
  }
}
bool HandleFrame() {
 static int selected=-1;
 if(selected<0) {
  auto* h=Header(GetModuleHandleA("engine.dll"));if(!h)return false;
  const bool requested=strstr(GetCommandLineA(),"-corehubvr")!=nullptr;
  selected=requested || h->FileHeader.TimeDateStamp==builds[1].timestamp ? 1:0;
  if(selected && !Verified())selected=2;
 }
 if(!selected)return false;if(selected==2)return true;
 if(!s.engine)s.engine=Address("engine.dll",0x3c0144);
 if(!s.materials){s.materials=*static_cast<void**>(Address("client.dll",0x5ab558));if(!s.materials)return true;}
 if(!s.system) {const DWORD now=GetTickCount();if(s.retry && now-s.retry<5000)return true;s.retry=now;if(!Start())return true;}
 Update();return true;
}
void RenderTargetBound(IDirect3DSurface9* surface) {
 if(s.bindingEye<0 || !surface || !g_D3DVR9)return;
 D3DSURFACE_DESC level{};if(FAILED(surface->GetDesc(&level)) || !(level.Usage&D3DUSAGE_RENDERTARGET) || level.Width!=s.width || level.Height!=s.height)return;
 const int eye=s.bindingEye;
 D3D9_TEXTURE_VR_DESC desc{};
 if(FAILED(g_D3DVR9->GetVRDesc(surface,&desc)))return;
 if(desc.Width!=s.width || desc.Height!=s.height)return;
 s.bindingEye=-1;
 if(s.surfaces[eye]!=surface) {
  surface->AddRef();if(s.surfaces[eye])s.surfaces[eye]->Release();s.surfaces[eye]=surface;
  PortalVrLog("Corehub: bound eye=%d surface=%p image=%llu %ux%u",eye,surface,desc.Image,desc.Width,desc.Height);
 }
 static_assert(sizeof(desc)==sizeof(vr::VRVulkanTextureData_t));
}
}
