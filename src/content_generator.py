
import os
import re
from pathlib import Path
from dataclasses import dataclass, field
from typing import Dict, List, Optional
from datetime import datetime

try:
    from jinja2.sandbox import SandboxedEnvironment as Environment
    from jinja2 import FileSystemLoader
    JINJA2_AVAILABLE = True
except ImportError:
    try:
        from jinja2 import Environment, FileSystemLoader
        JINJA2_AVAILABLE = True
    except ImportError:
        JINJA2_AVAILABLE = False
        Environment = None
        FileSystemLoader = None

from .config import Config
from .utils import read_text_file, format_duration, sanitize_filename


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
        try:
            self.templates_dir = Path(__file__).parent.parent / "templates"
        except Exception:
            self.templates_dir = Path("./templates")

        try:
            self.num_title_candidates = int(self.config.get("templates.title_candidates", 5))
        except (TypeError, ValueError):
            self.num_title_candidates = 5
        if self.num_title_candidates <= 0:
            self.num_title_candidates = 5

        platforms = self.config.get("templates.social_media_platforms", ["weibo", "xiaohongshu", "wechat", "twitter"])
        if isinstance(platforms, list):
            self.social_platforms = [str(p) for p in platforms if isinstance(p, str)]
        else:
            self.social_platforms = ["weibo", "xiaohongshu", "wechat", "twitter"]

        self.env: Optional[Environment] = None
        if JINJA2_AVAILABLE:
            try:
                self.env = Environment(
                    loader=FileSystemLoader(str(self.templates_dir)),
                    trim_blocks=True,
                    lstrip_blocks=True,
                    keep_trailing_newline=False,
                )
            except Exception:
                self.env = None

    def generate(
        self,
        episode_number: Optional[str],
        guest_file: Optional[str],
        summary_file: Optional[str],
        audio_duration=0,
    ) -> GeneratedContent:
        content = GeneratedContent()

        safe_episode = str(episode_number) if episode_number else "000"
        safe_episode = sanitize_filename(safe_episode)

        try:
            guest_info = self._parse_guest_file(guest_file)
        except Exception:
            guest_info = {"name": "", "title": "", "bio": "", "company": "", "links": [], "raw": ""}

        try:
            summary_info = self._parse_summary_file(summary_file)
        except Exception:
            summary_info = {"title": "", "subtitle": "", "summary": "", "key_points": [], "highlights": [], "links": [], "tags": [], "raw": ""}

        try:
            audio_duration_val = float(audio_duration) if audio_duration is not None else 0.0
            if audio_duration_val < 0:
                audio_duration_val = 0.0
        except (TypeError, ValueError):
            audio_duration_val = 0.0

        try:
            context = self._build_context(
                safe_episode, guest_info, summary_info, audio_duration_val
            )
        except Exception:
            context = {}

        try:
            content.title_candidates = self._generate_title_candidates(
                safe_episode, summary_info
            )
        except Exception as e:
            content.title_candidates = ["未命名节目"]
            content.warnings.append(f"标题生成失败: {str(e)}")

        try:
            context["title"] = content.title_candidates[0] if content.title_candidates else "未命名节目"
            raw_title = summary_info.get("title", "")
            title_text = str(raw_title) if raw_title else ""
            if len(title_text) > 30:
                context["short_title"] = title_text[:30] + "..."
            else:
                context["short_title"] = title_text
        except Exception:
            context["title"] = "未命名节目"
            context["short_title"] = "未命名节目"

        try:
            content.shownotes = self._render_template("shownotes.md", context)
        except Exception as e:
            content.shownotes = ""
            content.warnings.append(f"shownotes 渲染失败: {str(e)}")

        try:
            content.guest_intro = self._extract_guest_intro(guest_info)
        except Exception:
            content.guest_intro = ""

        try:
            content.timeline = self._generate_timeline(summary_info, audio_duration_val)
        except Exception:
            content.timeline = []

        try:
            context["timeline"] = content.timeline
            content.shownotes = self._render_template("shownotes.md", context)
        except Exception:
            pass

        for platform in self.social_platforms:
            try:
                template_file = f"{platform}.txt"
                template_path = self.templates_dir / template_file
                if template_path.exists():
                    content.social_media[platform] = self._render_template(
                        template_file, context
                    )
            except Exception as e:
                content.warnings.append(f"{platform} 文案生成失败: {str(e)}")
                continue

        try:
            content.todo_list = self._generate_todo_list(safe_episode)
        except Exception:
            content.todo_list = []

        return content

    def _parse_guest_file(self, filepath: Optional[str]) -> Dict:
        info = {
            "name": "",
            "title": "",
            "bio": "",
            "company": "",
            "links": [],
            "raw": "",
        }

        if not filepath or not isinstance(filepath, str):
            return info
        if not os.path.exists(filepath):
            return info

        try:
            content = read_text_file(filepath)
            info["raw"] = content if content else ""

            if not content or not content.strip():
                return info

            lines = content.strip().split("\n")

            if lines:
                first_line = lines[0].strip().lstrip("#").strip()
                info["name"] = first_line

            for i, line in enumerate(lines[1:], 1):
                line = line.strip() if isinstance(line, str) else ""
                if not line:
                    continue

                if re.match(r"^#{1,3}\s", line):
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
                    try:
                        if "：" in line:
                            key, value = line.split("：", 1)
                        else:
                            key, value = line.split(":", 1)
                        key = key.strip().lower() if isinstance(key, str) else ""
                        value = value.strip() if isinstance(value, str) else ""
                        if key in ["职位", "title", "职务"]:
                            info["title"] = value
                        elif key in ["公司", "company", "机构"]:
                            info["company"] = value
                        elif key in ["简介", "bio", "介绍"]:
                            info["bio"] = value
                    except (ValueError, TypeError):
                        if not info["title"] and i <= 3:
                            info["title"] = line
                        elif not info["bio"]:
                            info["bio"] = line
                        else:
                            info["bio"] += "\n" + line
                elif not info["title"] and i <= 3:
                    info["title"] = line
                elif not info["bio"]:
                    info["bio"] = line
                else:
                    info["bio"] += "\n" + line

            if not info["title"] and len(lines) >= 2:
                info["title"] = lines[1].strip() if isinstance(lines[1], str) else ""

            if not info["bio"]:
                bio_lines = []
                for line in lines[2:]:
                    line_text = line.strip() if isinstance(line, str) else ""
                    if line_text and not line_text.startswith("#"):
                        bio_lines.append(line_text)
                info["bio"] = "\n".join(bio_lines)

        except Exception:
            pass

        return info

    def _parse_summary_file(self, filepath: Optional[str]) -> Dict:
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

        if not filepath or not isinstance(filepath, str):
            return info
        if not os.path.exists(filepath):
            return info

        try:
            content = read_text_file(filepath)
            info["raw"] = content if content else ""

            if not content or not content.strip():
                return info

            lines = content.strip().split("\n")
            current_section = ""

            for line in lines:
                stripped = line.strip() if isinstance(line, str) else ""
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
                    try:
                        if "：" in stripped:
                            key, value = stripped.split("：", 1)
                        else:
                            key, value = stripped.split(":", 1)
                        key = key.strip().lower() if isinstance(key, str) else ""
                        value = value.strip() if isinstance(value, str) else ""
                        if key in ["标题", "title", "主题"]:
                            info["title"] = value
                        elif key in ["副标题", "subtitle"]:
                            info["subtitle"] = value
                        elif key in ["摘要", "简介", "summary"]:
                            info["summary"] = value
                        elif key in ["标签", "tags"]:
                            if isinstance(value, str):
                                info["tags"] = [t.strip() for t in value.split(",") if t.strip()]
                    except (ValueError, TypeError):
                        pass

            if not info["title"] and lines:
                first = lines[0] if isinstance(lines[0], str) else ""
                info["title"] = first.strip().lstrip("#").strip()

            if not info["summary"]:
                summary_lines = []
                for line in lines:
                    line_text = line.strip() if isinstance(line, str) else ""
                    if line_text and not line_text.startswith("#") and not re.match(
                        r"^[-*•]\s", line_text
                    ):
                        if "：" not in line_text and ":" not in line_text:
                            summary_lines.append(line_text)
                if summary_lines:
                    info["summary"] = "\n".join(summary_lines[:3])

        except Exception:
            pass

        return info

    def _build_context(
        self,
        episode_number: str,
        guest_info: Dict,
        summary_info: Dict,
        audio_duration: float,
    ) -> Dict:
        try:
            now = datetime.now()
        except Exception:
            now = datetime(2000, 1, 1)

        safe_episode = sanitize_filename(str(episode_number) if episode_number else "000")
        title_val = str(summary_info.get("title", "")) if summary_info.get("title") else ""
        subtitle_val = str(summary_info.get("subtitle", "")) if summary_info.get("subtitle") else ""
        summary_val = str(summary_info.get("summary", "")) if summary_info.get("summary") else ""
        guest_name_val = str(guest_info.get("name", "")) if guest_info.get("name") else ""
        guest_title_val = str(guest_info.get("title", "")) if guest_info.get("title") else ""
        guest_bio_val = str(guest_info.get("bio", "")) if guest_info.get("bio") else ""

        if len(summary_val) > 100:
            summary_short = summary_val[:100]
        else:
            summary_short = summary_val

        key_points_raw = summary_info.get("key_points", [])
        if not isinstance(key_points_raw, list):
            key_points_raw = []
        key_points_list = [str(p) for p in key_points_raw if p is not None]

        highlights_raw = summary_info.get("highlights", [])
        if not isinstance(highlights_raw, list):
            highlights_raw = []
        highlights_list = [str(h) for h in highlights_raw if h is not None]

        links_raw = summary_info.get("links", [])
        if not isinstance(links_raw, list):
            links_raw = []
        links_list = [str(l) for l in links_raw if l is not None]

        tags_raw = summary_info.get("tags", [])
        if not isinstance(tags_raw, list) or not tags_raw:
            tags_raw = ["播客"]
        tags_list = [str(t) for t in tags_raw if t is not None]
        tags_en_list = [str(t) for t in tags_raw if t is not None] or ["podcast"]

        try:
            short_title = title_val[:30] + "..." if len(title_val) > 30 else title_val
        except Exception:
            short_title = title_val

        try:
            if safe_episode:
                listen_link = "https://example.com/episode/" + safe_episode
            else:
                listen_link = "https://example.com/"
        except Exception:
            listen_link = "https://example.com/"

        return {
            "episode_number": safe_episode,
            "title": title_val,
            "short_title": short_title,
            "subtitle": subtitle_val,
            "summary_short": summary_short,
            "guest_name": guest_name_val,
            "guest_title": guest_title_val,
            "guest_bio": guest_bio_val,
            "guest_name_en": guest_name_val,
            "key_points": "\n".join([f"- {p}" for p in key_points_list]),
            "bullet_points": "\n".join([f"• {p}" for p in key_points_list[:3]]),
            "highlights": "\n".join([f"- {h}" for h in highlights_list]),
            "links": "\n".join(links_list),
            "tags": " #".join(tags_list),
            "tags_en": " #".join(tags_en_list),
            "publish_date": now.strftime("%Y年%m月%d日") if now else "",
            "title_en": title_val,
            "summary_en": summary_val[:140] if len(summary_val) > 140 else summary_val,
            "listen_link": listen_link,
            "listen_options": "小宇宙 | 苹果播客 | Spotify | 喜马拉雅",
            "podcast_name": "播客名称",
            "footer": "感谢收听，欢迎订阅分享！",
            "duration": format_duration(audio_duration) if audio_duration else "待定",
        }

    def _generate_title_candidates(
        self, episode_number: str, summary_info: Dict
    ) -> List[str]:
        base_title = str(summary_info.get("title", "")) if summary_info.get("title") else ""
        key_points = summary_info.get("key_points", [])
        if not isinstance(key_points, list):
            key_points = []
        candidates: List[str] = []

        if base_title and base_title.strip():
            candidates.append(base_title.strip())

        if base_title and base_title.strip():
            patterns = [
                f"深度对话：{base_title}",
                f"{base_title}的真相",
                f"聊聊{base_title}这件事",
                f"为什么{base_title}很重要",
                f"关于{base_title}，你需要知道的事",
            ]
            for pattern in patterns:
                if pattern and pattern not in candidates and pattern.strip():
                    candidates.append(pattern)

            for point in key_points[:2]:
                try:
                    point_str = str(point)
                    short_point = point_str[:20] if len(point_str) > 20 else point_str
                    candidate = f"{short_point}背后的故事"
                    if candidate not in candidates and candidate.strip():
                        candidates.append(candidate)
                except Exception:
                    continue

        if not candidates:
            candidates.append(f"第{episode_number}期节目")

        return candidates[: self.num_title_candidates]

    def _generate_timeline(self, summary_info: Dict, audio_duration: float) -> List[Dict]:
        timeline: List[Dict] = []
        key_points = summary_info.get("key_points", [])
        if not isinstance(key_points, list):
            key_points = []

        if not key_points:
            key_points = ["开场介绍", "主题讨论", "总结与展望"]

        total_points = len(key_points)
        try:
            dur_val = float(audio_duration)
        except (TypeError, ValueError):
            dur_val = 0.0

        if dur_val > 0 and total_points > 0:
            try:
                interval = dur_val / (total_points + 1)
                for i, point in enumerate(key_points):
                    try:
                        time_seconds = int(interval * (i + 1))
                        if time_seconds < 0:
                            time_seconds = 0
                        timeline.append(
                            {"time": format_duration(time_seconds), "topic": str(point)}
                        )
                    except Exception:
                        continue
            except (ZeroDivisionError, TypeError, ValueError):
                for i, point in enumerate(key_points):
                    minutes = (i + 1) * 5
                    timeline.append({"time": f"{minutes:02d}:00", "topic": str(point)})
        else:
            for i, point in enumerate(key_points):
                try:
                    minutes = (i + 1) * 5
                    timeline.append({"time": f"{minutes:02d}:00", "topic": str(point)})
                except Exception:
                    continue

        return timeline

    def _extract_guest_intro(self, guest_info: Dict) -> str:
        try:
            name = str(guest_info.get("name", "")) if guest_info.get("name") else ""
            title = str(guest_info.get("title", "")) if guest_info.get("title") else ""
            bio = str(guest_info.get("bio", "")) if guest_info.get("bio") else ""

            intro = f"**{name}**\n{title}\n\n{bio}"
            return intro.strip()
        except Exception:
            return ""

    def _generate_todo_list(self, episode_number: str) -> List[str]:
        safe_ep = str(episode_number) if episode_number else "000"
        return [
            f"确认第{safe_ep}期音频最终版本",
            f"确认第{safe_ep}期封面图",
            "审核嘉宾资料",
            "审核节目简介",
            "确认标题",
            "发布到各平台",
            "社媒宣传",
            "归档本期素材",
        ]

    def _render_template(self, template_name: str, context: Dict) -> str:
        if not template_name or not self.env:
            return ""
        try:
            template = self.env.get_template(template_name)
            safe_context = {}
            for k, v in (context or {}).items():
                try:
                    if v is None:
                        safe_context[k] = ""
                    elif isinstance(v, (str, int, float, bool, list, dict)):
                        safe_context[k] = v
                    else:
                        safe_context[k] = str(v)
                except Exception:
                    safe_context[k] = ""
            result = template.render(**safe_context)
            return result if result else ""
        except Exception as e:
            return f"[模板渲染错误: {str(e)}]"
