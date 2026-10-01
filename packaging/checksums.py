"""Write SHA-256 sidecars without embedding absolute paths or user metadata."""
import argparse
import hashlib
from pathlib import Path

parser = argparse.ArgumentParser()
parser.add_argument("directory", type=Path)
args = parser.parse_args()
for path in sorted(args.directory.iterdir()):
    if path.is_file() and path.suffix in (".zip", ".json"):
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        path.with_name(path.name + ".sha256").write_text(digest + "  " + path.name + "\n", encoding="ascii")
