import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from config import Config


class ConfigTests(unittest.TestCase):
    def test_legacy_config_is_migrated_and_defaults_are_merged(self):
        with tempfile.TemporaryDirectory() as temp:
            home = Path(temp)
            xdg_config = home / "xdg-config"
            legacy = home / ".config" / "local-ai"
            legacy.mkdir(parents=True)
            (legacy / "settings.json").write_text(
                json.dumps({"temperature": 1.2}),
                encoding="utf-8",
            )

            with patch.dict(
                os.environ,
                {
                    "HOME": str(home),
                    "XDG_CONFIG_HOME": str(xdg_config),
                },
                clear=False,
            ):
                config = Config()

                self.assertEqual(config.get("temperature"), 1.2)
                self.assertEqual(config.get("context"), 8192)
                self.assertTrue(config.path.exists())

    def test_save_is_persistent(self):
        with tempfile.TemporaryDirectory() as temp:
            home = Path(temp)

            with patch.dict(
                os.environ,
                {
                    "HOME": str(home),
                    "XDG_CONFIG_HOME": str(home / "config"),
                },
                clear=False,
            ):
                config = Config()
                config.set("theme", "light")

                reloaded = Config()
                self.assertEqual(reloaded.get("theme"), "light")


if __name__ == "__main__":
    unittest.main()
