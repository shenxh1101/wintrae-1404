
import os
from dataclasses import dataclass, field
from typing import Dict, Optional

from .config import Config
from .validator import MaterialValidator, ValidationResult
from .audio_analyzer import AudioAnalyzer, AudioInfo
from .cover_checker import CoverChecker, CoverInfo
from .content_generator import ContentGenerator, GeneratedContent
from .release_manager import ReleaseManager, ReleasePackage
from .utils import ensure_directory


@dataclass
class EpisodeProcessResult:
    episode_number: str
    directory: str
    validation: ValidationResult = None
    audio_info: AudioInfo = None
    cover_info: CoverInfo = None
    generated_content: GeneratedContent = None
    release_package: ReleasePackage = None
    is_valid: bool = False
    errors: list = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "episode_number": self.episode_number,
            "directory": self.directory,
            "validation": self.validation.to_dict() if self.validation else None,
            "audio_info": self.audio_info.to_dict() if self.audio_info else None,
            "cover_info": self.cover_info.to_dict() if self.cover_info else None,
            "generated_content": (
                self.generated_content.to_dict() if self.generated_content else None
            ),
            "release_package": (
                self.release_package.to_dict() if self.release_package else None
            ),
            "is_valid": self.is_valid,
            "errors": self.errors,
        }


class EpisodeProcessor:
    def __init__(self, config: Config = None):
        self.config = config or Config()
        self.validator = MaterialValidator(self.config)
        self.audio_analyzer = AudioAnalyzer(self.config)
        self.cover_checker = CoverChecker(self.config)
        self.content_generator = ContentGenerator(self.config)
        self.release_manager = ReleaseManager(self.config)

        ensure_directory(self.config.input_dir)
        ensure_directory(self.config.output_dir)
        ensure_directory(self.config.archive_dir)

    def process_episode(self, directory: str) -> EpisodeProcessResult:
        result = EpisodeProcessResult(
            episode_number="",
            directory=directory,
        )

        if not os.path.exists(directory):
            result.errors.append(f"目录不存在: {directory}")
            return result

        result.validation = self.validator.validate_directory(directory)
        result.episode_number = result.validation.episode_number or "未知"

        if "audio" in result.validation.files:
            result.audio_info = self.audio_analyzer.analyze(
                result.validation.files["audio"]
            )

        if "cover" in result.validation.files:
            result.cover_info = self.cover_checker.check(
                result.validation.files["cover"]
            )

        audio_duration = result.audio_info.duration_seconds if result.audio_info else 0
        if "guest" in result.validation.files or "summary" in result.validation.files:
            result.generated_content = self.content_generator.generate(
                episode_number=result.episode_number,
                guest_file=result.validation.files.get("guest", ""),
                summary_file=result.validation.files.get("summary", ""),
                audio_duration=audio_duration,
            )

        title = (
            result.generated_content.title_candidates[0]
            if result.generated_content and result.generated_content.title_candidates
            else "未命名"
        )

        result.release_package = self.release_manager.create_release_package(
            episode_number=result.episode_number,
            title=title,
            files=result.validation.files,
            validation_result=result.validation,
            audio_info=result.audio_info,
            cover_info=result.cover_info,
            generated_content=result.generated_content,
        )

        result.is_valid = result.validation.is_valid and (
            result.audio_info.is_valid if result.audio_info else True
        ) and (result.cover_info.is_valid if result.cover_info else True)

        return result

    def confirm_and_release(
        self, result: EpisodeProcessResult, title: Optional[str] = None
    ) -> ReleasePackage:
        if not result.release_package:
            raise ValueError("没有可用的发布包")

        if title:
            result.release_package.title = title

        self.release_manager.execute_renames(result.release_package)

        if result.generated_content:
            self.release_manager.generate_release_documents(
                result.release_package, result.generated_content
            )

        return result.release_package

    def archive_episode(self, result: EpisodeProcessResult) -> bool:
        if not result.release_package:
            return False
        return self.release_manager.archive_episode(result.release_package)
