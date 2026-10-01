"""Explicit opt-in packaged-GUI check. Captures remain private."""
import json
import subprocess
import time
from pathlib import Path
from PySide6.QtWidgets import QApplication
from .gui import Window
from .usb_source import UsbSource
from .runtime import ffmpeg_executable


def capture_check(directory, seconds):
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=False)
    window = Window(preferences=False)
    window.output = directory
    receiver = UsbSource()
    window.source = receiver
    receiver.start()
    window.show()
    recorder = None
    recording_started = None
    report = {"physical_usb": True, "png": False, "recording": False,
              "private_capture": True, "recording_format": "H.264/MP4"}
    started = time.monotonic()
    try:
        while time.monotonic() - started < seconds:
            QApplication.processEvents()
            window.poll()
            if recorder is None and not window.screen.image.isNull():
                width, height = window.screen.image.width(), window.screen.image.height()
                window.save_image()
                report.update(png=bool(list(directory.glob("*.png"))), width=width, height=height)
                window.scale.setCurrentIndex(4)
                assert window.record_scale == 1 and window.record_format == "h264"
                window.toggle_record()
                recorder = window.recorder
                if recorder is None:
                    raise RuntimeError("GUI recording did not start")
                recording_started = time.monotonic()
                report.update(display_scale=5, record_scale=window.record_scale,
                              recording_scale_independent=True, video=window.record_path.name)
            if recording_started and time.monotonic() - recording_started >= 10:
                break
            if receiver.connection_state() == "error":
                raise RuntimeError("USB receiver stopped with an error")
            time.sleep(0.02)
    finally:
        if recorder:
            window.finish_record()
            report.update(recording=recorder.error is None and recorder.frames > 0,
                          recorded_frames=recorder.frames, recording_error=recorder.error)
            if report["recording"]:
                decoded = subprocess.check_output([ffmpeg_executable(), "-v", "error", "-xerror",
                           "-i", str(window.record_path), "-f", "rawvideo", "-pix_fmt", "rgb24", "pipe:1"],
                           timeout=30, creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
                expected = (report["width"] + report["width"] % 2) * (report["height"] + report["height"] % 2) * 3
                report["full_decode_verified"] = len(decoded) == recorder.frames * expected
        report["source_frames"] = receiver.snapshot()[0]
        report["connection_state"] = receiver.connection_state()
        window.close()
        (directory / "result.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report))
    return report["png"] and report["recording"] and report.get("full_decode_verified", False)
