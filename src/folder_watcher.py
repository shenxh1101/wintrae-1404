
import os
import time
import threading
from pathlib import Path
from typing import Callable, Optional, List, Set
from datetime import datetime

from .config import Config
from .utils import list_files_by_extension

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
        self.input_dir = self.config.input_dir
        self.on_change = on_change
        self.on_new_episode = on_new_episode

        self._observer = None
        self._running = False
        self._known_files: Set[str] = set()
        self._debounce_timers: dict = {}
        self._debounce_delay = 2.0

        self._audio_extensions = self.config.get("naming.audio_extensions", [".mp3"])
        self._cover_extensions = self.config.get("naming.cover_extensions", [".jpg"])
        self._all_extensions = set(
            self._audio_extensions
            + self._cover_extensions
            + [".md", ".txt"]
        )

    def start(self):
        if self._running:
            return

        os.makedirs(self.input_dir, exist_ok=True)
        self._scan_initial_files()

        if not WATCHDOG_AVAILABLE:
            print("[警告] watchdog 库未安装，使用轮询模式")
            self._start_polling()
            return

        self._start_watchdog()

    def _scan_initial_files(self):
        for ext in self._all_extensions:
            files = list_files_by_extension(self.input_dir, [ext])
            for f in files:
                self._known_files.add(f)

    def _start_watchdog(self):
        event_handler = _EventHandler(self._on_file_event)
        self._observer = Observer()
        self._observer.schedule(event_handler, self.input_dir, recursive=True)
        self._observer.start()
        self._running = True

    def _start_polling(self):
        self._running = True
        poll_thread = threading.Thread(target=self._poll_loop, daemon=True)
        poll_thread.start()

    def _poll_loop(self):
        while self._running:
            try:
                current_files = set()
                for ext in self._all_extensions:
                    files = list_files_by_extension(self.input_dir, [ext])
                    current_files.update(files)

                new_files = current_files - self._known_files
                if new_files:
                    self._known_files = current_files
                    for f in new_files:
                        self._debounce(f, "created")

                removed_files = self._known_files - current_files
                if removed_files:
                    self._known_files = current_files

            except Exception as e:
                print(f"[轮询错误] {e}")

            time.sleep(2)

    def _on_file_event(self, event):
        if event.is_directory:
            return

        filepath = event.src_path
        ext = Path(filepath).suffix.lower()
        if ext not in self._all_extensions:
            return

        event_type = "created" if isinstance(event, FileCreatedEvent) else "modified"
        self._debounce(filepath, event_type)

    def _debounce(self, filepath: str, event_type: str):
        if filepath in self._debounce_timers:
            self._debounce_timers[filepath].cancel()

        timer = threading.Timer(
            self._debounce_delay, self._handle_file_event, args=[filepath, event_type]
        )
        self._debounce_timers[filepath] = timer
        timer.start()

    def _handle_file_event(self, filepath: str, event_type: str):
        if filepath in self._debounce_timers:
            del self._debounce_timers[filepath]

        if not os.path.exists(filepath):
            return

        file_size = os.path.getsize(filepath)
        if file_size == 0:
            return

        self._known_files.add(filepath)

        if self.on_change:
            try:
                self.on_change(filepath, event_type)
            except Exception as e:
                print(f"[回调错误] {e}")

        self._check_episode_complete()

    def _check_episode_complete(self):
        if not self.on_new_episode:
            return

        subdirs = [
            os.path.join(self.input_dir, d)
            for d in os.listdir(self.input_dir)
            if os.path.isdir(os.path.join(self.input_dir, d))
        ]

        if not subdirs:
            subdirs = [self.input_dir]

        for subdir in subdirs:
            has_audio = any(
                ext in self._audio_extensions
                for ext in [
                    Path(f).suffix.lower()
                    for f in list_files_by_extension(subdir, self._audio_extensions)
                ]
            )
            has_cover = any(
                ext in self._cover_extensions
                for ext in [
                    Path(f).suffix.lower()
                    for f in list_files_by_extension(subdir, self._cover_extensions)
                ]
            )
            has_guest = len(list_files_by_extension(subdir, [".md", ".txt"])) >= 1
            has_summary = len(list_files_by_extension(subdir, [".md", ".txt"])) >= 2

            if has_audio and has_cover and has_guest and has_summary:
                try:
                    self.on_new_episode(subdir)
                except Exception as e:
                    print(f"[新期数回调错误] {e}")

    def stop(self):
        self._running = False
        if self._observer:
            self._observer.stop()
            self._observer.join()
            self._observer = None

    @property
    def is_running(self) -> bool:
        return self._running


class _EventHandler(FileSystemEventHandler):
    def __init__(self, callback):
        self.callback = callback

    def on_created(self, event):
        self.callback(event)

    def on_modified(self, event):
        self.callback(event)
