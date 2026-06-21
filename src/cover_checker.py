
import os
from dataclasses import dataclass, field
from typing import List, Tuple

from .config import Config

try:
    from PIL import Image

    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False


@dataclass
class CoverInfo:
    filepath: str
    filename: str
    width: int = 0
    height: int = 0
    aspect_ratio: float = 0.0
    file_size_bytes: int = 0
    file_size_mb: float = 0.0
    format: str = ""
    mode: str = ""
    is_valid: bool = False
    issues: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "filepath": self.filepath,
            "filename": self.filename,
            "width": self.width,
            "height": self.height,
            "aspect_ratio": self.aspect_ratio,
            "file_size_bytes": self.file_size_bytes,
            "file_size_mb": self.file_size_mb,
            "format": self.format,
            "mode": self.mode,
            "is_valid": self.is_valid,
            "issues": self.issues,
            "warnings": self.warnings,
        }


class CoverChecker:
    def __init__(self, config: Config = None):
        self.config = config or Config()
        self.min_width = self.config.get("cover.min_width", 1400)
        self.min_height = self.config.get("cover.min_height", 1400)
        self.target_ratio = self.config.get("cover.target_ratio", 1.0)
        self.ratio_tolerance = self.config.get("cover.ratio_tolerance", 0.01)
        self.max_file_size_mb = self.config.get("cover.max_file_size_mb", 5)

    def check(self, filepath: str) -> CoverInfo:
        filename = os.path.basename(filepath)
        info = CoverInfo(filepath=filepath, filename=filename)

        if not os.path.exists(filepath):
            info.issues.append(f"文件不存在: {filepath}")
            return info

        info.file_size_bytes = os.path.getsize(filepath)
        info.file_size_mb = info.file_size_bytes / (1024 * 1024)

        if not PIL_AVAILABLE:
            info.warnings.append("Pillow 库未安装，无法进行图片尺寸检查")
            info.warnings.append(f"文件大小: {info.file_size_mb:.2f} MB")
            return info

        try:
            with Image.open(filepath) as img:
                info.width = img.width
                info.height = img.height
                info.format = img.format or ""
                info.mode = img.mode

                if info.height > 0:
                    info.aspect_ratio = info.width / info.height

                self._validate_cover(info)

        except Exception as e:
            info.issues.append(f"解析图片失败: {str(e)}")

        return info

    def _validate_cover(self, info: CoverInfo):
        if info.width < self.min_width:
            info.issues.append(
                f"宽度不足: {info.width}px (最小要求 {self.min_width}px)"
            )

        if info.height < self.min_height:
            info.issues.append(
                f"高度不足: {info.height}px (最小要求 {self.min_height}px)"
            )

        ratio_diff = abs(info.aspect_ratio - self.target_ratio)
        if ratio_diff > self.ratio_tolerance:
            info.issues.append(
                f"比例不符合要求: {info.aspect_ratio:.3f} "
                f"(目标 {self.target_ratio}, 容差 {self.ratio_tolerance})"
            )

        if info.file_size_mb > self.max_file_size_mb:
            info.issues.append(
                f"文件过大: {info.file_size_mb:.2f} MB "
                f"(最大限制 {self.max_file_size_mb} MB)"
            )

        if info.mode not in ["RGB", "RGBA"]:
            info.warnings.append(f"颜色模式为 {info.mode}，建议使用 RGB 或 RGBA")

        info.is_valid = len(info.issues) == 0
