"""Allowlisted, owner-free source handoff; excludes Git, caches and private captures."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import zipfile

from privacy import audit

FILES = ["LICENSE", "README.md", "README.en.md", "README.zh-CN.md", "README.zh-TW.md",
         "THIRD_PARTY_NOTICES.md", "launch.py", "pyproject.toml",
         "requirements.txt", "requirements-cli.txt", "requirements-build.txt", ".gitignore"]
BRAIN_FILES = ("LICENSE", "README.md", "brain_pixels.c", "brain_pixels.py",
               "brain_usb_source.py", "exword-capture-preview.py", "build-brain-pixels.sh",
               "exword-live", "exword-live.desktop", "test_brain_pixels.py", "test_brain_receiver.py")
FILES += ["packaging/brain-preview/" + name for name in BRAIN_FILES]
# Every publication input is reviewed by name. Adding an extension-compatible
# local note or image must never silently add it to a release.
FILES += [
    ".github/workflows/build.yml",
    "assets/GENERATION_PROMPT.md", "assets/ICON.md",
    "assets/exword-screen-capture-256.png", "assets/exword-screen-capture.icns",
    "assets/exword-screen-capture.ico", "assets/exword-screen-capture.png",
    "docs/BRAINUX.md", "docs/COMPATIBILITY.md", "docs/DEPENDENCY_BUILD.md",
    "docs/LIBRARY_REPLACEMENT.md", "docs/LICENSING.md", "docs/PROTOCOL.md",
    "docs/RESOURCE_ESTIMATES.md", "docs/SETUP.md", "docs/WINDOWS_BUILD.md",
    "docs/WINDOWS_USB.md", "docs/images/capture-ui-window.png",
    "exword_capture/__init__.py", "exword_capture/app.py", "exword_capture/cli.py",
    "exword_capture/desktop.py", "exword_capture/entrypoints.py", "exword_capture/gui.py",
    "exword_capture/i18n.py", "exword_capture/ohp.py", "exword_capture/onefile.py",
    "exword_capture/pixels.py", "exword_capture/runtime.py", "exword_capture/usb_source.py",
    "exword_capture/verification.py", "exword_capture/video.py",
    "packaging/60-exword-capture.rules", "packaging/build-windows.ps1",
    "packaging/build.py", "packaging/build_cli.py", "packaging/build_media.py",
    "packaging/build_onefile.py", "packaging/checksums.py", "packaging/compliance.py",
    "packaging/export_dependencies.py", "packaging/export_source.py", "packaging/gcc-ascii.sh",
    "packaging/minimize_windows.py", "packaging/onefile.spec", "packaging/prepare_icons.py",
    "packaging/prepare_runtime_notices.py", "packaging/prepare_sources.py", "packaging/privacy.py",
    "packaging/sanitize_supplier_paths.py", "packaging/windows-version.txt",
    "packaging/x264_pkgconfig.py", "tests/manual_capture.py",
    "tests/test_brain_source_export.py", "tests/test_capture.py", "tests/test_compliance.py", "tests/test_headless.py",
    "tests/test_icons.py", "tests/test_privacy.py", "tests/test_recording_options.py",
    "tests/test_runtime.py", "tools/render_ui_preview.py",
]


def source_files(root):
    root = Path(root)
    if root.is_symlink():
        raise ValueError("Source root must not be a symlink")
    resolved_root = root.resolve()
    paths = [root / name for name in FILES]
    for path in paths:
        if not path.resolve().is_relative_to(resolved_root):
            raise ValueError("Source input resolves outside source root")
        candidate = path
        while candidate != root:
            if candidate.is_symlink():
                raise ValueError("Source input or parent must not be a symlink")
            candidate = candidate.parent
        if path.exists() and not path.is_file():
            raise ValueError("Source input must be a regular file")
    return sorted(set(paths))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--stage", type=Path, required=True)
    parser.add_argument("--zip", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    args.stage.mkdir(parents=True, exist_ok=False)
    for path in source_files(root):
        target = args.stage / path.relative_to(root)
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(path, target)
    result = audit(args.stage)
    args.report.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    if not result["passed"]:
        raise SystemExit("Source privacy inspection failed; see report.")
    args.zip.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(args.zip, "x", compression=zipfile.ZIP_DEFLATED) as archive:
        for path in sorted(args.stage.rglob("*")):
            if path.is_file():
                entry = zipfile.ZipInfo(path.relative_to(args.stage).as_posix(), (1980, 1, 1, 0, 0, 0))
                entry.create_system = 3
                entry.external_attr = 0o100644 << 16
                archive.writestr(entry, path.read_bytes(), compress_type=zipfile.ZIP_DEFLATED)
    print(json.dumps({"files": len(source_files(root)), "sha256": hashlib.sha256(args.zip.read_bytes()).hexdigest(),
                      "source_privacy_passed": True}, indent=2))


if __name__ == "__main__":
    main()
