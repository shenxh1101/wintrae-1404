
import os
import json
import copy
import threading
from typing import Dict, Optional, Any, List
from datetime import datetime
from pathlib import Path

from .config import Config
from .utils import ensure_directory, sanitize_filename


EPISODE_STATUS_PENDING = "pending"
EPISODE_STATUS_READY = "ready"
EPISODE_STATUS_PROCESSING = "processing"
EPISODE_STATUS_RELEASED = "released"
EPISODE_STATUS_ARCHIVED = "archived"
EPISODE_STATUS_ERROR = "error"


class EpisodeState:
    def __init__(self, episode_number: str, directory: str = ""):
        self.episode_number: str = str(episode_number) if episode_number else "unknown"
        self.directory: str = str(directory) if directory else ""
        self.status: str = EPISODE_STATUS_PENDING
        self.created_at: str = datetime.now().isoformat()
        self.updated_at: str = datetime.now().isoformat()
        self.last_processed_at: Optional[str] = None
        self.last_released_at: Optional[str] = None
        self.last_archived_at: Optional[str] = None

        self.missing_files: List[str] = []
        self.naming_issues: List[str] = []
        self.sensitive_words_found: List[List[str]] = []

        self.audio_duration_seconds: Optional[float] = None
        self.audio_format: str = ""
        self.cover_width: Optional[int] = None
        self.cover_height: Optional[int] = None
        self.cover_format: str = ""

        self.files: Dict[str, str] = {}
        self.title: str = ""
        self.title_candidates: List[str] = []

        self.output_dir: str = ""
        self.archive_dir: str = ""
        self.generated_files: List[str] = []

        self.warnings: List[str] = []
        self.errors: List[str] = []
        self.checklist: List[List[Any]] = []

        self.is_valid: bool = False
        self.is_released: bool = False
        self.is_archived: bool = False

        self.custom_user_edits: bool = False
        self.release_notes: str = ""
        self.metadata: Dict[str, Any] = {}

    def touch(self):
        try:
            self.updated_at = datetime.now().isoformat()
        except Exception:
            pass

    def to_dict(self) -> Dict[str, Any]:
        try:
            return {
                "episode_number": str(self.episode_number),
                "directory": str(self.directory),
                "status": str(self.status),
                "created_at": str(self.created_at),
                "updated_at": str(self.updated_at),
                "last_processed_at": self.last_processed_at,
                "last_released_at": self.last_released_at,
                "last_archived_at": self.last_archived_at,

                "missing_files": list(self.missing_files) if isinstance(self.missing_files, list) else [],
                "naming_issues": list(self.naming_issues) if isinstance(self.naming_issues, list) else [],
                "sensitive_words_found": [list(item) for item in self.sensitive_words_found] if isinstance(self.sensitive_words_found, list) else [],

                "audio_duration_seconds": self.audio_duration_seconds,
                "audio_format": str(self.audio_format) if self.audio_format else "",
                "cover_width": self.cover_width,
                "cover_height": self.cover_height,
                "cover_format": str(self.cover_format) if self.cover_format else "",

                "files": dict(self.files) if isinstance(self.files, dict) else {},
                "title": str(self.title) if self.title else "",
                "title_candidates": list(self.title_candidates) if isinstance(self.title_candidates, list) else [],

                "output_dir": str(self.output_dir) if self.output_dir else "",
                "archive_dir": str(self.archive_dir) if self.archive_dir else "",
                "generated_files": list(self.generated_files) if isinstance(self.generated_files, list) else [],

                "warnings": list(self.warnings) if isinstance(self.warnings, list) else [],
                "errors": list(self.errors) if isinstance(self.errors, list) else [],
                "checklist": [list(item) if isinstance(item, (list, tuple)) else item for item in self.checklist] if isinstance(self.checklist, list) else [],

                "is_valid": bool(self.is_valid),
                "is_released": bool(self.is_released),
                "is_archived": bool(self.is_archived),

                "custom_user_edits": bool(self.custom_user_edits),
                "release_notes": str(self.release_notes) if self.release_notes else "",
                "metadata": dict(self.metadata) if isinstance(self.metadata, dict) else {},
            }
        except Exception:
            return {
                "episode_number": str(self.episode_number),
                "directory": str(self.directory),
                "status": EPISODE_STATUS_ERROR,
                "errors": ["状态序列化失败"],
            }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "EpisodeState":
        try:
            ep = data.get("episode_number", "unknown")
            directory = data.get("directory", "")
            state = cls(ep, directory)

            try:
                state.status = str(data.get("status", EPISODE_STATUS_PENDING))
                state.created_at = str(data.get("created_at", datetime.now().isoformat()))
                state.updated_at = str(data.get("updated_at", datetime.now().isoformat()))
                state.last_processed_at = data.get("last_processed_at")
                state.last_released_at = data.get("last_released_at")
                state.last_archived_at = data.get("last_archived_at")
            except Exception:
                pass

            try:
                mf = data.get("missing_files", [])
                state.missing_files = [str(x) for x in mf if isinstance(x, str)] if isinstance(mf, list) else []
            except Exception:
                state.missing_files = []

            try:
                ni = data.get("naming_issues", [])
                state.naming_issues = [str(x) for x in ni if isinstance(x, str)] if isinstance(ni, list) else []
            except Exception:
                state.naming_issues = []

            try:
                sw = data.get("sensitive_words_found", [])
                if isinstance(sw, list):
                    converted = []
                    for item in sw:
                        try:
                            if isinstance(item, (list, tuple)) and len(item) >= 3:
                                converted.append([str(item[0]), str(item[1]), str(item[2])])
                        except Exception:
                            continue
                    state.sensitive_words_found = converted
            except Exception:
                state.sensitive_words_found = []

            try:
                dur = data.get("audio_duration_seconds")
                if dur is not None and isinstance(dur, (int, float)):
                    state.audio_duration_seconds = float(dur)
                state.audio_format = str(data.get("audio_format", ""))
            except Exception:
                pass

            try:
                cw = data.get("cover_width")
                if cw is not None and isinstance(cw, (int, float)):
                    state.cover_width = int(cw)
                ch = data.get("cover_height")
                if ch is not None and isinstance(ch, (int, float)):
                    state.cover_height = int(ch)
                state.cover_format = str(data.get("cover_format", ""))
            except Exception:
                pass

            try:
                f = data.get("files", {})
                if isinstance(f, dict):
                    state.files = {str(k): str(v) for k, v in f.items() if isinstance(k, str) and isinstance(v, str)}
            except Exception:
                state.files = {}

            try:
                state.title = str(data.get("title", ""))
                tc = data.get("title_candidates", [])
                state.title_candidates = [str(x) for x in tc if isinstance(x, str)] if isinstance(tc, list) else []
            except Exception:
                pass

            try:
                state.output_dir = str(data.get("output_dir", ""))
                state.archive_dir = str(data.get("archive_dir", ""))
                gf = data.get("generated_files", [])
                state.generated_files = [str(x) for x in gf if isinstance(x, str)] if isinstance(gf, list) else []
            except Exception:
                pass

            try:
                w = data.get("warnings", [])
                state.warnings = [str(x) for x in w if isinstance(x, str)] if isinstance(w, list) else []
                e = data.get("errors", [])
                state.errors = [str(x) for x in e if isinstance(x, str)] if isinstance(e, list) else []
            except Exception:
                state.warnings = []
                state.errors = []

            try:
                cl = data.get("checklist", [])
                if isinstance(cl, list):
                    converted = []
                    for item in cl:
                        try:
                            if isinstance(item, (list, tuple)) and len(item) >= 2:
                                converted.append([str(item[0]), bool(item[1])])
                        except Exception:
                            continue
                    state.checklist = converted
            except Exception:
                state.checklist = []

            try:
                state.is_valid = bool(data.get("is_valid", False))
                state.is_released = bool(data.get("is_released", False))
                state.is_archived = bool(data.get("is_archived", False))
                state.custom_user_edits = bool(data.get("custom_user_edits", False))
                state.release_notes = str(data.get("release_notes", ""))
            except Exception:
                pass

            try:
                md = data.get("metadata", {})
                if isinstance(md, dict):
                    safe_md = {}
                    for k, v in md.items():
                        try:
                            if isinstance(k, str) and isinstance(v, (str, int, float, bool, list, dict, type(None))):
                                safe_md[str(k)] = copy.deepcopy(v)
                        except Exception:
                            continue
                    state.metadata = safe_md
            except Exception:
                state.metadata = {}

            return state
        except Exception:
            fallback = cls("unknown", "")
            fallback.status = EPISODE_STATUS_ERROR
            fallback.errors = ["状态反序列化失败"]
            return fallback


class StateManager:
    def __init__(self, config: Config = None):
        try:
            self.config = config or Config()
        except Exception:
            from .config import Config
            self.config = Config()

        try:
            base_dir = getattr(self.config, "output_dir", None)
            if base_dir:
                self.state_dir = os.path.join(str(base_dir), ".state")
            else:
                self.state_dir = os.path.join(".", "output", ".state")
        except Exception:
            self.state_dir = os.path.join(".", "output", ".state")

        try:
            self.state_file = os.path.join(self.state_dir, "episodes.json")
        except Exception:
            self.state_file = "episodes_state.json"

        self._lock = threading.RLock()
        self._episodes: Dict[str, EpisodeState] = {}
        self._dirty = False

        try:
            ensure_directory(self.state_dir)
        except Exception:
            pass

        try:
            self._load()
        except Exception:
            self._episodes = {}

    def _load(self):
        with self._lock:
            self._episodes = {}
            try:
                if not os.path.exists(self.state_file):
                    return
                with open(self.state_file, "r", encoding="utf-8") as f:
                    raw = f.read()
                if not raw or not raw.strip():
                    return
                data = json.loads(raw)
                if not isinstance(data, dict):
                    return
                eps_data = data.get("episodes", {})
                if not isinstance(eps_data, dict):
                    return
                for key, ep_data in eps_data.items():
                    try:
                        if isinstance(ep_data, dict):
                            state = EpisodeState.from_dict(ep_data)
                            if isinstance(key, str) and key:
                                self._episodes[key] = state
                    except Exception:
                        continue
            except (json.JSONDecodeError, OSError, IOError, PermissionError, UnicodeDecodeError):
                self._episodes = {}

    def save(self) -> bool:
        with self._lock:
            try:
                ensure_directory(self.state_dir)
                data = {
                    "version": 1,
                    "saved_at": datetime.now().isoformat(),
                    "episodes": {k: v.to_dict() for k, v in self._episodes.items()},
                }
                tmp_file = self.state_file + ".tmp"
                with open(tmp_file, "w", encoding="utf-8") as f:
                    json.dump(data, f, ensure_ascii=False, indent=2)
                if os.path.exists(self.state_file):
                    try:
                        os.remove(self.state_file)
                    except Exception:
                        pass
                os.replace(tmp_file, self.state_file)
                self._dirty = False
                return True
            except (OSError, IOError, PermissionError, TypeError, ValueError, UnicodeEncodeError):
                try:
                    if os.path.exists(self.state_file + ".tmp"):
                        os.remove(self.state_file + ".tmp")
                except Exception:
                    pass
                return False

    def _get_key(self, episode_number: str, directory: str = "") -> str:
        try:
            if episode_number and isinstance(episode_number, str) and episode_number.strip():
                return sanitize_filename(episode_number)
        except Exception:
            pass
        try:
            if directory and isinstance(directory, str) and directory.strip():
                norm = os.path.normpath(directory)
                return sanitize_filename(norm.replace(os.sep, "_").replace(":", "_"))
        except Exception:
            pass
        return "unknown"

    def get(self, episode_number: str, directory: str = "") -> Optional[EpisodeState]:
        with self._lock:
            key = self._get_key(episode_number, directory)
            if key in self._episodes:
                return self._episodes[key]
            return None

    def get_or_create(self, episode_number: str, directory: str = "") -> EpisodeState:
        with self._lock:
            key = self._get_key(episode_number, directory)
            if key in self._episodes:
                return self._episodes[key]
            state = EpisodeState(episode_number, directory)
            self._episodes[key] = state
            self._dirty = True
            return state

    def update_from_process_result(self, episode_number: str, directory: str, process_result) -> EpisodeState:
        with self._lock:
            state = self.get_or_create(episode_number, directory)

            preserved_user_edited = False
            preserved_title = ""
            try:
                preserved_user_edited = bool(state.custom_user_edits)
                if preserved_user_edited:
                    preserved_title = str(state.title) if state.title else ""
            except Exception:
                preserved_user_edited = False
                preserved_title = ""

            try:
                state.directory = str(directory) if directory else state.directory
            except Exception:
                pass

            try:
                vr = getattr(process_result, "validation", None)
                if vr is not None:
                    try:
                        mf = getattr(vr, "missing_files", None)
                        if isinstance(mf, list):
                            state.missing_files = [str(x) for x in mf if isinstance(x, str)]
                    except Exception:
                        pass
                    try:
                        ni = getattr(vr, "naming_issues", None)
                        if isinstance(ni, list):
                            state.naming_issues = [str(x) for x in ni if isinstance(x, str)]
                    except Exception:
                        pass
                    try:
                        sw = getattr(vr, "sensitive_words_found", None)
                        if isinstance(sw, list):
                            converted = []
                            for item in sw:
                                try:
                                    if isinstance(item, (list, tuple)) and len(item) >= 3:
                                        converted.append([str(item[0]), str(item[1]), str(item[2])])
                                except Exception:
                                    continue
                            state.sensitive_words_found = converted
                    except Exception:
                        pass
                    try:
                        f = getattr(vr, "files", None)
                        if isinstance(f, dict):
                            state.files = {str(k): str(v) for k, v in f.items() if isinstance(k, str) and isinstance(v, str)}
                    except Exception:
                        pass
                    try:
                        w = getattr(vr, "warnings", None)
                        if isinstance(w, list):
                            state.warnings = [str(x) for x in w if isinstance(x, str)]
                    except Exception:
                        pass
            except Exception:
                pass

            try:
                ai = getattr(process_result, "audio_info", None)
                if ai is not None:
                    try:
                        dur = getattr(ai, "duration_seconds", None)
                        if dur is not None and isinstance(dur, (int, float)) and dur >= 0:
                            state.audio_duration_seconds = float(dur)
                    except Exception:
                        pass
                    try:
                        fmt = getattr(ai, "format", None)
                        if fmt is not None:
                            state.audio_format = str(fmt)
                    except Exception:
                        pass
            except Exception:
                pass

            try:
                ci = getattr(process_result, "cover_info", None)
                if ci is not None:
                    try:
                        w = getattr(ci, "width", None)
                        if w is not None and isinstance(w, (int, float)) and w >= 0:
                            state.cover_width = int(w)
                    except Exception:
                        pass
                    try:
                        h = getattr(ci, "height", None)
                        if h is not None and isinstance(h, (int, float)) and h >= 0:
                            state.cover_height = int(h)
                    except Exception:
                        pass
                    try:
                        fmt = getattr(ci, "format", None)
                        if fmt is not None:
                            state.cover_format = str(fmt)
                    except Exception:
                        pass
            except Exception:
                pass

            try:
                gc = getattr(process_result, "generated_content", None)
                if gc is not None:
                    try:
                        tc = getattr(gc, "title_candidates", None)
                        if isinstance(tc, list) and tc:
                            state.title_candidates = [str(x) for x in tc if isinstance(x, str)]
                            if not state.custom_user_edits and state.title_candidates:
                                first = state.title_candidates[0]
                                if first and isinstance(first, str) and first.strip():
                                    state.title = first
                    except Exception:
                        pass
            except Exception:
                pass

            try:
                rp = getattr(process_result, "release_package", None)
                if rp is not None:
                    try:
                        t = getattr(rp, "title", None)
                        if t and isinstance(t, str) and t.strip():
                            if not state.custom_user_edits or not state.title:
                                state.title = t
                    except Exception:
                        pass
                    try:
                        od = getattr(rp, "output_dir", None)
                        if od:
                            state.output_dir = str(od)
                    except Exception:
                        pass
                    try:
                        ad = getattr(rp, "archive_dir", None)
                        if ad:
                            state.archive_dir = str(ad)
                    except Exception:
                        pass
                    try:
                        gf = getattr(rp, "generated_files", None)
                        if isinstance(gf, list):
                            existing = set(state.generated_files)
                            for f in gf:
                                try:
                                    if isinstance(f, str) and f and f not in existing:
                                        state.generated_files.append(f)
                                        existing.add(f)
                                except Exception:
                                    continue
                    except Exception:
                        pass
                    try:
                        cl = getattr(rp, "checklist", None)
                        if isinstance(cl, list):
                            converted = []
                            for item in cl:
                                try:
                                    if isinstance(item, (list, tuple)) and len(item) >= 2:
                                        converted.append([str(item[0]), bool(item[1])])
                                except Exception:
                                    continue
                            if converted:
                                state.checklist = converted
                    except Exception:
                        pass
                    try:
                        ready = getattr(rp, "is_ready", False)
                        if ready:
                            state.is_released = True
                            state.last_released_at = datetime.now().isoformat()
                    except Exception:
                        pass
            except Exception:
                pass

            try:
                proc_errors = getattr(process_result, "errors", None)
                if isinstance(proc_errors, list) and proc_errors:
                    state.errors = [str(x) for x in proc_errors if isinstance(x, str)]
            except Exception:
                pass

            try:
                is_valid = getattr(process_result, "is_valid", False)
                state.is_valid = bool(is_valid)
            except Exception:
                pass

            try:
                if state.is_released and state.is_archived:
                    state.status = EPISODE_STATUS_ARCHIVED
                elif state.is_released:
                    state.status = EPISODE_STATUS_RELEASED
                elif state.errors:
                    state.status = EPISODE_STATUS_ERROR
                elif state.is_valid:
                    state.status = EPISODE_STATUS_READY
                else:
                    state.status = EPISODE_STATUS_PENDING
            except Exception:
                state.status = EPISODE_STATUS_PENDING

            try:
                state.last_processed_at = datetime.now().isoformat()
                state.touch()
            except Exception:
                pass

            try:
                if preserved_user_edited:
                    state.custom_user_edits = True
                    if preserved_title:
                        state.title = preserved_title
                    try:
                        if state.output_dir and isinstance(state.output_dir, str) and state.output_dir.strip():
                            marker = os.path.join(state.output_dir, ".user_edited")
                            if not os.path.exists(marker):
                                try:
                                    ensure_directory(state.output_dir)
                                    with open(marker, "w", encoding="utf-8") as f:
                                        f.write(f"# 此文件表示用户已手动修改本期内容\n")
                                        f.write(f"episode: {episode_number}\n")
                                        f.write(f"timestamp: {datetime.now().isoformat()}\n")
                                except Exception:
                                    pass
                    except Exception:
                        pass
            except Exception:
                pass

            self._dirty = True
            return state

    def mark_released(self, episode_number: str, directory: str = "") -> Optional[EpisodeState]:
        with self._lock:
            state = self.get(episode_number, directory)
            if state is None:
                return None
            try:
                state.is_released = True
                state.last_released_at = datetime.now().isoformat()
                if not state.is_archived:
                    state.status = EPISODE_STATUS_RELEASED
                state.touch()
                self._dirty = True
            except Exception:
                pass
            return state

    def mark_archived(self, episode_number: str, directory: str = "") -> Optional[EpisodeState]:
        with self._lock:
            state = self.get(episode_number, directory)
            if state is None:
                return None
            try:
                state.is_archived = True
                state.last_archived_at = datetime.now().isoformat()
                state.status = EPISODE_STATUS_ARCHIVED
                state.touch()
                self._dirty = True
            except Exception:
                pass
            return state

    def mark_user_edited(self, episode_number: str, directory: str = "") -> Optional[EpisodeState]:
        with self._lock:
            state = self.get(episode_number, directory)
            if state is None:
                return None
            try:
                state.custom_user_edits = True
                state.touch()
                self._dirty = True
                try:
                    od = getattr(state, "output_dir", "")
                    if od and isinstance(od, str) and od.strip():
                        try:
                            ensure_directory(od)
                            marker = os.path.join(od, ".user_edited")
                            with open(marker, "w", encoding="utf-8") as f:
                                f.write(f"# 此文件表示用户已手动修改本期内容\n")
                                f.write(f"episode: {episode_number}\n")
                                f.write(f"timestamp: {datetime.now().isoformat()}\n")
                        except (OSError, IOError, PermissionError, UnicodeEncodeError):
                            pass
                except Exception:
                    pass
            except Exception:
                pass
            return state

    def set_title(self, episode_number: str, title: str, directory: str = "", user_edited: bool = True) -> Optional[EpisodeState]:
        with self._lock:
            state = self.get_or_create(episode_number, directory)
            try:
                state.title = str(title) if title else ""
                if user_edited:
                    state.custom_user_edits = True
                    try:
                        od = getattr(state, "output_dir", "")
                        if od and isinstance(od, str) and od.strip():
                            try:
                                ensure_directory(od)
                                marker = os.path.join(od, ".user_edited")
                                if not os.path.exists(marker):
                                    with open(marker, "w", encoding="utf-8") as f:
                                        f.write(f"# 此文件表示用户已手动修改本期内容\n")
                                        f.write(f"episode: {episode_number}\n")
                                        f.write(f"timestamp: {datetime.now().isoformat()}\n")
                            except (OSError, IOError, PermissionError, UnicodeEncodeError):
                                pass
                    except Exception:
                        pass
                state.touch()
                self._dirty = True
            except Exception:
                pass
            return state

    def list_all(self) -> List[EpisodeState]:
        with self._lock:
            return list(self._episodes.values())

    def list_by_status(self, status: str) -> List[EpisodeState]:
        with self._lock:
            return [s for s in self._episodes.values() if s.status == status]

    def list_ready(self) -> List[EpisodeState]:
        return self.list_by_status(EPISODE_STATUS_READY)

    def list_pending(self) -> List[EpisodeState]:
        return self.list_by_status(EPISODE_STATUS_PENDING)

    def list_released(self) -> List[EpisodeState]:
        return [s for s in self.list_all() if s.is_released]

    def list_not_released(self) -> List[EpisodeState]:
        return [s for s in self.list_all() if not s.is_released]

    def delete(self, episode_number: str, directory: str = "") -> bool:
        with self._lock:
            key = self._get_key(episode_number, directory)
            if key in self._episodes:
                del self._episodes[key]
                self._dirty = True
                return True
            return False

    def clear(self):
        with self._lock:
            self._episodes.clear()
            self._dirty = True

    def get_generated_file_path(self, episode_number: str, filename: str, directory: str = "") -> Optional[str]:
        try:
            state = self.get(episode_number, directory)
            if state is None:
                return None
            if not state.output_dir or not state.custom_user_edits:
                return None
            target = os.path.join(state.output_dir, filename)
            if os.path.exists(target):
                return target
            return None
        except Exception:
            return None

    def has_user_edited_files(self, episode_number: str, directory: str = "") -> bool:
        try:
            state = self.get(episode_number, directory)
            if state is None:
                return False
            if state.custom_user_edits:
                return True
            if not state.output_dir or not os.path.exists(state.output_dir):
                return False
            meta_file = os.path.join(state.output_dir, ".user_edited")
            return os.path.exists(meta_file)
        except Exception:
            return False

    @property
    def dirty(self) -> bool:
        with self._lock:
            return self._dirty

    def __len__(self) -> int:
        with self._lock:
            return len(self._episodes)
