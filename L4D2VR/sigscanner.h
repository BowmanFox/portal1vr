#pragma once
#include <Windows.h>
#include <psapi.h>
#include <vector>
#include <sstream>

class SigScanner
{
public:
	// Returns 0 if current offset matches, -1 if no matches found.
	// A value > 0 is the new offset.
	static int VerifyOffset(const std::string &moduleName, int currentOffset, const std::string &signature, int sigOffset = 0)
	{
		HMODULE hModule = GetModuleHandleA(moduleName.c_str());
		if (!hModule)
			return -1;

		MODULEINFO moduleInfo = {};
		if (!GetModuleInformation(GetCurrentProcess(), hModule, &moduleInfo, sizeof(moduleInfo)))
			return -1;

		const auto *bytes = static_cast<const uint8_t *>(moduleInfo.lpBaseOfDll);

		std::vector<int> pattern;

		std::stringstream ss(signature);
		std::string sigByte;
		while (ss >> sigByte)
		{
			if (sigByte == "?" || sigByte == "??")
				pattern.push_back(-1);
			else
				pattern.push_back(strtoul(sigByte.c_str(), NULL, 16));
		}

		const size_t patternLen = pattern.size();
		const size_t imageSize = static_cast<size_t>(moduleInfo.SizeOfImage);
		if (patternLen == 0 || patternLen > imageSize)
			return -1;

		// Check if current offset is good
		bool offsetMatchesSig = true;
		const int currentPatternOffset = currentOffset - sigOffset;
		if (currentPatternOffset < 0 || static_cast<size_t>(currentPatternOffset) + patternLen > imageSize)
			offsetMatchesSig = false;

		for (size_t i = 0; offsetMatchesSig && i < patternLen; ++i)
		{
			if ((bytes[currentPatternOffset + i] != pattern[i]) && (pattern[i] != -1))
			{
				offsetMatchesSig = false;
				break;
			}
		}

		if (offsetMatchesSig)
			return 0;

		// Scan the dll for new offset
		for (size_t i = 0; i + patternLen <= imageSize; ++i)
		{
			bool found = true;
			for (size_t j = 0; j < patternLen; ++j)
			{
				if ((bytes[i + j] != pattern[j]) && (pattern[j] != -1))
				{
					found = false;
					break;
				}
			}
			if (found)
			{
				return static_cast<int>(i) + sigOffset;
			}
		}
		return -1;

	}
};
