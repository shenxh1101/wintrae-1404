
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
        self.min_duration = self.config.get("audio.min_duration_seconds", 60)
        self.max_duration = self.config.get("audio.max_duration_seconds", 7200)
        self.preferred_format = self.config.get("audio.preferred_format", "mp3")
        self.preferred_bitrate = self.config.get("audio.preferred_bitrate", 192000)

    def analyze(self, filepath: str) -> AudioInfo:
        filename = os.path.basename(filepath)
        info = AudioInfo(filepath=filepath, filename=filename)

        if not os.path.exists(filepath):
            info.issues.append(f"文件不存在: {filepath}")
            return info

        if not MUTAGEN_AVAILABLE:
            info.warnings.append("mutagen 库未安装，仅能进行基础检查")
            file_size = os.path.getsize(filepath)
            info.warnings.append(f"文件大小: {file_size / 1024 / 1024:.2f} MB")
            self._check_basics(filepath, info)
            return info

        try:
            audio = MutagenFile(filepath)
            if audio is None:
                info.issues.append("无法识别的音频格式")
                return info

            self._extract_metadata(audio, info)
            self._validate_audio(info)

        except Exception as e:
            info.issues.append(f"解析音频失败: {str(e)}")

        return info

    def _extract_metadata(self, audio, info: AudioInfo):
        ext = os.path.splitext(info.filename)[1].lower()
        info.format = ext.lstrip(".")

        if hasattr(audio, "info"):
            audio_info = audio.info
            if hasattr(audio_info, "length"):
                info.duration_seconds = audio_info.length
                info.duration_formatted = format_duration(audio_info.length)
            if hasattr(audio_info, "bitrate"):
                info.bitrate = audio_info.bitrate
            if hasattr(audio_info, "sample_rate"):
                info.sample_rate = audio_info.sample_rate
            if hasattr(audio_info, "channels"):
                info.channels = audio_info.channels

        if hasattr(audio, "tags") and audio.tags:
            tags = audio.tags
            if hasattr(tags, "get"):
                info.title = self._get_tag(tags, ["title", "TIT2", "©nam"])
                info.artist = self._get_tag(tags, ["artist", "TPE1", "©ART"])
                info.album = self._get_tag(tags, ["album", "TALB", "©alb"])

    def _get_tag(self, tags, keys: List[str]) -> str:
        for key in keys:
            value = tags.get(key)
            if value:
                if isinstance(value, list):
                    return str(value[0])
                return str(value)
        return ""

    def _validate_audio(self, info: AudioInfo):
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

        if info.bitrate and info.bitrate < self.preferred_bitrate * 0.8:
            info.warnings.append(
                f"比特率偏低: {info.bitrate // 1000} kbps "
                f"(推荐 {self.preferred_bitrate // 1000} kbps)"
            )

        if info.format and info.format != self.preferred_format:
            info.warnings.append(
                f"格式为 {info.format} (推荐 {self.preferred_format})"
            )

        info.is_valid = len(info.issues) == 0

    def _check_basics(self, filepath: str, info: AudioInfo):
        ext = os.path.splitext(filepath)[1].lower()
        info.format = ext.lstrip(".")
        info.is_valid = False
