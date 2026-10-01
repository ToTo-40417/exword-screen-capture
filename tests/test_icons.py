from pathlib import Path
import struct
import shlex
import tempfile
import unittest
from exword_capture.desktop import install_launcher, APP_ID
from exword_capture.runtime import application_icon

ROOT = Path(__file__).resolve().parents[1]


class IconTests(unittest.TestCase):
    def test_os_formats(self):
        png = application_icon().read_bytes()
        self.assertEqual(png[:8], b"\x89PNG\r\n\x1a\n")
        ico = (ROOT / "assets/exword-screen-capture.ico").read_bytes()
        reserved, kind, count = struct.unpack("<HHH", ico[:6])
        self.assertEqual((reserved, kind, count), (0, 1, 7))
        sizes = []
        for index in range(count):
            width, height, _, _, planes, bits, length, offset = struct.unpack("<BBBBHHII", ico[6 + index * 16:22 + index * 16])
            self.assertEqual((planes, bits), (1, 32))
            self.assertEqual(ico[offset:offset + 8], b"\x89PNG\r\n\x1a\n")
            self.assertLessEqual(offset + length, len(ico))
            sizes.append(width or 256)
        self.assertEqual(sizes, [16, 24, 32, 48, 64, 128, 256])
        icns = (ROOT / "assets/exword-screen-capture.icns").read_bytes()
        self.assertEqual(icns[:4], b"icns")
        self.assertEqual(struct.unpack(">I", icns[4:8])[0], len(icns))

    def test_linux_desktop_local_only(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            executable = root / "App Folder/EXwordScreenCapture"
            executable.parent.mkdir()
            executable.touch()
            icon = ROOT / "assets/exword-screen-capture-256.png"
            data = root / "user-data"
            launcher = install_launcher(executable, icon, data)
            self.assertEqual(launcher.parent, data / "applications")
            text = launcher.read_text(encoding="utf-8")
            exec_line = next(line[5:] for line in text.splitlines() if line.startswith("Exec="))
            command = shlex.split(exec_line.replace("\\\\", "\\"))
            self.assertEqual(command, [str(executable.resolve())])
            self.assertIn(f"Icon={APP_ID}", text)
            self.assertEqual((data / f"icons/hicolor/256x256/apps/{APP_ID}.png").read_bytes(), icon.read_bytes())


if __name__ == "__main__":
    unittest.main()
