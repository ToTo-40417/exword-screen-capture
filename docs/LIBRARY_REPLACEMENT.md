# Library replacement / ライブラリの差し替え

The application is MIT. Qt/PySide/Shiboken use LGPL-3.0; libusb uses LGPL-2.1-or-later.
The separate FFmpeg/libx264 executable uses GPL-2.0-or-later. You may modify, replace and debug these
components, including reverse engineering for debugging modifications. There is
no license-key check, certificate allowlist or checksum enforcement at runtime.
Build-time integrity checks protect the original distribution, not your modified copy.

## Locations

| Package | Qt / Python bindings | libusb / FFmpeg | Notices and sources |
| --- | --- | --- | --- |
| macOS | `EXwordScreenCapture.app/Contents/Frameworks/` | libusb: `Contents/Frameworks/`; FFmpeg: `Contents/Helpers/ffmpeg` | `Contents/Resources/third-party/` |
| Windows | `EXwordScreenCapture/_internal/`, including `PySide6/Qt/` | `_internal/native/` | `EXwordScreenCapture/third-party/` |
| Linux GUI | `EXwordScreenCapture/_internal/`, including `PySide6/Qt/` | `_internal/native/` | `EXwordScreenCapture/third-party/` |

The exact native-file paths are listed in the package's `*-compliance.json`.
Keep relative symlinks intact. PyInstaller may flatten Qt frameworks or create
symlinks between `Frameworks` and `Resources`; replace the actual file, not just
one symlink. Do not remove the rest of the directory bundle.

## Procedure

For the Windows single-file delivery, first export its included sources, notices
and replaceable-library portable app to a **new** directory:

```powershell
.\EXwordScreenCapture.exe --export-package .\EXwordScreenCapture-portable
```

Use the exported `EXwordScreenCapture.exe` and `_internal/` for the steps below.
Keep `third-party/` for the original sources and notices. Export does not modify
USB drivers. A pre-existing destination is rejected to prevent overwriting files.

1. Quit the app and make a separate copy of its entire directory or `.app`.
2. Build replacement libraries from the supplied sources using
   [DEPENDENCY_BUILD.md](DEPENDENCY_BUILD.md). Keep the target OS/architecture,
   Python ABI, Qt 6.8 ABI, required plugins and compiler runtime compatible.
   A changed API/ABI may also require rebuilding the open application.
3. Replace the appropriate Qt frameworks/shared libraries, PySide/Shiboken bindings
   and plugins together when they depend on each other. libusb is a standalone
   shared library; FFmpeg is a separate executable at the path shown above.
4. For macOS, re-sign each changed native library or executable ad hoc, then the
   containing app. No Apple account or paid certificate is needed:

   ```sh
   codesign --force --sign - "/path/to/replaced/library-or-executable"
   codesign --force --sign - "/path/to/EXwordScreenCapture.app"
   codesign --verify --deep --strict "/path/to/EXwordScreenCapture.app"
   ```

   Sign nested native files before the enclosing app. For newly built libraries,
   preserve relative install names/rpaths; use `otool -L` to check them.
   Permit the unnotarized app through macOS's normal security UI when necessary.
   Do not disable system-wide Gatekeeper or SIP.
5. Run the offline tests, then reconnect the device in projector mode:

   ```sh
   # macOS example: no USB requests are made by these commands.
   "/path/to/EXwordScreenCapture.app/Contents/MacOS/EXwordScreenCapture" --self-test
   "/path/to/EXwordScreenCapture.app/Contents/MacOS/EXwordScreenCapture" --usb-check
   ```

   On Windows/Linux use the corresponding `EXwordScreenCapture.exe` / executable.
   Then test a screenshot and a recording with your own content.

For libusb or FFmpeg you can instead set `EXWORD_LIBUSB` / `EXWORD_FFMPEG` to an
absolute path to your modified library/executable. The GUI otherwise uses its
bundled versions, not system PATH. Source execution and the lightweight Linux
CLI retain their external-library behavior.

## 日本語

Windowsの単体EXE版は、上の `--export-package` コマンドで、対応ソース・
権利表示とライブラリを差し替えられるフォルダ版を新しい場所へ取り出せます。
取り出したフォルダ版を使って以下の作業を行ってください。

アプリを終了し、配布フォルダ全体を複製してから作業してください。同梱ソースから
同じOS・CPU向けにライブラリを再ビルドし、上表の実体ファイルを置き換えます。
Qt・PySide・Shiboken・プラグインは互換性を揃え、必要ならアプリも再ビルドします。
FFmpegは単独の実行ファイル、libusbは共有ライブラリなので、それぞれ独立して差し替えられます。

Macでは変更したライブラリとアプリにad-hoc署名をし直します。Apple Developer登録・
公証は不要ですが、OS側の初回実行許可は必要な場合があります。
改変や、そのためのデバッグ・リバースエンジニアリングを禁止する条件は設けません。
