# Windows UVC camera bridge

This Windows-only DLL exposes standard UVC camera controls through DirectShow,
including pan, tilt, zoom, focus, exposure, and video-processing controls. The
vendor Extension Unit implementation is the required subset of the
GPL-3.0-or-later PTZControl source, copied into `native/ptzcontrol/`. The
complete original PTZControl project is kept locally under the ignored
`dev/local/PTZControl/` folder and is not required to build this bridge.

## Build

Build with Visual Studio and CMake from the repository root:

```powershell
cmake -S native -B dev/native-build -G "Visual Studio 17 2022" -A x64
cmake --build dev/native-build --config Release
```

The output must be:

```text
dev/native-build/Release/merekaiptzcontrol_camera.dll
```

Start MerekaiPTZControl after building. The camera selector will show DirectShow/UVC
devices, including compatible cameras such as OBSBOT Tiny 4K. A device must
expose standard UVC camera controls for the corresponding controls to work.
For standard UVC devices, tilt-up uses the positive relative direction.
Pan/tilt release sends zero relative movement; zoom release stops the lens
when the device exposes a relative zoom control. Vendor Extension Unit
movement remains unchanged.
Serial cameras continue to use the existing VISCA path.

## Licensing

`ptzcontrol/ExtensionUnit.cpp`, `ptzcontrol/ExtensionUnit.h`, and
`ptzcontrol/ExtensionUnitDefines.h` retain their original PTZControl copyright
and GPL-3.0-or-later notices. The bridge is a derivative integration and must
be distributed under compatible GPL-3.0-or-later terms when built and
distributed with these files. The complete license text is in
[`ptzcontrol/COPYING`](ptzcontrol/COPYING).
