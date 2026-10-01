"""Acquire original dependency sources with upstream integrity receipts; no publication."""
import argparse
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
import re
from pathlib import Path, PurePosixPath
import tarfile
import urllib.request
import xml.etree.ElementTree as ET
import zipfile

PYPI = {"pyusb": "1.3.1", "pyinstaller": "6.16.0", "pyinstaller-hooks-contrib": "2026.8",
        "altgraph": "0.17.5", "packaging": "26.3", "setuptools": "84.0.0",
        "macholib": "1.16.4", "pefile": "2023.2.7", "pywin32-ctypes": "0.2.3"}
QT = {
    "qtbase": "https://download.qt.io/archive/qt/6.8/6.8.3/submodules/qtbase-everywhere-src-6.8.3.tar.xz",
    "qtsvg": "https://download.qt.io/archive/qt/6.8/6.8.3/submodules/qtsvg-everywhere-src-6.8.3.tar.xz",
    "pyside-setup": "https://download.qt.io/official_releases/QtForPython/pyside6/PySide6-6.8.3-src/pyside-setup-everywhere-src-6.8.3.tar.xz",
}


def get(url):
    with urllib.request.urlopen(url, timeout=90) as response:
        return response.read()


def digest(data):
    return hashlib.sha256(data).hexdigest()


def notices(path):
    """Read, never execute or extract, upstream license/attribution files."""
    def selected(name):
        name = PurePosixPath(name)
        return not name.is_absolute() and ".." not in name.parts and (
            any(word in name.name.lower() for word in ("license", "copying", "notice", "copyright"))
            or "LICENSES" in name.parts or name.as_posix().endswith(".reuse/dep5")
            or name.name in ("AUTHORS", "qt_attribution.json"))
    if path.suffix == ".zip":
        with zipfile.ZipFile(path) as archive:
            for member in archive.infolist():
                if not member.is_dir() and selected(member.filename):
                    yield member.filename, archive.read(member)
    else:
        with tarfile.open(path) as archive:
            for member in archive:
                if member.isfile() and selected(member.name):
                    yield member.name, archive.extractfile(member).read()


def acquire(item, output):
    name, version, url, expected, receipt_url = item
    filename = url.rsplit("/", 1)[-1]
    path = output / "archives" / filename
    data = path.read_bytes() if path.is_file() else get(url)
    actual = digest(data)
    if expected and actual != expected:
        raise RuntimeError("Upstream SHA-256 mismatch: " + filename)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)
    notice_list = []
    for member, payload in notices(path):
        target = output / "notices" / name / member
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(payload)
        notice_list.append({"path": target.relative_to(output).as_posix(), "sha256": digest(payload)})
    print("Verified source:", filename, flush=True)
    return {"component": name, "version": version, "filename": filename,
            "url": url, "sha256": actual, "bytes": len(data),
            "integrity_receipt": receipt_url, "upstream_sha256_verified": bool(expected),
            "modified": False, "notices": notice_list}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--python-version", default="3.12.14")
    parser.add_argument("--x264-source", type=Path, help="Unmodified git archive from the pinned official x264 commit")
    parser.add_argument("--x264-commit", help="Full 40-character official x264 commit")
    parser.add_argument("--add-x264-only", action="store_true", help="Keep existing verified sources; register x264 only")
    parser.add_argument("--extra-source", type=Path, action="append", default=[],
                        help="Original ffmpeg-8.0.tar.xz or libusb-1.0.29.tar.bz2")
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    if bool(args.x264_source) != bool(args.x264_commit) or (args.x264_commit and not re.fullmatch(r"[0-9a-f]{40}", args.x264_commit)):
        parser.error("Supply both --x264-source and a full --x264-commit")
    if args.add_x264_only:
        if not args.x264_source:
            parser.error("--add-x264-only requires x264 source/commit")
        manifest = json.loads((args.output / "manifest.json").read_text())
        register_x264(args, manifest)
        (args.output / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
        return
    items = []
    for name, url in QT.items():
        receipt = url + ".meta4"
        metadata = ET.fromstring(get(receipt))
        expected = metadata.find(".//{urn:ietf:params:xml:ns:metalink}hash[@type='sha-256']").text
        items.append((name, "6.8.3", url, expected, receipt))
    for name, version in PYPI.items():
        receipt = f"https://pypi.org/pypi/{name}/{version}/json"
        metadata = json.loads(get(receipt))
        source = next(entry for entry in metadata["urls"] if entry["packagetype"] == "sdist")
        items.append((name, version, source["url"], source["digests"]["sha256"], receipt))
    # PSF terms do not require corresponding source; include it as useful build material.
    version = args.python_version
    if not all(part.isdigit() for part in version.split(".")) or len(version.split(".")) != 3:
        parser.error("Use a numeric Python x.y.z version")
    items.append(("cpython", version, f"https://www.python.org/ftp/python/{version}/Python-{version}.tar.xz", None,
                  "https://www.python.org/downloads/release/python-" + version.replace(".", "") + "/"))
    with ThreadPoolExecutor(max_workers=4) as executor:
        records = list(executor.map(lambda item: acquire(item, args.output), items))
    extras = {
        "ffmpeg-8.0.tar.xz": ("ffmpeg", "8.0", "https://ffmpeg.org/releases/ffmpeg-8.0.tar.xz"),
        "libusb-1.0.29.tar.bz2": ("libusb", "1.0.29", "https://github.com/libusb/libusb/releases/download/v1.0.29/libusb-1.0.29.tar.bz2"),
    }
    for source in args.extra_source:
        name, version, url = extras[source.name]
        target = args.output / "archives" / source.name
        target.write_bytes(source.read_bytes())
        records.append(acquire((name, version, url, None, url), args.output))
    manifest = {"schema": 1, "qt_version": "6.8.3", "pyside_version": "6.8.3",
                "source_modifications": "none", "records": sorted(records, key=lambda record: record["component"])}
    if args.x264_source:
        register_x264(args, manifest)
    (args.output / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print("All dependency sources acquired; manifest.json written.")


def register_x264(args, manifest):
    import shutil
    filename = "x264-" + args.x264_commit + ".tar.gz"
    target = args.output / "archives" / filename
    if args.x264_source.resolve() != target.resolve():
        shutil.copyfile(args.x264_source, target)
    notice_list = []
    for member, payload in notices(target):
        path = args.output / "notices/x264" / member
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(payload)
        notice_list.append({"path": path.relative_to(args.output).as_posix(), "sha256": digest(payload)})
    record = {"component": "x264", "version": args.x264_commit, "git_commit": args.x264_commit,
              "filename": filename, "url": "https://code.videolan.org/videolan/x264.git",
              "sha256": digest(target.read_bytes()), "bytes": target.stat().st_size,
              "integrity_receipt": "Pinned git commit; local git archive SHA-256, not an upstream archive checksum",
              "upstream_sha256_verified": False, "modified": False, "notices": notice_list}
    manifest["records"] = sorted([r for r in manifest["records"] if r["component"] != "x264"] + [record], key=lambda r: r["component"])


if __name__ == "__main__":
    main()
