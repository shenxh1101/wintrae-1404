
import os
import yaml
from pathlib import Path
from typing import Any, Optional


class Config:
    _instance: Optional["Config"] = None
    _config_path_used: Optional[str] = None

    def __new__(cls, config_path: Optional[str] = None):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._load_config(config_path)
            cls._config_path_used = config_path
        elif config_path is not None and config_path != cls._config_path_used:
            cls._instance._load_config(config_path)
            cls._config_path_used = config_path
        return cls._instance

    def _load_config(self, config_path: Optional[str] = None):
        self._config: dict = {}

        if config_path is None:
            config_path = str(Path(__file__).parent.parent / "config.yaml")

        try:
            config_path_obj = Path(config_path)
            if not config_path_obj.exists():
                self._config = self._get_default_config()
                return

            with open(config_path_obj, "r", encoding="utf-8") as f:
                loaded = yaml.safe_load(f)
                if isinstance(loaded, dict):
                    self._config = loaded
                else:
                    self._config = self._get_default_config()
        except (yaml.YAMLError, OSError, IOError, PermissionError):
            self._config = self._get_default_config()
            return

        try:
            base_dir = Path(__file__).parent.parent
            watch_cfg = self._config.get("watch", {})
            if isinstance(watch_cfg, dict):
                input_dir = watch_cfg.get("input_dir", "./input")
                output_dir = watch_cfg.get("output_dir", "./output")
                archive_dir = watch_cfg.get("archive_dir", "./archive")
                watch_cfg["input_dir"] = str(base_dir / input_dir) if not os.path.isabs(str(input_dir)) else str(input_dir)
                watch_cfg["output_dir"] = str(base_dir / output_dir) if not os.path.isabs(str(output_dir)) else str(output_dir)
                watch_cfg["archive_dir"] = str(base_dir / archive_dir) if not os.path.isabs(str(archive_dir)) else str(archive_dir)
                self._config["watch"] = watch_cfg
        except Exception:
            pass

    def _get_default_config(self) -> dict:
        return {
            "watch": {
                "input_dir": str(Path(__file__).parent.parent / "input"),
                "output_dir": str(Path(__file__).parent.parent / "output"),
                "archive_dir": str(Path(__file__).parent.parent / "archive"),
            },
            "naming": {
                "episode_pattern": r"^(\d{3})",
                "audio_extensions": [".mp3", ".wav", ".m4a", ".flac", ".aac"],
                "cover_extensions": [".jpg", ".jpeg", ".png", ".webp"],
                "guest_extensions": [".md", ".txt"],
                "summary_extensions": [".md", ".txt"],
                "required_files": ["audio", "cover", "guest", "summary"],
            },
            "audio": {
                "min_duration_seconds": 60,
                "max_duration_seconds": 7200,
                "preferred_format": "mp3",
                "preferred_bitrate": 192000,
            },
            "cover": {
                "min_width": 1400,
                "min_height": 1400,
                "target_ratio": 1.0,
                "ratio_tolerance": 0.01,
                "max_file_size_mb": 5,
            },
            "sensitive_words": [
                "TODO", "待补充", "placeholder", "xxx", "XXX", "示例", "test", "TEST"
            ],
            "templates": {
                "title_candidates": 5,
                "social_media_platforms": ["weibo", "xiaohongshu", "wechat", "twitter"],
            },
            "checklist": {
                "items": [
                    "音频文件已校验", "封面图符合规范", "嘉宾资料已确认",
                    "节目简介已审核", "标题候选已生成", "时间轴草稿已生成",
                    "社媒文案已准备", "文件已批量重命名",
                ]
            },
        }

    def get(self, key: str, default: Any = None) -> Any:
        if not key:
            return default
        keys = key.split(".")
        value = self._config
        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default
        return value

    @property
    def input_dir(self) -> str:
        val = self.get("watch.input_dir")
        return str(val) if val else str(Path(__file__).parent.parent / "input")

    @property
    def output_dir(self) -> str:
        val = self.get("watch.output_dir")
        return str(val) if val else str(Path(__file__).parent.parent / "output")

    @property
    def archive_dir(self) -> str:
        val = self.get("watch.archive_dir")
        return str(val) if val else str(Path(__file__).parent.parent / "archive")
