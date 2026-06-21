
import os
from typing import List, Optional, Dict, Any
from pathlib import Path

from .config import Config
from .validator import MaterialValidator, ValidationResult
from .audio_analyzer import AudioAnalyzer
from .cover_checker import CoverChecker
from .state_manager import (
    StateManager,
    EpisodeState,
    EPISODE_STATUS_PENDING,
    EPISODE_STATUS_READY,
    EPISODE_STATUS_RELEASED,
    EPISODE_STATUS_ARCHIVED,
    EPISODE_STATUS_ERROR,
)
from .utils import format_duration, ensure_directory, is_path_safe


FILTER_ALL = "all"
FILTER_READY = "ready"
FILTER_PENDING = "pending"
FILTER_HAS_ISSUES = "issues"
FILTER_RELEASED = "released"
FILTER_NOT_RELEASED = "not_released"
FILTER_ARCHIVED = "archived"
FILTER_ERROR = "error"

VALID_FILTERS = {
    FILTER_ALL,
    FILTER_READY,
    FILTER_PENDING,
    FILTER_HAS_ISSUES,
    FILTER_RELEASED,
    FILTER_NOT_RELEASED,
    FILTER_ARCHIVED,
    FILTER_ERROR,
}

FILE_TYPE_LABELS = {
    "audio": "音频",
    "cover": "封面",
    "guest": "嘉宾资料",
    "summary": "摘要",
}

STATUS_LABELS = {
    EPISODE_STATUS_PENDING: "待处理",
    EPISODE_STATUS_READY: "就绪",
    EPISODE_STATUS_RELEASED: "已发布",
    EPISODE_STATUS_ARCHIVED: "已归档",
    EPISODE_STATUS_ERROR: "错误",
}


class EpisodeDashboardRow:
    def __init__(self):
        self.episode_number: str = ""
        self.directory: str = ""
        self.status: str = EPISODE_STATUS_PENDING
        self.status_label: str = STATUS_LABELS.get(EPISODE_STATUS_PENDING, "待处理")

        self.is_valid: bool = False
        self.is_released: bool = False
        self.is_archived: bool = False
        self.has_user_edits: bool = False

        self.missing_files: List[str] = []
        self.naming_issues: List[str] = []
        self.sensitive_words_found: List = []

        self.audio_duration_formatted: str = "-"
        self.audio_format: str = ""
        self.cover_size: str = "-"
        self.cover_format: str = ""

        self.title: str = ""
        self.output_dir: str = ""
        self.generated_files_count: int = 0

        self.warnings: List[str] = []
        self.errors: List[str] = []

    def to_dict(self) -> Dict[str, Any]:
        try:
            return {
                "episode_number": str(self.episode_number),
                "directory": str(self.directory),
                "status": str(self.status),
                "status_label": str(self.status_label),
                "is_valid": bool(self.is_valid),
                "is_released": bool(self.is_released),
                "is_archived": bool(self.is_archived),
                "has_user_edits": bool(self.has_user_edits),
                "missing_files": list(self.missing_files),
                "naming_issues": list(self.naming_issues),
                "sensitive_words_found": list(self.sensitive_words_found),
                "audio_duration_formatted": str(self.audio_duration_formatted),
                "audio_format": str(self.audio_format),
                "cover_size": str(self.cover_size),
                "cover_format": str(self.cover_format),
                "title": str(self.title),
                "output_dir": str(self.output_dir),
                "generated_files_count": int(self.generated_files_count),
                "warnings": list(self.warnings),
                "errors": list(self.errors),
            }
        except Exception:
            return {"episode_number": "", "status": "error"}

    @property
    def has_issues(self) -> bool:
        try:
            if self.missing_files:
                return True
            if self.naming_issues:
                return True
            if self.sensitive_words_found:
                return True
            if self.errors:
                return True
            return not self.is_valid
        except Exception:
            return True


class EpisodeDashboard:
    def __init__(self, config: Config = None, state_manager: StateManager = None):
        try:
            self.config = config or Config()
        except Exception:
            from .config import Config
            self.config = Config()

        try:
            self.input_dir = str(self.config.input_dir)
        except Exception:
            self.input_dir = "./input"

        try:
            self.state_manager = state_manager or StateManager(self.config)
        except Exception:
            self.state_manager = StateManager(self.config)

        try:
            self.validator = MaterialValidator(self.config)
        except Exception:
            self.validator = MaterialValidator()

        try:
            self.audio_analyzer = AudioAnalyzer(self.config)
        except Exception:
            self.audio_analyzer = AudioAnalyzer()

        try:
            self.cover_checker = CoverChecker(self.config)
        except Exception:
            self.cover_checker = CoverChecker()

    def _find_episode_directories(self) -> List[str]:
        dirs: List[str] = []
        try:
            if not self.input_dir or not os.path.exists(self.input_dir):
                return dirs
            try:
                items = os.listdir(self.input_dir)
            except (OSError, PermissionError):
                return dirs

            has_subdir = False
            for item in items:
                try:
                    item_path = os.path.join(self.input_dir, item)
                    if os.path.isdir(item_path) and is_path_safe(self.input_dir, item_path):
                        dirs.append(item_path)
                        has_subdir = True
                except Exception:
                    continue

            if not has_subdir:
                try:
                    dirs.append(self.input_dir)
                except Exception:
                    pass
        except Exception:
            pass
        return dirs

    def _build_row_from_state(self, state: EpisodeState) -> EpisodeDashboardRow:
        row = EpisodeDashboardRow()
        try:
            row.episode_number = str(state.episode_number) if state.episode_number else ""
            row.directory = str(state.directory) if state.directory else ""
            row.status = str(state.status)
            row.status_label = STATUS_LABELS.get(state.status, str(state.status))
            row.is_valid = bool(state.is_valid)
            row.is_released = bool(state.is_released)
            row.is_archived = bool(state.is_archived)
            row.has_user_edits = bool(state.custom_user_edits)

            try:
                if isinstance(state.missing_files, list):
                    row.missing_files = [str(x) for x in state.missing_files if isinstance(x, str)]
            except Exception:
                pass
            try:
                if isinstance(state.naming_issues, list):
                    row.naming_issues = [str(x) for x in state.naming_issues if isinstance(x, str)]
            except Exception:
                pass
            try:
                if isinstance(state.sensitive_words_found, list):
                    row.sensitive_words_found = list(state.sensitive_words_found)
            except Exception:
                pass

            try:
                dur = state.audio_duration_seconds
                if dur is not None and isinstance(dur, (int, float)) and dur >= 0:
                    row.audio_duration_formatted = format_duration(dur)
                row.audio_format = str(state.audio_format) if state.audio_format else ""
            except Exception:
                pass

            try:
                cw = state.cover_width
                ch = state.cover_height
                if cw is not None and ch is not None and isinstance(cw, (int, float)) and isinstance(ch, (int, float)) and cw >= 0 and ch >= 0:
                    row.cover_size = f"{int(cw)}x{int(ch)}"
                row.cover_format = str(state.cover_format) if state.cover_format else ""
            except Exception:
                pass

            row.title = str(state.title) if state.title else ""
            row.output_dir = str(state.output_dir) if state.output_dir else ""
            try:
                if isinstance(state.generated_files, list):
                    row.generated_files_count = len(state.generated_files)
            except Exception:
                row.generated_files_count = 0

            try:
                if isinstance(state.warnings, list):
                    row.warnings = [str(x) for x in state.warnings if isinstance(x, str)]
            except Exception:
                pass
            try:
                if isinstance(state.errors, list):
                    row.errors = [str(x) for x in state.errors if isinstance(x, str)]
            except Exception:
                pass
        except Exception:
            pass
        return row

    def _scan_directory(self, directory: str, rescan: bool = False) -> EpisodeDashboardRow:
        row = EpisodeDashboardRow()
        try:
            row.directory = str(directory) if directory else ""
        except Exception:
            pass

        try:
            vr: Optional[ValidationResult] = None
            try:
                if self.validator is not None:
                    vr = self.validator.validate_directory(directory)
            except Exception:
                vr = None

            if vr is None:
                row.status = EPISODE_STATUS_ERROR
                row.status_label = STATUS_LABELS.get(EPISODE_STATUS_ERROR, "错误")
                row.errors.append("校验失败")
                return row

            try:
                row.episode_number = str(vr.episode_number) if vr.episode_number else "未知"
            except Exception:
                row.episode_number = "未知"

            try:
                row.is_valid = bool(vr.is_valid)
            except Exception:
                row.is_valid = False

            try:
                if isinstance(vr.missing_files, list):
                    row.missing_files = [str(x) for x in vr.missing_files if isinstance(x, str)]
            except Exception:
                pass
            try:
                if isinstance(vr.naming_issues, list):
                    row.naming_issues = [str(x) for x in vr.naming_issues if isinstance(x, str)]
            except Exception:
                pass
            try:
                if isinstance(vr.sensitive_words_found, list):
                    row.sensitive_words_found = list(vr.sensitive_words_found)
            except Exception:
                pass
            try:
                if isinstance(vr.warnings, list):
                    row.warnings = [str(x) for x in vr.warnings if isinstance(x, str)]
            except Exception:
                pass

            try:
                files = getattr(vr, "files", {}) if vr else {}
            except Exception:
                files = {}

            if isinstance(files, dict) and "audio" in files and self.audio_analyzer is not None:
                try:
                    audio_path = files.get("audio", "")
                    if audio_path and os.path.exists(audio_path):
                        ai = self.audio_analyzer.analyze(audio_path)
                        if ai is not None:
                            dur = getattr(ai, "duration_seconds", None)
                            if dur is not None and isinstance(dur, (int, float)) and dur >= 0:
                                row.audio_duration_formatted = format_duration(dur)
                            fmt = getattr(ai, "format", "")
                            row.audio_format = str(fmt) if fmt else ""
                except Exception:
                    pass

            if isinstance(files, dict) and "cover" in files and self.cover_checker is not None:
                try:
                    cover_path = files.get("cover", "")
                    if cover_path and os.path.exists(cover_path):
                        ci = self.cover_checker.check(cover_path)
                        if ci is not None:
                            cw = getattr(ci, "width", None)
                            ch = getattr(ci, "height", None)
                            if cw is not None and ch is not None and isinstance(cw, (int, float)) and isinstance(ch, (int, float)) and cw >= 0 and ch >= 0:
                                row.cover_size = f"{int(cw)}x{int(ch)}"
                            fmt = getattr(ci, "format", "")
                            row.cover_format = str(fmt) if fmt else ""
                except Exception:
                    pass

            state = None
            try:
                if row.episode_number and row.episode_number != "未知":
                    state = self.state_manager.get(row.episode_number, directory)
            except Exception:
                state = None

            if state is not None:
                try:
                    row.is_released = bool(state.is_released)
                    row.is_archived = bool(state.is_archived)
                    row.has_user_edits = bool(state.custom_user_edits)
                    row.title = str(state.title) if state.title else row.title
                    row.output_dir = str(state.output_dir) if state.output_dir else ""
                    if isinstance(state.generated_files, list):
                        row.generated_files_count = len(state.generated_files)
                    if isinstance(state.errors, list) and state.errors:
                        for e in state.errors:
                            if isinstance(e, str) and e not in row.errors:
                                row.errors.append(e)
                except Exception:
                    pass

            try:
                if row.is_archived:
                    row.status = EPISODE_STATUS_ARCHIVED
                elif row.is_released:
                    row.status = EPISODE_STATUS_RELEASED
                elif row.errors:
                    row.status = EPISODE_STATUS_ERROR
                elif row.is_valid and not row.has_issues:
                    row.status = EPISODE_STATUS_READY
                else:
                    row.status = EPISODE_STATUS_PENDING
                row.status_label = STATUS_LABELS.get(row.status, row.status)
            except Exception:
                row.status = EPISODE_STATUS_PENDING
                row.status_label = STATUS_LABELS.get(EPISODE_STATUS_PENDING, "待处理")

        except Exception as e:
            try:
                row.status = EPISODE_STATUS_ERROR
                row.status_label = STATUS_LABELS.get(EPISODE_STATUS_ERROR, "错误")
                row.errors.append(f"扫描异常: {e}")
            except Exception:
                pass

        return row

    def _matches_filter(self, row: EpisodeDashboardRow, filter_name: str) -> bool:
        try:
            f = str(filter_name).lower() if filter_name else FILTER_ALL
            if f == FILTER_ALL:
                return True
            if f == FILTER_READY:
                return row.status == EPISODE_STATUS_READY
            if f == FILTER_PENDING:
                return row.status == EPISODE_STATUS_PENDING
            if f == FILTER_HAS_ISSUES:
                return row.has_issues
            if f == FILTER_RELEASED:
                return row.is_released
            if f == FILTER_NOT_RELEASED:
                return not row.is_released
            if f == FILTER_ARCHIVED:
                return row.is_archived
            if f == FILTER_ERROR:
                return row.status == EPISODE_STATUS_ERROR
            return True
        except Exception:
            return True

    def scan(
        self,
        filter_name: str = FILTER_ALL,
        rescan: bool = False,
        save_state: bool = True,
    ) -> List[EpisodeDashboardRow]:
        rows: List[EpisodeDashboardRow] = []
        try:
            episode_dirs = self._find_episode_directories()
        except Exception:
            episode_dirs = []

        for d in episode_dirs:
            try:
                row = self._scan_directory(d, rescan=rescan)
                if self._matches_filter(row, filter_name):
                    rows.append(row)

                if save_state and row.episode_number and row.episode_number != "未知":
                    try:
                        state = self.state_manager.get_or_create(row.episode_number, d)
                        try:
                            state.directory = str(d) if d else state.directory
                        except Exception:
                            pass
                        try:
                            state.missing_files = list(row.missing_files)
                        except Exception:
                            pass
                        try:
                            state.naming_issues = list(row.naming_issues)
                        except Exception:
                            pass
                        try:
                            state.is_valid = bool(row.is_valid)
                        except Exception:
                            pass
                        try:
                            state.status = str(row.status)
                        except Exception:
                            pass
                        try:
                            state.touch()
                        except Exception:
                            pass
                    except Exception:
                        pass
            except Exception:
                continue

        try:
            if save_state:
                self.state_manager.save()
        except Exception:
            pass

        try:
            rows.sort(key=lambda r: (r.episode_number or "", r.directory or ""))
        except Exception:
            pass

        return rows

    def render_table(self, rows: List[EpisodeDashboardRow]) -> str:
        try:
            lines: List[str] = []
            lines.append("")
            lines.append("期数看板")
            lines.append("")

            if not rows:
                lines.append("  暂无符合条件的期数")
                lines.append("")
                return "\n".join(lines)

            header = f"  {'期号':<8s} {'状态':<8s} {'标题':<24s} {'音频时长':<10s} {'封面尺寸':<12s} {'缺失文件':<16s} {'已发布':<6s}"
            lines.append(header)
            lines.append("  " + "-" * (8 + 8 + 24 + 10 + 12 + 16 + 6 + 6))

            for row in rows:
                try:
                    ep = str(row.episode_number or "?")[:8]
                    st = str(row.status_label or "?")[:8]
                    tl = str(row.title or "-")[:24]
                    ad = str(row.audio_duration_formatted or "-")[:10]
                    cs = str(row.cover_size or "-")[:12]

                    missing = "-"
                    if row.missing_files:
                        labels = [FILE_TYPE_LABELS.get(m, str(m)) for m in row.missing_files if m]
                        missing = ",".join(labels)[:16] if labels else "?"

                    rel = "是" if row.is_released else "否"
                    if row.is_archived:
                        rel = "归档"

                    lines.append(f"  {ep:<8s} {st:<8s} {tl:<24s} {ad:<10s} {cs:<12s} {missing:<16s} {rel:<6s}")
                except Exception:
                    continue

            lines.append("")
            lines.append(f"  共 {len(rows)} 期")
            lines.append("")

            try:
                ready = sum(1 for r in rows if r.status == EPISODE_STATUS_READY)
                pending = sum(1 for r in rows if r.status == EPISODE_STATUS_PENDING)
                released = sum(1 for r in rows if r.is_released)
                archived = sum(1 for r in rows if r.is_archived)
                errors = sum(1 for r in rows if r.status == EPISODE_STATUS_ERROR)
                issues = sum(1 for r in rows if r.has_issues)
                lines.append(f"  就绪: {ready}  待处理: {pending}  有问题: {issues}  已发布: {released}  已归档: {archived}  错误: {errors}")
                lines.append("")
            except Exception:
                pass

            return "\n".join(lines)
        except Exception:
            return "\n期数看板渲染失败\n"

    def render_details(self, row: EpisodeDashboardRow) -> str:
        try:
            lines: List[str] = []
            lines.append("")
            ep = str(row.episode_number or "未知")
            title = str(row.title or "(未命名)")
            lines.append(f"期数 {ep} - {title}")
            lines.append("-" * 40)
            lines.append(f"  目录: {str(row.directory or '')}")
            lines.append(f"  状态: {str(row.status_label or row.status or '')}")
            lines.append(f"  校验通过: {'是' if row.is_valid else '否'}")
            lines.append(f"  已发布: {'是' if row.is_released else '否'}")
            lines.append(f"  已归档: {'是' if row.is_archived else '否'}")
            if row.has_user_edits:
                lines.append(f"  有用户手动编辑")
            if row.output_dir:
                lines.append(f"  输出目录: {row.output_dir}")
            if row.generated_files_count > 0:
                lines.append(f"  已生成文件: {row.generated_files_count} 个")
            lines.append("")

            if row.audio_duration_formatted != "-" or row.audio_format:
                parts = []
                if row.audio_duration_formatted:
                    parts.append(f"时长 {row.audio_duration_formatted}")
                if row.audio_format:
                    parts.append(f"格式 {row.audio_format}")
                lines.append(f"  音频: {' / '.join(parts)}")

            if row.cover_size != "-" or row.cover_format:
                parts = []
                if row.cover_size != "-":
                    parts.append(f"尺寸 {row.cover_size}")
                if row.cover_format:
                    parts.append(f"格式 {row.cover_format}")
                lines.append(f"  封面: {' / '.join(parts)}")

            if row.missing_files:
                lines.append("")
                lines.append("  缺失文件:")
                for m in row.missing_files:
                    label = FILE_TYPE_LABELS.get(str(m), str(m))
                    lines.append(f"    - {label}")

            if row.naming_issues:
                lines.append("")
                lines.append("  命名问题:")
                for n in row.naming_issues:
                    lines.append(f"    - {n}")

            if row.sensitive_words_found:
                lines.append("")
                lines.append("  敏感词:")
                for item in row.sensitive_words_found:
                    try:
                        if isinstance(item, (list, tuple)) and len(item) >= 3:
                            lines.append(f"    - [{str(item[0])}] '{str(item[1])}': {str(item[2])[:50]}")
                    except Exception:
                        continue

            if row.warnings:
                lines.append("")
                lines.append("  警告:")
                for w in row.warnings:
                    lines.append(f"    ! {w}")

            if row.errors:
                lines.append("")
                lines.append("  错误:")
                for e in row.errors:
                    lines.append(f"    X {e}")

            lines.append("")
            return "\n".join(lines)
        except Exception:
            return "\n详情渲染失败\n"
