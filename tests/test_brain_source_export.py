"""Brain source export contains portable inputs, not private build records."""
import importlib.util
from pathlib import Path
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("capture_source_export", ROOT / "packaging/export_source.py")
import sys
sys.path.insert(0, str(ROOT / "packaging"))
export = importlib.util.module_from_spec(spec)
spec.loader.exec_module(export)


class BrainSourceTests(unittest.TestCase):
    def test_unreviewed_extension_compatible_files_excluded(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            for name in ("docs/private.md", "assets/private.png", "packaging/private.txt"):
                path = root / name
                path.parent.mkdir(parents=True, exist_ok=True)
                path.touch()
                self.assertNotIn(path, export.source_files(root))

    def test_allowlisted_file_and_parent_symlinks_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder) / "source"
            root.mkdir()
            outside = Path(folder) / "outside"
            outside.mkdir()
            (outside / "README.md").touch()
            (root / "README.md").symlink_to(outside / "README.md")
            with self.assertRaises(ValueError):
                export.source_files(root)
            (root / "README.md").unlink()
            (root / "docs").symlink_to(outside, target_is_directory=True)
            with self.assertRaises(ValueError):
                export.source_files(root)

    def test_all_adapter_inputs_exist(self):
        files = export.source_files(ROOT)
        for name in export.BRAIN_FILES:
            target = ROOT / "packaging/brain-preview" / name
            self.assertIn(target, files)
            self.assertTrue(target.is_file())

    def test_private_records_and_binaries_excluded(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            brain = root / "packaging/brain-preview"
            brain.mkdir(parents=True)
            names = ("EXWORD-BRAIN-LIVE-PREVIEW.md", "libbrain_pixels.so", "libbrain_pixels-test.so", "private.txt")
            for name in names:
                (brain / name).touch()
            files = export.source_files(root)
            for name in names:
                self.assertNotIn(brain / name, files)


if __name__ == "__main__":
    unittest.main()
