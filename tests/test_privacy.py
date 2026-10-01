"""Privacy gate tests using synthetic fixtures, never real private information."""
import importlib.util
import hashlib
import io
import marshal
from pathlib import Path
import struct
import tarfile
import tempfile
import unittest
from unittest.mock import patch
import zipfile
import zlib

module_path = Path(__file__).resolve().parents[1] / "packaging/privacy.py"
spec = importlib.util.spec_from_file_location("capture_privacy", module_path)
privacy = importlib.util.module_from_spec(spec)
spec.loader.exec_module(privacy)


class PrivacyTests(unittest.TestCase):
    def check_bytes(self, data, name="input.bin", **kwargs):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / name
            path.write_bytes(data)
            return privacy.audit(path, **kwargs)

    @staticmethod
    def zip_bytes(name, data):
        result = io.BytesIO()
        with zipfile.ZipFile(result, "w", compression=zipfile.ZIP_DEFLATED) as archive:
            archive.writestr(name, data)
        return result.getvalue()

    @staticmethod
    def frozen_bytes(payload, name="module", prefix=b"MZ"):
        data = zlib.compress(payload)
        filename = name.encode() + b"\0"
        toc = struct.pack("!IIIIBc", 18 + len(filename), 0, len(data), len(payload), 1, b"z") + filename
        cookie = struct.pack("!8sIIII64s", privacy.PYINSTALLER_MAGIC,
                             len(data) + len(toc) + 88, len(data), len(toc), 312, b"python312.dll")
        return prefix + data + toc + cookie

    def test_versioned_frozen_executable_and_nested_pyz(self):
        marker = b"synthetic-frozen-private-marker"
        payload = zlib.compress(marker)
        toc = marshal.dumps({"module": (0, 12, len(payload))})
        pyz = b"PYZ\0" + b"0000" + struct.pack("!i", 12 + len(payload)) + payload + toc
        result = self.check_bytes(self.frozen_bytes(pyz, "PYZ.pyz"),
                                  "renamed-v1.exe", denied=[marker.decode()])
        self.assertFalse(result["passed"])
        self.assertTrue(any("PYZ.pyz/module" in f["file"] for f in result["findings"]))

    def test_nested_zip_tar_and_member_names(self):
        tar = io.BytesIO()
        with tarfile.open(fileobj=tar, mode="w:gz") as archive:
            info = tarfile.TarInfo("safe.txt")
            data = b"synthetic-nested-private-marker"
            info.size = len(data)
            archive.addfile(info, io.BytesIO(data))
        nested = self.zip_bytes("inner.zip", self.zip_bytes("source.tar.gz", tar.getvalue()))
        self.assertFalse(self.check_bytes(nested, denied=[data.decode()])["passed"])
        for name in ("captures/screen.png", ".git/config", "../safe.txt", "synthetic-name-marker.txt"):
            self.assertFalse(self.check_bytes(self.zip_bytes(name, b"safe"),
                                               denied=["synthetic-name-marker"])["passed"])

    def test_limits_and_broken_pyinstaller_are_explicit(self):
        with patch.object(privacy, "MAX_DEPTH", 0):
            result = self.check_bytes(self.zip_bytes("inner.zip", self.zip_bytes("safe.txt", b"safe")))
        self.assertTrue(any("inspection_limit" in f["rules"] for f in result["findings"]))
        with patch.object(privacy, "MAX_OBJECT_BYTES", 10):
            self.assertFalse(self.check_bytes(b"x" * 11)["passed"])
        self.assertFalse(self.check_bytes(b"MZ" + privacy.PYINSTALLER_MAGIC, "renamed.exe")["passed"])
        self.assertTrue(self.check_bytes(b"MZordinary native DLL", "ordinary.dll")["passed"])

    def test_verified_upstream_archive_attribution_retains_secret_checks(self):
        upstream = self.zip_bytes("notice.txt", b"synthetic.upstream" + b"@" + b"gmail.com "
                                  + b"/" + b"home/" + b"public-author/source")
        digest = hashlib.sha256(upstream).hexdigest()
        self.assertFalse(self.check_bytes(upstream)["passed"])
        self.assertTrue(self.check_bytes(upstream, public_source_hashes={digest})["passed"])
        self.assertFalse(self.check_bytes(upstream, public_source_hashes={digest},
                                          denied=["public-author"])["passed"])
        secret = self.zip_bytes("notice.txt", b"ghp_" + b"A" * 35)
        self.assertFalse(self.check_bytes(secret, public_source_hashes={hashlib.sha256(secret).hexdigest()})["passed"])

    def test_archive_links_cannot_escape(self):
        result = io.BytesIO()
        with zipfile.ZipFile(result, "w") as archive:
            entry = zipfile.ZipInfo("dir/link")
            entry.create_system = 3
            entry.external_attr = 0o120777 << 16
            archive.writestr(entry, "../../outside")
        self.assertFalse(self.check_bytes(result.getvalue())["passed"])

    def test_verified_original_fixtures_are_reported_without_hiding_builder_data(self):
        key = b"-----BEGIN RSA PRIVATE KEY-----\n" + b"A" * 80 + b"\n-----END RSA PRIVATE KEY-----"
        original = self.zip_bytes("upstream/tests/certs/test.key", key)
        result = self.check_bytes(original, public_source_hashes={hashlib.sha256(original).hexdigest()})
        self.assertTrue(result["passed"])
        self.assertGreater(result["public_source_finding_count"], 0)
        self.assertFalse(self.check_bytes(original)["passed"])
        application = self.zip_bytes("upstream/application.key", key)
        self.assertFalse(self.check_bytes(application, public_source_hashes={hashlib.sha256(application).hexdigest()})["passed"])
        malformed = self.zip_bytes("upstream/tests/broken.tar", b"not a tar archive")
        result = self.check_bytes(malformed, public_source_hashes={hashlib.sha256(malformed).hexdigest()})
        self.assertTrue(result["passed"])
        self.assertTrue(any("inspection_error" in f["rules"][0] for f in result["public_source_findings"]))
        containing_builder = self.zip_bytes("upstream/tests/broken.tar", b"synthetic-builder-private-data")
        self.assertFalse(self.check_bytes(containing_builder,
                         public_source_hashes={hashlib.sha256(containing_builder).hexdigest()},
                         denied=["synthetic-builder-private-data"])["passed"])
        modified = original + b"modified-source"
        self.assertFalse(self.check_bytes(modified, public_source_hashes={hashlib.sha256(original).hexdigest()})["passed"])

    def test_tar_owner_metadata_is_checked(self):
        archive = io.BytesIO()
        with tarfile.open(fileobj=archive, mode="w") as tar:
            entry = tarfile.TarInfo("safe.txt")
            entry.uname = "synthetic-private-owner"
            tar.addfile(entry, io.BytesIO())
        self.assertFalse(self.check_bytes(archive.getvalue(), denied=[entry.uname])["passed"])

    def test_private_marker_inside_compressed_zip(self):
        with tempfile.TemporaryDirectory() as directory:
            archive = Path(directory) / "packed.zip"
            marker = "synthetic-builder-marker"
            with zipfile.ZipFile(archive, "w", compression=zipfile.ZIP_DEFLATED) as output:
                output.writestr("module.pyc", marker.encode())
            result = privacy.audit(archive, [marker])
            self.assertFalse(result["passed"])
            self.assertTrue(any("!/module.pyc" in finding["file"] for finding in result["findings"]))

    def test_pem_header_without_key_is_not_a_credential(self):
        header = b"-----BEGIN " + b"RSA PRIVATE KEY-----"
        self.assertIsNone(privacy.SENSITIVE_KEY.search(header))
        complete = header + b"\n" + b"A" * 80 + b"\n-----END " + b"RSA PRIVATE KEY-----"
        self.assertIsNotNone(privacy.SENSITIVE_KEY.search(complete))

    def test_unrecognized_email_is_not_exempted_by_license_path(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "LICENSE"
            path.write_bytes(b"synthetic.author" + b"@" + b"gmail.com")
            self.assertFalse(privacy.audit(path)["passed"])

    def test_source_version_matches_package_metadata(self):
        import tomllib
        from exword_capture import __version__
        root = module_path.parents[1]
        metadata = tomllib.loads((root / "pyproject.toml").read_text(encoding="utf-8"))
        self.assertEqual(__version__, metadata["project"]["version"])

    def test_exact_upstream_notice_does_not_disable_private_marker_check(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "notice.txt"
            data = b"synthetic-author" + b"@" + b"gmail.com"
            path.write_bytes(data)
            hashes = {hashlib.sha256(data).hexdigest()}
            self.assertTrue(privacy.audit(path, public_notice_hashes=hashes)["passed"])
            self.assertFalse(privacy.audit(path, ["synthetic-author"], public_notice_hashes=hashes)["passed"])


if __name__ == "__main__":
    unittest.main()
