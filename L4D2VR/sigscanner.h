#pragma once
#include <Windows.h>
#include <psapi.h>
#include <cstring>
#include <string>
#include <vector>
#include <sstream>

class SigScanner
{
public:
	static uintptr_t GetVirtualFunction(void *instance, size_t index)
	{
		if (!instance)
			return 0;

		auto *vtable = *reinterpret_cast<uintptr_t **>(instance);
		if (!vtable)
			return 0;

		return vtable[index];
	}

	static uintptr_t FindRttiVtable(const std::string &moduleName, const char *typeName)
	{
		HMODULE hModule = GetModuleHandleA(moduleName.c_str());
		if (!hModule || !typeName || !*typeName)
			return 0;

		MODULEINFO moduleInfo = {};
		if (!GetModuleInformation(GetCurrentProcess(), hModule, &moduleInfo, sizeof(moduleInfo)))
			return 0;

		const auto *bytes = static_cast<const uint8_t *>(moduleInfo.lpBaseOfDll);
		const auto baseAddress = reinterpret_cast<uintptr_t>(moduleInfo.lpBaseOfDll);
		const size_t imageSize = static_cast<size_t>(moduleInfo.SizeOfImage);
		const size_t typeNameLen = std::strlen(typeName);

		if (typeNameLen == 0 || typeNameLen + 8 > imageSize)
			return 0;

		for (size_t stringPos = 8; stringPos + typeNameLen <= imageSize; ++stringPos)
		{
			if (std::memcmp(bytes + stringPos, typeName, typeNameLen) != 0)
				continue;

			const uintptr_t typeDescriptorAddress = baseAddress + stringPos - 8;
			for (size_t refPos = 12; refPos + sizeof(uintptr_t) <= imageSize; ++refPos)
			{
				if (*reinterpret_cast<const uintptr_t *>(bytes + refPos) != typeDescriptorAddress)
					continue;

				const size_t colPos = refPos - 12;
				const uintptr_t colAddress = baseAddress + colPos;

				for (size_t colRefPos = 0; colRefPos + sizeof(uintptr_t) <= imageSize; ++colRefPos)
				{
					if (*reinterpret_cast<const uintptr_t *>(bytes + colRefPos) != colAddress)
						continue;

					const uintptr_t vtableAddress = baseAddress + colRefPos + sizeof(uintptr_t);
					const uintptr_t firstFunction = *reinterpret_cast<const uintptr_t *>(bytes + colRefPos + sizeof(uintptr_t));
					if (firstFunction >= baseAddress && firstFunction < baseAddress + imageSize)
						return vtableAddress;
				}
			}
		}

		return 0;
	}

	static uintptr_t FindRttiVtableFunction(const std::string &moduleName, const char *typeName, size_t index)
	{
		const uintptr_t vtableAddress = FindRttiVtable(moduleName, typeName);
		if (!vtableAddress)
			return 0;

		const auto *functionAddress = reinterpret_cast<const uintptr_t *>(vtableAddress + (index * sizeof(uintptr_t)));
		return *functionAddress;
	}

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
