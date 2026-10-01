"""Bundle verified original sources and inspect the actual dynamic-library inventory."""
import hashlib
import json
from pathlib import Path
import shutil


def image_plugin_supplied(name):
    """Plugins whose implementations are in the supplied QtBase/QtSvg sources."""
    stem = name.lower().split(".")[0]
    if stem.startswith("lib"):
        stem = stem[3:]
    return stem in {"qgif", "qico", "qjpeg", "qsvg"}


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def supply_sources(source_directory, notices):
    manifest_path = source_directory / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    records = {record["component"]: record for record in manifest["records"]}
    for required in ("qtbase", "qtsvg", "pyside-setup", "pyinstaller", "cpython", "pyusb"):
        if required not in records:
            raise RuntimeError("Missing source: " + required)
    for name in ("qtbase", "qtsvg", "pyside-setup"):
        if records[name]["version"] != "6.8.3" or not records[name]["upstream_sha256_verified"]:
            raise RuntimeError("Qt source version/integrity mismatch")
    destination = notices / "corresponding-source"
    destination.mkdir(parents=True, exist_ok=True)
    public_hashes = set()
    for record in manifest["records"]:
        original = source_directory / "archives" / record["filename"]
        if original.name != record["filename"] or sha256(original) != record["sha256"]:
            raise RuntimeError("Source integrity mismatch: " + record["component"])
        target = destination / "archives" / original.name
        target.parent.mkdir(exist_ok=True)
        shutil.copyfile(original, target)
        for index, notice in enumerate(record["notices"]):
            relative = Path(notice["path"])
            if relative.is_absolute() or ".." in relative.parts:
                raise RuntimeError("Unsafe notice path")
            original_notice = source_directory / relative
            if sha256(original_notice) != notice["sha256"]:
                raise RuntimeError("Modified upstream copyright/license notice")
            short_relative = Path("notices") / record["component"] / (str(index).zfill(3) + ".txt")
            target = destination / short_relative
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(original_notice, target)
            public_hashes.add(notice["sha256"])
            notice["original_path"] = notice["path"]
            notice["path"] = short_relative.as_posix()
    for notice in manifest.get("runtime_notices", []):
        relative = Path(notice["path"])
        if relative.is_absolute() or ".." in relative.parts:
            raise RuntimeError("Unsafe runtime notice path")
        original_notice = source_directory / relative
        if sha256(original_notice) != notice["sha256"]:
            raise RuntimeError("Modified runtime copyright/license notice")
        target = destination / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(original_notice, target)
        public_hashes.add(notice["sha256"])
    (destination / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    return manifest, public_hashes


def binary_inventory(bundle):
    result = []
    qt_names = set()
    for path in sorted(bundle.rglob("*")):
        if (path.is_file() or path.is_symlink()) and path.parent.name == "imageformats" and not image_plugin_supplied(path.name):
            raise RuntimeError("Unsupplied Qt image plugin: " + path.relative_to(bundle).as_posix())
        if path.is_symlink() or not path.is_file():
            continue
        data = path.read_bytes()
        native = data[:4] in (b"\xcf\xfa\xed\xfe", b"\xce\xfa\xed\xfe", b"\xca\xfe\xba\xbe", b"\xca\xfe\xba\xbf", b"\x7fELF") or data[:2] == b"MZ"
        if not native:
            continue
        name = path.name
        if name.startswith("Qt") and name[2:3].isupper():
            qt_names.add(name.split(".")[0])
        elif name.startswith("Qt6"):
            qt_names.add("Qt" + name[3:].split(".")[0])
        elif name.startswith("libQt6"):
            qt_names.add("Qt" + name[6:].split(".")[0])
        result.append({"path": path.relative_to(bundle).as_posix(), "bytes": len(data),
                       "sha256": hashlib.sha256(data).hexdigest()})
    # These modules and their bundled plugins are supplied by qtbase + qtsvg.
    allowed = {"QtCore", "QtGui", "QtWidgets", "QtNetwork", "QtDBus", "QtSvg", "QtXcbQpa", "QtOpenGL", "QtEglFSDeviceIntegration", "QtEglFsKmsSupport"}
    unknown = qt_names - allowed
    if unknown:
        raise RuntimeError("Unreviewed Qt modules: " + ", ".join(sorted(unknown)))
    return {"qt_modules": sorted(qt_names), "native_files": result}


def check_runtime_notices(native_inventory, source_manifest, openssl_version="3.0.15"):
    """Require the matching notices for supplied indirect runtime libraries."""
    records = {(record["component"], record["version"])
               for record in (source_manifest or {}).get("runtime_notices", [])}
    names = {Path(entry["path"]).name.lower() for entry in native_inventory["native_files"]}
    required = set()
    if any(name.startswith("libicu") for name in names):
        required.add(("icu", "73.2"))
    if any(name.startswith("libcrypto") for name in names):
        required.add(("openssl", openssl_version))
    missing = required - records
    if missing:
        raise RuntimeError("Missing runtime notices: " + ", ".join(component + " " + version for component, version in sorted(missing)))
