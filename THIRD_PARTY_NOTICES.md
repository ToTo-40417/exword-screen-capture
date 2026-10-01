# Third-party notices

This application uses PySide6/Qt and Shiboken under the LGPL-3.0 option,
and PyUSB under BSD-3-Clause. Python and transitive components retain their
own notices. libusb 1.0.29 uses LGPL-2.1-or-later. The standalone FFmpeg 8.0 and its
statically linked libx264 use GPL-2.0-or-later.
See [the license review](docs/LICENSING.md).

Self-contained GUI distributions must include extracted original copyright/license
notices and all applicable corresponding source archives in `third-party/`:
`corresponding-source/archives/` and its version/hash manifest. The Qt/PySide
archives include incorporated third-party sources and build scripts. The application
source, native build configuration and replacement instructions are also included.
Sources are delivered inside the distribution package, not by a promise of a later download.
The Windows single-file EXE can export its bundled package as described in
[library replacement](docs/LIBRARY_REPLACEMENT.md).

Qt modules/plugins, PySide/Shiboken bindings and libusb are dynamically loaded.
FFmpeg is a separate, replaceable GPL executable with libx264 for H.264 encoding.
Nonfree and version-3-only features and auto-detected external libraries are disabled.
Complete FFmpeg/libx264 sources, notices and build recipes are supplied. Their authors'
rights remain intact; none are claimed as original project code.

You may modify/replace these components and reverse engineer to debug those
modifications. No restrictive EULA, certificate whitelist or runtime hash check
is imposed. Mac modifications can be signed ad hoc, without an Apple account.

The lightweight Linux CLI and source execution continue to use external libusb/
FFmpeg. Cahute is a protocol-research reference, not a linked component.

Original source archives retain all of their license texts, including licenses
for tools/examples not used by the app. Alternative commercial terms present in
the originals are not selected. Consult `LICENSING.md`, `DEPENDENCY_BUILD.md`
and `LIBRARY_REPLACEMENT.md` under `docs/` for the distribution scope.
