"""Build a minimal standalone FFmpeg executable and dynamically replaceable libusb.

Run on the target OS. Windows requires an MSYS2 UCRT64 shell/toolchain.
Only the specified work/output directories are written; no system installation.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import platform
import shutil
import subprocess
import tarfile

FFMPEG_FLAGS = [
    "--prefix=/", "--disable-all", "--disable-autodetect", "--disable-network",
    "--enable-gpl", "--disable-version3", "--disable-nonfree", "--disable-doc", "--disable-debug",
    "--disable-shared", "--enable-static", "--enable-pthreads", "--enable-ffmpeg",
    "--enable-avcodec", "--enable-avformat", "--enable-avutil", "--enable-avfilter", "--enable-swscale",
    "--enable-libx264", "--enable-encoder=libx264,ffv1,rawvideo", "--enable-decoder=rawvideo,h264,ffv1",
    "--enable-demuxer=rawvideo,mov,matroska", "--enable-muxer=mp4,matroska,rawvideo", "--enable-protocol=file,pipe",
    "--pkg-config=python3 ./x264-pkg-config.py", "--pkg-config-flags=--static",
    "--enable-filter=scale,pad,format,null",
]


def unpack(archive, destination):
    destination.mkdir(parents=True, exist_ok=False)
    with tarfile.open(archive) as stream:
        stream.extractall(destination, filter="data")
    return next(path for path in destination.iterdir() if path.is_dir())


def run(command, directory):
    subprocess.run(command, cwd=directory, check=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sources", type=Path, required=True)
    parser.add_argument("--work", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--jobs", type=int, default=4)
    parser.add_argument("--resume", action="store_true", help="Resume this build's already-verified, unmodified work trees")
    parser.add_argument("--finalize-only", action="store_true", help="Strip/debug-clean existing native output and refresh hashes")
    args = parser.parse_args()
    args.sources, args.work, args.output = args.sources.absolute(), args.work.absolute(), args.output.absolute()
    if args.finalize_only:
        report_path = args.output / "manifest.json"
        report = json.loads(report_path.read_text())
        for entry in report["files"]:
            path = args.output / entry["filename"]
            if path.name.startswith("libusb"):
                run(["strip", "--strip-unneeded", str(path)], args.output)
            entry.update(bytes=path.stat().st_size, sha256=hashlib.sha256(path.read_bytes()).hexdigest())
        report["binary_postprocessing"] = "libusb: strip --strip-unneeded"
        report_path.write_text(json.dumps(report, indent=2) + "\n")
        return
    manifest = json.loads((args.sources / "manifest.json").read_text())
    x264_record = next(record for record in manifest["records"] if record["component"] == "x264")
    for name in ("ffmpeg-8.0.tar.xz", "libusb-1.0.29.tar.bz2", x264_record["filename"]):
        record = next(record for record in manifest["records"] if record["filename"] == name)
        if hashlib.sha256((args.sources / "archives" / name).read_bytes()).hexdigest() != record["sha256"]:
            raise SystemExit("Source checksum mismatch: " + name)
    args.output.mkdir(parents=True, exist_ok=True)
    ffmpeg = args.work / "ffmpeg/ffmpeg-8.0" if args.resume else unpack(args.sources / "archives/ffmpeg-8.0.tar.xz", args.work / "ffmpeg")
    libusb = args.work / "libusb/libusb-1.0.29" if args.resume else unpack(args.sources / "archives/libusb-1.0.29.tar.bz2", args.work / "libusb")
    x264 = args.work / "x264" / ("x264-" + x264_record["version"]) if args.resume else unpack(args.sources / "archives" / x264_record["filename"], args.work / "x264")
    x264_flags = ["--prefix=/", "--enable-static", "--disable-cli", "--disable-opencl", "--enable-pic", "--disable-asm"]
    if platform.system() == "Darwin":
        x264_flags += ["--extra-cflags=-mmacosx-version-min=12.0", "--extra-ldflags=-mmacosx-version-min=12.0"]
    native_cc = os.environ.get("EXWORD_NATIVE_CC")
    if native_cc:
        os.environ["CC"] = native_cc
        x264_flags += ["--extra-ldflags=-static-libgcc"]
    run(["sh", "./configure", *x264_flags], x264)
    run(["make", f"-j{args.jobs}"], x264)
    run(["make", "install-lib-static", "DESTDIR=" + (args.work / "x264-prefix").as_posix()], x264)
    shutil.copyfile(Path(__file__).with_name("x264_pkgconfig.py"), ffmpeg / "x264-pkg-config.py")
    windows = platform.system() == "Windows" or platform.system().startswith(("MINGW", "MSYS"))
    flags = FFMPEG_FLAGS + (["--extra-ldflags=-static-libgcc -static"] if windows else [])
    if native_cc:
        flags += ["--cc=" + native_cc]
    usb_flags = ["--prefix=/", "--enable-shared", "--disable-static", "--disable-examples-build", "--disable-tests-build", "CFLAGS=-O2"]
    if platform.system() == "Linux":
        usb_flags += ["--disable-udev"]
    if platform.system() == "Darwin":
        flags += ["--extra-cflags=-mmacosx-version-min=12.0", "--extra-ldflags=-mmacosx-version-min=12.0"]
        usb_flags += ["CFLAGS=-O2 -mmacosx-version-min=12.0", "LDFLAGS=-mmacosx-version-min=12.0"]
    if windows:
        usb_flags += ["LDFLAGS=-static-libgcc"]
        if native_cc:
            usb_flags += ["CC=" + native_cc]
        flags += ["--disable-pthreads", "--enable-w32threads", "--disable-x86asm"]
    elif platform.machine().lower() in ("x86_64", "amd64") and not shutil.which("nasm"):
        flags += ["--disable-x86asm"]
    run(["sh", "./configure", *flags], ffmpeg)
    run(["make", f"-j{args.jobs}"], ffmpeg)
    run(["sh", "./configure", *usb_flags], libusb)
    run(["make", f"-j{args.jobs}"], libusb)
    ffmpeg_name = "ffmpeg.exe" if windows else "ffmpeg"
    usb_name = "libusb-1.0.dll" if windows else "libusb-1.0.0.dylib" if platform.system() == "Darwin" else "libusb-1.0.so.0"
    usb_built = libusb / "libusb/.libs" / usb_name
    if windows and not usb_built.is_file():
        usb_built = next((libusb / "libusb/.libs").glob("libusb-1.0*.dll"))
    shutil.copyfile(ffmpeg / ffmpeg_name, args.output / ffmpeg_name)
    shutil.copyfile(usb_built.resolve(), args.output / usb_name)
    for name in (ffmpeg_name, usb_name):
        (args.output / name).chmod(0o755)
    if platform.system() != "Darwin":
        run(["strip", "--strip-unneeded", str(args.output / usb_name)], args.output)
    if platform.system() == "Darwin":
        run(["install_name_tool", "-id", "@rpath/" + usb_name, str(args.output / usb_name)], args.output)
        for name in (ffmpeg_name, usb_name):
            run(["codesign", "--force", "--sign", "-", str(args.output / name)], args.output)
    # Keep exact generated configuration and build options with the sources.
    configs = args.output / "build-config"
    configs.mkdir(exist_ok=True)
    for file in ("config.h", "config_components.h", "ffbuild/config.mak"):
        payload = (ffmpeg / file).read_text().replace(str(ffmpeg), "/path/to/ffmpeg-source")
        (configs / Path(file).name).write_text(payload)
    license_text = subprocess.check_output([str(args.output / ffmpeg_name), "-L"], stderr=subprocess.STDOUT, text=True)
    if "GNU General Public License" not in license_text or "version 2" not in license_text:
        raise SystemExit("FFmpeg must report GPL version 2 or later")
    (configs / "ffmpeg-license.txt").write_text(license_text)
    for file in ("config.h", "config.mak", "x264_config.h"):
        (configs / ("x264-" + file)).write_text((x264 / file).read_text().replace(str(x264), "/path/to/x264-source"))
    report = {"ffmpeg_version": "8.0", "ffmpeg_license": "GPL-2.0-or-later",
              "x264_version": x264_record["version"], "x264_license": "GPL-2.0-or-later", "x264_configure": x264_flags,
              "libusb_version": "1.0.29", "libusb_license": "LGPL-2.1-or-later",
              "architecture": platform.machine(), "system": platform.system(),
              "ffmpeg_configure": flags, "libusb_configure": usb_flags, "source_modifications": "none",
              "ffmpeg_linkage": "separate GPL executable; libx264 statically included with complete source/build scripts",
              "libusb_linkage": "shared library",
              "binary_postprocessing": "ad-hoc signing" if platform.system() == "Darwin" else "libusb: strip --strip-unneeded",
              "files": [{"filename": name, "bytes": (args.output / name).stat().st_size,
                         "sha256": hashlib.sha256((args.output / name).read_bytes()).hexdigest()}
                        for name in (ffmpeg_name, usb_name)]}
    if windows and os.environ.get("EXWORD_NATIVE_ROOT"):
        license_root = Path(os.environ["EXWORD_NATIVE_ROOT"]) / "ucrt64/share/licenses"
        runtime_notices = []
        for component in ("libgcc", "crt", "winpthreads"):
            for source in sorted((license_root / component).glob("COPYING*")):
                target = args.output / "runtime-notices" / component / source.name
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(source, target)
                runtime_notices.append({"path": target.relative_to(args.output).as_posix(), "sha256": hashlib.sha256(target.read_bytes()).hexdigest()})
        if not runtime_notices:
            raise RuntimeError("Compiler runtime license notices missing")
        report["compiler_runtime_notices"] = runtime_notices
    (args.output / "manifest.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
