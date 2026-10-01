"""Export verified corresponding sources for an independent Windows build."""
import argparse
import hashlib
from pathlib import Path
import tempfile
import zipfile

from compliance import supply_sources


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sources", type=Path, required=True)
    parser.add_argument("--zip", type=Path, required=True)
    args = parser.parse_args()
    args.zip.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="exword-source-export-") as temporary:
        stage = Path(temporary)
        supply_sources(args.sources, stage)
        verified = stage / "corresponding-source"
        with zipfile.ZipFile(args.zip, "x", compression=zipfile.ZIP_STORED) as archive:
            for path in sorted(verified.rglob("*")):
                if path.is_file():
                    info = zipfile.ZipInfo(path.relative_to(verified).as_posix(),
                                           (1980, 1, 1, 0, 0, 0))
                    info.create_system = 3
                    info.external_attr = 0o100644 << 16
                    archive.writestr(info, path.read_bytes())
    digest = hashlib.sha256(args.zip.read_bytes()).hexdigest()
    args.zip.with_name(args.zip.name + ".sha256").write_text(
        digest + "  " + args.zip.name + "\n", encoding="ascii")
    print(f"Verified dependency sources exported: {args.zip.name}")


if __name__ == "__main__":
    main()
