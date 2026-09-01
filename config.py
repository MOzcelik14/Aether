import json
from pathlib import Path


class Config:

    def __init__(self):

        self.directory = (
            Path.home()
            / ".config"
            / "local-ai"
        )

        self.directory.mkdir(
            parents=True,
            exist_ok=True
        )

        self.path = (
            self.directory
            / "settings.json"
        )

        self.defaults = {
            "thinking": False,
            "context": 8192,
            "temperature": 0.6,
            "theme": "dark",
            "selected_model": "qwen3:8b",

            "enter_to_send": True,
            "ollama_url": (
                "http://127.0.0.1:11434"
            ),
        }

        self.data = self.load()

    def load(self):

        if not self.path.exists():
            return self.defaults.copy()

        try:

            with self.path.open(
                "r",
                encoding="utf-8"
            ) as file:

                data = json.load(file)

            settings = self.defaults.copy()
            settings.update(data)

            return settings

        except Exception as error:

            print(
                f"Ayarlar okunamadı: {error}"
            )

            return self.defaults.copy()

    def save(self):

        try:

            with self.path.open(
                "w",
                encoding="utf-8"
            ) as file:

                json.dump(
                    self.data,
                    file,
                    indent=4,
                    ensure_ascii=False
                )

        except Exception as error:

            print(
                f"Ayarlar kaydedilemedi: {error}"
            )

    def get(self, key):

        return self.data.get(
            key,
            self.defaults.get(key)
        )

    def set(self, key, value):

        self.data[key] = value
        self.save()
