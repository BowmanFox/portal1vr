#pragma once

#include <math.h>
#include "game.h"
#include "offsets.h"

class Game;

class CNewParticleEffect
{
public:
	inline void SetControlPoint(int nWhichPoint, const Vector& v) {
		typedef int(__thiscall* tSetControlPoint)(void* thisptr, int nWhichPoint, const Vector& v);
		tSetControlPoint oSetControlPoint = (tSetControlPoint)(g_Game->m_Offsets->SetControlPoint.address);
		if (!oSetControlPoint)
			return;

		oSetControlPoint(this, nWhichPoint, v);
	};

	inline void StopEmission(bool bInfiniteOnly = false, bool bRemoveAllParticles = false, bool bWakeOnStop = false, bool bPlayEndCap = false) {
		typedef int(__thiscall* tStopEmission)(void* thisptr, bool bInfiniteOnly, bool bRemoveAllParticles, bool bWakeOnStop, bool bPlayEndCap);
		tStopEmission oStopEmission = (tStopEmission)(g_Game->m_Offsets->StopEmission.address);
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
