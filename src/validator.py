
import os
import re
from pathlib import Path
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass, field

from .config import Config
from .utils import (
    extract_episode_number,
    get_file_extension,
    list_files_by_extension,
    read_text_file,
)


@dataclass
class ValidationResult:
    episode_number: Optional[str] = None
    is_valid: bool = False
    missing_files: List[str] = field(default_factory=list)
    naming_issues: List[str] = field(default_factory=list)
    sensitive_words_found: List[Tuple[str, str, str]] = field(default_factory=list)
    files: Dict[str, str] = field(default_factory=dict)
    warnings: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict:
        return {
            "episode_number": self.episode_number,
            "is_valid": self.is_valid,
            "missing_files": self.missing_files,
            "naming_issues": self.naming_issues,
            "sensitive_words_found": [
                {"file": f, "word": w, "context": c}
                for f, w, c in self.sensitive_words_found
            ],
            "files": self.files,
            "warnings": self.warnings,
        }


class MaterialValidator:
    def __init__(self, config: Config = None):
        self.config = config or Config()
        self.audio_extensions = self.config.get("naming.audio_extensions", [".mp3"])
        self.cover_extensions = self.config.get("naming.cover_extensions", [".jpg"])
        self.guest_extensions = self.config.get("naming.guest_extensions", [".md"])
        self.summary_extensions = self.config.get(
            "naming.summary_extensions", [".md"]
        )
        self.episode_pattern = self.config.get(
            "naming.episode_pattern", r"^(\d{3})"
        )
        self.sensitive_words = self.config.get("sensitive_words", [])
        self.required_files = self.config.get(
            "naming.required_files", ["audio", "cover", "guest", "summary"]
        )

    def validate_directory(self, directory: str) -> ValidationResult:
        result = ValidationResult()

        try:
            if directory is None:
                result.warnings.append("目录参数为空")
                result.missing_files = list(self.required_files)
                return result
            if not isinstance(directory, str) or not directory.strip():
                result.warnings.append("目录路径无效")
                result.missing_files = list(self.required_files)
                return result
        except Exception:
            result.warnings.append("目录参数异常")
            result.missing_files = list(self.required_files) if isinstance(self.required_files, list) else []
            return result

        try:
            if not os.path.exists(directory):
                result.warnings.append(f"目录不存在: {directory}")
                result.missing_files = list(self.required_files) if isinstance(self.required_files, list) else []
                return result
        except (OSError, ValueError, TypeError) as e:
            result.warnings.append(f"检查目录时出错: {e}")
            result.missing_files = list(self.required_files) if isinstance(self.required_files, list) else []
            return result

        try:
            if not os.path.isdir(directory):
                result.warnings.append(f"路径不是目录: {directory}")
                result.missing_files = list(self.required_files) if isinstance(self.required_files, list) else []
                return result
        except (OSError, ValueError, TypeError) as e:
            result.warnings.append(f"检查目录类型时出错: {e}")
            result.missing_files = list(self.required_files) if isinstance(self.required_files, list) else []
            return result

        try:
            if not os.access(directory, os.R_OK):
                result.warnings.append(f"目录无读取权限: {directory}")
                result.missing_files = list(self.required_files) if isinstance(self.required_files, list) else []
                return result
        except Exception as e:
            result.warnings.append(f"检查目录权限时出错: {e}")
            result.missing_files = list(self.required_files) if isinstance(self.required_files, list) else []
            return result

        try:
            dir_contents = os.listdir(directory)
            if len(dir_contents) == 0:
                result.warnings.append("目录为空，未找到任何素材文件")
                result.missing_files = list(self.required_files) if isinstance(self.required_files, list) else []
                return result
        except PermissionError:
            result.warnings.append(f"无法列出目录内容（权限不足）: {directory}")
            result.missing_files = list(self.required_files) if isinstance(self.required_files, list) else []
            return result
        except (OSError, ValueError, TypeError) as e:
            result.warnings.append(f"列出目录内容时出错: {e}")
            result.missing_files = list(self.required_files) if isinstance(self.required_files, list) else []
            return result

        try:
            episode_num = self._detect_episode_number(directory)
            result.episode_number = episode_num
        except Exception as e:
            result.warnings.append(f"检测期号时出错: {e}")
            result.episode_number = None

        try:
            files = self._categorize_files(directory)
            result.files = files
        except Exception as e:
            result.warnings.append(f"分类文件时出错: {e}")
            result.files = {}
            files = {}

        try:
            self._check_missing_files(files, result)
        except Exception as e:
            result.warnings.append(f"检查缺失文件时出错: {e}")

        try:
            self._check_naming_convention(files, result.episode_number, result)
        except Exception as e:
            result.warnings.append(f"检查命名规范时出错: {e}")

        try:
            self._check_sensitive_words(files, result)
        except Exception as e:
            result.warnings.append(f"检查敏感词时出错: {e}")

        try:
            result.is_valid = (
                isinstance(result.missing_files, list) and len(result.missing_files) == 0
                and isinstance(result.naming_issues, list) and len(result.naming_issues) == 0
                and isinstance(result.sensitive_words_found, list) and len(result.sensitive_words_found) == 0
            )
        except Exception:
            result.is_valid = False

        return result

    def _detect_episode_number(self, directory: str) -> Optional[str]:
        try:
            dir_name = os.path.basename(os.path.normpath(directory))
        except (OSError, ValueError, TypeError):
            dir_name = ""
        episode_num = extract_episode_number(dir_name, self.episode_pattern)
        if episode_num:
            return episode_num

        all_files: List[str] = []
        try:
            for root, dirs, files in os.walk(directory):
                try:
                    all_files.extend(files)
                except (OSError, ValueError, TypeError):
                    continue
        except (OSError, PermissionError, ValueError, TypeError):
            pass

        for filename in sorted(all_files):
            episode_num = extract_episode_number(filename, self.episode_pattern)
            if episode_num:
                return episode_num

        return None

    def _categorize_files(self, directory: str) -> Dict[str, str]:
        files = {}

        audio_files = list_files_by_extension(directory, self.audio_extensions)
        if audio_files:
            files["audio"] = sorted(audio_files)[0]

        cover_files = list_files_by_extension(directory, self.cover_extensions)
        if cover_files:
            files["cover"] = sorted(cover_files)[0]

        guest_files = list_files_by_extension(directory, self.guest_extensions)
        for gf in guest_files:
            basename = os.path.basename(gf).lower()
            if "guest" in basename or "嘉宾" in basename:
                files["guest"] = gf
                break
        if "guest" not in files and len(guest_files) >= 1:
            files["guest"] = sorted(guest_files)[0]

        summary_files = list_files_by_extension(directory, self.summary_extensions)
        for sf in summary_files:
            basename = os.path.basename(sf).lower()
            if "summary" in basename or "摘要" in basename or "简介" in basename:
                files["summary"] = sf
                break
        if "summary" not in files and len(summary_files) >= 1:
            for sf in sorted(summary_files):
                if sf != files.get("guest"):
                    files["summary"] = sf
                    break

        return files

    def _check_missing_files(
        self, files: Dict[str, str], result: ValidationResult
    ):
        for required in self.required_files:
            if required not in files:
                result.missing_files.append(required)

    def _check_naming_convention(
        self, files: Dict[str, str], episode_num: Optional[str], result: ValidationResult
    ):
        if not episode_num:
            result.naming_issues.append("未检测到期号")
            return

        file_type_names = {
            "audio": "音频文件",
            "cover": "封面文件",
            "guest": "嘉宾资料",
            "summary": "摘要文件",
        }

        for file_type, filepath in files.items():
            filename = os.path.basename(filepath)
            file_episode = extract_episode_number(filename, self.episode_pattern)
            if not file_episode:
                result.naming_issues.append(
                    f"{file_type_names.get(file_type, file_type)}文件名中不包含期号: {filename}"
                )
            elif file_episode != episode_num:
                result.naming_issues.append(
                    f"{file_type_names.get(file_type, file_type)}期号不一致: 期望 {episode_num}, 实际 {file_episode}"
                )

    def _check_sensitive_words(
        self, files: Dict[str, str], result: ValidationResult
    ):
        text_files = ["guest", "summary"]

        for file_type in text_files:
            if file_type in files:
                filepath = files[file_type]
                try:
                    content = read_text_file(filepath)
                    filename = os.path.basename(filepath)

                    for word in self.sensitive_words:
                        if word in content:
                            context = self._get_word_context(content, word)
                            result.sensitive_words_found.append(
                                (filename, word, context)
                            )
                except Exception as e:
                    result.warnings.append(f"读取文件失败 {filepath}: {str(e)}")

    def _get_word_context(self, content: str, word: str, context_len: int = 20) -> str:
        idx = content.find(word)
        if idx == -1:
            return word

        start = max(0, idx - context_len)
        end = min(len(content), idx + len(word) + context_len)
        context = content[start:end].replace("\n", " ").strip()

        if start > 0:
            context = "..." + context
        if end < len(content):
            context = context + "..."

        return context
