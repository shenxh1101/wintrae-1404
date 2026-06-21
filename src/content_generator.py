
import os
import re
from pathlib import Path
from dataclasses import dataclass, field
from typing import Dict, List, Optional
from datetime import datetime

from jinja2 import Environment, FileSystemLoader

from .config import Config
from .utils import read_text_file, format_duration


@dataclass
class GeneratedContent:
    title_candidates: List[str] = field(default_factory=list)
    shownotes: str = ""
    guest_intro: str = ""
    social_media: Dict[str, str] = field(default_factory=dict)
    timeline: List[Dict] = field(default_factory=list)
    todo_list: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "title_candidates": self.title_candidates,
            "shownotes": self.shownotes,
            "guest_intro": self.guest_intro,
            "social_media": self.social_media,
            "timeline": self.timeline,
            "todo_list": self.todo_list,
            "warnings": self.warnings,
        }


class ContentGenerator:
    def __init__(self, config: Config = None):
        self.config = config or Config()
        self.templates_dir = Path(__file__).parent.parent / "templates"
        self.num_title_candidates = self.config.get("templates.title_candidates", 5)
        self.social_platforms = self.config.get(
            "templates.social_media_platforms",
            ["weibo", "xiaohongshu", "wechat", "twitter"],
        )

        self.env = Environment(
            loader=FileSystemLoader(str(self.templates_dir)),
            trim_blocks=True,
            lstrip_blocks=True,
            keep_trailing_newline=False,
        )

    def generate(
        self,
        episode_number: str,
        guest_file: str,
        summary_file: str,
        audio_duration: float = 0,
    ) -> GeneratedContent:
        content = GeneratedContent()

        guest_info = self._parse_guest_file(guest_file)
        summary_info = self._parse_summary_file(summary_file)

        context = self._build_context(
            episode_number, guest_info, summary_info, audio_duration
        )

        content.title_candidates = self._generate_title_candidates(
            episode_number, summary_info
        )
        context["title"] = content.title_candidates[0] if content.title_candidates else ""
        context["short_title"] = (
            summary_info.get("title", "")[:30] + "..."
            if len(summary_info.get("title", "")) > 30
            else summary_info.get("title", "")
        )

        content.shownotes = self._render_template("shownotes.md", context)
        content.guest_intro = self._extract_guest_intro(guest_info)
        content.timeline = self._generate_timeline(summary_info, audio_duration)
        context["timeline"] = content.timeline

        content.shownotes = self._render_template("shownotes.md", context)

        for platform in self.social_platforms:
            template_file = f"{platform}.txt"
            if (self.templates_dir / template_file).exists():
                content.social_media[platform] = self._render_template(
                    template_file, context
                )

        content.todo_list = self._generate_todo_list(episode_number)

        return content

    def _parse_guest_file(self, filepath: str) -> Dict:
        info = {
            "name": "",
            "title": "",
            "bio": "",
            "company": "",
            "links": [],
            "raw": "",
        }

        if not filepath or not os.path.exists(filepath):
            return info

        try:
            content = read_text_file(filepath)
            info["raw"] = content

            lines = content.strip().split("\n")

            if lines:
                first_line = lines[0].strip().lstrip("#").strip()
                info["name"] = first_line

            for i, line in enumerate(lines[1:], 1):
                line = line.strip()
                if not line:
                    continue

                if re.match(r"^#{1,3}\s", line):
                    section = line.lstrip("#").strip().lower()
                    continue

                if re.match(r"^[-*•]\s", line):
                    bullet = line.lstrip("-*•").strip()
                    if "http" in bullet:
                        info["links"].append(bullet)
                    elif info["bio"]:
                        info["bio"] += "\n" + bullet
                    else:
                        info["title"] = bullet
                elif "：" in line or ":" in line:
                    if "：" in line:
                        key, value = line.split("：", 1)
                    else:
                        key, value = line.split(":", 1)
                    key = key.strip().lower()
                    value = value.strip()
                    if key in ["职位", "title", "职务"]:
                        info["title"] = value
                    elif key in ["公司", "company", "机构"]:
                        info["company"] = value
                    elif key in ["简介", "bio", "介绍"]:
                        info["bio"] = value
                elif not info["title"] and i <= 3:
                    info["title"] = line
                elif not info["bio"]:
                    info["bio"] = line
                else:
                    info["bio"] += "\n" + line

            if not info["title"] and len(lines) >= 2:
                info["title"] = lines[1].strip()

            if not info["bio"]:
                bio_lines = []
                for line in lines[2:]:
                    line = line.strip()
                    if line and not line.startswith("#"):
                        bio_lines.append(line)
                info["bio"] = "\n".join(bio_lines)

        except Exception as e:
            pass

        return info

    def _parse_summary_file(self, filepath: str) -> Dict:
        info = {
            "title": "",
            "subtitle": "",
            "summary": "",
            "key_points": [],
            "highlights": [],
            "links": [],
            "tags": [],
            "raw": "",
        }

        if not filepath or not os.path.exists(filepath):
            return info

        try:
            content = read_text_file(filepath)
            info["raw"] = content

            lines = content.strip().split("\n")
            current_section = ""

            for line in lines:
                stripped = line.strip()
                if not stripped:
                    continue

                if re.match(r"^#{1,3}\s", stripped):
                    section = stripped.lstrip("#").strip().lower()
                    current_section = section
                    if not info["title"] and (
                        "标题" in section or "title" in section or "主题" in section
                    ):
                        continue
                    elif not info["title"]:
                        info["title"] = stripped.lstrip("#").strip()
                    continue

                if re.match(r"^[-*•]\s", stripped):
                    bullet = stripped.lstrip("-*•").strip()
                    if "http" in bullet:
                        info["links"].append(bullet)
                    elif current_section in ["要点", "亮点", "key points", "highlights"]:
                        info["key_points"].append(bullet)
                        info["highlights"].append(bullet)
                    elif current_section in ["标签", "tags"]:
                        info["tags"].append(bullet)
                    else:
                        info["key_points"].append(bullet)
                elif "：" in stripped or ":" in stripped:
                    if "：" in stripped:
                        key, value = stripped.split("：", 1)
                    else:
                        key, value = stripped.split(":", 1)
                    key = key.strip().lower()
                    value = value.strip()
                    if key in ["标题", "title", "主题"]:
                        info["title"] = value
                    elif key in ["副标题", "subtitle"]:
                        info["subtitle"] = value
                    elif key in ["摘要", "简介", "summary"]:
                        info["summary"] = value
                    elif key in ["标签", "tags"]:
                        info["tags"] = [t.strip() for t in value.split(",")]

            if not info["title"] and lines:
                info["title"] = lines[0].strip().lstrip("#").strip()

            if not info["summary"]:
                summary_lines = []
                for line in lines:
                    line = line.strip()
                    if line and not line.startswith("#") and not re.match(
                        r"^[-*•]\s", line
                    ):
                        if "：" not in line and ":" not in line:
                            summary_lines.append(line)
                if summary_lines:
                    info["summary"] = "\n".join(summary_lines[:3])

        except Exception as e:
            pass

        return info

    def _build_context(
        self,
        episode_number: str,
        guest_info: Dict,
        summary_info: Dict,
        audio_duration: float,
    ) -> Dict:
        now = datetime.now()
        return {
            "episode_number": episode_number,
            "title": summary_info.get("title", ""),
            "short_title": summary_info.get("title", "")[:30],
            "subtitle": summary_info.get("subtitle", ""),
            "summary_short": (
                summary_info.get("summary", "")[:100]
                if len(summary_info.get("summary", "")) > 100
                else summary_info.get("summary", "")
            ),
            "guest_name": guest_info.get("name", ""),
            "guest_title": guest_info.get("title", ""),
            "guest_bio": guest_info.get("bio", ""),
            "guest_name_en": guest_info.get("name", ""),
            "key_points": "\n".join(
                [f"- {p}" for p in summary_info.get("key_points", [])]
            ),
            "bullet_points": "\n".join(
                [f"• {p}" for p in summary_info.get("key_points", [])[:3]]
            ),
            "highlights": "\n".join(
                [f"- {h}" for h in summary_info.get("highlights", [])]
            ),
            "links": "\n".join(summary_info.get("links", [])),
            "tags": " #".join(summary_info.get("tags", ["播客"])),
            "tags_en": " #".join(summary_info.get("tags", ["podcast"])),
            "publish_date": now.strftime("%Y年%m月%d日"),
            "title_en": summary_info.get("title", ""),
            "summary_en": summary_info.get("summary", "")[:140],
            "listen_link": "https://example.com/episode/" + episode_number,
            "listen_options": "小宇宙 | 苹果播客 | Spotify | 喜马拉雅",
            "podcast_name": "播客名称",
            "footer": "感谢收听，欢迎订阅分享！",
            "duration": format_duration(audio_duration) if audio_duration else "待定",
        }

    def _generate_title_candidates(
        self, episode_number: str, summary_info: Dict
    ) -> List[str]:
        base_title = summary_info.get("title", "")
        key_points = summary_info.get("key_points", [])
        candidates = []

        if base_title:
            candidates.append(base_title)

        patterns = [
            f"深度对话：{base_title}",
            f"{base_title}的真相",
            f"聊聊{base_title}这件事",
            f"为什么{base_title}很重要",
            f"关于{base_title}，你需要知道的事",
        ]

        for pattern in patterns:
            if pattern not in candidates:
                candidates.append(pattern)

        for point in key_points[:2]:
            short_point = point[:20] if len(point) > 20 else point
            candidate = f"{short_point}背后的故事"
            if candidate not in candidates:
                candidates.append(candidate)

        return candidates[: self.num_title_candidates]

    def _generate_timeline(self, summary_info: Dict, audio_duration: float) -> List[Dict]:
        timeline = []
        key_points = summary_info.get("key_points", [])

        if not key_points:
            key_points = ["开场介绍", "主题讨论", "总结与展望"]

        total_points = len(key_points)
        if audio_duration > 0 and total_points > 0:
            interval = audio_duration / (total_points + 1)
            for i, point in enumerate(key_points):
                time_seconds = int(interval * (i + 1))
                timeline.append(
                    {"time": format_duration(time_seconds), "topic": point}
                )
        else:
            for i, point in enumerate(key_points):
                minutes = (i + 1) * 5
                timeline.append({"time": f"{minutes:02d}:00", "topic": point})

        return timeline

    def _extract_guest_intro(self, guest_info: Dict) -> str:
        name = guest_info.get("name", "")
        title = guest_info.get("title", "")
        bio = guest_info.get("bio", "")

        intro = f"**{name}**\n{title}\n\n{bio}"
        return intro.strip()

    def _generate_todo_list(self, episode_number: str) -> List[str]:
        return [
            f"确认第{episode_number}期音频最终版本",
            f"确认第{episode_number}期封面图",
            f"审核嘉宾资料",
            f"审核节目简介",
            f"确认标题",
            f"发布到各平台",
            f"社媒宣传",
            f"归档本期素材",
        ]

    def _render_template(self, template_name: str, context: Dict) -> str:
        try:
            template = self.env.get_template(template_name)
            return template.render(**context)
        except Exception as e:
            return f"[模板渲染错误: {str(e)}]"
