import json
import os
import shutil
from pathlib import Path


APP_DIR_NAME = "aether"
LEGACY_DIR_NAME = "local-ai"


def _xdg_dir(env_name: str, fallback: Path) -> Path:
    value = os.environ.get(env_name)
    return Path(value).expanduser() if value else fallback


class Config:
    def __init__(self):
        base = _xdg_dir(
            "XDG_CONFIG_HOME",
            Path.home() / ".config"
        )

        self.directory = base / APP_DIR_NAME
        self.directory.mkdir(parents=True, exist_ok=True)

        self.path = self.directory / "settings.json"
        self.legacy_path = (
            Path.home()
            / ".config"
            / LEGACY_DIR_NAME
            / "settings.json"
        )

        self.defaults = {
            "thinking": False,
            "context": 8192,
            "temperature": 0.6,
            "top_p": 0.9,
            "top_k": 40,
            "repeat_penalty": 1.1,
            "num_predict": -1,
            "system_prompt": "",
            "theme": "system",
            "selected_model": "qwen3:8b",
            "enter_to_send": True,
            "ollama_url": "http://127.0.0.1:11434",
        }

        self._migrate_legacy_config()
        self.data = self.load()

    def _migrate_legacy_config(self):
        if self.path.exists() or not self.legacy_path.exists():
            return

        try:
            shutil.copy2(self.legacy_path, self.path)
        except OSError as error:
            print(f"Ayarlar taşınamadı: {error}")

    def load(self):
        if not self.path.exists():
            return self.defaults.copy()

        try:
            with self.path.open("r", encoding="utf-8") as file:
                data = json.load(file)

            if not isinstance(data, dict):
                raise ValueError("settings.json bir JSON nesnesi olmalı")

            settings = self.defaults.copy()
            settings.update(data)
            return settings

        except (OSError, ValueError, json.JSONDecodeError) as error:
            print(f"Ayarlar okunamadı: {error}")
            return self.defaults.copy()

    def save(self):
        temporary = self.path.with_suffix(".json.tmp")

        try:
            with temporary.open("w", encoding="utf-8") as file:
                json.dump(
                    self.data,
                    file,
                    indent=4,
                    ensure_ascii=False,
                    sort_keys=True,
                )
                file.write("\n")

            os.chmod(temporary, 0o600)
            temporary.replace(self.path)

        except OSError as error:
            print(f"Ayarlar kaydedilemedi: {error}")

            try:
                temporary.unlink(missing_ok=True)
            except OSError:
                pass

    def get(self, key):
        return self.data.get(key, self.defaults.get(key))

    def set(self, key, value):
        self.data[key] = value
        self.save()
