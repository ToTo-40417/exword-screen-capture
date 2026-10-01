"""Build a headless wheel without collecting Qt, libusb or FFmpeg binaries."""
from pathlib import Path
import subprocess
import sys

root = Path(__file__).resolve().parents[1]
subprocess.run([sys.executable, "-m", "pip", "wheel", "--no-deps", "--wheel-dir",
                str(root / "dist-cli"), str(root)], check=True)
