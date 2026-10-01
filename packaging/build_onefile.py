"""Windows-only: wrap the verified portable bundle without losing its legal materials."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
from privacy import audit

if sys.platform != "win32":
    raise SystemExit("Run on the native Windows build PC")
root = Path(__file__).absolute().parents[1]
stage = root / "dist/EXwordScreenCapture"
sources = json.loads((stage / "third-party/corresponding-source/manifest.json").read_text())
hashes = {n["sha256"] for r in sources["records"] for n in r["notices"]}
hashes.update(n["sha256"] for n in sources.get("runtime_notices", []))
inventory = json.loads((stage / "third-party/inventory.json").read_text())
hashes.update(n["sha256"] for n in inventory["native_runtime"].get("compiler_runtime_notices", []))

source_hashes = {record["sha256"] for record in sources["records"]}
if not audit(stage, public_notice_hashes=hashes, public_source_hashes=source_hashes)["passed"]:
    raise SystemExit("Portable bundle privacy check failed")

environment = dict(os.environ, EXWORD_SOURCE_ROOT=str(root), EXWORD_ONEFILE_STAGE=str(stage))
subprocess.run([sys.executable, "-m", "PyInstaller", "--noconfirm", "--clean",
                "--distpath", str(root / "onefile-dist"), str(root / "packaging/onefile.spec")],
               cwd=root, env=environment, check=True)
exe = root / "onefile-dist/EXwordScreenCapture.exe"
report = audit(exe.parent, public_notice_hashes=hashes, public_source_hashes=source_hashes)
if not report["passed"]:
    raise SystemExit("One-file privacy check failed")
subprocess.run([str(exe), "--self-test"], check=True)
target = root / "release-artifacts/EXwordScreenCapture-v1.0.0-windows-x86_64.exe"
import shutil
shutil.copyfile(exe, target)
(Path(str(target) + ".sha256")).write_text(hashlib.sha256(target.read_bytes()).hexdigest() + "  " + target.name + "\n")
(target.with_suffix(".privacy.json")).write_text(json.dumps(report, indent=2) + "\n")
