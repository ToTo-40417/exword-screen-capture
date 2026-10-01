"""Projector-only USB transport. No reset, mount, storage writes or driver detach."""
import queue
import ctypes.util
import os
import threading
import time

import usb.core
import usb.util
import usb.backend.libusb1

from exword_capture.ohp import StreamParser, acknowledgement
from brain_pixels import decode_frame as ppm_image


def system_backend():
    """Works in source and frozen apps; backend library stays external."""
    return usb.backend.libusb1.get_backend(
        find_library=lambda name: os.environ.get("EXWORD_LIBUSB") or ctypes.util.find_library(name))


class UsbSource:
    def __init__(self):
        self.stop_event = threading.Event()
        self.lock = threading.Lock()
        self.latest = None
        self.sequence = 0
        self.state = "waiting"
        self.messages = queue.Queue(maxsize=32)
        self.thread = threading.Thread(target=self._run, daemon=True)
        self.received_bytes = 0
        self.received_frames = 0
        self.decoded_frames = 0
        self.last_decode = 0.0
        self.last_report = 0.0
        self.decode_seconds = 0.0
        self.pending = None
        self.decode_wake = threading.Event()
        self.decoder = threading.Thread(target=self._decode, daemon=True)

    def _decode(self):
        while not self.stop_event.is_set():
            self.decode_wake.wait(0.25)
            if not self.decode_wake.is_set():
                continue
            if self.stop_event.wait(max(0, 0.1 - (time.monotonic() - self.last_decode))):
                break
            with self.lock:
                event, self.pending = self.pending, None
                self.decode_wake.clear()
            if event is None:
                continue
            self.last_decode = time.monotonic()
            try:
                ppm = ppm_image(event)
                self.decode_seconds = time.monotonic() - self.last_decode
                if ppm:
                    with self.lock:
                        self.latest = (event.meta["width"], event.meta["height"], ppm.split(b"\n", 3)[3])
                        self.sequence += 1
                        self.decoded_frames += 1
                else:
                    self.notice("unknown_format")
            except Exception as error:
                self.notice("decode_error", detail=str(error))
                self.stop_event.set()

    def report(self, parser):
        now = time.monotonic()
        if now - self.last_report >= 10:
            self.last_report = now
            self.notice("transport", bytes=self.received_bytes,
                        received=self.received_frames, decoded=self.decoded_frames,
                        decode_seconds=round(self.decode_seconds, 3),
                        buffered=len(parser.buffer), opaque=parser.opaque,
                        discarded=parser.discarded)

    def notice(self, message, **values):
        try:
            self.messages.put_nowait((message, values))
        except queue.Full:
            pass

    def start(self):
        self.decoder.start()
        self.thread.start()

    def snapshot(self):
        with self.lock:
            return self.sequence, self.latest

    def connection_state(self):
        with self.lock:
            return self.state

    def set_state(self, state):
        with self.lock:
            self.state = state

    def stop(self):
        self.stop_event.set()
        self.decode_wake.set()
        self.thread.join(timeout=2)
        self.decoder.join(timeout=2)

    def _run(self):
        self.notice("idle")
        try:
            # A frozen app's PyInstaller USB hook otherwise searches only inside
            # its bundle. Supply an explicit system-library resolver.
            backend = system_backend()
            if backend is None:
                raise RuntimeError("libusb_not_found")
            while not self.stop_event.is_set():
                devices = list(usb.core.find(find_all=True, idVendor=0x07cf, idProduct=0x6101, backend=backend))
                if len(devices) > 1:
                    raise RuntimeError("multiple_devices")
                if not devices:
                    self.stop_event.wait(1.0)
                    continue
                device = devices[0]
                claimed, interface_number = False, None
                try:
                    config = device.get_active_configuration()
                    candidates = []
                    for interface in config:
                        ins = [e for e in interface if usb.util.endpoint_type(e.bmAttributes) == 2
                               and usb.util.endpoint_direction(e.bEndpointAddress) == usb.util.ENDPOINT_IN]
                        outs = [e for e in interface if usb.util.endpoint_type(e.bmAttributes) == 2
                                and usb.util.endpoint_direction(e.bEndpointAddress) == usb.util.ENDPOINT_OUT]
                        if interface.bInterfaceClass == 255 and len(ins) == len(outs) == 1:
                            candidates.append((interface.bInterfaceNumber, ins[0], outs[0]))
                    if len(candidates) != 1:
                        raise RuntimeError("interface_not_found")
                    interface_number, endpoint_in, endpoint_out = candidates[0]
                    # Some backends (notably Windows) do not implement this query.
                    try:
                        if device.is_kernel_driver_active(interface_number):
                            raise RuntimeError("driver_active")
                    except NotImplementedError:
                        pass
                    usb.util.claim_interface(device, interface_number)
                    claimed = True
                    device.ctrl_transfer(0x41, 1, 0, 0, b"", timeout=300)
                    parser = StreamParser()
                    while not self.stop_event.is_set():
                        try:
                            chunk = bytes(device.read(endpoint_in.bEndpointAddress, 32768, timeout=250))
                        except usb.core.USBTimeoutError:
                            self.report(parser)
                            continue
                        self.received_bytes += len(chunk)
                        for event in parser.feed(chunk):
                            ack = acknowledgement(event)
                            if ack:
                                if device.write(endpoint_out.bEndpointAddress, ack, timeout=300) != len(ack):
                                    raise RuntimeError("partial_ack")
                                self.set_state("connected")
                                self.notice("connected")
                            if event.kind == "frame":
                                self.received_frames += 1
                                self.set_state("connected")
                                # Keep the newest validated packet, including the final update.
                                with self.lock:
                                    self.pending = event
                                    self.decode_wake.set()
                            elif event.kind not in ("check", "ack"):
                                self.notice("validation", detail=event.kind)
                        self.report(parser)
                except usb.core.USBError as error:
                    if error.errno not in (5, 19):
                        raise
                    self.set_state("waiting")
                    self.notice("idle", detail=str(error), errno=error.errno)
                    self.stop_event.wait(1.0)
                finally:
                    if claimed:
                        try:
                            usb.util.release_interface(device, interface_number)
                        except usb.core.USBError:
                            pass
                    usb.util.dispose_resources(device)
        except Exception as error:
            self.set_state("error")
            self.notice("error_detail", detail=str(error))
        finally:
            if self.stop_event.is_set():
                self.set_state("stopped")
