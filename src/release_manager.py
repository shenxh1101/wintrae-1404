
import os
import shutil
from pathlib import Path
from dataclasses import dataclass, field
from typing import Dict, List, Tuple, Optional
from datetime import datetime

from .config import Config
from .utils import sanitize_filename, ensure_directory


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
            "is_ready": self.is_ready,
        }


class ReleaseManager:
    def __init__(self, config: Config = None):
        self.config = config or Config()
        self.output_dir = self.config.output_dir
        self.archive_dir = self.config.archive_dir
        self.checklist_items = self.config.get(
            "checklist.items",
            [
                "音频文件已校验",
                "封面图符合规范",
                "嘉宾资料已确认",
                "节目简介已审核",
                "标题候选已生成",
                "时间轴草稿已生成",
                "社媒文案已准备",
                "文件已批量重命名",
            ],
        )

    def create_release_package(
        self,
        episode_number: str,
        title: str,
        files: Dict[str, str],
        validation_result=None,
        audio_info=None,
        cover_info=None,
        generated_content=None,
    ) -> ReleasePackage:
        package = ReleasePackage(
            episode_number=episode_number,
            title=title,
            output_dir=os.path.join(self.output_dir, f"{episode_number}"),
            archive_dir=os.path.join(self.archive_dir, f"{episode_number}"),
            files=files.copy(),
        )

        package.rename_plans = self._generate_rename_plans(
            episode_number, title, files
        )

        package.checklist = self._build_checklist(
            validation_result, audio_info, cover_info, generated_content
        )

        package.is_ready = all(checked for _, checked in package.checklist)

        return package

    def _generate_rename_plans(
        self, episode_number: str, title: str, files: Dict[str, str]
    ) -> List[RenamePlan]:
        plans = []
        safe_title = sanitize_filename(title)

        naming_map = {
            "audio": f"{episode_number}_{safe_title}",
            "cover": f"{episode_number}_{safe_title}_cover",
            "guest": f"{episode_number}_{safe_title}_嘉宾资料",
            "summary": f"{episode_number}_{safe_title}_节目简介",
        }

        for file_type, filepath in files.items():
            if not os.path.exists(filepath):
                continue

            ext = Path(filepath).suffix
            base_name = naming_map.get(file_type, f"{episode_number}_{file_type}")
            new_filename = f"{base_name}{ext}"

            output_dir = os.path.join(self.output_dir, f"{episode_number}")
            target_path = os.path.join(output_dir, new_filename)

            plans.append(
                RenamePlan(
                    source=filepath,
                    target=target_path,
                    file_type=file_type,
                )
            )

        return plans

    def _build_checklist(
        self, validation_result, audio_info, cover_info, generated_content
    ) -> List[Tuple[str, bool]]:
        checklist = []

        if audio_info:
            checklist.append(("音频文件已校验", audio_info.is_valid))
        else:
            checklist.append(("音频文件已校验", False))

        if cover_info:
            checklist.append(("封面图符合规范", cover_info.is_valid))
        else:
            checklist.append(("封面图符合规范", False))

        if validation_result and "guest" in validation_result.files:
            has_sensitive = any(
                f == os.path.basename(validation_result.files.get("guest", ""))
                for f, w, c in validation_result.sensitive_words_found
            )
            checklist.append(("嘉宾资料已确认", not has_sensitive))
        else:
            checklist.append(("嘉宾资料已确认", False))

        if validation_result and "summary" in validation_result.files:
            has_sensitive = any(
                f == os.path.basename(validation_result.files.get("summary", ""))
                for f, w, c in validation_result.sensitive_words_found
            )
            checklist.append(("节目简介已审核", not has_sensitive))
        else:
            checklist.append(("节目简介已审核", False))

        if generated_content and generated_content.title_candidates:
            checklist.append(("标题候选已生成", True))
        else:
            checklist.append(("标题候选已生成", False))

        if generated_content and generated_content.timeline:
            checklist.append(("时间轴草稿已生成", True))
        else:
            checklist.append(("时间轴草稿已生成", False))

        if generated_content and generated_content.social_media:
            checklist.append(("社媒文案已准备", True))
        else:
            checklist.append(("社媒文案已准备", False))

        checklist.append(("文件已批量重命名", False))

        return checklist

    def execute_renames(self, package: ReleasePackage) -> ReleasePackage:
        ensure_directory(package.output_dir)

        for plan in package.rename_plans:
            if plan.executed:
                continue

            try:
                ensure_directory(os.path.dirname(plan.target))
                shutil.copy2(plan.source, plan.target)
                plan.executed = True
                plan.success = True
                package.generated_files.append(plan.target)
            except Exception as e:
                plan.executed = True
                plan.success = False
                plan.error = str(e)

        for i, (item, _) in enumerate(package.checklist):
            if item == "文件已批量重命名":
                all_success = all(p.success for p in package.rename_plans if p.executed)
                package.checklist[i] = (item, all_success)
                break

        package.is_ready = all(checked for _, checked in package.checklist)

        return package

    def generate_release_documents(
        self, package: ReleasePackage, generated_content
    ) -> ReleasePackage:
        ensure_directory(package.output_dir)

        if generated_content.shownotes:
            shownotes_path = os.path.join(
                package.output_dir, f"{package.episode_number}_shownotes.md"
            )
            with open(shownotes_path, "w", encoding="utf-8") as f:
                f.write(generated_content.shownotes)
            package.generated_files.append(shownotes_path)

        if generated_content.guest_intro:
            guest_path = os.path.join(
                package.output_dir, f"{package.episode_number}_嘉宾介绍.md"
            )
            with open(guest_path, "w", encoding="utf-8") as f:
                f.write(generated_content.guest_intro)
            package.generated_files.append(guest_path)

        for platform, content in generated_content.social_media.items():
            social_path = os.path.join(
                package.output_dir, f"{package.episode_number}_{platform}.txt"
            )
            with open(social_path, "w", encoding="utf-8") as f:
                f.write(content)
            package.generated_files.append(social_path)

        todo_path = os.path.join(
            package.output_dir, f"{package.episode_number}_待办清单.md"
        )
        with open(todo_path, "w", encoding="utf-8") as f:
            f.write(self._format_todo_list(package, generated_content))
        package.generated_files.append(todo_path)

        checklist_path = os.path.join(
            package.output_dir, f"{package.episode_number}_发布清单.md"
        )
        with open(checklist_path, "w", encoding="utf-8") as f:
            f.write(self._format_checklist(package))
        package.generated_files.append(checklist_path)

        return package

    def _format_todo_list(self, package: ReleasePackage, generated_content) -> str:
        lines = [f"# 第{package.episode_number}期待办清单", ""]
        for item in generated_content.todo_list:
            lines.append(f"- [ ] {item}")
        lines.append("")
        lines.append(f"*生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*")
        return "\n".join(lines)

    def _format_checklist(self, package: ReleasePackage) -> str:
        lines = [
            f"# 第{package.episode_number}期发布清单",
            "",
            f"**标题**: {package.title}",
            "",
            "## 检查项",
            "",
        ]

        for item, checked in package.checklist:
            status = "[x]" if checked else "[ ]"
            lines.append(f"- {status} {item}")

        lines.extend(["", "## 文件清单", ""])

        for plan in package.rename_plans:
            status = "✅" if plan.success else "❌" if plan.error else "⏳"
            lines.append(f"- {status} {plan.file_type}: {os.path.basename(plan.target)}")

        lines.extend(["", "## 生成文件", ""])
        for f in package.generated_files:
            lines.append(f"- {os.path.basename(f)}")

        lines.append("")
        lines.append(f"*生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*")

        return "\n".join(lines)

    def archive_episode(self, package: ReleasePackage) -> bool:
        try:
            ensure_directory(package.archive_dir)
            for plan in package.rename_plans:
                if plan.success:
                    archive_target = os.path.join(
                        package.archive_dir, os.path.basename(plan.target)
                    )
                    shutil.copy2(plan.target, archive_target)

            for f in package.generated_files:
                if os.path.exists(f):
                    archive_target = os.path.join(
                        package.archive_dir, os.path.basename(f)
                    )
                    shutil.copy2(f, archive_target)

            return True
        except Exception as e:
            print(f"归档失败: {e}")
            return False
