
import os
import shutil
import filecmp
from pathlib import Path
from dataclasses import dataclass, field
from typing import Dict, List, Tuple, Optional
from datetime import datetime

from .config import Config
from .utils import sanitize_filename, ensure_directory, is_path_safe


@dataclass
class RenamePlan:
    source: str
    target: str
    file_type: str
    executed: bool = False
    success: bool = False
    error: str = ""

    def to_dict(self) -> dict:
        return {
            "source": self.source,
            "target": self.target,
            "file_type": self.file_type,
            "executed": self.executed,
            "success": self.success,
            "error": self.error,
        }


@dataclass
class ReleasePackage:
    episode_number: str
    title: str
    output_dir: str
    archive_dir: str
    files: Dict[str, str] = field(default_factory=dict)
    rename_plans: List[RenamePlan] = field(default_factory=list)
    checklist: List[Tuple[str, bool]] = field(default_factory=list)
    generated_files: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    conflicts: List[Dict] = field(default_factory=list)
    is_ready: bool = False

    def to_dict(self) -> dict:
        return {
            "episode_number": self.episode_number,
            "title": self.title,
            "output_dir": self.output_dir,
            "archive_dir": self.archive_dir,
            "files": self.files,
            "rename_plans": [p.to_dict() for p in self.rename_plans],
            "checklist": [{"item": i, "checked": c} for i, c in self.checklist],
            "generated_files": self.generated_files,
            "warnings": list(self.warnings) if isinstance(self.warnings, list) else [],
            "conflicts": list(self.conflicts) if isinstance(self.conflicts, list) else [],
            "is_ready": self.is_ready,
        }


class ReleaseManager:
    def __init__(self, config: Config = None):
        self.config = config or Config()
        try:
            self.output_dir = str(self.config.output_dir)
        except Exception:
            self.output_dir = "./output"
        try:
            self.archive_dir = str(self.config.archive_dir)
        except Exception:
            self.archive_dir = "./archive"
        try:
            checklist_items = self.config.get("checklist.items", None)
            if isinstance(checklist_items, list) and checklist_items:
                self.checklist_items = [str(i) for i in checklist_items if isinstance(i, str)]
            else:
                self.checklist_items = [
                    "音频文件已校验", "封面图符合规范", "嘉宾资料已确认",
                    "节目简介已审核", "标题候选已生成", "时间轴草稿已生成",
                    "社媒文案已准备", "文件已批量重命名",
                ]
        except Exception:
            self.checklist_items = [
                "音频文件已校验", "封面图符合规范", "嘉宾资料已确认",
                "节目简介已审核", "标题候选已生成", "时间轴草稿已生成",
                "社媒文案已准备", "文件已批量重命名",
            ]

    def create_release_package(
        self,
        episode_number: Optional[str],
        title: Optional[str],
        files: Optional[Dict[str, str]],
        validation_result=None,
        audio_info=None,
        cover_info=None,
        generated_content=None,
    ) -> ReleasePackage:
        safe_episode = sanitize_filename(str(episode_number) if episode_number else "000")
        safe_title = sanitize_filename(str(title) if title else "未命名节目")

        safe_output_base = self.output_dir if self.output_dir else "./output"
        safe_archive_base = self.archive_dir if self.archive_dir else "./archive"

        output_dir = os.path.join(safe_output_base, safe_episode)
        archive_dir = os.path.join(safe_archive_base, safe_episode)

        safe_files: Dict[str, str] = {}
        if isinstance(files, dict):
            for k, v in files.items():
                try:
                    if isinstance(k, str) and isinstance(v, str) and os.path.exists(v):
                        safe_files[str(k)] = str(v)
                except Exception:
                    continue

        package = ReleasePackage(
            episode_number=safe_episode,
            title=safe_title if safe_title else "未命名节目",
            output_dir=output_dir,
            archive_dir=archive_dir,
            files=safe_files,
        )

        try:
            package.rename_plans = self._generate_rename_plans(
                safe_episode, safe_title, safe_files, output_dir
            )
        except Exception:
            package.rename_plans = []

        try:
            package.checklist = self._build_checklist(
                validation_result, audio_info, cover_info, generated_content
            )
        except Exception:
            package.checklist = [(item, False) for item in self.checklist_items]

        try:
            package.is_ready = all(checked for _, checked in package.checklist) if package.checklist else False
        except Exception:
            package.is_ready = False

        return package

    def _generate_rename_plans(
        self,
        episode_number: str,
        title: str,
        files: Dict[str, str],
        output_dir: str,
    ) -> List[RenamePlan]:
        plans: List[RenamePlan] = []
        safe_title = sanitize_filename(title) if title else "未命名节目"
        safe_episode = sanitize_filename(episode_number) if episode_number else "000"

        naming_map = {
            "audio": f"{safe_episode}_{safe_title}",
            "cover": f"{safe_episode}_{safe_title}_cover",
            "guest": f"{safe_episode}_{safe_title}_嘉宾资料",
            "summary": f"{safe_episode}_{safe_title}_节目简介",
        }

        if not isinstance(files, dict):
            return plans

        for file_type, filepath in files.items():
            try:
                if not isinstance(filepath, str) or not os.path.exists(filepath):
                    continue

                ext = Path(filepath).suffix
                base_name = naming_map.get(str(file_type), f"{safe_episode}_{file_type}")
                new_filename = f"{base_name}{ext}"

                if not output_dir:
                    continue
                target_path = os.path.join(output_dir, new_filename)

                plans.append(
                    RenamePlan(
                        source=filepath,
                        target=target_path,
                        file_type=str(file_type),
                    )
                )
            except Exception:
                continue

        return plans

    def _build_checklist(
        self, validation_result, audio_info, cover_info, generated_content
    ) -> List[Tuple[str, bool]]:
        checklist: List[Tuple[str, bool]] = []

        for idx, item_name in enumerate(self.checklist_items):
            try:
                if idx == 0:
                    checked = audio_info is not None and getattr(audio_info, "is_valid", False)
                elif idx == 1:
                    checked = cover_info is not None and getattr(cover_info, "is_valid", False)
                elif idx == 2:
                    checked = False
                    if validation_result is not None:
                        try:
                            vfiles = getattr(validation_result, "files", {})
                            if "guest" in vfiles:
                                sw = getattr(validation_result, "sensitive_words_found", [])
                                guest_file = vfiles.get("guest", "")
                                guest_basename = os.path.basename(guest_file) if guest_file else ""
                                has_sensitive = any(
                                    f == guest_basename for f, w, c in sw
                                )
                                checked = not has_sensitive
                        except Exception:
                            pass
                elif idx == 3:
                    checked = False
                    if validation_result is not None:
                        try:
                            vfiles = getattr(validation_result, "files", {})
                            if "summary" in vfiles:
                                sw = getattr(validation_result, "sensitive_words_found", [])
                                summary_file = vfiles.get("summary", "")
                                summary_basename = os.path.basename(summary_file) if summary_file else ""
                                has_sensitive = any(
                                    f == summary_basename for f, w, c in sw
                                )
                                checked = not has_sensitive
                        except Exception:
                            pass
                elif idx == 4:
                    tc = getattr(generated_content, "title_candidates", None) if generated_content else None
                    checked = isinstance(tc, list) and len(tc) > 0
                elif idx == 5:
                    tl = getattr(generated_content, "timeline", None) if generated_content else None
                    checked = isinstance(tl, list) and len(tl) > 0
                elif idx == 6:
                    sm = getattr(generated_content, "social_media", None) if generated_content else None
                    checked = isinstance(sm, dict) and len(sm) > 0
                elif idx == 7:
                    checked = False
                else:
                    checked = False
                checklist.append((item_name, bool(checked)))
            except Exception:
                checklist.append((item_name, False))

        while len(checklist) < len(self.checklist_items):
            try:
                checklist.append((self.checklist_items[len(checklist)], False))
            except Exception:
                break

        return checklist

    def execute_renames(self, package: ReleasePackage) -> ReleasePackage:
        if not package:
            return package

        try:
            if not ensure_directory(package.output_dir):
                return package
        except Exception:
            return package

        if not isinstance(package.rename_plans, list):
            return package

        for plan in package.rename_plans:
            try:
                if not isinstance(plan, RenamePlan):
                    continue
                if plan.executed:
                    if os.path.exists(plan.target) and os.path.exists(plan.source):
                        try:
                            if filecmp.cmp(plan.source, plan.target, shallow=False):
                                plan.success = True
                        except Exception:
                            pass
                    continue

                if not plan.source or not os.path.exists(plan.source):
                    plan.executed = True
                    plan.success = False
                    plan.error = "源文件不存在"
                    continue

                try:
                    target_dir = os.path.dirname(plan.target)
                    if target_dir and not ensure_directory(target_dir):
                        plan.executed = True
                        plan.success = False
                        plan.error = "无法创建目标目录"
                        continue
                except Exception:
                    plan.executed = True
                    plan.success = False
                    plan.error = "目标目录异常"
                    continue

                try:
                    if os.path.exists(plan.target):
                        try:
                            if filecmp.cmp(plan.source, plan.target, shallow=False):
                                plan.executed = True
                                plan.success = True
                                if plan.target not in package.generated_files:
                                    package.generated_files.append(plan.target)
                                continue
                        except Exception:
                            pass
                        try:
                            os.remove(plan.target)
                        except Exception:
                            pass

                    shutil.copy2(plan.source, plan.target)
                    plan.executed = True
                    plan.success = True
                    if plan.target not in package.generated_files:
                        package.generated_files.append(plan.target)
                except Exception as e:
                    plan.executed = True
                    plan.success = False
                    plan.error = str(e)
            except Exception as e:
                try:
                    plan.executed = True
                    plan.success = False
                    plan.error = str(e)
                except Exception:
                    pass

        try:
            for i, (item, _) in enumerate(package.checklist):
                try:
                    if item == "文件已批量重命名":
                        all_success = all(
                            p.success for p in package.rename_plans
                            if isinstance(p, RenamePlan) and p.executed
                        )
                        any_executed = any(
                            p.executed for p in package.rename_plans
                            if isinstance(p, RenamePlan)
                        )
                        if any_executed:
                            package.checklist[i] = (item, bool(all_success))
                        break
                except Exception:
                    continue
        except Exception:
            pass

        try:
            package.is_ready = all(checked for _, checked in package.checklist) if package.checklist else False
        except Exception:
            package.is_ready = False

        return package

    def generate_release_documents(
        self, package: ReleasePackage, generated_content,
        conflict_policy: str = "preserve",
        user_edited_filenames: Optional[List[str]] = None,
    ) -> ReleasePackage:
        if not package:
            return package

        try:
            if not ensure_directory(package.output_dir):
                return package
        except Exception:
            return package

        safe_ep = sanitize_filename(package.episode_number) if package.episode_number else "000"

        try:
            if not isinstance(package.warnings, list):
                package.warnings = []
            if not isinstance(package.conflicts, list):
                package.conflicts = []
        except Exception:
            try:
                package.warnings = []
                package.conflicts = []
            except Exception:
                pass

        def _existing_version_suffix(base_dir: str, stem: str, ext: str) -> str:
            try:
                now_suffix = datetime.now().strftime("%Y%m%d_%H%M%S")
                candidate = os.path.join(base_dir, f"{stem}_v1{ext}")
                idx = 1
                while os.path.exists(candidate) and idx < 9999:
                    idx += 1
                    candidate = os.path.join(base_dir, f"{stem}_v{idx}{ext}")
                if idx >= 9999:
                    candidate = os.path.join(base_dir, f"{stem}_{now_suffix}{ext}")
                return candidate
            except Exception:
                try:
                    return os.path.join(base_dir, f"{stem}_{datetime.now().strftime('%Y%m%d_%H%M%S')}{ext}")
                except Exception:
                    return os.path.join(base_dir, f"{stem}_backup{ext}")

        def _is_user_edited(filepath: str) -> bool:
            try:
                if not user_edited_filenames:
                    return False
                bn = os.path.basename(filepath)
                if bn in user_edited_filenames:
                    return True
                return False
            except Exception:
                return False

        def safe_write(filepath: str, content: str) -> bool:
            try:
                if not filepath:
                    return False
                fdir = os.path.dirname(filepath)
                if fdir and not ensure_directory(fdir):
                    return False
                safe_content = content if isinstance(content, str) else str(content) if content is not None else ""
                already_exists = os.path.exists(filepath)
                is_conflict = already_exists and _is_user_edited(filepath)
                policy = conflict_policy if conflict_policy in ("preserve", "overwrite", "keep_both") else "preserve"
                written_path = filepath
                if is_conflict:
                    try:
                        bn = os.path.basename(filepath)
                        if policy == "preserve":
                            try:
                                package.conflicts.append({
                                    "filename": bn, "filepath": filepath,
                                    "action": "preserved", "reason": "检测到用户手改，已保留原文件",
                                })
                                package.warnings.append(f"{bn}: 检测到用户手改，已保留原文件不覆盖")
                            except Exception:
                                pass
                            return True
                        elif policy == "keep_both":
                            try:
                                stem, ext = os.path.splitext(bn)
                                backup = _existing_version_suffix(os.path.dirname(filepath), stem, ext)
                                try:
                                    import shutil
                                    shutil.copy2(filepath, backup)
                                except Exception:
                                    with open(filepath, "rb") as rf:
                                        with open(backup, "wb") as wf:
                                            wf.write(rf.read())
                                try:
                                    package.conflicts.append({
                                        "filename": bn, "filepath": filepath,
                                        "backup_file": backup,
                                        "action": "keep_both",
                                        "reason": "检测到用户手改，已将旧版本另存备份后写入新版本",
                                    })
                                    package.warnings.append(f"{bn}: 检测到用户手改，已另存旧版本为 {os.path.basename(backup)}")
                                    if backup not in package.generated_files:
                                        package.generated_files.append(backup)
                                except Exception:
                                    pass
                            except Exception:
                                pass
                        elif policy == "overwrite":
                            try:
                                package.conflicts.append({
                                    "filename": bn, "filepath": filepath,
                                    "action": "overwritten",
                                    "reason": "检测到用户手改，但按策略已覆盖",
                                })
                            except Exception:
                                pass
                    except Exception:
                        pass
                with open(written_path, "w", encoding="utf-8") as f:
                    f.write(safe_content)
                if written_path not in package.generated_files:
                    package.generated_files.append(written_path)
                return True
            except (OSError, IOError, PermissionError, UnicodeEncodeError):
                return False

        if generated_content is not None:
            try:
                sn = getattr(generated_content, "shownotes", "")
                if sn and isinstance(sn, str) and sn.strip():
                    shownotes_path = os.path.join(package.output_dir, f"{safe_ep}_shownotes.md")
                    safe_write(shownotes_path, sn)
            except Exception:
                pass

            try:
                gi = getattr(generated_content, "guest_intro", "")
                if gi and isinstance(gi, str) and gi.strip():
                    guest_path = os.path.join(package.output_dir, f"{safe_ep}_嘉宾介绍.md")
                    safe_write(guest_path, gi)
            except Exception:
                pass

            try:
                sm = getattr(generated_content, "social_media", {})
                if isinstance(sm, dict):
                    for platform, content_text in sm.items():
                        try:
                            safe_platform = sanitize_filename(str(platform))
                            if content_text and isinstance(content_text, str):
                                social_path = os.path.join(package.output_dir, f"{safe_ep}_{safe_platform}.txt")
                                safe_write(social_path, content_text)
                        except Exception:
                            continue
            except Exception:
                pass

            try:
                todo_content = self._format_todo_list(package, generated_content)
                todo_path = os.path.join(package.output_dir, f"{safe_ep}_待办清单.md")
                safe_write(todo_path, todo_content)
            except Exception:
                pass

        try:
            checklist_content = self._format_checklist(package)
            checklist_path = os.path.join(package.output_dir, f"{safe_ep}_发布清单.md")
            safe_write(checklist_path, checklist_content)
        except Exception:
            pass

        return package

    def _format_todo_list(self, package: ReleasePackage, generated_content) -> str:
        try:
            ep = str(package.episode_number) if package.episode_number else "000"
            lines = [f"# 第{ep}期待办清单", ""]
            try:
                todo_items = getattr(generated_content, "todo_list", []) if generated_content else []
                if isinstance(todo_items, list):
                    for item in todo_items:
                        if isinstance(item, str):
                            lines.append(f"- [ ] {item}")
            except Exception:
                pass
            lines.append("")
            try:
                now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            except Exception:
                now = ""
            lines.append(f"*生成时间: {now}*")
            return "\n".join(lines)
        except Exception:
            return "# 待办清单\n"

    def _format_checklist(self, package: ReleasePackage) -> str:
        try:
            ep = str(package.episode_number) if package.episode_number else "000"
            title = str(package.title) if package.title else "未命名"
            lines = [
                f"# 第{ep}期发布清单",
                "",
                f"**标题**: {title}",
                "",
                "## 检查项",
                "",
            ]

            try:
                if isinstance(package.checklist, list):
                    for item, checked in package.checklist:
                        if isinstance(item, str):
                            status = "[x]" if checked else "[ ]"
                            lines.append(f"- {status} {item}")
            except Exception:
                pass

            lines.extend(["", "## 文件清单", ""])

            try:
                if isinstance(package.rename_plans, list):
                    for plan in package.rename_plans:
                        try:
                            if not isinstance(plan, RenamePlan):
                                continue
                            status = "✅" if plan.success else "❌" if plan.error else "⏳"
                            target_name = os.path.basename(plan.target) if plan.target else ""
                            ft = str(plan.file_type) if plan.file_type else ""
                            lines.append(f"- {status} {ft}: {target_name}")
                        except Exception:
                            continue
            except Exception:
                pass

            lines.extend(["", "## 生成文件", ""])
            try:
                if isinstance(package.generated_files, list):
                    for f in package.generated_files:
                        try:
                            if isinstance(f, str):
                                lines.append(f"- {os.path.basename(f)}")
                        except Exception:
                            continue
            except Exception:
                pass

            lines.append("")
            try:
                now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            except Exception:
                now = ""
            lines.append(f"*生成时间: {now}*")

            return "\n".join(lines)
        except Exception:
            return "# 发布清单\n"

    def archive_episode(self, package: ReleasePackage) -> bool:
        if not package:
            return False

        try:
            if not package.archive_dir or not ensure_directory(package.archive_dir):
                return False
        except Exception:
            return False

        success_count = 0
        total_count = 0

        try:
            if isinstance(package.rename_plans, list):
                for plan in package.rename_plans:
                    try:
                        if not isinstance(plan, RenamePlan):
                            continue
                        if plan.success and plan.target and os.path.exists(plan.target):
                            total_count += 1
                            archive_target = os.path.join(
                                package.archive_dir, os.path.basename(plan.target)
                            )
                            try:
                                if os.path.exists(archive_target):
                                    try:
                                        if filecmp.cmp(plan.target, archive_target, shallow=False):
                                            success_count += 1
                                            continue
                                    except Exception:
                                        pass
                                shutil.copy2(plan.target, archive_target)
                                success_count += 1
                            except Exception:
                                continue
                    except Exception:
                        continue
        except Exception:
            pass

        try:
            if isinstance(package.generated_files, list):
                for f in package.generated_files:
                    try:
                        if isinstance(f, str) and os.path.exists(f):
                            total_count += 1
                            archive_target = os.path.join(
                                package.archive_dir, os.path.basename(f)
                            )
                            try:
                                if os.path.exists(archive_target):
                                    try:
                                        if filecmp.cmp(f, archive_target, shallow=False):
                                            success_count += 1
                                            continue
                                    except Exception:
                                        pass
                                shutil.copy2(f, archive_target)
                                success_count += 1
                            except Exception:
                                continue
                    except Exception:
                        continue
        except Exception:
            pass

        return total_count > 0 and success_count == total_count
