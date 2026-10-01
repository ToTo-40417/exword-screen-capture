"""Native RGB565 conversion; no USB or display operations."""
import ctypes as C
import os
from pathlib import Path

from exword_capture.ohp import ppm_image

library = C.CDLL(os.environ.get('BRAIN_PIXELS_LIBRARY') or
                 str(Path(__file__).with_name('libbrain_pixels.so')))
convert = library.brain_rgb565
convert.restype = None
convert.argtypes = [C.c_char_p, C.c_void_p, C.c_uint]


def decode_frame(event):
    if event.kind != 'frame' or event.meta.get('format') != '1RC2':
        return ppm_image(event)
    width, height = event.meta['width'], event.meta['height']
    count = width * height
    if not (0 < width <= 4096 and 0 < height <= 4096) or len(event.payload) != count * 2:
        return None
    rgb = C.create_string_buffer(count * 3)
    convert(event.payload, rgb, count)
    return f'P6\n{width} {height}\n255\n'.encode('ascii') + rgb.raw
