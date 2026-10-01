import os
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
import shutil
import subprocess
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from PySide6.QtGui import QColor, QImage
from PySide6.QtWidgets import QApplication

from exword_capture.ohp import StreamParser, acknowledgement, checksum, ppm_image
from exword_capture.video import Recorder, integer_fit, frame_index
from exword_capture.app import Window, render_canvas, rgb_bytes
from exword_capture.usb_source import UsbSource


class ProtocolTests(unittest.TestCase):
    def test_real_check(self):
        event = StreamParser().feed(b"\x16DIC00D0")[0]
        self.assertEqual(acknowledgement(event), b"\x06020010D")

    def test_fragmentation_and_pixels(self):
        body = b"TYPZ2" + b"00000004" + b"00010002" + b"1RC2" + b"\xf8\x00\x07\xe0"
        packet = b"\x0b" + body + checksum(body)
        parser = StreamParser()
        events = []
        for byte in packet:
            events.extend(parser.feed(bytes([byte])))
        self.assertEqual(len(events), 1)
        self.assertEqual(ppm_image(events[0]), b"P6\n2 1\n255\n\xff\x00\x00\x00\xff\x00")

    def test_corrupt_frame_never_accepted(self):
        self.assertNotEqual(StreamParser().feed(b"\x16DIC0000")[0].kind, "check")

    def test_unknown_frame_stops_acks(self):
        parser = StreamParser()
        events = parser.feed(b"\x0bTYPXX" + b"\x16DIC00D0")
        self.assertTrue(parser.opaque)
        self.assertFalse(any(acknowledgement(e) for e in events))


class GraphicsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def test_integer_fit_8k(self):
        self.assertEqual(integer_fit(528, 432, 7680, 4320), (10, 1200, 0))
        self.assertEqual(integer_fit(528, 320, 7680, 4320), (10, 1200, 560))
        self.assertEqual(integer_fit(2, 1, 7680, 4320), (10, 3830, 2155))
        with self.assertRaises(ValueError):
            integer_fit(528, 432, 100, 100)

    def test_nearest_neighbor_padding_and_rgb_stride(self):
        image = QImage(2, 1, QImage.Format.Format_RGB888)
        image.setPixelColor(0, 0, QColor("red"))
        image.setPixelColor(1, 0, QColor("green"))
        rendered = render_canvas(image, (6, 4))
        self.assertEqual(rendered.pixelColor(0, 0), QColor("red"))
        self.assertEqual(rendered.pixelColor(2, 2), QColor("red"))
        self.assertEqual(rendered.pixelColor(3, 2), QColor("green"))
        self.assertEqual(rendered.pixelColor(0, 3), QColor("black"))
        self.assertEqual(len(rgb_bytes(image)), 6)

    def test_gui_save_split_fullscreen(self):
        with tempfile.TemporaryDirectory() as directory:
            window = Window()
            window.output = Path(directory)
            image = QImage(528, 432, QImage.Format.Format_RGB888)
            image.fill(QColor("red"))
            window.full_image = image
            window.refresh_view()
            window.save_image()
            window.save_image()
            self.assertEqual(len(list(Path(directory).glob("*.png"))), 2)
            window.view.setCurrentIndex(1)
            self.assertEqual(window.screen.image.height(), 320)
            window.view.setCurrentIndex(2)
            self.assertEqual(window.screen.image.height(), 112)
            window.toggle_fullscreen()
            self.assertTrue(window.isFullScreen())
            window.exit_fullscreen()
            self.assertFalse(window.isFullScreen())
            window.close()

    def test_single_screen_has_no_false_lower_panel(self):
        window = Window()
        window.full_image = QImage(528, 320, QImage.Format.Format_RGB888)
        window.full_image.fill(QColor("blue"))
        window.refresh_view()
        self.assertEqual(window.view.itemText(0), "全体")
        self.assertFalse(window.view.model().item(1).isEnabled())
        self.assertFalse(window.view.model().item(2).isEnabled())
        self.assertEqual(window.screen.image.size(), window.full_image.size())
        window.close()

    def test_languages_and_connection_states(self):
        window = Window()
        for language in ("ja", "en", "zh_CN", "zh_TW"):
            window.set_language(language)
            self.assertTrue(window.save_button.text().endswith("(F8)"))
            self.assertTrue(window.fullscreen_action.text().endswith("(F11)"))
            self.assertEqual(window.scale.itemText(1), "x2")
        window.set_language("en")
        window.source = Mock()
        window.source.connection_state.return_value = "waiting"
        window.update_connection_button()
        self.assertEqual(window.connect_button.text(), "Waiting")
        window.source.connection_state.return_value = "connected"
        window.update_connection_button()
        self.assertEqual(window.connect_button.text(), "Disconnect")
        window.source = None
        window.close()

    def test_filter_and_exact_scale_png(self):
        with tempfile.TemporaryDirectory() as directory:
            window = Window()
            window.output = Path(directory)
            image = QImage(2, 1, QImage.Format.Format_RGB888)
            image.fill(QColor("red"))
            window.full_image = image
            window.set_filter("invert")
            window.scale.setCurrentIndex(3)
            window.save_image()
            saved = QImage(str(next(Path(directory).glob("*.png"))))
            self.assertEqual((saved.width(), saved.height()), (8, 4))
            self.assertEqual(saved.pixelColor(0, 0), QColor("cyan"))
            window.close()


class TransportTests(unittest.TestCase):
    def test_handshake_frame_and_cleanup(self):
        source = UsbSource()
        incoming = Mock(bmAttributes=2, bEndpointAddress=0x82)
        outgoing = Mock(bmAttributes=2, bEndpointAddress=0x01)
        class Interface(list):
            bInterfaceClass = 255
            bInterfaceNumber = 0
        device = Mock()
        device.get_active_configuration.return_value = [Interface([incoming, outgoing])]
        device.is_kernel_driver_active.side_effect = NotImplementedError
        device.write.side_effect = lambda address, data, **kw: len(data)
        body = b"TYPZ200000004000100021RC2\xf8\x00\x07\xe0"
        def read(*args, **kw):
            source.stop_event.set()
            return b"\x16DIC00D0\x0b" + body + checksum(body)
        device.read.side_effect = read
        with patch("exword_capture.usb_source.system_backend", return_value=object()), \
             patch("usb.core.find", return_value=[device]), \
             patch("usb.util.claim_interface") as claim, \
             patch("usb.util.release_interface") as release, \
             patch("usb.util.dispose_resources") as dispose:
            source._run()
            claim.assert_called_once_with(device, 0)
            release.assert_called_once_with(device, 0)
            dispose.assert_called_once_with(device)
        self.assertEqual(source.snapshot(), (1, (2, 1, b"\xff\x00\x00\x00\xff\x00")))
        device.write.assert_called_once_with(0x01, b"\x06020010D", timeout=300)
        device.reset.assert_not_called()
        device.set_configuration.assert_not_called()
        device.detach_kernel_driver.assert_not_called()

    def test_multiple_devices_not_claimed(self):
        source = UsbSource()
        with patch("exword_capture.usb_source.system_backend", return_value=object()), \
             patch("usb.core.find", return_value=[Mock(), Mock()]), \
             patch("usb.util.claim_interface") as claim:
            source._run()
            claim.assert_not_called()


class RecordingTests(unittest.TestCase):
    def test_wall_clock_index(self):
        self.assertEqual(frame_index(3.21, 10), 32)

    @unittest.skipUnless(shutil.which("ffmpeg"), "FFmpeg not installed")
    def test_idle_recording_duration(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "test.mkv"
            recording = Recorder(path, 2, 2, b"\xff\x00\x00" * 4, (8, 8))
            time.sleep(1.1)
            recording.stop()
            self.assertIsNone(recording.error)
            decoded = subprocess.check_output(["ffmpeg", "-v", "error", "-xerror", "-i", str(path),
                                "-f", "rawvideo", "-pix_fmt", "rgb24", "pipe:1"])
            self.assertEqual(len(decoded) % (8 * 8 * 3), 0)
            duration = len(decoded) // (8 * 8 * 3) / 10
            self.assertGreaterEqual(duration, 1.0)
            self.assertLess(duration, 1.5)
            self.assertEqual(decoded, b"\xff\x00\x00" * (len(decoded) // 3))


if __name__ == "__main__":
    unittest.main()
