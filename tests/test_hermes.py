from __future__ import annotations

import sys
from pathlib import Path
from types import SimpleNamespace
import unittest


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from skinwalker.hermes import HermesBridge  # noqa: E402


class HermesBridgeTests(unittest.TestCase):
    def _bridge_for_home(self, home: Path) -> HermesBridge:
        bridge = HermesBridge.__new__(HermesBridge)
        bridge.hermes_root = home
        bridge._get_hermes_home = lambda: home
        bridge._skin_engine = SimpleNamespace(_BUILTIN_SKINS={"default": {"name": "default"}})
        return bridge

    def test_list_user_skins_deduplicates_visible_names(self) -> None:
        home = ROOT / ".tmp_hermes_home"
        skins = home / "skins"
        skins.mkdir(parents=True, exist_ok=True)
        try:
            (skins / "cass-ascii.yaml").write_text("name: cass-ascii\ndescription: primary\n", encoding="utf-8")
            (skins / "cass-ascii-backup.yaml").write_text("name: cass-ascii\ndescription: backup\n", encoding="utf-8")
            bridge = self._bridge_for_home(home)
            entries = bridge.list_user_skins()
        finally:
            for path in sorted(skins.glob("*"), reverse=True):
                path.unlink(missing_ok=True)
            skins.rmdir()
            home.rmdir()

        self.assertEqual(len(entries), 1)
        self.assertEqual(entries[0].name, "cass-ascii")
        self.assertIn("Duplicate definitions ignored", entries[0].note)

    def test_activate_skin_targets_specific_profile_config(self) -> None:
        home = ROOT / ".tmp_profile_home"
        profile_root = ROOT / ".tmp_profile_target"
        profile_root.mkdir(parents=True, exist_ok=True)
        config_path = profile_root / "config.yaml"
        try:
            bridge = self._bridge_for_home(home)
            bridge.config_path_for_profile = lambda profile=None: config_path  # type: ignore[method-assign]
            bridge.activate_skin("demo", profile="skinwalker-test-profile")
            content = config_path.read_text(encoding="utf-8")
        finally:
            config_path.unlink(missing_ok=True)
            profile_root.rmdir()

        self.assertIn("display:", content)
        self.assertIn("skin: demo", content)


if __name__ == "__main__":
    unittest.main()
