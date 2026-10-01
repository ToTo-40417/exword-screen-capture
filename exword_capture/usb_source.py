"""Projector-only USB transport. No reset, mount, storage writes or driver detach."""
import queue
import ctypes.util
import os
from pathlib import Path
import sys
import threading
import time

import usb.core
import usb.util
import usb.backend.libusb1

from .ohp import StreamParser, acknowledgement, ppm_image
from .runtime import bundled_libusb


def system_backend():
    """Explicit override, then packaged GUI backend, then source/CLI system backend."""
    def locate(name):
        configured = os.environ.get("EXWORD_LIBUSB")
        if configured:
            return configured
        packaged = bundled_libusb()
        if packaged:
            return packaged
        if getattr(sys, "frozen", False):
            return None
        found = ctypes.util.find_library(name)
        if found:
            return found
        if sys.platform == "darwin":
            for candidate in ("/opt/homebrew/lib/libusb-1.0.dylib",
                              "/usr/local/lib/libusb-1.0.dylib"):
                if Path(candidate).is_file():
                    return candidate
        return None
    return usb.backend.libusb1.get_backend(find_library=locate)


class UsbSource:
    def __init__(self):
        self.stop_event = threading.Event()
        self.lock = threading.Lock()
        self.latest = None
        self.sequence = 0
        self.state = "waiting"
        self.messages = queue.Queue(maxsize=32)
        self.thread = threading.Thread(target=self._run, daemon=True)

    def notice(self, message, **values):
        try:
            self.messages.put_nowait((message, values))
        except queue.Full:
            pass

    def start(self):
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
        self.thread.join(timeout=2)

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
                    self.stop_event.wait(0.1)
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
                            continue
                        for event in parser.feed(chunk):
                            ack = acknowledgement(event)
                            if ack:
                                if device.write(endpoint_out.bEndpointAddress, ack, timeout=300) != len(ack):
                                    raise RuntimeError("partial_ack")
                                self.set_state("connected")
                                self.notice("connected")
                            if event.kind == "frame":
                                ppm = ppm_image(event)
                                if ppm:
                                    self.set_state("connected")
                                    with self.lock:
                                        self.latest = (event.meta["width"], event.meta["height"], ppm.split(b"\n", 3)[3])
                                        self.sequence += 1
                                else:
                                    self.notice("unknown_format")
                            elif event.kind not in ("check", "ack"):
                                self.notice("validation", detail=event.kind)
                except usb.core.USBError as error:
                    if error.errno not in (5, 19):
                        raise
                    self.set_state("waiting")
                    self.notice("idle")
                    self.stop_event.wait(0.2)
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
