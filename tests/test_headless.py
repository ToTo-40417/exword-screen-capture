"""Tests which require no Qt or display server. Run in a CLI-only environment."""
import contextlib
import io
from pathlib import Path
import struct
import sys
import tempfile
import unittest
import zlib

from exword_capture.cli import main
from exword_capture.i18n import ROWS, LANGUAGES, tr
from exword_capture.pixels import transform, write_png
from exword_capture.ohp import checksum


def decode_png(path):
    data = path.read_bytes()
    position = 8
    packed = b""
    dims = None
    while position < len(data):
        length = struct.unpack(">I", data[position:position + 4])[0]
        kind = data[position + 4:position + 8]
        body = data[position + 8:position + 8 + length]
        crc = struct.unpack(">I", data[position + 8 + length:position + 12 + length])[0]
        assert crc == zlib.crc32(kind + body) & 0xffffffff
        if kind == b"IHDR":
            dims = struct.unpack(">II", body[:8])
        if kind == b"IDAT":
            packed += body
        position += 12 + length
    return dims, zlib.decompress(packed)


class HeadlessTests(unittest.TestCase):
    def test_streaming_png_replicates_whole_pixels(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "test.png"
            write_png(path, 2, 1, b"\xff\0\0\0\xff\0", 3)
            dims, rows = decode_png(path)
            self.assertEqual(dims, (6, 3))
            self.assertEqual(rows, (b"\0" + b"\xff\0\0" * 3 + b"\0\xff\0" * 3) * 3)
            with self.assertRaises(FileExistsError):
                write_png(path, 2, 1, b"\0" * 6)

    def test_filters_and_view_validation(self):
        self.assertEqual(transform(1, 1, b"\xff\0\0", filter_name="invert"), (1, 1, b"\0\xff\xff"))
        self.assertEqual(transform(1, 1, b"\xff\0\0", filter_name="grayscale")[2], bytes((76,) * 3))
        with self.assertRaises(ValueError):
            transform(528, 320, bytes(528 * 320 * 3), view="lower")

    def test_locale_keys_complete(self):
        for key, row in ROWS.items():
            self.assertEqual(len(row), len(LANGUAGES), key)
            self.assertTrue(all(row), key)
        self.assertEqual(tr("en", "waiting"), "Waiting")

    def test_offline_cli_replay(self):
        with tempfile.TemporaryDirectory() as directory:
            packet = Path(directory) / "test.packet"
            body = b"TYPZ200000004000100021RC2\xf8\x00\x07\xe0"
            packet.write_bytes(b"\x0b" + body + checksum(body))
            output = Path(directory) / "captures"
            with contextlib.redirect_stdout(io.StringIO()):
                result = main(["--replay", str(packet), "--output", str(output), "--scale", "2"])
            self.assertEqual(result, 0)
            self.assertEqual(decode_png(next(output.glob("*.png")))[0], (4, 2))

    def test_cli_requires_projector_confirmation(self):
        with contextlib.redirect_stderr(io.StringIO()):
            with self.assertRaises(SystemExit) as error:
                main(["--listen"])
        self.assertEqual(error.exception.code, 2)


if __name__ == "__main__":
    unittest.main()
