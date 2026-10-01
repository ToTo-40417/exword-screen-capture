"""Build a replaceable-library bundle and inspect it before packaging."""
import argparse
import importlib.metadata
import json
from pathlib import Path
import platform
import plistlib
import shutil
import stat
import subprocess
import sys
import zipfile

from export_source import source_files
from privacy import audit
from compliance import supply_sources, binary_inventory, image_plugin_supplied, check_runtime_notices
from sanitize_supplier_paths import sanitize

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--sources", type=Path, help="Verified directory created by prepare_sources.py; include corresponding source")
parser.add_argument("--native", type=Path, help="FFmpeg/libusb output from build_media.py; mandatory with --sources")
args = parser.parse_args()
if args.sources and not args.native:
    parser.error("Self-contained release candidates require --native")

root = Path(__file__).absolute().parents[1]
sys.path.insert(0, str(root))
from exword_capture import __version__

command = [sys.executable, "-m", "PyInstaller", "--noconfirm", "--clean", "--onedir",
           "--windowed", "--name", "EXwordScreenCapture"]
icon_png = root / "assets/exword-screen-capture.png"
if not icon_png.is_file():
    raise SystemExit("Application icon missing")
command += ["--add-data", str(icon_png) + ":assets"]
command += ["--add-data", str(root / "assets/exword-screen-capture-256.png") + ":assets"]
if sys.platform == "darwin":
    command += ["--target-arch", "arm64", "--osx-bundle-identifier",
                "io.github.ToTo-40417.exword-screen-capture",
                "--icon", str(root / "assets/exword-screen-capture.icns")]
elif sys.platform == "win32":
    command += ["--version-file", str(root / "packaging/windows-version.txt"),
                "--icon", str(root / "assets/exword-screen-capture.ico")]
command.append(str(root / "launch.py"))
subprocess.run(command, cwd=root, check=True)
bundle = root / "dist" / ("EXwordScreenCapture.app" if sys.platform == "darwin" else "EXwordScreenCapture")
if sys.platform in {"darwin", "linux", "win32"}:
    # Only QtBase and QtSvg sources are supplied. Qt Image Formats plugins
    # (TIFF, WebP, JPEG2000, etc.) belong to a separate source component.
    for candidate in bundle.rglob("*"):
        if (candidate.is_file() or candidate.is_symlink()) and candidate.parent.name == "imageformats" and not image_plugin_supplied(candidate.name):
            candidate.unlink()
if sys.platform == "linux":
    # GUI baseline is X11/XWayland. Keep only required Qt platform plugins;
    # OS display/C runtimes are platform prerequisites, not redistributed libraries.
    for candidate in bundle.rglob("*"):
        if not (candidate.is_file() or candidate.is_symlink()):
            continue
        name = candidate.name
        remove = (candidate.parent.name == "platforms" and name not in {"libqxcb.so", "libqoffscreen.so"})
        remove |= name.startswith(("libQt6Wayland", "libQt6WlShell", "libQt6Qml", "libQt6Quick"))
        remove |= any("wayland" in part.lower() for part in candidate.relative_to(bundle).parts)
        remove |= candidate.parent.name == "_internal" and name.startswith("lib") and ".so" in name and not name.startswith(("libQt6", "libpython", "libpyside", "libshiboken", "libusb"))
        if remove:
            candidate.unlink()
# The PyInstaller USB hook can auto-collect a system backend. Keep libusb external.
for candidate in bundle.rglob("*"):
    if (candidate.is_file() or candidate.is_symlink()) and candidate.name.lower().startswith("libusb") and candidate.suffix.lower() in (".dll", ".dylib", ".so", ".0"):
        candidate.unlink()
native_manifest = None
if args.native:
    native_manifest = json.loads((args.native / "manifest.json").read_text(encoding="utf-8"))
    if native_manifest["ffmpeg_license"] != "GPL-2.0-or-later" or native_manifest["libusb_version"] != "1.0.29":
        raise SystemExit("Unreviewed native runtime")
    native = bundle / ("Contents/Frameworks" if sys.platform == "darwin" else "_internal/native")
    native.mkdir(parents=True, exist_ok=True)
    for entry in native_manifest["files"]:
        source = args.native / entry["filename"]
        import hashlib
        if source.name != entry["filename"] or hashlib.sha256(source.read_bytes()).hexdigest() != entry["sha256"]:
            raise SystemExit("Native runtime checksum mismatch")
        target = bundle / "Contents/Helpers" / source.name if sys.platform == "darwin" and source.name == "ffmpeg" else native / source.name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, target)
        target.chmod(0o755)
    if (args.native / "runtime-notices").is_dir():
        runtime_notices = args.native / "runtime-notices"
    else:
        runtime_notices = None
notices = bundle / ("Contents/Resources/third-party" if sys.platform == "darwin" else "third-party")
notices.mkdir(parents=True, exist_ok=True)
if args.native and runtime_notices:
    shutil.copytree(runtime_notices, notices / "compiler-runtime", dirs_exist_ok=True)
inventory = []
names = ["PySide6-Essentials", "shiboken6", "pyusb", "pyinstaller", "packaging",
         "altgraph", "pyinstaller-hooks-contrib", "setuptools"]
names += ["macholib"] if sys.platform == "darwin" else ["pefile", "pywin32-ctypes"] if sys.platform == "win32" else []
for name in names:
    distribution = importlib.metadata.distribution(name)
    inventory.append({"name": name, "version": distribution.version,
                      "license": distribution.metadata.get("License-Expression") or distribution.metadata.get("License")})
    for entry in distribution.files or []:
        if ("__pycache__" not in entry.parts and entry.suffix not in {".py", ".pyc", ".pyo", ".dll", ".pyd"}
                and any(word in str(entry).lower() for word in ("license", "copying", "notice"))):
            source = Path(distribution.locate_file(entry))
            if source.is_file():
                target = notices / name / str(entry).replace("..", "_parent_")
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(source, target)
# Python's license covers incorporated standard-library components.
python_license = Path(sys.base_prefix) / "lib" / ("python" + platform.python_version_tuple()[0] + "." + platform.python_version_tuple()[1]) / "LICENSE.txt"
if sys.platform == "win32":
    python_license = Path(sys.base_prefix) / "LICENSE.txt"
if not python_license.is_file():
    raise SystemExit("Python LICENSE.txt was not found; refusing an incomplete package.")
shutil.copyfile(python_license, notices / "PYTHON-LICENSE.txt")
# One complete, allowlisted source/document tree preserves every relative link.
# Do not flatten documents or recursively collect unreviewed local notes.
shutil.copyfile(root / "LICENSE", notices / "LICENSE")
(notices / "README.md").write_text(
    "# EX-word Screen Capture — documentation and licenses\n\n"
    "[日本語](application-source/README.md) · [English](application-source/README.en.md) · "
    "[简体中文](application-source/README.zh-CN.md) · [繁體中文](application-source/README.zh-TW.md)\n\n"
    "- [Third-party notices](application-source/THIRD_PARTY_NOTICES.md)\n"
    "- [Licenses and distribution](application-source/docs/LICENSING.md)\n"
    "- [Library replacement](application-source/docs/LIBRARY_REPLACEMENT.md)\n"
    "- [Dependency builds](application-source/docs/DEPENDENCY_BUILD.md)\n"
    "- [Brainux](application-source/docs/BRAINUX.md)\n\n"
    "Original dependency archives and their manifest are in `corresponding-source/`.\n",
    encoding="utf-8")
public_notice_hashes = set()
source_manifest = None
if args.sources:
    source_manifest, public_notice_hashes = supply_sources(args.sources.resolve(), notices)
    for dependency in inventory:
        component = "pyside-setup" if dependency["name"] in ("PySide6-Essentials", "shiboken6") else dependency["name"]
        if not any(record["component"] == component and record["version"] == dependency["version"] for record in source_manifest["records"]):
            raise SystemExit("Source/runtime version mismatch: " + dependency["name"])
    if not any(record["component"] == "cpython" and record["version"] == platform.python_version() for record in source_manifest["records"]):
        raise SystemExit("Missing exact Python runtime source")
    for required in ("ffmpeg", "libusb", "x264"):
        if not any(record["component"] == required for record in source_manifest["records"]):
            raise SystemExit("Missing corresponding source: " + required)
if native_manifest:
    public_notice_hashes.update(entry["sha256"] for entry in native_manifest.get("compiler_runtime_notices", []))
    shutil.copytree(args.native / "build-config", notices / "native-build-config", dirs_exist_ok=True)
(notices / "inventory.json").write_text(json.dumps({
    "application_version": __version__, "python_version": platform.python_version(),
    "os": sys.platform, "architecture": platform.machine(), "dependencies": inventory,
    "public_binary_release_approved": False,
    "corresponding_source_included": bool(source_manifest),
    "native_runtime": native_manifest,
    "source_modifications": "none to dependency sources; application includes Windows build adaptations; PyInstaller adjusts binary load paths and architecture slices",
    "publication": "held; no upload or release is performed by this script",
    "signing": "ad-hoc, not notarized" if sys.platform == "darwin" else "unsigned"}, indent=2) + "\n", encoding="utf-8")
source_root = notices / "application-source"
for source in source_files(root):
    target = source_root / source.relative_to(root)
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(source, target)
if sys.platform == "darwin":
    info = bundle / "Contents/Info.plist"
    with info.open("rb") as stream:
        properties = plistlib.load(stream)
    properties.update(CFBundleShortVersionString=__version__, CFBundleVersion=__version__,
                      CFBundleDisplayName="EX-word Screen Capture",
                      NSHumanReadableCopyright="Copyright 2026 ToTo-40417")
    with info.open("wb") as stream:
        plistlib.dump(properties, stream)
    # Resource additions require an updated ad-hoc seal. No personal identity/cert is used.
    subprocess.run(["/usr/bin/codesign", "--force", "--sign", "-", str(bundle)], check=True)
    subprocess.run(["/usr/bin/codesign", "--verify", "--deep", "--strict", str(bundle)], check=True)
if sys.platform == "win32" and args.native:
    from minimize_windows import minimize
    minimized = minimize(bundle)
    (notices / "windows-runtime-validation.json").write_text(json.dumps(minimized, indent=2) + "\n")
elif sys.platform != "win32":
    redactions = sanitize(bundle)
    (notices / "supplier-path-redactions.json").write_text(json.dumps(redactions, indent=2) + "\n")
    if sys.platform == "darwin":
        subprocess.run(["codesign", "--force", "--sign", "-", str(bundle)], check=True)
        subprocess.run(["codesign", "--verify", "--deep", "--strict", str(bundle)], check=True)
native_inventory = binary_inventory(bundle)
if args.sources:
    import ssl
    openssl_version = ssl.OPENSSL_VERSION.split()[1]
    for entry in native_inventory["native_files"]:
        if Path(entry["path"]).name.lower().startswith("libcrypto"):
            if ("OpenSSL " + openssl_version).encode() not in (bundle / entry["path"]).read_bytes():
                raise SystemExit("Bundled OpenSSL differs from the Python runtime; review its license inventory")
    check_runtime_notices(native_inventory, source_manifest, openssl_version=openssl_version)
artifacts = root / "release-artifacts"
artifacts.mkdir(exist_ok=True)
system = "macos" if sys.platform == "darwin" else "windows" if sys.platform == "win32" else "linux"
architecture = "arm64" if platform.machine().lower() in ("arm64", "aarch64") else "x86_64"
stem = f"EXwordScreenCapture-v{__version__}-{system}-{architecture}"
inspection = audit(bundle, public_notice_hashes=public_notice_hashes,
                   public_source_hashes={r["sha256"] for r in source_manifest["records"]} if source_manifest else ())
(artifacts / (stem + "-privacy.json")).write_text(json.dumps(inspection, indent=2) + "\n", encoding="utf-8")
if not inspection["passed"]:
    raise SystemExit("Bundle privacy inspection failed. See the privacy report.")
(artifacts / (stem + "-compliance.json")).write_text(json.dumps({
    "application_version": __version__, "source_supply": bool(source_manifest),
    "qt_modules": native_inventory["qt_modules"], "native_files": native_inventory["native_files"],
    "native_runtime": native_manifest,
    "privacy_passed": True, "publication": "held",
    "third_party_sources": [{key: record[key] for key in ("component", "version", "filename", "sha256")}
                            for record in source_manifest["records"]] if source_manifest else [],
    "runtime_notices": source_manifest.get("runtime_notices", []) if source_manifest else [],
}, indent=2) + "\n", encoding="utf-8")
# Preserve relative symlinks and executable modes, but not owner IDs, xattrs or timestamps.
output = artifacts / (stem + ".zip")
with zipfile.ZipFile(output, "x", compression=zipfile.ZIP_DEFLATED) as archive:
    for path in sorted(bundle.rglob("*")):
        if path.is_dir() and not path.is_symlink():
            continue
        entry = zipfile.ZipInfo((Path(bundle.name) / path.relative_to(bundle)).as_posix(), (1980, 1, 1, 0, 0, 0))
        if sys.platform == "win32" and len(entry.filename) > 120:
            raise SystemExit("Archive path exceeds Windows extraction budget: " + entry.filename)
        entry.create_system = 3
        if path.is_symlink():
            entry.external_attr = (stat.S_IFLNK | 0o777) << 16
            payload = str(path.readlink()).encode("utf-8")
        else:
            entry.external_attr = (stat.S_IFREG | (0o755 if path.stat().st_mode & 0o111 else 0o644)) << 16
            payload = path.read_bytes()
        archive.writestr(entry, payload, compress_type=zipfile.ZIP_DEFLATED)
print(f"Package: {output.name}")
print("Privacy inspection passed. Corresponding sources included:", bool(source_manifest))
print("Publication held; complete the target-platform verification in docs/LICENSING.md.")
