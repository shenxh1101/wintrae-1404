
import os
from dataclasses import dataclass, field
from typing import Dict, Optional, Tuple

from .config import Config
from .validator import MaterialValidator, ValidationResult
from .audio_analyzer import AudioAnalyzer, AudioInfo
from .cover_checker import CoverChecker, CoverInfo
from .content_generator import ContentGenerator, GeneratedContent
from .release_manager import ReleaseManager, ReleasePackage
from .state_manager import StateManager
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
    def __init__(self, config: Config = None, state_manager: StateManager = None):
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

        if state_manager is not None:
            self.state_manager = state_manager
        else:
            try:
                self.state_manager = StateManager(self.config)
            except Exception:
                self.state_manager = StateManager()

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

        try:
            if self.state_manager is not None:
                ep_num = result.episode_number if result.episode_number and result.episode_number != "未知" else ""
                directory = result.directory if result.directory else ""
                if ep_num or directory:
                    self.state_manager.update_from_process_result(ep_num, directory, result)
                    try:
                        self.state_manager.save()
                    except Exception:
                        pass
        except Exception:
            pass

        return result

    def confirm_and_release(
        self, result: EpisodeProcessResult, title: Optional[str] = None,
        conflict_policy: str = "preserve",
        release_mode: str = "release",
        reviewer: str = "",
        review_notes: str = "",
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

            try:
                mode = str(release_mode or "release").lower()
                if mode not in ("draft", "pending_review", "release"):
                    mode = "release"
                result.release_package.release_mode = mode
                result.release_package.is_draft = (mode == "draft")
                if mode == "draft":
                    try:
                        result.release_package.checklist = []
                        try:
                            from .release_manager import RenamePlan
                            for rp in result.release_package.rename_plans:
                                try:
                                    if isinstance(rp, RenamePlan):
                                        rp.executed = False
                                        rp.success = False
                                except Exception:
                                    continue
                        except Exception:
                            pass
                    except Exception:
                        pass
            except Exception:
                pass

            if title and isinstance(title, str) and title.strip():
                try:
                    result.release_package.title = title
                    if self.state_manager is not None:
                        ep = result.episode_number if result.episode_number and result.episode_number != "未知" else ""
                        if ep:
                            self.state_manager.set_title(ep, title, result.directory, user_edited=True)
                except Exception:
                    pass

            try:
                do_renames = True
                try:
                    if result.release_package.release_mode == "draft":
                        do_renames = False
                except Exception:
                    pass
                if do_renames:
                    self.release_manager.execute_renames(result.release_package)
            except Exception as e:
                errors.append(f"重命名执行失败: {e}")

            user_edited_files: list = []
            try:
                if self.state_manager is not None and result.episode_number and result.episode_number != "未知":
                    user_edited_files = list(self.state_manager.scan_user_edited_files(
                        result.episode_number, result.directory
                    ))
            except Exception:
                user_edited_files = []

            if result.generated_content is not None:
                try:
                    self.release_manager.generate_release_documents(
                        result.release_package, result.generated_content,
                        conflict_policy=conflict_policy,
                        user_edited_filenames=user_edited_files,
                    )
                except Exception as e:
                    errors.append(f"发布文档生成失败: {e}")

            try:
                if self.state_manager is not None:
                    ep = result.episode_number if result.episode_number and result.episode_number != "未知" else ""
                    directory = result.directory if result.directory else ""
                    if ep or directory:
                        try:
                            mode = str(getattr(result.release_package, "release_mode", "release") or "release")
                        except Exception:
                            mode = "release"
                        self.state_manager.update_from_process_result(ep, directory, result)
                        if mode == "draft":
                            self.state_manager.mark_draft(ep, directory)
                        elif mode == "pending_review":
                            self.state_manager.mark_pending_review(ep, directory)
                        elif mode == "release":
                            self.state_manager.mark_released(ep, directory)

                        try:
                            if reviewer and isinstance(reviewer, str) and reviewer.strip():
                                try:
                                    from .state_manager import ReviewRecord
                                    title_candidates: list = []
                                    sw_actions: list = []
                                    conf_summary: list = []
                                    clist: list = []
                                    has_user_ack = False
                                    try:
                                        gc = getattr(result, "generated_content", None)
                                        if gc is not None:
                                            tc = getattr(gc, "title_candidates", None)
                                            if isinstance(tc, list):
                                                title_candidates = [str(x) for x in tc if isinstance(x, str)]
                                    except Exception:
                                        pass
                                    try:
                                        vr = getattr(result, "validation", None)
                                        if vr is not None:
                                            sw = getattr(vr, "sensitive_words_found", None)
                                            if isinstance(sw, list):
                                                for item in sw:
                                                    try:
                                                        if isinstance(item, (list, tuple)) and len(item) >= 3:
                                                            sw_actions.append({
                                                                "type": str(item[0]),
                                                                "word": str(item[1]),
                                                                "context": str(item[2])[:120],
                                                                "action": "kept",
                                                            })
                                                    except Exception:
                                                        continue
                                    except Exception:
                                        pass
                                    try:
                                        conflicts = getattr(result.release_package, "conflicts", None)
                                        if isinstance(conflicts, list):
                                            conf_summary = [dict(c) for c in conflicts if isinstance(c, dict)]
                                    except Exception:
                                        pass
                                    try:
                                        cl = getattr(result.release_package, "checklist", None)
                                        if isinstance(cl, list):
                                            clist = [list(x) if isinstance(x, (list, tuple)) else [] for x in cl]
                                    except Exception:
                                        pass
                                    try:
                                        has_user_ack = bool(self.state_manager.has_user_edited_files(ep, directory))
                                    except Exception:
                                        has_user_ack = False
                                    final_title = str(getattr(result.release_package, "title", "") or "")
                                    rec = ReviewRecord(
                                        episode_number=str(ep),
                                        directory=str(directory),
                                        reviewer=str(reviewer),
                                        approved=True,
                                        final_title=final_title,
                                        title_candidates=title_candidates,
                                        sensitive_word_actions=sw_actions,
                                        conflict_policy=str(conflict_policy),
                                        conflict_summary=conf_summary,
                                        checklist_result=clist,
                                        notes=str(review_notes) if review_notes else "",
                                        custom_user_edits_acknowledged=has_user_ack,
                                    )
                                    if mode == "release":
                                        rec.approved = True
                                    elif mode == "pending_review":
                                        rec.approved = False
                                    self.state_manager.add_review_record(rec)
                                except Exception:
                                    pass
                        except Exception:
                            pass
                        try:
                            self.state_manager.save()
                        except Exception:
                            pass
            except Exception:
                pass

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
            success = bool(self.release_manager.archive_episode(result.release_package))
            if success and self.state_manager is not None:
                try:
                    ep = result.episode_number if result.episode_number and result.episode_number != "未知" else ""
                    directory = result.directory if result.directory else ""
                    if ep or directory:
                        self.state_manager.mark_archived(ep, directory)
                        self.state_manager.save()
                except Exception:
                    pass
            return success
        except Exception:
            return False

    def render_release_review(self, result: EpisodeProcessResult, conflict_policy: str = "preserve") -> str:
        lines: list = []
        try:
            lines.append("")
            lines.append("=" * 60)
            lines.append(" 发布前复核")
            lines.append("=" * 60)
            try:
                ep = str(result.episode_number or "未知")
                title = ""
                try:
                    if result.release_package is not None:
                        title = str(getattr(result.release_package, "title", "") or "")
                except Exception:
                    title = ""
                lines.append(f" 期号: {ep}")
                lines.append(f" 标题: {title if title else '(未命名)'}")
                try:
                    if result.generated_content is not None:
                        tc = getattr(result.generated_content, "title_candidates", None)
                        if isinstance(tc, list) and tc:
                            lines.append(f" 备选标题 ({len(tc)}):")
                            for i, t in enumerate(tc, 1):
                                try:
                                    lines.append(f"   {i}. {str(t)}")
                                except Exception:
                                    continue
                except Exception:
                    pass
            except Exception:
                pass
            lines.append("")

            try:
                if result.validation is not None:
                    vr = result.validation
                    mf = getattr(vr, "missing_files", None)
                    if isinstance(mf, list) and mf:
                        from .validator import FILE_TYPE_LABELS
                        labels = [FILE_TYPE_LABELS.get(str(m), str(m)) for m in mf if m]
                        lines.append(f" ⚠ 缺失文件: {', '.join(labels)}")
                    ni = getattr(vr, "naming_issues", None)
                    if isinstance(ni, list) and ni:
                        lines.append(f" ⚠ 命名问题 ({len(ni)}):")
                        for n in ni:
                            lines.append(f"    - {str(n)}")
                    sw = getattr(vr, "sensitive_words_found", None)
                    if isinstance(sw, list) and sw:
                        lines.append(f" ⚠ 敏感词 ({len(sw)} 处):")
                        for item in sw:
                            try:
                                if isinstance(item, (list, tuple)) and len(item) >= 3:
                                    lines.append(f"    - [{str(item[0])}] '{str(item[1])}': {str(item[2])[:60]}")
                            except Exception:
                                continue
                    w = getattr(vr, "warnings", None)
                    if isinstance(w, list) and w:
                        lines.append(f" ⚠ 校验警告 ({len(w)}):")
                        for x in w:
                            lines.append(f"    ! {str(x)}")
                    valid = getattr(vr, "is_valid", False)
                    lines.append(f" 校验结果: {'通过' if valid else '未通过'}")
            except Exception:
                pass
            lines.append("")

            try:
                if result.audio_info is not None:
                    ai = result.audio_info
                    from .utils import format_duration
                    dur = getattr(ai, "duration_seconds", None)
                    fmt = getattr(ai, "format", "")
                    sr = getattr(ai, "sample_rate", None)
                    ch = getattr(ai, "channels", None)
                    bits = getattr(ai, "bit_depth", None)
                    parts = []
                    if dur is not None:
                        parts.append(f"时长 {format_duration(dur)}")
                    if fmt:
                        parts.append(f"格式 {fmt}")
                    if sr:
                        parts.append(f"采样率 {sr}Hz")
                    if ch:
                        parts.append(f"声道 {ch}")
                    if bits:
                        parts.append(f"位深 {bits}bit")
                    lines.append(f" 音频: {' / '.join(parts) if parts else '未检测到'}")
            except Exception:
                pass

            try:
                if result.cover_info is not None:
                    ci = result.cover_info
                    w = getattr(ci, "width", None)
                    h = getattr(ci, "height", None)
                    fmt = getattr(ci, "format", "")
                    parts = []
                    if w is not None and h is not None:
                        parts.append(f"{int(w)}x{int(h)}")
                    if fmt:
                        parts.append(f"格式 {fmt}")
                    sq = getattr(ci, "is_square", None)
                    if sq is not None:
                        parts.append(f"正方形 {'是' if sq else '否'}")
                    lines.append(f" 封面: {' / '.join(parts) if parts else '未检测到'}")
            except Exception:
                pass
            lines.append("")

            try:
                if result.release_package is not None and hasattr(result.release_package, "checklist"):
                    cl = result.release_package.checklist
                    if isinstance(cl, list) and cl:
                        lines.append(f" 待办/检查清单:")
                        ok = 0
                        for item in cl:
                            try:
                                if isinstance(item, (list, tuple)) and len(item) >= 2:
                                    checked = bool(item[1])
                                    if checked:
                                        ok += 1
                                    mark = "[x]" if checked else "[ ]"
                                    lines.append(f"    {mark} {str(item[0])}")
                            except Exception:
                                continue
                        lines.append(f" 完成度: {ok}/{len(cl)}")
            except Exception:
                pass

            try:
                if self.state_manager is not None and result.episode_number and result.episode_number != "未知":
                    conflicts = self.state_manager.detect_conflicts(result.episode_number, result.directory)
                    if conflicts:
                        policy_label = {"preserve": "保留（不覆盖）", "overwrite": "强制覆盖", "keep_both": "另存新旧版本"}.get(conflict_policy, conflict_policy)
                        lines.append("")
                        lines.append(f" 文案变更（冲突处理策略: {policy_label}）:")
                        for c in conflicts:
                            try:
                                fn = str(c.get("filename", "?"))
                                action = str(c.get("reason", "检测到用户手改"))
                                backup = c.get("backup_file")
                                suffix = f"（备份: {os.path.basename(str(backup))}）" if backup else ""
                                lines.append(f"    ! {fn}: {action}{suffix}")
                            except Exception:
                                continue
            except Exception:
                pass

            try:
                if isinstance(result.errors, list) and result.errors:
                    lines.append("")
                    lines.append(f" 错误 ({len(result.errors)}):")
                    for e in result.errors:
                        lines.append(f"    X {str(e)}")
            except Exception:
                pass

            lines.append("")
            lines.append(" 请确认后再执行真正写入 output。")
            lines.append("=" * 60)
            lines.append("")
        except Exception:
            try:
                lines.append(" 复核视图渲染失败")
            except Exception:
                pass
        return "\n".join(lines)

    def preview_release(self, directory: str, conflict_policy: str = "preserve") -> Tuple[Optional[EpisodeProcessResult], str, list]:
        errors: list = []
        try:
            result = self.process_episode(directory)
            if result is None:
                errors.append("处理结果为空")
                return None, "预览失败: 处理结果为空\n", errors
            review = self.render_release_review(result, conflict_policy=conflict_policy)
            return result, review, errors
        except Exception as e:
            try:
                errors.append(f"预览失败: {e}")
            except Exception:
                pass
            return None, f"预览失败: {e}\n", errors

    def render_review_records(self, episode_number: str = "", directory: str = "",
                              limit: int = 10) -> str:
        lines: list = []
        try:
            if self.state_manager is None:
                return "  状态管理器未初始化\n"
            try:
                from datetime import datetime
                records = self.state_manager.get_review_records(
                    episode_number=episode_number, directory=directory, limit=limit
                )
                lines.append("")
                lines.append(" 复核记录")
                lines.append("=" * 60)
                if not records:
                    lines.append("  (暂无记录)")
                    lines.append("")
                    return "\n".join(lines)
                for idx, rec in enumerate(records, 1):
                    try:
                        lines.append(f" {idx}. ID: {str(rec.id)[:8]}...")
                        lines.append(f"    复核时间: {str(rec.created_at)}")
                        lines.append(f"    复核人: {str(rec.reviewer) if rec.reviewer else '(未填写)'}")
                        lines.append(f"    结果: {'通过' if rec.approved else '待确认'}")
                        if rec.final_title:
                            lines.append(f"    最终标题: {str(rec.final_title)}")
                        if rec.conflict_policy:
                            lines.append(f"    冲突策略: {str(rec.conflict_policy)}")
                        try:
                            if isinstance(rec.sensitive_word_actions, list) and rec.sensitive_word_actions:
                                lines.append(f"    敏感词处理 ({len(rec.sensitive_word_actions)} 处):")
                                for sw in rec.sensitive_word_actions[:5]:
                                    try:
                                        lines.append(f"      - [{sw.get('type', '')}] '{sw.get('word', '')}': {str(sw.get('context', ''))[:60]}")
                                    except Exception:
                                        continue
                        except Exception:
                            pass
                        try:
                            if isinstance(rec.conflict_summary, list) and rec.conflict_summary:
                                lines.append(f"    文案冲突 ({len(rec.conflict_summary)} 项):")
                                for c in rec.conflict_summary[:5]:
                                    try:
                                        bn = str(c.get("filename", "?"))
                                        act = str(c.get("action", "?"))
                                        reason = str(c.get("reason", ""))
                                        lines.append(f"      - {bn}: {act} {reason[:40]}")
                                    except Exception:
                                        continue
                        except Exception:
                            pass
                        if rec.notes:
                            lines.append(f"    备注: {str(rec.notes)}")
                        if rec.custom_user_edits_acknowledged:
                            lines.append(f"    已确认用户手改: 是")
                        lines.append("")
                    except Exception:
                        continue
                lines.append("=" * 60)
                lines.append("")
                return "\n".join(lines)
            except Exception:
                return "  复核记录渲染失败\n"
        except Exception:
            return "  复核记录渲染失败\n"
        return "\n".join(lines)
