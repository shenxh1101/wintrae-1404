
import re
import os
from pathlib import Path
from typing import List, Optional


def extract_episode_number(filename: str, pattern: str = r"^(\d{3})") -> Optional[str]:
    if not filename or not pattern:
        return None
    try:
        match = re.search(pattern, filename)
        if match and match.group(1):
            return str(match.group(1))
    except (re.error, TypeError, ValueError):
        pass
    return None


def get_file_extension(filepath: str) -> str:
    try:
        if not filepath:
            return ""
        return Path(filepath).suffix.lower()
    except (TypeError, ValueError):
        return ""


def list_files_by_extension(directory: str, extensions: List[str]) -> List[str]:
    result: List[str] = []
    if not directory or not os.path.exists(directory) or not extensions:
        return result
    ext_set = set(e.lower() for e in extensions if isinstance(e, str))
    if not ext_set:
        return result
    try:
        for root, dirs, files in os.walk(directory):
            for file in files:
                try:
                    if Path(file).suffix.lower() in ext_set:
                        result.append(os.path.join(root, file))
                except (TypeError, ValueError, OSError):
                    continue
    except (OSError, PermissionError, ValueError):
        pass
    return result


def format_duration(seconds) -> str:
    try:
        secs_val = float(seconds) if seconds is not None else 0.0
        if secs_val < 0:
            secs_val = 0.0
        hours = int(secs_val // 3600)
        minutes = int((secs_val % 3600) // 60)
        secs = int(secs_val % 60)
        if hours > 0:
            return f"{hours:02d}:{minutes:02d}:{secs:02d}"
        return f"{minutes:02d}:{secs:02d}"
    except (TypeError, ValueError):
        return "00:00"


def sanitize_filename(filename: str) -> str:
    if not filename:
        return "unnamed"
    try:
        invalid_chars = r'[<>:"/\\|?*\x00-\x1f]'
        sanitized = re.sub(invalid_chars, "_", str(filename))
        sanitized = sanitized.replace("..", "_")
        sanitized = sanitized.replace("/", "_").replace("\\", "_")
        sanitized = sanitized.strip().strip(".")
        if not sanitized:
            return "unnamed"
        if len(sanitized) > 200:
            sanitized = sanitized[:200]
        return sanitized
    except (TypeError, ValueError, re.error):
        return "unnamed"


def safe_filename_component(name: str) -> str:
    return sanitize_filename(name)


def read_text_file(filepath: str) -> str:
    if not filepath or not os.path.exists(filepath):
        return ""
    encodings = ["utf-8", "utf-8-sig", "gbk", "gb18030", "latin-1"]
    for enc in encodings:
        try:
            with open(filepath, "r", encoding=enc) as f:
                content = f.read()
                if content is not None:
                    return content
        except (UnicodeDecodeError, OSError, IOError, PermissionError):
            continue
    try:
        with open(filepath, "r", encoding="utf-8", errors="replace") as f:
            content = f.read()
            return content if content is not None else ""
    except (OSError, IOError, PermissionError):
        return ""


def ensure_directory(directory: str) -> bool:
    if not directory:
        return False
    try:
        os.makedirs(directory, exist_ok=True)
        return True
    except (OSError, PermissionError, ValueError):
        return False


def safe_join_path(base_dir: str, *parts) -> Optional[str]:
    try:
        if not base_dir:
            return None
        safe_parts = [str(p) for p in parts if p is not None]
        candidate = os.path.join(str(base_dir), *safe_parts)
        candidate_norm = os.path.normpath(candidate)
        base_norm = os.path.normpath(str(base_dir))
        try:
            if not candidate_norm.startswith(base_norm):
                return None
            if len(candidate_norm) > len(base_norm) and candidate_norm[len(base_norm)] not in (os.sep, '/'):
                return None
        except Exception:
            return None
        return candidate_norm
    except (TypeError, ValueError, OSError):
        return None


def is_path_safe(base_dir: str, target_path: str) -> bool:
    try:
        if not base_dir or not target_path:
            return False
        base_real = os.path.realpath(base_dir)
        target_real = os.path.realpath(target_path)
        common = os.path.commonpath([base_real, target_real])
        return common == base_real or common.startswith(base_real + os.sep)
    except (OSError, ValueError):
        return False
