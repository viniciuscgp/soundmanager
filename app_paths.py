"""Keep bundled resources separate from persistent, writable user settings."""
from pathlib import Path
import os
import sys

APP_DIR = Path(__file__).resolve().parent


def state_dir() -> Path:
    if not getattr(sys, "frozen", False):
        return APP_DIR / ".state"
    if sys.platform == "win32":
        base = Path(os.environ.get("LOCALAPPDATA") or Path.home() / "AppData" / "Local")
        return base / "SoundManager"
    base = Path(os.environ.get("XDG_CONFIG_HOME") or Path.home() / ".config")
    return base / "sound-manager"


def default_library_dir() -> Path:
    return Path.home() if getattr(sys, "frozen", False) else APP_DIR.parent
