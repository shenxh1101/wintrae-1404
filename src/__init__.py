
import os
import yaml
from pathlib import Path


class Config:
    _instance = None

    def __new__(cls, config_path=None):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._load_config(config_path)
        return cls._instance

    def _load_config(self, config_path=None):
        if config_path is None:
            config_path = Path(__file__).parent.parent / "config.yaml"

        with open(config_path, "r", encoding="utf-8") as f:
            self._config = yaml.safe_load(f)

        base_dir = Path(__file__).parent.parent
        self._config["watch"]["input_dir"] = str(
            base_dir / self._config["watch"]["input_dir"]
        )
        self._config["watch"]["output_dir"] = str(
            base_dir / self._config["watch"]["output_dir"]
        )
        self._config["watch"]["archive_dir"] = str(
            base_dir / self._config["watch"]["archive_dir"]
        )

    def get(self, key, default=None):
        keys = key.split(".")
        value = self._config
        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default
        return value

    @property
    def input_dir(self):
        return self.get("watch.input_dir")

    @property
    def output_dir(self):
        return self.get("watch.output_dir")

    @property
    def archive_dir(self):
        return self.get("watch.archive_dir")
