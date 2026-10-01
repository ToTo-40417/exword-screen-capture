"""Redact supplier diagnostic paths; refuse any change to executable sections."""
from pathlib import Path
import re
import subprocess
import sys
from privacy import PRIVATE_PATH


def sanitize(bundle):
    report = []
    for path in sorted(Path(bundle).rglob("*")):
        if path.is_symlink() or not path.is_file():
            continue
        original = path.read_bytes()
        if original[:4] not in (b"\xcf\xfa\xed\xfe", b"\x7fELF"):
            continue
        matches = list(PRIVATE_PATH.finditer(original))
        if not matches:
            continue
        ranges = []
        if original[:4] == b"\xcf\xfa\xed\xfe":
            from macholib.MachO import MachO
            for header in MachO(str(path)).headers:
                for _, command, sections in header.commands:
                    if isinstance(sections, list):
                        for section in sections:
                            if section.flags & (0x80000000 | 0x400) or section.sectname.rstrip(b"\0") == b"__text":
                                ranges.append((section.offset, section.offset + section.size))
        else:
            listing = subprocess.check_output(["readelf", "-W", "-S", str(path)], text=True)
            for line in listing.splitlines():
                match = re.match(r"\s*\[\s*\d+\]\s+\S+\s+\S+\s+[0-9a-fA-F]+\s+([0-9a-fA-F]+)\s+([0-9a-fA-F]+)\s+[0-9a-fA-F]+\s+([A-Z]+)", line)
                if match and "X" in match[3]:
                    offset, size = int(match[1], 16), int(match[2], 16)
                    ranges.append((offset, offset + size))
        if not ranges:
            raise RuntimeError("Unable to identify executable sections")
        data = bytearray(original)
        for match in matches:
            if any(match.start() < end and match.end() > start for start, end in ranges):
                raise RuntimeError("Refusing to redact executable code")
            length = match.end() - match.start()
            replacement = b"/source" + b"_" * (length - 8) + b"/"
            if len(replacement) != length:
                raise RuntimeError("Unexpected diagnostic path length")
            data[match.start():match.end()] = replacement
        if any(original[start:end] != data[start:end] for start, end in ranges):
            raise RuntimeError("Executable section changed")
        path.write_bytes(data)
        if sys.platform == "darwin":
            subprocess.run(["codesign", "--force", "--sign", "-", str(path)], check=True)
        report.append({"file": path.relative_to(bundle).as_posix(), "diagnostic_paths_redacted": len(matches),
                       "executable_sections_unchanged": True, "date": "2026-10-01"})
    return report
