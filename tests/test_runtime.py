import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
from exword_capture import runtime


class RuntimeTests(unittest.TestCase):
    def test_frozen_gui_does_not_fall_back_to_path(self):
        with patch.object(sys, "frozen", True, create=True), patch.object(sys, "_MEIPASS", "/nonexistent", create=True), \
                patch.dict(os.environ, {}, clear=True), patch("shutil.which") as which:
            self.assertIsNone(runtime.ffmpeg_executable())
            which.assert_not_called()

    def test_local_helper_precedes_system_path(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "native" / ("ffmpeg.exe" if sys.platform == "win32" else "ffmpeg")
            path.parent.mkdir()
            path.write_bytes(b"synthetic")
            with patch.object(sys, "frozen", True, create=True), patch.object(sys, "_MEIPASS", directory, create=True), \
                    patch.dict(os.environ, {}, clear=True):
                self.assertEqual(runtime.ffmpeg_executable(), str(path))

    def test_user_override_is_allowed(self):
        with patch.dict(os.environ, {"EXWORD_FFMPEG": "/path/to/modified/ffmpeg"}):
            self.assertEqual(runtime.ffmpeg_executable(), "/path/to/modified/ffmpeg")


if __name__ == "__main__":
    unittest.main()
