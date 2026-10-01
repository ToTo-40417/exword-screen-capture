"""Acquire pinned, unmodified permissive runtime license texts; never publish."""
import argparse
import hashlib
import json
import re
from pathlib import Path
import urllib.request


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sources", type=Path, required=True)
    parser.add_argument("--openssl-version", default="3.0.15",
                        help="Exact redistributed OpenSSL 3.x patch version")
    args = parser.parse_args()
    if not re.fullmatch(r"3\.\d+\.\d+", args.openssl_version):
        parser.error("Use an exact numeric OpenSSL 3.x.y version; other families need review")
    openssl_root = "https://raw.githubusercontent.com/openssl/openssl/openssl-" + args.openssl_version + "/"
    notices = {
        "icu": ("73.2", "https://raw.githubusercontent.com/unicode-org/icu/release-73-2/icu4c/LICENSE"),
        "openssl": (args.openssl_version, openssl_root + "LICENSE.txt"),
    }
    manifest_path = args.sources / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    records = []
    for component, (version, url) in notices.items():
        with urllib.request.urlopen(url, timeout=60) as response:
            payload = response.read()
        if len(payload) < 500 or b"license" not in payload.lower():
            raise RuntimeError("Unexpected upstream notice: " + component)
        relative = Path("runtime-notices") / component / "LICENSE.txt"
        target = args.sources / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        # Official originals must not be shortened or edited.
        target.write_bytes(payload)
        records.append({"component": component, "version": version,
                        "path": relative.as_posix(), "url": url,
                        "sha256": hashlib.sha256(payload).hexdigest(),
                        "modified": False,
                        "integrity": "HTTPS version-tagged upstream; locally recorded SHA-256"})
    attribution_url = openssl_root + "README.md"
    with urllib.request.urlopen(attribution_url, timeout=60) as response:
        attribution = response.read()
    if b"Copyright" not in attribution:
        raise RuntimeError("OpenSSL attribution missing")
    relative = Path("runtime-notices/openssl/README.md")
    (args.sources / relative).write_bytes(attribution)
    records.append({"component": "openssl", "version": args.openssl_version,
                    "path": relative.as_posix(), "url": attribution_url,
                    "sha256": hashlib.sha256(attribution).hexdigest(), "modified": False,
                    "integrity": "HTTPS version-tagged upstream; locally recorded SHA-256"})
    manifest["runtime_notices"] = records
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"runtime_notices": records}, indent=2))


if __name__ == "__main__":
    main()
