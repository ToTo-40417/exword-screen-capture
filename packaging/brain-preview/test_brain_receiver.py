"""Brain adapter tests; run with the core package on PYTHONPATH."""
import threading
import time
import unittest
from unittest.mock import patch

from brain_usb_source import UsbSource
from exword_capture.ohp import Event


class DecoderTests(unittest.TestCase):
    def test_latest_packet_survives_rate_limit(self):
        source = UsbSource()
        decoded = []
        ready = threading.Event()

        def convert(event):
            decoded.append((time.monotonic(), event.payload))
            ready.set()
            return b'P6\n1 1\n255\n' + event.payload

        def submit(rgb):
            with source.lock:
                source.pending = Event('frame', payload=rgb, meta={'width': 1, 'height': 1})
                source.decode_wake.set()

        with patch('brain_usb_source.ppm_image', side_effect=convert):
            source.decoder.start()
            try:
                submit(b'\xff\0\0')
                self.assertTrue(ready.wait(2))
                ready.clear()
                submit(b'\0\xff\0')
                submit(b'\0\0\xff')
                self.assertTrue(ready.wait(2))
                deadline = time.monotonic() + 1
                while source.snapshot()[0] < 2 and time.monotonic() < deadline:
                    time.sleep(0.01)
                self.assertEqual(source.snapshot(), (2, (1, 1, b'\0\0\xff')))
                self.assertEqual(len(decoded), 2)
                self.assertGreaterEqual(decoded[1][0] - decoded[0][0], 0.09)
            finally:
                source.stop_event.set()
                source.decode_wake.set()
                source.decoder.join(2)
        self.assertFalse(source.decoder.is_alive())


if __name__ == '__main__':
    unittest.main()
