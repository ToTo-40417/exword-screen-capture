"""Native RGB transforms and streaming PNG output; Python standard library only."""
import struct
import zlib

VIEWS = ("all", "upper", "lower")
FILTERS = ("none", "grayscale", "invert")


def transform(width, height, rgb, view="all", filter_name="none"):
    if width < 1 or height < 1 or len(rgb) != width * height * 3:
        raise ValueError("Invalid native RGB dimensions")
    if view not in VIEWS or filter_name not in FILTERS:
        raise ValueError("Unknown view or filter")
    if view != "all":
        if (width, height) != (528, 432):
            raise ValueError("Upper/lower split requires the verified 528x432 layout")
        if view == "upper":
            rgb, height = rgb[:width * 320 * 3], 320
        else:
            rgb, height = rgb[width * 320 * 3:], 112
    if filter_name == "invert":
        rgb = bytes(255 - value for value in rgb)
    elif filter_name == "grayscale":
        output = bytearray(len(rgb))
        for index in range(0, len(rgb), 3):
            gray = (77 * rgb[index] + 150 * rgb[index + 1] + 29 * rgb[index + 2]) >> 8
            output[index:index + 3] = bytes((gray, gray, gray))
        rgb = bytes(output)
    return width, height, rgb


def write_png(path, width, height, rgb, scale=1):
    """Rows are integer-replicated and streamed; no enlarged full-frame buffer."""
    if not 1 <= scale <= 10 or len(rgb) != width * height * 3 or min(width, height) < 1:
        raise ValueError("Invalid RGB frame or scale (1..10)")
    with open(path, "xb") as output:
        output.write(b"\x89PNG\r\n\x1a\n")
        def chunk(kind, data):
            output.write(struct.pack(">I", len(data)) + kind + data
                         + struct.pack(">I", zlib.crc32(kind + data) & 0xffffffff))
        chunk(b"IHDR", struct.pack(">IIBBBBB", width * scale, height * scale, 8, 2, 0, 0, 0))
        compressor = zlib.compressobj(6)
        row_bytes = width * 3
        for y in range(height):
            row = rgb[y * row_bytes:(y + 1) * row_bytes]
            if scale > 1:
                row = b"".join(row[x:x + 3] * scale for x in range(0, row_bytes, 3))
            for _ in range(scale):
                compressed = compressor.compress(b"\0" + row)
                if compressed:
                    chunk(b"IDAT", compressed)
        chunk(b"IDAT", compressor.flush())
        chunk(b"IEND", b"")
