import tempfile
from pathlib import Path
import subprocess
import time
import unittest
from exword_capture.i18n import LANGUAGES, tr
from exword_capture.video import Recorder


class RecordingOptionsTests(unittest.TestCase):
    def test_repository_link_precedes_disclaimer(self):
        for language in LANGUAGES:
            text = tr(language, "licenses_text")
            lines = text.splitlines()
            self.assertEqual(lines[-2], "https://github.com/ToTo-40417/exword-screen-capture")
            self.assertIn("CASIO", lines[-1])
            self.assertNotIn("--export-package", text)

    def test_gui_recording_independent_of_display_scale(self):
        from PySide6.QtWidgets import QApplication
        from exword_capture.gui import Window
        app = QApplication.instance() or QApplication([])
        window = Window(preferences=False)
        window.scale.setCurrentIndex(9)
        self.assertEqual(window.record_scale, 1)
        self.assertEqual(window.record_format, "h264")
        window.close()

    def test_invalid_codec(self):
        with self.assertRaises(ValueError):
            Recorder("test.xyz", 2, 2, b"\0" * 12, codec="invalid")


if __name__ == "__main__":
    unittest.main()
