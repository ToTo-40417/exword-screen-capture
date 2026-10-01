# Build from the verified, minimized portable tree, never recollect system DLLs.
import os
from pathlib import Path

root = Path(os.environ['EXWORD_SOURCE_ROOT'])
stage = Path(os.environ['EXWORD_ONEFILE_STAGE'])
a = Analysis([str(root / 'launch.py')], pathex=[str(root)],
             binaries=[], datas=[], hiddenimports=[], hookspath=[],
             hooksconfig={}, runtime_hooks=[],
             excludes=['PySide6.QtNetwork', '_hashlib'], noarchive=False, optimize=0)
pyz = PYZ(a.pure)
curated = []
for path in sorted((stage / '_internal').rglob('*')):
    if path.is_file():
        relative = path.relative_to(stage / '_internal').as_posix()
        kind = 'BINARY' if path.suffix.lower() in {'.dll', '.pyd', '.exe'} else 'DATA'
        curated.append((relative, str(path), kind))
for path in sorted((stage / 'third-party').rglob('*')):
    if path.is_file():
        curated.append((path.relative_to(stage).as_posix(), str(path), 'DATA'))
curated.append(('portable-launcher.exe', str(stage / 'EXwordScreenCapture.exe'), 'DATA'))
exe = EXE(pyz, a.scripts, curated, name='EXwordScreenCapture',
          debug=False, bootloader_ignore_signals=False, strip=False, upx=False,
          console=False, disable_windowed_traceback=False,
          version=str(root / 'packaging/windows-version.txt'),
          icon=str(root / 'assets/exword-screen-capture.ico'))
