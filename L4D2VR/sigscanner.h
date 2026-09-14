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
	struct MemoryRange { uintptr_t begin; size_t size; DWORD protection; };

	static bool IsReadable(uintptr_t address, size_t length)
	{
		MEMORY_BASIC_INFORMATION info{};
		if (!address || !length || !VirtualQuery(reinterpret_cast<void *>(address), &info, sizeof(info)))
			return false;
		if (info.State != MEM_COMMIT || (info.Protect & (PAGE_NOACCESS | PAGE_GUARD)))
			return false;
		const auto end = reinterpret_cast<uintptr_t>(info.BaseAddress) + info.RegionSize;
		return address < end && length <= end - address;
	}

	static bool IsExecutable(uintptr_t address)
	{
		MEMORY_BASIC_INFORMATION info{};
		return IsReadable(address, 1) && VirtualQuery(reinterpret_cast<void *>(address), &info, sizeof(info))
			&& (info.Protect & (PAGE_EXECUTE | PAGE_EXECUTE_READ | PAGE_EXECUTE_READWRITE | PAGE_EXECUTE_WRITECOPY));
	}

	static std::vector<MemoryRange> GetReadableRanges(const std::string &moduleName)
	{
		MODULEINFO moduleInfo{};
		HMODULE module = GetModuleHandleA(moduleName.c_str());
		if (!module || !GetModuleInformation(GetCurrentProcess(), module, &moduleInfo, sizeof(moduleInfo)))
			return {};
		std::vector<MemoryRange> ranges;
		uintptr_t cursor = reinterpret_cast<uintptr_t>(moduleInfo.lpBaseOfDll);
		const uintptr_t end = cursor + moduleInfo.SizeOfImage;
		while (cursor < end)
		{
			MEMORY_BASIC_INFORMATION info{};
			if (!VirtualQuery(reinterpret_cast<void *>(cursor), &info, sizeof(info)))
				break;
			uintptr_t next = reinterpret_cast<uintptr_t>(info.BaseAddress) + info.RegionSize;
			if (next > end) next = end;
			if (next <= cursor) break;
			if (info.State == MEM_COMMIT && !(info.Protect & (PAGE_NOACCESS | PAGE_GUARD)))
				ranges.push_back({cursor, next - cursor, info.Protect});
			cursor = next;
		}
		return ranges;
	}

	static uintptr_t GetVirtualFunction(void *instance, size_t index)
	{
		if (!IsReadable(reinterpret_cast<uintptr_t>(instance), sizeof(uintptr_t))) return 0;
		const uintptr_t table = *reinterpret_cast<const uintptr_t *>(instance);
		if (index > SIZE_MAX / sizeof(uintptr_t) - 1 || !IsReadable(table, (index + 1) * sizeof(uintptr_t))) return 0;
		const uintptr_t function = reinterpret_cast<const uintptr_t *>(table)[index];
		return IsExecutable(function) ? function : 0;
	}

	static uintptr_t FindRttiVtable(const std::string &moduleName, const char *typeName)
	{
		static_assert(sizeof(uintptr_t) == 4, "Portal 1 uses the x86 MSVC RTTI layout");
		if (!typeName || !*typeName) return 0;
		const auto ranges = GetReadableRanges(moduleName);
		const size_t nameLength = std::strlen(typeName) + 1;
		uintptr_t result = 0;
		for (const auto &strings : ranges)
		for (size_t i = 8; i + nameLength <= strings.size; ++i)
		{
			if (std::memcmp(reinterpret_cast<void *>(strings.begin + i), typeName, nameLength)) continue;
			const uintptr_t descriptor = strings.begin + i - 8;
			for (const auto &references : ranges)
			for (size_t j = 12; j + 8 <= references.size; j += 4)
			{
				const auto *col = reinterpret_cast<const uint32_t *>(references.begin + j - 12);
				// Only the complete object's primary vtable, never a base subobject.
				if (col[0] || col[1] || col[2] || col[3] != descriptor) continue;
				for (const auto &tables : ranges)
				for (size_t k = 0; k + 8 <= tables.size; k += 4)
				{
					const auto *candidate = reinterpret_cast<const uintptr_t *>(tables.begin + k);
					if (candidate[0] != reinterpret_cast<uintptr_t>(col) || !IsExecutable(candidate[1])) continue;
					const uintptr_t table = tables.begin + k + 4;
					if (result && result != table) return 0;
					result = table;
				}
			}
		}
		return result;
	}

	static uintptr_t FindRttiObject(const std::string &moduleName, const char *typeName)
	{
		const uintptr_t table = FindRttiVtable(moduleName, typeName);
		if (!table) return 0;
		uintptr_t result = 0;
		for (const auto &range : GetReadableRanges(moduleName))
		{
			if (!(range.protection & (PAGE_READWRITE | PAGE_WRITECOPY))) continue;
			for (size_t i = 0; i + sizeof(uintptr_t) <= range.size; i += sizeof(uintptr_t))
			{
				const uintptr_t address = range.begin + i;
				if (*reinterpret_cast<const uintptr_t *>(address) != table) continue;
				if (result) return 0; // Ambiguous global: wait instead of hooking an arbitrary object.
				result = address;
			}
		}
		return result;
	}

	static uintptr_t FindRttiVtableFunction(const std::string &moduleName, const char *typeName, size_t index)
	{
		uintptr_t table = FindRttiVtable(moduleName, typeName);
		return table ? GetVirtualFunction(&table, index) : 0;
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
