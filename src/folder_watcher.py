
import os
import time
import hashlib
import threading
from pathlib import Path
from typing import Callable, Optional, List, Set, Dict, Tuple
from datetime import datetime

from .config import Config
from .utils import list_files_by_extension, is_path_safe

try:
    from watchdog.observers import Observer
    from watchdog.events import (
        FileSystemEventHandler,
        FileCreatedEvent,
        FileModifiedEvent,
        FileMovedEvent,
    )

    WATCHDOG_AVAILABLE = True
except ImportError:
    WATCHDOG_AVAILABLE = False


def _compute_dir_signature(directory: str, extensions: Set[str]) -> str:
    try:
        if not directory or not os.path.exists(directory):
            return ""
        files = []
        try:
            for root, _, filenames in os.walk(directory):
                try:
                    for fn in filenames:
                        try:
                            ext = Path(fn).suffix.lower()
                            if ext in extensions:
                                full = os.path.join(root, fn)
                                try:
                                    mtime = os.path.getmtime(full)
                                    size = os.path.getsize(full)
                                    files.append((full, mtime, size))
                                except Exception:
                                    files.append((full, 0, 0))
                        except Exception:
                            continue
                except Exception:
                    continue
        except Exception:
            pass
        files.sort()
        try:
            h = hashlib.md5()
            for f, m, s in files:
                h.update(f.encode("utf-8"))
                h.update(str(m).encode("utf-8"))
                h.update(str(s).encode("utf-8"))
            return h.hexdigest()
        except Exception:
            return str(files)
    except Exception:
        return ""


class FolderWatcher:
    def __init__(
        self,
        config: Config = None,
        on_change: Optional[Callable] = None,
        on_new_episode: Optional[Callable] = None,
        on_episode_updated: Optional[Callable] = None,
    ):
        try:
            self.config = config or Config()
        except Exception:
            from .config import Config
            self.config = Config()

        try:
            self.input_dir = str(self.config.input_dir)
        except Exception:
            self.input_dir = "./input"

        self.on_change = on_change
        self.on_new_episode = on_new_episode
        self.on_episode_updated = on_episode_updated

        self._observer: Optional[Observer] = None
        self._running = False
        self._poll_thread: Optional[threading.Thread] = None
        self._known_files: Set[str] = set()
        self._debounce_timers: Dict[str, threading.Timer] = {}
        self._debounce_delay = 2.0
        self._file_complete_delay = 1.0

        self._episode_signatures: Dict[str, str] = {}
        self._episode_incomplete_seen: Set[str] = set()
        self._episode_complete_seen: Set[str] = set()

        self._lock = threading.RLock()

        try:
            audio_exts = self.config.get("naming.audio_extensions", [".mp3"])
            self._audio_extensions: List[str] = [str(e).lower() for e in audio_exts if isinstance(e, str)]
        except Exception:
            self._audio_extensions = [".mp3"]

        try:
            cover_exts = self.config.get("naming.cover_extensions", [".jpg"])
            self._cover_extensions: List[str] = [str(e).lower() for e in cover_exts if isinstance(e, str)]
        except Exception:
            self._cover_extensions = [".jpg"]

        try:
            guest_exts = self.config.get("naming.guest_extensions", [".md", ".txt"])
            self._guest_extensions: List[str] = [str(e).lower() for e in guest_exts if isinstance(e, str)]
        except Exception:
            self._guest_extensions = [".md", ".txt"]

        try:
            summary_exts = self.config.get("naming.summary_extensions", [".md", ".txt"])
            self._summary_extensions: List[str] = [str(e).lower() for e in summary_exts if isinstance(e, str)]
        except Exception:
            self._summary_extensions = [".md", ".txt"]

        self._all_extensions: Set[str] = set(
            self._audio_extensions
            + self._cover_extensions
            + self._guest_extensions
            + self._summary_extensions
        )

    def start(self):
        if self._running:
            return

        try:
            os.makedirs(self.input_dir, exist_ok=True)
        except Exception:
            pass

        try:
            if not os.path.exists(self.input_dir):
                return
        except Exception:
            return

        try:
            self._scan_initial_files()
        except Exception:
            pass

        if not WATCHDOG_AVAILABLE:
            try:
                print("[警告] watchdog 库未安装，使用轮询模式")
            except Exception:
                pass
            self._start_polling()
            return

        self._start_watchdog()

    def _scan_initial_files(self):
        for ext in list(self._all_extensions):
            try:
                files = list_files_by_extension(self.input_dir, [ext])
                for f in files:
                    try:
                        if is_path_safe(self.input_dir, f):
                            self._known_files.add(f)
                    except Exception:
                        continue
            except Exception:
                continue

        try:
            self._check_all_episodes(initial=True)
        except Exception:
            pass

    def _start_watchdog(self):
        try:
            event_handler = _EventHandler(self._on_file_event)
            self._observer = Observer()
            self._observer.schedule(event_handler, self.input_dir, recursive=True)
            self._observer.start()
            self._running = True
        except Exception:
            try:
                print("[警告] watchdog 启动失败，使用轮询模式")
            except Exception:
                pass
            self._start_polling()

    def _start_polling(self):
        self._running = True
        self._poll_thread = threading.Thread(target=self._poll_loop, daemon=True)
        self._poll_thread.start()

    def _poll_loop(self):
        while self._running:
            try:
                current_files: Set[str] = set()
                for ext in list(self._all_extensions):
                    try:
                        files = list_files_by_extension(self.input_dir, [ext])
                        for f in files:
                            try:
                                if is_path_safe(self.input_dir, f):
                                    current_files.add(f)
                            except Exception:
                                continue
                    except Exception:
                        continue

                new_files = current_files - self._known_files
                removed_files = self._known_files - current_files
                changed = bool(new_files or removed_files)

                with self._lock:
                    self._known_files = current_files

                if changed:
                    try:
                        self._check_all_episodes()
                    except Exception:
                        pass

            except Exception:
                pass

            try:
                time.sleep(2)
            except Exception:
                break

    def _on_file_event(self, event):
        try:
            if event is None:
                return
            if hasattr(event, "is_directory") and event.is_directory:
                return

            filepath = None
            try:
                if isinstance(event, FileMovedEvent) and hasattr(event, "dest_path"):
                    filepath = event.dest_path
                elif hasattr(event, "src_path"):
                    filepath = event.src_path
            except Exception:
                return

            if not filepath or not isinstance(filepath, str):
                return

            try:
                if not is_path_safe(self.input_dir, filepath):
                    return
            except Exception:
                return

            ext = ""
            try:
                ext = Path(filepath).suffix.lower()
            except Exception:
                return
            if ext not in self._all_extensions:
                return

            event_type = "modified"
            try:
                if isinstance(event, FileCreatedEvent):
                    event_type = "created"
                elif isinstance(event, FileMovedEvent):
                    event_type = "moved"
                elif isinstance(event, FileModifiedEvent):
                    event_type = "modified"
            except Exception:
                event_type = "modified"

            try:
                self._debounce(filepath, event_type)
            except Exception:
                pass
        except Exception:
            pass

    def _debounce(self, filepath: str, event_type: str):
        try:
            if not filepath:
                return
            with self._lock:
                if filepath in self._debounce_timers:
                    old_timer = self._debounce_timers[filepath]
                    try:
                        old_timer.cancel()
                    except Exception:
                        pass

                timer = threading.Timer(
                    self._debounce_delay,
                    self._handle_file_event,
                    args=[filepath, event_type],
                )
                self._debounce_timers[filepath] = timer
                timer.daemon = True
                timer.start()
        except Exception:
            pass

    def _handle_file_event(self, filepath: str, event_type: str):
        try:
            with self._lock:
                if filepath in self._debounce_timers:
                    del self._debounce_timers[filepath]
        except Exception:
            pass

        try:
            if not os.path.exists(filepath):
                return
        except Exception:
            return

        try:
            file_size = os.path.getsize(filepath)
            if file_size == 0:
                return
        except (OSError, PermissionError):
            return

        try:
            with self._lock:
                self._known_files.add(filepath)
        except Exception:
            pass

        if self.on_change:
            try:
                self.on_change(filepath, event_type)
            except Exception:
                pass

        try:
            time.sleep(self._file_complete_delay)
        except Exception:
            pass

        try:
            self._check_all_episodes()
        except Exception:
            pass

    def _find_episode_dirs(self) -> List[str]:
        subdirs: List[str] = []
        try:
            if not os.path.exists(self.input_dir):
                return subdirs
            for item in os.listdir(self.input_dir):
                try:
                    item_path = os.path.join(self.input_dir, item)
                    if os.path.isdir(item_path) and is_path_safe(self.input_dir, item_path):
                        subdirs.append(item_path)
                except Exception:
                    continue
        except (OSError, PermissionError):
            return subdirs
        except Exception:
            return subdirs

        if not subdirs:
            try:
                if os.path.exists(self.input_dir):
                    subdirs = [self.input_dir]
            except Exception:
                pass
        return subdirs

    def _check_episode_files(self, subdir: str) -> Tuple[bool, Dict[str, str]]:
        status = {
            "audio": False,
            "cover": False,
            "guest": False,
            "summary": False,
        }
        found_files: Dict[str, str] = {}

        try:
            audio_files = list_files_by_extension(subdir, self._audio_extensions)
            if audio_files:
                status["audio"] = True
                found_files["audio"] = sorted(audio_files)[0]
        except Exception:
            pass

        try:
            cover_files = list_files_by_extension(subdir, self._cover_extensions)
            if cover_files:
                status["cover"] = True
                found_files["cover"] = sorted(cover_files)[0]
        except Exception:
            pass

        try:
            guest_files = list_files_by_extension(subdir, self._guest_extensions)
            for gf in guest_files:
                try:
                    basename = os.path.basename(gf).lower()
                    if "guest" in basename or "嘉宾" in basename:
                        status["guest"] = True
                        found_files["guest"] = gf
                        break
                except Exception:
                    continue
            if not status["guest"] and len(guest_files) >= 1:
                status["guest"] = True
                found_files["guest"] = sorted(guest_files)[0]
        except Exception:
            pass

        try:
            summary_files = list_files_by_extension(subdir, self._summary_extensions)
            for sf in summary_files:
                try:
                    basename = os.path.basename(sf).lower()
                    if "summary" in basename or "摘要" in basename or "简介" in basename:
                        status["summary"] = True
                        found_files["summary"] = sf
                        break
                except Exception:
                    continue
            if not status["summary"]:
                for sf in sorted(summary_files):
                    try:
                        if sf != found_files.get("guest"):
                            status["summary"] = True
                            found_files["summary"] = sf
                            break
                    except Exception:
                        continue
        except Exception:
            pass

        all_complete = all(status.values())
        return all_complete, found_files

    def _check_all_episodes(self, initial: bool = False):
        try:
            subdirs = self._find_episode_dirs()
        except Exception:
            return

        for subdir in subdirs:
            try:
                if not is_path_safe(self.input_dir, subdir):
                    continue

                episode_key = os.path.normpath(subdir)

                try:
                    current_sig = _compute_dir_signature(subdir, self._all_extensions)
                except Exception:
                    current_sig = ""

                try:
                    all_complete, _ = self._check_episode_files(subdir)
                except Exception:
                    all_complete = False

                with self._lock:
                    last_sig = self._episode_signatures.get(episode_key, "")
                    sig_changed = current_sig and current_sig != last_sig
                    if current_sig:
                        self._episode_signatures[episode_key] = current_sig

                should_notify_new = False
                should_notify_update = False

                if all_complete:
                    if episode_key not in self._episode_complete_seen or sig_changed:
                        if episode_key not in self._episode_complete_seen:
                            should_notify_new = True
                        else:
                            should_notify_update = True
                        with self._lock:
                            self._episode_complete_seen.add(episode_key)
                            if episode_key in self._episode_incomplete_seen:
                                self._episode_incomplete_seen.discard(episode_key)
                else:
                    with self._lock:
                        self._episode_incomplete_seen.add(episode_key)
                        if episode_key in self._episode_complete_seen:
                            self._episode_complete_seen.discard(episode_key)

                if should_notify_new and self.on_new_episode:
                    try:
                        self.on_new_episode(subdir)
                    except Exception:
                        pass

                if should_notify_update and self.on_episode_updated:
                    try:
                        self.on_episode_updated(subdir)
                    except Exception:
                        pass
                elif should_notify_update and self.on_new_episode:
                    try:
                        self.on_new_episode(subdir)
                    except Exception:
                        pass

            except Exception:
                continue

    def reset_episode(self, directory: str):
        try:
            if not directory:
                return
            key = os.path.normpath(directory)
            with self._lock:
                self._episode_incomplete_seen.discard(key)
                self._episode_complete_seen.discard(key)
                if key in self._episode_signatures:
                    del self._episode_signatures[key]
        except Exception:
            pass

    def reset_all(self):
        with self._lock:
            self._episode_incomplete_seen.clear()
            self._episode_complete_seen.clear()
            self._episode_signatures.clear()

    def stop(self):
        self._running = False

        with self._lock:
            for timer in list(self._debounce_timers.values()):
                try:
                    timer.cancel()
                except Exception:
                    continue
            self._debounce_timers.clear()

        if self._observer is not None:
            try:
                self._observer.stop()
                self._observer.join(timeout=5)
            except Exception:
                pass
            self._observer = None

    @property
    def is_running(self) -> bool:
        return self._running


class _EventHandler(FileSystemEventHandler):
    def __init__(self, callback):
        self.callback = callback

    def on_created(self, event):
        try:
            self.callback(event)
        except Exception:
            pass

    def on_modified(self, event):
        try:
            self.callback(event)
        except Exception:
            pass

    def on_moved(self, event):
        try:
            self.callback(event)
        except Exception:
            pass
