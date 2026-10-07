// PTZControl
// Copyright (C) 2026 Martin Richter (xMRi-Software) - webmaster@m-ri.de
//
// This program is free software: you can redistribute it and/or modify
// it under the terms of the GNU General Public License as published by
// the Free Software Foundation, either version 3 of the License or
// (at your option) any later version.
//
// This program is distributed in the hope that it will be useful,
// but WITHOUT ANY WARRANTY; without even the implied warranty of
// MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.
// See the GNU General Public License for more details.
//
// You should have received a copy of the GNU General Public License
// along with this program. If not, see
// <https://www.gnu.org/licenses/>.
//
// SPDX-License-Identifier: GPL-3.0-or-later

#include "pch.h"
// #include <sstream>
// #include <iomanip>
// #include <iostream>			// Including this before DShow.h avoids a bunch of C4995 warnings for unsafe
// 							// string functions if (and only if) strsafe.h is not included above.

#include <initguid.h>
#include <comdef.h>
#define NO_DSHOW_STRSAFE // Avoid more C4995 warnings in intrin.h
#include <DShow.h>
#include <Ks.h>
#include <KsMedia.h>

#pragma comment(lib, "strmiids.lib")

#include "ExtensionUnit.h"

#define NONODE 0xFFFFFFFF

//////////////////////////////////////////////////////////////////////////

void MySleep(int mSec)
{
	// TIcks per second
	LARGE_INTEGER li;
	QueryPerformanceFrequency(&li);

	LARGE_INTEGER liStart;
	QueryPerformanceCounter(&liStart);

	LARGE_INTEGER liEnd;
	liEnd.QuadPart = liStart.QuadPart + (li.QuadPart * mSec) / 1000;

	LARGE_INTEGER liNow;
	do
	{
		QueryPerformanceCounter(&liNow);
	} while (liNow.QuadPart < liEnd.QuadPart);
	TRACE(__FUNCTION__ " %d\n", DWORD((liNow.QuadPart - liStart.QuadPart) * 1000 / li.QuadPart));
}

CWebcamController::CWebcamController()
{
	CloseDevice();
}

CWebcamController::~CWebcamController()
{
	CloseDevice();
}

HRESULT CWebcamController::OpenDevice(BSTR bstrDevicePath, DWORD wVID, DWORD wPID)
{
	// Create the System Device Enumerator
	CComPtr<ICreateDevEnum> pSysDevEnum;
	HRESULT hr = CoCreateInstance(CLSID_SystemDeviceEnum, NULL, CLSCTX_INPROC_SERVER, __uuidof(ICreateDevEnum), (void **)&pSysDevEnum);
	if (FAILED(hr))
		return hr;

	// Obtain a class enumerator for the video input device category
	CComPtr<IEnumMoniker> pEnumCat;
	hr = pSysDevEnum->CreateClassEnumerator(CLSID_VideoInputDeviceCategory, &pEnumCat, 0);
	if (hr == S_OK)
	{
		hr = HRESULT_FROM_WIN32(ERROR_PATH_NOT_FOUND);

		// Enumerate the monikers and check if we can find a matching device
		CComPtr<IMoniker> pMoniker;
		ULONG cFetched;
		while (pEnumCat->Next(1, &pMoniker, &cFetched) == S_OK)
		{
			if (DeviceMatches(pMoniker, bstrDevicePath, wVID, wPID))
			{
				hr = OpenDevice(pMoniker);
				break; // We're done searching (even if the OpenDevice() call above failed)
			}
			pMoniker = nullptr;
		}
	}

	return hr;
}

void CWebcamController::CloseDevice()
{
	m_spKsControl = nullptr;
	m_spAMCameraControl = nullptr;
	m_spVideoProcAmp = nullptr;
	m_spsPropertySet = nullptr;
	m_spCameraControl = nullptr;

	m_dwXUDeviceInformationNodeId =
		m_dwXUVideoPipeControlNodeId =
			m_dwXUTestDebugNodeId =
				m_dwXUPeripheralControlNodeId = NONODE;

	// Use IAMCameraControl motion control
	m_bUseExtensionUnitMotionControl = false;
	m_iMotorIntervalTimer = DEFAULT_MOTOR_INTERVAL_TIMER;

	// The PTZ Pro 2 has a mechanical pan tilt
	m_bMechanicalPanTilt = false;
	m_lDigitalTiltMin = m_lDigitalTiltMax = m_lDigitalPanMin = m_lDigitalPanMax = -1;
}

HRESULT CWebcamController::IsPeripheralPropertySetSupported()
{
	if (!m_spKsControl)
		return -1;

	KSP_NODE extProp{};
	extProp.Property.Set = VENDOR_XU_PERIPHERAL_CONTROL;
	extProp.Property.Id = 0;
	extProp.Property.Flags = KSPROPERTY_TYPE_SETSUPPORT | KSPROPERTY_TYPE_TOPOLOGY;
	extProp.NodeId = m_dwXUPeripheralControlNodeId;
	extProp.Reserved = 0;
	ULONG ulBytesReturned = 0;
	return m_spKsControl->KsProperty((PKSPROPERTY)&extProp, sizeof(extProp), NULL, 0, &ulBytesReturned);
}

HRESULT CWebcamController::GetProperty(VENDOR_XU_PROPERTYSET lPropertySet, ULONG ulPropertyId, ULONG ulSize, VOID *pValue)
{
	if (!m_spKsControl)
		return -1;

	ASSERT(pValue != 0 && ulSize != 0);

	KSP_NODE extprop{};
	extprop.Property.Id = ulPropertyId;
	extprop.Property.Flags = KSPROPERTY_TYPE_GET | KSPROPERTY_TYPE_TOPOLOGY;

	switch (lPropertySet)
	{
	case XU_DEVICE_INFORMATION:
		extprop.NodeId = m_dwXUDeviceInformationNodeId;
		extprop.Property.Set = VENDOR_XU_DEVICE_INFORMATION;
		break;
	case XU_VIDEOPIPE_CONTROL:
		extprop.NodeId = m_dwXUVideoPipeControlNodeId;
		extprop.Property.Set = VENDOR_XU_VIDEOPIPE_CONTROL;
		break;
	case XU_TEST_DEBUG:
		extprop.NodeId = m_dwXUTestDebugNodeId;
		extprop.Property.Set = VENDOR_XU_TEST_DEBUG;
		break;
	case XU_PERIPHERAL_CONTROL:
		extprop.NodeId = m_dwXUPeripheralControlNodeId;
		extprop.Property.Set = VENDOR_XU_PERIPHERAL_CONTROL;
		break;
	}

	HRESULT hr = m_spKsControl->KsProperty(
		(PKSPROPERTY)&extprop,
		sizeof(extprop),
		pValue,
		ulSize,
		&ulSize);

	return hr;
}

HRESULT CWebcamController::SetProperty(VENDOR_XU_PROPERTYSET lPropertySet, ULONG ulPropertyId, ULONG ulSize, VOID *pValue)
{
	if (!m_spKsControl)
		return -1;

	ASSERT(pValue != 0 && ulSize != 0);

	KSP_NODE extprop{};
	extprop.Property.Id = ulPropertyId;
	extprop.Property.Flags = KSPROPERTY_TYPE_SET | KSPROPERTY_TYPE_TOPOLOGY;

	switch (lPropertySet)
	{
	case XU_DEVICE_INFORMATION:
		extprop.NodeId = m_dwXUDeviceInformationNodeId;
		extprop.Property.Set = VENDOR_XU_DEVICE_INFORMATION;
		break;
	case XU_VIDEOPIPE_CONTROL:
		extprop.NodeId = m_dwXUVideoPipeControlNodeId;
		extprop.Property.Set = VENDOR_XU_VIDEOPIPE_CONTROL;
		break;
	case XU_TEST_DEBUG:
		extprop.NodeId = m_dwXUTestDebugNodeId;
		extprop.Property.Set = VENDOR_XU_TEST_DEBUG;
		break;
	case XU_PERIPHERAL_CONTROL:
		extprop.NodeId = m_dwXUPeripheralControlNodeId;
		extprop.Property.Set = VENDOR_XU_PERIPHERAL_CONTROL;
		break;
	}

	ULONG ulBytesReturned;
	HRESULT hr = m_spKsControl->KsProperty(
		(PKSPROPERTY)&extprop,
		sizeof(extprop),
		pValue,
		ulSize,
		&ulBytesReturned);

	return hr;
}

/*
 * Checks whether the device represented by the given IMoniker matches the given device path
 * or the given VID/PID.
 *
 * If the device path is NULL no device path matching is performed.
 * A VID or PID of 0 is considered to always match. If the VID and PID are both 0 no VID/PID
 * matching is performed.
 */
bool CWebcamController::DeviceMatches(CComPtr<IMoniker> pMoniker, BSTR devicePath, DWORD wVID, DWORD wPID)
{

	bool match = false;
	CComPtr<IPropertyBag> pPropBag;
	CComVariant varPath;

	// Open the device properties
	HRESULT hr = pMoniker->BindToStorage(NULL, NULL, __uuidof(IPropertyBag), (void **)&pPropBag);
	if (FAILED(hr))
		goto done;

	// Retrieve the device path
	hr = pPropBag->Read(L"DevicePath", &varPath, 0);
	if (FAILED(hr) || varPath.bstrVal == NULL)
		goto done;

	// Return true if the device path matches
	if (devicePath != NULL)
	{
		// Parse the device path for vid pid
		m_dwVid = m_dwPid = 0;
		if (FAILED(varPath.ChangeType(VT_BSTR)))
			return false;

		if (_wcsicmp(varPath.bstrVal, devicePath) == 0)
		{
			// Lowercase
			_wcslwr_s(varPath.bstrVal, SysStringLen(varPath.bstrVal) + 1);
			ParseDevicePath(varPath.bstrVal, m_dwVid, m_dwPid);

			match = true;
			goto done;
		}
	}

	// Return true if the USB information matches
	if (wVID || wPID)
	{
		// Parse the device path (Convert it to lower-case first for safer parsing)
		_wcslwr_s(varPath.bstrVal, SysStringLen(varPath.bstrVal) + 1);
		DWORD vid = 0, pid = 0;
		if (ParseDevicePath(varPath.bstrVal, vid, pid))
		{
			match =
				(wVID == 0 || vid == wVID) &&
				(wPID == 0 || pid == wPID);
		}
	}

done:
	VariantClear(&varPath);
	return match;
}

HRESULT CWebcamController::OpenDevice(CComPtr<IMoniker> pMoniker)
{
	CComPtr<IKsControl> pKsControl;

	// Get a pointer to the optional Extension Unit interface. Standard UVC
	// controls can still be exposed when IKsControl is unavailable.
	HRESULT hr = pMoniker->BindToObject(
		NULL, NULL, __uuidof(IKsControl), (void **)&pKsControl);

	// USB cameras expose an Extension Unit, while generic UVC cameras
	// may expose only the standard IAMCameraControl/IAMVideoProcAmp interfaces.
	// Avoid probing vendor-specific Extension Units on non-USB cameras.
	const HRESULT xu_result = pKsControl && m_dwVid == 0x046D
		? InitializeXUNodesArray(pKsControl)
		: E_NOINTERFACE;
	if (SUCCEEDED(xu_result))
	{
		m_bUseExtensionUnitMotionControl = m_dwXUPeripheralControlNodeId != NONODE;
	}
	else
	{
		m_dwXUDeviceInformationNodeId =
			m_dwXUVideoPipeControlNodeId =
				m_dwXUTestDebugNodeId =
					m_dwXUPeripheralControlNodeId = NONODE;
		m_bUseExtensionUnitMotionControl = false;
	}

	m_spKsControl = pKsControl;
	if (pKsControl)
	{
		m_spAMCameraControl = pKsControl;
		m_spVideoProcAmp = pKsControl;
		m_spsPropertySet = pKsControl;
		m_spCameraControl = pKsControl; // not supported
	}
	if (!m_spAMCameraControl)
	{
		CComPtr<IAMCameraControl> cameraControl;
		pMoniker->BindToObject(
			NULL, NULL, __uuidof(IAMCameraControl),
			(void **)&cameraControl);
		m_spAMCameraControl = cameraControl;
	}
	if (!m_spVideoProcAmp)
	{
		CComPtr<IAMVideoProcAmp> videoProcAmp;
		pMoniker->BindToObject(
			NULL, NULL, __uuidof(IAMVideoProcAmp),
			(void **)&videoProcAmp);
		m_spVideoProcAmp = videoProcAmp;
	}

	if (m_spAMCameraControl != nullptr)
	{
		long lValue = 0, lMin = 0, lMax = 0, lSteppingSize = 0, lDefaults = 0, lFlags = 0;
		HRESULT hResult = m_spAMCameraControl->Get(KSPROPERTY_CAMERACONTROL_PAN_RELATIVE, &lValue, &lFlags);
		m_bMechanicalPanTilt = SUCCEEDED(hResult);

		{
			for (int i = 0; i <= 19; ++i)
			{
				hResult = m_spAMCameraControl->Get(i, &lValue, &lFlags);
				if (SUCCEEDED(hr))
					TRACE(__FUNCTION__ " m_spAMCameraControl-%d val=%d, flag=%d\n", i, lValue, lFlags);
			}
		}

		// The PTZ Pro 2 has a mechanical pan tilt
		ASSERT(m_bMechanicalPanTilt);

		// 		{
		// 			HRESULT hResult = GetProperty(  KSPROPERTY_CAMERACONTROL_PANTILT_RELATIVE, &lValue, &lFlags);
		// 		}

		hResult = m_spAMCameraControl->GetRange(CameraControl_Pan, &lMin, &lMax, &lSteppingSize, &lDefaults, &lFlags);
		if (S_OK == hResult)
		{
			m_lDigitalPanMin = lMin;
			m_lDigitalPanMax = lMax;
		}
		lMin = lMax = lSteppingSize = lDefaults = lFlags = 0;
		hResult = m_spAMCameraControl->GetRange(CameraControl_Tilt, &lMin, &lMax, &lSteppingSize, &lDefaults, &lFlags);
		if (S_OK == hResult)
		{
			m_lDigitalTiltMin = lMin;
			m_lDigitalTiltMax = lMax;
		}
	}

	hr = (m_spAMCameraControl != nullptr || m_spVideoProcAmp != nullptr)
		? S_OK : xu_result;
	return hr;
}

bool CWebcamController::ParseDevicePath(const wchar_t *devicePath, DWORD &vid, DWORD &pid)
{
	if (swscanf_s(devicePath, L"\\\\?\\usb#vid_%04x&pid_%04x", &vid, &pid) != 2)
		return false;
	return true;
}

void CWebcamController::GetVidPid(DWORD &vid, DWORD &pid)
{
	vid = m_dwVid;
	pid = m_dwPid;
}

void CWebcamController::GotoHome()
{
	if (!m_bUseExtensionUnitMotionControl && m_spAMCameraControl)
	{
		long minimum = 0, maximum = 0, step = 0, defaultValue = 0, flags = 0;
		if (SUCCEEDED(m_spAMCameraControl->GetRange(
				CameraControl_Pan, &minimum, &maximum, &step,
				&defaultValue, &flags)))
		{
			m_spAMCameraControl->Set(
				CameraControl_Pan, defaultValue, CameraControl_Flags_Manual);
		}
		if (SUCCEEDED(m_spAMCameraControl->GetRange(
				CameraControl_Tilt, &minimum, &maximum, &step,
				&defaultValue, &flags)))
		{
			m_spAMCameraControl->Set(
				CameraControl_Tilt, defaultValue, CameraControl_Flags_Manual);
		}
		return;
	}

	// Zoom to Home
	{
		DWORD dwValue = 0;
		SetProperty(XU_VIDEOPIPE_CONTROL, XU_VIDEO_FW_ZOOM_CONTROL, sizeof(dwValue), &dwValue);
	}
	// Zoom to Home
	// Home = No Action
	//			1 ?
	//			2 ?
	// Goto Home = 3
	// 8 Presets
	// Preset 1-8 = 4-11,
	// Goto Preset 1-8 = 12-19
	// Test 22
	{
		DWORD dwValue(3);
		SetProperty(XU_PERIPHERAL_CONTROL, XU_PERIPHERALCONTROL_PANTILT_MODE_CONTROL, sizeof(DWORD), &dwValue);
	}
	return;
}

void CWebcamController::SavePreset(int iNum)
{
	if (iNum < 0 || iNum >= NUM_PRESETS)
		return;

	// Zoom to Home
	// Home = No Action
	//			1 ?
	//			2 ?
	// Goto Home = 3
	// 8 Presets
	// Preset 1-8 = 4-11,
	// Goto Preset 1-8 = 12-19
	// Test 22
	DWORD dwValue(iNum + 4);
	SetProperty(XU_PERIPHERAL_CONTROL, XU_PERIPHERALCONTROL_PANTILT_MODE_CONTROL, sizeof(DWORD), &dwValue);
}

void CWebcamController::GotoPreset(int iNum)
{
	if (iNum < 0 || iNum >= NUM_PRESETS)
		return;

	// Zoom to Home
	// Home = No Action
	//			1 ?
	//			2 ?
	// Goto Home = 3
	// 8 Presets
	// Preset 1-8 = 4-11,
	// Goto Preset 1-8 = 12-19
	// Test 22
	DWORD dwValue(iNum + 12);
	SetProperty(XU_PERIPHERAL_CONTROL, XU_PERIPHERALCONTROL_PANTILT_MODE_CONTROL, sizeof(DWORD), &dwValue);
}

#include <cstdlib>

int CWebcamController::GetCurrentZoom()
{
	if (!m_spAMCameraControl)
		return -1;

	long oldZoom = 0, oldFlags = 0;
	oldFlags = CameraControl_Flags_Manual;
	m_spAMCameraControl->Get(CameraControl_Zoom, &oldZoom, &oldFlags);
	return oldZoom;
}

int CWebcamController::Zoom(int direction)
{
	if (!m_spAMCameraControl)
		return -1;

	const bool relativeZoomSupported =
		!m_bUseExtensionUnitMotionControl &&
		SupportsCameraControl(KSPROPERTY_CAMERACONTROL_ZOOM_RELATIVE);
	if (relativeZoomSupported)
	{
		long minimum = 0, maximum = 0, step = 0, defaultValue = 0, flags = 0;
		if (FAILED(m_spAMCameraControl->GetRange(
				KSPROPERTY_CAMERACONTROL_ZOOM_RELATIVE,
				&minimum, &maximum, &step, &defaultValue, &flags)))
			return -1;

		if (direction == 0)
			return SUCCEEDED(m_spAMCameraControl->Set(
				KSPROPERTY_CAMERACONTROL_ZOOM_RELATIVE, 0, 0))
				? 0
				: -1;

		const bool directionSupported =
			direction > 0 ? maximum > 0 : minimum < 0;
		if (directionSupported)
		{
			const long maxSpeed = direction > 0 ? maximum : -minimum;
			const long speed = min(maxSpeed, std::abs(direction));
			const long relativeValue = direction > 0 ? speed : -speed;
			if (SUCCEEDED(m_spAMCameraControl->Set(
					KSPROPERTY_CAMERACONTROL_ZOOM_RELATIVE, relativeValue, 0)))
				return relativeValue;
			if (!SupportsCameraControl(CameraControl_Zoom))
				return -1;
		}
		else if (!SupportsCameraControl(CameraControl_Zoom))
		{
			return -1;
		}
	}

	if (direction == 0)
		return GetCurrentZoom();

	direction = (direction > 0) - (direction < 0);

	long lZoomMin = 0, lZoomMax = 0, lZoomDefault = 0, lZoomStep = 0, lFlags = CameraControl_Flags_Manual;
	if (FAILED(m_spAMCameraControl->GetRange(
			CameraControl_Zoom, &lZoomMin, &lZoomMax, &lZoomStep,
			&lZoomDefault, &lFlags)))
		return -1;

	long lOldZoom = GetCurrentZoom();
	if (lOldZoom < lZoomMin || lOldZoom > lZoomMax)
		lOldZoom = lZoomDefault;

	long lNewZoom = lOldZoom;

	// Devide in 150 parts
	int iStep = (lZoomMax - lZoomMin) / 150;
	if (iStep == 0)
		iStep = 1;

	// calculate new zoom
	lNewZoom = max(lZoomMin, min(lZoomMax,
		lOldZoom + lZoomStep * direction * iStep));

	return SUCCEEDED(m_spAMCameraControl->Set(
		CameraControl_Zoom, lNewZoom, CameraControl_Flags_Manual))
		? lNewZoom
		: -1;
}

bool CWebcamController::SupportsCameraControl(long property) const
{
	if (!m_spAMCameraControl)
		return false;

	long minimum = 0, maximum = 0, step = 0, defaultValue = 0, flags = 0;
	return SUCCEEDED(m_spAMCameraControl->GetRange(
		property, &minimum, &maximum, &step, &defaultValue, &flags));
}

bool CWebcamController::AdjustCameraControl(long property, int direction)
{
	if (!m_spAMCameraControl || direction == 0)
		return false;

	long minimum = 0, maximum = 0, step = 0, defaultValue = 0, flags = 0;
	if (FAILED(m_spAMCameraControl->GetRange(
			property, &minimum, &maximum, &step, &defaultValue, &flags)))
		return false;

	long current = defaultValue;
	long currentFlags = CameraControl_Flags_Manual;
	m_spAMCameraControl->Get(property, &current, &currentFlags);
	const long increment = step > 0 ? step : 1;
	current += increment * direction;
	current = max(minimum, min(maximum, current));
	return SUCCEEDED(m_spAMCameraControl->Set(
		property, current, CameraControl_Flags_Manual));
}

bool CWebcamController::SetCameraControlMode(long property, long flags)
{
	if (!m_spAMCameraControl)
		return false;
	return SUCCEEDED(m_spAMCameraControl->Set(property, 0, flags));
}

bool CWebcamController::SetCameraControlValue(long property, long value)
{
	if (!m_spAMCameraControl)
		return false;
	return SUCCEEDED(m_spAMCameraControl->Set(
		property, value, CameraControl_Flags_Manual));
}

bool CWebcamController::SetCameraControlNormalizedRange(
	long property, int value, int normalizedMaximum)
{
	if (!m_spAMCameraControl || normalizedMaximum <= 0)
		return false;

	long minimum = 0, maximum = 0, step = 0, defaultValue = 0, flags = 0;
	if (FAILED(m_spAMCameraControl->GetRange(
			property, &minimum, &maximum, &step, &defaultValue, &flags)))
		return false;

	value = max(0, min(normalizedMaximum, value));
	const long long range = static_cast<long long>(maximum) - minimum;
	long mapped = static_cast<long>(
		minimum + (range * value + normalizedMaximum / 2) / normalizedMaximum);
	if (step > 0)
	{
		const long offset = mapped - minimum;
		mapped = minimum + ((offset + step / 2) / step) * step;
		mapped = min(maximum, mapped);
	}
	return SUCCEEDED(m_spAMCameraControl->Set(
		property, mapped, CameraControl_Flags_Manual));
}

bool CWebcamController::GetCameraControlNormalizedRange(
	long property, int normalizedMaximum, int &value) const
{
	if (!m_spAMCameraControl || normalizedMaximum <= 0)
		return false;

	long minimum = 0, maximum = 0, step = 0, defaultValue = 0, rangeFlags = 0;
	if (FAILED(m_spAMCameraControl->GetRange(
			property, &minimum, &maximum, &step, &defaultValue, &rangeFlags)) ||
		maximum <= minimum)
		return false;

	long current = 0, currentFlags = 0;
	if (FAILED(m_spAMCameraControl->Get(property, &current, &currentFlags)))
		return false;

	current = max(minimum, min(maximum, current));
	const long long range = static_cast<long long>(maximum) - minimum;
	value = static_cast<int>(
		(static_cast<long long>(current - minimum) * normalizedMaximum
			+ range / 2) / range);
	return true;
}

bool CWebcamController::SetCameraControlNormalized(long property, int value)
{
	if (!m_spAMCameraControl)
		return false;

	long minimum = 0, maximum = 0, step = 0, defaultValue = 0, flags = 0;
	if (FAILED(m_spAMCameraControl->GetRange(
			property, &minimum, &maximum, &step, &defaultValue, &flags)))
		return false;

	value = max(-12, min(12, value));
	const long range = value >= 0 ? maximum - defaultValue : defaultValue - minimum;
	const long mapped = defaultValue + (range * value) / 12;
	return SUCCEEDED(m_spAMCameraControl->Set(
		property, mapped, CameraControl_Flags_Manual));
}

bool CWebcamController::SupportsVideoProcAmp(long property) const
{
	if (!m_spVideoProcAmp)
		return false;

	long minimum = 0, maximum = 0, step = 0, defaultValue = 0, flags = 0;
	return SUCCEEDED(m_spVideoProcAmp->GetRange(
		property, &minimum, &maximum, &step, &defaultValue, &flags));
}

bool CWebcamController::SetVideoProcAmpMode(long property, long flags)
{
	if (!m_spVideoProcAmp)
		return false;

	long value = 0, currentFlags = 0;
	if (FAILED(m_spVideoProcAmp->Get(property, &value, &currentFlags)))
		return false;
	return SUCCEEDED(m_spVideoProcAmp->Set(property, value, flags));
}

bool CWebcamController::SetVideoProcAmpValue(long property, long value)
{
	if (!m_spVideoProcAmp)
		return false;
	return SUCCEEDED(m_spVideoProcAmp->Set(property, value, VideoProcAmp_Flags_Manual));
}

bool CWebcamController::SetVideoProcAmpNormalized(long property, int value)
{
	if (!m_spVideoProcAmp)
		return false;

	long minimum = 0, maximum = 0, step = 0, defaultValue = 0, flags = 0;
	if (FAILED(m_spVideoProcAmp->GetRange(
			property, &minimum, &maximum, &step, &defaultValue, &flags)))
		return false;

	value = max(0, min(100, value));
	const long mapped = minimum + ((maximum - minimum) * value) / 100;
	return SUCCEEDED(m_spVideoProcAmp->Set(
		property, mapped, VideoProcAmp_Flags_Manual));
}

void CWebcamController::Tilt(int yDirection)
{
	if (m_spAMCameraControl)
	{
		const long amount = max(-100L, min(100L, static_cast<long>(yDirection)));
		m_spAMCameraControl->Set(
			KSPROPERTY_CAMERACONTROL_TILT_RELATIVE, amount, 0);
	}
}

void CWebcamController::MoveTilt(int yDirection)
{
	if (m_bUseExtensionUnitMotionControl && m_dwXUPeripheralControlNodeId != NONODE)
	{
		const int direction = yDirection > 0 ? 1 : (yDirection < 0 ? -1 : 0);
		DWORD dwValue = MAKELONG(
			MAKEWORD(0, 0), MAKEWORD(0, direction));
		SetProperty(XU_PERIPHERAL_CONTROL, XU_PERIPHERALCONTROL_PANTILT_RELATIVE_CONTROL, sizeof(DWORD), &dwValue);
	}
	else
	{
		if (!m_spAMCameraControl)
			return;

		if (m_bMechanicalPanTilt)
		{
			Tilt(yDirection);
		}
		else
		{
			long lValue(0), lFlags(0);
			if (yDirection != 0)
			{
				HRESULT hResult = m_spAMCameraControl->Get(CameraControl_Tilt, &lValue, &lFlags);
				if (S_OK == hResult)
				{
					const long delta = yDirection;
					lValue += delta;
					if (yDirection > 0 && lValue > m_lDigitalTiltMax)
						lValue = m_lDigitalTiltMax;
					if (yDirection < 0 && lValue < m_lDigitalTiltMin)
						lValue = m_lDigitalTiltMin;
					hResult = m_spAMCameraControl->Set(CameraControl_Tilt, lValue, lFlags);
				}
			}
		}
	}
	return;
}

void CWebcamController::Pan(int xDirection)
{
	if (m_spAMCameraControl)
	{
		const long amount = max(-100L, min(100L, static_cast<long>(xDirection)));
		m_spAMCameraControl->Set(
			KSPROPERTY_CAMERACONTROL_PAN_RELATIVE, amount, 0);
	}
}

void CWebcamController::MovePan(int xDirection)
{
	if (m_bUseExtensionUnitMotionControl)
	{
		const int direction = xDirection > 0 ? 1 : (xDirection < 0 ? -1 : 0);
		DWORD dwValue = MAKELONG(
			MAKEWORD(0, direction), MAKEWORD(0, 0));
		if (SUCCEEDED(SetProperty(XU_PERIPHERAL_CONTROL, XU_PERIPHERALCONTROL_PANTILT_RELATIVE_CONTROL, sizeof(DWORD), &dwValue)))
			return;
	}

	if (!m_spAMCameraControl)
		return;

	if (m_bMechanicalPanTilt)
	{
		Pan(xDirection);
	}
	else
	{
		long lValue(0), lFlags(0);
		if (xDirection != 0)
		{
			HRESULT hResult = m_spAMCameraControl->Get(CameraControl_Pan, &lValue, &lFlags);
			if (S_OK == hResult)
			{
				lValue += xDirection;
				if (xDirection > 0 && lValue > m_lDigitalPanMax)
					lValue = m_lDigitalPanMax;
				if (xDirection < 0 && lValue < m_lDigitalPanMin)
					lValue = m_lDigitalPanMin;
				m_spAMCameraControl->Set(CameraControl_Pan, lValue, lFlags);
			}
		}
	}
}

/*
 * Tries to locate the node that carries H.264 XU extension and saves its ID.
 */
HRESULT CWebcamController::InitializeXUNodesArray(CComPtr<IKsControl> pKsControl)
{
	// Get the IKsTopologyInfo interface
	CComQIPtr<IKsTopologyInfo> pKsTopologyInfo = pKsControl;
	if (!pKsTopologyInfo)
		return E_NOINTERFACE;

	// Retrieve the number of nodes in the filter
	DWORD dwNumNodes = 0;
	HRESULT hr = pKsTopologyInfo->get_NumNodes(&dwNumNodes);
	if (FAILED(hr))
		return hr;

	// Go through all extension unit nodes and try to find the required XU node
	hr = E_FAIL;
	std::set<CString> setGuids;
	for (unsigned int nodeId = 0; nodeId < dwNumNodes; nodeId++)
	{
		GUID guidNodeType;
		hr = pKsTopologyInfo->get_NodeType(nodeId, &guidNodeType);
		if (FAILED(hr))
			continue;

		// All Node types we have
		// 		{ 941C7AC0 - C559 - 11D0 - 8A2B - 00A0C9255AC1 } KSNODETYPE_DEV_SPECIFIC
		// 		{ DFF229E1 - F70F - 11D0 - B917 - 00A0C9223196 } KSNODETYPE_VIDEO_STREAMING
		// 		{ DFF229E5 - F70F - 11D0 - B917 - 00A0C9223196 } KSNODETYPE_VIDEO_PROCESSING
		// 		{ DFF229E6 - F70F - 11D0 - B917 - 00A0C9223196 } KSNODETYPE_VIDEO_CAMERA_TERMINAL
		{
			wchar_t szText[100];
			StringFromGUID2(guidNodeType, szText, _countof(szText));
			setGuids.emplace(szText);
		}

		if (!IsEqualGUID(guidNodeType, KSNODETYPE_DEV_SPECIFIC))
			continue;

		if (IsExtensionUnitSupported(pKsControl, VENDOR_XU_DEVICE_INFORMATION, nodeId))
		{
			m_dwXUDeviceInformationNodeId = nodeId;
		}
		else if (IsExtensionUnitSupported(pKsControl, VENDOR_XU_VIDEOPIPE_CONTROL, nodeId))
		{
			m_dwXUVideoPipeControlNodeId = nodeId;
		}
		else if (IsExtensionUnitSupported(pKsControl, VENDOR_XU_TEST_DEBUG, nodeId))
		{
			m_dwXUTestDebugNodeId = nodeId;
		}
		else if (IsExtensionUnitSupported(pKsControl, VENDOR_XU_PERIPHERAL_CONTROL, nodeId))
		{
			m_dwXUPeripheralControlNodeId = nodeId;
		}
		// 		else if (IsExtensionUnitSupported(pKsControl, PROPSETID_VIDCAP_CAMERACONTROL, nodeId))
		// 		{
		// 			// DWORD dwNodeId = nodeId;
		// 		}
	}
	for (const auto &str : setGuids)
		TRACE(__FUNCTION__ " - %ls\n", str.GetString());
	return hr;
}

bool CWebcamController::IsExtensionUnitSupported(CComPtr<IKsControl> pKsControl, const GUID &guidExtension, unsigned int nodeId)
{
	KSP_NODE extProp{};
	extProp.Property.Set = guidExtension;
	extProp.Property.Id = 0;
	extProp.Property.Flags = KSPROPERTY_TYPE_SETSUPPORT | KSPROPERTY_TYPE_TOPOLOGY;
	extProp.NodeId = nodeId;
	extProp.Reserved = 0;
	ULONG ulBytesReturned = 0;
	HRESULT hr = pKsControl->KsProperty((PKSPROPERTY)&extProp, sizeof(extProp), NULL, 0, &ulBytesReturned);
	return SUCCEEDED(hr);
}

void CWebcamController::ListDevices(CStringArray &aDevices)
{
	aDevices.RemoveAll();

	// Get a device list
	CComPtr<ICreateDevEnum> pSysDevEnum;
	HRESULT hr;
	hr = CoCreateInstance(CLSID_SystemDeviceEnum, NULL, CLSCTX_INPROC_SERVER, IID_ICreateDevEnum, (void **)&pSysDevEnum);
	if (SUCCEEDED(hr))
	{
		// create a device class enumerator
		CComPtr<IEnumMoniker> pIEnumMoniker;
		HRESULT hResult = pSysDevEnum->CreateClassEnumerator(CLSID_VideoInputDeviceCategory, &pIEnumMoniker, 0);
		if (SUCCEEDED(hr))
		{
			ULONG pFetched = NULL;
			CComPtr<IMoniker> pImoniker;
			while (S_OK == pIEnumMoniker->Next(1, &pImoniker, &pFetched))
			{
				CComPtr<IPropertyBag> pPropBag;
				hResult = pImoniker->BindToStorage(0, 0, IID_IPropertyBag, (void **)&pPropBag);
				if (SUCCEEDED(hResult) && pPropBag != nullptr)
				{
					CComVariant varCameraName, varDevicePath;
					pPropBag->Read(L"FriendlyName", &varCameraName, 0);
					pPropBag->Read(L"DevicePath", &varDevicePath, 0);

					if (SUCCEEDED(varCameraName.ChangeType(VT_BSTR)) &&
						SUCCEEDED(varDevicePath.ChangeType(VT_BSTR)))
					{
						CString strCameraName(varCameraName.bstrVal), strDevicePath(varDevicePath.bstrVal);
						aDevices.Add(strCameraName + _T('\t') + strDevicePath);
					}
				}

				// Set to null
				pImoniker = nullptr;
			}
		}
	}
}
