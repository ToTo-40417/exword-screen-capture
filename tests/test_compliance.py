"""Release gates for sources and indirectly bundled Qt runtime components."""
import hashlib
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest


spec = importlib.util.spec_from_file_location("capture_compliance", Path(__file__).resolve().parents[1] / "packaging/compliance.py")
compliance = importlib.util.module_from_spec(spec)
spec.loader.exec_module(compliance)


class ComplianceTests(unittest.TestCase):
    def test_image_formats_source_boundary(self):
        for name in ("libqgif.so", "libqico.dylib", "qjpeg.dll", "libqsvg.so"):
            self.assertTrue(compliance.image_plugin_supplied(name))
        with tempfile.TemporaryDirectory() as directory:
            plugin = Path(directory) / "PySide6/plugins/imageformats/libqwebp.so"
            plugin.parent.mkdir(parents=True)
            plugin.write_bytes(b"\x7fELFsynthetic")
            with self.assertRaisesRegex(RuntimeError, "Unsupplied Qt image plugin"):
                compliance.binary_inventory(Path(directory))

    def test_indirect_libraries_require_exact_notices(self):
        inventory = {"native_files": [{"path": "_internal/libicuuc.so.73"}, {"path": "_internal/libcrypto.so.3"}]}
        with self.assertRaisesRegex(RuntimeError, "Missing runtime notices"):
            compliance.check_runtime_notices(inventory, {"runtime_notices": []})
        notices = [{"component": "icu", "version": "73.2"}, {"component": "openssl", "version": "3.0.15"}]
        compliance.check_runtime_notices(inventory, {"runtime_notices": notices})

    def test_notice_copy_preserves_bytes_and_rejects_tampering(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "source"
            (source / "archives").mkdir(parents=True)
            (source / "runtime-notices").mkdir()
            original = b"Original supplier notice\n"
            runtime = source / "runtime-notices/icu-73.2.txt"
            runtime.write_bytes(original)
            records = []
            for component in ("qtbase", "qtsvg", "pyside-setup", "pyinstaller", "cpython", "pyusb"):
                archive = source / "archives" / (component + ".tar")
                archive.write_bytes(b"fixture")
                records.append({"component": component, "version": "6.8.3", "upstream_sha256_verified": True,
                                "filename": archive.name, "sha256": compliance.sha256(archive), "notices": []})
            notice = {"component": "icu", "version": "73.2", "path": "runtime-notices/icu-73.2.txt",
                      "sha256": hashlib.sha256(original).hexdigest(), "url": "https://example.invalid/fixture"}
            (source / "manifest.json").write_text(json.dumps({"records": records, "runtime_notices": [notice]}))
            destination = Path(directory) / "notices"
            manifest, hashes = compliance.supply_sources(source, destination)
            self.assertEqual((destination / "corresponding-source" / notice["path"]).read_bytes(), original)
            self.assertIn(notice["sha256"], hashes)
            self.assertEqual(manifest["runtime_notices"], [notice])
            runtime.write_bytes(b"modified")
            with self.assertRaisesRegex(RuntimeError, "Modified runtime copyright/license notice"):
                compliance.supply_sources(source, Path(directory) / "rejected")
