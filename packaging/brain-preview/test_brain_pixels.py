import unittest

from brain_pixels import decode_frame
from exword_capture.ohp import Event, ppm_image


class PixelTests(unittest.TestCase):
    def test_all_rgb565_values_match_reference(self):
        payload = b''.join(value.to_bytes(2, 'big') for value in range(65536))
        event = Event('frame', payload=payload,
                      meta={'width': 256, 'height': 256, 'format': '1RC2',
                            'expected_length': len(payload)})
        self.assertEqual(decode_frame(event), ppm_image(event))

    def test_invalid_size_is_rejected(self):
        event = Event('frame', payload=b'\0',
                      meta={'width': 1, 'height': 1, 'format': '1RC2'})
        self.assertIsNone(decode_frame(event))


if __name__ == '__main__':
    unittest.main()
