/*
 * USB Extension Unit bridge for MerekaiPTZControl.
 *
 * This bridge uses the GPL-3.0 PTZControl ExtensionUnit source in ptzcontrol/.
 * Keep the corresponding source and license notices when distributing it.
 * SPDX-License-Identifier: GPL-3.0-or-later
 */

#include <windows.h>
#include <afxcoll.h>
#include <atlbase.h>
#include <atlstr.h>
#include <Ks.h>
#include <KsMedia.h>
#include <cstring>
#include <vector>
#include <string>

#include "ExtensionUnit.h"

namespace
{
    std::vector<std::wstring> g_device_paths;

    struct CameraHandle
    {
        CWebcamController controller;
        bool com_initialized = false;
    };

    std::wstring DevicePathFromEntry(const CString &entry)
    {
        const int separator = entry.Find(L'\t');
        if (separator < 0)
        {
            return L"";
        }
        return std::wstring(entry.Mid(separator + 1).GetString());
    }

    std::string JsonEscape(const std::wstring &value)
    {
        CStringA utf8(value.c_str());
        std::string result = "\"";
        for (const char character : std::string(utf8))
        {
            if (character == '\\' || character == '\"')
            {
                result += '\\';
            }
            result += character;
        }
        result += "\"";
        return result;
    }
}

extern "C" __declspec(dllexport) int __cdecl lc_list_devices(char *buffer, size_t buffer_size)
{
    if (buffer == nullptr || buffer_size == 0)
    {
        return 0;
    }

    CoInitializeEx(nullptr, COINIT_MULTITHREADED);
    CStringArray devices;
    CWebcamController::ListDevices(devices);
    g_device_paths.clear();

    std::string json = "[";
    for (int index = 0; index < devices.GetCount(); ++index)
    {
        const CString entry = devices[index];
        const int separator = entry.Find(L'\t');
        if (separator < 0)
        {
            continue;
        }
        const CString name = entry.Left(separator);
        g_device_paths.push_back(DevicePathFromEntry(entry));
        if (json.size() > 1)
        {
            json += ",";
        }
        json += JsonEscape(std::wstring(name.GetString()));
    }
    json += "]";

    if (json.size() + 1 > buffer_size)
    {
        buffer[0] = '\0';
        return 0;
    }
    memcpy(buffer, json.c_str(), json.size() + 1);
    CoUninitialize();
    return static_cast<int>(g_device_paths.size());
}

extern "C" __declspec(dllexport) void *__cdecl lc_open(int index)
{
    if (index < 0 || index >= static_cast<int>(g_device_paths.size()))
    {
        return nullptr;
    }

    auto *handle = new CameraHandle();
    const HRESULT com_result = CoInitializeEx(nullptr, COINIT_MULTITHREADED);
    handle->com_initialized = com_result == S_OK || com_result == S_FALSE;
    const HRESULT result = handle->controller.OpenDevice(
        CComBSTR(g_device_paths[index].c_str()), 0, 0);
    if (FAILED(result))
    {
        if (handle->com_initialized && com_result != RPC_E_CHANGED_MODE)
        {
            CoUninitialize();
        }
        delete handle;
        return nullptr;
    }
    return handle;
}

extern "C" __declspec(dllexport) void __cdecl lc_close(void *value)
{
    auto *handle = static_cast<CameraHandle *>(value);
    if (handle == nullptr)
    {
        return;
    }
    handle->controller.CloseDevice();
    if (handle->com_initialized)
    {
        CoUninitialize();
    }
    delete handle;
}

extern "C" __declspec(dllexport) int __cdecl lc_move_pan(void *value, int direction)
{
    auto *handle = static_cast<CameraHandle *>(value);
    if (handle == nullptr)
    {
        return 0;
    }
    handle->controller.MovePan(direction);
    return 1;
}

extern "C" __declspec(dllexport) int __cdecl lc_move_tilt(void *value, int direction)
{
    auto *handle = static_cast<CameraHandle *>(value);
    if (handle == nullptr)
    {
        return 0;
    }
    handle->controller.MoveTilt(direction);
    return 1;
}

extern "C" __declspec(dllexport) int __cdecl lc_stop(void *value, int unused)
{
    auto *handle = static_cast<CameraHandle *>(value);
    if (handle == nullptr)
    {
        return 0;
    }
    handle->controller.MovePan(0);
    handle->controller.MoveTilt(0);
    return 1;
}

extern "C" __declspec(dllexport) int __cdecl lc_home(void *value, int unused)
{
    auto *handle = static_cast<CameraHandle *>(value);
    if (handle == nullptr)
    {
        return 0;
    }
    handle->controller.GotoHome();
    return 1;
}

extern "C" __declspec(dllexport) int __cdecl lc_zoom(void *value, int direction)
{
    auto *handle = static_cast<CameraHandle *>(value);
    if (handle == nullptr)
    {
        return 0;
    }
    handle->controller.Zoom(direction);
    return 1;
}

extern "C" __declspec(dllexport) int __cdecl lc_zoom_absolute(void *value, int position)
{
    auto *handle = static_cast<CameraHandle *>(value);
    return handle != nullptr &&
        handle->controller.SetCameraControlNormalizedRange(
            CameraControl_Zoom, position, 0xFFFF);
}

extern "C" __declspec(dllexport) int __cdecl lc_get_ptz_position(
    void *value, int axis)
{
    auto *handle = static_cast<CameraHandle *>(value);
    if (handle == nullptr)
    {
        return -1;
    }

    const long property = axis == 0
        ? CameraControl_Pan
        : axis == 1
            ? CameraControl_Tilt
            : axis == 2
                ? CameraControl_Zoom
                : -1;
    int position = 0;
    return property >= 0 &&
        handle->controller.GetCameraControlNormalizedRange(
            property, 0xFFFF, position)
        ? position
        : -1;
}

extern "C" __declspec(dllexport) int __cdecl lc_set_pan_tilt_absolute(
    void *value, int panPosition, int tiltPosition)
{
    auto *handle = static_cast<CameraHandle *>(value);
    return handle != nullptr &&
        handle->controller.SetCameraControlNormalizedRange(
            CameraControl_Pan, panPosition, 0xFFFF) &&
        handle->controller.SetCameraControlNormalizedRange(
            CameraControl_Tilt, tiltPosition, 0xFFFF);
}

extern "C" __declspec(dllexport) int __cdecl lc_save_preset(void *value, int index)
{
    auto *handle = static_cast<CameraHandle *>(value);
    if (handle == nullptr)
    {
        return 0;
    }
    handle->controller.SavePreset(index);
    return 1;
}

extern "C" __declspec(dllexport) int __cdecl lc_goto_preset(void *value, int index)
{
    auto *handle = static_cast<CameraHandle *>(value);
    if (handle == nullptr)
    {
        return 0;
    }
    handle->controller.GotoPreset(index);
    return 1;
}

extern "C" __declspec(dllexport) int __cdecl lc_capabilities(void *value, int unused)
{
    auto *handle = static_cast<CameraHandle *>(value);
    if (handle == nullptr)
    {
        return 0;
    }

    int capabilities = 0;
    const bool pan = handle->controller.SupportsCameraControl(CameraControl_Pan);
    const bool tilt = handle->controller.SupportsCameraControl(CameraControl_Tilt);
    const bool panRelative = handle->controller.SupportsCameraControl(
        KSPROPERTY_CAMERACONTROL_PAN_RELATIVE);
    const bool tiltRelative = handle->controller.SupportsCameraControl(
        KSPROPERTY_CAMERACONTROL_TILT_RELATIVE);
    if ((pan || panRelative) && (tilt || tiltRelative))
        capabilities |= 1;
    if (pan && tilt)
        capabilities |= 65536;
    if (handle->controller.SupportsCameraControl(CameraControl_Zoom) ||
        handle->controller.SupportsCameraControl(
            KSPROPERTY_CAMERACONTROL_ZOOM_RELATIVE))
        capabilities |= 2;
    if (handle->controller.SupportsCameraControl(CameraControl_Zoom))
        capabilities |= 262144;
    if (handle->controller.UseExtensionUnitMotionControl())
        capabilities |= 128;
    if (!handle->controller.UseExtensionUnitMotionControl())
        capabilities |= 131072;
    if (handle->controller.SupportsCameraControl(CameraControl_Focus))
        capabilities |= 4;
    if (handle->controller.SupportsCameraControl(CameraControl_Iris))
        capabilities |= 8;
    if (handle->controller.SupportsVideoProcAmp(VideoProcAmp_WhiteBalance))
        capabilities |= 16;
    if (handle->controller.SupportsCameraControl(CameraControl_Exposure))
        capabilities |= 32;
    if (handle->controller.SupportsVideoProcAmp(VideoProcAmp_Contrast))
        capabilities |= 64;
    if (handle->controller.SupportsVideoProcAmp(VideoProcAmp_Brightness))
        capabilities |= 256;
    if (handle->controller.SupportsVideoProcAmp(VideoProcAmp_Saturation))
        capabilities |= 512;
    if (handle->controller.SupportsVideoProcAmp(VideoProcAmp_Sharpness))
        capabilities |= 1024;
    if (handle->controller.SupportsVideoProcAmp(VideoProcAmp_Gamma))
        capabilities |= 2048;
    if (handle->controller.SupportsVideoProcAmp(VideoProcAmp_Hue))
        capabilities |= 4096;
    if (handle->controller.SupportsVideoProcAmp(VideoProcAmp_Gain))
        capabilities |= 8192;
    if (handle->controller.SupportsVideoProcAmp(VideoProcAmp_BacklightCompensation))
        capabilities |= 16384;
    if (handle->controller.SupportsVideoProcAmp(VideoProcAmp_ColorEnable))
        capabilities |= 32768;
    return capabilities;
}

extern "C" __declspec(dllexport) int __cdecl lc_video_proc_amp(
    void *value, int property, int setting)
{
    auto *handle = static_cast<CameraHandle *>(value);
    return handle != nullptr && handle->controller.SetVideoProcAmpNormalized(
                                    property, setting);
}

extern "C" __declspec(dllexport) int __cdecl lc_focus_auto(void *value, int unused)
{
    auto *handle = static_cast<CameraHandle *>(value);
    return handle != nullptr && handle->controller.SetCameraControlMode(
                                    CameraControl_Focus, CameraControl_Flags_Auto);
}

extern "C" __declspec(dllexport) int __cdecl lc_focus_manual(void *value, int unused)
{
    auto *handle = static_cast<CameraHandle *>(value);
    return handle != nullptr && handle->controller.SetCameraControlMode(
                                    CameraControl_Focus, CameraControl_Flags_Manual);
}

extern "C" __declspec(dllexport) int __cdecl lc_focus(void *value, int direction)
{
    auto *handle = static_cast<CameraHandle *>(value);
    return handle != nullptr && handle->controller.AdjustCameraControl(
                                    CameraControl_Focus, direction);
}

extern "C" __declspec(dllexport) int __cdecl lc_iris(void *value, int direction)
{
    auto *handle = static_cast<CameraHandle *>(value);
    return handle != nullptr && handle->controller.AdjustCameraControl(
                                    CameraControl_Iris, direction);
}

extern "C" __declspec(dllexport) int __cdecl lc_exposure(void *value, int setting)
{
    auto *handle = static_cast<CameraHandle *>(value);
    return handle != nullptr && handle->controller.SetCameraControlNormalized(
                                    CameraControl_Exposure, setting);
}

extern "C" __declspec(dllexport) int __cdecl lc_white_balance_auto(void *value, int unused)
{
    auto *handle = static_cast<CameraHandle *>(value);
    return handle != nullptr && handle->controller.SetVideoProcAmpMode(
                                    VideoProcAmp_WhiteBalance, VideoProcAmp_Flags_Auto);
}

extern "C" __declspec(dllexport) int __cdecl lc_white_balance_manual(void *value, int setting)
{
    auto *handle = static_cast<CameraHandle *>(value);
    return handle != nullptr && handle->controller.SetVideoProcAmpValue(
                                    VideoProcAmp_WhiteBalance, setting);
}

extern "C" __declspec(dllexport) int __cdecl lc_contrast(void *value, int setting)
{
    auto *handle = static_cast<CameraHandle *>(value);
    return handle != nullptr && handle->controller.SetVideoProcAmpNormalized(
                                    VideoProcAmp_Contrast, setting);
}
