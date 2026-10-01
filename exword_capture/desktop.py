"""Optional Linux user-local desktop entry; never run during packaging."""
from pathlib import Path
import shutil

APP_ID = "io.github.ToTo-40417.exword-screen-capture"


def install_launcher(application, icon, data_home):
    application, icon, data_home = Path(application).resolve(), Path(icon).resolve(), Path(data_home)
    if not application.is_file() or not icon.is_file() or not data_home.is_absolute():
        raise ValueError("Use an existing application/icon and an absolute data directory")
    path = str(application)
    if "\n" in path or "\r" in path or "%" in path:
        raise ValueError("Unsupported character in launcher path")
    # Desktop Entry Exec escaping, not shell quoting. No shell is invoked.
    for character in ("\\", '"', "`", "$"):
        path = path.replace(character, "\\" + character)
    path = path.replace("\\", "\\\\")
    icons = data_home / "icons/hicolor/256x256/apps"
    applications = data_home / "applications"
    icons.mkdir(parents=True, exist_ok=True)
    applications.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(icon, icons / (APP_ID + ".png"))
    target = applications / (APP_ID + ".desktop")
    target.write_text("[Desktop Entry]\nType=Application\nName=EX-word Screen Capture\n"
                      f'Exec="{path}"\nIcon={APP_ID}\nTerminal=false\nCategories=Utility;\n', encoding="utf-8")
    return target
