"""Private integration capture. Never commit the generated device images."""
import argparse
from pathlib import Path
import time

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication

from exword_capture.app import Window
from exword_capture.usb_source import UsbSource

parser = argparse.ArgumentParser()
parser.add_argument("--output", type=Path, required=True)
parser.add_argument("--image", type=Path)
parser.add_argument("--live", action="store_true")
parser.add_argument("--duration", type=float, default=3.2)
parser.add_argument("--wait", type=float, default=240)
parser.add_argument("--keep-listening", action="store_true", help="Stop recording but keep the USB session alive")
args = parser.parse_args()
if bool(args.image) == args.live:
    parser.error("Choose --image or --live (projector mode only)")
args.output.mkdir(parents=True, exist_ok=False)
app = QApplication([])
window = Window(args.image)
window.output = args.output
window.show()
started = time.monotonic()
captured = False
last_sequence = 0
last_status = ""


def check():
    global captured, last_sequence, last_status
    status = window.statusBar().currentMessage()
    if status != last_status:
        last_status = status
        print("STATUS", round(time.monotonic() - started, 3), status, flush=True)
    if not captured and not window.full_image.isNull():
        captured = True
        window.save_image()
        window.grab().save(str(args.output / "gui.png"))
        window.scale.setCurrentIndex(9)
        window.save_image()
        window.scale.setCurrentIndex(0)
        window.toggle_record()
        print("FRAME_CAPTURED", window.full_image.width(), window.full_image.height(), flush=True)
        QTimer.singleShot(int(args.duration * 1000), complete)
    if captured and window.last_sequence != last_sequence:
        last_sequence = window.last_sequence
        window.save_image()
        print("FRAME", last_sequence, round(time.monotonic() - started, 3), flush=True)
    if not captured and time.monotonic() - started > args.wait:
        print("NO_FRAME_TIMEOUT", flush=True)
        complete()


def complete():
    if args.keep_listening and captured:
        window.finish_record()
        print("RECORDING_COMPLETE_RECEIVER_REMAINS_ACTIVE", flush=True)
        return
    window.close()
    app.quit()


if args.live:
    window.source = UsbSource()
    window.source.start()
timer = QTimer()
timer.timeout.connect(check)
timer.start(100)
app.exec()
raise SystemExit(0 if captured else 1)
