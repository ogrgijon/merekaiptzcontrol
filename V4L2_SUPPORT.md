# Linux V4L2 camera support

On Linux, MerekaiPTZControl discovers `/dev/video*` devices that expose usable V4L2
pan and tilt controls. Install `v4l-utils` so the `v4l2-ctl` command is
available, then use **Refresh Cameras** in the application. Discovered cameras
are added to the same camera selector as the existing USB cameras.

Pan/tilt controls are required for discovery. Zoom, focus, iris, exposure,
white balance, and image controls are enabled only when the camera exposes the
corresponding V4L2 controls. Relative or absolute pan/tilt controls and
continuous, relative, or absolute zoom controls are supported. Cameras whose
PTZ functions are only available through vendor-specific controls not exposed
by V4L2 standard controls are not discovered by this backend.

On Windows, compatible UVC cameras are discovered through the DirectShow
bridge. This includes cameras such as OBSBOT Tiny 4K when their PTZ functions
are exposed through standard UVC camera controls. Build the bridge described in
[`native/README.md`](./native/README.md) and use **Refresh Cameras**.
