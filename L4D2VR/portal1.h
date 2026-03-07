#pragma once

#include <cstddef>
#include <cstdint>

namespace Portal1
{
namespace Interfaces
{
inline constexpr const char *kClientEntityList = "VClientEntityList003";
inline constexpr const char *kEngineTrace = "EngineTraceClient003";
inline constexpr const char *kEngineClient = "VEngineClient014";
inline constexpr const char *kEngineRenderView = "VEngineRenderView014";
inline constexpr const char *kMaterialSystem = "VMaterialSystem080";
inline constexpr const char *kModelInfo = "VModelInfoClient006";
inline constexpr const char *kModelRender = "VEngineModel016";
inline constexpr const char *kVguiInput = "VGUI_InputInternal001";
inline constexpr const char *kVguiSurface = "VGUI_Surface030";
}

namespace ClientGlobal
{
// Resolved from the Portal 1 client.dll decompile.
inline constexpr uintptr_t kViewRender = 0x50EB98;
inline constexpr uintptr_t kClientModePortalNormal = 0x51ACF0;
}

namespace VTableIndex
{
inline constexpr size_t kViewRender_RenderView = 6;
inline constexpr size_t kClientMode_CreateMove = 22;
inline constexpr size_t kClientMode_GetViewModelFOV = 33;
}
}
