"""Keep raster GUI plugins and the transitive imported Windows DLL closure.

Windows 10/11 supplies Universal CRT and API-set forwarders. Python extension
modules selected by PyInstaller are retained; this function removes unused DLLs
and Qt plugin/data payloads. No host paths are written to the report.
"""
import hashlib
import os
from pathlib import Path
import re
import shutil
import struct

import pefile


def sanitize_debug_paths(path):
    """Remove supplier home paths without changing executable sections.

    These are PDB records and compiler diagnostic file-name strings, not
    application resources. Changed DLLs must not retain invalid Authenticode
    signatures; preserve copyright/license texts separately in the bundle.
    """
    pattern = re.compile(rb"(?:[A-Za-z]:[\\/]+Users[\\/]+[A-Za-z0-9_.-]+|/(?:home|Users)/[A-Za-z0-9_.-]+)[\\/]", re.I)
    original = path.read_bytes()
    if not pattern.search(original):
        return None
    data = bytearray(original)
    pe = pefile.PE(data=original)
    executable_sections = [(s.PointerToRawData, s.PointerToRawData + s.SizeOfRawData)
                           for s in pe.sections if s.Characteristics & 0x20000000]
    debug_count = 0
    for entry in getattr(pe, "DIRECTORY_ENTRY_DEBUG", ()):
        start, size = entry.struct.PointerToRawData, entry.struct.SizeOfData
        if start and size:
            data[start:start + size] = b"\0" * size
            debug_count += 1
        start, size = entry.struct.get_file_offset(), entry.struct.sizeof()
        data[start:start + size] = b"\0" * size
    debug_dir = pe.OPTIONAL_HEADER.DATA_DIRECTORY[pefile.DIRECTORY_ENTRY["IMAGE_DIRECTORY_ENTRY_DEBUG"]]
    struct.pack_into("<II", data, debug_dir.get_file_offset(), 0, 0)
    diagnostic_count = 0
    for match in list(pattern.finditer(data)):
        end = data.find(b"\0", match.start())
        if end < 0 or end - match.start() > 4096:
            raise RuntimeError("Unrecognized supplier path string")
        replacement = b"source"
        data[match.start():end] = replacement + b"\0" * (end - match.start() - len(replacement))
        diagnostic_count += 1
    cert = pe.OPTIONAL_HEADER.DATA_DIRECTORY[pefile.DIRECTORY_ENTRY["IMAGE_DIRECTORY_ENTRY_SECURITY"]]
    signature_removed = bool(cert.Size)
    if cert.Size:
        start, size = cert.VirtualAddress, cert.Size
        data[start:start + size] = b"\0" * size
        if start + size == len(data):
            del data[start:]
        struct.pack_into("<II", data, cert.get_file_offset(), 0, 0)
    if any(original[a:b] != data[a:b] for a, b in executable_sections):
        raise RuntimeError("Refusing to change executable code")
    checksum_offset = pe.OPTIONAL_HEADER.get_field_absolute_offset("CheckSum")
    struct.pack_into("<I", data, checksum_offset, 0)
    pe.close()
    edited = pefile.PE(data=bytes(data))
    struct.pack_into("<I", data, checksum_offset, edited.generate_checksum())
    edited.close()
    if pattern.search(data):
        raise RuntimeError("Supplier home path remains")
    path.write_bytes(data)
    return {"debug_records_removed": debug_count, "diagnostic_paths_replaced": diagnostic_count,
            "vendor_signature_removed": signature_removed, "executable_sections_unchanged": True}


def minimize(bundle):
    bundle = Path(bundle)
    internal = bundle / "_internal"
    removed = []

    def discard(path):
        removed.append(path.relative_to(bundle).as_posix())
        path.unlink()

    allowed_plugins = {
        "platforms/qwindows.dll",  # Native Windows desktop and file dialogs.
        "platforms/qoffscreen.dll",  # The application's offline self-test.
        "styles/qmodernwindowsstyle.dll",  # Default Windows Qt Widgets style.
    }
    plugin_root = internal / "PySide6/plugins"
    for path in sorted(plugin_root.rglob("*")):
        if path.is_file() and path.relative_to(plugin_root).as_posix() not in allowed_plugins:
            discard(path)
    # This application uses its own translations and does not load QTranslator.
    for path in (internal / "PySide6/translations").rglob("*"):
        if path.is_file():
            discard(path)

    # Windows already loads one C/C++ runtime DLL per basename. Put one copy in
    # the bootloader's DLL search directory instead of keeping duplicate copies.
    runtimes = {}
    for path in internal.rglob("*.dll"):
        if path.name.lower().startswith(("vcruntime", "msvcp")):
            runtimes.setdefault(path.name.lower(), []).append(path)
    for paths in runtimes.values():
        paths.sort(key=lambda p: (p.parent != internal, p.as_posix()))
        selected = paths[0]
        target = internal / selected.name
        if selected != target:
            shutil.copyfile(selected, target)
        for path in paths:
            if path != target:
                discard(path)

    dlls = {path.name.lower(): path for path in internal.rglob("*.dll")}
    system = Path(os.environ["SystemRoot"]) / "System32"
    system_contracts = {name for name in dlls if name.startswith(("api-ms-win-", "ext-ms-win-")) or name == "ucrtbase.dll"}
    # Qt6 is supported on Windows 10/11, where these are operating-system DLLs.
    if not (system / "ucrtbase.dll").is_file():
        raise RuntimeError("Windows 10/11 Universal CRT is required")

    roots = [bundle / "EXwordScreenCapture.exe", *internal.rglob("*.pyd")]
    # These helpers are loaded dynamically and cannot be inferred from imports.
    roots.extend([internal / "native/ffmpeg.exe", internal / "native/libusb-1.0.dll"])
    roots.extend(plugin_root / name for name in sorted(allowed_plugins))
    if not all(path.is_file() for path in roots):
        raise RuntimeError("Required GUI or Python runtime component missing")
    retained = set(roots)
    queue = list(roots)
    imports = {}
    missing = set()
    while queue:
        path = queue.pop()
        pe = pefile.PE(str(path), fast_load=True)
        try:
            pe.parse_data_directories(directories=[
                pefile.DIRECTORY_ENTRY["IMAGE_DIRECTORY_ENTRY_IMPORT"],
                pefile.DIRECTORY_ENTRY["IMAGE_DIRECTORY_ENTRY_DELAY_IMPORT"],
            ])
            dependencies = sorted({item.dll.decode("ascii").lower()
                                   for attr in ("DIRECTORY_ENTRY_IMPORT", "DIRECTORY_ENTRY_DELAY_IMPORT")
                                   for item in getattr(pe, attr, ())})
        finally:
            pe.close()
        imports[path.relative_to(bundle).as_posix()] = dependencies
        # PyInstaller's bootloader loads the Python DLL dynamically.
        if path.name == "EXwordScreenCapture.exe":
            dependencies.append("python312.dll")
        for name in dependencies:
            if name in system_contracts or name.startswith(("api-ms-win-", "ext-ms-win-")):
                continue
            dependency = dlls.get(name)
            if dependency:
                if dependency not in retained:
                    retained.add(dependency)
                    queue.append(dependency)
            elif not (system / name).is_file():
                missing.add(name)
    if missing:
        raise RuntimeError("Unresolved DLL dependencies: " + ", ".join(sorted(missing)))
    for path in sorted(internal.rglob("*.dll")):
        if path not in retained:
            discard(path)
    sanitization = []
    for path in sorted(retained):
        result = sanitize_debug_paths(path)
        if result:
            sanitization.append({"file": path.relative_to(bundle).as_posix(), **result})
    # Remove now-empty plugin directories, without touching anything outside bundle.
    for path in sorted(internal.rglob("*"), key=lambda p: len(p.parts), reverse=True):
        if path.is_dir() and not any(path.iterdir()):
            path.rmdir()
    inventory = []
    for path in sorted(retained):
        inventory.append({"file": path.relative_to(bundle).as_posix(),
                          "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                          "imports": imports[path.relative_to(bundle).as_posix()]})
    return {"passed": True, "target": "Windows 10/11 x64", "qt_plugins": sorted(allowed_plugins),
            "bundled_components": ["libusb", "FFmpeg"], "unresolved_imports": [],
            "removed_files": sorted(removed), "runtime_binaries": inventory,
            "supplier_path_sanitization": sanitization}
