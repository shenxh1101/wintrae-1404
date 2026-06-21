
import os
import time
import threading
from pathlib import Path
from typing import Callable, Optional, List, Set
from datetime import datetime

from .config import Config
from .utils import list_files_by_extension, is_path_safe

try:
    from watchdog.observers import Observer
    from watchdog.events import (
        FileSystemEventHandler,
        FileCreatedEvent,
        FileModifiedEvent,
    )

    WATCHDOG_AVAILABLE = True
except ImportError:
    WATCHDOG_AVAILABLE = False


class FolderWatcher:
    def __init__(
        self,
        config: Config = None,
        on_change: Optional[Callable] = None,
        on_new_episode: Optional[Callable] = None,
    ):
        self.config = config or Config()
        try:
            self.input_dir = str(self.config.input_dir)
        except Exception:
            self.input_dir = "./input"
        self.on_change = on_change
        self.on_new_episode = on_new_episode

        self._observer: Optional[Observer] = None
        self._running = False
        self._poll_thread: Optional[threading.Thread] = None
        self._known_files: Set[str] = set()
        self._debounce_timers: dict = {}
        self._debounce_delay = 2.0
        self._processed_episodes: Set[str] = set()
        self._lock = threading.Lock()

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

        self._all_extensions: Set[str] = set(
            self._audio_extensions
            + self._cover_extensions
            + [".md", ".txt"]
        )

    def start(self):
        if self._running:
            return

        try:
            os.makedirs(self.input_dir, exist_ok=True)
        except Exception:
            pass

        if not os.path.exists(self.input_dir):
            return

        self._scan_initial_files()

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
                if new_files:
                    with self._lock:
                        self._known_files = current_files
                    for f in new_files:
                        try:
                            self._debounce(f, "created")
                        except Exception:
                            continue

                removed_files = self._known_files - current_files
                if removed_files:
                    with self._lock:
                        self._known_files = current_files

            except Exception:
                pass

            try:
                time.sleep(2)
            except Exception:
                break

    def _on_file_event(self, event):
        try:
            if not hasattr(event, "is_directory"):
                return
            if event.is_directory:
                return

            if not hasattr(event, "src_path"):
                return
            filepath = event.src_path
            if not filepath:
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

            event_type = "created" if isinstance(event, FileCreatedEvent) else "modified"
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
            self._check_episode_complete()
        except Exception:
            pass

    def _check_episode_complete(self):
        if not self.on_new_episode:
            return

        subdirs: List[str] = []
        try:
            if not os.path.exists(self.input_dir):
                return
            for item in os.listdir(self.input_dir):
                try:
                    item_path = os.path.join(self.input_dir, item)
                    if os.path.isdir(item_path) and is_path_safe(self.input_dir, item_path):
                        subdirs.append(item_path)
                except Exception:
                    continue
        except (OSError, PermissionError):
            return

        if not subdirs:
            if os.path.exists(self.input_dir):
                subdirs = [self.input_dir]

        for subdir in subdirs:
            try:
                if not is_path_safe(self.input_dir, subdir):
                    continue

                audio_files = list_files_by_extension(subdir, self._audio_extensions)
                has_audio = len(audio_files) > 0

                cover_files = list_files_by_extension(subdir, self._cover_extensions)
                has_cover = len(cover_files) > 0

                text_files = list_files_by_extension(subdir, [".md", ".txt"])
                has_guest = False
                has_summary = False
                for tf in text_files:
                    try:
                        basename = os.path.basename(tf).lower()
                        if "guest" in basename or "嘉宾" in basename:
                            has_guest = True
                        elif "summary" in basename or "摘要" in basename or "简介" in basename:
                            has_summary = True
                    except Exception:
                        continue

                if not has_guest and len(text_files) >= 1:
                    has_guest = True
                if not has_summary and len(text_files) >= 2:
                    has_summary = True
                elif not has_summary and len(text_files) == 1 and has_guest:
                    has_summary = True

                if has_audio and has_cover and has_guest and has_summary:
                    episode_key = os.path.normpath(subdir)
                    with self._lock:
                        if episode_key in self._processed_episodes:
                            continue
                        self._processed_episodes.add(episode_key)

                    try:
                        self.on_new_episode(subdir)
                    except Exception:
                        pass
            except Exception:
                continue

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
