#pragma once
struct IDirect3DSurface9;
struct IDirect3DDevice9;
namespace CorehubVR {
// True consumes the frame for Corehub, including an unsupported build or a
// disconnected HMD. It must never fall through to Portal 1 hooks in that case.
bool HandleFrame();
void BeforePresent(IDirect3DDevice9* device);
void RenderTargetBound(IDirect3DSurface9* surface);
}
