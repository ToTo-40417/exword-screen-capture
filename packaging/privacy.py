"""Inspect first-party privacy markers, including compressed frozen Python code.

Public contributor names in third-party copyright notices must be retained.
This is a deterministic check, not a claim to identify every possible secret.
"""
import argparse
import hashlib
import io
import json
import marshal
from pathlib import Path
import re
import stat
import struct
import tarfile
import zipfile
import zlib

MAX_DEPTH = 8
MAX_OBJECT_BYTES = 512 * 1024 * 1024
MAX_EXPANDED_BYTES = 8 * 1024 * 1024 * 1024
MAX_OBJECTS = 500000
PYINSTALLER_MAGIC = b"MEI\x0c\x0b\n\x0b\x0e"

PERSONAL_EMAIL = re.compile(rb"[a-zA-Z0-9._%+-]+@(?:gmail|icloud|hotmail|outlook|yahoo)\.[a-zA-Z.]+")
SENSITIVE_KEY = re.compile(rb"-----BEGIN (?:OPENSSH|RSA|EC|DSA) PRIVATE KEY-----[\r\n]+[A-Za-z0-9+/=\r\n]{64,}-----END (?:OPENSSH|RSA|EC|DSA) PRIVATE KEY-----|ghp_[A-Za-z0-9]{30,}|hf_[A-Za-z0-9]{25,}|github_pat_[A-Za-z0-9_]{40,}")
PRIVATE_PATH = re.compile(rb"(?:[A-Za-z]:[\\/]+Users[\\/]+[A-Za-z0-9_.-]+|/(?:home|Users)/[A-Za-z0-9_.-]+)(?:[\\/]|\x00)", re.IGNORECASE)
# Public attribution in upstream CPython 3.12 Lib/io.py and Lib/bz2.py.
# Exact email hashes were compared to those public sources; no builder address
# is exempted. Qt's PEM header strings are not a complete private key.
PUBLIC_ATTRIBUTION_HASHES = {
    "62c7b1d40e2a2b8250d4669ed0546bf4fc666185685fa644b4302f2084edd89b",
    "92efe35f454c518456042c90a1d4609da8741581469d4bc92c4f34648cbdbeba",
    "d1b6a703ea89b35a7ca7b5ccdcc373bacb308f4518c621feb6f0916e694e4692",
}
PRIVATE_ASSETS = {"rx.bin", "gui.png", "HWINFO.TXT", "PERFLOG.TXT", "discord_ex-word.jsonl"}


def audit(root, denied=(), public_notice_hashes=(), public_source_hashes=()):
    root = Path(root)
    findings = []
    public_source_findings = []
    checked = 0
    public_notice_emails = 0
    expanded_bytes = 0
    verified_source_archives = 0
    tokens = set(denied)
    # Include the current build user's path/name without recording either in reports.
    home = Path.home()
    tokens.add(str(home))
    # Generic build account names also occur in ordinary library code. Their
    # absolute home paths are always checked; do not classify "user_agent" as PII.
    if len(home.name) > 3 and home.name not in {"agent", "user", "runner", "admin", "builder", "build"}:
        tokens.add(home.name)
    encoded = [value.encode("utf-8") for value in tokens if value]

    def inspect(data, label, public_source=False, container=False):
        nonlocal checked, public_notice_emails
        checked += 1
        hits = set()
        for value in encoded:
            if value in data or value.decode("utf-8").encode("utf-16le") in data:
                hits.add("private_build_marker")
        if container:
            if hits:
                findings.append({"file": label, "rules": sorted(hits)})
            return
        for match in SENSITIVE_KEY.finditer(data):
            # Published supplier test keys are fixtures, never application keys.
            # Tokens and private builder markers remain fatal even in originals.
            fixture_path = re.search(r"/(?:tests?|testdata|certdata)/", label.replace("\\", "/"))
            if public_source and fixture_path and match.group().startswith(b"-----BEGIN "):
                fail(label, "published_test_key_fixture", public_source=True)
            else:
                hits.add("credential_material")
        verified_public_notice = public_source or hashlib.sha256(data).hexdigest() in public_notice_hashes
        if not verified_public_notice and (PRIVATE_PATH.search(data) or PRIVATE_PATH.search(data.decode("utf-16le", errors="ignore").encode("utf-8"))):
            hits.add("private_home_path")
        for match in PERSONAL_EMAIL.finditer(data):
            if verified_public_notice or hashlib.sha256(match.group()).hexdigest() in PUBLIC_ATTRIBUTION_HASHES:
                public_notice_emails += 1
            else:
                hits.add("personal_email")
        if hits:
            findings.append({"file": label, "rules": sorted(hits)})

    def fail(label, rule, public_source=False):
        target = public_source_findings if public_source else findings
        target.append({"file": label, "rules": [rule]})

    def name_check(name, label, public_source=False):
        normalized = name.replace("\\", "/")
        parts = normalized.split("/")
        inspect(normalized.encode("utf-8", errors="surrogateescape"), label + " [name]", public_source)
        if (normalized.startswith("/") or re.match(r"^[A-Za-z]:", normalized)
                or ".." in parts):
            fail(label, "unsafe_archive_path", public_source)
        if any(p in {".git", ".DS_Store", "__pycache__", "captures"} or p in PRIVATE_ASSETS for p in parts):
            fail(label, "private_or_metadata_asset", public_source)

    def bounded_inflate(data):
        inflater = zlib.decompressobj()
        result = inflater.decompress(data, MAX_OBJECT_BYTES + 1)
        if len(result) > MAX_OBJECT_BYTES or inflater.unconsumed_tail:
            raise ValueError("object limit")
        if not inflater.eof:
            raise ValueError("truncated compression")
        return result

    def scan(data, label, depth=0, public_source=False):
        nonlocal expanded_bytes, verified_source_archives
        if depth > MAX_DEPTH or len(data) > MAX_OBJECT_BYTES or checked >= MAX_OBJECTS:
            fail(label, "inspection_limit", public_source)
            return
        expanded_bytes += len(data)
        if expanded_bytes > MAX_EXPANDED_BYTES:
            fail(label, "inspection_limit", public_source)
            return
        try:
            if hashlib.sha256(data).hexdigest() in public_source_hashes:
                public_source = True
                verified_source_archives += 1
            # Also inspect raw container markers: malformed public test archives
            # must never prevent detection of the private builder's identifier.
            inspect(data, label + " [container markers]", public_source, container=True)
            if zipfile.is_zipfile(io.BytesIO(data)):
                with zipfile.ZipFile(io.BytesIO(data)) as archive:
                    for entry in archive.infolist():
                        child = label + "!/" + entry.filename
                        name_check(entry.filename, child, public_source)
                        if entry.file_size > MAX_OBJECT_BYTES or checked >= MAX_OBJECTS:
                            fail(child, "inspection_limit", public_source)
                            break
                        if entry.extra or entry.comment:
                            inspect(entry.extra + entry.comment, child + " [metadata]", public_source)
                        if not entry.is_dir():
                            payload = archive.read(entry)
                            if stat.S_ISLNK(entry.external_attr >> 16):
                                symlink_check(payload.decode("utf-8"), child, entry.filename, public_source)
                            else:
                                scan(payload, child, depth + 1, public_source)
                    if archive.comment:
                        inspect(archive.comment, label + " [comment]", public_source)
                return
            if data[:4] in (b"PK\x03\x04", b"PK\x05\x06"):
                raise ValueError("invalid ZIP archive")
            # Recognize tar by format, including gzip/bzip2/xz, without extracting.
            tar = None
            if (data[:6] in (b"\xfd7zXZ\x00",) or data[:2] in (b"\x1f\x8b", b"BZ")
                    or data[257:262] == b"ustar" or label.lower().endswith(".tar")):
                try:
                    tar = tarfile.open(fileobj=io.BytesIO(data), mode="r:*")
                except tarfile.ReadError:
                    # A non-tar compressed file is a leaf, not a broken tar.
                    if label.lower().endswith((".tar", ".tar.gz", ".tgz", ".tar.bz2", ".tar.xz")):
                        raise
            if tar is not None:
                with tar:
                    for entry in tar:
                        child = label + "!/" + entry.name
                        name_check(entry.name, child, public_source)
                        if entry.size > MAX_OBJECT_BYTES or checked >= MAX_OBJECTS:
                            fail(child, "inspection_limit", public_source)
                            break
                        if entry.pax_headers:
                            inspect(json.dumps(entry.pax_headers).encode(), child + " [metadata]", public_source)
                        if entry.uname or entry.gname:
                            inspect((entry.uname + "\n" + entry.gname).encode("utf-8", errors="surrogateescape"),
                                    child + " [owner metadata]", public_source)
                        if entry.issym() or entry.islnk():
                            symlink_check(entry.linkname, child, entry.name, public_source)
                        elif entry.isfile():
                            with tar.extractfile(entry) as stream:
                                scan(stream.read(MAX_OBJECT_BYTES + 1), child, depth + 1, public_source)
                return
            inspect(data, label, public_source)
            if data[:4] == b"PYZ\x00":
                offset = struct.unpack("!i", data[8:12])[0]
                if not 12 <= offset < len(data):
                    raise ValueError("invalid PYZ offset")
                toc = dict(marshal.loads(data[offset:]))
                for name, (_, start, size) in toc.items():
                    child = label + "/" + name
                    name_check(name, child, public_source)
                    if size:
                        if start < 12 or size < 0 or start + size > offset:
                            raise ValueError("invalid PYZ entry")
                        scan(bounded_inflate(data[start:start + size]), child, depth + 1, public_source)
            elif data[:2] == b"MZ" or data[:4] in (b"\x7fELF", b"\xcf\xfa\xed\xfe", b"\xce\xfa\xed\xfe", b"\xca\xfe\xba\xbe", b"\xca\xfe\xba\xbf"):
                cookie = data.rfind(PYINSTALLER_MAGIC)
                if cookie < 0:
                    return  # Ordinary native libraries are inspected as bytes.
                magic, length, offset, size, _, _ = struct.unpack("!8sIIII64s", data[cookie:cookie + 88])
                start = cookie + 88 - length
                if start < 0 or offset + size > length - 88:
                    raise ValueError("invalid PyInstaller cookie")
                toc = data[start + offset:start + offset + size]
                pos = 0
                while pos < len(toc):
                    length, off, compressed_size, unpacked_size, compressed, kind = struct.unpack("!IIIIBc", toc[pos:pos + 18])
                    if length < 18 or pos + length > len(toc) or off + compressed_size > offset:
                        raise ValueError("invalid PyInstaller entry")
                    name = toc[pos + 18:pos + length].rstrip(b"\0").decode("utf-8")
                    pos += length
                    child = label + "!/" + name
                    name_check(name, child, public_source)
                    if unpacked_size > MAX_OBJECT_BYTES:
                        fail(child, "inspection_limit", public_source)
                        continue
                    payload = data[start + off:start + off + compressed_size]
                    if compressed:
                        payload = bounded_inflate(payload)
                    if len(payload) != unpacked_size:
                        raise ValueError("invalid PyInstaller size")
                    if kind != b"o":
                        scan(payload, child, depth + 1, public_source)
        except Exception as error:
            # Record the category, never raw exception text that can contain PII.
            fail(label, "inspection_error:" + type(error).__name__, public_source)

    def symlink_check(target, label, member_name, public_source=False):
        inspect(target.encode("utf-8", errors="surrogateescape"), label + " [link]", public_source)
        normalized = target.replace("\\", "/")
        if normalized.startswith("/") or re.match(r"^[A-Za-z]:", normalized):
            fail(label, "absolute_symlink", public_source)
        else:
            level = len(member_name.replace("\\", "/").split("/")) - 1
            for part in normalized.split("/"):
                if part == "..":
                    level -= 1
                elif part not in ("", "."):
                    level += 1
                if level < 0:
                    fail(label, "escaping_symlink", public_source)
                    break

    files = [root] if root.is_file() else sorted(root.rglob("*"))
    for path in files:
        label = path.name if root.is_file() else path.relative_to(root).as_posix()
        name_check(label, label)
        if path.is_symlink():
            # Absolute symlinks can leak build paths and are not portable.
            target = path.readlink().as_posix()
            symlink_check(target, label, label)
            continue
        if not path.is_file():
            continue
        if path.stat().st_size > MAX_OBJECT_BYTES:
            fail(label, "inspection_limit")
            continue
        scan(path.read_bytes(), label)
    return {"passed": not findings, "checked_objects": checked,
            "findings": findings, "public_upstream_attribution_hits": public_notice_emails,
            "public_source_findings": public_source_findings,
            "public_source_finding_count": len(public_source_findings),
            "verified_public_source_archives": verified_source_archives,
            "inspection_limits": {"depth": MAX_DEPTH, "object_bytes": MAX_OBJECT_BYTES,
                                  "expanded_bytes": MAX_EXPANDED_BYTES, "objects": MAX_OBJECTS},
            "limitations": ["Deterministic marker inspection cannot identify every secret.",
                            "Caller-verified original upstream archive hashes classify attribution emails/paths, published test keys and metadata fixtures separately; tokens and private builder markers remain fatal.",
                            "Inspection errors/limits within verified originals are reported as supplier-source coverage gaps, not proof of complete inspection."]}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("path", type=Path)
    parser.add_argument("--report", type=Path)
    parser.add_argument("--deny", action="append", default=[])
    args = parser.parse_args()
    result = audit(args.path, args.deny)
    output = json.dumps(result, ensure_ascii=False, indent=2) + "\n"
    if args.report:
        args.report.write_text(output, encoding="utf-8")
    print(output, end="")
    raise SystemExit(0 if result["passed"] else 1)


if __name__ == "__main__":
    main()
