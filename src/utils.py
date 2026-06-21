
import re
import os
from pathlib import Path
from typing import List, Optional


def extract_episode_number(filename: str, pattern: str = r"^(\d{3})") -> Optional[str]:
    match = re.search(pattern, filename)
    if match:
        return match.group(1)
    return None


def get_file_extension(filepath: str) -> str:
    return Path(filepath).suffix.lower()


def list_files_by_extension(directory: str, extensions: List[str]) -> List[str]:
    result = []
    if not os.path.exists(directory):
        return result
    for root, dirs, files in os.walk(directory):
        for file in files:
            if Path(file).suffix.lower() in extensions:
                result.append(os.path.join(root, file))
    return result


def format_duration(seconds: float) -> str:
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    if hours > 0:
        return f"{hours:02d}:{minutes:02d}:{secs:02d}"
    return f"{minutes:02d}:{secs:02d}"


def sanitize_filename(filename: str) -> str:
    invalid_chars = r'[<>:"/\\|?*]'
    sanitized = re.sub(invalid_chars, "_", filename)
    return sanitized.strip()


def read_text_file(filepath: str) -> str:
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            return f.read()
    except UnicodeDecodeError:
        with open(filepath, "r", encoding="gbk") as f:
            return f.read()


def ensure_directory(directory: str):
    os.makedirs(directory, exist_ok=True)
