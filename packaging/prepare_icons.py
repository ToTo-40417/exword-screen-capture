"""Package the approved raster artwork as OS icons; does not redesign the image.

Run on macOS with its built-in sips/iconutil. Other build PCs use the supplied
PNG, ICO and ICNS assets directly; no image-generation service is needed.
"""
from pathlib import Path
import struct
import subprocess
import tempfile

root = Path(__file__).resolve().parents[1]
assets = root / "assets"
source = assets / "exword-screen-capture.png"
with tempfile.TemporaryDirectory(prefix="exword-icon-pack-") as temporary:
    stage = Path(temporary)
    iconset = stage / "capture.iconset"
    iconset.mkdir()
    entries = []
    for size in (16, 24, 32, 48, 64, 128, 256, 512, 1024):
        target = stage / (str(size) + ".png")
        subprocess.run(["sips", "-z", str(size), str(size), str(source), "--out", str(target)],
                       check=True, stdout=subprocess.DEVNULL)
        if size <= 256:
            entries.append((size, target.read_bytes()))
        if size == 256:
            (assets / "exword-screen-capture-256.png").write_bytes(target.read_bytes())
        if size in (16, 32, 128, 256, 512):
            (iconset / f"icon_{size}x{size}.png").write_bytes(target.read_bytes())
        if size in (32, 64, 256, 512, 1024):
            logical = size // 2
            (iconset / f"icon_{logical}x{logical}@2x.png").write_bytes(target.read_bytes())
    subprocess.run(["iconutil", "-c", "icns", str(iconset), "-o",
                    str(assets / "exword-screen-capture.icns")], check=True)
    # ICO stores the same derived PNGs, not a second design or flattened image.
    offset = 6 + 16 * len(entries)
    directory = bytearray(struct.pack("<HHH", 0, 1, len(entries)))
    payload = bytearray()
    for size, png in entries:
        directory.extend(struct.pack("<BBBBHHII", size if size < 256 else 0,
                                     size if size < 256 else 0, 0, 0, 1, 32, len(png), offset))
        payload.extend(png)
        offset += len(png)
    (assets / "exword-screen-capture.ico").write_bytes(directory + payload)
print("PNG / ICO / ICNS application icons ready")
