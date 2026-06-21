
import os
from dataclasses import dataclass, field
from typing import List

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
        try:
            self.min_width = int(self.config.get("cover.min_width", 1400))
        except (TypeError, ValueError):
            self.min_width = 1400
        try:
            self.min_height = int(self.config.get("cover.min_height", 1400))
        except (TypeError, ValueError):
            self.min_height = 1400
        try:
            self.target_ratio = float(self.config.get("cover.target_ratio", 1.0))
        except (TypeError, ValueError):
            self.target_ratio = 1.0
        try:
            self.ratio_tolerance = float(self.config.get("cover.ratio_tolerance", 0.01))
        except (TypeError, ValueError):
            self.ratio_tolerance = 0.01
        try:
            self.max_file_size_mb = float(self.config.get("cover.max_file_size_mb", 5))
        except (TypeError, ValueError):
            self.max_file_size_mb = 5.0

    def check(self, filepath: str) -> CoverInfo:
        try:
            filename = os.path.basename(filepath) if filepath else ""
        except (OSError, ValueError, TypeError):
            filename = str(filepath) if filepath else ""
        info = CoverInfo(filepath=filepath or "", filename=filename)

        if not filepath or not os.path.exists(filepath):
            info.issues.append(f"文件不存在: {filepath}")
            return info

        try:
            info.file_size_bytes = int(os.path.getsize(filepath))
            if info.file_size_bytes < 0:
                info.file_size_bytes = 0
        except (OSError, PermissionError, ValueError, TypeError):
            info.file_size_bytes = 0
        try:
            info.file_size_mb = info.file_size_bytes / (1024 * 1024) if info.file_size_bytes >= 0 else 0.0
        except (ZeroDivisionError, TypeError, ValueError):
            info.file_size_mb = 0.0

        if not PIL_AVAILABLE:
            info.warnings.append("Pillow 库未安装，无法进行图片尺寸检查")
            info.warnings.append(f"文件大小: {info.file_size_mb:.2f} MB")
            return info

        try:
            with Image.open(filepath) as img:
                try:
                    info.width = int(img.width) if img.width else 0
                    if info.width < 0:
                        info.width = 0
                except (TypeError, ValueError):
                    info.width = 0
                try:
                    info.height = int(img.height) if img.height else 0
                    if info.height < 0:
                        info.height = 0
                except (TypeError, ValueError):
                    info.height = 0
                try:
                    info.format = str(img.format) if img.format else ""
                except (TypeError, ValueError):
                    info.format = ""
                try:
                    info.mode = str(img.mode) if img.mode else ""
                except (TypeError, ValueError):
                    info.mode = ""

                if info.height > 0 and info.width >= 0:
                    try:
                        info.aspect_ratio = info.width / info.height
                        if info.aspect_ratio < 0:
                            info.aspect_ratio = 0.0
                    except (ZeroDivisionError, TypeError, ValueError):
                        info.aspect_ratio = 0.0

                self._validate_cover(info)

        except Exception as e:
            info.issues.append(f"解析图片失败: {str(e)}")

        return info

    def _validate_cover(self, info: CoverInfo):
        try:
            if info.width < self.min_width:
                info.issues.append(
                    f"宽度不足: {info.width}px (最小要求 {self.min_width}px)"
                )

            if info.height < self.min_height:
                info.issues.append(
                    f"高度不足: {info.height}px (最小要求 {self.min_height}px)"
                )

            try:
                ratio_diff = abs(info.aspect_ratio - self.target_ratio)
                if ratio_diff > self.ratio_tolerance:
                    info.issues.append(
                        f"比例不符合要求: {info.aspect_ratio:.3f} "
                        f"(目标 {self.target_ratio}, 容差 {self.ratio_tolerance})"
                    )
            except (TypeError, ValueError):
                pass

            if info.file_size_mb > self.max_file_size_mb:
                info.issues.append(
                    f"文件过大: {info.file_size_mb:.2f} MB "
                    f"(最大限制 {self.max_file_size_mb} MB)"
                )

            if info.mode and info.mode not in ["RGB", "RGBA"]:
                info.warnings.append(f"颜色模式为 {info.mode}，建议使用 RGB 或 RGBA")
        except Exception:
            pass

        info.is_valid = len(info.issues) == 0
