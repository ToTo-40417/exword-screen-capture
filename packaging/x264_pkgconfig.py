"""Private x264-only pkg-config adapter; never queries system codec libraries."""
from pathlib import Path
import sys
import shlex

prefix = Path("../../x264-prefix")
pc = prefix / "lib/pkgconfig/x264.pc"
if "--version" in sys.argv:
    print("0.29")
    raise SystemExit(0)
if not pc.is_file() or "x264" not in sys.argv[1:]:
    raise SystemExit(1)
fields = dict(line.split(":", 1) for line in pc.read_text().splitlines() if ":" in line)
if "--modversion" in sys.argv:
    print(fields["Version"].strip())
elif "--cflags" in sys.argv:
    print("-I" + (prefix / "include").as_posix())
elif "--libs" in sys.argv:
    dependencies = [token for token in shlex.split(fields.get("Libs", "") + " " + fields.get("Libs.private", ""))
                    if not token.startswith("-L") and token != "-lx264"]
    print("-L" + (prefix / "lib").as_posix() + " -lx264 " + " ".join(dependencies))
elif "--exists" not in sys.argv:
    raise SystemExit(1)
