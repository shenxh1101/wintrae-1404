
import os
import json
import copy
import hashlib
import threading
from typing import Dict, Optional, Any, List, Tuple
from datetime import datetime
from pathlib import Path

from .config import Config
from .utils import ensure_directory, sanitize_filename


EPISODE_STATUS_PENDING = "pending"
EPISODE_STATUS_READY = "ready"
EPISODE_STATUS_PROCESSING = "processing"
EPISODE_STATUS_DRAFT = "draft"
EPISODE_STATUS_PENDING_REVIEW = "pending_review"
EPISODE_STATUS_RELEASED = "released"
EPISODE_STATUS_ARCHIVED = "archived"
EPISODE_STATUS_ERROR = "error"


def compute_file_hash(filepath: str) -> Optional[str]:
    try:
        if not filepath or not os.path.exists(filepath):
            return None
        if not os.path.isfile(filepath):
            return None
        h = hashlib.md5()
        with open(filepath, "rb") as f:
            while True:
                chunk = f.read(65536)
                if not chunk:
                    break
                h.update(chunk)
        return h.hexdigest()
    except (OSError, IOError, PermissionError):
        return None


def compute_content_hash(content: str) -> Optional[str]:
    try:
        if content is None:
            return None
        if isinstance(content, bytes):
            return hashlib.md5(content).hexdigest()
        return hashlib.md5(str(content).encode("utf-8")).hexdigest()
    except Exception:
        return None


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
        self.file_hashes: Dict[str, str] = {}
        self.user_edited_files: List[str] = []

        self.warnings: List[str] = []
        self.errors: List[str] = []
        self.checklist: List[List[Any]] = []

        self.is_valid: bool = False
        self.is_released: bool = False
        self.is_draft: bool = False
        self.is_pending_review: bool = False
        self.is_archived: bool = False

        self.custom_user_edits: bool = False
        self.release_notes: str = ""
        self.reviewer: str = ""
        self.last_reviewed_at: Optional[str] = None
        self.last_scanned_at: Optional[str] = None
        self.metadata: Dict[str, Any] = {}

    def touch(self):
        try:
            self.updated_at = datetime.now().isoformat()
        except Exception:
            pass

    def record_generated_file_hash(self, filepath: str, content: Optional[str] = None):
        try:
            if not filepath:
                return
            key = os.path.basename(filepath)
            if not key:
                key = str(filepath)
            h = None
            if content is not None:
                h = compute_content_hash(content)
            if not h:
                h = compute_file_hash(filepath)
            if h:
                self.file_hashes[key] = h
        except Exception:
            pass

    def is_file_user_edited(self, filepath: str) -> bool:
        try:
            if not filepath or not os.path.exists(filepath):
                return False
            key = os.path.basename(filepath)
            if not key:
                key = str(filepath)
            if key in self.user_edited_files:
                return True
            if key not in self.file_hashes:
                if self.custom_user_edits:
                    return True
                return False
            current_hash = compute_file_hash(filepath)
            if not current_hash:
                return False
            return current_hash != self.file_hashes[key]
        except Exception:
            return False

    def scan_user_edited_files(self) -> List[str]:
        edited: List[str] = []
        try:
            if not self.output_dir or not os.path.exists(self.output_dir):
                return edited
            seen_keys: set = set()
            try:
                if isinstance(self.generated_files, list):
                    for fp in self.generated_files:
                        try:
                            if isinstance(fp, str) and fp and os.path.exists(fp):
                                if self.is_file_user_edited(fp):
                                    bn = os.path.basename(fp)
                                    edited.append(bn)
                                    seen_keys.add(bn)
                        except Exception:
                            continue
            except Exception:
                pass
            try:
                if isinstance(self.user_edited_files, list):
                    for f in self.user_edited_files:
                        try:
                            if isinstance(f, str) and f and f not in seen_keys:
                                edited.append(f)
                                seen_keys.add(f)
                        except Exception:
                            continue
            except Exception:
                pass
            try:
                self.user_edited_files = [str(x) for x in edited if x]
            except Exception:
                pass
            return edited
        except Exception:
            return edited

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
                "file_hashes": dict(self.file_hashes) if isinstance(self.file_hashes, dict) else {},
                "user_edited_files": list(self.user_edited_files) if isinstance(self.user_edited_files, list) else [],

                "warnings": list(self.warnings) if isinstance(self.warnings, list) else [],
                "errors": list(self.errors) if isinstance(self.errors, list) else [],
                "checklist": [list(item) if isinstance(item, (list, tuple)) else item for item in self.checklist] if isinstance(self.checklist, list) else [],

                "is_valid": bool(self.is_valid),
                "is_released": bool(self.is_released),
                "is_draft": bool(self.is_draft),
                "is_pending_review": bool(self.is_pending_review),
                "is_archived": bool(self.is_archived),
                "custom_user_edits": bool(self.custom_user_edits),
                "release_notes": str(self.release_notes) if self.release_notes else "",
                "reviewer": str(self.reviewer) if self.reviewer else "",
                "last_reviewed_at": self.last_reviewed_at if isinstance(self.last_reviewed_at, str) else None,
                "last_scanned_at": self.last_scanned_at if isinstance(self.last_scanned_at, str) else None,
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
                fh = data.get("file_hashes", {})
                if isinstance(fh, dict):
                    state.file_hashes = {str(k): str(v) for k, v in fh.items() if isinstance(k, str) and isinstance(v, str)}
                uef = data.get("user_edited_files", [])
                state.user_edited_files = [str(x) for x in uef if isinstance(x, str)] if isinstance(uef, list) else []
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
                state.is_draft = bool(data.get("is_draft", False))
                state.is_pending_review = bool(data.get("is_pending_review", False))
                state.is_archived = bool(data.get("is_archived", False))
                state.custom_user_edits = bool(data.get("custom_user_edits", False))
                state.release_notes = str(data.get("release_notes", ""))
                state.reviewer = str(data.get("reviewer", ""))
                lr = data.get("last_reviewed_at", None)
                state.last_reviewed_at = str(lr) if isinstance(lr, str) else None
                ls = data.get("last_scanned_at", None)
                state.last_scanned_at = str(ls) if isinstance(ls, str) else None
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


class ReviewRecord:
    def __init__(
        self,
        episode_number: str,
        directory: str = "",
        reviewer: str = "",
        approved: bool = True,
        final_title: str = "",
        title_candidates: Optional[List[str]] = None,
        sensitive_word_actions: Optional[List[Dict]] = None,
        conflict_policy: str = "preserve",
        conflict_summary: Optional[List[Dict]] = None,
        checklist_result: Optional[List[List]] = None,
        notes: str = "",
        custom_user_edits_acknowledged: bool = False,
    ):
        self.id: str = ""
        self.episode_number: str = str(episode_number) if episode_number else "unknown"
        self.directory: str = str(directory) if directory else ""
        self.reviewer: str = str(reviewer) if reviewer else ""
        self.approved: bool = bool(approved)
        self.final_title: str = str(final_title) if final_title else ""
        self.title_candidates: List[str] = list(title_candidates) if isinstance(title_candidates, list) else []
        self.sensitive_word_actions: List[Dict] = list(sensitive_word_actions) if isinstance(sensitive_word_actions, list) else []
        self.conflict_policy: str = str(conflict_policy) if conflict_policy else "preserve"
        self.conflict_summary: List[Dict] = list(conflict_summary) if isinstance(conflict_summary, list) else []
        self.checklist_result: List[List] = [list(x) for x in checklist_result] if isinstance(checklist_result, list) else []
        self.notes: str = str(notes) if notes else ""
        self.custom_user_edits_acknowledged: bool = bool(custom_user_edits_acknowledged)
        self.created_at: str = datetime.now().isoformat()
        if not self.id:
            try:
                import uuid
                self.id = str(uuid.uuid4())
            except Exception:
                self.id = f"rev_{self.episode_number}_{int(datetime.now().timestamp())}"

    def to_dict(self) -> dict:
        try:
            def _safe_item(x):
                try:
                    if isinstance(x, (list, tuple)) and len(x) >= 2:
                        return [str(x[0]), bool(x[1])]
                    if isinstance(x, list):
                        return [str(v) for v in x]
                except Exception:
                    pass
                return []
            return {
                "id": str(self.id),
                "episode_number": str(self.episode_number),
                "directory": str(self.directory),
                "reviewer": str(self.reviewer),
                "approved": bool(self.approved),
                "final_title": str(self.final_title),
                "title_candidates": [str(x) for x in self.title_candidates if x is not None] if isinstance(self.title_candidates, list) else [],
                "sensitive_word_actions": list(self.sensitive_word_actions) if isinstance(self.sensitive_word_actions, list) else [],
                "conflict_policy": str(self.conflict_policy),
                "conflict_summary": list(self.conflict_summary) if isinstance(self.conflict_summary, list) else [],
                "checklist_result": [_safe_item(x) for x in self.checklist_result] if isinstance(self.checklist_result, list) else [],
                "notes": str(self.notes),
                "custom_user_edits_acknowledged": bool(self.custom_user_edits_acknowledged),
                "created_at": str(self.created_at),
            }
        except Exception:
            return {"id": str(self.id), "episode_number": str(self.episode_number), "created_at": str(self.created_at)}

    @classmethod
    def from_dict(cls, data: Dict) -> "ReviewRecord":
        try:
            r = cls("")
            try:
                r.id = str(data.get("id", ""))
            except Exception:
                pass
            try:
                r.episode_number = str(data.get("episode_number", ""))
            except Exception:
                pass
            try:
                r.directory = str(data.get("directory", ""))
            except Exception:
                pass
            try:
                r.reviewer = str(data.get("reviewer", ""))
            except Exception:
                pass
            try:
                r.approved = bool(data.get("approved", True))
            except Exception:
                pass
            try:
                r.final_title = str(data.get("final_title", ""))
            except Exception:
                pass
            try:
                tc = data.get("title_candidates", [])
                r.title_candidates = [str(x) for x in tc if isinstance(x, str)] if isinstance(tc, list) else []
            except Exception:
                r.title_candidates = []
            try:
                swa = data.get("sensitive_word_actions", [])
                r.sensitive_word_actions = [dict(x) for x in swa if isinstance(x, dict)] if isinstance(swa, list) else []
            except Exception:
                r.sensitive_word_actions = []
            try:
                r.conflict_policy = str(data.get("conflict_policy", "preserve"))
            except Exception:
                pass
            try:
                cs = data.get("conflict_summary", [])
                r.conflict_summary = [dict(x) for x in cs if isinstance(x, dict)] if isinstance(cs, list) else []
            except Exception:
                r.conflict_summary = []
            try:
                cl = data.get("checklist_result", [])
                r.checklist_result = [list(x) for x in cl if isinstance(x, (list, tuple))] if isinstance(cl, list) else []
            except Exception:
                r.checklist_result = []
            try:
                r.notes = str(data.get("notes", ""))
            except Exception:
                pass
            try:
                r.custom_user_edits_acknowledged = bool(data.get("custom_user_edits_acknowledged", False))
            except Exception:
                pass
            try:
                ca = data.get("created_at", None)
                if ca:
                    r.created_at = str(ca)
            except Exception:
                pass
            return r
        except Exception:
            fallback = cls("unknown")
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
            self.review_file = os.path.join(self.state_dir, "review_records.json")
        except Exception:
            self.state_file = "episodes_state.json"
            self.review_file = "review_records_state.json"

        self._lock = threading.RLock()
        self._episodes: Dict[str, EpisodeState] = {}
        self._review_records: List[ReviewRecord] = []
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
            self._review_records = []
            try:
                if not os.path.exists(self.state_file):
                    pass
                else:
                    with open(self.state_file, "r", encoding="utf-8") as f:
                        raw = f.read()
                    if raw and raw.strip():
                        data = json.loads(raw)
                        if isinstance(data, dict):
                            eps_data = data.get("episodes", {})
                            if isinstance(eps_data, dict):
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

            try:
                if not os.path.exists(self.review_file):
                    return
                with open(self.review_file, "r", encoding="utf-8") as f:
                    raw = f.read()
                if not raw or not raw.strip():
                    return
                data = json.loads(raw)
                records = data.get("records", []) if isinstance(data, dict) else []
                if not isinstance(records, list):
                    return
                for item in records:
                    try:
                        if isinstance(item, dict):
                            rec = ReviewRecord.from_dict(item)
                            self._review_records.append(rec)
                    except Exception:
                        continue
            except (json.JSONDecodeError, OSError, IOError, PermissionError, UnicodeDecodeError):
                self._review_records = []

    def save(self) -> bool:
        with self._lock:
            ok_eps = False
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
                ok_eps = True
            except (OSError, IOError, PermissionError, TypeError, ValueError, UnicodeEncodeError):
                try:
                    if os.path.exists(self.state_file + ".tmp"):
                        os.remove(self.state_file + ".tmp")
                except Exception:
                    pass
                ok_eps = False

            ok_rev = False
            try:
                ensure_directory(self.state_dir)
                rev_data = {
                    "version": 1,
                    "saved_at": datetime.now().isoformat(),
                    "records": [r.to_dict() for r in self._review_records],
                }
                tmp_rev = self.review_file + ".tmp"
                with open(tmp_rev, "w", encoding="utf-8") as f:
                    json.dump(rev_data, f, ensure_ascii=False, indent=2)
                if os.path.exists(self.review_file):
                    try:
                        os.remove(self.review_file)
                    except Exception:
                        pass
                os.replace(tmp_rev, self.review_file)
                ok_rev = True
            except (OSError, IOError, PermissionError, TypeError, ValueError, UnicodeEncodeError):
                try:
                    if os.path.exists(self.review_file + ".tmp"):
                        os.remove(self.review_file + ".tmp")
                except Exception:
                    pass
                ok_rev = False

            if ok_eps or ok_rev:
                self._dirty = False
            return ok_eps and ok_rev

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
            try:
                key = self._get_key(episode_number, directory)
                if key in self._episodes:
                    return self._episodes[key]
            except Exception:
                pass
            return None

    def get_or_create(self, episode_number: str, directory: str = "") -> EpisodeState:
        with self._lock:
            try:
                key = self._get_key(episode_number, directory)
                if key in self._episodes:
                    return self._episodes[key]
            except Exception:
                key = "unknown"
            try:
                state = EpisodeState(episode_number, directory)
            except Exception:
                state = EpisodeState("unknown", "")
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
                        overwritten_list: list = []
                        preserved_list: list = []
                        try:
                            rl = getattr(rp, "files_overwritten", None)
                            if isinstance(rl, list):
                                overwritten_list = [str(x) for x in rl if isinstance(x, str)]
                            pl = getattr(rp, "files_preserved", None)
                            if isinstance(pl, list):
                                preserved_list = [str(x) for x in pl if isinstance(x, str)]
                        except Exception:
                            overwritten_list = []
                            preserved_list = []

                        try:
                            if overwritten_list:
                                for f in overwritten_list:
                                    try:
                                        state.record_generated_file_hash(f)
                                    except Exception:
                                        continue
                                seen_overwritten = {os.path.basename(x) for x in overwritten_list if isinstance(x, str)}
                                try:
                                    new_ue = [f for f in state.user_edited_files if isinstance(f, str) and f not in seen_overwritten]
                                    state.user_edited_files = new_ue
                                except Exception:
                                    pass
                                if preserved_user_edited and not state.user_edited_files and seen_overwritten:
                                    state.custom_user_edits = False
                        except Exception:
                            pass

                        try:
                            if preserved_list:
                                for f in preserved_list:
                                    try:
                                        bn = os.path.basename(f)
                                        if bn and isinstance(bn, str) and bn not in state.user_edited_files:
                                            state.user_edited_files.append(bn)
                                    except Exception:
                                        continue
                                state.custom_user_edits = True
                        except Exception:
                            pass
                    except Exception:
                        pass

                    try:
                        rl_mode = getattr(rp, "release_mode", "release")
                        if rl_mode and isinstance(rl_mode, str):
                            state.metadata["last_release_mode"] = str(rl_mode)
                        if getattr(rp, "is_draft", False):
                            state.metadata["is_draft"] = True
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
                        mode = str(getattr(rp, "release_mode", "release") or "release")
                        is_draft_mode = bool(getattr(rp, "is_draft", False))
                        try:
                            if is_draft_mode or mode == "draft":
                                state.is_draft = True
                                state.is_pending_review = False
                                state.is_released = False
                            elif mode == "pending_review":
                                state.is_draft = False
                                state.is_pending_review = True
                                state.is_released = False
                            elif ready:
                                state.is_draft = False
                                state.is_pending_review = False
                                state.is_released = True
                                state.last_released_at = datetime.now().isoformat()
                        except Exception:
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
                elif state.is_pending_review:
                    state.status = EPISODE_STATUS_PENDING_REVIEW
                elif state.is_draft:
                    state.status = EPISODE_STATUS_DRAFT
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
                state.is_draft = False
                state.is_pending_review = False
                state.last_released_at = datetime.now().isoformat()
                if not state.is_archived:
                    state.status = EPISODE_STATUS_RELEASED
                state.touch()
                self._dirty = True
            except Exception:
                pass
            return state

    def mark_draft(self, episode_number: str, directory: str = "") -> Optional[EpisodeState]:
        with self._lock:
            state = self.get_or_create(episode_number, directory)
            try:
                state.is_draft = True
                state.is_pending_review = False
                state.is_released = False
                if not state.is_archived:
                    state.status = EPISODE_STATUS_DRAFT
                state.touch()
                self._dirty = True
            except Exception:
                pass
            return state

    def mark_pending_review(self, episode_number: str, directory: str = "") -> Optional[EpisodeState]:
        with self._lock:
            state = self.get_or_create(episode_number, directory)
            try:
                state.is_draft = False
                state.is_pending_review = True
                state.is_released = False
                if not state.is_archived:
                    state.status = EPISODE_STATUS_PENDING_REVIEW
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
            if state.output_dir and os.path.exists(state.output_dir):
                meta_file = os.path.join(state.output_dir, ".user_edited")
                if os.path.exists(meta_file):
                    return True
                edited = state.scan_user_edited_files()
                if edited:
                    return True
            return False
        except Exception:
            return False

    def scan_user_edited_files(self, episode_number: str, directory: str = "") -> List[str]:
        try:
            with self._lock:
                state = self.get_or_create(episode_number, directory)
                edited = state.scan_user_edited_files()
                if edited:
                    state.custom_user_edits = True
                    self._dirty = True
                return edited
        except Exception:
            return []

    def detect_conflicts(self, episode_number: str, directory: str = "",
                          new_files: Optional[List[Tuple[str, Optional[str]]]] = None) -> List[Dict[str, Any]]:
        conflicts: List[Dict[str, Any]] = []
        try:
            state = self.get(episode_number, directory)
            if state is None or not state.output_dir or not os.path.exists(state.output_dir):
                return conflicts
            targets: List[Tuple[str, Optional[str]]] = []
            try:
                if new_files:
                    for item in new_files:
                        try:
                            if isinstance(item, (list, tuple)) and len(item) >= 1:
                                targets.append((str(item[0]), item[1] if len(item) > 1 else None))
                        except Exception:
                            continue
                else:
                    try:
                        if isinstance(state.generated_files, list):
                            for fp in state.generated_files:
                                try:
                                    if isinstance(fp, str) and fp and os.path.exists(fp):
                                        targets.append((fp, None))
                                except Exception:
                                    continue
                    except Exception:
                        pass
            except Exception:
                pass
            for filepath, new_content in targets:
                try:
                    if not filepath or not os.path.exists(filepath):
                        continue
                    bn = os.path.basename(filepath)
                    is_edited = state.is_file_user_edited(filepath)
                    if is_edited:
                        conflict = {
                            "filepath": str(filepath),
                            "filename": bn,
                            "is_user_edited": True,
                            "old_hash": state.file_hashes.get(bn, ""),
                            "current_hash": compute_file_hash(filepath),
                        }
                        if new_content is not None:
                            conflict["new_hash"] = compute_content_hash(new_content)
                            try:
                                with open(filepath, "r", encoding="utf-8") as f:
                                    old_lines = [ln for ln in f.read().splitlines() if ln.strip()]
                                new_lines = [ln for ln in str(new_content).splitlines() if ln.strip()]
                                conflict["delta_old_lines"] = max(0, len(old_lines) - len(new_lines))
                                conflict["delta_new_lines"] = max(0, len(new_lines) - len(old_lines))
                            except Exception:
                                pass
                        conflicts.append(conflict)
                except Exception:
                    continue
            return conflicts
        except Exception:
            return conflicts

    def list_conflicting_files(self, episode_number: str, directory: str = "") -> List[str]:
        try:
            return [str(c.get("filename", "")) for c in self.detect_conflicts(episode_number, directory) if c.get("is_user_edited")]
        except Exception:
            return []

    def add_review_record(self, record: ReviewRecord) -> Optional[ReviewRecord]:
        with self._lock:
            try:
                if record is None:
                    return None
                if not record.id:
                    try:
                        import uuid
                        record.id = str(uuid.uuid4())
                    except Exception:
                        record.id = f"rev_{record.episode_number}_{int(datetime.now().timestamp())}"
                self._review_records.append(record)
                try:
                    state = self.get(record.episode_number, record.directory)
                    if state is not None:
                        try:
                            state.last_reviewed_at = str(record.created_at) if isinstance(record.created_at, str) else datetime.now().isoformat()
                            if isinstance(record.reviewer, str) and record.reviewer:
                                state.reviewer = str(record.reviewer)
                            if record.approved and isinstance(record.final_title, str) and record.final_title:
                                state.title = str(record.final_title)
                            if isinstance(record.notes, str) and record.notes:
                                try:
                                    if not isinstance(state.metadata, dict):
                                        state.metadata = {}
                                    state.metadata["last_review_notes"] = str(record.notes)
                                except Exception:
                                    pass
                        except Exception:
                            pass
                except Exception:
                    pass
                self._dirty = True
                return record
            except Exception:
                return None

    def get_review_records(self, episode_number: str = "", directory: str = "",
                           reviewer: str = "", approved_only: bool = False,
                           limit: Optional[int] = None) -> List[ReviewRecord]:
        try:
            with self._lock:
                out: List[ReviewRecord] = []
                for r in self._review_records:
                    try:
                        if episode_number and r.episode_number != str(episode_number):
                            continue
                        if reviewer and r.reviewer != str(reviewer):
                            continue
                        if approved_only and not r.approved:
                            continue
                        out.append(r)
                    except Exception:
                        continue
                try:
                    out.sort(key=lambda r: r.created_at, reverse=True)
                except Exception:
                    pass
                try:
                    if limit is not None and isinstance(limit, int) and limit > 0:
                        out = out[:limit]
                except Exception:
                    pass
                return out
        except Exception:
            return []

    def get_latest_review(self, episode_number: str, directory: str = "") -> Optional[ReviewRecord]:
        try:
            recs = self.get_review_records(episode_number, directory, limit=1)
            return recs[0] if recs else None
        except Exception:
            return None

    def has_pending_review(self, episode_number: str, directory: str = "") -> bool:
        try:
            state = self.get(episode_number, directory)
            if state is None:
                return False
            if state.is_pending_review:
                return True
            if state.is_draft:
                return True
            latest = self.get_latest_review(episode_number, directory)
            if latest is None:
                return state.is_draft
            return not latest.approved
        except Exception:
            return False

    def mark_scanned(self, episode_number: str, directory: str = "",
                     source_dir_mtime: Optional[str] = None) -> Optional[EpisodeState]:
        with self._lock:
            state = self.get_or_create(episode_number, directory)
            try:
                state.last_scanned_at = datetime.now().isoformat()
                if source_dir_mtime and isinstance(source_dir_mtime, str):
                    try:
                        if not isinstance(state.metadata, dict):
                            state.metadata = {}
                        state.metadata["input_dir_mtime"] = str(source_dir_mtime)
                    except Exception:
                        pass
                self._dirty = True
            except Exception:
                pass
            return state

    @property
    def dirty(self) -> bool:
        with self._lock:
            return self._dirty

    def __len__(self) -> int:
        with self._lock:
            return len(self._episodes)
