#pragma once

#include <math.h>
#include "game.h"
#include "portal1.h"

class Game;

class CNewParticleEffect
{
public:
	inline void SetControlPoint(int nWhichPoint, const Vector& v) {
		typedef int(__thiscall* tSetControlPoint)(void* thisptr, int nWhichPoint, const Vector& v);
		if (!g_Game)
			return;

		static tSetControlPoint oSetControlPoint = nullptr;
		if (!oSetControlPoint)
			oSetControlPoint = reinterpret_cast<tSetControlPoint>(g_Game->GetModuleOffset("client.dll", Portal1::ClientFunction::kSetControlPoint, false));
		if (!oSetControlPoint)
			return;

		oSetControlPoint(this, nWhichPoint, v);
	};

	inline void StopEmission(bool bInfiniteOnly = false, bool bRemoveAllParticles = false, bool bWakeOnStop = false, bool bPlayEndCap = false) {
		typedef int(__thiscall* tStopEmission)(void* thisptr, bool bInfiniteOnly, bool bRemoveAllParticles, bool bWakeOnStop, bool bPlayEndCap);
		if (!g_Game)
			return;

		static tStopEmission oStopEmission = nullptr;
		if (!oStopEmission)
			oStopEmission = reinterpret_cast<tStopEmission>(g_Game->GetModuleOffset("client.dll", Portal1::ClientFunction::kStopEmission, false));
		if (!oStopEmission)
			return;

		oStopEmission(this, bInfiniteOnly, bRemoveAllParticles, bWakeOnStop, bPlayEndCap);
	};
};

class CPortal_Base2D
{
public:
	inline VMatrix MatrixThisToLinked() {
		return *(VMatrix*)((uintptr_t)this + 0x4C4);
	};
};
