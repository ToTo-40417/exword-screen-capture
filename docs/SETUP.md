# Setup and builds / 接続・ビルド

## Application icon / アプリのアイコン

Macのアプリ、WindowsのEXE、GUIのウィンドウには共通のアイコンを含みます。
Linuxでアプリ一覧にも登録する場合は、展開したGUI版のフォルダで実行してください。

```sh
./EXwordScreenCapture --install-desktop
```

現在のユーザーのアプリ一覧とアイコン領域だけへ登録します（管理者権限は不要）。
そのフォルダを後から移動した場合は、新しい場所から同じコマンドを再実行してください。
This optional Linux command installs the launcher/icon for the current user only.
It is not run automatically by the build or during screen capture.

## GUI / 共通

For source execution: Python 3.11–3.13, libusb 1.0 runtime, and optional FFmpeg for recording.
GUI binary packages include Python, Qt/PySide, libusb and minimal FFmpeg.
They do not require a system Python or extra library installation. The lightweight
Linux CLI wheel retains external libusb/FFmpeg dependencies.
If automatic library discovery fails, set `EXWORD_LIBUSB` to the absolute path
of your installed libusb shared library (`.dll`, `.dylib`, or `.so`).
`python launch.py --usb-check` tests backend discovery without accessing a device.
Create a virtual environment and install the pinned requirements:

```sh
python -m venv .venv
# Linux/macOS
. .venv/bin/activate
python -m pip install -r requirements.txt
python launch.py
```

Windows PowerShell: activate with `.venv\Scripts\Activate.ps1` instead.
Offline preview is available with `python launch.py --image own-image.png`;
this does not issue USB requests.

通常のUSB転送ソフトと同時に接続しないでください。本体は1台だけ接続します。
アプリで受信待機を開始してから本体のプロジェクター接続を選ぶと、短い接続待ち時間に対応できます。
Do not run another USB transfer tool simultaneously. Connect only one dictionary.
Start listening first, then select projector mode to avoid the short handshake timeout.

## Linux

The supplied x86_64 GUI bundle is built on Debian 13 and requires glibc 2.38
or later, plus an X11/XWayland desktop stack. This is not a universal Linux
binary. On an older distribution, build from source on that system or use the
separate CLI package with compatible system dependencies.

Debian/Ubuntu example:

```sh
sudo apt install python3-venv libusb-1.0-0 ffmpeg
```

### Headless CLI / 軽量環境向けCLI

GUIなしの独立パッケージです。Qt・Pillow・X11/Waylandは不要です。
Python依存はPyUSBのみで、PNGは標準ライブラリで保存します。
録画しない場合はFFmpegも不要です。Python 3.9以上を対象とし、3.13で検証しています。

This package runs without Qt, Pillow or a display server. It requires Python
3.9+ (tested on 3.13) and PyUSB; external libusb is required for USB and FFmpeg
only for recording. Large integer scales still require adequate CPU/storage.

```sh
python3 -m venv .venv-cli
. .venv-cli/bin/activate
python -m pip install .
exword-capture --usb-check
exword-capture --listen --projector-mode --snapshot --seconds 60
exword-capture --listen --projector-mode --record --seconds 30 --scale 2
exword-capture --help
```

Build the separately installable wheel on the development machine:

```sh
python packaging/build_cli.py
# Install the generated .whl from dist-cli/ on the target machine.
```

The wheel does not install Qt by default. GUI support is an optional `[gui]`
extra; its entry point explains the missing dependency if invoked without it.
CLI output includes a session JSONL log. Ctrl+C or SIGTERM finalizes recording.
The `--seconds` limit includes the initial connection wait; `--frames` limits
PNG files, while recording continues until stopped or timed out.

GUIなしの試験:

```sh
python -m unittest discover -s tests -p test_headless.py -v
exword-capture --demo --output captures
```

For non-root USB access, an administrator may install `packaging/60-exword-capture.rules`
in `/etc/udev/rules.d/`, reload udev rules and reconnect the device in an active local desktop session.
Do not run the full GUI as root for routine use. SSH-only sessions may not receive
`uaccess` permissions; choose a locally managed group rule if necessary.

## macOS

For source execution, install Python and libusb using your preferred package manager; recording also
requires FFmpeg. For Homebrew, the relevant packages are `python`, `libusb`, `ffmpeg`.
Installing these changes your Mac environment and is not done automatically by this project.
Use Python and libraries of the same CPU architecture (Apple Silicon arm64 or Intel x86_64).
Unsigned local `.app` builds may need explicit user approval to open. Signing/notarization
is a separate distribution step and is not configured here.

## Windows

For source execution, install matching-architecture Python and a libusb runtime from the
[official project](https://libusb.info/). PyUSB must be able to locate `libusb-1.0.dll`.
Recording needs `ffmpeg.exe` on PATH.

The Windows GUI delivery is a single `EXwordScreenCapture.exe`. It includes the
runtime libraries, but the target USB must separately use WinUSB. Follow
[Windows USB setup / Windowsの接続準備](WINDOWS_USB.md) to identify the device,
record its original driver, assign WinUSB and restore the driver if needed.
Changing the driver can affect CASIO's normal transfer software.
XD-Y4900 projector-mode screen reception and display were verified on Windows
with WinUSB assigned.

## Packaging / パッケージ化

Build on each target OS; PyInstaller is not a cross-compiler:

The v1.0.0 macOS bundle targets Apple Silicon (arm64) and macOS 12 or later
(the pinned Qt wheel's baseline). Intel Mac builds require a separate x86_64
Python environment and are not produced by this arm64 build helper.
Windows builds target x64; the [E130 handoff script](WINDOWS_BUILD.md)
downloads source, builds on Windows, and returns sanitized artifacts.

```sh
python -m pip install -r requirements-build.txt
python packaging/build.py --sources /path/to/dependency-sources --native /path/to/native-output
```

Output is a directory bundle on Windows/Linux and an application bundle on macOS.
The helper stamps v1.0.0 application metadata, includes notices and application
source, inspects the bundle including frozen Python bytecode, and creates an
owner-free ZIP in `release-artifacts/`. A failed privacy gate prevents packaging.
macOS uses ad-hoc signing without a personal certificate; it is not notarized.
See [DEPENDENCY_BUILD.md](DEPENDENCY_BUILD.md) for source acquisition and native
helpers. Self-contained candidates include original corresponding sources,
copyright/license notices and [replacement instructions](LIBRARY_REPLACEMENT.md).
The manual CI matrix creates test artifacts only; no release/push is automatic.
Target-platform checks in [LICENSING.md](LICENSING.md) remain separate from a build.

GUI packages still require the target OS's standard libraries. Linux needs a
compatible glibc and GUI/display stack; device permissions are not supplied by
bundling libusb. Windows needs a compatible USB driver. Unnotarized Mac apps may
need explicit initial approval through the system UI; do not disable Gatekeeper.

## Tests / 試験

```sh
# Linux headless example
QT_QPA_PLATFORM=offscreen python -m unittest discover -s tests -v
```

Protocol tests are synthetic. Actual captured screens are private and never included
in the source or build archives.
