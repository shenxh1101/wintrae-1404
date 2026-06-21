
import os
from dataclasses import dataclass, field
from typing import Dict, Optional, Tuple

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
        try:
            validation_dict = None
            try:
                if self.validation is not None:
                    validation_dict = self.validation.to_dict()
            except Exception:
                pass

            audio_dict = None
            try:
                if self.audio_info is not None:
                    audio_dict = self.audio_info.to_dict()
            except Exception:
                pass

            cover_dict = None
            try:
                if self.cover_info is not None:
                    cover_dict = self.cover_info.to_dict()
            except Exception:
                pass

            content_dict = None
            try:
                if self.generated_content is not None:
                    content_dict = self.generated_content.to_dict()
            except Exception:
                pass

            release_dict = None
            try:
                if self.release_package is not None:
                    release_dict = self.release_package.to_dict()
            except Exception:
                pass

            errors_list = []
            try:
                if isinstance(self.errors, list):
                    errors_list = [str(e) for e in self.errors if e is not None]
            except Exception:
                pass

            return {
                "episode_number": str(self.episode_number) if self.episode_number else "",
                "directory": str(self.directory) if self.directory else "",
                "validation": validation_dict,
                "audio_info": audio_dict,
                "cover_info": cover_dict,
                "generated_content": content_dict,
                "release_package": release_dict,
                "is_valid": bool(self.is_valid),
                "errors": errors_list,
            }
        except Exception:
            return {
                "episode_number": str(self.episode_number) if self.episode_number else "",
                "directory": str(self.directory) if self.directory else "",
                "is_valid": False,
                "errors": ["结果序列化失败"],
            }


class EpisodeProcessor:
    def __init__(self, config: Config = None):
        try:
            self.config = config or Config()
        except Exception:
            from .config import Config
            self.config = Config()

        try:
            self.validator = MaterialValidator(self.config)
        except Exception:
            self.validator = None

        try:
            self.audio_analyzer = AudioAnalyzer(self.config)
        except Exception:
            self.audio_analyzer = None

        try:
            self.cover_checker = CoverChecker(self.config)
        except Exception:
            self.cover_checker = None

        try:
            self.content_generator = ContentGenerator(self.config)
        except Exception:
            self.content_generator = None

        try:
            self.release_manager = ReleaseManager(self.config)
        except Exception:
            self.release_manager = None

        try:
            in_dir = getattr(self.config, "input_dir", "./input")
            if in_dir:
                ensure_directory(str(in_dir))
        except Exception:
            pass

        try:
            out_dir = getattr(self.config, "output_dir", "./output")
            if out_dir:
                ensure_directory(str(out_dir))
        except Exception:
            pass

        try:
            arc_dir = getattr(self.config, "archive_dir", "./archive")
            if arc_dir:
                ensure_directory(str(arc_dir))
        except Exception:
            pass

    def process_episode(self, directory: str) -> EpisodeProcessResult:
        result = EpisodeProcessResult(
            episode_number="未知",
            directory=str(directory) if directory else "",
        )

        try:
            if not directory or not isinstance(directory, str):
                result.errors.append("目录参数无效")
                return result

            try:
                if not os.path.exists(directory):
                    result.errors.append(f"目录不存在: {directory}")
                    return result
            except Exception:
                result.errors.append("目录检查异常")
                return result

            if self.validator is None:
                result.errors.append("素材校验器未初始化")
                return result

            try:
                result.validation = self.validator.validate_directory(directory)
            except Exception as e:
                result.errors.append(f"素材校验失败: {e}")
                return result

            try:
                if result.validation is not None:
                    ep_num = getattr(result.validation, "episode_number", None)
                    result.episode_number = str(ep_num) if ep_num else "未知"
            except Exception:
                result.episode_number = "未知"

            try:
                vfiles = getattr(result.validation, "files", {}) if result.validation else {}
            except Exception:
                vfiles = {}

            if self.audio_analyzer is not None and isinstance(vfiles, dict) and "audio" in vfiles:
                try:
                    audio_path = vfiles.get("audio", "")
                    if audio_path and isinstance(audio_path, str) and os.path.exists(audio_path):
                        result.audio_info = self.audio_analyzer.analyze(audio_path)
                except Exception as e:
                    result.errors.append(f"音频分析失败: {e}")

            if self.cover_checker is not None and isinstance(vfiles, dict) and "cover" in vfiles:
                try:
                    cover_path = vfiles.get("cover", "")
                    if cover_path and isinstance(cover_path, str) and os.path.exists(cover_path):
                        result.cover_info = self.cover_checker.check(cover_path)
                except Exception as e:
                    result.errors.append(f"封面检查失败: {e}")

            audio_duration = 0
            try:
                if result.audio_info is not None:
                    dur = getattr(result.audio_info, "duration_seconds", 0)
                    audio_duration = dur if isinstance(dur, (int, float)) and dur >= 0 else 0
            except Exception:
                audio_duration = 0

            has_text_files = (
                isinstance(vfiles, dict)
                and ("guest" in vfiles or "summary" in vfiles)
            )
            if self.content_generator is not None and has_text_files:
                try:
                    guest_file = vfiles.get("guest", "") if isinstance(vfiles, dict) else ""
                    summary_file = vfiles.get("summary", "") if isinstance(vfiles, dict) else ""
                    result.generated_content = self.content_generator.generate(
                        episode_number=result.episode_number,
                        guest_file=str(guest_file) if guest_file else "",
                        summary_file=str(summary_file) if summary_file else "",
                        audio_duration=audio_duration,
                    )
                except Exception as e:
                    result.errors.append(f"文案生成失败: {e}")

            title = "未命名"
            try:
                if result.generated_content is not None:
                    tcs = getattr(result.generated_content, "title_candidates", None)
                    if isinstance(tcs, list) and len(tcs) > 0:
                        first_candidate = tcs[0]
                        if isinstance(first_candidate, str) and first_candidate.strip():
                            title = first_candidate
            except Exception:
                title = "未命名"

            if self.release_manager is not None:
                try:
                    result.release_package = self.release_manager.create_release_package(
                        episode_number=result.episode_number,
                        title=title,
                        files=vfiles if isinstance(vfiles, dict) else {},
                        validation_result=result.validation,
                        audio_info=result.audio_info,
                        cover_info=result.cover_info,
                        generated_content=result.generated_content,
                    )
                except Exception as e:
                    result.errors.append(f"发布包创建失败: {e}")

            try:
                v_valid = bool(getattr(result.validation, "is_valid", False)) if result.validation else False
                a_valid = True
                if result.audio_info is not None:
                    a_valid = bool(getattr(result.audio_info, "is_valid", False))
                c_valid = True
                if result.cover_info is not None:
                    c_valid = bool(getattr(result.cover_info, "is_valid", False))
                result.is_valid = v_valid and a_valid and c_valid
            except Exception:
                result.is_valid = False

        except Exception as e:
            try:
                result.errors.append(f"处理流程异常: {e}")
            except Exception:
                pass

        return result

    def confirm_and_release(
        self, result: EpisodeProcessResult, title: Optional[str] = None
    ) -> Tuple[Optional[ReleasePackage], list]:
        errors: list = []

        try:
            if result is None:
                errors.append("处理结果为空")
                return None, errors

            if result.release_package is None:
                errors.append("没有可用的发布包")
                return None, errors

            if self.release_manager is None:
                errors.append("发布管理器未初始化")
                return result.release_package, errors

            if title and isinstance(title, str) and title.strip():
                try:
                    result.release_package.title = title
                except Exception:
                    pass

            try:
                self.release_manager.execute_renames(result.release_package)
            except Exception as e:
                errors.append(f"重命名执行失败: {e}")

            if result.generated_content is not None:
                try:
                    self.release_manager.generate_release_documents(
                        result.release_package, result.generated_content
                    )
                except Exception as e:
                    errors.append(f"发布文档生成失败: {e}")

            return result.release_package, errors

        except Exception as e:
            try:
                errors.append(f"确认发布异常: {e}")
            except Exception:
                pass
            return result.release_package if result is not None else None, errors

    def archive_episode(self, result: EpisodeProcessResult) -> bool:
        try:
            if result is None or result.release_package is None:
                return False
            if self.release_manager is None:
                return False
            return bool(self.release_manager.archive_episode(result.release_package))
        except Exception:
            return False
