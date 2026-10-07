from pathlib import Path
import os
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app_paths import APP_DIR, default_library_dir, state_dir


class AppPathsTests(unittest.TestCase):
    def test_source_mode_preserves_existing_portable_preferences(self):
        with patch.object(sys, "frozen", False, create=True):
            self.assertEqual(state_dir(), APP_DIR / ".state")
            self.assertEqual(default_library_dir(), APP_DIR.parent)

    def test_windows_bundle_stores_preferences_outside_resources(self):
        user_data = str(Path.home() / "packaging-test-user-data")
        with patch.object(sys, "frozen", True, create=True), patch.object(sys, "platform", "win32"), \
                patch.dict(os.environ, {"LOCALAPPDATA": user_data}):
            self.assertEqual(state_dir(), Path(user_data) / "SoundManager")
            self.assertEqual(default_library_dir(), Path.home())

    def test_linux_bundle_respects_xdg_and_home_fallback(self):
        config = str(Path.home() / "packaging-test-config")
        with patch.object(sys, "frozen", True, create=True), patch.object(sys, "platform", "linux"), \
                patch.dict(os.environ, {"XDG_CONFIG_HOME": config}):
            self.assertEqual(state_dir(), Path(config) / "sound-manager")
            os.environ.pop("XDG_CONFIG_HOME")
            self.assertEqual(state_dir(), Path.home() / ".config" / "sound-manager")
