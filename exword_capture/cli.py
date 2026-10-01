"""Headless capture. No Qt, Pillow, desktop or display server is required."""
import argparse
from datetime import datetime
import json
from pathlib import Path
import queue
import signal
import sys
import threading
import time

from .i18n import LANGUAGES, tr
from .ohp import StreamParser, ppm_image
from .pixels import transform, write_png, VIEWS, FILTERS
from .usb_source import UsbSource, system_backend
from .video import Recorder


def demo_frame():
    width, height = 528, 320
    rgb = bytearray(width * height * 3)
    colors = [(255, 95, 86), (255, 189, 46), (39, 201, 63), (75, 163, 255), (189, 131, 255)]
    for y in range(height):
        for x in range(width):
            color = colors[min(4, x * 5 // width)] if 190 <= y < 254 else ((41, 59, 77) if x % 16 == 0 or y % 16 == 0 else (22, 32, 44))
            index = (y * width + x) * 3
            rgb[index:index + 3] = bytes(color)
    return width, height, bytes(rgb)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--listen", action="store_true", help="Receive projector-mode USB")
    mode.add_argument("--replay", type=Path, help="Decode our own saved OHP packet/stream offline")
    mode.add_argument("--demo", action="store_true", help="Original test pattern; no USB traffic")
    mode.add_argument("--usb-check", action="store_true", help="Check library discovery, not the device")
    parser.add_argument("--projector-mode", action="store_true", help="Confirm device mode before USB enable/ACK")
    parser.add_argument("--output", type=Path, default=Path("captures"))
    parser.add_argument("--scale", type=int, choices=range(1, 11), default=1)
    parser.add_argument("--view", choices=VIEWS, default="all")
    parser.add_argument("--filter", choices=FILTERS, default="none")
    parser.add_argument("--language", choices=tuple(LANGUAGES), default="en")
    parser.add_argument("--snapshot", action="store_true", help="Save each received frame as PNG")
    parser.add_argument("--record", action="store_true", help="Record real-time silent FFV1/Matroska")
    parser.add_argument("--frames", type=int, default=1, help="PNG frame limit; ignored for record-only mode")
    parser.add_argument("--seconds", type=float, default=60, help="Reception budget including initial wait")
    args = parser.parse_args(argv)
    if args.usb_check:
        ready = system_backend() is not None
        print(json.dumps({"libusb": ready, "gui_loaded": any(x.startswith("PySide") for x in sys.modules)}))
        return 0 if ready else 1
    if args.listen and not args.projector_mode:
        parser.error("--listen requires --projector-mode; normal USB transfer mode is not supported")
    if args.frames <= 0 or args.seconds <= 0:
        parser.error("--frames and --seconds must be positive")
    snapshots = args.snapshot or not args.record
    args.output.mkdir(parents=True, exist_ok=True)
    # Session identifiers make repeated runs non-overwriting; log files are exclusive.
    stem = "EXWORD_" + datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    log_path = args.output / (stem + ".jsonl")
    stopped = threading.Event()
    previous_handlers = {}
    if threading.current_thread() is threading.main_thread():
        for signum in (signal.SIGINT, signal.SIGTERM):
            previous_handlers[signum] = signal.signal(signum, lambda *_: stopped.set())
    source = recorder = None
    count = 0
    failed = False
    started = time.monotonic()
    with log_path.open("x", encoding="utf-8") as log:
        def event(kind, **values):
            line = json.dumps({"event": kind, "elapsed_s": round(time.monotonic() - started, 6), **values}, ensure_ascii=False)
            log.write(line + "\n")
            log.flush()
            print(line, flush=True)

        def accept(frame):
            nonlocal count, recorder
            width, height, rgb = transform(*frame, view=args.view, filter_name=args.filter)
            count += 1
            event("frame", index=count, width=width, height=height, scale=args.scale)
            if snapshots and count <= args.frames:
                path = args.output / f"{stem}_{count:05d}.png"
                write_png(path, width, height, rgb, args.scale)
                event("saved", path=str(path))
            if args.record:
                if recorder is None:
                    path = args.output / (stem + ".mkv")
                    recorder = Recorder(path, width, height, rgb, (width * args.scale, height * args.scale))
                    event("recording", path=str(path))
                elif (width, height) != (recorder.width, recorder.height):
                    raise RuntimeError("dimension_error")
                else:
                    recorder.update(rgb)

        try:
            if args.listen:
                source = UsbSource()
                source.start()
                sequence = 0
                while not stopped.is_set() and time.monotonic() - started < args.seconds:
                    while True:
                        try:
                            key, values = source.messages.get_nowait()
                            if key == "error_detail":
                                values["detail"] = tr(args.language, values["detail"])
                            event(key, message=tr(args.language, key, **values))
                        except queue.Empty:
                            break
                    current, frame = source.snapshot()
                    if current != sequence and frame:
                        sequence = current
                        accept(frame)
                    if snapshots and not args.record and count >= args.frames:
                        break
                    if not source.thread.is_alive():
                        if source.connection_state() == "error":
                            failed = True
                        break
                    if recorder and not recorder.thread.is_alive():
                        raise RuntimeError(recorder.error or "Recording ended unexpectedly")
                    stopped.wait(.05)
            elif args.demo:
                accept(demo_frame())
            else:
                stream = StreamParser()
                with args.replay.open("rb") as packet_file:
                    while not stopped.is_set():
                        chunk = packet_file.read(32768)
                        if not chunk:
                            break
                        for decoded in stream.feed(chunk):
                            if decoded.kind == "frame":
                                ppm = ppm_image(decoded)
                                if ppm:
                                    accept((decoded.meta["width"], decoded.meta["height"], ppm.split(b"\n", 3)[3]))
                                    if not args.record and count >= args.frames:
                                        break
                            elif decoded.kind not in ("ack", "check"):
                                event("validation", detail=decoded.kind)
                        if count >= args.frames and not args.record:
                            break
            if args.record and not args.listen and recorder:
                while not stopped.is_set() and time.monotonic() - started < args.seconds:
                    if not recorder.thread.is_alive():
                        raise RuntimeError(recorder.error or "Recording ended unexpectedly")
                    stopped.wait(.05)
        except Exception as error:
            failed = True
            event("error", message=tr(args.language, str(error)))
        finally:
            if recorder:
                recorder.stop()
                if recorder.error:
                    failed = True
                    event("error", message=tr(args.language, recorder.error))
            if source:
                source.stop()
            for signum, handler in previous_handlers.items():
                signal.signal(signum, handler)
            event("complete", frames=count, success=bool(count) and not failed)
    return 0 if count and not failed else 1


if __name__ == "__main__":
    raise SystemExit(main())
