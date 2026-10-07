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

#pragma once
#include <Ks.h>
#include <KsProxy.h> // For IKsControl
#include <vidcap.h>	 // For IKsNodeControl

#include "ExtensionUnitDefines.h"

#define DEFAULT_MOTOR_INTERVAL_TIMER 70

/**
 * CWebcamExtensionUnit encapsulates the USB extension unit capability of the device.
 * (see https://msdn.microsoft.com/en-us/library/windows/hardware/ff568656(v=vs.85).aspx).
 */

class CWebcamController
{
public:
	CWebcamController(void);
	~CWebcamController(void);

	HRESULT OpenDevice(BSTR bstrDevicePath, DWORD wVID, DWORD wPID);
	void CloseDevice();
	HRESULT IsPeripheralPropertySetSupported();
	HRESULT GetProperty(VENDOR_XU_PROPERTYSET lPropertySet, ULONG ulPropertyId, ULONG ulSize, VOID *pValue);
	HRESULT SetProperty(VENDOR_XU_PROPERTYSET lPropertySet, ULONG ulPropertyId, ULONG ulSize, VOID *pValue);
	void GetVidPid(DWORD &vid, DWORD &pid);

	int GetCurrentZoom();
	int Zoom(int direction);
	bool SupportsCameraControl(long property) const;
	bool AdjustCameraControl(long property, int direction);
	bool SetCameraControlMode(long property, long flags);
	bool SetCameraControlValue(long property, long value);
	bool SetCameraControlNormalizedRange(long property, int value, int normalizedMaximum);
	bool GetCameraControlNormalizedRange(
		long property, int normalizedMaximum, int &value) const;
	bool SetCameraControlNormalized(long property, int value);
	bool SupportsVideoProcAmp(long property) const;
	bool SetVideoProcAmpMode(long property, long flags);
	bool SetVideoProcAmpValue(long property, long value);
	bool SetVideoProcAmpNormalized(long property, int value);
	void MoveTilt(int yDirection);
	void MovePan(int xDirection);
	void Tilt(int yDirection);
	void Pan(int xDirection);

	void GotoHome();
	void SavePreset(int iNum);
	void GotoPreset(int iNum);

	static void ListDevices(CStringArray &aDevices);
	static const int NUM_PRESETS = 8;

	bool UseExtensionUnitMotionControl() const { return m_bUseExtensionUnitMotionControl; }
	void UseExtensionUnitMotionControl(bool val) { m_bUseExtensionUnitMotionControl = val; }

	int GetMotorIntervalTimer() const { return m_iMotorIntervalTimer; }
	void SetMotorIntervalTimer(int val) { m_iMotorIntervalTimer = val; }

private:
	bool DeviceMatches(CComPtr<IMoniker> pMoniker, BSTR devicePath, DWORD wVID, DWORD wPID);
	HRESULT OpenDevice(CComPtr<IMoniker> pMoniker);
	bool ParseDevicePath(const wchar_t *devicePath, DWORD &vid, DWORD &pid);
	HRESULT InitializeXUNodesArray(CComPtr<IKsControl> pKsControl);
	bool IsExtensionUnitSupported(CComPtr<IKsControl> pKsControl, const GUID &guidExtension, unsigned int nodeId);

private:
	CComPtr<IKsControl> m_spKsControl;
	CComQIPtr<IAMCameraControl> m_spAMCameraControl;
	CComQIPtr<IAMVideoProcAmp> m_spVideoProcAmp;
	CComQIPtr<IKsPropertySet> m_spsPropertySet;
	CComQIPtr<ICameraControl> m_spCameraControl;

	DWORD m_dwXUDeviceInformationNodeId;
	DWORD m_dwXUVideoPipeControlNodeId;
	DWORD m_dwXUTestDebugNodeId;
	DWORD m_dwXUPeripheralControlNodeId;
	DWORD m_dwVid;
	DWORD m_dwPid;

	bool m_bMechanicalPanTilt;
	long m_lDigitalTiltMin, m_lDigitalTiltMax,
		m_lDigitalPanMin, m_lDigitalPanMax;

	bool m_bUseExtensionUnitMotionControl;
	int m_iMotorIntervalTimer;
};
