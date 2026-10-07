param(
    [string]$Python = ""
)

$ErrorActionPreference = "Stop"
$repoRoot = Split-Path -Parent $PSScriptRoot
if (-not $Python) {
    $Python = Join-Path $repoRoot "dev\.venv\Scripts\python.exe"
}

if (-not (Test-Path $Python)) {
    throw "Python was not found at '$Python'. Create dev\.venv and install the build extra: python -m pip install -e `".[build]`"."
}

$architecture = & $Python -c "import struct; print(struct.calcsize('P') * 8)"
if ($LASTEXITCODE -ne 0 -or $architecture.Trim() -ne "64") {
    throw "A 64-bit Python interpreter is required to build the Windows x64 application."
}

& $Python -m PyInstaller --version
if ($LASTEXITCODE -ne 0) {
    throw "PyInstaller is missing. Install it with: $Python -m pip install -e `".[build]`"."
}

$distPath = Join-Path $repoRoot "dev\artifacts\windows-x64"
$workPath = Join-Path $repoRoot "dev\artifacts\pyinstaller-work"
New-Item -ItemType Directory -Force -Path $distPath, $workPath | Out-Null

$arguments = @(
    "--noconfirm",
    "--clean",
    "--onefile",
    "--windowed",
    "--name", "MerekaiPTZControl",
    "--paths", $repoRoot,
    "--distpath", $distPath,
    "--workpath", $workPath,
    "--specpath", $workPath,
    (Join-Path $repoRoot "main.py")
)

$logoPath = Join-Path $repoRoot "resources\merekaiptzcontrol.png"
$iconPath = Join-Path $repoRoot "resources\merekaiptzcontrol.ico"
if (-not (Test-Path $logoPath) -or -not (Test-Path $iconPath)) {
    throw "Application logo files are missing from resources: merekaiptzcontrol.png and merekaiptzcontrol.ico."
}
$arguments += @("--add-data", "$logoPath;resources")
$arguments += @("--icon", $iconPath)

$bridgeDll = @(
    (Join-Path $repoRoot "dev\native-build\Release\merekaiptzcontrol_camera.dll"),
    (Join-Path $repoRoot "dev\native-build\Debug\merekaiptzcontrol_camera.dll"),
    (Join-Path $repoRoot "dev\native-build\merekaiptzcontrol_camera.dll")
) | Where-Object { Test-Path $_ } | Select-Object -First 1

if ($bridgeDll) {
    $arguments += @("--add-binary", "$bridgeDll;.")
    $arguments += @(
        "--add-data",
        "$(Join-Path $repoRoot 'native\ptzcontrol\COPYING');licenses"
    )
}

Push-Location $repoRoot
try {
    & $Python -m PyInstaller @arguments
    if ($LASTEXITCODE -ne 0) {
        throw "PyInstaller failed with exit code $LASTEXITCODE."
    }
}
finally {
    Pop-Location
}

if ($bridgeDll) {
    $sourceArchive = Join-Path $distPath "native-bridge-source.zip"
    Compress-Archive -Force -DestinationPath $sourceArchive -Path @(
        (Join-Path $repoRoot "native\CMakeLists.txt"),
        (Join-Path $repoRoot "native\merekaiptzcontrol_camera_bridge.cpp"),
        (Join-Path $repoRoot "native\ptzcontrol")
    )
    Write-Host "Bundled Windows UVC bridge; GPL source and license: $sourceArchive"
}
else {
    Write-Warning "No native camera bridge DLL was found; the app will be built without Windows UVC bridge support."
}

Write-Host "Portable Windows x64 application: $(Join-Path $distPath 'MerekaiPTZControl.exe')"
