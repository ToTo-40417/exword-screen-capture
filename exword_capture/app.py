"""Optional desktop entry point; never imported by the headless CLI."""
import argparse
from pathlib import Path
import sys
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QRect, Qt
from PySide6.QtGui import QImage, QPainter, QIcon
from .gui import Window, rgb_bytes
from .video import integer_fit


def render_canvas(image, canvas):
    """Compatibility helper for integer letterboxed export tests."""
    if canvas is None:
        return image.copy()
    width, height = canvas
    factor, x, y = integer_fit(image.width(), image.height(), width, height)
    result = QImage(width, height, QImage.Format.Format_RGB888)
    result.fill(Qt.GlobalColor.black)
    painter = QPainter(result)
    painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, False)
    painter.drawImage(QRect(x, y, image.width() * factor, image.height() * factor), image)
    painter.end()
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--image", type=Path, help="Offline preview; no USB traffic")
    parser.add_argument("--usb-check", action="store_true", help="Check backend only; no device requests")
    parser.add_argument("--self-test", action="store_true", help="Offline packaged-GUI and PNG smoke test; no USB")
    parser.add_argument("--export-package", type=Path, help="Export included materials and replaceable libraries to a new directory")
    parser.add_argument("--install-desktop", action="store_true", help="Linux only: install an application-menu entry and icon for the current user")
    parser.add_argument("--capture-test", type=Path, help="Opt-in GUI/USB/PNG/recording test; new private output directory")
    parser.add_argument("--projector-mode", action="store_true", help="Confirm projector mode for --capture-test")
    parser.add_argument("--seconds", type=int, default=20, help="Capture-test duration, 1–120 seconds")
    args = parser.parse_args()
    if args.install_desktop:
        if sys.platform != "linux" or not getattr(sys, "frozen", False):
            parser.error("--install-desktop is available in the packaged Linux GUI only")
        import os
        from .desktop import install_launcher
        from .runtime import application_icon
        icon = application_icon().with_name("exword-screen-capture-256.png")
        data_home = Path(os.environ.get("XDG_DATA_HOME", str(Path.home() / ".local/share")))
        print(install_launcher(sys.executable, icon, data_home))
        return
    if args.export_package:
        from .onefile import export_package
        export_package(args.export_package)
        return
    if args.capture_test and (not args.projector_mode or not 1 <= args.seconds <= 120):
        parser.error("--capture-test requires --projector-mode and --seconds 1–120")
    if args.usb_check:
        from .usb_source import system_backend
        ready = system_backend() is not None
        print("libusb backend:", "OK" if ready else "NOT FOUND")
        raise SystemExit(0 if ready else 1)
    app = QApplication(sys.argv[:1])
    from .runtime import application_icon
    app.setWindowIcon(QIcon(str(application_icon())))
    app.setDesktopFileName("io.github.ToTo-40417.exword-screen-capture")
    if args.capture_test:
        from .verification import capture_check
        raise SystemExit(0 if capture_check(args.capture_test, args.seconds) else 1)
    if args.self_test:
        import json
        import tempfile
        from . import __version__
        from .pixels import write_png
        from .i18n import LANGUAGES
        window = Window(preferences=False)
        assert not app.windowIcon().isNull(), "Application icon failed to load"
        image = QImage(2, 2, QImage.Format.Format_RGB888)
        image.fill(Qt.GlobalColor.red)
        window.full_image = image
        window.refresh_view()
        window.show()
        app.processEvents()
        for language in LANGUAGES:
            window.set_language(language)
            assert window.save_button.text().endswith("(F8)")
        with tempfile.TemporaryDirectory(prefix="exword-self-test-") as directory:
            path = Path(directory) / "test.png"
            write_png(path, 2, 2, rgb_bytes(window.screen.image), 2)
            assert QImage(str(path)).size().width() == 4
            if getattr(sys, "frozen", False):
                import time
                from .video import Recorder
                from .usb_source import system_backend
                assert system_backend() is not None, "Bundled libusb failed to load"
                import subprocess
                from .runtime import ffmpeg_executable
                for extension in ("mp4", "mkv"):
                    recording = Path(directory) / ("test." + extension)
                    recorder = Recorder(recording, 16, 16, b"\xff\x00\x00" * 256, canvas=(36, 36))
                    time.sleep(0.35)
                    recorder.stop()
                    assert recorder.error is None, recorder.error
                    assert recording.stat().st_size > 256 and recorder.frames > 0
                    decoded = subprocess.run([ffmpeg_executable(), "-v", "error", "-xerror", "-i", str(recording),
                                              "-f", "rawvideo", "-pix_fmt", "rgb24", "pipe:1"],
                                             capture_output=True, timeout=15, check=True,
                                             creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
                    assert len(decoded.stdout) == recorder.frames * 36 * 36 * 3
        window.close()
        print(json.dumps({"version": __version__, "gui": True, "png": True,
                          "languages": len(LANGUAGES), "usb_accessed": False,
                          "application_icon": not app.windowIcon().isNull(),
                          "bundled_recording": bool(getattr(sys, "frozen", False)),
                          "recording_formats": ["H.264/MP4", "FFV1/MKV"] if getattr(sys, "frozen", False) else [],
                          "full_decode_verified": bool(getattr(sys, "frozen", False))}))
        return
    window = Window(args.image, preferences=True)
    window.show()
    sys.exit(app.exec())
