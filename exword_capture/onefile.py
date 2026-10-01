"""Make the embedded legal materials and replaceable libraries accessible."""
from pathlib import Path
import shutil
import sys


def export_package(destination):
    root = Path(getattr(sys, '_MEIPASS', ''))
    if not getattr(sys, 'frozen', False) or not (root / 'portable-launcher.exe').is_file():
        raise RuntimeError('Package export is available in the Windows one-file build')
    destination = Path(destination).absolute()
    destination.mkdir(parents=True, exist_ok=False)
    internal = destination / '_internal'
    internal.mkdir()
    for entry in root.iterdir():
        if entry.name == 'portable-launcher.exe':
            shutil.copyfile(entry, destination / 'EXwordScreenCapture.exe')
        elif entry.name == 'third-party':
            shutil.copytree(entry, destination / entry.name)
        elif entry.is_dir():
            shutil.copytree(entry, internal / entry.name)
        else:
            shutil.copyfile(entry, internal / entry.name)
