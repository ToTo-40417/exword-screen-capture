"""Independent stream parser for documented OHP and the observed DIC00 check.

Wire format reference: Cahute Protocol 7.00 Screenstreaming documentation.
No Cahute parser or code is linked. Unknown input is recorded by the transport.
"""
from dataclasses import dataclass, field

MAX_PAYLOAD = 2 * 1024 * 1024
ACK = b"\x06020010D"
CHECK_SUBTYPES = {"CAL00", "DIC00"}
HEX = frozenset(b"0123456789ABCDEFabcdef")


def checksum(body):
    return f"{(-sum(body)) & 255:02X}".encode("ascii")


def is_hex(value):
    return bool(value) and all(c in HEX for c in value)


@dataclass
class Event:
    kind: str
    subtype: str = ""
    packet: bytes = b""
    payload: bytes = b""
    meta: dict = field(default_factory=dict)


def acknowledgement(event):
    # DIC00 + this ACK was verified on XD-N6500 projector mode.
    if event.kind == "check" and event.subtype in CHECK_SUBTYPES:
        return ACK
    return None


class StreamParser:
    def __init__(self):
        self.buffer = bytearray()
        self.opaque = False
        self.discarded = 0

    def feed(self, data):
        if self.opaque:
            return []
        self.buffer.extend(data)
        events = []
        while self.buffer:
            if self.buffer[0] not in (0x06, 0x0B, 0x16):
                del self.buffer[0]
                self.discarded += 1
                continue
            if len(self.buffer) < 6:
                break
            subtype_bytes = bytes(self.buffer[1:6])
            if not all(48 <= c <= 57 or 65 <= c <= 90 for c in subtype_bytes):
                del self.buffer[0]
                self.discarded += 1
                continue
            subtype = subtype_bytes.decode("ascii")
            kind = self.buffer[0]
            header_length, payload_length, meta = 6, 0, {}
            if kind == 0x0B:
                if subtype == "TYP01":
                    payload_length = 1024
                    meta = dict(width=128, height=64, format="MONO1")
                elif subtype in ("TYPZ1", "TYPZ2"):
                    digits = 6 if subtype == "TYPZ1" else 8
                    header_length = 6 + digits + 12
                    if len(self.buffer) < header_length:
                        break
                    numeric = bytes(self.buffer[6:6 + digits + 8])
                    if not is_hex(numeric):
                        events.append(Event("malformed_header", subtype))
                        del self.buffer[0]
                        self.discarded += 1
                        continue
                    payload_length = int(self.buffer[6:6 + digits], 16)
                    height = int(self.buffer[6 + digits:10 + digits], 16)
                    width = int(self.buffer[10 + digits:14 + digits], 16)
                    encoding = bytes(self.buffer[14 + digits:18 + digits]).decode("ascii", "replace")
                    if not (0 < payload_length <= MAX_PAYLOAD and 0 < width <= 4096 and 0 < height <= 4096):
                        events.append(Event("invalid_dimensions", subtype, meta=dict(length=payload_length, width=width, height=height)))
                        self.opaque = True
                        self.buffer.clear()
                        break
                    stride = (width + 7) // 8
                    expected = {"1RC2": width * height * 2,
                                "1RC3": (width * height + 1) // 2,
                                "1RM2": 2 * height * stride}.get(encoding)
                    meta = dict(width=width, height=height, format=encoding,
                                expected_length=expected, payload_length=payload_length)
                else:
                    # Unknown frame lengths cannot be guessed. Stop interpretation
                    # for this session, retaining all following bytes in rx.bin.
                    events.append(Event("unknown_frame_header", subtype,
                                        meta=dict(prefix=bytes(self.buffer[:64]).hex())))
                    self.opaque = True
                    self.buffer.clear()
                    break
            total = header_length + payload_length + 2
            if len(self.buffer) < total:
                break
            packet = bytes(self.buffer[:total])
            tail = packet[-2:]
            if not is_hex(tail) or int(tail, 16) != int(checksum(packet[1:-2]), 16):
                events.append(Event("bad_checksum", subtype, meta=dict(prefix=packet[:24].hex())))
                del self.buffer[0]
                self.discarded += 1
                continue
            del self.buffer[:total]
            event_kind = {0x06: "ack", 0x0B: "frame", 0x16: "check"}[kind]
            events.append(Event(event_kind, subtype, packet,
                                packet[header_length:-2], meta))
        return events


def ppm_image(event):
    """Return a PPM for validated, supported frame layouts; otherwise None."""
    if event.kind != "frame":
        return None
    w, h, fmt = (event.meta[k] for k in ("width", "height", "format"))
    expected = event.meta.get("expected_length", 1024)
    if expected is None or len(event.payload) != expected:
        return None
    src = event.payload
    rgb = bytearray()
    if fmt == "1RC2":
        for i in range(0, len(src), 2):
            value = (src[i] << 8) | src[i + 1]
            r, g, b = (value >> 11) & 31, (value >> 5) & 63, value & 31
            rgb.extend(((r << 3) | (r >> 2), (g << 2) | (g >> 4), (b << 3) | (b >> 2)))
    elif fmt == "1RC3":
        for i in range(w * h):
            value = (src[i // 2] >> (4 if i % 2 == 0 else 0)) & 15
            rgb.extend((255 if value & 8 else 0, 255 if value & 4 else 0, 255 if value & 2 else 0))
    elif fmt in ("MONO1", "1RM2"):
        stride = (w + 7) // 8
        plane = h * stride
        for y in range(h):
            for x in range(w):
                i, mask = y * stride + x // 8, 128 >> (x % 8)
                if fmt == "MONO1":
                    value = 0 if src[i] & mask else 255
                else:
                    index = (2 if src[i] & mask else 0) | (1 if src[plane + i] & mask else 0)
                    value = (255, 170, 119, 0)[index]
                rgb.extend((value, value, value))
    else:
        return None
    return f"P6\n{w} {h}\n255\n".encode("ascii") + rgb
