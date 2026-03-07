#pragma once

#include <Windows.h>
#include <cstdarg>
#include <cstdio>

inline void PortalVrResetLog()
{
    char currentDir[MAX_PATH] = {};
    if (!GetCurrentDirectoryA(MAX_PATH, currentDir))
        return;

    char path[MAX_PATH * 2] = {};
    sprintf_s(path, "%s\\portalvr.log", currentDir);

    FILE *file = nullptr;
    fopen_s(&file, path, "w");
    if (file)
        fclose(file);
}

inline void PortalVrLog(const char *format, ...)
{
    char currentDir[MAX_PATH] = {};
    if (!GetCurrentDirectoryA(MAX_PATH, currentDir))
        return;

    char path[MAX_PATH * 2] = {};
    sprintf_s(path, "%s\\portalvr.log", currentDir);

    FILE *file = nullptr;
    fopen_s(&file, path, "a");
    if (!file)
        return;

    SYSTEMTIME localTime = {};
    GetLocalTime(&localTime);

    fprintf(
        file,
        "[%02u:%02u:%02u.%03u][tid=%lu] ",
        localTime.wHour,
        localTime.wMinute,
        localTime.wSecond,
        localTime.wMilliseconds,
        static_cast<unsigned long>(GetCurrentThreadId()));

    va_list args;
    va_start(args, format);
    vfprintf(file, format, args);
    va_end(args);

    fputc('\n', file);
    fclose(file);
}
