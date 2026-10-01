# License review / ライセンス確認

Reviewed 2026-10-01. This project's original source is MIT, copyright ToTo-40417.
Dependency copyrights and licenses remain with their respective authors.

## Research and implementation

- [Cahute 0.6](https://gitlab.com/cahuteproject/cahute), inspected checkout `63f3b523c839d177397cca7a598cf8d5d6a18b65`: **CeCILL-2.1** (`LICENSE.txt`).
- Its [OHP packet specification](https://cahute.org/topics/protocols/seven-ohp/packet-format.html), [flows](https://cahute.org/topics/protocols/seven-ohp/flows.html), and [USB transport](https://cahute.org/topics/protocols/transport.html) informed protocol interpretation.
- This app uses the project's independently written stream parser and USB receiver. It does **not** bundle or link Cahute, copy its parser, or reproduce documentation prose. The `DIC00` handshake and `TYPZ2 / 1RC2` 528×432 reception were verified on our own XD-N6500.
- Referencing documented byte layouts does not make Cahute's software license this project's license. Any future incorporation of Cahute code needs a new compatibility review; do not silently label it MIT.
- CASIO firmware, NAND dumps, dictionaries, fonts, private Discord exports, credentials, and captured device screens are **not** repository assets. A user's right to record a screen does not automatically grant redistribution rights to the content displayed.
- Dictionary-screen captures from this investigation must not be published. Public UI previews use only original synthetic test images.

## Runtime components

| Component | Use | License / distribution boundary |
| --- | --- | --- |
| PyUSB 1.3.1 | USB API | [BSD-3-Clause](https://github.com/pyusb/pyusb/blob/v1.3.1/LICENSE); preserve notice and disclaimer |
| libusb 1.0.29 | Bundled GUI USB backend; external for source/CLI | [LGPL-2.1-or-later](https://github.com/libusb/libusb/blob/v1.0.29/COPYING); shared, replaceable |
| PySide6 Essentials / Shiboken 6.8.3 | QtCore, QtGui, QtWidgets GUI | LGPL-3.0 option; inspect installed distribution licenses and Qt's transitive notices |
| Python | Runtime | [PSF license and incorporated component notices](https://docs.python.org/3/license.html) |
| FFmpeg 8.0 | Bundled GUI recorder; external for source/CLI | [GPL-2.0-or-later](https://ffmpeg.org/legal.html); separate executable with statically linked GPL libx264; no nonfree/version-3-only features |
| PyInstaller 6.16.0 | Build only | [GPL-2.0-or-later with bundling exception](https://pyinstaller.org/en/stable/license.html); does not force application code to GPL |

Only Qt Essentials modules are used; no GPL-only Qt add-ons are intentionally imported.
The default CLI package depends on PyUSB only and does not install or import Qt.
Its PNG encoder is independently written using the Python standard library.
The optional GUI extra and GUI binary bundles retain the Qt-related obligations below.
See [Qt for Python licensing](https://doc.qt.io/qtforpython-6/licenses.html) and [Qt LGPL obligations](https://www.qt.io/licensing/open-source-lgpl-obligations).
GUI recording defaults to H.264/MP4 via libx264; FFV1/MKV remains selectable.
GUI candidates include the exact pinned libx264 source and our GPL FFmpeg build;
source/CLI users' installed FFmpeg builds retain their own build-dependent licenses.

## Source publication versus binary distribution

The independently authored source can be published under MIT with these references.
Packaged builds are **unpublished release candidates**. No legal certification or
patent clearance is claimed. No commercial contract, paid signing or notarization is used.
Self-contained GUI distributions must include Python/dependency notices,
first-party source and the corresponding original source archives for the
redistributed LGPL/GPL components, including any additional Qt image plugins.
Build options and installation/replacement instructions must also be included.
The distribution method is source delivery with the binary, not a future written offer
or an upstream-homepage-only link. Preserve the sources when redistributing the package.
Public upstream author attribution in Python's standard library is retained and
distinguished from the builder's private email/path or physical-device identifiers.
The privacy gate verifies such attribution against exact hashes from upstream
CPython's `Lib/io.py` and `Lib/bz2.py`; it does not exempt arbitrary license-file email.
The application prominently identifies LGPL components under **Settings → Licenses**.
Qt, bindings and libusb remain dynamically replaceable. FFmpeg is a replaceable
standalone process with its complete source and build recipe. Modification,
replacement and reverse engineering for debugging those modifications are allowed.
There is no runtime hash lock, paid certificate requirement or restrictive EULA.

Before publishing binaries:

1. Include exact installed dependency copyright/license texts and notices (the build helper collects them), including Qt's transitive components and Python.
2. Keep `third-party/corresponding-source/` in each binary package, including the exportable Windows single-file EXE. The manifest must match the redistributed versions and original archive hashes. Keep `application-source/`, native build configuration and this documentation. Downloaded originals retain all source license terms; upstream binary build recipes are present in PySide's `coin/` scripts.
3. Keep dynamic Qt libraries replaceable; use directory bundles or the Windows one-file exportable portable tree. Do not prohibit debugging/reverse engineering for LGPL-library modifications.
4. Audit each target's final native file inventory and dynamic dependencies; unreviewed Qt modules or undeclared external runtime libraries must block that candidate. FFmpeg must report GPL version 2 or later, with no nonfree or version-3-only features. Source archives also contain tools/examples under other licenses; those are not compiled into this app.
5. Keep recordings and private device data out of release archives.

6. Verify startup, PNG/recording and library replacement on each target; report
   physical USB checks separately. Windows USB drivers, Linux device permissions
   and OS standard runtimes remain prerequisites even though extra libraries are bundled.

See [source/build instructions](DEPENDENCY_BUILD.md) and
[library replacement](LIBRARY_REPLACEMENT.md). The generated compliance JSON
records actual native-file paths/hashes and the matching source list. A successful
build is not approval to publish; uploading remains a separate user action.

## 日本語

独自に作成したアプリのソースはMITで公開可能な構成です。Cahuteは仕様の参照元であり、コードや資料本文は取り込んでいません。
Qt等の権利は各作者に残ります。配布バイナリには、対象バージョンのライセンス・著作権表示、対応ソースの提供方法、ライブラリを差し替えられる構成などの確認が別途必要です。
対応ソース原本は配布候補パッケージへ同梱し、ライセンス・著作権表示を保持します。
ライブラリの差し替え手順も同梱し、変更・そのための解析を禁止しません。
公開直前までの技術的な準備であり、法的適合の保証や公証ではありません。
本体画面、辞書データ、NAND、私的なログは公開対象に含めません。
