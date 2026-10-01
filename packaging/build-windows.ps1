param(
    [Parameter(Mandatory = $true)][string]$E130,
    [Parameter(Mandatory = $true)][string]$RemoteRoot,
    [string]$MSYS2Root = "C:\msys64",
    [string]$BuildRoot = "C:\EXwordBuild"
)
$ErrorActionPreference = "Stop"
foreach ($Command in @("ssh", "scp", "py")) {
    if (-not (Get-Command $Command -ErrorAction SilentlyContinue)) {
        throw "Required command not found: $Command"
    }
}
if ($RemoteRoot -notmatch '^/[A-Za-z0-9_./-]+$' -or $RemoteRoot.Contains("..")) {
    throw "RemoteRoot must be a simple absolute path without spaces or parent traversal."
}
if ($E130 -notmatch '^[A-Za-z0-9_.@-]+$' -or $E130.StartsWith('-')) {
    throw "Use an SSH alias or user@host; do not include SSH options."
}
$Workspace = Join-Path $BuildRoot ("exword-build-" + [guid]::NewGuid().ToString("N"))
if ($Workspace -notmatch '^[A-Za-z]:\\[A-Za-z0-9_\\.-]+$' -or $MSYS2Root -notmatch '^[A-Za-z]:\\[A-Za-z0-9_\\.-]+$') {
    throw "Use ASCII-only paths for BuildRoot and MSYS2Root to avoid MinGW path errors."
}
New-Item -ItemType Directory -Path $Workspace | Out-Null
$Archive = Join-Path $Workspace "EXwordScreenCapture-source-v1.0.0.zip"
$Checksum = $Archive + ".sha256"
& scp ($E130 + ":" + $RemoteRoot + "/EXwordScreenCapture-source-v1.0.0.zip") $Archive
if ($LASTEXITCODE -ne 0) { throw "Source download failed." }
& scp ($E130 + ":" + $RemoteRoot + "/EXwordScreenCapture-source-v1.0.0.zip.sha256") $Checksum
if ($LASTEXITCODE -ne 0) { throw "Checksum download failed." }
$Expected = ((Get-Content -Raw $Checksum).Trim() -split '\s+')[0]
if ($Expected -notmatch '^[A-Fa-f0-9]{64}$' -or (Get-FileHash -Algorithm SHA256 $Archive).Hash -ne $Expected) {
    throw "Source SHA-256 mismatch."
}
Add-Type -AssemblyName System.IO.Compression.FileSystem
$Zip = [System.IO.Compression.ZipFile]::OpenRead($Archive)
try {
    foreach ($Entry in $Zip.Entries) {
        $Name = $Entry.FullName.Replace('\', '/')
        if ($Name.StartsWith('/') -or $Name.Contains(':') -or ($Name.Split('/') -contains '..')) {
            throw "Unsafe source archive entry."
        }
    }
} finally { $Zip.Dispose() }
$Source = Join-Path $Workspace "source"
Expand-Archive -Path $Archive -DestinationPath $Source
$DependencyArchive = Join-Path $Workspace "dependency-sources.zip"
& scp ($E130 + ":" + $RemoteRoot + "/EXwordScreenCapture-dependency-sources-v1.0.0.zip") $DependencyArchive
if ($LASTEXITCODE -ne 0) { throw "Dependency source download failed." }
& scp ($E130 + ":" + $RemoteRoot + "/EXwordScreenCapture-dependency-sources-v1.0.0.zip.sha256") ($DependencyArchive + ".sha256")
if ($LASTEXITCODE -ne 0) { throw "Dependency checksum download failed." }
$DependencyExpected = ((Get-Content -Raw ($DependencyArchive + ".sha256")).Trim() -split '\s+')[0]
if ($DependencyExpected -notmatch '^[A-Fa-f0-9]{64}$' -or (Get-FileHash -Algorithm SHA256 $DependencyArchive).Hash -ne $DependencyExpected) {
    throw "Dependency source SHA-256 mismatch."
}
$DependencySource = Join-Path $Workspace "dependency-sources"
$Zip = [System.IO.Compression.ZipFile]::OpenRead($DependencyArchive)
try {
    foreach ($Entry in $Zip.Entries) {
        $Name = $Entry.FullName.Replace('\', '/')
        if ($Name.StartsWith('/') -or $Name.Contains(':') -or ($Name.Split('/') -contains '..')) {
            throw "Unsafe dependency archive entry."
        }
    }
} finally { $Zip.Dispose() }
Expand-Archive -Path $DependencyArchive -DestinationPath $DependencySource
& py -3.12 -m venv (Join-Path $Workspace "venv")
if ($LASTEXITCODE -ne 0) { throw "Python 3.12 (64-bit) is required." }
$Python = Join-Path $Workspace "venv/Scripts/python.exe"
& $Python -m pip install --no-cache-dir -r (Join-Path $Source "requirements-build.txt")
if ($LASTEXITCODE -ne 0) { throw "Dependency installation failed." }
$OldQt = $env:QT_QPA_PLATFORM
$OldCache = $env:PYINSTALLER_CONFIG_DIR
Push-Location $Source
try {
    $env:QT_QPA_PLATFORM = "offscreen"
    $env:PYINSTALLER_CONFIG_DIR = Join-Path $Workspace "pyinstaller-cache"
    & $Python -c "import platform; assert platform.machine().lower() in ('amd64', 'x86_64'), 'Use x64 Python'"
    if ($LASTEXITCODE -ne 0) { throw "Wrong Python architecture." }
    & $Python -m unittest discover -s tests -v
    if ($LASTEXITCODE -ne 0) { throw "Tests failed." }
    $PythonVersion = (& $Python -c "import platform; print(platform.python_version())").Trim()
    & $Python packaging/prepare_sources.py --output $DependencySource --python-version $PythonVersion --extra-source (Join-Path $DependencySource "archives/ffmpeg-8.0.tar.xz") --extra-source (Join-Path $DependencySource "archives/libusb-1.0.29.tar.bz2") --x264-source (Join-Path $DependencySource "archives/x264-0480cb05fa188d37ae87e8f4fd8f1aea3711f7ee.tar.gz") --x264-commit 0480cb05fa188d37ae87e8f4fd8f1aea3711f7ee
    if ($LASTEXITCODE -ne 0) { throw "Corresponding source preparation failed." }
    $OpenSSLVersion = (& $Python -c "import ssl; print(ssl.OPENSSL_VERSION.split()[1])").Trim()
    & $Python packaging/prepare_runtime_notices.py --sources $DependencySource --openssl-version $OpenSSLVersion
    if ($LASTEXITCODE -ne 0) { throw "Runtime license preparation failed." }
    $MSYSShell = Join-Path $MSYS2Root "msys2_shell.cmd"
    if (-not (Test-Path $MSYSShell)) { throw "Install MSYS2 UCRT64 and the build tools listed in docs/WINDOWS_BUILD.md." }
    $Native = Join-Path $Workspace "native-output"
    $NativeWork = Join-Path $Workspace "native-work"
    function To-MSYSPath([string]$Value) {
        $Value = $Value.Replace('\', '/')
        if ($Value -notmatch '^([A-Za-z]):/(.*)$' -or $Value.Contains("'")) { throw "Use a local drive path without single quotes for the temporary directory." }
        return '/' + $Matches[1].ToLower() + '/' + $Matches[2]
    }
    $NativeTemp = Join-Path $Workspace "native-temp"
    New-Item -ItemType Directory -Path $NativeTemp | Out-Null
    $NativeCommand = "export EXWORD_NATIVE_ROOT='" + (To-MSYSPath $MSYS2Root) + "' EXWORD_NATIVE_TEMP='" + (To-MSYSPath $NativeTemp) + "' EXWORD_NATIVE_CC='" + (To-MSYSPath (Join-Path $Source "packaging/gcc-ascii.sh")) + "'; cd '" + (To-MSYSPath $Source) + "' && chmod +x packaging/gcc-ascii.sh && /ucrt64/bin/python packaging/build_media.py --sources '" + (To-MSYSPath $DependencySource) + "' --work '" + (To-MSYSPath $NativeWork) + "' --output '" + (To-MSYSPath $Native) + "' --jobs 4"
    & $MSYSShell -defterm -no-start -ucrt64 -c $NativeCommand
    if ($LASTEXITCODE -ne 0 -or -not (Test-Path (Join-Path $Native "manifest.json"))) { throw "Native FFmpeg/libusb build failed." }
    & $Python packaging/build.py --sources $DependencySource --native $Native
    if ($LASTEXITCODE -ne 0) { throw "Build or privacy inspection failed." }
    $Smoke = Start-Process -FilePath "./dist/EXwordScreenCapture/EXwordScreenCapture.exe" -ArgumentList "--self-test" -Wait -PassThru
    if ($Smoke.ExitCode -ne 0) { throw "Packaged GUI smoke test failed." }
    & $Python packaging/build_onefile.py
    if ($LASTEXITCODE -ne 0) { throw "Standalone EXE build, privacy inspection or recording test failed." }
    & $Python packaging/checksums.py release-artifacts
    if ($LASTEXITCODE -ne 0) { throw "Artifact checksum generation failed." }
    # Only sanitized artifacts are returned. Do not send venv, cache or build logs.
    & ssh $E130 ("mkdir -p " + $RemoteRoot + "/windows-return")
    if ($LASTEXITCODE -ne 0) { throw "Unable to create return directory." }
    foreach ($Artifact in Get-ChildItem -File release-artifacts) {
        & scp $Artifact.FullName ($E130 + ":" + $RemoteRoot + "/windows-return/")
        if ($LASTEXITCODE -ne 0) { throw "Artifact upload failed." }
    }
    Write-Host "Windows build, offline GUI test and privacy inspection passed."
    Write-Host "Local artifacts: $Source/release-artifacts"
} finally {
    Pop-Location
    $env:QT_QPA_PLATFORM = $OldQt
    $env:PYINSTALLER_CONFIG_DIR = $OldCache
}
