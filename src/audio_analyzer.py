
import os
from dataclasses import dataclass, field
from typing import List, Optional

from .config import Config
from .utils import format_duration

try:
    from mutagen import File as MutagenFile
    from mutagen.mp3 import MP3
    from mutagen.mp4 import MP4
    from mutagen.flac import FLAC
    from mutagen.wave import WAVE
    MUTAGEN_AVAILABLE = True
except ImportError:
    MUTAGEN_AVAILABLE = False


@dataclass
class AudioInfo:
    filepath: str
    filename: str
    duration_seconds: float = 0.0
    duration_formatted: str = "00:00"
    format: str = ""
    bitrate: int = 0
    sample_rate: int = 0
    channels: int = 0
    title: str = ""
    artist: str = ""
    album: str = ""
    is_valid: bool = False
    issues: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "filepath": self.filepath,
            "filename": self.filename,
            "duration_seconds": self.duration_seconds,
            "duration_formatted": self.duration_formatted,
            "format": self.format,
            "bitrate": self.bitrate,
            "sample_rate": self.sample_rate,
            "channels": self.channels,
            "title": self.title,
            "artist": self.artist,
            "album": self.album,
            "is_valid": self.is_valid,
            "issues": self.issues,
            "warnings": self.warnings,
        }


class AudioAnalyzer:
    def __init__(self, config: Config = None):
        self.config = config or Config()
        try:
            self.min_duration = float(self.config.get("audio.min_duration_seconds", 60))
        except (TypeError, ValueError):
            self.min_duration = 60.0
        try:
            self.max_duration = float(self.config.get("audio.max_duration_seconds", 7200))
        except (TypeError, ValueError):
            self.max_duration = 7200.0
        self.preferred_format = str(self.config.get("audio.preferred_format", "mp3"))
        try:
            self.preferred_bitrate = int(self.config.get("audio.preferred_bitrate", 192000))
        except (TypeError, ValueError):
            self.preferred_bitrate = 192000

    def analyze(self, filepath: str) -> AudioInfo:
        try:
            filename = os.path.basename(filepath) if filepath else ""
        except (OSError, ValueError, TypeError):
            filename = str(filepath) if filepath else ""
        info = AudioInfo(filepath=filepath or "", filename=filename)

        if not filepath or not os.path.exists(filepath):
            info.issues.append(f"文件不存在: {filepath}")
            return info

        if not MUTAGEN_AVAILABLE:
            info.warnings.append("mutagen 库未安装，仅能进行基础检查")
            try:
                file_size = os.path.getsize(filepath)
                info.warnings.append(f"文件大小: {file_size / 1024 / 1024:.2f} MB")
            except (OSError, PermissionError):
                pass
            self._check_basics(filepath, info)
            return info

        try:
            try:
                audio = MutagenFile(filepath)
            except Exception:
                audio = None
            if audio is None:
                info.issues.append("无法识别的音频格式")
                return info

            self._extract_metadata(audio, info)
            self._validate_audio(info)

        except Exception as e:
            info.issues.append(f"解析音频失败: {str(e)}")

        return info

    def _extract_metadata(self, audio, info: AudioInfo):
        try:
            ext = os.path.splitext(info.filename)[1].lower()
            info.format = ext.lstrip(".")
        except (OSError, ValueError, TypeError):
            pass

        try:
            if hasattr(audio, "info"):
                audio_info = audio.info
                if hasattr(audio_info, "length") and audio_info.length is not None:
                    try:
                        info.duration_seconds = float(audio_info.length)
                        if info.duration_seconds < 0:
                            info.duration_seconds = 0.0
                        info.duration_formatted = format_duration(info.duration_seconds)
                    except (TypeError, ValueError):
                        pass
                if hasattr(audio_info, "bitrate") and audio_info.bitrate is not None:
                    try:
                        info.bitrate = int(audio_info.bitrate)
                        if info.bitrate < 0:
                            info.bitrate = 0
                    except (TypeError, ValueError):
                        pass
                if hasattr(audio_info, "sample_rate") and audio_info.sample_rate is not None:
                    try:
                        info.sample_rate = int(audio_info.sample_rate)
                        if info.sample_rate < 0:
                            info.sample_rate = 0
                    except (TypeError, ValueError):
                        pass
                if hasattr(audio_info, "channels") and audio_info.channels is not None:
                    try:
                        info.channels = int(audio_info.channels)
                        if info.channels < 0:
                            info.channels = 0
                    except (TypeError, ValueError):
                        pass
        except Exception:
            pass

        try:
            if hasattr(audio, "tags") and audio.tags:
                tags = audio.tags
                if hasattr(tags, "get"):
                    info.title = self._get_tag(tags, ["title", "TIT2", "©nam"])
                    info.artist = self._get_tag(tags, ["artist", "TPE1", "©ART"])
                    info.album = self._get_tag(tags, ["album", "TALB", "©alb"])
        except Exception:
            pass

    def _get_tag(self, tags, keys: List[str]) -> str:
        if not tags or not keys:
            return ""
        for key in keys:
            try:
                value = tags.get(key)
            except Exception:
                continue
            if value:
                try:
                    if isinstance(value, list):
                        return str(value[0]) if len(value) > 0 else ""
                    return str(value)
                except (TypeError, ValueError):
                    continue
        return ""

    def _validate_audio(self, info: AudioInfo):
        try:
            if info.duration_seconds <= 0:
                info.issues.append("音频时长为0或无法读取")
            elif info.duration_seconds < self.min_duration:
                info.issues.append(
                    f"音频时长过短: {info.duration_formatted} "
                    f"(最短要求 {format_duration(self.min_duration)})"
                )
            elif info.duration_seconds > self.max_duration:
                info.issues.append(
                    f"音频时长过长: {info.duration_formatted} "
                    f"(最长限制 {format_duration(self.max_duration)})"
                )

            if info.bitrate and self.preferred_bitrate > 0 and info.bitrate < self.preferred_bitrate * 0.8:
                try:
                    info.warnings.append(
                        f"比特率偏低: {info.bitrate // 1000} kbps "
                        f"(推荐 {self.preferred_bitrate // 1000} kbps)"
                    )
                except (ZeroDivisionError, TypeError, ValueError):
                    pass

            if info.format and info.format != self.preferred_format:
                info.warnings.append(
                    f"格式为 {info.format} (推荐 {self.preferred_format})"
                )
        except Exception:
            pass

        info.is_valid = len(info.issues) == 0

    def _check_basics(self, filepath: str, info: AudioInfo):
        try:
            ext = os.path.splitext(filepath)[1].lower()
            info.format = ext.lstrip(".")
        except (OSError, ValueError, TypeError):
            pass
        info.is_valid = False
