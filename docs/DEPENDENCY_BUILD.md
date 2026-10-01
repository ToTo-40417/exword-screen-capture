# Dependency sources and builds

## Included originals

`third-party/corresponding-source/archives/` contains the original source archives,
not merely upstream links. Its `manifest.json` gives versions, original URLs,
SHA-256, sizes and the integrity receipts used. Qt/PySide archives are verified
against Qt's official SHA-256; Python packages against PyPI's SHA-256. FFmpeg,
libusb and CPython have recorded SHA-256 of the downloaded official originals.

| Source | Covers |
| --- | --- |
| `qtbase-everywhere-src-6.8.3.tar.xz` | QtCore/Gui/Widgets/Network/DBus, platform plugins and built-in GIF/ICO/JPEG plugins, incorporated third-party sources |
| `qtsvg-everywhere-src-6.8.3.tar.xz` | QtSvg and its image/icon plugins |
| `pyside-setup-everywhere-src-6.8.3.tar.xz` | PySide6, Shiboken6, binding generator, CMake/setup/CI scripts |
| `libusb-1.0.29.tar.bz2` | Dynamically loaded libusb |
| `ffmpeg-8.0.tar.xz` | Standalone GPL FFmpeg with statically linked libx264 |
| CPython and Python-package archives | Python, PyUSB, PyInstaller bootloader/exception, build tooling and notices |

The pinned official `x264-<commit>.tar.gz` git archive is also included.
Its manifest records the full commit and local archive SHA-256, not an upstream archive checksum.

Qt Image Formats plugins such as TIFF, WebP, ICNS, TGA and WBMP are not covered
by QtBase or QtSvg. If packaged, they require matching `qtimageformats` sources,
build information and applicable codec notices. Remove unused plugins or supply
those materials before distribution. Independently bundled libraries such as
ICU and OpenSSL also need version-matched license/attribution inventory; Qt's
Unicode data notice is not a substitute for the complete ICU license.

No upstream source patches are applied. The packaging scripts redact supplier diagnostic
home paths in binary data, never executable sections, and record affected files and dates.
Windows removes invalidated supplier signatures; Mac re-signs ad hoc. This binary
postprocessing is reproducible with the included scripts; original source archives are unchanged.
PyInstaller changes binary load paths, slices the
Mac binaries to arm64, and signs ad hoc. Original archive licenses remain intact;
the archive may include alternative commercial terms and GPL tools/examples not
used by the app. Those alternatives are not accepted or applied to this app.
The distributed Qt modules use their LGPL option; third-party subcomponents keep
their own terms. Source archives include build scripts, headers, license texts and
incorporated third-party code. Extracted notices are also provided separately.

## Build the app and native helpers

The application source is included under `third-party/application-source/`.
Use a private build directory, Python 3.12, a C compiler and make. No installation
into a system prefix is performed by the native helper.

```sh
python -m venv .venv-build
# Activate the environment using your OS's normal command.
python -m pip install -r requirements-build.txt
python packaging/prepare_sources.py --output /path/to/dependency-sources
```

Also obtain the unmodified FFmpeg/libusb archives at the URLs in the manifest.
The supplied x264 archive can be reproduced from the official pinned commit:

```sh
git clone https://code.videolan.org/videolan/x264.git x264-source
git -C x264-source archive --format=tar.gz \
  --prefix=x264-0480cb05fa188d37ae87e8f4fd8f1aea3711f7ee/ \
  --output=/path/to/x264-0480cb05fa188d37ae87e8f4fd8f1aea3711f7ee.tar.gz \
  0480cb05fa188d37ae87e8f4fd8f1aea3711f7ee
```

Register these originals when preparing sources:

```sh
python packaging/prepare_sources.py --output /path/to/dependency-sources \
  --extra-source /path/to/ffmpeg-8.0.tar.xz \
  --extra-source /path/to/libusb-1.0.29.tar.bz2 \
  --x264-source /path/to/x264-0480cb05fa188d37ae87e8f4fd8f1aea3711f7ee.tar.gz \
  --x264-commit 0480cb05fa188d37ae87e8f4fd8f1aea3711f7ee
python packaging/build_media.py --sources /path/to/dependency-sources \
  --work /path/to/new-native-work --output /path/to/native-output
python packaging/prepare_runtime_notices.py --sources /path/to/dependency-sources
python packaging/build.py --sources /path/to/dependency-sources --native /path/to/native-output
```

`build_media.py` is the actual native build recipe. Its manifest records configure
options and output hashes; `native-build-config/` contains FFmpeg's generated
configuration (only machine-specific source paths are replaced with placeholders).
FFmpeg supports raw RGB input, H.264/MP4, FFV1/Matroska, integer nearest-neighbor
scale/pad and file/pipe I/O. It enables GPL/libx264 and disables network, nonfree,
version-3-only features and auto-detected external libraries.
The build first installs static libx264 into its private work prefix. A scoped
x264-only pkg-config adapter prevents accidental use of system codecs. It is a separate process, not linked to the app.
libusb is shared; Linux builds disable libudev to avoid adding that dependency.

`prepare_runtime_notices.py` preserves the complete ICU 73.2 license and
OpenSSL license/copyright originals with version-pinned URLs and SHA-256 records.
For a Windows Python runtime with a different OpenSSL 3.x version, pass
`--openssl-version` with the exact `ssl.OPENSSL_VERSION` patch version.
The native inventory must agree with the supplied notices. Unused Qt Image
Formats plugins are excluded; retained image plugins use QtBase/QtSvg sources.
Both still require their target OS's standard runtime libraries.

On Mac use Apple's free Command Line Tools. Native helpers target macOS 12+.
On Windows run the native helper under MSYS2 UCRT64 with GCC/make/Python;
`build-windows.ps1` handles the Python/Qt app separately on Windows x64.
On Linux use the target distribution's compiler/make and build on the oldest
supported OS baseline. Do not assume a newer glibc binary runs on an older OS.

## Modify/rebuild Qt and the bindings

A C++ toolchain, CMake, Ninja and (for binding generation) libclang are required.
Consult the included Qt/PySide README and source build scripts for platform
requirements and optional dependencies. Use Qt/PySide/Shiboken 6.8.3 together.

Typical QtBase build, in a new build directory:

```sh
/path/to/qtbase-source/configure -opensource -confirm-license -release -shared \
  -nomake examples -nomake tests -prefix /path/to/private-qt-install
cmake --build . --parallel 4
cmake --install .
```

Build QtSvg against that installation with CMake's `CMAKE_PREFIX_PATH`. In the
PySide source directory, the upstream binding build can then be invoked as:

```sh
python setup.py install --qtpaths=/path/to/private-qt-install/bin/qtpaths \
  --ignore-git --parallel=4 --module-subset=Core,Gui,Widgets,Network
```

Use the same Python ABI and target architecture as your app. Install into a
dedicated venv, retain the required Qt plugins, and package using `build.py`.
These are modification/rebuild instructions, not a promise of byte-for-byte
reproduction of Qt's upstream wheels. Exact compiler/feature settings matter;
the original source also includes Qt for Python's `coin/` build infrastructure.

Official references: [Qt 6.8 source builds](https://doc.qt.io/qt-6.8/build-sources.html),
[Qt for Python 6.8 source builds](https://doc.qt.io/qtforpython-6.8/building_from_source/index.html).
See [library replacement](LIBRARY_REPLACEMENT.md) for installation and testing.
