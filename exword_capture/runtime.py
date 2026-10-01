"""Frozen GUI dependencies are local; source/CLI retain external-library support."""
import os
from pathlib import Path
import shutil
import sys


def application_icon():
    root = Path(sys._MEIPASS) if getattr(sys, "frozen", False) else Path(__file__).resolve().parents[1]
    return root / "assets/exword-screen-capture.png"


def bundled_path(name):
    if not getattr(sys, "frozen", False):
        return None
    path = Path(sys._MEIPASS) / "native" / name
    if sys.platform == "darwin" and not path.is_file():
        path = Path(sys._MEIPASS).parent / "Helpers" / name if name == "ffmpeg" else Path(sys._MEIPASS) / name
    return str(path) if path.is_file() else None


def bundled_libusb():
    name = "libusb-1.0.dll" if sys.platform == "win32" else "libusb-1.0.0.dylib" if sys.platform == "darwin" else "libusb-1.0.so.0"
    return bundled_path(name)


def ffmpeg_executable():
    configured = os.environ.get("EXWORD_FFMPEG")
    if configured:
        return configured
    if getattr(sys, "frozen", False):
        return bundled_path("ffmpeg.exe" if sys.platform == "win32" else "ffmpeg")
    return shutil.which("ffmpeg")
